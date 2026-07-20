# backend/tests/test_file_batch_ops.py
"""Tests for the batch file endpoints: POST /file/batch-delete and POST /file/move.

Both endpoints have data-loss history (sequential frontend deletes, half-moved
files), so this suite pins down:
- batch-delete: happy path (rows + storage blobs gone), the 200-file cap,
  per-file error isolation (linked file without force, missing file), and the
  force path removing dependent documents.
- move: documents follow their file, preprocessing configs are cloned into the
  target project (one clone per source config, shared across files), lineage to
  the source project is severed (source project delete can't cascade into moved
  documents), trial/document-set references block the move with a 409, and a
  mid-file failure rolls back only that file (SAVEPOINT) while invalidating the
  stale config-clone cache entries it created.
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select


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


def _make_project(client, api_url, headers, name: str) -> int:
    resp = client.post(f"{api_url}/project", headers=headers, json={"name": name})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _upload_file(client, api_url, headers, project_id: int, name: str, content: bytes):
    resp = client.post(
        f"{api_url}/project/{project_id}/file",
        headers=headers,
        files={
            "file": (name, content, "text/plain"),
            "file_info": (
                "",
                f'{{"file_name": "{name}", "file_type": "text/plain"}}',
                "application/json",
            ),
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _file_uuid(file_id: int) -> str | None:
    from ..src import models
    from ..src.db.session import SessionLocal

    db = SessionLocal()
    try:
        file = db.get(models.File, file_id)
        return file.file_uuid if file else None
    finally:
        db.close()


def _blob_path(file_uuid: str) -> str:
    return os.path.join(os.environ["LOCAL_DIRECTORY"], file_uuid)


def _add_config_and_document(project_id: int, file_id: int, *, config_name="cfg"):
    """Attach a preprocessing config + one document to an existing file."""
    from ..src import models
    from ..src.db.session import SessionLocal

    db = SessionLocal()
    try:
        config = models.PreprocessingConfiguration(
            project_id=project_id, name=config_name, additional_settings={}
        )
        db.add(config)
        db.flush()
        doc = models.Document(
            project_id=project_id,
            original_file_id=file_id,
            preprocessing_config_id=config.id,
            text="doc text",
            document_name=f"doc-for-file-{file_id}-{uuid.uuid4().hex[:6]}",
            is_latest=True,
        )
        db.add(doc)
        db.commit()
        return config.id, doc.id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# batch-delete
# ---------------------------------------------------------------------------


def test_batch_delete_removes_files_and_blobs(client, api_url):
    headers = _admin_headers(client, api_url)
    project_id = _make_project(client, api_url, headers, "Batch Delete Happy")

    file_ids, uuids = [], []
    for i in range(3):
        f = _upload_file(
            client, api_url, headers, project_id, f"bd-{i}.txt", f"content {i}".encode()
        )
        file_ids.append(f["id"])
        uuids.append(_file_uuid(f["id"]))

    for u in uuids:
        assert os.path.exists(_blob_path(u)), "uploaded blob missing before delete"

    resp = client.post(
        f"{api_url}/project/{project_id}/file/batch-delete",
        headers=headers,
        json={"file_ids": file_ids, "force": False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_deleted"] == 3
    assert body["errors"] == []
    assert sorted(body["deleted"]) == sorted(file_ids)

    for fid, u in zip(file_ids, uuids):
        assert _file_uuid(fid) is None, "File row survived batch delete"
        assert not os.path.exists(_blob_path(u)), "storage blob survived batch delete"

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_batch_delete_rejects_oversized_batch(client, api_url):
    headers = _admin_headers(client, api_url)
    project_id = _make_project(client, api_url, headers, "Batch Delete Cap")

    resp = client.post(
        f"{api_url}/project/{project_id}/file/batch-delete",
        headers=headers,
        json={"file_ids": list(range(1, 202)), "force": False},
    )
    assert resp.status_code == 400
    assert "200" in resp.json()["detail"]["message"]

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_batch_delete_isolates_per_file_errors(client, api_url):
    """One linked file (no force) and one missing id must not stop the batch:
    the plain file is deleted, the other two produce error entries."""
    plain = None
    headers = _admin_headers(client, api_url)
    project_id = _make_project(client, api_url, headers, "Batch Delete Partial")

    plain = _upload_file(client, api_url, headers, project_id, "plain.txt", b"plain")
    linked = _upload_file(client, api_url, headers, project_id, "linked.txt", b"linked")
    _add_config_and_document(project_id, linked["id"])

    resp = client.post(
        f"{api_url}/project/{project_id}/file/batch-delete",
        headers=headers,
        json={"file_ids": [plain["id"], linked["id"], 99999999], "force": False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["deleted"] == [plain["id"]]
    assert body["total_errors"] == 2
    errors_by_id = {e["file_id"]: e for e in body["errors"]}
    assert linked["id"] in errors_by_id
    assert "linked" in errors_by_id[linked["id"]]["error"]["message"]
    assert errors_by_id[99999999]["error"]["message"] == "File not found"

    # The linked file must still exist after the refused delete.
    assert _file_uuid(linked["id"]) is not None

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_batch_delete_force_removes_linked_documents(client, api_url):
    from ..src import models
    from ..src.db.session import SessionLocal

    headers = _admin_headers(client, api_url)
    project_id = _make_project(client, api_url, headers, "Batch Delete Force")

    linked = _upload_file(client, api_url, headers, project_id, "linked.txt", b"x")
    _, doc_id = _add_config_and_document(project_id, linked["id"])

    resp = client.post(
        f"{api_url}/project/{project_id}/file/batch-delete",
        headers=headers,
        json={"file_ids": [linked["id"]], "force": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["deleted"] == [linked["id"]]

    db = SessionLocal()
    try:
        assert db.get(models.File, linked["id"]) is None
        assert db.get(models.Document, doc_id) is None, (
            "linked document survived force batch delete"
        )
    finally:
        db.close()

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


# ---------------------------------------------------------------------------
# move
# ---------------------------------------------------------------------------


def test_move_files_moves_documents_and_severs_source_lineage(client, api_url):
    """The moved file's documents follow it, their config is cloned into the
    target project, task lineage is nulled — and deleting the SOURCE project
    afterwards must not cascade into the moved rows (the original bug)."""
    from ..src import models
    from ..src.db.session import SessionLocal

    headers = _admin_headers(client, api_url)
    source_id = _make_project(client, api_url, headers, "Move Source")
    target_id = _make_project(client, api_url, headers, "Move Target")

    file = _upload_file(client, api_url, headers, source_id, "move-me.txt", b"move")
    src_config_id, doc_id = _add_config_and_document(source_id, file["id"])

    resp = client.post(
        f"{api_url}/project/{source_id}/file/move",
        headers=headers,
        json={"file_ids": [file["id"]], "target_project_id": target_id},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["moved"] == 1
    assert body["errors"] == []

    db = SessionLocal()
    try:
        moved_file = db.get(models.File, file["id"])
        assert moved_file.project_id == target_id
        doc = db.get(models.Document, doc_id)
        assert doc.project_id == target_id
        assert doc.file_preprocessing_task_id is None
        assert doc.preprocessing_config_id != src_config_id, (
            "document still points at the source project's config"
        )
        clone = db.get(models.PreprocessingConfiguration, doc.preprocessing_config_id)
        assert clone.project_id == target_id
        # The source config stays behind (other source docs may use it).
        assert db.get(models.PreprocessingConfiguration, src_config_id) is not None
    finally:
        db.close()

    # Deleting the source project must not touch the moved file/document.
    resp = client.delete(f"{api_url}/project/{source_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    db = SessionLocal()
    try:
        assert db.get(models.File, file["id"]) is not None, (
            "source project delete cascaded into the moved file"
        )
        assert db.get(models.Document, doc_id) is not None, (
            "source project delete cascaded into the moved document"
        )
    finally:
        db.close()

    client.delete(f"{api_url}/project/{target_id}", headers=headers)


def test_move_files_shared_config_reuses_single_clone(client, api_url):
    from ..src import models
    from ..src.db.session import SessionLocal

    headers = _admin_headers(client, api_url)
    source_id = _make_project(client, api_url, headers, "Move Shared Cfg Source")
    target_id = _make_project(client, api_url, headers, "Move Shared Cfg Target")

    file_a = _upload_file(client, api_url, headers, source_id, "a.txt", b"aaa")
    file_b = _upload_file(client, api_url, headers, source_id, "b.txt", b"bbb")

    # One shared config, one document per file.
    db = SessionLocal()
    try:
        config = models.PreprocessingConfiguration(
            project_id=source_id, name="shared-cfg", additional_settings={}
        )
        db.add(config)
        db.flush()
        doc_ids = []
        for f in (file_a, file_b):
            doc = models.Document(
                project_id=source_id,
                original_file_id=f["id"],
                preprocessing_config_id=config.id,
                text="t",
                document_name=f"shared-{f['id']}",
                is_latest=True,
            )
            db.add(doc)
            db.flush()
            doc_ids.append(doc.id)
        db.commit()
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{source_id}/file/move",
        headers=headers,
        json={
            "file_ids": [file_a["id"], file_b["id"]],
            "target_project_id": target_id,
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["moved"] == 2

    db = SessionLocal()
    try:
        configs = {db.get(models.Document, d).preprocessing_config_id for d in doc_ids}
        assert len(configs) == 1, "shared source config was cloned more than once"
        clones = (
            db.execute(
                select(models.PreprocessingConfiguration).where(
                    models.PreprocessingConfiguration.project_id == target_id
                )
            )
            .scalars()
            .all()
        )
        assert len(clones) == 1
    finally:
        db.close()

    client.delete(f"{api_url}/project/{source_id}", headers=headers)
    client.delete(f"{api_url}/project/{target_id}", headers=headers)


def test_move_blocked_by_trial_reference(client, api_url):
    from ..src import models
    from ..src.db.session import SessionLocal

    headers = _admin_headers(client, api_url)
    source_id = _make_project(client, api_url, headers, "Move Trial Block Source")
    target_id = _make_project(client, api_url, headers, "Move Trial Block Target")

    file = _upload_file(client, api_url, headers, source_id, "ref.txt", b"ref")
    _, doc_id = _add_config_and_document(source_id, file["id"])

    db = SessionLocal()
    try:
        schema = models.Schema(
            project_id=source_id, schema_name="s", schema_definition={}
        )
        prompt = models.Prompt(project_id=source_id, name="p")
        db.add_all([schema, prompt])
        db.flush()
        trial = models.Trial(
            project_id=source_id,
            project_trial_number=1,
            schema_id=schema.id,
            prompt_id=prompt.id,
            llm_model="m",
            base_url="http://localhost",
            document_ids=[doc_id],
        )
        trial.api_key = "k"
        db.add(trial)
        db.commit()
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{source_id}/file/move",
        headers=headers,
        json={"file_ids": [file["id"]], "target_project_id": target_id},
    )
    assert resp.status_code == 409, resp.text
    assert doc_id in resp.json()["detail"]["referenced_document_ids"]

    # Nothing moved.
    db = SessionLocal()
    try:
        assert db.get(models.File, file["id"]).project_id == source_id
        assert db.get(models.Document, doc_id).project_id == source_id
    finally:
        db.close()

    client.delete(f"{api_url}/project/{source_id}", headers=headers)
    client.delete(f"{api_url}/project/{target_id}", headers=headers)


def test_move_blocked_by_document_set_membership(client, api_url):
    from ..src import models
    from ..src.db.session import SessionLocal
    from ..src.models.project import document_set_association

    headers = _admin_headers(client, api_url)
    source_id = _make_project(client, api_url, headers, "Move Set Block Source")
    target_id = _make_project(client, api_url, headers, "Move Set Block Target")

    file = _upload_file(client, api_url, headers, source_id, "member.txt", b"member")
    _, doc_id = _add_config_and_document(source_id, file["id"])

    db = SessionLocal()
    try:
        doc_set = models.DocumentSet(project_id=source_id, name="blocking-set")
        db.add(doc_set)
        db.flush()
        db.execute(
            document_set_association.insert(),
            [{"document_id": doc_id, "document_set_id": doc_set.id}],
        )
        db.commit()
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{source_id}/file/move",
        headers=headers,
        json={"file_ids": [file["id"]], "target_project_id": target_id},
    )
    assert resp.status_code == 409, resp.text
    assert doc_id in resp.json()["detail"]["referenced_document_ids"]

    client.delete(f"{api_url}/project/{source_id}", headers=headers)
    client.delete(f"{api_url}/project/{target_id}", headers=headers)


def test_move_rejects_same_project_and_oversized_batch(client, api_url):
    headers = _admin_headers(client, api_url)
    source_id = _make_project(client, api_url, headers, "Move Validation")
    target_id = _make_project(client, api_url, headers, "Move Validation Target")

    resp = client.post(
        f"{api_url}/project/{source_id}/file/move",
        headers=headers,
        json={"file_ids": [1], "target_project_id": source_id},
    )
    assert resp.status_code == 400
    assert "same" in resp.json()["detail"]["message"]

    resp = client.post(
        f"{api_url}/project/{source_id}/file/move",
        headers=headers,
        json={"file_ids": list(range(1, 202)), "target_project_id": target_id},
    )
    assert resp.status_code == 400
    assert "200" in resp.json()["detail"]["message"]

    client.delete(f"{api_url}/project/{source_id}", headers=headers)
    client.delete(f"{api_url}/project/{target_id}", headers=headers)


def test_move_partial_failure_rolls_back_only_failed_file(client, api_url, monkeypatch):
    """A failure mid-file (config clone constructor raises) must roll back that
    file's SAVEPOINT — file and documents stay fully in the source project —
    while later files still move, and the clone-map entries created inside the
    rolled-back savepoint are NOT reused (they'd be dangling ids)."""
    from ..src import models
    from ..src.db.session import SessionLocal

    headers = _admin_headers(client, api_url)
    source_id = _make_project(client, api_url, headers, "Move Savepoint Source")
    target_id = _make_project(client, api_url, headers, "Move Savepoint Target")

    file_b = _upload_file(client, api_url, headers, source_id, "b-fail.txt", b"bf")
    file_c = _upload_file(client, api_url, headers, source_id, "c-ok.txt", b"co")

    # file_b has two documents: one on "fresh-cfg" (clone flushes fine inside
    # the savepoint) and one on "poison-cfg" (clone constructor raises) — so
    # the savepoint rollback discards an already-cached clone. file_c uses
    # "fresh-cfg" too and must get a NEW, live clone.
    db = SessionLocal()
    try:
        fresh = models.PreprocessingConfiguration(
            project_id=source_id, name="fresh-cfg", additional_settings={}
        )
        poison = models.PreprocessingConfiguration(
            project_id=source_id, name="poison-cfg", additional_settings={}
        )
        db.add_all([fresh, poison])
        db.flush()
        b_doc1 = models.Document(
            project_id=source_id,
            original_file_id=file_b["id"],
            preprocessing_config_id=fresh.id,
            text="t",
            document_name="b-doc-fresh",
            is_latest=True,
        )
        b_doc2 = models.Document(
            project_id=source_id,
            original_file_id=file_b["id"],
            preprocessing_config_id=poison.id,
            text="t",
            document_name="b-doc-poison",
            is_latest=True,
        )
        c_doc = models.Document(
            project_id=source_id,
            original_file_id=file_c["id"],
            preprocessing_config_id=fresh.id,
            text="t",
            document_name="c-doc-fresh",
            is_latest=True,
        )
        db.add_all([b_doc1, b_doc2, c_doc])
        db.commit()
        fresh_id, poison_id = fresh.id, poison.id
        b_doc_ids = [b_doc1.id, b_doc2.id]
        c_doc_id = c_doc.id
    finally:
        db.close()

    # Poison the clone constructor AFTER the source rows exist.
    orig_init = models.PreprocessingConfiguration.__init__

    def poisoned_init(self, *args, **kwargs):
        if kwargs.get("name") == "poison-cfg":
            raise RuntimeError("simulated clone failure")
        orig_init(self, *args, **kwargs)

    monkeypatch.setattr(models.PreprocessingConfiguration, "__init__", poisoned_init)

    resp = client.post(
        f"{api_url}/project/{source_id}/file/move",
        headers=headers,
        json={
            "file_ids": [file_b["id"], file_c["id"]],
            "target_project_id": target_id,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["moved"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["file_id"] == file_b["id"]
    assert "error_id" in body["errors"][0]

    db = SessionLocal()
    try:
        # file_b fully rolled back: still in source, docs untouched.
        assert db.get(models.File, file_b["id"]).project_id == source_id
        for did in b_doc_ids:
            doc = db.get(models.Document, did)
            assert doc.project_id == source_id, "failed file was half-moved"
            assert doc.preprocessing_config_id in (fresh_id, poison_id)

        # file_c moved, and its document points at a LIVE config in the target
        # project (not the dangling clone id from file_b's rolled-back savepoint).
        assert db.get(models.File, file_c["id"]).project_id == target_id
        c_doc = db.get(models.Document, c_doc_id)
        assert c_doc.project_id == target_id
        clone = db.get(models.PreprocessingConfiguration, c_doc.preprocessing_config_id)
        assert clone is not None, "moved document points at a dangling config id"
        assert clone.project_id == target_id
        assert clone.name == "fresh-cfg"
    finally:
        db.close()

    client.delete(f"{api_url}/project/{source_id}", headers=headers)
    client.delete(f"{api_url}/project/{target_id}", headers=headers)
