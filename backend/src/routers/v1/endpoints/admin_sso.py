# backend/src/routers/v1/endpoints/admin_sso.py
"""Admin CRUD for OIDC identity providers."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .... import schemas
from ....core.security import get_admin_user
from ....dependencies import get_db
from ....models import User
from ....models.sso import IdentityProvider
from ....services import oidc_service
from ....utils.crypto import encrypt

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
    slug = _slugify(payload.name)
    if db.execute(
        select(IdentityProvider).where(
            (IdentityProvider.slug == slug) | (IdentityProvider.name == payload.name)
        )
    ).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A provider with this name already exists.",
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
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found."
        )

    if payload.name is not None and payload.name != provider.name:
        new_slug = _slugify(payload.name)
        if db.execute(
            select(IdentityProvider).where(
                (IdentityProvider.slug == new_slug)
                | (IdentityProvider.name == payload.name),
                IdentityProvider.id != provider.id,
            )
        ).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A provider with this name already exists.",
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
    if payload.enabled is not None:
        provider.enabled = payload.enabled
    if payload.client_secret:
        provider.client_secret_encrypted = encrypt(payload.client_secret)

    db.commit()
    db.refresh(provider)
    return _to_response(provider)


@router.delete("/providers/{provider_id}", status_code=204)
def delete_provider(
    provider_id: int = Path(...),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    provider = db.get(IdentityProvider, provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found."
        )
    db.delete(provider)
    db.commit()
    return None


def _slugify(name: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider name must contain alphanumeric characters.",
        )
    return slug[:100]
