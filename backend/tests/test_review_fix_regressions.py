# backend/tests/test_review_fix_regressions.py
"""Regression tests for the 2026-07 review-backlog fixes (tranche 3).

Covers:
- SQLite connections enforce foreign keys (PRAGMA foreign_keys=ON), so the
  test suite exercises the same RESTRICT/FK semantics as PostgreSQL.
- /file/check-duplicates tolerates entries with missing keys (no KeyError 500).
- A rejected preprocess submission no longer leaves an orphaned
  PreprocessingConfiguration row behind.
- A per-file timeout rolls back the timed-out file's partially committed
  (batch-committed row-by-row) documents.
- Cancel-with-rollback keeps documents still referenced by trial results
  instead of failing the whole cancel with an IntegrityError 500.
"""

import types
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text


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


def test_sqlite_enforces_foreign_keys():
    """Every pooled SQLite connection must run with PRAGMA foreign_keys=ON."""
    from ..src.db.session import SessionLocal, engine

    if engine.dialect.name != "sqlite":
        pytest.skip("PRAGMA check only applies to SQLite")

    db = SessionLocal()
    try:
        assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
    finally:
        db.close()


def test_check_duplicates_tolerates_missing_keys(client, api_url):
    """Entries without 'hash'/'filename' must yield no-match rows, not a 500."""
    headers = _admin_headers(client, api_url)
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Dup Keys"}
    ).json()["id"]

    resp = client.post(
        f"{api_url}/project/{project_id}/file/check-duplicates",
        headers=headers,
        json=[{"filename": "no-hash.txt"}, {}, {"hash": "deadbeef"}],
    )
    assert resp.status_code == 200, resp.text
    results = resp.json()
    assert len(results) == 3
    assert all(r["exists"] is False for r in results)

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def test_rejected_preprocess_leaves_no_orphan_config(client, api_url):
    """A submission that fails validation (missing files → 404) must not
    persist the PreprocessingConfiguration it created along the way."""
    from ..src import models
    from ..src.db.session import SessionLocal

    headers = _admin_headers(client, api_url)
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Orphan Config"}
    ).json()["id"]

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess",
        headers=headers,
        json={
            "file_ids": [99999999],
            "inline_config": {"name": "orphan-cfg", "description": "d"},
        },
    )
    assert resp.status_code == 404, resp.text

    db = SessionLocal()
    try:
        configs = (
            db.execute(
                select(models.PreprocessingConfiguration).where(
                    models.PreprocessingConfiguration.project_id == project_id
                )
            )
            .scalars()
            .all()
        )
        assert configs == [], "rejected submission left an orphaned config row"
    finally:
        db.close()

    client.delete(f"{api_url}/project/{project_id}", headers=headers)


def _build_preprocessing_graph(db, *, owner_id: int):
    """Create project → config → file → task → file_task → 2 documents."""
    from ..src import models

    project = models.Project(name="Timeout Rollback", owner_id=owner_id)
    db.add(project)
    db.flush()

    config = models.PreprocessingConfiguration(
        project_id=project.id, name="cfg", additional_settings={}
    )
    db.add(config)
    db.flush()

    file = models.File(
        project_id=project.id,
        file_uuid=str(uuid.uuid4()),
        file_name="rows.csv",
        file_type="text/csv",
    )
    db.add(file)
    db.flush()

    task = models.PreprocessingTask(
        project_id=project.id,
        configuration_id=config.id,
        total_files=1,
        status=models.PreprocessingStatus.IN_PROGRESS,
    )
    db.add(task)
    db.flush()

    file_task = models.FilePreprocessingTask(
        preprocessing_task_id=task.id,
        file_id=file.id,
        file_name=file.file_name,
        status=models.PreprocessingStatus.IN_PROGRESS,
    )
    db.add(file_task)
    db.flush()

    docs = []
    for i in range(2):
        doc = models.Document(
            project_id=project.id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            preprocessing_config_id=config.id,
            text=f"row {i}",
            document_name=f"rows.csv_row_{i}",
            is_latest=True,
        )
        db.add(doc)
        docs.append(doc)
    db.commit()
    return project, config, file, task, file_task, docs


def _admin_user_id():
    from ..src.db.session import SessionLocal
    from ..src.models.user import User

    db = SessionLocal()
    try:
        return (
            db.execute(select(User.id).where(User.email == "admin@example.com"))
            .scalars()
            .first()
        )
    finally:
        db.close()


def test_timeout_finalize_rolls_back_partial_documents():
    """_finalize_after_timeout must delete the timed-out file task's already
    batch-committed documents (partial row-by-row output), not leave them
    live under a FAILED task."""
    from ..src import models
    from ..src.db.session import SessionLocal
    from ..src.utils.preprocessing import PreprocessingPipeline

    db = SessionLocal()
    try:
        project, config, file, task, file_task, docs = _build_preprocessing_graph(
            db, owner_id=_admin_user_id()
        )
        task_id, file_task_id = task.id, file_task.id
        doc_ids = [d.id for d in docs]
    finally:
        db.close()

    pipeline = PreprocessingPipeline.__new__(PreprocessingPipeline)
    pipeline.task = types.SimpleNamespace(id=task_id)
    pipeline._finalize_after_timeout(file_task_id)

    db = SessionLocal()
    try:
        remaining = (
            db.execute(select(models.Document).where(models.Document.id.in_(doc_ids)))
            .scalars()
            .all()
        )
        assert remaining == [], "partial documents survived the timeout rollback"
        task = db.get(models.PreprocessingTask, task_id)
        assert task.status == models.PreprocessingStatus.FAILED
    finally:
        db.close()


def test_cancel_rollback_keeps_trial_referenced_documents(client, api_url):
    """Cancelling with rollback while a trial result references a produced
    document must keep that document (and succeed) instead of tripping the
    RESTRICT FK with a raw IntegrityError 500."""
    from ..src import models
    from ..src.db.session import SessionLocal

    headers = _admin_headers(client, api_url)
    project_id = client.post(
        f"{api_url}/project", headers=headers, json={"name": "Cancel Keep"}
    ).json()["id"]

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
            file_name="rows.csv",
            file_type="text/csv",
        )
        db.add(file)
        db.flush()

        task = models.PreprocessingTask(
            project_id=project_id,
            configuration_id=config.id,
            total_files=1,
            status=models.PreprocessingStatus.IN_PROGRESS,
            rollback_on_cancel=True,
        )
        db.add(task)
        db.flush()

        file_task = models.FilePreprocessingTask(
            preprocessing_task_id=task.id,
            file_id=file.id,
            file_name=file.file_name,
            status=models.PreprocessingStatus.COMPLETED,
        )
        db.add(file_task)
        db.flush()

        referenced_doc = models.Document(
            project_id=project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            preprocessing_config_id=config.id,
            text="referenced",
            document_name="rows.csv_row_0",
            is_latest=True,
        )
        free_doc = models.Document(
            project_id=project_id,
            original_file_id=file.id,
            file_preprocessing_task_id=file_task.id,
            preprocessing_config_id=config.id,
            text="free",
            document_name="rows.csv_row_1",
            is_latest=True,
        )
        db.add_all([referenced_doc, free_doc])
        db.flush()

        schema = models.Schema(
            project_id=project_id, schema_name="s", schema_definition={}
        )
        prompt = models.Prompt(project_id=project_id, name="p")
        db.add_all([schema, prompt])
        db.flush()

        trial = models.Trial(
            project_id=project_id,
            project_trial_number=1,
            schema_id=schema.id,
            prompt_id=prompt.id,
            llm_model="test-model",
            api_key_encrypted="",
            base_url="http://localhost",
            document_ids=[referenced_doc.id],
        )
        db.add(trial)
        db.flush()

        db.add(
            models.TrialResult(
                trial_id=trial.id, document_id=referenced_doc.id, result={}
            )
        )
        db.commit()
        task_id = task.id
        referenced_doc_id = referenced_doc.id
        free_doc_id = free_doc.id
    finally:
        db.close()

    resp = client.post(
        f"{api_url}/project/{project_id}/preprocess/{task_id}/cancel",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "cancelled"
    assert "kept" in body["message"]

    db = SessionLocal()
    try:
        assert db.get(models.Document, referenced_doc_id) is not None, (
            "trial-referenced document was deleted"
        )
        assert db.get(models.Document, free_doc_id) is None, (
            "unreferenced document was not rolled back"
        )
    finally:
        db.close()


def _build_full_project_graph(db, *, owner_id: int):
    """Full object graph: project → file/config/task/file_task/docs → set →
    schema/prompt → trial → result → ground truth → mapping → evaluation →
    metric. Used to prove the bulk project delete removes every child table."""
    from ..src import models
    from ..src.models.project import document_set_association

    project, config, file, task, file_task, docs = _build_preprocessing_graph(
        db, owner_id=owner_id
    )
    project.name = "Bulk Delete"

    doc_set = models.DocumentSet(project_id=project.id, name="set")
    db.add(doc_set)
    db.flush()
    db.execute(
        document_set_association.insert(),
        [{"document_id": d.id, "document_set_id": doc_set.id} for d in docs],
    )

    schema = models.Schema(
        project_id=project.id,
        schema_name="s",
        schema_definition={"type": "object", "properties": {}},
    )
    prompt = models.Prompt(project_id=project.id, name="p")
    db.add_all([schema, prompt])
    db.flush()

    trial = models.Trial(
        project_id=project.id,
        project_trial_number=1,
        schema_id=schema.id,
        prompt_id=prompt.id,
        document_set_id=doc_set.id,
        document_ids=[d.id for d in docs],
        llm_model="m",
        base_url="http://localhost",
    )
    trial.api_key = "k"
    db.add(trial)
    db.flush()

    result = models.TrialResult(
        trial_id=trial.id, document_id=docs[0].id, result={"a": 1}
    )
    gt = models.GroundTruth(
        project_id=project.id, name="gt", format="csv", file_uuid=str(uuid.uuid4())
    )
    db.add_all([result, gt])
    db.flush()

    mapping = models.FieldMapping(
        ground_truth_id=gt.id,
        schema_id=schema.id,
        schema_field="a",
        ground_truth_field="a",
    )
    evaluation = models.Evaluation(
        trial_id=trial.id,
        groundtruth_id=gt.id,
        metrics={},
        field_metrics={},
        document_metrics=[],
    )
    db.add_all([mapping, evaluation])
    db.flush()

    metric = models.EvaluationMetric(
        evaluation_id=evaluation.id,
        document_id=docs[0].id,
        field_name="a",
        is_correct=True,
    )
    db.add(metric)
    db.commit()
    child_ids = {
        "file_task": file_task.id,
        "trial_result": result.id,
        "field_mapping": mapping.id,
        "evaluation": evaluation.id,
        "metric": metric.id,
        "set": doc_set.id,
    }
    return project, child_ids


def test_project_delete_bulk_cascade_removes_all_children(client, api_url):
    """DELETE /project must remove every child row (bulk path, no ORM cascade)."""
    from ..src import models
    from ..src.db.session import SessionLocal
    from ..src.models.project import document_set_association

    headers = _admin_headers(client, api_url)
    db = SessionLocal()
    try:
        project, child_ids = _build_full_project_graph(db, owner_id=_admin_user_id())
        project_id = project.id
    finally:
        db.close()

    resp = client.delete(f"{api_url}/project/{project_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Bulk Delete"

    db = SessionLocal()
    try:
        checks = [
            (models.Project, models.Project.id == project_id),
            (models.File, models.File.project_id == project_id),
            (models.Document, models.Document.project_id == project_id),
            (models.DocumentSet, models.DocumentSet.project_id == project_id),
            (
                models.PreprocessingTask,
                models.PreprocessingTask.project_id == project_id,
            ),
            (
                models.PreprocessingConfiguration,
                models.PreprocessingConfiguration.project_id == project_id,
            ),
            (models.Schema, models.Schema.project_id == project_id),
            (models.Prompt, models.Prompt.project_id == project_id),
            (models.Trial, models.Trial.project_id == project_id),
            (models.GroundTruth, models.GroundTruth.project_id == project_id),
        ]
        for model, cond in checks:
            assert db.execute(select(model).where(cond)).scalars().first() is None, (
                f"{model.__name__} rows survived project delete"
            )
        # Grandchildren without a project_id column: check the specific rows
        # this graph created (the shared test DB may hold other tests' rows).
        assert db.get(models.FilePreprocessingTask, child_ids["file_task"]) is None
        assert db.get(models.TrialResult, child_ids["trial_result"]) is None
        assert db.get(models.FieldMapping, child_ids["field_mapping"]) is None
        assert db.get(models.Evaluation, child_ids["evaluation"]) is None
        assert db.get(models.EvaluationMetric, child_ids["metric"]) is None
        assert (
            db.execute(
                select(document_set_association).where(
                    document_set_association.c.document_set_id == child_ids["set"]
                )
            ).first()
            is None
        ), "document_set_association rows survived project delete"
    finally:
        db.close()


def test_delete_document_set_batched_keeps_referenced_docs(client, api_url):
    """delete_documents=true: unreferenced docs die with the set, docs with
    trial results survive (batched reference checks, bulk deletes)."""
    from ..src import models
    from ..src.db.session import SessionLocal
    from ..src.models.project import document_set_association

    headers = _admin_headers(client, api_url)
    db = SessionLocal()
    try:
        project, config, file, task, file_task, docs = _build_preprocessing_graph(
            db, owner_id=_admin_user_id()
        )
        project_id = project.id
        doc_set = models.DocumentSet(project_id=project.id, name="batch-del")
        db.add(doc_set)
        db.flush()
        set_id = doc_set.id
        db.execute(
            document_set_association.insert(),
            [{"document_id": d.id, "document_set_id": set_id} for d in docs],
        )
        schema = models.Schema(
            project_id=project.id, schema_name="s", schema_definition={}
        )
        prompt = models.Prompt(project_id=project.id, name="p")
        db.add_all([schema, prompt])
        db.flush()
        trial = models.Trial(
            project_id=project.id,
            project_trial_number=1,
            schema_id=schema.id,
            prompt_id=prompt.id,
            document_ids=[],
            llm_model="m",
            base_url="http://localhost",
        )
        trial.api_key = "k"
        db.add(trial)
        db.flush()
        db.add(models.TrialResult(trial_id=trial.id, document_id=docs[0].id, result={}))
        db.commit()
        referenced_id, unreferenced_id = docs[0].id, docs[1].id
    finally:
        db.close()

    resp = client.delete(
        f"{api_url}/project/{project_id}/document-set/{set_id}",
        params={"delete_documents": "true"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["deleted_document_ids"] == [unreferenced_id]

    db = SessionLocal()
    try:
        assert db.get(models.DocumentSet, set_id) is None
        assert db.get(models.Document, referenced_id) is not None
        assert db.get(models.Document, unreferenced_id) is None
        assert (
            db.execute(
                select(document_set_association).where(
                    document_set_association.c.document_set_id == set_id
                )
            ).first()
            is None
        )
    finally:
        db.close()
