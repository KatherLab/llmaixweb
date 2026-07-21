# backend/tests/test_users_api.py
"""API-level tests for backend/src/routers/v1/endpoints/users.py.

Complements test_auth.py (which already covers login, /user/me, list_users,
invite, validate-invitation, list/delete invitations, toggle-status, delete_user,
and the password-reset flow). This file focuses on the remaining surface:

  * create_user (POST /user) — admin-role rejection, missing invitation,
    duplicate email, weak password, happy path
  * change_password (POST /user/change-password)
  * admin_set_user_password (POST /user/{id}/set-password)
  * admin_update_user (PATCH /user/{id}) — role/active/email/self-guards
  * toggle_user_status admin guard
  * delete_user self/admin guards
  * /user/me/identities (list + delete)
  * first-admin-check / first-admin (blocked when an admin exists)
  * authz negatives (plain user -> 403, unauthenticated -> 401)
  * response leak check (no hashed_password / token_version in payloads)

Test isolation: seeded users (admin@/test@/another@/delete@) are NOT mutated in
any unrestored way. Password changes and role/status flips operate only on
freshly-created throwaway users with unique emails.
"""

import uuid

import pytest

STRONG_PW = "Throwpassword1"


def _unique_email(prefix: str = "throwaway") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


def _make_throwaway_user(
    client,
    api_url,
    admin_headers,
    *,
    email=None,
    password=STRONG_PW,
    full_name="Throwaway User",
):
    """Invite + register a fresh plain user; return the created user dict.

    Uses the public registration flow so it exercises the real code path and
    never touches the shared seeded accounts.
    """
    email = email or _unique_email()
    # Admin invites the email (multipart form).
    resp = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data={"email": email}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]

    resp = client.post(
        f"{api_url}/user",
        json={
            "email": email,
            "full_name": full_name,
            "password": password,
            "invitation_token": token,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _user_id_by_email(client, api_url, admin_headers, email):
    resp = client.get(f"{api_url}/user", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    match = next((u for u in resp.json() if u["email"] == email), None)
    assert match is not None, f"user {email} not found"
    return match["id"]


# ---------------------------------------------------------------------------
# first-admin endpoints (an admin already exists in the seeded DB)
# ---------------------------------------------------------------------------


def test_first_admin_check_disallowed_when_admin_exists(client, api_url):
    resp = client.get(f"{api_url}/user/first-admin-check")
    assert resp.status_code == 200, resp.text
    assert resp.json()["allow_first_admin_setup"] is False


def test_create_first_admin_forbidden_when_admin_exists(client, api_url):
    resp = client.post(
        f"{api_url}/user/first-admin",
        json={
            "email": _unique_email("firstadmin"),
            "full_name": "Would-be Admin",
            "password": "Firstadminpassword1",
            "role": "admin",
        },
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"]["code"] == "users.first_admin_not_allowed"


# ---------------------------------------------------------------------------
# create_user (POST /user)
# ---------------------------------------------------------------------------


def test_create_user_success_with_invitation(client, api_url, admin_headers):
    email = _unique_email("created")
    resp = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data={"email": email}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]

    resp = client.post(
        f"{api_url}/user",
        json={
            "email": email,
            "full_name": "Created User",
            "password": STRONG_PW,
            "invitation_token": token,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == email
    assert body["role"] == "user"
    assert body["is_active"] is True


def test_create_user_rejects_admin_role(client, api_url, admin_headers):
    """Cannot self-provision an admin account via the public create endpoint."""
    email = _unique_email("wantadmin")
    resp = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data={"email": email}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]

    resp = client.post(
        f"{api_url}/user",
        json={
            "email": email,
            "full_name": "Escalation Attempt",
            "password": STRONG_PW,
            "role": "admin",
            "invitation_token": token,
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.cannot_create_admin"


def test_create_user_requires_invitation(client, api_url):
    """REQUIRE_INVITATION defaults True — no token means generic failure."""
    resp = client.post(
        f"{api_url}/user",
        json={
            "email": _unique_email("noinvite"),
            "full_name": "No Invite",
            "password": STRONG_PW,
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.account_creation_failed"


def test_create_user_invitation_email_mismatch(client, api_url, admin_headers):
    """A token issued for one email cannot be redeemed for a different email."""
    invited_email = _unique_email("invited")
    resp = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data={"email": invited_email}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]

    # Redeem with a DIFFERENT email than the invitation was issued for.
    resp = client.post(
        f"{api_url}/user",
        json={
            "email": _unique_email("attacker"),
            "full_name": "Mismatch",
            "password": STRONG_PW,
            "invitation_token": token,
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.account_creation_failed"


def test_invite_existing_user_email_rejected(client, api_url, admin_headers):
    """Inviting an already-registered email is rejected outright."""
    email = _unique_email("dup")
    _make_throwaway_user(client, api_url, admin_headers, email=email)
    resp = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data={"email": email}
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.email_already_exists"


def test_create_user_weak_password(client, api_url, admin_headers):
    email = _unique_email("weakpw")
    resp = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data={"email": email}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]

    resp = client.post(
        f"{api_url}/user",
        json={
            "email": email,
            "full_name": "Weak PW",
            "password": "short",  # < 8 chars -> Pydantic min_length gate (422)
            "invitation_token": token,
        },
    )
    # Pydantic min_length=8 rejects at validation before the handler runs.
    assert resp.status_code == 422, resp.text


def test_create_user_policy_weak_password(client, api_url, admin_headers):
    """8+ chars but missing complexity -> caught by validate_password (400)."""
    email = _unique_email("policypw")
    resp = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data={"email": email}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]

    resp = client.post(
        f"{api_url}/user",
        json={
            "email": email,
            "full_name": "Policy PW",
            "password": "alllowercase",  # no upper/digit
            "invitation_token": token,
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "core.password_policy"


# ---------------------------------------------------------------------------
# Response leak checks — sensitive columns must never be serialized.
# ---------------------------------------------------------------------------


def test_list_users_does_not_leak_secrets(client, api_url, admin_headers):
    resp = client.get(f"{api_url}/user", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) > 0
    for u in resp.json():
        assert "hashed_password" not in u
        assert "password" not in u
        assert "token_version" not in u


def test_me_does_not_leak_secrets(client, api_url, user_headers):
    resp = client.get(f"{api_url}/user/me", headers=user_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "hashed_password" not in body
    assert "token_version" not in body
    assert body["email"] == "test@example.com"


# ---------------------------------------------------------------------------
# change_password (POST /user/change-password) — operates on a throwaway user
# ---------------------------------------------------------------------------


def test_change_password_flow(client, api_url, login, admin_headers):
    email = _unique_email("chpw")
    _make_throwaway_user(
        client, api_url, admin_headers, email=email, password=STRONG_PW
    )
    headers = login(email, STRONG_PW)

    # Wrong old password.
    resp = client.post(
        f"{api_url}/user/change-password",
        headers=headers,
        json={"old_password": "Wrongpassword1", "new_password": "Newpassword123"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.old_password_incorrect"

    # New == old.
    resp = client.post(
        f"{api_url}/user/change-password",
        headers=headers,
        json={"old_password": STRONG_PW, "new_password": STRONG_PW},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.new_password_same_as_old"

    # Weak new password (policy violation, but >= 8 chars so passes Pydantic).
    resp = client.post(
        f"{api_url}/user/change-password",
        headers=headers,
        json={"old_password": STRONG_PW, "new_password": "alllowercase"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "core.password_policy"

    # Happy path.
    new_pw = "Newpassword123"
    resp = client.post(
        f"{api_url}/user/change-password",
        headers=headers,
        json={"old_password": STRONG_PW, "new_password": new_pw},
    )
    assert resp.status_code == 200, resp.text

    # Old token is revoked (token_version bumped) -> old header now 401.
    resp = client.get(f"{api_url}/user/me", headers=headers)
    assert resp.status_code == 401

    # New password logs in.
    new_headers = login(email, new_pw)
    resp = client.get(f"{api_url}/user/me", headers=new_headers)
    assert resp.status_code == 200


def test_change_password_unauthenticated(client, api_url):
    resp = client.post(
        f"{api_url}/user/change-password",
        json={"old_password": "whatever1A", "new_password": "Newpassword123"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# admin_set_user_password (POST /user/{id}/set-password)
# ---------------------------------------------------------------------------


def test_admin_set_user_password(client, api_url, admin_headers, login):
    email = _unique_email("setpw")
    user = _make_throwaway_user(client, api_url, admin_headers, email=email)

    new_pw = "Adminsetpw123"
    resp = client.post(
        f"{api_url}/user/{user['id']}/set-password",
        headers=admin_headers,
        json={"new_password": new_pw},
    )
    assert resp.status_code == 200, resp.text

    # The target can log in with the admin-set password.
    resp = client.post(
        f"{api_url}/auth/login",
        data={"username": email, "password": new_pw},
    )
    assert resp.status_code == 200, resp.text


def test_admin_set_user_password_weak(client, api_url, admin_headers):
    user = _make_throwaway_user(client, api_url, admin_headers)
    resp = client.post(
        f"{api_url}/user/{user['id']}/set-password",
        headers=admin_headers,
        json={"new_password": "alllowercase"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "core.password_policy"


def test_admin_set_user_password_not_found(client, api_url, admin_headers):
    resp = client.post(
        f"{api_url}/user/99999/set-password",
        headers=admin_headers,
        json={"new_password": STRONG_PW},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "users.not_found"


def test_admin_set_user_password_requires_admin(client, api_url, user_headers):
    resp = client.post(
        f"{api_url}/user/1/set-password",
        headers=user_headers,
        json={"new_password": STRONG_PW},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# admin_update_user (PATCH /user/{id})
# ---------------------------------------------------------------------------


def test_admin_update_user_full_name(client, api_url, admin_headers):
    user = _make_throwaway_user(client, api_url, admin_headers)
    resp = client.patch(
        f"{api_url}/user/{user['id']}",
        headers=admin_headers,
        json={"full_name": "Renamed User"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["full_name"] == "Renamed User"


def test_admin_update_user_role_and_active(client, api_url, admin_headers):
    user = _make_throwaway_user(client, api_url, admin_headers)
    # Deactivate.
    resp = client.patch(
        f"{api_url}/user/{user['id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False


def test_admin_update_user_duplicate_email(client, api_url, admin_headers):
    a = _make_throwaway_user(client, api_url, admin_headers)
    b = _make_throwaway_user(client, api_url, admin_headers)
    resp = client.patch(
        f"{api_url}/user/{a['id']}",
        headers=admin_headers,
        json={"email": b["email"]},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.email_in_use"


def test_admin_update_user_not_found(client, api_url, admin_headers):
    resp = client.patch(
        f"{api_url}/user/99999",
        headers=admin_headers,
        json={"full_name": "Nobody"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "users.not_found"


def test_admin_update_user_requires_admin(client, api_url, user_headers):
    resp = client.patch(
        f"{api_url}/user/1",
        headers=user_headers,
        json={"full_name": "Hacker"},
    )
    assert resp.status_code == 403


def test_admin_cannot_demote_self(client, api_url, admin_headers):
    me = client.get(f"{api_url}/user/me", headers=admin_headers).json()
    resp = client.patch(
        f"{api_url}/user/{me['id']}",
        headers=admin_headers,
        json={"role": "user"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.cannot_demote_self"


def test_admin_cannot_change_own_status(client, api_url, admin_headers):
    me = client.get(f"{api_url}/user/me", headers=admin_headers).json()
    resp = client.patch(
        f"{api_url}/user/{me['id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.cannot_change_own_status"


def test_admin_cannot_touch_other_admin(client, api_url, admin_headers):
    """Promote a throwaway to admin, then the guards should block further edits,
    password sets, and deletes against that other admin."""
    user = _make_throwaway_user(client, api_url, admin_headers)
    uid = user["id"]

    # Promote to admin.
    resp = client.patch(
        f"{api_url}/user/{uid}",
        headers=admin_headers,
        json={"role": "admin"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "admin"

    # Can no longer modify this other admin.
    resp = client.patch(
        f"{api_url}/user/{uid}",
        headers=admin_headers,
        json={"full_name": "Blocked"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.cannot_modify_other_admin"

    # Cannot set another admin's password.
    resp = client.post(
        f"{api_url}/user/{uid}/set-password",
        headers=admin_headers,
        json={"new_password": STRONG_PW},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.cannot_change_other_admin_password"

    # Cannot delete an admin.
    resp = client.delete(f"{api_url}/user/{uid}", headers=admin_headers)
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.cannot_delete_admin"

    # Cannot toggle an admin's status.
    resp = client.patch(f"{api_url}/user/{uid}/toggle-status", headers=admin_headers)
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.cannot_change_admin_status"


# ---------------------------------------------------------------------------
# delete_user self-guard
# ---------------------------------------------------------------------------


def test_admin_cannot_delete_self(client, api_url, admin_headers):
    me = client.get(f"{api_url}/user/me", headers=admin_headers).json()
    resp = client.delete(f"{api_url}/user/{me['id']}", headers=admin_headers)
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "users.cannot_delete_self"


def test_delete_user_requires_admin(client, api_url, user_headers, admin_headers):
    user = _make_throwaway_user(client, api_url, admin_headers)
    resp = client.delete(f"{api_url}/user/{user['id']}", headers=user_headers)
    assert resp.status_code == 403


def test_delete_throwaway_user(client, api_url, admin_headers):
    user = _make_throwaway_user(client, api_url, admin_headers)
    resp = client.delete(f"{api_url}/user/{user['id']}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == user["email"]
    # Confirm it's gone.
    resp = client.get(f"{api_url}/user", headers=admin_headers)
    assert user["email"] not in [u["email"] for u in resp.json()]


# ---------------------------------------------------------------------------
# /user/me/identities (self-service SSO identity management)
# ---------------------------------------------------------------------------


def test_list_my_identities_empty(client, api_url, user_headers):
    resp = client.get(f"{api_url}/user/me/identities", headers=user_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_list_my_identities_requires_auth(client, api_url):
    resp = client.get(f"{api_url}/user/me/identities")
    assert resp.status_code == 401


def test_delete_my_identity_not_found(client, api_url, user_headers):
    resp = client.delete(f"{api_url}/user/me/identities/99999", headers=user_headers)
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "users.identity_not_found"


# ---------------------------------------------------------------------------
# authz negatives on admin-only endpoints (plain user + unauthenticated)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/user", "/user/invitations"])
def test_admin_get_endpoints_forbidden_for_plain_user(
    client, api_url, user_headers, path
):
    resp = client.get(f"{api_url}{path}", headers=user_headers)
    assert resp.status_code == 403, resp.text


def test_invite_forbidden_for_plain_user(client, api_url, user_headers):
    # Valid form body so the 403 comes from the admin guard, not form validation.
    resp = client.post(
        f"{api_url}/user/invite",
        headers=user_headers,
        data={"email": "someone@example.com"},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/user"),
        ("get", "/user/invitations"),
        ("get", "/user/me"),
    ],
)
def test_admin_endpoints_unauthenticated(client, api_url, method, path):
    resp = getattr(client, method)(f"{api_url}{path}")
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# invite: re-inviting a pending email extends the same invitation
# ---------------------------------------------------------------------------


def test_reinvite_pending_returns_same_invitation(client, api_url, admin_headers):
    email = _unique_email("reinvite")
    resp1 = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data={"email": email}
    )
    assert resp1.status_code == 200, resp1.text
    first = resp1.json()

    resp2 = client.post(
        f"{api_url}/user/invite", headers=admin_headers, data={"email": email}
    )
    assert resp2.status_code == 200, resp2.text
    second = resp2.json()

    # Same invitation row reused (not a duplicate).
    assert second["id"] == first["id"]
    assert second["token"] == first["token"]
