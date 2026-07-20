# backend/src/routers/v1/endpoints/trials.py
"""Trial endpoints for projects."""

import csv
import datetime
import io
import json
import logging
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import String, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, defer, noload, selectinload

from .... import models, schemas
from ....core.config import settings
from ....core.security import (
    admin_has_global_project_access,
    can_access_project,
    get_current_user,
)
from ....dependencies import get_db, get_file
from ....middleware.error_handlers import internal_error_message
from ....utils.audit import record_audit
from ....utils.csv_safety import SafeDictCsvWriter
from ....utils.deletion import cascade_delete_trials
from ....utils.enums import AuditAction, TrialResultStatus
from ....utils.helpers import flatten_dict, trial_filename_slug
from ....utils.streaming_zip import iter_zip
from ....utils.url_safety import (
    UnsafeEndpointError,
    enforce_endpoint_allowlist,
    validate_user_endpoint,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _broadcast_trial_event(trial_db: models.Trial, event: str = "created") -> None:
    """Best-effort WebSocket broadcast for an API-side trial state change.

    The Celery extraction task emits progress/terminal updates on its own
    heartbeat, but state changes made directly by the API — creation and
    cancellation — happen outside that loop. Without these events, other
    clients' ActivityBell/trials table don't learn about a brand-new trial
    until the first heartbeat lands, and a PENDING trial cancelled before its
    worker starts never gets a terminal update at all (stuck spinner).

    Mirrors the payload shape used by ``celery/info_extraction.py`` so the
    frontend merge logic treats it identically. Best-effort: if Redis is down,
    the trial still runs — the frontend just won't see the event.
    """
    try:
        from ....utils.redis_broadcast import publish_trial_update

        publish_trial_update(
            {
                "type": "trial_update",
                "trial_id": trial_db.id,
                "project_id": trial_db.project_id,
                "status": trial_db.status.value
                if hasattr(trial_db.status, "value")
                else str(trial_db.status),
                "docs_done": trial_db.docs_done,
                "documents_count": len(trial_db.document_ids)
                if trial_db.document_ids
                else 0,
                "progress": float(trial_db.progress) if trial_db.progress else 0,
                "name": trial_db.name,
                "project_trial_number": trial_db.project_trial_number,
                "started_at": trial_db.started_at.isoformat()
                if trial_db.started_at
                else None,
                "finished_at": trial_db.finished_at.isoformat()
                if trial_db.finished_at
                else None,
                "meta": trial_db.meta,
                "event": event,
            }
        )
    except Exception as e:
        logger.debug("Trial %s broadcast failed: %s", event, e)


def _to_int(value) -> int:
    """Coerce a JSON-decoded numeric value to int, tolerating None/strings."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def check_project_access(
    project_id: int, current_user: models.User, db: Session, permission: str = "read"
) -> models.Project:
    """Check if user has access to project."""
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Admin has full access only when cross-user project access is enabled
    if admin_has_global_project_access(current_user):
        return project

    # Owner has full access
    if project.owner_id == current_user.id:
        return project

    raise HTTPException(
        status_code=403, detail=f"Not authorized to {permission} this project"
    )


@router.post("", response_model=schemas.Trial)
def create_trial(
    project_id: int,
    trial: schemas.TrialCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Trial:
    # 1. Project, schema, prompt existence & authorization checks
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403, detail="Not authorized to create trials for this project"
        )

    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.id == trial.schema_id,
            models.Schema.project_id == project_id,
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    prompt: models.Prompt | None = db.execute(
        select(models.Prompt).where(
            models.Prompt.id == trial.prompt_id,
            models.Prompt.project_id == project_id,
        )
    ).scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # 2. Decide document IDs to use: either direct list, or from document set
    document_ids: list[int] = []

    if trial.document_set_id is not None:
        # Document set mode
        document_set: models.DocumentSet | None = db.execute(
            select(models.DocumentSet).where(
                (models.DocumentSet.id == trial.document_set_id)
                & (models.DocumentSet.project_id == project_id)
            )
        ).scalar_one_or_none()
        if not document_set:
            raise HTTPException(
                status_code=404, detail="Document set not found in this project"
            )
        # Fetch doc IDs from the set without materializing full Document rows
        # (the relationship would load 100k ORM objects incl. the text column).
        document_ids = list(
            db.execute(
                select(models.Document.id).where(
                    models.Document.document_sets.any(
                        models.DocumentSet.id == trial.document_set_id
                    )
                )
            )
            .scalars()
            .all()
        )
        if not document_ids:
            raise HTTPException(status_code=400, detail="Document set is empty")
    elif trial.document_ids:
        # Explicit document IDs
        document_ids = trial.document_ids
        # Verify all requested documents belong to this project. Done in SQL to
        # avoid loading every project document ID + an O(n²) membership scan.
        found_ids = set(
            db.execute(
                select(models.Document.id).where(
                    models.Document.id.in_(document_ids),
                    models.Document.project_id == project_id,
                )
            )
            .scalars()
            .all()
        )
        missing_ids = [doc_id for doc_id in document_ids if doc_id not in found_ids]
        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Document(s) with id(s) {missing_ids} not found in project {project_id}",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Either document_ids or document_set_id must be provided",
        )

    # Dedupe (order-preserving): a duplicated id would inflate the trial's
    # total while results are unique per (trial, document) — done == total
    # would then be unreachable and the trial could never COMPLETE.
    document_ids = list(dict.fromkeys(document_ids))

    # 3. Use default config values if not set
    llm_model = trial.llm_model or settings.OPENAI_API_MODEL
    api_key = trial.api_key or settings.OPENAI_API_KEY
    base_url = trial.base_url or settings.OPENAI_API_BASE

    if llm_model is None or api_key is None or base_url is None:
        raise HTTPException(status_code=400, detail="LLM configuration is incomplete")

    # Validate the user-supplied endpoint against the SSRF policy (blocks cloud
    # metadata hosts / non-http schemes). The extraction clients also disable
    # redirect-following, but rejecting at submission time gives a clean 400
    # instead of a per-document failure and prevents storing a blocked URL.
    try:
        validate_user_endpoint(base_url)
        enforce_endpoint_allowlist(base_url, settings.ALLOWED_LLM_ENDPOINTS)
    except UnsafeEndpointError:
        raise HTTPException(
            status_code=400, detail="The provided LLM endpoint URL is not allowed."
        )

    # Only admins may run extraction synchronously in the request thread
    # (bypass_celery). It blocks a FastAPI worker for the whole trial and,
    # since the caller also supplies base_url/api_key, makes the server issue
    # synchronous requests to a user-chosen URL (SSRF). Non-admins must go
    # through Celery. Mirrors the preprocessing router's guard. Checked before
    # any DB writes so a 403 doesn't leave an orphaned PROCESSING row behind.
    if trial.bypass_celery and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins may set bypass_celery")

    # With Celery disabled there is no worker, no queue, and no sweeper — a
    # non-bypass trial could only ever fail at dispatch. Refuse it up front
    # with an explicit reason instead of committing a trial row that
    # immediately dies with an opaque "could not queue" error.
    if settings.DISABLE_CELERY and not trial.bypass_celery:
        raise HTTPException(
            status_code=503,
            detail="Background processing is disabled on this server "
            "(DISABLE_CELERY). Enable Celery, or run the trial with "
            "bypass_celery (admins only).",
        )

    # 4. Create trial object
    # Per-project sequence number (MAX+1) for the "Trial #N" display fallback.
    # Computed before the insert so the unique constraint
    # (uq_trials_project_number) can't be violated by stale state. Two
    # concurrent create calls in the same project could still race for the same
    # number; the second commit then fails on the unique constraint. That's a
    # rare edge case (trials are user-initiated, not a high-frequency path) and
    # is preferable to renumber-on-delete or global ids; if it ever bites, wrap
    # the commit in a retry-on-IntegrityError loop.
    next_trial_number = (
        db.execute(
            select(func.coalesce(func.max(models.Trial.project_trial_number), 0)).where(
                models.Trial.project_id == project_id
            )
        ).scalar_one()
        + 1
    )

    trial_db = models.Trial(
        name=trial.name,
        description=trial.description,
        project_trial_number=next_trial_number,
        schema_id=trial.schema_id,
        prompt_id=trial.prompt_id,
        project_id=project_id,
        llm_model=llm_model,
        api_key=api_key,
        base_url=base_url,
        document_ids=document_ids,
        document_set_id=trial.document_set_id
        if trial.document_set_id is not None
        else None,
        bypass_celery=trial.bypass_celery,
        advanced_options=trial.advanced_options or {},
        # Freeze the schema + prompt so the trial record stays accurate even
        # if the source is edited (or deleted) later.
        schema_snapshot={
            "schema_name": schema.schema_name,
            "schema_definition": schema.schema_definition,
        },
        prompt_snapshot={
            "name": prompt.name,
            "description": prompt.description,
            "system_prompt": prompt.system_prompt,
            "user_prompt": prompt.user_prompt,
        },
    )

    # 5. Kick-off extraction ----------------------------------------------------
    now = datetime.datetime.now(datetime.UTC)
    if trial.bypass_celery:
        # Synchronous debug path runs inline immediately below, so it starts now.
        trial_db.status = models.TrialStatus.PROCESSING
        trial_db.started_at = now
    else:
        # Celery path: stay PENDING until a worker actually picks the task up
        # (mark_trial_started in task_signals.py flips it to PROCESSING and sets
        # started_at). This keeps a trial that is merely waiting in the queue out
        # of the orphan sweeper's "PROCESSING + stale updated_at" net — otherwise
        # a trial queued behind busy workers for >10 min would be wrongly marked
        # FAILED before it ever ran. started_at is left NULL so the ETA doesn't
        # count queue-wait time.
        trial_db.status = models.TrialStatus.PENDING
    trial_db.progress = 0.0
    db.add(trial_db)
    db.commit()
    db.refresh(trial_db)

    # Notify WS clients immediately so the new trial appears in the ActivityBell
    # and trials table without waiting for the first Celery heartbeat.
    _broadcast_trial_event(trial_db)

    # Accountability: record the trial creation now; the PHI-egress audit
    # (LLM_EXTRACTION_CALL) is deferred until the work is actually initiated —
    # after a successful Celery dispatch, or just before the synchronous loop —
    # so a failed dispatch never leaves an audit row claiming egress that never
    # happened.
    from urllib.parse import urlparse

    record_audit(
        AuditAction.CREATE,
        actor=current_user,
        resource_type="trial",
        resource_id=trial_db.id,
        project_id=project_id,
    )

    def _record_egress(mode: str) -> None:
        record_audit(
            AuditAction.LLM_EXTRACTION_CALL,
            actor=current_user,
            resource_type="trial",
            resource_id=trial_db.id,
            project_id=project_id,
            detail={
                "endpoint_host": urlparse(base_url).hostname,
                "model": llm_model,
                "document_count": len(document_ids),
                "mode": mode,
            },
        )

    if trial.bypass_celery:
        # synchronous (debug)
        _record_egress("sync")
        import threading

        from ....db.session import db_session
        from ....utils.info_extraction import (
            extract_info_single_doc,
            update_trial_progress,
        )

        # Heartbeat for the synchronous path. The Celery path bumps
        # `updated_at` every few seconds; here progress only advances after
        # each *document*, and a single LLM call (LLM_REQUEST_TIMEOUT_SECONDS,
        # doubled on the length-retry) can outlast ORPHAN_STALE_SECONDS — the
        # orphan sweeper would false-fail a live trial mid-call. A background
        # tick keeps `updated_at` fresh so the sweeper's staleness contract
        # holds for bypass trials too (and a dead web process stops ticking,
        # so genuinely orphaned bypass trials still get swept).
        stop_heartbeat = threading.Event()

        def _sync_heartbeat(trial_id: int) -> None:
            while not stop_heartbeat.wait(15):
                try:
                    with db_session() as hb_db:
                        hb_trial = hb_db.get(models.Trial, trial_id)
                        if (
                            not hb_trial
                            or hb_trial.status != models.TrialStatus.PROCESSING
                        ):
                            return
                        hb_trial.updated_at = datetime.datetime.now(datetime.UTC)
                        hb_db.commit()
                except Exception:  # noqa: BLE001 — keep ticking on transient DB errors
                    logger.debug("sync trial heartbeat tick failed", exc_info=True)

        heartbeat = threading.Thread(
            target=_sync_heartbeat, args=(trial_db.id,), daemon=True
        )
        heartbeat.start()

        try:
            for doc_id in document_ids:
                extract_info_single_doc(
                    db_session=db,
                    trial_id=trial_db.id,
                    document_id=doc_id,
                    llm_model=llm_model,
                    api_key=api_key,
                    base_url=base_url,
                    schema_id=trial.schema_id,
                    prompt_id=trial.prompt_id,
                    project_id=project_id,
                    advanced_options=trial_db.advanced_options,
                )
                update_trial_progress(db, trial_db.id)

            trial_db.status = models.TrialStatus.COMPLETED
            trial_db.finished_at = datetime.datetime.now(datetime.UTC)
            # Scrub phantom sweeper/reclaim failure markers: if the sweeper (or
            # a worker-startup reclaim) wrongly declared this live trial dead
            # mid-run, the marker would otherwise survive the COMPLETED commit
            # as a permanent "has failures" flag.
            failures = dict((trial_db.meta or {}).get("failures") or {})
            had_sweeper = failures.pop("_sweeper", None) is not None
            had_restart = failures.pop("_restart", None) is not None
            if had_sweeper or had_restart:
                meta = dict(trial_db.meta or {})
                if failures:
                    meta["failures"] = failures
                else:
                    meta.pop("failures", None)
                trial_db.meta = meta
            db.commit()
        except Exception:
            # Without this the trial stays stuck in PROCESSING forever after a
            # synchronous extraction failure (bad API key, network error, …).
            db.rollback()
            trial_db = db.get(models.Trial, trial_db.id)
            if trial_db and trial_db.status not in (
                models.TrialStatus.COMPLETED,
                models.TrialStatus.FAILED,
                models.TrialStatus.CANCELLED,
            ):
                trial_db.status = models.TrialStatus.FAILED
                trial_db.finished_at = datetime.datetime.now(datetime.UTC)
                trial_db.meta = (trial_db.meta or {}) | {
                    "failures": {"_sync": "synchronous extraction raised an exception"},
                    "eta_seconds": 0,
                }
                db.commit()
            raise
        finally:
            stop_heartbeat.set()
    else:
        # The api_key is NOT passed through the broker: it is stored encrypted
        # on the Trial row (api_key_encrypted) and decrypted inside the task.
        # Passing it as a Celery arg would serialize the plaintext key into
        # Redis, exposing it via `celery inspect` / Flower.
        try:
            from ....celery.info_extraction import extract_info_celery

            extract_info_celery.delay(
                trial_id=trial_db.id,
                document_ids=document_ids,
                llm_model=llm_model,
                base_url=base_url,
                schema_id=trial.schema_id,
                prompt_id=trial.prompt_id,
                project_id=project_id,
                advanced_options=trial_db.advanced_options,
            )
        except Exception as e:
            # Dispatch failed (broker unreachable / Celery disabled). The trial
            # was committed PENDING; without this it would sit PENDING forever
            # (the sweeper only reaps PROCESSING trials, and PENDING is exactly
            # the state we use to keep queued trials out of the sweeper). Mark it
            # FAILED with a correlated error id so the user sees it and can retry.
            db.rollback()
            trial_db = db.get(models.Trial, trial_db.id)
            if trial_db and trial_db.status not in (
                models.TrialStatus.COMPLETED,
                models.TrialStatus.FAILED,
                models.TrialStatus.CANCELLED,
            ):
                trial_db.status = models.TrialStatus.FAILED
                trial_db.finished_at = datetime.datetime.now(datetime.UTC)
                trial_db.meta = (trial_db.meta or {}) | {
                    "failures": {
                        "_dispatch": internal_error_message(
                            e, actor=current_user, prefix="Failed to queue trial"
                        )
                    },
                    "eta_seconds": 0,
                }
                db.commit()
            logger.error(
                "Failed to dispatch trial %s: %s",
                trial_db.id if trial_db else "?",
                e,
                exc_info=True,
            )
            raise HTTPException(
                status_code=503,
                detail="Could not queue trial for background processing. "
                "Please try again later.",
            )

        # Dispatch succeeded — now record the PHI egress this trial represents.
        _record_egress("celery")

    return schemas.Trial.model_validate(trial_db)


@router.post("/{trial_id}/retry", response_model=schemas.Trial)
def retry_trial(
    project_id: int,
    trial_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Trial:
    """Re-run an existing trial as a new trial, preserving its full config.

    Cloning server-side (rather than rebuilding the payload on the client) keeps
    the custom endpoint ``base_url`` and its encrypted ``api_key`` — which are
    never returned in API responses — along with the document set, name, and
    description. Reuses ``create_trial`` for all validation and dispatch.
    """
    source: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.id == trial_id,
            models.Trial.project_id == project_id,
        )
    ).scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Trial not found")

    # Re-run against the same source of documents the original used: the set (so
    # current membership is picked up) if it was set-based, otherwise the exact
    # id list. TrialCreate requires exactly one of the two.
    uses_set = source.document_set_id is not None
    payload = schemas.TrialCreate(
        name=source.name,
        description=source.description,
        schema_id=source.schema_id,
        prompt_id=source.prompt_id,
        document_ids=None if uses_set else (source.document_ids or []),
        document_set_id=source.document_set_id if uses_set else None,
        llm_model=source.llm_model,
        api_key=source.api_key,  # decrypted via the model property
        base_url=source.base_url,
        bypass_celery=source.bypass_celery,
        advanced_options=source.advanced_options or {},
    )
    return create_trial(
        project_id=project_id, trial=payload, current_user=current_user, db=db
    )


@router.get("", response_model=schemas.PaginatedTrials)
def get_trials(
    project_id: Annotated[int, Path()],
    # --- filters ---
    search: Annotated[
        str | None, Query(description="Search name/description or ID")
    ] = None,
    status: Annotated[
        str | None, Query(description="pending|processing|completed|failed|cancelled")
    ] = None,
    schema_id: Annotated[int | None, Query()] = None,
    prompt_id: Annotated[int | None, Query()] = None,
    document_set_id: Annotated[
        int | None, Query(description="Filter trials run against a document set")
    ] = None,
    llm_model: Annotated[str | None, Query()] = None,
    has_failures: Annotated[
        bool | None, Query(description="true/false; meta.failures length > 0")
    ] = None,
    date_from: Annotated[
        datetime.datetime | None,
        Query(description="ISO datetime lower bound (inclusive)"),
    ] = None,
    date_to: Annotated[
        datetime.datetime | None,
        Query(description="ISO datetime upper bound (exclusive)"),
    ] = None,
    # --- pagination ---
    limit: Annotated[int, Query(ge=1, le=500)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PaginatedTrials:
    check_project_access(project_id, current_user, db, "read")

    T = models.Trial
    TR = models.TrialResult

    base = select(T).where(T.project_id == project_id)

    # --- apply filters ---
    if status:
        base = base.where(T.status == status)

    if schema_id is not None:
        base = base.where(T.schema_id == schema_id)

    if prompt_id is not None:
        base = base.where(T.prompt_id == prompt_id)

    if document_set_id is not None:
        base = base.where(T.document_set_id == document_set_id)

    if llm_model:
        base = base.where(T.llm_model == llm_model)

    if date_from is not None:
        base = base.where(T.created_at >= date_from)
    if date_to is not None:
        base = base.where(T.created_at < date_to)

    if search:
        try:
            search_id = int(search)
        except ValueError:
            search_id = None
        pattern = f"%{search}%"
        conds = [
            T.name.ilike(pattern),
            T.description.ilike(pattern),
        ]
        if search_id is not None:
            conds.append(T.id == search_id)
        else:
            conds.append(T.id.cast(String).ilike(pattern))
        base = base.where(or_(*conds))

    page_options = (
        noload(T.results),
        selectinload(T.prompt),
        selectinload(T.document_set),
    )

    if has_failures is not None:
        # ``meta.failures`` is JSON evaluated in Python, so the filter must
        # run over the full candidate set BEFORE limit/offset — post-filtering
        # a sliced page drops items and desyncs ``total`` from the pages.
        # Load only (id, meta) to avoid hydrating schema/prompt snapshots,
        # advanced_options, document_ids, etc. for every candidate row.
        id_meta_rows = db.execute(
            base.with_only_columns(T.id, T.meta).order_by(T.created_at.desc())
        ).all()
        matching_ids: list[int] = []
        for _id, _meta in id_meta_rows:
            _has = False
            if isinstance(_meta, dict) and isinstance(_meta.get("failures"), dict):
                _has = len(_meta["failures"]) > 0
            if (has_failures is True and _has) or (has_failures is False and not _has):
                matching_ids.append(_id)
        total = len(matching_ids)

        page_ids = matching_ids[offset : offset + limit]
        page_trials: list[models.Trial] = []
        if page_ids:
            rank = {tid: i for i, tid in enumerate(page_ids)}
            page_trials = sorted(
                db.execute(select(T).where(T.id.in_(page_ids)).options(*page_options))
                .scalars()
                .all(),
                key=lambda t: rank[t.id],
            )
    else:
        total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
        page_q = (
            base.order_by(T.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(*page_options)
        )
        page_trials = list(db.execute(page_q).scalars().all())

    if not page_trials:
        return schemas.PaginatedTrials(items=[], total=total)

    # --- aggregates (counts and last_result_at) for *current* page ---
    trial_ids = [t.id for t in page_trials]
    counts_map: dict[int, int] = {}
    last_map: dict[int, datetime.datetime | None] = {}

    if trial_ids:
        counts_rows = db.execute(
            select(TR.trial_id, func.count(TR.id).label("cnt"))
            .where(TR.trial_id.in_(trial_ids))
            .group_by(TR.trial_id)
        ).all()
        counts_map = {tid: cnt for (tid, cnt) in counts_rows}

        last_rows = db.execute(
            select(TR.trial_id, func.max(TR.created_at).label("last_at"))
            .where(TR.trial_id.in_(trial_ids))
            .group_by(TR.trial_id)
        ).all()
        last_map = {tid: last_at for (tid, last_at) in last_rows}

    # attach computed attributes for TrialSummary
    for t in page_trials:
        try:
            docs_count = len(t.document_ids) if t.document_ids else 0
        except Exception:
            docs_count = 0

        failures = None
        has_fail = None
        error_count = None
        if isinstance(t.meta, dict) and isinstance(t.meta.get("failures"), dict):
            failures = t.meta["failures"]
            error_count = len(failures)
            has_fail = error_count > 0

        setattr(t, "documents_count", docs_count)
        setattr(t, "results_count", counts_map.get(t.id, 0))
        setattr(t, "last_result_at", last_map.get(t.id))
        setattr(t, "error_count", error_count)
        setattr(t, "has_failures", has_fail)

    return schemas.PaginatedTrials(
        items=[schemas.TrialSummary.model_validate(t) for t in page_trials],
        total=total,
    )


@router.get("/{trial_id}", response_model=schemas.Trial)
def get_trial(
    project_id: int,
    trial_id: int,
    include_results: Annotated[
        bool,
        Query(
            description="Embed all results (default false). Fetch pages via /results."
        ),
    ] = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Trial:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's trials"
        )

    # noload keeps serialization from lazy-loading every result anyway when
    # include_results is false — previously the flag only skipped the explicit
    # query while schemas.Trial.model_validate still hydrated the relationship.
    trial: models.Trial | None = db.execute(
        select(models.Trial)
        .where(models.Trial.project_id == project_id, models.Trial.id == trial_id)
        .options(noload(models.Trial.results))
    ).scalar_one_or_none()

    if trial and include_results:
        trial.results = cast(
            list[models.TrialResult],
            (
                db.execute(
                    select(models.TrialResult).where(
                        models.TrialResult.trial_id == trial_id
                    )
                )
                .scalars()
                .all()
            ),
        )

    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return schemas.Trial.model_validate(trial)


@router.get("/{trial_id}/results", response_model=schemas.PaginatedTrialResults)
def list_trial_results(
    project_id: Annotated[int, Path()],
    trial_id: Annotated[int, Path()],
    search: Annotated[
        str | None, Query(description="Search document name / original file name")
    ] = None,
    status: Annotated[
        str | None,
        Query(
            description="success|failed|incomplete|invalid_json|schema_invalid|refused|provider_error"
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PaginatedTrialResults:
    """Paginated list of a trial's results, with document names joined server-side.

    Replaces the load-all + N+1 pattern of embedding every result in `GET /{trial_id}`.
    """
    check_project_access(project_id, current_user, db, "read")

    # Verify the trial exists in this project (404 otherwise).
    trial = db.execute(
        select(models.Trial.id).where(
            models.Trial.project_id == project_id, models.Trial.id == trial_id
        )
    ).scalar_one_or_none()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    TR = models.TrialResult
    Doc = models.Document

    base = select(TR).where(TR.trial_id == trial_id)

    # --- status filter ---
    if status:
        try:
            status_enum = TrialResultStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid status filter: {status}"
            )
        base = base.where(TR.status == status_enum)

    # --- search filter (document name or original file name) ---
    if search:
        pattern = f"%{search}%"
        base = base.join(Doc, Doc.id == TR.document_id).outerjoin(
            models.File, models.File.id == Doc.original_file_id
        )
        base = base.where(
            or_(
                Doc.document_name.ilike(pattern),
                models.File.file_name.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    page_q = (
        base.order_by(TR.created_at.asc())
        .limit(limit)
        .offset(offset)
        .options(
            selectinload(TR.document).joinedload(Doc.original_file),
        )
    )
    page_results: list[models.TrialResult] = list(db.execute(page_q).scalars().all())

    items: list[schemas.TrialResultItem] = []
    for r in page_results:
        item = schemas.TrialResultItem.model_validate(r)
        doc = r.document
        item.document_name = doc.document_name if doc is not None else None
        item.original_file_name = (
            doc.original_file.file_name
            if doc is not None and doc.original_file is not None
            else None
        )
        items.append(item)

    # Aggregate token usage across ALL results for this trial (for the meta
    # header). Extract just the `usage` sub-object DB-side (JSON path works on
    # both PostgreSQL and SQLite) so the full additional_content — raw LLM
    # output, reasoning traces — is never hydrated per page. Summed in Python
    # to stay lenient about junk/missing values.
    usage_rows = db.execute(
        select(TR.additional_content["usage"]).where(TR.trial_id == trial_id)
    ).all()
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for (usage,) in usage_rows:
        if isinstance(usage, str):
            # Some dialect/driver combinations return the extracted JSON as text.
            try:
                usage = json.loads(usage)
            except ValueError:
                continue
        if not isinstance(usage, dict):
            continue
        total_usage["prompt_tokens"] += _to_int(usage.get("prompt_tokens"))
        total_usage["completion_tokens"] += _to_int(usage.get("completion_tokens"))
        total_usage["total_tokens"] += _to_int(usage.get("total_tokens"))

    # Audit opening a trial's results (viewing extracted PHI). Only the first
    # page (offset 0) is recorded so paging through results doesn't flood the
    # trail; the `total` gives the extent of what was viewed.
    if offset == 0:
        record_audit(
            AuditAction.TRIAL_RESULT_VIEW,
            actor=current_user,
            resource_type="trial",
            resource_id=trial_id,
            project_id=project_id,
            detail={"total_results": total},
        )

    return schemas.PaginatedTrialResults(
        items=items, total=total, total_usage=total_usage
    )


@router.patch("/{trial_id}", response_model=schemas.Trial)
def update_trial(
    project_id: int,
    trial_id: int,
    trial_update: schemas.TrialUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403, detail="Not authorized to update trials for this project"
        )

    trial = db.execute(
        select(models.Trial).where(
            models.Trial.project_id == project_id, models.Trial.id == trial_id
        )
    ).scalar_one_or_none()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    updated = False
    if trial_update.name is not None:
        trial.name = trial_update.name
        updated = True
    if trial_update.description is not None:
        trial.description = trial_update.description
        updated = True

    if not updated:
        raise HTTPException(status_code=400, detail="No updatable fields provided")

    db.commit()
    db.refresh(trial)
    record_audit(
        AuditAction.UPDATE,
        actor=current_user,
        resource_type="trial",
        resource_id=trial_id,
        project_id=project_id,
    )
    return schemas.Trial.model_validate(trial)


@router.post("/{trial_id}/cancel", response_model=schemas.Trial)
def cancel_trial(
    project_id: int,
    trial_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    check_project_access(project_id, current_user, db)
    trial = db.get(models.Trial, trial_id)
    if not trial or trial.project_id != project_id:
        raise HTTPException(status_code=404, detail="Trial not found")
    if trial.is_cancelled or trial.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail="Trial cannot be cancelled")

    trial.is_cancelled = True
    trial.status = models.TrialStatus.CANCELLED
    db.commit()
    db.refresh(trial)
    # A PENDING trial cancelled before its worker starts never gets a
    # terminal heartbeat, so tell other clients directly.
    _broadcast_trial_event(trial, event="cancelled")
    record_audit(
        AuditAction.CANCEL,
        actor=current_user,
        resource_type="trial",
        resource_id=trial_id,
        project_id=project_id,
        detail={"rollback_on_cancel": trial.rollback_on_cancel},
    )
    return schemas.Trial.model_validate(trial)


@router.delete("/{trial_id}", response_model=schemas.Trial)
def delete_trial(
    project_id: int,
    trial_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Trial:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403, detail="Not authorized to delete trials for this project"
        )

    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.project_id == project_id, models.Trial.id == trial_id
        )
    ).scalar_one_or_none()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    # Deleting a running trial doesn't stop its worker: the task keeps
    # calling the LLM and writing results against a vanished row. Require
    # cancellation (which the task observes) before deletion.
    if trial.status in (models.TrialStatus.PENDING, models.TrialStatus.PROCESSING):
        raise HTTPException(
            status_code=409,
            detail="Trial is still running. Cancel it before deleting.",
        )

    trial_data = schemas.Trial.model_validate(trial)

    try:
        counts = cascade_delete_trials(db, [trial_id])
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Database error deleting trial %s: %s", trial_id, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Database error during deletion. See server logs for details.",
        )

    record_audit(
        AuditAction.DELETE,
        actor=current_user,
        resource_type="trial",
        resource_id=trial_id,
        project_id=project_id,
        detail={
            "results_deleted": counts["results"],
            "evaluations_deleted": counts["evaluations"],
        },
    )
    return trial_data


@router.get("/{trial_id}/download", response_class=Response)
def download_trial_results(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    trial_id: int,
    format: str = Query("json", enum=["json", "csv"]),
    include_content: bool = Query(True),
    current_user: "models.User" = Depends(get_current_user),
) -> Response:
    """Download trial results, with a separate metadata.json for trial/prompt/schema metadata."""

    def filter_sensitive_keys(d, blacklist=("api_key", "api_key_encrypted")):
        if not d:
            return {}
        return {k: v for k, v in d.items() if k not in blacklist}

    # --- Permissions ---
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's trials"
        )
    trial = db.execute(
        select(models.Trial).where(
            models.Trial.project_id == project_id, models.Trial.id == trial_id
        )
    ).scalar_one_or_none()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    # Prefer the user-set trial name for the download filename, falling back to
    # the project-wise "trial_N" number so it still matches the UI when unnamed.
    download_basename = f"{trial_filename_slug(trial)}_results"

    prompt = db.execute(
        select(models.Prompt).where(models.Prompt.id == trial.prompt_id)
    ).scalar_one_or_none()
    schema = db.execute(
        select(models.Schema).where(models.Schema.id == trial.schema_id)
    ).scalar_one_or_none()

    # additional_content (raw LLM output, reasoning traces — the bulk of a
    # result row) is never read by this export; defer it so a large trial
    # doesn't hydrate it all into memory.
    results = list(
        db.execute(
            select(models.TrialResult)
            .where(models.TrialResult.trial_id == trial_id)
            .options(defer(models.TrialResult.additional_content))
        )
        .scalars()
        .all()
    )
    if not results:
        raise HTTPException(status_code=404, detail="No results found for this trial")

    # Exporting a trial's extracted results (PHI leaving the system as a file).
    record_audit(
        AuditAction.EXPORT,
        actor=current_user,
        resource_type="trial",
        resource_id=trial_id,
        project_id=project_id,
        detail={
            "format": format,
            "results": len(results),
            "include_content": include_content,
        },
    )

    document_cache = {}
    file_cache = {}
    preprocessing_config_cache = {}
    all_meta_keys = set()
    all_result_keys = set()
    all_prep_keys = set()

    # Batch-load all documents (with their original file + preprocessing config)
    # in a single query instead of 3 queries per result (N+1). The text column
    # is only fetched when the export actually embeds it — without content it
    # stays deferred (never loaded; nothing below reads it in that case).
    doc_ids = [result.document_id for result in results]
    doc_options = [
        selectinload(models.Document.original_file),
        selectinload(models.Document.preprocessing_config),
    ]
    if not include_content:
        doc_options.append(defer(models.Document.text))
    docs = (
        db.execute(
            select(models.Document)
            .where(models.Document.id.in_(doc_ids))
            .options(*doc_options)
        )
        .scalars()
        .all()
    )
    for doc in docs:
        document_cache[doc.id] = doc
        if doc.original_file_id:
            # Cache the file (may be None) so it isn't re-queried per result.
            file_cache[doc.original_file_id] = doc.original_file
        if doc.preprocessing_config_id:
            # Cache the config (may be None) so it isn't re-queried per result.
            prep_conf = doc.preprocessing_config
            preprocessing_config_cache[doc.preprocessing_config_id] = prep_conf
            if prep_conf:
                all_prep_keys.update(
                    _extract_keys(filter_sensitive_keys(prep_conf.__dict__))
                )
        all_meta_keys.update(_extract_keys(doc.meta_data or {}))

    # Batch-load any preprocessed files referenced by the documents (the
    # preprocessed_file relationship isn't eager-loaded above). Without this,
    # the include_content branches below issue one SELECT per result for the
    # preprocessed file.
    preprocessed_file_ids = [
        doc.preprocessed_file_id
        for doc in docs
        if doc.preprocessed_file_id and doc.preprocessed_file_id not in file_cache
    ]
    if preprocessed_file_ids:
        for pf in (
            db.execute(
                select(models.File).where(models.File.id.in_(preprocessed_file_ids))
            )
            .scalars()
            .all()
        ):
            file_cache[pf.id] = pf

    for result in results:
        all_result_keys.update(_extract_keys(result.result or {}))

    trial_dict = filter_sensitive_keys(
        {
            k: v
            for k, v in trial.__dict__.items()
            if not k.startswith("_")
            and isinstance(v, (str, int, float, bool, dict, list, type(None)))
        }
    )
    # Prefer the frozen snapshots captured at trial creation; fall back to the
    # live schema/prompt rows for trials created before snapshots existed.
    if trial.prompt_snapshot:
        prompt_dict = filter_sensitive_keys(dict(trial.prompt_snapshot))
    else:
        prompt_dict = filter_sensitive_keys(
            {
                k: v
                for k, v in (prompt.__dict__ if prompt else {}).items()
                if not k.startswith("_")
                and isinstance(v, (str, int, float, bool, dict, list, type(None)))
            }
        )
    if trial.schema_snapshot:
        schema_dict = filter_sensitive_keys(dict(trial.schema_snapshot))
    else:
        schema_dict = filter_sensitive_keys(
            {
                k: v
                for k, v in (schema.__dict__ if schema else {}).items()
                if not k.startswith("_")
                and isinstance(v, (str, int, float, bool, dict, list, type(None)))
            }
        )

    for d in (trial_dict, prompt_dict, schema_dict):
        for key in list(d.keys()):
            if isinstance(d[key], (dict, list)):
                continue
            try:
                json.dumps(d[key])
            except Exception:
                d.pop(key)

    # --- JSON Format ---
    if format == "json":

        def _json_entries():
            """Yield (arcname, bytes) lazily so the ZIP streams and each embedded
            file's bytes are read from storage one at a time (not all buffered)."""
            metadata_json = {
                "trial": trial_dict,
                "prompt": prompt_dict,
                "schema": schema_dict,
            }
            yield (
                "metadata.json",
                json.dumps(metadata_json, indent=2, ensure_ascii=False).encode("utf-8"),
            )

            added_files = set()
            for result in results:
                document = document_cache.get(result.document_id)
                if not document:
                    continue

                file = None
                document_name = document.document_name
                if document.original_file_id:
                    file = file_cache.get(document.original_file_id)
                    if not document_name and file:
                        document_name = file.file_name

                prep_conf = None
                if document.preprocessing_config_id:
                    prep_obj = preprocessing_config_cache.get(
                        document.preprocessing_config_id
                    )
                    if prep_obj:
                        prep_conf = filter_sensitive_keys(
                            {
                                k: v
                                for k, v in prep_obj.__dict__.items()
                                if not k.startswith("_")
                                and isinstance(
                                    v, (str, int, float, bool, dict, list, type(None))
                                )
                            }
                        )

                result_data = {
                    "result": result.result,
                    "document_id": result.document_id,
                    "document_name": document_name,
                    "file_name": file.file_name if file else None,
                    "created_at": result.created_at.isoformat(),
                    "document_metadata": document.meta_data or {},
                    "preprocessing": prep_conf or {},
                }
                if include_content:
                    result_data["content"] = document.text
                    file_id = document.preprocessed_file_id or document.original_file_id
                    if file_id:
                        # Both preprocessed_file and original_file are in
                        # file_cache (batch-loaded above), so no per-result query.
                        file_to_add = file_cache.get(file_id)
                        if file_to_add and file_id not in added_files:
                            added_files.add(file_id)
                            file_content = get_file(file_to_add.file_uuid)
                            file_path = (
                                f"files/{file_to_add.file_uuid}_{file_to_add.file_name}"
                            )
                            yield (file_path, file_content)

                file_base = document_name or f"document_{result.document_id}"
                safe_base = "".join(
                    c for c in file_base if c.isalnum() or c in " ._-"
                ).rstrip()
                if not safe_base:
                    safe_base = f"document_{result.document_id}"
                json_filename = f"{safe_base}.json"
                yield (
                    json_filename,
                    json.dumps(result_data, indent=2, ensure_ascii=False).encode(
                        "utf-8"
                    ),
                )

        return StreamingResponse(
            iter_zip(_json_entries()),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{download_basename}.zip"'
            },
        )

    # --- CSV Format ---
    elif format == "csv":
        meta_keys = sorted(all_meta_keys)
        prep_keys = sorted(all_prep_keys)
        result_keys = sorted(all_result_keys)
        trial_keys = sorted(_extract_keys(trial_dict))
        prompt_keys = sorted(_extract_keys(prompt_dict))
        schema_keys = sorted(_extract_keys(schema_dict))

        base_columns = ["document_id", "document_name", "file_name", "created_at"]
        if include_content:
            base_columns.append("document_content")
        header = (
            base_columns
            + [f"meta.{k}" for k in meta_keys]
            + [f"preprocessing.{k}" for k in prep_keys]
            + [f"trial.{k}" for k in trial_keys]
            + [f"prompt.{k}" for k in prompt_keys]
            + [f"schema.{k}" for k in schema_keys]
            + [f"result.{k}" for k in result_keys]
        )

        def _iter_csv_rows():
            """Yield the CSV as encoded chunks, one row at a time.

            The whole body is never accumulated — a trial over thousands of
            documents with embedded content would otherwise buffer every
            document text in one StringIO.
            """
            buf = io.StringIO()
            writer = SafeDictCsvWriter(csv.DictWriter(buf, fieldnames=header))
            # Constant per export — flattened once, not per row.
            trial_flat = flatten_dict(trial_dict)
            prompt_flat = flatten_dict(prompt_dict)
            schema_flat = flatten_dict(schema_dict)

            def _drain() -> bytes:
                data = buf.getvalue().encode("utf-8")
                buf.seek(0)
                buf.truncate(0)
                return data

            writer.writeheader()
            yield _drain()
            for result in results:
                row = {
                    "document_id": result.document_id,
                    "document_name": "",
                    "file_name": "",
                    "created_at": result.created_at.isoformat(),
                }
                if include_content:
                    row["document_content"] = ""
                document = document_cache.get(result.document_id)
                file = None
                document_name = ""
                file_name = ""
                prep_conf = {}
                if document:
                    document_name = document.document_name
                    if document.original_file_id:
                        file = file_cache.get(document.original_file_id)
                        if not document_name and file:
                            document_name = file.file_name
                    file_name = file.file_name if file else ""
                    if include_content:
                        row["document_content"] = document.text or ""
                    if document.preprocessing_config_id:
                        prep_obj = preprocessing_config_cache.get(
                            document.preprocessing_config_id
                        )
                        if prep_obj:
                            prep_conf = filter_sensitive_keys(
                                {
                                    k: v
                                    for k, v in prep_obj.__dict__.items()
                                    if not k.startswith("_")
                                    and isinstance(
                                        v,
                                        (str, int, float, bool, dict, list, type(None)),
                                    )
                                }
                            )
                row["document_name"] = document_name or ""
                row["file_name"] = file_name or ""
                meta_flat = flatten_dict(document.meta_data if document else {})
                for k in meta_keys:
                    row[f"meta.{k}"] = meta_flat.get(k, "")
                prep_flat = flatten_dict(prep_conf)
                for k in prep_keys:
                    row[f"preprocessing.{k}"] = prep_flat.get(k, "")
                for k in trial_keys:
                    row[f"trial.{k}"] = trial_flat.get(k, "")
                for k in prompt_keys:
                    row[f"prompt.{k}"] = prompt_flat.get(k, "")
                for k in schema_keys:
                    row[f"schema.{k}"] = schema_flat.get(k, "")
                res_flat = flatten_dict(result.result)
                for k in result_keys:
                    row[f"result.{k}"] = res_flat.get(k, "")
                writer.writerow(row)
                yield _drain()

        if include_content:

            def _csv_content_entries():
                """Stream embedded source files one at a time, then the CSV.

                Each file's bytes are read from storage on demand and drained
                before the next; the CSV member itself is written chunk-wise
                (see _iter_csv_rows), so neither part is held in memory whole.
                """
                added_files = set()
                for result in results:
                    document = document_cache.get(result.document_id)
                    if not document:
                        continue
                    file_id = document.preprocessed_file_id or document.original_file_id
                    if file_id:
                        # Batch-loaded into file_cache above (no per-result query).
                        file_to_add = file_cache.get(file_id)
                        if file_to_add and file_id not in added_files:
                            added_files.add(file_id)
                            file_content = get_file(file_to_add.file_uuid)
                            file_path = (
                                f"files/{file_to_add.file_uuid}_{file_to_add.file_name}"
                            )
                            yield (file_path, file_content)
                yield ("results.csv", _iter_csv_rows())

            return StreamingResponse(
                iter_zip(_csv_content_entries()),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{download_basename}.zip"'
                },
            )
        else:
            return StreamingResponse(
                _iter_csv_rows(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{download_basename}.csv"'
                },
            )

    raise HTTPException(status_code=404, detail="No results found for this trial")


@router.post("/{trial_id}/evaluate", response_model=schemas.EvaluationSummary)
def evaluate_trial(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    trial_id: int,
    groundtruth_id: int = Query(...),
    force_recalculate: bool = Query(False),
    current_user: models.User = Depends(get_current_user),
) -> schemas.EvaluationSummary:
    """Evaluate a trial against ground truth with comprehensive error handling."""

    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403, detail="Not authorized to evaluate trials for this project"
        )

    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.project_id == project_id, models.Trial.id == trial_id
        )
    ).scalar_one_or_none()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    from ....utils.evaluation import EvaluationEngine

    engine = EvaluationEngine(db)

    try:
        validation_result = engine._validate_evaluation_prerequisites(
            trial_id, groundtruth_id
        )
        if not validation_result["valid"]:
            error_details = {
                "message": "Cannot evaluate trial due to validation errors",
                "errors": validation_result["errors"],
                "suggestions": [],
            }
            for error in validation_result["errors"]:
                if "No field mappings configured" in error:
                    error_details["suggestions"].append(
                        "Configure field mappings between your ground truth data and schema fields"
                    )
                elif "No results found" in error:
                    error_details["suggestions"].append(
                        "Ensure the trial has completed successfully and produced results"
                    )
                elif "documents have matching ground truth" in error:
                    error_details["suggestions"].append(
                        "Check that your ground truth file contains keys that match your document IDs or filenames"
                    )
            raise HTTPException(status_code=400, detail=error_details)
    except HTTPException:
        # Re-raise the structured validation error (with errors + suggestions)
        # so it reaches the client instead of being flattened by the handler below.
        raise
    except Exception as e:
        # Don't echo the internal exception string to the client — it can
        # contain DB error messages, file paths, or library internals.
        logger.warning("Evaluation validation failed for trial %s: %s", trial_id, e)
        raise HTTPException(
            status_code=400, detail="Validation failed. See server logs for details."
        )

    try:
        evaluation = engine.evaluate_trial(
            trial_id=trial_id,
            groundtruth_id=groundtruth_id,
            force_recalculate=force_recalculate,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Evaluation failed for trial %s / ground truth %s: %s",
            trial_id,
            groundtruth_id,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Evaluation failed. See server logs for details.",
        )

    # Batch-load all EvaluationMetric rows for this evaluation once and group
    # them in Python, instead of one query per field (sample errors) and one
    # per document (field details) — that was 2 queries × (fields + docs).
    all_metrics = (
        db.execute(
            select(models.EvaluationMetric).where(
                models.EvaluationMetric.evaluation_id == evaluation.id
            )
        )
        .scalars()
        .all()
    )
    metrics_by_field: dict[str, list[models.EvaluationMetric]] = {}
    metrics_by_doc: dict[int, list[models.EvaluationMetric]] = {}
    for m in all_metrics:
        metrics_by_field.setdefault(m.field_name, []).append(m)
        metrics_by_doc.setdefault(m.document_id, []).append(m)

    # Batch-load all referenced documents with original_file eager-loaded
    # (avoids db.get(Document) + lazy original_file per document).
    doc_ids = [dm["document_id"] for dm in evaluation.document_metrics]
    document_lookup: dict[int, models.Document] = {}
    if doc_ids:
        document_lookup = {
            d.id: d
            for d in db.execute(
                select(models.Document)
                .where(models.Document.id.in_(doc_ids))
                .options(selectinload(models.Document.original_file))
            )
            .scalars()
            .all()
        }

    field_summaries = []
    for field_name, metrics in evaluation.field_metrics.items():
        error_count = sum(metrics.get("error_distribution", {}).values())

        sample_errors = []
        # First 5 incorrect metrics for this field (already batch-loaded).
        incorrect = [
            m for m in metrics_by_field.get(field_name, []) if not m.is_correct
        ]
        for detail in incorrect[:5]:
            sample_errors.append(
                {
                    "document_id": detail.document_id,
                    "ground_truth": detail.ground_truth_value,
                    "predicted": detail.predicted_value,
                    "error_type": detail.error_type,
                }
            )

        field_summaries.append(
            schemas.FieldEvaluationSummary(
                field_name=field_name,
                accuracy=metrics.get("accuracy", 0),
                total_count=metrics.get("total_count", 0),
                correct_count=metrics.get("correct_count", 0),
                error_distribution=metrics.get("error_distribution", {}),
                sample_errors=sample_errors,
                error_count=error_count,
            )
        )

    document_summaries = []
    total_errors = 0
    error_documents = []

    for doc_metrics in evaluation.document_metrics:
        doc_id = doc_metrics["document_id"]

        has_error = "error" in doc_metrics
        if has_error:
            total_errors += 1
            error_documents.append(doc_id)

        document = document_lookup.get(doc_id)
        document_name = None
        if document and document.original_file:
            document_name = document.original_file.file_name

        field_details = {}
        for detail in metrics_by_doc.get(doc_id, []):
            field_details[detail.field_name] = schemas.EvaluationMetricDetail(
                document_id=doc_id,
                field_name=detail.field_name,
                ground_truth_value=detail.ground_truth_value,
                predicted_value=detail.predicted_value,
                is_correct=detail.is_correct,
                error_type=detail.error_type,
                confidence_score=detail.confidence_score,
            )

        document_summary = schemas.DocumentEvaluationDetail(
            document_id=doc_id,
            accuracy=doc_metrics.get("accuracy", 0.0),
            correct_fields=doc_metrics.get("correct_fields", 0),
            total_fields=doc_metrics.get("total_fields", 0),
            missing_fields=doc_metrics.get("missing_fields", []),
            incorrect_fields=doc_metrics.get("incorrect_fields", []),
            field_details=field_details,
            has_error=has_error,
            document_name=document_name,
        )
        if has_error:
            document_summary.error = doc_metrics["error"]
        document_summaries.append(document_summary)

    return schemas.EvaluationSummary(
        id=evaluation.id,
        trial_id=evaluation.trial_id,
        groundtruth_id=evaluation.groundtruth_id,
        overall_metrics=evaluation.metrics,
        field_summaries=field_summaries,
        document_summaries=document_summaries,
        confusion_matrices=evaluation.confusion_matrices,
        created_at=evaluation.created_at,
        total_errors=total_errors,
        error_documents=error_documents,
        warnings=getattr(engine, "last_warnings", None) or None,
    )


def _extract_keys(d, parent_key="", sep="_"):
    """Extract all keys from a nested dictionary."""
    keys = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            keys.extend(_extract_keys(v, new_key, sep=sep))
        else:
            keys.append(new_key)
    return keys
