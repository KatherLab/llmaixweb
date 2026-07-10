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
    user = (
        db.query(models.User).filter_by(email="v@example.com").first()
        or models.User(
            email="v@example.com", full_name="V", hashed_password="x", role="user"
        )
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

    print(f"[happy] task.status={task.status.value} docs={docs} (want completed/{N_FILES})")
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


def main() -> int:
    from backend.src.celery.celery_config import celery_app
    from backend.src.db.base import Base
    from backend.src.db.session import engine

    # Run the re-enqueue synchronously, in-process.
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    Base.metadata.create_all(bind=engine)

    ok = _scenario_happy_path() and _scenario_cancelled()
    print("PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
