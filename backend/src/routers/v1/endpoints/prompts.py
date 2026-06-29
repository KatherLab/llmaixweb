# backend/src/routers/v1/endpoints/prompts.py
"""Prompt endpoints for projects."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .... import models, schemas
from ....core.security import get_current_user
from ....dependencies import get_db
from ....utils.helpers import validate_prompt

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


@router.post("", response_model=schemas.Prompt)
def create_prompt(
    project_id: int,
    prompt: schemas.PromptCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Prompt:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to create prompts for this project"
        )

    # Validate prompt
    validate_prompt(prompt)

    prompt_db = models.Prompt(
        **prompt.model_dump(exclude={"project_id"}), project_id=project_id
    )
    db.add(prompt_db)
    db.commit()
    db.refresh(prompt_db)
    return schemas.Prompt.model_validate(prompt_db)


@router.get("", response_model=list[schemas.Prompt])
def get_prompts(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(1000, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[schemas.Prompt]:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's prompts"
        )

    prompts_list = list(
        db.execute(
            select(models.Prompt)
            .where(models.Prompt.project_id == project_id)
            .order_by(models.Prompt.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return [schemas.Prompt.model_validate(p) for p in prompts_list]


@router.get("/{prompt_id}", response_model=schemas.Prompt)
def get_prompt(
    project_id: int,
    prompt_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Prompt:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's prompts"
        )

    prompt: models.Prompt | None = db.execute(
        select(models.Prompt).where(
            models.Prompt.project_id == project_id, models.Prompt.id == prompt_id
        )
    ).scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return schemas.Prompt.model_validate(prompt)


@router.put("/{prompt_id}", response_model=schemas.Prompt)
def update_prompt(
    project_id: int,
    prompt_id: int,
    prompt: schemas.PromptUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Prompt:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to update prompts for this project"
        )

    existing_prompt: models.Prompt | None = db.execute(
        select(models.Prompt).where(
            models.Prompt.project_id == project_id, models.Prompt.id == prompt_id
        )
    ).scalar_one_or_none()
    if not existing_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Create a temporary object to validate
    temp_prompt = schemas.PromptUpdate(
        system_prompt=prompt.system_prompt
        if prompt.system_prompt is not None
        else existing_prompt.system_prompt,
        user_prompt=prompt.user_prompt
        if prompt.user_prompt is not None
        else existing_prompt.user_prompt,
    )
    validate_prompt(temp_prompt)

    for key, value in prompt.model_dump(exclude_unset=True).items():
        setattr(existing_prompt, key, value)

    db.add(existing_prompt)
    db.commit()
    db.refresh(existing_prompt)

    return schemas.Prompt.model_validate(existing_prompt)


@router.delete("/{prompt_id}", response_model=schemas.Prompt)
def delete_prompt(
    project_id: int,
    prompt_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Prompt:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete prompts from this project"
        )

    prompt: models.Prompt | None = db.execute(
        select(models.Prompt).where(
            models.Prompt.project_id == project_id, models.Prompt.id == prompt_id
        )
    ).scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Check if the prompt is referenced by any trials
    trial = (
        db.execute(select(models.Trial).where(models.Trial.prompt_id == prompt_id))
        .scalars()
        .first()
    )
    if trial:
        raise HTTPException(
            status_code=400, detail="Cannot delete prompt referenced by a trial"
        )

    db.delete(prompt)
    db.commit()
    return schemas.Prompt.model_validate(prompt)
