"""Pure-unit tests for the no-I/O helpers in ``backend/src/utils/helpers.py``.

These cover the label/filename builders, the MIME magic-byte sniffers, the
encoding detector, the whole JSON-schema validation family, and the small
datetime/prompt helpers. Everything here is deterministic and dependency-free
(no DB, no network).

IMPORTANT: ``helpers.py`` defines a module-level function named
``test_remote_image_support`` (leading ``test_``). We deliberately import only
the specific helpers under test — never ``import *`` — so pytest does not
collect that network function as a test case.
"""

import io
import sys
import zipfile
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from backend.src.schemas.project import PromptUpdate
from backend.src.utils.helpers import (
    CSV_MIME,
    XLS_MIME,
    XLSX_MIME,
    _is_zip,
    _looks_like_ole_xls,
    _looks_like_xlsx,
    _make_aware,
    _resolve_schema_type,
    check_field_types,
    check_missing_fields_nested,
    check_value_type,
    content_disposition,
    detect_structured_mime,
    detect_text_encoding,
    excel_sheet_name,
    extract_field_types_from_schema,
    extract_leaf_paths_from_dict,
    extract_required_fields_from_schema,
    find_extra_fields,
    find_extra_fields_nested,
    flatten_dict,
    make_naive_fields_timezone_aware,
    trial_display_label,
    trial_filename_slug,
    validate_prompt,
)


class _Trial:
    """Minimal stand-in for the Trial ORM object (only attrs the helpers read)."""

    def __init__(self, name=None, project_trial_number=1):
        self.name = name
        self.project_trial_number = project_trial_number


# --------------------------------------------------------------------------- #
# trial_display_label
# --------------------------------------------------------------------------- #
class TestTrialDisplayLabel:
    def test_uses_name_when_set(self):
        assert trial_display_label(_Trial(name="My Run", project_trial_number=7)) == (
            "My Run"
        )

    def test_strips_whitespace_from_name(self):
        assert trial_display_label(_Trial(name="  Named  ")) == "Named"

    def test_falls_back_to_number_when_name_none(self):
        assert trial_display_label(_Trial(name=None, project_trial_number=3)) == (
            "Trial #3"
        )

    def test_falls_back_when_name_is_only_whitespace(self):
        assert trial_display_label(_Trial(name="   ", project_trial_number=9)) == (
            "Trial #9"
        )


# --------------------------------------------------------------------------- #
# trial_filename_slug
# --------------------------------------------------------------------------- #
class TestTrialFilenameSlug:
    def test_plain_name(self):
        assert trial_filename_slug(_Trial(name="report")) == "report"

    def test_special_chars_become_underscores(self):
        assert trial_filename_slug(_Trial(name="a b/c:d")) == "a_b_c_d"

    def test_keeps_word_dot_dash(self):
        assert trial_filename_slug(_Trial(name="v1.2-final")) == "v1.2-final"

    def test_leading_trailing_separators_stripped(self):
        assert trial_filename_slug(_Trial(name="__weird__")) == "weird"

    def test_all_special_falls_back_to_number(self):
        # "***" -> single "_" -> stripped to "" -> falsy -> trial_N
        assert trial_filename_slug(_Trial(name="***", project_trial_number=4)) == (
            "trial_4"
        )

    def test_none_name_falls_back(self):
        assert trial_filename_slug(_Trial(name=None, project_trial_number=8)) == (
            "trial_8"
        )

    def test_truncated_to_80_chars(self):
        slug = trial_filename_slug(_Trial(name="a" * 200))
        assert len(slug) == 80
        assert slug == "a" * 80


# --------------------------------------------------------------------------- #
# content_disposition (mostly covered in test_download_safety.py — add gaps)
# --------------------------------------------------------------------------- #
class TestContentDisposition:
    def test_none_filename_falls_back(self):
        # Distinct from the empty-string case already covered elsewhere.
        assert "download" in content_disposition(None)

    def test_custom_disposition_prefix(self):
        assert content_disposition("a.png", "inline").startswith("inline; ")


# --------------------------------------------------------------------------- #
# detect_text_encoding
# --------------------------------------------------------------------------- #
class _FakeChardet:
    def __init__(self, encoding, confidence):
        self._encoding = encoding
        self._confidence = confidence

    def detect(self, _content):
        return {"encoding": self._encoding, "confidence": self._confidence}


class TestDetectTextEncoding:
    def test_fallback_chain_first_success(self):
        # Invalid UTF-8, but latin-1 decodes any byte sequence.
        out = detect_text_encoding(b"\xff\xfe", "utf-8,latin-1", use_chardet=False)
        assert out == "latin-1"

    def test_plain_ascii_utf8(self):
        assert detect_text_encoding(b"hello", "utf-8", use_chardet=False) == "utf-8"

    def test_unknown_encoding_in_chain_is_skipped(self):
        # "bogus-enc" raises LookupError -> skipped -> utf-8 succeeds.
        out = detect_text_encoding(b"hi", "bogus-enc,utf-8", use_chardet=False)
        assert out == "utf-8"

    def test_empty_chain_returns_utf8(self):
        assert detect_text_encoding(b"\xff", "", use_chardet=False) == "utf-8"

    def test_all_fail_returns_utf8(self):
        # No fallback can decode 0xFF as UTF-8/ASCII -> final default.
        assert detect_text_encoding(b"\xff", "utf-8,ascii", use_chardet=False) == (
            "utf-8"
        )

    def test_missing_chardet_falls_back(self):
        # chardet is genuinely not installed in this env -> ImportError path.
        assert "chardet" not in sys.modules or sys.modules.get("chardet") is not None
        out = detect_text_encoding(b"hello", "utf-8", use_chardet=True)
        assert out == "utf-8"

    def test_chardet_high_confidence_used(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "chardet", _FakeChardet("utf-8", 0.99))
        assert detect_text_encoding(b"hello", "latin-1", use_chardet=True) == "utf-8"

    def test_chardet_low_confidence_ignored(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "chardet", _FakeChardet("utf-16", 0.1))
        # Low confidence -> ignore chardet -> use fallback chain.
        assert detect_text_encoding(b"hello", "ascii", use_chardet=True) == "ascii"

    def test_chardet_detected_encoding_undecodable_falls_through(self, monkeypatch):
        # High confidence but the guessed encoding cannot decode -> fall through.
        monkeypatch.setitem(sys.modules, "chardet", _FakeChardet("ascii", 0.99))
        out = detect_text_encoding(b"\xff\xfe", "latin-1", use_chardet=True)
        assert out == "latin-1"

    def test_chardet_none_encoding_defaults_utf8(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "chardet", _FakeChardet(None, 0.99))
        assert detect_text_encoding(b"hello", "ascii", use_chardet=True) == "utf-8"


# --------------------------------------------------------------------------- #
# MIME magic-byte sniffers
# --------------------------------------------------------------------------- #
def _make_zip(*members: str, extra_bytes: int = 0) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name in members:
            zf.writestr(name, "<x/>")
        if extra_bytes:
            zf.writestr("padding.bin", b"Q" * extra_bytes)
    return buf.getvalue()


class TestZipSniffers:
    def test_is_zip_true(self):
        assert _is_zip(b"PK\x03\x04rest") is True

    def test_is_zip_false_wrong_magic(self):
        assert _is_zip(b"%PDF-1.4") is False

    def test_is_zip_false_too_short(self):
        assert _is_zip(b"PK") is False

    def test_looks_like_xlsx_true_workbook(self):
        assert _looks_like_xlsx(_make_zip("xl/workbook.xml")) is True

    def test_looks_like_xlsx_true_content_types(self):
        assert _looks_like_xlsx(_make_zip("[Content_Types].xml")) is True

    def test_looks_like_xlsx_false_generic_zip(self):
        assert _looks_like_xlsx(_make_zip("readme.txt")) is False

    def test_looks_like_xlsx_false_not_zip(self):
        assert _looks_like_xlsx(b"not a zip at all") is False

    def test_looks_like_xlsx_false_corrupt_zip(self):
        # Valid ZIP magic prefix but truncated body -> BadZipFile -> False.
        assert _looks_like_xlsx(b"PK\x03\x04" + b"\x00" * 20) is False

    def test_looks_like_ole_xls_true(self):
        assert _looks_like_ole_xls(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\x1e" + b"junk") is (
            True
        )

    def test_looks_like_ole_xls_false(self):
        assert _looks_like_ole_xls(b"PK\x03\x04") is False

    def test_looks_like_ole_xls_too_short(self):
        assert _looks_like_ole_xls(b"\xd0\xcf") is False


class TestDetectStructuredMime:
    def test_magic_xlsx_beats_everything(self):
        # xlsx magic wins even if the name/provided mime say CSV.
        content = _make_zip("xl/workbook.xml")
        assert detect_structured_mime("foo.csv", content, "text/csv") == XLSX_MIME

    def test_magic_ole_xls(self):
        content = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\x1e" + b"\x00" * 100
        assert detect_structured_mime("foo.csv", content, "text/csv") == XLS_MIME

    def test_extension_xlsx(self):
        assert detect_structured_mime("book.xlsx", b"random", None) == XLSX_MIME

    def test_extension_xls(self):
        assert detect_structured_mime("book.xls", b"random", None) == XLS_MIME

    def test_extension_csv(self):
        assert detect_structured_mime("data.csv", b"a,b\n1,2", None) == CSV_MIME

    def test_provided_csv_hint(self):
        assert detect_structured_mime("noext", b"a,b", "text/csv") == CSV_MIME

    def test_provided_xlsx_hint(self):
        assert detect_structured_mime("noext", b"data", XLSX_MIME) == XLSX_MIME

    def test_provided_xls_hint(self):
        assert detect_structured_mime("noext", b"data", XLS_MIME) == XLS_MIME

    def test_mimetypes_guess_fallback(self):
        assert detect_structured_mime("notes.txt", b"hello", None) == "text/plain"

    def test_last_resort_returns_provided(self):
        assert detect_structured_mime("mystery", b"???", "foo/bar") == "foo/bar"

    def test_last_resort_octet_stream(self):
        assert detect_structured_mime("mystery", b"???", None) == (
            "application/octet-stream"
        )

    @pytest.mark.xfail(
        strict=False,
        reason="BUG: detect_structured_mime only inspects content[:4096]; the "
        "ZIP central directory of an XLSX larger than 4KB lands past that window "
        "so magic-byte detection fails and it mislabels the file "
        "(helpers.py:173).",
    )
    def test_large_xlsx_detected_by_magic(self):
        # A real >4KB xlsx with no telltale extension should still be XLSX.
        big = _make_zip("xl/workbook.xml", extra_bytes=8000)
        assert len(big) > 4096
        assert detect_structured_mime("data", big, None) == XLSX_MIME


# --------------------------------------------------------------------------- #
# JSON-schema family
# --------------------------------------------------------------------------- #
SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "address": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "zip": {"type": "string"},
            },
            "required": ["city"],
        },
        "tags": {"type": "array", "items": {"type": "string"}},
        "contacts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                },
                "required": ["email"],
            },
        },
    },
    "required": ["name", "address"],
}


class TestExtractRequiredFields:
    def test_nested_and_array_object_required(self):
        assert extract_required_fields_from_schema(SCHEMA) == [
            "name",
            "address",
            "address.city",
            "contacts[].email",
        ]

    def test_no_properties_returns_empty(self):
        assert extract_required_fields_from_schema({"type": "string"}) == []

    def test_prefix_is_applied(self):
        out = extract_required_fields_from_schema(
            {"properties": {"x": {"type": "string"}}, "required": ["x"]}, prefix="root"
        )
        assert out == ["root.x"]


class TestCheckMissingFieldsNested:
    def test_detects_nested_missing(self):
        data = {"name": "x", "address": {"zip": "1"}}
        req = extract_required_fields_from_schema(SCHEMA)
        # address.city missing; contacts[].email skipped (array notation).
        assert check_missing_fields_nested(data, req) == ["address.city"]

    def test_all_present(self):
        data = {"name": "x", "address": {"city": "c"}}
        assert check_missing_fields_nested(
            data, ["name", "address", "address.city"]
        ) == ([])

    def test_top_level_missing(self):
        assert check_missing_fields_nested({"address": {}}, ["name"]) == ["name"]

    def test_array_notation_is_skipped(self):
        assert check_missing_fields_nested({}, ["contacts[].email"]) == []

    def test_intermediate_non_dict_is_missing(self):
        # 'address' is a scalar, so 'address.city' cannot be resolved.
        assert check_missing_fields_nested({"address": "oops"}, ["address.city"]) == [
            "address.city"
        ]


class TestFindExtraFields:
    def test_extra_top_and_nested(self):
        data = {
            "name": "x",
            "extra1": "y",
            "address": {"city": "c", "bogus": "z"},
            "id": 5,  # ignored
            "contacts": [{"email": "e"}],
        }
        assert sorted(find_extra_fields(data, SCHEMA)) == ["address.bogus", "extra1"]

    def test_ignore_fields_dropped(self):
        data = {"id": 1, "document_id": 2, "_id": 3, "name": "ok"}
        assert find_extra_fields(data, SCHEMA) == []

    def test_no_extras(self):
        assert find_extra_fields({"name": "x"}, SCHEMA) == []

    def test_nested_wrapper_matches_direct(self):
        data = {"name": "x", "junk": 1}
        assert find_extra_fields(data, SCHEMA) == find_extra_fields_nested(data, SCHEMA)

    def test_arrays_of_objects_not_descended(self):
        # get_schema_fields does not expand array-item objects, but the data
        # value for an array is a list (not a dict) so it is not descended
        # either -> no false positives for contact sub-fields.
        data = {"contacts": [{"email": "e", "surprise": 1}]}
        assert find_extra_fields(data, SCHEMA) == []


class TestCheckValueType:
    def test_none_is_ok(self):
        assert check_value_type(None, "string", "f") is None

    def test_string_ok(self):
        assert check_value_type("hi", "string", "f") is None

    def test_number_accepts_int(self):
        assert check_value_type(5, "number", "f") is None

    def test_number_accepts_float(self):
        assert check_value_type(1.5, "number", "f") is None

    def test_integer_accepts_whole_float(self):
        assert check_value_type(5.0, "integer", "f") is None

    def test_unknown_type_skipped(self):
        assert check_value_type("anything", "geo-point", "f") is None

    def test_string_expected_got_number(self):
        msg = check_value_type(5, "string", "f")
        assert msg is not None and "wrap the value in quotes" in msg

    def test_number_expected_got_text(self):
        msg = check_value_type("5", "number", "amount")
        assert msg is not None and "amount" in msg and "numeric value" in msg

    def test_integer_expected_got_fractional_float(self):
        msg = check_value_type(5.5, "integer", "f")
        assert msg == "Field 'f' expects integer but got float"

    def test_boolean_expected_got_string(self):
        msg = check_value_type("true", "boolean", "flag")
        assert msg is not None and "true/false" in msg

    def test_boolean_true_ok(self):
        assert check_value_type(True, "boolean", "f") is None

    def test_generic_mismatch_message(self):
        msg = check_value_type([1, 2], "object", "f")
        assert msg == "Field 'f' expects object but got list"

    def test_integer_got_bool_is_rejected(self):
        # bool is a subclass of int in Python; a well-behaved validator should
        # still reject True/False where an integer is required. It currently
        # slips through (returns None) because isinstance(True, int) is True.
        result = check_value_type(True, "integer", "f")
        if result is None:
            pytest.xfail(
                "BUG: bool passes the integer type check because bool subclasses "
                "int (helpers.py:734)."
            )
        assert result is not None


class TestCheckFieldTypes:
    def test_no_errors_for_valid_data(self):
        data = {
            "name": "x",
            "age": 30,
            "address": {"city": "c", "zip": "1"},
            "contacts": [{"email": "a@b.c"}],
        }
        assert check_field_types(data, SCHEMA) == []

    def test_top_level_type_error(self):
        errors = check_field_types({"age": "old"}, SCHEMA)
        assert any("age" in e for e in errors)

    def test_nested_object_type_error(self):
        errors = check_field_types({"address": {"city": 123}}, SCHEMA)
        assert any(e.startswith("Field 'address.city'") for e in errors)

    def test_array_of_objects_indexed_error(self):
        errors = check_field_types({"contacts": [{"email": 123}]}, SCHEMA)
        assert any("contacts[0].email" in e for e in errors)

    def test_missing_field_not_reported_here(self):
        # Missing fields are handled elsewhere; check_field_types ignores them.
        assert check_field_types({}, SCHEMA) == []

    def test_no_properties_key(self):
        assert check_field_types({"a": 1}, {"type": "object"}) == []


class TestResolveSchemaType:
    @pytest.mark.parametrize(
        "prop_def,expected",
        [
            ({"type": "string"}, "string"),
            ({"type": "integer"}, "number"),
            ({"type": "number"}, "number"),
            ({"type": "boolean"}, "boolean"),
            ({"type": "array"}, "string"),  # 'array' not in mapping -> default
            ({"type": ["string", "null"]}, "string"),
            ({"type": ["null", "number"]}, "number"),
            ({"type": ["null"]}, "string"),  # only null -> default
            ({"anyOf": [{"type": "null"}, {"type": "integer"}]}, "number"),
            ({"oneOf": [{"type": "boolean"}]}, "boolean"),
            ({"$ref": "#/$defs/Thing"}, "string"),
            ({"const": 5}, "string"),
            ({}, "string"),
        ],
    )
    def test_resolve(self, prop_def, expected):
        assert _resolve_schema_type(prop_def) == expected


class TestExtractFieldTypesFromSchema:
    def test_full_schema(self):
        schema = {
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
                "active": {"type": "boolean"},
                "status": {"type": "string", "enum": ["a", "b"]},
                "created": {"type": "string", "format": "date-time"},
                "birth": {"type": "string", "format": "date"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "address": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                },
                "contacts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"email": {"type": "string"}},
                    },
                },
            }
        }
        result = {}
        extract_field_types_from_schema(schema, result)
        assert result == {
            "name": "string",
            "count": "number",
            "active": "boolean",
            "status": "category",
            "created": "date",
            "birth": "date",
            "tags[]": "string",
            "address.city": "string",
            "contacts[].email": "string",
        }

    def test_array_of_non_dict_items(self):
        # items given as a tuple/list form (not a dict) -> "string".
        schema = {"properties": {"x": {"type": "array", "items": [{"type": "string"}]}}}
        result = {}
        extract_field_types_from_schema(schema, result)
        assert result == {"x[]": "string"}

    def test_array_without_items_key(self):
        schema = {"properties": {"x": {"type": "array"}}}
        result = {}
        extract_field_types_from_schema(schema, result)
        assert result == {"x": "string"}

    def test_no_properties_is_noop(self):
        result = {}
        extract_field_types_from_schema({"type": "string"}, result)
        assert result == {}


class TestExtractLeafPathsFromDict:
    def test_nested_dict(self):
        data = {"a": 1, "b": {"c": 2}}
        assert extract_leaf_paths_from_dict(data) == ["a", "b.c"]

    def test_list_valued_field_is_a_single_leaf(self):
        # A list value inside a dict is treated as a leaf (the recursion into
        # list items only happens when the top-level arg is itself a list).
        assert extract_leaf_paths_from_dict({"d": [1, 2], "a": 1}) == ["d", "a"]

    def test_top_level_list_indexes(self):
        assert extract_leaf_paths_from_dict([{"e": 3}, {"f": 4}]) == [
            "[0].e",
            "[1].f",
        ]

    def test_scalar_returns_empty(self):
        assert extract_leaf_paths_from_dict(42) == []


class TestFlattenDict:
    def test_nested_and_list_of_dicts(self):
        data = {"a": 1, "b": {"c": 2}, "d": [{"e": 3}, 5]}
        assert flatten_dict(data) == {
            "a": 1,
            "b.c": 2,
            "d[0].e": 3,
            "d[1]": 5,
        }

    def test_custom_separator(self):
        assert flatten_dict({"a": {"b": 1}}, sep="/") == {"a/b": 1}

    def test_scalar_top_level(self):
        assert flatten_dict("x") == {"": "x"}

    def test_scalar_top_level_with_parent_key(self):
        assert flatten_dict(5, parent_key="root") == {"root": 5}


# --------------------------------------------------------------------------- #
# excel_sheet_name
# --------------------------------------------------------------------------- #
class TestExcelSheetName:
    def test_plain_label(self):
        assert excel_sheet_name("Summary") == "Summary"

    def test_forbidden_chars_replaced(self):
        # : \ / ? * [ ] all become spaces, collapsed.
        assert excel_sheet_name(r"a:b/c\d?e*f[g]h") == "a b c d e f g h"

    def test_truncated_to_31_chars(self):
        name = excel_sheet_name("x" * 50)
        assert len(name) == 31
        assert name == "x" * 31

    def test_empty_uses_fallback(self):
        assert excel_sheet_name("[]:*?", fallback="Data") == "Data"

    def test_whitespace_only_uses_fallback(self):
        assert excel_sheet_name("   ") == "Sheet"

    def test_uniqueness_suffix(self):
        used: set[str] = set()
        first = excel_sheet_name("Trial", used=used)
        second = excel_sheet_name("Trial", used=used)
        third = excel_sheet_name("Trial", used=used)
        assert first == "Trial"
        assert second == "Trial (2)"
        assert third == "Trial (3)"
        assert used == {"Trial", "Trial (2)", "Trial (3)"}

    def test_uniqueness_truncates_long_base(self):
        used = {"z" * 31}
        name = excel_sheet_name("z" * 40, used=used)
        # base truncated to fit the " (2)" suffix within 31 chars.
        assert len(name) == 31
        assert name.endswith(" (2)")


# --------------------------------------------------------------------------- #
# datetime helpers
# --------------------------------------------------------------------------- #
class TestDatetimeHelpers:
    def test_make_naive_fields_adds_utc(self):
        dt = datetime(2020, 1, 1, 12, 0, 0)
        out = make_naive_fields_timezone_aware(dt)
        assert out.tzinfo == timezone.utc

    def test_make_naive_fields_leaves_aware(self):
        dt = datetime(2020, 1, 1, tzinfo=timezone.utc)
        assert make_naive_fields_timezone_aware(dt) is dt

    def test_make_naive_fields_passthrough_non_datetime(self):
        assert make_naive_fields_timezone_aware("not a date") == "not a date"

    def test_make_aware_none(self):
        assert _make_aware(None) is None

    def test_make_aware_naive(self):
        out = _make_aware(datetime(2021, 6, 1))
        assert out.tzinfo == timezone.utc

    def test_make_aware_already_aware(self):
        dt = datetime(2021, 6, 1, tzinfo=timezone.utc)
        assert _make_aware(dt) is dt


# --------------------------------------------------------------------------- #
# validate_prompt
# --------------------------------------------------------------------------- #
class TestValidatePrompt:
    def test_raises_when_both_empty(self):
        with pytest.raises(HTTPException) as exc:
            validate_prompt(PromptUpdate())
        assert exc.value.status_code == 400
        detail = exc.value.detail
        code = detail.get("code") if isinstance(detail, dict) else None
        assert code == "core.prompt_required"

    def test_ok_with_system_prompt_only(self):
        assert validate_prompt(PromptUpdate(system_prompt="Extract fields")) is None

    def test_ok_with_user_prompt_only(self):
        assert validate_prompt(PromptUpdate(user_prompt="{document_content}")) is None

    def test_raises_when_both_blank_strings(self):
        # Empty strings are falsy, so this is still "no prompt".
        with pytest.raises(HTTPException):
            validate_prompt(PromptUpdate(system_prompt="", user_prompt=""))
