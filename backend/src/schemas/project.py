from __future__ import annotations

from pydantic import BaseModel
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User  # noqa: F401


class ProjectBase(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    owner_id: str | None = None


class ProjectCreate(ProjectBase):
    name: str


class ProjectUpdate(ProjectBase):
    name: str


class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    owner: User | None = None  # noqa: F821

    class Config:
        from_attributes = True


class FileBase(BaseModel):
    file_name: str | None = None
    file_type: str | None = None
    file_storage_type: str | None = None
    description: str | None = None


class FileCreate(FileBase):
    file_name: str


class File(FileBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    preprocessing_method: str | None = None
    text: str | None = None
    metadata: str | None = None


class DocumentCreate(DocumentBase):
    original_file_id: int
    text: str


class Document(DocumentBase):
    id: int
    project_id: int
    original_file_id: int
    preprocessed_file_id: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentSetBase(BaseModel):
    pass


class DocumentSetCreate(DocumentSetBase):
    trial_id: int


class DocumentSet(DocumentSetBase):
    id: int
    project_id: int
    trial_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SchemaBase(BaseModel):
    schema_name: str | None = None
    schema_definition: dict | None = None


class SchemaCreate(SchemaBase):
    schema_name: str
    schema_definition: dict


class Schema(SchemaBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrialBase(BaseModel):
    prompt: str | None = None
    model: str | None = None
    trial_name: str | None = None
    trial_description: str | None = None


class TrialCreate(TrialBase):
    schema_id: int
    prompt: str
    model: str
    trial_name: str


class Trial(TrialBase):
    id: int
    project_id: int
    schema_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrialResultBase(BaseModel):
    result: dict | None = None


class TrialResultCreate(TrialResultBase):
    result: dict


class TrialResult(TrialResultBase):
    id: int
    trial_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


from .user import User  # noqa: E402, F401

Project.model_rebuild()
