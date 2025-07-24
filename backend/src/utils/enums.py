import enum
from enum import Enum


class FileCreator(str, Enum):
    user = "user"
    system = "system"


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class FieldType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    CATEGORY = "category"
    DATE = "date"
    ARRAY = "array"
    OBJECT = "object"


class ComparisonMethod(str, Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    CATEGORY = "category"
    DATE = "date"


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
    APPLICATION_VND_MS_EXCEL = "application/vnd.ms-excel"  # Add this
    APPLICATION_VND_OPENXMLFORMATS_OFFICEDOCUMENT_SPREADSHEETML_SHEET = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  # Add this
    )
    IMAGE_JPEG = "image/jpeg"
    IMAGE_PNG = "image/png"
    IMAGE_SVG = "image/svg+xml"
    TEXT_PLAIN = "text/plain"
    TEXT_CSV = "text/csv"
    MIXED = "mixed"
    APPLICATION_XML = "application/xml"
    APPLICATION_JSON = "application/json"
    TEXT_RTF = "text/rtf"


class PreprocessingMethod(str, enum.Enum):
    TESSERACT = "tesseract"
    VISION_OCR = "vision_ocr"
    SURYA_OCR = "surya_ocr"


class PreprocessingStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PreprocessingStrategy(str, Enum):
    FULL_DOCUMENT = "full_document"
    ROW_BY_ROW = "row_by_row"
    CUSTOM = "custom"
