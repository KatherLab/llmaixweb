# backend/src/utils/helpers.py
import base64
import io
import json
import mimetypes
import zipfile
from datetime import datetime, timezone
from typing import Any

import requests
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.src import models, schemas
from backend.src.utils.api_errors import api_error

# If your enums/constants are here:

CSV_MIME = "text/csv"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
XLS_MIME = "application/vnd.ms-excel"


def trial_display_label(trial: Any) -> str:
    """Human-facing label for a trial.

    Prefers the user-set ``name`` and falls back to the per-project sequence
    number (``Trial #N``) only when no name is set — mirrors the frontend
    ``trialLabel`` helper. Never uses the global DB ``id``.
    """
    name = (trial.name or "").strip()
    if name:
        return name
    return f"Trial #{trial.project_trial_number}"


def trial_filename_slug(trial: Any) -> str:
    """Filesystem-safe slug identifying a trial, for download filenames.

    Uses the user-set name when present (slugified), otherwise ``trial_N`` from
    the per-project sequence number.
    """
    import re

    name = (trial.name or "").strip()
    if name:
        slug = re.sub(r"[^\w.-]+", "_", name).strip("_.")
        if slug:
            return slug[:80]
    return f"trial_{trial.project_trial_number}"


def content_disposition(filename: str, disposition: str = "attachment") -> str:
    """Build a Content-Disposition header value with a safely-encoded filename.

    Percent-encoding (RFC 5987) neutralizes quotes, CR/LF and non-ASCII in
    user-controlled file names, which could otherwise break the header or
    smuggle extra directives into it.
    """
    import urllib.parse

    quoted = urllib.parse.quote(filename or "download", safe="")
    return f"{disposition}; filename=\"{quoted}\"; filename*=UTF-8''{quoted}"


def excel_sheet_name(
    label: str, fallback: str = "Sheet", used: set[str] | None = None
) -> str:
    """Sanitize an arbitrary label into a valid, unique Excel sheet name.

    Excel forbids the characters ``: \\ / ? * [ ]`` and caps sheet names at 31
    characters. When ``used`` is provided, ensures the returned name is unique
    within it (appending a numeric suffix on collision) and records it — needed
    because duplicate trial names would otherwise make xlsxwriter raise.
    """
    import re

    cleaned = re.sub(r"[:\\/?*\[\]]", " ", label).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        cleaned = fallback
    name = cleaned[:31]
    if used is not None:
        base = name
        i = 2
        while name in used:
            suffix = f" ({i})"
            name = base[: 31 - len(suffix)] + suffix
            i += 1
        used.add(name)
    return name


def detect_text_encoding(
    content: bytes, fallback_chain: str, use_chardet: bool = True
) -> str:
    """Detect the encoding of raw text/CSV bytes.

    Tries chardet (when available and ``use_chardet``), then each encoding in
    the comma-separated ``fallback_chain``, returning the first that decodes
    cleanly. Falls back to ``"utf-8"`` (caller should decode with
    ``errors="replace"`` in that case). Shared by preprocessing and the
    ground-truth parser so both handle non-UTF-8 uploads the same way.
    """
    if use_chardet:
        try:
            import chardet

            result = chardet.detect(content[:1024])
            if result and result.get("confidence", 0) > 0.7:
                detected = result.get("encoding") or "utf-8"
                try:
                    content.decode(detected)
                    return detected
                except (UnicodeDecodeError, LookupError):
                    pass
        except ImportError:
            pass

    for encoding in [e.strip() for e in fallback_chain.split(",") if e.strip()]:
        try:
            content.decode(encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue

    return "utf-8"


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
    Yields ``(arcname, bytes)`` entries for a ZIP, using the export helpers and
    pandas. A generator so the caller can stream the archive without holding
    every entry (notably per-document texts) in memory at once.
    """
    import csv
    import io

    import pandas as pd

    # --- Summary CSV/XLSX ---
    if zip_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Evaluation ID",
                "Trial",
                "Trial Number",
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
            gt = db.get(models.GroundTruth, eval_obj.groundtruth_id)
            writer.writerow(
                [
                    eval_obj.id,
                    trial_display_label(trial),
                    trial.project_trial_number,
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
        yield (("summary.csv", output.getvalue().encode("utf-8")))

    else:
        output = io.BytesIO()
        summary_data = []
        for eval_obj, trial in evaluations:
            gt = db.get(models.GroundTruth, eval_obj.groundtruth_id)
            summary_data.append(
                {
                    "Evaluation ID": eval_obj.id,
                    "Trial": trial_display_label(trial),
                    "Trial Number": trial.project_trial_number,
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
        yield (("summary.xlsx", output.getvalue()))

    # Field-level metrics are exported with precision/recall/F1 alongside
    # accuracy — a researcher comparing fields usually cares more about recall
    # (what the model missed) than accuracy alone.
    field_metric_columns = [
        "Evaluation ID",
        "Field Name",
        "Accuracy",
        "Precision",
        "Recall",
        "F1 Score",
        "Total Count",
        "Correct Count",
        "Error Count",
    ]

    def _field_metric_row(eval_obj, field, metrics):
        return [
            eval_obj.id,
            field,
            metrics.get("accuracy", 0),
            metrics.get("precision", 0),
            metrics.get("recall", 0),
            metrics.get("f1_score", 0),
            metrics.get("total_count", 0),
            metrics.get("correct_count", 0),
            metrics.get("error_count", 0),
        ]

    # --- Field-level metrics (accuracy + precision/recall/F1 per field) ---
    if include_details:
        field_rows = []
        for eval_obj, _ in evaluations:
            for field, metrics in (eval_obj.field_metrics or {}).items():
                field_rows.append(_field_metric_row(eval_obj, field, metrics))
        if field_rows:
            if zip_format == "csv":
                out = io.StringIO()
                w = csv.writer(out)
                w.writerow(field_metric_columns)
                for row in field_rows:
                    w.writerow(row)
                yield (("field_metrics.csv", out.getvalue().encode("utf-8")))
            else:
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                    pd.DataFrame(field_rows, columns=field_metric_columns).to_excel(
                        writer, sheet_name="Field Metrics", index=False
                    )
                out.seek(0)
                yield (("field_metrics.xlsx", out.getvalue()))

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
                yield (("field_details.csv", out.getvalue().encode("utf-8")))
            else:
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                    pd.DataFrame(details).to_excel(
                        writer, sheet_name="Field Details", index=False
                    )
                out.seek(0)
                yield (("field_details.xlsx", out.getvalue()))

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
                yield (("document_metrics.csv", out.getvalue().encode("utf-8")))
            else:
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                    pd.DataFrame(doc_data).to_excel(
                        writer, sheet_name="Doc Metrics", index=False
                    )
                out.seek(0)
                yield (("document_metrics.xlsx", out.getvalue()))

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
                yield (
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
                    yield (
                        (f"docs/{doc_id}.txt", doc["Document Content"].encode("utf-8"))
                    )
                if (
                    include_ground_truth_content
                    and "Ground Truth" in doc
                    and doc["Ground Truth"]
                ):
                    gt = doc["Ground Truth"]
                    if isinstance(gt, str):
                        yield ((f"docs/{doc_id}_gt.txt", gt.encode("utf-8")))
                    else:
                        yield (
                            (
                                f"docs/{doc_id}_gt.json",
                                json.dumps(gt, ensure_ascii=False, indent=2).encode(
                                    "utf-8"
                                ),
                            )
                        )


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

    # Batch-load all referenced documents with original_file eager-loaded
    # (avoids N+1: previously one db.get + lazy original_file per result).
    doc_ids = [r.document_id for r in results if r.document_id is not None]
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

    docs = []
    gt_cache = {}
    # For each result/document, gather metadata
    for result in results:
        doc = document_lookup.get(result.document_id)
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
                    if doc.document_name is not None and doc.document_name in gt_data
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
                    if items_schema.get("type") == "object" and isinstance(item, dict):
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

    # bool is a subclass of int in Python, so isinstance(True, int) is True.
    # A boolean is not a valid integer/number — reject it explicitly.
    if expected_type in ("integer", "number") and isinstance(value, bool):
        return (
            f"Field '{field_path}' expects a {expected_type} but got boolean "
            f"'{value}'. Please use a numeric value."
        )

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
    """Validate that at least one prompt is present.

    Note: The {document_content} placeholder is no longer required.
    If missing, the document content is auto-appended with clear markers.
    """
    # Check that at least one prompt is provided
    if not prompt.system_prompt and not prompt.user_prompt:
        raise api_error(
            "core.prompt_required",
            400,
            "At least one of system_prompt or user_prompt must be provided",
        )

    # Placeholder validation removed - document is auto-injected if placeholder is missing


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


def _resolve_schema_type(prop_def: dict) -> str:
    """Resolve a JSON-schema property to a single normalized type string.

    Handles the common cases that the raw ``type`` key does not cover:
    nullable types (``"type": ["string", "null"]``), ``anyOf``/``oneOf``
    unions, and ``$ref`` / ``const`` definitions. Returns the first non-null
    type (mapped to our internal vocabulary), falling back to ``"string"``.
    """
    type_mapping = {
        "boolean": "boolean",
        "integer": "number",
        "number": "number",
        "string": "string",
    }

    raw_type = prop_def.get("type")
    # A list type (e.g. ["string", "null"]) means nullable; pick the first
    # non-null member. A plain string type is the common case.
    if isinstance(raw_type, list):
        candidates = [t for t in raw_type if t != "null"]
        raw_type = candidates[0] if candidates else None
    if isinstance(raw_type, str):
        return type_mapping.get(raw_type, "string")

    # anyOf / oneOf: pick the first non-null member schema's type.
    for combiner in ("anyOf", "oneOf"):
        sub_schemas = prop_def.get(combiner)
        if isinstance(sub_schemas, list):
            for sub in sub_schemas:
                if isinstance(sub, dict) and sub.get("type") != "null":
                    return _resolve_schema_type(sub)

    # $ref: an unresolvable reference at this layer — treat as opaque/string
    # rather than crashing, so mapping still works.
    if prop_def.get("$ref") is not None or prop_def.get("const") is not None:
        return "string"

    return "string"


def extract_field_types_from_schema(schema_def: dict, result: dict, prefix: str = ""):
    """Extract all field types from a JSON schema as dot notation (leaf paths)."""
    if "properties" in schema_def:
        for prop_name, prop_def in schema_def["properties"].items():
            full_path = f"{prefix}.{prop_name}" if prefix else prop_name

            if prop_def.get("type") == "object" and "properties" in prop_def:
                extract_field_types_from_schema(prop_def, result, full_path)
            elif prop_def.get("type") == "array" and "items" in prop_def:
                items = prop_def["items"]
                if isinstance(items, dict) and items.get("type") == "object":
                    # For arrays of objects, list the full path with []
                    extract_field_types_from_schema(items, result, f"{full_path}[]")
                else:
                    result[full_path + "[]"] = (
                        _resolve_schema_type(items)
                        if isinstance(items, dict)
                        else "string"
                    )
            else:
                # Primitive type or enum
                if "enum" in prop_def:
                    result[full_path] = "category"
                else:
                    result[full_path] = _resolve_schema_type(prop_def)

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
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
        "max_tokens": 3,
    }
    try:
        # allow_redirects=False: a user-controlled endpoint must not 3xx-bounce
        # the request to a blocked internal address (SSRF redirect bypass).
        response = requests.post(
            api_url, json=payload, headers=headers, timeout=10, allow_redirects=False
        )
        data = response.json()
        if not response.ok or "choices" not in data:
            return False
        reply = (data["choices"][0].get("message", {}).get("content") or "").lower()
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
