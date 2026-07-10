# backend/tests/test_trial_execution.py
"""End-to-end trial execution with a MOCKED LLM.

The main suite's trial/extraction tests skip in CI (OPENAI_NO_API_CHECK), so
trial execution — status transitions, result parsing/validation, result
storage — had no CI coverage. This mocks the OpenAI client used by the
synchronous (bypass_celery) extraction path so the real pipeline runs
deterministically without a network call.
"""

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_url():
    return "/api/v1"


@pytest.fixture
def client():
    from ..src.main import app

    return TestClient(app)


# ── Fake OpenAI client mimicking the bits _store_result / extract_* read ──


class _FakeMessage:
    def __init__(self, content):
        self.content = content
        self.reasoning_content = None
        self.refusal = None


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)
        self.finish_reason = "stop"


class _FakeUsage:
    def model_dump(self):
        return {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage()


def _make_fake_openai(content: str):
    class _FakeCompletions:
        def create(self, **kwargs):
            return _FakeCompletion(content)

    class _FakeChat:
        def __init__(self):
            self.completions = _FakeCompletions()

    class _FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = _FakeChat()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    return _FakeOpenAI


def _admin_headers(client, api_url):
    resp = client.post(
        f"{api_url}/auth/login",
        data={"username": "admin@example.com", "password": "Adminpassword1"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_bypass_celery_trial_extracts_and_stores_result(client, api_url, monkeypatch):
    headers = _admin_headers(client, api_url)

    # Mock the LLM so the real extraction pipeline runs offline. The canned
    # content is valid JSON matching the schema below.
    expected = {"field1": "hello", "field2": "world"}
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        _make_fake_openai(json.dumps(expected)),
    )

    # Project + prompt + schema.
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Mocked Trial Project"}
    ).json()["id"]

    prompt_id = client.post(
        f"{api_url}/project/{project_id}/prompt",
        headers=headers,
        json={
            "name": "P",
            "system_prompt": "Extract as JSON.",
            "user_prompt": "Doc: {document_content}",
            "project_id": project_id,
        },
    ).json()["id"]

    schema_id = client.post(
        f"{api_url}/project/{project_id}/schema",
        headers=headers,
        json={
            "schema_name": "S",
            "schema_definition": {
                "type": "object",
                "properties": {
                    "field1": {"type": "string"},
                    "field2": {"type": "string"},
                },
                "required": ["field1"],
            },
        },
    ).json()["id"]

    # File → preprocess (sync) → document.
    file_id = client.post(
        f"{api_url}/project/{project_id}/file",
        headers=headers,
        files={
            "file": ("doc.txt", b"some clinical text", "text/plain"),
            "file_info": (
                "",
                '{"file_name": "doc.txt", "file_type": "text/plain"}',
                "application/json",
            ),
        },
    ).json()["id"]

    assert (
        client.post(
            f"{api_url}/project/{project_id}/preprocess",
            headers=headers,
            json={
                "file_ids": [file_id],
                "inline_config": {"name": "cfg", "description": "d"},
                "bypass_celery": True,
            },
        ).status_code
        == 200
    )

    document_id = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()["items"][0]["id"]

    # Run the trial synchronously against the mocked LLM.
    trial_resp = client.post(
        f"{api_url}/project/{project_id}/trial",
        headers=headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_ids": [document_id],
            "bypass_celery": True,
            "llm_model": "mock-model",
            "api_key": "test-key",
            "base_url": "http://localhost:11434/v1",
        },
    )
    assert trial_resp.status_code == 200, trial_resp.text
    trial = trial_resp.json()
    trial_id = trial["id"]
    assert trial["status"] == "completed"

    # The stored result must reflect the (mocked) model output.
    results = client.get(
        f"{api_url}/project/{project_id}/trial/{trial_id}/results", headers=headers
    )
    assert results.status_code == 200, results.text
    items = results.json()["items"]
    assert len(items) == 1
    assert items[0]["result"] == expected

    # Streamed ZIP downloads (JSON + CSV-with-content) must be valid archives.
    import io as _io
    import zipfile as _zipfile

    for fmt in ("json", "csv"):
        dl = client.get(
            f"{api_url}/project/{project_id}/trial/{trial_id}/download",
            headers=headers,
            params={"format": fmt, "include_content": True},
        )
        assert dl.status_code == 200, dl.text
        assert dl.headers["content-type"] == "application/zip"
        zf = _zipfile.ZipFile(_io.BytesIO(dl.content))
        assert zf.testzip() is None  # archive integrity
        names = zf.namelist()
        if fmt == "json":
            assert "metadata.json" in names
        else:
            assert "results.csv" in names
            # The extracted value must appear in the CSV.
            assert b"hello" in zf.read("results.csv")

    # Deleting the trial removes it (and bulk-deletes its results/evaluations).
    assert (
        client.delete(
            f"{api_url}/project/{project_id}/trial/{trial_id}", headers=headers
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"{api_url}/project/{project_id}/trial/{trial_id}", headers=headers
        ).status_code
        == 404
    )

    # Cleanup.
    client.delete(f"{api_url}/project/{project_id}", headers=headers)
