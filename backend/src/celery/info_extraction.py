# celery/info_extraction.py
import asyncio
import datetime as dt
from typing import List, Dict, Any
from sqlalchemy import select, func
from openai import AsyncOpenAI

from ..dependencies import get_db
from .. import models
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
                sem = asyncio.Semaphore(5)
                failures = {}

                # Launch all extraction tasks
                async def _process(doc_id: int):
                    try:
                        with next(get_db()) as db:
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
                    except Exception as exc:
                        failures[str(doc_id)] = str(exc)
                        print(f"[Trial {trial_id}] Doc {doc_id} failed: {exc}")

                tasks = [
                    asyncio.create_task(_process(doc_id))
                    for doc_id in document_ids
                ]

                # Heartbeat coroutine: update progress every N seconds
                async def _progress_heartbeat():
                    while True:
                        await asyncio.sleep(5)  # Update every 5 seconds
                        with next(get_db()) as db:
                            update_trial_progress(db, trial_id)
                        # Exit when all tasks are done
                        if all(t.done() for t in tasks):
                            break

                # Run both gather and heartbeat concurrently
                await asyncio.gather(
                    asyncio.gather(*tasks, return_exceptions=True),
                    _progress_heartbeat(),
                )

            # Finalize state at end (update status, final progress, failures)
            with next(get_db()) as db:
                trial: models.Trial = db.get(models.Trial, trial_id)
                update_trial_progress(db, trial_id)  # Will set ETA to 0 if done
                trial.finished_at = dt.datetime.now(dt.UTC)
                total = len(trial.document_ids or [])
                done = db.scalar(
                    select(func.count())
                    .select_from(models.TrialResult)
                    .where(models.TrialResult.trial_id == trial_id)
                )
                if done == total and not failures:
                    trial.status = models.TrialStatus.COMPLETED
                    # Always include failures and eta_seconds
                    trial.meta = (trial.meta or {}) | {"failures": {}, "eta_seconds": 0}
                else:
                    trial.status = models.TrialStatus.FAILED
                    trial.meta = (trial.meta or {}) | {
                        "failures": failures,
                        "eta_seconds": 0,
                    }
                db.commit()

        asyncio.run(_run())
