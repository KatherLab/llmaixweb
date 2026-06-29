# backend/src/routers/v1/endpoints/projects.py
import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, load_only, noload, selectinload

from .... import models, schemas
from ....core.security import get_current_user
from ....dependencies import get_db, remove_file
from .documents import router as documents_router
from .evaluations import router as evaluations_router
from .files import router as files_router
from .groundtruth import router as groundtruth_router
from .llm import router as llm_router
from .preprocess import router as preprocess_router
from .prompts import router as prompts_router
from .schemas import router as schemas_router
from .trials import router as trials_router

logger = logging.getLogger(__name__)

router = APIRouter()


# IMPORTANT: Activity endpoint must be registered BEFORE /{project_id} routes
# FastAPI matches routes in order, and /{project_id} would match "activity" first
@router.get(
    "/activity/preprocess",
    response_model=list[schemas.PreprocessingTask],
    tags=["activity"],
)
def get_recent_preprocessing_tasks(
    *,
    limit: int = Query(10, ge=1, le=100),
    active_only: bool = Query(
        False, description="Only return active/in-progress tasks"
    ),
    hours: int = Query(
        24, ge=1, le=168, description="Hours to look back for completed tasks"
    ),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.PreprocessingTask]:
    """Get recent preprocessing tasks across all projects the user has access to."""
    # Get all projects the user has access to
    project_query = select(models.Project.id)

    if current_user.role != "admin":
        # Non-admin users only see their own projects
        project_query = project_query.where(models.Project.owner_id == current_user.id)

    project_ids = db.execute(project_query).scalars().all()

    if not project_ids:
        return []

    # Build query
    query = select(models.PreprocessingTask).where(
        models.PreprocessingTask.project_id.in_(project_ids)
    )

    # Filter by active_only if requested
    if active_only:
        query = query.where(
            models.PreprocessingTask.status.in_(["pending", "in_progress"])
        )
    else:
        # Filter by time window for completed tasks
        hours_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            hours=hours
        )
        query = query.where(
            or_(
                models.PreprocessingTask.status.in_(["pending", "in_progress"]),
                models.PreprocessingTask.created_at >= hours_ago,
            )
        )

    # Fetch recent preprocessing tasks from these projects
    query = (
        query.options(
            selectinload(models.PreprocessingTask.file_tasks).selectinload(
                models.FilePreprocessingTask.file
            ),
            selectinload(models.PreprocessingTask.configuration),
        )
        .order_by(models.PreprocessingTask.created_at.desc())
        .limit(limit)
    )

    tasks = db.execute(query).scalars().all()
    return [schemas.PreprocessingTask.model_validate(task) for task in tasks]


@router.get(
    "/activity/trials", response_model=list[schemas.TrialSummary], tags=["activity"]
)
def get_recent_trials(
    *,
    limit: int = Query(10, ge=1, le=100),
    active_only: bool = Query(
        False, description="Only return active/in-progress trials"
    ),
    hours: int = Query(
        24, ge=1, le=168, description="Hours to look back for completed trials"
    ),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.TrialSummary]:
    """Get recent trials across all projects the user has access to."""
    from sqlalchemy import func, or_

    # Get all projects the user has access to
    project_query = select(models.Project.id)

    if current_user.role != "admin":
        # Non-admin users only see their own projects
        project_query = project_query.where(models.Project.owner_id == current_user.id)

    project_ids = db.execute(project_query).scalars().all()

    if not project_ids:
        return []

    # Build query
    query = select(models.Trial).where(models.Trial.project_id.in_(project_ids))

    # Filter by active_only if requested
    if active_only:
        query = query.where(models.Trial.status.in_(["pending", "processing"]))
    else:
        # Filter by time window for completed trials
        hours_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            hours=hours
        )
        query = query.where(
            or_(
                models.Trial.status.in_(["pending", "processing"]),
                models.Trial.created_at >= hours_ago,
            )
        )

    # Order and limit
    query = query.order_by(models.Trial.created_at.desc()).limit(limit)

    trials = db.execute(query).scalars().all()

    if not trials:
        return []

    trial_ids = [trial.id for trial in trials]

    # Fetch per-trial aggregates in two grouped queries instead of 2 queries
    # per trial inside the loop (N+1).
    counts_by_trial = {
        row[0]: (row[1] or 0)
        for row in db.execute(
            select(
                models.TrialResult.trial_id,
                func.count(models.TrialResult.id),
            )
            .where(models.TrialResult.trial_id.in_(trial_ids))
            .group_by(models.TrialResult.trial_id)
        ).all()
    }

    last_result_by_trial = {
        row[0]: row[1]
        for row in db.execute(
            select(
                models.TrialResult.trial_id,
                func.max(models.TrialResult.created_at),
            )
            .where(models.TrialResult.trial_id.in_(trial_ids))
            .group_by(models.TrialResult.trial_id)
        ).all()
    }

    # Build TrialSummary objects with computed fields
    result = []
    for trial in trials:
        results_count = counts_by_trial.get(trial.id, 0)
        last_result = last_result_by_trial.get(trial.id)

        # Count errors from meta.failures
        error_count = None
        has_failures = None
        if isinstance(trial.meta, dict) and isinstance(
            trial.meta.get("failures"), dict
        ):
            error_count = len(trial.meta["failures"])
            has_failures = error_count > 0

        # Create summary
        summary = schemas.TrialSummary(
            id=trial.id,
            project_id=trial.project_id,
            name=trial.name,
            description=trial.description,
            schema_id=trial.schema_id,
            prompt_id=trial.prompt_id,
            document_ids=trial.document_ids,
            document_set_id=trial.document_set_id,
            llm_model=trial.llm_model,
            bypass_celery=trial.bypass_celery,
            advanced_options=trial.advanced_options,
            status=trial.status,
            created_at=trial.created_at,
            updated_at=trial.updated_at,
            docs_done=trial.docs_done,
            progress=trial.progress,
            started_at=trial.started_at,
            finished_at=trial.finished_at,
            meta=trial.meta,
            documents_count=len(trial.document_ids) if trial.document_ids else 0,
            results_count=results_count,
            last_result_at=last_result,
            error_count=error_count,
            has_failures=has_failures,
        )
        result.append(summary)

    return result


router.include_router(files_router, prefix="/{project_id}/file", tags=["files"])
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
    "", response_model=list[schemas.Project], response_model_exclude={"documents"}
)  # keep documents out
def get_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    all: bool = False,
    limit: int = Query(1000, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[schemas.Project]:
    from sqlalchemy import func

    stmt = select(models.Project)

    if current_user.role == "admin":
        if not all:
            stmt = stmt.where(models.Project.owner_id == current_user.id)
    else:
        stmt = stmt.where(models.Project.owner_id == current_user.id)

    # Subquery to count documents per project
    doc_count_subq = (
        select(func.count(models.Document.id))
        .where(models.Document.project_id == models.Project.id)
        .where(models.Document.is_latest)
        .correlate(models.Project)
        .scalar_subquery()
    )

    stmt = stmt.add_columns(doc_count_subq.label("document_count"))

    stmt = stmt.options(
        # bring owner, but only minimal fields
        selectinload(models.Project.owner).options(
            load_only(models.User.id, models.User.full_name, models.User.email)
        ),
        # absolutely no documents on the list route
        noload(models.Project.documents),
    )

    stmt = stmt.order_by(models.Project.created_at.desc()).limit(limit).offset(offset)

    results = list(db.execute(stmt).all())

    # Build projects with document_count
    projects = []
    for project, doc_count in results:
        project_dict = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "owner_id": project.owner_id,
            "owner": project.owner,
            "document_count": doc_count or 0,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        }
        projects.append(schemas.Project(**project_dict))

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


@router.post("", response_model=schemas.Project)
def create_project(
    *,
    db: Session = Depends(get_db),
    project: schemas.ProjectCreate,
    current_user: models.User = Depends(get_current_user),
) -> schemas.Project:
    if current_user.role == "admin":
        # Admins may create a project owned by another user; default to self.
        if not project.owner_id:
            project.owner_id = current_user.id
    else:
        # Non-admins can only create projects they own — ignore any client-
        # supplied owner_id to prevent creating projects under another user.
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

    update_data = project.model_dump(exclude_unset=True)
    # Ownership transfer is admin-only: a non-admin owner must not be able to
    # reassign the project to another user (privilege/visibility escalation).
    if current_user.role != "admin":
        update_data.pop("owner_id", None)

    for key, value in update_data.items():
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

    # Collect stored-file UUIDs (uploaded files + ground truth) before the
    # cascade-delete removes their DB rows, so we can still free the bytes in
    # local/S3 storage afterwards. Mirrors delete_user (users.py).
    file_uuids = [
        row[0]
        for row in db.execute(
            select(models.File.file_uuid).where(models.File.project_id == project_id)
        ).all()
    ]
    file_uuids.extend(
        row[0]
        for row in db.execute(
            select(models.GroundTruth.file_uuid).where(
                models.GroundTruth.project_id == project_id
            )
        ).all()
    )

    # Commit the DB deletion first; only then remove the stored bytes. If a
    # storage removal fails we log and continue (the DB row is already gone,
    # so leaving an orphaned blob is the lesser evil vs. failing the delete).
    db.delete(existing_project)
    db.commit()

    for file_uuid in file_uuids:
        try:
            remove_file(file_uuid)
        except FileNotFoundError:
            pass
        except Exception:
            logger.warning(
                "Failed to remove stored file %s while deleting project %s",
                file_uuid,
                project_id,
                exc_info=True,
            )

    return schemas.Project.model_validate(existing_project)
