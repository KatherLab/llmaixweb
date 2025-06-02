from typing import Generator
from .db.session import SessionLocal
from openai import OpenAI
from .core.config import settings
import boto3
from botocore.client import BaseClient

if settings.OPENAI_NO_API_CHECK:
    openai_client: OpenAI | None = None
else:
    openai_client: OpenAI | None = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE)

if not settings.LOCAL_DIRECTORY:
    if settings.S3_ENDPOINT_URL:
        s3_client: BaseClient = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    else:
        s3_client: BaseClient = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
