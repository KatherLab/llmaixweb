from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict, SkipValidation, field_validator

from ..core.config import settings
from ..utils.enums import FileCreator

if TYPE_CHECKING:
    from .user import User  # noqa: F401


class ProjectBase(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    owner_id: int | None = None


class ProjectCreate(ProjectBase):
    name: str


class ProjectUpdate(ProjectBase):
    name: str


class Project(ProjectBase):
    id: int
    owner: Annotated[User, SkipValidation] | None = None
    documents: list[Document] = []

    model_config = ConfigDict(from_attributes=True)


class FileBase(BaseModel):
    file_name: str | None = None
    file_type: str | None = None
    file_uuid: str | None = None
    file_storage_type: str | None = None
    description: str | None = None


class FileCreate(FileBase):
    file_name: str


class File(FileBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
    file_creator: FileCreator = FileCreator.user

    model_config = ConfigDict(from_attributes=True)


class DocumentBase(BaseModel):
    preprocessing_method: str | None = None
    text: str | None = None
    meta_data: dict | None = None


class DocumentCreate(DocumentBase):
    original_file_id: int
    text: str


class Document(DocumentBase):
    id: int
    project_id: int
    original_file_id: int
    original_file: File | None = None
    preprocessed_file_id: int | None = None
    preprocessed_file: File | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class SchemaBase(BaseModel):
    schema_name: str | None = None
    schema_definition: dict | None = None


class SchemaCreate(SchemaBase):
    schema_name: str
    schema_definition: dict


class SchemaUpdate(SchemaBase):
    schema_name: str | None = None
    schema_definition: dict | None = None


class Schema(SchemaBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrialBase(BaseModel):
    schema_id: int
    document_ids: list[int]
    llm_model: str | None = settings.OPENAI_API_MODEL
    api_key: str | None = settings.OPENAI_API_KEY
    base_url: str | None = settings.OPENAI_API_BASE
    bypass_celery: bool = False


class TrialCreate(TrialBase):
    pass


class Trial(TrialBase):
    id: int
    project_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    results: list[TrialResult] = []
    model_config = ConfigDict(from_attributes=True)


class TrialResultBase(BaseModel):
    result: dict | None = None


class TrialResultCreate(TrialResultBase):
    result: dict


class TrialResult(TrialResultBase):
    id: int
    trial_id: int
    document_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PreprocessingTaskBase(BaseModel):
    status: str | None = None
    message: str | None = None
    progress: float | None = None
    progress_details: dict | None = None
    celery_id: str | None = None
    bypass_celery: bool = False
    file_ids: list[int] = []
    document_ids: list[int] = []
    ocr_backend: str | None = None
    pdf_backend: str | None = None
    use_ocr: bool = True
    force_ocr: bool = False
    ocr_languages: list[str] | None = None
    ocr_model: str | None = None
    llm_model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


class PreprocessingTaskCreate(PreprocessingTaskBase):
    @field_validator("file_ids")
    def file_ids_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("At least one file ID must be provided for preprocessing")
        return v

    @field_validator("ocr_languages")
    def ocr_languages_must_be_list(cls, v):
        if v and not isinstance(v, list):
            raise ValueError("OCR languages must be a list of language codes")
        return v

    @field_validator("pdf_backend")
    def pdf_backend_must_be_valid(cls, v):
        valid_backends = ["pymupdf4llm", "markitdown"]  # Add valid backends here
        if v and v not in valid_backends:
            raise ValueError(
                f"Invalid PDF backend: {v}. Valid backends are: {valid_backends}"
            )
        return v

    @field_validator("ocr_backend")
    def ocr_backend_must_be_valid(cls, v):
        valid_backends = ["ocrmypdf"]  # Add valid backends here
        if v and v not in valid_backends:
            raise ValueError(
                f"Invalid OCR backend: {v}. Valid backends are: {valid_backends}"
            )
        return v

    @field_validator("force_ocr")
    def force_ocr_must_be_used_with_use_ocr(cls, v, info):
        if v and info.data.get("use_ocr") is False:
            raise ValueError(
                "force_ocr is True, but use_ocr is False. Set use_ocr=True."
            )
        return v

    @field_validator("llm_model", "api_key")
    def llm_model_and_api_key_must_be_provided_together(cls, v, info):
        if info.field_name == "llm_model" and v and not info.data.get("api_key"):
            raise ValueError("Both LLM model and API key must be provided together")
        if info.field_name == "api_key" and v and not info.data.get("llm_model"):
            raise ValueError("Both LLM model and API key must be provided together")
        return v


class PreprocessingTaskUpdate(PreprocessingTaskBase):
    pass


class PreprocessingTask(PreprocessingTaskBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
    files: list[File] | None = None
    documents: list[Document] | None = None

    model_config = ConfigDict(from_attributes=True)


class EvaluationBase(BaseModel):
    trial_id: int
    groundtruth_id: int
    metrics: dict
    field_metrics: dict
    document_metrics: list


class EvaluationCreate(EvaluationBase):
    pass


class Evaluation(EvaluationBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationDetail(BaseModel):
    id: int
    trial_id: int
    groundtruth_id: int
    model: str
    metrics: dict
    document_count: int
    fields: dict
    documents: list
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FieldMappingBase(BaseModel):
    schema_field: str
    ground_truth_field: str
    schema_id: int
    field_type: str = "string"
    comparison_method: str = "exact"
    comparison_options: dict | None = None


class FieldMappingCreate(FieldMappingBase):
    pass


class FieldMapping(FieldMappingBase):
    id: int
    ground_truth_id: int
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class GroundTruthBase(BaseModel):
    name: str | None = None
    format: str | None = None


class GroundTruthCreate(GroundTruthBase):
    name: str
    format: str


class GroundTruthUpdate(BaseModel):
    name: str | None = None
    field_mappings: list[FieldMappingCreate] | None = None


class GroundTruth(GroundTruthBase):
    id: int
    project_id: int
    file_uuid: str
    field_mappings: list[FieldMapping] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EvaluationMetricDetail(BaseModel):
    document_id: int
    field_name: str
    ground_truth_value: str | None
    predicted_value: str | None
    is_correct: bool
    error_type: str | None
    confidence_score: float | None


# Enhanced DocumentEvaluationDetail with error handling
class DocumentEvaluationDetail(BaseModel):
    document_id: int
    accuracy: float
    correct_fields: int
    total_fields: int
    missing_fields: list[str]
    incorrect_fields: list[str]
    field_details: dict[str, EvaluationMetricDetail]
    # Add error handling fields
    error: str | None = None
    has_error: bool = False
    document_name: str | None = None


class FieldEvaluationSummary(BaseModel):
    field_name: str
    accuracy: float
    total_count: int
    correct_count: int
    error_distribution: dict[str, int]
    sample_errors: list[dict]
    # Add error count for frontend
    error_count: int | None = None


# Enhanced EvaluationSummary with better error handling
class EvaluationSummary(BaseModel):
    id: int
    trial_id: int
    groundtruth_id: int
    overall_metrics: dict
    field_summaries: list[FieldEvaluationSummary]
    document_summaries: list[DocumentEvaluationDetail]
    confusion_matrices: dict | None
    created_at: datetime
    # Add summary error information
    total_errors: int | None = None
    error_documents: list[int] | None = None


# Add new schema for error details
class EvaluationError(BaseModel):
    document_id: int
    document_name: str | None
    error_message: str
    error_type: str
    field_name: str | None = None
    ground_truth_value: str | None = None
    predicted_value: str | None = None
    context: str | None = None


class EvaluationErrorSummary(BaseModel):
    evaluation_id: int
    total_errors: int
    error_types: dict[str, int]
    affected_documents: int
    errors: list[EvaluationError]


from .user import User  # noqa: E402, F401

Project.model_rebuild()
