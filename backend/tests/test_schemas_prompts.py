# backend/tests/test_schemas_prompts.py
"""Tests for Schema + Prompt CRUD and schema-deletion guards.

Covers:
- prompt CRUD (create/list/get/update/delete, plus the now-allowed
  missing-{document_content} case that the backend auto-appends),
- schema create/get/delete (round-tripping schema_name + schema_definition),
- and the two deletion guards: a schema with field mappings deletes cleanly
  (mappings go, the ground truth survives — regression on the NOT NULL FK),
  while a schema referenced by a trial is blocked with a 400
  ("schemas.referenced_by_trial").
"""

import uuid


def test_prompt_crud(client, api_url, user_headers, make_project):
    headers = user_headers
    project_id = make_project(headers, name="Prompt Test")["id"]

    # Create prompt
    prompt_data = {
        "name": "Prompt CRUD",
        "system_prompt": "Extract info: {document_content}",
        "user_prompt": "User: Please extract patient data from {document_content}.",
        "project_id": project_id,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/prompt", headers=headers, json=prompt_data
    )
    assert response.status_code == 200
    prompt = response.json()
    prompt_id = prompt["id"]
    assert prompt["name"] == prompt_data["name"]

    # List prompts
    response = client.get(f"{api_url}/project/{project_id}/prompt", headers=headers)
    assert response.status_code == 200
    assert any(p["id"] == prompt_id for p in response.json())

    # Get prompt
    response = client.get(
        f"{api_url}/project/{project_id}/prompt/{prompt_id}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["id"] == prompt_id

    # Update prompt
    update_data = {"name": "Prompt CRUD Updated"}
    response = client.put(
        f"{api_url}/project/{project_id}/prompt/{prompt_id}",
        headers=headers,
        json=update_data,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Prompt CRUD Updated"

    # Delete prompt
    response = client.delete(
        f"{api_url}/project/{project_id}/prompt/{prompt_id}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["id"] == prompt_id

    # Get deleted prompt (should 404)
    response = client.get(
        f"{api_url}/project/{project_id}/prompt/{prompt_id}", headers=headers
    )
    assert response.status_code == 404

    # Prompt creation: missing {document_content} is now allowed
    # Document content is auto-appended by the backend if placeholder is missing
    no_placeholder_prompt = {
        "name": "No Placeholder",
        "system_prompt": "No placeholder here.",
        "user_prompt": "Nope.",
        "project_id": project_id,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/prompt",
        headers=headers,
        json=no_placeholder_prompt,
    )
    assert response.status_code == 200


# Test Create Schema
def test_create_schema(client, api_url, user_headers, make_project):
    headers = user_headers
    project_id = make_project(
        headers, name="Test Project", description="This is a test project"
    )["id"]

    # Create a schema
    schema_data = {
        "schema_name": "Test Schema",
        "schema_definition": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "string"},
            },
        },
    }
    response = client.post(
        f"{api_url}/project/{project_id}/schema", headers=headers, json=schema_data
    )
    assert response.status_code == 200
    schema = response.json()
    assert schema["schema_name"] == schema_data["schema_name"]
    assert schema["schema_definition"] == schema_data["schema_definition"]


# Test Get Schema
def test_get_schema(client, api_url, user_headers, make_project):
    headers = user_headers
    project_id = make_project(
        headers, name="Test Project", description="This is a test project"
    )["id"]

    # Create a schema
    schema_data = {
        "schema_name": "Test Schema",
        "schema_definition": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "string"},
            },
        },
    }
    response = client.post(
        f"{api_url}/project/{project_id}/schema", headers=headers, json=schema_data
    )
    assert response.status_code == 200
    schema_id = response.json()["id"]

    # Get the schema
    response = client.get(
        f"{api_url}/project/{project_id}/schema/{schema_id}", headers=headers
    )
    assert response.status_code == 200
    schema = response.json()
    assert schema["schema_name"] == schema_data["schema_name"]
    assert schema["schema_definition"] == schema_data["schema_definition"]


# Test Delete Schema
def test_delete_schema(client, api_url, user_headers, make_project, make_schema):
    headers = user_headers
    project_id = make_project(
        headers, name="Test Project", description="This is a test project"
    )["id"]

    schema_id = make_schema(headers, project_id)["id"]

    # Delete the schema
    response = client.delete(
        f"{api_url}/project/{project_id}/schema/{schema_id}", headers=headers
    )
    assert response.status_code == 200

    # Try to get the deleted schema
    response = client.get(
        f"{api_url}/project/{project_id}/schema/{schema_id}", headers=headers
    )
    assert response.status_code == 404


def test_delete_schema_with_field_mappings(client, api_url, user_headers, make_project):
    """Deleting a schema that has field mappings (but no trials) must succeed
    and take the mappings with it — previously the NOT NULL FK on
    field_mappings.schema_id made this a 500 (regression)."""
    from backend.src import models
    from backend.src.db.session import SessionLocal

    headers = user_headers
    project_id = make_project(headers, name="Mapping Delete Project")["id"]

    schema_data = {
        "schema_name": "Mapped Schema",
        "schema_definition": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        },
    }
    response = client.post(
        f"{api_url}/project/{project_id}/schema", headers=headers, json=schema_data
    )
    assert response.status_code == 200
    schema_id = response.json()["id"]

    # Seed a ground truth + field mapping directly (the API path needs a real
    # ground-truth file upload, which is irrelevant to this regression).
    db = SessionLocal()
    try:
        gt = models.GroundTruth(
            project_id=project_id,
            name="GT for mapping",
            format="csv",
            file_uuid=str(uuid.uuid4()),
        )
        db.add(gt)
        db.flush()
        db.add(
            models.FieldMapping(
                ground_truth_id=gt.id,
                schema_id=schema_id,
                schema_field="name",
                ground_truth_field="name",
            )
        )
        db.commit()
        gt_id = gt.id
    finally:
        db.close()

    response = client.delete(
        f"{api_url}/project/{project_id}/schema/{schema_id}", headers=headers
    )
    assert response.status_code == 200, response.text

    db = SessionLocal()
    try:
        remaining = (
            db.query(models.FieldMapping)
            .filter(models.FieldMapping.schema_id == schema_id)
            .count()
        )
        assert remaining == 0
        # The ground truth itself must survive — only the mappings go.
        assert db.get(models.GroundTruth, gt_id) is not None
    finally:
        db.close()


def test_update_schema(client, api_url, user_headers, make_project, make_schema):
    """PUT /schema/{id} updates name + definition and round-trips."""
    headers = user_headers
    project_id = make_project(headers, name="Schema Update Project")["id"]
    schema_id = make_schema(headers, project_id)["id"]

    new_def = {
        "type": "object",
        "properties": {"diagnosis": {"type": "string"}},
    }
    response = client.put(
        f"{api_url}/project/{project_id}/schema/{schema_id}",
        headers=headers,
        json={"schema_name": "Renamed Schema", "schema_definition": new_def},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_name"] == "Renamed Schema"
    assert body["schema_definition"] == new_def

    # Persisted
    response = client.get(
        f"{api_url}/project/{project_id}/schema/{schema_id}", headers=headers
    )
    assert response.json()["schema_name"] == "Renamed Schema"


def test_update_schema_not_found(client, api_url, user_headers, make_project):
    headers = user_headers
    project_id = make_project(headers, name="Schema Update 404")["id"]
    response = client.put(
        f"{api_url}/project/{project_id}/schema/999999",
        headers=headers,
        json={
            "schema_name": "x",
            "schema_definition": {"type": "object", "properties": {}},
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "schemas.not_found"


def test_schema_field_types_endpoint(
    client, api_url, user_headers, make_project, make_schema
):
    """GET /schema/{id}/field_types flattens nested objects, arrays, enums, and
    date-formatted fields into dot-notation leaf paths."""
    headers = user_headers
    project_id = make_project(headers, name="Field Types Project")["id"]
    definition = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "status": {"type": "string", "enum": ["a", "b"]},
            "collected_on": {"type": "string", "format": "date"},
            "patient": {
                "type": "object",
                "properties": {"mrn": {"type": "string"}},
            },
            "tags": {"type": "array", "items": {"type": "string"}},
            "labs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"value": {"type": "number"}},
                },
            },
        },
    }
    schema_id = make_schema(headers, project_id, definition=definition)["id"]

    response = client.get(
        f"{api_url}/project/{project_id}/schema/{schema_id}/field_types",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    types = response.json()
    assert types["name"] == "string"
    assert types["status"] == "category"  # enum -> category
    assert types["collected_on"] == "date"  # format override
    assert types["patient.mrn"] == "string"  # nested object flattened
    assert types["tags[]"] == "string"  # array of primitive
    assert types["labs[].value"] == "number"  # array of objects flattened


def test_schema_access_control(
    client, api_url, user_headers, login, make_project, make_schema
):
    """A different (non-admin) user cannot read/update/delete another user's schema."""
    owner_headers = user_headers
    project_id = make_project(owner_headers, name="Owned Schema Project")["id"]
    schema_id = make_schema(owner_headers, project_id)["id"]

    other_headers = login("another@example.com", "Anotherpassword1")

    # Read list
    resp = client.get(f"{api_url}/project/{project_id}/schema", headers=other_headers)
    assert resp.status_code == 403
    # Read one
    resp = client.get(
        f"{api_url}/project/{project_id}/schema/{schema_id}", headers=other_headers
    )
    assert resp.status_code == 403
    # Update
    resp = client.put(
        f"{api_url}/project/{project_id}/schema/{schema_id}",
        headers=other_headers,
        json={
            "schema_name": "hijack",
            "schema_definition": {"type": "object", "properties": {}},
        },
    )
    assert resp.status_code == 403
    # Delete
    resp = client.delete(
        f"{api_url}/project/{project_id}/schema/{schema_id}", headers=other_headers
    )
    assert resp.status_code == 403


def test_schema_project_not_found(client, api_url, user_headers):
    headers = user_headers
    resp = client.get(f"{api_url}/project/999999/schema", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "schemas.project_not_found"


# Test Delete Schema Referenced by Trial
def test_delete_schema_referenced_by_trial(
    client, api_url, admin_headers, make_project, monkeypatch
):
    from .fake_llm import make_fake_openai

    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai({"name": "Ada", "location": "Berlin"}),
    )
    headers = admin_headers

    # 1. Create a project
    project_id = make_project(
        headers, name="Test Project", description="This is a test project"
    )["id"]

    # 2. Upload a text file and preprocess it to create a document
    file_data = {
        "file": ("test.txt", b"Hello World!", "text/plain"),
        "file_info": (
            "",
            '{"file_name": "test.txt", "file_type": "text/plain"}',
            "application/json",
        ),
    }
    response = client.post(
        f"{api_url}/project/{project_id}/file", headers=headers, files=file_data
    )
    assert response.status_code == 200
    file_id = response.json()["id"]

    # Preprocess with inline config
    preprocessing_data = {
        "file_ids": [file_id],
        "inline_config": {
            "name": "Simple Text Config",
            "description": "For test document creation",
        },
        "bypass_celery": True,
    }
    response = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json=preprocessing_data,
    )
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "completed"

    # Get the created document
    response = client.get(f"{api_url}/project/{project_id}/document", headers=headers)
    assert response.status_code == 200
    documents = response.json()
    assert len(documents) > 0
    document_id = documents["items"][0]["id"]

    # 3. Create a prompt with {document_content} in user_prompt
    prompt_data = {
        "name": "Test Prompt",
        "project_id": project_id,
        "description": "Prompt for schema-trial test",
        "system_prompt": "System context.",
        "user_prompt": "Extract name and location from the document: {document_content}",
    }
    response = client.post(
        f"{api_url}/project/{project_id}/prompt", headers=headers, json=prompt_data
    )
    assert response.status_code == 200
    prompt_id = response.json()["id"]

    # 4. Create a schema
    schema_data = {
        "schema_name": "Test Schema",
        "schema_definition": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "string"},
            },
        },
    }
    response = client.post(
        f"{api_url}/project/{project_id}/schema", headers=headers, json=schema_data
    )
    assert response.status_code == 200
    schema_id = response.json()["id"]

    # 5. Create a trial referencing schema, prompt, and document
    trial_data = {
        "schema_id": schema_id,
        "prompt_id": prompt_id,
        "document_ids": [document_id],
        "bypass_celery": True,
        "llm_model": "mock-model",
        "api_key": "test-key",
        "base_url": "http://localhost:11434/v1",
    }
    response = client.post(
        f"{api_url}/project/{project_id}/trial", headers=headers, json=trial_data
    )
    assert response.status_code == 200

    # 6. Try to delete the schema (should fail)
    response = client.delete(
        f"{api_url}/project/{project_id}/schema/{schema_id}", headers=headers
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "schemas.referenced_by_trial"
