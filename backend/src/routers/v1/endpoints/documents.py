# backend/src/routers/v1/endpoints/documents.py
"""Document and document-set endpoints for projects."""

import datetime
import logging
import urllib.parse
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, contains_eager, defer, joinedload, selectinload

from .... import models, schemas
from ....core.security import (
    admin_has_global_project_access,
    can_access_project,
    get_current_user,
)
from ....dependencies import get_db, get_file, remove_file
from ....models.project import document_set_association
from ....utils.audit import record_audit
from ....utils.deletion import (
    cascade_clear_document_references,
    compute_document_dependencies,
    trials_referencing_docs,
)
from ....utils.enums import AuditAction
from ....utils.streaming_zip import iter_zip

logger = logging.getLogger(__name__)

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

    # Admin has full access only when cross-user project access is enabled
    if admin_has_global_project_access(current_user):
        return project

    # Owner has full access
    if project.owner_id == current_user.id:
        return project

    # For non-owners, check specific permissions if needed
    raise HTTPException(
        status_code=403, detail=f"Not authorized to {permission} this project"
    )


@router.get("/document", response_model=None)  # keep None just for the test
def get_documents(
    project_id: Annotated[int, Path()],
    file_id: Annotated[
        int | None, Query(description="Filter by original file id")
    ] = None,
    file_preprocessing_task_id: Annotated[
        int | None, Query(description="Filter by file_preprocessing_task id")
    ] = None,
    config_id: Annotated[
        int | None, Query(description="Filter by preprocessing_config_id")
    ] = None,
    search: Annotated[
        str | None, Query(description="Search text and/or filename (case-insensitive)")
    ] = None,
    date_from: Annotated[
        datetime.datetime | None,
        Query(description="ISO datetime lower bound (inclusive)"),
    ] = None,
    date_to: Annotated[
        datetime.datetime | None,
        Query(description="ISO datetime upper bound (exclusive)"),
    ] = None,
    ocr_engine: Annotated[
        str | None,
        Query(
            description="Filter by OCR engine (pypdf, tesseract, mistral_ocr, llm_vision)"
        ),
    ] = None,
    document_set_id: Annotated[
        int | None, Query(description="Filter by document set membership")
    ] = None,
    sort: Annotated[
        str,
        Query(
            description="Sort order: 'created_desc' (default, newest first) or "
            "'created_asc' (oldest first — natural row/insertion order)"
        ),
    ] = "created_desc",
    limit: Annotated[int, Query(ge=1, le=500)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_archived: Annotated[
        bool | None,
        Query(description="Include archived (non-latest) document versions"),
    ] = False,
    compute_stats: Annotated[
        bool | None,
        Query(description="Compute stats (recent_count, today_count, etc.)"),
    ] = True,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PaginatedDocuments:
    check_project_access(project_id, current_user, db, "read")

    D = models.Document
    F = models.File

    # Build base SELECT with filters (no limit/offset yet)
    # Apply same filters as main query for accurate stats
    base = select(D).where(D.project_id == project_id)

    # By default, only show latest document versions (hide archived/history)
    if not include_archived:
        base = base.where(D.is_latest.is_(True))

    if file_id is not None:
        base = base.where(D.original_file_id == file_id)

    if file_preprocessing_task_id is not None:
        base = base.where(D.file_preprocessing_task_id == file_preprocessing_task_id)

    if config_id is not None:
        base = base.where(D.preprocessing_config_id == config_id)

    if date_from is not None:
        base = base.where(D.created_at >= date_from)
    if date_to is not None:
        base = base.where(D.created_at < date_to)

    # Filter by OCR engine (stored in meta_data JSON)
    if ocr_engine is not None:
        # PostgreSQL JSON operator for ocr_engine field
        base = base.where(D.meta_data["ocr_engine"].as_string() == ocr_engine)

    if document_set_id is not None:
        # Membership filter via the association table (EXISTS subquery).
        base = base.where(D.document_sets.any(models.DocumentSet.id == document_set_id))

    joined_for_search = False
    if search:
        pattern = f"%{search}%"
        # Join original_file for filename search; keep it optional if you only want text search
        base = base.join(F, F.id == D.original_file_id).where(
            or_(
                D.text.ilike(pattern),
                D.document_name.ilike(pattern),
                F.file_name.ilike(pattern),
            )
        )
        joined_for_search = True

    # total BEFORE slicing
    # Use exact count - reliable and works with all query types
    # For large tables, PostgreSQL will use index-only scans when possible
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    # Compute stats server-side using efficient COUNT queries
    recent_count = None
    today_count = None
    week_count = None
    month_count = None

    if compute_stats:
        now = datetime.datetime.now(datetime.UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - datetime.timedelta(days=7)
        month_ago = now - datetime.timedelta(days=30)

        # Build stats query with same filters as base
        stats_base = select(func.count(D.id)).where(D.project_id == project_id)
        if not include_archived:
            stats_base = stats_base.where(D.is_latest.is_(True))
        if file_id is not None:
            stats_base = stats_base.where(D.original_file_id == file_id)
        if file_preprocessing_task_id is not None:
            stats_base = stats_base.where(
                D.file_preprocessing_task_id == file_preprocessing_task_id
            )
        if config_id is not None:
            stats_base = stats_base.where(D.preprocessing_config_id == config_id)
        if ocr_engine is not None:
            stats_base = stats_base.where(
                D.meta_data["ocr_engine"].as_string() == ocr_engine
            )
        if document_set_id is not None:
            stats_base = stats_base.where(
                D.document_sets.any(models.DocumentSet.id == document_set_id)
            )

        # Today count
        today_count = db.scalar(stats_base.where(D.created_at >= today_start)) or 0

        # Week count (last 7 days)
        week_count = db.scalar(stats_base.where(D.created_at >= week_ago)) or 0

        # Month count (last 30 days)
        month_count = db.scalar(stats_base.where(D.created_at >= month_ago)) or 0

        # Recent count (alias for week_count)
        recent_count = week_count

    # Page query.
    # A stable secondary sort on the primary key is REQUIRED: rows created in the
    # same transaction (e.g. a batch-committed row-by-row CSV import) share an
    # identical `created_at` because Postgres `now()` returns the transaction
    # start time. Ordering by `created_at` alone leaves those ties in an
    # arbitrary, query-to-query order, so a document could appear on two pages
    # (and another be skipped) as the UI paginates. Tie-breaking on `id` makes
    # pagination deterministic.
    if sort == "created_asc":
        # Oldest first — for a row-by-row import this is the natural ID001→ID150
        # order (lowest id = first inserted).
        page_q = base.order_by(D.created_at.asc(), D.id.asc())
    else:
        page_q = base.order_by(D.created_at.desc(), D.id.desc())
    page_q = page_q.limit(limit).offset(offset)

    # Eager load relationships needed for the document list UI
    if joined_for_search:
        # We already joined File for search; use contains_eager to populate relationship
        page_q = page_q.options(
            contains_eager(D.original_file),
            selectinload(D.preprocessing_config),
            selectinload(D.file_preprocessing_task),
            defer(D.text),
        )
    else:
        # Always eager load to avoid N+1 queries in the UI
        page_q = page_q.options(
            joinedload(D.original_file),
            selectinload(D.preprocessing_config),
            selectinload(D.file_preprocessing_task),
            defer(D.text),
        )

    items = db.execute(page_q).scalars().all()
    return schemas.PaginatedDocuments(
        items=[schemas.DocumentListItem.model_validate(d) for d in items],
        total=total,
        recent_count=recent_count,
        today_count=today_count,
        week_count=week_count,
        month_count=month_count,
    )


@router.get("/document/{document_id}", response_model=schemas.Document)
def get_document(
    *,
    project_id: int,
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Document:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's documents"
        )

    document: models.Document | None = db.execute(
        select(models.Document).where(
            models.Document.project_id == project_id,
            models.Document.id == document_id,
        )
    ).scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    record_audit(
        AuditAction.DOCUMENT_VIEW,
        actor=current_user,
        resource_type="document",
        resource_id=document.id,
        project_id=project_id,
    )
    return schemas.Document.model_validate(document)


@router.post("/document/{document_id}/restore", response_model=schemas.Document)
def restore_document_version(
    *,
    project_id: int,
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Document:
    """Restore an archived document version as the new latest — WITHOUT reprocessing.

    Copies the archived version's extracted text (and metadata) into a fresh
    ``is_latest=True`` document, archiving whatever version was previously latest.
    No OCR/LLM work runs, so the restored content is exactly the archived
    version's content. Users can still run "Reprocess Document" afterwards.
    """
    check_project_access(project_id, current_user, db, "write")

    target: models.Document | None = db.execute(
        select(models.Document).where(
            models.Document.id == document_id,
            models.Document.project_id == project_id,
        )
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Document not found")
    if target.is_latest:
        raise HTTPException(
            status_code=400, detail="This version is already the latest."
        )

    # Current latest version(s) sharing the same versioning key (file/config/name).
    latest_docs = (
        db.execute(
            select(models.Document).where(
                models.Document.project_id == project_id,
                models.Document.original_file_id == target.original_file_id,
                models.Document.preprocessing_config_id
                == target.preprocessing_config_id,
                models.Document.document_name == target.document_name,
                models.Document.is_latest.is_(True),
            )
        )
        .scalars()
        .all()
    )

    # Determine the version-chain root (mirrors the preprocessing convention).
    if latest_docs:
        first_latest = latest_docs[0]
        version_of_root = first_latest.version_of or first_latest.id
        replaced_doc_id: int | None = first_latest.id
    else:
        version_of_root = target.version_of or target.id
        replaced_doc_id = None

    # Archive the current latest to free the is_latest uniqueness slot, capturing
    # its document-set memberships so the restored copy inherits them (a restore
    # shouldn't silently drop the document out of its groups).
    inherited_sets: dict[int, models.DocumentSet] = {}
    for doc in latest_docs:
        for ds in doc.document_sets:
            inherited_sets[ds.id] = ds
        doc.document_sets.clear()
        doc.is_latest = False
        doc.updated_at = datetime.datetime.now(datetime.UTC)
        doc.version_of = version_of_root
    db.flush()

    # Copy the archived version's content into a new latest document. The
    # preprocessed file is shared by reference — delete_document only removes a
    # preprocessed file once no document references it, so sharing is safe.
    new_meta = dict(target.meta_data or {})
    new_meta["version_of"] = version_of_root
    new_meta["restored_from_document_id"] = target.id
    if replaced_doc_id is not None:
        new_meta["replaced_document_id"] = replaced_doc_id

    restored = models.Document(
        project_id=project_id,
        original_file_id=target.original_file_id,
        file_preprocessing_task_id=target.file_preprocessing_task_id,
        preprocessing_config_id=target.preprocessing_config_id,
        text=target.text,
        document_name=target.document_name,
        meta_data=new_meta,
        preprocessed_file_id=target.preprocessed_file_id,
        is_latest=True,
        version_of=version_of_root,
    )
    if inherited_sets:
        restored.document_sets = list(inherited_sets.values())
    db.add(restored)
    db.commit()
    db.refresh(restored)

    record_audit(
        AuditAction.UPDATE,
        actor=current_user,
        resource_type="document",
        resource_id=restored.id,
        project_id=project_id,
        detail={"restored_from_document_id": target.id},
    )
    return schemas.Document.model_validate(restored)


def cleanup_empty_preprocessing_tasks(
    db: Session, file_preprocessing_task_id: int | None
) -> None:
    """Clean up FilePreprocessingTask and PreprocessingTask when they have no remaining documents.

    This function:
    1. Checks if the FilePreprocessingTask has any remaining documents
    2. If empty, deletes the FilePreprocessingTask
    3. If parent PreprocessingTask has no more FilePreprocessingTask children, deletes it too
    """
    if file_preprocessing_task_id is None:
        return

    file_task = db.get(models.FilePreprocessingTask, file_preprocessing_task_id)
    if not file_task:
        return

    # Check if there are any remaining documents for this file task
    # Existence check: multiple rows are expected → .scalars().first()
    # (scalar_one_or_none raises MultipleResultsFound on >1 row).
    remaining_docs = (
        db.execute(
            select(models.Document.id).where(
                models.Document.file_preprocessing_task_id == file_preprocessing_task_id
            )
        )
        .scalars()
        .first()
    )

    if remaining_docs is not None:
        # Still has documents, don't clean up
        return

    # No remaining documents - delete the FilePreprocessingTask
    preprocessing_task_id = file_task.preprocessing_task_id

    db.delete(file_task)
    db.flush()  # Ensure deletion is staged before checking parent

    # Check if parent PreprocessingTask has any remaining FilePreprocessingTask children
    remaining_file_tasks = (
        db.execute(
            select(models.FilePreprocessingTask.id).where(
                models.FilePreprocessingTask.preprocessing_task_id
                == preprocessing_task_id
            )
        )
        .scalars()
        .first()
    )

    if remaining_file_tasks is None:
        # No remaining file tasks - delete the parent PreprocessingTask
        preprocessing_task = db.get(models.PreprocessingTask, preprocessing_task_id)
        if preprocessing_task:
            db.delete(preprocessing_task)

    db.commit()


@router.post("/document/dependencies", response_model=schemas.DocumentDependencies)
def get_document_dependencies(
    project_id: int,
    payload: schemas.DocumentDependencyRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.DocumentDependencies:
    """Summarize what a cascade delete of the given documents would also remove.

    Used by the batch-delete confirmation to preview the impact (how many trials,
    groups, extraction results and evaluation metrics would be deleted).
    """
    check_project_access(project_id, current_user, db, "write")
    summary = compute_document_dependencies(db, project_id, payload.document_ids)
    return schemas.DocumentDependencies(**summary)


@router.delete("/document/{document_id}")
def delete_document(
    *,
    project_id: int,
    document_id: int,
    cascade: Annotated[
        bool,
        Query(
            description="Also delete the trials, groups, and evaluations that "
            "reference this document, instead of refusing when they exist."
        ),
    ] = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a specific document.

    Without ``cascade``, deletion is refused (``400``) if the document is used in
    any trial, trial result, evaluation metric, or document set. With
    ``cascade=true``, those referencing trials and groups (and their evaluations)
    are deleted first so the document can be removed.
    """
    check_project_access(project_id, current_user, db, "write")

    document = db.execute(
        select(models.Document).where(
            models.Document.id == document_id, models.Document.project_id == project_id
        )
    ).scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    cascade_counts: dict[str, int] = {}
    if cascade:
        # Delete everything that references the document so it becomes deletable:
        # whole trials (with their evaluations/results), whole groups, plus any
        # residual result/metric rows (RESTRICT FKs) tied directly to this doc.
        cascade_counts.update(
            cascade_clear_document_references(db, project_id, [document_id])
        )
        # Membership rows for any set are gone via cascade_clear_document_references;
        # refresh the ORM relationship so the later db.delete(document) is clean.
        db.expire(document, ["document_sets"])
    else:
        # --- Check for usage in any trial (document_ids is a JSON list) ---
        # Membership is checked in Python to avoid JSON operator incompatibility
        # between SQLite and PostgreSQL; only lightweight columns are loaded.
        referencing = trials_referencing_docs(db, project_id, [document_id])
        if referencing:
            trial_id, trial_name, _ = referencing[0]
            raise HTTPException(
                status_code=400,
                detail=f"Document is referenced in trial '{trial_name or trial_id}'. Remove from trial(s) first.",
            )

        # --- Check if document is used in any trial results ---
        # A document can have results across many trials; use .scalars().first()
        # (scalar_one_or_none raises MultipleResultsFound when >1 row exists).
        trial_result = (
            db.execute(
                select(models.TrialResult).where(
                    models.TrialResult.document_id == document_id
                )
            )
            .scalars()
            .first()
        )
        if trial_result:
            raise HTTPException(
                status_code=400,
                detail="Document is referenced in a trial result. Remove results/trials first.",
            )

        # --- (Optional) Check if document is used in any evaluation metric ---
        metric = (
            db.execute(
                select(models.EvaluationMetric).where(
                    models.EvaluationMetric.document_id == document_id
                )
            )
            .scalars()
            .first()
        )
        if metric:
            raise HTTPException(
                status_code=400,
                detail="Document is referenced in evaluation metrics. Remove related evaluation/trial first.",
            )

        # --- Existing check: Document sets ---
        if document.document_sets:
            raise HTTPException(
                status_code=400,
                detail=f"Document is part of {len(document.document_sets)} document sets. Remove from sets first.",
            )

    # Store file_preprocessing_task_id before deletion for cleanup
    file_preprocessing_task_id = document.file_preprocessing_task_id

    # --- Preprocessed file deletion logic as before ---
    orphaned_blob_uuid: str | None = None
    if document.preprocessed_file_id:
        other_docs_using_file = (
            db.execute(
                select(models.Document).where(
                    models.Document.preprocessed_file_id
                    == document.preprocessed_file_id,
                    models.Document.id != document_id,
                )
            )
            .scalars()
            .first()
        )

        if not other_docs_using_file:
            preprocessed_file = db.get(models.File, document.preprocessed_file_id)
            if preprocessed_file:
                orphaned_blob_uuid = preprocessed_file.file_uuid
                db.delete(preprocessed_file)

    db.delete(document)
    db.commit()

    # Remove the storage blob only after the DB delete committed — if the
    # commit fails the blob must still back the surviving File row.
    if orphaned_blob_uuid:
        try:
            remove_file(orphaned_blob_uuid)
        except Exception:
            logger.exception("Error deleting preprocessed file from storage")

    record_audit(
        AuditAction.DELETE,
        actor=current_user,
        resource_type="document",
        resource_id=document_id,
        project_id=project_id,
        detail={"cascade": True, **cascade_counts} if cascade else None,
    )

    # Clean up empty preprocessing tasks after document deletion
    cleanup_empty_preprocessing_tasks(db, file_preprocessing_task_id)

    return {"detail": "Document deleted successfully"}


@router.post("/document-set", response_model=schemas.DocumentSet)
def create_document_set(
    project_id: int,
    document_set: schemas.DocumentSetCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.DocumentSet:
    """Create a document set from documents or a trial"""
    # Check project access
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not can_access_project(current_user, project):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to create document sets for this project",
        )

    # Create the document set
    db_set = models.DocumentSet(
        project_id=project_id,
        name=document_set.name,
        description=document_set.description,
    )

    db.add(db_set)
    db.flush()

    # Add documents based on whether it's from trial or direct selection
    if document_set.trial_id:
        # Get documents from trial
        trial: models.Trial | None = db.execute(
            select(models.Trial).where(
                models.Trial.id == document_set.trial_id,
                models.Trial.project_id == project_id,
            )
        ).scalar_one_or_none()

        if not trial:
            raise HTTPException(
                status_code=404, detail="Trial not found in this project"
            )

        document_ids = trial.document_ids
    else:
        # Use provided document IDs
        document_ids = document_set.document_ids

    # Validate all candidate documents belong to the project in one query, then
    # bulk-insert the membership rows in a single statement (was one SELECT +
    # one INSERT per document — thousands of round-trips for a large set).
    if document_ids:
        valid_ids = set(
            db.execute(
                select(models.Document.id).where(
                    models.Document.id.in_(document_ids),
                    models.Document.project_id == project_id,
                )
            )
            .scalars()
            .all()
        )
        # Preserve input order and drop duplicates / out-of-project ids.
        ordered_ids = [d for d in dict.fromkeys(document_ids) if d in valid_ids]
        if ordered_ids:
            db.execute(
                document_set_association.insert(),
                [{"document_id": d, "document_set_id": db_set.id} for d in ordered_ids],
            )

    db.commit()
    db.refresh(db_set)

    return schemas.DocumentSet.model_validate(db_set)


@router.get("/document-set", response_model=schemas.PaginatedDocumentSets)
def get_document_sets(
    project_id: int,
    include_auto_generated: bool = Query(
        True, description="Include auto-generated sets from preprocessing"
    ),
    preprocessing_config_id: int = Query(
        None, description="Filter by preprocessing configuration"
    ),
    tag: Annotated[str | None, Query(description="Filter by tag")] = None,
    search: Annotated[
        str | None, Query(description="Search name/description (case-insensitive)")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PaginatedDocumentSets:
    check_project_access(project_id, current_user, db, "read")

    DS = models.DocumentSet

    query = select(DS).where(DS.project_id == project_id)

    if not include_auto_generated:
        query = query.where(~DS.is_auto_generated)

    if preprocessing_config_id:
        query = query.where(DS.preprocessing_config_id == preprocessing_config_id)

    if search:
        pattern = f"%{search}%"
        query = query.where(or_(DS.name.ilike(pattern), DS.description.ilike(pattern)))

    # Eager-load preprocessing_config (used by the list card); do NOT load
    # `documents` — counts are computed below for the page only.
    query = query.options(selectinload(DS.preprocessing_config)).order_by(
        DS.created_at.desc()
    )

    all_sets = db.execute(query).scalars().all()

    # Tag filter is JSON-array membership; kept in Python for SQLite/Postgres
    # parity (sets are bounded per project, so this is not a scaling concern).
    if tag:
        all_sets = [s for s in all_sets if s.tags and tag in s.tags]

    total = len(all_sets)
    page_sets = all_sets[offset : offset + limit]
    total_pages = (total + limit - 1) // limit if limit else 1
    page = offset // limit + 1 if limit else 1

    # Compute member/trial counts for the page's sets only (two grouped queries,
    # not one-per-set).
    set_ids = [s.id for s in page_sets]
    doc_counts: dict[int, int] = {}
    trial_counts: dict[int, int] = {}
    if set_ids:
        doc_counts = {
            row[0]: row[1]
            for row in db.execute(
                select(
                    document_set_association.c.document_set_id,
                    func.count(),
                )
                .where(document_set_association.c.document_set_id.in_(set_ids))
                .group_by(document_set_association.c.document_set_id)
            ).all()
        }
        trial_counts = {
            row[0]: row[1]
            for row in db.execute(
                select(
                    models.Trial.document_set_id,
                    func.count(),
                )
                .where(models.Trial.document_set_id.in_(set_ids))
                .group_by(models.Trial.document_set_id)
            ).all()
        }

    items = []
    for s in page_sets:
        summary = schemas.DocumentSetSummary.model_validate(s)
        summary.document_count = doc_counts.get(s.id, 0)
        summary.trials_count = trial_counts.get(s.id, 0)
        items.append(summary)

    return schemas.PaginatedDocumentSets(
        items=items,
        total=total,
        page=page,
        page_size=limit,
        total_pages=total_pages,
    )


@router.get("/document-set/{set_id}", response_model=schemas.DocumentSetSummary)
def get_document_set(
    project_id: int,
    set_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.DocumentSetSummary:
    """Fetch a single document set's summary (used to deep-link the group viewer)."""
    check_project_access(project_id, current_user, db, "read")

    DS = models.DocumentSet
    doc_set = db.execute(
        select(DS)
        .where(DS.id == set_id, DS.project_id == project_id)
        .options(selectinload(DS.preprocessing_config))
    ).scalar_one_or_none()

    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")

    document_count = (
        db.execute(
            select(func.count()).where(
                document_set_association.c.document_set_id == set_id
            )
        ).scalar()
        or 0
    )
    trials_count = (
        db.execute(
            select(func.count()).where(models.Trial.document_set_id == set_id)
        ).scalar()
        or 0
    )

    summary = schemas.DocumentSetSummary.model_validate(doc_set)
    summary.document_count = document_count
    summary.trials_count = trials_count
    return summary


@router.patch("/document-set/{set_id}", response_model=schemas.DocumentSet)
def update_document_set(
    project_id: int,
    set_id: int,
    update_data: schemas.DocumentSetUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.DocumentSet:
    check_project_access(project_id, current_user, db, "write")

    doc_set = db.execute(
        select(models.DocumentSet).where(
            models.DocumentSet.id == set_id, models.DocumentSet.project_id == project_id
        )
    ).scalar_one_or_none()

    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")

    # Update fields
    for field, value in update_data.model_dump(exclude_unset=True).items():
        if field == "document_ids":
            # Handle document updates
            # Remove existing associations
            db.execute(
                document_set_association.delete().where(
                    document_set_association.c.document_set_id == set_id
                )
            )
            # Add new associations — but only for documents that actually belong
            # to this project. Without this check a caller could add another
            # project's document IDs to their set (cross-project reference).
            if value:
                valid_ids = {
                    row[0]
                    for row in db.execute(
                        select(models.Document.id).where(
                            models.Document.id.in_(value),
                            models.Document.project_id == project_id,
                        )
                    ).all()
                }
                for doc_id in value:
                    if doc_id in valid_ids:
                        db.execute(
                            document_set_association.insert().values(
                                document_id=doc_id, document_set_id=set_id
                            )
                        )
        else:
            setattr(doc_set, field, value)

    db.commit()
    db.refresh(doc_set)

    return schemas.DocumentSet.model_validate(doc_set)


@router.delete(
    "/document-set/{set_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document set (only if not used by any trial)",
)
def delete_document_set(
    project_id: int,
    set_id: int,
    delete_documents: bool = Query(
        False,
        description="Also delete all documents in this set (if not referenced elsewhere)",
    ),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document set.

    If delete_documents=True, also attempts to delete all documents in the set.
    Documents that are referenced in trials, trial results, evaluations, or other
    document sets will not be deleted (errors are logged but don't prevent set deletion).
    """
    # 1. Permission check
    check_project_access(project_id, current_user, db, "write")

    # 2. Fetch the document set with relationships
    doc_set = db.execute(
        select(models.DocumentSet)
        .where(
            models.DocumentSet.id == set_id,
            models.DocumentSet.project_id == project_id,
        )
        .options(
            selectinload(models.DocumentSet.trials),
            selectinload(models.DocumentSet.documents),
        )
    ).scalar_one_or_none()

    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")

    # 3. Prevent deletion if any trial references this set
    if doc_set.trials and len(doc_set.trials) > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete document set: one or more trials reference it.",
        )

    # 4. Optionally delete documents first
    deleted_doc_ids = []
    file_preprocessing_task_ids = set()  # Track tasks for cleanup
    orphaned_blob_uuids: list[str] = []  # Storage blobs to remove post-commit
    if delete_documents:
        # Load trial-referenced doc IDs once for the whole set instead of
        # re-querying every trial per document (was O(docs × trials)).
        set_doc_ids = [doc.id for doc in doc_set.documents]
        referenced_doc_ids: set[int] = set()
        if set_doc_ids:
            rows = db.execute(
                select(models.Trial.document_ids).where(
                    models.Trial.project_id == project_id
                )
            ).all()
            ref_set = set(set_doc_ids)
            for (trial_doc_ids,) in rows:
                if trial_doc_ids and ref_set.intersection(trial_doc_ids):
                    referenced_doc_ids.update(ref_set.intersection(trial_doc_ids))

        for doc in doc_set.documents:
            # Check if document can be safely deleted
            can_delete = True

            # Check trial references (via document_ids JSON list)
            if doc.id in referenced_doc_ids:
                can_delete = False

            # Check trial results (a doc may have results across many trials)
            if (
                db.execute(
                    select(models.TrialResult).where(
                        models.TrialResult.document_id == doc.id
                    )
                )
                .scalars()
                .first()
            ):
                can_delete = False

            # Check evaluation metrics (many per document)
            if (
                db.execute(
                    select(models.EvaluationMetric).where(
                        models.EvaluationMetric.document_id == doc.id
                    )
                )
                .scalars()
                .first()
            ):
                can_delete = False

            # Check other document sets
            if doc.document_sets and any(s.id != set_id for s in doc.document_sets):
                can_delete = False

            if can_delete:
                # Track file_preprocessing_task_id for cleanup after deletion
                if doc.file_preprocessing_task_id:
                    file_preprocessing_task_ids.add(doc.file_preprocessing_task_id)

                # Delete preprocessed file if not used by other docs
                if doc.preprocessed_file_id:
                    other_docs = (
                        db.execute(
                            select(models.Document).where(
                                models.Document.preprocessed_file_id
                                == doc.preprocessed_file_id,
                                models.Document.id != doc.id,
                            )
                        )
                        .scalars()
                        .first()
                    )

                    if not other_docs:
                        preprocessed_file = db.get(
                            models.File, doc.preprocessed_file_id
                        )
                        if preprocessed_file:
                            orphaned_blob_uuids.append(preprocessed_file.file_uuid)
                            db.delete(preprocessed_file)

                deleted_doc_ids.append(doc.id)
                db.delete(doc)

    # 5. Delete the document set
    # Note: Association rows in document_set_association are automatically handled:
    # - If documents were deleted above, their associations are already gone (cascade from Document)
    # - Remaining associations will be deleted when doc_set is deleted (many-to-many cleanup)
    db.delete(doc_set)
    db.commit()

    # Remove storage blobs only after the DB delete committed — if the commit
    # fails the blobs must still back the surviving File rows.
    for blob_uuid in orphaned_blob_uuids:
        try:
            remove_file(blob_uuid)
        except Exception:
            logger.exception("Error deleting preprocessed file from storage")

    record_audit(
        AuditAction.DELETE,
        actor=current_user,
        resource_type="document_set",
        resource_id=set_id,
        project_id=project_id,
        detail={
            "documents_deleted": len(deleted_doc_ids),
            "cascade_documents": bool(delete_documents),
        },
    )

    # Clean up empty preprocessing tasks after document deletion
    for task_id in file_preprocessing_task_ids:
        cleanup_empty_preprocessing_tasks(db, task_id)

    # Return info about what was deleted (for frontend feedback)
    return {"deleted_set_id": set_id, "deleted_document_ids": deleted_doc_ids}


def _stream_set_zip(file_rows):
    """Yield a ZIP archive byte-stream for ``(file_name, file_uuid)`` entries.

    Each file's content is read from storage (via ``get_file``) lazily as the
    stream is consumed, so we never hold more than one file's bytes in memory.
    """

    def _entries():
        for file_name, file_uuid in file_rows:
            try:
                yield (file_name, get_file(file_uuid))
            except Exception:
                # Log and continue with the other files.
                logger.exception("Error adding file %s", file_name)

    return iter_zip(_entries())


@router.post("/document-set/{set_id}/download-all")
def download_all_documents(
    project_id: int,
    set_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download all documents in a set as a (streamed) ZIP file"""
    check_project_access(project_id, current_user, db, "read")

    doc_set = db.execute(
        select(models.DocumentSet).where(
            models.DocumentSet.id == set_id, models.DocumentSet.project_id == project_id
        )
    ).scalar_one_or_none()

    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")

    # Collect only (file_name, file_uuid) for the set's members — do not load
    # the Document rows (and especially not the `text` column). File contents
    # are read lazily from storage during streaming.
    file_rows = list(
        db.execute(
            select(models.File.file_name, models.File.file_uuid)
            .join(
                models.Document,
                models.Document.original_file_id == models.File.id,
            )
            .join(
                document_set_association,
                document_set_association.c.document_id == models.Document.id,
            )
            .where(
                document_set_association.c.document_set_id == set_id,
                models.Document.project_id == project_id,
            )
        ).all()
    )

    # RFC 5987 / safely-quoted filename for the Content-Disposition header.
    safe_name = doc_set.name.replace(" ", "_") or "documents"
    quoted = urllib.parse.quote(f"{safe_name}_documents.zip")
    disposition = f"attachment; filename=\"{quoted}\"; filename*=UTF-8''{quoted}"

    record_audit(
        AuditAction.EXPORT,
        actor=current_user,
        resource_type="document_set",
        resource_id=set_id,
        project_id=project_id,
        detail={"files": len(file_rows), "format": "zip"},
    )
    return StreamingResponse(
        _stream_set_zip(file_rows),
        media_type="application/zip",
        headers={"Content-Disposition": disposition},
    )


@router.get("/document-set/{set_id}/stats", response_model=schemas.DocumentSetStats)
def get_document_set_stats(
    project_id: int,
    set_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.DocumentSetStats:
    """Get usage statistics for a document set"""
    check_project_access(project_id, current_user, db, "read")

    doc_set = db.execute(
        select(models.DocumentSet).where(
            models.DocumentSet.id == set_id, models.DocumentSet.project_id == project_id
        )
    ).scalar_one_or_none()

    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")

    # Get document IDs in this set directly from the association table — avoids
    # loading every member Document (incl. the `text` column) as an ORM object.
    doc_ids = list(
        db.execute(
            select(document_set_association.c.document_id).where(
                document_set_association.c.document_set_id == set_id
            )
        )
        .scalars()
        .all()
    )

    if not doc_ids:
        return schemas.DocumentSetStats(
            trials_count=0, extractions_count=0, last_used=None
        )

    # Count trials that contain ANY of these document IDs. Membership is
    # checked in Python for SQLite/PostgreSQL compatibility; only lightweight
    # columns are loaded instead of full Trial rows.
    trials_with_docs = trials_referencing_docs(db, project_id, doc_ids)

    trials_count = len(trials_with_docs)
    last_trial_date = None
    for _trial_id, _name, created_at in trials_with_docs:
        if created_at and (not last_trial_date or created_at > last_trial_date):
            last_trial_date = created_at

    # Count total extractions (trial results for these documents)
    extractions_count = (
        db.execute(
            select(func.count(models.TrialResult.id))
            .join(models.Trial)
            .where(
                models.Trial.project_id == project_id,
                models.TrialResult.document_id.in_(doc_ids),
            )
        ).scalar()
        or 0
    )

    return schemas.DocumentSetStats(
        trials_count=trials_count,
        extractions_count=extractions_count,
        last_used=last_trial_date,
    )


@router.post("/document-set/from-trial/{trial_id}", response_model=schemas.DocumentSet)
def create_document_set_from_trial(
    project_id: int,
    trial_id: int,
    set_data: schemas.DocumentSetFromTrial,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.DocumentSet:
    """Create a named document set from a trial's documents"""
    check_project_access(project_id, current_user, db, "write")

    # Get trial
    trial = db.execute(
        select(models.Trial).where(
            models.Trial.id == trial_id, models.Trial.project_id == project_id
        )
    ).scalar_one_or_none()

    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    # Create document set
    db_set = models.DocumentSet(
        project_id=project_id,
        name=set_data.name,
        description=set_data.description or f"Documents from trial #{trial_id}",
        tags=set_data.tags or [],
        is_auto_generated=False,
    )

    db.add(db_set)
    db.flush()

    # Add documents — verify membership in one batched query rather than
    # trusting trial.document_ids (which could be stale or reference docs that
    # were since moved/deleted). Avoids cross-project references.
    doc_ids = list(trial.document_ids or [])
    if doc_ids:
        valid_ids = {
            row[0]
            for row in db.execute(
                select(models.Document.id).where(
                    models.Document.id.in_(doc_ids),
                    models.Document.project_id == project_id,
                )
            ).all()
        }
        for doc_id in doc_ids:
            if doc_id in valid_ids:
                db.execute(
                    document_set_association.insert().values(
                        document_id=doc_id, document_set_id=db_set.id
                    )
                )

    db.commit()
    db.refresh(db_set)

    return schemas.DocumentSet.model_validate(db_set)
