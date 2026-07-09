# backend/src/routers/v1/endpoints/auth.py
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .... import models, schemas
from ....core.dynamic_settings import get_settings
from ....core.rate_limit import limiter
from ....core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    verify_password,
    verify_refresh_token,
)
from ....dependencies import get_db

# Use dynamic settings (includes database overrides from admin UI)
settings = get_settings()

router = APIRouter()


def _now_utc_naive() -> datetime:
    """Naive UTC datetime, matching the lockout columns' stored tz-naive values."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _register_failed_login(db: Session, user: models.User) -> None:
    """Increment failed attempts and lock the account if the threshold is reached.

    Mutates + commits the user row. Called on every failed password verification
    (whether or not the user exists — but we only track per-user when the user
    exists; non-existent emails are covered by the IP rate limit + the constant
    0.5s sleep).
    """
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= settings.LOGIN_MAX_ATTEMPTS:
        user.locked_until = _now_utc_naive() + timedelta(
            minutes=settings.LOGIN_LOCKOUT_MINUTES
        )
    db.commit()


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    # NOTE: this endpoint is unauthenticated (the login/landing page reads it to
    # decide which OCR backends to advertise and which SSO buttons to show).
    # Never return internal topology here — the *_api_base values are internal
    # service URLs (e.g. http://deepseek-ocr:8000) in self-hosted deployments.
    # The frontend only needs the enabled flags + display strings, and for SSO
    # only the public (slug, name) of enabled providers.
    sso_providers = []
    if settings.SSO_ENABLED:
        try:
            from sqlalchemy import select

            from ....models.sso import IdentityProvider

            providers = (
                db.execute(
                    select(IdentityProvider)
                    .where(IdentityProvider.enabled.is_(True))
                    .order_by(IdentityProvider.name)
                )
                .scalars()
                .all()
            )
            sso_providers = [{"slug": p.slug, "name": p.name} for p in providers]
        except Exception:
            # Table not ready (e.g. pre-migration) — advertise no providers.
            sso_providers = []

    return {
        "banner_enabled": settings.BANNER_ENABLED,
        "banner_text": settings.BANNER_TEXT,
        "banner_color": settings.BANNER_COLOR,
        "require_invitation": settings.REQUIRE_INVITATION,
        "sso_enabled": settings.SSO_ENABLED,
        "sso_providers": sso_providers,
        "mistral_ocr_enabled": settings.MISTRAL_OCR_ENABLED,
        "vision_ocr_enabled": settings.VISION_OCR_ENABLED,
        "vision_ocr_model": settings.VISION_OCR_MODEL,
        "vision_ocr_prompt": settings.VISION_OCR_PROMPT,
        "mistral_ocr_display_name": settings.MISTRAL_OCR_DISPLAY_NAME,
        "mistral_ocr_display_subtitle": settings.MISTRAL_OCR_DISPLAY_SUBTITLE,
        "vision_ocr_display_name": settings.VISION_OCR_DISPLAY_NAME,
        "vision_ocr_display_subtitle": settings.VISION_OCR_DISPLAY_SUBTITLE,
        "docling_serve_enabled": settings.DOCLING_SERVE_ENABLED,
        "docling_serve_display_name": settings.DOCLING_SERVE_DISPLAY_NAME,
        "docling_serve_display_subtitle": settings.DOCLING_SERVE_DISPLAY_SUBTITLE,
    }


@router.post("/login", response_model=schemas.Token)
@router.post("/api/v1/login", response_model=schemas.Token)
@limiter.limit(None if settings.DISABLE_RATE_LIMIT else "10/minute")
def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> schemas.Token:
    """OAuth2 compatible token login, get an access token for future requests."""
    user = db.query(models.User).filter(models.User.email == form_data.username).first()

    # Account lockout: if the account is currently locked, refuse before
    # checking the password. This prevents continued guessing during the lock
    # window even if the attacker now has the correct password.
    if user and user.locked_until and user.locked_until > _now_utc_naive():
        time.sleep(0.5)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to too many failed login attempts. Try again later.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user or not verify_password(
        form_data.password, str(user.hashed_password)
    ):  #
        if user:
            _register_failed_login(db, user)
        time.sleep(0.5)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        time.sleep(0.5)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user"
        )

    # Success: clear any failed-attempt state and record the login time.
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = _now_utc_naive()
    db.commit()

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user.id,
        expires_delta=access_token_expires,
        token_version=user.token_version,
    )
    refresh_token = create_refresh_token(db, user)
    # Return token and user info. `is_active` / `last_login_at` are included so
    # the response matches `AuthTokenUser` on the frontend — the auth store
    # re-fetches `/user/me` right after, but the token response must still be
    # well-typed on its own (callers that read it directly must not get
    # undefined for fields the type declares as required).
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "last_login_at": user.last_login_at,
        },
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=schemas.Token)
@limiter.limit("30/minute" if not settings.DISABLE_RATE_LIMIT else "1000/minute")
def refresh_token(
    request: Request,
    body: schemas.RefreshRequest,
    db: Session = Depends(get_db),
) -> schemas.Token:
    """Exchange a valid refresh token for a new access + refresh token (rotation).

    The presented refresh token is revoked (rotated) regardless of outcome, so
    a leaked token can be used at most once. Reuse of an already-revoked token
    is treated as invalid (callers should re-authenticate).
    """
    user = verify_refresh_token(body.refresh_token, db)
    # Revoke (rotate) the presented token whether or not it was valid — if it
    # was valid we're about to issue a fresh one; if invalid, revoking a
    # second time is a no-op.
    revoke_refresh_token(body.refresh_token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )
    access_token = create_access_token(user.id, token_version=user.token_version)
    new_refresh = create_refresh_token(db, user)
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "last_login_at": user.last_login_at,
        },
        refresh_token=new_refresh,
    )


@router.post("/logout")
def logout(
    body: schemas.LogoutRequest = Body(default={}),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke the caller's refresh token(s). The access token itself remains
    valid until it expires (short-lived) — server-side logout primarily
    disables refresh. ``everywhere=True`` revokes all of the user's refresh
    tokens and bumps ``token_version`` to invalidate existing access tokens."""
    if body.everywhere:
        revoke_all_refresh_tokens(db, current_user)
        current_user.token_version += 1
        db.commit()
    elif body.refresh_token:
        revoke_refresh_token(body.refresh_token, db)
    return {"logged_out": True}
