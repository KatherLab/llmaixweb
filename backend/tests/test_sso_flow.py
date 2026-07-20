# backend/tests/test_sso_flow.py
"""End-to-end OIDC SSO flow tests with the IdP network layer mocked.

Only the functions in ``services/oidc_service.py`` that perform HTTP calls to
the IdP (``discover``, ``exchange_code``, ``fetch_userinfo``) are monkeypatched
— everything else runs for real: the signed state JWT round-trip (PKCE
verifier + nonce + redirect embedded), the state cookie, provider resolution,
the verified-email takeover guard, JIT provisioning, and token issuance.

Covers the previously untested account-takeover guard: an IdP asserting an
UNVERIFIED email matching an existing local account must not be able to link
to (i.e. take over) that account.
"""

from urllib.parse import parse_qs, urlparse

import pytest

from backend.src.core import config
from backend.src.services import oidc_service

_ISSUER = "https://idp.example.test"

_DISCOVERY_DOC = {
    "issuer": _ISSUER,
    "authorization_endpoint": f"{_ISSUER}/authorize",
    "token_endpoint": f"{_ISSUER}/token",
    "userinfo_endpoint": f"{_ISSUER}/userinfo",
    "jwks_uri": f"{_ISSUER}/jwks",
}


# ─────────────────────────── helpers / fixtures ───────────────────────────


def _login_headers(client, api_url, email, password):
    resp = client.post(
        f"{api_url}/auth/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _admin_headers(client, api_url):
    return _login_headers(client, api_url, "admin@example.com", "Adminpassword1")


@pytest.fixture
def sso_settings(monkeypatch):
    """Enable SSO on the live settings instance (the proxy has __slots__=(),
    so patch the underlying Settings object) and mock OIDC discovery."""
    s = config._get_settings()
    monkeypatch.setattr(s, "SSO_ENABLED", True)
    monkeypatch.setattr(s, "APP_URL", "http://testserver")
    monkeypatch.setattr(s, "SSO_REQUIRE_VERIFIED_EMAIL", True)
    monkeypatch.setattr(
        oidc_service, "discover", lambda issuer_url: dict(_DISCOVERY_DOC)
    )
    return s


@pytest.fixture
def cleanup_sso():
    """Remove identities, providers, and JIT-provisioned users after the test
    so the session-scoped shared test DB stays clean for other files."""
    yield
    from backend.src.db.session import SessionLocal
    from backend.src.models import User, UserIdentity
    from backend.src.models.sso import IdentityProvider

    db = SessionLocal()
    db.query(UserIdentity).delete()
    db.query(IdentityProvider).delete()
    for user in db.query(User).filter(User.email.like("%@sso.example.com")).all():
        db.delete(user)
    db.commit()
    db.close()


def _create_provider(client, api_url, name="Test IdP", enabled=True):
    resp = client.post(
        f"{api_url}/admin/sso/providers",
        headers=_admin_headers(client, api_url),
        json={
            "name": name,
            "issuer_url": _ISSUER,
            "client_id": "llmaix-client",
            "client_secret": "s3cret",
            "enabled": enabled,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _start_login(client, api_url, slug, redirect="/"):
    """GET the login redirect; return the state param (cookie is kept by the
    client's jar automatically)."""
    resp = client.get(
        f"{api_url}/auth/sso/{slug}/login",
        params={"redirect": redirect},
        follow_redirects=False,
    )
    assert resp.status_code == 302, resp.text
    query = parse_qs(urlparse(resp.headers["location"]).query)
    return resp, query["state"][0]


def _mock_idp_user(monkeypatch, userinfo: dict, token_resp: dict | None = None):
    """Mock the code exchange + userinfo the callback performs against the IdP."""
    monkeypatch.setattr(
        oidc_service,
        "exchange_code",
        lambda **kwargs: dict(token_resp or {"access_token": "idp-access-token"}),
    )
    monkeypatch.setattr(
        oidc_service, "fetch_userinfo", lambda issuer_url, token: dict(userinfo)
    )


def _callback(client, api_url, slug, state, code="authcode"):
    return client.get(
        f"{api_url}/auth/sso/{slug}/callback",
        params={"code": code, "state": state},
        follow_redirects=False,
    )


def _fragment_params(location: str) -> dict:
    frag = urlparse(location).fragment
    return {k: v[0] for k, v in parse_qs(frag).items()}


# ─────────────────────────── gating & provider CRUD ───────────────────────────


def test_sso_login_requires_sso_enabled(client, api_url):
    # SSO_ENABLED defaults to False in the test env.
    resp = client.get(f"{api_url}/auth/sso/whatever/login", follow_redirects=False)
    assert resp.status_code == 403


def test_admin_provider_crud(client, api_url, sso_settings, cleanup_sso):
    # Non-admins cannot manage providers.
    user_headers = _login_headers(client, api_url, "test@example.com", "Testpassword1")
    assert (
        client.get(f"{api_url}/admin/sso/providers", headers=user_headers).status_code
        == 403
    )

    provider = _create_provider(client, api_url, name="My Corp IdP")
    assert provider["slug"] == "my-corp-idp"
    assert provider["has_secret"] is True

    admin_headers = _admin_headers(client, api_url)

    # Duplicate name is rejected.
    resp = client.post(
        f"{api_url}/admin/sso/providers",
        headers=admin_headers,
        json={
            "name": "My Corp IdP",
            "issuer_url": _ISSUER,
            "client_id": "x",
            "client_secret": "y",
        },
    )
    assert resp.status_code == 400

    # Enabled providers are exposed in the public login settings.
    public = client.get(f"{api_url}/auth/settings").json()
    assert public["sso_enabled"] is True
    assert {"slug": "my-corp-idp", "name": "My Corp IdP"} in public["sso_providers"]

    # Disable → login refused, provider gone from public settings.
    resp = client.patch(
        f"{api_url}/admin/sso/providers/{provider['id']}",
        headers=admin_headers,
        json={"enabled": False},
    )
    assert resp.status_code == 200 and resp.json()["enabled"] is False
    resp = client.get(f"{api_url}/auth/sso/my-corp-idp/login", follow_redirects=False)
    assert resp.status_code == 403
    public = client.get(f"{api_url}/auth/settings").json()
    assert public["sso_providers"] == []

    # Delete.
    assert (
        client.delete(
            f"{api_url}/admin/sso/providers/{provider['id']}", headers=admin_headers
        ).status_code
        == 204
    )
    resp = client.get(f"{api_url}/auth/sso/my-corp-idp/login", follow_redirects=False)
    assert resp.status_code == 404


# ─────────────────────────── login redirect ───────────────────────────


def test_login_redirect_carries_pkce_and_sets_state_cookie(
    client, api_url, sso_settings, cleanup_sso
):
    provider = _create_provider(client, api_url)
    resp, state = _start_login(client, api_url, provider["slug"])

    location = resp.headers["location"]
    assert location.startswith(_DISCOVERY_DOC["authorization_endpoint"])
    query = parse_qs(urlparse(location).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["llmaix-client"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"][0]
    assert query["nonce"][0]
    assert query["redirect_uri"] == [
        f"http://testserver/api/v1/auth/sso/{provider['slug']}/callback"
    ]

    # The state cookie must match the state query param (verified on callback).
    assert client.cookies.get("sso_state") == state


# ─────────────────────────── full flow: JIT provisioning ───────────────────────────


def test_full_flow_jit_provisions_user_and_issues_tokens(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_provider(client, api_url)
    _, state = _start_login(client, api_url, provider["slug"], redirect="/projects")
    _mock_idp_user(
        monkeypatch,
        {
            "sub": "subject-jit-1",
            "email": "new.user@sso.example.com",
            "email_verified": True,
            "name": "New SSO User",
        },
    )

    resp = _callback(client, api_url, provider["slug"], state)
    assert resp.status_code == 302, resp.text
    location = resp.headers["location"]
    assert location.startswith("http://testserver/auth/sso/complete#")
    params = _fragment_params(location)
    assert params["redirect"] == "/projects"

    # The issued access token authenticates the JIT-created user.
    headers = {"Authorization": f"Bearer {params['access_token']}"}
    me = client.get(f"{api_url}/user/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "new.user@sso.example.com"
    assert me.json()["full_name"] == "New SSO User"
    assert me.json()["role"] == "user"

    # The refresh token works.
    refreshed = client.post(
        f"{api_url}/auth/refresh", json={"refresh_token": params["refresh_token"]}
    )
    assert refreshed.status_code == 200, refreshed.text

    # The identity is linked exactly once.
    identities = client.get(f"{api_url}/user/me/identities", headers=headers).json()
    assert len(identities) == 1
    assert identities[0]["external_subject"] == "subject-jit-1"

    # JIT users have no password — password login must be impossible.
    resp = client.post(
        f"{api_url}/auth/login",
        data={"username": "new.user@sso.example.com", "password": "Anything123"},
    )
    assert resp.status_code in (400, 401, 403)

    # …and unlinking the last identity would lock them out → refused.
    resp = client.delete(
        f"{api_url}/user/me/identities/{identities[0]['id']}", headers=headers
    )
    assert resp.status_code == 400

    # A second SSO login with the same subject reuses the account (no dup).
    _, state2 = _start_login(client, api_url, provider["slug"])
    resp2 = _callback(client, api_url, provider["slug"], state2)
    assert resp2.status_code == 302
    params2 = _fragment_params(resp2.headers["location"])
    headers2 = {"Authorization": f"Bearer {params2['access_token']}"}
    assert (
        client.get(f"{api_url}/user/me", headers=headers2).json()["id"]
        == me.json()["id"]
    )
    identities = client.get(f"{api_url}/user/me/identities", headers=headers2).json()
    assert len(identities) == 1


# ─────────────────────────── the takeover guard ───────────────────────────


def test_unverified_email_cannot_link_existing_account(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    """THE takeover guard: an IdP asserting an existing local user's email
    WITHOUT email_verified must not link (= take over) that account."""
    provider = _create_provider(client, api_url)
    _, state = _start_login(client, api_url, provider["slug"])
    _mock_idp_user(
        monkeypatch,
        {
            "sub": "attacker-subject",
            "email": "another@example.com",  # existing local user (conftest)
            "email_verified": False,
        },
    )

    resp = _callback(client, api_url, provider["slug"], state)
    assert resp.status_code == 403, resp.text
    assert "verify" in resp.json()["detail"].lower()

    # No identity was linked; the victim's password login is untouched.
    victim_headers = _login_headers(
        client, api_url, "another@example.com", "Anotherpassword1"
    )
    identities = client.get(
        f"{api_url}/user/me/identities", headers=victim_headers
    ).json()
    assert identities == []

    # Same claim with a missing email_verified claim is equally refused.
    _, state = _start_login(client, api_url, provider["slug"])
    _mock_idp_user(
        monkeypatch, {"sub": "attacker-subject", "email": "another@example.com"}
    )
    assert _callback(client, api_url, provider["slug"], state).status_code == 403

    # With a VERIFIED email (string "true" — some IdPs send it that way),
    # linking the account is legitimate and succeeds.
    _, state = _start_login(client, api_url, provider["slug"])
    _mock_idp_user(
        monkeypatch,
        {
            "sub": "legit-subject",
            "email": "another@example.com",
            "email_verified": "true",
        },
    )
    resp = _callback(client, api_url, provider["slug"], state)
    assert resp.status_code == 302, resp.text
    params = _fragment_params(resp.headers["location"])
    headers = {"Authorization": f"Bearer {params['access_token']}"}
    assert (
        client.get(f"{api_url}/user/me", headers=headers).json()["email"]
        == "another@example.com"
    )
    identities = client.get(f"{api_url}/user/me/identities", headers=headers).json()
    assert len(identities) == 1 and identities[0]["external_subject"] == "legit-subject"


# ─────────────────────────── state / CSRF hardening ───────────────────────────


def test_callback_rejects_missing_or_mismatched_state_cookie(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_provider(client, api_url)
    _, state = _start_login(client, api_url, provider["slug"])
    _mock_idp_user(monkeypatch, {"sub": "s", "email": "x@sso.example.com"})

    # Valid state JWT but no cookie (e.g. state injected into another browser).
    client.cookies.delete("sso_state")
    resp = _callback(client, api_url, provider["slug"], state)
    assert resp.status_code == 400
    assert "cookie" in resp.json()["detail"].lower()

    # Cookie present but holding a DIFFERENT state than the query param.
    _start_login(client, api_url, provider["slug"])  # sets a fresh cookie
    resp = _callback(client, api_url, provider["slug"], state)  # old state param
    assert resp.status_code == 400

    # Tampered/garbage state JWT.
    client.cookies.set("sso_state", "garbage.token.here")
    resp = _callback(client, api_url, provider["slug"], "garbage.token.here")
    assert resp.status_code == 400

    # Missing code/state entirely.
    resp = client.get(
        f"{api_url}/auth/sso/{provider['slug']}/callback", follow_redirects=False
    )
    assert resp.status_code == 400


def test_callback_rejects_state_from_other_provider(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider_a = _create_provider(client, api_url, name="IdP A")
    provider_b = _create_provider(client, api_url, name="IdP B")
    _, state_a = _start_login(client, api_url, provider_a["slug"])
    _mock_idp_user(monkeypatch, {"sub": "s", "email": "x@sso.example.com"})

    # State minted for provider A must not be accepted on B's callback.
    resp = _callback(client, api_url, provider_b["slug"], state_a)
    assert resp.status_code == 400
    assert "provider" in resp.json()["detail"].lower()


def test_open_redirect_target_is_whitelisted(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_provider(client, api_url)
    # Protocol-relative external target smuggled through the login redirect.
    _, state = _start_login(client, api_url, provider["slug"], redirect="//evil.test")
    _mock_idp_user(
        monkeypatch,
        {"sub": "r", "email": "redir@sso.example.com", "email_verified": True},
    )

    resp = _callback(client, api_url, provider["slug"], state)
    assert resp.status_code == 302
    location = resp.headers["location"]
    # Still lands on OUR origin, and the post-login target is coerced to "/".
    assert location.startswith("http://testserver/auth/sso/complete#")
    assert _fragment_params(location)["redirect"] == "/"


# ─────────────────────────── provisioning edge cases ───────────────────────────


def test_jit_gated_by_invitation(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    monkeypatch.setattr(sso_settings, "REQUIRE_INVITATION", True)
    monkeypatch.setattr(sso_settings, "SSO_BYPASS_INVITATION", False)

    provider = _create_provider(client, api_url)
    _, state = _start_login(client, api_url, provider["slug"])
    _mock_idp_user(
        monkeypatch,
        {"sub": "gated", "email": "gated@sso.example.com", "email_verified": True},
    )

    resp = _callback(client, api_url, provider["slug"], state)
    assert resp.status_code == 403
    assert "invitation" in resp.json()["detail"].lower()

    # No account was created.
    from backend.src.db.session import SessionLocal
    from backend.src.models import User

    db = SessionLocal()
    exists = db.query(User).filter(User.email == "gated@sso.example.com").first()
    db.close()
    assert exists is None


def test_missing_subject_or_email_rejected(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_provider(client, api_url)

    # No subject → 400.
    _, state = _start_login(client, api_url, provider["slug"])
    _mock_idp_user(monkeypatch, {"email": "nosub@sso.example.com"})
    assert _callback(client, api_url, provider["slug"], state).status_code == 400

    # Subject but no email for a brand-new identity → cannot create an account.
    _, state = _start_login(client, api_url, provider["slug"])
    _mock_idp_user(monkeypatch, {"sub": "no-email-subject"})
    resp = _callback(client, api_url, provider["slug"], state)
    assert resp.status_code == 400
    assert "email" in resp.json()["detail"].lower()


def test_deactivated_user_cannot_sso_login(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    from backend.src.core.security import get_password_hash
    from backend.src.db.session import SessionLocal
    from backend.src.models.user import User, UserRole

    db = SessionLocal()
    user = User(
        email="inactive@sso.example.com",
        full_name="Inactive",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.user,
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.close()

    provider = _create_provider(client, api_url)
    _, state = _start_login(client, api_url, provider["slug"])
    _mock_idp_user(
        monkeypatch,
        {
            "sub": "inactive-sub",
            "email": "inactive@sso.example.com",
            "email_verified": True,
        },
    )
    resp = _callback(client, api_url, provider["slug"], state)
    assert resp.status_code == 403
    assert "deactivated" in resp.json()["detail"].lower()
