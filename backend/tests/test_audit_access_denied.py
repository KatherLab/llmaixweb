# backend/tests/test_audit_access_denied.py
"""Authorization refusals are audited (``access_denied`` / outcome ``denied``).

Failed *authentication* was already covered (``login_failure``); what was
missing is the "logged in but not allowed" trail — the signal that surfaces a
compromised account probing for resources it can't reach. Auditing lives in the
two chokepoints every such refusal passes through, ``can_access_project`` and
``get_admin_user``, so all ~55 project gates are covered at one point.

Also covers the throttle: nothing rate-limits a client hammering a 403, so
identical denials must collapse rather than inflate an append-only table.
"""

from types import SimpleNamespace

import pytest


def _throttle_cache():
    """Lazy import — app modules must not be imported at module scope, or
    ``Settings()`` runs before the session env fixture configures it."""
    from backend.src.utils import audit as audit_service

    return audit_service._recent_denials


@pytest.fixture(autouse=True)
def reset_denial_throttle():
    """The throttle is a process-global; other test files trigger denials too
    (e.g. the admin-guard assertions), which would otherwise suppress the rows
    under test here."""
    _throttle_cache().clear()
    yield
    _throttle_cache().clear()


def _denials(client, api_url, admin_headers, **params):
    resp = client.get(
        f"{api_url}/admin/audit",
        headers=admin_headers,
        params={"action": "access_denied", **params},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["items"]


def test_cross_user_project_access_is_audited(
    client, api_url, login, admin_headers, make_project
):
    owner_headers = login("test@example.com", "Testpassword1")
    project = make_project(owner_headers, name="Denial Audit Project")

    intruder_headers = login("another@example.com", "Anotherpassword1")
    resp = client.get(f"{api_url}/project/{project['id']}", headers=intruder_headers)
    assert resp.status_code == 403, resp.text

    rows = _denials(client, api_url, admin_headers, project_id=project["id"])
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"] == "denied"
    assert row["actor_email"] == "another@example.com"
    assert row["resource_type"] == "project"
    assert row["resource_id"] == str(project["id"])
    # The row records *what* was probed, not just which resource was refused.
    assert row["detail"]["method"] == "GET"
    assert row["detail"]["path"] == f"/api/v1/project/{project['id']}"
    assert row["detail"]["reason"] == "not_project_owner"


def test_owner_access_writes_no_denial(
    client, api_url, login, admin_headers, make_project
):
    owner_headers = login("test@example.com", "Testpassword1")
    project = make_project(owner_headers, name="Allowed Project")

    assert (
        client.get(f"{api_url}/project/{project['id']}", headers=owner_headers)
    ).status_code == 200
    assert _denials(client, api_url, admin_headers, project_id=project["id"]) == []


def test_non_admin_on_admin_route_is_audited(client, api_url, login, admin_headers):
    user_headers = login("test@example.com", "Testpassword1")
    resp = client.get(f"{api_url}/admin/settings", headers=user_headers)
    assert resp.status_code == 403, resp.text

    rows = _denials(client, api_url, admin_headers, resource_type="admin_route")
    assert rows, "admin-guard refusal was not audited"
    row = rows[0]
    assert row["outcome"] == "denied"
    assert row["actor_email"] == "test@example.com"
    assert row["detail"]["reason"] == "admin_role_required"
    assert row["detail"]["path"] == f"{api_url}/admin/settings"


def test_repeated_identical_denials_are_throttled(
    client, api_url, login, admin_headers, make_project
):
    """A prober hammering one forbidden endpoint yields one row per window, not
    one row per request."""
    owner_headers = login("test@example.com", "Testpassword1")
    project = make_project(owner_headers, name="Throttle Project")
    intruder_headers = login("another@example.com", "Anotherpassword1")

    for _ in range(6):
        resp = client.get(
            f"{api_url}/project/{project['id']}", headers=intruder_headers
        )
        assert resp.status_code == 403

    rows = _denials(client, api_url, admin_headers, project_id=project["id"])
    assert len(rows) == 1

    # A *different* path against the same project is a distinct event.
    resp = client.get(
        f"{api_url}/project/{project['id']}/file", headers=intruder_headers
    )
    assert resp.status_code == 403
    paths = {
        r["detail"]["path"]
        for r in _denials(client, api_url, admin_headers, project_id=project["id"])
    }
    assert paths == {
        f"/api/v1/project/{project['id']}",
        f"/api/v1/project/{project['id']}/file",
    }


def test_audit_false_suppresses_the_row():
    """The escape hatch for using the predicate as a filter rather than a gate."""
    from backend.src.core.security import can_access_project
    from backend.src.db.session import SessionLocal
    from backend.src.models.user import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "test@example.com").one()
        foreign_project = SimpleNamespace(id=987654, owner_id=user.id + 10_000)

        assert can_access_project(user, foreign_project, audit=False) is False
        assert len(_throttle_cache()) == 0

        assert can_access_project(user, foreign_project) is False
        assert len(_throttle_cache()) == 1
    finally:
        db.close()
