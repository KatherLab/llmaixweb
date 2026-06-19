# backend/src/routers/v1/endpoints/documents.py
"""Document and document-set endpoints for projects."""

import datetime
import io
import urllib.parse
import zipfile
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, contains_eager, defer, joinedload, selectinload

from .... import models, schemas
from ....core.security import get_current_user
from ....dependencies import get_db, get_file, remove_file
from ....models.project import document_set_association

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

    # Page query
    page_q = base.order_by(D.created_at.desc()).limit(limit).offset(offset)

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
    if current_user.role != "admin" and project.owner_id != current_user.id:
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

    return schemas.Document.model_validate(document)


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


@router.delete("/document/{document_id}")
def delete_document(
    *,
    project_id: int,
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a specific document, only if not used in any trial, trial result, or evaluation metric."""
    check_project_access(project_id, current_user, db, "write")

    document = db.execute(
        select(models.Document).where(
            models.Document.id == document_id, models.Document.project_id == project_id
        )
    ).scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # --- Check for usage in any trial (document_ids is a JSON list) ---
    # Use in-Python filtering to avoid JSON operator incompatibility between SQLite and PostgreSQL
    trials_with_doc = (
        db.execute(select(models.Trial).where(models.Trial.project_id == project_id))
        .scalars()
        .all()
    )
    trials_with_doc = next(
        (
            t
            for t in trials_with_doc
            if t.document_ids and document_id in t.document_ids
        ),
        None,
    )
    if trials_with_doc:
        raise HTTPException(
            status_code=400,
            detail=f"Document is referenced in trial '{trials_with_doc.name or trials_with_doc.id}'. Remove from trial(s) first.",
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
                try:
                    remove_file(preprocessed_file.file_uuid)
                    db.delete(preprocessed_file)
                except Exception as e:
                    print(f"Error deleting preprocessed file: {e}")

    db.delete(document)
    db.commit()

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

    if current_user.role != "admin" and project.owner_id != current_user.id:
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

    # Add documents to the set
    for doc_id in document_ids:
        # Verify document exists in project
        doc = db.execute(
            select(models.Document).where(
                models.Document.id == doc_id, models.Document.project_id == project_id
            )
        ).scalar_one_or_none()

        if doc:
            db.execute(
                document_set_association.insert().values(
                    document_id=doc_id, document_set_id=db_set.id
                )
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
        doc_counts = dict(
            db.execute(
                select(
                    document_set_association.c.document_set_id,
                    func.count(),
                )
                .where(document_set_association.c.document_set_id.in_(set_ids))
                .group_by(document_set_association.c.document_set_id)
            ).all()
        )
        trial_counts = dict(
            db.execute(
                select(
                    models.Trial.document_set_id,
                    func.count(),
                )
                .where(models.Trial.document_set_id.in_(set_ids))
                .group_by(models.Trial.document_set_id)
            ).all()
        )

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
            # Add new associations
            for doc_id in value:
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
    if delete_documents:
        for doc in doc_set.documents:
            # Check if document can be safely deleted
            can_delete = True

            # Check trial references (via document_ids JSON list)
            trials_with_doc = (
                db.execute(
                    select(models.Trial).where(models.Trial.project_id == project_id)
                )
                .scalars()
                .all()
            )
            if any(
                t.document_ids and doc.id in t.document_ids for t in trials_with_doc
            ):
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
                        try:
                            preprocessed_file = db.get(
                                models.File, doc.preprocessed_file_id
                            )
                            if preprocessed_file:
                                remove_file(preprocessed_file.file_uuid)
                                db.delete(preprocessed_file)
                        except Exception as e:
                            print(
                                f"Error deleting preprocessed file for doc {doc.id}: {e}"
                            )

                deleted_doc_ids.append(doc.id)
                db.delete(doc)

    # 5. Delete the document set
    # Note: Association rows in document_set_association are automatically handled:
    # - If documents were deleted above, their associations are already gone (cascade from Document)
    # - Remaining associations will be deleted when doc_set is deleted (many-to-many cleanup)
    db.delete(doc_set)
    db.commit()

    # Clean up empty preprocessing tasks after document deletion
    for task_id in file_preprocessing_task_ids:
        cleanup_empty_preprocessing_tasks(db, task_id)

    # Return info about what was deleted (for frontend feedback)
    return {"deleted_set_id": set_id, "deleted_document_ids": deleted_doc_ids}


class _StreamingZipSink:
    """Forward-only file-like sink for :mod:`zipfile`.

    ``zipfile.ZipFile`` in write mode only calls ``write()`` and ``tell()`` (it
    records offsets from ``tell()`` and writes the central directory on
    ``close()`` without seeking back). This lets us drain the bytes it produces
    incrementally and stream them to the client, so a 100k-document set doesn't
    get buffered entirely in memory (or on disk) before the first byte ships.
    """

    def __init__(self) -> None:
        self._chunks: list[bytes] = []
        self._pos = 0

    def write(self, data) -> None:
        if data:
            b = bytes(data)
            self._chunks.append(b)
            self._pos += len(b)

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = 0) -> int:
        # zipfile only uses tell() in write mode; allow the no-op seek-to-current
        # it occasionally issues, and refuse anything else rather than corrupt.
        if whence == 1 and offset == 0:
            return self._pos
        raise io.UnsupportedOperation("forward-only stream does not support seek")

    def flush(self) -> None:  # pragma: no cover - zipfile calls this
        pass

    def drain(self) -> bytes:
        if not self._chunks:
            return b""
        data = b"".join(self._chunks)
        self._chunks.clear()
        return data


def _stream_set_zip(file_rows: list[tuple[str, str]]):
    """Yield a ZIP archive byte-stream for ``(file_name, file_uuid)`` entries.

    Each file's content is read from storage (via ``get_file``) lazily as the
    stream is consumed, so we never hold more than one file's bytes in memory.
    """
    sink = _StreamingZipSink()
    zf = zipfile.ZipFile(sink, "w", zipfile.ZIP_DEFLATED)
    try:
        for file_name, file_uuid in file_rows:
            try:
                content = get_file(file_uuid)
                zf.writestr(file_name, content)
            except Exception as e:
                # Log and continue with the other files.
                print(f"Error adding file {file_name}: {e}")
            yield sink.drain()
        zf.close()  # writes the central directory
        yield sink.drain()
    finally:
        zf.close()


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
    file_rows = db.execute(
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

    # RFC 5987 / safely-quoted filename for the Content-Disposition header.
    safe_name = doc_set.name.replace(" ", "_") or "documents"
    quoted = urllib.parse.quote(f"{safe_name}_documents.zip")
    disposition = f"attachment; filename=\"{quoted}\"; filename*=UTF-8''{quoted}"

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
    doc_ids = (
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

    # For SQLite, we need to check JSON array membership differently
    # Count trials that contain ANY of these document IDs
    trials_with_docs = (
        db.execute(select(models.Trial).where(models.Trial.project_id == project_id))
        .scalars()
        .all()
    )

    # Filter trials that contain any of our document IDs
    trials_count = 0
    last_trial_date = None

    for trial in trials_with_docs:
        if trial.document_ids and any(
            doc_id in trial.document_ids for doc_id in doc_ids
        ):
            trials_count += 1
            if not last_trial_date or trial.created_at > last_trial_date:
                last_trial_date = trial.created_at

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

    # Add documents
    for doc_id in trial.document_ids:
        db.execute(
            document_set_association.insert().values(
                document_id=doc_id, document_set_id=db_set.id
            )
        )

    db.commit()
    db.refresh(db_set)

    return schemas.DocumentSet.model_validate(db_set)
