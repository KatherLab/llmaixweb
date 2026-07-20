"""Standalone validation of the chunked self-requeue preprocessing task.

Run directly (NOT via the normal pytest env, which disables Celery):

    uv run python -m backend.tests.validate_chunking

Sets up an isolated SQLite DB + local storage, enables Celery in EAGER mode
(so the re-enqueue runs synchronously in-process), and runs a batch of N text
files with a small PREPROCESS_CHUNK_SIZE so the task must re-enqueue itself
several times. Verifies every file is processed exactly once across the chunks
and the task finalizes COMPLETED.
"""

import os
import tempfile

# Must be set BEFORE importing anything that builds settings / the celery app.
_tmp = tempfile.mkdtemp(prefix="chunkval_")
os.environ["SKIP_RUNTIME_CHECKS"] = "true"
os.environ["DISABLE_CELERY"] = "false"  # build the celery app + task
os.environ["OPENAI_NO_API_CHECK"] = "true"
os.environ["SECRET_KEY"] = "validation-secret-key-1234567890"
os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{_tmp}/db.sqlite"
os.environ["LOCAL_DIRECTORY"] = _tmp
os.environ["PREPROCESS_CHUNK_SIZE"] = "2"  # tiny chunk → forces several resumes
os.environ["DOCLING_SERVE_ENABLED"] = "false"

N_FILES = 7  # with chunk size 2 → chunks of 2,2,2,1 (4 executions)


def _seed_batch(n_files: int, *, cancelled: bool, rollback: bool):
    from backend.src import models
    from backend.src.db.session import SessionLocal
    from backend.src.dependencies import save_file
    from backend.src.utils.enums import FileType, PreprocessingStatus

    db = SessionLocal()
    user = db.query(models.User).filter_by(
        email="v@example.com"
    ).first() or models.User(
        email="v@example.com", full_name="V", hashed_password="x", role="user"
    )
    db.add(user)
    db.flush()
    project = models.Project(name="Chunk Validation", owner_id=user.id)
    db.add(project)
    db.flush()
    config = models.PreprocessingConfiguration(
        project_id=project.id, name="cfg", additional_settings={}
    )
    db.add(config)
    db.flush()
    task = models.PreprocessingTask(
        project_id=project.id,
        configuration_id=config.id,
        total_files=n_files,
        is_cancelled=cancelled,
        rollback_on_cancel=rollback,
    )
    db.add(task)
    db.flush()
    for i in range(n_files):
        uuid = save_file(f"clinical text for document number {i}".encode())
        f = models.File(
            project_id=project.id,
            file_name=f"doc_{i}.txt",
            file_type=FileType.TEXT_PLAIN,
            file_uuid=uuid,
            file_size=10,
            file_hash=f"hash{project.id}_{i}",
        )
        db.add(f)
        db.flush()
        db.add(
            models.FilePreprocessingTask(
                preprocessing_task_id=task.id,
                file_id=f.id,
                file_name=f.file_name,
                status=PreprocessingStatus.PENDING,
            )
        )
    db.commit()
    task_id, project_id = task.id, project.id
    db.close()
    return task_id, project_id


def _scenario_happy_path() -> bool:
    from backend.src import models
    from backend.src.celery.preprocessing import process_files_async
    from backend.src.db.session import SessionLocal
    from backend.src.utils.enums import PreprocessingStatus

    task_id, project_id = _seed_batch(N_FILES, cancelled=False, rollback=False)
    process_files_async.apply(args=[task_id])  # eager → drives all resumes

    db = SessionLocal()
    task = db.get(models.PreprocessingTask, task_id)
    statuses = [
        ft.status
        for ft in db.query(models.FilePreprocessingTask).filter_by(
            preprocessing_task_id=task_id
        )
    ]
    docs = db.query(models.Document).filter_by(project_id=project_id).count()
    db.close()

    print(
        f"[happy] task.status={task.status.value} docs={docs} (want completed/{N_FILES})"
    )
    ok = (
        task.status == PreprocessingStatus.COMPLETED
        and all(s == PreprocessingStatus.COMPLETED for s in statuses)
        and docs == N_FILES
    )
    print("[happy] PASS" if ok else "[happy] FAIL")
    return ok


def _scenario_cancelled() -> bool:
    """A cancelled batch must stop chunking and finalize CANCELLED with rollback."""
    from backend.src import models
    from backend.src.celery.preprocessing import process_files_async
    from backend.src.db.session import SessionLocal
    from backend.src.utils.enums import PreprocessingStatus

    task_id, project_id = _seed_batch(N_FILES, cancelled=True, rollback=True)
    process_files_async.apply(args=[task_id])

    db = SessionLocal()
    task = db.get(models.PreprocessingTask, task_id)
    docs = db.query(models.Document).filter_by(project_id=project_id).count()
    db.close()

    print(f"[cancel] task.status={task.status.value} docs={docs} (want cancelled/0)")
    ok = task.status == PreprocessingStatus.CANCELLED and docs == 0
    print("[cancel] PASS" if ok else "[cancel] FAIL")
    return ok


def _run_with_cancel_at_first_chunk_boundary(task_id: int, on_cancel=None):
    """Run the task, flipping is_cancelled when the first chunk re-enqueues.

    In eager mode the self-re-enqueue (``apply_async(..., resumed=True)``) runs
    inline, so intercepting it is exactly "the user cancelled between chunk 1
    and chunk 2": chunk 1's documents are already committed, later files are
    still PENDING. ``on_cancel(db)`` lets a scenario mutate state (e.g. add a
    trial result) at that same moment, before the resumed run continues.
    """
    from backend.src import models
    from backend.src.celery.preprocessing import process_files_async
    from backend.src.db.session import SessionLocal

    original_apply_async = process_files_async.apply_async
    fired = {"done": False}

    def cancelling_apply_async(*args, **kwargs):
        if not fired["done"]:
            fired["done"] = True
            db = SessionLocal()
            try:
                task = db.get(models.PreprocessingTask, task_id)
                task.is_cancelled = True
                if on_cancel is not None:
                    on_cancel(db)
                db.commit()
            finally:
                db.close()
        return original_apply_async(*args, **kwargs)

    process_files_async.apply_async = cancelling_apply_async
    try:
        process_files_async.apply(args=[task_id])
    finally:
        process_files_async.apply_async = original_apply_async
    assert fired["done"], "task never reached a chunk boundary (no re-enqueue)"


def _scenario_mid_chunk_cancel_rollback() -> bool:
    """Cancel arriving BETWEEN chunks (rollback_on_cancel=True): chunk 1's
    already-committed documents must be rolled back, later files end CANCELLED,
    and the task finalizes CANCELLED without processing further chunks."""
    from backend.src import models
    from backend.src.db.session import SessionLocal
    from backend.src.utils.enums import PreprocessingStatus

    task_id, project_id = _seed_batch(N_FILES, cancelled=False, rollback=True)
    _run_with_cancel_at_first_chunk_boundary(task_id)

    db = SessionLocal()
    task = db.get(models.PreprocessingTask, task_id)
    statuses = [
        ft.status
        for ft in db.query(models.FilePreprocessingTask).filter_by(
            preprocessing_task_id=task_id
        )
    ]
    docs = db.query(models.Document).filter_by(project_id=project_id).count()
    db.close()

    completed = sum(1 for s in statuses if s == PreprocessingStatus.COMPLETED)
    cancelled = sum(1 for s in statuses if s == PreprocessingStatus.CANCELLED)
    print(
        f"[mid-cancel-rollback] task.status={task.status.value} docs={docs} "
        f"completed={completed} cancelled={cancelled} "
        f"(want cancelled/0 docs, some completed, rest cancelled)"
    )
    ok = (
        task.status == PreprocessingStatus.CANCELLED
        and docs == 0
        and 0 < completed < N_FILES
        and completed + cancelled == N_FILES
        and "rolled back" in (task.message or "")
    )
    print("[mid-cancel-rollback] PASS" if ok else "[mid-cancel-rollback] FAIL")
    return ok


def _scenario_mid_chunk_cancel_keep_processed() -> bool:
    """Cancel between chunks with rollback_on_cancel=False: chunk 1's documents
    are KEPT, their file tasks stay COMPLETED, the rest end CANCELLED."""
    from backend.src import models
    from backend.src.db.session import SessionLocal
    from backend.src.utils.enums import PreprocessingStatus

    task_id, project_id = _seed_batch(N_FILES, cancelled=False, rollback=False)
    _run_with_cancel_at_first_chunk_boundary(task_id)

    db = SessionLocal()
    task = db.get(models.PreprocessingTask, task_id)
    statuses = [
        ft.status
        for ft in db.query(models.FilePreprocessingTask).filter_by(
            preprocessing_task_id=task_id
        )
    ]
    docs = db.query(models.Document).filter_by(project_id=project_id).count()
    db.close()

    completed = sum(1 for s in statuses if s == PreprocessingStatus.COMPLETED)
    cancelled = sum(1 for s in statuses if s == PreprocessingStatus.CANCELLED)
    print(
        f"[mid-cancel-keep] task.status={task.status.value} docs={docs} "
        f"completed={completed} cancelled={cancelled} "
        f"(want cancelled, docs == completed > 0)"
    )
    ok = (
        task.status == PreprocessingStatus.CANCELLED
        and 0 < completed < N_FILES
        and docs == completed
        and completed + cancelled == N_FILES
        and task.processed_files == completed
        and task.skipped_files == cancelled
        and "keeping processed documents" in (task.message or "")
    )
    print("[mid-cancel-keep] PASS" if ok else "[mid-cancel-keep] FAIL")
    return ok


def _scenario_mid_chunk_cancel_rollback_keeps_referenced() -> bool:
    """Rollback-on-cancel must skip a chunk-1 document a trial result already
    references (ON DELETE RESTRICT) instead of failing the finalization, and
    say so in the message."""
    from backend.src import models
    from backend.src.db.session import SessionLocal
    from backend.src.utils.enums import PreprocessingStatus

    task_id, project_id = _seed_batch(N_FILES, cancelled=False, rollback=True)

    def reference_first_doc(db):
        doc = (
            db.query(models.Document)
            .filter_by(project_id=project_id)
            .order_by(models.Document.id)
            .first()
        )
        assert doc is not None, "no chunk-1 document to reference"
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
            llm_model="m",
            base_url="http://localhost",
            document_ids=[doc.id],
        )
        trial.api_key = "k"
        db.add(trial)
        db.flush()
        db.add(models.TrialResult(trial_id=trial.id, document_id=doc.id, result={}))

    _run_with_cancel_at_first_chunk_boundary(task_id, on_cancel=reference_first_doc)

    db = SessionLocal()
    task = db.get(models.PreprocessingTask, task_id)
    docs = db.query(models.Document).filter_by(project_id=project_id).count()
    db.close()

    print(
        f"[mid-cancel-restrict] task.status={task.status.value} docs={docs} "
        f"(want cancelled, exactly the referenced doc kept)"
    )
    ok = (
        task.status == PreprocessingStatus.CANCELLED
        and docs == 1
        and "kept because trial results or evaluations" in (task.message or "")
    )
    print("[mid-cancel-restrict] PASS" if ok else "[mid-cancel-restrict] FAIL")
    return ok


def main() -> int:
    from backend.src.celery.celery_config import celery_app
    from backend.src.db.base import Base
    from backend.src.db.session import engine

    # Run the re-enqueue synchronously, in-process.
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    Base.metadata.create_all(bind=engine)

    # Run every scenario (no short-circuit) so a failure prints all results.
    results = [
        _scenario_happy_path(),
        _scenario_cancelled(),
        _scenario_mid_chunk_cancel_rollback(),
        _scenario_mid_chunk_cancel_keep_processed(),
        _scenario_mid_chunk_cancel_rollback_keeps_referenced(),
    ]
    ok = all(results)
    print("PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
