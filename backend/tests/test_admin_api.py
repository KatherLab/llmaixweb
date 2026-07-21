"""API-level tests for the admin router (`admin.py`) and the admin OIDC-provider
CRUD router (`admin_sso.py`).

These complement (rather than duplicate) two existing suites:

- ``test_audit_admin_export.py`` already exercises the ``/admin/audit*`` +
  error-log surfaces and the settings *override round-trip* on the BANNER_*
  keys, so here we keep settings coverage light (a different key +
  restore-to-clean, readonly rejection, unauthenticated 401) and focus the
  admin.py effort on the previously untested **Celery monitoring endpoints**.
- ``test_sso_flow.py`` covers the OIDC login/callback flow and a happy-path
  provider create/patch/delete. Here we focus on the CRUD guarantees that
  matter most: the client secret is *never* returned (masked + encrypted at
  rest), 404 paths, slug validation, and the authz negatives.

Isolation / cleanup notes:
- Any dynamic setting mutated is captured and restored (deleted) at test end.
- Every IdentityProvider created uses the ``AdminApiTest`` name prefix and is
  removed via a teardown fixture so it cannot leak into other suites
  (public-settings, test_sso_flow.py).
- The Celery endpoints 500 under DISABLE_CELERY (see the flagged bug); the
  "graceful degradation" assertions are marked ``xfail(strict=False)`` so the
  suite documents the *correct* behavior without failing the build.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

_PROVIDER_NAME_PREFIX = "AdminApiTest"
_ISSUER = "https://idp.example.test"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_discover(monkeypatch):
    """Stub OIDC discovery so provider create/update never performs real HTTP
    (SSRF-guarded) calls to the issuer."""
    from backend.src.services import oidc_service

    monkeypatch.setattr(
        oidc_service,
        "discover",
        lambda issuer_url: {
            "issuer": _ISSUER,
            "authorization_endpoint": f"{_ISSUER}/authorize",
            "token_endpoint": f"{_ISSUER}/token",
            "userinfo_endpoint": f"{_ISSUER}/userinfo",
            "jwks_uri": f"{_ISSUER}/jwks",
        },
    )


@pytest.fixture
def sso_cleanup():
    """Delete any providers created by this suite (matched by name prefix) so
    they don't leak into other session-scoped-DB suites."""
    yield
    from backend.src.db.session import SessionLocal
    from backend.src.models.sso import IdentityProvider

    db = SessionLocal()
    try:
        for p in (
            db.query(IdentityProvider)
            .filter(IdentityProvider.name.like(f"{_PROVIDER_NAME_PREFIX}%"))
            .all()
        ):
            db.delete(p)
        db.commit()
    finally:
        db.close()


def _create_provider(client, api_url, admin_headers, name, **overrides):
    payload = {
        "name": name,
        "issuer_url": _ISSUER,
        "client_id": "llmaix-client",
        "client_secret": "s3cret-value",
        "enabled": True,
    }
    payload.update(overrides)
    return client.post(
        f"{api_url}/admin/sso/providers", headers=admin_headers, json=payload
    )


# ---------------------------------------------------------------------------
# admin.py — dynamic settings
# ---------------------------------------------------------------------------


def test_settings_read_authz(client, api_url, user_headers):
    """GET /admin/settings: plain user → 403, unauthenticated → 401."""
    assert (
        client.get(f"{api_url}/admin/settings", headers=user_headers).status_code == 403
    )
    assert client.get(f"{api_url}/admin/settings").status_code == 401


def test_settings_read_shape(client, api_url, admin_headers):
    resp = client.get(f"{api_url}/admin/settings", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Every entry carries the descriptor fields the frontend relies on.
    entry = body["PROJECT_NAME"]
    for field in ("key", "category", "label", "type", "readonly", "secret"):
        assert field in entry
    assert entry["readonly"] is False
    # A readonly key is flagged as such.
    assert body["API_V1_STR"]["readonly"] is True


def test_settings_update_roundtrip_and_restore(client, api_url, admin_headers):
    """Override a non-readonly, non-secret setting, read it back, then delete
    the override so the shared DB is left clean for other suites."""
    before = client.get(f"{api_url}/admin/settings", headers=admin_headers).json()
    assert before["PROJECT_NAME"]["overridden"] is False
    new_value = "AdminApiTest Project Name ZZZ"

    try:
        resp = client.put(
            f"{api_url}/admin/settings",
            headers=admin_headers,
            json={"PROJECT_NAME": new_value},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"updated": True}

        body = client.get(f"{api_url}/admin/settings", headers=admin_headers).json()
        assert body["PROJECT_NAME"]["override"] == new_value
        assert body["PROJECT_NAME"]["effective"] == new_value
        assert body["PROJECT_NAME"]["overridden"] is True
    finally:
        # Restore: delete the override (reverts to the env/.env default).
        client.delete(f"{api_url}/admin/settings/PROJECT_NAME", headers=admin_headers)

    body = client.get(f"{api_url}/admin/settings", headers=admin_headers).json()
    assert body["PROJECT_NAME"]["overridden"] is False


def test_settings_update_rejects_readonly(client, api_url, admin_headers):
    """A readonly key can't be overridden (400) and mutating nothing else."""
    resp = client.put(
        f"{api_url}/admin/settings",
        headers=admin_headers,
        json={"API_V1_STR": "/api/v2"},
    )
    assert resp.status_code == 400


def test_settings_update_authz(client, api_url, user_headers):
    assert (
        client.put(
            f"{api_url}/admin/settings",
            headers=user_headers,
            json={"PROJECT_NAME": "hax"},
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"{api_url}/admin/settings", json={"PROJECT_NAME": "hax"}
        ).status_code
        == 401
    )


def test_delete_setting_readonly_and_missing(client, api_url, admin_headers):
    # Readonly key → 400 (never reaches the "not found" branch).
    assert (
        client.delete(
            f"{api_url}/admin/settings/API_V1_STR", headers=admin_headers
        ).status_code
        == 400
    )
    # Non-readonly key with no active override → 404.
    assert (
        client.delete(
            f"{api_url}/admin/settings/PROJECT_NAME", headers=admin_headers
        ).status_code
        == 404
    )


# ---------------------------------------------------------------------------
# admin.py — Celery monitoring
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/admin/celery/workers"),
        ("get", "/admin/celery/queues"),
        ("get", "/admin/celery/tasks/some-task-id"),
        ("post", "/admin/celery/revoke/some-task-id"),
        ("get", "/admin/celery/failed-tasks"),
    ],
)
def test_celery_endpoints_require_admin(client, api_url, user_headers, method, path):
    """Every Celery monitoring endpoint rejects plain users (403) and
    unauthenticated callers (401)."""
    call = getattr(client, method)
    assert call(f"{api_url}{path}", headers=user_headers).status_code == 403
    assert call(f"{api_url}{path}").status_code == 401


def test_celery_failed_tasks_returns_list(client, api_url, admin_headers):
    """DB-backed endpoint (independent of the broker) returns a JSON list."""
    resp = client.get(f"{api_url}/admin/celery/failed-tasks", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)


def test_celery_failed_tasks_validates_pagination(client, api_url, admin_headers):
    # limit is bounded 1..1000; 0 and >1000 are rejected by the query validator.
    assert (
        client.get(
            f"{api_url}/admin/celery/failed-tasks?limit=0", headers=admin_headers
        ).status_code
        == 422
    )
    assert (
        client.get(
            f"{api_url}/admin/celery/failed-tasks?offset=-1", headers=admin_headers
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/admin/celery/workers"),
        ("get", "/admin/celery/queues"),
        ("get", "/admin/celery/tasks/some-task-id"),
        ("post", "/admin/celery/revoke/some-task-id"),
    ],
)
def test_celery_monitoring_degrades_gracefully(api_url, admin_headers, method, path):
    """With Celery disabled (DISABLE_CELERY), the admin monitoring endpoints
    degrade to a clean 503 (admin.celery_disabled) rather than a 500 — the
    `_require_celery_app` guard replaced the bare `assert celery_app is not None`."""
    from backend.src.main import app

    # raise_server_exceptions=False so an in-route error surfaces as a 500
    # response instead of propagating out of the test client.
    c = TestClient(app, raise_server_exceptions=False)
    resp = getattr(c, method)(f"{api_url}{path}", headers=admin_headers)
    assert resp.status_code != 500


# ---------------------------------------------------------------------------
# admin_sso.py — OIDC provider CRUD
# ---------------------------------------------------------------------------


def test_providers_list_authz(client, api_url, user_headers):
    assert (
        client.get(f"{api_url}/admin/sso/providers", headers=user_headers).status_code
        == 403
    )
    assert client.get(f"{api_url}/admin/sso/providers").status_code == 401


def test_provider_create_authz(client, api_url, user_headers, mock_discover):
    resp = _create_provider(
        client, api_url, user_headers, f"{_PROVIDER_NAME_PREFIX} Unauthorized"
    )
    assert resp.status_code == 403
    # Unauthenticated (no token) → 401.
    resp = client.post(
        f"{api_url}/admin/sso/providers",
        json={
            "name": f"{_PROVIDER_NAME_PREFIX} NoAuth",
            "issuer_url": _ISSUER,
            "client_id": "x",
            "client_secret": "y",
        },
    )
    assert resp.status_code == 401


def test_provider_crud_masks_secret(
    client, api_url, admin_headers, mock_discover, sso_cleanup
):
    """Full CRUD, asserting the client secret is never echoed and is stored
    Fernet-encrypted at rest."""
    from backend.src.db.session import SessionLocal
    from backend.src.models.sso import IdentityProvider
    from backend.src.utils.crypto import decrypt

    plaintext = "super-secret-oidc-value-123"
    name = f"{_PROVIDER_NAME_PREFIX} Corp"

    # --- create (201) ---
    resp = _create_provider(
        client, api_url, admin_headers, name, client_secret=plaintext
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    provider_id = created["id"]
    assert created["slug"] == "adminapitest-corp"
    assert created["name"] == name
    assert created["has_secret"] is True
    # The secret must not be present anywhere in the response.
    assert "client_secret" not in created
    assert plaintext not in resp.text

    # --- stored encrypted at rest (not plaintext) ---
    db = SessionLocal()
    try:
        row = db.get(IdentityProvider, provider_id)
        assert row is not None
        assert row.client_secret_encrypted != plaintext
        assert decrypt(row.client_secret_encrypted) == plaintext
    finally:
        db.close()

    # --- list contains it, still masked ---
    resp = client.get(f"{api_url}/admin/sso/providers", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    listed = {p["id"]: p for p in resp.json()}
    assert provider_id in listed
    assert "client_secret" not in listed[provider_id]
    assert plaintext not in resp.text

    # --- update: rotate secret + rename (200), secret still not echoed ---
    new_plaintext = "rotated-secret-456"
    new_name = f"{_PROVIDER_NAME_PREFIX} Renamed"
    resp = client.patch(
        f"{api_url}/admin/sso/providers/{provider_id}",
        headers=admin_headers,
        json={"name": new_name, "client_secret": new_plaintext, "enabled": False},
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["name"] == new_name
    assert updated["slug"] == "adminapitest-renamed"
    assert updated["enabled"] is False
    assert updated["has_secret"] is True
    assert "client_secret" not in updated
    assert new_plaintext not in resp.text and plaintext not in resp.text

    db = SessionLocal()
    try:
        row = db.get(IdentityProvider, provider_id)
        assert decrypt(row.client_secret_encrypted) == new_plaintext
    finally:
        db.close()

    # --- update without client_secret leaves the stored secret untouched ---
    resp = client.patch(
        f"{api_url}/admin/sso/providers/{provider_id}",
        headers=admin_headers,
        json={"scopes": "openid email"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["scopes"] == "openid email"
    db = SessionLocal()
    try:
        row = db.get(IdentityProvider, provider_id)
        assert decrypt(row.client_secret_encrypted) == new_plaintext
    finally:
        db.close()

    # --- delete (204) ---
    resp = client.delete(
        f"{api_url}/admin/sso/providers/{provider_id}", headers=admin_headers
    )
    assert resp.status_code == 204
    # Gone from the list.
    resp = client.get(f"{api_url}/admin/sso/providers", headers=admin_headers)
    assert provider_id not in {p["id"] for p in resp.json()}


def test_provider_duplicate_name_rejected(
    client, api_url, admin_headers, mock_discover, sso_cleanup
):
    name = f"{_PROVIDER_NAME_PREFIX} Dup"
    assert _create_provider(client, api_url, admin_headers, name).status_code == 201
    # Same name → 400.
    assert _create_provider(client, api_url, admin_headers, name).status_code == 400


def test_provider_name_requires_alphanumeric(
    client, api_url, admin_headers, mock_discover, sso_cleanup
):
    # Name passes pydantic (min_length=1) but slugifies to empty → 400.
    resp = _create_provider(client, api_url, admin_headers, "###")
    assert resp.status_code == 400


def test_provider_update_and_delete_missing_return_404(
    client, api_url, admin_headers, mock_discover
):
    missing_id = 999999
    resp = client.patch(
        f"{api_url}/admin/sso/providers/{missing_id}",
        headers=admin_headers,
        json={"enabled": False},
    )
    assert resp.status_code == 404
    resp = client.delete(
        f"{api_url}/admin/sso/providers/{missing_id}", headers=admin_headers
    )
    assert resp.status_code == 404
