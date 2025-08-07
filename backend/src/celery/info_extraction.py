import asyncio
import datetime as dt
from typing import Any, Dict, List

from openai import AsyncOpenAI
from sqlalchemy import func, select

from .. import models
from ..dependencies import get_db
from ..utils.info_extraction import extract_info_single_doc_async, update_trial_progress
from .celery_config import celery_app

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
            async with AsyncOpenAI(api_key=api_key, base_url=base_url) as client:
                failures = {}
                doc_tasks = {}

                # Processing for each document
                async def _process(doc_id: int):
                    try:
                        with next(get_db()) as db:
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
                        await extract_info_single_doc_async(
                            client=client,
                            db_session=next(get_db()),
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
                        # You could choose not to count this as failure, or not store at all.
                        raise
                    except Exception as exc:
                        failures[str(doc_id)] = str(exc)
                        print(f"[Trial {trial_id}] Doc {doc_id} failed: {exc}")

                # Launch all doc tasks, with high concurrency
                for doc_id in document_ids:
                    doc_tasks[doc_id] = asyncio.create_task(_process(doc_id))

                # Progress heartbeat coroutine
                async def _progress_heartbeat():
                    while True:
                        await asyncio.sleep(5)
                        with next(get_db()) as db:
                            update_trial_progress(db, trial_id)
                        # Stop heartbeat if all tasks done
                        if all(t.done() for t in doc_tasks.values()):
                            break

                # Cancellation watcher
                async def _cancellation_watcher():
                    while True:
                        await asyncio.sleep(1)
                        with next(get_db()) as db:
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

                # Run all together
                await asyncio.gather(
                    asyncio.gather(*doc_tasks.values(), return_exceptions=True),
                    _progress_heartbeat(),
                    _cancellation_watcher(),
                )

            # Finalize state
            with next(get_db()) as db:
                trial: models.Trial = db.get(models.Trial, trial_id)
                update_trial_progress(db, trial_id)
                trial.finished_at = dt.datetime.now(dt.UTC)
                total = len(trial.document_ids or [])
                done = db.scalar(
                    select(func.count())
                    .select_from(models.TrialResult)
                    .where(models.TrialResult.trial_id == trial_id)
                )
                cancelled = trial.is_cancelled if trial else False
                if cancelled:
                    trial.status = models.TrialStatus.CANCELLED
                    trial.meta = (trial.meta or {}) | {
                        "failures": failures,
                        "eta_seconds": 0,
                    }
                elif done == total and not failures:
                    trial.status = models.TrialStatus.COMPLETED
                    trial.meta = (trial.meta or {}) | {"failures": {}, "eta_seconds": 0}
                else:
                    trial.status = models.TrialStatus.FAILED
                    trial.meta = (trial.meta or {}) | {
                        "failures": failures,
                        "eta_seconds": 0,
                    }
                db.commit()

        asyncio.run(_run())
