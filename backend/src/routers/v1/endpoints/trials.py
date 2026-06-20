# backend/src/routers/v1/endpoints/trials.py
"""Trial endpoints for projects."""

import csv
import datetime
import io
import json
import zipfile
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import Response
from sqlalchemy import String, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, noload, selectinload

from .... import models, schemas
from ....core.config import settings
from ....core.security import get_current_user
from ....dependencies import get_db, get_file
from ....utils.helpers import flatten_dict

router = APIRouter()


def check_project_access(
    project_id: int, current_user: models.User, db: Session, permission: str = "read"
) -> models.Project:
    """Check if user has access to project."""
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Admin has full access
    if current_user.role == "admin":
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
    if current_user.role != "admin" and project.owner_id != current_user.id:
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
        document_ids = (
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

    # 3. Use default config values if not set
    llm_model = trial.llm_model or settings.OPENAI_API_MODEL
    api_key = trial.api_key or settings.OPENAI_API_KEY
    base_url = trial.base_url or settings.OPENAI_API_BASE

    if llm_model is None or api_key is None or base_url is None:
        raise HTTPException(status_code=400, detail="LLM configuration is incomplete")

    # 4. Create trial object
    trial_db = models.Trial(
        name=trial.name,
        description=trial.description,
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
    trial_db.status = models.TrialStatus.PROCESSING
    trial_db.started_at = datetime.datetime.now(datetime.UTC)
    trial_db.progress = 0.0
    db.add(trial_db)
    db.commit()
    db.refresh(trial_db)

    if trial.bypass_celery:
        # synchronous (debug)
        from ....utils.info_extraction import (
            extract_info_single_doc,
            update_trial_progress,
        )

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
    else:
        from ....celery.info_extraction import extract_info_celery

        extract_info_celery.delay(
            trial_id=trial_db.id,
            document_ids=document_ids,
            llm_model=llm_model,
            api_key=api_key,
            base_url=base_url,
            schema_id=trial.schema_id,
            prompt_id=trial.prompt_id,
            project_id=project_id,
            advanced_options=trial_db.advanced_options,
        )

    return schemas.Trial.model_validate(trial_db)


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
            conds.append(cast(T.id, String).ilike(pattern))
        base = base.where(or_(*conds))

    apply_python_has_failures = has_failures is not None

    total_pre = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    page_q = (
        base.order_by(T.created_at.desc())
        .limit(limit)
        .offset(offset)
        .options(
            noload(T.results),
            selectinload(T.prompt),
            selectinload(T.document_set),
        )
    )

    page_trials: list[models.Trial] = db.execute(page_q).scalars().all()
    if not page_trials:
        return schemas.PaginatedTrials(items=[], total=0 if offset == 0 else total_pre)

    # --- post-filter for has_failures if requested ---
    if apply_python_has_failures:
        filtered = []
        for t in page_trials:
            _has = None
            if isinstance(t.meta, dict) and isinstance(t.meta.get("failures"), dict):
                _has = len(t.meta["failures"]) > 0
            elif t.meta is None:
                _has = False
            if has_failures is True and _has:
                filtered.append(t)
            elif has_failures is False and not _has:
                filtered.append(t)
        page_trials = filtered

        all_ids_rows = db.execute(base.with_only_columns(T.id)).all()
        all_ids = [r[0] for r in all_ids_rows]
        if all_ids:
            all_trials = (
                db.execute(
                    select(T).where(T.id.in_(all_ids)).options(noload(T.results))
                )
                .scalars()
                .all()
            )
            total = 0
            for t in all_trials:
                _has = False
                if isinstance(t.meta, dict) and isinstance(
                    t.meta.get("failures"), dict
                ):
                    _has = len(t.meta["failures"]) > 0
                if (has_failures and _has) or (has_failures is False and not _has):
                    total += 1
        else:
            total = 0
    else:
        total = total_pre

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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Trial:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's trials"
        )

    trial: models.Trial | None = db.execute(
        select(models.Trial).where(
            models.Trial.project_id == project_id, models.Trial.id == trial_id
        )
    ).scalar_one_or_none()

    if trial:
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
    if current_user.role != "admin" and project.owner_id != current_user.id:
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
    if current_user.role != "admin" and project.owner_id != current_user.id:
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

    trial_data = schemas.Trial.model_validate(trial)

    try:
        evaluations = (
            db.execute(
                select(models.Evaluation).where(models.Evaluation.trial_id == trial_id)
            )
            .scalars()
            .all()
        )
        for evaluation in evaluations:
            db.delete(evaluation)

        results = (
            db.execute(
                select(models.TrialResult).where(
                    models.TrialResult.trial_id == trial_id
                )
            )
            .scalars()
            .all()
        )
        for result in results:
            db.delete(result)

        db.delete(trial)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Database error during deletion: {e}"
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
    if current_user.role != "admin" and project.owner_id != current_user.id:
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

    prompt = db.execute(
        select(models.Prompt).where(models.Prompt.id == trial.prompt_id)
    ).scalar_one_or_none()
    schema = db.execute(
        select(models.Schema).where(models.Schema.id == trial.schema_id)
    ).scalar_one_or_none()

    results = list(
        db.execute(
            select(models.TrialResult).where(models.TrialResult.trial_id == trial_id)
        )
        .scalars()
        .all()
    )
    if not results:
        raise HTTPException(status_code=404, detail="No results found for this trial")

    document_cache = {}
    file_cache = {}
    preprocessing_config_cache = {}
    all_meta_keys = set()
    all_result_keys = set()
    all_prep_keys = set()

    for result in results:
        doc = db.execute(
            select(models.Document).where(models.Document.id == result.document_id)
        ).scalar_one_or_none()
        document_cache[result.document_id] = doc
        if doc:
            if doc.original_file_id and doc.original_file_id not in file_cache:
                file_cache[doc.original_file_id] = db.execute(
                    select(models.File).where(models.File.id == doc.original_file_id)
                ).scalar_one_or_none()
            prep_conf = None
            if doc.preprocessing_config_id:
                prep_conf = db.execute(
                    select(models.PreprocessingConfiguration).where(
                        models.PreprocessingConfiguration.id
                        == doc.preprocessing_config_id
                    )
                ).scalar_one_or_none()
                if prep_conf:
                    preprocessing_config_cache[doc.preprocessing_config_id] = prep_conf
                    all_prep_keys.update(
                        _extract_keys(filter_sensitive_keys(prep_conf.__dict__))
                    )
            all_meta_keys.update(_extract_keys(doc.meta_data or {}))
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
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            metadata_json = {
                "trial": trial_dict,
                "prompt": prompt_dict,
                "schema": schema_dict,
            }
            zipf.writestr(
                "metadata.json", json.dumps(metadata_json, indent=2, ensure_ascii=False)
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
                        file_to_add = db.execute(
                            select(models.File).where(models.File.id == file_id)
                        ).scalar_one_or_none()
                        if file_to_add and file_id not in added_files:
                            added_files.add(file_id)
                            file_content = get_file(file_to_add.file_uuid)
                            file_path = (
                                f"files/{file_to_add.file_uuid}_{file_to_add.file_name}"
                            )
                            zipf.writestr(file_path, file_content)

                file_base = document_name or f"document_{result.document_id}"
                safe_base = "".join(
                    c for c in file_base if c.isalnum() or c in " ._-"
                ).rstrip()
                if not safe_base:
                    safe_base = f"document_{result.document_id}"
                json_filename = f"{safe_base}.json"
                zipf.writestr(
                    json_filename,
                    json.dumps(result_data, indent=2, ensure_ascii=False),
                )
        zip_buffer.seek(0)
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=trial_{trial_id}_results.zip"
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

        if include_content:
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipf:
                header = (
                    [
                        "document_id",
                        "document_name",
                        "file_name",
                        "created_at",
                        "document_content",
                    ]
                    + [f"meta.{k}" for k in meta_keys]
                    + [f"preprocessing.{k}" for k in prep_keys]
                    + [f"trial.{k}" for k in trial_keys]
                    + [f"prompt.{k}" for k in prompt_keys]
                    + [f"schema.{k}" for k in schema_keys]
                    + [f"result.{k}" for k in result_keys]
                )
                csv_output = io.StringIO()
                writer = csv.DictWriter(csv_output, fieldnames=header)
                writer.writeheader()
                added_files = set()
                for result in results:
                    row = {
                        "document_id": result.document_id,
                        "document_name": "",
                        "file_name": "",
                        "created_at": result.created_at.isoformat(),
                        "document_content": "",
                    }
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
                                            (
                                                str,
                                                int,
                                                float,
                                                bool,
                                                dict,
                                                list,
                                                type(None),
                                            ),
                                        )
                                    }
                                )
                        file_id = (
                            document.preprocessed_file_id or document.original_file_id
                        )
                        if file_id:
                            file_to_add = db.execute(
                                select(models.File).where(models.File.id == file_id)
                            ).scalar_one_or_none()
                            if file_to_add and file_id not in added_files:
                                added_files.add(file_id)
                                file_content = get_file(file_to_add.file_uuid)
                                file_path = f"files/{file_to_add.file_uuid}_{file_to_add.file_name}"
                                zipf.writestr(file_path, file_content)
                    row["document_name"] = document_name or ""
                    row["file_name"] = file_name or ""
                    meta_flat = flatten_dict(document.meta_data if document else {})
                    for k in meta_keys:
                        row[f"meta.{k}"] = meta_flat.get(k, "")
                    prep_flat = flatten_dict(prep_conf)
                    for k in prep_keys:
                        row[f"preprocessing.{k}"] = prep_flat.get(k, "")
                    trial_flat = flatten_dict(trial_dict)
                    for k in trial_keys:
                        row[f"trial.{k}"] = trial_flat.get(k, "")
                    prompt_flat = flatten_dict(prompt_dict)
                    for k in prompt_keys:
                        row[f"prompt.{k}"] = prompt_flat.get(k, "")
                    schema_flat = flatten_dict(schema_dict)
                    for k in schema_keys:
                        row[f"schema.{k}"] = schema_flat.get(k, "")
                    res_flat = flatten_dict(result.result)
                    for k in result_keys:
                        row[f"result.{k}"] = res_flat.get(k, "")
                    writer.writerow(row)
                zipf.writestr("results.csv", csv_output.getvalue())
            output.seek(0)
            return Response(
                content=output.getvalue(),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename=trial_{trial_id}_results.zip"
                },
            )
        else:
            output = io.StringIO()
            header = (
                ["document_id", "document_name", "file_name", "created_at"]
                + [f"meta.{k}" for k in meta_keys]
                + [f"preprocessing.{k}" for k in prep_keys]
                + [f"trial.{k}" for k in trial_keys]
                + [f"prompt.{k}" for k in prompt_keys]
                + [f"schema.{k}" for k in schema_keys]
                + [f"result.{k}" for k in result_keys]
            )
            writer = csv.DictWriter(output, fieldnames=header)
            writer.writeheader()
            for result in results:
                row = {
                    "document_id": result.document_id,
                    "document_name": "",
                    "file_name": "",
                    "created_at": result.created_at.isoformat(),
                }
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
                trial_flat = flatten_dict(trial_dict)
                for k in trial_keys:
                    row[f"trial.{k}"] = trial_flat.get(k, "")
                prompt_flat = flatten_dict(prompt_dict)
                for k in prompt_keys:
                    row[f"prompt.{k}"] = prompt_flat.get(k, "")
                schema_flat = flatten_dict(schema_dict)
                for k in schema_keys:
                    row[f"schema.{k}"] = schema_flat.get(k, "")
                res_flat = flatten_dict(result.result)
                for k in result_keys:
                    row[f"result.{k}"] = res_flat.get(k, "")
                writer.writerow(row)
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=trial_{trial_id}_results.csv"
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
    if current_user.role != "admin" and project.owner_id != current_user.id:
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
        raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")

    try:
        evaluation = engine.evaluate_trial(
            trial_id=trial_id,
            groundtruth_id=groundtruth_id,
            force_recalculate=force_recalculate,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

    field_summaries = []
    for field_name, metrics in evaluation.field_metrics.items():
        error_count = sum(metrics.get("error_distribution", {}).values())

        sample_errors = []
        error_details = (
            db.query(models.EvaluationMetric)
            .filter(
                models.EvaluationMetric.evaluation_id == evaluation.id,
                models.EvaluationMetric.field_name == field_name,
                ~models.EvaluationMetric.is_correct,
            )
            .limit(5)
            .all()
        )
        for detail in error_details:
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

        document = db.get(models.Document, doc_id)
        document_name = None
        if document and document.original_file:
            document_name = document.original_file.file_name

        field_details = {}
        details = (
            db.query(models.EvaluationMetric)
            .filter(
                models.EvaluationMetric.evaluation_id == evaluation.id,
                models.EvaluationMetric.document_id == doc_id,
            )
            .all()
        )
        for detail in details:
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
