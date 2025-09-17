import base64
import io
import json
from datetime import datetime, timezone
from typing import Any

import requests
from fastapi import HTTPException
from PIL import Image
from sqlalchemy.orm import Session

from backend.src import models, schemas


import io
import mimetypes
import zipfile

# If your enums/constants are here:
from .enums import FileType  # adjust import if needed

CSV_MIME = "text/csv"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
XLS_MIME = "application/vnd.ms-excel"


def _is_zip(buffer: bytes) -> bool:
    # Fast check: PK\x03\x04
    return len(buffer) >= 4 and buffer[:4] == b"PK\x03\x04"


def _looks_like_xlsx(buffer: bytes) -> bool:
    """
    XLSX is a ZIP with 'xl/workbook.xml' (and usually '[Content_Types].xml').
    We only open a tiny zipfile view (ZipFile can read from bytes).
    """
    if not _is_zip(buffer):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(buffer)) as zf:
            names = set(zf.namelist())
            # Minimal XLSX signature
            return "xl/workbook.xml" in names or "[Content_Types].xml" in names
    except zipfile.BadZipFile:
        return False


def _looks_like_ole_xls(buffer: bytes) -> bool:
    # Legacy XLS is OLE2/CFB: D0 CF 11 E0 A1 B1 1A 1E
    sig = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\x1e"
    return len(buffer) >= len(sig) and buffer[: len(sig)] == sig


def detect_structured_mime(
    file_name: str, content: bytes, provided_mime: str | None
) -> str:
    """
    Decide the *best* MIME for structured files (CSV/XLSX/XLS), ignoring browser quirks.
    Priority:
      1) Magic bytes (XLSX/ZIP vs XLS/OLE)
      2) Filename extension (.xlsx / .xls / .csv)
      3) Provided MIME (as a hint)
      4) mimetypes.guess_type fallback
    """
    name = (file_name or "").lower()
    provided = (provided_mime or "").lower()

    # Magic bytes first (most reliable)
    head = content[:4096]  # enough for signatures and Zip listing
    if _looks_like_xlsx(head):
        return XLSX_MIME
    if _looks_like_ole_xls(head):
        return XLS_MIME

    # Extension next
    if name.endswith(".xlsx"):
        return XLSX_MIME
    if name.endswith(".xls"):
        return XLS_MIME
    if name.endswith(".csv"):
        return CSV_MIME

    # Provided MIME as a hint; Windows often lies (vnd.ms-excel for CSV)
    # Only trust it if it is text/csv or real XLSX
    if provided == CSV_MIME:
        return CSV_MIME
    if provided == XLSX_MIME:
        return XLSX_MIME
    if provided == XLS_MIME:
        # Could still be CSV mislabeled; but we already checked magic/extension above.
        return XLS_MIME

    # Fallback to python's mimetypes (by extension)
    guessed, _ = mimetypes.guess_type(name)
    if guessed:
        return guessed

    # Last resort: keep the original or use octet-stream
    return provided or "application/octet-stream"


def build_evaluation_zipfiles(
    db,
    evaluations,
    *,
    include_details,
    include_field_details,
    include_errors,
    include_document_content,
    include_ground_truth_content,
    zip_format="csv",  # or "xlsx"
):
    """
    Prepares files (filename, bytes) for a ZIP, using the export helpers and pandas.
    Returns: List of (arcname, bytes)
    """
    import csv
    import io

    import pandas as pd

    files = []

    # --- Summary CSV/XLSX ---
    if zip_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Evaluation ID",
                "Trial ID",
                "Model",
                "Ground Truth",
                "Accuracy",
                "Precision",
                "Recall",
                "F1 Score",
                "Total Documents",
                "Total Fields",
                "Created At",
            ]
        )
        for eval_obj, trial in evaluations:
            gt = db.query(models.GroundTruth).get(eval_obj.groundtruth_id)
            writer.writerow(
                [
                    eval_obj.id,
                    eval_obj.trial_id,
                    trial.llm_model,
                    gt.name if gt else "Unknown",
                    eval_obj.metrics.get("accuracy", 0),
                    eval_obj.metrics.get("precision", 0),
                    eval_obj.metrics.get("recall", 0),
                    eval_obj.metrics.get("f1_score", 0),
                    eval_obj.metrics.get("total_documents", 0),
                    eval_obj.metrics.get("total_fields", 0),
                    eval_obj.created_at.isoformat(),
                ]
            )
        files.append(("summary.csv", output.getvalue().encode("utf-8")))

    else:
        output = io.BytesIO()
        summary_data = []
        for eval_obj, trial in evaluations:
            gt = db.query(models.GroundTruth).get(eval_obj.groundtruth_id)
            summary_data.append(
                {
                    "Evaluation ID": eval_obj.id,
                    "Trial ID": eval_obj.trial_id,
                    "Model": trial.llm_model,
                    "Ground Truth": gt.name if gt else "Unknown",
                    "Accuracy": eval_obj.metrics.get("accuracy", 0),
                    "Precision": eval_obj.metrics.get("precision", 0),
                    "Recall": eval_obj.metrics.get("recall", 0),
                    "F1 Score": eval_obj.metrics.get("f1_score", 0),
                    "Total Documents": eval_obj.metrics.get("total_documents", 0),
                    "Total Fields": eval_obj.metrics.get("total_fields", 0),
                    "Created At": eval_obj.created_at.isoformat(),
                }
            )
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            pd.DataFrame(summary_data).to_excel(
                writer, sheet_name="Summary", index=False
            )
        output.seek(0)
        files.append(("summary.xlsx", output.getvalue()))

    # --- Field-by-field Details (CSV or Excel sheet) ---
    if include_field_details:
        details = []
        for eval_obj, _ in evaluations:
            details.extend(
                collect_evaluation_field_level_details(db, eval_obj, include_errors)
            )
        if details:
            if zip_format == "csv":
                out = io.StringIO()
                w = csv.writer(out)
                headers = list(details[0].keys())
                w.writerow(headers)
                for row in details:
                    w.writerow([row.get(h, "") for h in headers])
                files.append(("field_details.csv", out.getvalue().encode("utf-8")))
            else:
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                    pd.DataFrame(details).to_excel(
                        writer, sheet_name="Field Details", index=False
                    )
                out.seek(0)
                files.append(("field_details.xlsx", out.getvalue()))

    # --- Document-level metrics ---
    if include_details:
        doc_data = []
        for eval_obj, _ in evaluations:
            for doc_metrics in eval_obj.document_metrics:
                doc_data.append(
                    {
                        "Evaluation ID": eval_obj.id,
                        "Document ID": doc_metrics.get("document_id"),
                        "Accuracy": doc_metrics.get("accuracy"),
                        "Correct Fields": doc_metrics.get("correct_fields"),
                        "Total Fields": doc_metrics.get("total_fields"),
                        "Missing Fields": ";".join(
                            doc_metrics.get("missing_fields", [])
                        ),
                        "Incorrect Fields": ";".join(
                            doc_metrics.get("incorrect_fields", [])
                        ),
                        "Error": doc_metrics.get("error", ""),
                    }
                )
        if doc_data:
            if zip_format == "csv":
                out = io.StringIO()
                w = csv.writer(out)
                headers = list(doc_data[0].keys())
                w.writerow(headers)
                for row in doc_data:
                    w.writerow([row.get(h, "") for h in headers])
                files.append(("document_metrics.csv", out.getvalue().encode("utf-8")))
            else:
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                    pd.DataFrame(doc_data).to_excel(
                        writer, sheet_name="Doc Metrics", index=False
                    )
                out.seek(0)
                files.append(("document_metrics.xlsx", out.getvalue()))

    # --- Per-document JSONs/Texts/GT (optional) ---
    if include_document_content or include_ground_truth_content:
        # Put all docs in a subfolder, one JSON per document
        for eval_obj, trial in evaluations:
            docs = collect_trial_document_metadata(
                db,
                trial,
                include_content=include_document_content,
                include_ground_truth=include_ground_truth_content,
            )
            for doc in docs:
                doc_id = (
                    doc.get("Document ID") or doc.get("document_id") or doc.get("id")
                )
                arcname = f"docs/{doc_id}.json"
                files.append(
                    (
                        arcname,
                        json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"),
                    )
                )
                # Optionally: export text/GT as plain .txt
                if (
                    include_document_content
                    and "Document Content" in doc
                    and doc["Document Content"]
                ):
                    files.append(
                        (f"docs/{doc_id}.txt", doc["Document Content"].encode("utf-8"))
                    )
                if (
                    include_ground_truth_content
                    and "Ground Truth" in doc
                    and doc["Ground Truth"]
                ):
                    gt = doc["Ground Truth"]
                    if isinstance(gt, str):
                        files.append((f"docs/{doc_id}_gt.txt", gt.encode("utf-8")))
                    else:
                        files.append(
                            (
                                f"docs/{doc_id}_gt.json",
                                json.dumps(gt, ensure_ascii=False, indent=2).encode(
                                    "utf-8"
                                ),
                            )
                        )
    return files


def collect_evaluation_field_level_details(
    db: Session, evaluation: models.Evaluation, include_errors=False
) -> list[dict[str, Any]]:
    """
    Returns list of dicts: one per field per document, with gt/pred/error info.
    """
    details = []
    for metric in evaluation.detailed_metrics:
        row = {
            "Evaluation ID": metric.evaluation_id,
            "Document ID": metric.document_id,
            "Field Name": metric.field_name,
            "Ground Truth": metric.ground_truth_value,
            "Prediction": metric.predicted_value,
            "Is Correct": metric.is_correct,
        }
        if include_errors:
            row["Error Type"] = metric.error_type
            row["Confidence"] = metric.confidence_score
        details.append(row)
    return details


def collect_trial_document_metadata(
    db: Session,
    trial: models.Trial,
    include_content: bool = False,
    include_ground_truth: bool = False,
) -> list[dict[str, Any]]:
    """
    Collects metadata for all documents in a trial. Optionally includes document text and ground truth.
    """
    # Fetch all TrialResults for the trial
    results = db.query(models.TrialResult).filter_by(trial_id=trial.id).all()
    docs = []
    gt_cache = {}
    # For each result/document, gather metadata
    for result in results:
        doc = db.get(models.Document, result.document_id)
        if not doc:
            continue
        entry = {
            "Document ID": doc.id,
            "Document Name": doc.document_name,
            "File Name": doc.original_file.file_name if doc.original_file else None,
            "Trial Result": result.result,
        }
        if include_content:
            entry["Document Content"] = doc.text
        # Optionally attach ground truth for that doc
        if include_ground_truth and trial.evaluations:
            eval_obj = trial.evaluations[0]  # usually one evaluation per trial/gt
            gt = db.get(models.GroundTruth, eval_obj.groundtruth_id)
            if gt:
                if gt.id not in gt_cache:
                    gt_cache[gt.id] = gt.data_cache or {}
                gt_data = gt_cache[gt.id]
                # Try to match the document by doc_name or file_name
                key = (
                    str(doc.document_name)
                    if doc.document_name in gt_data
                    else str(doc.id)
                )
                entry["Ground Truth"] = gt_data.get(key)
        docs.append(entry)
    return docs


def extract_leaf_paths_from_dict(data, parent=""):
    """Recursively extracts all leaf field paths from a nested dict using dot notation."""
    fields = []
    if isinstance(data, dict):
        for k, v in data.items():
            new_parent = f"{parent}.{k}" if parent else k
            if isinstance(v, dict):
                fields.extend(extract_leaf_paths_from_dict(v, new_parent))
            else:
                fields.append(new_parent)
    elif isinstance(data, list):
        # List: treat as array, add [*] to path (optionally)
        for i, item in enumerate(data):
            new_parent = f"{parent}[{i}]"
            fields.extend(extract_leaf_paths_from_dict(item, new_parent))
    return fields


def extract_required_fields_from_schema(
    schema_def: dict, prefix: str = ""
) -> list[str]:
    """Extract required fields from JSON schema using dot notation."""
    required = []

    if "properties" in schema_def:
        # Get fields marked as required at this level
        required_at_level = schema_def.get("required", [])

        for prop, prop_def in schema_def["properties"].items():
            field_path = f"{prefix}.{prop}" if prefix else prop

            # Check if this field is required
            if prop in required_at_level:
                required.append(field_path)

            # Recurse for nested objects
            if prop_def.get("type") == "object":
                required.extend(
                    extract_required_fields_from_schema(prop_def, field_path)
                )

            # Handle arrays of objects
            elif (
                prop_def.get("type") == "array"
                and prop_def.get("items", {}).get("type") == "object"
            ):
                # For arrays, we check the items schema
                required.extend(
                    extract_required_fields_from_schema(
                        prop_def["items"], f"{field_path}[]"
                    )
                )

    return required


def check_missing_fields_nested(
    data: dict, required_fields: list[str], prefix: str = ""
) -> list[str]:
    """Check for missing required fields in nested structure using dot notation."""
    missing = []

    for field_path in required_fields:
        # Skip array notation for now
        if "[]" in field_path:
            continue

        keys = field_path.split(".")
        current = data
        found = True

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                found = False
                break

        if not found:
            missing.append(field_path)

    return missing


def find_extra_fields_nested(
    data: dict, schema_def: dict, prefix: str = ""
) -> list[str]:
    """Find fields in data that aren't in schema."""
    extra = []

    # Special fields to ignore
    ignore_fields = {"id", "document_id", "_id"}

    def get_schema_fields(schema: dict, prefix: str = "") -> set[str]:
        """Extract all field paths from schema."""
        fields = set()

        if "properties" in schema:
            for prop, prop_def in schema["properties"].items():
                field_path = f"{prefix}.{prop}" if prefix else prop
                fields.add(field_path)

                # Recurse for nested objects
                if prop_def.get("type") == "object":
                    fields.update(get_schema_fields(prop_def, field_path))

        return fields

    # Get all schema fields
    schema_fields = get_schema_fields(schema_def)

    def check_data_fields(data: dict, prefix: str = ""):
        """Check data fields against schema."""
        for key, value in data.items():
            if key in ignore_fields:
                continue

            field_path = f"{prefix}.{key}" if prefix else key

            if field_path not in schema_fields:
                extra.append(field_path)
            elif isinstance(value, dict):
                # Recurse for nested objects
                check_data_fields(value, field_path)

    check_data_fields(data)
    return extra


def check_field_types(data: dict, schema_def: dict, prefix: str = "") -> list[str]:
    """Check if data types in the JSON match the schema definition."""
    type_errors = []

    if "properties" in schema_def:
        for prop, prop_def in schema_def["properties"].items():
            field_path = f"{prefix}.{prop}" if prefix else prop

            # Check if field exists in data
            if prop not in data:
                continue  # Missing fields are handled separately

            value = data[prop]
            expected_type = prop_def.get("type")

            # Check type compatibility
            if expected_type:
                type_error = check_value_type(value, expected_type, field_path)
                if type_error:
                    type_errors.append(type_error)

            # Recurse for nested objects
            if expected_type == "object" and isinstance(value, dict):
                nested_errors = check_field_types(value, prop_def, field_path)
                type_errors.extend(nested_errors)

            # Handle arrays
            elif expected_type == "array" and isinstance(value, list):
                items_schema = prop_def.get("items", {})
                for i, item in enumerate(value):
                    if items_schema.get("type") == "object":
                        nested_errors = check_field_types(
                            item, items_schema, f"{field_path}[{i}]"
                        )
                        type_errors.extend(nested_errors)

    return type_errors


def check_value_type(value: Any, expected_type: str, field_path: str) -> str | None:
    """Check if a value matches the expected JSON schema type."""
    if value is None:
        return None  # Null values are generally acceptable

    type_mapping = {
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    expected_python_type = type_mapping.get(expected_type)

    if expected_python_type is None:
        return None  # Unknown type, skip validation

    if not isinstance(value, expected_python_type):
        # Special handling for numbers
        if expected_type == "number" and isinstance(value, (int, float)):
            return None  # Both int and float are acceptable for number

        # Special handling for integer vs float
        if (
            expected_type == "integer"
            and isinstance(value, float)
            and value.is_integer()
        ):
            return None  # Float with no decimal part is acceptable as integer

        # Generate user-friendly error message
        actual_type = type(value).__name__

        # Make error messages more intuitive
        if isinstance(value, str) and expected_type in ["number", "integer"]:
            return f"Field '{field_path}' expects a {expected_type} but got text '{value}'. Please use a numeric value without quotes."
        elif isinstance(value, (int, float)) and expected_type == "string":
            return f"Field '{field_path}' expects text but got number {value}. Please wrap the value in quotes."
        elif expected_type == "boolean":
            return f"Field '{field_path}' expects true/false but got {actual_type} '{value}'. Use true or false without quotes."
        else:
            return f"Field '{field_path}' expects {expected_type} but got {actual_type}"

    return None


def find_extra_fields(data: dict, schema_def: dict) -> list[str]:
    """Find fields in data that aren't defined in the schema."""

    # Use the existing find_extra_fields_nested function
    extra_fields = find_extra_fields_nested(data, schema_def)

    return extra_fields


def make_naive_fields_timezone_aware(value: Any) -> Any:
    # Only process datetime instances that are naive
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        # Optional: normalize to UTC if already tz-aware but not UTC
        # return value.astimezone(timezone.utc)
    return value


def validate_prompt(prompt: schemas.PromptCreate | schemas.PromptUpdate) -> None:
    """Validate that the prompt contains the required placeholder and at least one prompt is present."""
    placeholder = "{document_content}"

    # Check that at least one prompt is provided
    if not prompt.system_prompt and not prompt.user_prompt:
        raise HTTPException(
            status_code=400,
            detail="At least one of system_prompt or user_prompt must be provided",
        )

    # Check that the placeholder exists in at least one of the prompts
    has_placeholder = False
    if prompt.system_prompt and placeholder in prompt.system_prompt:
        has_placeholder = True
    if prompt.user_prompt and placeholder in prompt.user_prompt:
        has_placeholder = True

    if not has_placeholder:
        raise HTTPException(
            status_code=400,
            detail=f"The placeholder '{placeholder}' must be present in either system_prompt or user_prompt",
        )


def flatten_dict(d, parent_key="", sep="."):
    """Flatten dictionary with dot notation for nested fields."""
    flat_dict = {}
    if isinstance(d, dict):
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                flat_dict.update(flatten_dict(v, new_key, sep))
            elif isinstance(v, list):
                # Recursively flatten lists of dicts
                for i, item in enumerate(v):
                    flat_dict.update(flatten_dict(item, f"{new_key}[{i}]", sep))
            else:
                flat_dict[new_key] = v
    else:
        flat_dict[parent_key] = d
    return flat_dict


def extract_field_types_from_schema(schema_def: dict, result: dict, prefix: str = ""):
    """Extract all field types from a JSON schema as dot notation (leaf paths)."""
    if "properties" in schema_def:
        for prop_name, prop_def in schema_def["properties"].items():
            full_path = f"{prefix}.{prop_name}" if prefix else prop_name

            if prop_def.get("type") == "object" and "properties" in prop_def:
                extract_field_types_from_schema(prop_def, result, full_path)
            elif prop_def.get("type") == "array" and "items" in prop_def:
                if prop_def["items"].get("type") == "object":
                    # For arrays of objects, list the full path with []
                    extract_field_types_from_schema(
                        prop_def["items"], result, f"{full_path}[]"
                    )
                else:
                    result[full_path + "[]"] = prop_def["items"].get("type", "string")
            else:
                # Primitive type or enum
                if "enum" in prop_def:
                    result[full_path] = "category"
                else:
                    type_mapping = {
                        "boolean": "boolean",
                        "integer": "number",
                        "number": "number",
                        "string": "string",
                    }
                    result[full_path] = type_mapping.get(
                        prop_def.get("type", "string"), "string"
                    )

            if prop_def.get("format") in ["date", "date-time"]:
                result[full_path] = "date"


# As sqlite does not support timezone-aware datetimes, we have to do this manually.
# Make extra-sure that all datetimes are timezone-aware to utc before saving to the database!
def _make_aware(dt):
    """Make a datetime timezone-aware, assuming UTC if naive."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def test_remote_image_support(api_url: str, model: str, api_key: str) -> bool:
    img = Image.new("RGB", (1, 1), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in one word."},
                    {"type": "image_url", "image_url": f"data:image/png;base64,{b64}"},
                ],
            }
        ],
        "max_tokens": 3,
    }
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        data = response.json()
        if not response.ok or "choices" not in data:
            return False
        reply = data["choices"][0].get("message", {}).get("content", "").lower()
        # You may want to adjust the check below based on expected behavior
        if (
            "white" in reply
            or "blank" in reply
            or "cannot" in reply
            or "empty" in reply
        ):
            return True
        return False
    except Exception:
        return False
