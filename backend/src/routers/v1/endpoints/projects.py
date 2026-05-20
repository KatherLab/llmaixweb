from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, load_only, noload, selectinload

from .... import models, schemas
from ....core.security import get_current_user
from ....dependencies import get_db
from .documents import router as documents_router
from .evaluations import router as evaluations_router
from .files import router as files_router
from .groundtruth import router as groundtruth_router
from .llm import router as llm_router
from .preprocessing_config import router as preprocessing_config_router
from .preprocess import router as preprocess_router
from .prompts import router as prompts_router
from .schemas import router as schemas_router
from .trials import router as trials_router

router = APIRouter()
router.include_router(files_router, prefix="/{project_id}/file", tags=["files"])
router.include_router(preprocessing_config_router, prefix="/{project_id}", tags=["preprocessing-config"])
router.include_router(preprocess_router, prefix="/{project_id}", tags=["preprocess"])
router.include_router(documents_router, prefix="/{project_id}", tags=["documents"])
router.include_router(prompts_router, prefix="/{project_id}/prompt", tags=["prompts"])
router.include_router(schemas_router, prefix="/{project_id}/schema", tags=["schemas"])
router.include_router(trials_router, prefix="/{project_id}/trial", tags=["trials"])
router.include_router(groundtruth_router, prefix="/{project_id}", tags=["groundtruth"])
router.include_router(evaluations_router, prefix="/{project_id}", tags=["evaluations"])
router.include_router(llm_router, prefix="/llm", tags=["llm"])


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
    # You could extend this with a project_members table for shared projects
    raise HTTPException(
        status_code=403, detail=f"Not authorized to {permission} this project"
    )


@router.get(
    "/", response_model=list[schemas.Project], response_model_exclude={"documents"}
)  # keep documents out
def get_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.Project]:
    stmt = select(models.Project)

    if current_user.role != "admin":
        stmt = stmt.where(models.Project.owner_id == current_user.id)

    stmt = stmt.options(
        # bring owner, but only minimal fields
        selectinload(models.Project.owner).options(
            load_only(models.User.id, models.User.full_name, models.User.email)
        ),
        # absolutely no documents on the list route
        noload(models.Project.documents),
    )

    projects = list(db.execute(stmt).scalars().all())
    return projects


@router.get("/{project_id}", response_model=schemas.Project)
def get_project(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.Project:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project"
        )

    return project


@router.post("/", response_model=schemas.Project)
def create_project(
    *,
    db: Session = Depends(get_db),
    project: schemas.ProjectCreate,
    current_user: models.User = Depends(get_current_user),
) -> schemas.Project:
    if not current_user.role == "user":
        if not project.owner_id:
            project.owner_id = current_user.id
        elif project.owner_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to create project for another user",
            )
    else:
        if not project.owner_id:
            project.owner_id = current_user.id

    new_project = models.Project(**project.model_dump())

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return schemas.Project.model_validate(new_project)


@router.put("/{project_id}", response_model=schemas.Project)
def update_project(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    project: schemas.ProjectUpdate,
    current_user: models.User = Depends(get_current_user),
) -> schemas.Project:
    existing_project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not existing_project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and existing_project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this project"
        )

    for key, value in project.model_dump(exclude_unset=True).items():
        setattr(existing_project, key, value)

    db.add(existing_project)
    db.commit()
    db.refresh(existing_project)

    return schemas.Project.model_validate(existing_project)


@router.delete("/{project_id}", response_model=schemas.Project)
def delete_project(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.Project:
    existing_project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not existing_project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and existing_project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this project"
        )

    # TODO: Make sure to handle any related resources (e.g., files, documents) before deleting the project

    db.delete(existing_project)
    db.commit()

    return schemas.Project.model_validate(existing_project)
