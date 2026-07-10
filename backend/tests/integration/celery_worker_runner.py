"""Runs REAL Celery worker + broker preprocessing scenarios (subprocess entry).

Invoked as a subprocess by ``test_celery_integration.py`` with these env vars
already set (before this module imports anything app-related):

    DISABLE_CELERY=false
    CELERY_BROKER_URL=<redis url>
    SQLALCHEMY_DATABASE_URI=<postgres dsn>   (schema already migrated)
    PREPROCESS_CHUNK_SIZE=2

Starts an in-process Celery worker THREAD consuming the ``preprocess`` queue
from the real broker, then dispatches ``process_files_async.delay(...)`` (a real
broker round-trip) and polls the DB for the outcome. This exercises the chunked
self-requeue over actual Redis messages processed by a real worker — the part
the eager-mode test can't cover.

Prints ``PASS ✅`` / ``FAIL ❌`` and exits 0/1.
"""

import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _start_worker() -> subprocess.Popen:
    """Start a REAL Celery worker as a subprocess (its own main thread, so
    signal handlers install cleanly) consuming the preprocess queue."""
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "backend.src.celery.celery_config",
            "worker",
            "-Q",
            "preprocess",
            "-c",
            "1",
            "--pool",
            "solo",
            "--loglevel",
            "warning",
        ],
        cwd=str(_REPO_ROOT),
    )


def _seed_batch(n_files: int, *, cancelled: bool):
    from backend.src import models
    from backend.src.db.session import SessionLocal
    from backend.src.dependencies import save_file
    from backend.src.utils.enums import FileType, PreprocessingStatus

    db = SessionLocal()
    user = models.User(
        email=f"it{time.time_ns()}@example.com",
        full_name="IT",
        hashed_password="x",
        role="user",
    )
    db.add(user)
    db.flush()
    project = models.Project(name="Integration", owner_id=user.id)
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
        rollback_on_cancel=cancelled,
    )
    db.add(task)
    db.flush()
    for i in range(n_files):
        uuid = save_file(f"clinical text {i} for project {project.id}".encode())
        f = models.File(
            project_id=project.id,
            file_name=f"doc_{i}.txt",
            file_type=FileType.TEXT_PLAIN,
            file_uuid=uuid,
            file_size=10,
            file_hash=f"h{project.id}_{i}",
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
    ids = (task.id, project.id)
    db.close()
    return ids


def _wait_terminal(task_id: int, timeout: float = 90.0):
    from backend.src import models
    from backend.src.db.session import SessionLocal
    from backend.src.utils.enums import PreprocessingStatus

    terminal = {
        PreprocessingStatus.COMPLETED,
        PreprocessingStatus.FAILED,
        PreprocessingStatus.CANCELLED,
    }
    deadline = time.time() + timeout
    while time.time() < deadline:
        db = SessionLocal()
        task = db.get(models.PreprocessingTask, task_id)
        status = task.status if task else None
        db.close()
        if status in terminal:
            return status
        time.sleep(0.5)
    return None


def _count_docs(project_id: int) -> int:
    from backend.src import models
    from backend.src.db.session import SessionLocal

    db = SessionLocal()
    n = db.query(models.Document).filter_by(project_id=project_id).count()
    db.close()
    return n


def main() -> int:
    from backend.src.celery.preprocessing import process_files_async
    from backend.src.utils.enums import PreprocessingStatus

    # Start a real worker (subprocess) consuming from the real broker.
    worker = _start_worker()
    time.sleep(5)  # let the worker connect + start consuming
    ok = True
    try:
        if worker.poll() is not None:
            print(f"FAIL: worker exited early (code {worker.returncode})")
            return 1

        # Scenario 1: chunked happy path over the real broker (7 files, chunk 2
        # → the task re-enqueues itself through Redis several times).
        task_id, project_id = _seed_batch(7, cancelled=False)
        process_files_async.delay(task_id)
        status = _wait_terminal(task_id)
        docs = _count_docs(project_id)
        print(
            f"[happy] status={getattr(status, 'value', status)} docs={docs} "
            "(want completed/7)"
        )
        if status != PreprocessingStatus.COMPLETED or docs != 7:
            print("[happy] FAIL")
            ok = False
        else:
            print("[happy] PASS")

        # Scenario 2: a cancelled batch finalizes CANCELLED with rollback.
        task_id, project_id = _seed_batch(5, cancelled=True)
        process_files_async.delay(task_id)
        status = _wait_terminal(task_id)
        docs = _count_docs(project_id)
        print(
            f"[cancel] status={getattr(status, 'value', status)} docs={docs} "
            "(want cancelled/0)"
        )
        if status != PreprocessingStatus.CANCELLED or docs != 0:
            print("[cancel] FAIL")
            ok = False
        else:
            print("[cancel] PASS")
    finally:
        worker.terminate()
        try:
            worker.wait(timeout=15)
        except subprocess.TimeoutExpired:
            worker.kill()

    print("PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
