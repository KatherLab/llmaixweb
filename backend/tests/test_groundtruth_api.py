"""API-level tests for backend/src/routers/v1/endpoints/groundtruth.py.

The happy-path mapping + auto-map + id-column + evaluate flow is already covered
by ``test_evaluation_pipeline.py::test_field_mapping_and_evaluation``. This module
deliberately targets the *other* endpoints and the edge/error cases:

- upload (CSV / XLSX / single-JSON / multiple-JSON) + upload validation errors
- list / get / update-name / delete (+ blob removal on delete)
- id-column set (valid + nonexistent-column behaviour)
- preview
- mapping/suggest, validate-json, mapping/status (empty), legacy POST /mapping
- mapping validation error (schema_field not a schema leaf)
- authz: another user's project -> 403/404; unauthenticated -> 401

All routes live under ``/api/v1/project/{project_id}``.
"""

import io
import json
import os

# Ground-truth columns present in reports_with_groundtruth.csv/.xlsx:
#   id, "shortness of breath", "chest pain", "leg pain or swelling",
#   "heart palpitations", "cough", "dizziness", location, side, report

# A small schema whose leaf paths ("cough", "location") exactly match GT columns.
_MAP_SCHEMA_DEF = {
    "type": "object",
    "properties": {
        "cough": {"type": "boolean"},
        "location": {"type": "string"},
    },
    "required": ["cough"],
}

# JSON ground truth (list-of-docs form; each needs an "id").
_JSON_GT = [
    {"id": "doc1.pdf", "cough": True, "location": "main"},
    {"id": "doc2.pdf", "cough": False, "location": "left", "extra": "x"},
]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _gt_url(api_url, project_id, suffix=""):
    return f"{api_url}/project/{project_id}/groundtruth{suffix}"


def _upload_csv(client, api_url, headers, project_id, files_base_path, name=None):
    with open(files_base_path / "reports_with_groundtruth.csv", "rb") as f:
        data = {"format": "csv"}
        if name is not None:
            data["name"] = name
        resp = client.post(
            _gt_url(api_url, project_id),
            headers=headers,
            files={"file": ("reports_with_groundtruth.csv", f, "text/csv")},
            data=data,
        )
    return resp


def _upload_json(client, api_url, headers, project_id, docs=None):
    content = json.dumps(_JSON_GT if docs is None else docs).encode()
    return client.post(
        _gt_url(api_url, project_id),
        headers=headers,
        files={"file": ("gt.json", io.BytesIO(content), "application/json")},
        data={"format": "json"},
    )


# --------------------------------------------------------------------------- #
# Upload: happy paths (CSV / XLSX / JSON / multiple JSON)
# --------------------------------------------------------------------------- #
def test_upload_csv(client, api_url, user_headers, make_project, files_base_path):
    project_id = make_project(user_headers)["id"]
    resp = _upload_csv(client, api_url, user_headers, project_id, files_base_path)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["format"] == "csv"
    # Name falls back to the uploaded filename when not supplied.
    assert body["name"] == "reports_with_groundtruth.csv"
    assert body["project_id"] == project_id
    assert body["file_uuid"]


def test_upload_xlsx(client, api_url, user_headers, make_project, files_base_path):
    project_id = make_project(user_headers)["id"]
    xlsx_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    with open(files_base_path / "reports_with_groundtruth.xlsx", "rb") as f:
        resp = client.post(
            _gt_url(api_url, project_id),
            headers=user_headers,
            files={"file": ("reports_with_groundtruth.xlsx", f, xlsx_type)},
            data={"format": "xlsx", "name": "my xlsx gt"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["format"] == "xlsx"
    assert body["name"] == "my xlsx gt"


def test_upload_json_single(client, api_url, user_headers, make_project):
    project_id = make_project(user_headers)["id"]
    resp = _upload_json(client, api_url, user_headers, project_id)
    assert resp.status_code == 200, resp.text
    assert resp.json()["format"] == "json"


def test_upload_multiple_json(client, api_url, user_headers, make_project):
    project_id = make_project(user_headers)["id"]
    files = [
        ("files", ("a.json", json.dumps({"id": "a"}).encode(), "application/json")),
        ("files", ("b.json", json.dumps({"id": "b"}).encode(), "application/json")),
    ]
    resp = client.post(
        _gt_url(api_url, project_id),
        headers=user_headers,
        files=files,
        data={"format": "json", "multiple_json": "true", "name": "bundle"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # multiple_json is zipped and stored internally as a ZIP archive.
    assert body["format"] == "zip"
    assert body["name"] == "bundle"


# --------------------------------------------------------------------------- #
# Upload: validation errors
# --------------------------------------------------------------------------- #
def test_upload_missing_file(client, api_url, user_headers, make_project):
    project_id = make_project(user_headers)["id"]
    resp = client.post(
        _gt_url(api_url, project_id),
        headers=user_headers,
        data={"format": "csv", "name": "x"},
    )
    assert resp.status_code == 400, resp.text
    assert "no file" in str(resp.json()["detail"]).lower()


def test_upload_bad_format(client, api_url, user_headers, make_project):
    project_id = make_project(user_headers)["id"]
    resp = client.post(
        _gt_url(api_url, project_id),
        headers=user_headers,
        files={"file": ("x.txt", b"hello", "text/plain")},
        data={"format": "txt"},
    )
    assert resp.status_code == 400, resp.text
    assert "format" in str(resp.json()["detail"]).lower()


def test_upload_multiple_json_invalid_json(client, api_url, user_headers, make_project):
    project_id = make_project(user_headers)["id"]
    files = [
        ("files", ("ok.json", json.dumps({"id": "a"}).encode(), "application/json")),
        ("files", ("bad.json", b"not-json{", "application/json")),
    ]
    resp = client.post(
        _gt_url(api_url, project_id),
        headers=user_headers,
        files=files,
        data={"format": "json", "multiple_json": "true", "name": "bundle"},
    )
    assert resp.status_code == 400, resp.text
    assert "not valid json" in str(resp.json()["detail"]).lower()


def test_upload_multiple_json_requires_name(
    client, api_url, user_headers, make_project
):
    """multiple_json has no single ``file`` to derive a name from -> name required."""
    project_id = make_project(user_headers)["id"]
    files = [
        ("files", ("a.json", json.dumps({"id": "a"}).encode(), "application/json")),
    ]
    resp = client.post(
        _gt_url(api_url, project_id),
        headers=user_headers,
        files=files,
        data={"format": "json", "multiple_json": "true"},
    )
    assert resp.status_code == 400, resp.text
    assert "name" in str(resp.json()["detail"]).lower()


# --------------------------------------------------------------------------- #
# List / get / update / delete
# --------------------------------------------------------------------------- #
def test_list_and_get(client, api_url, user_headers, make_project, files_base_path):
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]

    resp = client.get(_gt_url(api_url, project_id), headers=user_headers)
    assert resp.status_code == 200, resp.text
    listed = resp.json()
    assert isinstance(listed, list)
    assert any(g["id"] == gt_id for g in listed)

    resp = client.get(_gt_url(api_url, project_id, f"/{gt_id}"), headers=user_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == gt_id


def test_get_nonexistent(client, api_url, user_headers, make_project):
    project_id = make_project(user_headers)["id"]
    resp = client.get(_gt_url(api_url, project_id, "/999999"), headers=user_headers)
    assert resp.status_code == 404, resp.text


def test_update_name(client, api_url, user_headers, make_project, files_base_path):
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]

    resp = client.put(
        _gt_url(api_url, project_id, f"/{gt_id}"),
        headers=user_headers,
        data={"name": "renamed gt"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "renamed gt"

    # Persisted.
    resp = client.get(_gt_url(api_url, project_id, f"/{gt_id}"), headers=user_headers)
    assert resp.json()["name"] == "renamed gt"


def test_delete_removes_blob(
    client, api_url, user_headers, make_project, files_base_path
):
    project_id = make_project(user_headers)["id"]
    upload = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()
    gt_id = upload["id"]
    file_uuid = upload["file_uuid"]

    local_dir = os.environ.get("LOCAL_DIRECTORY")
    blob_path = os.path.join(local_dir, file_uuid) if local_dir else None
    if blob_path is not None:
        assert os.path.exists(blob_path), "blob should exist before delete"

    resp = client.delete(
        _gt_url(api_url, project_id, f"/{gt_id}"), headers=user_headers
    )
    assert resp.status_code == 200, resp.text

    # Row gone.
    resp = client.get(_gt_url(api_url, project_id, f"/{gt_id}"), headers=user_headers)
    assert resp.status_code == 404

    # Stored bytes cleaned up.
    if blob_path is not None:
        assert not os.path.exists(blob_path), "blob should be removed after delete"


# --------------------------------------------------------------------------- #
# id-column
# --------------------------------------------------------------------------- #
def test_id_column_valid(client, api_url, user_headers, make_project, files_base_path):
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]

    resp = client.put(
        _gt_url(api_url, project_id, f"/{gt_id}/id-column"),
        headers=user_headers,
        json={"id_column": "id"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["id_column_name"] == "id"


def test_id_column_nonexistent_deferred_validation(
    client, api_url, user_headers, make_project, files_base_path
):
    """Setting a nonexistent id-column is accepted (no validation at set time);
    the error is deferred until the file is parsed (preview -> 422)."""
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]

    # The endpoint does not validate the column against the file headers.
    resp = client.put(
        _gt_url(api_url, project_id, f"/{gt_id}/id-column"),
        headers=user_headers,
        json={"id_column": "column_that_does_not_exist"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["id_column_name"] == "column_that_does_not_exist"

    # Parsing now fails loudly because the column is missing.
    resp = client.get(
        _gt_url(api_url, project_id, f"/{gt_id}/preview"), headers=user_headers
    )
    assert resp.status_code == 422, resp.text


# --------------------------------------------------------------------------- #
# preview
# --------------------------------------------------------------------------- #
def test_preview_csv(client, api_url, user_headers, make_project, files_base_path):
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]
    client.put(
        _gt_url(api_url, project_id, f"/{gt_id}/id-column"),
        headers=user_headers,
        json={"id_column": "id"},
    )

    resp = client.get(
        _gt_url(api_url, project_id, f"/{gt_id}/preview"), headers=user_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(["fields", "field_types", "preview_data", "available_columns"]).issubset(
        body.keys()
    )
    # Column headers surface in available_columns for CSV.
    assert "cough" in body["available_columns"]
    assert body["current_id_column"] == "id"
    # Parsed field paths exclude the id column and include the real fields.
    assert "cough" in body["fields"]


# --------------------------------------------------------------------------- #
# mapping/suggest, validate-json, mapping/status, legacy mapping,
# mapping validation error
# --------------------------------------------------------------------------- #
def test_mapping_status_empty(
    client, api_url, user_headers, make_project, make_schema, files_base_path
):
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]
    schema_id = make_schema(user_headers, project_id, definition=_MAP_SCHEMA_DEF)["id"]

    resp = client.get(
        _gt_url(api_url, project_id, f"/{gt_id}/schema/{schema_id}/mapping/status"),
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_mappings"] is False
    assert body["mapping_count"] == 0
    assert body["schema_field_count"] == 2  # cough + location
    assert body["mapping_complete"] is False


def test_mapping_suggest_csv(
    client, api_url, user_headers, make_project, make_schema, files_base_path
):
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]
    client.put(
        _gt_url(api_url, project_id, f"/{gt_id}/id-column"),
        headers=user_headers,
        json={"id_column": "id"},
    )
    schema_id = make_schema(user_headers, project_id, definition=_MAP_SCHEMA_DEF)["id"]

    resp = client.get(
        _gt_url(api_url, project_id, f"/{gt_id}/schema/{schema_id}/mapping/suggest"),
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text
    suggestions = resp.json()
    assert isinstance(suggestions, list)
    mapped = {s["schema_field"]: s["ground_truth_field"] for s in suggestions}
    # "cough" and "location" are exact column matches.
    assert mapped.get("cough") == "cough"
    assert mapped.get("location") == "location"


def test_validate_json_on_csv_is_noop(
    client, api_url, user_headers, make_project, make_schema, files_base_path
):
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]
    schema_id = make_schema(user_headers, project_id, definition=_MAP_SCHEMA_DEF)["id"]

    resp = client.post(
        _gt_url(api_url, project_id, f"/{gt_id}/schema/{schema_id}/validate-json"),
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["errors"] == []
    # For non-JSON formats validation is skipped with a warning.
    assert any("json" in w.lower() for w in body["warnings"])


def test_validate_json_on_json(
    client, api_url, user_headers, make_project, make_schema
):
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_json(client, api_url, user_headers, project_id).json()["id"]
    schema_id = make_schema(user_headers, project_id, definition=_MAP_SCHEMA_DEF)["id"]

    resp = client.post(
        _gt_url(api_url, project_id, f"/{gt_id}/schema/{schema_id}/validate-json"),
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "errors" in body and "warnings" in body
    # Docs satisfy the required "cough" field -> no missing-field errors.
    assert body["errors"] == []
    # doc2 has an "extra" field not in the schema -> reported as a warning.
    assert any("extra" in w.lower() for w in body["warnings"])


def test_legacy_mapping_post(
    client, api_url, user_headers, make_project, make_schema, files_base_path
):
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]
    schema_id = make_schema(user_headers, project_id, definition=_MAP_SCHEMA_DEF)["id"]

    mappings = [
        {
            "schema_field": "cough",
            "ground_truth_field": "cough",
            "schema_id": schema_id,
            "field_type": "boolean",
        }
    ]
    resp = client.post(
        _gt_url(api_url, project_id, f"/{gt_id}/mapping"),
        headers=user_headers,
        json=mappings,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == gt_id

    # Legacy endpoint is not schema-scoped, but the mapping still shows up under
    # the schema it was created for.
    resp = client.get(
        _gt_url(api_url, project_id, f"/{gt_id}/schema/{schema_id}/mapping"),
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1


def test_mapping_invalid_schema_field(
    client, api_url, user_headers, make_project, make_schema, files_base_path
):
    """A mapping whose schema_field is not a schema leaf path -> 422."""
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]
    schema_id = make_schema(user_headers, project_id, definition=_MAP_SCHEMA_DEF)["id"]

    mappings = [
        {
            "schema_field": "not_a_real_field",
            "ground_truth_field": "cough",
            "schema_id": schema_id,
            "field_type": "string",
        }
    ]
    resp = client.post(
        _gt_url(api_url, project_id, f"/{gt_id}/schema/{schema_id}/mapping"),
        headers=user_headers,
        json=mappings,
    )
    assert resp.status_code == 422, resp.text
    assert "not_a_real_field" in str(resp.json()["detail"])


def test_configure_mapping_forces_path_schema_id(
    client, api_url, user_headers, make_project, make_schema, files_base_path
):
    """The PATH schema_id is authoritative: a mismatched body schema_id must NOT
    redirect the written rows to a different schema (regression — rows used to be
    stored under the body value, leaving the path schema with none)."""
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]
    schema_a = make_schema(
        user_headers, project_id, name="A", definition=_MAP_SCHEMA_DEF
    )["id"]
    schema_b = make_schema(
        user_headers, project_id, name="B", definition=_MAP_SCHEMA_DEF
    )["id"]

    # POST to schema A's path, but with body schema_id pointing at B.
    mappings = [
        {
            "schema_field": "cough",
            "ground_truth_field": "cough",
            "schema_id": schema_b,  # mismatched on purpose
            "field_type": "boolean",
        }
    ]
    resp = client.post(
        _gt_url(api_url, project_id, f"/{gt_id}/schema/{schema_a}/mapping"),
        headers=user_headers,
        json=mappings,
    )
    assert resp.status_code == 200, resp.text

    # The mapping must live under schema A (the path), not B (the body).
    under_a = client.get(
        _gt_url(api_url, project_id, f"/{gt_id}/schema/{schema_a}/mapping"),
        headers=user_headers,
    ).json()
    under_b = client.get(
        _gt_url(api_url, project_id, f"/{gt_id}/schema/{schema_b}/mapping"),
        headers=user_headers,
    ).json()
    assert len(under_a) == 1
    assert under_a[0]["schema_id"] == schema_a
    assert len(under_b) == 0


def test_legacy_mapping_rejects_foreign_project_schema(
    client, api_url, user_headers, login, make_project, make_schema, files_base_path
):
    """The legacy (body-schema_id) endpoint must reject a schema_id that belongs
    to another project, so it can't write mapping rows referencing it."""
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]

    # A schema in a DIFFERENT project (owned by another user).
    other = login("another@example.com", "Anotherpassword1")
    other_project = make_project(other, name="Other")["id"]
    foreign_schema = make_schema(other, other_project, definition=_MAP_SCHEMA_DEF)["id"]

    mappings = [
        {
            "schema_field": "cough",
            "ground_truth_field": "cough",
            "schema_id": foreign_schema,
            "field_type": "boolean",
        }
    ]
    resp = client.post(
        _gt_url(api_url, project_id, f"/{gt_id}/mapping"),
        headers=user_headers,
        json=mappings,
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "groundtruth.schema_not_found"


def test_multiple_json_duplicate_filenames_both_survive(
    client, api_url, user_headers, make_project
):
    """Two id-less JSON files sharing a filename must both be preserved: the ZIP
    arcname is de-duplicated so neither is silently dropped (parser keys id-less
    docs by filename stem)."""
    project_id = make_project(user_headers)["id"]
    files = [
        (
            "files",
            (
                "dup.json",
                json.dumps({"cough": True, "location": "a"}).encode(),
                "application/json",
            ),
        ),
        (
            "files",
            (
                "dup.json",
                json.dumps({"cough": False, "location": "b"}).encode(),
                "application/json",
            ),
        ),
    ]
    resp = client.post(
        _gt_url(api_url, project_id),
        headers=user_headers,
        files=files,
        data={"format": "json", "multiple_json": "true", "name": "dupbundle"},
    )
    assert resp.status_code == 200, resp.text
    gt_id = resp.json()["id"]

    preview = client.get(
        _gt_url(api_url, project_id, f"/{gt_id}/preview"), headers=user_headers
    )
    assert preview.status_code == 200, preview.text
    # Both documents parsed (not collapsed to one by an arcname collision).
    assert len(preview.json()["preview_data"]) == 2


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #
def test_other_user_forbidden(
    client, api_url, user_headers, login, make_project, files_base_path
):
    project_id = make_project(user_headers)["id"]
    gt_id = _upload_csv(
        client, api_url, user_headers, project_id, files_base_path
    ).json()["id"]

    other = login("another@example.com", "Anotherpassword1")

    # List, get, and upload should all be refused for a non-member.
    resp = client.get(_gt_url(api_url, project_id), headers=other)
    assert resp.status_code in (403, 404), resp.text

    resp = client.get(_gt_url(api_url, project_id, f"/{gt_id}"), headers=other)
    assert resp.status_code in (403, 404), resp.text

    resp = client.delete(_gt_url(api_url, project_id, f"/{gt_id}"), headers=other)
    assert resp.status_code in (403, 404), resp.text


def test_unauthenticated(client, api_url, user_headers, make_project):
    project_id = make_project(user_headers)["id"]
    resp = client.get(_gt_url(api_url, project_id))
    assert resp.status_code == 401, resp.text


def test_project_not_found(client, api_url, user_headers):
    resp = client.get(_gt_url(api_url, 987654321), headers=user_headers)
    assert resp.status_code == 404, resp.text
