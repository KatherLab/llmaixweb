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

import json

from .fake_llm import make_fake_openai

# Creds spread into every trial-create body. base_url passes the SSRF +
# ALLOWED_LLM_ENDPOINTS checks in the test config; the client itself is mocked.
_LLM_CREDS = {
    "llm_model": "mock-model",
    "api_key": "test-key",
    "base_url": "http://localhost:11434/v1",
}


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
