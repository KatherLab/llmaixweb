from __future__ import annotations

from pydantic import BaseModel, EmailStr
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .project import Project  # noqa: F401


# User schemas
class UserBase(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = "student"

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    email: EmailStr
    password: str
    full_name: str
    invitation_token: str | None = None


class UserUpdate(UserBase):
    password: str | None = None


class UserInDBBase(UserBase):
    id: int
    is_active: bool
    projects: list[Project] | None = None  # noqa: F821


class User(UserInDBBase):
    pass


class UserInDB(UserInDBBase):
    hashed_password: str


# Token schema
class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


# Invitation schemas
class InvitationBase(BaseModel):
    email: EmailStr
    token: str
    is_used: bool = False


class InvitationCreate(InvitationBase):
    class Config:
        from_attributes = True


class InvitationResponse(InvitationBase):
    id: int

    class Config:
        from_attributes = True


class InvitationInfo(BaseModel):
    valid: bool
    email: str | None = None


from .project import Project  # noqa: E402, F401

UserInDBBase.model_rebuild()
User.model_rebuild()
UserInDB.model_rebuild()
