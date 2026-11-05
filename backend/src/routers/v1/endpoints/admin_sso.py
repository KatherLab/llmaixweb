# backend/src/routers/v1/endpoints/admin_sso.py
"""Admin CRUD for OIDC identity providers."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .... import schemas
from ....core.config import settings
from ....core.security import get_admin_user
from ....dependencies import get_db
from ....models import User
from ....models.sso import IdentityProvider
from ....services import oidc_service
from ....utils.api_errors import api_error
from ....utils.audit import record_audit
from ....utils.crypto import encrypt
from ....utils.enums import AuditAction

router = APIRouter()


def _to_response(provider: IdentityProvider) -> schemas.IdentityProviderResponse:
    return schemas.IdentityProviderResponse(
        id=provider.id,
        name=provider.name,
        slug=provider.slug,
        issuer_url=provider.issuer_url,
        client_id=provider.client_id,
        scopes=provider.scopes,
        enabled=provider.enabled,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
        has_secret=bool(provider.client_secret_encrypted),
        groups_claim=provider.groups_claim,
        user_groups=provider.user_groups,
        admin_groups=provider.admin_groups,
        managed_by_env=provider.managed_by_env,
    )


def _refuse_if_managed(provider: IdentityProvider) -> None:
    if provider.managed_by_env:
        raise api_error(
            "sso.provider_managed_by_env",
            status.HTTP_409_CONFLICT,
            "This provider is configured via SSO_OIDC_* environment variables. "
            "Change it there and restart the backend.",
        )


def _refuse_if_last_provider_under_sso_only(
    db: Session, provider: IdentityProvider
) -> None:
    """With SSO_ONLY, the last enabled provider is the only way into the app."""
    if not settings.SSO_ONLY or not provider.enabled:
        return
    other_enabled = db.scalar(
        select(IdentityProvider.id)
        .where(IdentityProvider.enabled.is_(True), IdentityProvider.id != provider.id)
        .limit(1)
    )
    if not other_enabled:
        raise api_error(
            "sso.sso_only_last_provider",
            status.HTTP_409_CONFLICT,
            "The last enabled provider cannot be removed while SSO_ONLY is set.",
        )


@router.get("/providers", response_model=list[schemas.IdentityProviderResponse])
def list_providers(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> list[schemas.IdentityProviderResponse]:
    providers = (
        db.execute(select(IdentityProvider).order_by(IdentityProvider.id))
        .scalars()
        .all()
    )
    return [_to_response(p) for p in providers]


@router.post(
    "/providers", response_model=schemas.IdentityProviderResponse, status_code=201
)
def create_provider(
    payload: schemas.IdentityProviderCreate = Body(...),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> schemas.IdentityProviderResponse:
    slug = oidc_service.slugify_provider_name(payload.name)
    if db.execute(
        select(IdentityProvider).where(
            (IdentityProvider.slug == slug) | (IdentityProvider.name == payload.name)
        )
    ).scalar_one_or_none():
        raise api_error(
            "sso.provider_name_exists",
            status.HTTP_400_BAD_REQUEST,
            "A provider with this name already exists.",
        )
    # Validate the issuer/discovery up front so misconfig is caught at save.
    oidc_service.discover(payload.issuer_url)

    provider = IdentityProvider(
        name=payload.name,
        slug=slug,
        issuer_url=payload.issuer_url.rstrip("/"),
        client_id=payload.client_id,
        client_secret_encrypted=encrypt(payload.client_secret),
        scopes=payload.scopes,
        enabled=payload.enabled,
        groups_claim=payload.groups_claim.strip(),
        user_groups=oidc_service.normalize_group_setting(payload.user_groups),
        admin_groups=oidc_service.normalize_group_setting(payload.admin_groups),
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    record_audit(
        AuditAction.SSO_PROVIDER_CHANGE,
        actor=current_user,
        resource_type="identity_provider",
        resource_id=provider.id,
        detail={"operation": "create", "slug": provider.slug},
    )
    return _to_response(provider)


@router.patch(
    "/providers/{provider_id}", response_model=schemas.IdentityProviderResponse
)
def update_provider(
    provider_id: int = Path(...),
    payload: schemas.IdentityProviderUpdate = Body(...),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> schemas.IdentityProviderResponse:
    provider = db.get(IdentityProvider, provider_id)
    if not provider:
        raise api_error(
            "sso.provider_not_found",
            status.HTTP_404_NOT_FOUND,
            "Provider not found.",
        )
    _refuse_if_managed(provider)

    if payload.name is not None and payload.name != provider.name:
        new_slug = oidc_service.slugify_provider_name(payload.name)
        if db.execute(
            select(IdentityProvider).where(
                (IdentityProvider.slug == new_slug)
                | (IdentityProvider.name == payload.name),
                IdentityProvider.id != provider.id,
            )
        ).scalar_one_or_none():
            raise api_error(
                "sso.provider_name_exists",
                status.HTTP_400_BAD_REQUEST,
                "A provider with this name already exists.",
            )
        provider.name = payload.name
        provider.slug = new_slug
    if payload.issuer_url is not None and payload.issuer_url != provider.issuer_url:
        oidc_service.discover(payload.issuer_url)
        provider.issuer_url = payload.issuer_url.rstrip("/")
    if payload.client_id is not None:
        provider.client_id = payload.client_id
    if payload.scopes is not None:
        provider.scopes = payload.scopes
    if payload.enabled is False:
        _refuse_if_last_provider_under_sso_only(db, provider)
    if payload.enabled is not None:
        provider.enabled = payload.enabled
    if payload.groups_claim is not None:
        provider.groups_claim = payload.groups_claim.strip()
    if payload.user_groups is not None:
        provider.user_groups = oidc_service.normalize_group_setting(payload.user_groups)
    if payload.admin_groups is not None:
        provider.admin_groups = oidc_service.normalize_group_setting(
            payload.admin_groups
        )
    if payload.client_secret:
        provider.client_secret_encrypted = encrypt(payload.client_secret)

    db.commit()
    db.refresh(provider)
    record_audit(
        AuditAction.SSO_PROVIDER_CHANGE,
        actor=current_user,
        resource_type="identity_provider",
        resource_id=provider.id,
        detail={
            "operation": "update",
            "slug": provider.slug,
            "fields": sorted(payload.model_dump(exclude_unset=True).keys()),
        },
    )
    return _to_response(provider)


@router.delete("/providers/{provider_id}", status_code=204)
def delete_provider(
    provider_id: int = Path(...),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    provider = db.get(IdentityProvider, provider_id)
    if not provider:
        raise api_error(
            "sso.provider_not_found",
            status.HTTP_404_NOT_FOUND,
            "Provider not found.",
        )
    _refuse_if_managed(provider)
    _refuse_if_last_provider_under_sso_only(db, provider)
    slug = provider.slug
    db.delete(provider)
    db.commit()
    record_audit(
        AuditAction.SSO_PROVIDER_CHANGE,
        actor=current_user,
        resource_type="identity_provider",
        resource_id=provider_id,
        detail={"operation": "delete", "slug": slug},
    )
    return None
