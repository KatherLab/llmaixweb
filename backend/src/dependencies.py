# backend/src/dependencies.py
import hashlib
import os
import uuid
from typing import Generator

import boto3
from botocore.client import BaseClient
from openai import OpenAI

from .core.dynamic_settings import get_settings
from .db.session import SessionLocal

settings = get_settings()

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


def get_file(file_name: str, force_streaming: bool = False) -> bytes:
    """
    Retrieves a file from S3 or local storage.

    For large files (exceeding FILE_STREAMING_THRESHOLD_BYTES), uses streaming
    to reduce memory usage.

    Args:
        file_name (str): The name of the file to retrieve.
        force_streaming (bool): Force streaming regardless of file size.

    Returns:
        bytes: The content of the file.
    """
    if settings.LOCAL_DIRECTORY:
        # check if the file exists in local storage
        file_path = f"{settings.LOCAL_DIRECTORY}/{file_name}"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_name} not found in local storage.")

        # Check file size to decide whether to stream
        file_size = os.path.getsize(file_path)
        if force_streaming or file_size > settings.FILE_STREAMING_THRESHOLD_BYTES:
            # Stream large files in chunks
            chunks = []
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(settings.FILE_STREAM_CHUNK_SIZE)
                    if not chunk:
                        break
                    chunks.append(chunk)
            return b"".join(chunks)
        else:
            # Read small files directly
            with open(file_path, "rb") as file:
                return file.read()
    else:
        assert s3_client is not None
        # For S3, check if we should use streaming
        try:
            head = s3_client.head_object(Bucket=settings.S3_BUCKET_NAME, Key=file_name)  # type: ignore
            file_size = head.get("ContentLength", 0)
        except Exception:
            file_size = 0  # Unknown size, proceed without streaming

        if force_streaming or file_size > settings.FILE_STREAMING_THRESHOLD_BYTES:
            # Stream large files from S3
            response = s3_client.get_object(  # type: ignore
                Bucket=settings.S3_BUCKET_NAME,
                Key=file_name,
            )
            # Use streaming body for large files
            body = response["Body"]
            chunks = []
            while True:
                chunk = body.read(settings.FILE_STREAM_CHUNK_SIZE)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)
        else:
            # Read small files directly
            response = s3_client.get_object(
                Bucket=settings.S3_BUCKET_NAME, Key=file_name
            )  # type: ignore
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
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
