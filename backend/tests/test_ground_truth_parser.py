"""Pure-unit tests for ``GroundTruthParser`` (backend/src/utils/evaluation.py).

No DB, no network — the parser works on in-memory ``bytes``. These tests cover
every ``parse`` dispatch branch (json / csv / xlsx / zip / unsupported) plus the
row-collection edge cases (missing IDs, duplicates, dot-notation nesting,
multi-sheet merge, auto ID-column resolution) and the error paths.

CSV parsing reads ``settings.CSV_ENCODING_FALLBACK_CHAIN`` at call time, so the
parser is imported lazily inside a helper (matching the sibling evaluation
tests) and the session-scoped conftest fixture provides the test env before any
test runs.
"""

import io
import json
import zipfile
import zipfile as _zipfile
from pathlib import Path

import pandas as pd
import pytest

FILES = Path(__file__).parent / "files"


def _parser():
    from ..src.utils.evaluation import GroundTruthParser

    return GroundTruthParser()


def _xlsx_bytes(sheets: dict) -> bytes:
    """Build an in-memory .xlsx from ``{sheet_name: DataFrame}``."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf) as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return buf.getvalue()


def _zip_bytes(entries: dict) -> bytes:
    """Build an in-memory .zip from ``{arcname: text}``."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in entries.items():
            zf.writestr(name, text)
    return buf.getvalue()


# ─── dispatch ───────────────────────────────────────────────────────────────


def test_parse_unsupported_format_raises():
    with pytest.raises(ValueError, match="Unsupported format"):
        _parser().parse(b"x", "foobar")


# ─── JSON ───────────────────────────────────────────────────────────────────


def test_json_single_object_keyed_by_id():
    data = json.dumps({"id": "A1", "value": 5}).encode()
    result = _parser().parse(data, "json")
    assert result == {"A1": {"id": "A1", "value": 5}}


def test_json_single_object_keyed_by_patient_id():
    data = json.dumps({"patient_id": "P9", "value": 5}).encode()
    result = _parser().parse(data, "json")
    assert result == {"P9": {"patient_id": "P9", "value": 5}}


def test_json_single_object_without_id_raises():
    data = json.dumps({"value": 5}).encode()
    with pytest.raises(ValueError, match="must have 'id' or 'patient_id'"):
        _parser().parse(data, "json")


def test_json_document_map_uses_id_patient_id_and_key_fallback():
    data = json.dumps(
        {
            "k1": {"id": "D1", "x": 1},
            "k2": {"patient_id": "P2", "y": 2},
            "k3": {"z": 3},  # no id/patient_id → fall back to outer key
        }
    ).encode()
    result = _parser().parse(data, "json")
    assert set(result) == {"D1", "P2", "k3"}
    assert result["D1"]["x"] == 1
    assert result["P2"]["y"] == 2
    assert result["k3"]["z"] == 3


def test_json_list_of_objects():
    data = json.dumps([{"id": 1, "a": "x"}, {"patient_id": "P2", "b": "y"}]).encode()
    result = _parser().parse(data, "json")
    assert set(result) == {"1", "P2"}  # ids stringified
    assert result["1"]["a"] == "x"


def test_json_list_item_missing_id_raises():
    data = json.dumps([{"a": 1}]).encode()
    with pytest.raises(ValueError, match="missing 'id' or 'patient_id'"):
        _parser().parse(data, "json")


def test_json_list_non_dict_item_raises():
    data = json.dumps([1, 2]).encode()
    with pytest.raises(ValueError, match="is not an object"):
        _parser().parse(data, "json")


def test_json_scalar_top_level_raises():
    data = json.dumps(5).encode()
    with pytest.raises(ValueError, match="must be an object or array"):
        _parser().parse(data, "json")


def test_json_invalid_syntax_raises():
    with pytest.raises(ValueError, match="Invalid JSON"):
        _parser().parse(b"{not valid json", "json")


# ─── ZIP ────────────────────────────────────────────────────────────────────


def test_zip_multiple_json_documents():
    content = _zip_bytes(
        {
            "rep1.json": json.dumps({"x": 1}),  # no id → filename stem
            "rep2.json": json.dumps({"id": "ZID", "y": 2}),
            "__MACOSX/junk.json": "garbage",  # skipped
            "notes.txt": "ignored",  # non-json ignored
        }
    )
    result = _parser().parse(content, "zip")
    assert set(result) == {"rep1", "ZID"}
    # filename stem injected as id when absent
    assert result["rep1"]["id"] == "rep1"
    assert result["ZID"]["y"] == 2


def test_zip_without_json_raises():
    content = _zip_bytes({"a.txt": "hi"})
    with pytest.raises(ValueError, match="No JSON files found"):
        _parser().parse(content, "zip")


def test_zip_with_invalid_json_raises():
    content = _zip_bytes({"bad.json": "{nope"})
    with pytest.raises(ValueError, match="Invalid JSON in"):
        _parser().parse(content, "zip")


def test_zip_corrupt_archive_raises_badzipfile():
    # A non-zip byte payload surfaces as zipfile.BadZipFile (NOT ValueError) —
    # the parser does not wrap the archive-open failure.
    with pytest.raises(_zipfile.BadZipFile):
        _parser().parse(b"PK\x03\x04 not really a zip", "zip")


# ─── CSV ────────────────────────────────────────────────────────────────────


def test_csv_with_explicit_id_column():
    content = b"id,name,score\nDOC1,Alice,10\nDOC2,Bob,20\n"
    result = _parser().parse(content, "csv", id_column="id")
    assert set(result) == {"DOC1", "DOC2"}
    assert result["DOC1"] == {"name": "Alice", "score": 10}
    # id column itself is not duplicated into the value dict
    assert "id" not in result["DOC1"]


def test_csv_auto_id_column_from_candidates():
    content = b"doc_id,v\n7,x\n"
    result = _parser().parse(content, "csv")
    assert result == {"7": {"v": "x"}}


def test_csv_falls_back_to_row_index_when_no_candidate():
    content = b"foo,bar\nq,r\n"
    result = _parser().parse(content, "csv")
    # keyed by DataFrame row index "0", non-id columns retained
    assert result == {"0": {"foo": "q", "bar": "r"}}


def test_csv_missing_explicit_id_column_raises():
    content = b"a,b\n1,2\n"
    with pytest.raises(ValueError, match="ID column 'nope' was not found"):
        _parser().parse(content, "csv", id_column="nope")


def test_csv_empty_file_raises():
    with pytest.raises(ValueError, match="CSV file is empty"):
        _parser().parse(b"", "csv")


def test_csv_duplicate_ids_raise():
    content = b"id,v\n1,x\n1,y\n"
    with pytest.raises(ValueError, match="Duplicate IDs"):
        _parser().parse(content, "csv", id_column="id")


def test_csv_row_with_data_but_no_id_raises():
    content = b"id,v\n,x\n"
    with pytest.raises(ValueError, match="have data but no value in ID column"):
        _parser().parse(content, "csv", id_column="id")


def test_csv_no_parseable_rows_raises():
    # Header only, no data rows → nothing collected.
    content = b"id,v\n"
    with pytest.raises(ValueError, match="No documents could be parsed"):
        _parser().parse(content, "csv", id_column="id")


def test_csv_dot_notation_columns_nest():
    content = b"id,vitals.hr,vitals.bp\nD1,80,120\n"
    result = _parser().parse(content, "csv", id_column="id")
    assert result == {"D1": {"vitals": {"hr": 80, "bp": 120}}}


def test_csv_header_whitespace_trimmed():
    content = b"id, name \nD1,Alice\n"
    result = _parser().parse(content, "csv", id_column="id")
    assert result == {"D1": {"name": "Alice"}}


def test_csv_id_float_normalized_to_int_string():
    # Blank in an integer id column makes pandas read it as float (123.0);
    # case_id_str renders whole-number floats as ints.
    content = b"id,v\n123,x\n456,y\n\n"
    result = _parser().parse(content, "csv", id_column="id")
    assert set(result) == {"123", "456"}


def test_csv_real_fixture_file():
    content = (FILES / "reports_with_groundtruth.csv").read_bytes()
    result = _parser().parse(content, "csv", id_column="id")
    assert len(result) == 8
    assert "9874562.pdf" in result
    row = result["9874562.pdf"]
    # boolean-like and text columns are preserved
    assert row["chest pain"] is True
    assert row["location"] == "main"
    assert row["side"] == "left"


# ─── Excel ──────────────────────────────────────────────────────────────────


def test_excel_with_explicit_id_column():
    content = _xlsx_bytes({"s": pd.DataFrame({"id": ["A", "B"], "v": [1, 2]})})
    result = _parser().parse(content, "xlsx", id_column="id")
    assert result == {"A": {"v": 1}, "B": {"v": 2}}


def test_excel_auto_id_column_candidate():
    content = _xlsx_bytes({"s": pd.DataFrame({"id": ["A"], "v": [1]})})
    result = _parser().parse(content, "xlsx")
    assert result == {"A": {"v": 1}}


def test_excel_falls_back_to_row_index():
    content = _xlsx_bytes({"s": pd.DataFrame({"foo": ["q"], "v": [1]})})
    result = _parser().parse(content, "xlsx")
    assert result == {"0": {"foo": "q", "v": 1}}


def test_excel_multi_sheet_merge_with_dot_notation():
    content = _xlsx_bytes(
        {
            "s1": pd.DataFrame({"id": ["D1", "D2"], "a": [1, 2]}),
            "s2": pd.DataFrame({"id": ["D1"], "nested.x": [9]}),
        }
    )
    result = _parser().parse(content, "xlsx", id_column="id")
    # D1 is deep-merged across both sheets; D2 only on s1
    assert result["D1"] == {"a": 1, "nested": {"x": 9}}
    assert result["D2"] == {"a": 2}


def test_excel_sheet_missing_id_column_is_skipped():
    content = _xlsx_bytes(
        {
            "good": pd.DataFrame({"id": ["A"], "v": [1]}),
            "bad": pd.DataFrame({"other": [1]}),  # no id column → skipped
        }
    )
    result = _parser().parse(content, "xlsx", id_column="id")
    assert result == {"A": {"v": 1}}


def test_excel_id_column_missing_in_all_sheets_raises():
    content = _xlsx_bytes({"s": pd.DataFrame({"other": [1]})})
    with pytest.raises(ValueError, match="was not found in any sheet"):
        _parser().parse(content, "xlsx", id_column="id")


def test_excel_empty_sheets_yield_no_documents_error():
    content = _xlsx_bytes({"s": pd.DataFrame({"id": [], "v": []})})
    with pytest.raises(ValueError, match="No documents could be parsed"):
        _parser().parse(content, "xlsx", id_column="id")


def test_excel_invalid_bytes_raises():
    with pytest.raises(ValueError, match="Invalid Excel file"):
        _parser().parse(b"not an excel file", "xlsx")


def test_excel_duplicate_ids_within_one_sheet_raise():
    content = _xlsx_bytes({"s": pd.DataFrame({"id": ["D1", "D1"], "v": [1, 2]})})
    with pytest.raises(ValueError, match="Duplicate IDs"):
        _parser().parse(content, "xlsx", id_column="id")


def test_excel_real_fixture_file():
    content = (FILES / "reports_with_groundtruth.xlsx").read_bytes()
    result = _parser().parse(content, "xlsx", id_column="id")
    assert len(result) == 8
    assert "9874562.pdf" in result
    assert result["9874562.pdf"]["location"] == "main"
