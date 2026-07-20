# backend/tests/test_preprocessing_dispatch.py
"""Preprocessing dispatch-failure handling.

When the Celery dispatch fails (broker down), the task and its file tasks must
not be left stuck PENDING forever — the orphan sweeper can't reap never-started
rows. They should be marked FAILED and the caller gets a 503.

The test env runs with DISABLE_CELERY=True. Submissions in that mode are
refused up front (fail-fast, no rows created); to exercise the *dispatch*
failure path the tests flip the runtime flag off, at which point the Celery
task import still fails (the module was loaded with Celery disabled) exactly
like a broker/dispatch error would.
"""

import pytest
from fastapi.testclient import TestClient


def _enable_celery_flag(monkeypatch):
    """Turn off DISABLE_CELERY on the live Settings instance so a submission
    gets past the fail-fast guard and reaches the dispatch (which then fails,
    since the Celery task module was imported with Celery disabled)."""
    from ..src.core import config

    monkeypatch.setattr(config._get_settings(), "DISABLE_CELERY", False)


@pytest.fixture
def api_url():
    return "/api/v1"


@pytest.fixture
def client():
    from ..src.main import app

    return TestClient(app)


def _admin_headers(client, api_url):
    resp = client.post(
        f"{api_url}/auth/login",
        data={"username": "admin@example.com", "password": "Adminpassword1"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_disable_celery_fails_fast_without_creating_rows(client, api_url):
    """With DISABLE_CELERY on, a non-bypass submission is refused up front —
    no task/file-task rows are created that would instantly die at dispatch."""
    headers = _admin_headers(client, api_url)

    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Fail Fast"}
    ).json()["id"]

    file_id = client.post(
        f"{api_url}/project/{project_id}/file",
        headers=headers,
        files={
            "file": ("ff.txt", b"text", "text/plain"),
            "file_info": (
                "",
                '{"file_name": "ff.txt", "file_type": "text/plain"}',
                "application/json",
            ),
        },
    ).json()["id"]

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [file_id],
            "inline_config": {"name": "c", "description": "d"},
        },
    )
    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"]["code"] == "preprocess.celery_disabled"

    # No task rows were created at all.
    tasks = client.get(
        f"{api_url}/project/{project_id}/preprocess", headers=headers
    ).json()
    assert tasks == []

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_celery_dispatch_failure_fails_task_not_stuck_pending(
    client, api_url, monkeypatch
):
    headers = _admin_headers(client, api_url)
    _enable_celery_flag(monkeypatch)

    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Dispatch Fail"}
    ).json()["id"]

    file_id = client.post(
        f"{api_url}/project/{project_id}/file",
        headers=headers,
        files={
            "file": ("d.txt", b"text", "text/plain"),
            "file_info": (
                "",
                '{"file_name": "d.txt", "file_type": "text/plain"}',
                "application/json",
            ),
        },
    ).json()["id"]

    # Non-bypass path → tries to dispatch to Celery, whose task import fails
    # (module was loaded with Celery disabled) → dispatch failure.
    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [file_id],
            "inline_config": {"name": "c", "description": "d"},
        },
    )
    assert resp.status_code == 503, resp.text

    # The task must be FAILED, not left PENDING (which the sweeper can't recover).
    tasks = client.get(
        f"{api_url}/project/{project_id}/preprocess", headers=headers
    ).json()
    assert len(tasks) == 1
    assert tasks[0]["status"] == "failed"
    assert all(ft["status"] == "failed" for ft in tasks[0]["file_tasks"])

    # And the file must be deletable afterwards even though a (failed)
    # preprocessing task references it — no force needed, since it produced no
    # documents. Previously the lingering FilePreprocessingTask blocked deletion.
    del_resp = client.delete(
        f"{api_url}/project/{project_id}/file/{file_id}", headers=headers
    )
    assert del_resp.status_code == 200, del_resp.text
    # The now-empty parent preprocessing task is cleaned up too.
    remaining = client.get(
        f"{api_url}/project/{project_id}/preprocess", headers=headers
    ).json()
    assert remaining == []

    client.delete(f"{api_url}/project/{project_id}", headers=headers)
