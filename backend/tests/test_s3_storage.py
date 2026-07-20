# backend/tests/test_s3_storage.py
# ruff: noqa: N803 — the fake client mirrors boto3's CapWords kwargs
# (Bucket=, Key=, Body=, Fileobj=), which the production call sites use.
"""Tests for the S3 branch of the storage abstraction (dependencies.py).

The suite was previously local-storage only, leaving every S3 code path
untested. These tests swap in a fake in-memory S3 client at the
``get_s3_client`` boundary (no moto / no network) and flip the settings
instance to S3 mode (``LOCAL_DIRECTORY`` empty), covering:
- save_file / get_file / stream_file / remove_file S3 branches
- save_upload_stream via ``upload_fileobj``
- streaming-body close on exhaustion AND on early abandonment
- missing-key mapping to FileNotFoundError (404/NoSuchKey) vs re-raise
- the client cache keyed on (endpoint, access key, secret key)
- an end-to-end upload → download → delete cycle through the API
"""

import io
import types
import uuid as uuid_mod

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

BUCKET = "test-bucket"


class _FakeBody:
    """Mimics the botocore StreamingBody: read(n) + close() tracking."""

    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)
        self.closed = False

    def read(self, n: int = -1) -> bytes:
        return self._buf.read(n)

    def close(self) -> None:
        self.closed = True


class FakeS3Client:
    def __init__(self):
        self.store: dict[str, bytes] = {}
        self.bodies: list[_FakeBody] = []

    def _require(self, Bucket, Key, op):
        assert Bucket == BUCKET
        if Key not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, op)

    def put_object(self, Bucket, Key, Body):
        assert Bucket == BUCKET
        self.store[Key] = Body

    def upload_fileobj(self, Fileobj, Bucket, Key):
        assert Bucket == BUCKET
        self.store[Key] = Fileobj.read()

    def get_object(self, Bucket, Key):
        self._require(Bucket, Key, "GetObject")
        body = _FakeBody(self.store[Key])
        self.bodies.append(body)
        return {"Body": body}

    def head_object(self, Bucket, Key):
        # head_object surfaces missing keys as "404" (not "NoSuchKey").
        assert Bucket == BUCKET
        if Key not in self.store:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return {}

    def delete_object(self, Bucket, Key):
        self._require(Bucket, Key, "DeleteObject")
        del self.store[Key]


@pytest.fixture
def api_url():
    return "/api/v1"


@pytest.fixture
def client():
    from ..src.main import app

    return TestClient(app)


@pytest.fixture
def s3_mode(monkeypatch):
    """Switch storage to S3 mode with a fake client; restores on teardown."""
    from ..src import dependencies
    from ..src.core import config

    s = config._get_settings()
    monkeypatch.setattr(s, "LOCAL_DIRECTORY", "")
    monkeypatch.setattr(s, "S3_BUCKET_NAME", BUCKET)

    fake = FakeS3Client()
    monkeypatch.setattr(dependencies, "get_s3_client", lambda: fake)
    return fake


def _admin_headers(client, api_url):
    resp = client.post(
        f"{api_url}/auth/login",
        data={"username": "admin@example.com", "password": "Adminpassword1"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_save_and_get_file_round_trip(s3_mode):
    from ..src.dependencies import get_file, save_file

    key = save_file(b"s3 payload")
    assert s3_mode.store[key] == b"s3 payload"
    assert get_file(key) == b"s3 payload"


def test_stream_file_chunks_and_closes_body(s3_mode, monkeypatch):
    from ..src.core import config
    from ..src.dependencies import stream_file

    monkeypatch.setattr(config._get_settings(), "FILE_STREAM_CHUNK_SIZE", 4)
    s3_mode.store["chunked"] = b"0123456789"

    chunks = list(stream_file("chunked"))
    assert chunks == [b"0123", b"4567", b"89"]
    assert s3_mode.bodies[-1].closed, "streaming body not closed after exhaustion"


def test_stream_file_closes_body_on_early_abandonment(s3_mode):
    """A client disconnect abandons the generator mid-stream — the S3 body
    (and its socket) must still be released via the finally block."""
    from ..src.dependencies import stream_file

    s3_mode.store["abandoned"] = b"x" * 100_000
    gen = stream_file("abandoned")
    next(gen)
    gen.close()
    assert s3_mode.bodies[-1].closed, "streaming body leaked on early close"


def test_get_missing_file_raises_client_error(s3_mode):
    from ..src.dependencies import get_file

    with pytest.raises(ClientError):
        get_file("does-not-exist")


def test_remove_file_missing_raises_file_not_found(s3_mode):
    from ..src.dependencies import remove_file

    with pytest.raises(FileNotFoundError):
        remove_file("does-not-exist")


def test_remove_file_deletes_and_reraises_other_errors(s3_mode, monkeypatch):
    from ..src.dependencies import remove_file, save_file

    key = save_file(b"to delete")
    remove_file(key)
    assert key not in s3_mode.store

    # Non-404 errors (e.g. AccessDenied) must propagate, not become 404s.
    def denied(Bucket, Key):
        raise ClientError({"Error": {"Code": "AccessDenied"}}, "HeadObject")

    s3_mode.store["locked"] = b"x"
    monkeypatch.setattr(s3_mode, "head_object", denied)
    with pytest.raises(ClientError):
        remove_file("locked")
    assert "locked" in s3_mode.store


def test_save_upload_stream_uses_upload_fileobj(s3_mode):
    from ..src.dependencies import save_upload_stream

    upload = types.SimpleNamespace(file=io.BytesIO(b"streamed upload"))
    key = save_upload_stream(upload)
    assert s3_mode.store[key] == b"streamed upload"
    # Storage keys are UUIDs.
    uuid_mod.UUID(key)


def test_s3_client_cache_rebuilds_on_settings_change(monkeypatch):
    """The cached boto3 client must be reused for identical settings and
    rebuilt when endpoint/credentials change (admin override)."""
    from ..src import dependencies
    from ..src.core import config

    s = config._get_settings()
    monkeypatch.setattr(s, "S3_ENDPOINT_URL", "http://s3-one.example.com")
    monkeypatch.setattr(s, "AWS_ACCESS_KEY_ID", "key-one")
    monkeypatch.setattr(s, "AWS_SECRET_ACCESS_KEY", "secret-one")
    monkeypatch.setattr(dependencies, "_s3_client_cache", None)

    first = dependencies.get_s3_client()
    assert dependencies.get_s3_client() is first, "identical settings rebuilt client"

    monkeypatch.setattr(s, "AWS_ACCESS_KEY_ID", "key-two")
    second = dependencies.get_s3_client()
    assert second is not first, "changed credentials did not invalidate the cache"
    assert dependencies.get_s3_client() is second


def test_api_upload_download_delete_cycle_over_s3(client, api_url, s3_mode):
    """Full file lifecycle through the API with S3 storage: the blob lands in
    the bucket (not local disk), downloads stream back the same bytes, and
    delete removes both the DB row and the S3 object."""
    from ..src import models
    from ..src.db.session import SessionLocal

    headers = _admin_headers(client, api_url)
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "S3 Cycle"}
    ).json()["id"]

    content = b"s3 end-to-end content"
    resp = client.post(
        f"{api_url}/project/{project_id}/file",
        headers=headers,
        files={
            "file": ("s3.txt", content, "text/plain"),
            "file_info": (
                "",
                '{"file_name": "s3.txt", "file_type": "text/plain"}',
                "application/json",
            ),
        },
    )
    assert resp.status_code == 200, resp.text
    file_id = resp.json()["id"]

    db = SessionLocal()
    try:
        file_uuid = db.get(models.File, file_id).file_uuid
    finally:
        db.close()
    assert s3_mode.store[file_uuid] == content, "upload did not land in the bucket"

    resp = client.get(
        f"{api_url}/project/{project_id}/file/{file_id}/content", headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.content == content

    resp = client.delete(
        f"{api_url}/project/{project_id}/file/{file_id}", headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert file_uuid not in s3_mode.store, "S3 object survived file delete"
    db = SessionLocal()
    try:
        assert db.get(models.File, file_id) is None
    finally:
        db.close()

    client.delete(f"{api_url}/project/{project_id}", headers=headers)
