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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    REQUIRE_INVITATION: bool = True
    ALLOW_FIRST_ADMIN_SETUP: bool = True

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
    DOCLING_SERVE_TIMEOUT_SECONDS: int = 600
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

    # Per-file timeout (general default)
    PREPROCESS_FILE_TIMEOUT_SECONDS: int = Field(
        default=600,
        ge=60,
        le=7200,
        description="Default timeout in seconds for processing a single file",
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
    DOCLING_SERVE_FILE_TIMEOUT_SECONDS: int = Field(
        default=900,
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
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )
            print(
                f"INFO: SQLALCHEMY_DATABASE_URI not explicitly set — "
                f"derived from POSTGRES_* defaults: postgresql://{self.POSTGRES_USER}:****@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
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
                import traceback

                print(traceback.format_exc())
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
_settings_instance: Settings | None = None
_settings_lock = threading.Lock()


def _get_settings() -> Settings:
    """Get the live settings instance, initializing on first access.

    Thread-safe: the first access validates the config (OpenAI/S3 checks in
    Settings.__init__). Subsequent calls return the cached instance.
    """
    global _settings_instance
    if _settings_instance is None:
        with _settings_lock:
            if _settings_instance is None:
                try:
                    _settings_instance = Settings()
                except ValidationError as e:
                    print("Configuration Error:")
                    print(e)
                    print("Please check your .env file or environment variables.")
                    sys.exit(1)
    return _settings_instance


def apply_runtime_overrides(overrides: dict) -> None:
    """Apply DB-backed runtime overrides to the live settings singleton.

    Uses ``model_validate`` so DB string values are coerced to the correct
    field types (int/bool/etc.), but — unlike ``Settings(**overrides)`` — it
    does NOT re-run ``__init__``'s OpenAI/S3 network validation. That avoids
    latency and a potential ``sys.exit(1)`` on every admin settings save.

    Only call this after the singleton has been initialized (e.g. from
    ``dynamic_settings`` once the DB is available).
    """
    global _settings_instance
    if not overrides:
        return
    base = _get_settings()
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
    "DISABLE_CELERY": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Celery",
        "label": "Disable Celery",
    },
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
