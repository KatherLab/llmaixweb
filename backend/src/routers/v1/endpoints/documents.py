# backend/src/routers/v1/endpoints/documents.py
"""Document and document-set endpoints for projects."""

import datetime
import io
import zipfile
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, contains_eager, joinedload, selectinload

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
        )
    else:
        # Always eager load to avoid N+1 queries in the UI
        page_q = page_q.options(
            joinedload(D.original_file),
            selectinload(D.preprocessing_config),
            selectinload(D.file_preprocessing_task),
        )

    items = db.execute(page_q).scalars().all()
    return schemas.PaginatedDocuments(
        items=[schemas.Document.model_validate(d) for d in items],
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
    trial_result = db.execute(
        select(models.TrialResult).where(models.TrialResult.document_id == document_id)
    ).scalar_one_or_none()
    if trial_result:
        raise HTTPException(
            status_code=400,
            detail="Document is referenced in a trial result. Remove results/trials first.",
        )

    # --- (Optional) Check if document is used in any evaluation metric ---
    metric = db.execute(
        select(models.EvaluationMetric).where(
            models.EvaluationMetric.document_id == document_id
        )
    ).scalar_one_or_none()
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

    # --- Preprocessed file deletion logic as before ---
    if document.preprocessed_file_id:
        other_docs_using_file = db.execute(
            select(models.Document).where(
                models.Document.preprocessed_file_id == document.preprocessed_file_id,
                models.Document.id != document_id,
            )
        ).scalar_one_or_none()

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


@router.get("/document-set", response_model=List[schemas.DocumentSet])
def get_document_sets(
    project_id: int,
    include_auto_generated: bool = Query(
        True, description="Include auto-generated sets from preprocessing"
    ),
    preprocessing_config_id: int = Query(
        None, description="Filter by preprocessing configuration"
    ),
    tag: str = Query(None, description="Filter by tag"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[schemas.DocumentSet]:
    check_project_access(project_id, current_user, db, "read")

    query = select(models.DocumentSet).where(
        models.DocumentSet.project_id == project_id
    )

    if not include_auto_generated:
        query = query.where(~models.DocumentSet.is_auto_generated)

    if preprocessing_config_id:
        query = query.where(
            models.DocumentSet.preprocessing_config_id == preprocessing_config_id
        )

    if tag:
        # In-Python filtering to avoid JSON `LIKE` incompatibility with PostgreSQL
        pass  # Filtered below after fetch

    sets = (
        db.execute(query.order_by(models.DocumentSet.created_at.desc())).scalars().all()
    )

    if tag:
        sets = [s for s in sets if s.tags and tag in s.tags]

    return [schemas.DocumentSet.model_validate(s) for s in sets]


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
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document set (only if not used by any trial)",
)
def delete_document_set(
    project_id: int,
    set_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. Permission check
    check_project_access(project_id, current_user, db, "write")

    # 2. Fetch the document set, ensure it belongs to project
    doc_set = db.execute(
        select(models.DocumentSet)
        .where(
            models.DocumentSet.id == set_id,
            models.DocumentSet.project_id == project_id,
        )
        .options(selectinload(models.DocumentSet.trials))
    ).scalar_one_or_none()

    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")

    # 3. Prevent deletion if any trial references this set
    if doc_set.trials and len(doc_set.trials) > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete document set: one or more trials reference it.",
        )

    # 4. Delete the set and its associations
    # Remove document associations (optional, for clean DB)
    db.execute(
        document_set_association.delete().where(
            document_set_association.c.document_set_id == set_id
        )
    )
    db.delete(doc_set)
    db.commit()
    return


@router.post("/document-set/{set_id}/download-all")
def download_all_documents(
    project_id: int,
    set_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download all documents in a set as a ZIP file"""
    check_project_access(project_id, current_user, db, "read")

    doc_set = db.execute(
        select(models.DocumentSet)
        .where(
            models.DocumentSet.id == set_id, models.DocumentSet.project_id == project_id
        )
        .options(
            selectinload(models.DocumentSet.documents).selectinload(
                models.Document.original_file
            )
        )
    ).scalar_one_or_none()

    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for doc in doc_set.documents:
            if doc.original_file:
                try:
                    # Get file content
                    file_content = get_file(doc.original_file.file_uuid)

                    # Add to ZIP with original filename
                    zip_file.writestr(doc.original_file.file_name, file_content)
                except Exception as e:
                    # Log error but continue with other files
                    print(f"Error adding file {doc.original_file.file_name}: {e}")

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={doc_set.name.replace(' ', '_')}_documents.zip"
        },
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
        select(models.DocumentSet)
        .options(selectinload(models.DocumentSet.documents))
        .where(
            models.DocumentSet.id == set_id, models.DocumentSet.project_id == project_id
        )
    ).scalar_one_or_none()

    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")

    # Get document IDs in this set
    doc_ids = [doc.id for doc in doc_set.documents]

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
