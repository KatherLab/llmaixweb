import csv
import datetime
import io
import json
import re
from typing import Any, List, cast

import pandas as pd
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload
from thefuzz import fuzz

from .... import models, schemas
from ....core.config import settings
from ....core.security import get_current_user
from ....dependencies import get_db, get_file, remove_file, save_file
from ....utils.enums import FileCreator, FileType, PreprocessingStrategy
from ....utils.helpers import extract_field_types_from_schema
from ....utils.info_extraction import (
    get_available_models,
    test_api_connection,
    test_llm_connection,
)

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
    # You could extend this with a project_members table for shared projects
    raise HTTPException(
        status_code=403, detail=f"Not authorized to {permission} this project"
    )


@router.get("/", response_model=list[schemas.Project])
def get_projects(
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.Project]:
    if current_user.role == "admin":
        projects = list(db.execute(select(models.Project)).scalars().all())
    else:
        projects = list(
            db.execute(
                select(models.Project).where(models.Project.owner_id == current_user.id)
            )
            .scalars()
            .all()
        )
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


@router.get("/{project_id}/file", response_model=list[schemas.File])
def get_project_files(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_creator: FileCreator | None = Query(None),
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.File]:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's files"
        )
    query = select(models.File).where(models.File.project_id == project_id)
    if file_creator is not None:
        query = query.where(models.File.file_creator == file_creator)
    files = list(db.execute(query).scalars().all())
    return [schemas.File.model_validate(file) for file in files]


@router.get("/{project_id}/file/{file_id}", response_model=schemas.File)
def get_project_file(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.File:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's files"
        )

    file: models.File | None = db.execute(
        select(models.File).where(
            models.File.project_id == project_id, models.File.id == file_id
        )
    ).scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return schemas.File.model_validate(file)


@router.get("/{project_id}/file/{file_id}/content", response_class=Response)
def get_project_file_content(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_id: int,
    preview: bool = Query(False),
    current_user: models.User = Depends(get_current_user),
) -> Response:
    """Retrieve the content of a file associated with a project."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's files"
        )

    file: models.File | None = db.execute(
        select(models.File).where(
            models.File.project_id == project_id, models.File.id == file_id
        )
    ).scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Retrieve the file content from storage
    file_content = get_file(file.file_uuid)

    if preview:
        headers = {"Content-Disposition": f"inline; filename={file.file_name}"}
    else:
        headers = {"Content-Disposition": f"attachment; filename={file.file_name}"}
    return Response(content=file_content, media_type=file.file_type, headers=headers)


@router.post("/{project_id}/file", response_model=schemas.File)
def upload_file(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file: UploadFile = File(...),
    file_info: str = Form(...),
    current_user: models.User = Depends(get_current_user),
) -> schemas.File:
    try:
        file_info = schemas.FileCreate.model_validate_json(file_info)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in file_info")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to upload files to this project"
        )

    # Read MIME type from the uploaded file
    file_info.file_type = (
        file.content_type if not file_info.file_type else file_info.file_type
    )

    # Save the file content to the storage using the generated file_uuid
    file_uuid = save_file(file.file.read())
    new_file = models.File(
        **file_info.model_dump(exclude={"file_uuid"}),
        project_id=project_id,
        file_uuid=file_uuid,
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return schemas.File.model_validate(new_file)


@router.delete("/{project_id}/file/{file_id}", response_model=schemas.File)
def delete_file(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.File:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete files from this project"
        )

    file: models.File | None = db.execute(
        select(models.File).where(
            models.File.project_id == project_id, models.File.id == file_id
        )
    ).scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Delete the file content from storage
    try:
        remove_file(file.file_uuid)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="File content not found in storage. Something went wrong. Contact the administrator.",
        )

    db.delete(file)
    db.commit()

    return schemas.File.model_validate(file)


@router.get(
    "/{project_id}/preprocessing-config",
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
    "/{project_id}/preprocessing-config/{config_id}",
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
    "/{project_id}/preprocessing-config",
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

    # Validate file type
    try:
        FileType(config.file_type)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid file type: {config.file_type}"
        )

    # Validate preprocessing strategy
    try:
        PreprocessingStrategy(config.preprocessing_strategy)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid preprocessing strategy: {config.preprocessing_strategy}",
        )

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

    db_config = models.PreprocessingConfiguration(
        **config.model_dump(), project_id=project_id
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)

    return schemas.PreprocessingConfiguration.model_validate(db_config)


@router.put(
    "/{project_id}/preprocessing-config/{config_id}",
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

    # Check if configuration is in use
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

    # Update fields
    in_use = (
        db.query(models.Document)
        .filter(models.Document.preprocessing_config_id == config.id)
        .count()
        > 0
    )
    if in_use:
        allowed_fields = {"name", "description"}
        for field, value in config_update.model_dump(exclude_unset=True).items():
            if field not in allowed_fields:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot edit a configuration in use by existing documents (except name/description)",
                )
            setattr(config, field, value)
    else:
        # Proceed as before for unused configs
        for field, value in config_update.model_dump(exclude_unset=True).items():
            setattr(config, field, value)

    db.commit()
    db.refresh(config)

    return schemas.PreprocessingConfiguration.model_validate(config)


@router.delete("/{project_id}/preprocessing-config/{config_id}")
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


@router.post("/{project_id}/preprocess", response_model=schemas.PreprocessingTask)
def preprocess_project_data(
    *,
    project_id: int,
    preprocessing_task: schemas.PreprocessingTaskCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    """Start preprocessing with advanced duplicate detection and progress tracking."""
    check_project_access(project_id, current_user, db, "write")

    # Validate configuration
    if preprocessing_task.configuration_id:
        config = db.get(
            models.PreprocessingConfiguration, preprocessing_task.configuration_id
        )
        if not config or config.project_id != project_id:
            raise HTTPException(status_code=404, detail="Configuration not found")
    elif preprocessing_task.inline_config:
        # Create temporary configuration from inline config
        config_dict = preprocessing_task.inline_config.model_dump()
        config = models.PreprocessingConfiguration(
            project_id=project_id,
            name=config_dict.pop(
                "name", f"Temp config {datetime.datetime.now(datetime.UTC)}"
            ),
            **config_dict,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    else:
        raise HTTPException(
            status_code=400,
            detail="Either configuration_id or inline_config must be provided",
        )

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

    # Validate file types match configuration
    for file in files:
        if (
            not config.file_type == FileType.MIXED.value
            and config.file_type != file.file_type
        ):
            raise HTTPException(
                status_code=400,
                detail=f"File {file.file_name} has type {file.file_type} but configuration expects {config.file_type}",
            )

    # Create preprocessing task
    task = models.PreprocessingTask(
        project_id=project_id,
        configuration_id=config.id,
        total_files=len(files),
        rollback_on_cancel=preprocessing_task.rollback_on_cancel,
    )
    db.add(task)
    db.commit()

    # Check for duplicates and create file tasks
    file_tasks_to_process = []

    for file in files:
        # Check for existing documents with same configuration (FK!)
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
            continue

        # Delete existing documents if force reprocess
        if existing_docs and preprocessing_task.force_reprocess:
            for doc in existing_docs:
                doc.document_sets.clear()
                db.delete(doc)

        file_task = models.FilePreprocessingTask(
            preprocessing_task_id=task.id, file_id=file.id
        )
        db.add(file_task)
        file_tasks_to_process.append(file_task)

    db.commit()

    if not file_tasks_to_process:
        task.status = models.PreprocessingStatus.COMPLETED
        task.message = "All files already processed with these settings"
        task.completed_at = datetime.datetime.now(datetime.UTC)
        db.commit()
        db.refresh(task)
        return schemas.PreprocessingTask.model_validate(task)

    # Start processing
    if preprocessing_task.bypass_celery:
        from ....utils.preprocessing import process_files_with_config

        try:
            process_files_with_config(task.id, db)
        except Exception as e:
            task.status = models.PreprocessingStatus.FAILED
            task.message = f"Processing failed: {str(e)}"
            db.commit()
            raise HTTPException(status_code=500, detail=str(e))
    else:
        from ....celery.preprocessing import process_files_async

        result = process_files_async.delay(task.id)
        task.celery_task_id = result.id
        db.commit()

    db.refresh(task)
    return schemas.PreprocessingTask.model_validate(task)


@router.get("/{project_id}/preprocess", response_model=List[schemas.PreprocessingTask])
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


@router.get(
    "/{project_id}/preprocess/{task_id}", response_model=schemas.PreprocessingTask
)
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


@router.post("/{project_id}/preprocess/{task_id}/cancel")
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

    task = db.execute(
        select(models.PreprocessingTask).where(
            models.PreprocessingTask.id == task_id,
            models.PreprocessingTask.project_id == project_id,
        )
    ).scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in [
        models.PreprocessingStatus.COMPLETED,
        models.PreprocessingStatus.CANCELLED,
    ]:
        raise HTTPException(
            status_code=400, detail=f"Cannot cancel task in {task.status} status"
        )

    # Cancel celery task if exists
    if task.celery_task_id:
        from celery.result import AsyncResult

        try:
            AsyncResult(task.celery_task_id).revoke(terminate=True)
        except Exception as e:
            # Log error but continue
            print(f"Error revoking celery task: {e}")

    # Update task status
    task.is_cancelled = True
    task.status = models.PreprocessingStatus.CANCELLED
    task.completed_at = datetime.datetime.now(datetime.UTC)

    # Handle rollback
    if not keep_processed and task.rollback_on_cancel:
        # Delete documents created by this task
        deleted_count = 0
        for file_task in task.file_tasks:
            if file_task.status == models.PreprocessingStatus.COMPLETED:
                for doc in file_task.documents:
                    # Remove from document sets first
                    doc.document_sets.clear()
                    db.delete(doc)
                    deleted_count += 1
        task.message = (
            f"Task cancelled and {deleted_count} processed documents rolled back"
        )
    else:
        task.message = "Task cancelled, keeping processed documents"

    # Update file task statuses
    for file_task in task.file_tasks:
        if file_task.status in [
            models.PreprocessingStatus.PENDING,
            models.PreprocessingStatus.IN_PROGRESS,
        ]:
            file_task.status = models.PreprocessingStatus.CANCELLED

    db.commit()
    db.refresh(task)

    return schemas.PreprocessingTask.model_validate(task)


@router.get("/{project_id}/preprocess/{task_id}/progress")
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


@router.get("/{project_id}/preprocess/{task_id}/retry-failed")
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


@router.get("/{project_id}/document", response_model=List[schemas.Document])
def get_documents(
    *,
    project_id: int,
    file_id: str | None = Query(None, description="Filter by original file"),
    preprocessing_task_id: int | None = Query(
        None, description="Filter by preprocessing task"
    ),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[schemas.Document]:
    """Get documents for a project with optional filtering."""
    check_project_access(project_id, current_user, db, "read")

    query = select(models.Document).where(models.Document.project_id == project_id)

    if file_id:
        query = query.where(models.Document.original_file_id == file_id)

    if preprocessing_task_id:
        query = query.join(models.FilePreprocessingTask).where(
            models.FilePreprocessingTask.preprocessing_task_id == preprocessing_task_id
        )

    query = query.order_by(models.Document.created_at.desc())
    query = query.limit(limit).offset(offset)

    documents = db.execute(query).scalars().all()
    return [schemas.Document.model_validate(doc) for doc in documents]


@router.get("/{project_id}/document/{document_id}", response_model=schemas.Document)
def get_document(
    *,
    project_id: int,
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Document:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's documents"
        )

    document: models.Document | None = db.execute(
        select(models.Document).where(
            models.Document.project_id == project_id,
            models.Document.id == document_id,
        )
    ).scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return schemas.Document.model_validate(document)


@router.delete("/{project_id}/document/{document_id}")
def delete_document(
    *,
    project_id: int,
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a specific document."""
    check_project_access(project_id, current_user, db, "write")

    document = db.execute(
        select(models.Document).where(
            models.Document.id == document_id, models.Document.project_id == project_id
        )
    ).scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if document is part of any document sets
    if document.document_sets:
        raise HTTPException(
            status_code=400,
            detail=f"Document is part of {len(document.document_sets)} document sets. Remove from sets first.",
        )

    # Delete preprocessed file if exists and not used by other documents
    if document.preprocessed_file_id:
        other_docs_using_file = db.execute(
            select(models.Document).where(
                models.Document.preprocessed_file_id == document.preprocessed_file_id,
                models.Document.id != document_id,
            )
        ).scalar_one_or_none()

        if not other_docs_using_file:
            # Safe to delete preprocessed file
            preprocessed_file = db.get(models.File, document.preprocessed_file_id)
            if preprocessed_file:
                try:
                    from ....dependencies import remove_file

                    remove_file(preprocessed_file.file_uuid)
                    db.delete(preprocessed_file)
                except Exception as e:
                    # Log error but continue
                    print(f"Error deleting preprocessed file: {e}")

    db.delete(document)
    db.commit()

    return {"detail": "Document deleted successfully"}


@router.post("/{project_id}/schema", response_model=schemas.Schema)
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


@router.get("/{project_id}/schema", response_model=list[schemas.Schema])
def get_schemas(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
        db.execute(select(models.Schema).where(models.Schema.project_id == project_id))
        .scalars()
        .all()
    )
    return [schemas.Schema.model_validate(schema) for schema in schemas_list]


@router.get("/{project_id}/schema/{schema_id}", response_model=schemas.Schema)
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


@router.put("/{project_id}/schema/{schema_id}", response_model=schemas.Schema)
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


@router.delete("/{project_id}/schema/{schema_id}", response_model=schemas.Schema)
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
    trial: models.Trial | None = db.execute(
        select(models.Trial).where(models.Trial.schema_id == schema_id)
    ).scalar_one_or_none()
    if trial:
        raise HTTPException(
            status_code=400, detail="Cannot delete schema referenced by a trial"
        )

    db.delete(schema)
    db.commit()
    return schemas.Schema.model_validate(schema)


@router.post("/{project_id}/trial", response_model=schemas.Trial)
def create_trial(
    project_id: int,
    trial: schemas.TrialCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Trial:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to create trials for this project"
        )

    # Check if the schema exists
    schema: models.Schema | None = db.execute(
        select(models.Schema).where(models.Schema.id == trial.schema_id)
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Check if the documents exist and belong to the project
    existing_documents = (
        db.execute(
            select(models.Document.id).where(models.Document.project_id == project_id)
        )
        .scalars()
        .all()
    )
    for document_id in trial.document_ids:
        if document_id not in existing_documents:
            raise HTTPException(
                status_code=404,
                detail=f"Document with id {document_id} not found in project {project_id}",
            )

    # Use default values from config if not provided
    llm_model = trial.llm_model or settings.OPENAI_API_MODEL
    api_key = trial.api_key or settings.OPENAI_API_KEY
    base_url = trial.base_url or settings.OPENAI_API_BASE

    if llm_model is None or api_key is None or base_url is None:
        raise HTTPException(status_code=400, detail="LLM configuration is incomplete")

    # Create the trial
    trial_db = models.Trial(
        **trial.model_dump(exclude={"llm_model", "api_key", "base_url"}),
        project_id=project_id,
        llm_model=llm_model,
        api_key=api_key,
        base_url=base_url,
    )

    db.add(trial_db)
    db.commit()
    db.refresh(trial_db)

    if trial.bypass_celery:
        from ....utils.info_extraction import extract_info

        try:
            extract_info(
                trial_id=trial_db.id,
                document_ids=trial.document_ids,
                llm_model=llm_model,
                api_key=api_key,
                base_url=base_url,
                schema_id=trial.schema_id,
                db_session=db,
                project_id=project_id,
            )
        except Exception as e:
            db.delete(trial_db)
            db.commit()
            raise HTTPException(
                status_code=500, detail="Information extraction failed: " + str(e)
            )
    else:
        from ....celery import info_extraction
        from ....celery.celery_config import celery_app

        if celery_app is not None:
            info_extraction.extract_info_celery.delay(  # type: ignore
                trial_id=trial_db.id,
                document_ids=trial.document_ids,
                llm_model=trial.llm_model,
                api_key=trial.api_key,
                base_url=trial.base_url,
                schema_id=trial.schema_id,
                project_id=project_id,
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Celery task for information extraction is not available.",
            )

    return schemas.Trial.model_validate(trial_db)


@router.delete("/{project_id}/trial/{trial_id}", response_model=schemas.Trial)
def delete_trial(
    project_id: int,
    trial_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Trial:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete trials for this project"
        )

    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.project_id == project_id, models.Trial.id == trial_id
        )
    ).scalar_one_or_none()

    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    # Check if the trial has results
    results = (
        db.execute(
            select(models.TrialResult).where(models.TrialResult.trial_id == trial_id)
        )
        .scalars()
        .all()
    )
    if results:
        raise HTTPException(
            status_code=400, detail="Cannot delete trial with existing results"
        )

    db.delete(trial)
    db.commit()

    return schemas.Trial.model_validate(trial)


@router.get("/{project_id}/trial", response_model=list[schemas.Trial])
def get_trials(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.Trial]:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's trials"
        )

    trials = list(
        db.execute(select(models.Trial).where(models.Trial.project_id == project_id))
        .scalars()
        .all()
    )
    return [schemas.Trial.model_validate(trial) for trial in trials]


@router.get("/{project_id}/trial/{trial_id}", response_model=schemas.Trial)
def get_trial(
    project_id: int,
    trial_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Trial:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's trials"
        )

    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.project_id == project_id, models.Trial.id == trial_id
        )
    ).scalar_one_or_none()

    if trial:
        trial.results = cast(
            list[models.TrialResult],
            (
                db.execute(
                    select(models.TrialResult).where(
                        models.TrialResult.trial_id == trial_id
                    )
                )
                .scalars()
                .all()
            ),
        )

    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return schemas.Trial.model_validate(trial)


@router.get("/{project_id}/trial/{trial_id}/download", response_class=Response)
def download_trial_results(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    trial_id: int,
    format: str = Query("json", enum=["json", "csv"]),
    include_content: bool = Query(True),
    current_user: models.User = Depends(get_current_user),
) -> Response:
    """Download trial results in specified format."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's trials"
        )
    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.project_id == project_id, models.Trial.id == trial_id
        )
    ).scalar_one_or_none()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    # Get trial results
    results = list(
        db.execute(
            select(models.TrialResult).where(models.TrialResult.trial_id == trial_id)
        )
        .scalars()
        .all()
    )
    if not results:
        raise HTTPException(status_code=404, detail="No results found for this trial")
    # Handle different format types
    if format == "json":
        # For JSON, create a JSON file for each document result
        import io
        import zipfile

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            added_files = set()
            for i, result in enumerate(results):
                # Get document content if needed
                document: models.Document | None = db.execute(
                    select(models.Document).where(
                        models.Document.id == result.document_id
                    )
                ).scalar_one_or_none()
                if not document:
                    continue

                # Create result data
                result_data = {
                    "result": result.result,
                    "metadata": {
                        "trial_id": trial.id,
                        "document_id": result.document_id,
                        "created_at": result.created_at.isoformat(),
                    },
                }
                if include_content:
                    result_data["content"] = document.text
                    # Add preprocessed or original file to zip
                    file_id = document.preprocessed_file_id or document.original_file_id
                    file: models.File | None = db.execute(
                        select(models.File).where(models.File.id == file_id)
                    ).scalar_one_or_none()
                    if file and file_id not in added_files:
                        added_files.add(file_id)
                        file_content = get_file(file.file_uuid)
                        file_path = f"files/{file.file_uuid}_{file.file_name}"
                        zipf.writestr(file_path, file_content)

                # Add to ZIP
                zipf.writestr(
                    f"document_{result.document_id}.json",
                    json.dumps(result_data, indent=2),
                )
        zip_buffer.seek(0)
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=trial_{trial_id}_results.zip"
            },
        )
    elif format == "csv":
        # For CSV, flatten the structure
        import csv
        import io
        import zipfile

        if include_content:
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Extract all keys from all results to create CSV columns
                all_keys = set()
                for result in results:
                    all_keys.update(_extract_keys(result.result))
                # Sort keys
                all_keys = sorted(list(all_keys))
                # Create header row
                header = ["document_id", "trial_id", "created_at"]
                header.append("document_content")
                header.extend(all_keys)
                csv_output = io.StringIO()
                writer = csv.DictWriter(csv_output, fieldnames=header)
                writer.writeheader()
                added_files = set()
                # Write data rows
                for result in results:
                    row = {
                        "document_id": result.document_id,
                        "trial_id": trial.id,
                        "created_at": result.created_at.isoformat(),
                    }
                    # Add document content if needed
                    document: models.Document | None = db.execute(
                        select(models.Document).where(
                            models.Document.id == result.document_id
                        )
                    ).scalar_one_or_none()
                    row["document_content"] = document.text if document else ""
                    # Add preprocessed or original file to zip
                    if document:
                        file_id = (
                            document.preprocessed_file_id or document.original_file_id
                        )
                        file: models.File | None = db.execute(
                            select(models.File).where(models.File.id == file_id)
                        ).scalar_one_or_none()
                        if file and file_id not in added_files:
                            added_files.add(file_id)
                            file_content = get_file(file.file_uuid)
                            file_path = f"files/{file.file_uuid}_{file.file_name}"
                            zipf.writestr(file_path, file_content)

                    # Add flattened result data
                    flattened = _flatten_dict(result.result)
                    for key, value in flattened.items():
                        row[key] = value
                    writer.writerow(row)
                zipf.writestr("results.csv", csv_output.getvalue())
            output.seek(0)
            return Response(
                content=output.getvalue(),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename=trial_{trial_id}_results.zip"
                },
            )
        else:
            output = io.StringIO()
            # Extract all keys from all results to create CSV columns
            all_keys = set()
            for result in results:
                all_keys.update(_extract_keys(result.result))
            # Sort keys
            all_keys = sorted(list(all_keys))
            # Create header row
            header = ["document_id", "trial_id", "created_at"]
            header.extend(all_keys)
            writer = csv.DictWriter(output, fieldnames=header)
            writer.writeheader()
            # Write data rows
            for result in results:
                row = {
                    "document_id": result.document_id,
                    "trial_id": trial.id,
                    "created_at": result.created_at.isoformat(),
                }
                # Add flattened result data
                flattened = _flatten_dict(result.result)
                for key, value in flattened.items():
                    row[key] = value
                writer.writerow(row)
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=trial_{trial_id}_results.csv"
                },
            )

    raise HTTPException(status_code=404, detail="No results found for this trial")


def _flatten_dict(d, parent_key="", sep="_"):
    """Flatten a nested dictionary."""
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(_flatten_dict(v, new_key, sep=sep))
        else:
            items[new_key] = v
    return items


def _extract_keys(d, parent_key="", sep="_"):
    """Extract all keys from a nested dictionary."""
    keys = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            keys.extend(_extract_keys(v, new_key, sep=sep))
        else:
            keys.append(new_key)
    return keys


@router.get("/llm/models", response_model=dict[str, Any])
def get_available_llm_models(
    api_key: str | None = settings.OPENAI_API_KEY,
    base_url: str | None = settings.OPENAI_API_BASE,
) -> dict[str, Any]:
    if api_key is None or base_url is None:
        return {
            "success": False,
            "models": [],
            "message": "LLM configuration is incomplete",
            "error_type": "incomplete_config",
        }
    return get_available_models(api_key, base_url)


@router.post("/llm/test-connection", response_model=dict[str, Any])
def test_api_connection_endpoint(
    api_key: str | None = settings.OPENAI_API_KEY,
    base_url: str | None = settings.OPENAI_API_BASE,
) -> dict[str, Any]:
    if api_key is None or base_url is None:
        return {
            "success": False,
            "message": "LLM configuration is incomplete. Please provide API key and base URL.",
            "error_type": "incomplete_config",
        }
    return test_api_connection(api_key, base_url)


@router.post("/llm/test-model", response_model=dict[str, Any])
def test_llm_model_endpoint(
    api_key: str | None = settings.OPENAI_API_KEY,
    base_url: str | None = settings.OPENAI_API_BASE,
    llm_model: str | None = settings.OPENAI_API_MODEL,
) -> dict[str, Any]:
    if api_key is None or base_url is None or llm_model is None:
        return {
            "success": False,
            "message": "LLM configuration is incomplete. Please provide API key, base URL, and model.",
            "error_type": "incomplete_config",
        }
    return test_llm_connection(api_key, base_url, llm_model)


# Add these endpoints to your existing projects.py file
@router.post("/{project_id}/groundtruth", response_model=schemas.GroundTruth)
def upload_groundtruth(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file: UploadFile = File(...),
    name: str = Form(None),
    format: str = Form(...),  # 'json', 'csv', 'xlsx', 'zip'
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    """Upload ground truth file for evaluation."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to upload ground truth to this project",
        )
    # Validate format
    if format not in ["json", "csv", "xlsx", "zip"]:
        raise HTTPException(
            status_code=400, detail="Invalid format. Must be json, csv, xlsx, or zip"
        )
    # Save the file
    file_content = file.file.read()
    file_uuid = save_file(file_content)
    # Create ground truth record
    gt = models.GroundTruth(
        project_id=project_id,
        name=name or file.filename,
        format=format,
        file_uuid=file_uuid,
    )
    db.add(gt)
    db.commit()
    db.refresh(gt)
    return schemas.GroundTruth.model_validate(gt)


@router.get(
    "/{project_id}/groundtruth/{groundtruth_id}", response_model=schemas.GroundTruth
)
def get_groundtruth(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    """Get a specific ground truth file."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's ground truth",
        )

    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()

    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    return schemas.GroundTruth.model_validate(groundtruth)


@router.delete(
    "/{project_id}/groundtruth/{groundtruth_id}", response_model=schemas.GroundTruth
)
def delete_groundtruth(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    """Delete a ground truth file."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this project's ground truth",
        )

    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()

    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Delete the file content from storage
    try:
        remove_file(groundtruth.file_uuid)
    except FileNotFoundError:
        # Continue deletion even if file not found in storage
        pass

    # Remove any evaluations using this ground truth
    evaluations = (
        db.execute(
            select(models.Evaluation).where(
                models.Evaluation.groundtruth_id == groundtruth_id
            )
        )
        .scalars()
        .all()
    )

    for evaluation in evaluations:
        db.delete(evaluation)

    db.delete(groundtruth)
    db.commit()

    return schemas.GroundTruth.model_validate(groundtruth)


@router.get("/{project_id}/groundtruth", response_model=list[schemas.GroundTruth])
def get_groundtruth_files(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.GroundTruth]:
    """Get all ground truth files for a project."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's ground truth files",
        )
    ground_truths = list(
        db.execute(
            select(models.GroundTruth).where(
                models.GroundTruth.project_id == project_id
            )
        )
        .scalars()
        .all()
    )
    return [schemas.GroundTruth.model_validate(gt) for gt in ground_truths]


@router.put(
    "/{project_id}/groundtruth/{groundtruth_id}", response_model=schemas.GroundTruth
)
def update_groundtruth(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    file: UploadFile = File(None),
    name: str = Form(None),
    comparison_options: str = Form(None),
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this project's ground truth",
        )

    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()

    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    if name:
        groundtruth.name = name

    if comparison_options:
        try:
            groundtruth.comparison_options = json.loads(comparison_options)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid comparison options JSON"
            )

    if file:
        try:
            remove_file(groundtruth.file_uuid)
        except FileNotFoundError:
            pass

        file_content = file.file.read()
        file_uuid = save_file(file_content)
        groundtruth.file_uuid = file_uuid

        evaluations = (
            db.execute(
                select(models.Evaluation).where(
                    models.Evaluation.groundtruth_id == groundtruth_id
                )
            )
            .scalars()
            .all()
        )
        for evaluation in evaluations:
            db.delete(evaluation)

    groundtruth.updated_at = func.now()
    db.add(groundtruth)
    db.commit()
    db.refresh(groundtruth)

    return schemas.GroundTruth.model_validate(groundtruth)


@router.post(
    "/{project_id}/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping",
    response_model=schemas.GroundTruth,
)
def configure_field_mapping(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    mappings: list[schemas.FieldMappingCreate] = Body(...),
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    """Configure field mappings for a specific groundtruth-schema combination."""
    # Validate project access
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to configure field mappings"
        )

    # Validate groundtruth exists
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Validate schema exists
    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id,
            models.Schema.id == schema_id,
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Delete existing mappings for this groundtruth-schema combination
    db.execute(
        delete(models.FieldMapping).where(
            models.FieldMapping.ground_truth_id == groundtruth_id,
            models.FieldMapping.schema_id == schema_id,
        )
    )

    # Create new mappings
    for mapping_data in mappings:
        mapping = models.FieldMapping(
            ground_truth_id=groundtruth_id, **mapping_data.model_dump()
        )
        db.add(mapping)

    # Invalidate evaluations for this specific groundtruth-schema combination
    db.execute(
        delete(models.Evaluation).where(
            models.Evaluation.groundtruth_id == groundtruth_id,
            models.Evaluation.trial_id.in_(
                select(models.Trial.id).where(models.Trial.schema_id == schema_id)
            ),
        )
    )

    db.commit()
    db.refresh(groundtruth)
    return schemas.GroundTruth.model_validate(groundtruth)


@router.get("/{project_id}/schema/{schema_id}/field_types", response_model=dict)
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


@router.get("/{project_id}/evaluation", response_model=list[schemas.Evaluation])
def get_evaluations(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int = Query(...),
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.Evaluation]:
    """Get evaluation results for all trials using a specific ground truth."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )

    # Verify ground truth exists for this project
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()

    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Get all evaluations for this ground truth
    evaluations = list(
        db.execute(
            select(models.Evaluation).where(
                models.Evaluation.groundtruth_id == groundtruth_id
            )
        )
        .scalars()
        .all()
    )

    return [schemas.Evaluation.model_validate(eval) for eval in evaluations]


@router.get(
    "/{project_id}/evaluation/{evaluation_id}", response_model=schemas.EvaluationDetail
)
def get_evaluation_detail(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.EvaluationDetail:
    """Get detailed evaluation for a specific trial/ground truth pair."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )

    evaluation: models.Evaluation | None = db.execute(
        select(models.Evaluation).where(models.Evaluation.id == evaluation_id)
    ).scalar_one_or_none()

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Ensure the evaluation belongs to a trial in this project
    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.id == evaluation.trial_id,
            models.Trial.project_id == project_id,
        )
    ).scalar_one_or_none()

    if not trial:
        raise HTTPException(
            status_code=404, detail="Evaluation not found for this project"
        )

    # Get detailed evaluation data
    evaluation_detail = schemas.EvaluationDetail(
        id=evaluation.id,
        trial_id=evaluation.trial_id,
        groundtruth_id=evaluation.groundtruth_id,
        model=trial.llm_model,
        metrics=evaluation.metrics,
        document_count=len(evaluation.document_metrics),
        fields=evaluation.field_metrics,
        documents=evaluation.document_metrics,
        created_at=evaluation.created_at,
    )

    return evaluation_detail


@router.get("/{project_id}/groundtruth/{groundtruth_id}/preview", response_model=dict)
def preview_groundtruth(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    limit: int = Query(10, description="Number of documents to preview"),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Preview ground truth data and field structure."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's ground truth",
        )
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")
    # Load ground truth data
    from ....utils.evaluation import EvaluationEngine

    engine = EvaluationEngine(db)
    gt_data = engine._load_ground_truth(groundtruth)
    # Get field structure
    all_fields = set()
    field_types = {}
    sample_values = {}
    for doc_id, fields in list(gt_data.items())[:limit]:
        for field, value in fields.items():
            all_fields.add(field)
            # Infer field type
            if field not in field_types:
                if isinstance(value, bool):
                    field_types[field] = "boolean"
                elif isinstance(value, (int, float)):
                    field_types[field] = "number"
                elif isinstance(value, str):
                    # Check if it's a date
                    if re.match(r"\d{4}-\d{2}-\d{2}", value):
                        field_types[field] = "date"
                    else:
                        field_types[field] = "string"
                else:
                    field_types[field] = "string"
            # Collect sample values
            if field not in sample_values:
                sample_values[field] = []
            if value not in sample_values[field] and len(sample_values[field]) < 5:
                sample_values[field].append(value)
    return {
        "document_count": len(gt_data),
        "fields": list(all_fields),
        "field_types": field_types,
        "sample_values": sample_values,
        "preview_data": dict(list(gt_data.items())[:limit]),
    }


@router.post(
    "/{project_id}/groundtruth/{groundtruth_id}/mapping",
    response_model=schemas.GroundTruth,
)
def configure_field_mapping_legacy(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    mappings: list[schemas.FieldMappingCreate] = Body(...),
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    """Configure field mappings for ground truth evaluation."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to configure ground truth mappings"
        )
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")
    # Delete existing mappings
    db.execute(
        delete(models.FieldMapping).where(
            models.FieldMapping.ground_truth_id == groundtruth_id
        )
    )
    # Create new mappings
    for mapping_data in mappings:
        mapping = models.FieldMapping(
            ground_truth_id=groundtruth_id, **mapping_data.model_dump()
        )
        db.add(mapping)
    # Invalidate existing evaluations
    db.execute(
        delete(models.Evaluation).where(
            models.Evaluation.groundtruth_id == groundtruth_id
        )
    )
    db.commit()
    db.refresh(groundtruth)
    return schemas.GroundTruth.model_validate(groundtruth)


@router.get(
    "/{project_id}/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping",
    response_model=list[schemas.FieldMapping],
)
def get_field_mappings(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.FieldMapping]:
    """Get field mappings for a specific groundtruth-schema combination."""
    # Validate project access
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access field mappings"
        )

    # Validate groundtruth exists
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Validate schema exists
    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id,
            models.Schema.id == schema_id,
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Get mappings for this groundtruth-schema combination
    mappings = (
        db.execute(
            select(models.FieldMapping).where(
                models.FieldMapping.ground_truth_id == groundtruth_id,
                models.FieldMapping.schema_id == schema_id,
            )
        )
        .scalars()
        .all()
    )

    return [schemas.FieldMapping.model_validate(mapping) for mapping in mappings]


@router.delete(
    "/{project_id}/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping",
    response_model=dict,
)
def delete_field_mappings(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Delete all field mappings for a specific groundtruth-schema combination."""
    # Validate project access
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete field mappings"
        )

    # Validate groundtruth exists
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Validate schema exists
    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id,
            models.Schema.id == schema_id,
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Delete mappings for this groundtruth-schema combination
    deleted_count = db.execute(
        delete(models.FieldMapping).where(
            models.FieldMapping.ground_truth_id == groundtruth_id,
            models.FieldMapping.schema_id == schema_id,
        )
    ).rowcount

    # Invalidate related evaluations
    db.execute(
        delete(models.Evaluation).where(
            models.Evaluation.groundtruth_id == groundtruth_id,
            models.Evaluation.trial_id.in_(
                select(models.Trial.id).where(models.Trial.schema_id == schema_id)
            ),
        )
    )

    db.commit()

    return {"deleted_mappings": deleted_count}


@router.get(
    "/{project_id}/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping/suggest",
    response_model=list[schemas.FieldMapping],
)
def suggest_field_mappings(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.FieldMapping]:
    """Suggest field mappings based on schema and ground truth."""
    # Validate project access
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project"
        )

    # Get schema
    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id, models.Schema.id == schema_id
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Get ground truth
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Load ground truth data
    from ....utils.evaluation import EvaluationEngine

    engine = EvaluationEngine(db)
    gt_data = engine._load_ground_truth(groundtruth)

    # Extract schema fields
    schema_fields = {}
    extract_field_types_from_schema(schema.schema_definition, schema_fields)

    # Get ground truth fields
    gt_fields = set()
    for fields in gt_data.values():
        gt_fields.update(fields.keys())

    # Suggest mappings
    suggestions = []
    for schema_field, field_type in schema_fields.items():
        # Try exact match
        if schema_field in gt_fields:
            suggestions.append(
                {
                    "id": 0,
                    "ground_truth_id": groundtruth_id,
                    "schema_id": schema_id,
                    "schema_field": schema_field,
                    "ground_truth_field": schema_field,
                    "field_type": field_type,
                    "comparison_method": _get_comparison_method(field_type),
                    "confidence": 1.0,
                }
            )
            continue

        # Try fuzzy matching
        best_match = None
        best_score = 0
        for gt_field in gt_fields:
            score = fuzz.ratio(schema_field.lower(), gt_field.lower())
            if score > best_score and score > 70:
                best_score = score
                best_match = gt_field

        if best_match:
            suggestions.append(
                {
                    "id": 0,
                    "ground_truth_id": groundtruth_id,
                    "schema_id": schema_id,
                    "schema_field": schema_field,
                    "ground_truth_field": best_match,
                    "field_type": field_type,
                    "comparison_method": _get_comparison_method(field_type),
                    "confidence": best_score / 100.0,
                }
            )

    return suggestions


def _get_comparison_method(field_type: str) -> str:
    """Get default comparison method for field type."""
    type_to_method = {
        "boolean": "boolean",
        "number": "numeric",
        "date": "date",
        "category": "category",
        "string": "exact",
    }
    return type_to_method.get(field_type, "exact")


@router.post(
    "/{project_id}/trial/{trial_id}/evaluate", response_model=schemas.EvaluationSummary
)
def evaluate_trial(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    trial_id: int,
    groundtruth_id: int = Query(...),
    force_recalculate: bool = Query(False),
    current_user: models.User = Depends(get_current_user),
) -> schemas.EvaluationSummary:
    """Evaluate a trial against ground truth with comprehensive error handling."""

    # Validate project access
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to evaluate trials for this project"
        )

    # Verify trial exists and belongs to project
    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.project_id == project_id, models.Trial.id == trial_id
        )
    ).scalar_one_or_none()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    # Verify ground truth exists and belongs to project
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Pre-validation checks
    from ....utils.evaluation import EvaluationEngine

    engine = EvaluationEngine(db)

    try:
        validation_result = engine._validate_evaluation_prerequisites(
            trial_id, groundtruth_id
        )
        if not validation_result["valid"]:
            # Provide detailed error information
            error_details = {
                "message": "Cannot evaluate trial due to validation errors",
                "errors": validation_result["errors"],
                "suggestions": [],
            }

            # Add specific suggestions based on error types
            for error in validation_result["errors"]:
                if "No field mappings configured" in error:
                    error_details["suggestions"].append(
                        "Configure field mappings between your ground truth data and schema fields"
                    )
                elif "No results found" in error:
                    error_details["suggestions"].append(
                        "Ensure the trial has completed successfully and produced results"
                    )
                elif "documents have matching ground truth" in error:
                    error_details["suggestions"].append(
                        "Check that your ground truth file contains keys that match your document IDs or filenames"
                    )

            raise HTTPException(status_code=400, detail=error_details)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")

    # Run evaluation
    try:
        evaluation = engine.evaluate_trial(
            trial_id=trial_id,
            groundtruth_id=groundtruth_id,
            force_recalculate=force_recalculate,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

    # Build enhanced summary with error information
    field_summaries = []
    for field_name, metrics in evaluation.field_metrics.items():
        # Calculate error count
        error_count = sum(metrics.get("error_distribution", {}).values())

        # Get sample errors
        sample_errors = []
        error_details = (
            db.query(models.EvaluationMetric)
            .filter(
                models.EvaluationMetric.evaluation_id == evaluation.id,
                models.EvaluationMetric.field_name == field_name,
                ~models.EvaluationMetric.is_correct,
            )
            .limit(5)
            .all()
        )
        for detail in error_details:
            sample_errors.append(
                {
                    "document_id": detail.document_id,
                    "ground_truth": detail.ground_truth_value,
                    "predicted": detail.predicted_value,
                    "error_type": detail.error_type,
                }
            )

        field_summaries.append(
            schemas.FieldEvaluationSummary(
                field_name=field_name,
                accuracy=metrics.get("accuracy", 0),
                total_count=metrics.get("total_count", 0),
                correct_count=metrics.get("correct_count", 0),
                error_distribution=metrics.get("error_distribution", {}),
                sample_errors=sample_errors,
                error_count=error_count,
            )
        )

    # Build document summaries with enhanced error information
    document_summaries = []
    total_errors = 0
    error_documents = []

    for doc_metrics in evaluation.document_metrics:
        doc_id = doc_metrics["document_id"]

        # Check if this document had errors
        has_error = "error" in doc_metrics
        if has_error:
            total_errors += 1
            error_documents.append(doc_id)

        # Get document name
        document = db.query(models.Document).get(doc_id)
        document_name = None
        if document and document.original_file:
            document_name = document.original_file.file_name

        # Get field details
        field_details = {}
        details = (
            db.query(models.EvaluationMetric)
            .filter(
                models.EvaluationMetric.evaluation_id == evaluation.id,
                models.EvaluationMetric.document_id == doc_id,
            )
            .all()
        )
        for detail in details:
            field_details[detail.field_name] = schemas.EvaluationMetricDetail(
                document_id=doc_id,
                field_name=detail.field_name,
                ground_truth_value=detail.ground_truth_value,
                predicted_value=detail.predicted_value,
                is_correct=detail.is_correct,
                error_type=detail.error_type,
                confidence_score=detail.confidence_score,
            )

        document_summary = schemas.DocumentEvaluationDetail(
            document_id=doc_id,
            accuracy=doc_metrics.get("accuracy", 0.0),
            correct_fields=doc_metrics.get("correct_fields", 0),
            total_fields=doc_metrics.get("total_fields", 0),
            missing_fields=doc_metrics.get("missing_fields", []),
            incorrect_fields=doc_metrics.get("incorrect_fields", []),
            field_details=field_details,
            has_error=has_error,
            document_name=document_name,
        )

        # Add error information if present
        if has_error:
            document_summary.error = doc_metrics["error"]

        document_summaries.append(document_summary)

    return schemas.EvaluationSummary(
        id=evaluation.id,
        trial_id=evaluation.trial_id,
        groundtruth_id=evaluation.groundtruth_id,
        overall_metrics=evaluation.metrics,
        field_summaries=field_summaries,
        document_summaries=document_summaries,
        confusion_matrices=evaluation.confusion_matrices,
        created_at=evaluation.created_at,
        total_errors=total_errors,
        error_documents=error_documents,
    )


@router.get(
    "/{project_id}/evaluation/{evaluation_id}/document/{document_id}",
    response_model=schemas.DocumentEvaluationDetail,
)
def get_document_evaluation(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_id: int,
    document_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.DocumentEvaluationDetail:
    """Get detailed evaluation for a single document."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )
    # Get evaluation
    evaluation: models.Evaluation | None = db.execute(
        select(models.Evaluation).where(models.Evaluation.id == evaluation_id)
    ).scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    # Verify evaluation belongs to project
    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.id == evaluation.trial_id,
            models.Trial.project_id == project_id,
        )
    ).scalar_one_or_none()
    if not trial:
        raise HTTPException(
            status_code=404, detail="Evaluation not found for this project"
        )
    # Find document metrics
    doc_metrics = None
    for metrics in evaluation.document_metrics:
        if metrics["document_id"] == document_id:
            doc_metrics = metrics
            break
    if not doc_metrics:
        raise HTTPException(status_code=404, detail="Document not found in evaluation")
    # Get detailed metrics
    field_details = {}
    details = (
        db.query(models.EvaluationMetric)
        .filter(
            models.EvaluationMetric.evaluation_id == evaluation_id,
            models.EvaluationMetric.document_id == document_id,
        )
        .all()
    )
    for detail in details:
        field_details[detail.field_name] = schemas.EvaluationMetricDetail(
            document_id=document_id,
            field_name=detail.field_name,
            ground_truth_value=detail.ground_truth_value,
            predicted_value=detail.predicted_value,
            is_correct=detail.is_correct,
            error_type=detail.error_type,
            confidence_score=detail.confidence_score,
        )
    return schemas.DocumentEvaluationDetail(
        document_id=document_id,
        accuracy=doc_metrics["accuracy"],
        correct_fields=doc_metrics["correct_fields"],
        total_fields=doc_metrics["total_fields"],
        missing_fields=doc_metrics.get("missing_fields", []),
        incorrect_fields=doc_metrics.get("incorrect_fields", []),
        field_details=field_details,
    )


@router.get("/{project_id}/evaluations/download", response_class=Response)
def download_evaluations_report(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_ids: str = Query(...),
    format: str = Query("csv", enum=["csv", "xlsx"]),
    include_details: bool = Query(True),
    current_user: models.User = Depends(get_current_user),
) -> Response:
    """Download evaluation report in CSV or Excel format."""
    try:
        evaluation_ids_list = [int(i) for i in evaluation_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid evaluation_ids")
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )
    # Get evaluations
    evaluations = []
    for eval_id in evaluation_ids_list:
        eval_obj = db.execute(
            select(models.Evaluation).where(models.Evaluation.id == eval_id)
        ).scalar_one_or_none()
        if eval_obj:
            # Verify it belongs to project
            trial = db.execute(
                select(models.Trial).where(
                    models.Trial.id == eval_obj.trial_id,
                    models.Trial.project_id == project_id,
                )
            ).scalar_one_or_none()
            if trial:
                evaluations.append((eval_obj, trial))
    if not evaluations:
        raise HTTPException(status_code=404, detail="No evaluations found")
    # Create report data
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        # Summary sheet
        writer.writerow(
            [
                "Evaluation ID",
                "Trial ID",
                "Model",
                "Ground Truth",
                "Accuracy",
                "Precision",
                "Recall",
                "F1 Score",
                "Total Documents",
                "Total Fields",
                "Created At",
            ]
        )
        for eval, trial in evaluations:
            gt = db.query(models.GroundTruth).get(eval.groundtruth_id)
            writer.writerow(
                [
                    eval.id,
                    eval.trial_id,
                    trial.llm_model,
                    gt.name if gt else "Unknown",
                    eval.metrics.get("accuracy", 0),
                    eval.metrics.get("precision", 0),
                    eval.metrics.get("recall", 0),
                    eval.metrics.get("f1_score", 0),
                    eval.metrics.get("total_documents", 0),
                    eval.metrics.get("total_fields", 0),
                    eval.created_at.isoformat(),
                ]
            )
        if include_details:
            writer.writerow([])  # Empty row
            writer.writerow(["Field-Level Metrics"])
            writer.writerow(
                [
                    "Evaluation ID",
                    "Field Name",
                    "Accuracy",
                    "Total Count",
                    "Correct Count",
                ]
            )
            for eval, _ in evaluations:
                for field, metrics in eval.field_metrics.items():
                    writer.writerow(
                        [
                            eval.id,
                            field,
                            metrics.get("accuracy", 0),
                            metrics.get("total_count", 0),
                            metrics.get("correct_count", 0),
                        ]
                    )
        content = output.getvalue()
        media_type = "text/csv"
        filename = f"evaluation_report_{project_id}.csv"
    else:  # xlsx
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            # Summary sheet
            summary_data = []
            for eval, trial in evaluations:
                gt = db.query(models.GroundTruth).get(eval.groundtruth_id)
                summary_data.append(
                    {
                        "Evaluation ID": eval.id,
                        "Trial ID": eval.trial_id,
                        "Model": trial.llm_model,
                        "Ground Truth": gt.name if gt else "Unknown",
                        "Accuracy": eval.metrics.get("accuracy", 0),
                        "Precision": eval.metrics.get("precision", 0),
                        "Recall": eval.metrics.get("recall", 0),
                        "F1 Score": eval.metrics.get("f1_score", 0),
                        "Total Documents": eval.metrics.get("total_documents", 0),
                        "Total Fields": eval.metrics.get("total_fields", 0),
                        "Created At": eval.created_at.isoformat(),
                    }
                )
            pd.DataFrame(summary_data).to_excel(
                writer, sheet_name="Summary", index=False
            )
            if include_details:
                # Field metrics sheet
                field_data = []
                for eval, _ in evaluations:
                    for field, metrics in eval.field_metrics.items():
                        field_data.append(
                            {
                                "Evaluation ID": eval.id,
                                "Field Name": field,
                                "Accuracy": metrics.get("accuracy", 0),
                                "Total Count": metrics.get("total_count", 0),
                                "Correct Count": metrics.get("correct_count", 0),
                            }
                        )
                pd.DataFrame(field_data).to_excel(
                    writer, sheet_name="Field Metrics", index=False
                )
                # Document metrics sheet
                doc_data = []
                for eval, _ in evaluations:
                    for doc_metrics in eval.document_metrics:
                        doc_data.append(
                            {
                                "Evaluation ID": eval.id,
                                "Document ID": doc_metrics["document_id"],
                                "Accuracy": doc_metrics["accuracy"],
                                "Correct Fields": doc_metrics["correct_fields"],
                                "Total Fields": doc_metrics["total_fields"],
                            }
                        )
                pd.DataFrame(doc_data).to_excel(
                    writer, sheet_name="Document Metrics", index=False
                )
        output.seek(0)
        content = output.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"evaluation_report_{project_id}.xlsx"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/{project_id}/evaluation/batch", response_model=list[schemas.EvaluationSummary]
)
def batch_evaluate_trials(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    trial_ids: list[int] = Body(...),
    groundtruth_id: int = Body(...),
    force_recalculate: bool = Body(False),
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.EvaluationSummary]:
    """Evaluate multiple trials against ground truth."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to evaluate trials for this project"
        )
    # Verify ground truth
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")
    # Evaluate trials
    from ....utils.evaluation import EvaluationEngine

    engine = EvaluationEngine(db)
    results = []
    errors = []
    for trial_id in trial_ids:
        try:
            # Verify trial exists
            trial: models.Trial | None = db.execute(
                select(models.Trial).where(
                    models.Trial.project_id == project_id, models.Trial.id == trial_id
                )
            ).scalar_one_or_none()
            if not trial:
                errors.append(f"Trial {trial_id} not found")
                continue
            evaluation = engine.evaluate_trial(
                trial_id=trial_id,
                groundtruth_id=groundtruth_id,
                force_recalculate=force_recalculate,
            )
            # Build summary (same as single evaluation)
            # ... (same summary building code as above)
            results.append(evaluation)
        except Exception as e:
            errors.append(f"Error evaluating trial {trial_id}: {str(e)}")
    if errors and not results:
        raise HTTPException(
            status_code=400, detail=f"All evaluations failed: {'; '.join(errors)}"
        )
    return results


@router.get("/{project_id}/evaluation/compare", response_model=dict)
def compare_evaluations(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_ids: list[int] = Query(...),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Compare multiple evaluations side by side."""

    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )

    # Get evaluations
    evaluations = []
    for eval_id in evaluation_ids:
        eval_obj = db.execute(
            select(models.Evaluation).where(models.Evaluation.id == eval_id)
        ).scalar_one_or_none()

        if eval_obj:
            # Verify it belongs to project
            trial = db.execute(
                select(models.Trial).where(
                    models.Trial.id == eval_obj.trial_id,
                    models.Trial.project_id == project_id,
                )
            ).scalar_one_or_none()

            if trial:
                evaluations.append({"evaluation": eval_obj, "trial": trial})

    if not evaluations:
        raise HTTPException(status_code=404, detail="No evaluations found")

    # Build comparison
    comparison = {
        "evaluations": [],
        "overall_comparison": {},
        "field_comparison": {},
        "model_comparison": {},
    }

    # Collect all fields
    all_fields = set()
    for eval_data in evaluations:
        eval = eval_data["evaluation"]
        all_fields.update(eval.field_metrics.keys())

    # Build evaluation summaries
    for eval_data in evaluations:
        eval = eval_data["evaluation"]
        trial = eval_data["trial"]

        comparison["evaluations"].append(
            {
                "id": eval.id,
                "trial_id": eval.trial_id,
                "model": trial.llm_model,
                "groundtruth_id": eval.groundtruth_id,
                "metrics": eval.metrics,
                "created_at": eval.created_at.isoformat(),
            }
        )

    # Compare overall metrics
    metrics_to_compare = ["accuracy", "precision", "recall", "f1_score"]
    for metric in metrics_to_compare:
        comparison["overall_comparison"][metric] = []
        for eval_data in evaluations:
            eval = eval_data["evaluation"]
            trial = eval_data["trial"]
            comparison["overall_comparison"][metric].append(
                {
                    "evaluation_id": eval.id,
                    "model": trial.llm_model,
                    "value": eval.metrics.get(metric, 0),
                }
            )

    # Compare field metrics
    for field in sorted(all_fields):
        comparison["field_comparison"][field] = []
        for eval_data in evaluations:
            eval = eval_data["evaluation"]
            trial = eval_data["trial"]
            field_metric = eval.field_metrics.get(field, {})
            comparison["field_comparison"][field].append(
                {
                    "evaluation_id": eval.id,
                    "model": trial.llm_model,
                    "accuracy": field_metric.get("accuracy", 0),
                    "total_count": field_metric.get("total_count", 0),
                    "correct_count": field_metric.get("correct_count", 0),
                }
            )

    # Group by model
    model_groups = {}
    for eval_data in evaluations:
        eval = eval_data["evaluation"]
        trial = eval_data["trial"]
        model = trial.llm_model

        if model not in model_groups:
            model_groups[model] = []
        model_groups[model].append(eval.metrics.get("accuracy", 0))

    comparison["model_comparison"] = {
        model: {
            "average_accuracy": sum(accuracies) / len(accuracies),
            "evaluation_count": len(accuracies),
            "min_accuracy": min(accuracies),
            "max_accuracy": max(accuracies),
        }
        for model, accuracies in model_groups.items()
    }

    return comparison


@router.get(
    "/{project_id}/evaluation/{evaluation_id}/errors", response_model=list[dict]
)
def get_evaluation_errors(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    evaluation_id: int,
    field_name: str | None = Query(None),
    error_type: str | None = Query(None),
    limit: int = Query(100),
    current_user: models.User = Depends(get_current_user),
) -> list[dict]:
    """Get detailed error analysis for an evaluation."""

    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's evaluations",
        )

    # Get evaluation
    evaluation: models.Evaluation | None = db.execute(
        select(models.Evaluation).where(models.Evaluation.id == evaluation_id)
    ).scalar_one_or_none()

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Verify evaluation belongs to project
    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.id == evaluation.trial_id,
            models.Trial.project_id == project_id,
        )
    ).scalar_one_or_none()

    if not trial:
        raise HTTPException(
            status_code=404, detail="Evaluation not found for this project"
        )

    # Get errors from detailed metrics
    query = db.query(models.EvaluationMetric).filter(
        models.EvaluationMetric.evaluation_id == evaluation_id,
        ~models.EvaluationMetric.is_correct,
    )

    if field_name:
        query = query.filter(models.EvaluationMetric.field_name == field_name)

    if error_type:
        query = query.filter(models.EvaluationMetric.error_type == error_type)

    errors = query.limit(limit).all()

    # Build error details
    error_details = []
    for error in errors:
        # Get document info
        document = db.query(models.Document).get(error.document_id)

        error_detail = {
            "document_id": error.document_id,
            "document_name": document.original_file.file_name
            if document and document.original_file
            else "Unknown",
            "field_name": error.field_name,
            "ground_truth_value": error.ground_truth_value,
            "predicted_value": error.predicted_value,
            "error_type": error.error_type,
            "confidence_score": error.confidence_score,
        }

        # Add context if available
        if document:
            # Extract surrounding text for context
            text_snippet = document.text[:500] if document.text else ""
            error_detail["context"] = text_snippet

        error_details.append(error_detail)

    return error_details


@router.post(
    "/{project_id}/groundtruth/{groundtruth_id}/schema/{schema_id}/auto-map",
    response_model=dict,
)
def auto_map_fields(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    confidence_threshold: float = Body(0.7),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Automatically map ground truth fields to schema fields."""
    # Validate project access
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project"
        )

    # Get schema and ground truth
    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id, models.Schema.id == schema_id
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Load ground truth data
    from ....utils.evaluation import EvaluationEngine

    engine = EvaluationEngine(db)
    gt_data = engine._load_ground_truth(groundtruth)

    # Extract schema fields
    schema_fields = {}
    extract_field_types_from_schema(schema.schema_definition, schema_fields)

    # Get ground truth fields and sample values
    gt_fields = {}
    for doc_id, fields in list(gt_data.items())[:10]:  # Sample first 10 docs
        for field, value in fields.items():
            if field not in gt_fields:
                gt_fields[field] = []
            if value not in gt_fields[field] and len(gt_fields[field]) < 5:
                gt_fields[field].append(value)

    # Auto-map fields
    from ....utils.field_mapping import FieldMapper

    mapper = FieldMapper()
    mappings = mapper.auto_map(
        schema_fields=schema_fields,
        ground_truth_fields=gt_fields,
        confidence_threshold=confidence_threshold,
    )

    # Delete existing mappings for this groundtruth-schema combination
    db.execute(
        delete(models.FieldMapping).where(
            models.FieldMapping.ground_truth_id == groundtruth_id,
            models.FieldMapping.schema_id == schema_id,
        )
    )

    # Apply mappings
    applied_count = 0
    for mapping in mappings:
        if mapping["confidence"] >= confidence_threshold:
            field_mapping = models.FieldMapping(
                ground_truth_id=groundtruth_id,
                schema_id=schema_id,
                schema_field=mapping["schema_field"],
                ground_truth_field=mapping["ground_truth_field"],
                field_type=mapping["field_type"],
                comparison_method=mapping["comparison_method"],
                comparison_options=mapping.get("comparison_options", {}),
            )
            db.add(field_mapping)
            applied_count += 1

    # Invalidate existing evaluations for this groundtruth-schema combination
    db.execute(
        delete(models.Evaluation).where(
            models.Evaluation.groundtruth_id == groundtruth_id,
            models.Evaluation.trial_id.in_(
                select(models.Trial.id).where(models.Trial.schema_id == schema_id)
            ),
        )
    )

    db.commit()

    return {
        "total_schema_fields": len(schema_fields),
        "total_ground_truth_fields": len(gt_fields),
        "suggested_mappings": len(mappings),
        "applied_mappings": applied_count,
        "mappings": mappings,
    }


@router.get(
    "/{project_id}/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping/status",
    response_model=dict,
)
def check_mapping_status(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Check if field mappings exist for a groundtruth-schema combination."""
    # Validate project access
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project"
        )

    # Validate groundtruth and schema exist
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id,
            models.Schema.id == schema_id,
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Check mapping status
    mapping_count = db.execute(
        select(func.count(models.FieldMapping.id)).where(
            models.FieldMapping.ground_truth_id == groundtruth_id,
            models.FieldMapping.schema_id == schema_id,
        )
    ).scalar()

    # Get schema field count
    schema_fields = {}
    extract_field_types_from_schema(schema.schema_definition, schema_fields)
    schema_field_count = len(schema_fields)

    return {
        "has_mappings": mapping_count > 0,
        "mapping_count": mapping_count,
        "schema_field_count": schema_field_count,
        "mapping_complete": mapping_count == schema_field_count,
        "groundtruth_name": groundtruth.name,
        "schema_name": schema.schema_name,
    }
