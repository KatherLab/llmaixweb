from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    SkipValidation,
    field_validator,
    model_validator,
)

from ..core.config import settings
from ..utils.enums import FileCreator, PreprocessingStrategy
from .other import UTCModel

if TYPE_CHECKING:
    from .user import User  # noqa: F401


class ProjectBase(UTCModel):
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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FileBase(UTCModel):
    file_name: str | None = None
    file_type: str | None = None
    file_uuid: str | None = None
    file_storage_type: str | None = None
    description: str | None = None
    file_size: int | None = None
    file_hash: str | None = None
    file_metadata: dict | None = None
    preprocessing_strategy: PreprocessingStrategy | None = None


class FileCreate(FileBase):
    file_name: str
    file_type: str | None = None
    file_size: int | None = None
    file_hash: str | None = None


class FileUpdate(FileBase):
    description: str | None = None


class File(FileBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
    file_creator: FileCreator = FileCreator.user

    # Add computed properties
    @property
    def is_linked(self) -> bool:
        """Check if file is linked to documents or preprocessing tasks"""
        return bool(
            self.documents_as_original
            or self.documents_as_preprocessed
            or self.preprocessing_tasks
            or self.file_preprocessing_tasks
        )

    model_config = ConfigDict(from_attributes=True)


class FileFilter(BaseModel):
    """Filter parameters for file queries"""

    search: str | None = None
    file_type: str | None = None
    file_creator: FileCreator | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    min_size: int | None = None
    max_size: int | None = None


class DocumentBase(UTCModel):
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


class DocumentSetBase(UTCModel):
    name: str
    description: str | None = None
    tags: list[str] = []
    is_auto_generated: bool = False
    preprocessing_config_id: int | None = None


class DocumentSetUpdate(UTCModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    document_ids: list[int] | None = None


class DocumentSetCreate(DocumentSetBase):
    name: str
    description: str | None = None
    trial_id: int | None = None  # Optional - for creating from trial
    document_ids: list[int] = []  # Optional - for creating from documents

    @model_validator(mode="after")
    def validate_documents_or_trial(self):
        """Ensure either document_ids or trial_id is provided"""
        if not self.document_ids and not self.trial_id:
            raise ValueError("Either document_ids or trial_id must be provided")
        if self.document_ids and self.trial_id:
            raise ValueError("Cannot provide both document_ids and trial_id")
        return self


class DocumentSet(DocumentSetBase):
    id: int
    project_id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    documents: list[Document] = []

    model_config = ConfigDict(from_attributes=True)


class DocumentSetFromTrial(BaseModel):
    """Schema for creating a document set from an existing trial"""

    name: str
    description: str | None = None
    tags: list[str] = []


class DocumentSetStats(BaseModel):
    """Statistics about document set usage"""

    trials_count: int
    extractions_count: int
    last_used: datetime | None


class DocumentFilter(BaseModel):
    """Filter parameters for document queries"""

    search: str | None = None
    preprocessing_config_id: int | None = None
    preprocessing_task_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    file_ids: list[int] | None = None
    status: str | None = None
    tags: list[str] | None = None


class DocumentBulkAction(BaseModel):
    """Schema for bulk document operations"""

    action: str  # 'add_to_set', 'remove_from_set', 'delete', 'reprocess'
    document_ids: list[int]
    target_set_id: int | None = None  # For add_to_set action
    force: bool = False


class DocumentSetSummary(BaseModel):
    """Summary information for document set listing"""

    id: int
    name: str
    description: str | None
    document_count: int
    tags: list[str]
    preprocessing_config_name: str | None
    is_auto_generated: bool
    created_at: datetime
    last_used: datetime | None
    usage_count: int


class DocumentSetDetail(DocumentSet):
    """Detailed document set information including documents"""

    documents: list[Document]
    usage_stats: DocumentSetStats
    preprocessing_config: PreprocessingConfiguration | None


class SmartDocumentSelection(BaseModel):
    """Parameters for smart document selection"""

    mode: str  # 'previous_trial', 'by_config', 'by_date', 'by_tags'

    # For previous_trial mode
    source_trial_id: int | None = None

    # For by_config mode
    preprocessing_config_id: int | None = None

    # For by_date mode
    date_from: datetime | None = None
    date_to: datetime | None = None

    # For by_tags mode (documents that have these tags in their sets)
    tags: list[str] | None = None

    # Common options
    limit: int | None = None
    exclude_ids: list[int] = []


class SchemaBase(UTCModel):
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


class PromptBase(UTCModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    user_prompt: str | None = None


class PromptCreate(PromptBase):
    name: str
    project_id: int
    description: str | None = None
    system_prompt: str | None = None
    user_prompt: str | None = None


class PromptUpdate(PromptBase):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    user_prompt: str | None = None


class Prompt(PromptBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrialBase(UTCModel):
    name: str | None = None
    description: str | None = None
    schema_id: int
    prompt_id: int
    document_ids: list[int] | None = None  # Make optional
    document_set_id: int | None = None  # Add this for selecting entire sets
    llm_model: str | None = settings.OPENAI_API_MODEL
    api_key: str | None = settings.OPENAI_API_KEY
    base_url: str | None = settings.OPENAI_API_BASE
    bypass_celery: bool = False
    advanced_options: dict | None = None


class TrialCreate(TrialBase):
    @model_validator(mode="after")
    def validate_documents_or_set(self):
        """Ensure either document_ids or document_set_id is provided"""
        if not self.document_ids and not self.document_set_id:
            raise ValueError("Either document_ids or document_set_id must be provided")
        if self.document_ids and self.document_set_id:
            raise ValueError("Cannot provide both document_ids and document_set_id")
        return self


class TrialUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class Trial(TrialBase):
    id: int
    project_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    results: list[TrialResult] = []
    prompt: Prompt | None = None
    document_set: DocumentSet | None = None  # Add this
    advanced_options: dict | None = None

    docs_done: int | None = None  # number of documents already processed
    progress: float | None = None  # 0.0 – 1.0
    started_at: datetime | None = None  # set when the first doc starts
    finished_at: datetime | None = None  # set when everything is done
    meta: dict | None = None  # currently holds {"eta_seconds": …}

    model_config = ConfigDict(from_attributes=True)


class TrialResultBase(UTCModel):
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


class PreprocessingConfigurationBase(UTCModel):
    name: str
    description: str | None = None
    pdf_backend: str | None = None
    ocr_backend: str | None = None
    use_ocr: bool = True
    force_ocr: bool = False
    ocr_languages: list[str] | None = None
    ocr_model: str | None = None
    llm_model: str | None = None
    additional_settings: dict | None = None


class PreprocessingConfigurationCreate(PreprocessingConfigurationBase):
    pass


class PreprocessingConfigurationUpdate(UTCModel):
    name: str | None = None
    description: str | None = None
    additional_settings: dict | None = None


class PreprocessingConfiguration(PreprocessingConfigurationBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FilePreprocessingTaskBase(UTCModel):
    file_id: int
    status: str
    progress: float = 0.0
    error_message: str | None = None
    document_count: int = 0
    file_name: str | None = None
    processing_time: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class FilePreprocessingTask(FilePreprocessingTaskBase):
    id: int
    preprocessing_task_id: int

    model_config = ConfigDict(from_attributes=True)


class PreprocessingTaskBase(UTCModel):
    configuration_id: int | None = None
    rollback_on_cancel: bool = True


class PreprocessingTaskCreate(PreprocessingTaskBase):
    file_ids: list[int]
    configuration_id: int | None = None

    # Allow inline configuration if no configuration_id
    inline_config: PreprocessingConfigurationBase | None = None

    force_reprocess: bool = False
    bypass_celery: bool = False

    # Optional API credentials for LLM preprocessing
    api_key: str | None = None
    base_url: str | None = None

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

    # Update to use the proper schema
    file_tasks: list[FilePreprocessingTask] = []

    # Configuration used
    configuration: PreprocessingConfiguration | None = None

    skipped_files: int = 0
    task_metadata: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class EvaluationBase(UTCModel):
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


class EvaluationDetail(UTCModel):
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


class FieldMappingBase(UTCModel):
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


class GroundTruthBase(UTCModel):
    name: str | None = None
    format: str | None = None


class GroundTruthCreate(GroundTruthBase):
    name: str
    format: str


class GroundTruthUpdate(UTCModel):
    name: str | None = None
    field_mappings: list[FieldMappingCreate] | None = None


class GroundTruth(GroundTruthBase):
    id: int
    project_id: int
    file_uuid: str
    field_mappings: list[FieldMapping] = []
    id_column_name: str | None = None
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
class EvaluationSummary(UTCModel):
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
