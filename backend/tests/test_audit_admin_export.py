# backend/tests/test_audit_admin_export.py
"""Tests for three previously untested surfaces:

- Audit trail: login success/failure rows, the admin read API (+ admin guard),
  and the project-delete audit regression — the delete endpoint used to pass
  the just-deleted project's id as ``project_id``, so the FK on
  ``audit_logs.project_id`` rejected the insert and the best-effort
  ``record_audit`` silently dropped the row: project deletions were never
  audited.
- Admin settings: override round-trip (stored → effective → live settings
  proxy), bool canonicalization, readonly/unknown-key rejection, invalid-value
  422, secret overrides encrypted at rest and never echoed, delete-override
  revert, and the keys-only SETTING_CHANGE audit.
- Evaluation export: CSV and streamed ZIP downloads over a real evaluation
  graph, including the PHI-egress EXPORT audit row.
"""

import io
import uuid
import zipfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_url():
    return "/api/v1"


@pytest.fixture
def client():
    from ..src.main import app

    return TestClient(app)


def _login_headers(client, api_url, email, password):
    resp = client.post(
        f"{api_url}/auth/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _admin_headers(client, api_url):
    return _login_headers(client, api_url, "admin@example.com", "Adminpassword1")


def _audit_rows(client, api_url, headers, **params):
    resp = client.get(f"{api_url}/admin/audit", headers=headers, params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()["items"]


# ---------------------------------------------------------------------------
# audit trail
# ---------------------------------------------------------------------------


def test_audit_api_requires_admin(client, api_url):
    user_headers = _login_headers(client, api_url, "test@example.com", "Testpassword1")
    resp = client.get(f"{api_url}/admin/audit", headers=user_headers)
    assert resp.status_code in (401, 403)


def test_login_success_and_failure_are_audited(client, api_url):
    admin_headers = _admin_headers(client, api_url)

    resp = client.post(
        f"{api_url}/auth/login",
        data={"username": "another@example.com", "password": "WrongPassword1"},
    )
    assert resp.status_code == 401
    # Reset the failed-attempt counter (and produce a success row).
    _login_headers(client, api_url, "another@example.com", "Anotherpassword1")

    failures = _audit_rows(client, api_url, admin_headers, action="login_failure")
    assert any(r["actor_email"] == "another@example.com" for r in failures)
    successes = _audit_rows(client, api_url, admin_headers, action="login_success")
    assert any(r["actor_email"] == "another@example.com" for r in successes)


def test_project_delete_writes_audit_row(client, api_url):
    """Regression: the DELETE-project audit row must actually be written (the
    old project_id FK reference to the deleted row silently killed it)."""
    headers = _admin_headers(client, api_url)
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Audit Delete"}
    ).json()["id"]

    resp = client.delete(f"{api_url}/project/{project_id}", headers=headers)
    assert resp.status_code == 200, resp.text

    rows = _audit_rows(
        client, api_url, headers, action="delete", resource_type="project"
    )
    matching = [r for r in rows if r["resource_id"] == str(project_id)]
    assert matching, "project deletion left no audit row"
    row = matching[0]
    assert row["actor_email"] == "admin@example.com"
    assert row["outcome"] == "success"
    assert "deleted" in (row["detail"] or {})


# ---------------------------------------------------------------------------
# admin settings
# ---------------------------------------------------------------------------


def test_settings_read_requires_admin_and_hides_secrets(client, api_url):
    user_headers = _login_headers(client, api_url, "test@example.com", "Testpassword1")
    assert client.get(
        f"{api_url}/admin/settings", headers=user_headers
    ).status_code in (401, 403)

    admin_headers = _admin_headers(client, api_url)
    resp = client.get(f"{api_url}/admin/settings", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    secret = body["SECRET_KEY"]
    assert secret["readonly"] is True
    assert secret["secret"] is True
    assert secret["original"] is None
    assert secret["override"] is None
    assert secret["effective"] is None
    assert secret["is_set"] is True

    banner = body["BANNER_TEXT"]
    assert banner["readonly"] is False
    assert banner["secret"] is False


def test_settings_override_round_trip_and_audit(client, api_url):
    from ..src.core import config

    headers = _admin_headers(client, api_url)

    resp = client.put(
        f"{api_url}/admin/settings",
        headers=headers,
        json={"BANNER_TEXT": "Maintenance tonight", "BANNER_ENABLED": "1"},
    )
    assert resp.status_code == 200, resp.text

    body = client.get(f"{api_url}/admin/settings", headers=headers).json()
    assert body["BANNER_TEXT"]["override"] == "Maintenance tonight"
    assert body["BANNER_TEXT"]["overridden"] is True
    # Bool canonicalized to lowercase "true" (not Python's str(True)).
    assert body["BANNER_ENABLED"]["override"] == "true"

    # The LIVE settings proxy reflects the override immediately.
    assert config.settings.BANNER_TEXT == "Maintenance tonight"
    assert config.settings.BANNER_ENABLED is True

    # Audited with the changed KEYS only — values may be security-relevant.
    rows = _audit_rows(client, api_url, headers, action="setting_change")
    keys_rows = [r for r in rows if "keys" in (r["detail"] or {})]
    assert keys_rows and set(keys_rows[0]["detail"]["keys"]) == {
        "BANNER_TEXT",
        "BANNER_ENABLED",
    }
    assert "Maintenance tonight" not in str(keys_rows[0]["detail"])

    # Deleting the override reverts the live value to the env default.
    resp = client.delete(f"{api_url}/admin/settings/BANNER_TEXT", headers=headers)
    assert resp.status_code == 200, resp.text
    resp = client.delete(f"{api_url}/admin/settings/BANNER_ENABLED", headers=headers)
    assert resp.status_code == 200, resp.text
    assert config.settings.BANNER_TEXT != "Maintenance tonight"
    body = client.get(f"{api_url}/admin/settings", headers=headers).json()
    assert body["BANNER_TEXT"]["overridden"] is False


def test_settings_rejects_readonly_unknown_and_invalid_values(client, api_url):
    headers = _admin_headers(client, api_url)

    resp = client.put(
        f"{api_url}/admin/settings", headers=headers, json={"SECRET_KEY": "x"}
    )
    assert resp.status_code == 400

    resp = client.put(
        f"{api_url}/admin/settings", headers=headers, json={"NOT_A_SETTING": "x"}
    )
    assert resp.status_code == 400

    resp = client.put(
        f"{api_url}/admin/settings",
        headers=headers,
        json={"INVITATION_EXPIRE_HOURS": "not-a-number"},
    )
    assert resp.status_code == 422

    resp = client.delete(f"{api_url}/admin/settings/BANNER_COLOR", headers=headers)
    assert resp.status_code == 404  # no override present


def test_secret_setting_override_encrypted_at_rest_and_clearable(client, api_url):
    from ..src.db.session import SessionLocal
    from ..src.models import AppSetting
    from ..src.utils.crypto import decrypt

    headers = _admin_headers(client, api_url)
    plaintext = "sk-test-secret-override-123"

    resp = client.put(
        f"{api_url}/admin/settings", headers=headers, json={"OPENAI_API_KEY": plaintext}
    )
    assert resp.status_code == 200, resp.text

    db = SessionLocal()
    try:
        row = db.get(AppSetting, "OPENAI_API_KEY")
        assert row is not None
        assert row.value != plaintext, "secret override persisted in plaintext"
        assert decrypt(row.value) == plaintext
    finally:
        db.close()

    body = client.get(f"{api_url}/admin/settings", headers=headers).json()
    entry = body["OPENAI_API_KEY"]
    assert entry["is_set"] is True
    assert entry["override"] is None and entry["effective"] is None
    assert plaintext not in str(body)

    # Empty value clears the override (reverting to the env value).
    resp = client.put(
        f"{api_url}/admin/settings", headers=headers, json={"OPENAI_API_KEY": ""}
    )
    assert resp.status_code == 200, resp.text
    db = SessionLocal()
    try:
        assert db.get(AppSetting, "OPENAI_API_KEY") is None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# evaluation export
# ---------------------------------------------------------------------------


def _build_evaluation_graph(project_id: int):
    """file → config → document → schema/prompt → trial → result → ground
    truth → evaluation (+ one metric). Returns the evaluation id."""
    from ..src import models
    from ..src.db.session import SessionLocal

    db = SessionLocal()
    try:
        config = models.PreprocessingConfiguration(
            project_id=project_id, name="cfg", additional_settings={}
        )
        db.add(config)
        db.flush()
        file = models.File(
            project_id=project_id,
            file_uuid=str(uuid.uuid4()),
            file_name="doc.txt",
            file_type="text/plain",
        )
        db.add(file)
        db.flush()
        doc = models.Document(
            project_id=project_id,
            original_file_id=file.id,
            preprocessing_config_id=config.id,
            text="patient report text",
            document_name="doc.txt",
            is_latest=True,
        )
        db.add(doc)
        db.flush()
        schema = models.Schema(
            project_id=project_id,
            schema_name="s",
            schema_definition={"type": "object", "properties": {"a": {}}},
        )
        prompt = models.Prompt(project_id=project_id, name="p")
        db.add_all([schema, prompt])
        db.flush()
        trial = models.Trial(
            project_id=project_id,
            project_trial_number=1,
            schema_id=schema.id,
            prompt_id=prompt.id,
            llm_model="m",
            base_url="http://localhost",
            document_ids=[doc.id],
        )
        trial.api_key = "k"
        db.add(trial)
        db.flush()
        db.add(
            models.TrialResult(trial_id=trial.id, document_id=doc.id, result={"a": 1})
        )
        gt = models.GroundTruth(
            project_id=project_id, name="gt", format="csv", file_uuid=str(uuid.uuid4())
        )
        db.add(gt)
        db.flush()
        evaluation = models.Evaluation(
            trial_id=trial.id,
            groundtruth_id=gt.id,
            metrics={"accuracy": 1.0, "total_documents": 1},
            field_metrics={"a": {"accuracy": 1.0, "correct": 1, "total": 1}},
            document_metrics=[{"document_id": doc.id, "accuracy": 1.0}],
        )
        db.add(evaluation)
        db.flush()
        db.add(
            models.EvaluationMetric(
                evaluation_id=evaluation.id,
                document_id=doc.id,
                field_name="a",
                is_correct=True,
            )
        )
        db.commit()
        return evaluation.id
    finally:
        db.close()


def test_evaluation_export_csv_and_zip(client, api_url):
    headers = _admin_headers(client, api_url)
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Eval Export"}
    ).json()["id"]
    evaluation_id = _build_evaluation_graph(project_id)

    # CSV
    resp = client.get(
        f"{api_url}/project/{project_id}/evaluations/download",
        headers=headers,
        params={"evaluation_ids": [str(evaluation_id)], "format": "csv"},
    )
    assert resp.status_code == 200, resp.text
    assert "text/csv" in resp.headers["content-type"]
    assert resp.text.strip(), "CSV export is empty"

    # ZIP (streamed)
    resp = client.get(
        f"{api_url}/project/{project_id}/evaluations/download",
        headers=headers,
        params={"evaluation_ids": [str(evaluation_id)], "format": "zip"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = zf.namelist()
        assert names, "ZIP export has no entries"
        assert not any(n.startswith("/") or ".." in n for n in names)

    # PHI-egress audit row.
    rows = _audit_rows(
        client,
        api_url,
        headers,
        action="export",
        resource_type="evaluation",
        project_id=project_id,
    )
    assert rows, "evaluation export was not audited"
    assert rows[0]["detail"]["evaluation_ids"] == [evaluation_id]

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_evaluation_export_validates_ids(client, api_url):
    headers = _admin_headers(client, api_url)
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Eval Export Bad Ids"}
    ).json()["id"]

    resp = client.get(
        f"{api_url}/project/{project_id}/evaluations/download",
        headers=headers,
        params={"evaluation_ids": ["abc"], "format": "csv"},
    )
    assert resp.status_code == 400

    resp = client.get(
        f"{api_url}/project/{project_id}/evaluations/download",
        headers=headers,
        params={"evaluation_ids": ["999999"], "format": "csv"},
    )
    assert resp.status_code == 404

    client.delete(f"{api_url}/project/{project_id}", headers=headers)
