# backend/src/models/sso.py
"""OpenID Connect SSO models.

An :class:`IdentityProvider` is an admin-configured OIDC IdP (Google,
Keycloak, Azure AD, …). A :class:`UserIdentity` links a local :class:`User`
to an external identity ``(provider, subject)`` — one user may have several
linked identities. SSO login resolves the identity (or JIT-creates the user)
and issues the same JWT the password flow uses.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base

if TYPE_CHECKING:
    from .user import User


class IdentityProvider(Base):
    __tablename__ = "identity_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Human-readable label shown on the "Continue with X" button.
    name: Mapped[str] = mapped_column(String(100), unique=True)
    # URL-safe identifier used in routes (/auth/sso/{slug}/...). Lowercase,
    # slugified from name on create.
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    # Issuer URL — the IdP's base URL, used for OIDC discovery
    # ({issuer}/.well-known/openid-configuration).
    issuer_url: Mapped[str] = mapped_column(String(512))
    client_id: Mapped[str] = mapped_column(String(256))
    # Fernet-encrypted at rest (see utils.crypto). Never returned by the API.
    client_secret_encrypted: Mapped[str] = mapped_column(String(1024))
    scopes: Mapped[str] = mapped_column(String(256), default="openid email profile")
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), onupdate=func.now()
    )

    identities: Mapped[list["UserIdentity"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        # A given external subject is unique per provider.
        UniqueConstraint("provider_id", "external_subject", name="uq_provider_subject"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("identity_providers.id", ondelete="CASCADE"), index=True
    )
    # The IdP's stable subject claim (`sub`). Combined with provider_id this
    # is the federated primary key.
    external_subject: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    user: Mapped["User"] = relationship(back_populates="identities")
    provider: Mapped["IdentityProvider"] = relationship(back_populates="identities")
