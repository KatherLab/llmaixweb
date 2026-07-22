# backend/tests/test_files.py
"""Tests for the basic per-file CRUD endpoints under a project's /file route.

Covers listing an empty project's files, uploading a file (disk PDF and inline
bytes), fetching a single file's metadata, deleting a file, and downloading a
file's raw content. Complements the batch-ops suite in
``test_file_batch_ops.py`` (batch-delete / move), which exercises the bulk
paths.

Additionally exercises the spreadsheet-oriented endpoints (``/preview-rows``,
``/validate-id-column``, ``/configure``), the ``/stats`` aggregation, the
single-file delete safety checks (active preprocessing task, linked documents,
orphaned-preprocessed-file reclaim), and the ``/move`` access/validation guards.
"""

import io
import os
import uuid
import zipfile


# Test Get Project Files
def test_get_project_files(client, api_url, user_headers, make_project):
    project_id = make_project(user_headers)["id"]
    response = client.get(f"{api_url}/project/{project_id}/file", headers=user_headers)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["total"] == 0  # No files uploaded yet
    assert response_data["items"] == []


# Test Upload File
def test_upload_file(
    client, api_url, files_base_path, user_headers, make_project, upload_file
):
    project_id = make_project(user_headers)["id"]
    response_json = upload_file(
        user_headers,
        project_id,
        path=files_base_path / "9874562_text.pdf",
        content_type="application/pdf",
    )
    assert "id" in response_json
    assert "file_name" in response_json
    assert "file_type" in response_json
    assert response_json["file_name"] == "9874562_text.pdf"
    assert response_json["file_type"] == "application/pdf"


# Test Get Project File
def test_get_project_file(client, api_url, user_headers, make_project, upload_file):
    project_id = make_project(user_headers)["id"]
    file_id = upload_file(
        user_headers, project_id, content=b"Hello World!", name="test.txt"
    )["id"]
    response = client.get(
        f"{api_url}/project/{project_id}/file/{file_id}", headers=user_headers
    )
    assert response.status_code == 200
    assert response.json()["file_name"] == "test.txt"


# Test Delete File
def test_delete_file(client, api_url, user_headers, make_project, upload_file):
    project_id = make_project(user_headers)["id"]
    file_id = upload_file(
        user_headers, project_id, content=b"Hello World!", name="test.txt"
    )["id"]
    response = client.delete(
        f"{api_url}/project/{project_id}/file/{file_id}", headers=user_headers
    )
    assert response.status_code == 200
    assert response.json()["file_name"] == "test.txt"


# Test Get Project File Content
def test_get_project_file_content(
    client, api_url, user_headers, make_project, upload_file
):
    project_id = make_project(user_headers)["id"]
    file_id = upload_file(
        user_headers, project_id, content=b"Hello KatherLab!", name="test.txt"
    )["id"]
    response = client.get(
        f"{api_url}/project/{project_id}/file/{file_id}/content", headers=user_headers
    )
    assert response.status_code == 200
    assert response.content == b"Hello KatherLab!"


# ---------------------------------------------------------------------------
# Local-DB helpers for seeding ORM rows the API can't create directly.
# ---------------------------------------------------------------------------


def _session():
    from ..src.db.session import SessionLocal

    return SessionLocal()


def _file_row(file_id: int):
    from ..src import models

    db = _session()
    try:
        return db.get(models.File, file_id)
    finally:
        db.close()


def _blob_path(file_uuid: str) -> str:
    return os.path.join(os.environ["LOCAL_DIRECTORY"], file_uuid)


def _add_config_and_document(
    project_id: int, file_id: int, *, preprocessed_file_id=None, config_name="cfg"
):
    """Attach a preprocessing config + one document to an existing file."""
    from ..src import models

    db = _session()
    try:
        config = models.PreprocessingConfiguration(
            project_id=project_id, name=config_name, additional_settings={}
        )
        db.add(config)
        db.flush()
        doc = models.Document(
            project_id=project_id,
            original_file_id=file_id,
            preprocessed_file_id=preprocessed_file_id,
            preprocessing_config_id=config.id,
            text="doc text",
            document_name=f"doc-{file_id}-{uuid.uuid4().hex[:6]}",
            is_latest=True,
        )
        db.add(doc)
        db.commit()
        return config.id, doc.id
    finally:
        db.close()


def _seed_active_preprocessing_task(project_id: int, file_id: int, status):
    """Create a PreprocessingTask + one FilePreprocessingTask in the given status."""
    from ..src import models

    db = _session()
    try:
        task = models.PreprocessingTask(
            project_id=project_id,
            status=models.PreprocessingStatus.IN_PROGRESS,
            total_files=1,
        )
        db.add(task)
        db.flush()
        ft = models.FilePreprocessingTask(
            preprocessing_task_id=task.id,
            file_id=file_id,
            status=status,
        )
        db.add(ft)
        db.commit()
        return task.id, ft.id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /{file_id}/preview-rows
# ---------------------------------------------------------------------------


def _preview(client, api_url, headers, project_id, file_id, **params):
    return client.get(
        f"{api_url}/project/{project_id}/file/{file_id}/preview-rows",
        headers=headers,
        params=params,
    )


def test_preview_rows_legacy_xls_unsupported(
    client, api_url, user_headers, make_project, upload_file
):
    """A file named .xls is rejected for preview with a clean 400."""
    project_id = make_project(user_headers)["id"]
    # Filename ending in .xls short-circuits to the "xls" branch regardless of
    # content, so any bytes work here.
    f = upload_file(
        user_headers,
        project_id,
        content=b"a,b\n1,2\n",
        name="legacy.xls",
        content_type="application/vnd.ms-excel",
    )
    resp = _preview(client, api_url, user_headers, project_id, f["id"])
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "files.xls_preview_unsupported"


def test_preview_rows_xlsx_name_but_csv_bytes_falls_back_to_csv(
    client, api_url, user_headers, make_project, upload_file
):
    """A .xlsx name whose bytes are actually CSV (not a ZIP) parses as CSV."""
    project_id = make_project(user_headers)["id"]
    f = upload_file(
        user_headers,
        project_id,
        content=b"name,city\nAlice,Berlin\nBob,Paris\n",
        name="mislabeled.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp = _preview(client, api_url, user_headers, project_id, f["id"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["headers"] == ["name", "city"]
    assert body["rows"][0] == ["Alice", "Berlin"]


def test_preview_rows_corrupt_real_zip_xlsx_returns_error_id(
    client, api_url, user_headers, make_project, upload_file
):
    """Real ZIP magic bytes but not a workbook -> 400 with an error id."""
    project_id = make_project(user_headers)["id"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("hello.txt", "not an excel workbook")
    corrupt = buf.getvalue()
    assert corrupt[:4] == b"PK\x03\x04"
    f = upload_file(
        user_headers,
        project_id,
        content=corrupt,
        name="corrupt.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp = _preview(client, api_url, user_headers, project_id, f["id"])
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "files.xlsx_unreadable"
    assert detail["params"]["error_id"]


def test_preview_rows_headerless_width_fallback_headers(
    client, api_url, files_base_path, user_headers, make_project, upload_file
):
    """has_header=false synthesizes Column N headers from the row width."""
    project_id = make_project(user_headers)["id"]
    f = upload_file(
        user_headers,
        project_id,
        path=files_base_path / "csv_150.csv",
        content_type="text/csv",
    )
    resp = _preview(
        client, api_url, user_headers, project_id, f["id"], has_header=False
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # csv_150.csv has two columns (id,text).
    assert body["headers"] == ["Column 1", "Column 2"]
    # First (would-be header) row is now a data row.
    assert body["rows"][0] == ["id", "text"]


def test_preview_rows_bad_sheet_falls_back_to_first(
    client, api_url, files_base_path, user_headers, make_project, upload_file
):
    """An unknown sheet name silently falls back to the first sheet."""
    project_id = make_project(user_headers)["id"]
    f = upload_file(
        user_headers,
        project_id,
        path=files_base_path / "reports_with_groundtruth.xlsx",
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    resp = _preview(
        client,
        api_url,
        user_headers,
        project_id,
        f["id"],
        sheet="ThisSheetDoesNotExist",
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "sheets" in body
    assert body["headers"][0] == "id"


# ---------------------------------------------------------------------------
# POST /{file_id}/validate-id-column
# ---------------------------------------------------------------------------


def test_validate_id_column_duplicates(
    client, api_url, user_headers, make_project, upload_file
):
    project_id = make_project(user_headers)["id"]
    f = upload_file(
        user_headers,
        project_id,
        content=b"id,text\n1,a\n1,b\n2,c\n",
        name="dups.csv",
        content_type="text/csv",
    )
    resp = client.post(
        f"{api_url}/project/{project_id}/file/{f['id']}/validate-id-column",
        headers=user_headers,
        json={"case_id_column": "id"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_valid"] is False
    assert body["column_exists"] is True
    dup_values = {d["value"] for d in body["duplicates"]}
    assert "1" in dup_values


def test_validate_id_column_empty_values(
    client, api_url, user_headers, make_project, upload_file
):
    project_id = make_project(user_headers)["id"]
    f = upload_file(
        user_headers,
        project_id,
        content=b"id,text\nA,x\n,y\nB,z\n",
        name="empties.csv",
        content_type="text/csv",
    )
    resp = client.post(
        f"{api_url}/project/{project_id}/file/{f['id']}/validate-id-column",
        headers=user_headers,
        json={"case_id_column": "id"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_valid"] is False
    assert any(d.get("is_empty") for d in body["duplicates"])


def test_validate_id_column_missing_column(
    client, api_url, user_headers, make_project, upload_file
):
    project_id = make_project(user_headers)["id"]
    f = upload_file(
        user_headers,
        project_id,
        content=b"id,text\n1,a\n2,b\n",
        name="ok.csv",
        content_type="text/csv",
    )
    resp = client.post(
        f"{api_url}/project/{project_id}/file/{f['id']}/validate-id-column",
        headers=user_headers,
        json={"case_id_column": "nope"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_valid"] is False
    assert body["column_exists"] is False


# ---------------------------------------------------------------------------
# POST /{file_id}/configure
# ---------------------------------------------------------------------------


def test_configure_row_by_row_rejects_non_unique_case_id(
    client, api_url, user_headers, make_project, upload_file
):
    project_id = make_project(user_headers)["id"]
    f = upload_file(
        user_headers,
        project_id,
        content=b"id,text\n1,a\n1,b\n",
        name="dup-config.csv",
        content_type="text/csv",
    )
    resp = client.post(
        f"{api_url}/project/{project_id}/file/{f['id']}/configure",
        headers=user_headers,
        json={
            "preprocessing_strategy": "row_by_row",
            "file_metadata": {"case_id_column": "id", "text_columns": ["text"]},
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["is_valid"] is False


def test_configure_row_by_row_rejects_missing_case_id_column(
    client, api_url, user_headers, make_project, upload_file
):
    project_id = make_project(user_headers)["id"]
    f = upload_file(
        user_headers,
        project_id,
        content=b"id,text\n1,a\n2,b\n",
        name="missing-config.csv",
        content_type="text/csv",
    )
    resp = client.post(
        f"{api_url}/project/{project_id}/file/{f['id']}/configure",
        headers=user_headers,
        json={
            "preprocessing_strategy": "row_by_row",
            "file_metadata": {"case_id_column": "does_not_exist"},
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["column_exists"] is False


def test_configure_row_by_row_accepts_unique_case_id(
    client, api_url, user_headers, make_project, upload_file
):
    project_id = make_project(user_headers)["id"]
    f = upload_file(
        user_headers,
        project_id,
        content=b"id,text\n1,a\n2,b\n3,c\n",
        name="unique-config.csv",
        content_type="text/csv",
    )
    resp = client.post(
        f"{api_url}/project/{project_id}/file/{f['id']}/configure",
        headers=user_headers,
        json={
            "preprocessing_strategy": "row_by_row",
            "file_metadata": {"case_id_column": "id", "text_columns": ["text"]},
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["preprocessing_strategy"] == "row_by_row"


# ---------------------------------------------------------------------------
# DELETE /{file_id} safety checks
# ---------------------------------------------------------------------------


def test_delete_blocked_by_active_preprocessing_task(
    client, api_url, user_headers, make_project, upload_file
):
    from ..src import models

    project_id = make_project(user_headers)["id"]
    f = upload_file(user_headers, project_id, content=b"x", name="busy.txt")
    _seed_active_preprocessing_task(
        project_id, f["id"], models.PreprocessingStatus.IN_PROGRESS
    )
    resp = client.delete(
        f"{api_url}/project/{project_id}/file/{f['id']}", headers=user_headers
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["links"]["active_preprocessing_tasks"] == 1
    # File must survive the refused delete.
    assert _file_row(f["id"]) is not None


def test_delete_blocked_by_linked_documents_without_force(
    client, api_url, user_headers, make_project, upload_file
):
    project_id = make_project(user_headers)["id"]
    f = upload_file(user_headers, project_id, content=b"x", name="linked.txt")
    _add_config_and_document(project_id, f["id"])
    resp = client.delete(
        f"{api_url}/project/{project_id}/file/{f['id']}", headers=user_headers
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["links"]["documents"] == 1
    assert _file_row(f["id"]) is not None


def test_force_delete_reclaims_orphaned_preprocessed_file(
    client, api_url, user_headers, make_project, upload_file
):
    """Force-deleting an original file also removes a now-orphaned, system-
    generated preprocessed File row and its storage blob."""
    from ..src import models
    from ..src.utils.enums import FileCreator

    project_id = make_project(user_headers)["id"]
    original = upload_file(user_headers, project_id, content=b"orig", name="orig.txt")

    # Seed a separate system-generated preprocessed file with a real blob.
    src_original = _file_row(original["id"])
    pre_uuid = uuid.uuid4().hex
    with open(_blob_path(pre_uuid), "wb") as fh:
        fh.write(b"preprocessed output")

    db = _session()
    try:
        pre = models.File(
            project_id=project_id,
            file_storage_type=src_original.file_storage_type,
            file_uuid=pre_uuid,
            file_name="orig.preprocessed.txt",
            file_type="text/plain",
            file_creator=FileCreator.system,
            file_size=19,
            file_hash="preprocessed-hash-" + pre_uuid,
        )
        db.add(pre)
        db.commit()
        pre_id = pre.id
    finally:
        db.close()

    # Document links original -> preprocessed; the preprocessed file is orphaned
    # once the document is cascade-deleted with the original.
    _add_config_and_document(project_id, original["id"], preprocessed_file_id=pre_id)

    assert os.path.exists(_blob_path(pre_uuid))

    resp = client.delete(
        f"{api_url}/project/{project_id}/file/{original['id']}?force=true",
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text

    assert _file_row(original["id"]) is None
    assert _file_row(pre_id) is None, "orphaned preprocessed File row was not reclaimed"
    assert not os.path.exists(_blob_path(pre_uuid)), (
        "orphaned preprocessed blob was not removed"
    )


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------


def test_file_stats_duplicates_and_creator_filter(
    client, api_url, user_headers, make_project, upload_file
):
    """`duplicates` = total - distinct(hash); the file_creator filter scopes all
    counts. A system file sharing a user file's hash is a duplicate overall but
    invisible under file_creator=user."""
    from ..src import models
    from ..src.utils.enums import FileCreator

    project_id = make_project(user_headers)["id"]
    user_file = upload_file(
        user_headers, project_id, content=b"shared-bytes", name="user.txt"
    )
    src = _file_row(user_file["id"])
    shared_hash = src.file_hash

    db = _session()
    try:
        sys_file = models.File(
            project_id=project_id,
            file_storage_type=src.file_storage_type,
            file_uuid=uuid.uuid4().hex,
            file_name="system.txt",
            file_type="text/plain",
            file_creator=FileCreator.system,
            file_size=src.file_size,
            file_hash=shared_hash,  # same hash -> a duplicate overall
        )
        db.add(sys_file)
        db.commit()
    finally:
        db.close()

    # No filter: two files, one distinct hash -> one duplicate.
    resp = client.get(
        f"{api_url}/project/{project_id}/file/stats", headers=user_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_files"] == 2
    assert body["unique_files"] == 1
    assert body["duplicates"] == 1

    # Scoped to user files: one file, no duplicate.
    resp = client.get(
        f"{api_url}/project/{project_id}/file/stats",
        headers=user_headers,
        params={"file_creator": "user"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_files"] == 1
    assert body["duplicates"] == 0

    # Scoped to system files: the seeded one.
    resp = client.get(
        f"{api_url}/project/{project_id}/file/stats",
        headers=user_headers,
        params={"file_creator": "system"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_files"] == 1


# ---------------------------------------------------------------------------
# POST /move access + audit
# ---------------------------------------------------------------------------


def test_move_forbidden_without_access_to_target(
    client, api_url, user_headers, make_project, upload_file
):
    """Moving into a project the caller can't write to -> 403."""
    project_id = make_project(user_headers)["id"]
    f = upload_file(user_headers, project_id, content=b"x", name="movable.txt")

    # A project owned by a different user (no shared access). `another@example.com`
    # is seeded by conftest.setup_test_environment.
    other_headers = {
        "Authorization": "Bearer "
        + client.post(
            f"{api_url}/auth/login",
            data={"username": "another@example.com", "password": "Anotherpassword1"},
        ).json()["access_token"]
    }
    other_project_id = make_project(other_headers, name="Other User Project")["id"]

    resp = client.post(
        f"{api_url}/project/{project_id}/file/move",
        headers=user_headers,
        json={"file_ids": [f["id"]], "target_project_id": other_project_id},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"]["code"] == "files.project_forbidden_action"
    # File stays put.
    assert _file_row(f["id"]).project_id == project_id


def test_move_writes_audit_row(
    client, api_url, user_headers, make_project, upload_file
):
    from ..src import models

    source_id = make_project(user_headers, name="Audit Move Source")["id"]
    target_id = make_project(user_headers, name="Audit Move Target")["id"]
    f = upload_file(user_headers, source_id, content=b"move-audit", name="ma.txt")

    resp = client.post(
        f"{api_url}/project/{source_id}/file/move",
        headers=user_headers,
        json={"file_ids": [f["id"]], "target_project_id": target_id},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["moved"] == 1

    db = _session()
    try:
        from sqlalchemy import select

        rows = (
            db.execute(
                select(models.AuditLog).where(
                    models.AuditLog.resource_type == "file",
                    models.AuditLog.project_id == source_id,
                )
            )
            .scalars()
            .all()
        )
        assert any((r.detail or {}).get("action") == "move" for r in rows), (
            "successful move did not write an audit row"
        )
    finally:
        db.close()
