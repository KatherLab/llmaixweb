# backend/src/schemas/sso.py
"""Pydantic schemas for OIDC SSO providers and user identities."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IdentityProviderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    issuer_url: str = Field(..., min_length=1, max_length=512)
    client_id: str = Field(..., min_length=1, max_length=256)
    scopes: str = Field(default="openid email profile", max_length=256)
    enabled: bool = True


class IdentityProviderCreate(IdentityProviderBase):
    # Write-only: encrypted at rest, never returned by any endpoint.
    client_secret: str = Field(..., min_length=1, max_length=1024)


class IdentityProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    issuer_url: str | None = Field(default=None, min_length=1, max_length=512)
    client_id: str | None = Field(default=None, min_length=1, max_length=256)
    # Optional on update — omit to leave the stored secret unchanged.
    client_secret: str | None = Field(default=None, min_length=1, max_length=1024)
    scopes: str | None = Field(default=None, max_length=256)
    enabled: bool | None = None


class IdentityProviderResponse(IdentityProviderBase):
    id: int
    slug: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Whether a stored secret is present (never the secret itself).
    has_secret: bool = True

    model_config = ConfigDict(from_attributes=True)


class IdentityProviderPublic(BaseModel):
    """Minimal, unauthenticated view for the login page's SSO buttons."""

    slug: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserIdentityResponse(BaseModel):
    id: int
    provider_name: str
    external_subject: str
    created_at: datetime | None = None
    last_login_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
