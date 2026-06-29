# backend/src/models/user.py
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from ..utils.enums import UserRole

if TYPE_CHECKING:
    from .project import Project


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
    projects: Mapped[list["Project"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )  # noqa: F821

    reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
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
