# backend/src/routers/v1/endpoints/shares.py
"""Project sharing: who, besides the owner, may reach a project.

Mounted under ``/project/{project_id}/share``. Reading the collaborator list is
open to anyone who can already read the project (a viewer should be able to see
who else is in the room); every mutation requires ``owner`` level, so a
full-access collaborator cannot widen the circle or lock the owner out.

Collaborators are addressed by **email**, not user id: ``GET /user`` is
admin-only, so a non-admin owner has no way to enumerate the directory. That is
deliberate — sharing must not become a user-enumeration oracle either, so an
unknown address and an inactive account return the same generic 404.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .... import models, schemas
from ....core.security import (
    ACCESS_OWNER,
    ACCESS_READ,
    can_access_project,
    get_current_user,
)
from ....dependencies import get_db
from ....utils.api_errors import api_error
from ....utils.audit import record_audit
from ....utils.enums import AuditAction

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_project(
    project_id: int, current_user: models.User, db: Session, permission: str
) -> models.Project:
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise api_error("shares.project_not_found", 404, "Project not found")
    if not can_access_project(current_user, project, permission=permission):
        raise api_error(
            "shares.project_forbidden",
            403,
            "Not authorized to manage sharing for this project",
            permission=permission,
        )
    return project


def _load_shares(project_id: int, db: Session) -> list[models.ProjectShare]:
    return list(
        db.execute(
            select(models.ProjectShare)
            .where(models.ProjectShare.project_id == project_id)
            .options(
                selectinload(models.ProjectShare.user),
                selectinload(models.ProjectShare.created_by),
            )
            .order_by(models.ProjectShare.created_at)
        )
        .scalars()
        .all()
    )


@router.get("", response_model=list[schemas.ProjectShare])
def list_project_shares(
    *,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.ProjectShare]:
    """List everyone the project is shared with (the owner is not included)."""
    _get_project(project_id, current_user, db, ACCESS_READ)
    return [
        schemas.ProjectShare.model_validate(share, from_attributes=True)
        for share in _load_shares(project_id, db)
    ]


@router.post("", response_model=schemas.ProjectShare)
def create_project_share(
    *,
    project_id: int,
    payload: schemas.ProjectShareCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> schemas.ProjectShare:
    """Share the project with an existing user, addressed by email.

    Idempotent on (project, user): sharing with someone who already has access
    updates their permission instead of failing on the unique constraint.
    """
    project = _get_project(project_id, current_user, db, ACCESS_OWNER)

    email = payload.email.strip()
    # Case-insensitive lookup: addresses are stored as typed at registration,
    # but nobody expects sharing to hinge on the capitalisation they used.
    target = db.execute(
        select(models.User).where(func.lower(models.User.email) == email.lower())
    ).scalar_one_or_none()

    # Same response for "no such user" and "deactivated account" — otherwise
    # this endpoint tells any project owner which addresses are registered.
    if not target or not target.is_active:
        raise api_error(
            "shares.user_not_found",
            404,
            "No active user with that email address",
        )

    if target.id == project.owner_id:
        raise api_error(
            "shares.cannot_share_with_owner",
            400,
            "This user already owns the project",
        )

    existing = db.execute(
        select(models.ProjectShare).where(
            models.ProjectShare.project_id == project_id,
            models.ProjectShare.user_id == target.id,
        )
    ).scalar_one_or_none()

    if existing:
        previous = existing.permission
        existing.permission = payload.permission
        share = existing
        action = AuditAction.PROJECT_SHARE_UPDATE
        detail = {
            "target_user_id": target.id,
            "from": getattr(previous, "value", previous),
            "to": payload.permission.value,
        }
    else:
        share = models.ProjectShare(
            project_id=project_id,
            user_id=target.id,
            permission=payload.permission,
            created_by_id=current_user.id,
        )
        db.add(share)
        action = AuditAction.PROJECT_SHARE
        detail = {"target_user_id": target.id, "permission": payload.permission.value}

    db.commit()
    db.refresh(share)

    record_audit(
        action,
        actor=current_user,
        resource_type="project_share",
        resource_id=share.id,
        project_id=project_id,
        detail=detail,
    )
    return schemas.ProjectShare.model_validate(share, from_attributes=True)


@router.patch("/{share_id}", response_model=schemas.ProjectShare)
def update_project_share(
    *,
    project_id: int,
    share_id: int,
    payload: schemas.ProjectShareUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> schemas.ProjectShare:
    """Change a collaborator's permission between read and write."""
    _get_project(project_id, current_user, db, ACCESS_OWNER)

    # Scoped by project_id as well as PK: a bare-PK lookup would let an owner
    # of project A edit a share belonging to project B.
    share = db.execute(
        select(models.ProjectShare)
        .where(
            models.ProjectShare.id == share_id,
            models.ProjectShare.project_id == project_id,
        )
        .options(selectinload(models.ProjectShare.user))
    ).scalar_one_or_none()
    if not share:
        raise api_error("shares.not_found", 404, "Share not found")

    previous = share.permission
    share.permission = payload.permission
    db.commit()
    db.refresh(share)

    record_audit(
        AuditAction.PROJECT_SHARE_UPDATE,
        actor=current_user,
        resource_type="project_share",
        resource_id=share.id,
        project_id=project_id,
        detail={
            "target_user_id": share.user_id,
            "from": getattr(previous, "value", previous),
            "to": payload.permission.value,
        },
    )
    return schemas.ProjectShare.model_validate(share, from_attributes=True)


@router.delete("/{share_id}")
def delete_project_share(
    *,
    project_id: int,
    share_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Revoke a share.

    Two callers are allowed: the owner revoking someone else's access, and a
    collaborator giving up their own (the "leave project" action). The latter
    is why this endpoint resolves the share *before* gating on ownership.
    """
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise api_error("shares.project_not_found", 404, "Project not found")

    share = db.execute(
        select(models.ProjectShare).where(
            models.ProjectShare.id == share_id,
            models.ProjectShare.project_id == project_id,
        )
    ).scalar_one_or_none()
    if not share:
        raise api_error("shares.not_found", 404, "Share not found")

    is_self_removal = share.user_id == current_user.id
    if not is_self_removal and not can_access_project(
        current_user, project, permission=ACCESS_OWNER
    ):
        raise api_error(
            "shares.project_forbidden",
            403,
            "Not authorized to manage sharing for this project",
            permission=ACCESS_OWNER,
        )

    target_user_id = share.user_id
    db.delete(share)
    db.commit()

    record_audit(
        AuditAction.PROJECT_UNSHARE,
        actor=current_user,
        resource_type="project_share",
        resource_id=share_id,
        project_id=project_id,
        detail={"target_user_id": target_user_id, "self_removal": is_self_removal},
    )
    return {"status": "success"}
