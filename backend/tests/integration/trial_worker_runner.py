"""Runs REAL Celery worker + broker TRIAL extraction scenarios (subprocess entry).

Invoked as a subprocess by ``test_celery_integration.py`` with these env vars
already set (before this module imports anything app-related):

    DISABLE_CELERY=false
    INITIALIZE_CELERY=false          (we manage our own worker)
    CELERY_BROKER_URL=<redis url>
    SQLALCHEMY_DATABASE_URI=<postgres dsn>   (schema already migrated)

This is the production extraction path end-to-end: the FastAPI app (via
TestClient) creates project → file → documents → schema → prompt → trial with
``bypass_celery=False``, so the API performs a real ``extract_info_celery``
dispatch through Redis; a real Celery worker on the ``default`` queue consumes
it and calls a local fake OpenAI-compatible HTTP server. Covers what the
mocked bypass-path test can't: broker round-trip, worker signals
(PENDING→PROCESSING via task_prerun), the async per-document fan-out,
heartbeat/cancellation watchers, and terminal finalization.

Scenarios:
  1. happy    — trial COMPLETES, one TrialResult per document with the JSON
                the (fake) model returned.
  2. failure  — the LLM endpoint rejects every request (HTTP 400) → trial ends
                FAILED with per-document failure messages in meta.
  3. cancel   — mid-run cancel of an in-flight trial → CANCELLED, in-flight
                docs recorded as "Cancelled", results rolled back.

Prints ``PASS ✅`` / ``FAIL ❌`` and exits 0/1.
"""

import json
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_API = "/api/v1"

_EXPECTED = {"field1": "hello", "field2": "world"}


# ───────────────────────── fake OpenAI-compatible server ─────────────────────────


class _FakeLLMHandler(BaseHTTPRequestHandler):
    """Minimal /chat/completions endpoint. The requested model name selects
    the behavior: mock-ok → canned JSON, mock-fail → HTTP 400, mock-slow →
    6s delay then canned JSON (long enough for a cancel to land mid-flight)."""

    def do_POST(self):  # noqa: N802 — http.server API
        length = int(self.headers.get("content-length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            body = {}
        model = body.get("model", "")

        if not self.path.endswith("/chat/completions"):
            self._send(404, {"error": {"message": "not found"}})
            return
        if model == "mock-fail":
            self._send(
                400,
                {
                    "error": {
                        "message": "mock rejection",
                        "type": "invalid_request_error",
                    }
                },
            )
            return
        if model == "mock-slow":
            time.sleep(6)

        self._send(
            200,
            {
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "created": 1,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(_EXPECTED),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        )

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # silence request logging
        pass


def _start_fake_llm() -> tuple[ThreadingHTTPServer, str]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), _FakeLLMHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{port}/v1"


# ───────────────────────── worker + app plumbing ─────────────────────────


def _start_worker() -> subprocess.Popen:
    """Start a REAL Celery worker subprocess consuming the default queue
    (where extract_info_celery is routed)."""
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "backend.src.celery.celery_config",
            "worker",
            "-Q",
            "default",
            "-c",
            "1",
            "--pool",
            "solo",
            "--loglevel",
            "warning",
        ],
        cwd=str(_REPO_ROOT),
    )


def _seed_admin() -> tuple[str, str]:
    from backend.src.core.security import get_password_hash
    from backend.src.db.session import SessionLocal
    from backend.src.models.user import User, UserRole

    email = f"it{time.time_ns()}@example.com"
    password = "Adminpassword1"
    db = SessionLocal()
    db.add(
        User(
            email=email,
            full_name="Trial IT Admin",
            hashed_password=get_password_hash(password),
            role=UserRole.admin,
            is_active=True,
        )
    )
    db.commit()
    db.close()
    return email, password


def _setup_project(client, headers, n_docs: int) -> tuple[int, int, int, list[int]]:
    """Create project + preprocessed documents + schema + prompt via the API."""
    project_id = client.post(
        f"{_API}/project", headers=headers, json={"name": f"Trial IT {time.time_ns()}"}
    ).json()["id"]

    file_ids = []
    for i in range(n_docs):
        resp = client.post(
            f"{_API}/project/{project_id}/file",
            headers=headers,
            files={
                "file": (f"doc_{i}.txt", f"clinical text {i}".encode(), "text/plain"),
                "file_info": (
                    "",
                    json.dumps(
                        {"file_name": f"doc_{i}.txt", "file_type": "text/plain"}
                    ),
                    "application/json",
                ),
            },
        )
        assert resp.status_code == 200, resp.text
        file_ids.append(resp.json()["id"])

    resp = client.post(
        f"{_API}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": file_ids,
            "inline_config": {"name": "cfg", "description": "d"},
            "bypass_celery": True,
        },
    )
    assert resp.status_code == 200, resp.text

    docs = client.get(f"{_API}/project/{project_id}/document", headers=headers).json()[
        "items"
    ]
    doc_ids = [d["id"] for d in docs]
    assert len(doc_ids) == n_docs, f"expected {n_docs} documents, got {len(doc_ids)}"

    schema_id = client.post(
        f"{_API}/project/{project_id}/schema",
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

    prompt_id = client.post(
        f"{_API}/project/{project_id}/prompt",
        headers=headers,
        json={
            "name": "P",
            "system_prompt": "Extract as JSON.",
            "user_prompt": "Doc: {document_content}",
            "project_id": project_id,
        },
    ).json()["id"]

    return project_id, schema_id, prompt_id, doc_ids


def _create_trial(
    client, headers, project_id, schema_id, prompt_id, doc_ids, model, base_url
):
    resp = client.post(
        f"{_API}/project/{project_id}/trial",
        headers=headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_ids": doc_ids,
            "bypass_celery": False,
            "llm_model": model,
            "api_key": "mock-key",
            "base_url": base_url,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _get_trial(client, headers, project_id, trial_id) -> dict:
    resp = client.get(f"{_API}/project/{project_id}/trial/{trial_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _wait_for(fn, timeout: float = 90.0, interval: float = 0.5):
    """Poll ``fn`` until it returns a truthy value; None on timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(interval)
    return None


def _get_results(client, headers, project_id, trial_id) -> list[dict]:
    resp = client.get(
        f"{_API}/project/{project_id}/trial/{trial_id}/results", headers=headers
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["items"]


# ───────────────────────── scenarios ─────────────────────────

_TERMINAL = {"completed", "failed", "cancelled"}


def _scenario_happy(client, headers, base_url) -> bool:
    project_id, schema_id, prompt_id, doc_ids = _setup_project(client, headers, 3)
    trial = _create_trial(
        client, headers, project_id, schema_id, prompt_id, doc_ids, "mock-ok", base_url
    )
    assert trial["status"] == "pending", trial["status"]

    final = _wait_for(
        lambda: (
            t
            if (t := _get_trial(client, headers, project_id, trial["id"]))["status"]
            in _TERMINAL
            else None
        )
    )
    results = _get_results(client, headers, project_id, trial["id"]) if final else []
    status = final["status"] if final else "timeout"
    print(f"[happy] status={status} results={len(results)} (want completed/3)")
    ok = (
        status == "completed"
        and len(results) == 3
        and all(r["result"] == _EXPECTED for r in results)
        and final["docs_done"] == 3
    )
    print("[happy] PASS" if ok else "[happy] FAIL")
    return ok


def _scenario_failure(client, headers, base_url) -> bool:
    project_id, schema_id, prompt_id, doc_ids = _setup_project(client, headers, 2)
    trial = _create_trial(
        client,
        headers,
        project_id,
        schema_id,
        prompt_id,
        doc_ids,
        "mock-fail",
        base_url,
    )

    final = _wait_for(
        lambda: (
            t
            if (t := _get_trial(client, headers, project_id, trial["id"]))["status"]
            in _TERMINAL
            else None
        )
    )
    results = _get_results(client, headers, project_id, trial["id"]) if final else []
    status = final["status"] if final else "timeout"
    failures = ((final or {}).get("meta") or {}).get("failures") or {}
    print(
        f"[failure] status={status} failures={len(failures)} results={len(results)} "
        "(want failed/2/0)"
    )
    ok = status == "failed" and len(failures) == 2 and len(results) == 0
    print("[failure] PASS" if ok else "[failure] FAIL")
    return ok


def _scenario_cancel(client, headers, base_url) -> bool:
    project_id, schema_id, prompt_id, doc_ids = _setup_project(client, headers, 2)
    trial = _create_trial(
        client,
        headers,
        project_id,
        schema_id,
        prompt_id,
        doc_ids,
        "mock-slow",
        base_url,
    )

    # Wait until the worker has actually picked the task up (PENDING→PROCESSING
    # via the task_prerun signal); cancelling while still PENDING would hit the
    # task's stale-delivery guard instead of the cancellation watcher.
    processing = _wait_for(
        lambda: (
            _get_trial(client, headers, project_id, trial["id"])["status"]
            == "processing"
        ),
        timeout=30,
    )
    if not processing:
        print("[cancel] FAIL: trial never reached processing")
        return False
    time.sleep(1.5)  # let the per-document LLM calls go in-flight

    resp = client.post(
        f"{_API}/project/{project_id}/trial/{trial['id']}/cancel", headers=headers
    )
    assert resp.status_code == 200, resp.text

    # The cancel endpoint flips status immediately; wait for the WORKER's
    # finalization (meta.failures written) to prove the watcher aborted the
    # in-flight documents.
    final = _wait_for(
        lambda: (
            t
            if (
                (
                    (t := _get_trial(client, headers, project_id, trial["id"])).get(
                        "meta"
                    )
                )
                or {}
            ).get("failures")
            else None
        ),
        timeout=60,
    )
    results = _get_results(client, headers, project_id, trial["id"])
    status = (final or {}).get("status", "timeout")
    failures = ((final or {}).get("meta") or {}).get("failures") or {}
    print(
        f"[cancel] status={status} failures={sorted(set(failures.values()))} "
        f"results={len(results)} (want cancelled/Cancelled/0)"
    )
    ok = (
        status == "cancelled"
        and failures
        and all(v == "Cancelled" for v in failures.values())
        and len(results) == 0
    )
    print("[cancel] PASS" if ok else "[cancel] FAIL")
    return ok


# ───────────────────────── main ─────────────────────────


def main() -> int:
    from fastapi.testclient import TestClient

    from backend.src.main import app

    llm_server, llm_base_url = _start_fake_llm()
    email, password = _seed_admin()

    worker = _start_worker()
    time.sleep(5)  # let the worker connect + start consuming
    ok = True
    try:
        if worker.poll() is not None:
            print(f"FAIL: worker exited early (code {worker.returncode})")
            return 1

        with TestClient(app) as client:
            resp = client.post(
                f"{_API}/auth/login", data={"username": email, "password": password}
            )
            assert resp.status_code == 200, resp.text
            headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

            ok = _scenario_happy(client, headers, llm_base_url) and ok
            ok = _scenario_failure(client, headers, llm_base_url) and ok
            ok = _scenario_cancel(client, headers, llm_base_url) and ok
    finally:
        llm_server.shutdown()
        worker.terminate()
        try:
            worker.wait(timeout=15)
        except subprocess.TimeoutExpired:
            worker.kill()

    print("PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
