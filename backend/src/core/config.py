import sys

from pydantic import ValidationError
from pydantic_settings import BaseSettings
import secrets
import openai


class Settings(BaseSettings):
    PROJECT_NAME: str = "LLMAIx (v2) backend"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "medical_cases"
    SQLALCHEMY_DATABASE_URI: str | None = "sqlite:///database.db"

    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str | None = None
    OPENAI_API_MODEL: str = ""
    OPENAI_NO_API_CHECK: bool = False

    BACKEND_CORS_ORIGINS: list = ["http://localhost:5173"]

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

        if not self.OPENAI_NO_API_CHECK:
            if not self.OPENAI_API_KEY:
                print("OPENAI_API_KEY is not set. Please set it in your .env file.")
                sys.exit(1)
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


try:
    settings = Settings()
except ValidationError as e:
    print("Configuration Error:")
    print(e)
    print("Please check your .env file or environment variables.")
    sys.exit(1)
