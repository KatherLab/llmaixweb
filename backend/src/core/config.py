# backend/src/core/config.py
import os
import sys
import threading
from pathlib import Path

import boto3
import openai
from botocore.exceptions import ClientError
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "LLMAIx (v2) backend"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = ""  # Must be set in .env — validated at startup
    # Access-token lifetime. Kept short for PHI: refresh tokens (rotated,
    # revocable) transparently re-issue access tokens, so a short access-token
    # window limits the blast radius of a leaked token without harming UX. The
    # frontend silently refreshes on 401. Was 8 days historically — override
    # via env if a longer session is genuinely required.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REQUIRE_INVITATION: bool = True
    ALLOW_FIRST_ADMIN_SETUP: bool = True
    # How long an invitation token remains valid after creation (hours).
    # 0 = never expire (not recommended — leaked invitation links never revoke).
    INVITATION_EXPIRE_HOURS: int = 24 * 7

    # ─────────────────────────────────────────────────────────────
    # Site-wide banner
    # ─────────────────────────────────────────────────────────────
    # An optional notice bar rendered at the very top of every page (e.g.
    # "Research Use Only!"). Exposed via the unauthenticated /auth/settings
    # endpoint so it shows on login/landing pages too. Configurable at runtime
    # from the admin settings panel.
    BANNER_ENABLED: bool = False
    BANNER_TEXT: str = ""
    # One of: amber, red, blue, green, gray. Controls the banner color scheme.
    BANNER_COLOR: str = "amber"

    # ─────────────────────────────────────────────────────────────
    # Password policy
    # ─────────────────────────────────────────────────────────────
    # Enforced centrally by utils.password_policy.validate_password,
    # which every password-setting endpoint calls in addition to the
    # Pydantic min/max length gates on the request schemas.
    PASSWORD_POLICY_MIN_LENGTH: int = Field(default=8, ge=8, le=128)
    PASSWORD_POLICY_MAX_LENGTH: int = Field(default=128, ge=8, le=256)
    PASSWORD_POLICY_REQUIRE_UPPERCASE: bool = True
    PASSWORD_POLICY_REQUIRE_LOWERCASE: bool = True
    PASSWORD_POLICY_REQUIRE_DIGIT: bool = True
    PASSWORD_POLICY_REQUIRE_SYMBOL: bool = False

    # ─────────────────────────────────────────────────────────────
    # Account lockout (login brute-force protection)
    # ─────────────────────────────────────────────────────────────
    # Per-user: after LOGIN_MAX_ATTEMPTS failed logins, the account is
    # locked for LOGIN_LOCKOUT_MINUTES. The IP rate limit (10/min on
    # /login) is the first line of defense; this is the per-account
    # backstop that survives distributed attacks across IPs.
    LOGIN_MAX_ATTEMPTS: int = Field(default=5, ge=1, le=50)
    LOGIN_LOCKOUT_MINUTES: int = Field(default=15, ge=1, le=1440)

    # ─────────────────────────────────────────────────────────────
    # SSO / OpenID Connect
    # ─────────────────────────────────────────────────────────────
    # Global feature flag. When False, all /auth/sso/* endpoints refuse
    # to start a flow (providers list is empty). Individual providers are
    # also toggled via IdentityProvider.enabled in the DB.
    SSO_ENABLED: bool = False
    # Fernet key for encrypting provider client_secret at rest. If empty,
    # a key is derived from SECRET_KEY via PBKDF2 (see utils.crypto).
    # Set explicitly only if you want to rotate independently of SECRET_KEY.
    SSO_CLIENT_SECRET_ENCRYPTION_KEY: str = ""
    # Role assigned to users auto-provisioned via SSO (JIT).
    SSO_JIT_DEFAULT_ROLE: str = "user"
    # When True, SSO login bypasses REQUIRE_INVITATION (standard for SSO —
    # the IdP is the trust source, not an invitation token).
    SSO_BYPASS_INVITATION: bool = True
    # When True (default), the IdP must assert `email_verified: true` before we
    # will link an SSO identity to (or provision) an account by email address.
    # This prevents account takeover: without it, an IdP that permits
    # self-asserted/unverified emails would let an attacker register
    # victim@clinic.com upstream and get merged into the victim's local account.
    SSO_REQUIRE_VERIFIED_EMAIL: bool = True

    # ─────────────────────────────────────────────────────────────
    # Refresh tokens
    # ─────────────────────────────────────────────────────────────
    # Refresh tokens are stored hashed (sha256) in the refresh_tokens
    # table, rotated on each use, and revocable. Issued alongside the
    # access token when the client opts in (login response includes
    # refresh_token only when this is enabled and the client requests it).
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, ge=1, le=365)

    # ─────────────────────────────────────────────────────────────
    # Egress allowlist (PHI destination control)
    # ─────────────────────────────────────────────────────────────
    # Comma-separated host allowlists for user-supplied LLM / OCR endpoints.
    # Empty (default) = any host allowed, subject to the SSRF policy. Set these
    # in a clinical deployment to guarantee patient data can only be sent to
    # your approved (ideally on-prem) endpoints. Matches exact host or subdomain
    # (e.g. "example.com" also permits "api.example.com").
    ALLOWED_LLM_ENDPOINTS: str = ""
    ALLOWED_OCR_ENDPOINTS: str = ""

    # ─────────────────────────────────────────────────────────────
    # Admin project visibility
    # ─────────────────────────────────────────────────────────────
    # By default admins can only see and manage their OWN projects, exactly
    # like a regular user. Set True to grant admins read/write access to ALL
    # users' projects. Intentionally env-only (NOT exposed in the admin
    # settings UI) so an admin can't grant themselves cross-user visibility at
    # runtime — it must be a deliberate deployment-level decision.
    ADMIN_ALL_PROJECT_ACCESS: bool = False

    # Skip runtime validation checks (useful for Alembic migrations)
    SKIP_RUNTIME_CHECKS: bool = False

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "llmaixweb"
    SQLALCHEMY_DATABASE_URI: str | None = None

    # storing files in S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_ENDPOINT_URL: str | None = None
    S3_BUCKET_NAME: str = "llmaixweb"

    # Alternative for storing files locally
    LOCAL_DIRECTORY: str | None = None

    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str | None = None
    OPENAI_API_MODEL: str = ""
    OPENAI_NO_API_CHECK: bool = False
    # Per-request timeout for LLM completion calls (seconds). The openai SDK
    # defaults to 600s; making it explicit + configurable bounds hung calls so
    # a single unresponsive endpoint can't stall a trial indefinitely.
    LLM_REQUEST_TIMEOUT_SECONDS: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Timeout in seconds for a single LLM completion request",
    )

    MISTRAL_API_BASE: str = "https://api.mistral.ai"
    MISTRAL_API_KEY: str = ""
    MISTRAL_OCR_ENABLED: bool = False
    MISTRAL_OCR_MODEL: str = "mistral-ocr-latest"
    MISTRAL_OCR_DISPLAY_NAME: str = "Mistral OCR API"
    MISTRAL_OCR_DISPLAY_SUBTITLE: str = "Best for complex layouts"

    # Separate API endpoint/config for Vision LLM OCR (independent of main LLM client)
    VISION_OCR_ENABLED: bool = False
    VISION_OCR_API_KEY: str = ""
    VISION_OCR_API_BASE: str = ""
    VISION_OCR_MODEL: str = "gpt-4o"
    VISION_OCR_PROMPT: str = (
        "Extract all text from this image and return it as clean markdown. "
        "Preserve the original structure, headings, lists, and formatting as much as possible."
    )
    VISION_OCR_DISPLAY_NAME: str = "Vision LLM API"
    VISION_OCR_DISPLAY_SUBTITLE: str = "Best for complex documents"

    # Docling-serve remote OCR service configuration
    DOCLING_SERVE_ENABLED: bool = False
    DOCLING_SERVE_URL: str = "http://docling-serve:5001"
    # HTTP read timeout for the (synchronous) /v1/convert/file call. Docling runs
    # its layout + table-structure models on every page even with OCR disabled,
    # so a large PDF can legitimately take many minutes on CPU (~6 min observed
    # for an 18 MB doc). This MUST be >= DOCLING_SERVE_FILE_TIMEOUT_SECONDS,
    # otherwise the HTTP read aborts before the per-file budget is spent and a
    # slow-but-valid conversion is lost as a timeout.
    DOCLING_SERVE_TIMEOUT_SECONDS: int = 1800
    DOCLING_SERVE_MAX_RETRIES: int = 1
    DOCLING_SERVE_DISPLAY_NAME: str = "Quick (Local OCR)"
    DOCLING_SERVE_DISPLAY_SUBTITLE: str = "Docling / Tesseract"

    # Default OCR settings for docling-serve
    # Use "auto" for automatic language detection, or specify languages (e.g., "deu,eng" or ["deu", "eng"])
    DOCLING_DEFAULT_OCR_LANGS: list[str] | str = Field(default="auto")
    DOCLING_DEFAULT_TABLE_MODE: str = "fast"
    DOCLING_IMAGE_EXPORT_MODE: str = "placeholder"

    # Text extraction thresholds for quality checks (embedded text detection)
    DOCLING_MIN_EXTRACTED_CHARS_PDF: int = 100
    DOCLING_MIN_EXTRACTED_CHARS_IMAGE: int = 20

    # Remote OCR fallback (Mistral/Vision) - disabled by default for privacy
    REMOTE_OCR_FALLBACK_ENABLED: bool = False

    # Local Docling fallback for testing (when docling-serve is unavailable)
    DOCLING_LOCAL_FALLBACK: bool = False

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    LOG_LEVEL: str = "INFO"
    # "text" (human-readable, default) or "json" (structured, one object per
    # line — feed this to a SIEM/Loki in production). Every record carries the
    # per-request correlation id.
    LOG_FORMAT: str = "text"

    DISABLE_CELERY: bool = False
    INITIALIZE_CELERY: bool = True  # Whether to initialize Celery workers on startup
    DISABLE_RATE_LIMIT: bool = False  # Disable rate limiting (for tests)

    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"
    APP_URL: str = "http://localhost:5173"

    # Email / SMTP settings
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_ADDRESS: str = ""
    SMTP_FROM_NAME: str = "LLMAIx Web"
    SMTP_USE_TLS: bool = True

    CELERY_PREPROCESS_POOL: str = Field(
        default="auto",  # auto | solo | prefork
        description="How to start the preprocess worker pool",
    )  # Has to be solo for MacOS to avoid

    # ─────────────────────────────────────────────────────────────
    # Preprocessing Performance & Concurrency Settings
    # ─────────────────────────────────────────────────────────────

    # General file processing concurrency (max concurrent files in Celery task)
    PREPROCESS_MAX_CONCURRENT_FILES: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of files to process concurrently in a single preprocessing task",
    )

    # A preprocessing task processes at most this many files per Celery
    # execution, then re-enqueues itself (to the back of the queue) to continue
    # the rest. This keeps each execution well under the task time limit / broker
    # visibility timeout (so large batches finish instead of being killed), and
    # interleaves different users' batches fairly at chunk granularity.
    PREPROCESS_CHUNK_SIZE: int = Field(
        default=200,
        ge=1,
        le=100000,
        description="Max files processed per preprocessing task execution before it re-enqueues itself to continue",
    )

    CELERY_TASK_SOFT_TIME_LIMIT_SECONDS: int = Field(
        default=21600,  # 6 hours
        ge=300,
        le=86400,
        description=(
            "Celery soft time limit for a task execution (applied at worker "
            "boot). Also used to size each preprocessing self-requeue chunk so a "
            "single run can't exceed this limit even if every file runs to its "
            "full per-file timeout."
        ),
    )

    # Per-file timeout (general default)
    PREPROCESS_FILE_TIMEOUT_SECONDS: int = Field(
        default=600,
        ge=60,
        le=7200,
        description="Default timeout in seconds for processing a single file",
    )

    # ─────────────────────────────────────────────────────────────
    # Orphaned-task recovery (crash / restart detection)
    # ─────────────────────────────────────────────────────────────
    # A preprocessing file task heartbeats every ~15s while alive and a trial
    # bumps updated_at every few seconds, so a non-terminal task whose last
    # heartbeat is older than this is assumed to have a dead worker. Kept low
    # (8+ missed heartbeats) so a crashed worker is detected in ~2 min instead
    # of the old 10 min — well clear of a transient DB blip. The per-file OCR
    # timeout (up to 2h) is irrelevant here: a slow-but-alive file keeps
    # heartbeating, so it's never falsely reaped.
    ORPHAN_STALE_SECONDS: int = Field(
        default=120,
        ge=30,
        le=3600,
        description="Seconds since last heartbeat before a running task is treated as orphaned by the sweeper",
    )

    # How often the periodic sweeper runs. Short so a crashed (not restarted)
    # worker's tasks are finalized promptly; a restart is handled instantly by
    # the worker-startup reclaim, independent of this interval.
    ORPHAN_SWEEP_INTERVAL_SECONDS: int = Field(
        default=60,
        ge=15,
        le=3600,
        description="Interval in seconds between periodic orphaned-task sweeps",
    )

    # ─────────────────────────────────────────────────────────────
    # OCR Backend-Specific Concurrency Settings
    # ─────────────────────────────────────────────────────────────

    # Docling-serve (local Tesseract) concurrency
    DOCLING_SERVE_MAX_CONCURRENT_FILES: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum concurrent files for docling-serve OCR",
    )
    # Per-file processing budget for the docling-serve path. Covers the whole
    # conversion (layout + table models, plus Tesseract OCR when enabled), which
    # is CPU-bound and slow for large PDFs. Kept generous (30 min) so big/scanned
    # docs aren't falsely reaped; a genuinely stuck file only blocks one of the
    # DOCLING_SERVE_MAX_CONCURRENT_FILES slots until this elapses. The pipeline
    # heartbeats every ~15s throughout, so the orphan sweeper (ORPHAN_STALE_
    # SECONDS) never trips while a conversion this long is actually running.
    # Keep DOCLING_SERVE_TIMEOUT_SECONDS (the HTTP read timeout) >= this value.
    DOCLING_SERVE_FILE_TIMEOUT_SECONDS: int = Field(
        default=1800,
        ge=60,
        le=7200,
        description="Timeout in seconds for docling-serve OCR per file",
    )

    # Mistral OCR API concurrency
    MISTRAL_OCR_MAX_CONCURRENT_FILES: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum concurrent files for Mistral OCR API",
    )
    MISTRAL_OCR_FILE_TIMEOUT_SECONDS: int = Field(
        default=600,
        ge=60,
        le=7200,
        description="Timeout in seconds for Mistral OCR API per file",
    )
    MISTRAL_OCR_MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for Mistral OCR API requests",
    )

    # Vision LLM OCR concurrency
    VISION_OCR_MAX_CONCURRENT_FILES: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum concurrent files for Vision LLM OCR API",
    )
    VISION_OCR_FILE_TIMEOUT_SECONDS: int = Field(
        default=600,
        ge=60,
        le=7200,
        description="Timeout in seconds for Vision LLM OCR API per file",
    )
    VISION_OCR_MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for Vision LLM OCR API requests",
    )

    # ─────────────────────────────────────────────────────────────
    # CSV/Excel Processing Settings
    # ─────────────────────────────────────────────────────────────

    # CSV encoding detection
    CSV_ENCODING_FALLBACK_CHAIN: str = Field(
        default="utf-8,cp1252,latin-1,iso-8859-1",
        description="Comma-separated list of encodings to try when reading CSV files",
    )
    CSV_DETECT_ENCODING: bool = Field(
        default=True,
        description="Enable automatic encoding detection for CSV files",
    )

    # ─────────────────────────────────────────────────────────────
    # PDF Processing Settings
    # ─────────────────────────────────────────────────────────────

    PDF_CHECK_EMBEDDED_TEXT: bool = Field(
        default=True,
        description="Check for embedded text in PDFs before OCR",
    )
    PDF_MAX_PAGES_FOR_TEXT_PROBE: int = Field(
        default=8,
        ge=1,
        le=50,
        description="Maximum pages to sample when checking for embedded text",
    )
    PDF_HANDLE_PASSWORD_PROTECTED: bool = Field(
        default=False,
        description="Attempt to handle password-protected PDFs (requires pypdf with encryption support)",
    )

    # ─────────────────────────────────────────────────────────────
    # Image Processing Settings
    # ─────────────────────────────────────────────────────────────

    IMAGE_MAX_DIMENSION: int = Field(
        default=4096,
        ge=512,
        le=16384,
        description="Maximum image dimension - larger images will be resized before OCR",
    )
    IMAGE_HANDLE_EXIF_ROTATION: bool = Field(
        default=True,
        description="Apply EXIF orientation tag correction before OCR",
    )

    # ─────────────────────────────────────────────────────────────
    # Streaming & Memory Settings
    # ─────────────────────────────────────────────────────────────

    FILE_STREAMING_THRESHOLD_BYTES: int = Field(
        default=52428800,  # 50MB
        ge=1048576,
        le=524288000,
        description="File size threshold above which streaming downloads are used",
    )
    FILE_STREAM_CHUNK_SIZE: int = Field(
        default=8192,
        ge=1024,
        le=1048576,
        description="Chunk size for streaming file downloads",
    )
    MAX_UPLOAD_SIZE_BYTES: int = Field(
        default=524288000,  # 500MB
        ge=1048576,  # at least 1MB
        le=5368709120,  # cap at 5GB
        description="Maximum allowed size for a single uploaded file (files/ground truth)",
    )

    # ─────────────────────────────────────────────────────────────
    # Logging & Debugging
    # ─────────────────────────────────────────────────────────────

    PREPROCESS_LOG_DOCUMENT_IDS: bool = Field(
        default=False,
        description="Log document IDs during creation (verbose)",
    )

    @property
    def BACKEND_CORS_ORIGINS_LIST(self):
        if not self.BACKEND_CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]

    # Determine .env file path - used only if file exists and is readable
    _env_path = Path(os.getenv("ENV_PATH", "backend/.env"))
    _env_file_to_load = None

    # Check if .env file exists and is readable (handle permission errors gracefully)
    try:
        if _env_path.exists() and _env_path.is_file():
            _env_file_to_load = str(_env_path)
            print("Loading configuration from .env file at: ", _env_path.absolute())
        else:
            # Running in Docker with environment variables only
            if os.getenv("DOCKER_ENV", "false").lower() == "true":
                pass  # Silent - expected in Docker
            else:
                print(
                    f"Note: .env file not found at {_env_path.absolute()}, using environment variables only."
                )
    except (PermissionError, OSError):
        # File might exist but not be readable, or parent directory not accessible
        # Fall back to environment variables only
        if os.getenv("DOCKER_ENV", "false").lower() != "true":
            print(
                f"Note: Cannot access .env file at {_env_path.absolute()}, using environment variables only."
            )

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=_env_file_to_load,
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields not defined in the model
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # raise ValueError("Reading .env file from ", os.getenv("ENV_PATH", "backend/.env"), "Current working directory: ", os.getcwd())

        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = (
                f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )
            print(
                f"INFO: SQLALCHEMY_DATABASE_URI not explicitly set — "
                f"derived from POSTGRES_* defaults: postgresql+psycopg://{self.POSTGRES_USER}:****@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

        # Skip runtime checks for operations like Alembic migrations
        if self.SKIP_RUNTIME_CHECKS:
            return

        # SECRET_KEY is required — refuse to start with a default/empty value
        if not self.SECRET_KEY or len(self.SECRET_KEY) < 16:
            print(
                "ERROR: SECRET_KEY must be explicitly set in your .env file "
                "(at least 16 characters). Do not rely on a default.\n"
                'Generate one with:  python3 -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
            sys.exit(1)

        if not self.OPENAI_NO_API_CHECK:
            if not self.OPENAI_API_KEY:
                print("OPENAI_API_KEY is not set. Please set it in your .env file.")
                sys.exit(1)
            print("Initializing OpenAI client with BASE URL:", self.OPENAI_API_BASE)
            client = openai.OpenAI(
                api_key=self.OPENAI_API_KEY, base_url=self.OPENAI_API_BASE
            )
            try:
                models = client.models.list()

                if self.OPENAI_API_MODEL:
                    assert self.OPENAI_API_MODEL in [
                        model.id for model in models.data
                    ], (
                        f"Model {self.OPENAI_API_MODEL} not found in available models: {', '.join([model.id for model in models.data])}"
                    )

                print("LLM API Connection Successful")
            except openai.APIConnectionError as e:
                print("LLM API Connection Error: ", e)
                sys.exit(1)
            except Exception as e:
                print("LLM API Connection Error: ", e)
                sys.exit(1)

        if self.LOCAL_DIRECTORY:
            path = Path(self.LOCAL_DIRECTORY)
            if not path.exists():
                print(
                    f"Local directory {self.LOCAL_DIRECTORY} does not exist. Please create it or configure S3."
                )
                sys.exit(1)
            else:
                print(f"Using local directory for file storage: {self.LOCAL_DIRECTORY}")
        elif self.AWS_SECRET_ACCESS_KEY and self.AWS_ACCESS_KEY_ID:
            if not self.S3_ENDPOINT_URL:
                print("S3_ENDPOINT_URL is not set. Please set it in your .env file.")
                sys.exit(1)
            if not self.S3_BUCKET_NAME:
                print("S3_BUCKET_NAME is not set. Please set it in your .env file.")
                sys.exit(1)

            try:
                if self.S3_ENDPOINT_URL:
                    s3 = boto3.client(
                        "s3",
                        endpoint_url=self.S3_ENDPOINT_URL,
                        aws_access_key_id=self.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY,
                    )
                else:
                    s3 = boto3.client(
                        "s3",
                        aws_access_key_id=self.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY,
                    )
                s3.head_bucket(Bucket=self.S3_BUCKET_NAME)
                print(f"Connected to S3 bucket: {self.S3_BUCKET_NAME}")
            except ClientError as client_error:
                print(f"Error connecting to S3: {client_error}")
                if "HeadBucket" in str(client_error) and "Not Found" in str(
                    client_error
                ):
                    print(
                        f"Probably the bucket {self.S3_BUCKET_NAME} does not exist or you do not have access to it."
                    )
                if "HeadBucket" in str(client_error) and "Forbidden" in str(
                    client_error
                ):
                    print(
                        f"Access to the bucket {self.S3_BUCKET_NAME} is forbidden. Please check your AWS credentials."
                    )
                sys.exit(1)
            except Exception as exception:
                print(f"Unexpected error connecting to S3: {exception}")
                sys.exit(1)
        else:
            print(
                "Neither LOCAL_DIRECTORY nor S3 credentials are set. Please configure one of them in your .env file."
            )
            sys.exit(1)


# Lazy initialization - settings are validated only when first accessed
# This avoids requiring .env file for operations like Alembic migrations
#
# Two instances are tracked:
#   * ``_base_settings_instance`` — the pristine, env/.env-only config, built
#     once. Runtime overrides are always applied ON TOP of this so that
#     *removing* an override (admin resets a field to its default, deleting the
#     DB row) correctly reverts the live value. Merging onto the already-
#     overridden instance instead would make overrides purely additive and
#     stick forever.
#   * ``_settings_instance`` — the effective config (base + current overrides),
#     which is what ``_get_settings()`` / the proxy return.
_settings_instance: Settings | None = None
_base_settings_instance: Settings | None = None
_settings_lock = threading.Lock()


def _get_settings() -> Settings:
    """Get the live settings instance, initializing on first access.

    Thread-safe: the first access validates the config (OpenAI/S3 checks in
    Settings.__init__). Subsequent calls return the cached instance.
    """
    global _settings_instance, _base_settings_instance
    if _settings_instance is None:
        with _settings_lock:
            if _settings_instance is None:
                try:
                    _base_settings_instance = Settings()
                except ValidationError as e:
                    print("Configuration Error:")
                    print(e)
                    print("Please check your .env file or environment variables.")
                    sys.exit(1)
                # No overrides applied yet: effective == pristine base.
                _settings_instance = _base_settings_instance
    return _settings_instance


def apply_runtime_overrides(overrides: dict) -> None:
    """Apply DB-backed runtime overrides to the live settings singleton.

    Uses ``model_validate`` so DB string values are coerced to the correct
    field types (int/bool/etc.), but — unlike ``Settings(**overrides)`` — it
    does NOT re-run ``__init__``'s OpenAI/S3 network validation. That avoids
    latency and a potential ``sys.exit(1)`` on every admin settings save.

    Overrides are always merged onto the pristine ``_base_settings_instance``
    (NOT the currently-overridden one), so that dropping an override — i.e.
    passing an ``overrides`` dict that no longer contains a key — reverts that
    field to its env/.env default instead of retaining the last override.

    Only call this after the singleton has been initialized (e.g. from
    ``dynamic_settings`` once the DB is available).
    """
    global _settings_instance
    # Ensure the pristine base is initialized, then merge onto it.
    _get_settings()
    base = _base_settings_instance
    if not overrides:
        # No active overrides — effective settings are exactly the base.
        _settings_instance = base
        return
    merged = {**base.model_dump(), **overrides}
    _settings_instance = Settings.model_validate(merged)


class _SettingsProxy:
    """Transparent proxy to the live :class:`Settings` instance.

    ``from ..core.config import settings`` binds this proxy rather than a
    concrete ``Settings`` object, so attribute access always reads the current
    ``_settings_instance``. This lets runtime overrides applied via
    :func:`apply_runtime_overrides` (triggered by the admin panel through
    ``dynamic_settings.reload_settings_cache``) propagate to modules that
    captured ``settings`` at import time. Attribute access is O(1) after the
    first load (the instance is cached in ``_settings_instance``).
    """

    __slots__ = ()

    def __getattr__(self, name: str):
        return getattr(_get_settings(), name)

    def __repr__(self) -> str:
        return f"<_SettingsProxy -> {_get_settings()!r}>"


#: Module-level settings accessor. Use ``from ..core.config import settings``
#: or ``from ..core import config; config.settings`` — both resolve to this
#: proxy, which always reflects the latest runtime overrides.
settings = _SettingsProxy()


def __getattr__(name: str) -> Settings:
    """Lazy load settings on first attribute access (fallback)."""
    if name == "settings":
        return _get_settings()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


SETTINGS_META = {
    "PROJECT_NAME": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "General",
        "label": "Project Name",
    },
    "API_V1_STR": {
        "type": "str",
        "secret": False,
        "readonly": True,
        "category": "General",
        "label": "API Prefix",
    },
    "BANNER_ENABLED": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "General",
        "label": "Show Banner",
        "help": "Show a site-wide notice bar at the top of every page (e.g. 'Research Use Only!').",
    },
    "BANNER_TEXT": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "General",
        "label": "Banner Text",
        "help": "Text shown in the site-wide banner when enabled.",
    },
    "BANNER_COLOR": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "General",
        "label": "Banner Color",
        "help": "Banner color scheme: amber, red, blue, green, or gray.",
    },
    "SECRET_KEY": {
        "type": "str",
        "secret": True,
        "readonly": True,
        "category": "Security",
        "label": "Secret Key",
    },
    "ACCESS_TOKEN_EXPIRE_MINUTES": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Token Expiry (min)",
    },
    "REQUIRE_INVITATION": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Require Invitation",
    },
    "INVITATION_EXPIRE_HOURS": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Invitation Expiry (hours)",
    },
    "PASSWORD_POLICY_MIN_LENGTH": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Password Min Length",
        "help": "Minimum password length enforced by the shared password validator (8-128).",
    },
    "PASSWORD_POLICY_MAX_LENGTH": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Password Max Length",
    },
    "PASSWORD_POLICY_REQUIRE_UPPERCASE": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Require Uppercase",
    },
    "PASSWORD_POLICY_REQUIRE_LOWERCASE": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Require Lowercase",
    },
    "PASSWORD_POLICY_REQUIRE_DIGIT": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Require Digit",
    },
    "PASSWORD_POLICY_REQUIRE_SYMBOL": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Require Symbol",
    },
    "LOGIN_MAX_ATTEMPTS": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Max Login Attempts",
        "help": "Failed logins before an account is temporarily locked (1-50).",
    },
    "LOGIN_LOCKOUT_MINUTES": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Lockout Duration (min)",
    },
    "SSO_ENABLED": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "SSO",
        "label": "SSO Enabled",
        "help": "Global feature flag for OpenID Connect single sign-on. Individual providers are configured in the SSO admin panel.",
    },
    "SSO_CLIENT_SECRET_ENCRYPTION_KEY": {
        "type": "str",
        "secret": True,
        "readonly": True,
        "category": "SSO",
        "label": "SSO Secret Encryption Key",
    },
    "SSO_JIT_DEFAULT_ROLE": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "SSO",
        "label": "JIT Default Role",
        "help": "Role assigned to users auto-created on first SSO login (user/admin).",
    },
    "SSO_BYPASS_INVITATION": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "SSO",
        "label": "SSO Bypass Invitation",
        "help": "When True, SSO login ignores REQUIRE_INVITATION (the IdP is the trust source).",
    },
    "SSO_REQUIRE_VERIFIED_EMAIL": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "SSO",
        "label": "SSO Require Verified Email",
        "help": "When True, the IdP must assert email_verified before an SSO identity is linked to or provisions an account by email. Prevents account takeover via unverified emails. Keep enabled unless every configured IdP verifies emails.",
    },
    "REFRESH_TOKEN_EXPIRE_DAYS": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Refresh Token Expiry (days)",
        "help": "Lifetime of refresh tokens (1-365 days). Refresh tokens are rotated on each use and revocable.",
    },
    "ALLOWED_LLM_ENDPOINTS": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Allowed LLM Endpoints",
        "help": "Comma-separated host allowlist for LLM extraction endpoints. Empty = any host (SSRF policy still applies). Set to restrict where patient data can be sent (e.g. on-prem hosts only).",
    },
    "ALLOWED_OCR_ENDPOINTS": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "Security",
        "label": "Allowed OCR Endpoints",
        "help": "Comma-separated host allowlist for custom OCR endpoints. Empty = any host (SSRF policy still applies).",
    },
    "POSTGRES_SERVER": {
        "type": "str",
        "secret": False,
        "readonly": True,
        "category": "Database",
        "label": "DB Host",
    },
    "POSTGRES_USER": {
        "type": "str",
        "secret": False,
        "readonly": True,
        "category": "Database",
        "label": "DB User",
    },
    "POSTGRES_PASSWORD": {
        "type": "str",
        "secret": True,
        "readonly": True,
        "category": "Database",
        "label": "DB Password",
    },
    "POSTGRES_DB": {
        "type": "str",
        "secret": False,
        "readonly": True,
        "category": "Database",
        "label": "DB Name",
    },
    "SQLALCHEMY_DATABASE_URI": {
        "type": "str",
        # Secret: the assembled URI embeds the DB password
        # (postgresql://user:password@host/db). Marking it secret masks it in
        # the admin GET /settings response, where a plain secret:False would
        # otherwise expose the database credentials.
        "secret": True,
        "readonly": True,
        "category": "Database",
        "label": "DB URI",
    },
    "AWS_ACCESS_KEY_ID": {
        "type": "str",
        "secret": True,
        "readonly": True,
        "category": "Storage",
        "label": "AWS Access Key",
    },
    "AWS_SECRET_ACCESS_KEY": {
        "type": "str",
        "secret": True,
        "readonly": True,
        "category": "Storage",
        "label": "AWS Secret Key",
    },
    "S3_ENDPOINT_URL": {
        "type": "str",
        "secret": False,
        "readonly": True,
        "category": "Storage",
        "label": "S3 Endpoint",
    },
    "S3_BUCKET_NAME": {
        "type": "str",
        "secret": False,
        "readonly": True,
        "category": "Storage",
        "label": "S3 Bucket",
    },
    "LOCAL_DIRECTORY": {
        "type": "str",
        "secret": False,
        "readonly": True,
        "category": "Storage",
        "label": "Local Directory",
    },
    "OPENAI_API_KEY": {
        "type": "str",
        "secret": True,
        "readonly": False,
        "category": "OpenAI",
        "label": "OpenAI API Key",
    },
    "OPENAI_API_BASE": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "OpenAI",
        "label": "OpenAI API Base URL",
    },
    "OPENAI_API_MODEL": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "OpenAI",
        "label": "OpenAI API Model",
    },
    "OPENAI_NO_API_CHECK": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "OpenAI",
        "label": "Skip OpenAI Check",
    },
    "LOG_LEVEL": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "General",
        "label": "Log Level",
    },
    "LOG_FORMAT": {
        "type": "str",
        "secret": False,
        "readonly": True,
        "category": "General",
        "label": "Log Format",
        "help": "Log output format: 'text' (human-readable) or 'json' (structured for a SIEM). Applied at process startup.",
    },
    # NOTE: DISABLE_CELERY is intentionally NOT exposed here. It disables
    # background processing entirely (no workers, no queue, no sweeper):
    # non-bypass preprocessing/trial submissions are refused with a 503, and
    # only the admin-only bypass_celery paths run (synchronously, in-process).
    # Test/dev only and dangerous in production, so it is configurable via
    # environment variable only — never the UI.
    "EMAIL_ENABLED": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Email",
        "label": "Email Enabled",
    },
    "SMTP_HOST": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "Email",
        "label": "SMTP Host",
    },
    "SMTP_PORT": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Email",
        "label": "SMTP Port",
    },
    "SMTP_USERNAME": {
        "type": "str",
        "secret": True,
        "readonly": False,
        "category": "Email",
        "label": "SMTP Username",
    },
    "SMTP_PASSWORD": {
        "type": "str",
        "secret": True,
        "readonly": False,
        "category": "Email",
        "label": "SMTP Password",
    },
    "SMTP_FROM_ADDRESS": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "Email",
        "label": "From Address",
    },
    "SMTP_FROM_NAME": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "Email",
        "label": "From Name",
    },
    "SMTP_USE_TLS": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Email",
        "label": "Use TLS",
    },
    "BACKEND_CORS_ORIGINS": {
        "type": "str",
        "secret": False,
        "readonly": True,
        "category": "General",
        "label": "CORS Origins",
    },
    "APP_URL": {
        "type": "str",
        "secret": False,
        "readonly": True,
        "category": "General",
        "label": "App URL",
    },
    "MISTRAL_OCR_ENABLED": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Mistral OCR Enabled",
    },
    "MISTRAL_OCR_MODEL": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Mistral OCR Model",
        "help": "Model name for Mistral OCR (e.g., 'mistral-ocr-latest'). Used for display/metadata when using custom Mistral OCR endpoints.",
    },
    "MISTRAL_OCR_DISPLAY_NAME": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Mistral OCR Display Name",
    },
    "MISTRAL_OCR_DISPLAY_SUBTITLE": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Mistral OCR Display Subtitle",
    },
    "VISION_OCR_ENABLED": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Vision LLM OCR Enabled",
        "help": "Enable/disable the Vision LLM OCR engine. Can be overridden via .env file (VISION_OCR_ENABLED).",
    },
    "VISION_OCR_DISPLAY_NAME": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Vision OCR Display Name",
    },
    "VISION_OCR_DISPLAY_SUBTITLE": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Vision OCR Display Subtitle",
    },
    "VISION_OCR_PROMPT": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Vision OCR Prompt",
    },
    "DOCLING_SERVE_ENABLED": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Local OCR Enabled",
        "help": "Enable/disable the local OCR engine (Docling/Tesseract). If disabled along with other OCR engines, PDF/image preprocessing will not be available.",
    },
    "DOCLING_SERVE_DISPLAY_NAME": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Local OCR Display Name",
        "help": "Display name for the local OCR engine in the UI.",
    },
    "DOCLING_SERVE_DISPLAY_SUBTITLE": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Local OCR Display Subtitle",
        "help": "Subtitle for the local OCR engine in the UI.",
    },
    "DOCLING_SERVE_URL": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "docling-serve",
        "label": "docling-serve URL",
    },
    "DOCLING_SERVE_TIMEOUT_SECONDS": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "docling-serve",
        "label": "docling-serve Timeout (seconds)",
    },
    "DOCLING_SERVE_MAX_RETRIES": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "docling-serve",
        "label": "docling-serve Max Retries",
    },
    "DOCLING_DEFAULT_OCR_LANGS": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Default OCR Languages",
        "help": "Use 'auto' for automatic language detection (recommended), or specify languages as comma-separated values (e.g., 'deu,eng' or 'eng').",
    },
    "DOCLING_DEFAULT_TABLE_MODE": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "docling-serve",
        "label": "Table Mode",
    },
    "DOCLING_IMAGE_EXPORT_MODE": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "docling-serve",
        "label": "Image Export Mode",
    },
    "DOCLING_MIN_EXTRACTED_CHARS_PDF": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Min Extracted Chars (PDF)",
    },
    "DOCLING_MIN_EXTRACTED_CHARS_IMAGE": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Min Extracted Chars (Image)",
    },
    "REMOTE_OCR_FALLBACK_ENABLED": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "OCR",
        "label": "Remote OCR Fallback Enabled",
    },
    "DOCLING_LOCAL_FALLBACK": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "docling-serve",
        "label": "Local Docling Fallback Enabled",
    },
    # Preprocessing Performance & Concurrency
    "PREPROCESS_MAX_CONCURRENT_FILES": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Max Concurrent Files",
        "help": "Maximum number of files to process concurrently in a single preprocessing task (1-20)",
    },
    "PREPROCESS_CHUNK_SIZE": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Preprocessing Chunk Size",
        "help": "Files processed per preprocessing task execution before it re-enqueues itself to continue. Keeps large batches under the task time limit and interleaves users' batches fairly.",
    },
    "CELERY_TASK_SOFT_TIME_LIMIT_SECONDS": {
        "type": "int",
        "secret": False,
        "readonly": True,
        "category": "Preprocessing",
        "label": "Celery Task Soft Time Limit (seconds)",
        "help": "Soft time limit for a Celery task execution (applied at worker boot; restart workers to change). Preprocessing sizes each self-requeue chunk to stay under this even in the worst case.",
    },
    "PREPROCESS_FILE_TIMEOUT_SECONDS": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "File Timeout (seconds)",
        "help": "Default timeout in seconds for processing a single file (60-7200)",
    },
    # Docling-serve specific settings
    "DOCLING_SERVE_MAX_CONCURRENT_FILES": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Docling Max Concurrent Files",
        "help": "Maximum concurrent files for docling-serve OCR (1-10)",
    },
    "DOCLING_SERVE_FILE_TIMEOUT_SECONDS": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Docling File Timeout (seconds)",
        "help": "Timeout in seconds for docling-serve OCR per file (60-7200)",
    },
    # Mistral OCR specific settings
    "MISTRAL_OCR_MAX_CONCURRENT_FILES": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Mistral Max Concurrent Files",
        "help": "Maximum concurrent files for Mistral OCR API (1-10)",
    },
    "MISTRAL_OCR_FILE_TIMEOUT_SECONDS": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Mistral File Timeout (seconds)",
        "help": "Timeout in seconds for Mistral OCR API per file (60-7200)",
    },
    "MISTRAL_OCR_MAX_RETRIES": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Mistral Max Retries",
        "help": "Maximum retry attempts for Mistral OCR API requests (0-10)",
    },
    # Vision LLM OCR specific settings
    "VISION_OCR_MAX_CONCURRENT_FILES": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Vision Max Concurrent Files",
        "help": "Maximum concurrent files for Vision LLM OCR API (1-10)",
    },
    "VISION_OCR_FILE_TIMEOUT_SECONDS": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Vision File Timeout (seconds)",
        "help": "Timeout in seconds for Vision LLM OCR API per file (60-7200)",
    },
    "VISION_OCR_MAX_RETRIES": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Vision Max Retries",
        "help": "Maximum retry attempts for Vision LLM OCR API requests (0-10)",
    },
    # CSV/Excel processing settings
    "CSV_ENCODING_FALLBACK_CHAIN": {
        "type": "str",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "CSV Encoding Fallback Chain",
        "help": "Comma-separated list of encodings to try when reading CSV files (e.g., 'utf-8,cp1252,latin-1')",
    },
    "CSV_DETECT_ENCODING": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Auto-detect CSV Encoding",
        "help": "Enable automatic encoding detection for CSV files before using fallback chain",
    },
    # PDF processing settings
    "PDF_CHECK_EMBEDDED_TEXT": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Check PDF Embedded Text",
        "help": "Check for embedded text in PDFs before applying OCR",
    },
    "PDF_MAX_PAGES_FOR_TEXT_PROBE": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "PDF Text Probe Max Pages",
        "help": "Maximum pages to sample when checking for embedded text (1-50)",
    },
    "PDF_HANDLE_PASSWORD_PROTECTED": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Handle Password-Protected PDFs",
        "help": "Attempt to handle password-protected PDFs (requires pypdf with encryption support)",
    },
    # Image processing settings
    "IMAGE_MAX_DIMENSION": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Max Image Dimension",
        "help": "Maximum image dimension - larger images will be resized before OCR (512-16384)",
    },
    "IMAGE_HANDLE_EXIF_ROTATION": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Apply EXIF Rotation",
        "help": "Apply EXIF orientation tag correction before OCR",
    },
    # Streaming & Memory settings
    "FILE_STREAMING_THRESHOLD_BYTES": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "File Streaming Threshold (bytes)",
        "help": "File size threshold above which streaming downloads are used (default 50MB)",
    },
    "FILE_STREAM_CHUNK_SIZE": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "File Stream Chunk Size",
        "help": "Chunk size for streaming file downloads in bytes (default 8KB)",
    },
    "MAX_UPLOAD_SIZE_BYTES": {
        "type": "int",
        "secret": False,
        "readonly": False,
        "category": "Storage",
        "label": "Max Upload Size (bytes)",
        "help": "Maximum allowed size for a single uploaded file, e.g. PDFs/images/ground truth (default 500MB). Uploads exceeding this are rejected with 413 before being fully read.",
    },
    # Logging & Debugging
    "PREPROCESS_LOG_DOCUMENT_IDS": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Preprocessing",
        "label": "Log Document IDs",
        "help": "Log document IDs during creation (verbose, for debugging)",
    },
}
