from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    SkipValidation,
    field_validator,
    model_validator,
)

from ..core.config import settings
from ..utils.enums import FileCreator, FileType, PreprocessingStrategy

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
    text: str
    document_name: str | None = None
    meta_data: dict | None = None
    preprocessing_config: dict


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
    preprocessing_config_id: int
    preprocessing_config: PreprocessingConfiguration | None = None
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

class PreprocessingConfigurationBase(BaseModel):
    name: str
    description: str | None = None
    file_type: str
    preprocessing_strategy: str = "full_document"
    pdf_backend: str | None = None
    ocr_backend: str | None = None
    use_ocr: bool = True
    force_ocr: bool = False
    ocr_languages: list[str] | None = None
    ocr_model: str | None = None
    table_settings: dict | None = None
    llm_model: str | None = None
    additional_settings: dict | None = None

    @field_validator("file_type")
    def validate_file_type(cls, v):
        """Convert file type string to enum value."""
        if not v:
            raise ValueError("file_type is required")

        # Map common variations to enum values
        file_type_mapping = {
            # Direct enum values
            "application/pdf": FileType.APPLICATION_PDF,
            "application/msword": FileType.APPLICATION_MSWORD,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.APPLICATION_VND_OPENXMLFORMATS_OFFICEDOCUMENT_WORDPROCESSINGML_DOCUMENT,
            "application/vnd.ms-excel": FileType.APPLICATION_VND_MS_EXCEL,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.APPLICATION_VND_OPENXMLFORMATS_OFFICEDOCUMENT_SPREADSHEETML_SHEET,
            "image/jpeg": FileType.IMAGE_JPEG,
            "image/png": FileType.IMAGE_PNG,
            "image/svg+xml": FileType.IMAGE_SVG,
            "text/plain": FileType.TEXT_PLAIN,
            "text/csv": FileType.TEXT_CSV,
            "mixed": FileType.MIXED,
            # Common aliases
            "pdf": FileType.APPLICATION_PDF,
            "word": FileType.APPLICATION_MSWORD,
            "docx": FileType.APPLICATION_VND_OPENXMLFORMATS_OFFICEDOCUMENT_WORDPROCESSINGML_DOCUMENT,
            "excel": FileType.APPLICATION_VND_MS_EXCEL,
            "xlsx": FileType.APPLICATION_VND_OPENXMLFORMATS_OFFICEDOCUMENT_SPREADSHEETML_SHEET,
            "jpg": FileType.IMAGE_JPEG,
            "jpeg": FileType.IMAGE_JPEG,
            "png": FileType.IMAGE_PNG,
            "svg": FileType.IMAGE_SVG,
            "txt": FileType.TEXT_PLAIN,
            "csv": FileType.TEXT_CSV,
        }

        # Convert to lowercase for case-insensitive matching
        v_lower = v.lower()

        # Check if it's already an enum value
        try:
            return FileType(v).value
        except ValueError:
            pass

        # Check mapping
        if v_lower in file_type_mapping:
            return file_type_mapping[v_lower].value

        # Check if it's an enum name (e.g., "APPLICATION_PDF")
        for enum_item in FileType:
            if v_lower == enum_item.name.lower():
                return enum_item.value

        raise ValueError(
            f"Invalid file type: {v}. Valid types are: {', '.join([e.value for e in FileType])}"
        )

    @field_validator("preprocessing_strategy")
    def validate_preprocessing_strategy(cls, v):
        """Convert preprocessing strategy string to enum value."""
        if not v:
            return PreprocessingStrategy.FULL_DOCUMENT.value

        strategy_mapping = {
            "full_document": PreprocessingStrategy.FULL_DOCUMENT,
            "row_by_row": PreprocessingStrategy.ROW_BY_ROW,
            "custom": PreprocessingStrategy.CUSTOM,
        }

        v_lower = v.lower()

        # Check if it's already an enum value
        try:
            return PreprocessingStrategy(v).value
        except ValueError:
            pass

        # Check mapping
        if v_lower in strategy_mapping:
            return strategy_mapping[v_lower].value

        # Check if it's an enum name
        for enum_item in PreprocessingStrategy:
            if v_lower == enum_item.name.lower():
                return enum_item.value

        raise ValueError(
            f"Invalid preprocessing strategy: {v}. Valid strategies are: {', '.join([e.value for e in PreprocessingStrategy])}"
        )


class PreprocessingConfigurationCreate(PreprocessingConfigurationBase):
    pass


class PreprocessingConfigurationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    table_settings: dict | None = None
    additional_settings: dict | None = None


class PreprocessingConfiguration(PreprocessingConfigurationBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FilePreprocessingTaskStatus(BaseModel):
    file_id: int
    file_name: str
    status: str
    progress: float
    error_message: str | None = None
    document_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PreprocessingTaskBase(BaseModel):
    configuration_id: int | None = None
    rollback_on_cancel: bool = True


class PreprocessingTaskCreate(PreprocessingTaskBase):
    file_ids: list[int]
    configuration_id: int | None = None

    # Allow inline configuration if no configuration_id
    inline_config: PreprocessingConfigurationBase | None = None

    force_reprocess: bool = False
    bypass_celery: bool = False

    @field_validator("file_ids")
    def file_ids_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("At least one file ID must be provided")
        return v

    @model_validator(mode="after")
    def validate_configuration(self):
        if not self.configuration_id and not self.inline_config:
            raise ValueError(
                "Either configuration_id or inline_config must be provided"
            )
        return self

class PreprocessingTaskUpdate(PreprocessingTaskBase):
    pass


class PreprocessingTask(PreprocessingTaskBase):
    id: int
    project_id: int
    status: str
    message: str | None = None
    total_files: int
    processed_files: int
    failed_files: int
    is_cancelled: bool
    celery_task_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_completion: datetime | None = None
    created_at: datetime
    updated_at: datetime

    # Change this to accept the ORM model directly
    file_tasks: list[Any] = []  # Will be converted in validator

    # Configuration used
    configuration: PreprocessingConfiguration | None = None

    @field_validator("file_tasks", mode="before")
    def convert_file_tasks(cls, v):
        """Convert FilePreprocessingTask ORM objects to FilePreprocessingTaskStatus."""
        if not v:
            return []

        result = []
        for task in v:
            # Handle both ORM objects and dicts
            if hasattr(task, "__dict__"):  # ORM object
                result.append(
                    {
                        "file_id": task.file_id,
                        "file_name": task.file.file_name
                        if hasattr(task, "file") and task.file
                        else f"File {task.file_id}",
                        "status": task.status.value
                        if hasattr(task.status, "value")
                        else task.status,
                        "progress": task.progress or 0.0,
                        "error_message": task.error_message,
                        "document_count": task.document_count,
                        "started_at": task.started_at,
                        "completed_at": task.completed_at,
                    }
                )
            else:  # Already a dict
                result.append(v)

        return result

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
