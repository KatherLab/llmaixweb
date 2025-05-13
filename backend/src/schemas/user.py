from typing import Optional
from pydantic import BaseModel, EmailStr


# User schemas
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = "student"


class UserCreate(UserBase):
    email: EmailStr
    password: str
    full_name: str
    invitation_token: Optional[str] = None  # Made optional to support both workflows


class UserUpdate(UserBase):
    password: Optional[str] = None


class UserInDBBase(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


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
    email: Optional[str] = None
