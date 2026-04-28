import os
import secrets
import sys
from pathlib import Path

import boto3
import openai
from botocore.exceptions import ClientError
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "LLMAIx (v2) backend"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    REQUIRE_INVITATION: bool = True
    ALLOW_FIRST_ADMIN_SETUP: bool = True

    # Skip runtime validation checks (useful for Alembic migrations)
    SKIP_RUNTIME_CHECKS: bool = False

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "llmaixweb"
    SQLALCHEMY_DATABASE_URI: str | None = "sqlite:///database.db"

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

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    DISABLE_CELERY: bool = False
    INITIALIZE_CELERY: bool = True  # Whether to initialize Celery workers on startup

    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"

    CELERY_PREPROCESS_POOL: str = Field(
        default="auto",  # auto | solo | prefork
        description="How to start the preprocess worker pool",
    )  # Has to be solo for MacOS to avoid

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

        # Skip runtime checks for operations like Alembic migrations
        if self.SKIP_RUNTIME_CHECKS:
            return

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


def _get_settings() -> Settings:
    """Get settings instance, initializing on first access."""
    global _settings_instance
    if _settings_instance is None:
        try:
            _settings_instance = Settings()
        except ValidationError as e:
            print("Configuration Error:")
            print(e)
            print("Please check your .env file or environment variables.")
            sys.exit(1)
    return _settings_instance


def __getattr__(name: str) -> Settings:
    """Lazy load settings on first attribute access."""
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
        "secret": False,
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
    "DISABLE_CELERY": {
        "type": "bool",
        "secret": False,
        "readonly": False,
        "category": "Celery",
        "label": "Disable Celery",
    },
    "BACKEND_CORS_ORIGINS": {
        "type": "str",
        "secret": False,
        "readonly": True,
        "category": "General",
        "label": "CORS Origins",
    },
}
