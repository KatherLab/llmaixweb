# backend/src/dependencies.py
import hashlib
import os
import threading
import uuid
from typing import Any, Generator

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

    Typed as ``BaseClient`` but callers use S3 service methods (``get_object``,
    ``put_object``, …) — without ``boto3-stubs`` the static type checker only
    knows the base client, so call sites ``cast`` to ``Any`` for those methods.
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


def read_upload_with_limit(file, max_bytes: int | None = None) -> bytes:
    """Read an uploaded file into memory, aborting if it exceeds the size cap.

    ``file`` is a Starlette ``UploadFile``. Reading via ``file.file.read()``
    loads the entire upload into memory unbounded — a malicious or accidental
    huge upload would OOM the process. We check ``Content-Length`` first for an
    early rejection, then read in chunks so a lying/absent header can't bypass
    the cap. Raises ``HTTPException(413)`` on overflow.

    Synchronous variant — use in ``def`` endpoints. For ``async def`` endpoints
    use :func:`read_upload_with_limit_async`.
    """
    from fastapi import HTTPException

    limit = max_bytes if max_bytes is not None else settings.MAX_UPLOAD_SIZE_BYTES

    # Fast path: trust the declared content length when present.
    declared = getattr(file, "size", None)
    if declared is not None and declared > limit:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds the maximum allowed size of {limit} bytes.",
        )

    chunks: list[bytes] = []
    total = 0
    chunk_size = settings.FILE_STREAM_CHUNK_SIZE
    while True:
        chunk = file.file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail=f"Uploaded file exceeds the maximum allowed size of {limit} bytes.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def read_upload_with_limit_async(file, max_bytes: int | None = None) -> bytes:
    """Async counterpart to :func:`read_upload_with_limit`.

    Uses ``await file.read(chunk)`` so the event loop isn't blocked while
    reading from a ``def``-style SpooledTemporaryFile in an ``async def``
    endpoint. Same size-cap behaviour and 413 on overflow.
    """
    from fastapi import HTTPException

    limit = max_bytes if max_bytes is not None else settings.MAX_UPLOAD_SIZE_BYTES

    declared = getattr(file, "size", None)
    if declared is not None and declared > limit:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds the maximum allowed size of {limit} bytes.",
        )

    chunks: list[bytes] = []
    total = 0
    chunk_size = settings.FILE_STREAM_CHUNK_SIZE
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail=f"Uploaded file exceeds the maximum allowed size of {limit} bytes.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def hash_measure_and_head(
    file, max_bytes: int | None = None, head_len: int = 8192
) -> tuple[str, int, bytes]:
    """Stream an upload once to compute its SHA-256, size, and a head buffer.

    Reads ``file.file`` (a Starlette ``UploadFile``'s disk-backed
    ``SpooledTemporaryFile``) in chunks WITHOUT accumulating the whole payload in
    memory, so a large upload can't OOM the process. Enforces the size cap (413)
    and captures the first ``head_len`` bytes — enough for content-based MIME
    sniffing (``detect_structured_mime`` only reads the first 4096). Rewinds the
    file to position 0 so the caller can stream it to storage afterwards.

    Returns ``(sha256_hex, size, head_bytes)``. Use with :func:`save_upload_stream`
    for a fully streamed upload path (hash/dedup, then store, never buffering the
    whole file).
    """
    from fastapi import HTTPException

    limit = max_bytes if max_bytes is not None else settings.MAX_UPLOAD_SIZE_BYTES

    declared = getattr(file, "size", None)
    if declared is not None and declared > limit:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds the maximum allowed size of {limit} bytes.",
        )

    hasher = hashlib.sha256()
    total = 0
    head = bytearray()
    chunk_size = settings.FILE_STREAM_CHUNK_SIZE
    fileobj = file.file
    fileobj.seek(0)
    while True:
        chunk = fileobj.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail=f"Uploaded file exceeds the maximum allowed size of {limit} bytes.",
            )
        hasher.update(chunk)
        if len(head) < head_len:
            head.extend(chunk[: head_len - len(head)])
    fileobj.seek(0)
    return hasher.hexdigest(), total, bytes(head)


def save_upload_stream(file) -> str:
    """Stream a Starlette ``UploadFile`` to storage without buffering it in RAM.

    The file must be positioned at 0 (``hash_measure_and_head`` rewinds it).
    Local storage writes chunk-by-chunk; S3 uses ``upload_fileobj`` (streaming +
    automatic multipart). Returns the generated storage key.
    """
    file_name = f"{uuid.uuid4()}"
    fileobj = file.file
    fileobj.seek(0)

    if settings.LOCAL_DIRECTORY:
        file_path = f"{settings.LOCAL_DIRECTORY}/{file_name}"
        chunk_size = settings.FILE_STREAM_CHUNK_SIZE
        with open(file_path, "wb") as dest:
            while True:
                chunk = fileobj.read(chunk_size)
                if not chunk:
                    break
                dest.write(chunk)
    else:
        s3: Any = get_s3_client()
        s3.upload_fileobj(fileobj, settings.S3_BUCKET_NAME, file_name)

    return file_name


def save_upload_stream_checked(file, max_bytes: int | None = None) -> str:
    """Size-cap-enforced streamed save, for uploads that don't need hash/dedup.

    Two passes over the disk-backed upload: the first enforces the size cap
    (rejecting an oversized upload with 413 BEFORE anything is written to
    storage, so there's no partial file to clean up), the second streams it to
    storage. Neither buffers the whole file in memory. Returns the storage key.

    (The file-upload endpoint uses :func:`hash_measure_and_head` directly instead
    because it needs the hash for dedup and the head for MIME detection.)
    """
    hash_measure_and_head(file, max_bytes=max_bytes)  # cap check (+ rewinds)
    return save_upload_stream(file)


def stream_file(file_name: str):
    """Yield a file's content in chunks from S3 or local storage.

    A generator that reads ``FILE_STREAM_CHUNK_SIZE`` bytes at a time, so a
    caller wrapping this in :class:`StreamingResponse` can ship a large file
    to the client without ever holding the whole file in memory. For local
    storage the file handle is closed when the generator is exhausted or
    garbage-collected; for S3 the streaming body is closed in a ``finally``.
    """
    chunk_size = settings.FILE_STREAM_CHUNK_SIZE
    if settings.LOCAL_DIRECTORY:
        file_path = f"{settings.LOCAL_DIRECTORY}/{file_name}"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_name} not found in local storage.")
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    else:
        s3: Any = get_s3_client()
        response = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=file_name)
        body = response["Body"]
        try:
            while True:
                chunk = body.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            # Release the S3 streaming body (and its underlying socket) even on
            # early client disconnect / exception, so connections aren't leaked.
            close = getattr(body, "close", None)
            if close is not None:
                try:
                    close()
                except Exception:
                    pass


def get_file(file_name: str, force_streaming: bool = False) -> bytes:
    """
    Retrieves a file from S3 or local storage as bytes.

    Note: the ``force_streaming`` flag and ``FILE_STREAMING_THRESHOLD_BYTES``
    threshold are retained for compatibility, but since this function returns
    the full file as ``bytes`` the file is necessarily held in memory once
    returned regardless. Callers that need true constant-memory delivery
    (e.g. HTTP download endpoints) should use :func:`stream_file` with a
    ``StreamingResponse`` instead.

    Args:
        file_name (str): The name of the file to retrieve.
        force_streaming (bool): Unused — kept for backwards compatibility.

    Returns:
        bytes: The content of the file.
    """
    return b"".join(stream_file(file_name))


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
        s3: Any = get_s3_client()
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
        s3: Any = get_s3_client()
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
