import hashlib
import os
import uuid
from typing import Generator

import boto3
from botocore.client import BaseClient
from openai import OpenAI

from .core.config import settings
from .db.session import SessionLocal

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


def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA-256 hash of file content"""
    return hashlib.sha256(content).hexdigest()


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
        assert s3_client is not None
        response = s3_client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=file_name)  # type: ignore
        return response["Body"].read()


def save_file(file_content: bytes) -> str:
    """
    Saves a file to S3 or local storage.

    Args:
        file_content (bytes): The content of the file to upload.

    Returns:
        str: The generated file name.
    """
    file_name = f"{uuid.uuid4()}"
    file_path = f"{settings.LOCAL_DIRECTORY}/{file_name}"

    if settings.LOCAL_DIRECTORY:
        with open(file_path, "wb") as file:
            file.write(file_content)
    else:
        s3_client.put_object(  # type: ignore
            Bucket=settings.S3_BUCKET_NAME, Key=file_name, Body=file_content
        )

    return file_name


def remove_file(file_name: str) -> None:
    """
    Deletes a file from S3 or local storage.

    Args:
        file_name (str): The name of the file to delete.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if settings.LOCAL_DIRECTORY:
        file_path = f"{settings.LOCAL_DIRECTORY}/{file_name}"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_name} not found in local storage.")
        os.remove(file_path)
    else:
        try:
            s3_client.head_object(Bucket=settings.S3_BUCKET_NAME, Key=file_name)  # type: ignore
            s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=file_name)  # type: ignore
        except s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(f"File {file_name} not found in S3.")
            else:
                raise e


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
