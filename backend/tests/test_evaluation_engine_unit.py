# backend/tests/test_evaluation_engine_unit.py
"""Unit tests for pure ``EvaluationEngine`` helpers that don't need a DB.

``_get_nested_value`` (dot/`[]` path lookup into the LLM result JSON) and
``_find_document_key_by_data`` (matching a document to its ground-truth row by
name/filename/id) are pure given their arguments. They're constructed via
``__new__`` so ``__init__`` (which wants a live SQLAlchemy session) is skipped.
"""

import pytest


def _engine():
    from ..src.utils.evaluation import EvaluationEngine

    # Skip __init__ (needs a DB session); the helpers under test use no self.*
    return EvaluationEngine.__new__(EvaluationEngine)


# ─────────────────────────── _get_nested_value ───────────────────────────


@pytest.mark.parametrize(
    "data,path,expected",
    [
        ({"a": {"b": {"c": 5}}}, "a.b.c", 5),
        ({"a": {"b": 1}}, "a.b", 1),
        ({"a": [10, 20]}, "a[]", 10),  # [] -> first element
        ({"a": {"b": 2}}, "a.missing", None),  # missing key -> default
        ({"a": [1]}, "a.5", None),  # out-of-range index -> default
        ({"x": "v"}, "y", None),
    ],
)
def test_get_nested_value(data, path, expected):
    assert _engine()._get_nested_value(data, path) == expected


def test_get_nested_value_custom_default():
    assert _engine()._get_nested_value({}, "a.b", default="X") == "X"


# ─────────────────────────── _find_document_key_by_data ───────────────────


def test_find_key_by_document_name_exact():
    gt = {"Report_A.pdf": {}, "other": {}}
    key = _engine()._find_document_key_by_data(1, {"document_name": "report_a.pdf"}, gt)
    assert key == "Report_A.pdf"  # case-insensitive, original casing returned


def test_find_key_by_document_name_stem():
    gt = {"report_a": {}}
    key = _engine()._find_document_key_by_data(1, {"document_name": "Report_A.pdf"}, gt)
    assert key == "report_a"


def test_find_key_by_filename_when_no_document_name():
    gt = {"scan01": {}}
    key = _engine()._find_document_key_by_data(
        1, {"document_name": None, "filename": "/uploads/scan01.png"}, gt
    )
    assert key == "scan01"


def test_find_key_by_doc_id_variants():
    for gt_key in ["7", "doc_7", "document_7"]:
        gt = {gt_key: {}}
        key = _engine()._find_document_key_by_data(7, {}, gt)
        assert key == gt_key


def test_find_key_no_match_returns_none():
    gt = {"unrelated": {}}
    assert _engine()._find_document_key_by_data(1, {"document_name": "x"}, gt) is None
