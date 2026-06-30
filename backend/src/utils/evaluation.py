# backend/src/utils/evaluation.py
import io
import json
import logging
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from pandas.errors import ParserError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from thefuzz import fuzz

from .. import models
from .enums import ComparisonMethod, FieldType
from .helpers import flatten_dict
from .json_utils import make_jsonable

logger = logging.getLogger(__name__)


def _is_missing(value: Any) -> bool:
    """True if ``value`` is None/NaN/empty — safe for array-like values.

    ``pd.isna`` returns a numpy bool *array* (not a scalar) when given a list
    or array, and using that in a boolean expression raises
    ``ValueError: The truth value of an array ... is ambiguous``. That crashed
    evaluation for any schema field holding a list (common in lab data) and —
    because the per-document eval handler swallows the exception — silently
    marked those documents 0% accurate. Guard array-likes explicitly.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return value == ""
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


class EvaluationEngine:
    """Main evaluation engine with enhanced concurrency handling."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self._cache = {}
        # Store engine for creating new sessions in parallel processing
        self.engine = db_session.bind
        # Validation warnings from the most recent evaluate_trial() call
        # (e.g. low document↔GT match rate). Read by the API layer to surface
        # in the response. Reset on each call.
        self.last_warnings: List[str] = []

    def evaluate_trial(
        self, trial_id: int, groundtruth_id: int, force_recalculate: bool = False
    ) -> models.Evaluation:
        """Evaluate a trial against ground truth with comprehensive validation."""

        # Reset warnings from any previous evaluate_trial() call on this engine.
        self.last_warnings = []

        # Pre-validation phase
        validation_result = self._validate_evaluation_prerequisites(
            trial_id, groundtruth_id
        )
        if not validation_result["valid"]:
            raise ValueError(
                f"Evaluation prerequisites not met: {'; '.join(validation_result['errors'])}"
            )

        # Check cache. A cached evaluation is reused only when the trial's
        # results have not changed since it was computed — otherwise the user
        # would silently see metrics for stale results. (Field-mapping, ID-column
        # and ground-truth file changes already delete the cached evaluation;
        # this guards against the trial simply being re-run.)
        if not force_recalculate:
            existing = (
                self.db.query(models.Evaluation)
                .filter_by(trial_id=trial_id, groundtruth_id=groundtruth_id)
                .first()
            )
            if existing:
                latest_result_update = (
                    self.db.query(func.max(models.TrialResult.updated_at))
                    .filter_by(trial_id=trial_id)
                    .scalar()
                )
                if (
                    latest_result_update is None
                    or existing.created_at >= latest_result_update
                ):
                    return existing
                # Results changed since the cached evaluation → recompute.
                # Delete the stale row first (cascade removes its
                # EvaluationMetric children) so we don't leave duplicate
                # evaluations for the same (trial, ground truth) pair.
                self.db.delete(existing)
                self.db.flush()

        # Load validated data
        trial = self.db.get(models.Trial, trial_id)
        ground_truth = self.db.get(models.GroundTruth, groundtruth_id)
        results = self.db.query(models.TrialResult).filter_by(trial_id=trial_id).all()

        # Load and validate ground truth data
        gt_data = self._load_ground_truth(ground_truth)
        field_mappings = self._get_field_mappings(ground_truth, trial.schema_id)

        # Final data consistency check
        consistency_check = self._validate_data_consistency(
            results, gt_data, field_mappings
        )
        if not consistency_check["valid"]:
            raise ValueError(
                f"Data consistency issues: {'; '.join(consistency_check['errors'])}"
            )
        # Stash validation warnings (e.g. low document↔GT match rate) so the
        # API layer can surface them in the response — they no longer block
        # evaluation, but a researcher should still see them.
        self.last_warnings = consistency_check.get("warnings", [])

        # Pre-load all document data to avoid session issues in parallel processing
        document_data = self._preload_document_data(results)

        # Evaluate with enhanced error handling
        evaluation_results = self._evaluate_parallel(
            results, gt_data, field_mappings, document_data
        )

        # Calculate metrics (field_mappings drives confusion-matrix scoping)
        metrics = self._calculate_metrics(evaluation_results, field_mappings)

        # Create evaluation record
        evaluation = models.Evaluation(
            trial_id=trial_id,
            groundtruth_id=groundtruth_id,
            metrics=metrics["overall"],
            field_metrics=metrics["fields"],
            document_metrics=metrics["documents"],
            confusion_matrices=metrics.get("confusion_matrices"),
        )

        # Store detailed metrics
        for detail in evaluation_results["detailed_metrics"]:
            metric = models.EvaluationMetric(**detail)
            evaluation.detailed_metrics.append(metric)

        self.db.add(evaluation)
        self.db.commit()
        return evaluation

    def _validate_evaluation_prerequisites(
        self, trial_id: int, groundtruth_id: int
    ) -> Dict:
        """Comprehensive validation before evaluation starts."""
        errors = []
        warnings = []

        # Check trial exists
        trial = self.db.get(models.Trial, trial_id)
        if not trial:
            errors.append(f"Trial {trial_id} not found")
            return {"valid": False, "errors": errors}

        # Check trial is completed
        if trial.status != "completed":
            errors.append(f"Trial {trial_id} is not completed (status: {trial.status})")

        # Check ground truth exists
        ground_truth = self.db.get(models.GroundTruth, groundtruth_id)
        if not ground_truth:
            errors.append(f"Ground truth {groundtruth_id} not found")
            return {"valid": False, "errors": errors}

        # Check trial has results
        results = self.db.query(models.TrialResult).filter_by(trial_id=trial_id).all()
        if not results:
            errors.append(f"No results found for trial {trial_id}")

        # Check field mappings exist for this schema
        mappings = (
            self.db.query(models.FieldMapping)
            .filter_by(ground_truth_id=groundtruth_id, schema_id=trial.schema_id)
            .all()
        )
        if not mappings:
            errors.append(
                f"No field mappings configured for ground truth {groundtruth_id} and schema {trial.schema_id}"
            )

        # Validate ground truth data can be loaded
        try:
            gt_data = self._load_ground_truth(ground_truth)
            if not gt_data:
                errors.append("Ground truth data is empty or invalid")
        except Exception as e:
            errors.append(f"Failed to load ground truth data: {str(e)}")
            return {"valid": False, "errors": errors}

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _load_documents_for_results(
        self, results: List[models.TrialResult]
    ) -> Dict[int, models.Document]:
        """Batch-load all Documents referenced by ``results`` with their
        ``original_file`` eager-loaded.

        Replaces the per-result ``db.get(Document, id)`` + lazy
        ``document.original_file`` pattern (2 queries × N results → 2 queries
        total). Returns a ``{doc_id: Document}`` map; missing docs are absent.
        """
        doc_ids = []
        for result in results:
            try:
                doc_ids.append(int(result.document_id))
            except (ValueError, TypeError):
                continue
        if not doc_ids:
            return {}
        documents = (
            self.db.execute(
                select(models.Document)
                .where(models.Document.id.in_(doc_ids))
                .options(selectinload(models.Document.original_file))
            )
            .scalars()
            .all()
        )
        return {doc.id: doc for doc in documents}

    def _validate_data_consistency(
        self, results: List[models.TrialResult], gt_data: Dict, field_mappings: Dict
    ) -> Dict:
        """Validate that trial results can be matched with ground truth data."""
        errors = []
        warnings = []

        total_results = len(results)
        matched_count = 0
        unmatched_documents = []

        # Build document lookup for better error reporting (batch-loaded with
        # original_file eager-loaded to avoid N+1 queries).
        document_lookup = self._load_documents_for_results(results)

        for result in results:
            doc_id = result.document_id

            # Check if document exists
            if doc_id not in document_lookup:
                errors.append(f"Document {doc_id} not found in database")
                continue

            document = document_lookup[doc_id]

            # Try to find ground truth key. Use the SAME matcher as the actual
            # evaluation (_find_document_key_by_data) so the validation match
            # rate reflects what evaluation will really achieve.
            doc_info = {
                "document_name": document.document_name,
                "filename": document.original_file.file_name
                if document.original_file
                else None,
            }
            gt_key = self._find_document_key_by_data(doc_id, doc_info, gt_data)
            if gt_key:
                matched_count += 1
            else:
                # No real ground-truth match — always unmatched, regardless of
                # whether the document has a name. (Previously a document with a
                # name but no GT match was counted as matched, inflating the
                # match percentage and suppressing the mismatch warnings.)
                label = document.document_name if document.document_name else "Unknown"
                unmatched_documents.append({"doc_id": doc_id, "filename": label})

        # Calculate match percentage
        match_percentage = (
            (matched_count / total_results) * 100 if total_results > 0 else 0
        )

        # Match-rate and unmatched-document signals are warnings, not hard
        # errors: the engine already handles unmatched documents correctly
        # (they become error-document rows excluded from accuracy), so there is
        # no correctness reason to block evaluation. Surfacing them as warnings
        # lets a researcher evaluate partial-overlap ground truth while still
        # seeing that some documents could not be matched.
        if match_percentage < 50:
            warnings.append(
                f"Only {match_percentage:.1f}% of documents have matching ground truth data. "
                f"This suggests a mismatch between document identifiers and ground truth keys."
            )
        elif match_percentage < 80:
            warnings.append(
                f"Only {match_percentage:.1f}% of documents have matching ground truth data"
            )

        if unmatched_documents:
            # Show sample of unmatched documents
            sample_unmatched = unmatched_documents[:3]
            unmatched_list = [
                f"Document {doc['doc_id']} ({doc['filename']})"
                for doc in sample_unmatched
            ]
            if len(unmatched_documents) > 3:
                unmatched_list.append(f"... and {len(unmatched_documents) - 3} more")

            # Show available ground truth keys for debugging
            available_keys = list(gt_data.keys())[:5]
            warnings.append(
                f"Documents without ground truth matches: {', '.join(unmatched_list)}. "
                f"Available ground truth keys: {available_keys}. "
                f"Please check that ground truth keys match document IDs or filenames."
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "match_percentage": match_percentage,
            "matched_count": matched_count,
            "total_count": total_results,
        }

    def _preload_document_data(self, results: List[models.TrialResult]) -> Dict:
        """Pre-load all document data to avoid session issues in parallel processing."""
        document_data = {}

        # Batch-load documents (with original_file eager-loaded) instead of one
        # db.get + lazy load per result.
        document_lookup = self._load_documents_for_results(results)

        for result in results:
            doc_id = result.document_id
            try:
                doc_id = int(doc_id)
                document = document_lookup.get(doc_id)
                if document:
                    # Store relevant document data
                    document_data[doc_id] = {
                        "id": document.id,
                        "filename": document.original_file.file_name
                        if document.original_file
                        else None,
                        "document_name": document.document_name
                        if document.document_name
                        else None,
                        "exists": True,
                    }
                else:
                    document_data[doc_id] = {"exists": False}
            except (ValueError, TypeError):
                logger.warning("Error converting document ID: %s", doc_id)
                document_data[doc_id] = {
                    "exists": False,
                    "error": "Invalid document ID",
                }
            except Exception:
                logger.exception("Error loading document %s", doc_id)

        return document_data

    def get_available_columns(self, ground_truth: models.GroundTruth) -> List[str]:
        """
        Return header names for tabular ground truth exactly as they appear
        in the file (trimmed), so the chosen ID column is never "lost".
        For CSV: read only headers. For XLSX: union headers across sheets.
        """
        if ground_truth.format not in ["csv", "xlsx"]:
            return []

        # read raw file bytes
        from ..dependencies import get_file

        content = get_file(ground_truth.file_uuid)

        def _norm(x):  # keep original string but trim edges
            return str(x).strip()

        if ground_truth.format == "csv":
            try:
                df = pd.read_csv(io.BytesIO(content), nrows=0)
            except Exception as e:
                raise ValueError(f"Failed to read CSV headers: {e}")
            return [_norm(c) for c in df.columns.tolist()]

        # xlsx
        try:
            xls = pd.ExcelFile(io.BytesIO(content))
        except Exception as e:
            raise ValueError(f"Invalid Excel file: {e}")

        seen = set()
        cols: List[str] = []
        for sheet in xls.sheet_names:
            try:
                df = xls.parse(sheet, nrows=0)
            except Exception:
                continue
            for c in df.columns.tolist():
                s = _norm(c)
                if s and s.lower() not in seen:
                    seen.add(s.lower())
                    cols.append(s)
        return cols

    def _load_ground_truth(self, ground_truth: models.GroundTruth) -> Dict:
        """Load ground truth data with caching."""
        # Check cache
        if ground_truth.data_cache:
            return ground_truth.data_cache

        # Load from file
        from ..dependencies import get_file

        content = get_file(ground_truth.file_uuid)
        parser = GroundTruthParser()

        # Pass ID column for CSV/XLSX files
        if ground_truth.format in ["csv", "xlsx"]:
            data = parser.parse(
                content, ground_truth.format, id_column=ground_truth.id_column_name
            )
        else:
            data = parser.parse(content, ground_truth.format)

        data = make_jsonable(data)

        # Cache parsed data
        ground_truth.data_cache = data
        try:
            self.db.commit()
        except TypeError as e:
            raise ValueError(f"Ground truth contains non-JSON-serializable values: {e}")

        return data

    def _get_field_mappings(
        self, ground_truth: models.GroundTruth, schema_id: int
    ) -> Dict:
        """Get field mappings for specific schema."""
        mappings = {}

        # Load mappings for this specific schema
        for mapping in ground_truth.field_mappings:
            if mapping.schema_id == schema_id:
                mappings[mapping.schema_field] = {
                    "gt_field": mapping.ground_truth_field,
                    "type": mapping.field_type,
                    "method": mapping.comparison_method,
                    "options": mapping.comparison_options or {},
                }

        return mappings

    def validate_json_against_schema(
        self, json_data: Dict, schema_def: Dict
    ) -> Dict[str, List[str]]:
        """Validate JSON ground truth against schema definition."""
        errors = []
        warnings = []

        # Extract required fields from schema
        required_fields = self._extract_required_fields(schema_def)

        # Check for missing required fields
        for field in required_fields:
            if field not in json_data:
                errors.append(f"Missing required field: {field}")

        # Validate data types
        for field, value in json_data.items():
            expected_type = self._get_expected_type(field, schema_def)
            if expected_type and not self._validate_type(value, expected_type):
                errors.append(
                    f"Field '{field}' has wrong type. Expected {expected_type}"
                )

        # Extra fields are OK (warnings only)
        schema_fields = self._extract_all_fields(schema_def)
        for field in json_data:
            if field not in schema_fields and field not in ["id", "document_id"]:
                warnings.append(
                    f"Extra field '{field}' not in schema (will be ignored)"
                )

        return {"errors": errors, "warnings": warnings}

    def _evaluate_parallel(
        self,
        results: List[models.TrialResult],
        gt_data: Dict,
        field_mappings: Dict,
        document_data: Dict,
    ) -> Dict:
        """
        Evaluate all TrialResult objects in parallel **without passing ORM
        instances to worker threads**.  Each worker receives only primitive
        data (document_id + prediction JSON) so no SQLAlchemy session is ever
        touched outside the main thread.
        """
        detailed_metrics: List[Dict] = []
        doc_evaluations: List[Dict] = []

        # A modest pool avoids exhausting the Postgres connection pool
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []

            for result in results:
                # Build a plain‑Python payload
                payload = {
                    "document_id": result.document_id,
                    "prediction": result.result,  # already a dict
                }
                future = executor.submit(
                    self._evaluate_document_isolated,
                    payload,
                    gt_data,
                    field_mappings,
                    document_data,
                )
                futures.append((result.document_id, future))

            # Collect results
            for doc_id, future in futures:
                try:
                    doc_eval = future.result()
                    doc_evaluations.append(doc_eval)
                    detailed_metrics.extend(doc_eval["detailed_metrics"])
                except Exception as exc:  # noqa: BLE001
                    logger.exception("EvaluationEngine error on doc %s", doc_id)
                    doc_evaluations.append(
                        self._create_error_result(doc_id, f"Evaluation failed: {exc}")
                    )

        return {
            "document_evaluations": doc_evaluations,
            "detailed_metrics": detailed_metrics,
        }

    def _evaluate_document_isolated(
        self,
        result_payload: Dict,
        gt_data: Dict,
        field_mappings: Dict,
        document_data: Dict,
    ) -> Dict:
        """Evaluate a single document with proper JSON nested structure handling."""
        doc_id = result_payload["document_id"]

        # Ensure numeric ID
        try:
            doc_id_int = int(doc_id)
        except (ValueError, TypeError):
            return self._create_error_result(doc_id, f"Invalid document ID: {doc_id}")

        # Check we have pre-loaded metadata for this document
        if not document_data.get(doc_id_int, {}).get("exists", False):
            return self._create_error_result(doc_id, "Document not found in database")

        doc_info = document_data[doc_id_int]

        # Locate ground-truth record
        gt_key = self._find_document_key_by_data(doc_id_int, doc_info, gt_data)
        if gt_key is None or gt_key not in gt_data:
            filename = doc_info.get("filename", "Unknown")
            return self._create_error_result(
                doc_id,
                f"No ground truth found for document {doc_id} (filename: {filename})",
            )

        gt_values = gt_data[gt_key]

        # Check if ground truth is JSON (nested) or CSV (flattened)
        is_json_gt = isinstance(gt_values, dict) and any(
            isinstance(v, dict) for v in gt_values.values()
        )

        # Prepare prediction values
        pred_values = result_payload["prediction"]

        # Evaluate field-by-field
        detailed_metrics = []
        correct_count = 0
        total_count = 0
        missing_fields = []
        incorrect_fields = []

        for schema_field, mapping in field_mappings.items():
            gt_field = mapping["gt_field"]

            # For JSON ground truth, use direct nested access
            if is_json_gt:
                gt_val = self._get_nested_value(gt_values, gt_field)
                pred_val = self._get_nested_value(pred_values, schema_field)
            else:
                # For CSV ground truth, use flattened access with dots
                if gt_field not in gt_values:
                    continue
                gt_val = gt_values[gt_field]

                # Flatten prediction for CSV comparison
                pred_values_flat = flatten_dict(pred_values, sep=".")
                pred_val = pred_values_flat.get(schema_field)

            if gt_val is None:
                continue  # Skip if ground truth doesn't have this field

            total_count += 1

            comparison = self._compare_values(
                gt_val,
                pred_val,
                mapping["type"],
                mapping["method"],
                mapping["options"],
            )

            if comparison["is_correct"]:
                correct_count += 1
            else:
                if comparison["error_type"] == "missing":
                    missing_fields.append(schema_field)
                else:
                    incorrect_fields.append(schema_field)

            detailed_metrics.append(
                {
                    "document_id": doc_id,
                    "field_name": schema_field,
                    "ground_truth_value": str(gt_val) if gt_val is not None else None,
                    "predicted_value": str(pred_val) if pred_val is not None else None,
                    "is_correct": comparison["is_correct"],
                    "error_type": comparison["error_type"],
                    "confidence_score": comparison.get("confidence_score"),
                }
            )

        accuracy = correct_count / total_count if total_count else 0.0

        return {
            "document_id": doc_id,
            "accuracy": accuracy,
            "correct_fields": correct_count,
            "total_fields": total_count,
            "missing_fields": missing_fields,
            "incorrect_fields": incorrect_fields,
            "detailed_metrics": detailed_metrics,
        }

    def _get_nested_value(self, data: dict, path: str, default=None):
        keys = path.replace("[]", ".0").split(
            "."
        )  # crude handling for first array element
        value = data
        try:
            for key in keys:
                # List index?
                if key.isdigit():
                    value = value[int(key)]
                elif key:
                    value = value[key]
            return value
        except Exception:
            return default

    def _find_document_key_by_data(
        self, doc_id: int, doc_info: Dict, gt_data: Dict
    ) -> Optional[str]:
        """
        Find document key using pre-loaded document data, prioritizing document_name.

        Tries the following, in order:
        1. document_name (case-insensitive, with and without file extension)
        2. filename (case-insensitive, with and without extension)
        3. doc_id (int and str)
        """
        # Get both document_name and filename
        document_name = doc_info.get("document_name")
        filename = doc_info.get("filename")

        # Prepare all GT keys for lower-case matching
        gt_keys_lower = {str(k).lower(): k for k in gt_data.keys()}

        # 1. Try document_name (with and without extension)
        if document_name:
            docname_lower = document_name.lower()
            docname_stem_lower = Path(document_name).stem.lower()

            # With extension
            if docname_lower in gt_keys_lower:
                return gt_keys_lower[docname_lower]
            # Without extension
            if docname_stem_lower in gt_keys_lower:
                return gt_keys_lower[docname_stem_lower]

        # 2. Try filename (with and without extension)
        if filename:
            filename_lower = filename.lower()
            filename_stem_lower = Path(filename).stem.lower()
            # With extension
            if filename_lower in gt_keys_lower:
                return gt_keys_lower[filename_lower]
            # Without extension
            if filename_stem_lower in gt_keys_lower:
                return gt_keys_lower[filename_stem_lower]
            # Also try only the base filename (in case of folders in path)
            filename_name_lower = Path(filename).name.lower()
            filename_name_stem_lower = Path(filename).stem.lower()
            if filename_name_lower in gt_keys_lower:
                return gt_keys_lower[filename_name_lower]
            if filename_name_stem_lower in gt_keys_lower:
                return gt_keys_lower[filename_name_stem_lower]

        # 3. Try doc_id as str (sometimes in GT CSVs)
        for variant in [doc_id, str(doc_id), f"doc_{doc_id}", f"document_{doc_id}"]:
            if str(variant).lower() in gt_keys_lower:
                return gt_keys_lower[str(variant).lower()]

        # No match found
        return None

    def _create_error_result(self, doc_id: Any, error_message: str) -> Dict:
        """Create standardized error result."""
        return {
            "document_id": doc_id,
            "error": error_message,
            "accuracy": 0.0,
            "correct_fields": 0,
            "total_fields": 0,
            "missing_fields": [],
            "incorrect_fields": [],
            "detailed_metrics": [],
        }

    def _compare_values(
        self,
        gt_value: Any,
        pred_value: Any,
        field_type: str,
        method: str,
        options: Dict,
    ) -> Dict:
        """Compare two values based on type and method."""
        comparator = ValueComparator()
        return comparator.compare(gt_value, pred_value, field_type, method, options)

    def _calculate_metrics(
        self, evaluation_results: Dict, field_mappings: Dict
    ) -> Dict:
        """Calculate overall and field-level metrics."""
        calculator = MetricsCalculator()
        evaluation_results["field_mappings"] = field_mappings
        return calculator.calculate(evaluation_results)


class GroundTruthParser:
    """Parser for different ground truth formats."""

    def parse(
        self, content: bytes, format_type: str, id_column: Optional[str] = None
    ) -> Dict:
        """Parse ground truth content based on format."""
        if format_type == "json":
            return self._parse_json(content)
        elif format_type == "csv":
            return self._parse_csv(content, id_column)
        elif format_type == "xlsx":
            return self._parse_excel(content, id_column)
        elif format_type == "zip":
            return self._parse_zip(content)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def _parse_json(self, content: bytes) -> Dict:
        """Parse JSON ground truth - maintains nested structures."""
        try:
            data = json.loads(content.decode("utf-8"))

            if isinstance(data, dict):
                if all(isinstance(v, dict) for v in data.values()):
                    # Document map format
                    result = {}
                    for key, doc_data in data.items():
                        if "id" in doc_data:
                            doc_id = str(doc_data["id"])
                        elif "patient_id" in doc_data:
                            doc_id = str(doc_data["patient_id"])
                        else:
                            doc_id = str(key)
                        result[doc_id] = doc_data
                    return make_jsonable(result)
                else:
                    # Single document
                    if "id" in data:
                        doc_id = str(data["id"])
                    elif "patient_id" in data:
                        doc_id = str(data["patient_id"])
                    else:
                        raise ValueError("JSON document must have 'id' or 'patient_id'")
                    return make_jsonable({doc_id: data})
            elif isinstance(data, list):
                result = {}
                for i, doc in enumerate(data):
                    if not isinstance(doc, dict):
                        raise ValueError(f"Document at index {i} is not an object")
                    if "id" in doc:
                        doc_id = str(doc["id"])
                    elif "patient_id" in doc:
                        doc_id = str(doc["patient_id"])
                    else:
                        raise ValueError(f"Doc at {i} missing 'id' or 'patient_id'")
                    result[doc_id] = doc
                return make_jsonable(result)
            else:
                raise ValueError("JSON must be an object or array")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    def _parse_zip(self, content: bytes) -> Dict:
        """Parse ZIP file with multiple JSON documents."""
        result = {}
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            json_files = [
                f
                for f in zf.namelist()
                if f.endswith(".json") and not f.startswith("__MACOSX/")
            ]
            if not json_files:
                raise ValueError("No JSON files found in ZIP archive")

            for filename in json_files:
                with zf.open(filename) as f:
                    try:
                        doc_data = json.loads(f.read().decode("utf-8"))
                        if "id" not in doc_data:
                            doc_id = Path(filename).stem
                            doc_data["id"] = doc_id
                        else:
                            doc_id = str(doc_data["id"])
                        result[doc_id] = doc_data
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON in {filename}: {e}")
        return make_jsonable(result)

    def _parse_csv(self, content: bytes, id_column: Optional[str] = None) -> Dict:
        """Parse CSV ground truth."""
        df = pd.read_csv(io.BytesIO(content))
        df = df.convert_dtypes()
        df = df.where(pd.notna(df), None)

        # Choose ID column
        if id_column and id_column in df.columns:
            id_col = id_column
        else:
            candidates = ["document_id", "doc_id", "id", "filename", "file_name"]
            id_col = next((c for c in candidates if c in df.columns), "_index")
            if id_col == "_index":
                df["_index"] = df.index

        result = {}
        for _, row in df.iterrows():
            doc_id = row[id_col]
            values = {}
            for col in df.columns:
                if col == id_col or row[col] is None:
                    continue
                keys = col.split(".")
                current = values
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[keys[-1]] = row[col]
            if values:
                result[str(doc_id)] = make_jsonable(values)
        return result

    def _parse_excel(self, content: bytes, id_column: Optional[str] = None) -> Dict:
        """Parse XLSX ground truth (multi-sheet, dot notation)."""

        def _deep_merge(dst: Dict, src: Dict) -> None:
            for k, v in src.items():
                if k in dst and isinstance(dst[k], dict) and isinstance(v, dict):
                    _deep_merge(dst[k], v)
                else:
                    dst[k] = v

        try:
            xls = pd.ExcelFile(io.BytesIO(content))
        except Exception as e:
            raise ValueError(f"Invalid Excel file: {e}")

        result: Dict[str, Dict] = {}
        for sheet_name in xls.sheet_names:
            try:
                df = xls.parse(sheet_name)
            except Exception as e:
                raise ValueError(f"Failed to read sheet '{sheet_name}': {e}")
            if df is None or df.empty:
                continue

            df = df.convert_dtypes()
            df = df.where(pd.notna(df), None)

            if id_column and id_column in df.columns:
                id_col = id_column
            else:
                candidates = ["document_id", "doc_id", "id", "filename", "file_name"]
                id_col = next((c for c in candidates if c in df.columns), "_index")
                if id_col == "_index":
                    df["_index"] = df.index

            for _, row in df.iterrows():
                doc_id_val = row.get(id_col)
                if doc_id_val is None:
                    continue
                doc_id = str(doc_id_val)
                values: Dict[str, Any] = {}
                for col in df.columns:
                    if col == id_col or row[col] is None:
                        continue
                    keys = str(col).split(".")
                    current = values
                    for key in keys[:-1]:
                        if key not in current or not isinstance(current[key], dict):
                            current[key] = {}
                        current = current[key]
                    current[keys[-1]] = row[col]
                if values:
                    if doc_id not in result:
                        result[doc_id] = make_jsonable(values)
                    else:
                        _deep_merge(result[doc_id], make_jsonable(values))

        return make_jsonable(result)


class ValueComparator:
    """Compare values with different methods."""

    def compare(
        self,
        gt_value: Any,
        pred_value: Any,
        field_type: str,
        method: str,
        options: Dict,
    ) -> Dict:
        """Compare two values and return comparison result."""
        # Handle None values
        if gt_value is None and pred_value is None:
            return {"is_correct": True, "error_type": None}
        if pred_value is None:
            return {"is_correct": False, "error_type": "missing"}
        if gt_value is None:
            return {"is_correct": False, "error_type": "extra"}
        # Array-valued fields: compare element-wise as sets (order-independent).
        # Previously `_get_nested_value` collapsed arrays to their first element,
        # so a 5-item lab-values list scored "correct" if the first matched.
        if isinstance(gt_value, list) or isinstance(pred_value, list):
            return self._compare_list(gt_value, pred_value, field_type, method, options)
        # Convert to appropriate types
        gt_value = self._convert_value(gt_value, field_type)
        pred_value = self._convert_value(pred_value, field_type)
        # Compare based on method
        if method == "exact":
            return self._exact_compare(gt_value, pred_value, options)
        elif method == "fuzzy":
            return self._fuzzy_compare(gt_value, pred_value, options)
        elif method == "numeric":
            return self._numeric_compare(gt_value, pred_value, options)
        elif method == "boolean":
            return self._boolean_compare(gt_value, pred_value, options)
        elif method == "category":
            return self._category_compare(gt_value, pred_value, options)
        elif method == "date":
            return self._date_compare(gt_value, pred_value, options)
        else:
            return self._exact_compare(gt_value, pred_value, options)

    def _compare_list(
        self,
        gt_value: Any,
        pred_value: Any,
        field_type: str,
        method: str,
        options: Dict,
    ) -> Dict:
        """Compare two lists element-wise, order-independent (set semantics).

        A prediction is correct when every ground-truth element is matched by
        some predicted element and there are no extra predicted elements. Each
        element is scored with the underlying scalar comparison method, so
        ``numeric`` tolerance / ``fuzzy`` thresholds still apply per item.
        """
        gt_list = gt_value if isinstance(gt_value, list) else [gt_value]
        pred_list = pred_value if isinstance(pred_value, list) else [pred_value]

        # Fast path: equal-length and every element matches in order.
        if len(gt_list) == len(pred_list) and all(
            self.compare(g, p, field_type, method, options)["is_correct"]
            for g, p in zip(gt_list, pred_list)
        ):
            return {"is_correct": True, "error_type": None, "confidence_score": 1.0}

        # Set semantics: match each GT element to a distinct predicted element.
        unmatched_pred = list(pred_list)
        for g in gt_list:
            for i, p in enumerate(unmatched_pred):
                if p is None:
                    continue
                if self.compare(g, p, field_type, method, options)["is_correct"]:
                    unmatched_pred[i] = None
                    break
            else:
                # No predicted element matched this GT element → missing item.
                return {
                    "is_correct": False,
                    "error_type": "missing",
                    "confidence_score": 0.0,
                }
        # Any leftover predicted elements are extras.
        extras = [p for p in unmatched_pred if p is not None]
        if extras:
            return {
                "is_correct": False,
                "error_type": "extra",
                "confidence_score": 0.0,
            }
        return {"is_correct": True, "error_type": None, "confidence_score": 1.0}

    def _convert_value(self, value: Any, field_type: str) -> Any:
        """Convert value to appropriate type."""
        if _is_missing(value):
            return None
        if field_type == "number":
            try:
                return float(value)
            except (ValueError, TypeError):
                return str(value)
        elif field_type == "boolean":
            return self._to_boolean(value)
        elif field_type == "date":
            return self._to_date(value)
        else:
            return str(value)

    def _exact_compare(self, gt: Any, pred: Any, options: Dict) -> Dict:
        """Exact string comparison."""
        case_sensitive = options.get("case_sensitive", False)
        if not case_sensitive:
            gt = str(gt).lower().strip()
            pred = str(pred).lower().strip()
        else:
            gt = str(gt).strip()
            pred = str(pred).strip()
        is_correct = gt == pred
        return {
            "is_correct": is_correct,
            "error_type": "mismatch" if not is_correct else None,
            "confidence_score": 1.0 if is_correct else 0.0,
        }

    def _fuzzy_compare(self, gt: Any, pred: Any, options: Dict) -> Dict:
        """Fuzzy string comparison.

        By default the score is ``max(ratio, token_sort_ratio)`` — both respect
        length/order, so they tolerate typos and word reordering ("chest pain"
        vs "pain chest") without rewarding pure substring containment.
        ``partial_ratio`` (which would mark "cancer" vs "non-cancer" as highly
        similar) is only included when ``allow_partial_match`` is set, because
        for medical/lab coding a substring match can invert the meaning.
        """
        threshold = options.get("threshold", 85)
        allow_partial = options.get("allow_partial_match", False)
        gt_str = str(gt).lower().strip()
        pred_str = str(pred).lower().strip()
        # Calculate similarity
        ratio = fuzz.ratio(gt_str, pred_str)
        token_sort_ratio = fuzz.token_sort_ratio(gt_str, pred_str)
        # Use best score
        score = max(ratio, token_sort_ratio)
        if allow_partial:
            score = max(score, fuzz.partial_ratio(gt_str, pred_str))
        is_correct = score >= threshold
        return {
            "is_correct": is_correct,
            "error_type": "fuzzy_mismatch" if not is_correct else None,
            "confidence_score": score / 100.0,
        }

    def _numeric_compare(self, gt: Any, pred: Any, options: Dict) -> Dict:
        """Numeric comparison with tolerance."""
        try:
            gt_num = float(gt)
            pred_num = float(pred)
        except (ValueError, TypeError):
            return {
                "is_correct": False,
                "error_type": "type_error",
                "confidence_score": 0.0,
            }
        tolerance = options.get("tolerance", 0.001)
        relative = options.get("relative", False)
        if relative and gt_num != 0:
            diff = abs((gt_num - pred_num) / gt_num)
            is_correct = diff <= tolerance
        else:
            diff = abs(gt_num - pred_num)
            is_correct = diff <= tolerance
        return {
            "is_correct": is_correct,
            "error_type": "numeric_mismatch" if not is_correct else None,
            "confidence_score": 1.0 - min(diff, 1.0),
        }

    def _boolean_compare(self, gt: Any, pred: Any, options: Dict) -> Dict:
        """Boolean comparison.

        A value that isn't a recognised boolean token (``true``/``false``/``yes``/
        ``no``/``1``/``0``/...) is a *type error* — it is not silently coerced to
        ``False``. Previously ``"maybe"`` vs ``"unknown"`` both defaulted to
        ``False`` and scored as a correct match, hiding genuine ambiguity in
        boolean clinical fields.
        """
        gt_bool = self._to_boolean(gt)
        pred_bool = self._to_boolean(pred)
        if gt_bool is None or pred_bool is None:
            return {
                "is_correct": False,
                "error_type": "type_error",
                "confidence_score": 0.0,
            }
        is_correct = gt_bool == pred_bool
        return {
            "is_correct": is_correct,
            "error_type": "boolean_mismatch" if not is_correct else None,
            "confidence_score": 1.0 if is_correct else 0.0,
        }

    def _category_compare(self, gt: Any, pred: Any, options: Dict) -> Dict:
        """Category comparison with mapping."""
        mappings = options.get("mappings", {})
        gt_str = str(gt).lower().strip()
        pred_str = str(pred).lower().strip()
        # Check direct match
        if gt_str == pred_str:
            return {"is_correct": True, "error_type": None, "confidence_score": 1.0}
        # Check mappings
        if gt_str in mappings:
            valid_values = mappings[gt_str]
            if isinstance(valid_values, str):
                valid_values = [valid_values]
            if pred_str in [v.lower() for v in valid_values]:
                return {"is_correct": True, "error_type": None, "confidence_score": 0.9}
        return {
            "is_correct": False,
            "error_type": "category_mismatch",
            "confidence_score": 0.0,
        }

    def _date_compare(self, gt: Any, pred: Any, options: Dict) -> Dict:
        """Date comparison."""
        gt_date = self._to_date(gt)
        pred_date = self._to_date(pred)
        if gt_date is None or pred_date is None:
            return {
                "is_correct": False,
                "error_type": "date_parse_error",
                "confidence_score": 0.0,
            }
        # Compare dates
        is_correct = gt_date == pred_date
        return {
            "is_correct": is_correct,
            "error_type": "date_mismatch" if not is_correct else None,
            "confidence_score": 1.0 if is_correct else 0.0,
        }

    def _to_boolean(self, value: Any) -> Optional[bool]:
        """Convert value to boolean.

        Returns ``None`` for values that are not recognised boolean tokens, so
        the caller can flag them as a type error rather than silently treating
        them as ``False``.
        """
        if isinstance(value, bool):
            return value
        str_val = str(value).lower().strip()
        true_values = {"true", "yes", "1", "y", "t", "on"}
        false_values = {"false", "no", "0", "n", "f", "off"}
        if str_val in true_values:
            return True
        elif str_val in false_values:
            return False
        else:
            # Unrecognised token — not a boolean. Returning None lets the
            # comparator emit a type_error instead of a silent False match.
            return None

    def _to_date(self, value: Any) -> Optional[datetime]:
        """Convert value to date."""
        if isinstance(value, datetime):
            return value.date()
        if _is_missing(value):
            return None
        str_val = str(value).strip()
        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%m-%d-%Y",
            "%Y%m%d",
            "%d.%m.%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(str_val, fmt).date()
            except ValueError:
                continue
        # Try pandas parser
        try:
            return pd.to_datetime(str_val).date()
        except ParserError:
            return None
        except ValueError:
            return None


class MetricsCalculator:
    """Calculate evaluation metrics."""

    def calculate(self, evaluation_results: Dict) -> Dict:
        """Calculate all metrics from evaluation results."""
        doc_evals = evaluation_results["document_evaluations"]
        detailed_metrics = evaluation_results["detailed_metrics"]
        field_mappings = evaluation_results.get("field_mappings") or {}
        # Overall metrics
        overall = self._calculate_overall_metrics(doc_evals, detailed_metrics)
        # Field metrics
        fields = self._calculate_field_metrics(detailed_metrics)
        # Document metrics
        documents = self._calculate_document_metrics(doc_evals)
        # Confusion matrices for categorical fields
        confusion_matrices = self._calculate_confusion_matrices(
            detailed_metrics, field_mappings
        )
        return {
            "overall": overall,
            "fields": fields,
            "documents": documents,
            "confusion_matrices": confusion_matrices,
        }

    @staticmethod
    def _error_roles(error_type: Optional[str]) -> set:
        """Classify an incorrect prediction's error_type into metric role(s).

        Returns a set drawn from:
          - ``"fn"`` — false negative: the ground-truth value went unrecovered.
          - ``"fp"`` — false positive: the model emitted a value it should not
            have (a wrong or extra value).

        A ``missing`` field (GT present, prediction absent) is FN-only: the
        model failed to extract something that exists. An ``extra`` field
        (prediction present, GT absent) is FP-only: the model invented
        something. A *substitution* — any ``*_mismatch`` / ``type_error`` /
        ``date_parse_error``, where the model produced a value where the GT
        also had one, but it was wrong — counts as **both** FP and FN. This
        follows the standard IE/MUC scoring convention: a wrong value is one
        false positive *and* one missed true positive, so it penalises both
        precision and recall. Counting it as FP-only made recall artificially
        tolerant of wrong values (a fully-wrong-but-present field set reported
        recall = 100%).
        """
        if error_type == "missing":
            return {"fn"}
        if error_type == "extra":
            return {"fp"}
        # Every remaining error_type (mismatch, fuzzy_mismatch,
        # numeric_mismatch, boolean_mismatch, category_mismatch,
        # date_mismatch, type_error, date_parse_error) is a substitution:
        # the model emitted a value where the GT had one, but it was wrong.
        return {"fp", "fn"}

    @staticmethod
    def _prf(tp: int, fp: int, fn: int) -> Dict[str, float]:
        """Compute precision / recall / F1 from raw counts."""
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        return {"precision": precision, "recall": recall, "f1_score": f1}

    def _calculate_overall_metrics(
        self, doc_evals: List[Dict], detailed_metrics: List[Dict]
    ) -> Dict:
        """Calculate overall metrics.

        Documents that failed to evaluate (no ground-truth match, DB lookup
        error, etc.) carry an ``error`` key and ``total_fields=0``. They are
        excluded from the accuracy denominator (there is nothing to score
        them against), so we surface ``matched_document_count`` and
        ``error_document_count`` separately — otherwise a trial where half
        the documents failed to match ground truth would report an accuracy
        computed only over the surviving half, with no indication that
        documents were dropped.

        Precision / recall / F1 are computed from the per-field detailed
        metrics: TP = correct, FN = ``missing`` or a substitution (wrong
        value where the GT had one), FP = any wrong/extra value. A wrong
        value is thus counted once against precision and once against recall
        (standard IE/MUC convention) — see ``_error_roles``. This is the
        field-level extraction quality the user actually cares about.
        """
        total_docs = len(doc_evals)
        error_docs = sum(1 for d in doc_evals if d.get("error"))
        matched_docs = total_docs - error_docs
        total_fields = sum(d.get("total_fields", 0) for d in doc_evals)
        correct_fields = sum(d.get("correct_fields", 0) for d in doc_evals)
        # Accuracy is over matched documents only (error docs have no scoreable fields).
        accuracy = correct_fields / total_fields if total_fields > 0 else 0

        # Aggregate TP/FN/FP across all field-level metrics for P/R/F1.
        # A substitution counts as both FP and FN (see ``_error_roles``).
        tp = sum(1 for m in detailed_metrics if m.get("is_correct"))
        fn = 0
        fp = 0
        for m in detailed_metrics:
            if m.get("is_correct"):
                continue
            roles = self._error_roles(m.get("error_type"))
            if "fn" in roles:
                fn += 1
            if "fp" in roles:
                fp += 1
        prf = self._prf(tp, fp, fn)

        return {
            "accuracy": accuracy,
            "precision": prf["precision"],
            "recall": prf["recall"],
            "f1_score": prf["f1_score"],
            "total_documents": total_docs,
            "matched_document_count": matched_docs,
            "error_document_count": error_docs,
            "total_fields": total_fields,
            "correct_fields": correct_fields,
        }

    def _calculate_field_metrics(self, detailed_metrics: List[Dict]) -> Dict:
        """Calculate field-level metrics."""
        field_metrics = {}
        for metric in detailed_metrics:
            field_name = metric["field_name"]
            if field_name not in field_metrics:
                field_metrics[field_name] = {
                    "total_count": 0,
                    "correct_count": 0,
                    "error_distribution": {},
                    "_tp": 0,
                    "_fp": 0,
                    "_fn": 0,
                }
            field_metrics[field_name]["total_count"] += 1
            if metric["is_correct"]:
                field_metrics[field_name]["correct_count"] += 1
                field_metrics[field_name]["_tp"] += 1
            else:
                error_type = metric["error_type"]
                if error_type not in field_metrics[field_name]["error_distribution"]:
                    field_metrics[field_name]["error_distribution"][error_type] = 0
                field_metrics[field_name]["error_distribution"][error_type] += 1
                roles = self._error_roles(error_type)
                if "fn" in roles:
                    field_metrics[field_name]["_fn"] += 1
                if "fp" in roles:
                    field_metrics[field_name]["_fp"] += 1
        # Calculate accuracy + precision/recall/F1 for each field
        for field_name, metrics in field_metrics.items():
            metrics["accuracy"] = metrics["correct_count"] / metrics["total_count"]
            prf = self._prf(metrics["_tp"], metrics["_fp"], metrics["_fn"])
            metrics["precision"] = prf["precision"]
            metrics["recall"] = prf["recall"]
            metrics["f1_score"] = prf["f1_score"]
            metrics["error_count"] = metrics["total_count"] - metrics["correct_count"]
            # Drop the internal counters before persisting.
            del metrics["_tp"]
            del metrics["_fp"]
            del metrics["_fn"]
        return field_metrics

    def _calculate_document_metrics(self, doc_evals: List[Dict]) -> List[Dict]:
        """Calculate document-level metrics with error handling."""
        processed_docs = []

        for doc_eval in doc_evals:
            # Ensure all required fields are present
            processed_doc = {
                "document_id": doc_eval.get("document_id"),
                "accuracy": doc_eval.get("accuracy", 0.0),
                "correct_fields": doc_eval.get("correct_fields", 0),
                "total_fields": doc_eval.get("total_fields", 0),
                "missing_fields": doc_eval.get("missing_fields", []),
                "incorrect_fields": doc_eval.get("incorrect_fields", []),
            }

            # Add error information if present
            if "error" in doc_eval:
                processed_doc["error"] = doc_eval["error"]
                processed_doc["has_error"] = True
            else:
                processed_doc["has_error"] = False

            processed_docs.append(processed_doc)

        return processed_docs

    def _calculate_confusion_matrices(
        self, detailed_metrics: List[Dict], field_mappings: Dict
    ) -> Dict:
        """Calculate confusion matrices for discrete-valued fields.

        A confusion matrix is only meaningful when the field has a small,
        known set of allowed values — i.e. boolean or categorical/enum
        fields. Building one for free-text fields produces a huge,
        unreadable GT×prediction table (every distinct string its own
        row/column), so we restrict to fields whose mapping ``type`` or
        ``method`` is ``"boolean"`` or ``"category"``. Keying off the
        comparison ``method`` as well as the schema ``type`` catches
        categorical fields whose stored ``field_type`` is ``"string"``
        (e.g. enum-less or auto-mapped categories).
        """
        discrete_fields = {
            path
            for path, mapping in field_mappings.items()
            if mapping
            and (
                mapping.get("type") in (FieldType.CATEGORY, FieldType.BOOLEAN)
                or mapping.get("method")
                in (ComparisonMethod.CATEGORY, ComparisonMethod.BOOLEAN)
            )
        }
        if not discrete_fields:
            return {}

        confusion_matrices = {}
        for metric in detailed_metrics:
            field_name = metric["field_name"]
            if field_name not in discrete_fields:
                continue
            if field_name not in confusion_matrices:
                confusion_matrices[field_name] = {}
            gt_value = metric["ground_truth_value"]
            pred_value = metric["predicted_value"]
            if gt_value not in confusion_matrices[field_name]:
                confusion_matrices[field_name][gt_value] = {}
            if pred_value not in confusion_matrices[field_name][gt_value]:
                confusion_matrices[field_name][gt_value][pred_value] = 0
            confusion_matrices[field_name][gt_value][pred_value] += 1
        return confusion_matrices
