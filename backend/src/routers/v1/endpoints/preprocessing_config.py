"""Preprocessing configuration endpoints for projects."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .... import models, schemas
from ....core.security import get_current_user
from ....dependencies import get_db

router = APIRouter()


def check_project_access(
    project_id: int, current_user: models.User, db: Session, permission: str = "read"
) -> models.Project:
    """Check if user has access to project."""
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Admin has full access
    if current_user.role == "admin":
        return project

    # Owner has full access
    if project.owner_id == current_user.id:
        return project

    # For non-owners, check specific permissions if needed
    raise HTTPException(
        status_code=403, detail=f"Not authorized to {permission} this project"
    )


@router.get(
    "/preprocessing-config",
    response_model=List[schemas.PreprocessingConfiguration],
)
def get_preprocessing_configurations(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_type: str | None = None,
    current_user: models.User = Depends(get_current_user),
) -> List[schemas.PreprocessingConfiguration]:
    """Get all preprocessing configurations for a project."""
    check_project_access(project_id, current_user, db, "read")

    query = select(models.PreprocessingConfiguration).where(
        models.PreprocessingConfiguration.project_id == project_id
    )

    if file_type:
        file_type_enum = models.FileType(file_type)  # now accepts "mixed"
        query = query.where(
            models.PreprocessingConfiguration.file_type == file_type_enum
        )

    configs = db.execute(query).scalars().all()
    return [schemas.PreprocessingConfiguration.model_validate(c) for c in configs]


@router.get(
    "/preprocessing-config/{config_id}",
    response_model=schemas.PreprocessingConfiguration,
)
def get_preprocessing_configuration(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    config_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.PreprocessingConfiguration:
    """Get a specific preprocessing configuration."""
    check_project_access(project_id, current_user, db, "read")

    config = db.execute(
        select(models.PreprocessingConfiguration).where(
            models.PreprocessingConfiguration.id == config_id,
            models.PreprocessingConfiguration.project_id == project_id,
        )
    ).scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    return schemas.PreprocessingConfiguration.model_validate(config)


@router.post(
    "/preprocessing-config",
    response_model=schemas.PreprocessingConfiguration,
)
def create_preprocessing_configuration(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    config: schemas.PreprocessingConfigurationCreate,
    current_user: models.User = Depends(get_current_user),
) -> schemas.PreprocessingConfiguration:
    """Create a reusable preprocessing configuration."""
    check_project_access(project_id, current_user, db, "write")

    # Check for duplicate names
    existing = db.execute(
        select(models.PreprocessingConfiguration).where(
            models.PreprocessingConfiguration.project_id == project_id,
            models.PreprocessingConfiguration.name == config.name,
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400, detail="Configuration with this name already exists"
        )

    # Create new configuration
    db_config = models.PreprocessingConfiguration(
        **config.model_dump(), project_id=project_id
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)

    return schemas.PreprocessingConfiguration.model_validate(db_config)


@router.put(
    "/preprocessing-config/{config_id}",
    response_model=schemas.PreprocessingConfiguration,
)
def update_preprocessing_configuration(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    config_id: int,
    config_update: schemas.PreprocessingConfigurationUpdate,
    current_user: models.User = Depends(get_current_user),
) -> schemas.PreprocessingConfiguration:
    """Update a preprocessing configuration."""
    check_project_access(project_id, current_user, db, "write")

    config = db.execute(
        select(models.PreprocessingConfiguration).where(
            models.PreprocessingConfiguration.id == config_id,
            models.PreprocessingConfiguration.project_id == project_id,
        )
    ).scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Check if configuration is in use by active task
    active_tasks = (
        db.execute(
            select(models.PreprocessingTask).where(
                models.PreprocessingTask.configuration_id == config_id,
                models.PreprocessingTask.status.in_(
                    [
                        models.PreprocessingStatus.PENDING,
                        models.PreprocessingStatus.IN_PROGRESS,
                    ]
                ),
            )
        )
        .scalars()
        .first()
    )

    if active_tasks:
        raise HTTPException(
            status_code=400,
            detail="Cannot update configuration while it's being used in active tasks",
        )

    # Is config referenced by any document?
    in_use = (
        db.query(models.Document)
        .filter(models.Document.preprocessing_config_id == config.id)
        .count()
        > 0
    )

    allowed_fields = {"name", "description"}
    changes = config_update.model_dump(exclude_unset=True)

    if in_use:
        # Find which *disallowed* fields are *actually being changed*
        disallowed_changed = [
            field
            for field, value in changes.items()
            if field not in allowed_fields and getattr(config, field) != value
        ]
        if disallowed_changed:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cannot edit a configuration in use by existing documents "
                    "(except name/description). The following fields would change: "
                    f"{', '.join(disallowed_changed)}"
                ),
            )

    # Apply the changes
    for field, value in changes.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return schemas.PreprocessingConfiguration.model_validate(config)


@router.delete("/preprocessing-config/{config_id}")
def delete_preprocessing_configuration(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    config_id: int,
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Delete a preprocessing configuration."""
    check_project_access(project_id, current_user, db, "write")

    config = db.execute(
        select(models.PreprocessingConfiguration).where(
            models.PreprocessingConfiguration.id == config_id,
            models.PreprocessingConfiguration.project_id == project_id,
        )
    ).scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Check if configuration has been used
    tasks_using_config = (
        db.execute(
            select(models.PreprocessingTask).where(
                models.PreprocessingTask.configuration_id == config_id
            )
        )
        .scalars()
        .first()
    )

    if tasks_using_config:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete configuration that has been used in preprocessing tasks",
        )

    db.delete(config)
    db.commit()

    return {"detail": "Configuration deleted successfully"}
