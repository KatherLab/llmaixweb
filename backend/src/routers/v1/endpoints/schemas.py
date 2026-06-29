# backend/src/routers/v1/endpoints/schemas.py
"""Schema endpoints for projects."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .... import models, schemas
from ....core.security import get_current_user
from ....dependencies import get_db
from ....utils.helpers import extract_field_types_from_schema

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

    raise HTTPException(
        status_code=403, detail=f"Not authorized to {permission} this project"
    )


@router.post("", response_model=schemas.Schema)
def create_schema(
    project_id: int,
    schema: schemas.SchemaCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Schema:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to create schemas for this project"
        )
    if not isinstance(schema.schema_definition, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON schema")
    schema_db = models.Schema(**schema.model_dump(), project_id=project_id)
    db.add(schema_db)
    db.commit()
    db.refresh(schema_db)
    return schemas.Schema.model_validate(schema_db)


@router.get("", response_model=list[schemas.Schema])
def get_schemas(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(1000, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[schemas.Schema]:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's schemas"
        )

    schemas_list = list(
        db.execute(
            select(models.Schema)
            .where(models.Schema.project_id == project_id)
            .order_by(models.Schema.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return [schemas.Schema.model_validate(s) for s in schemas_list]


@router.get("/{schema_id}", response_model=schemas.Schema)
def get_schema(
    project_id: int,
    schema_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Schema:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's schemas"
        )

    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id, models.Schema.id == schema_id
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    return schemas.Schema.model_validate(schema)


@router.put("/{schema_id}", response_model=schemas.Schema)
def update_schema(
    project_id: int,
    schema_id: int,
    schema: schemas.SchemaUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Schema:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to update schemas for this project"
        )

    existing_schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id, models.Schema.id == schema_id
        )
    ).scalar_one_or_none()
    if not existing_schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    if not isinstance(schema.schema_definition, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON schema")

    for key, value in schema.model_dump(exclude_unset=True).items():
        setattr(existing_schema, key, value)

    db.add(existing_schema)
    db.commit()
    db.refresh(existing_schema)

    return schemas.Schema.model_validate(existing_schema)


@router.delete("/{schema_id}", response_model=schemas.Schema)
def delete_schema(
    project_id: int,
    schema_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Schema:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete schemas from this project"
        )

    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id, models.Schema.id == schema_id
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Check if the schema is referenced by any trials
    trials: list[models.Trial] = (
        db.execute(select(models.Trial).where(models.Trial.schema_id == schema_id))
        .scalars()
        .all()
    )

    if trials:
        raise HTTPException(
            status_code=400, detail="Cannot delete schema referenced by a trial"
        )

    db.delete(schema)
    db.commit()
    return schemas.Schema.model_validate(schema)


@router.get("/{schema_id}/field_types", response_model=dict)
def get_schema_field_types(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    schema_id: int,
    current_user: models.User = Depends(get_current_user),
) -> dict:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's schemas"
        )

    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id, models.Schema.id == schema_id
        )
    ).scalar_one_or_none()

    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    field_types = {}
    extract_field_types_from_schema(schema.schema_definition, field_types)

    return field_types
