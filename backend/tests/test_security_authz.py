# backend/tests/test_security_authz.py
"""Security-focused tests: cross-project authorization (IDOR) and the auth
hardening paths (refresh-token rotation + reuse detection, account lockout).

These cover surfaces the main suite didn't: the per-router project-access
checks (copy-pasted across files/documents/trials/... and thus prone to drift)
and the recently added refresh-token / lockout logic. None require an LLM.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_url():
    return "/api/v1"


@pytest.fixture
def client():
    from ..src.main import app

    return TestClient(app)


def _login(client, api_url, email, password):
    resp = client.post(
        f"{api_url}/auth/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _auth_headers(client, api_url, email, password):
    return {
        "Authorization": f"Bearer {_login(client, api_url, email, password)['access_token']}"
    }


# ─────────────────────────── Cross-project IDOR ───────────────────────────


def test_cross_project_access_matrix(client, api_url):
    """A non-owner must be denied on the project AND every sub-resource route.

    The project-access check is duplicated per sub-router, so this asserts the
    whole matrix rather than just the top-level project endpoints.
    """
    owner = _auth_headers(client, api_url, "test@example.com", "Testpassword1")
    other = _auth_headers(client, api_url, "another@example.com", "Anotherpassword1")

    # Owner creates a project.
    created = client.post(
        f"{api_url}/project",
        headers=owner,
        json={"name": "IDOR Project", "description": "owned by test@"},
    )
    assert created.status_code == 200, created.text
    pid = created.json()["id"]

    # Every sub-resource list endpoint must reject the non-owner. A leaked ID
    # must not expose another user's files/documents/trials/etc.
    sub_resource_paths = [
        f"/project/{pid}",
        f"/project/{pid}/file",
        f"/project/{pid}/document",
        f"/project/{pid}/document-set",
        f"/project/{pid}/trial",
        f"/project/{pid}/schema",
        f"/project/{pid}/prompt",
        f"/project/{pid}/groundtruth",
        # evaluation list requires a groundtruth_id query param; supply one so
        # request validation passes and the auth check is what rejects us.
        f"/project/{pid}/evaluation?groundtruth_id=1",
    ]
    for path in sub_resource_paths:
        resp = client.get(f"{api_url}{path}", headers=other)
        assert resp.status_code in (403, 404), (
            f"Expected non-owner to be denied on GET {path}, got {resp.status_code}"
        )

    # Mutating the project itself must also be denied.
    assert client.put(
        f"{api_url}/project/{pid}", headers=other, json={"name": "hijacked"}
    ).status_code in (403, 404)
    assert client.delete(f"{api_url}/project/{pid}", headers=other).status_code in (
        403,
        404,
    )

    # Sanity: the owner still has access.
    assert client.get(f"{api_url}/project/{pid}", headers=owner).status_code == 200

    # Cleanup.
    client.delete(f"{api_url}/project/{pid}", headers=owner)


def test_unauthenticated_requests_rejected(client, api_url):
    """No token → 401 on protected routes."""
    assert client.get(f"{api_url}/project").status_code == 401
    assert client.get(f"{api_url}/user/me").status_code == 401


# ─────────────────────────── Refresh-token rotation ───────────────────────────


def test_refresh_token_rotation_and_reuse_detection(client, api_url):
    """Rotation is single-use; replaying a rotated token revokes the family."""
    tokens = _login(client, api_url, "test@example.com", "Testpassword1")
    r0 = tokens["refresh_token"]
    assert r0

    # First use rotates: returns a new pair.
    first = client.post(f"{api_url}/auth/refresh", json={"refresh_token": r0})
    assert first.status_code == 200, first.text
    r1 = first.json()["refresh_token"]
    assert r1 and r1 != r0

    # Replaying the now-revoked r0 must fail...
    reuse = client.post(f"{api_url}/auth/refresh", json={"refresh_token": r0})
    assert reuse.status_code == 401

    # ...and the reuse must have revoked the whole family, so the freshly minted
    # r1 is now invalid too (theft-response).
    after = client.post(f"{api_url}/auth/refresh", json={"refresh_token": r1})
    assert after.status_code == 401


def test_forgot_password_does_not_enumerate(client, api_url):
    """The response must be identical for a registered and an unknown email so
    an attacker can't tell which accounts exist (even when SMTP is unconfigured,
    as in the test env)."""
    existing = client.post(
        f"{api_url}/user/forgot-password", json={"email": "test@example.com"}
    )
    missing = client.post(
        f"{api_url}/user/forgot-password",
        json={"email": "definitely-not-a-user@example.com"},
    )
    assert existing.status_code == missing.status_code
    assert existing.json() == missing.json()


def test_refresh_token_invalid_is_rejected(client, api_url):
    assert (
        client.post(
            f"{api_url}/auth/refresh", json={"refresh_token": "not-a-real-token"}
        ).status_code
        == 401
    )


# ─────────────────────────── Account lockout ───────────────────────────


def test_account_lockout_after_max_attempts(client, api_url):
    """After LOGIN_MAX_ATTEMPTS failures the account locks (423), even with the
    correct password, until the lock window elapses."""
    from ..src.core.dynamic_settings import get_settings
    from ..src.core.security import get_password_hash
    from ..src.db.session import SessionLocal
    from ..src.models.user import User, UserRole

    email = "lockme@example.com"
    password = "Lockmepassword1"

    # Create (or reset) a dedicated user so we don't lock a shared fixture user.
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name="Lock Me",
            hashed_password=get_password_hash(password),
            role=UserRole.user,
            is_active=True,
        )
        db.add(user)
    else:
        user.hashed_password = get_password_hash(password)
        user.failed_login_attempts = 0
        user.locked_until = None
    db.commit()
    db.close()

    max_attempts = get_settings().LOGIN_MAX_ATTEMPTS

    # Exhaust the attempts with a wrong password (each returns 401).
    for _ in range(max_attempts):
        resp = client.post(
            f"{api_url}/auth/login",
            data={"username": email, "password": "WrongPassword9"},
        )
        assert resp.status_code == 401, resp.text

    # Now the account is locked: even the CORRECT password returns 423.
    locked = client.post(
        f"{api_url}/auth/login", data={"username": email, "password": password}
    )
    assert locked.status_code == 423, locked.text
