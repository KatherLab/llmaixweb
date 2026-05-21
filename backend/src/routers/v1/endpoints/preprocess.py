"""Preprocessing task endpoints for projects."""

import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

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


async def get_admin_user(current_user: models.User) -> bool:
    """Check if user is admin."""
    return current_user.role == "admin"


@router.post("/preprocess", response_model=schemas.PreprocessingTask)
async def preprocess_project_data(
    *,
    project_id: int,
    preprocessing_task: schemas.PreprocessingTaskCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    """Start preprocessing with advanced duplicate detection and progress tracking."""
    check_project_access(project_id, current_user, db, "write")

    if not preprocessing_task.inline_config:
        raise HTTPException(
            status_code=400,
            detail="inline_config is required",
        )

    # Create configuration from inline config
    config_dict = preprocessing_task.inline_config.model_dump(exclude={"bypass_celery"})
    config = models.PreprocessingConfiguration(
        project_id=project_id,
        name=config_dict.get("name", f"Task {datetime.datetime.now(datetime.UTC)}"),
        description=config_dict.get("description"),
        additional_settings=config_dict.get("additional_settings"),
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    # Validate files exist and belong to project
    files = (
        db.execute(
            select(models.File).where(
                models.File.id.in_(preprocessing_task.file_ids),
                models.File.project_id == project_id,
            )
        )
        .scalars()
        .all()
    )
    if len(files) != len(preprocessing_task.file_ids):
        missing_ids = set(preprocessing_task.file_ids) - {f.id for f in files}
        raise HTTPException(
            status_code=404,
            detail=f"Files not found or don't belong to project: {missing_ids}",
        )

    # Create preprocessing task
    task = models.PreprocessingTask(
        project_id=project_id,
        configuration_id=config.id,
        total_files=len(files),
        rollback_on_cancel=preprocessing_task.rollback_on_cancel,
    )

    # Store API credentials in task metadata if provided
    if preprocessing_task.api_key and preprocessing_task.base_url:
        task.task_metadata = {
            "custom_api_used": True,
            "api_base_url": preprocessing_task.base_url,
            # Don't store the actual API key for security
        }

    db.add(task)
    db.commit()

    # Check for duplicates and create file tasks
    file_tasks_to_process = []
    skipped_files = 0
    skipped_file_names = []

    for file in files:
        # Check for existing documents with same configuration
        existing_docs = (
            db.execute(
                select(models.Document).where(
                    models.Document.original_file_id == file.id,
                    models.Document.preprocessing_config_id == config.id,
                )
            )
            .scalars()
            .all()
        )

        if existing_docs and not preprocessing_task.force_reprocess:
            # Skip this file
            task.processed_files += 1
            skipped_files += 1
            skipped_file_names.append(file.file_name)
            continue

        # Delete existing documents if force reprocess
        if existing_docs and preprocessing_task.force_reprocess:
            for doc in existing_docs:
                doc.document_sets.clear()
                db.delete(doc)

        file_task = models.FilePreprocessingTask(
            preprocessing_task_id=task.id,
            file_id=file.id,
            file_name=file.file_name,  # Set file name immediately
        )
        db.add(file_task)
        file_tasks_to_process.append(file_task)

    db.commit()

    # Update task with skipped files information
    if skipped_files > 0:
        if not task.task_metadata:
            task.task_metadata = {}
        task.task_metadata["skipped_files"] = skipped_files
        task.task_metadata["skipped_file_names"] = skipped_file_names
        task.skipped_files = skipped_files

    if not file_tasks_to_process:
        task.status = models.PreprocessingStatus.COMPLETED
        task.message = f"All files already processed with these settings. {skipped_files} files skipped."
        task.completed_at = datetime.datetime.now(datetime.UTC)
        db.commit()
        db.refresh(task)
        return schemas.PreprocessingTask.model_validate(task)

    # Set initial message
    if skipped_files > 0:
        task.message = f"Processing {len(file_tasks_to_process)} files. {skipped_files} files already processed and skipped."

    bypass_celery = getattr(preprocessing_task, "bypass_celery", False)
    inline_cfg = getattr(preprocessing_task, "inline_config", None)
    if inline_cfg:
        if hasattr(inline_cfg, "bypass_celery"):
            bypass_celery = getattr(inline_cfg, "bypass_celery", False)
        elif isinstance(inline_cfg, dict):
            bypass_celery = inline_cfg.get("bypass_celery", False)

    # 2. Only check admin if someone tried to set bypass_celery
    if bypass_celery:
        if not await get_admin_user(current_user):
            # Not an admin, so do not allow bypass
            bypass_celery = False
            # Optionally, raise error instead:
            raise HTTPException(403, "Only admins may set bypass_celery")

    # Start processing
    if bypass_celery:
        print("Bypassing Celery for preprocessing task")
        from ....utils.preprocessing import PreprocessingPipeline

        try:
            # Pass API credentials to pipeline
            pipeline = PreprocessingPipeline(
                db,
                task.id,
                api_key=preprocessing_task.api_key,
                base_url=preprocessing_task.base_url,
            )
            pipeline.process()
        except Exception as e:
            task.status = models.PreprocessingStatus.FAILED
            task.message = f"Processing failed: {str(e)}"
            db.commit()
            raise HTTPException(status_code=500, detail=str(e))
    else:
        from ....celery.preprocessing import process_files_async

        # Pass credentials through celery
        result = process_files_async.delay(
            task.id,
            api_key=preprocessing_task.api_key,
            base_url=preprocessing_task.base_url,
        )
        task.celery_task_id = result.id
        db.commit()

    db.commit()
    db.refresh(task)
    return schemas.PreprocessingTask.model_validate(task)


@router.get("/preprocess", response_model=List[schemas.PreprocessingTask])
def get_preprocessing_tasks(
    *,
    project_id: int,
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[schemas.PreprocessingTask]:
    """Get preprocessing tasks for a project."""
    check_project_access(project_id, current_user, db, "read")

    query = (
        select(models.PreprocessingTask)
        .where(models.PreprocessingTask.project_id == project_id)
        .options(
            selectinload(models.PreprocessingTask.file_tasks).selectinload(
                models.FilePreprocessingTask.file
            ),
            selectinload(models.PreprocessingTask.configuration),
        )
    )

    if status:
        try:
            status_enum = models.PreprocessingStatus(status)
            query = query.where(models.PreprocessingTask.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    query = query.order_by(models.PreprocessingTask.created_at.desc())
    query = query.limit(limit).offset(offset)

    tasks = db.execute(query).scalars().all()
    return [schemas.PreprocessingTask.model_validate(task) for task in tasks]


@router.get("/preprocess/{task_id}", response_model=schemas.PreprocessingTask)
def get_preprocessing_task(
    *,
    project_id: int,
    task_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    """Get detailed information about a preprocessing task."""
    check_project_access(project_id, current_user, db, "read")

    task = db.execute(
        select(models.PreprocessingTask)
        .where(
            models.PreprocessingTask.id == task_id,
            models.PreprocessingTask.project_id == project_id,
        )
        .options(
            selectinload(models.PreprocessingTask.file_tasks).selectinload(
                models.FilePreprocessingTask.file
            ),
            selectinload(models.PreprocessingTask.configuration),
        )
    ).scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return schemas.PreprocessingTask.model_validate(task)


@router.post(
    "/preprocess/{task_id}/cancel",
    response_model=schemas.PreprocessingTask,
)
def cancel_preprocessing_task(
    *,
    project_id: int,
    task_id: int,
    keep_processed: bool = Query(False, description="Keep already processed files"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    """Cancel a preprocessing task with option to keep or rollback processed files."""

    check_project_access(project_id, current_user, db, "write")

    task = (
        db.query(models.PreprocessingTask)
        .filter(
            models.PreprocessingTask.id == task_id,
            models.PreprocessingTask.project_id == project_id,
        )
        .first()
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in [
        models.PreprocessingStatus.COMPLETED,
        models.PreprocessingStatus.CANCELLED,
    ]:
        raise HTTPException(
            status_code=400, detail=f"Cannot cancel task in {task.status} status"
        )

    # Set cancellation flag
    task.is_cancelled = True
    task.status = models.PreprocessingStatus.CANCELLED
    task.completed_at = datetime.datetime.now(datetime.UTC)

    # Rollback logic: remove processed docs if requested
    if not keep_processed and task.rollback_on_cancel:
        deleted_count = 0
        for file_task in task.file_tasks:
            if file_task.status == models.PreprocessingStatus.COMPLETED:
                for doc in file_task.documents:
                    doc.document_sets.clear()
                    db.delete(doc)
                    deleted_count += 1
        task.message = (
            f"Task cancelled and {deleted_count} processed documents rolled back"
        )
    else:
        task.message = "Task cancelled, keeping processed documents"

    # Mark all still-pending/in-progress file tasks as cancelled
    for file_task in task.file_tasks:
        if file_task.status in [
            models.PreprocessingStatus.PENDING,
            models.PreprocessingStatus.IN_PROGRESS,
        ]:
            file_task.status = models.PreprocessingStatus.CANCELLED
            file_task.completed_at = datetime.datetime.now(datetime.UTC)

    db.commit()
    db.refresh(task)

    return schemas.PreprocessingTask.model_validate(task)


@router.get("/preprocess/{task_id}/progress")
def get_preprocessing_progress(
    *,
    project_id: int,
    task_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    """Get detailed progress of a preprocessing task."""
    check_project_access(project_id, current_user, db, "read")

    task = db.execute(
        select(models.PreprocessingTask).where(
            models.PreprocessingTask.id == task_id,
            models.PreprocessingTask.project_id == project_id,
        )
    ).scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Calculate estimated completion time if in progress
    if (
        task.status == models.PreprocessingStatus.IN_PROGRESS
        and task.processed_files > 0
    ):
        elapsed = datetime.datetime.now(datetime.UTC) - task.started_at
        avg_time_per_file = elapsed.total_seconds() / task.processed_files
        remaining_files = task.total_files - task.processed_files - task.failed_files

        if remaining_files > 0:
            estimated_remaining = datetime.timedelta(
                seconds=avg_time_per_file * remaining_files
            )
            task.estimated_completion = (
                datetime.datetime.now(datetime.UTC) + estimated_remaining
            )

    return schemas.PreprocessingTask.model_validate(task)


@router.get("/preprocess/{task_id}/retry-failed")
def retry_failed_files(
    *,
    project_id: int,
    task_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    """Create a new task to retry failed files from a previous task."""
    check_project_access(project_id, current_user, db, "write")

    original_task = db.execute(
        select(models.PreprocessingTask).where(
            models.PreprocessingTask.id == task_id,
            models.PreprocessingTask.project_id == project_id,
        )
    ).scalar_one_or_none()

    if not original_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get failed file IDs
    failed_file_ids = [
        ft.file_id
        for ft in original_task.file_tasks
        if ft.status == models.PreprocessingStatus.FAILED
    ]

    if not failed_file_ids:
        raise HTTPException(status_code=400, detail="No failed files to retry")

    # Create new task with same configuration
    new_task = models.PreprocessingTask(
        project_id=project_id,
        configuration_id=original_task.configuration_id,
        total_files=len(failed_file_ids),
        rollback_on_cancel=original_task.rollback_on_cancel,
    )
    db.add(new_task)
    db.commit()

    # Create file tasks for failed files
    for file_id in failed_file_ids:
        file_task = models.FilePreprocessingTask(
            preprocessing_task_id=new_task.id, file_id=file_id
        )
        db.add(file_task)

    db.commit()

    # Start processing
    from ....celery.preprocessing import process_files_async

    result = process_files_async.delay(new_task.id)
    new_task.celery_task_id = result.id
    db.commit()

    db.refresh(new_task)
    return schemas.PreprocessingTask.model_validate(new_task)
