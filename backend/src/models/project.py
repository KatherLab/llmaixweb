# backend/src/models/project.py
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
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base
from ..utils.crypto import decrypt, encrypt
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

    file_metadata: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )

    preprocessing_strategy: Mapped[PreprocessingStrategy] = mapped_column(
        Enum(PreprocessingStrategy, native_enum=False, length=20), nullable=True
    )

    file_size: Mapped[int] = mapped_column(nullable=True)  # Size in bytes
    file_hash: Mapped[str] = mapped_column(String(64), nullable=True)  # SHA-256 hash

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Add indexes for common query patterns (optimized for 50k+ files)
    __table_args__ = (
        Index("ix_file_hash_project", "file_hash", "project_id"),
        Index("ix_files_project_created", "project_id", "created_at"),
        Index("ix_files_project_type", "project_id", "file_type"),
        Index("ix_files_project_creator", "project_id", "file_creator"),
    )

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
    # PK leads with document_id; index the reverse direction so "all documents
    # in a set" (document_set_id lookups) doesn't seq-scan at 100k+ members.
    Index("ix_document_set_association_document_set_id", "document_set_id"),
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

    # Version tracking (for document history)
    is_latest: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    version_of: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )  # Links to the "root" document for version chains

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
    # Version tracking relationships
    parent_version: Mapped["Document | None"] = relationship(
        foreign_keys=[version_of], remote_side="Document.id", backref="versions"
    )

    # Unique constraint to support document versioning.
    # Only enforces uniqueness when is_latest=True, allowing unlimited
    # archived versions (is_latest=False) for version history.
    # Note: The actual partial constraint is created via migration
    # (fix_document_versioning_constraint) using postgresql_where.
    __table_args__ = (
        # This UniqueConstraint is for documentation/SQLAlchemy awareness.
        # The actual DB constraint is partial (only when is_latest=True).
        UniqueConstraint(
            "original_file_id",
            "preprocessing_config_id",
            "document_name",
            name="_document_uniqueness",
        ),
        Index("ix_documents_latest", "is_latest"),
        Index("ix_documents_version_of", "version_of"),
        # Composite indexes for common query patterns (optimized for 50k+ documents)
        Index("ix_documents_project_created", "project_id", "created_at"),
        Index("ix_documents_project_latest", "project_id", "is_latest"),
        Index("ix_documents_project_file", "project_id", "original_file_id"),
        Index("ix_documents_project_config", "project_id", "preprocessing_config_id"),
        Index("ix_documents_project_task", "project_id", "file_preprocessing_task_id"),
    )


class DocumentSet(Base):
    __tablename__ = "document_sets"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)

    __table_args__ = (
        Index("ix_document_sets_project_created", "project_id", "created_at"),
    )

    # Add metadata for better organization
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    is_auto_generated: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # True for auto-created sets (e.g., row-by-row preprocessing, trial results)

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
    # NOTE: no "delete-orphan" here. Trial.document_set_id is nullable and
    # trials are routinely created without a set, so unlinking a trial from a
    # set (setting document_set = None) must NOT delete the trial — and with
    # "delete-orphan" it would, silently destroying the trial plus its
    # TrialResults and Evaluations. Deleting a DocumentSet nulls the FK
    # instead (see ondelete="SET NULL" on Trial.document_set_id); the
    # delete_document_set endpoint additionally rejects sets still referenced
    # by a trial.
    trials: Mapped[list["Trial"]] = relationship(
        "Trial",
        back_populates="document_set",
        # Let the DB handle deletion (Trial.document_set_id has
        # ondelete="SET NULL"): passive_deletes=True tells SQLAlchemy NOT to
        # load the trials and ORM-DELETE them when a DocumentSet is deleted.
        # With cascade="all" (the previous setting) the ORM would emit DELETEs
        # for every trial, silently destroying the trials and their cascaded
        # TrialResults/Evaluations — the opposite of the SET NULL intent above.
        passive_deletes=True,
    )

    documents: Mapped[list["Document"]] = relationship(
        secondary=document_set_association, back_populates="document_sets"
    )
    preprocessing_config: Mapped["PreprocessingConfiguration"] = relationship(
        back_populates="document_sets"
    )


class PreprocessingTaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PreprocessingConfiguration(Base):
    __tablename__ = "preprocessing_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        Index(
            "ix_preprocessing_configurations_project_created",
            "project_id",
            "created_at",
        ),
    )
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    # Engine settings are stored in additional_settings
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

    __table_args__ = (
        Index("ix_preprocessing_tasks_project_created", "project_id", "created_at"),
        Index("ix_preprocessing_tasks_configuration_id", "configuration_id"),
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
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # ETA, etc.

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    task_metadata: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )

    # Stored encrypted (Fernet). Read/written via the `api_key` property below,
    # which decrypts on read and encrypts on write — so the OCR API key for a
    # custom preprocessing backend never persists in plaintext. Mirrors Trial.
    api_key_encrypted: Mapped[str] = mapped_column(
        "api_key_encrypted", String(512), nullable=True, default=""
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

    @property
    def api_key(self) -> str:
        """Plaintext OCR API key (decrypted on read)."""
        return decrypt(self.api_key_encrypted)

    @api_key.setter
    def api_key(self, value: str) -> None:
        """Encrypt the plaintext key before storing it."""
        self.api_key_encrypted = encrypt(value) if value else ""


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
    error_message: Mapped[str] = mapped_column(String(4000), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)

    # Track produced documents
    document_count: Mapped[int] = mapped_column(default=0)
    document_ids: Mapped[list[int]] = mapped_column(
        MutableList.as_mutable(JSON), nullable=True, default=list
    )

    # Add these new fields
    file_name: Mapped[str] = mapped_column(String(255), nullable=True)
    processing_time: Mapped[float] = mapped_column(Float, nullable=True)

    # Track warnings (e.g., skipped rows during CSV processing)
    warnings: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Bumped periodically while the file is actively processing. The orphan
    # sweeper treats a stale last_heartbeat_at (rather than started_at) as
    # evidence of a dead worker, so a slow-but-legitimate file whose per-file
    # timeout exceeds the sweeper cutoff is not wrongly marked FAILED.
    last_heartbeat_at: Mapped[DateTime] = mapped_column(
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

    __table_args__ = (
        Index(
            "ix_file_preprocessing_tasks_preprocessing_task_id", "preprocessing_task_id"
        ),
        Index("ix_file_preprocessing_tasks_file_id", "file_id"),
    )


class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    system_prompt: Mapped[str] = mapped_column(String, nullable=True)
    user_prompt: Mapped[str] = mapped_column(String, nullable=True)

    __table_args__ = (Index("ix_prompts_project_created", "project_id", "created_at"),)

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

    __table_args__ = (Index("ix_schemas_project_created", "project_id", "created_at"),)
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
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Trial(Base):
    __tablename__ = "trials"

    # ── identity ────────────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(512))

    # ── foreign keys ────────────────────────────────────────────────────────────
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    schema_id: Mapped[int] = mapped_column(ForeignKey("schemas.id"))
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id"))
    document_set_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_sets.id", ondelete="SET NULL")
    )

    __table_args__ = (
        Index("ix_trials_project_created", "project_id", "created_at"),
        Index("ix_trials_project_status", "project_id", "status"),
    )

    # ── config ──────────────────────────────────────────────────────────────────
    document_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    status: Mapped[TrialStatus] = mapped_column(
        Enum(TrialStatus, native_enum=False, length=20), default=TrialStatus.PENDING
    )
    llm_model: Mapped[str] = mapped_column(String(255))
    # Stored encrypted (Fernet). Read/written via the `api_key` property below,
    # which decrypts on read and encrypts on write — so `trial.api_key` always
    # yields the plaintext key without ever persisting it.
    api_key_encrypted: Mapped[str] = mapped_column("api_key_encrypted", String(512))
    base_url: Mapped[str] = mapped_column(String(512))
    bypass_celery: Mapped[bool] = mapped_column(Boolean, default=False)
    advanced_options: Mapped[dict] = mapped_column(JSON, default=dict)

    # Frozen copies of the schema + prompt at trial-creation time, so the
    # record reflects exactly what was used even if the source is edited later.
    schema_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    prompt_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)

    # ── progress tracking ───────────────────────────────────────────────────────
    docs_done: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0-1.0
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # ETA etc.

    # Cancellation settings
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    rollback_on_cancel: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── timestamps ──────────────────────────────────────────────────────────────
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── relationships ───────────────────────────────────────────────────────────
    project: Mapped["Project"] = relationship(back_populates="trials")
    schema: Mapped["Schema"] = relationship(back_populates="trials")
    prompt: Mapped["Prompt"] = relationship(back_populates="trials")
    document_set: Mapped["DocumentSet"] = relationship(back_populates="trials")
    results: Mapped[list["TrialResult"]] = relationship(
        back_populates="trial", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="trial", cascade="all, delete-orphan"
    )

    @property
    def api_key(self) -> str:
        """Plaintext API key (decrypted on read)."""
        return decrypt(self.api_key_encrypted)

    @api_key.setter
    def api_key(self, value: str) -> None:
        """Encrypt the plaintext key before storing it."""
        self.api_key_encrypted = encrypt(value) if value else ""

    def cancel(self):
        self.is_cancelled = True
        self.status = TrialStatus.CANCELLED


class TrialResult(Base):
    __tablename__ = "trial_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    trial_id: Mapped[int] = mapped_column(ForeignKey("trials.id"), nullable=False)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    additional_content: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    trial: Mapped["Trial"] = relationship(back_populates="results")
    document: Mapped["Document"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "trial_id",
            "document_id",
            name="uq_trial_document",  # <-- prevents duplicates
        ),
        # The (trial_id, document_id) unique constraint covers trial_id-leading
        # lookups; document_id-only lookups (deletes, downloads, stats) need this.
        Index("ix_trial_results_document_id", "document_id"),
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

    __table_args__ = (
        Index("ix_evaluation_metrics_evaluation_id", "evaluation_id"),
        Index("ix_evaluation_metrics_document_id", "document_id"),
    )


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

    __table_args__ = (Index("ix_ground_truth_project_id", "project_id"),)


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

    __table_args__ = (
        Index("ix_evaluations_trial_id", "trial_id"),
        Index("ix_evaluations_groundtruth_id", "groundtruth_id"),
    )
