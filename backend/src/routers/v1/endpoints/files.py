"""File management endpoints for projects."""

import datetime
import io
import json
import zipfile

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.orm import Session, selectinload

from .... import models, schemas
from ....core.security import get_current_user
from ....dependencies import (
    calculate_file_hash,
    get_db,
    get_file,
    remove_file,
    save_file,
)
from ....utils.enums import FileCreator
from ....utils.helpers import detect_structured_mime

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
    # You could extend this with a project_members table for shared projects
    raise HTTPException(
        status_code=403, detail=f"Not authorized to {permission} this project"
    )


@router.get("", response_model=list[schemas.File])
def get_project_files(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    # Filter parameters
    search: str | None = Query(None, description="Search in filename"),
    file_type: str | None = Query(None, description="Filter by file type"),
    file_creator: FileCreator | None = Query(None),
    date_from: datetime.datetime | None = Query(None),
    date_to: datetime.datetime | None = Query(None),
    min_size: int | None = Query(None, description="Minimum file size in bytes"),
    max_size: int | None = Query(None, description="Maximum file size in bytes"),
    # Pagination
    skip: int = Query(0, ge=0),
    limit: int = Query(0, ge=0, le=1000),
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.File]:
    """Get project files with advanced filtering"""
    check_project_access(project_id, current_user, db)

    query = select(models.File).where(models.File.project_id == project_id)

    # Apply filters
    if search:
        query = query.where(models.File.file_name.ilike(f"%{search}%"))
    if file_type:
        query = query.where(models.File.file_type == file_type)
    if file_creator is not None:
        query = query.where(models.File.file_creator == file_creator)
    if date_from:
        query = query.where(models.File.created_at >= date_from)
    if date_to:
        query = query.where(models.File.created_at <= date_to)
    if min_size is not None:
        query = query.where(models.File.file_size >= min_size)
    if max_size is not None:
        query = query.where(models.File.file_size <= max_size)

    # Order by created_at desc and apply pagination
    if limit == 0:
        query = query.order_by(models.File.created_at.desc()).offset(skip)
    else:
        query = query.order_by(models.File.created_at.desc()).offset(skip).limit(limit)

    files = list(db.execute(query).scalars().all())
    return [schemas.File.model_validate(file) for file in files]


@router.get("/stats", response_model=dict)
def get_file_stats(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_creator: FileCreator | None = Query(None),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Get file statistics for the project"""
    check_project_access(project_id, current_user, db)

    # Base query
    base_query = select(models.File).where(models.File.project_id == project_id)
    if file_creator is not None:
        base_query = base_query.where(models.File.file_creator == file_creator)

    # Get total count and size
    stats = db.execute(
        select(
            func.count(models.File.id).label("total_files"),
            func.sum(models.File.file_size).label("total_size"),
            func.count(distinct(models.File.file_hash)).label("unique_files"),
        ).where(
            models.File.project_id == project_id,
            models.File.file_creator == file_creator if file_creator else True,
        )
    ).first()

    # Get files by type
    type_query = select(
        models.File.file_type,
        func.count(models.File.id).label("count"),
        func.sum(models.File.file_size).label("size"),
    ).where(models.File.project_id == project_id)

    if file_creator is not None:
        type_query = type_query.where(models.File.file_creator == file_creator)

    type_stats = db.execute(type_query.group_by(models.File.file_type)).all()

    # Get recent files (last 7 days)
    week_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=7)
    recent_query = select(func.count(models.File.id)).where(
        and_(models.File.project_id == project_id, models.File.created_at >= week_ago)
    )

    if file_creator is not None:
        recent_query = recent_query.where(models.File.file_creator == file_creator)

    recent_count = db.execute(recent_query).scalar()

    return {
        "total_files": stats.total_files or 0,
        "total_size": stats.total_size or 0,
        "unique_files": stats.unique_files or 0,
        "recent_files": recent_count or 0,
        "duplicates": (stats.total_files or 0) - (stats.unique_files or 0),
        "by_type": [
            {"type": t.file_type, "count": t.count, "size": t.size or 0}
            for t in type_stats
        ],
    }


@router.get("/{file_id}", response_model=schemas.File)
def get_project_file(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.File:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's files"
        )

    file: models.File | None = db.execute(
        select(models.File).where(
            models.File.project_id == project_id, models.File.id == file_id
        )
    ).scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return schemas.File.model_validate(file)


@router.get("/{file_id}/content", response_class=Response)
def get_project_file_content(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_id: int,
    preview: bool = Query(False),
    current_user: models.User = Depends(get_current_user),
) -> Response:
    """Retrieve the content of a file associated with a project."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project's files"
        )

    file: models.File | None = db.execute(
        select(models.File).where(
            models.File.project_id == project_id, models.File.id == file_id
        )
    ).scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Retrieve the file content from storage
    file_content = get_file(file.file_uuid)

    if preview:
        headers = {"Content-Disposition": f"inline; filename={file.file_name}"}
    else:
        headers = {"Content-Disposition": f"attachment; filename={file.file_name}"}
    return Response(content=file_content, media_type=file.file_type, headers=headers)


@router.post("", response_model=schemas.File)
def upload_file(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file: UploadFile = File(...),
    file_info: str = Form(...),
    current_user: models.User = Depends(get_current_user),
) -> schemas.File:
    """Upload a file with duplicate detection and *server-side MIME normalization*"""
    try:
        file_info = schemas.FileCreate.model_validate_json(file_info)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in file_info")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    check_project_access(project_id, current_user, db, permission="write")

    # Read file content *once*
    file_content = file.file.read()
    file_size = len(file_content)
    file_hash = calculate_file_hash(file_content)

    # --- Normalize MIME based on content + filename (fixes CSV mislabeled as vnd.ms-excel) ---
    # Prefer the originally submitted file name if present in the upload field; otherwise use the JSON's file_name.
    incoming_name = file.filename or file_info.file_name
    normalized_mime = detect_structured_mime(
        file_name=incoming_name,
        content=file_content,
        provided_mime=file.content_type or getattr(file_info, "file_type", None),
    )

    # Check duplicates by hash
    existing_file = db.execute(
        select(models.File).where(
            and_(
                models.File.project_id == project_id, models.File.file_hash == file_hash
            )
        )
    ).scalar_one_or_none()

    if existing_file:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "File already exists",
                "existing_file": {
                    "id": existing_file.id,
                    "file_name": existing_file.file_name,
                    "created_at": existing_file.created_at.isoformat(),
                },
            },
        )

    # Finalize file info:
    # - Name: prefer actual upload name
    # - Type: normalized
    # - Store file_metadata from JSON if present
    file_info.file_name = incoming_name
    file_info.file_type = normalized_mime or "application/octet-stream"

    # Save the file bytes and persist DB row
    file_uuid = save_file(file_content)

    new_file = models.File(
        **file_info.model_dump(
            exclude={"file_uuid", "file_size", "file_hash", "file_metadata"}
        ),
        project_id=project_id,
        file_uuid=file_uuid,
        file_size=file_size,
        file_hash=file_hash,
        file_metadata=getattr(file_info, "file_metadata", None),
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return schemas.File.model_validate(new_file)


@router.post("/{file_id}/configure", response_model=schemas.File)
def configure_file_import(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_id: int,
    config: dict = Body(...),
    current_user: models.User = Depends(get_current_user),
) -> schemas.File:
    """
    Set/update import config and preprocessing strategy for a file.
    """
    check_project_access(project_id, current_user, db, permission="write")

    file = db.execute(
        select(models.File).where(
            models.File.project_id == project_id, models.File.id == file_id
        )
    ).scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Accept "preprocessing_strategy" and/or "file_metadata"
    if "preprocessing_strategy" in config:
        file.preprocessing_strategy = config["preprocessing_strategy"]
    if "file_metadata" in config:
        file.file_metadata = config["file_metadata"]
    elif any(
        k in config
        for k in (
            "delimiter",
            "has_header",
            "row_split",
            "case_id_column",
            "text_columns",
        )
    ):
        file.file_metadata = {**(file.file_metadata or {}), **config}

    db.add(file)
    db.commit()
    db.refresh(file)

    return schemas.File.model_validate(file)


@router.get("/{file_id}/preview-rows", response_model=dict)
def preview_structured_file(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_id: int,
    delimiter: str = Query(None, description="Delimiter for CSV"),
    encoding: str = Query("utf-8"),
    has_header: bool = Query(True),
    sheet: str = Query(None),
    max_rows: int = Query(10, ge=1, le=50),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """
    Return first N rows from CSV/XLSX for configuration/preview.
    Robust handling for:
      - Ambiguous MIME types (e.g., CSV uploaded as application/vnd.ms-excel)
      - Empty sheets
      - Blank headers / None cells
      - Invalid sheet names
      - Truncated CSV samples mid-line
      - Very long cells (clipped in preview)
      - Legacy XLS explicitly unsupported for preview
    """
    check_project_access(project_id, current_user, db)

    file = db.execute(
        select(models.File).where(
            models.File.project_id == project_id, models.File.id == file_id
        )
    ).scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    file_content = get_file(file.file_uuid)
    filename = (file.file_name or "").lower()

    # IMPORTANT: get Enum value string, not str(Enum)
    try:
        mime = (file.file_type.value or "").lower()
    except AttributeError:
        mime = (str(file.file_type or "")).lower()

    import csv as _csv
    import io as _io

    # ---- Helpers ----
    def _dedupe_headers(headers: list[str]) -> list[str]:
        seen: dict[str, int] = {}
        out: list[str] = []
        for h in headers:
            if h in seen:
                seen[h] += 1
                out.append(f"{h} ({seen[h]})")
            else:
                seen[h] = 1
                out.append(h)
        return out

    def _coerce_row(row: list) -> list:
        return [("" if v is None else v) for v in row]

    def _normalize_headers(
        raw_headers: list, width_fallback: int | None = None
    ) -> list[str]:
        if not raw_headers and width_fallback:
            headers = [f"Column {i + 1}" for i in range(width_fallback)]
        else:
            headers = []
            for idx, h in enumerate(raw_headers):
                if isinstance(h, str) and h.strip():
                    headers.append(h)
                else:
                    headers.append(f"Column {idx + 1}")
        return _dedupe_headers(headers)

    def _is_zip_xlsx(buf: bytes) -> bool:
        # XLSX is a ZIP: PK\x03\x04
        return len(buf) >= 4 and buf[:4] == b"PK\x03\x04"

    def _is_ole_xls(buf: bytes) -> bool:
        # Legacy XLS is OLE2/CFB: D0 CF 11 E0 A1 B1 1A 1E
        sig = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\x1e"
        return len(buf) >= len(sig) and buf[: len(sig)] == sig

    def _decide_format() -> str:
        """
        Decide 'csv' | 'xlsx' | 'xls' based on magic bytes and filename.
        Treat application/vnd.ms-excel as ambiguous (often CSV).
        """
        head = file_content[:16]

        # Strong magic checks first
        if _is_zip_xlsx(head) or filename.endswith(".xlsx"):
            return "xlsx"
        if _is_ole_xls(head) or filename.endswith(".xls"):
            return "xls"

        # CSV by extension or by elimination
        if filename.endswith(".csv"):
            return "csv"

        # MIME heuristics (browsers lie on Windows)
        if mime == "text/csv":
            return "csv"
        if mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            # Double-check it's a real ZIP, else fall back to CSV
            return "xlsx" if _is_zip_xlsx(head) else "csv"
        if mime == "application/vnd.ms-excel":
            # Ambiguous; prefer magic: ZIP -> xlsx, OLE -> xls, else CSV
            if _is_zip_xlsx(head):
                return "xlsx"
            if _is_ole_xls(head):
                return "xls"
            return "csv"

        # Default: treat as CSV
        return "csv"

    # Limit single cell payload size
    CLIP = 5000
    decided = _decide_format()

    # ---------------- CSV ----------------
    if decided == "csv":
        sample_bytes = file_content[:131072]  # 128 KiB
        try:
            sample = sample_bytes.decode(encoding, errors="replace")
            detected_encoding = encoding
        except Exception:
            sample = sample_bytes.decode("utf-8", errors="replace")
            detected_encoding = "utf-8"

        last_nl = sample.rfind("\n")
        if last_nl != -1:
            sample = sample[: last_nl + 1]

        # Detect delimiter if not provided
        sniffer = _csv.Sniffer()
        detected_delimiter = delimiter
        if not delimiter:
            try:
                dialect = sniffer.sniff(sample)
                detected_delimiter = dialect.delimiter
            except Exception:
                detected_delimiter = ","

        reader = _csv.reader(_io.StringIO(sample), delimiter=detected_delimiter)
        all_rows = list(reader)

        if not all_rows:
            return {
                "headers": [],
                "rows": [],
                "detected_delimiter": detected_delimiter,
                "detected_encoding": detected_encoding,
                "total_rows": 0,
                "truncated": False,
            }

        if has_header:
            raw_headers = _coerce_row(all_rows[0])
            headers = _normalize_headers(raw_headers)
            data_rows = all_rows[1 : 1 + max_rows]
        else:
            width = len(all_rows[0])
            headers = _normalize_headers([], width_fallback=width)
            data_rows = all_rows[:max_rows]

        preview_rows = []
        for r in data_rows:
            r = _coerce_row(r)
            preview_rows.append(
                [
                    (
                        c
                        if not isinstance(c, str) or len(c) <= CLIP
                        else (c[:CLIP] + "…")
                    )
                    for c in r
                ]
            )

        total_rows = len(all_rows) - (1 if has_header else 0)
        truncated = len(all_rows) > (max_rows + (1 if has_header else 0))

        return {
            "headers": headers,
            "rows": preview_rows,
            "detected_delimiter": detected_delimiter,
            "detected_encoding": detected_encoding,
            "total_rows": max(0, total_rows),
            "truncated": truncated,
        }

    # --------------- XLSX ----------------
    if decided == "xlsx":
        import openpyxl

        wb = openpyxl.load_workbook(
            _io.BytesIO(file_content), read_only=True, data_only=True
        )

        # Guard sheet selection
        if not sheet or sheet not in wb.sheetnames:
            sheet = wb.sheetnames[0]
        ws = wb[sheet]
        sheets = wb.sheetnames

        rows: list[list] = []
        take = max_rows + (1 if has_header else 0)
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            rows.append(_coerce_row(list(row)))
            if i + 1 >= take:
                break

        try:
            total_rows_raw = int(ws.max_row or 0)
        except Exception:
            total_rows_raw = 0
        total_rows = max(0, total_rows_raw - (1 if has_header else 0))
        truncated = total_rows > max_rows

        if not rows:
            return {
                "headers": [],
                "rows": [],
                "sheets": sheets,
                "total_rows": 0,
                "truncated": False,
            }

        if has_header:
            headers = _normalize_headers(rows[0])
            data_rows = rows[1:]
        else:
            width = len(rows[0])
            headers = _normalize_headers([], width_fallback=width)
            data_rows = rows

        preview_rows = []
        for r in data_rows[:max_rows]:
            preview_rows.append(
                [
                    (
                        c
                        if not isinstance(c, str) or len(c) <= CLIP
                        else (c[:CLIP] + "…")
                    )
                    for c in r
                ]
            )

        return {
            "headers": headers,
            "rows": preview_rows,
            "sheets": sheets,
            "total_rows": total_rows,
            "truncated": truncated,
        }

    # --------------- Legacy XLS (binary) ----------------
    if decided == "xls":
        raise HTTPException(
            status_code=400,
            detail=(
                "Preview for legacy .xls (binary) files is not supported. "
                "Please convert the file to .xlsx or .csv and try again."
            ),
        )

    raise HTTPException(
        status_code=400, detail="Preview not supported for this file type"
    )


@router.post("/check-duplicates", response_model=list[dict])
def check_duplicates(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    files: list[dict] = Body(..., description="List of {filename, hash} objects"),
    current_user: models.User = Depends(get_current_user),
) -> list[dict]:
    """Check for duplicate files before uploading"""
    check_project_access(project_id, current_user, db)

    results = []
    for file_info in files:
        existing = db.execute(
            select(models.File).where(
                and_(
                    models.File.project_id == project_id,
                    models.File.file_hash == file_info["hash"],
                )
            )
        ).scalar_one_or_none()

        results.append(
            {
                "filename": file_info["filename"],
                "hash": file_info["hash"],
                "exists": existing is not None,
                "existing_file": {
                    "id": existing.id,
                    "file_name": existing.file_name,
                    "created_at": existing.created_at.isoformat(),
                }
                if existing
                else None,
            }
        )

    return results


@router.delete("/{file_id}", response_model=schemas.File)
def delete_file(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_id: int,
    force: bool = Query(False, description="Force delete even if linked"),
    current_user: models.User = Depends(get_current_user),
) -> schemas.File:
    """Delete a file with safety checks"""
    check_project_access(project_id, current_user, db, permission="write")

    file = db.execute(
        select(models.File)
        .options(
            selectinload(models.File.documents_as_original),
            selectinload(models.File.documents_as_preprocessed),
            selectinload(models.File.preprocessing_tasks),
            selectinload(models.File.file_preprocessing_tasks),
        )
        .where(models.File.project_id == project_id, models.File.id == file_id)
    ).scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Check if file is linked to other resources
    is_linked = (
        len(file.documents_as_original) > 0
        or len(file.documents_as_preprocessed) > 0
        or len(file.preprocessing_tasks) > 0
        or len(file.file_preprocessing_tasks) > 0
    )

    if is_linked and not force:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "File is linked to other resources",
                "links": {
                    "documents": len(file.documents_as_original)
                    + len(file.documents_as_preprocessed),
                    "preprocessing_tasks": len(file.preprocessing_tasks)
                    + len(file.file_preprocessing_tasks),
                },
            },
        )

    # Delete the file content from storage
    try:
        remove_file(file.file_uuid)
    except FileNotFoundError:
        # Log the error but continue with database deletion
        pass

    db.delete(file)
    db.commit()

    return schemas.File.model_validate(file)


@router.post("/batch-delete", response_model=dict)
def batch_delete_files(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_ids: list[int] = Body(...),
    force: bool = Body(False),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Delete multiple files at once"""
    check_project_access(project_id, current_user, db, permission="write")

    deleted = []
    errors = []

    for file_id in file_ids:
        try:
            _ = delete_file(
                db=db,
                project_id=project_id,
                file_id=file_id,
                force=force,
                current_user=current_user,
            )
            deleted.append(file_id)
        except HTTPException as e:
            errors.append({"file_id": file_id, "error": e.detail})
        except Exception as e:
            errors.append({"file_id": file_id, "error": str(e)})

    return {
        "deleted": deleted,
        "errors": errors,
        "total_deleted": len(deleted),
        "total_errors": len(errors),
    }


@router.post("/download-zip")
async def download_files_as_zip(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_ids: list[int] = Body(...),
    include_metadata: bool = Body(True),
    current_user: models.User = Depends(get_current_user),
) -> Response:
    """Download multiple files as a ZIP archive"""
    check_project_access(project_id, current_user, db)

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        files_metadata = []

        for file_id in file_ids:
            file = db.execute(
                select(models.File).where(
                    models.File.id == file_id, models.File.project_id == project_id
                )
            ).scalar_one_or_none()

            if not file:
                continue

            try:
                # Get file content
                file_content = get_file(file.file_uuid)

                # Add file to ZIP
                zip_file.writestr(file.file_name, file_content)

                # Collect metadata
                if include_metadata:
                    files_metadata.append(
                        {
                            "id": file.id,
                            "file_name": file.file_name,
                            "file_type": file.file_type,
                            "file_size": file.file_size,
                            "file_hash": file.file_hash,
                            "description": file.description,
                            "created_at": file.created_at.isoformat()
                            if file.created_at
                            else None,
                            "updated_at": file.updated_at.isoformat()
                            if file.updated_at
                            else None,
                        }
                    )

            except Exception as e:
                print(f"Error adding file {file.file_name} to ZIP: {e}")
                continue

        # Add metadata file if requested
        if include_metadata and files_metadata:
            metadata_json = json.dumps(
                {
                    "project_id": project_id,
                    "export_date": datetime.datetime.now(datetime.UTC).isoformat(),
                    "total_files": len(files_metadata),
                    "files": files_metadata,
                },
                indent=2,
            )
            zip_file.writestr("metadata.json", metadata_json)

    # Prepare response
    zip_buffer.seek(0)
    filename = f"project_{project_id}_files_{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d_%H%M%S')}.zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/move")
async def move_files(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_ids: list[int] = Body(...),
    target_project_id: int = Body(...),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Move files to another project"""
    # Check access to both source and target projects
    check_project_access(project_id, current_user, db, permission="write")
    check_project_access(target_project_id, current_user, db, permission="write")

    if project_id == target_project_id:
        raise HTTPException(
            status_code=400, detail="Source and target projects cannot be the same"
        )

    moved_count = 0
    errors = []

    for file_id in file_ids:
        try:
            file = db.execute(
                select(models.File).where(
                    models.File.id == file_id, models.File.project_id == project_id
                )
            ).scalar_one_or_none()

            if not file:
                errors.append({"file_id": file_id, "error": "File not found"})
                continue

            # Update the file's project
            file.project_id = target_project_id

            # Update any related documents
            documents = (
                db.execute(
                    select(models.Document).where(
                        or_(
                            models.Document.original_file_id == file_id,
                            models.Document.preprocessed_file_id == file_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

            for doc in documents:
                doc.project_id = target_project_id

            moved_count += 1

        except Exception as e:
            errors.append({"file_id": file_id, "error": str(e)})

    db.commit()

    return {"moved": moved_count, "errors": errors, "total_requested": len(file_ids)}


@router.get("/check-links/{file_id}")
def check_file_links(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file_id: int,
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Check if a file has any linked resources"""
    check_project_access(project_id, current_user, db)

    file = db.execute(
        select(models.File)
        .options(
            selectinload(models.File.documents_as_original),
            selectinload(models.File.documents_as_preprocessed),
            selectinload(models.File.preprocessing_tasks),
            selectinload(models.File.file_preprocessing_tasks),
        )
        .where(models.File.project_id == project_id, models.File.id == file_id)
    ).scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "file_id": file_id,
        "is_linked": bool(
            file.documents_as_original
            or file.documents_as_preprocessed
            or file.preprocessing_tasks
            or file.file_preprocessing_tasks
        ),
        "links": {
            "documents_as_original": len(file.documents_as_original),
            "documents_as_preprocessed": len(file.documents_as_preprocessed),
            "preprocessing_tasks": len(file.preprocessing_tasks),
            "file_preprocessing_tasks": len(file.file_preprocessing_tasks),
        },
    }
