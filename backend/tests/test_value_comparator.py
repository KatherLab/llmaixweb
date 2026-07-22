# backend/tests/test_value_comparator.py
"""Unit tests for ``ValueComparator`` fuzzy / boolean comparison rules.

These do not touch the DB or the API — they exercise the comparator directly
to lock in two scoring decisions that matter for medical/lab data:

* **Fuzzy** matching must not reward pure substring containment by default.
  "cancer" vs "non-cancer" is a *mismatch* unless ``allow_partial_match`` is
  opted in — substring matching can invert meaning in clinical text.
* **Boolean** comparison must not silently coerce unrecognised tokens to
  ``False``. "maybe" vs "unknown" is a *type error*, not a correct match.
"""


def _comparator():
    # Lazy import so test collection doesn't trigger the app's settings init
    # (which validates OpenAI/S3 and sys.exits without the test env vars the
    # session-scoped conftest fixture installs).
    from ..src.utils.evaluation import ValueComparator

    return ValueComparator()


def _compare(gt, pred, field_type="string", method="fuzzy", options=None):
    return _comparator().compare(gt, pred, field_type, method, options or {})


# ─── Fuzzy: substring containment is NOT a default match ────────────────────


def test_fuzzy_substring_is_not_correct_by_default():
    """'cancer' vs 'non-cancer' must NOT be correct at the default threshold.

    ``partial_ratio`` would score this highly (substring containment), but
    for medical coding that inverts the meaning. The default score uses only
    ratio + token_sort_ratio, so this is a fuzzy_mismatch.
    """
    result = _compare("cancer", "non-cancer", method="fuzzy", options={"threshold": 85})
    assert result["is_correct"] is False
    assert result["error_type"] == "fuzzy_mismatch"


def test_fuzzy_substring_matches_when_partial_opted_in():
    """With ``allow_partial_match=True`` the substring score is included,
    so 'cancer' vs 'non-cancer' clears the threshold."""
    result = _compare(
        "cancer",
        "non-cancer",
        method="fuzzy",
        options={"threshold": 85, "allow_partial_match": True},
    )
    assert result["is_correct"] is True


def test_fuzzy_word_reorder_is_correct():
    """token_sort_ratio still tolerates word reordering ('chest pain' vs
    'pain chest') — the legitimate use case for fuzzy matching."""
    result = _compare(
        "chest pain", "pain chest", method="fuzzy", options={"threshold": 85}
    )
    assert result["is_correct"] is True


def test_fuzzy_minor_typo_is_correct():
    result = _compare("diabetes", "diabetis", method="fuzzy", options={"threshold": 85})
    assert result["is_correct"] is True


def test_fuzzy_clearly_different_is_mismatch():
    result = _compare(
        "diabetes", "hypertension", method="fuzzy", options={"threshold": 85}
    )
    assert result["is_correct"] is False
    assert result["error_type"] == "fuzzy_mismatch"


# ─── Boolean: unrecognised tokens are a type error, not a silent False ──────


def _bool_compare(gt, pred):
    return _comparator().compare(gt, pred, "boolean", "boolean", {})


def test_boolean_unrecognised_tokens_are_type_error():
    """'maybe' vs 'unknown' must NOT silently match as False == False."""
    result = _bool_compare("maybe", "unknown")
    assert result["is_correct"] is False
    assert result["error_type"] == "type_error"


def test_boolean_one_side_unrecognised_is_type_error():
    result = _bool_compare("true", "maybe")
    assert result["is_correct"] is False
    assert result["error_type"] == "type_error"


def test_boolean_true_false_variants_match():
    # Token variants on both sides collapse to the same boolean.
    assert _bool_compare("True", "true")["is_correct"] is True
    assert _bool_compare("yes", "1")["is_correct"] is True
    assert _bool_compare("False", "no")["is_correct"] is True
    assert _bool_compare(0, "false")["is_correct"] is True


def test_boolean_mismatch_when_values_differ():
    result = _bool_compare("true", "false")
    assert result["is_correct"] is False
    assert result["error_type"] == "boolean_mismatch"


# ─── Missing / empty-value classification ───────────────────────────────────
# An empty-string / NaN prediction must be "missing" (FN only), NOT a
# substitution (FP+FN). Regression on precision for every blank field.


def test_empty_string_prediction_is_missing_not_substitution():
    for method, field_type, gt in [
        ("exact", "string", "hello"),
        ("numeric", "number", 5),
        ("date", "date", "2020-01-01"),
        ("fuzzy", "string", "hello"),
    ]:
        result = _compare(gt, "", field_type=field_type, method=method)
        assert result["is_correct"] is False, (method, field_type)
        assert result["error_type"] == "missing", (method, field_type)


def test_nan_prediction_is_missing():
    result = _compare(5, float("nan"), field_type="number", method="numeric")
    assert result["error_type"] == "missing"


def test_empty_gt_with_present_prediction_is_extra():
    result = _compare("", "surprise", field_type="string", method="exact")
    assert result["is_correct"] is False
    assert result["error_type"] == "extra"


def test_both_empty_is_correct():
    assert _compare("", "", field_type="string", method="exact")["is_correct"] is True


# ─── Category comparison: non-string mapping options must not crash ─────────


def test_category_mapping_with_non_string_option_matches():
    """A mapping option that is a non-string scalar (e.g. ``{"positive": 1}``)
    must be coerced through ``str`` rather than raising AttributeError (which
    previously zeroed the entire document)."""
    result = _compare(
        "positive",
        "1",
        field_type="string",
        method="category",
        options={"mappings": {"positive": 1}},
    )
    assert result["is_correct"] is True


def test_category_mapping_with_list_of_mixed_types():
    result = _compare(
        "pos",
        "yes",
        field_type="string",
        method="category",
        options={"mappings": {"pos": [1, "YES", "y"]}},
    )
    assert result["is_correct"] is True


def test_category_direct_match_and_mismatch():
    assert _compare("A", "a", method="category")["is_correct"] is True
    r = _compare("A", "B", method="category")
    assert r["is_correct"] is False
    assert r["error_type"] == "category_mismatch"


# ─── List (array-valued) field comparison, order-independent set semantics ──


def _list_compare(gt, pred, field_type="string", method="exact", options=None):
    return _comparator().compare(gt, pred, field_type, method, options or {})


def test_list_order_independent_match():
    r = _list_compare(["a", "b", "c"], ["c", "a", "b"])
    assert r["is_correct"] is True


def test_list_missing_element():
    r = _list_compare(["a", "b", "c"], ["a", "b"])
    assert r["is_correct"] is False
    assert r["error_type"] == "missing"


def test_list_extra_element():
    r = _list_compare(["a", "b"], ["a", "b", "c"])
    assert r["is_correct"] is False
    assert r["error_type"] == "extra"


def test_list_fuzzy_maximum_matching_not_greedy():
    """A perfect pairing exists (ab->ab, abc->abc); a greedy first-match loop
    would let gt 'ab' consume 'abc' and then falsely report 'abc' as missing.
    Maximum matching must find the complete pairing."""
    r = _list_compare(
        ["ab", "abc"],
        ["abc", "ab"],
        field_type="string",
        method="fuzzy",
        options={"threshold": 60},  # low enough that ab~abc also matches
    )
    assert r["is_correct"] is True


def test_list_numeric_tolerance_per_element():
    r = _list_compare(
        [1.0, 2.0],
        [1.0005, 2.0],
        field_type="number",
        method="numeric",
        options={"tolerance": 0.01},
    )
    assert r["is_correct"] is True


# ─── Numeric relative tolerance + gt=0 fallback ─────────────────────────────


def test_numeric_relative_tolerance():
    r = _compare(
        100,
        105,
        field_type="number",
        method="numeric",
        options={"relative": True, "tolerance": 0.1},
    )
    assert r["is_correct"] is True  # 5% within 10%


def test_numeric_relative_gt_zero_falls_back_to_absolute():
    # gt=0 with relative would divide by zero; falls back to absolute diff.
    r = _compare(
        0,
        0.0005,
        field_type="number",
        method="numeric",
        options={"relative": True, "tolerance": 0.001},
    )
    assert r["is_correct"] is True


def test_numeric_type_error_on_non_numeric():
    r = _compare("abc", "def", field_type="number", method="numeric")
    assert r["error_type"] == "type_error"


# ─── Date parsing ───────────────────────────────────────────────────────────


def test_date_multiple_formats_match():
    # Same day expressed two ways.
    r = _compare("2020-01-15", "15/01/2020", field_type="date", method="date")
    assert r["is_correct"] is True


def test_date_parse_error():
    r = _compare("not-a-date", "2020-01-01", field_type="date", method="date")
    assert r["error_type"] == "date_parse_error"
