import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base
from ..utils.enums import (
    ComparisonMethod,
    FieldType,
    FileCreator,
    FileStorageType,
    FileType,
    PreprocessingStatus,
    PreprocessingStrategy,
)

if TYPE_CHECKING:
    from .user import User


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False, length=10), default=ProjectStatus.ACTIVE
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    files: Mapped[list["File"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    document_sets: Mapped[list["DocumentSet"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    trials: Mapped[list["Trial"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    schemas: Mapped[list["Schema"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    prompts: Mapped[list["Prompt"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    preprocessing_tasks: Mapped[list["PreprocessingTask"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    ground_truth_files: Mapped[list["GroundTruth"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    owner: Mapped["User"] = relationship(back_populates="projects")  # noqa: F821
    preprocessing_configurations: Mapped[list["PreprocessingConfiguration"]] = (
        relationship(back_populates="project", cascade="all, delete-orphan")
    )


preprocessing_task_file_association = Table(
    "preprocessing_task_file_association",
    Base.metadata,
    Column(
        "preprocessing_task_id", ForeignKey("preprocessing_tasks.id"), primary_key=True
    ),
    Column("file_id", ForeignKey("files.id"), primary_key=True),
)

preprocessing_task_document_association = Table(
    "preprocessing_task_document_association",
    Base.metadata,
    Column(
        "preprocessing_task_id", ForeignKey("preprocessing_tasks.id"), primary_key=True
    ),
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
)

preprocessing_configuration_file_association = Table(
    "preprocessing_configuration_file_association",
    Base.metadata,
    Column(
        "configuration_id",
        ForeignKey("preprocessing_configurations.id"),
        primary_key=True,
    ),
    Column("file_id", ForeignKey("files.id"), primary_key=True),
)


class File(Base):
    __tablename__ = "files"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    file_storage_type: Mapped[FileStorageType] = mapped_column(
        Enum(FileStorageType, native_enum=False, length=10),
        default=FileStorageType.LOCAL,
    )
    file_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType, native_enum=False, length=100), default=FileType.APPLICATION_PDF
    )
    file_creator: Mapped[FileCreator] = mapped_column(
        Enum(FileCreator, native_enum=False, length=20), default=FileCreator.user
    )
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    # New fields for better file management
    file_size: Mapped[int] = mapped_column(nullable=True)  # Size in bytes
    file_hash: Mapped[str] = mapped_column(String(64), nullable=True)  # SHA-256 hash

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Add index for hash lookups
    __table_args__ = (Index("ix_file_hash_project", "file_hash", "project_id"),)

    project: Mapped["Project"] = relationship(back_populates="files")
    documents_as_original: Mapped[list["Document"]] = relationship(
        foreign_keys="[Document.original_file_id]", back_populates="original_file"
    )
    documents_as_preprocessed: Mapped[list["Document"]] = relationship(
        foreign_keys="[Document.preprocessed_file_id]",
        back_populates="preprocessed_file",
    )
    preprocessing_tasks: Mapped[list["PreprocessingTask"]] = relationship(
        secondary="preprocessing_task_file_association", back_populates="files"
    )
    preprocessing_configurations: Mapped[list["PreprocessingConfiguration"]] = (
        relationship(
            secondary=preprocessing_configuration_file_association,
            back_populates="files",
        )
    )
    file_preprocessing_tasks: Mapped[list["FilePreprocessingTask"]] = relationship(
        back_populates="file"  # Link to FilePreprocessingTask.file
    )


document_set_association = Table(
    "document_set_association",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("document_set_id", ForeignKey("document_sets.id"), primary_key=True),
)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    original_file_id: Mapped[int] = mapped_column(
        ForeignKey("files.id"), nullable=False
    )
    file_preprocessing_task_id: Mapped[int] = mapped_column(
        ForeignKey("file_preprocessing_tasks.id"), nullable=True
    )

    # Configuration snapshot (for tracking what settings were used)
    preprocessing_config_id: Mapped[int] = mapped_column(
        ForeignKey("preprocessing_configurations.id"), nullable=False
    )
    preprocessing_config: Mapped["PreprocessingConfiguration"] = relationship(
        back_populates="documents"
    )

    # Document content
    text: Mapped[str] = mapped_column(String, nullable=False)
    document_name: Mapped[str] = mapped_column(String(500), nullable=True)

    # Metadata
    meta_data: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), nullable=True)
    # Can include: page_number, row_number, source_columns, etc.

    # Optional preprocessed file (for PDFs with OCR)
    preprocessed_file_id: Mapped[int] = mapped_column(
        ForeignKey("files.id"), nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="documents")
    original_file: Mapped["File"] = relationship(
        foreign_keys=[original_file_id], back_populates="documents_as_original"
    )
    preprocessed_file: Mapped["File"] = relationship(
        foreign_keys=[preprocessed_file_id], back_populates="documents_as_preprocessed"
    )
    file_preprocessing_task: Mapped["FilePreprocessingTask"] = relationship(
        back_populates="documents"
    )
    document_sets: Mapped[list["DocumentSet"]] = relationship(
        secondary=document_set_association, back_populates="documents"
    )

    # Add unique constraint for duplicate detection
    __table_args__ = (
        UniqueConstraint(
            "original_file_id",
            "preprocessing_config_id",
            "document_name",
            name="_document_uniqueness",
        ),
    )


class DocumentSet(Base):
    __tablename__ = "document_sets"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)

    # Add metadata for better organization
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    is_auto_generated: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # True for trial-created sets

    # Tags for categorization
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Track preprocessing configuration if all docs share one
    preprocessing_config_id: Mapped[int] = mapped_column(
        ForeignKey("preprocessing_configurations.id"), nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="document_sets")
    trials: Mapped[list["Trial"]] = relationship(
        "Trial", back_populates="document_set", cascade="all, delete-orphan"
    )

    documents: Mapped[list["Document"]] = relationship(
        secondary=document_set_association, back_populates="document_sets"
    )
    preprocessing_config: Mapped["PreprocessingConfiguration"] = relationship(
        back_populates="document_sets"
    )


class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    system_prompt: Mapped[str] = mapped_column(String, nullable=True)
    user_prompt: Mapped[str] = mapped_column(String, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    project: Mapped["Project"] = relationship(back_populates="prompts")
    trials: Mapped[list["Trial"]] = relationship(back_populates="prompt")


class Schema(Base):
    __tablename__ = "schemas"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    schema_name: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    project: Mapped["Project"] = relationship(back_populates="schemas")
    trials: Mapped[list["Trial"]] = relationship(back_populates="schema")
    field_mappings: Mapped[list["FieldMapping"]] = relationship(back_populates="schema")


class TrialStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Trial(Base):
    __tablename__ = "trials"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    schema_id: Mapped[int] = mapped_column(ForeignKey("schemas.id"), nullable=False)
    prompt_id: Mapped[str] = mapped_column(ForeignKey("prompts.id"), nullable=False)
    document_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    document_set_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_sets.id"), nullable=True
    )

    document_set: Mapped["DocumentSet"] = relationship(
        "DocumentSet", back_populates="trials"
    )

    status: Mapped[TrialStatus] = mapped_column(
        Enum(TrialStatus, native_enum=False, length=20),
        default=TrialStatus.PENDING,
    )
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(String(100), nullable=False)
    bypass_celery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    advanced_options: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    project: Mapped["Project"] = relationship(back_populates="trials")
    schema: Mapped["Schema"] = relationship(back_populates="trials")
    prompt: Mapped["Prompt"] = relationship(back_populates="trials")
    results: Mapped[list["TrialResult"]] = relationship(
        back_populates="trial", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="trial", cascade="all, delete-orphan"
    )


class TrialResult(Base):
    __tablename__ = "trial_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    trial_id: Mapped[int] = mapped_column(ForeignKey("trials.id"), nullable=False)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    trial: Mapped["Trial"] = relationship(back_populates="results")
    document: Mapped["Document"] = relationship()


class PreprocessingTaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PreprocessingConfiguration(Base):
    __tablename__ = "preprocessing_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    # File type specific settings
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType, native_enum=False, length=100, default=FileType.MIXED),
        nullable=False,
    )
    preprocessing_strategy: Mapped[PreprocessingStrategy] = mapped_column(
        Enum(PreprocessingStrategy, native_enum=False, length=50),
        default=PreprocessingStrategy.FULL_DOCUMENT,
    )

    # PDF/Image settings
    pdf_backend: Mapped[str] = mapped_column(String(50), nullable=True)
    ocr_backend: Mapped[str] = mapped_column(String(50), nullable=True)
    use_ocr: Mapped[bool] = mapped_column(Boolean, default=True)
    force_ocr: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_languages: Mapped[list[str]] = mapped_column(JSON, nullable=True)
    ocr_model: Mapped[str] = mapped_column(String(100), nullable=True)

    # Table/CSV settings
    table_settings: Mapped[dict] = mapped_column(JSON, nullable=True)
    # Example structure:
    # {
    #     "content_columns": ["column1", "column2"],
    #     "name_column": "document_name",
    #     "join_separator": " ",
    #     "skip_header_rows": 1,
    #     "encoding": "utf-8"
    # }

    # LLM settings (optional)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=True)

    # Additional settings
    additional_settings: Mapped[dict] = mapped_column(JSON, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        back_populates="preprocessing_configurations"
    )
    preprocessing_tasks: Mapped[list["PreprocessingTask"]] = relationship(
        back_populates="configuration"
    )
    files: Mapped[list["File"]] = relationship(
        secondary=preprocessing_configuration_file_association,
        back_populates="preprocessing_configurations",
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="preprocessing_config"
    )
    document_sets: Mapped[list["DocumentSet"]] = relationship(
        back_populates="preprocessing_config"
    )


class PreprocessingTask(Base):
    __tablename__ = "preprocessing_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    configuration_id: Mapped[int] = mapped_column(
        ForeignKey("preprocessing_configurations.id"), nullable=True
    )

    status: Mapped[PreprocessingStatus] = mapped_column(
        Enum(PreprocessingStatus, native_enum=False, length=20),
        default=PreprocessingStatus.PENDING,
    )
    message: Mapped[str] = mapped_column(String(500), nullable=True)

    # Overall progress
    total_files: Mapped[int] = mapped_column(default=0)
    processed_files: Mapped[int] = mapped_column(default=0)
    failed_files: Mapped[int] = mapped_column(default=0)
    skipped_files: Mapped[int] = mapped_column(default=0)

    # Cancellation settings
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    rollback_on_cancel: Mapped[bool] = mapped_column(Boolean, default=True)

    # Celery task ID for cancellation
    celery_task_id: Mapped[str] = mapped_column(String(100), nullable=True)

    # Timing
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estimated_completion: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    task_metadata: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="preprocessing_tasks")
    configuration: Mapped["PreprocessingConfiguration"] = relationship(
        back_populates="preprocessing_tasks"
    )
    file_tasks: Mapped[list["FilePreprocessingTask"]] = relationship(
        back_populates="preprocessing_task", cascade="all, delete-orphan"
    )
    files: Mapped[list["File"]] = relationship(
        secondary="preprocessing_task_file_association",
        back_populates="preprocessing_tasks",
    )


class FilePreprocessingTask(Base):
    __tablename__ = "file_preprocessing_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    preprocessing_task_id: Mapped[int] = mapped_column(
        ForeignKey("preprocessing_tasks.id"), nullable=False
    )
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)

    status: Mapped[PreprocessingStatus] = mapped_column(
        Enum(PreprocessingStatus, native_enum=False, length=20),
        default=PreprocessingStatus.PENDING,
    )
    error_message: Mapped[str] = mapped_column(String(1000), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)

    # Track produced documents
    document_count: Mapped[int] = mapped_column(default=0)

    # Add these new fields
    file_name: Mapped[str] = mapped_column(String(255), nullable=True)
    processing_time: Mapped[float] = mapped_column(Float, nullable=True)

    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    preprocessing_task: Mapped["PreprocessingTask"] = relationship(
        back_populates="file_tasks"
    )
    file: Mapped["File"] = relationship(back_populates="file_preprocessing_tasks")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="file_preprocessing_task", cascade="all, delete-orphan"
    )


class FieldMapping(Base):
    __tablename__ = "field_mappings"
    id: Mapped[int] = mapped_column(primary_key=True)
    ground_truth_id: Mapped[int] = mapped_column(
        ForeignKey("ground_truth.id"), nullable=False
    )
    schema_id: Mapped[int] = mapped_column(ForeignKey("schemas.id"), nullable=False)
    schema_field: Mapped[str] = mapped_column(String(200), nullable=False)
    ground_truth_field: Mapped[str] = mapped_column(String(200), nullable=False)
    field_type: Mapped[FieldType] = mapped_column(
        Enum(FieldType, native_enum=False, length=20), default=FieldType.STRING
    )
    comparison_method: Mapped[ComparisonMethod] = mapped_column(
        Enum(ComparisonMethod, native_enum=False, length=20),
        default=ComparisonMethod.EXACT,
    )
    comparison_options: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    schema: Mapped[Schema] = relationship(back_populates="field_mappings")
    ground_truth: Mapped["GroundTruth"] = relationship(back_populates="field_mappings")

    __table_args__ = (
        UniqueConstraint(
            "ground_truth_id",
            "schema_id",
            "schema_field",
            name="uq_field_mapping_gt_schema_field",
        ),
    )


class EvaluationMetric(Base):
    __tablename__ = "evaluation_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(
        ForeignKey("evaluations.id"), nullable=False
    )
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(200), nullable=False)
    ground_truth_value: Mapped[str] = mapped_column(String, nullable=True)
    predicted_value: Mapped[str] = mapped_column(String, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_type: Mapped[str] = mapped_column(String(50), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    evaluation: Mapped["Evaluation"] = relationship(back_populates="detailed_metrics")
    document: Mapped["Document"] = relationship()


class GroundTruth(Base):
    __tablename__ = "ground_truth"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    file_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    data_cache: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )
    id_column_name: Mapped[str] = mapped_column(String(200), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    project: Mapped["Project"] = relationship(back_populates="ground_truth_files")
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="ground_truth", cascade="all, delete-orphan"
    )
    field_mappings: Mapped[list["FieldMapping"]] = relationship(
        back_populates="ground_truth", cascade="all, delete-orphan"
    )


class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[int] = mapped_column(primary_key=True)
    trial_id: Mapped[int] = mapped_column(ForeignKey("trials.id"), nullable=False)
    groundtruth_id: Mapped[int] = mapped_column(
        ForeignKey("ground_truth.id"), nullable=False
    )
    metrics: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), nullable=False)
    field_metrics: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=False
    )
    document_metrics: Mapped[list] = mapped_column(JSON, nullable=False)
    confusion_matrices: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    trial: Mapped["Trial"] = relationship(back_populates="evaluations")
    ground_truth: Mapped["GroundTruth"] = relationship(back_populates="evaluations")
    detailed_metrics: Mapped[list["EvaluationMetric"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )
