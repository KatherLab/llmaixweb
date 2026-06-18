# backend/src/celery/info_extraction.py
import asyncio
import datetime as dt
import logging
from typing import Any, Dict, List

from openai import AsyncOpenAI
from sqlalchemy import func, select

from .. import models
from ..db.session import db_session
from ..utils.info_extraction import extract_info_single_doc_async, update_trial_progress
from .celery_config import celery_app

log = logging.getLogger(__name__)


def _broadcast_trial_update(trial: models.Trial, event: str = "progress"):
    """Broadcast trial task update via Redis pub/sub (for use in Celery tasks).

    Since Celery workers run in separate processes/containers from FastAPI,
    we use Redis pub/sub to send messages to the FastAPI backend, which then
    broadcasts to connected WebSocket clients.

    Includes full trial data so frontend can display complete trial information.
    """
    try:
        from ..utils.redis_broadcast import publish_trial_update

        # Build full trial data for frontend display
        trial_data = {
            "type": "trial_update",
            "trial_id": trial.id,
            "project_id": trial.project_id,
            "status": trial.status.value
            if hasattr(trial.status, "value")
            else str(trial.status),
            "docs_done": trial.docs_done,
            "documents_count": len(trial.document_ids) if trial.document_ids else 0,
            "progress": float(trial.progress) if trial.progress else 0,
            "name": trial.name,
            "started_at": trial.started_at.isoformat() if trial.started_at else None,
            "finished_at": trial.finished_at.isoformat() if trial.finished_at else None,
            "meta": trial.meta,
            "event": event,
        }

        publish_trial_update(trial_data)
    except ImportError as e:
        log.debug("Redis broadcast not available: %s", e)
    except Exception as e:
        log.error("Error broadcasting trial update: %s", e, exc_info=True)


if celery_app:

    @celery_app.task(
        bind=True,
        autoretry_for=(Exception,),
        retry_backoff=True,
        acks_late=True,
    )
    def extract_info_celery(
        self,
        trial_id: int,
        document_ids: List[int],
        llm_model: str,
        api_key: str,
        base_url: str,
        schema_id: int,
        prompt_id: int,
        project_id: int,
        advanced_options: Dict[str, Any] | None = None,
    ) -> None:
        async def _run():
            # Create one client per task
            async with AsyncOpenAI(api_key=api_key, base_url=base_url) as client:
                failures: Dict[str, str] = {}
                doc_tasks: Dict[int, asyncio.Task] = {}

                # ---- Concurrency limiter inside the task ----
                max_conc = 8
                if advanced_options and isinstance(advanced_options, dict):
                    max_conc = int(advanced_options.get("max_concurrency", max_conc))
                    if max_conc < 1:
                        max_conc = 1
                sem = asyncio.Semaphore(max_conc)

                # Per-document processing -------------------------------------------------
                async def _process(doc_id: int):
                    async with sem:
                        try:
                            # First, quick checks with a short-lived session
                            with db_session() as db:
                                trial = db.get(models.Trial, trial_id)
                                if trial and trial.is_cancelled:
                                    raise asyncio.CancelledError("Trial was cancelled")

                                exists = db.scalar(
                                    select(models.TrialResult.id).where(
                                        models.TrialResult.trial_id == trial_id,
                                        models.TrialResult.document_id == doc_id,
                                    )
                                )
                                if exists:
                                    return

                            # Do the LLM call + store result with a fresh session
                            with db_session() as db:
                                await extract_info_single_doc_async(
                                    client=client,
                                    db_session=db,
                                    trial_id=trial_id,
                                    document_id=doc_id,
                                    llm_model=llm_model,
                                    schema_id=schema_id,
                                    prompt_id=prompt_id,
                                    project_id=project_id,
                                    advanced_options=advanced_options,
                                    base_url=base_url,
                                )

                        except asyncio.CancelledError:
                            log.warning(
                                "Trial %s: Doc %s was force-cancelled", trial_id, doc_id
                            )
                            failures[str(doc_id)] = "Cancelled"
                            raise
                        except Exception as exc:
                            failures[str(doc_id)] = str(exc)
                            log.error(
                                "Trial %s: Doc %s failed: %s", trial_id, doc_id, exc
                            )

                # Launch tasks (they'll be throttled by the semaphore)
                for doc_id in document_ids:
                    doc_tasks[doc_id] = asyncio.create_task(_process(doc_id))

                # Heartbeat: updates progress periodically + broadcasts via WebSocket
                async def _progress_heartbeat():
                    try:
                        last_broadcast = None
                        while True:
                            await asyncio.sleep(3)  # Faster updates (matching preprocessing)
                            with db_session() as db:
                                update_trial_progress(db, trial_id)
                                trial = db.get(models.Trial, trial_id)

                                if trial:
                                    # Broadcast update if status/progress changed
                                    current_state = (
                                        trial.status,
                                        trial.docs_done,
                                        trial.progress,
                                    )
                                    if last_broadcast != current_state:
                                        last_broadcast = current_state
                                        _broadcast_trial_update(trial, "progress")

                            if all(t.done() for t in doc_tasks.values()):
                                break
                    except Exception as exc:
                        # non-fatal; just log
                        log.warning("Trial %s: Heartbeat error: %s", trial_id, exc)

                # Cancellation watcher: cancels in-flight tasks
                async def _cancellation_watcher():
                    try:
                        while True:
                            await asyncio.sleep(1)
                            with db_session() as db:
                                trial = db.get(models.Trial, trial_id)
                                if trial and trial.is_cancelled:
                                    log.warning(
                                        "Trial %s: Cancellation detected, aborting in-flight tasks",
                                        trial_id,
                                    )
                                    for t in doc_tasks.values():
                                        if not t.done():
                                            t.cancel()
                                    break
                            if all(t.done() for t in doc_tasks.values()):
                                break
                    except Exception as exc:
                        log.warning(
                            "Trial %s: Cancellation watcher error: %s", trial_id, exc
                        )

                # Run all together
                await asyncio.gather(
                    asyncio.gather(*doc_tasks.values(), return_exceptions=True),
                    _progress_heartbeat(),
                    _cancellation_watcher(),
                )

            # Finalize state in a short-lived session
            with db_session() as db:
                trial: models.Trial = db.get(models.Trial, trial_id)
                update_trial_progress(
                    db, trial_id
                )  # ensure docs_done/progress are up to date
                if trial:
                    trial.finished_at = dt.datetime.now(dt.UTC)
                    total = len(trial.document_ids or [])
                    done = db.scalar(
                        select(func.count())
                        .select_from(models.TrialResult)
                        .where(models.TrialResult.trial_id == trial_id)
                    )
                    cancelled = trial.is_cancelled

                    if cancelled:
                        trial.status = models.TrialStatus.CANCELLED
                        event = "cancelled"
                        trial.meta = (trial.meta or {}) | {
                            "failures": failures,
                            "eta_seconds": 0,
                        }
                    elif done == total and not failures:
                        trial.status = models.TrialStatus.COMPLETED
                        event = "completed"
                        trial.meta = (trial.meta or {}) | {
                            "failures": {},
                            "eta_seconds": 0,
                        }
                    else:
                        trial.status = models.TrialStatus.FAILED
                        event = "failed"
                        trial.meta = (trial.meta or {}) | {
                            "failures": failures,
                            "eta_seconds": 0,
                        }
                    db.commit()

                    # Broadcast final status via Redis pub/sub
                    _broadcast_trial_update(trial, event)

        asyncio.run(_run())
