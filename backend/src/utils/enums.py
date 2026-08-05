# backend/src/utils/enums.py
import enum
from enum import Enum


class FileCreator(str, Enum):
    user = "user"
    system = "system"


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class ProjectPermission(str, Enum):
    """What a collaborator may do with a project shared with them.

    ``READ`` is view-only: every GET-shaped route, no mutations and no LLM/OCR
    egress. ``WRITE`` adds every mutation an owner can perform *except*
    deleting the project and managing its shares — those stay owner-only so a
    project always has exactly one accountable owner.
    """

    READ = "read"
    WRITE = "write"


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
    MARKER = "marker"


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


class AuditAction(str, enum.Enum):
    """Actions recorded in the append-only audit log.

    Grouped (by value prefix) into: authentication, authorization, PHI access,
    data mutations, external egress (patient data leaving to an LLM/OCR
    endpoint), and administrative changes. The enum is the single source of
    truth — the frontend audit filter mirrors these values.
    """

    # ── Authentication ──
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKED = "account_locked"
    SSO_LOGIN = "sso_login"

    # ── Authorization ──
    # An authenticated principal was refused a resource (project they don't own,
    # admin-only route). Always paired with ``AuditOutcome.DENIED``. Failed
    # *authentication* stays under LOGIN_FAILURE — this is the "logged in but
    # not allowed" case that surfaces probing by a compromised account.
    ACCESS_DENIED = "access_denied"

    # ── Access (reading PHI) ──
    DOCUMENT_VIEW = "document_view"
    DOCUMENT_DOWNLOAD = "document_download"
    FILE_DOWNLOAD = "file_download"
    TRIAL_RESULT_VIEW = "trial_result_view"
    EXPORT = "export"

    # ── Mutations ──
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    CANCEL = "cancel"

    # ── Egress (PHI leaves to an external service) ──
    LLM_EXTRACTION_CALL = "llm_extraction_call"
    OCR_EXTERNAL_CALL = "ocr_external_call"

    # ── Sharing ──
    # A project owner granted, changed, or revoked another user's access to a
    # project. Kept distinct from CREATE/UPDATE/DELETE because a share change
    # widens who can reach PHI, which reviewers need to be able to filter for.
    PROJECT_SHARE = "project_share"
    PROJECT_SHARE_UPDATE = "project_share_update"
    PROJECT_UNSHARE = "project_unshare"

    # ── Administration ──
    SETTING_CHANGE = "setting_change"
    USER_CREATE = "user_create"
    USER_ROLE_CHANGE = "user_role_change"
    USER_DEACTIVATE = "user_deactivate"
    INVITATION_SEND = "invitation_send"
    SSO_PROVIDER_CHANGE = "sso_provider_change"


class AuditOutcome(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


class TrialResultStatus(str, enum.Enum):
    """Outcome of a single document extraction within a trial.

    Mirrors the `ResultStatus` Literal in `utils/info_extraction.py` — the values
    are produced by `_determine_result_status` and persisted on `TrialResult.status`.
    """

    SUCCESS = "success"
    FAILED = "failed"
    INCOMPLETE = "incomplete"
    INVALID_JSON = "invalid_json"
    SCHEMA_INVALID = "schema_invalid"
    REFUSED = "refused"
    PROVIDER_ERROR = "provider_error"


class NotificationCategory(str, enum.Enum):
    """Groups of notification email a user can independently opt out of.

    Each value maps 1:1 to a boolean column on ``NotificationPreference`` and to
    a toggle in Account settings. Adding a category means adding the column, the
    toggle, and the catalog strings — the value itself is the contract between
    the three.
    """

    # A preprocessing task or extraction run reached a terminal state.
    JOB_FINISHED = "job_finished"
    # A project was shared with the recipient, or their permission changed.
    PROJECT_SHARED = "project_shared"
    # Account/security notices: password changed, account locked out, SSO
    # identity linked or unlinked.
    SECURITY = "security"
    # Operational alerts (worker crash, swept stuck tasks). Admins only.
    ADMIN_ALERTS = "admin_alerts"
