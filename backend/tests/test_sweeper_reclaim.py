# backend/tests/test_sweeper_reclaim.py
"""Tests for the orphan sweeper and worker-startup reclaim decision logic
(celery/task_signals.py).

These are plain functions (importable with DISABLE_CELERY=True), so the
decision rules can be pinned without a broker:
- sweep_orphans: stale-heartbeat cutoff (with started_at fallback for rows
  that never heartbeated), no reap while the heartbeat is fresh, parent
  finalization ONLY when no sibling file task is still in flight (no
  FAILED→COMPLETED status flap), completed-only processed_files counters,
  and stuck-trial finalization via updated_at with the _sweeper failure marker.
- reclaim_orphaned_on_startup: role scoping (preprocess vs default), the
  bypass_celery exclusion (a worker restart says nothing about a trial running
  inside the web process), and counter semantics on reclaimed tasks.
"""

import datetime
import uuid

import pytest
from sqlalchemy import func, select


def _now():
    return datetime.datetime.now(datetime.UTC)


def _old():
    """Well past any reasonable ORPHAN_STALE_SECONDS."""
    return _now() - datetime.timedelta(hours=2)


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


def _build_task_graph(db, *, name: str, file_task_specs: list[dict]):
    """project → config → file → IN_PROGRESS parent task → file tasks.

    Each spec: {"status": ..., "last_heartbeat_at": ..., "started_at": ...}.
    """
    from ..src import models

    project = models.Project(name=name, owner_id=_admin_user_id())
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
        file_name="f.txt",
        file_type="text/plain",
    )
    db.add(file)
    db.flush()
    task = models.PreprocessingTask(
        project_id=project.id,
        configuration_id=config.id,
        total_files=len(file_task_specs),
        status=models.PreprocessingStatus.IN_PROGRESS,
    )
    db.add(task)
    db.flush()
    file_tasks = []
    for spec in file_task_specs:
        ft = models.FilePreprocessingTask(
            preprocessing_task_id=task.id,
            file_id=file.id,
            file_name=file.file_name,
            status=spec["status"],
            last_heartbeat_at=spec.get("last_heartbeat_at"),
            started_at=spec.get("started_at"),
        )
        db.add(ft)
        file_tasks.append(ft)
    db.commit()
    return project, task, file_tasks


def _make_trial(db, project_id: int, *, status, updated_at, bypass_celery=False):
    from ..src import models

    schema = models.Schema(project_id=project_id, schema_name="s", schema_definition={})
    prompt = models.Prompt(project_id=project_id, name="p")
    db.add_all([schema, prompt])
    db.flush()
    next_number = (
        db.execute(
            select(func.coalesce(func.max(models.Trial.project_trial_number), 0)).where(
                models.Trial.project_id == project_id
            )
        ).scalar()
        + 1
    )
    trial = models.Trial(
        project_id=project_id,
        project_trial_number=next_number,
        schema_id=schema.id,
        prompt_id=prompt.id,
        llm_model="m",
        base_url="http://localhost",
        document_ids=[],
        status=status,
        updated_at=updated_at,
        bypass_celery=bypass_celery,
    )
    trial.api_key = "k"
    db.add(trial)
    db.commit()
    return trial


@pytest.fixture
def db():
    from ..src.db.session import SessionLocal

    db = SessionLocal()
    yield db
    db.close()


def _fresh(db, obj):
    db.expire_all()
    return db.get(type(obj), obj.id)


def _finalize_leftovers(db, *objs):
    """Mark still-running rows CANCELLED so later tests' sweep/reclaim calls
    (which scan the whole shared test DB) don't pick them up."""
    from ..src import models

    for obj in objs:
        row = _fresh(db, obj)
        if isinstance(row, models.Trial):
            if row.status == models.TrialStatus.PROCESSING:
                row.status = models.TrialStatus.CANCELLED
        elif row.status in (
            models.PreprocessingStatus.PENDING,
            models.PreprocessingStatus.IN_PROGRESS,
        ):
            row.status = models.PreprocessingStatus.CANCELLED
    db.commit()


# ---------------------------------------------------------------------------
# sweep_orphans
# ---------------------------------------------------------------------------


def test_sweep_reaps_stale_file_task_and_finalizes_parent(db):
    from ..src import models
    from ..src.celery.task_signals import sweep_orphans

    project, task, (stale_ft, done_ft) = _build_task_graph(
        db,
        name="Sweep Stale",
        file_task_specs=[
            {
                "status": models.PreprocessingStatus.IN_PROGRESS,
                "last_heartbeat_at": _old(),
            },
            {"status": models.PreprocessingStatus.COMPLETED},
        ],
    )

    sweep_orphans()

    stale_ft = _fresh(db, stale_ft)
    task = _fresh(db, task)
    assert stale_ft.status == models.PreprocessingStatus.FAILED
    assert "interrupted" in stale_ft.error_message
    # No sibling in flight → the parent is finalized with accurate counters.
    assert task.status == models.PreprocessingStatus.FAILED
    assert task.processed_files == 1
    assert task.failed_files == 1
    assert task.completed_at is not None
    assert "1 of 2 files processed" in task.message


def test_sweep_leaves_parent_alone_while_sibling_in_flight(db):
    """A stale file task is failed, but the parent must NOT be finalized while
    a sibling with a fresh heartbeat is still running — finalizing now would
    flap FAILED→COMPLETED when the live worker finishes."""
    from ..src import models
    from ..src.celery.task_signals import sweep_orphans

    project, task, (stale_ft, live_ft) = _build_task_graph(
        db,
        name="Sweep Flap Guard",
        file_task_specs=[
            {
                "status": models.PreprocessingStatus.IN_PROGRESS,
                "last_heartbeat_at": _old(),
            },
            {
                "status": models.PreprocessingStatus.IN_PROGRESS,
                "last_heartbeat_at": _now(),
            },
        ],
    )

    sweep_orphans()

    stale_ft, live_ft, task = (
        _fresh(db, stale_ft),
        _fresh(db, live_ft),
        _fresh(db, task),
    )
    assert stale_ft.status == models.PreprocessingStatus.FAILED
    assert live_ft.status == models.PreprocessingStatus.IN_PROGRESS
    assert task.status == models.PreprocessingStatus.IN_PROGRESS, (
        "parent was finalized while a file task was still in flight"
    )
    # Counters are still refreshed.
    assert task.failed_files == 1

    _finalize_leftovers(db, task, live_ft)


def test_sweep_ignores_fresh_heartbeat_even_if_started_long_ago(db):
    """A slow-but-alive file (old started_at, fresh heartbeat) is legitimate:
    the heartbeat, not the start time, decides staleness."""
    from ..src import models
    from ..src.celery.task_signals import sweep_orphans

    project, task, (slow_ft,) = _build_task_graph(
        db,
        name="Sweep Slow Alive",
        file_task_specs=[
            {
                "status": models.PreprocessingStatus.IN_PROGRESS,
                "last_heartbeat_at": _now(),
                "started_at": _old(),
            },
        ],
    )

    sweep_orphans()

    slow_ft, task = _fresh(db, slow_ft), _fresh(db, task)
    assert slow_ft.status == models.PreprocessingStatus.IN_PROGRESS
    assert task.status == models.PreprocessingStatus.IN_PROGRESS

    _finalize_leftovers(db, task, slow_ft)


def test_sweep_falls_back_to_started_at_when_never_heartbeated(db):
    """A row that crashed before its first heartbeat bump (heartbeat NULL) is
    judged by started_at instead."""
    from ..src import models
    from ..src.celery.task_signals import sweep_orphans

    project, task, (crashed_ft,) = _build_task_graph(
        db,
        name="Sweep Heartbeat Fallback",
        file_task_specs=[
            {
                "status": models.PreprocessingStatus.IN_PROGRESS,
                "last_heartbeat_at": None,
                "started_at": _old(),
            },
        ],
    )

    sweep_orphans()

    crashed_ft = _fresh(db, crashed_ft)
    assert crashed_ft.status == models.PreprocessingStatus.FAILED


def test_sweep_fails_stuck_trial_and_spares_fresh_one(db):
    from ..src import models
    from ..src.celery.task_signals import sweep_orphans

    project = models.Project(name="Sweep Trials", owner_id=_admin_user_id())
    db.add(project)
    db.commit()

    stuck = _make_trial(
        db, project.id, status=models.TrialStatus.PROCESSING, updated_at=_old()
    )
    fresh = _make_trial(
        db, project.id, status=models.TrialStatus.PROCESSING, updated_at=_now()
    )
    # A bypass trial with a fresh heartbeat (the sync path ticks updated_at)
    # must equally be left alone.
    fresh_bypass = _make_trial(
        db,
        project.id,
        status=models.TrialStatus.PROCESSING,
        updated_at=_now(),
        bypass_celery=True,
    )

    sweep_orphans()

    stuck, fresh, fresh_bypass = (
        _fresh(db, stuck),
        _fresh(db, fresh),
        _fresh(db, fresh_bypass),
    )
    assert stuck.status == models.TrialStatus.FAILED
    assert stuck.finished_at is not None
    assert "_sweeper" in stuck.meta["failures"]
    assert stuck.meta["eta_seconds"] == 0
    assert fresh.status == models.TrialStatus.PROCESSING
    assert fresh_bypass.status == models.TrialStatus.PROCESSING

    _finalize_leftovers(db, fresh, fresh_bypass)


# ---------------------------------------------------------------------------
# reclaim_orphaned_on_startup
# ---------------------------------------------------------------------------


def test_reclaim_preprocess_finalizes_in_progress_tasks_with_correct_counters(db):
    """A restarted preprocess worker owns every non-terminal preprocessing
    task: in-flight file tasks fail, and processed_files counts COMPLETED only
    (a fully-failed reclaimed task must not report 'N of N processed')."""
    from ..src import models
    from ..src.celery.task_signals import reclaim_orphaned_on_startup

    project, task, (done_ft, running_ft, cancelled_ft) = _build_task_graph(
        db,
        name="Reclaim Preprocess",
        file_task_specs=[
            {"status": models.PreprocessingStatus.COMPLETED},
            {
                "status": models.PreprocessingStatus.IN_PROGRESS,
                # Fresh heartbeat: the startup reclaim must ignore staleness —
                # the restart itself is the evidence.
                "last_heartbeat_at": _now(),
            },
            {"status": models.PreprocessingStatus.CANCELLED},
        ],
    )

    reclaim_orphaned_on_startup("preprocess")

    task = _fresh(db, task)
    running_ft = _fresh(db, running_ft)
    assert task.status == models.PreprocessingStatus.FAILED
    assert running_ft.status == models.PreprocessingStatus.FAILED
    assert running_ft.completed_at is not None
    assert task.processed_files == 1, "processed_files must count COMPLETED only"
    assert task.failed_files == 1
    assert task.skipped_files == 1
    assert task.completed_at is not None


def test_reclaim_preprocess_does_not_touch_trials(db):
    from ..src import models
    from ..src.celery.task_signals import reclaim_orphaned_on_startup

    project = models.Project(name="Reclaim Scope P", owner_id=_admin_user_id())
    db.add(project)
    db.commit()
    trial = _make_trial(
        db, project.id, status=models.TrialStatus.PROCESSING, updated_at=_now()
    )

    reclaim_orphaned_on_startup("preprocess")

    assert _fresh(db, trial).status == models.TrialStatus.PROCESSING
    _finalize_leftovers(db, trial)


def test_reclaim_default_fails_celery_trials_but_spares_bypass(db):
    """role=default reclaims PROCESSING Celery trials (with the _restart
    marker) but must NOT touch bypass trials — they run inside the web
    process, so a worker restart says nothing about them."""
    from ..src import models
    from ..src.celery.task_signals import reclaim_orphaned_on_startup

    project = models.Project(name="Reclaim Default", owner_id=_admin_user_id())
    db.add(project)
    db.commit()

    celery_trial = _make_trial(
        db, project.id, status=models.TrialStatus.PROCESSING, updated_at=_now()
    )
    bypass_trial = _make_trial(
        db,
        project.id,
        status=models.TrialStatus.PROCESSING,
        updated_at=_now(),
        bypass_celery=True,
    )
    completed_trial = _make_trial(
        db, project.id, status=models.TrialStatus.COMPLETED, updated_at=_now()
    )

    reclaim_orphaned_on_startup("default")

    celery_trial = _fresh(db, celery_trial)
    assert celery_trial.status == models.TrialStatus.FAILED
    assert celery_trial.finished_at is not None
    assert "_restart" in celery_trial.meta["failures"]
    assert _fresh(db, bypass_trial).status == models.TrialStatus.PROCESSING, (
        "startup reclaim false-failed a live bypass trial"
    )
    assert _fresh(db, completed_trial).status == models.TrialStatus.COMPLETED

    _finalize_leftovers(db, bypass_trial)


def test_reclaim_default_does_not_touch_preprocessing_tasks(db):
    from ..src import models
    from ..src.celery.task_signals import reclaim_orphaned_on_startup

    project, task, (running_ft,) = _build_task_graph(
        db,
        name="Reclaim Scope D",
        file_task_specs=[
            {
                "status": models.PreprocessingStatus.IN_PROGRESS,
                "last_heartbeat_at": _now(),
            },
        ],
    )

    reclaim_orphaned_on_startup("default")

    assert _fresh(db, task).status == models.PreprocessingStatus.IN_PROGRESS
    assert _fresh(db, running_ft).status == models.PreprocessingStatus.IN_PROGRESS

    _finalize_leftovers(db, task, running_ft)
