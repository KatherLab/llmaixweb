# backend/src/models/user.py
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from ..utils.enums import UserRole

if TYPE_CHECKING:
    from .project import Project, ProjectShare
    from .sso import UserIdentity


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    hashed_password: Mapped[str] = mapped_column(String())
    full_name: Mapped[str] = mapped_column(String())
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=10), default=UserRole.user
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    token_version: Mapped[int] = mapped_column(default=1)
    # UI locale ("en"/"de"/"fr"/"es"), mirrored from the frontend language
    # switcher. Notification email is rendered in this language; NULL means the
    # user never picked one, so mail falls back to English.
    preferred_language: Mapped[str | None] = mapped_column(String(5), nullable=True)
    # Brute-force protection: after LOGIN_MAX_ATTEMPTS failed logins the
    # account is locked until `locked_until`. Reset to 0 / None on success.
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    projects: Mapped[list["Project"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )  # noqa: F821
    # Projects shared *with* this user (not the ones they own). Deleting the
    # user revokes their grants; `foreign_keys` disambiguates from the
    # ProjectShare.created_by_id FK, which also points at users.
    project_shares: Mapped[list["ProjectShare"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="ProjectShare.user_id",
    )  # noqa: F821

    reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    identities: Mapped[list["UserIdentity"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    # Lazily created: a user without a row uses the defaults in
    # `NotificationPreference.DEFAULTS`, so existing accounts need no backfill.
    # Deliberately *not* eager-loaded — every authenticated request loads a User
    # and only the notification paths need this.
    notification_preference: Mapped["NotificationPreference | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    token: Mapped[str] = mapped_column(String(64), unique=True)
    is_used: Mapped[bool] = mapped_column(default=False)
    # Expiry: invitation tokens are bearer tokens that grant registration, so
    # they must not live forever. `created_at` has a server default so raw
    # inserts also work; `expires_at` is set by the invite endpoint. NULL means
    # "no expiry" — only present for rows created before this column existed
    # (the migration backfills a far-future expiry for them).
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Indexed: password reset flows look up tokens by user (e.g. cleanup,
    # invalidation) and the table is scanned per user on login-state checks.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime())
    # `server_default` so raw inserts (and fresh create_all() DBs) populate the
    # column without relying on the ORM default; the Python default keeps naive
    # datetimes consistent for tests that bypass the DB default.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="reset_tokens")


class RefreshToken(Base):
    """A hash-stored, rotatable, revocable refresh token.

    Only the sha256 hash is persisted; the plaintext is returned to the client
    exactly once at issuance. Rotation: ``/auth/refresh`` revokes the presented
    token and mints a fresh pair. Revocation also happens implicitly on
    password change / role change / status toggle via ``token_version`` bumps,
    but an explicit revoke (logout) covers the case where the access token is
    still valid.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # sha256 hex of the plaintext token — never store the raw token.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    revoked: Mapped[bool] = mapped_column(default=False)

    user: Mapped["User"] = relationship()


class NotificationPreference(Base):
    """Per-user opt-outs for notification email.

    One row per user, created on first write (the GET endpoint returns defaults
    without persisting anything). A missing row therefore means "all defaults",
    which is why every send path goes through
    :func:`backend.src.utils.notifications.preferences_for` rather than reading
    this relationship directly.

    Security notices default on and are *not* silently ignorable elsewhere: the
    toggle exists because some deployments route these to a SIEM instead, but the
    default keeps the user informed about their own account.
    """

    __tablename__ = "notification_preferences"

    # Defaults for a user with no row yet — also the reset target for the
    # Account settings "restore defaults" action. Keys match the column names
    # and the `NotificationCategory` values.
    DEFAULTS: "dict[str, bool | int | None]" = {
        "job_finished": True,
        "project_shared": True,
        "security": True,
        "admin_alerts": True,
        "only_when_away": True,
        "min_job_seconds": None,
    }

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    # ── Category opt-outs (see utils.enums.NotificationCategory) ──
    job_finished: Mapped[bool] = mapped_column(default=True)
    project_shared: Mapped[bool] = mapped_column(default=True)
    security: Mapped[bool] = mapped_column(default=True)
    # Only consulted for admins; a non-admin never receives these regardless.
    admin_alerts: Mapped[bool] = mapped_column(default=True)

    # ── Delivery gating ──
    # Suppress job-finished email while the user has the app open (tracked via
    # WebSocket presence). Applies to job notifications only — a security notice
    # or a share grant is worth an email either way.
    only_when_away: Mapped[bool] = mapped_column(default=True)
    # Per-user override of settings.NOTIFY_MIN_JOB_SECONDS. NULL = use the
    # server default.
    min_job_seconds: Mapped[int | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="notification_preference")
