# backend/src/routers/v1/endpoints/groundtruth.py
"""Ground truth endpoints for projects."""

import json

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from thefuzz import fuzz

from .... import models, schemas
from ....core.security import get_current_user
from ....dependencies import get_db, remove_file, save_file
from ....utils.helpers import extract_field_types_from_schema

router = APIRouter()


@router.post("/groundtruth", response_model=schemas.GroundTruth)
async def upload_groundtruth(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    files: list[UploadFile] = File(None),  # For multiple files
    file: UploadFile = File(None),  # For single file (backward compatibility)
    name: str = Form(None),
    format: str = Form(...),
    multiple_json: bool = Form(False),
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    """Upload ground truth file for evaluation."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to upload ground truth to this project",
        )
    # Validate format
    if format not in ["json", "csv", "xlsx", "zip"]:
        raise HTTPException(
            status_code=400, detail="Invalid format. Must be json, csv, xlsx, or zip"
        )
    # Save the file
    if multiple_json and files:
        # Create a ZIP file in memory containing all JSON files
        import io
        import zipfile

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for idx, json_file in enumerate(files):
                content = await json_file.read()
                # Validate it's valid JSON
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File {json_file.filename} is not valid JSON",
                    )
                zf.writestr(json_file.filename, content)

        zip_buffer.seek(0)
        file_content = zip_buffer.read()
        format = "zip"  # Treat as ZIP internally
    else:
        # Single file upload (existing logic)
        upload_file = file or (files[0] if files else None)
        if not upload_file:
            raise HTTPException(status_code=400, detail="No file provided")
        file_content = await upload_file.read()
    # save_file() does blocking disk/S3 I/O; run it in a threadpool so the
    # event loop isn't blocked for the duration of the write.
    file_uuid = await run_in_threadpool(save_file, file_content)
    # Derive a name safely: ``file`` may be None in the multiple_json path
    # (where the caller must pass ``name`` explicitly).
    fallback_name = file.filename if file else None
    gt_name = name or fallback_name
    if not gt_name:
        raise HTTPException(
            status_code=400, detail="A name is required when no single file is provided"
        )
    # Create ground truth record
    gt = models.GroundTruth(
        project_id=project_id,
        name=gt_name,
        format=format,
        file_uuid=file_uuid,
    )
    db.add(gt)
    try:
        db.commit()
    except Exception:
        # Bytes are already in storage with no DB row. Roll back and remove
        # the orphaned file so a failed commit doesn't leak storage.
        db.rollback()
        try:
            remove_file(file_uuid)
        except Exception:
            pass
        raise
    db.refresh(gt)
    return schemas.GroundTruth.model_validate(gt)


@router.get("/groundtruth/{groundtruth_id}", response_model=schemas.GroundTruth)
def get_groundtruth(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    """Get a specific ground truth file."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's ground truth",
        )

    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()

    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    return schemas.GroundTruth.model_validate(groundtruth)


@router.delete("/groundtruth/{groundtruth_id}", response_model=schemas.GroundTruth)
def delete_groundtruth(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    """Delete a ground truth file."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this project's ground truth",
        )

    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()

    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Delete the file content from storage
    try:
        remove_file(groundtruth.file_uuid)
    except FileNotFoundError:
        # Continue deletion even if file not found in storage
        pass

    # Remove any evaluations using this ground truth
    evaluations = (
        db.execute(
            select(models.Evaluation).where(
                models.Evaluation.groundtruth_id == groundtruth_id
            )
        )
        .scalars()
        .all()
    )

    for evaluation in evaluations:
        db.delete(evaluation)

    db.delete(groundtruth)
    db.commit()

    return schemas.GroundTruth.model_validate(groundtruth)


@router.get("/groundtruth", response_model=list[schemas.GroundTruth])
def get_groundtruth_files(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.GroundTruth]:
    """Get all ground truth files for a project."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this project's ground truth files",
        )
    ground_truths = list(
        db.execute(
            select(models.GroundTruth).where(
                models.GroundTruth.project_id == project_id
            )
        )
        .scalars()
        .all()
    )
    return [schemas.GroundTruth.model_validate(gt) for gt in ground_truths]


@router.put("/groundtruth/{groundtruth_id}", response_model=schemas.GroundTruth)
def update_groundtruth(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    file: UploadFile = File(None),
    name: str = Form(None),
    comparison_options: str = Form(None),
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this project's ground truth",
        )

    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()

    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    if name:
        groundtruth.name = name

    if comparison_options:
        try:
            groundtruth.comparison_options = json.loads(comparison_options)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid comparison options JSON"
            )

    if file:
        try:
            remove_file(groundtruth.file_uuid)
        except FileNotFoundError:
            pass

        file_content = file.file.read()
        file_uuid = save_file(file_content)
        groundtruth.file_uuid = file_uuid

        evaluations = (
            db.execute(
                select(models.Evaluation).where(
                    models.Evaluation.groundtruth_id == groundtruth_id
                )
            )
            .scalars()
            .all()
        )
        for evaluation in evaluations:
            db.delete(evaluation)

    groundtruth.updated_at = func.now()
    db.add(groundtruth)
    db.commit()
    db.refresh(groundtruth)

    return schemas.GroundTruth.model_validate(groundtruth)


@router.put(
    "/groundtruth/{groundtruth_id}/id-column",
    response_model=schemas.GroundTruth,
)
def update_ground_truth_id_column(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    id_column: str = Body(..., embed=True),
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    """
    Update the ID column/field for any ground truth file.
    - For CSV/XLSX: the column used as the document ID.
    - For JSON/ZIP: the field from each JSON object to use as document ID, or set empty to use filename.
    """
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this project"
        )

    # Get ground truth
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Update ID column/field
    groundtruth.id_column_name = id_column

    # Clear data cache to force re-parsing with new ID column/field logic
    groundtruth.data_cache = None

    # Invalidate related evaluations
    db.execute(
        delete(models.Evaluation).where(
            models.Evaluation.groundtruth_id == groundtruth_id
        )
    )

    db.commit()
    db.refresh(groundtruth)

    return schemas.GroundTruth.model_validate(groundtruth)


@router.get(
    "/groundtruth/{groundtruth_id}/preview",
    response_model=dict,
)
def preview_groundtruth(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    current_user: models.User = Depends(get_current_user),
):
    """
    Preview parsed ground truth: return field paths, field types, available ID columns,
    and a sample of parsed data.
    """
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

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
        gt_data = engine._load_ground_truth(groundtruth)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load ground truth: {e}")

    # Collect field paths + types from a sample document
    def collect_paths(doc: dict, prefix=""):
        paths = []
        types = {}
        for k, v in doc.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                subpaths, subtypes = collect_paths(v, path)
                paths.extend(subpaths)
                types.update(subtypes)
            else:
                paths.append(path)
                types[path] = type(v).__name__ if v is not None else "null"
        return paths, types

    field_paths, field_types, sample_doc = [], {}, None
    if gt_data:
        sample_doc = next(iter(gt_data.values()))
        field_paths, field_types = collect_paths(sample_doc)

    # Get available columns directly from the file so the ID header is preserved
    available_columns = []
    if groundtruth.format in ["csv", "xlsx"]:
        try:
            available_columns = engine.get_available_columns(groundtruth)
        except ValueError:
            available_columns = []

        # ensure the saved id column appears even if headers are quirky
        saved = (groundtruth.id_column_name or "").strip()
        if saved and saved not in available_columns:
            available_columns = [saved] + available_columns

    return {
        "fields": field_paths,
        "field_types": field_types,
        "preview_data": {k: v for k, v in list(gt_data.items())[:3]},
        "available_columns": available_columns,
        "current_id_column": groundtruth.id_column_name,
    }


@router.post(
    "/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping",
    response_model=schemas.GroundTruth,
)
def configure_field_mapping(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    mappings: list[schemas.FieldMappingCreate] = Body(...),
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    """Configure field mappings for a specific groundtruth-schema combination."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to configure field mappings"
        )

    # Validate groundtruth exists
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Validate schema exists
    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id,
            models.Schema.id == schema_id,
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Delete existing mappings for this groundtruth-schema combination
    db.execute(
        delete(models.FieldMapping).where(
            models.FieldMapping.ground_truth_id == groundtruth_id,
            models.FieldMapping.schema_id == schema_id,
        )
    )

    # Create new mappings
    for mapping_data in mappings:
        mapping = models.FieldMapping(
            ground_truth_id=groundtruth_id, **mapping_data.model_dump()
        )
        db.add(mapping)

    # Invalidate evaluations for this specific groundtruth-schema combination
    db.execute(
        delete(models.Evaluation).where(
            models.Evaluation.groundtruth_id == groundtruth_id,
            models.Evaluation.trial_id.in_(
                select(models.Trial.id).where(models.Trial.schema_id == schema_id)
            ),
        )
    )

    db.commit()
    db.refresh(groundtruth)
    return schemas.GroundTruth.model_validate(groundtruth)


@router.get(
    "/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping",
    response_model=list[schemas.FieldMapping],
)
def get_field_mappings(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.FieldMapping]:
    """Get field mappings for a specific groundtruth-schema combination."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access field mappings"
        )

    # Validate groundtruth exists
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Validate schema exists
    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id,
            models.Schema.id == schema_id,
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Get mappings for this groundtruth-schema combination
    mappings = (
        db.execute(
            select(models.FieldMapping).where(
                models.FieldMapping.ground_truth_id == groundtruth_id,
                models.FieldMapping.schema_id == schema_id,
            )
        )
        .scalars()
        .all()
    )

    return [schemas.FieldMapping.model_validate(mapping) for mapping in mappings]


@router.delete(
    "/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping",
    response_model=dict,
)
def delete_field_mappings(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Delete all field mappings for a specific groundtruth-schema combination."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete field mappings"
        )

    # Validate groundtruth exists
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Validate schema exists
    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id,
            models.Schema.id == schema_id,
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Delete mappings for this groundtruth-schema combination
    deleted_count = db.execute(
        delete(models.FieldMapping).where(
            models.FieldMapping.ground_truth_id == groundtruth_id,
            models.FieldMapping.schema_id == schema_id,
        )
    ).rowcount

    # Invalidate related evaluations
    db.execute(
        delete(models.Evaluation).where(
            models.Evaluation.groundtruth_id == groundtruth_id,
            models.Evaluation.trial_id.in_(
                select(models.Trial.id).where(models.Trial.schema_id == schema_id)
            ),
        )
    )

    db.commit()

    return {"deleted_mappings": deleted_count}


@router.get(
    "/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping/suggest",
    response_model=list[schemas.FieldMapping],
)
def suggest_field_mappings(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    current_user: models.User = Depends(get_current_user),
) -> list[schemas.FieldMapping]:
    """Suggest field mappings based on schema and ground truth."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project"
        )

    # Get schema
    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id, models.Schema.id == schema_id
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Get ground truth
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Load ground truth data
    from ....utils.evaluation import EvaluationEngine

    engine = EvaluationEngine(db)
    gt_data = engine._load_ground_truth(groundtruth)

    # Check if ground truth is JSON format
    is_json_format = groundtruth.format in ["json", "zip"]

    # Extract schema fields with dot notation
    schema_fields = {}
    extract_field_types_from_schema(schema.schema_definition, schema_fields)

    if is_json_format:
        # For JSON, create exact matches for nested fields
        suggestions = []

        # Get ground truth fields with dot notation from first document
        gt_fields_flat = set()
        sample_doc = next(iter(gt_data.values())) if gt_data else {}

        def extract_gt_fields(data, prefix=""):
            """Extract fields with dot notation from nested dict."""
            for key, value in data.items():
                if key in ["id", "patient_id"]:  # Skip ID fields
                    continue
                field_path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    extract_gt_fields(value, field_path)
                else:
                    gt_fields_flat.add(field_path)

        if isinstance(sample_doc, dict):
            extract_gt_fields(sample_doc)

        # Match schema fields to ground truth fields
        for schema_field, field_type in schema_fields.items():
            if schema_field in gt_fields_flat:
                # Exact match found
                suggestions.append(
                    {
                        "id": 0,
                        "ground_truth_id": groundtruth_id,
                        "schema_id": schema_id,
                        "schema_field": schema_field,
                        "ground_truth_field": schema_field,
                        "field_type": field_type,
                        "comparison_method": _get_comparison_method(field_type),
                        "comparison_options": {},
                        "confidence": 1.0,
                    }
                )

        return suggestions
    else:
        # Use existing fuzzy matching for CSV
        # Get ground truth fields
        gt_fields = set()
        for fields in gt_data.values():
            gt_fields.update(fields.keys())

        # Suggest mappings
        suggestions = []
        for schema_field, field_type in schema_fields.items():
            # Try exact match
            if schema_field in gt_fields:
                suggestions.append(
                    {
                        "id": 0,
                        "ground_truth_id": groundtruth_id,
                        "schema_id": schema_id,
                        "schema_field": schema_field,
                        "ground_truth_field": schema_field,
                        "field_type": field_type,
                        "comparison_method": _get_comparison_method(field_type),
                        "confidence": 1.0,
                    }
                )
                continue

            # Try fuzzy matching
            best_match = None
            best_score = 0
            for gt_field in gt_fields:
                score = fuzz.ratio(schema_field.lower(), gt_field.lower())
                if score > best_score and score > 70:
                    best_score = score
                    best_match = gt_field

            if best_match:
                suggestions.append(
                    {
                        "id": 0,
                        "ground_truth_id": groundtruth_id,
                        "schema_id": schema_id,
                        "schema_field": schema_field,
                        "ground_truth_field": best_match,
                        "field_type": field_type,
                        "comparison_method": _get_comparison_method(field_type),
                        "confidence": best_score / 100.0,
                    }
                )

        return suggestions


def _get_comparison_method(field_type: str) -> str:
    """Get default comparison method for field type."""
    type_to_method = {
        "boolean": "boolean",
        "number": "numeric",
        "date": "date",
        "category": "category",
        "string": "exact",
    }
    return type_to_method.get(field_type, "exact")


@router.post(
    "/groundtruth/{groundtruth_id}/schema/{schema_id}/validate-json",
    response_model=dict,
)
def validate_json_ground_truth(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Validate JSON ground truth against schema definition."""
    # ... access checks ...
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Fetch by (id, project_id) — a bare-PK lookup would let a caller pass
    # another project's groundtruth/schema id and read cross-project data.
    groundtruth = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.id == groundtruth_id,
            models.GroundTruth.project_id == project_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth file not found")

    schema = db.execute(
        select(models.Schema).where(
            models.Schema.id == schema_id, models.Schema.project_id == project_id
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Only for JSON format
    if groundtruth.format not in ["json", "zip"]:
        return {"errors": [], "warnings": ["Validation only applies to JSON format"]}

    # Load ground truth data
    from ....utils.evaluation import EvaluationEngine

    engine = EvaluationEngine(db)
    gt_data = engine._load_ground_truth(groundtruth)

    errors = []
    warnings = []

    from ....utils.helpers import (
        check_field_types,
        check_missing_fields_nested,
        extract_required_fields_from_schema,
        find_extra_fields,
    )

    # Validate structure matches schema
    schema_def = schema.schema_definition
    required_fields = extract_required_fields_from_schema(schema_def)

    # Check a sample of documents
    sample_size = min(10, len(gt_data))
    for i, (doc_id, doc_data) in enumerate(list(gt_data.items())[:sample_size]):
        # Check required fields
        missing = check_missing_fields_nested(doc_data, required_fields, "")
        if missing:
            errors.extend([f"Document {doc_id}: Missing {field}" for field in missing])

        # Check data types
        type_errors = check_field_types(doc_data, schema_def, "")
        if type_errors:
            errors.extend([f"Document {doc_id}: {err}" for err in type_errors])

    # Extra fields are warnings
    extra = find_extra_fields(doc_data, schema_def)
    if extra:
        warnings.extend([f"Extra field '{field}' not in schema" for field in extra])

    return {"errors": errors[:10], "warnings": warnings[:10]}  # Limit to 10 each


@router.post(
    "/groundtruth/{groundtruth_id}/schema/{schema_id}/auto-map",
    response_model=dict,
)
def auto_map_fields(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    confidence_threshold: float = Body(0.7),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Automatically map ground truth fields to schema fields."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project"
        )

    # Get schema and ground truth
    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id, models.Schema.id == schema_id
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    # Load ground truth data
    from ....utils.evaluation import EvaluationEngine

    engine = EvaluationEngine(db)
    gt_data = engine._load_ground_truth(groundtruth)

    # Extract schema fields
    schema_fields = {}
    extract_field_types_from_schema(schema.schema_definition, schema_fields)

    # Get ground truth fields and sample values
    gt_fields = {}
    for doc_id, fields in list(gt_data.items())[:10]:  # Sample first 10 docs
        for field, value in fields.items():
            if field not in gt_fields:
                gt_fields[field] = []
            if value not in gt_fields[field] and len(gt_fields[field]) < 5:
                gt_fields[field].append(value)

    # Auto-map fields
    from ....utils.field_mapping import FieldMapper

    mapper = FieldMapper()
    mappings = mapper.auto_map(
        schema_fields=schema_fields,
        ground_truth_fields=gt_fields,
        confidence_threshold=confidence_threshold,
    )

    # Delete existing mappings for this groundtruth-schema combination
    db.execute(
        delete(models.FieldMapping).where(
            models.FieldMapping.ground_truth_id == groundtruth_id,
            models.FieldMapping.schema_id == schema_id,
        )
    )

    # Apply mappings
    applied_count = 0
    for mapping in mappings:
        if mapping["confidence"] >= confidence_threshold:
            field_mapping = models.FieldMapping(
                ground_truth_id=groundtruth_id,
                schema_id=schema_id,
                schema_field=mapping["schema_field"],
                ground_truth_field=mapping["ground_truth_field"],
                field_type=mapping["field_type"],
                comparison_method=mapping["comparison_method"],
                comparison_options=mapping.get("comparison_options", {}),
            )
            db.add(field_mapping)
            applied_count += 1

    # Invalidate existing evaluations for this groundtruth-schema combination
    db.execute(
        delete(models.Evaluation).where(
            models.Evaluation.groundtruth_id == groundtruth_id,
            models.Evaluation.trial_id.in_(
                select(models.Trial.id).where(models.Trial.schema_id == schema_id)
            ),
        )
    )

    db.commit()

    return {
        "total_schema_fields": len(schema_fields),
        "total_ground_truth_fields": len(gt_fields),
        "suggested_mappings": len(mappings),
        "applied_mappings": applied_count,
        "mappings": mappings,
    }


@router.get(
    "/groundtruth/{groundtruth_id}/schema/{schema_id}/mapping/status",
    response_model=dict,
)
def check_mapping_status(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    schema_id: int,
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Check if field mappings exist for a groundtruth-schema combination."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project"
        )

    # Validate groundtruth and schema exist
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")

    schema: models.Schema | None = db.execute(
        select(models.Schema).where(
            models.Schema.project_id == project_id,
            models.Schema.id == schema_id,
        )
    ).scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    # Check mapping status
    mapping_count = db.execute(
        select(func.count(models.FieldMapping.id)).where(
            models.FieldMapping.ground_truth_id == groundtruth_id,
            models.FieldMapping.schema_id == schema_id,
        )
    ).scalar()

    # Get schema field count
    schema_fields = {}
    extract_field_types_from_schema(schema.schema_definition, schema_fields)
    schema_field_count = len(schema_fields)

    return {
        "has_mappings": mapping_count > 0,
        "mapping_count": mapping_count,
        "schema_field_count": schema_field_count,
        "mapping_complete": mapping_count == schema_field_count,
        "groundtruth_name": groundtruth.name,
        "schema_name": schema.schema_name,
    }


@router.post(
    "/groundtruth/{groundtruth_id}/mapping",
    response_model=schemas.GroundTruth,
)
def configure_field_mapping_legacy(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    groundtruth_id: int,
    mappings: list[schemas.FieldMappingCreate] = Body(...),
    current_user: models.User = Depends(get_current_user),
) -> schemas.GroundTruth:
    """Configure field mappings for ground truth evaluation."""
    project: models.Project | None = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to configure ground truth mappings"
        )
    groundtruth: models.GroundTruth | None = db.execute(
        select(models.GroundTruth).where(
            models.GroundTruth.project_id == project_id,
            models.GroundTruth.id == groundtruth_id,
        )
    ).scalar_one_or_none()
    if not groundtruth:
        raise HTTPException(status_code=404, detail="Ground truth not found")
    # Delete existing mappings
    db.execute(
        delete(models.FieldMapping).where(
            models.FieldMapping.ground_truth_id == groundtruth_id
        )
    )
    # Create new mappings
    for mapping_data in mappings:
        mapping = models.FieldMapping(
            ground_truth_id=groundtruth_id, **mapping_data.model_dump()
        )
        db.add(mapping)
    # Invalidate existing evaluations
    db.execute(
        delete(models.Evaluation).where(
            models.Evaluation.groundtruth_id == groundtruth_id
        )
    )
    db.commit()
    db.refresh(groundtruth)
    return schemas.GroundTruth.model_validate(groundtruth)
