import enum
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column
from sqlalchemy import String, Enum, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
from ..db.base import Base

from typing import TYPE_CHECKING

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
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False, length=10), default=ProjectStatus.ACTIVE
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
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
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    owner: Mapped["User"] = relationship(back_populates="projects")  # noqa: F821


class FileStorageType(str, enum.Enum):
    LOCAL = "local"
    S3 = "s3"


class FileType(str, enum.Enum):
    """MIMEs for image / application / text file types."""

    APPLICATION_PDF = "application/pdf"
    APPLICATION_MSWORD = "application/msword"
    APPLICATION_VND_OPENXMLFORMATS_OFFICEDOCUMENT_WORDPROCESSINGML_DOCUMENT = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    IMAGE_JPEG = "image/jpeg"
    IMAGE_PNG = "image/png"
    IMAGE_SVG = "image/svg+xml"
    TEXT_PLAIN = "text/plain"
    TEXT_CSV = "text/csv"


class File(Base):
    __tablename__ = "files"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    file_storage_type: Mapped[FileStorageType] = mapped_column(
        Enum(FileStorageType, native_enum=False, length=10),
        default=FileStorageType.LOCAL,
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType, native_enum=False, length=10), default=FileType.APPLICATION_PDF
    )
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    project: Mapped["Project"] = relationship(back_populates="files")
    documents_as_original: Mapped[list["Document"]] = relationship(
        foreign_keys="[Document.original_file_id]", back_populates="original_file"
    )
    documents_as_preprocessed: Mapped[list["Document"]] = relationship(
        foreign_keys="[Document.preprocessed_file_id]"
    )


class PreprocessingMethod(str, enum.Enum):
    TESSERACT = "tesseract"
    VISION_OCR = "vision_ocr"
    SURYA_OCR = "surya_ocr"


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    original_file_id: Mapped[int] = mapped_column(
        ForeignKey("files.id"), nullable=False
    )
    preprocessed_file_id: Mapped[int] = mapped_column(
        ForeignKey("files.id"), nullable=True
    )
    preprocessing_method: Mapped[PreprocessingMethod] = mapped_column(
        Enum(PreprocessingMethod, native_enum=False, length=20)
    )
    text: Mapped[str] = mapped_column(String, nullable=False)
    meta_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    project: Mapped["Project"] = relationship(back_populates="documents")
    original_file: Mapped["File"] = relationship(
        foreign_keys=[original_file_id], back_populates="documents_as_original"
    )
    preprocessed_file: Mapped["File"] = relationship(
        foreign_keys=[preprocessed_file_id]
    )
    document_set: Mapped["DocumentSet"] = relationship(back_populates="documents")


class DocumentSet(Base):
    __tablename__ = "document_sets"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    trial_id: Mapped[int] = mapped_column(ForeignKey("trials.id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    project: Mapped["Project"] = relationship(back_populates="document_sets")
    trial: Mapped["Trial"] = relationship(back_populates="document_set")
    documents: Mapped[list["Document"]] = relationship(back_populates="document_set")


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
        DateTime(timezone=True), onupdate=func.now()
    )
    project: Mapped["Project"] = relationship(back_populates="schemas")
    trials: Mapped[list["Trial"]] = relationship(back_populates="schema")


class Trial(Base):
    __tablename__ = "trials"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    schema_id: Mapped[int] = mapped_column(ForeignKey("schemas.id"), nullable=False)
    prompt: Mapped[str] = mapped_column(String(5000), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    trial_name: Mapped[str] = mapped_column(String(100), nullable=False)
    trial_description: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    project: Mapped["Project"] = relationship(back_populates="trials")
    schema: Mapped["Schema"] = relationship(back_populates="trials")
    document_set: Mapped["DocumentSet"] = relationship(
        back_populates="trial", uselist=False
    )
    results: Mapped[list["TrialResult"]] = relationship(
        back_populates="trial", cascade="all, delete-orphan"
    )


class TrialResult(Base):
    __tablename__ = "trial_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    trial_id: Mapped[int] = mapped_column(ForeignKey("trials.id"), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    trial: Mapped["Trial"] = relationship(back_populates="results")
