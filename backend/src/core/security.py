# backend/src/core/security.py
import datetime
import hashlib
import secrets
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import PyJWTError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..core.config import settings
from ..dependencies import get_db
from ..models.user import RefreshToken, User
from ..utils.api_errors import api_error
from ..utils.enums import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


def any_admin_exists(db: Session) -> bool:
    return db.query(User).filter(User.role == UserRole.admin).count() > 0


def admin_has_global_project_access(user: User) -> bool:
    """Whether *user* may access projects they do not own.

    Admins get cross-user project visibility ONLY when the deployment enables
    ``ADMIN_ALL_PROJECT_ACCESS`` (env-only). With the flag off (the default),
    admins are scoped to their own projects just like any other user.
    """
    return user.role == "admin" and settings.ADMIN_ALL_PROJECT_ACCESS


def can_access_project(user: User, project) -> bool:
    """Whether *user* may read/modify *project*.

    True for the project owner, or for an admin when cross-user project access
    is enabled via ``ADMIN_ALL_PROJECT_ACCESS``.
    """
    return project.owner_id == user.id or admin_has_global_project_access(user)


def create_access_token(
    subject: str | Any,
    expires_delta: datetime.timedelta | None = None,
    *,
    token_version: int = 1,
) -> str:
    if expires_delta:
        expire = datetime.datetime.now(datetime.UTC) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "tkn_v": token_version}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Convert plain password to bytes if it's not already
    if isinstance(plain_password, str):
        plain_password: bytes = plain_password.encode("utf-8")

    # Convert hashed password to bytes if it's not already
    if isinstance(hashed_password, str):
        hashed_password: bytes = hashed_password.encode("utf-8")

    # Empty hash sentinel = "no password set" (SSO-only JIT accounts). These
    # accounts can't be password-logged-in by design.
    if not hashed_password:
        return False

    try:
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception:
        return False


# ───────────────────────── Refresh tokens ─────────────────────────


def _hash_token(token: str) -> str:
    """sha256 hex of a refresh token for storage. sha256 is sufficient here:
    refresh tokens are high-entropy (48-byte) and short-lived, and we need
    constant-time lookup by hash (indexed unique column)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token(db: Session, user: User) -> str:
    """Mint + persist a refresh token for ``user``. Returns the plaintext token
    (returned to the client exactly once)."""
    plaintext = secrets.token_urlsafe(48)
    expires_at = datetime.datetime.now(datetime.UTC).replace(
        tzinfo=None
    ) + datetime.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=_hash_token(plaintext),
            expires_at=expires_at,
        )
    )
    db.commit()
    return plaintext


def verify_refresh_token(token: str, db: Session) -> User | None:
    """Look up a refresh token by hash. Returns the linked user if the token is
    valid, unexpired, and unrevoked; otherwise ``None``. Does NOT rotate — the
    caller (``/auth/refresh``) revokes + re-mints."""
    if not token:
        return None
    row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(token))
    ).scalar_one_or_none()
    if not row or row.revoked:
        return None
    if row.expires_at < datetime.datetime.now(datetime.UTC).replace(tzinfo=None):
        return None
    user = db.get(User, row.user_id)
    if not user or not user.is_active:
        return None
    return user


def rotate_refresh_token(token: str, db: Session) -> User | None:
    """Atomically claim (revoke) a refresh token and return its user.

    Uses a single conditional UPDATE (``... WHERE token_hash=? AND revoked=false``)
    so two concurrent requests presenting the same token can't both succeed —
    exactly one wins the claim; the loser sees rowcount 0. This closes the
    verify-then-revoke race where both callers minted fresh token pairs.

    Reuse detection: if the token exists but was already revoked (rowcount 0 on
    the claim, yet a row is present with ``revoked=true``), that's a replay of a
    rotated token — a strong theft signal — so we revoke the user's ENTIRE token
    family and return ``None``, forcing every session to re-authenticate.

    Returns the active user on a successful claim, else ``None``.
    """
    if not token:
        return None
    token_hash = _hash_token(token)
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

    # Atomic claim: only succeeds if the token is currently un-revoked.
    result = db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )
    if result.rowcount == 0:
        # Either the token never existed, or it was already revoked (reuse).
        row = db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).scalar_one_or_none()
        db.commit()
        if row is not None:
            # Replay of an already-rotated token → revoke the whole family.
            user = db.get(User, row.user_id)
            if user:
                revoke_all_refresh_tokens(db, user)
        return None

    # We won the claim. Load + validate the row we just revoked.
    row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()
    db.commit()
    if not row or row.expires_at < now:
        return None
    user = db.get(User, row.user_id)
    if not user or not user.is_active:
        return None
    return user


def revoke_refresh_token(token: str, db: Session) -> None:
    """Revoke a single refresh token (mark revoked). Idempotent."""
    if not token:
        return
    row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(token))
    ).scalar_one_or_none()
    if row and not row.revoked:
        row.revoked = True
        db.commit()


def revoke_all_refresh_tokens(db: Session, user: User) -> None:
    """Revoke every refresh token for a user (used on logout-everywhere)."""
    db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)
        )
    ).scalars().all()  # materialize before update
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)
    ).update({RefreshToken.revoked: True})
    db.commit()


def get_password_hash(password: str) -> str:
    # Convert password to bytes if it's not already
    if isinstance(password, str):
        password: bytes = password.encode("utf-8")

    # Generate a salt and hash the password
    salt = bcrypt.gensalt(rounds=12)  # Higher rounds = more secure but slower
    hashed = bcrypt.hashpw(password, salt)

    # Return the hash as a string
    return hashed.decode("utf-8")


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = api_error(
        "core.could_not_validate_credentials",
        status.HTTP_401_UNAUTHORIZED,
        "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        # int() may raise ValueError on a malformed "sub" claim — treat like
        # any other invalid token (401, not a 500).
        user_id_int = int(user_id)
    except (PyJWTError, ValueError, TypeError):
        raise credentials_exception

    user = (
        db.execute(select(User).where(User.id == user_id_int)).scalars().one_or_none()
    )
    if user is None:
        raise credentials_exception
    if not user.is_active:
        # Deactivated users cannot use any tokens
        raise api_error(
            "core.account_deactivated",
            status.HTTP_401_UNAUTHORIZED,
            "User account is deactivated",
        )
    # Validate token version — a newer version means old tokens are revoked
    token_version = payload.get("tkn_v", 0)
    if token_version < user.token_version:
        raise api_error(
            "core.token_revoked",
            status.HTTP_401_UNAUTHORIZED,
            "Token has been revoked. Please log in again.",
        )
    return user


# Add this function to protect admin-only endpoints
def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to check if the current user is an admin.

    Usage:
        @router.get("/admin-only")
        def admin_endpoint(admin: User = Depends(get_admin_user)):
            return {"message": "Hello Admin!"}
    """
    if current_user.role != "admin":
        raise api_error(
            "core.admin_required",
            status.HTTP_403_FORBIDDEN,
            "Not enough permissions. Admin role required.",
        )
    return current_user
