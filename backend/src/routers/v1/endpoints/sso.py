# backend/src/routers/v1/endpoints/sso.py
"""OpenID Connect SSO endpoints.

Public:
  - GET  /auth/sso/{slug}/login     → redirect to IdP authorize URL (sets state cookie)
  - GET  /auth/sso/{slug}/callback  → exchange code, JIT-provision user, issue JWT,
                                      redirect to frontend with token in URL fragment

Self-service (auth):
  - GET  /user/me/identities        → list linked identities
  - DELETE /user/me/identities/{id} → unlink an identity (with lockout guard)

Admin (auth + admin):
  - GET/POST/PATCH/DELETE /admin/sso/providers
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....core.config import settings
from ....core.rate_limit import limiter
from ....core.security import create_access_token
from ....dependencies import get_db
from ....models import User, UserIdentity
from ....models.sso import IdentityProvider
from ....services import oidc_service
from ....utils.audit import record_audit
from ....utils.crypto import decrypt
from ....utils.enums import AuditAction, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()

# Cookie name for the signed SSO state JWT. Short TTL, SameSite=Lax so it's
# sent on the IdP's top-level redirect back to the callback.
_STATE_COOKIE = "sso_state"
_STATE_MAX_AGE = 600  # 10 minutes (matches the state JWT exp)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider name must contain alphanumeric characters.",
        )
    return slug[:100]


def _get_provider_by_slug(db: Session, slug: str) -> IdentityProvider:
    provider = db.execute(
        select(IdentityProvider).where(IdentityProvider.slug == slug)
    ).scalar_one_or_none()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown SSO provider."
        )
    return provider


def _sso_enabled_guard() -> None:
    if not settings.SSO_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSO is not enabled on this server.",
        )


def _redirect_uri(slug: str, request: Request) -> str:
    """The canonical callback URL registered with the IdP.

    Derived from ``settings.APP_URL`` (the configured public origin) rather than
    the incoming request's base URL: behind a TLS-terminating proxy (nginx →
    backend over plain HTTP) Starlette doesn't honor ``X-Forwarded-Proto`` unless
    ``ProxyHeadersMiddleware`` is mounted, so ``request.base_url`` would resolve
    to ``http://`` on an HTTPS deployment and break the IdP redirect_uri match.
    APP_URL is the source of truth admins actually configure, so it's stable.
    Falls back to the request base URL only when APP_URL is unset.
    """
    base = (settings.APP_URL or str(request.base_url)).rstrip("/")
    return f"{base}/api/v1/auth/sso/{slug}/callback"


def _frontend_token_redirect(
    access_token: str, refresh_token: str, target: str
) -> RedirectResponse:
    """Redirect to the frontend's SSO-completion route with the tokens in the
    URL fragment (never the query string) so they don't hit server logs or
    the Referer header."""
    app_url = settings.APP_URL.rstrip("/")
    # Whitelist the redirect target to an absolute path on the app origin to
    # avoid open-redirect via a tampered state `redirect` value.
    if not target.startswith("/") or target.startswith("//"):
        target = "/"
    return RedirectResponse(
        url=(
            f"{app_url}/auth/sso/complete"
            f"#access_token={access_token}"
            f"&refresh_token={refresh_token}"
            f"&redirect={target}"
        ),
        status_code=status.HTTP_302_FOUND,
    )


# ─────────────────────────── Public SSO flow ───────────────────────────


@router.get("/{slug}/login")
def sso_login(
    request: Request,
    slug: str = Path(...),
    redirect: str = Query("/"),
    db: Session = Depends(get_db),
):
    """Begin the OIDC authorize redirect for the given provider."""
    _sso_enabled_guard()
    provider = _get_provider_by_slug(db, slug)
    if not provider.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This SSO provider is disabled.",
        )

    redirect_uri = _redirect_uri(slug, request)
    try:
        authorize_url, state_jwt = oidc_service.build_authorization_url(
            issuer_url=provider.issuer_url,
            client_id=provider.client_id,
            redirect_uri=redirect_uri,
            provider_slug=provider.slug,
            scopes=provider.scopes,
            post_login_redirect=redirect,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Failed to start SSO flow for provider %s: %s", slug, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start the SSO flow. Please try again later.",
        )

    resp = RedirectResponse(url=authorize_url, status_code=status.HTTP_302_FOUND)
    resp.set_cookie(
        key=_STATE_COOKIE,
        value=state_jwt,
        max_age=_STATE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.APP_URL.startswith("https"),
    )
    return resp


@router.get("/{slug}/callback")
@limiter.limit("30/minute" if not settings.DISABLE_RATE_LIMIT else "1000/minute")
def sso_callback(
    request: Request,
    slug: str = Path(...),
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """OIDC redirect_uri target: exchange code → userinfo → resolve/create user → JWT."""
    _sso_enabled_guard()

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SSO provider returned an error: {error}",
        )
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code or state.",
        )

    # Verify the state JWT. This proves the callback came from a flow we
    # started (CSRF protection) and carries the PKCE verifier + redirect target.
    state_payload = oidc_service.decode_state(state)
    if state_payload.get("provider") != slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSO state provider mismatch.",
        )

    # The cookie must match the state query param (defense in depth vs. a
    # stolen state JWT injected into a different browser).
    cookie_state = request.cookies.get(_STATE_COOKIE)
    if not cookie_state or cookie_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSO state cookie mismatch.",
        )

    provider = _get_provider_by_slug(db, slug)
    client_secret = decrypt(provider.client_secret_encrypted)
    if not client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Provider client secret is not readable (key rotation?).",
        )

    redirect_uri = _redirect_uri(slug, request)
    token_resp = oidc_service.exchange_code(
        issuer_url=provider.issuer_url,
        client_id=provider.client_id,
        client_secret=client_secret,
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=state_payload["verifier"],
    )

    access_token_oidc = token_resp.get("access_token", "")
    userinfo = oidc_service.fetch_userinfo(provider.issuer_url, access_token_oidc)
    # If the IdP has no userinfo endpoint, fall back to the id_token claims.
    if not userinfo and token_resp.get("id_token"):
        import jwt as pyjwt

        try:
            userinfo = pyjwt.decode(
                token_resp["id_token"],
                options={"verify_signature": False},
            )
        except pyjwt.PyJWTError:
            userinfo = {}

    subject = userinfo.get("sub")
    email = userinfo.get("email")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC provider did not return a subject identifier.",
        )

    user = _resolve_or_provision_user(db, provider, subject, email, userinfo)

    record_audit(
        AuditAction.SSO_LOGIN,
        actor=user,
        resource_type="user",
        resource_id=user.id,
        detail={"provider": slug},
    )

    access_token = create_access_token(user.id, token_version=user.token_version)
    from ....core.security import create_refresh_token

    refresh_token = create_refresh_token(db, user)

    resp = _frontend_token_redirect(
        access_token, refresh_token, state_payload.get("redirect", "/")
    )
    resp.delete_cookie(_STATE_COOKIE)
    return resp


def _resolve_or_provision_user(
    db: Session,
    provider: IdentityProvider,
    subject: str,
    email: str | None,
    userinfo: dict,
) -> User:
    """Find an existing user by identity or email, else JIT-create one.

    Linking precedence:
      1. Existing UserIdentity(provider, subject) → load that user.
      2. Existing User with matching email → link the identity to it.
      3. Else create a new user (subject to SSO_BYPASS_INVITATION / REQUIRE_INVITATION).
    """
    identity = db.execute(
        select(UserIdentity).where(
            UserIdentity.provider_id == provider.id,
            UserIdentity.external_subject == subject,
        )
    ).scalar_one_or_none()

    if identity:
        user = identity.user
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated.",
            )
        identity.last_login_at = datetime.now(timezone.utc)
        db.commit()
        return user

    # No identity yet — try to link by email.
    user_by_email: User | None = None
    if email:
        user_by_email = db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if user_by_email and not user_by_email.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated.",
            )

    if user_by_email:
        target = user_by_email
    else:
        # JIT provisioning.
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OIDC provider did not return an email; cannot create account.",
            )
        if not settings.SSO_BYPASS_INVITATION and settings.REQUIRE_INVITATION:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No existing account for this email, and SSO registration is gated by invitation.",
            )
        # No password — JIT users authenticate via SSO only. An empty
        # hashed_password is the "no password" sentinel: verify_password
        # treats it as invalid, so the account can't be password-logged-in.
        # The account-settings UI lets them set one later if desired.
        target = User(
            email=email,
            hashed_password="",
            full_name=userinfo.get("name")
            or userinfo.get("preferred_username")
            or email.split("@")[0],
            role=UserRole(settings.SSO_JIT_DEFAULT_ROLE),
            is_active=True,
        )
        db.add(target)
        db.flush()  # get the id

    new_identity = UserIdentity(
        user_id=target.id,
        provider_id=provider.id,
        external_subject=subject,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(new_identity)
    db.commit()
    db.refresh(target)
    return target


# Self-service identity endpoints live in users.py (under /user) so they
# align with the usersApi service module on the frontend.
