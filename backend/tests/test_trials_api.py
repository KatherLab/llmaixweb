"""Trial API surface with a MOCKED LLM.

These tests used to skip in CI under ``OPENAI_NO_API_CHECK`` because the
``bypass_celery`` extraction path calls a real LLM. They now stub the single LLM
seam (``backend.src.utils.info_extraction.OpenAI``) with a fake that returns JSON
matching each test's schema, so the full synchronous trial pipeline — create,
extract, store, read back, download, update, delete, cross-user authz — runs
offline. ``bypass_celery`` is admin-only, so every test authenticates as
``admin@example.com`` (the ``admin_headers`` fixture).

Complements ``test_trial_execution.py`` (which focuses on status transitions and
result-parsing edge cases via the same seam).
"""

import io
import json
import zipfile

from .fake_llm import make_fake_openai

# Creds spread into every trial-create body. base_url passes the SSRF +
# ALLOWED_LLM_ENDPOINTS checks in the test config; the client itself is mocked.
_LLM_CREDS = {
    "llm_model": "mock-model",
    "api_key": "test-key",
    "base_url": "http://localhost:11434/v1",
}


# --------------------------------------------------------------------------- #
# Shared setup helpers
#
# The filter/pagination/download/evaluate tests below only need a completed
# trial with results — they don't re-assert the create→extract→store pipeline
# (that's ``test_trial_crud_and_extraction`` / ``test_trial_execution.py``).
# These helpers collapse the project + prompt + schema + document + trial
# boilerplate so each test states just the behaviour it exercises.
# --------------------------------------------------------------------------- #
def _mk_prompt(client, api_url, headers, project_id, name="P"):
    return client.post(
        f"{api_url}/project/{project_id}/prompt",
        headers=headers,
        json={
            "name": name,
            "system_prompt": "Extract: {document_content}",
            "user_prompt": "Doc: {document_content}",
            "project_id": project_id,
        },
    ).json()["id"]


def _mk_schema(client, api_url, headers, project_id, name="S", props=None):
    props = props or {"field1": {"type": "string"}}
    return client.post(
        f"{api_url}/project/{project_id}/schema",
        headers=headers,
        json={
            "schema_name": name,
            "schema_definition": {"type": "object", "properties": props},
        },
    ).json()["id"]


def _seed_docs(client, api_url, headers, project_id, names):
    """Upload + synchronously preprocess ``names`` .txt files -> list of doc ids."""
    file_ids = []
    for n in names:
        file_ids.append(
            client.post(
                f"{api_url}/project/{project_id}/file",
                headers=headers,
                files={
                    "file": (n, f"content of {n}".encode(), "text/plain"),
                    "file_info": (
                        "",
                        json.dumps({"file_name": n, "file_type": "text/plain"}),
                        "application/json",
                    ),
                },
            ).json()["id"]
        )
    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": file_ids,
            "inline_config": {"name": "cfg", "description": "d"},
            "bypass_celery": True,
        },
    )
    assert resp.status_code == 200, resp.text
    docs = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()["items"]
    return [d["id"] for d in docs]


def _mk_trial(
    client, api_url, headers, project_id, schema_id, prompt_id, doc_ids, **extra
):
    body = {
        "schema_id": schema_id,
        "prompt_id": prompt_id,
        "document_ids": doc_ids,
        "bypass_celery": True,
        **_LLM_CREDS,
        **extra,
    }
    resp = client.post(
        f"{api_url}/project/{project_id}/trial", headers=headers, json=body
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_trial_crud_and_extraction(client, api_url, admin_headers, login, monkeypatch):
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"field1": "a", "field2": "b"}),
    )
    headers = admin_headers

    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Trial Project"}
    ).json()["id"]

    # Create prompt (with {document_content})
    prompt_data = {
        "name": "Extraction Prompt",
        "system_prompt": "Extract this: {document_content}",
        "user_prompt": "Extract info: {document_content}",
        "project_id": project_id,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/prompt", headers=headers, json=prompt_data
    )
    assert response.status_code == 200
    prompt_id = response.json()["id"]

    # Create schema
    schema_data = {
        "schema_name": "Trial Schema",
        "schema_definition": {
            "type": "object",
            "properties": {
                "field1": {"type": "string"},
                "field2": {"type": "string"},
            },
            "required": ["field1"],
        },
    }
    response = client.post(
        f"{api_url}/project/{project_id}/schema", headers=headers, json=schema_data
    )
    schema_id = response.json()["id"]

    # Upload a file and preprocess it to create a document
    file_data = {
        "file": ("trial_doc.txt", b"test document content", "text/plain"),
        "file_info": (
            "",
            '{"file_name": "trial_doc.txt", "file_type": "text/plain"}',
            "application/json",
        ),
    }
    file_id = client.post(
        f"{api_url}/project/{project_id}/file", headers=headers, files=file_data
    ).json()["id"]

    preprocess_data = {
        "file_ids": [file_id],
        "inline_config": {
            "name": "Trial File Config",
            "description": "Config for trial file",
        },
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json=preprocess_data,
    )
    assert response.status_code == 200

    # Get document ID
    document_id = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()["items"][0]["id"]

    # Create trial
    trial_data = {
        "schema_id": schema_id,
        "prompt_id": prompt_id,
        "document_ids": [document_id],
        "bypass_celery": True,
        **_LLM_CREDS,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/trial", headers=headers, json=trial_data
    )
    assert response.status_code == 200
    trial = response.json()
    trial_id = trial["id"]
    assert trial["status"] in ["completed", "pending", "in_progress"]

    # Get all trials for project
    response = client.get(f"{api_url}/project/{project_id}/trial", headers=headers)
    assert response.status_code == 200
    assert any(t["id"] == trial_id for t in response.json()["items"])

    # Get single trial
    response = client.get(
        f"{api_url}/project/{project_id}/trial/{trial_id}", headers=headers
    )
    assert response.status_code == 200
    trial = response.json()
    assert trial["id"] == trial_id
    assert trial["prompt"]["id"] == prompt_id

    # Update trial name/description
    response = client.patch(
        f"{api_url}/project/{project_id}/trial/{trial_id}",
        headers=headers,
        json={"name": "Updated Trial", "description": "Updated desc"},
    )
    assert response.status_code == 200
    updated_trial = response.json()
    assert updated_trial["name"] == "Updated Trial"
    assert updated_trial["description"] == "Updated desc"

    # Delete trial
    response = client.delete(
        f"{api_url}/project/{project_id}/trial/{trial_id}", headers=headers
    )
    assert response.status_code == 200

    # Get deleted trial should 404
    response = client.get(
        f"{api_url}/project/{project_id}/trial/{trial_id}", headers=headers
    )
    assert response.status_code == 404

    # Forbidden trial get (other user)
    response = client.post(
        f"{api_url}/project/{project_id}/trial", headers=headers, json=trial_data
    )
    trial_id = response.json()["id"]

    headers2 = login("another@example.com", "Anotherpassword1")
    resp = client.get(
        f"{api_url}/project/{project_id}/trial/{trial_id}", headers=headers2
    )
    assert resp.status_code in [403, 404]


def test_trial_result_download_and_status(client, api_url, admin_headers, monkeypatch):
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"foo": "bar"}),
    )
    headers = admin_headers

    # Create project, prompt, schema, document
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "TrialDL"}
    ).json()["id"]

    prompt_id = client.post(
        f"{api_url}/project/{project_id}/prompt",
        headers=headers,
        json={
            "name": "DLPrompt",
            "system_prompt": "Extract: {document_content}",
            "user_prompt": "Extract this: {document_content}",
            "project_id": project_id,
        },
    ).json()["id"]
    schema_id = client.post(
        f"{api_url}/project/{project_id}/schema",
        headers=headers,
        json={
            "schema_name": "DL",
            "schema_definition": {
                "type": "object",
                "properties": {"foo": {"type": "string"}},
            },
        },
    ).json()["id"]
    file_data = {
        "file": ("dl.txt", b"foo content", "text/plain"),
        "file_info": (
            "",
            '{"file_name": "dl.txt", "file_type": "text/plain"}',
            "application/json",
        ),
    }
    file_id = client.post(
        f"{api_url}/project/{project_id}/file", headers=headers, files=file_data
    ).json()["id"]
    client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [file_id],
            "inline_config": {"name": "cfg", "description": "Config for download test"},
            "bypass_celery": True,
        },
    )
    doc_id = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()["items"][0]["id"]

    # Create trial
    trial_id = client.post(
        f"{api_url}/project/{project_id}/trial",
        headers=headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_ids": [doc_id],
            "bypass_celery": True,
            **_LLM_CREDS,
        },
    ).json()["id"]

    # Download trial results (json)
    response = client.get(
        f"{api_url}/project/{project_id}/trial/{trial_id}/download?format=json",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")

    # Download trial results (csv)
    response = client.get(
        f"{api_url}/project/{project_id}/trial/{trial_id}/download?format=csv",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/zip"
    ) or response.headers["content-type"].startswith("text/csv")

    # Download trial progress (should be completed)
    response = client.get(
        f"{api_url}/project/{project_id}/preprocess/{trial_id}/progress",
        headers=headers,
    )
    # If not a preprocessing task ID, might 404; that's fine here
    assert response.status_code in [200, 404]


def test_create_trial_with_table_preprocessing(
    client, api_url, admin_headers, monkeypatch
):
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai(
            {
                "patient": "Alice",
                "diagnosis": "Flu",
                "location": "Leipzig",
                "date": "2024-05-01",
            }
        ),
    )
    headers = admin_headers

    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "TableTrial"}
    ).json()["id"]

    prompt_id = client.post(
        f"{api_url}/project/{project_id}/prompt",
        headers=headers,
        json={
            "name": "TablePrompt",
            "system_prompt": "Extract table: {document_content}",
            "user_prompt": "Table: {document_content}",
            "project_id": project_id,
        },
    ).json()["id"]

    # CSV content (3 rows)
    csv_content = """patient,diagnosis,location,date
Alice,Flu,Leipzig,2024-05-01
Bob,Covid,Berlin,2024-06-02
Carol,Cold,Hamburg,2024-07-03
"""
    file_id = client.post(
        f"{api_url}/project/{project_id}/file",
        headers=headers,
        files={"file": ("patients.csv", csv_content.encode(), "text/csv")},
        data={
            "file_info": json.dumps(
                {
                    "file_name": "patients.csv",
                    "file_type": "text/csv",
                    "preprocessing_strategy": "row_by_row",
                    "file_metadata": {
                        "delimiter": ",",
                        "encoding": "utf-8",
                        "has_header": True,
                        "text_columns": ["patient", "diagnosis", "location", "date"],
                        "case_id_column": "patient",
                    },
                }
            )
        },
    ).json()["id"]

    # Preprocess file with inline config
    preprocessing_response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [file_id],
            "inline_config": {
                "name": "CSV row-by-row",
                "description": "Process CSV per patient row",
            },
            "bypass_celery": True,
        },
    )
    assert preprocessing_response.status_code == 200

    # Check documents created
    docs = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()
    assert docs["total"] == 3
    doc_ids = [d["id"] for d in docs["items"]]
    assert sorted([d["document_name"] for d in docs["items"]]) == [
        "Alice",
        "Bob",
        "Carol",
    ]

    # Schema matching CSV
    schema = {
        "type": "object",
        "properties": {
            "patient": {"type": "string"},
            "diagnosis": {"type": "string"},
            "location": {"type": "string"},
            "date": {"type": "string"},
        },
        "required": ["patient", "diagnosis", "location", "date"],
    }
    schema_id = client.post(
        f"{api_url}/project/{project_id}/schema",
        headers=headers,
        json={"schema_name": "Patient CSV", "schema_definition": schema},
    ).json()["id"]

    # Create trial with all docs
    trial_id = client.post(
        f"{api_url}/project/{project_id}/trial",
        headers=headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_ids": doc_ids,
            "bypass_celery": True,
            **_LLM_CREDS,
        },
    ).json()["id"]

    # Results: all docs should have a result
    result = client.get(
        f"{api_url}/project/{project_id}/trial/{trial_id}?include_results=true",
        headers=headers,
    ).json()
    assert result["status"] == "completed"
    assert len(result["results"]) == 3
    for res in result["results"]:
        extracted = res["result"]
        assert "patient" in extracted
        assert "diagnosis" in extracted
        assert "location" in extracted
        assert "date" in extracted


def test_create_trial_with_mixed_preprocessing(
    client, api_url, files_base_path, admin_headers, monkeypatch
):
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai(
            {"patient": "Alice", "diagnosis": "Headache", "location": "Dresden"}
        ),
    )
    headers = admin_headers

    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "MixedTrial"}
    ).json()["id"]

    prompt_id = client.post(
        f"{api_url}/project/{project_id}/prompt",
        headers=headers,
        json={
            "name": "MixedPrompt",
            "system_prompt": "Extract: {document_content}",
            "user_prompt": "Extract: {document_content}",
            "project_id": project_id,
        },
    ).json()["id"]

    # Upload text file
    text_content = "Patient: Alice\nDiagnosis: Headache\nLocation: Dresden\n"
    file_data1 = {
        "file": ("note.txt", text_content.encode(), "text/plain"),
        "file_info": (
            "",
            '{"file_name": "note.txt", "file_type": "text/plain"}',
            "application/json",
        ),
    }
    file1_id = client.post(
        f"{api_url}/project/{project_id}/file", headers=headers, files=file_data1
    ).json()["id"]

    # Upload PDF file using the actual PDF
    with open(files_base_path / "9874562_text.pdf", "rb") as f:
        file_data2 = {
            "file": ("9874562_text.pdf", f, "application/pdf"),
            "file_info": (
                "",
                '{"file_name": "9874562_text.pdf", "file_type": "application/pdf"}',
                "application/json",
            ),
        }
        file2_id = client.post(
            f"{api_url}/project/{project_id}/file", headers=headers, files=file_data2
        ).json()["id"]

    # Preprocess files with inline configs
    client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [file1_id],
            "inline_config": {"name": "Text Config", "description": "Config for text"},
            "bypass_celery": True,
        },
    )
    # Preprocess pdf
    preprocessing_response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [file2_id],
            "inline_config": {"name": "PDF Config", "description": "Config for PDF"},
            "bypass_celery": True,
        },
    )
    assert preprocessing_response.status_code == 200

    # Docs
    docs = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()
    assert docs["total"] == 2
    doc_ids = [d["id"] for d in docs["items"]]

    # Schema
    schema = {
        "type": "object",
        "properties": {
            "patient": {"type": "string"},
            "diagnosis": {"type": "string"},
            "location": {"type": "string"},
        },
        "required": ["patient", "diagnosis"],
    }
    schema_id = client.post(
        f"{api_url}/project/{project_id}/schema",
        headers=headers,
        json={"schema_name": "Mixed", "schema_definition": schema},
    ).json()["id"]

    # Create trial with both docs
    trial_id = client.post(
        f"{api_url}/project/{project_id}/trial",
        headers=headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_ids": doc_ids,
            "bypass_celery": True,
            **_LLM_CREDS,
        },
    ).json()["id"]

    result = client.get(
        f"{api_url}/project/{project_id}/trial/{trial_id}?include_results=true",
        headers=headers,
    ).json()
    assert result["status"] == "completed"
    assert len(result["results"]) == 2
    for r in result["results"]:
        assert "patient" in r["result"]


def test_ocr_preprocessing_for_extraction(
    client, api_url, files_base_path, admin_headers, monkeypatch
):
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"patient": "Ashley Park", "diagnosis": "PE"}),
    )
    headers = admin_headers

    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "OCRTrial"}
    ).json()["id"]

    # Prompt with {document_content}
    prompt_id = client.post(
        f"{api_url}/project/{project_id}/prompt",
        headers=headers,
        json={
            "name": "OCRPrompt",
            "system_prompt": "Extract from scan: {document_content}",
            "user_prompt": "Scan: {document_content}",
            "project_id": project_id,
        },
    ).json()["id"]

    # --- Use a real PDF scan for OCR ---
    with open(files_base_path / "9874562_notext.pdf", "rb") as f:
        file_data = {
            "file": ("9874562_notext.pdf", f, "application/pdf"),
            "file_info": (
                "",
                '{"file_name": "9874562_notext.pdf", "file_type": "application/pdf"}',
                "application/json",
            ),
        }
        file_id = client.post(
            f"{api_url}/project/{project_id}/file", headers=headers, files=file_data
        ).json()["id"]

    # Preprocess with inline OCR config
    preprocessing_response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [file_id],
            "inline_config": {
                "name": "OCRScanConfig",
                "description": "OCR config for test scan",
            },
            "bypass_celery": True,
        },
    )
    assert preprocessing_response.status_code == 200

    # Doc
    doc = client.get(
        f"{api_url}/project/{project_id}/document", headers=headers
    ).json()["items"][0]

    # For PDF
    assert doc["meta_data"].get("file_type", doc.get("file_type")) in [
        "application/pdf",
        "image/png",
    ]

    # Schema
    schema = {
        "type": "object",
        "properties": {
            "patient": {"type": "string"},
            "diagnosis": {"type": "string"},
        },
        "required": ["patient"],
    }
    schema_id = client.post(
        f"{api_url}/project/{project_id}/schema",
        headers=headers,
        json={"schema_name": "OCR", "schema_definition": schema},
    ).json()["id"]

    # Create trial
    trial_id = client.post(
        f"{api_url}/project/{project_id}/trial",
        headers=headers,
        json={
            "schema_id": schema_id,
            "prompt_id": prompt_id,
            "document_ids": [doc["id"]],
            "bypass_celery": True,
            **_LLM_CREDS,
        },
    ).json()["id"]

    result = client.get(
        f"{api_url}/project/{project_id}/trial/{trial_id}?include_results=true",
        headers=headers,
    ).json()
    assert result["status"] == "completed"
    assert len(result["results"]) == 1
    assert "patient" in result["results"][0]["result"]


def test_get_trials_invalid_status_filter_returns_400(
    client, api_url, user_headers, make_project
):
    """An unknown/typo'd status filter must 400 (like list_trial_results),
    not silently return an empty page that masks the client's mistake."""
    project_id = make_project(user_headers)["id"]

    resp = client.get(
        f"{api_url}/project/{project_id}/trial?status=running", headers=user_headers
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "trials.invalid_status_filter"

    # Uppercase of a valid value is still invalid (enum values are lowercase).
    resp = client.get(
        f"{api_url}/project/{project_id}/trial?status=PENDING", headers=user_headers
    )
    assert resp.status_code == 400, resp.text

    # A valid status filter is accepted.
    resp = client.get(
        f"{api_url}/project/{project_id}/trial?status=pending", headers=user_headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0


# --------------------------------------------------------------------------- #
# get_trials — filter matrix
# --------------------------------------------------------------------------- #
def test_get_trials_filter_matrix(client, api_url, admin_headers, monkeypatch):
    """Every server-side filter branch of ``get_trials`` narrows the page as
    documented: schema_id / prompt_id / llm_model equality, the search
    numeric-id branch vs the name/text ILIKE branch, and the created_at
    date_from (inclusive) / date_to (exclusive) window. Seeds three trials that
    overlap on each dimension so a filter that ignored its argument would return
    the wrong set, not just the same set."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"field1": "x"}),
    )
    headers = admin_headers
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "FilterMatrix"}
    ).json()["id"]

    schema_a = _mk_schema(client, api_url, headers, project_id, name="SA")
    schema_b = _mk_schema(client, api_url, headers, project_id, name="SB")
    prompt_a = _mk_prompt(client, api_url, headers, project_id, name="PA")
    prompt_b = _mk_prompt(client, api_url, headers, project_id, name="PB")
    doc_ids = _seed_docs(client, api_url, headers, project_id, ["fm.txt"])

    # schema_a/prompt_a/model-x, schema_b/prompt_a/model-y, schema_a/prompt_b/model-x
    t1 = _mk_trial(
        client,
        api_url,
        headers,
        project_id,
        schema_a,
        prompt_a,
        doc_ids,
        name="Alpha One",
        llm_model="model-x",
    )["id"]
    t2 = _mk_trial(
        client,
        api_url,
        headers,
        project_id,
        schema_b,
        prompt_a,
        doc_ids,
        name="Beta Two",
        llm_model="model-y",
    )["id"]
    t3 = _mk_trial(
        client,
        api_url,
        headers,
        project_id,
        schema_a,
        prompt_b,
        doc_ids,
        name="Gamma Three",
        llm_model="model-x",
    )["id"]

    def ids(**params):
        resp = client.get(
            f"{api_url}/project/{project_id}/trial", headers=headers, params=params
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        got = {t["id"] for t in body["items"]}
        # total must agree with the page when everything fits on one page.
        assert body["total"] == len(body["items"])
        return got

    assert ids() == {t1, t2, t3}
    assert ids(status="completed") == {t1, t2, t3}
    # schema/prompt/model equality filters.
    assert ids(schema_id=schema_a) == {t1, t3}
    assert ids(prompt_id=prompt_a) == {t1, t2}
    assert ids(llm_model="model-y") == {t2}
    # search name-ILIKE branch (non-numeric term).
    assert ids(search="Alpha") == {t1}
    assert ids(search="gamma") == {t3}  # ILIKE is case-insensitive
    # search numeric-id branch matches the exact id (names carry no digits here).
    assert ids(search=str(t2)) == {t2}
    # date window: created_at is ~now, so a far-future lower bound excludes all
    # and a far-past lower bound includes all; the upper bound is exclusive.
    assert ids(date_from="2999-01-01T00:00:00") == set()
    assert ids(date_from="2000-01-01T00:00:00") == {t1, t2, t3}
    assert ids(date_to="2000-01-01T00:00:00") == set()
    assert ids(date_to="2999-01-01T00:00:00") == {t1, t2, t3}

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_get_trials_has_failures_filter_and_pagination(
    client, api_url, admin_headers, monkeypatch
):
    """``has_failures`` is evaluated in Python over ``meta.failures``, so the
    match must be computed BEFORE limit/offset: ``total`` counts every match
    while ``items`` is only the requested slice. A naive post-filter of a sliced
    page would desync the two and silently drop rows."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"field1": "x"}),
    )
    headers = admin_headers
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "HasFailures"}
    ).json()["id"]
    schema_id = _mk_schema(client, api_url, headers, project_id)
    prompt_id = _mk_prompt(client, api_url, headers, project_id)
    doc_ids = _seed_docs(client, api_url, headers, project_id, ["hf.txt"])

    t_ids = [
        _mk_trial(client, api_url, headers, project_id, schema_id, prompt_id, doc_ids)[
            "id"
        ]
        for _ in range(3)
    ]

    # Stamp per-document failures on two of the three trials.
    from backend.src.db.session import SessionLocal
    from backend.src.models.project import Trial

    db = SessionLocal()
    for tid in t_ids[:2]:
        trial_db = db.get(Trial, tid)
        trial_db.meta = {"failures": {str(doc_ids[0]): "provider error"}}
    db.commit()
    db.close()

    def page(**params):
        resp = client.get(
            f"{api_url}/project/{project_id}/trial", headers=headers, params=params
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    failed = page(has_failures="true")
    assert failed["total"] == 2
    assert {t["id"] for t in failed["items"]} == set(t_ids[:2])
    # has_failures rows expose the count on the summary.
    assert all(t["error_count"] == 1 for t in failed["items"])

    ok = page(has_failures="false")
    assert ok["total"] == 1
    assert {t["id"] for t in ok["items"]} == {t_ids[2]}

    # Pagination: total still reflects ALL matches; items is the single-row slice.
    sliced = page(has_failures="true", limit=1, offset=0)
    assert sliced["total"] == 2
    assert len(sliced["items"]) == 1

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


# --------------------------------------------------------------------------- #
# list_trial_results — status / search / usage aggregation
# --------------------------------------------------------------------------- #
def test_list_trial_results_status_and_search(
    client, api_url, admin_headers, monkeypatch
):
    """The results list must reject a bad ``status`` with 400 and filter by
    document/original-file name on ``search`` via the server-side join."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"field1": "x"}),
    )
    headers = admin_headers
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "ResultsFilter"}
    ).json()["id"]
    schema_id = _mk_schema(client, api_url, headers, project_id)
    prompt_id = _mk_prompt(client, api_url, headers, project_id)
    doc_ids = _seed_docs(
        client, api_url, headers, project_id, ["searchme.txt", "other.txt"]
    )
    trial_id = _mk_trial(
        client, api_url, headers, project_id, schema_id, prompt_id, doc_ids
    )["id"]

    results_url = f"{api_url}/project/{project_id}/trial/{trial_id}/results"

    # Bad status -> structured 400.
    resp = client.get(f"{results_url}?status=bogus", headers=headers)
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "trials.invalid_status_filter"

    # A valid status is accepted; the mocked extraction succeeds for both docs.
    resp = client.get(f"{results_url}?status=success", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 2

    # Search matches on the original file name join.
    resp = client.get(f"{results_url}?search=searchme", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["original_file_name"] == "searchme.txt"

    # Non-matching search -> empty page (not an error).
    resp = client.get(f"{results_url}?search=zzznomatch", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_list_trial_results_total_usage_sums_and_tolerates_junk(
    client, api_url, admin_headers, monkeypatch
):
    """``total_usage`` sums token counts across ALL of a trial's results for the
    meta header. It must stay lenient: a result whose stored usage carries
    non-numeric/junk values contributes 0 rather than 500-ing the endpoint."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"field1": "x"}),
    )
    headers = admin_headers
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Usage"}
    ).json()["id"]
    schema_id = _mk_schema(client, api_url, headers, project_id)
    prompt_id = _mk_prompt(client, api_url, headers, project_id)
    doc_ids = _seed_docs(client, api_url, headers, project_id, ["u1.txt", "u2.txt"])
    trial_id = _mk_trial(
        client, api_url, headers, project_id, schema_id, prompt_id, doc_ids
    )["id"]

    results_url = f"{api_url}/project/{project_id}/trial/{trial_id}/results"

    # Both docs used the fake usage (10/5/15) -> summed 20/10/30.
    resp = client.get(results_url, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_usage"] == {
        "prompt_tokens": 20,
        "completion_tokens": 10,
        "total_tokens": 15 + 15,
    }

    # Corrupt one row's usage with junk values and null out the other's
    # additional_content entirely: the aggregation must ignore both and 200.
    from backend.src.db.session import SessionLocal
    from backend.src.models.project import TrialResult

    db = SessionLocal()
    rows = db.query(TrialResult).filter(TrialResult.trial_id == trial_id).all()
    assert len(rows) == 2
    rows[0].additional_content = {
        "usage": {"prompt_tokens": "abc", "total_tokens": None}
    }
    rows[1].additional_content = None
    db.commit()
    db.close()

    resp = client.get(results_url, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_usage"] == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


# --------------------------------------------------------------------------- #
# Status-transition guards: cancel / delete
# --------------------------------------------------------------------------- #
def test_cancel_and_delete_status_guards(client, api_url, admin_headers, monkeypatch):
    """Cancelling a terminal trial is a 400; a still-running (PENDING/PROCESSING)
    trial must be cancelled before it can be deleted (409 otherwise); and a
    genuinely PENDING trial cancels cleanly to CANCELLED."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"field1": "x"}),
    )
    headers = admin_headers
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Guards"}
    ).json()["id"]
    schema_id = _mk_schema(client, api_url, headers, project_id)
    prompt_id = _mk_prompt(client, api_url, headers, project_id)
    doc_ids = _seed_docs(client, api_url, headers, project_id, ["g.txt"])

    # A bypass trial finishes COMPLETED -> cannot be cancelled.
    completed_id = _mk_trial(
        client, api_url, headers, project_id, schema_id, prompt_id, doc_ids
    )["id"]
    resp = client.post(
        f"{api_url}/project/{project_id}/trial/{completed_id}/cancel", headers=headers
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "trials.cannot_cancel"

    # Force a second trial back to PENDING to exercise the running-state guards.
    pending_id = _mk_trial(
        client, api_url, headers, project_id, schema_id, prompt_id, doc_ids
    )["id"]

    from backend.src.db.session import SessionLocal
    from backend.src.models.project import Trial, TrialStatus

    db = SessionLocal()
    db.get(Trial, pending_id).status = TrialStatus.PENDING
    db.commit()
    db.close()

    # DELETE of a running trial is refused with 409 (worker would keep writing).
    resp = client.delete(
        f"{api_url}/project/{project_id}/trial/{pending_id}", headers=headers
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "trials.still_running"

    # Cancelling the PENDING trial succeeds and flips it to CANCELLED.
    resp = client.post(
        f"{api_url}/project/{project_id}/trial/{pending_id}/cancel", headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"

    # Now that it's terminal (cancelled) it can be deleted.
    resp = client.delete(
        f"{api_url}/project/{project_id}/trial/{pending_id}", headers=headers
    )
    assert resp.status_code == 200, resp.text

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


# --------------------------------------------------------------------------- #
# update_trial
# --------------------------------------------------------------------------- #
def test_update_trial_validation_and_authz(
    client, api_url, admin_headers, user_headers, monkeypatch
):
    """PATCH with no updatable fields is a 400; a trial id from another project
    is a 404 (not a cross-project update); and a non-owner non-admin user is a
    403."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"field1": "x"}),
    )
    headers = admin_headers
    project_a = client.post(
        f"{api_url}/project", headers=headers, json={"name": "UpdA"}
    ).json()["id"]
    project_b = client.post(
        f"{api_url}/project", headers=headers, json={"name": "UpdB"}
    ).json()["id"]
    schema_id = _mk_schema(client, api_url, headers, project_a)
    prompt_id = _mk_prompt(client, api_url, headers, project_a)
    doc_ids = _seed_docs(client, api_url, headers, project_a, ["upd.txt"])
    trial_id = _mk_trial(
        client, api_url, headers, project_a, schema_id, prompt_id, doc_ids
    )["id"]

    # Neither name nor description -> 400.
    resp = client.patch(
        f"{api_url}/project/{project_a}/trial/{trial_id}", headers=headers, json={}
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "trials.no_updatable_fields"

    # Trial id addressed under a different project -> 404 (project scoping).
    resp = client.patch(
        f"{api_url}/project/{project_b}/trial/{trial_id}",
        headers=headers,
        json={"name": "x"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "trials.trial_not_found"

    # A non-owner, non-admin user cannot update the admin's project trials.
    resp = client.patch(
        f"{api_url}/project/{project_a}/trial/{trial_id}",
        headers=user_headers,
        json={"name": "x"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"]["code"] == "trials.not_authorized_update"

    client.delete(f"{api_url}/project/{project_a}", headers=headers)
    client.delete(f"{api_url}/project/{project_b}", headers=headers)


# --------------------------------------------------------------------------- #
# download_trial_results — flag combinations
# --------------------------------------------------------------------------- #
def test_download_csv_without_content_is_plain_csv(
    client, api_url, admin_headers, monkeypatch
):
    """``format=csv&include_content=false`` streams a bare text/csv body (no
    embedded source files -> no ZIP wrapper), and the usage/reasoning opt-ins
    add their columns to the header."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"field1": "x"}, reasoning="because"),
    )
    headers = admin_headers
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "DLCsv"}
    ).json()["id"]
    schema_id = _mk_schema(client, api_url, headers, project_id)
    prompt_id = _mk_prompt(client, api_url, headers, project_id)
    doc_ids = _seed_docs(client, api_url, headers, project_id, ["dl.txt"])
    trial_id = _mk_trial(
        client, api_url, headers, project_id, schema_id, prompt_id, doc_ids
    )["id"]
    dl_url = f"{api_url}/project/{project_id}/trial/{trial_id}/download"

    # Plain CSV: no ZIP, correct media type, and the extracted field is a column.
    resp = client.get(
        dl_url, headers=headers, params={"format": "csv", "include_content": False}
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    header_line = resp.text.splitlines()[0]
    assert "result.field1" in header_line
    assert "document_content" not in header_line  # content excluded

    # include_usage / include_reasoning add their columns.
    resp = client.get(
        dl_url,
        headers=headers,
        params={
            "format": "csv",
            "include_content": False,
            "include_usage": True,
            "include_reasoning": True,
        },
    )
    assert resp.status_code == 200, resp.text
    header_line = resp.text.splitlines()[0]
    assert "reasoning" in header_line
    assert "finish_reason" in header_line
    assert "usage.total_tokens" in header_line

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_download_trial_with_no_results_404(
    client, api_url, admin_headers, monkeypatch
):
    """Downloading a trial that has no result rows is a clean 404, not an empty
    archive."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"field1": "x"}),
    )
    headers = admin_headers
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "DLEmpty"}
    ).json()["id"]
    schema_id = _mk_schema(client, api_url, headers, project_id)
    prompt_id = _mk_prompt(client, api_url, headers, project_id)
    doc_ids = _seed_docs(client, api_url, headers, project_id, ["e.txt"])
    trial_id = _mk_trial(
        client, api_url, headers, project_id, schema_id, prompt_id, doc_ids
    )["id"]

    # Strip the trial's results so the download has nothing to emit.
    from backend.src.db.session import SessionLocal
    from backend.src.models.project import TrialResult

    db = SessionLocal()
    db.query(TrialResult).filter(TrialResult.trial_id == trial_id).delete()
    db.commit()
    db.close()

    for fmt in ("json", "csv"):
        resp = client.get(
            f"{api_url}/project/{project_id}/trial/{trial_id}/download",
            headers=headers,
            params={"format": fmt},
        )
        assert resp.status_code == 404, resp.text
        assert resp.json()["detail"]["code"] == "trials.no_results"

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_download_json_with_content_is_valid_zip(
    client, api_url, admin_headers, monkeypatch
):
    """Sanity check the JSON+content archive: it streams a real ZIP whose
    integrity holds and that carries metadata.json (guards the earlier
    text/csv assertion isn't masking a broken ZIP path)."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"field1": "x"}),
    )
    headers = admin_headers
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "DLZip"}
    ).json()["id"]
    schema_id = _mk_schema(client, api_url, headers, project_id)
    prompt_id = _mk_prompt(client, api_url, headers, project_id)
    doc_ids = _seed_docs(client, api_url, headers, project_id, ["z.txt"])
    trial_id = _mk_trial(
        client, api_url, headers, project_id, schema_id, prompt_id, doc_ids
    )["id"]

    resp = client.get(
        f"{api_url}/project/{project_id}/trial/{trial_id}/download",
        headers=headers,
        params={"format": "json", "include_content": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    assert zf.testzip() is None
    assert "metadata.json" in zf.namelist()

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


# --------------------------------------------------------------------------- #
# evaluate_trial — error surface
# --------------------------------------------------------------------------- #
def _upload_json_gt(client, api_url, headers, project_id, docs):
    content = json.dumps(docs).encode()
    return client.post(
        f"{api_url}/project/{project_id}/groundtruth",
        headers=headers,
        files={"file": ("gt.json", io.BytesIO(content), "application/json")},
        data={"format": "json"},
    )


def test_evaluate_trial_error_surface(client, api_url, admin_headers, monkeypatch):
    """Evaluating a completed trial with no field mappings returns the structured
    400 (errors + actionable suggestions), and a ground truth id from another
    project is a 404 rather than leaking across the tenant boundary."""
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"field1": "x"}),
    )
    headers = admin_headers
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "EvalSurface"}
    ).json()["id"]
    schema_id = _mk_schema(client, api_url, headers, project_id)
    prompt_id = _mk_prompt(client, api_url, headers, project_id)
    doc_ids = _seed_docs(client, api_url, headers, project_id, ["ev.txt"])
    trial_id = _mk_trial(
        client, api_url, headers, project_id, schema_id, prompt_id, doc_ids
    )["id"]

    gt = _upload_json_gt(
        client, api_url, headers, project_id, [{"id": "ev.txt", "field1": "x"}]
    )
    assert gt.status_code == 200, gt.text
    gt_id = gt.json()["id"]

    # No field mappings configured -> structured validation 400 with suggestions.
    resp = client.post(
        f"{api_url}/project/{project_id}/trial/{trial_id}/evaluate",
        headers=headers,
        params={"groundtruth_id": gt_id},
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert "errors" in detail and detail["errors"]
    assert any("field mappings" in e.lower() for e in detail["errors"])
    assert detail["suggestions"]  # actionable, non-empty

    # A ground truth id belonging to a different project -> 404.
    other_project = client.post(
        f"{api_url}/project", headers=headers, json={"name": "EvalOther"}
    ).json()["id"]
    other_gt = _upload_json_gt(
        client, api_url, headers, other_project, [{"id": "ev.txt", "field1": "x"}]
    )
    assert other_gt.status_code == 200, other_gt.text
    resp = client.post(
        f"{api_url}/project/{project_id}/trial/{trial_id}/evaluate",
        headers=headers,
        params={"groundtruth_id": other_gt.json()["id"]},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "trials.groundtruth_not_found"

    client.delete(f"{api_url}/project/{project_id}", headers=headers)
    client.delete(f"{api_url}/project/{other_project}", headers=headers)
