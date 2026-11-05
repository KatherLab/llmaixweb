# backend/src/services/sso_env_provider.py
"""Keep the provider declared through ``SSO_OIDC_*`` in step with the database.

The row is an ordinary :class:`IdentityProvider`, so the login flow has a single
code path; ``managed_by_env`` only makes it read-only in the admin API. No network
calls happen here: discovery stays lazy, so a Keycloak that is down while the
backend starts does not stop the backend from starting.
"""

from __future__ import annotations

import logging

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.sso import IdentityProvider
from ..utils.audit import record_audit
from ..utils.crypto import decrypt, encrypt
from ..utils.enums import AuditAction
from .oidc_service import normalize_group_setting, slugify_provider_name

logger = logging.getLogger(__name__)

_REQUIRED = ("SSO_OIDC_ISSUER_URL", "SSO_OIDC_CLIENT_ID", "SSO_OIDC_CLIENT_SECRET")


def _audit(provider: IdentityProvider, operation: str) -> None:
    record_audit(
        AuditAction.SSO_PROVIDER_CHANGE,
        actor_email="system:env",
        resource_type="identity_provider",
        resource_id=provider.id,
        detail={"operation": operation, "slug": provider.slug, "source": "env"},
    )


def _release_managed_provider(db: Session) -> None:
    """The variables were removed: stop offering the provider, keep its identities."""
    provider = db.scalar(
        select(IdentityProvider).where(IdentityProvider.managed_by_env.is_(True))
    )
    if not provider:
        return
    provider.managed_by_env = False
    provider.enabled = False
    db.commit()
    logger.warning(
        "SSO_OIDC_* is no longer set: provider '%s' is disabled and editable again.",
        provider.slug,
    )
    _audit(provider, "env_release")


def _find_target(db: Session, name: str, slug: str) -> IdentityProvider | None:
    """The row to write to: the managed one, else a same-named one to adopt, so
    that a provider first set up in the UI keeps its linked identities."""
    managed = db.scalar(
        select(IdentityProvider).where(IdentityProvider.managed_by_env.is_(True))
    )
    same_name = db.scalar(
        select(IdentityProvider).where(
            or_(IdentityProvider.slug == slug, IdentityProvider.name == name)
        )
    )
    if managed and same_name and managed.id != same_name.id:
        raise RuntimeError(
            f"SSO_OIDC_NAME='{name}' collides with the existing SSO provider "
            f"'{same_name.name}'. Rename or delete that provider first."
        )
    return managed or same_name


def sync_env_provider(db: Session) -> None:
    """Upsert the env-declared provider. Raises ``RuntimeError`` on a partial
    config: starting anyway would silently leave the deployment without its
    identity provider, and with first-admin setup open to the public."""
    values = {key: getattr(settings, key).strip() for key in _REQUIRED}
    if not any(values.values()):
        _release_managed_provider(db)
        return
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise RuntimeError(
            f"Incomplete SSO_OIDC_* configuration, missing: {', '.join(missing)}"
        )

    name = settings.SSO_OIDC_NAME.strip()
    try:
        slug = slugify_provider_name(name)
    except Exception as e:
        raise RuntimeError("SSO_OIDC_NAME must contain alphanumeric characters.") from e
    if not settings.SSO_ENABLED:
        logger.warning(
            "SSO_OIDC_* is set but SSO_ENABLED is false: provider '%s' is not active.",
            slug,
        )

    desired = {
        "name": name,
        "slug": slug,
        "issuer_url": values["SSO_OIDC_ISSUER_URL"].rstrip("/"),
        "client_id": values["SSO_OIDC_CLIENT_ID"],
        "scopes": settings.SSO_OIDC_SCOPES.strip() or "openid email profile",
        "enabled": True,
        "groups_claim": settings.SSO_OIDC_GROUPS_CLAIM.strip() or "groups",
        "user_groups": normalize_group_setting(settings.SSO_OIDC_USER_GROUPS),
        "admin_groups": normalize_group_setting(settings.SSO_OIDC_ADMIN_GROUPS),
        "managed_by_env": True,
    }
    secret = values["SSO_OIDC_CLIENT_SECRET"]

    provider = _find_target(db, name, slug)
    if provider is None:
        provider = IdentityProvider(**desired, client_secret_encrypted=encrypt(secret))
        db.add(provider)
        operation = "env_create"
    else:
        # Compare first: the audit trail should only show real changes, not one
        # row per restart. Fernet tokens differ per call, so compare plaintext.
        changed = any(getattr(provider, k) != v for k, v in desired.items())
        if decrypt(provider.client_secret_encrypted) != secret:
            provider.client_secret_encrypted = encrypt(secret)
            changed = True
        if not changed:
            return
        for key, value in desired.items():
            setattr(provider, key, value)
        operation = "env_update"

    try:
        db.commit()
    except IntegrityError:
        # Another worker of this deployment won the race with the same values.
        db.rollback()
        return
    _audit(provider, operation)
    logger.info("SSO provider '%s' synced from environment (%s).", slug, operation)


def verify_sso_only(db: Session) -> None:
    """Refuse to start with SSO_ONLY when nobody could sign in. Needs no network:
    an IdP that is merely down recovers on its own, a missing provider does not."""
    if not settings.SSO_ONLY:
        return
    if not settings.SSO_ENABLED:
        raise RuntimeError(
            "SSO_ONLY requires SSO_ENABLED=true (also check for an override of "
            "SSO_ENABLED in the admin settings)."
        )
    if not db.scalar(
        select(IdentityProvider.id).where(IdentityProvider.enabled.is_(True)).limit(1)
    ):
        raise RuntimeError(
            "SSO_ONLY requires an enabled SSO provider. Set SSO_OIDC_* or unset "
            "SSO_ONLY to configure one in the admin panel."
        )
    if settings.REQUIRE_INVITATION and not settings.SSO_BYPASS_INVITATION:
        logger.warning(
            "SSO_ONLY with SSO_BYPASS_INVITATION=false: invitations are disabled, "
            "so new users cannot get an account."
        )
