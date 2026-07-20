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


def test_document_set_from_explicit_ids(client, api_url):
    """Creating a set from explicit document_ids (bulk-insert path) adds exactly
    the valid in-project documents."""
    headers = _admin_headers(client, api_url)

    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "DocSet Project"}
    ).json()["id"]

    file_id = client.post(
        f"{api_url}/project/{project_id}/file",
        headers=headers,
        files={
            "file": ("d.txt", b"hello world", "text/plain"),
            "file_info": (
                "",
                '{"file_name": "d.txt", "file_type": "text/plain"}',
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
                "inline_config": {"name": "c", "description": "d"},
                "bypass_celery": True,
            },
        ).status_code
        == 200
    )

    doc_id = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()["items"][0]["id"]

    created = client.post(
        f"{api_url}/project/{project_id}/document-set",
        headers=headers,
        # Include a duplicate + a bogus id to confirm dedupe + project scoping.
        json={"name": "My Set", "document_ids": [doc_id, doc_id, 999999]},
    )
    assert created.status_code == 200, created.text
    docs = created.json()["documents"]
    assert [d["id"] for d in docs] == [doc_id]

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_force_reprocess_blocked_by_trial_result(client, api_url, monkeypatch):
    """force_reprocess on a document referenced by a trial result must return a
    409 (not a raw 500 IntegrityError from the RESTRICT FK)."""
    headers = _admin_headers(client, api_url)
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        _make_fake_openai(json.dumps({"field1": "x"})),
    )

    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Force Reprocess"}
    ).json()["id"]
    prompt_id = client.post(
        f"{api_url}/project/{project_id}/prompt",
        headers=headers,
        json={
            "name": "P",
            "system_prompt": "x",
            "user_prompt": "{document_content}",
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
                "properties": {"field1": {"type": "string"}},
                "required": ["field1"],
            },
        },
    ).json()["id"]
    file_id = client.post(
        f"{api_url}/project/{project_id}/file",
        headers=headers,
        files={
            "file": ("d.txt", b"clinical text", "text/plain"),
            "file_info": (
                "",
                '{"file_name": "d.txt", "file_type": "text/plain"}',
                "application/json",
            ),
        },
    ).json()["id"]

    # Same inline_config both times so the config — and thus the existing
    # document — is reused on the force_reprocess attempt (config-matching is by
    # additional_settings).
    inline_config = {"name": "cfg", "description": "d", "additional_settings": {}}
    assert (
        client.post(
            f"{api_url}/project/{project_id}/preprocess",
            headers=headers,
            json={
                "file_ids": [file_id],
                "inline_config": inline_config,
                "bypass_celery": True,
            },
        ).status_code
        == 200
    )
    doc_id = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()["items"][0]["id"]

    # Produce a trial result that references the document (RESTRICT FK).
    assert (
        client.post(
            f"{api_url}/project/{project_id}/trial",
            headers=headers,
            json={
                "schema_id": schema_id,
                "prompt_id": prompt_id,
                "document_ids": [doc_id],
                "bypass_celery": True,
                "llm_model": "mock",
                "api_key": "k",
                "base_url": "http://localhost:11434/v1",
            },
        ).status_code
        == 200
    )

    # force_reprocess must now be refused with a 409 (not a 500).
    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [file_id],
            "inline_config": inline_config,
            "force_reprocess": True,
            "bypass_celery": True,
        },
    )
    assert resp.status_code == 409, resp.text
    assert doc_id in resp.json()["detail"]["referenced_document_ids"]

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_celery_trial_dispatch_failure_marks_failed_not_stuck(
    client, api_url, monkeypatch
):
    """A non-bypass trial whose Celery dispatch fails must end FAILED, not stuck.

    The test env runs DISABLE_CELERY=True, which now fails fast at submission —
    so the runtime flag is flipped off to get past that guard; importing the
    Celery task then still raises (the module was loaded with Celery disabled),
    exactly like a broker/dispatch error → the create endpoint's dispatch guard
    must mark the trial FAILED and return 503. Without the guard the trial would
    sit in the queued state forever (the sweeper only reaps PROCESSING trials,
    and a queued trial is intentionally PENDING to stay out of the sweeper).
    """
    from ..src.core import config

    headers = _admin_headers(client, api_url)
    monkeypatch.setattr(config._get_settings(), "DISABLE_CELERY", False)

    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Trial Dispatch Fail"}
    ).json()["id"]

    prompt_id = client.post(
        f"{api_url}/project/{project_id}/prompt",
        headers=headers,
        json={
            "name": "P",
            "system_prompt": "Extract.",
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
                "properties": {"field1": {"type": "string"}},
                "required": ["field1"],
            },
        },
    ).json()["id"]

    file_id = client.post(
        f"{api_url}/project/{project_id}/file",
        headers=headers,
        files={
            "file": ("doc.txt", b"clinical text", "text/plain"),
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

    # Non-bypass trial → dispatch fails (Celery disabled) → 503, not 500.
    resp = client.post(
        f"{api_url}/project/{project_id}/trial",
        headers=headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_ids": [document_id],
            "bypass_celery": False,
            "llm_model": "mock",
            "api_key": "k",
            "base_url": "http://localhost:11434/v1",
        },
    )
    assert resp.status_code == 503, resp.text

    # The trial must exist and be FAILED (not PENDING/PROCESSING — which would
    # be unrecoverable, since the sweeper never reaps a never-dispatched trial).
    trials = client.get(
        f"{api_url}/project/{project_id}/trial", headers=headers
    ).json()["items"]
    assert len(trials) == 1
    assert trials[0]["status"] == "failed"

    # With DISABLE_CELERY back on (monkeypatch scope ends at test end, but the
    # flag is still off here — flip it back explicitly for this check), a
    # non-bypass trial is refused up front without creating a row.
    monkeypatch.setattr(config._get_settings(), "DISABLE_CELERY", True)
    resp = client.post(
        f"{api_url}/project/{project_id}/trial",
        headers=headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_ids": [document_id],
            "bypass_celery": False,
            "llm_model": "mock",
            "api_key": "k",
            "base_url": "http://localhost:11434/v1",
        },
    )
    assert resp.status_code == 503, resp.text
    assert "disabled" in resp.json()["detail"].lower()
    trials = client.get(
        f"{api_url}/project/{project_id}/trial", headers=headers
    ).json()["items"]
    assert len(trials) == 1  # still only the earlier dispatch-failure trial

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_trial_duplicate_document_ids_deduped_and_results_default_excluded(
    client, api_url, monkeypatch
):
    """Duplicated document_ids must be deduped at creation (a duplicate would
    inflate the total: results are unique per (trial, document), so done ==
    total could never be reached and progress would stick below 1.0). Also
    covers the GET /trial default: results are no longer embedded unless
    include_results=true is passed."""
    headers = _admin_headers(client, api_url)

    expected = {"field1": "x"}
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        _make_fake_openai(json.dumps(expected)),
    )

    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Dup Ids Trial Project"}
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
                "properties": {"field1": {"type": "string"}},
                "required": ["field1"],
            },
        },
    ).json()["id"]

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

    trial_resp = client.post(
        f"{api_url}/project/{project_id}/trial",
        headers=headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_ids": [document_id, document_id, document_id],
            "bypass_celery": True,
            "llm_model": "mock-model",
            "api_key": "test-key",
            "base_url": "http://localhost:11434/v1",
        },
    )
    assert trial_resp.status_code == 200, trial_resp.text
    trial = trial_resp.json()
    assert trial["status"] == "completed"
    assert trial["document_ids"] == [document_id]
    assert trial["docs_done"] == 1
    assert trial["progress"] == 1.0

    # GET default: no embedded results (fetch pages via /results instead)…
    detail = client.get(
        f"{api_url}/project/{project_id}/trial/{trial['id']}", headers=headers
    ).json()
    assert detail["results"] == []
    # …but include_results=true still embeds them.
    detail = client.get(
        f"{api_url}/project/{project_id}/trial/{trial['id']}?include_results=true",
        headers=headers,
    ).json()
    assert len(detail["results"]) == 1
    assert detail["results"][0]["result"] == expected

    client.delete(f"{api_url}/project/{project_id}", headers=headers)
