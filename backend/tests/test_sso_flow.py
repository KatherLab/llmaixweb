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


def _audit_rows(client, api_url, headers, **params):
    resp = client.get(f"{api_url}/admin/audit", headers=headers, params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()["items"]


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
    assert "verify" in resp.json()["detail"]["message"].lower()

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

    # Attaching a sign-in method to a pre-existing account is its own audit
    # event — SSO_LOGIN alone doesn't distinguish it from a routine login.
    admin_headers = _admin_headers(client, api_url)
    link_rows = _audit_rows(
        client, api_url, admin_headers, action="create", resource_type="user_identity"
    )
    assert link_rows, "identity link to an existing account was not audited"
    assert link_rows[0]["detail"]["linked_to_existing_account"] is True
    assert link_rows[0]["detail"]["email_verified"] is True
    assert link_rows[0]["detail"]["provider"] == provider["slug"]

    # …and removing it is an account-security event too. Allowed here because
    # the account still has a password to fall back on.
    resp = client.delete(
        f"{api_url}/user/me/identities/{identities[0]['id']}", headers=headers
    )
    assert resp.status_code == 200, resp.text
    unlink_rows = _audit_rows(
        client, api_url, admin_headers, action="delete", resource_type="user_identity"
    )
    assert unlink_rows, "identity unlink was not audited"
    assert unlink_rows[0]["actor_email"] == "another@example.com"
    assert unlink_rows[0]["detail"]["self_service"] is True
    assert unlink_rows[0]["detail"]["remaining_identities"] == 0


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
    assert "cookie" in resp.json()["detail"]["message"].lower()

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
    assert "provider" in resp.json()["detail"]["message"].lower()


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
    assert "invitation" in resp.json()["detail"]["message"].lower()

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
    assert "email" in resp.json()["detail"]["message"].lower()


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
    assert "deactivated" in resp.json()["detail"]["message"].lower()


# ─────────────────────────── group → role mapping ───────────────────────────


def _create_mapped_provider(client, api_url, **groups):
    resp = client.post(
        f"{api_url}/admin/sso/providers",
        headers=_admin_headers(client, api_url),
        json={
            "name": "Keycloak",
            "issuer_url": _ISSUER,
            "client_id": "llmaix-client",
            "client_secret": "s3cret",
            **groups,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _sso_login(client, api_url, monkeypatch, slug, sub, email, groups=None):
    _, state = _start_login(client, api_url, slug)
    userinfo = {"sub": sub, "email": email, "email_verified": True}
    if groups is not None:
        userinfo["groups"] = groups
    _mock_idp_user(monkeypatch, userinfo)
    return _callback(client, api_url, slug, state)


def _me(client, api_url, resp):
    assert resp.status_code == 302, resp.text
    token = _fragment_params(resp.headers["location"])["access_token"]
    me = client.get(f"{api_url}/user/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    return me.json()


def test_groups_decide_role_and_follow_membership_changes(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_mapped_provider(
        client, api_url, user_groups="users", admin_groups="/admins"
    )
    assert provider["admin_groups"] == "admins"
    slug, email = provider["slug"], "grouped@sso.example.com"

    # Keycloak's full-path form matches the plain configured name.
    resp = _sso_login(client, api_url, monkeypatch, slug, "g1", email, ["/admins"])
    assert _me(client, api_url, resp)["role"] == "admin"

    # Moved to the user group: demoted, with the old session invalidated.
    old_token = _fragment_params(resp.headers["location"])["access_token"]
    resp = _sso_login(client, api_url, monkeypatch, slug, "g1", email, ["users"])
    assert _me(client, api_url, resp)["role"] == "user"
    stale = client.get(
        f"{api_url}/user/me", headers={"Authorization": f"Bearer {old_token}"}
    )
    assert stale.status_code == 401

    rows = _audit_rows(
        client,
        api_url,
        _admin_headers(client, api_url),
        action="user_role_change",
    )
    assert rows[0]["detail"]["source"] == "sso_groups"
    assert rows[0]["detail"]["new_role"] == "user"


def test_user_in_no_allowed_group_is_refused_without_account(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    from backend.src.db.session import SessionLocal
    from backend.src.models import User

    provider = _create_mapped_provider(
        client, api_url, user_groups="users", admin_groups="admins"
    )
    email = "outsider@sso.example.com"

    # A same-named subgroup elsewhere in the tree grants nothing, and neither
    # does a missing claim.
    for groups in (["/other/admins"], None):
        resp = _sso_login(
            client, api_url, monkeypatch, provider["slug"], "o1", email, groups
        )
        assert resp.status_code == 302
        assert resp.headers["location"] == (
            "http://testserver/login?sso_error=not_in_allowed_group"
        )

    db = SessionLocal()
    assert db.query(User).filter(User.email == email).first() is None
    db.close()


def test_removal_from_groups_ends_existing_sessions(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_mapped_provider(client, api_url, user_groups="users")
    slug, email = provider["slug"], "leaver@sso.example.com"

    resp = _sso_login(client, api_url, monkeypatch, slug, "l1", email, ["users"])
    params = _fragment_params(resp.headers["location"])

    resp = _sso_login(client, api_url, monkeypatch, slug, "l1", email, [])
    assert "sso_error=not_in_allowed_group" in resp.headers["location"]

    headers = {"Authorization": f"Bearer {params['access_token']}"}
    assert client.get(f"{api_url}/user/me", headers=headers).status_code == 401
    refreshed = client.post(
        f"{api_url}/auth/refresh", json={"refresh_token": params["refresh_token"]}
    )
    assert refreshed.status_code == 401


def test_admin_groups_only_leaves_everyone_else_a_user(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_mapped_provider(client, api_url, admin_groups="admins")
    resp = _sso_login(
        client,
        api_url,
        monkeypatch,
        provider["slug"],
        "p1",
        "plain@sso.example.com",
    )
    assert _me(client, api_url, resp)["role"] == "user"


def test_groups_claim_in_verified_id_token_wins_over_userinfo(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_mapped_provider(
        client, api_url, admin_groups="admins", groups_claim="roles"
    )
    _, state = _start_login(client, api_url, provider["slug"])
    _mock_idp_user(
        monkeypatch,
        {
            "sub": "i1",
            "email": "idtoken@sso.example.com",
            "email_verified": True,
            "roles": ["admins"],
        },
        {"access_token": "a", "id_token": "signed"},
    )
    monkeypatch.setattr(
        oidc_service,
        "verify_id_token",
        lambda *a, **k: {"sub": "i1", "roles": ["staff"]},
    )
    resp = _callback(client, api_url, provider["slug"], state)
    assert _me(client, api_url, resp)["role"] == "user"


def test_userinfo_subject_must_match_id_token(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_provider(client, api_url)
    _, state = _start_login(client, api_url, provider["slug"])
    _mock_idp_user(
        monkeypatch,
        {"sub": "other", "email": "mix@sso.example.com", "email_verified": True},
        {"access_token": "a", "id_token": "signed"},
    )
    monkeypatch.setattr(oidc_service, "verify_id_token", lambda *a, **k: {"sub": "me"})
    resp = _callback(client, api_url, provider["slug"], state)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "sso.subject_mismatch"


def test_callback_refuses_disabled_provider(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_provider(client, api_url)
    _, state = _start_login(client, api_url, provider["slug"])
    client.patch(
        f"{api_url}/admin/sso/providers/{provider['id']}",
        headers=_admin_headers(client, api_url),
        json={"enabled": False},
    )
    assert _callback(client, api_url, provider["slug"], state).status_code == 403


# ─────────────────────────── provider declared in the environment ───────────


@pytest.fixture
def env_provider(sso_settings, cleanup_sso, monkeypatch):
    for key, value in {
        "SSO_OIDC_NAME": "Keycloak",
        "SSO_OIDC_ISSUER_URL": f"{_ISSUER}/",
        "SSO_OIDC_CLIENT_ID": "llmaix-client",
        "SSO_OIDC_CLIENT_SECRET": "env-secret",
        "SSO_OIDC_USER_GROUPS": "users",
        "SSO_OIDC_ADMIN_GROUPS": "admins",
    }.items():
        monkeypatch.setattr(sso_settings, key, value)
    return sso_settings


def _sync():
    from backend.src.db.session import SessionLocal
    from backend.src.services.sso_env_provider import sync_env_provider

    db = SessionLocal()
    try:
        sync_env_provider(db)
    finally:
        db.close()


def test_env_provider_is_upserted_and_read_only(
    client, api_url, env_provider, monkeypatch
):
    _sync()
    headers = _admin_headers(client, api_url)
    [provider] = client.get(f"{api_url}/admin/sso/providers", headers=headers).json()
    assert provider["slug"] == "keycloak"
    assert provider["issuer_url"] == _ISSUER
    assert provider["managed_by_env"] is True
    assert provider["admin_groups"] == "admins"
    url = f"{api_url}/admin/sso/providers/{provider['id']}"
    assert (
        client.patch(url, headers=headers, json={"enabled": False}).status_code == 409
    )
    assert client.delete(url, headers=headers).status_code == 409

    # A restart with unchanged values writes no audit row…
    def changes():
        return _audit_rows(client, api_url, headers, action="sso_provider_change")

    before = len(changes())
    _sync()
    assert len(changes()) == before

    # …and a rotated secret reaches the row the login flow reads.
    monkeypatch.setattr(env_provider, "SSO_OIDC_CLIENT_SECRET", "rotated")
    _sync()
    from backend.src.db.session import SessionLocal
    from backend.src.models.sso import IdentityProvider
    from backend.src.utils.crypto import decrypt

    db = SessionLocal()
    row = db.query(IdentityProvider).one()
    assert decrypt(row.client_secret_encrypted) == "rotated"
    db.close()
    assert len(changes()) == before + 1


def test_env_provider_adopts_ui_provider_and_keeps_identities(
    client, api_url, env_provider, monkeypatch
):
    ui_provider = _create_provider(client, api_url, name="Keycloak")
    resp = _sso_login(
        client,
        api_url,
        monkeypatch,
        ui_provider["slug"],
        "a1",
        "adopted@sso.example.com",
    )
    user_id = _me(client, api_url, resp)["id"]

    _sync()
    [provider] = client.get(
        f"{api_url}/admin/sso/providers", headers=_admin_headers(client, api_url)
    ).json()
    assert provider["id"] == ui_provider["id"] and provider["managed_by_env"] is True

    resp = _sso_login(
        client,
        api_url,
        monkeypatch,
        provider["slug"],
        "a1",
        "adopted@sso.example.com",
        ["users"],
    )
    assert _me(client, api_url, resp)["id"] == user_id


def test_env_provider_partial_config_stops_startup(env_provider, monkeypatch):
    monkeypatch.setattr(env_provider, "SSO_OIDC_CLIENT_SECRET", "")
    with pytest.raises(RuntimeError, match="SSO_OIDC_CLIENT_SECRET"):
        _sync()


def test_removing_env_vars_disables_and_releases_provider(
    client, api_url, env_provider, monkeypatch
):
    _sync()
    for key in ("ISSUER_URL", "CLIENT_ID", "CLIENT_SECRET"):
        monkeypatch.setattr(env_provider, f"SSO_OIDC_{key}", "")
    _sync()
    [provider] = client.get(
        f"{api_url}/admin/sso/providers", headers=_admin_headers(client, api_url)
    ).json()
    assert provider["managed_by_env"] is False
    assert provider["enabled"] is False


# ─────────────────────────── first-admin gate ───────────────────────────


def test_admin_group_closes_first_admin_setup(
    client, api_url, env_provider, monkeypatch
):
    """The public bootstrap form must stay shut when admins come from the IdP,
    and the first admin-group member to sign in becomes admin."""
    from backend.src.core import security
    from backend.src.db.session import SessionLocal

    # first_admin_setup_allowed() reads this module global, patched for the
    # "no admin exists yet" state of a fresh install.
    monkeypatch.setattr(security, "any_admin_exists", lambda db: False)
    monkeypatch.setattr(env_provider, "ALLOW_FIRST_ADMIN_SETUP", True)

    def allowed():
        db = SessionLocal()
        try:
            return security.first_admin_setup_allowed(db)
        finally:
            db.close()

    assert allowed() is True  # no provider yet

    _sync()
    assert allowed() is False
    check = client.get(f"{api_url}/user/first-admin-check").json()
    assert check["allow_first_admin_setup"] is False

    resp = client.post(
        f"{api_url}/user/first-admin",
        json={
            "email": "squatter@sso.example.com",
            "password": "Squatterpass1",
            "full_name": "Squatter",
            "role": "admin",
        },
    )
    assert resp.status_code == 403

    resp = _sso_login(
        client,
        api_url,
        monkeypatch,
        "keycloak",
        "first",
        "first.admin@sso.example.com",
        ["admins"],
    )
    assert _me(client, api_url, resp)["role"] == "admin"

    # SSO off globally: the provider can't deliver an admin, so don't lock out.
    monkeypatch.setattr(env_provider, "SSO_ENABLED", False)
    assert allowed() is True


# ─────────────────────────── SSO_ONLY ───────────────────────────


def _assert_password_disabled(resp):
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"]["code"] == "auth.password_auth_disabled"


def test_sso_only_refuses_every_password_route(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_provider(client, api_url)
    admin = _admin_headers(client, api_url)
    user = _login_headers(client, api_url, "test@example.com", "Testpassword1")
    monkeypatch.setattr(sso_settings, "SSO_ONLY", True)

    assert client.get(f"{api_url}/auth/settings").json()["sso_only"] is True
    assert (
        client.get(f"{api_url}/user/first-admin-check").json()[
            "allow_first_admin_setup"
        ]
        is False
    )
    new_user = {
        "email": "pw@sso.example.com",
        "password": "Passw0rdPassw0rd",
        "full_name": "Pw",
    }
    for resp in (
        client.post(
            f"{api_url}/auth/login",
            data={"username": "admin@example.com", "password": "Adminpassword1"},
        ),
        client.post(f"{api_url}/user", json=new_user),
        client.post(
            f"{api_url}/user/change-password",
            headers=user,
            json={"old_password": "Testpassword1", "new_password": "Passw0rdPassw0rd"},
        ),
        client.post(
            f"{api_url}/user/1/set-password",
            headers=admin,
            json={"new_password": "Passw0rdPassw0rd"},
        ),
        client.post(
            f"{api_url}/user/invite",
            headers=admin,
            data={"email": "new@sso.example.com"},
        ),
        client.post(
            f"{api_url}/user/forgot-password", json={"email": "test@example.com"}
        ),
        client.post(
            f"{api_url}/user/reset-password/tok",
            json={"token": "tok", "new_password": "Passw0rdPassw0rd"},
        ),
    ):
        _assert_password_disabled(resp)

    # First-admin has its own gate, and it answers its own code.
    resp = client.post(
        f"{api_url}/user/first-admin", json={**new_user, "role": "admin"}
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "users.first_admin_not_allowed"

    # The IdP path is unaffected.
    resp = _sso_login(
        client,
        api_url,
        monkeypatch,
        provider["slug"],
        "only-1",
        "only@sso.example.com",
    )
    assert _me(client, api_url, resp)["email"] == "only@sso.example.com"


def test_sso_only_flag_off_keeps_password_login(client, api_url):
    assert client.get(f"{api_url}/auth/settings").json()["sso_only"] is False
    _login_headers(client, api_url, "test@example.com", "Testpassword1")


def test_sso_only_ends_password_sessions_but_not_sso_sessions(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_provider(client, api_url)
    resp = client.post(
        f"{api_url}/auth/login",
        data={"username": "test@example.com", "password": "Testpassword1"},
    )
    password_refresh = resp.json()["refresh_token"]
    resp = _sso_login(
        client,
        api_url,
        monkeypatch,
        provider["slug"],
        "only-2",
        "session@sso.example.com",
    )
    sso_refresh = _fragment_params(resp.headers["location"])["refresh_token"]

    monkeypatch.setattr(sso_settings, "SSO_ONLY", True)

    def refresh(token):
        return client.post(f"{api_url}/auth/refresh", json={"refresh_token": token})

    assert refresh(password_refresh).status_code == 401
    assert refresh(sso_refresh).status_code == 200


def test_sso_only_refuses_unlinking_the_only_identity(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    """Even with a password on the account: it couldn't be used any more."""
    provider = _create_provider(client, api_url)
    resp = _sso_login(
        client, api_url, monkeypatch, provider["slug"], "only-3", "another@example.com"
    )
    token = _fragment_params(resp.headers["location"])["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    [identity] = client.get(f"{api_url}/user/me/identities", headers=headers).json()

    monkeypatch.setattr(sso_settings, "SSO_ONLY", True)
    resp = client.delete(
        f"{api_url}/user/me/identities/{identity['id']}", headers=headers
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "users.sso_only_last_identity"


def test_sso_only_blocks_admin_lockouts(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    provider = _create_provider(client, api_url, name="IdP A")
    admin = _admin_headers(client, api_url)
    monkeypatch.setattr(sso_settings, "SSO_ONLY", True)
    url = f"{api_url}/admin/sso/providers/{provider['id']}"

    def code(resp):
        assert resp.status_code == 409, resp.text
        return resp.json()["detail"]["code"]

    last = "sso.sso_only_last_provider"
    assert code(client.patch(url, headers=admin, json={"enabled": False})) == last
    assert code(client.delete(url, headers=admin)) == last

    sso_off = "core.sso_only_requires_sso"
    for value in (False, "false"):
        resp = client.put(
            f"{api_url}/admin/settings", headers=admin, json={"SSO_ENABLED": value}
        )
        assert code(resp) == sso_off
    resp = client.delete(f"{api_url}/admin/settings/SSO_ENABLED", headers=admin)
    assert code(resp) == sso_off

    # With a second provider enabled, the first may go.
    monkeypatch.setattr(sso_settings, "SSO_ONLY", False)
    _create_provider(client, api_url, name="IdP B")
    monkeypatch.setattr(sso_settings, "SSO_ONLY", True)
    assert client.patch(url, headers=admin, json={"enabled": False}).status_code == 200


def test_sso_only_startup_check(
    client, api_url, sso_settings, cleanup_sso, monkeypatch
):
    from backend.src.db.session import SessionLocal
    from backend.src.services.sso_env_provider import verify_sso_only

    def check():
        db = SessionLocal()
        try:
            verify_sso_only(db)
        finally:
            db.close()

    check()  # flag off: nothing to verify

    monkeypatch.setattr(sso_settings, "SSO_ONLY", True)
    with pytest.raises(RuntimeError, match="enabled SSO provider"):
        check()

    monkeypatch.setattr(sso_settings, "SSO_ONLY", False)
    _create_provider(client, api_url)
    monkeypatch.setattr(sso_settings, "SSO_ONLY", True)
    check()

    monkeypatch.setattr(sso_settings, "SSO_ENABLED", False)
    with pytest.raises(RuntimeError, match="SSO_ENABLED"):
        check()
