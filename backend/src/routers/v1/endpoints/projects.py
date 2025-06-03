from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .... import models, schemas
from ....core.security import get_current_user
from ....dependencies import get_db, save_file, get_file, remove_file
from ....celery.preprocessing import preprocess_data

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
    new_project = models.Project(**project.model_dump(), owner_id=current_user.id)
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
    file_content = get_file(str(file.id))

    headers = {"Content-Disposition": f"attachment; filename={file.file_name}"}

    return Response(content=file_content, media_type=file.file_type, headers=headers)


@router.post("/{project_id}/file", response_model=schemas.File)
def upload_file(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file: UploadFile = File(...),
    file_info: schemas.FileCreate,
    current_user: models.User = Depends(get_current_user),
) -> schemas.File:
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

    new_file = models.File(**file_info.model_dump(), project_id=project_id)
    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    # Save the file content to the storage using the File object's id
    save_file(str(new_file.id), file.file.read())

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
        remove_file(str(file.id))
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
    db: Session = Depends(get_db),
    project_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.PreprocessingTask:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to preprocess this project"
        )

    preprocessing_task = models.PreprocessingTask(project_id=project_id)
    db.add(preprocessing_task)
    db.commit()
    db.refresh(preprocessing_task)

    preprocess_data.delay(preprocessing_task.id)

    return schemas.PreprocessingTask.model_validate(preprocessing_task)
