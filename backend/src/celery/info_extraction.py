# backend/src/celery/info_extraction.py
import asyncio
import datetime as dt
from typing import Any, Dict, List

from openai import AsyncOpenAI
from sqlalchemy import func, select

from .. import models
from ..utils.info_extraction import extract_info_single_doc_async, update_trial_progress
from .celery_config import celery_app

from ..db.session import db_session


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
                                )

                        except asyncio.CancelledError:
                            print(f"[Trial {trial_id}] Doc {doc_id} was force-cancelled!")
                            failures[str(doc_id)] = "Cancelled"
                            raise
                        except Exception as exc:
                            failures[str(doc_id)] = str(exc)
                            print(f"[Trial {trial_id}] Doc {doc_id} failed: {exc}")

                # Launch tasks (they'll be throttled by the semaphore)
                for doc_id in document_ids:
                    doc_tasks[doc_id] = asyncio.create_task(_process(doc_id))

                # Heartbeat: updates progress periodically
                async def _progress_heartbeat():
                    try:
                        while True:
                            await asyncio.sleep(5)
                            with db_session() as db:
                                update_trial_progress(db, trial_id)
                            if all(t.done() for t in doc_tasks.values()):
                                break
                    except Exception as exc:
                        # non-fatal; just log
                        print(f"[Trial {trial_id}] Heartbeat error: {exc}")

                # Cancellation watcher: cancels in-flight tasks
                async def _cancellation_watcher():
                    try:
                        while True:
                            await asyncio.sleep(1)
                            with db_session() as db:
                                trial = db.get(models.Trial, trial_id)
                                if trial and trial.is_cancelled:
                                    print(
                                        f"[Trial {trial_id}] Cancellation detected, aborting in-flight tasks..."
                                    )
                                    for t in doc_tasks.values():
                                        if not t.done():
                                            t.cancel()
                                    break
                            if all(t.done() for t in doc_tasks.values()):
                                break
                    except Exception as exc:
                        print(f"[Trial {trial_id}] Cancellation watcher error: {exc}")

                # Run all together
                await asyncio.gather(
                    asyncio.gather(*doc_tasks.values(), return_exceptions=True),
                    _progress_heartbeat(),
                    _cancellation_watcher(),
                )

            # Finalize state in a short-lived session
            with db_session() as db:
                trial: models.Trial = db.get(models.Trial, trial_id)
                update_trial_progress(db, trial_id)  # ensure docs_done/progress are up to date
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
                        trial.meta = (trial.meta or {}) | {
                            "failures": failures,
                            "eta_seconds": 0,
                        }
                    elif done == total and not failures:
                        trial.status = models.TrialStatus.COMPLETED
                        trial.meta = (trial.meta or {}) | {
                            "failures": {},
                            "eta_seconds": 0,
                        }
                    else:
                        trial.status = models.TrialStatus.FAILED
                        trial.meta = (trial.meta or {}) | {
                            "failures": failures,
                            "eta_seconds": 0,
                        }
                    db.commit()

        asyncio.run(_run())
