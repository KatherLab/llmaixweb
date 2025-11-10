from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ..utils.enums import UserRole

if TYPE_CHECKING:
    from .project import Project, ProjectBase  # noqa: F401


class UserPublic(BaseModel):
    id: int
    full_name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)

# User schemas
class UserBase(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: UserRole | None = UserRole.user

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str
    invitation_token: str | None = None


class UserUpdate(UserBase):
    password: str | None = Field(default=None, min_length=8, max_length=128)


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordSet(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


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
    model_config = ConfigDict(from_attributes=True)


class InvitationResponse(InvitationBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class InvitationInfo(BaseModel):
    valid: bool
    email: str | None = None


from .project import Project  # noqa: E402, F401

UserInDBBase.model_rebuild()
User.model_rebuild()
UserInDB.model_rebuild()
