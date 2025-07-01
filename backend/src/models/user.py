from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
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
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")  # noqa: F821


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    token: Mapped[str] = mapped_column(String(64), unique=True)
    is_used: Mapped[bool] = mapped_column(default=False)
