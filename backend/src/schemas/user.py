# backend/src/schemas/user.py
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ..utils.enums import UserRole

if TYPE_CHECKING:
    from .project import Project, ProjectBase  # noqa: F401

# Keep in sync with utils.email_i18n.SUPPORTED_LOCALES and the frontend's
# SUPPORTED_LOCALES — this is the wire contract for the language switcher.
SupportedLanguage = Literal["en", "de", "fr", "es"]


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
    # UI locale, mirrored from the frontend language switcher so notification
    # email can be rendered in it. Constrained to the locales we have catalogs
    # for; anything else would silently fall back to English.
    preferred_language: SupportedLanguage | None = None


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordSet(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)


class UserUpdateAdmin(BaseModel):
    """Admin update for any user field. Only provided fields are updated."""

    full_name: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    preferred_language: SupportedLanguage | None = None
    last_login_at: datetime | None = None
    # True if the user has at least one linked SSO identity. Populated by the
    # list endpoint (not a DB column) so the admin grid can show SSO vs local.
    has_sso: bool | None = None
    # Whether this user may access projects they don't own (admins, and only
    # when ADMIN_ALL_PROJECT_ACCESS is enabled). Not a DB column — populated by
    # /me so the frontend can gate the "show all users' projects" toggle.
    can_access_all_projects: bool = False

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
    email_sent: bool = False
    created_at: datetime | None = None
    expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class InvitationInfo(BaseModel):
    valid: bool
    email: str | None = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetValidate(BaseModel):
    valid: bool


# Notification preferences
class NotificationPreferenceResponse(BaseModel):
    """A user's effective notification settings.

    Always populated — a user with no stored row gets the defaults rather than a
    404, so the frontend never has to special-case "never configured".
    ``email_configured`` is not a preference: it tells the UI whether the
    instance can deliver mail at all, so the toggles can explain themselves
    instead of silently doing nothing.
    """

    job_finished: bool
    project_shared: bool
    security: bool
    admin_alerts: bool
    only_when_away: bool
    min_job_seconds: int | None = None
    email_configured: bool = False

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    """Partial update — only the provided fields change."""

    job_finished: bool | None = None
    project_shared: bool | None = None
    security: bool | None = None
    admin_alerts: bool | None = None
    only_when_away: bool | None = None
    # Upper bound is a day: past that the threshold is indistinguishable from
    # switching job email off, which is what the toggle is for. None clears the
    # override and falls back to the server default.
    min_job_seconds: int | None = Field(default=None, ge=0, le=86400)


class TestEmailResponse(BaseModel):
    sent: bool
    recipient: EmailStr | None = None


class LanguageUpdate(BaseModel):
    preferred_language: SupportedLanguage


class UserSelfUpdate(BaseModel):
    """What a user may change about their own account from Account settings.

    Deliberately just the display name. Email is the sign-in identity — and, when
    SSO links accounts by email, the thing that decides *which* account an
    external identity attaches to — so changing it is an administrator action
    (``PATCH /user/{user_id}``), not self-service. Role and active status are
    likewise absent: this schema is the whole allowlist, so a field can only
    become self-editable by being added here on purpose.
    """

    full_name: str = Field(..., min_length=1, max_length=255)


from .project import Project  # noqa: E402, F401

UserInDBBase.model_rebuild()
User.model_rebuild()
UserInDB.model_rebuild()
