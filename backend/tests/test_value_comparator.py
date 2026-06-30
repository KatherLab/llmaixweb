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
