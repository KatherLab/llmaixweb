import os
from typing import Generator
from .db.session import SessionLocal
from openai import OpenAI
from .core.config import settings
import boto3
from botocore.client import BaseClient

if settings.OPENAI_NO_API_CHECK:
    openai_client: OpenAI | None = None
else:
    openai_client: OpenAI | None = OpenAI(
        api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE
    )

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


def get_file(file_name: str) -> bytes:
    """
    Retrieves a file from S3 or local storage.

    Args:
        file_name (str): The name of the file to retrieve.

    Returns:
        bytes: The content of the file.
    """
    if settings.LOCAL_DIRECTORY:
        # check if the file exists in local storage
        if not os.path.exists(f"{settings.LOCAL_DIRECTORY}/{file_name}"):
            raise FileNotFoundError(f"File {file_name} not found in local storage.")
        with open(f"{settings.LOCAL_DIRECTORY}/{file_name}", "rb") as file:
            return file.read()
    else:
        response = s3_client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=file_name)
        return response["Body"].read()


def upload_file(file_name: str, file_content: bytes, replace: bool = False) -> None:
    """
    Uploads a file to S3 or local storage.

    Args:
        file_name (str): The name of the file to upload.
        file_content (bytes): The content of the file to upload.
        replace (bool): Whether to replace the file if it already exists. Defaults to False.

    Raises:
        FileExistsError: If the file already exists and replace is False.
    """
    file_path = f"{settings.LOCAL_DIRECTORY}/{file_name}"
    if settings.LOCAL_DIRECTORY:
        if not replace and os.path.exists(file_path):
            raise FileExistsError(f"File {file_name} already exists")
        with open(file_path, "wb") as file:
            file.write(file_content)
    else:
        try:
            s3_client.head_object(Bucket=settings.S3_BUCKET_NAME, Key=file_name)
            if not replace:
                raise FileExistsError(f"File {file_name} already exists")
        except s3_client.exceptions.ClientError:
            # File does not exist in S3
            pass
        s3_client.put_object(
            Bucket=settings.S3_BUCKET_NAME, Key=file_name, Body=file_content
        )


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
