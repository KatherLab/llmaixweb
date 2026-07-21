"""Pure-unit tests for ``FieldMapper`` (backend/src/utils/field_mapping.py).

No DB, no network — ``FieldMapper`` is pure pandas/thefuzz/re logic. These
tests exercise ``auto_map`` end-to-end plus every pure helper directly, aiming
for high branch coverage and surfacing a couple of latent logic issues:

* ``common_mappings`` is largely dead for its underscore/suffix variants
  because ``_normalize_field_name`` rewrites ``document_id`` → ``document``,
  ``email_address`` → ``email address`` etc. before the ``name in variants``
  check runs. See ``test_common_mapping_underscore_variant_should_boost`` —
  marked xfail because it asserts the *intended* behaviour.
* The category comparison-method classifier uses a strict ``< 0.5`` unique
  ratio, so a field with exactly 50% distinct values is treated as free-text
  ``exact`` rather than ``category`` (documented, not locked as a bug).
"""

import pytest


def _mapper():
    # Lazy import to match the sibling evaluation tests and keep collection
    # cheap; field_mapping.py has no settings dependency, but the pattern is
    # consistent and harmless.
    from ..src.utils.field_mapping import FieldMapper

    return FieldMapper()


# ─── _normalize_field_name ──────────────────────────────────────────────────


def test_normalize_lowercases_and_replaces_separators():
    m = _mapper()
    assert m._normalize_field_name("Patient_Name") == "patient name"
    assert m._normalize_field_name("birth-date") == "birth date"


def test_normalize_strips_leading_articles():
    m = _mapper()
    assert m._normalize_field_name("the amount") == "amount"
    assert m._normalize_field_name("a record") == "record"
    assert m._normalize_field_name("an entry") == "entry"


def test_normalize_strips_trailing_id_number_suffixes():
    m = _mapper()
    # underscore -> space, then trailing " id"/"number"/"num"/"no" removed
    assert m._normalize_field_name("document_id") == "document"
    assert m._normalize_field_name("phone number") == "phone"
    assert m._normalize_field_name("item_num") == "item"
    assert m._normalize_field_name("line_no") == "line"


def test_normalize_collapses_extra_spaces():
    m = _mapper()
    assert m._normalize_field_name("  first    last  ") == "first last"


# ─── _calculate_name_similarity ─────────────────────────────────────────────


def test_name_similarity_exact_match_is_one():
    m = _mapper()
    assert m._calculate_name_similarity("age", "age") == 1.0
    # Match after normalization (case + separator) still counts as exact.
    assert m._calculate_name_similarity("Patient_Name", "patient name") == 1.0


def test_name_similarity_common_mapping_single_token_variant():
    """The common-mappings 0.9 boost fires for single-token variants that
    survive normalization unchanged (telephone, total, timestamp, ...)."""
    m = _mapper()
    assert m._calculate_name_similarity("phone", "telephone") == 0.9
    assert m._calculate_name_similarity("amount", "total") == 0.9
    assert m._calculate_name_similarity("date", "timestamp") == 0.9
    # symmetric: key/variant order swapped
    assert m._calculate_name_similarity("mobile", "phone") == 0.9


def test_name_similarity_fuzzy_fallback():
    m = _mapper()
    score = m._calculate_name_similarity("patient", "patinet")  # typo
    assert 0.0 < score < 1.0


def test_name_similarity_unrelated_is_low():
    m = _mapper()
    assert m._calculate_name_similarity("qqqqqq", "zzzzzz") < 0.3


def test_common_mapping_underscore_variant_boosts():
    m = _mapper()
    # 'id' maps to 'document_id' via common_mappings → 0.9. The variant list is
    # now normalized before comparison (fixed in field_mapping.py), so the boost
    # fires for underscore/suffix variants, not just single-token ones.
    assert m._calculate_name_similarity("id", "document_id") >= 0.9
    assert m._calculate_name_similarity("address", "street_address") >= 0.9


# ─── value-compatibility helpers ────────────────────────────────────────────


def test_boolean_compatibility_scoring():
    m = _mapper()
    assert m._check_boolean_compatibility(["true", "false", "yes", "no"]) == 1.0
    assert m._check_boolean_compatibility(["1", "0", "on", "off"]) == 1.0
    # half boolean-like
    assert m._check_boolean_compatibility(["true", "banana"]) == 0.5
    assert m._check_boolean_compatibility(["banana", "apple"]) == 0.0


def test_number_compatibility_scoring():
    m = _mapper()
    assert m._check_number_compatibility(["1", "2.5", "-3"]) == 1.0
    # comma stripped ("2,500" -> 2500)
    assert m._check_number_compatibility(["2,500"]) == 1.0
    # 2 of 3 numeric
    assert m._check_number_compatibility(["1", "2", "x"]) == pytest.approx(2 / 3)


def test_date_compatibility_regex_and_parser_paths():
    m = _mapper()
    # regex-matched ISO date + parser-matched textual date → both count
    assert m._check_date_compatibility(["2020-01-01", "January 5, 2020"]) == 1.0
    # one date, one unparseable string → 0.5 (exercises the except branches)
    assert m._check_date_compatibility(["2020-01-01", "definitely not a date"]) == 0.5


def test_category_compatibility_scoring():
    m = _mapper()
    # <=50% unique → high categorical score
    assert m._check_category_compatibility(["a", "a", "b", "b"]) == 0.9
    # all unique → low categorical score
    assert m._check_category_compatibility(["a", "b", "c", "d"]) == 0.3


def test_calculate_value_compatibility_dispatch():
    m = _mapper()
    assert m._calculate_value_compatibility("boolean", ["yes", "no"]) == 1.0
    assert m._calculate_value_compatibility("number", ["1", "2"]) == 1.0
    assert m._calculate_value_compatibility("date", ["2020-01-01"]) == 1.0
    assert m._calculate_value_compatibility("category", ["a", "a", "b", "b"]) == 0.9
    # unknown/string type → default high compatibility
    assert m._calculate_value_compatibility("string", ["free text"]) == 0.8


def test_calculate_value_compatibility_neutral_for_empty_or_all_null():
    m = _mapper()
    assert m._calculate_value_compatibility("number", []) == 0.5
    assert m._calculate_value_compatibility("number", [None, None]) == 0.5


# ─── _get_comparison_method ─────────────────────────────────────────────────


def test_comparison_method_by_type():
    m = _mapper()
    assert m._get_comparison_method("boolean", ["true"]) == "boolean"
    assert m._get_comparison_method("number", ["1"]) == "numeric"
    assert m._get_comparison_method("date", ["2020-01-01"]) == "date"


def test_comparison_method_empty_samples_guarded():
    m = _mapper()
    # Guard against divide-by-zero on all-null name-matched columns.
    assert m._get_comparison_method("category", []) == "exact"
    assert m._get_comparison_method("string", []) == "exact"


def test_comparison_method_category_unique_ratio():
    m = _mapper()
    # unique_ratio strictly < 0.5 → "category" (2 unique / 5 = 0.4)
    assert m._get_comparison_method("category", ["a", "a", "a", "a", "b"]) == "category"
    # exactly 0.5 (2 unique / 4) is NOT < 0.5 → falls through to "exact".
    # (Documenting actual boundary behaviour, not asserting it's ideal.)
    assert m._get_comparison_method("category", ["a", "a", "b", "b"]) == "exact"


def test_comparison_method_string_length_heuristic():
    m = _mapper()
    # avg length > 20 → fuzzy
    assert m._get_comparison_method("string", ["x" * 30, "y" * 30]) == "fuzzy"
    # short strings → exact
    assert m._get_comparison_method("string", ["hi", "yo"]) == "exact"


# ─── _get_comparison_options ────────────────────────────────────────────────


def test_comparison_options_per_method():
    m = _mapper()
    assert m._get_comparison_options("string", "fuzzy") == {"threshold": 85}
    assert m._get_comparison_options("number", "numeric") == {
        "tolerance": 0.001,
        "relative": False,
    }
    assert m._get_comparison_options("string", "exact") == {"case_sensitive": False}
    # boolean / date / category get no extra options
    assert m._get_comparison_options("boolean", "boolean") == {}
    assert m._get_comparison_options("date", "date") == {}
    assert m._get_comparison_options("category", "category") == {}


# ─── auto_map (integration of all helpers) ──────────────────────────────────


def test_auto_map_exact_matches_high_confidence():
    m = _mapper()
    schema = {
        "age": "number",
        "active": "boolean",
        "birth_date": "date",
        "note": "string",
    }
    gt = {
        "age": [10, 20, 30],
        "active": ["true", "false", "yes"],
        "birth_date": ["2020-01-01", "2019-05-05"],
        "note": ["some free-form text", "another note"],
    }
    result = {r["schema_field"]: r for r in m.auto_map(schema, gt)}

    assert result["age"]["ground_truth_field"] == "age"
    assert result["age"]["field_type"] == "number"
    assert result["age"]["comparison_method"] == "numeric"
    assert result["age"]["comparison_options"] == {
        "tolerance": 0.001,
        "relative": False,
    }
    assert result["age"]["confidence"] == pytest.approx(1.0)

    assert result["active"]["comparison_method"] == "boolean"
    assert result["active"]["confidence"] == pytest.approx(1.0)

    assert result["birth_date"]["comparison_method"] == "date"
    assert result["birth_date"]["confidence"] == pytest.approx(1.0)

    # string field: name 1.0 * 0.6 + value 0.8 * 0.4 = 0.92
    assert result["note"]["comparison_method"] == "exact"
    assert result["note"]["confidence"] == pytest.approx(0.92)


def test_auto_map_fuzzy_normalized_name_match():
    m = _mapper()
    # schema 'patientName' should match gt 'patient_name' after normalization
    schema = {"patientName": "string"}
    gt = {"patient_name": ["Alice", "Bob"]}
    result = m.auto_map(schema, gt)
    assert len(result) == 1
    assert result[0]["ground_truth_field"] == "patient_name"
    # 'patientName' vs 'patient_name' normalize to 'patientname' vs 'patient name'
    # (camelCase isn't split), so the name match is fuzzy-high rather than exact —
    # still comfortably above the default 0.7 threshold.
    assert result[0]["confidence"] > 0.8


def test_auto_map_category_confidence_and_method():
    m = _mapper()
    schema = {"status": "category"}
    # 2 unique / 4 → category compat 0.9 (name 1.0*0.6 + 0.9*0.4 = 0.96)
    gt = {"status": ["A", "A", "B", "B"]}
    result = m.auto_map(schema, gt)[0]
    assert result["confidence"] == pytest.approx(0.96)
    # method uses the < 0.5 boundary → "exact" here (see method test above)
    assert result["comparison_method"] == "exact"


def test_auto_map_drops_below_threshold():
    m = _mapper()
    # Unrelated name + string values → confidence ~= 0.32, below 0.7 default.
    schema = {"qqqqqq": "string"}
    gt = {"zzzzzz": ["free text value here"]}
    assert m.auto_map(schema, gt) == []


def test_auto_map_custom_threshold_includes_weak_match():
    m = _mapper()
    schema = {"qqqqqq": "string"}
    gt = {"zzzzzz": ["free text"]}
    # With a permissive threshold the weak (~0.32) match is kept.
    result = m.auto_map(schema, gt, confidence_threshold=0.1)
    assert len(result) == 1
    assert result[0]["ground_truth_field"] == "zzzzzz"


def test_auto_map_high_threshold_drops_good_match():
    m = _mapper()
    schema = {"note": "string"}
    gt = {"note": ["text"]}  # confidence 0.92
    assert m.auto_map(schema, gt, confidence_threshold=0.99) == []


def test_auto_map_results_sorted_by_confidence_desc():
    m = _mapper()
    schema = {"age": "number", "note": "string"}
    gt = {"age": [1, 2, 3], "note": ["some text"]}
    result = m.auto_map(schema, gt)
    confidences = [r["confidence"] for r in result]
    assert confidences == sorted(confidences, reverse=True)
    # age (1.0) must come before note (0.92)
    assert result[0]["schema_field"] == "age"


def test_auto_map_picks_best_of_multiple_candidates():
    m = _mapper()
    schema = {"age": "number"}
    gt = {"unrelated": ["x", "y"], "age": [1, 2, 3]}
    result = m.auto_map(schema, gt)
    assert len(result) == 1
    assert result[0]["ground_truth_field"] == "age"


def test_auto_map_empty_inputs():
    m = _mapper()
    assert m.auto_map({}, {"a": [1]}) == []
    # No ground-truth fields → nothing can match.
    assert m.auto_map({"a": "string"}, {}) == []
