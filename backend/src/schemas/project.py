# backend/src/schemas/project.py
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from ..models import ProjectStatus
from ..utils.enums import (
    ComparisonMethod,
    FieldType,
    FileCreator,
    PreprocessingStrategy,
)
from .other import UTCModel

if TYPE_CHECKING:
    from .user import User, UserPublic  # noqa: F401


class ProjectBase(UTCModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=500)
    status: ProjectStatus | None = None
    owner_id: int | None = None


class ProjectCreate(ProjectBase):
    name: str = Field(..., max_length=100)


class ProjectUpdate(ProjectBase):
    name: str = Field(..., max_length=100)


class Project(ProjectBase):
    id: int
    owner: UserPublic | None = None
    documents: list[Document] = Field(default_factory=list)
    document_count: int = 0
    # Aggregate counts used to drive the project workflow progression cue
    # (Files → Documents → Schemas → Trials → Evaluation check marks).
    schema_count: int = 0
    prompt_count: int = 0
    trial_count: int = 0
    evaluation_count: int = 0
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


class PaginatedFiles(UTCModel):
    """Paginated response for file listing"""

    items: List[File]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentBase(UTCModel):
    text: str
    document_name: str | None = None
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
    preprocessing_config_id: int
    preprocessing_config: PreprocessingConfiguration | None = None
    is_latest: bool = True
    version_of: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListItem(UTCModel):
    """Lightweight Document for list views — excludes the heavy `text` column.

    The full `text` is only returned by `GET /document/{id}` (used by the
    document viewer). List/picker views use this so a 500-row page doesn't
    ferry multi-MB OCR payloads.
    """

    id: int
    project_id: int
    document_name: str | None = None
    meta_data: dict | None = None
    original_file_id: int
    original_file: File | None = None
    preprocessed_file_id: int | None = None
    preprocessed_file: File | None = None
    preprocessing_config_id: int
    preprocessing_config: PreprocessingConfiguration | None = None
    is_latest: bool = True
    version_of: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedDocuments(UTCModel):
    """Paginated response for document listing with stats"""

    items: List[DocumentListItem]
    total: int
    # Stats computed server-side to avoid loading all documents
    recent_count: int | None = None  # Documents created in last 7 days
    today_count: int | None = None  # Documents created today
    week_count: int | None = None  # Documents created in last 7 days
    month_count: int | None = None  # Documents created in last 30 days


class DocumentDependencyRequest(UTCModel):
    """Request body for previewing what a cascade delete would remove."""

    document_ids: list[int] = Field(default_factory=list, max_length=1000)


class DependencyGroup(UTCModel):
    """A count of affected resources plus a few names for display."""

    count: int = 0
    names: list[str] = []


class DocumentDependencies(UTCModel):
    """Summary of what deleting the given documents (with cascade) would remove."""

    trials: DependencyGroup = Field(default_factory=DependencyGroup)
    document_sets: DependencyGroup = Field(default_factory=DependencyGroup)
    trial_results: int = 0
    evaluation_metrics: int = 0
    evaluations: int = 0


class FileDependencyRequest(UTCModel):
    """Request body for previewing what a cascade file delete would remove."""

    file_ids: list[int] = Field(default_factory=list, max_length=1000)


class FileDependencies(DocumentDependencies):
    """Impact preview for a cascade file delete: the documents produced from the
    files, plus the same downstream dependents (`POST /file/dependencies`)."""

    documents: int = 0


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
    name: str = Field(..., max_length=100)
    description: str | None = Field(None, max_length=500)
    trial_id: int | None = None  # Optional - for creating from trial
    document_ids: list[int] = Field(default_factory=list, max_length=1000)

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
    description: str | None = None
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
    last_used: datetime | None = None


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


class DocumentSetSummary(UTCModel):
    """Lightweight document-set info for list views.

    Carries aggregate counts instead of the full `documents` collection so the
    set list doesn't N+1-load every member document (with `text`) per set.
    """

    id: int
    project_id: int
    name: str
    description: str | None = None
    tags: list[str] = []
    is_auto_generated: bool = False
    preprocessing_config: PreprocessingConfiguration | None = None
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    trials_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PaginatedDocumentSets(UTCModel):
    """Paginated response for document-set listing"""

    items: List[DocumentSetSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentSetDetail(DocumentSet):
    """Detailed document set information including documents"""

    usage_stats: DocumentSetStats
    preprocessing_config: PreprocessingConfiguration | None = None
    documents: list[Document]


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
    schema_name: str = Field(..., max_length=100)
    schema_definition: dict


class SchemaUpdate(SchemaBase):
    schema_name: str | None = Field(None, max_length=100)
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
    name: str = Field(..., max_length=100)
    project_id: int
    description: str | None = Field(None, max_length=500)
    system_prompt: str | None = None
    user_prompt: str | None = None


class PromptUpdate(PromptBase):
    name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=500)
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
    # Defaults intentionally None: a Pydantic field default is evaluated at
    # class-definition time and embedded verbatim in the generated OpenAPI
    # schema, so defaulting these to settings.* would publish the server's
    # configured API key / base URL / model in /openapi.json and Swagger UI.
    # The router resolves the settings fallback at request time instead
    # (trials.py: `trial.api_key or settings.OPENAI_API_KEY`).
    llm_model: str | None = Field(None, max_length=255)
    api_key: str | None = Field(None, max_length=512)
    base_url: str | None = Field(None, max_length=512)
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
    name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=512)


class Trial(TrialBase):
    id: int
    project_id: int
    # Per-project sequence number; server-assigned (not user-supplied), like `id`.
    project_trial_number: int
    status: str
    created_at: datetime
    updated_at: datetime
    results: list[TrialResult] = Field(default_factory=list)
    prompt: Prompt | None = None
    document_set: DocumentSet | None = None  # Add this
    advanced_options: dict | None = None

    docs_done: int | None = None  # number of documents already processed
    progress: float | None = None  # 0.0 – 1.0
    started_at: datetime | None = None  # set when the first doc starts
    finished_at: datetime | None = None  # set when everything is done
    meta: dict | None = None  # currently holds {"eta_seconds": …}

    # Frozen schema/prompt captured at trial creation (None for legacy trials)
    schema_snapshot: dict | None = None
    prompt_snapshot: dict | None = None

    # Never expose API keys or base URLs in API responses
    api_key: str | None = Field(default=None, exclude=True)
    base_url: str | None = Field(default=None, exclude=True)

    model_config = ConfigDict(from_attributes=True)


class TrialSummary(UTCModel):
    """Lightweight Trial model for listings (no 'results')."""

    id: int
    project_id: int
    # Per-project sequence number; server-assigned (not user-supplied), like `id`.
    project_trial_number: int
    name: str | None = None
    description: str | None = None
    schema_id: int
    prompt_id: int
    document_ids: list[int] | None = None
    document_set_id: int | None = None
    llm_model: str | None = None
    api_key: str | None = Field(default=None, exclude=True)
    base_url: str | None = Field(default=None, exclude=True)
    bypass_celery: bool = False
    advanced_options: dict | None = None

    status: str
    created_at: datetime
    updated_at: datetime

    # progress-ish, meta, etc.
    docs_done: int | None = None
    progress: float | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    meta: dict | None = None

    # Frozen schema/prompt captured at trial creation (None for legacy trials)
    schema_snapshot: dict | None = None
    prompt_snapshot: dict | None = None

    # Optional small relationships you may show in cards
    prompt: "Prompt | None" = None
    document_set: "DocumentSet | None" = None

    # --- NEW summary fields for list view (no heavy loads) ---
    documents_count: int = 0
    results_count: int = 0
    last_result_at: datetime | None = None
    error_count: int | None = None  # length of meta.failures if present
    has_failures: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedTrials(UTCModel):
    items: List[TrialSummary]
    total: int


class TrialResultBase(UTCModel):
    result: dict | None = None
    status: str | None = None


class TrialResultCreate(TrialResultBase):
    result: dict


class TrialResult(TrialResultBase):
    id: int
    trial_id: int
    document_id: int
    additional_content: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrialResultItem(TrialResult):
    """TrialResult enriched with the joined document name for list views."""

    document_name: str | None = None
    original_file_name: str | None = None


class PaginatedTrialResults(UTCModel):
    items: List[TrialResultItem]
    total: int
    total_usage: dict | None = None


# Secret credential keys that may be embedded in a preprocessing
# configuration's additional_settings JSON. These are redacted from every API
# response and WebSocket broadcast so they never leave the server — from the
# UI's perspective they are write-only (re-enter to change). Storage-at-rest is
# the operator's DB-encryption responsibility (see docs/SECURITY.md).
_OCR_SECRET_KEYS = ("mistral_api_key", "vision_api_key")


def redact_ocr_secrets(additional_settings: dict | None) -> dict | None:
    """Return additional_settings with OCR credential keys stripped out."""
    if not additional_settings:
        return additional_settings
    if not any(k in additional_settings for k in _OCR_SECRET_KEYS):
        return additional_settings
    return {k: v for k, v in additional_settings.items() if k not in _OCR_SECRET_KEYS}


class PreprocessingConfigurationBase(UTCModel):
    name: str = Field(..., max_length=100)
    description: str | None = Field(None, max_length=500)
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

    @field_serializer("additional_settings")
    def _redact_additional_settings(self, v: dict | None) -> dict | None:
        # Never expose OCR credentials embedded in the config to clients.
        return redact_ocr_secrets(v)


class FilePreprocessingTaskBase(UTCModel):
    file_id: int
    status: str
    progress: float = 0.0
    error_message: str | None = None
    document_count: int = 0
    file_name: str | None = None
    processing_time: float | None = None
    warnings: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    document_ids: list[int] | None = Field(default_factory=list)


class FilePreprocessingTask(FilePreprocessingTaskBase):
    id: int
    preprocessing_task_id: int

    model_config = ConfigDict(from_attributes=True)

    @field_validator("document_ids", mode="before")
    @classmethod
    def set_default_document_ids(cls, v):
        """Convert None to empty list and filter out None values from list"""
        if v is None:
            return []
        # Filter out any None values that may exist in the list (from corrupted data)
        return [x for x in v if x is not None]


class PreprocessingTaskBase(UTCModel):
    configuration_id: int | None = None
    rollback_on_cancel: bool = True


class PreprocessingTaskCreate(PreprocessingTaskBase):
    file_ids: list[int]
    configuration_id: int | None = None

    # Allow inline configuration if no configuration_id
    inline_config: PreprocessingConfigurationBase | None = None

    force_reprocess: bool = False
    skip_existing: bool = (
        False  # If True, skip files with existing documents for this config
    )
    bypass_celery: bool = False

    # Optional API credentials for LLM preprocessing
    api_key: str | None = Field(None, max_length=512)
    base_url: str | None = Field(None, max_length=512)

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

    # Runtime progress meta written by the pipeline (eta_seconds, progress,
    # total_files, completed_files, failed_files). Distinct from
    # `task_metadata` (config/skip info). The ORM column is non-nullable with a
    # dict default, but this is exposed as `dict | None` for safety.
    meta: dict | None = None

    # Computed fields for document counts
    @computed_field
    @property
    def documents_count(self) -> int:
        """Total documents produced across all file tasks"""
        return (
            sum(ft.document_count for ft in self.file_tasks) if self.file_tasks else 0
        )

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


class EvaluationListItem(UTCModel):
    """Lightweight Evaluation for list endpoints.

    Omits the heavy per-field (`field_metrics`) and per-document
    (`document_metrics`) payloads — those can be multiple MB for a large
    evaluation and are only needed by the detail/analysis endpoint. Keeps the
    small overall `metrics` summary used for the list's accuracy display.
    """

    id: int
    trial_id: int
    groundtruth_id: int
    metrics: dict
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
    confusion_matrices: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FieldMappingBase(UTCModel):
    schema_field: str = Field(..., max_length=200)
    ground_truth_field: str = Field(..., max_length=200)
    schema_id: int
    field_type: FieldType = FieldType.STRING
    comparison_method: ComparisonMethod = ComparisonMethod.EXACT
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
    name: str = Field(..., max_length=100)
    format: str = Field(..., max_length=10)


class GroundTruthUpdate(UTCModel):
    name: str | None = None
    field_mappings: list[FieldMappingCreate] | None = None


class GroundTruth(GroundTruthBase):
    id: int
    project_id: int
    file_uuid: str
    field_mappings: list[FieldMapping] = Field(default_factory=list)
    id_column_name: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EvaluationMetricDetail(BaseModel):
    document_id: int
    field_name: str
    ground_truth_value: str | None = None
    predicted_value: str | None = None
    is_correct: bool
    error_type: str | None = None
    confidence_score: float | None = None


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
    confusion_matrices: dict | None = None
    created_at: datetime
    # Add summary error information
    total_errors: int | None = None
    error_documents: list[int] | None = None
    # Non-blocking validation warnings (e.g. low document↔GT match rate).
    # Evaluation still runs; these are surfaced so the user knows some
    # documents could not be matched to ground truth.
    warnings: list[str] | None = None


# Add new schema for error details
class EvaluationError(BaseModel):
    document_id: int
    document_name: str | None = None
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


class DuplicatePreviewItem(BaseModel):
    """Information about a single file's existing documents"""

    file_id: int
    file_name: str
    existing_document_count: int
    existing_document_ids: list[int]
    preprocessing_config_id: int | None = None
    config_name: str | None = None


class PdfEmbeddedTextInfo(BaseModel):
    """Information about PDFs with embedded text that may not need OCR"""

    file_id: int
    file_name: str
    has_embedded_text: bool
    existing_document_ocr_method: str | None = (
        None  # e.g., "docling_serve_no_ocr", "tesseract", "mistral_ocr"
    )


class PreprocessingDuplicatePreview(BaseModel):
    """Response for preprocessing duplicate preview endpoint"""

    has_duplicates: bool
    files_with_duplicates: list[DuplicatePreviewItem]
    total_files_to_process: int
    files_without_duplicates: int
    total_existing_documents: int
    # PDFs with embedded text info (only populated when processing PDFs)
    pdfs_with_embedded_text: list[PdfEmbeddedTextInfo] = Field(default_factory=list)
    # Files that have existing documents with the exact same config
    same_config_duplicates: list[DuplicatePreviewItem] = Field(default_factory=list)


from .user import User, UserPublic  # noqa: E402, F401

# --- Rebuild forward refs for Pydantic v2 / FastAPI ---
for _m in [
    Document,
    DocumentListItem,
    File,
    PreprocessingConfiguration,
    FilePreprocessingTask,
    PreprocessingTask,
    DocumentSet,
    DocumentSetSummary,
    PaginatedDocumentSets,
    TrialResult,
    TrialResultItem,
    Trial,
    Evaluation,
    EvaluationDetail,
    DocumentSetDetail,
    PaginatedDocuments,
    TrialSummary,
    PaginatedTrials,
    PaginatedTrialResults,
    Project,  # you already call this below, but keeping it here is fine
]:
    _m.model_rebuild()

Project.model_rebuild()
