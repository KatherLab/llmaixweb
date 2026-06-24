# backend/src/dependencies.py
import hashlib
import os
import threading
import uuid
from typing import Generator

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from .core.dynamic_settings import get_settings
from .db.session import SessionLocal

settings = get_settings()

# S3 client cache. The client is built once from the *current* settings and
# rebuilt only when the relevant S3 settings change (e.g. after an admin
# override applied via dynamic_settings). The cache key is the tuple of values
# that define the client, so it self-invalidates without coupling to the
# settings-reload machinery. Per-trial LLM clients are constructed elsewhere
# from Trial.api_key/base_url, so no module-level OpenAI client is needed.
_s3_client_lock = threading.Lock()
_s3_client_cache: tuple[tuple, BaseClient] | None = None


def get_s3_client() -> BaseClient:
    """Return an S3 client reflecting the current settings.

    Cached on the (endpoint, access key, secret key) tuple so that admin
    changes to S3 config take effect on the next call without rebuilding the
    client on every request.
    """
    global _s3_client_cache
    key = (
        settings.S3_ENDPOINT_URL,
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY,
    )
    cached = _s3_client_cache
    if cached is not None and cached[0] == key:
        return cached[1]
    with _s3_client_lock:
        cached = _s3_client_cache
        if cached is not None and cached[0] == key:
            return cached[1]
        if settings.S3_ENDPOINT_URL:
            client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        else:
            client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        _s3_client_cache = (key, client)
        return client


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
        s3 = get_s3_client()
        # For S3, check if we should use streaming
        try:
            head = s3.head_object(Bucket=settings.S3_BUCKET_NAME, Key=file_name)
            file_size = head.get("ContentLength", 0)
        except ClientError:
            file_size = 0  # Unknown size, proceed without streaming

        if force_streaming or file_size > settings.FILE_STREAMING_THRESHOLD_BYTES:
            # Stream large files from S3
            response = s3.get_object(
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
            response = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=file_name)
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

    if settings.LOCAL_DIRECTORY:
        file_path = f"{settings.LOCAL_DIRECTORY}/{file_name}"
        with open(file_path, "wb") as file:
            file.write(file_content)
    else:
        s3 = get_s3_client()
        s3.put_object(Bucket=settings.S3_BUCKET_NAME, Key=file_name, Body=file_content)

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
        s3 = get_s3_client()
        try:
            s3.head_object(Bucket=settings.S3_BUCKET_NAME, Key=file_name)
            s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=file_name)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                raise FileNotFoundError(f"File {file_name} not found in S3.")
            raise


def get_db() -> Generator:
    """Yield a DB session for a request.

    Handlers commit explicitly — there is no auto-commit on success, so
    read-only endpoints never persist incidental flushes and a handler that
    forgets to commit simply doesn't write (rather than silently persisting
    unintended state). Exceptions still roll back.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
