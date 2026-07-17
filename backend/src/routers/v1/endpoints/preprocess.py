# backend/src/routers/v1/endpoints/preprocess.py
"""Preprocessing task endpoints for projects."""

import datetime
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .... import models, schemas
from ....core.security import admin_has_global_project_access, get_current_user
from ....dependencies import get_db
from ....middleware.error_handlers import internal_error_message
from ....utils.audit import record_audit
from ....utils.enums import AuditAction

logger = logging.getLogger(__name__)
router = APIRouter()

# OCR engines that send document images/text to an external service (PHI egress),
# as opposed to the local Docling/Tesseract path.
_REMOTE_OCR_ENGINES = {"mistral_ocr", "llm_vision"}


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


@router.post(
    "/preprocess/preview", response_model=schemas.PreprocessingDuplicatePreview
)
async def preview_preprocessing_duplicates(
    *,
    project_id: int,
    preprocessing_task: schemas.PreprocessingTaskCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingDuplicatePreview:
    """Preview which files would have document duplicates if processed.

    This endpoint checks for existing documents that would be archived
    (marked as is_latest=False) if the preprocessing task were to run.

    Distinguishes between:
    - same_config_duplicates: Files with existing documents using the exact same OCR config
    - files_with_duplicates: All files with any existing documents (regardless of config)
    - pdfs_with_embedded_text: PDFs where embedded text was detected (OCR may not affect result)
    """
    check_project_access(project_id, current_user, db, "read")

    if not preprocessing_task.inline_config:
        raise HTTPException(
            status_code=400,
            detail="inline_config is required",
        )

    # Validate files exist and belong to project
    files = (
        db.execute(
            select(models.File).where(
                models.File.id.in_(preprocessing_task.file_ids),
                models.File.project_id == project_id,
            )
        )
        .scalars()
        .all()
    )
    if len(files) != len(preprocessing_task.file_ids):
        missing_ids = set(preprocessing_task.file_ids) - {f.id for f in files}
        raise HTTPException(
            status_code=404,
            detail=f"Files not found or don't belong to project: {missing_ids}",
        )

    # Check if any OCR engine is enabled when processing image files (PNG/JPEG).
    # PDFs are still allowed - they can use pypdf for embedded text extraction.
    # PDFs without embedded text will show a warning that OCR is not available.
    from ....core.dynamic_settings import get_settings

    settings = get_settings()

    image_types = {
        models.FileType.IMAGE_PNG,
        models.FileType.IMAGE_JPEG,
        "image/png",
        "image/jpeg",
        "image/jpg",
    }

    has_images = any(file.file_type in image_types for file in files)
    any_ocr_enabled = (
        settings.DOCLING_SERVE_ENABLED
        or settings.MISTRAL_OCR_ENABLED
        or settings.VISION_OCR_ENABLED
        or settings.DOCLING_LOCAL_FALLBACK
    )

    if has_images and not any_ocr_enabled:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "no_ocr_engine_enabled",
                "message": "All OCR engines are disabled. At least one OCR engine must be enabled to process image files (PNG/JPEG).",
                "hint": "Enable Local OCR, Mistral OCR, or Vision LLM in Admin Settings. PDF files can still be processed for embedded text extraction.",
            },
        )

    # Get or create config (don't commit - just for preview)
    config_dict = preprocessing_task.inline_config.model_dump()
    config = models.PreprocessingConfiguration(
        project_id=project_id,
        name=config_dict.get("name", "Preview Task"),
        description=config_dict.get("description"),
        additional_settings=config_dict.get("additional_settings"),
    )

    # Extract OCR engine info from additional_settings for comparison
    additional_settings = config_dict.get("additional_settings", {})
    new_ocr_engine = additional_settings.get("ocr_engine", "docling_tesseract")
    new_force_ocr = additional_settings.get("force_ocr", False)
    # Model names for duplicate detection (user may change model while keeping same engine)
    # Must use same defaults as actual processing to ensure proper comparison
    new_mistral_model = (
        additional_settings.get("mistral_model") or settings.MISTRAL_OCR_MODEL
    )
    new_vision_model = (
        additional_settings.get("vision_model") or settings.VISION_OCR_MODEL or "gpt-4o"
    )

    # Normalize OCR engine names for comparison
    # Frontend sends "docling_tesseract" but backend stores "tesseract"
    # This mapping ensures proper duplicate detection
    def normalize_ocr_engine(engine: str) -> str:
        """Normalize OCR engine names for comparison with stored metadata."""
        if engine == "docling_tesseract":
            return "tesseract"
        return engine

    new_ocr_engine_normalized = normalize_ocr_engine(new_ocr_engine)

    # OPTIMIZATION: Batch query all existing documents in a single query
    # instead of looping through files with O(n) queries.
    # This reduces database load significantly for large file batches.

    file_ids = [f.id for f in files]

    # Single batched query for all existing documents
    existing_docs_query = (
        select(models.Document)
        .where(
            models.Document.original_file_id.in_(file_ids),
            models.Document.is_latest.is_(True),
        )
        .order_by(models.Document.original_file_id)
    )
    all_existing_docs = db.execute(existing_docs_query).scalars().all()

    # Group documents by file_id for efficient lookup
    docs_by_file: dict[int, list[models.Document]] = {}
    for doc in all_existing_docs:
        if doc.original_file_id not in docs_by_file:
            docs_by_file[doc.original_file_id] = []
        docs_by_file[doc.original_file_id].append(doc)

    # Check for duplicates
    files_with_duplicates = []
    same_config_duplicates = []
    pdfs_with_embedded_text = []
    total_existing_docs = 0

    for file in files:
        existing_docs = docs_by_file.get(file.id, [])

        if existing_docs:
            files_with_duplicates.append(
                schemas.DuplicatePreviewItem(
                    file_id=file.id,
                    file_name=file.file_name,
                    existing_document_count=len(existing_docs),
                    existing_document_ids=[d.id for d in existing_docs],
                    preprocessing_config_id=config.id,
                    config_name=config.name,
                )
            )
            total_existing_docs += len(existing_docs)

            # Check for same config duplicates (OCR engine + force_ocr setting + model match)
            same_config_docs = []
            for doc in existing_docs:
                doc_meta = doc.meta_data or {}
                doc_ocr_engine = doc_meta.get("ocr_engine")
                doc_force_ocr = doc_meta.get("force_ocr", False)
                doc_extraction_method = doc_meta.get("extraction_method", "")
                # Model names stored in metadata (for mistral_ocr and llm_vision engines)
                doc_mistral_model = doc_meta.get("mistral_model")
                doc_vision_model = doc_meta.get("vision_model")

                # Check if this document was created with the same config
                # For PDFs with embedded text, docling_serve_no_ocr produces the same result
                # regardless of selected OCR engine (when force_ocr is False)
                has_embedded_text = doc_meta.get("embedded_text_detected", False)

                # Normalize the stored OCR engine for comparison
                doc_ocr_engine_normalized = (
                    normalize_ocr_engine(doc_ocr_engine) if doc_ocr_engine else ""
                )

                # Same config = same OCR engine AND same force_ocr setting
                # For mistral_ocr: also require same mistral_model
                # For llm_vision: also require same vision_model
                # OR both would use docling embedded text extraction (force_ocr=False for PDF)
                #
                # force_ocr is a PDF-specific concept: it forces OCR even when a PDF has
                # embedded text. For every other file type (images, spreadsheets, text)
                # OCR is either always required or never used, so force_ocr is irrelevant
                # and the frontend never sends it for them. Enforcing the match for images
                # caused a regression: the docling-serve image path stores force_ocr=True
                # (images always need OCR) while re-processing sends force_ocr=False (the
                # frontend default), so same-config duplicates were never detected and the
                # reprocessing warning modal never appeared. Only enforce it for PDFs.
                force_ocr_relevant = file.file_type == models.FileType.APPLICATION_PDF
                force_ocr_matches = (
                    doc_force_ocr == new_force_ocr
                ) or not force_ocr_relevant

                is_same_config = (
                    (
                        doc_ocr_engine_normalized == new_ocr_engine_normalized
                        and force_ocr_matches
                        # Model comparison: only check if engine matches
                        and (
                            # mistral_ocr engine: compare mistral_model
                            (
                                doc_ocr_engine == "mistral_ocr"
                                and new_ocr_engine == "mistral_ocr"
                                and doc_mistral_model == new_mistral_model
                            )
                            or
                            # llm_vision engine: compare vision_model
                            (
                                doc_ocr_engine == "llm_vision"
                                and new_ocr_engine == "llm_vision"
                                and doc_vision_model == new_vision_model
                            )
                            or
                            # Other engines (tesseract, pypdf, etc.): no model comparison needed
                            (
                                doc_ocr_engine not in ("mistral_ocr", "llm_vision")
                                and new_ocr_engine not in ("mistral_ocr", "llm_vision")
                            )
                        )
                    )
                    or
                    # Special case: PDF with embedded text, force_ocr=False for both
                    # (uses docling_serve_no_ocr regardless of OCR engine selection)
                    (
                        file.file_type == models.FileType.APPLICATION_PDF
                        and has_embedded_text
                        and not new_force_ocr
                        and "no_ocr" in doc_extraction_method
                    )
                )

                if is_same_config:
                    same_config_docs.append(doc)

            if same_config_docs:
                same_config_duplicates.append(
                    schemas.DuplicatePreviewItem(
                        file_id=file.id,
                        file_name=file.file_name,
                        existing_document_count=len(same_config_docs),
                        existing_document_ids=[d.id for d in same_config_docs],
                        preprocessing_config_id=config.id,
                        config_name=config.name,
                    )
                )

            # Check for PDFs with embedded text
            if file.file_type == models.FileType.APPLICATION_PDF and existing_docs:
                for doc in existing_docs:
                    doc_meta = doc.meta_data or {}
                    has_embedded = doc_meta.get("embedded_text_detected", False)
                    ocr_method = doc_meta.get("extraction_method")

                    if has_embedded or (ocr_method and "no_ocr" in ocr_method):
                        pdfs_with_embedded_text.append(
                            schemas.PdfEmbeddedTextInfo(
                                file_id=file.id,
                                file_name=file.file_name,
                                has_embedded_text=True,
                                existing_document_ocr_method=ocr_method,
                            )
                        )
                        break  # Only report once per file

    return schemas.PreprocessingDuplicatePreview(
        has_duplicates=len(files_with_duplicates) > 0,
        files_with_duplicates=files_with_duplicates,
        total_files_to_process=len(files),
        files_without_duplicates=len(files) - len(files_with_duplicates),
        total_existing_documents=total_existing_docs,
        same_config_duplicates=same_config_duplicates,
        pdfs_with_embedded_text=pdfs_with_embedded_text,
    )


@router.post("/preprocess", response_model=schemas.PreprocessingTask)
async def preprocess_project_data(
    *,
    project_id: int,
    preprocessing_task: schemas.PreprocessingTaskCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    """Start preprocessing with advanced duplicate detection and progress tracking."""
    check_project_access(project_id, current_user, db, "write")

    if not preprocessing_task.inline_config:
        raise HTTPException(
            status_code=400,
            detail="inline_config is required",
        )

    # Get config settings from inline config
    config_dict = preprocessing_task.inline_config.model_dump(exclude={"bypass_celery"})
    # Coerce None → {} so it matches the same normalization applied to stored
    # configs below (`existing.additional_settings or {}`). Without this, a config
    # with empty settings never matches an existing one (None != {}), so a fresh
    # config is created every time — breaking the document versioning this reuse
    # is meant to support.
    new_additional_settings = config_dict.get("additional_settings") or {}

    # Try to find an existing config with matching settings
    # This ensures document versioning works correctly when re-processing with same settings
    # Note: We compare additional_settings (JSON) in Python since SQL JSON comparison is unreliable
    all_configs = (
        db.execute(
            select(models.PreprocessingConfiguration).where(
                models.PreprocessingConfiguration.project_id == project_id,
            )
        )
        .scalars()
        .all()
    )

    config = None
    for existing_config in all_configs:
        existing_settings = existing_config.additional_settings or {}
        # Compare settings dicts (handle None values)
        if existing_settings == new_additional_settings:
            config = existing_config
            break

    # NOTE: flush (not commit) in both branches — every validation below
    # (missing files 404, unconfigured CSV 400, SSRF 400, in-progress 409, …)
    # raises before the task is created, and the request teardown's rollback
    # must discard this config too. Committing here used to leave an orphaned
    # PreprocessingConfiguration row behind on every rejected submission. The
    # config is persisted by the same commit that persists the task.
    if config:
        # Reuse existing config - update name/description if provided
        if config_dict.get("name"):
            config.name = config_dict.get("name")
        if config_dict.get("description"):
            config.description = config_dict.get("description")
        db.add(config)
        db.flush()
    else:
        # Create new configuration
        config = models.PreprocessingConfiguration(
            project_id=project_id,
            name=config_dict.get("name", f"Task {datetime.datetime.now(datetime.UTC)}"),
            description=config_dict.get("description"),
            additional_settings=new_additional_settings,
        )
        db.add(config)
        db.flush()  # assign config.id for the queries below

    # Validate files exist and belong to project.
    #
    # with_for_update() takes row-level locks on the file rows (PostgreSQL),
    # held until the request commits. This serializes concurrent preprocess
    # submissions touching the same files: the HARD CHECK below is a
    # check-then-act, so without the lock two concurrent requests could both
    # pass it and each create PreprocessingTask + FilePreprocessingTask rows
    # for the same files — duplicating the (expensive) OCR work. With the lock,
    # the second request blocks until the first commits, then sees the
    # in-flight tasks and returns 409. On SQLite (dev) FOR UPDATE is a no-op,
    # so the race is not serialized there — acceptable for the test stack.
    files = (
        db.execute(
            select(models.File)
            .where(
                models.File.id.in_(preprocessing_task.file_ids),
                models.File.project_id == project_id,
            )
            .with_for_update()
        )
        .scalars()
        .all()
    )
    if len(files) != len(preprocessing_task.file_ids):
        missing_ids = set(preprocessing_task.file_ids) - {f.id for f in files}
        raise HTTPException(
            status_code=404,
            detail=f"Files not found or don't belong to project: {missing_ids}",
        )

    # Validate CSV/XLSX files have preprocessing strategy configured
    csv_xlsx_types = {
        models.FileType.TEXT_CSV,
        models.FileType.APPLICATION_VND_MS_EXCEL,
        models.FileType.APPLICATION_VND_OPENXMLFORMATS_OFFICEDOCUMENT_SPREADSHEETML_SHEET,
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    unconfigured_files: list[dict[str, str | int]] = []
    for file in files:
        if file.file_type in csv_xlsx_types and not file.preprocessing_strategy:
            unconfigured_files.append(
                {
                    "id": file.id,
                    "name": file.file_name,
                    "type": file.file_type,
                }
            )

    if unconfigured_files:
        file_names = ", ".join(str(f["name"]) for f in unconfigured_files)
        raise HTTPException(
            status_code=400,
            detail={
                "code": "csv_xlsx_needs_config",
                "message": f"CSV/XLSX files need import configuration before preprocessing. "
                f"Please configure: {file_names}",
                "unconfigured_files": unconfigured_files,
            },
        )

    # Check if any OCR engine is enabled when processing image files (PNG/JPEG).
    # PDFs are still allowed - they can use pypdf for embedded text extraction.
    # PDFs without embedded text will show a warning that OCR is not available.
    from ....core.dynamic_settings import get_settings

    settings = get_settings()

    # Validate every user-supplied custom OCR endpoint against the SSRF policy and
    # the (optional) egress allowlist before doing any work, so patient images
    # can't be sent to a blocked or non-approved host. This covers both the
    # top-level task base_url AND the per-config `vision_base_url` in
    # additional_settings — the latter is the actual Vision-OCR egress target and
    # was previously only SSRF-checked (never allowlist-checked) in the worker,
    # letting it bypass ALLOWED_OCR_ENDPOINTS. The worker enforces this too
    # (defense in depth); doing it here fails fast with a clean 400.
    _custom_ocr_endpoints = [
        getattr(preprocessing_task, "base_url", None),
        (new_additional_settings or {}).get("vision_base_url"),
    ]
    if any(_custom_ocr_endpoints):
        from ....utils.url_safety import (
            UnsafeEndpointError,
            enforce_endpoint_allowlist,
            validate_user_endpoint,
        )

        try:
            for _endpoint in _custom_ocr_endpoints:
                if _endpoint:
                    validate_user_endpoint(_endpoint)
                    enforce_endpoint_allowlist(
                        _endpoint, settings.ALLOWED_OCR_ENDPOINTS
                    )
        except UnsafeEndpointError:
            raise HTTPException(
                status_code=400,
                detail="The provided OCR endpoint URL is not allowed.",
            )

    image_types = {
        models.FileType.IMAGE_PNG,
        models.FileType.IMAGE_JPEG,
        "image/png",
        "image/jpeg",
        "image/jpg",
    }

    has_images = any(file.file_type in image_types for file in files)
    any_ocr_enabled = (
        settings.DOCLING_SERVE_ENABLED
        or settings.MISTRAL_OCR_ENABLED
        or settings.VISION_OCR_ENABLED
        or settings.DOCLING_LOCAL_FALLBACK
    )

    if has_images and not any_ocr_enabled:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "no_ocr_engine_enabled",
                "message": "All OCR engines are disabled. At least one OCR engine must be enabled to process image files (PNG/JPEG).",
                "hint": "Enable Local OCR, Mistral OCR, or Vision LLM in Admin Settings. PDF files can still be processed for embedded text extraction.",
            },
        )

    # HARD CHECK: Reject request if any file is already being processed with this config
    # This prevents all race conditions and duplicate document creation
    in_progress_files = []
    for file in files:
        in_progress_file_task = (
            db.execute(
                select(models.FilePreprocessingTask)
                .join(models.PreprocessingTask)
                .where(
                    models.FilePreprocessingTask.file_id == file.id,
                    models.PreprocessingTask.configuration_id == config.id,
                    models.FilePreprocessingTask.status.in_(
                        [
                            models.PreprocessingStatus.PENDING,
                            models.PreprocessingStatus.IN_PROGRESS,
                        ]
                    ),
                )
            )
            .scalars()
            .first()
        )
        if in_progress_file_task:
            in_progress_files.append(
                {
                    "file_id": file.id,
                    "file_name": file.file_name,
                    "task_id": in_progress_file_task.preprocessing_task_id,
                    "status": in_progress_file_task.status.value,
                }
            )

    if in_progress_files:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "files_already_being_processed",
                "message": "One or more files are already being processed with this configuration. "
                "Please wait for the current preprocessing task to complete before resubmitting.",
                "in_progress_files": in_progress_files,
            },
        )

    # Check for existing documents (for skip_existing / force_reprocess logic)
    files_with_existing_docs = []
    for file in files:
        existing_docs = (
            db.execute(
                select(models.Document).where(
                    models.Document.original_file_id == file.id,
                    models.Document.preprocessing_config_id == config.id,
                )
            )
            .scalars()
            .all()
        )
        if existing_docs:
            files_with_existing_docs.append((file, existing_docs))

    # Handle skip_existing: filter out files with existing documents
    files_to_process = []
    skipped_file_names = []
    if preprocessing_task.skip_existing:
        for file in files:
            has_existing = any(f.id == file.id for f, _ in files_with_existing_docs)
            if has_existing:
                skipped_file_names.append(file.file_name)
                continue
            files_to_process.append(file)
    else:
        files_to_process = list(files)

    # Handle force_reprocess: delete existing documents
    if preprocessing_task.force_reprocess:
        docs_to_delete = [
            doc
            for _file, existing_docs in files_with_existing_docs
            for doc in existing_docs
        ]
        doc_ids_to_delete = [doc.id for doc in docs_to_delete]
        if doc_ids_to_delete:
            # trial_results.document_id and evaluation_metrics.document_id are
            # ON DELETE RESTRICT, so deleting a referenced document would raise a
            # raw IntegrityError at commit → 500. Detect it first and return an
            # actionable 409 (mirrors delete_document / delete_file).
            blocked = set(
                db.execute(
                    select(models.TrialResult.document_id).where(
                        models.TrialResult.document_id.in_(doc_ids_to_delete)
                    )
                )
                .scalars()
                .all()
            )
            blocked |= set(
                db.execute(
                    select(models.EvaluationMetric.document_id).where(
                        models.EvaluationMetric.document_id.in_(doc_ids_to_delete)
                    )
                )
                .scalars()
                .all()
            )
            if blocked:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": (
                            "Cannot force-reprocess: some existing documents are "
                            "referenced by trial results or evaluations. Delete "
                            "those trials/evaluations first."
                        ),
                        "referenced_document_ids": sorted(blocked),
                    },
                )
        for doc in docs_to_delete:
            doc.document_sets.clear()
            db.delete(doc)
        files_to_process = list(files)

    # Resolve bypass_celery (from the request body or an inline config) and
    # enforce the admin guard BEFORE creating any DB rows. A non-admin submitting
    # bypass_celery=True must get a 403 without leaving orphaned PENDING task/file
    # rows behind. Mirrors trials.py (which checks before any DB writes).
    bypass_celery = getattr(preprocessing_task, "bypass_celery", False)
    inline_cfg = getattr(preprocessing_task, "inline_config", None)
    if inline_cfg:
        if hasattr(inline_cfg, "bypass_celery"):
            bypass_celery = getattr(inline_cfg, "bypass_celery", False)
        elif isinstance(inline_cfg, dict):
            bypass_celery = inline_cfg.get("bypass_celery", False)
    if bypass_celery and current_user.role != "admin":
        raise HTTPException(403, "Only admins may set bypass_celery")
    # With Celery disabled there is no worker, no queue, and no sweeper — a
    # non-bypass submission could only ever fail at dispatch. Refuse it up
    # front with an explicit reason instead of creating task rows that
    # immediately die with an opaque "could not queue" error.
    if settings.DISABLE_CELERY and not bypass_celery:
        raise HTTPException(
            status_code=503,
            detail="Background processing is disabled on this server "
            "(DISABLE_CELERY). Enable Celery, or run with bypass_celery "
            "(admins only).",
        )

    # Create preprocessing task
    task = models.PreprocessingTask(
        project_id=project_id,
        configuration_id=config.id,
        total_files=len(files_to_process),
        rollback_on_cancel=preprocessing_task.rollback_on_cancel,
    )

    # Store custom API credentials for the OCR backend. The api_key is stored
    # encrypted on the row (api_key_encrypted) and decrypted inside the Celery
    # task — it never traverses the broker as plaintext and never sits in the
    # plaintext task_metadata JSON. base_url is not secret, so it stays in
    # task_metadata.
    if preprocessing_task.api_key and preprocessing_task.base_url:
        task.api_key = preprocessing_task.api_key
        task.task_metadata = {
            "custom_api_used": True,
            "api_base_url": preprocessing_task.base_url,
        }

    db.add(task)
    db.flush()  # Ensure task.id is populated before creating file tasks

    # Create file tasks for files to process
    file_tasks_to_process = []
    for file in files_to_process:
        file_task = models.FilePreprocessingTask(
            preprocessing_task_id=task.id,
            file_id=file.id,
            file_name=file.file_name,
        )
        db.add(file_task)
        file_tasks_to_process.append(file_task)

    db.commit()

    # Update task with skipped files information
    if skipped_file_names:
        if not task.task_metadata:
            task.task_metadata = {}
        task.task_metadata["skipped_files"] = len(skipped_file_names)
        task.task_metadata["skipped_file_names"] = skipped_file_names
        task.skipped_files = len(skipped_file_names)

    if not file_tasks_to_process:
        task.status = models.PreprocessingStatus.COMPLETED
        task.message = f"All files already processed with these settings. {len(skipped_file_names)} files skipped."
        task.completed_at = datetime.datetime.now(datetime.UTC)
        db.commit()
        db.refresh(task)
        return schemas.PreprocessingTask.model_validate(task)

    # Set initial message
    if skipped_file_names:
        task.message = f"Processing {len(file_tasks_to_process)} files. {len(skipped_file_names)} files already processed and skipped."

    # Start processing
    if bypass_celery:
        logger.info("Bypassing Celery for preprocessing task %s", task.id)
        from ....utils.preprocessing import PreprocessingPipeline

        try:
            # Bypass path runs synchronously in-process (no Celery broker), so
            # threading the in-memory credentials through the constructor is
            # safe here. The Celery path below does NOT pass them — it reads
            # them from the encrypted task row inside the worker.
            pipeline = PreprocessingPipeline(
                db,
                task.id,
                api_key=preprocessing_task.api_key,
                base_url=preprocessing_task.base_url,
            )
            pipeline.process()
        except Exception as e:
            task.status = models.PreprocessingStatus.FAILED
            task.message = internal_error_message(
                e, actor=current_user, prefix="Processing failed"
            )
            db.commit()
            logger.error(
                "Preprocessing failed for task %s: %s", task.id, e, exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail="Preprocessing failed. See server logs for details.",
            )
    else:
        # Credentials are NOT passed through the broker: the api_key is stored
        # encrypted on the task row and decrypted inside the worker; base_url
        # is read from task_metadata. Passing either as a Celery arg would
        # serialize the plaintext key into Redis.
        try:
            from ....celery.preprocessing import process_files_async

            result = process_files_async.delay(task.id)
        except Exception as e:
            # Dispatch failed (broker unreachable, or Celery disabled). The task
            # + its file tasks were already committed as PENDING, and the orphan
            # sweeper can't reap never-started rows (NULL heartbeat/started_at),
            # so they'd sit PENDING forever. Mark them FAILED so the user sees the
            # failure and can retry, instead of a silent stuck task + raw 500.
            task.status = models.PreprocessingStatus.FAILED
            task.message = internal_error_message(
                e, actor=current_user, prefix="Failed to queue preprocessing"
            )
            task.completed_at = datetime.datetime.now(datetime.UTC)
            for ft in file_tasks_to_process:
                ft.status = models.PreprocessingStatus.FAILED
                ft.error_message = "Could not be queued for processing."
            db.commit()
            logger.error(
                "Failed to dispatch preprocessing task %s: %s",
                task.id,
                e,
                exc_info=True,
            )
            raise HTTPException(
                status_code=503,
                detail="Could not queue preprocessing for background processing. "
                "Please try again later.",
            )
        task.celery_task_id = result.id
        db.commit()

    db.commit()
    db.refresh(task)

    # Accountability: record PHI egress when preprocessing uses a remote OCR
    # engine or a custom external endpoint (document images/text leave the host).
    # The local Docling/Tesseract path is not egress and is not recorded here.
    ocr_engine = (new_additional_settings or {}).get("ocr_engine", "docling_tesseract")
    custom_base = preprocessing_task.base_url or None
    if ocr_engine in _REMOTE_OCR_ENGINES or custom_base:
        from urllib.parse import urlparse

        record_audit(
            AuditAction.OCR_EXTERNAL_CALL,
            actor=current_user,
            resource_type="preprocessing_task",
            resource_id=task.id,
            project_id=project_id,
            detail={
                "ocr_engine": ocr_engine,
                "endpoint_host": urlparse(custom_base).hostname
                if custom_base
                else None,
                "file_count": len(file_tasks_to_process),
                "mode": "sync" if bypass_celery else "celery",
            },
        )
    return schemas.PreprocessingTask.model_validate(task)


@router.get("/preprocess", response_model=List[schemas.PreprocessingTask])
def get_preprocessing_tasks(
    *,
    project_id: int,
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[schemas.PreprocessingTask]:
    """Get preprocessing tasks for a project."""
    check_project_access(project_id, current_user, db, "read")

    query = (
        select(models.PreprocessingTask)
        .where(models.PreprocessingTask.project_id == project_id)
        .options(
            selectinload(models.PreprocessingTask.file_tasks).selectinload(
                models.FilePreprocessingTask.file
            ),
            selectinload(models.PreprocessingTask.configuration),
        )
    )

    if status:
        try:
            status_enum = models.PreprocessingStatus(status)
            query = query.where(models.PreprocessingTask.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    query = query.order_by(models.PreprocessingTask.created_at.desc())
    query = query.limit(limit).offset(offset)

    tasks = db.execute(query).scalars().all()
    return [schemas.PreprocessingTask.model_validate(task) for task in tasks]


@router.get("/preprocess/{task_id}", response_model=schemas.PreprocessingTask)
def get_preprocessing_task(
    *,
    project_id: int,
    task_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    """Get detailed information about a preprocessing task."""
    check_project_access(project_id, current_user, db, "read")

    task = db.execute(
        select(models.PreprocessingTask)
        .where(
            models.PreprocessingTask.id == task_id,
            models.PreprocessingTask.project_id == project_id,
        )
        .options(
            selectinload(models.PreprocessingTask.file_tasks).selectinload(
                models.FilePreprocessingTask.file
            ),
            selectinload(models.PreprocessingTask.configuration),
        )
    ).scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return schemas.PreprocessingTask.model_validate(task)


@router.post(
    "/preprocess/{task_id}/cancel",
    response_model=schemas.PreprocessingTask,
)
def cancel_preprocessing_task(
    *,
    project_id: int,
    task_id: int,
    keep_processed: bool = Query(False, description="Keep already processed files"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    """Cancel a preprocessing task with option to keep or rollback processed files."""

    check_project_access(project_id, current_user, db, "write")

    # Load task with file_tasks relationship
    task = (
        db.query(models.PreprocessingTask)
        .options(
            selectinload(models.PreprocessingTask.file_tasks),
            selectinload(models.PreprocessingTask.configuration),
        )
        .filter(
            models.PreprocessingTask.id == task_id,
            models.PreprocessingTask.project_id == project_id,
        )
        .first()
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in [
        models.PreprocessingStatus.COMPLETED,
        models.PreprocessingStatus.CANCELLED,
    ]:
        raise HTTPException(
            status_code=400, detail=f"Cannot cancel task in {task.status} status"
        )

    # Set cancellation flag
    task.is_cancelled = True
    task.status = models.PreprocessingStatus.CANCELLED
    task.completed_at = datetime.datetime.now(datetime.UTC)

    # Persist the keep-vs-rollback decision so a still-running (or about-to-run,
    # between-chunk) worker agrees with us: the worker's finalization only checks
    # `rollback_on_cancel`, so if the user asked to KEEP but we didn't clear the
    # flag, the worker would delete the documents anyway. Force it off here.
    if keep_processed:
        task.rollback_on_cancel = False

    # Rollback logic: remove processed docs if requested. Include CANCELLED and
    # FAILED file tasks, not just COMPLETED ones: a row-by-row CSV file task
    # commits documents in batches, so one cancelled or failed mid-flight can
    # still have many committed docs. This mirrors the worker's finalization
    # rollback — important because when cancel lands while a self-requeue is
    # merely queued (no worker running), the worker's rollback never runs and
    # this endpoint is the only rollback path.
    deleted_count = 0
    if task.rollback_on_cancel:
        rollback_statuses = (
            models.PreprocessingStatus.COMPLETED,
            models.PreprocessingStatus.CANCELLED,
            models.PreprocessingStatus.FAILED,
        )
        candidate_docs = [
            doc
            for file_task in task.file_tasks
            if file_task.status in rollback_statuses
            for doc in file_task.documents
        ]
        # trial_results.document_id / evaluation_metrics.document_id are
        # ON DELETE RESTRICT — deleting a referenced document would raise a raw
        # IntegrityError at commit and fail the whole cancel with a 500. Skip
        # referenced documents (keep them) instead: the cancel itself must
        # succeed. Mirrors the force_reprocess guard in preprocess submission.
        blocked: set[int] = set()
        candidate_ids = [doc.id for doc in candidate_docs]
        if candidate_ids:
            blocked = set(
                db.execute(
                    select(models.TrialResult.document_id).where(
                        models.TrialResult.document_id.in_(candidate_ids)
                    )
                ).scalars()
            )
            blocked |= set(
                db.execute(
                    select(models.EvaluationMetric.document_id).where(
                        models.EvaluationMetric.document_id.in_(candidate_ids)
                    )
                ).scalars()
            )
        for doc in candidate_docs:
            if doc.id in blocked:
                continue
            doc.document_sets.clear()
            db.delete(doc)
            deleted_count += 1
        task.message = (
            f"Task cancelled and {deleted_count} processed documents rolled back"
        )
        if blocked:
            task.message += (
                f"; {len(blocked)} document(s) kept because trial results or "
                "evaluations still reference them"
            )
    else:
        task.message = "Task cancelled, keeping processed documents"

    # Mark all still-pending/in-progress file tasks as cancelled
    for file_task in task.file_tasks:
        if file_task.status in [
            models.PreprocessingStatus.PENDING,
            models.PreprocessingStatus.IN_PROGRESS,
        ]:
            file_task.status = models.PreprocessingStatus.CANCELLED
            file_task.completed_at = datetime.datetime.now(datetime.UTC)

    db.commit()

    # Accountability: cancelling can DELETE documents (a destructive mutation),
    # so record who did it and how many docs were rolled back.
    record_audit(
        AuditAction.CANCEL,
        actor=current_user,
        resource_type="preprocessing_task",
        resource_id=task.id,
        project_id=project_id,
        detail={
            "kept_processed": keep_processed,
            "documents_rolled_back": deleted_count,
        },
    )

    # Refresh to ensure we get the latest data including updated file_tasks
    db.refresh(task)

    # Best-effort WebSocket broadcast: a task cancelled before (or between)
    # worker heartbeats never emits a terminal update itself, leaving other
    # clients' progress spinners stuck on the pre-cancel status.
    try:
        from ....celery.task_signals import _broadcast_preprocessing_update

        _broadcast_preprocessing_update(task, event="cancelled")
    except Exception as e:
        logger.debug("Cancel broadcast failed: %s", e)

    return schemas.PreprocessingTask.model_validate(task)


@router.get("/preprocess/{task_id}/progress")
def get_preprocessing_progress(
    *,
    project_id: int,
    task_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    """Get detailed progress of a preprocessing task."""
    check_project_access(project_id, current_user, db, "read")

    task = db.execute(
        select(models.PreprocessingTask).where(
            models.PreprocessingTask.id == task_id,
            models.PreprocessingTask.project_id == project_id,
        )
    ).scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Calculate estimated completion time if in progress
    if (
        task.status == models.PreprocessingStatus.IN_PROGRESS
        and task.processed_files > 0
    ):
        elapsed = datetime.datetime.now(datetime.UTC) - (
            task.started_at or datetime.datetime.now(datetime.UTC)
        )
        avg_time_per_file = elapsed.total_seconds() / task.processed_files
        remaining_files = task.total_files - task.processed_files - task.failed_files

        if remaining_files > 0:
            estimated_remaining = datetime.timedelta(
                seconds=avg_time_per_file * remaining_files
            )
            task.estimated_completion = (
                datetime.datetime.now(datetime.UTC) + estimated_remaining
            )

    return schemas.PreprocessingTask.model_validate(task)


@router.post("/preprocess/{task_id}/retry-failed")
def retry_failed_files(
    *,
    project_id: int,
    task_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PreprocessingTask:
    """Create a new task to retry failed files from a previous task.

    POST (not GET) because it mutates state: it creates a PreprocessingTask,
    commits, and dispatches Celery work. A GET would be unsafe — browser
    prefetch/link prefetch or crawlers could silently trigger retries.
    """
    check_project_access(project_id, current_user, db, "write")

    original_task = db.execute(
        select(models.PreprocessingTask)
        .where(
            models.PreprocessingTask.id == task_id,
            models.PreprocessingTask.project_id == project_id,
        )
        .options(selectinload(models.PreprocessingTask.file_tasks))
    ).scalar_one_or_none()

    if not original_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Refuse to retry while the original task is still running — its worker
    # may still write to the same file tasks/documents.
    if original_task.status in (
        models.PreprocessingStatus.PENDING,
        models.PreprocessingStatus.IN_PROGRESS,
    ):
        raise HTTPException(
            status_code=409,
            detail="Task is still running. Wait for it to finish (or cancel it) "
            "before retrying failed files.",
        )

    # Get failed file IDs
    failed_file_ids = [
        ft.file_id
        for ft in original_task.file_tasks
        if ft.status == models.PreprocessingStatus.FAILED
    ]

    if not failed_file_ids:
        raise HTTPException(status_code=400, detail="No failed files to retry")

    # In-flight guard: a double-click (or a second client) would spawn a
    # second retry over the same files; both workers then upsert the same
    # documents and the first task false-fails on the uniqueness constraint.
    in_flight = db.execute(
        select(models.FilePreprocessingTask.id)
        .join(
            models.PreprocessingTask,
            models.FilePreprocessingTask.preprocessing_task_id
            == models.PreprocessingTask.id,
        )
        .where(
            models.FilePreprocessingTask.file_id.in_(failed_file_ids),
            models.PreprocessingTask.project_id == project_id,
            models.PreprocessingTask.status.in_(
                [
                    models.PreprocessingStatus.PENDING,
                    models.PreprocessingStatus.IN_PROGRESS,
                ]
            ),
        )
        .limit(1)
    ).first()
    if in_flight:
        raise HTTPException(
            status_code=409,
            detail="A retry for these files is already in progress.",
        )

    # Create new task with same configuration. Carry over custom OCR
    # With Celery disabled a retry could only die at dispatch — refuse up front
    # (same guard as the main preprocess endpoint) before creating any rows.
    from ....core.dynamic_settings import get_settings

    if get_settings().DISABLE_CELERY:
        raise HTTPException(
            status_code=503,
            detail="Background processing is disabled on this server "
            "(DISABLE_CELERY), so failed files cannot be retried. "
            "Enable Celery, or start a new run with bypass_celery (admins only).",
        )

    # credentials (encrypted key + api_base_url metadata) so a retry of a
    # custom-API run doesn't silently fall back to the default backend.
    new_task = models.PreprocessingTask(
        project_id=project_id,
        configuration_id=original_task.configuration_id,
        total_files=len(failed_file_ids),
        rollback_on_cancel=original_task.rollback_on_cancel,
        api_key_encrypted=original_task.api_key_encrypted,
        task_metadata=dict(original_task.task_metadata)
        if original_task.task_metadata
        else None,
    )
    db.add(new_task)
    db.commit()

    # Create file tasks for failed files
    for file_id in failed_file_ids:
        file_task = models.FilePreprocessingTask(
            preprocessing_task_id=new_task.id, file_id=file_id
        )
        db.add(file_task)

    db.commit()

    # Start processing. Guard the dispatch: if the broker is unreachable, the
    # task + its file tasks were already committed PENDING, and the sweeper
    # can't reap never-started rows (NULL heartbeat/started_at), so they'd sit
    # PENDING forever. Mark them FAILED on dispatch failure — mirrors the main
    # preprocess endpoint.
    try:
        from ....celery.preprocessing import process_files_async

        result = process_files_async.delay(new_task.id)
    except Exception as e:
        new_task.status = models.PreprocessingStatus.FAILED
        new_task.message = internal_error_message(
            e, actor=current_user, prefix="Failed to queue preprocessing"
        )
        new_task.completed_at = datetime.datetime.now(datetime.UTC)
        for ft in new_task.file_tasks:
            ft.status = models.PreprocessingStatus.FAILED
            ft.error_message = "Could not be queued for processing."
        db.commit()
        logger.error(
            "Failed to dispatch retry preprocessing task %s: %s",
            new_task.id,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail="Could not queue preprocessing for background processing. "
            "Please try again later.",
        )
    new_task.celery_task_id = result.id
    db.commit()

    # Accountability: a retry re-sends the failed files to the OCR engine, so
    # record the PHI egress just as the original dispatch did (custom endpoint
    # or a remote OCR engine). The local Docling/Tesseract path is not egress.
    config = db.get(models.PreprocessingConfiguration, new_task.configuration_id)
    cfg_settings = (config.additional_settings if config else None) or {}
    ocr_engine = cfg_settings.get("ocr_engine", "docling_tesseract")
    custom_base = (new_task.task_metadata or {}).get("api_base_url")
    if ocr_engine in _REMOTE_OCR_ENGINES or custom_base:
        from urllib.parse import urlparse

        record_audit(
            AuditAction.OCR_EXTERNAL_CALL,
            actor=current_user,
            resource_type="preprocessing_task",
            resource_id=new_task.id,
            project_id=project_id,
            detail={
                "ocr_engine": ocr_engine,
                "endpoint_host": urlparse(custom_base).hostname
                if custom_base
                else None,
                "file_count": len(failed_file_ids),
                "mode": "celery",
                "retry_of": task_id,
            },
        )

    db.refresh(new_task)
    return schemas.PreprocessingTask.model_validate(new_task)
