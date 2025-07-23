import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from pandas.errors import ParserError
from sqlalchemy.orm import Session
from thefuzz import fuzz

from .. import models


def flatten_dict(d, parent_key="", sep="_"):
    flat_dict = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            flat_dict.update(flatten_dict(v, new_key, sep))
        else:
            flat_dict[new_key] = v
    return flat_dict


class EvaluationEngine:
    """Main evaluation engine with enhanced concurrency handling."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self._cache = {}
        # Store engine for creating new sessions in parallel processing
        self.engine = db_session.bind

    def evaluate_trial(
        self, trial_id: int, groundtruth_id: int, force_recalculate: bool = False
    ) -> models.Evaluation:
        """Evaluate a trial against ground truth with comprehensive validation."""

        # Pre-validation phase
        validation_result = self._validate_evaluation_prerequisites(
            trial_id, groundtruth_id
        )
        if not validation_result["valid"]:
            raise ValueError(
                f"Evaluation prerequisites not met: {'; '.join(validation_result['errors'])}"
            )

        # Check cache
        if not force_recalculate:
            existing = (
                self.db.query(models.Evaluation)
                .filter_by(trial_id=trial_id, groundtruth_id=groundtruth_id)
                .first()
            )
            if existing:
                return existing

        # Load validated data
        trial = self.db.query(models.Trial).get(trial_id)
        ground_truth = self.db.query(models.GroundTruth).get(groundtruth_id)
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

        # Pre-load all document data to avoid session issues in parallel processing
        document_data = self._preload_document_data(results)

        # Evaluate with enhanced error handling
        evaluation_results = self._evaluate_parallel(
            results, gt_data, field_mappings, document_data
        )

        # Calculate metrics
        metrics = self._calculate_metrics(evaluation_results)

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
        trial = self.db.query(models.Trial).get(trial_id)
        if not trial:
            errors.append(f"Trial {trial_id} not found")
            return {"valid": False, "errors": errors}

        # Check trial is completed
        if trial.status != "completed":
            errors.append(f"Trial {trial_id} is not completed (status: {trial.status})")

        # Check ground truth exists
        ground_truth = self.db.query(models.GroundTruth).get(groundtruth_id)
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

    def _validate_data_consistency(
        self, results: List[models.TrialResult], gt_data: Dict, field_mappings: Dict
    ) -> Dict:
        """Validate that trial results can be matched with ground truth data."""
        errors = []
        warnings = []

        total_results = len(results)
        matched_count = 0
        unmatched_documents = []

        # Build document lookup for better error reporting
        document_lookup = {}
        for result in results:
            doc_id = result.document_id
            document = self.db.query(models.Document).get(doc_id)
            if document:
                document_lookup[doc_id] = document

        for result in results:
            doc_id = result.document_id

            # Check if document exists
            if doc_id not in document_lookup:
                errors.append(f"Document {doc_id} not found in database")
                continue

            document = document_lookup[doc_id]

            # Try to find ground truth key
            gt_key = self._find_document_key_enhanced(doc_id, document, gt_data)
            if gt_key is None:
                filename = (
                    document.original_file.file_name
                    if document.original_file
                    else "Unknown"
                )
                unmatched_documents.append({"doc_id": doc_id, "filename": filename})
            else:
                matched_count += 1

        # Calculate match percentage
        match_percentage = (
            (matched_count / total_results) * 100 if total_results > 0 else 0
        )

        if match_percentage < 50:
            errors.append(
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
            errors.append(
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

        for result in results:
            doc_id = result.document_id
            try:
                doc_id = int(doc_id)
                document = self.db.query(models.Document).get(doc_id)
                if document:
                    # Store relevant document data
                    document_data[doc_id] = {
                        "id": document.id,
                        "filename": document.original_file.file_name
                        if document.original_file
                        else None,
                        "exists": True,
                    }
                else:
                    document_data[doc_id] = {"exists": False}
            except (ValueError, TypeError) as e:
                print("Error converting document ID:", e)
                document_data[doc_id] = {
                    "exists": False,
                    "error": "Invalid document ID",
                }
            except Exception as e:
                print("Error loading documents: ", e)
                import traceback

                print(traceback.format_exc())

        return document_data

    def _find_document_key_enhanced(
        self, doc_id: int, document: models.Document, gt_data: Dict
    ) -> Optional[str]:
        """Find ground truth key by matching only on original file filename (case-insensitive, with and without extension)."""
        if (
            not document
            or not document.original_file
            or not document.original_file.file_name
        ):
            return None

        filename = document.original_file.file_name
        filename_stem = Path(filename).stem
        filename_lower = filename.lower()
        filename_stem_lower = filename_stem.lower()

        # Prepare all ground truth keys to lower for case-insensitive comparison
        gt_keys_lower = {str(k).lower(): k for k in gt_data.keys()}

        # 1. Try exact filename (case-insensitive, with extension)
        if filename_lower in gt_keys_lower:
            return gt_keys_lower[filename_lower]

        # 2. Try filename without extension (case-insensitive)
        if filename_stem_lower in gt_keys_lower:
            return gt_keys_lower[filename_stem_lower]

        # 3. Try again with just the filename part (in case keys contain full paths)
        filename_name_lower = Path(filename).name.lower()
        if filename_name_lower in gt_keys_lower:
            return gt_keys_lower[filename_name_lower]

        # 4. Try only stem of the filename part (no extension, no path)
        filename_name_stem_lower = Path(filename).stem.lower()
        if filename_name_stem_lower in gt_keys_lower:
            return gt_keys_lower[filename_name_stem_lower]

        # If still not found, no match
        return None

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

        # Cache parsed data
        ground_truth.data_cache = data
        self.db.commit()

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

    def _evaluate_parallel(
        self,
        results: List[models.TrialResult],
        gt_data: Dict,
        field_mappings: Dict,
        document_data: Dict,
    ) -> Dict:
        """Evaluate results in parallel with session isolation."""
        detailed_metrics = []
        doc_evaluations = []

        # Use smaller thread pool to avoid overwhelming the database
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for result in results:
                future = executor.submit(
                    self._evaluate_document_isolated,
                    result,
                    gt_data,
                    field_mappings,
                    document_data,
                )
                futures.append((result.document_id, future))

            for doc_id, future in futures:
                try:
                    doc_eval = future.result()
                    doc_evaluations.append(doc_eval)
                    detailed_metrics.extend(doc_eval["detailed_metrics"])
                except Exception as e:
                    print(f"Error evaluating document {doc_id}: {e}")
                    # Add error document to results
                    doc_evaluations.append(
                        self._create_error_result(
                            doc_id, f"Evaluation failed: {str(e)}"
                        )
                    )

        return {
            "document_evaluations": doc_evaluations,
            "detailed_metrics": detailed_metrics,
        }

    def _evaluate_document_isolated(
        self,
        result: models.TrialResult,
        gt_data: Dict,
        field_mappings: Dict,
        document_data: Dict,
    ) -> Dict:
        """Evaluate a single document using pre-loaded data to avoid session issues."""
        doc_id = result.document_id

        # Ensure doc_id is properly formatted
        try:
            doc_id = int(doc_id)
        except (ValueError, TypeError):
            return self._create_error_result(doc_id, f"Invalid document ID: {doc_id}")

        # Use pre-loaded document data
        if doc_id not in document_data or not document_data[doc_id].get(
            "exists", False
        ):
            return self._create_error_result(doc_id, "Document not found in database")

        doc_info = document_data[doc_id]

        # Get ground truth for this document using filename from pre-loaded data
        gt_key = self._find_document_key_by_data(doc_id, doc_info, gt_data)
        if gt_key is None or gt_key not in gt_data:
            filename = doc_info.get("filename", "Unknown")
            return self._create_error_result(
                doc_id,
                f"No ground truth found for document {doc_id} (filename: {filename}). "
                f"Available ground truth keys: {list(gt_data.keys())[:5]}...",
            )

        gt_values = gt_data[gt_key]

        # Validate that we have trial results
        if not result.result:
            return self._create_error_result(
                doc_id, "No trial results found for document"
            )

        pred_values = flatten_dict(result.result)

        # Evaluate each field
        detailed_metrics = []
        correct_count = 0
        total_count = 0
        missing_fields = []
        incorrect_fields = []

        for schema_field, mapping in field_mappings.items():
            gt_field = mapping["gt_field"]
            if gt_field not in gt_values:
                continue

            total_count += 1
            gt_value = gt_values[gt_field]
            pred_value = pred_values.get(schema_field)

            comparison = self._compare_values(
                gt_value,
                pred_value,
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
                    "ground_truth_value": str(gt_value)
                    if gt_value is not None
                    else None,
                    "predicted_value": str(pred_value)
                    if pred_value is not None
                    else None,
                    "is_correct": comparison["is_correct"],
                    "error_type": comparison["error_type"],
                    "confidence_score": comparison.get("confidence_score"),
                }
            )

        accuracy = correct_count / total_count if total_count > 0 else 0

        return {
            "document_id": doc_id,
            "accuracy": accuracy,
            "correct_fields": correct_count,
            "total_fields": total_count,
            "missing_fields": missing_fields,
            "incorrect_fields": incorrect_fields,
            "detailed_metrics": detailed_metrics,
        }

    def _find_document_key_by_data(
        self, doc_id: int, doc_info: Dict, gt_data: Dict
    ) -> Optional[str]:
        """Find document key using pre-loaded document data."""
        # Strategy 1: Direct ID match
        id_variants = [doc_id, str(doc_id), f"doc_{doc_id}", f"document_{doc_id}"]
        for variant in id_variants:
            if variant in gt_data:
                return variant

        # Strategy 2: Filename matching
        filename = doc_info.get("filename")
        if filename:
            filename_variants = [
                filename,
                Path(filename).stem,
                Path(filename).name,
                filename.lower(),
                Path(filename).stem.lower(),
            ]

            for variant in filename_variants:
                if variant in gt_data:
                    return variant

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

    def _calculate_metrics(self, evaluation_results: Dict) -> Dict:
        """Calculate overall and field-level metrics."""
        calculator = MetricsCalculator()
        return calculator.calculate(evaluation_results)


# Keep existing GroundTruthParser, ValueComparator, and MetricsCalculator classes unchanged


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
        """Parse JSON ground truth."""
        try:
            data = json.loads(content.decode("utf-8"))
            # Handle both single JSON and document map
            if isinstance(data, dict) and all(
                isinstance(v, dict) for v in data.values()
            ):
                # Document map format
                result = {}
                for key, values in data.items():
                    result[key] = flatten_dict(values)
                return result
            else:
                # Single document
                return {"default": flatten_dict(data)}
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    def _parse_csv(self, content: bytes, id_column: Optional[str] = None) -> Dict:
        """Parse CSV ground truth."""
        df = pd.read_csv(io.BytesIO(content))

        # Use configured ID column or try to find one
        if id_column and id_column in df.columns:
            id_col = id_column
        else:
            # Fallback to auto-detection
            id_columns = ["document_id", "doc_id", "id", "filename", "file_name"]
            id_col = None
            for col in id_columns:
                if col in df.columns:
                    id_col = col
                    break
            if not id_col:
                # Use index if no ID column
                df["_index"] = df.index
                id_col = "_index"

        result = {}
        for _, row in df.iterrows():
            doc_id = row[id_col]
            values = {
                col: row[col]
                for col in df.columns
                if col != id_col and pd.notna(row[col])
            }
            result[str(doc_id)] = values
        return result

    def _parse_excel(self, content: bytes, id_column: Optional[str] = None) -> Dict:
        """Parse Excel ground truth."""
        df = pd.read_excel(io.BytesIO(content))
        # Convert to CSV and reuse the CSV parser logic
        csv_content = df.to_csv(index=False).encode("utf-8")
        return self._parse_csv(csv_content, id_column)

    def _parse_zip(self, content: bytes) -> Dict:
        """Parse ZIP file with multiple documents."""
        result = {}
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for filename in zf.namelist():
                if filename.endswith(".json"):
                    with zf.open(filename) as f:
                        doc_data = json.loads(f.read().decode("utf-8"))
                        # Extract document ID from filename
                        base_name = Path(filename).stem
                        result[base_name] = flatten_dict(doc_data)
        return result


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

    def _convert_value(self, value: Any, field_type: str) -> Any:
        """Convert value to appropriate type."""
        if value is None or pd.isna(value):
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
        """Fuzzy string comparison."""
        threshold = options.get("threshold", 85)
        gt_str = str(gt).lower().strip()
        pred_str = str(pred).lower().strip()
        # Calculate similarity
        ratio = fuzz.ratio(gt_str, pred_str)
        partial_ratio = fuzz.partial_ratio(gt_str, pred_str)
        token_sort_ratio = fuzz.token_sort_ratio(gt_str, pred_str)
        # Use best score
        score = max(ratio, partial_ratio, token_sort_ratio)
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
        """Boolean comparison."""
        gt_bool = self._to_boolean(gt)
        pred_bool = self._to_boolean(pred)
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

    def _to_boolean(self, value: Any) -> bool:
        """Convert value to boolean."""
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
            # Default to False for unknown values
            return False

    def _to_date(self, value: Any) -> Optional[datetime]:
        """Convert value to date."""
        if isinstance(value, datetime):
            return value.date()
        if pd.isna(value):
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
        # Overall metrics
        overall = self._calculate_overall_metrics(doc_evals, detailed_metrics)
        # Field metrics
        fields = self._calculate_field_metrics(detailed_metrics)
        # Document metrics
        documents = self._calculate_document_metrics(doc_evals)
        # Confusion matrices for categorical fields
        confusion_matrices = self._calculate_confusion_matrices(detailed_metrics)
        return {
            "overall": overall,
            "fields": fields,
            "documents": documents,
            "confusion_matrices": confusion_matrices,
        }

    def _calculate_overall_metrics(
        self, doc_evals: List[Dict], detailed_metrics: List[Dict]
    ) -> Dict:
        """Calculate overall metrics."""
        total_docs = len(doc_evals)
        total_fields = sum(d.get("total_fields", 0) for d in doc_evals)
        correct_fields = sum(d.get("correct_fields", 0) for d in doc_evals)
        # Basic metrics
        accuracy = correct_fields / total_fields if total_fields > 0 else 0
        return {
            "accuracy": accuracy,
            "total_documents": total_docs,
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
                }
            field_metrics[field_name]["total_count"] += 1
            if metric["is_correct"]:
                field_metrics[field_name]["correct_count"] += 1
            else:
                error_type = metric["error_type"]
                if error_type not in field_metrics[field_name]["error_distribution"]:
                    field_metrics[field_name]["error_distribution"][error_type] = 0
                field_metrics[field_name]["error_distribution"][error_type] += 1
        # Calculate accuracy for each field
        for field_name, metrics in field_metrics.items():
            metrics["accuracy"] = metrics["correct_count"] / metrics["total_count"]
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

    def _calculate_confusion_matrices(self, detailed_metrics: List[Dict]) -> Dict:
        """Calculate confusion matrices for categorical fields."""
        # This is a simplified example and may need to be adapted
        # based on the actual requirements and data structure
        confusion_matrices = {}
        for metric in detailed_metrics:
            field_name = metric["field_name"]
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
