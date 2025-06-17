import json

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import cast


from .... import models, schemas
from ....core.security import get_current_user
from ....dependencies import get_db, save_file, get_file, remove_file

router = APIRouter()


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


@router.get("/{project_id}/files", response_model=list[schemas.File])
def get_project_files(
    *,
    db: Session = Depends(get_db),
    project_id: int,
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

    files = list(
        db.execute(select(models.File).where(models.File.project_id == project_id))
        .scalars()
        .all()
    )

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


@router.post("/{project_id}/preprocess", response_model=schemas.PreprocessingTask)
def preprocess_project_data(
    *,
    project_id: int,
    preprocessing_task: schemas.PreprocessingTaskCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    """
    Preprocess project data.

    This endpoint initiates a preprocessing task for the specified project.

    Args:
    ----
    project_id (int): The ID of the project to preprocess.
    preprocessing_task (schemas.PreprocessingTaskCreate): The preprocessing task details.

    Returns:
    -------
    schemas.PreprocessingTask: The created preprocessing task.

    Raises:
    ------
    HTTPException: If the project is not found or the user is not authorized.
    """
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to preprocess this project"
        )
    # Check if all files in the preprocessing task exist in the project
    existing_files = (
        db.execute(select(models.File.id).where(models.File.project_id == project_id))
        .scalars()
        .all()
    )
    for file_id in preprocessing_task.file_ids:
        if file_id not in existing_files:
            raise HTTPException(
                status_code=404,
                detail=f"File with id {file_id} not found in project {project_id}",
            )
    preprocessing_task_db = models.PreprocessingTask(
        **preprocessing_task.model_dump(exclude={"base_url", "api_key"})
    )
    preprocessing_task_db.project_id = project_id
    db.add(preprocessing_task_db)
    db.commit()
    db.refresh(preprocessing_task_db)
    files = cast(
        list[models.File],
        (
            db.execute(
                select(models.File).where(
                    models.File.project_id == project_id,
                    models.File.id.in_(preprocessing_task.file_ids),
                )
            )
            .scalars()
            .all()
        ),
    )
    if preprocessing_task_db.bypass_celery:
        from ....utils.preprocessing import preprocess_files

        print("Bypassing Celery for preprocessing task, preprocess synchronously.")
        try:
            preprocess_files(
                files=files,
                pdf_backend=preprocessing_task.pdf_backend or "pymupdf4llm",
                ocr_backend=preprocessing_task.ocr_backend or "ocrmypdf",
                use_ocr=preprocessing_task.use_ocr,
                force_ocr=preprocessing_task.force_ocr,
                ocr_languages=preprocessing_task.ocr_languages,
                ocr_model=preprocessing_task.ocr_model,
                llm_model=preprocessing_task.llm_model,
                base_url=preprocessing_task.base_url,
                api_key=preprocessing_task.api_key,
                db_session=db,
                preprocessing_task_id=preprocessing_task_db.id,
                project_id=project_id,
            )
        except Exception as e:
            db.delete(preprocessing_task_db)
            db.commit()
            raise HTTPException(
                status_code=500, detail="Preprocessing failed: " + str(e)
            )
    else:
        from ....celery.preprocessing import preprocess_file_celery

        preprocess_file_celery.delay(
            files=files,
            preprocessing_task_id=preprocessing_task_db.id,
            pdf_backend=preprocessing_task.pdf_backend,
            ocr_backend=preprocessing_task.ocr_backend,
            use_ocr=preprocessing_task.use_ocr,
            force_ocr=preprocessing_task.force_ocr,
            ocr_languages=preprocessing_task.ocr_languages,
            ocr_model=preprocessing_task.ocr_model,
            llm_model=preprocessing_task.llm_model,
            base_url=preprocessing_task.base_url,
            api_key=preprocessing_task.api_key,
            db_session=db,
            project_id=project_id,
        )
    return schemas.PreprocessingTask.model_validate(preprocessing_task_db)


@router.get(
    "/{project_id}/preprocess/{preprocessing_task_id}",
    response_model=schemas.PreprocessingTask,
)
def get_preprocessing_task(
    *,
    project_id: int,
    preprocessing_task_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's preprocessing tasks",
        )

    preprocessing_task: models.PreprocessingTask | None = db.execute(
        select(models.PreprocessingTask).where(
            models.PreprocessingTask.project_id == project_id,
            models.PreprocessingTask.id == preprocessing_task_id,
        )
    ).scalar_one_or_none()
    if not preprocessing_task:
        raise HTTPException(status_code=404, detail="Preprocessing task not found")

    return schemas.PreprocessingTask.model_validate(preprocessing_task)


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
