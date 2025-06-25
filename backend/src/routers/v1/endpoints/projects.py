import json

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import cast

from .... import models, schemas
from ....core.config import settings
from ....core.security import get_current_user
from ....dependencies import get_db, save_file, get_file, remove_file
from ....utils.info_extraction import get_available_models, test_llm_connection

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


@router.get("/{project_id}/file", response_model=list[schemas.File])
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
    # TODO: Disable file loading when using celery
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
        print("Preprocess using celery task.")
        from ....celery import preprocessing
        from ....celery.celery_config import celery_app

        print("Loaded celery successfully")

        if celery_app is not None:
            preprocessing.preprocess_file_celery.delay(  # type: ignore
                file_ids=preprocessing_task.file_ids,
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
                project_id=project_id,
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Celery task for preprocessing is not available.",
            )
    return schemas.PreprocessingTask.model_validate(preprocessing_task_db)


@router.get(
    "/{project_id}/preprocess",
    response_model=list[schemas.PreprocessingTask],
)
def get_preprocessing_tasks(
    *,
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.PreprocessingTask]:
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

    preprocessing_tasks = list(
        db.execute(
            select(models.PreprocessingTask).where(
                models.PreprocessingTask.project_id == project_id
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas.PreprocessingTask.model_validate(task) for task in preprocessing_tasks
    ]


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


@router.get("/{project_id}/document", response_model=list[schemas.Document])
def get_documents(
    *,
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.Document]:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's documents"
        )

    documents = list(
        db.execute(
            select(models.Document).where(models.Document.project_id == project_id)
        )
        .scalars()
        .all()
    )
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
            info_extraction.extract_info_celery.delay( # type: ignore
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


@router.get("/llm/models", response_model=list[str])
def get_available_llm_models(
    api_key: str | None = settings.OPENAI_API_KEY,
    base_url: str | None = settings.OPENAI_API_BASE,
) -> list[str]:
    if api_key is None or base_url is None:
        raise HTTPException(status_code=400, detail="LLM configuration is incomplete")
    return get_available_models(api_key, base_url)


@router.post("/llm/test", response_model=bool)
def test_llm_connection_endpoint(
    api_key: str | None = settings.OPENAI_API_KEY,
    base_url: str | None = settings.OPENAI_API_BASE,
    llm_model: str | None = settings.OPENAI_API_MODEL,
) -> bool:
    if api_key is None or base_url is None or llm_model is None:
        raise HTTPException(status_code=400, detail="LLM configuration is incomplete")
    return test_llm_connection(api_key, base_url, llm_model)


@router.post("/{project_id}/groundtruth", response_model=schemas.GroundTruth)
def upload_groundtruth(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file: UploadFile = File(...),
    name: str = Form(None),
    format: str = Form(...),  # 'json', 'csv', or 'xlsx'
    comparison_options: str = Form(None),
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

    # Process comparison options if provided
    comp_options = {}
    if comparison_options:
        try:
            comp_options = json.loads(comparison_options)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid comparison options JSON"
            )

    # Save the file content
    file_content = file.file.read()
    file_uuid = save_file(file_content)

    # Create ground truth record
    gt = models.GroundTruth(
        project_id=project_id,
        name=name or file.filename,
        format=format,
        file_uuid=file_uuid,
        comparison_options=comp_options,
    )

    db.add(gt)
    db.commit()
    db.refresh(gt)

    return schemas.GroundTruth.model_validate(gt)


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


@router.get("/{project_id}/evaluation/download", response_class=Response)
def download_evaluation_metrics(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int = Query(...),
    current_user: models.User = Depends(get_current_user),
) -> Response:
    """Download evaluation metrics as CSV."""
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

    # Generate CSV content
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "Evaluation ID",
            "Trial ID",
            "Model",
            "Accuracy",
            "Precision",
            "Recall",
            "F1 Score",
            "Document Count",
            "Created At",
        ]
    )

    # Write data rows
    for eval in evaluations:
        trial: models.Trial | None = db.execute(
            select(models.Trial).where(models.Trial.id == eval.trial_id)
        ).scalar_one_or_none()

        model = trial.llm_model if trial else "Unknown"

        writer.writerow(
            [
                eval.id,
                eval.trial_id,
                model,
                eval.metrics.get("accuracy", "N/A"),
                eval.metrics.get("precision", "N/A"),
                eval.metrics.get("recall", "N/A"),
                eval.metrics.get("f1_score", "N/A"),
                len(eval.document_metrics),
                eval.created_at.isoformat(),
            ]
        )

    # Return CSV response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=evaluation_metrics_{project_id}.csv"
        },
    )


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
        import zipfile
        import io

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
