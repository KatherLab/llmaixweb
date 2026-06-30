# backend/tests/test_evaluation_metrics.py
"""Unit tests for ``MetricsCalculator`` precision/recall/F1 conventions.

These do not touch the DB or the API — they construct the
``evaluation_results`` dict the calculator consumes and assert on the
computed metrics. They exist to lock in the IE/MUC scoring convention:
a *substitution* (wrong value where the ground truth had one) counts as
both a false positive and a false negative, so it penalises precision
*and* recall. A ``missing`` value is FN-only; an ``extra`` value is
FP-only.
"""

import pytest

# Imported lazily inside ``_calculator`` so test *collection* doesn't trigger
# the app's settings init (which validates OpenAI/S3 and sys.exits without
# the test env vars the session-scoped conftest fixture installs).


def _calculator():
    from ..src.utils.evaluation import MetricsCalculator

    return MetricsCalculator()


def _metric(field, gt, pred, is_correct, error_type):
    return {
        "field_name": field,
        "ground_truth_value": gt,
        "predicted_value": pred,
        "is_correct": is_correct,
        "error_type": error_type,
    }


def _results(metrics, field_mappings=None):
    return {
        "document_evaluations": [
            {
                "document_id": 1,
                "accuracy": sum(m["is_correct"] for m in metrics) / len(metrics)
                if metrics
                else 0.0,
                "correct_fields": sum(m["is_correct"] for m in metrics),
                "total_fields": len(metrics),
                "missing_fields": [],
                "incorrect_fields": [],
            }
        ],
        "detailed_metrics": metrics,
        "field_mappings": field_mappings or {},
    }


def test_substitution_counts_against_both_precision_and_recall():
    """A wrong value (mismatch) must lower BOTH precision and recall.

    Previously a substitution was FP-only, so a fully-wrong-but-present
    field set reported recall = 100%. Under the IE/MUC convention it is
    one FP and one FN, so recall drops too.
    """
    metrics = [
        _metric("diag", "A", "B", False, "mismatch"),  # substitution
    ]
    out = _calculator().calculate(_results(metrics))
    overall = out["overall"]
    # TP=0, FP=1, FN=1 → precision 0, recall 0
    assert overall["precision"] == 0.0
    assert overall["recall"] == 0.0
    assert overall["f1_score"] == 0.0
    assert overall["accuracy"] == 0.0


def test_missing_is_fn_only():
    """A missing field (GT present, prediction absent) is FN, not FP."""
    metrics = [
        _metric("diag", "A", None, False, "missing"),
    ]
    out = _calculator().calculate(_results(metrics))
    overall = out["overall"]
    # TP=0, FP=0, FN=1 → precision 0/0 = 0, recall 0
    assert overall["precision"] == 0.0
    assert overall["recall"] == 0.0
    # No false positive: precision denominator is 0 → defined as 0 here.
    assert overall["f1_score"] == 0.0


def test_extra_is_fp_only():
    """An extra field (prediction present, GT absent) is FP, not FN."""
    metrics = [
        _metric("diag", None, "X", False, "extra"),
    ]
    out = _calculator().calculate(_results(metrics))
    overall = out["overall"]
    # TP=0, FP=1, FN=0 → precision 0, recall 0/0 = 0
    assert overall["precision"] == 0.0
    assert overall["recall"] == 0.0


def test_perfect_metrics():
    metrics = [
        _metric("diag", "A", "A", True, None),
        _metric("code", "1", "1", True, None),
    ]
    out = _calculator().calculate(_results(metrics))
    overall = out["overall"]
    assert overall["accuracy"] == 1.0
    assert overall["precision"] == 1.0
    assert overall["recall"] == 1.0
    assert overall["f1_score"] == 1.0


def test_mixed_field_and_overall_consistency():
    """One correct, one missing, one substitution across two fields.

    TP=1, FP=1 (substitution), FN=2 (missing + substitution).
    precision = 1/(1+1) = 0.5
    recall    = 1/(1+2) = 1/3
    """
    metrics = [
        _metric("a", "A", "A", True, None),
        _metric("b", "B", None, False, "missing"),
        _metric("c", "C", "D", False, "mismatch"),
    ]
    out = _calculator().calculate(_results(metrics))
    overall = out["overall"]
    assert overall["precision"] == 0.5
    assert overall["recall"] == pytest.approx(1 / 3)
    field_c = out["fields"]["c"]
    # Field c: one substitution → TP=0, FP=1, FN=1
    assert field_c["precision"] == 0.0
    assert field_c["recall"] == 0.0


# --- Confusion-matrix gating ------------------------------------------------
#
# A confusion matrix should be produced for discrete-valued fields — those
# whose mapping ``type`` OR ``method`` is ``boolean``/``category`` — and
# skipped for free-text/numeric fields. The ``method`` path matters because
# auto-mapped categorical fields can have ``field_type == "string"`` while
# their ``comparison_method == "category"``.


def _mapping(gt_field, field_type, method):
    return {
        "gt_field": gt_field,
        "type": field_type,
        "method": method,
        "options": {},
    }


def test_confusion_matrix_for_boolean_field():
    """A boolean field (by type) must get a confusion matrix."""
    metrics = [
        _metric("active", "true", "true", True, None),
        _metric("active", "false", "true", False, "mismatch"),
    ]
    mappings = {"active": _mapping("active", "boolean", "boolean")}
    out = _calculator().calculate(_results(metrics, mappings))
    cm = out["confusion_matrices"]["active"]
    assert cm["true"]["true"] == 1
    assert cm["false"]["true"] == 1


def test_confusion_matrix_for_category_by_type():
    """A categorical field (by type) must get a confusion matrix."""
    metrics = [
        _metric("status", "A", "A", True, None),
        _metric("status", "B", "A", False, "mismatch"),
    ]
    mappings = {"status": _mapping("status", "category", "category")}
    out = _calculator().calculate(_results(metrics, mappings))
    assert out["confusion_matrices"]["status"]["A"]["A"] == 1
    assert out["confusion_matrices"]["status"]["B"]["A"] == 1


def test_confusion_matrix_for_category_by_method_only():
    """A field typed ``string`` but compared as ``category`` must still get
    a confusion matrix (the enum-less / auto-mapped category case).
    """
    metrics = [
        _metric("status", "A", "B", False, "mismatch"),
    ]
    mappings = {"status": _mapping("status", "string", "category")}
    out = _calculator().calculate(_results(metrics, mappings))
    assert out["confusion_matrices"]["status"]["A"]["B"] == 1


def test_confusion_matrix_excludes_free_text_and_numeric():
    """Free-text (exact/fuzzy) and numeric fields must NOT get a matrix."""
    metrics = [
        _metric("note", "hello", "hi", False, "mismatch"),
        _metric("age", "10", "12", False, "mismatch"),
    ]
    mappings = {
        "note": _mapping("note", "string", "exact"),
        "age": _mapping("age", "number", "numeric"),
    }
    out = _calculator().calculate(_results(metrics, mappings))
    assert "note" not in out["confusion_matrices"]
    assert "age" not in out["confusion_matrices"]
    assert out["confusion_matrices"] == {}
