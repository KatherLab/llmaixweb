import io
import json
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
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
    """Main evaluation engine with caching and parallel processing."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self._cache = {}

    def evaluate_trial(
        self, trial_id: int, groundtruth_id: int, force_recalculate: bool = False
    ) -> models.Evaluation:
        """Evaluate a trial against ground truth with caching."""
        # Check cache
        if not force_recalculate:
            existing = (
                self.db.query(models.Evaluation)
                .filter_by(trial_id=trial_id, groundtruth_id=groundtruth_id)
                .first()
            )
            if existing:
                return existing
        # Load data
        trial = self.db.query(models.Trial).get(trial_id)
        ground_truth = self.db.query(models.GroundTruth).get(groundtruth_id)
        if not trial or not ground_truth:
            raise ValueError("Trial or ground truth not found")
        # Get results
        results = self.db.query(models.TrialResult).filter_by(trial_id=trial_id).all()
        if not results:
            raise ValueError("No results found for trial")
        # Load and parse ground truth
        gt_data = self._load_ground_truth(ground_truth)
        # Get field mappings
        field_mappings = self._get_field_mappings(ground_truth)
        # Evaluate in parallel
        evaluation_results = self._evaluate_parallel(results, gt_data, field_mappings)
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

    def _load_ground_truth(self, ground_truth: models.GroundTruth) -> Dict:
        """Load ground truth data with caching."""
        # Check cache
        if ground_truth.data_cache:
            return ground_truth.data_cache
        # Load from file
        from ..dependencies import get_file

        content = get_file(ground_truth.file_uuid)
        parser = GroundTruthParser()
        data = parser.parse(content, ground_truth.format)
        # Cache parsed data
        ground_truth.data_cache = data
        self.db.commit()
        return data

    def _get_field_mappings(self, ground_truth: models.GroundTruth) -> Dict:
        """Get field mappings with auto-detection."""
        mappings = {}
        # Load existing mappings
        for mapping in ground_truth.field_mappings:
            mappings[mapping.schema_field] = {
                "gt_field": mapping.ground_truth_field,
                "type": mapping.field_type,
                "method": mapping.comparison_method,
                "options": mapping.comparison_options or {},
            }
        return mappings

    def _evaluate_parallel(
        self, results: List[models.TrialResult], gt_data: Dict, field_mappings: Dict
    ) -> Dict:
        """Evaluate results in parallel."""
        detailed_metrics = []
        doc_evaluations = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for result in results:
                future = executor.submit(
                    self._evaluate_document, result, gt_data, field_mappings
                )
                futures.append((result.document_id, future))
            for doc_id, future in futures:
                try:
                    doc_eval = future.result()
                    doc_evaluations.append(doc_eval)
                    detailed_metrics.extend(doc_eval["detailed_metrics"])
                except Exception as e:
                    print(f"Error evaluating document {doc_id}: {e}")
        return {
            "document_evaluations": doc_evaluations,
            "detailed_metrics": detailed_metrics,
        }

    def _evaluate_document(
        self, result: models.TrialResult, gt_data: Dict, field_mappings: Dict
    ) -> Dict:
        """Evaluate a single document."""
        doc_id = result.document_id

        # Ensure doc_id is an integer for SQLite
        try:
            doc_id = int(doc_id)
        except (ValueError, TypeError):
            return {
                "document_id": doc_id,
                "error": f"Invalid document ID: {doc_id}",
                "accuracy": 0.0,
                "correct_fields": 0,
                "total_fields": 0,
                "missing_fields": [],
                "incorrect_fields": [],
                "detailed_metrics": [],
            }

        print("Evaluating document ID:", doc_id)
        document = self.db.query(models.Document).get(doc_id)
        if not document:
            return {
                "document_id": doc_id,
                "error": "Document not found",
                "accuracy": 0.0,
                "correct_fields": 0,
                "total_fields": 0,
                "missing_fields": [],
                "incorrect_fields": [],
                "detailed_metrics": [],
            }

        # Get ground truth for this document
        gt_key = self._find_document_key(doc_id, document, gt_data)
        if gt_key is None or gt_key not in gt_data:
            return {
                "document_id": doc_id,
                "error": "No ground truth found",
                "accuracy": 0.0,
                "correct_fields": 0,
                "total_fields": 0,
                "missing_fields": [],
                "incorrect_fields": [],
                "detailed_metrics": [],
            }

        gt_values = gt_data[gt_key]
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

    def _find_document_key(
        self, doc_id: int, document: models.Document, gt_data: Dict
    ) -> Optional[str]:
        """Find the ground truth key for a document."""
        # Try direct ID match
        if doc_id in gt_data:
            return doc_id
        if str(doc_id) in gt_data:
            return str(doc_id)
        # Try filename match
        if document.original_file:
            filename = document.original_file.file_name
            base_name = Path(filename).stem
            if filename in gt_data:
                return filename
            if base_name in gt_data:
                return base_name
        return None

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


class GroundTruthParser:
    """Parser for different ground truth formats."""

    def parse(self, content: bytes, format_type: str) -> Dict:
        """Parse ground truth content based on format."""
        if format_type == "json":
            return self._parse_json(content)
        elif format_type == "csv":
            return self._parse_csv(content)
        elif format_type == "xlsx":
            return self._parse_excel(content)
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

    def _parse_csv(self, content: bytes) -> Dict:
        """Parse CSV ground truth."""
        df = pd.read_csv(io.BytesIO(content))
        # Find ID column
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

    def _parse_excel(self, content: bytes) -> Dict:
        """Parse Excel ground truth."""
        df = pd.read_excel(io.BytesIO(content))
        return self._parse_csv(df.to_csv().encode("utf-8"))

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
        except:
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
        """Calculate document-level metrics."""
        # Ensure accuracy is always present
        for doc_eval in doc_evals:
            if "accuracy" not in doc_eval:
                doc_eval["accuracy"] = 0.0  # or some other default value
        return doc_evals

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
