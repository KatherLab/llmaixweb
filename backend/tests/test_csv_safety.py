# backend/tests/test_csv_safety.py
"""Pure-unit tests for backend/src/utils/csv_safety.py.

CSV formula-injection neutralization. Logic-only: we exercise the sanitizer
directly and drive the writer wrappers over a real csv.writer / csv.DictWriter
backed by an in-memory StringIO, asserting the produced buffer.
"""

import csv
import io

import pytest

from backend.src.utils.csv_safety import (
    SafeCsvWriter,
    SafeDictCsvWriter,
    safe_csv_row,
    sanitize_csv_cell,
)


class TestSanitizeCsvCell:
    @pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
    def test_formula_prefixes_neutralized(self, prefix):
        payload = f"{prefix}cmd|'/c calc'!A1"
        assert sanitize_csv_cell(payload) == "'" + payload

    @pytest.mark.parametrize("ws", ["\t", "\r"])
    def test_leading_risky_whitespace_neutralized(self, ws):
        assert sanitize_csv_cell(f"{ws}=1+1") == "'" + f"{ws}=1+1"

    def test_bare_equals(self):
        assert sanitize_csv_cell("=") == "'="

    def test_plain_text_unchanged(self):
        assert sanitize_csv_cell("hello world") == "hello world"

    def test_formula_char_not_leading_unchanged(self):
        assert sanitize_csv_cell("a=b") == "a=b"
        assert sanitize_csv_cell("1-2") == "1-2"

    def test_leading_newline_not_neutralized(self):
        # \n is NOT in the risky-leading-whitespace set; documents the branch.
        assert sanitize_csv_cell("\n=1") == "\n=1"

    def test_leading_space_not_neutralized(self):
        assert sanitize_csv_cell(" =1") == " =1"

    def test_empty_string_unchanged(self):
        assert sanitize_csv_cell("") == ""

    @pytest.mark.parametrize("value", [0, 5, -3, 3.14, True, False, None])
    def test_non_strings_pass_through(self, value):
        assert sanitize_csv_cell(value) is value

    def test_number_that_would_be_formula_as_int_is_safe(self):
        # An int -5 has no leading '-' string char, so it passes untouched.
        assert sanitize_csv_cell(-5) == -5


class TestSafeCsvRow:
    def test_maps_over_iterable(self):
        assert safe_csv_row(["=a", "b", 5, "-c"]) == ["'=a", "b", 5, "'-c"]

    def test_empty(self):
        assert safe_csv_row([]) == []

    def test_consumes_generator(self):
        gen = (v for v in ["@x", 1])
        assert safe_csv_row(gen) == ["'@x", 1]


class TestSafeCsvWriter:
    def _writer(self):
        buf = io.StringIO()
        return buf, SafeCsvWriter(csv.writer(buf))

    def test_writerow_sanitizes(self):
        buf, w = self._writer()
        w.writerow(["=cmd", "ok", 5])
        assert buf.getvalue() == "'=cmd,ok,5\r\n"

    def test_writerows_sanitizes_each(self):
        buf, w = self._writer()
        w.writerows([["=a", "b"], ["-c", 2]])
        assert buf.getvalue() == "'=a,b\r\n'-c,2\r\n"

    def test_plain_row_unchanged(self):
        buf, w = self._writer()
        w.writerow(["name", "value"])
        assert buf.getvalue() == "name,value\r\n"


class TestSafeDictCsvWriter:
    def _writer(self, fieldnames):
        buf = io.StringIO()
        dict_writer = csv.DictWriter(buf, fieldnames=fieldnames)
        return buf, SafeDictCsvWriter(dict_writer)

    def test_writeheader_sanitizes_field_names(self):
        buf, w = self._writer(["=evil", "safe"])
        w.writeheader()
        assert buf.getvalue() == "'=evil,safe\r\n"

    def test_writerow_sanitizes_values_keeps_keys(self):
        buf, w = self._writer(["a", "b"])
        w.writerow({"a": "=danger", "b": "fine"})
        assert buf.getvalue() == "'=danger,fine\r\n"

    def test_writerows(self):
        buf, w = self._writer(["a", "b"])
        w.writerows([{"a": "-1", "b": "x"}, {"a": "ok", "b": "@y"}])
        assert buf.getvalue() == "'-1,x\r\nok,'@y\r\n"

    def test_full_header_plus_rows(self):
        buf, w = self._writer(["name", "note"])
        w.writeheader()
        w.writerow({"name": "file.txt", "note": "=SUM(A1)"})
        assert buf.getvalue() == "name,note\r\nfile.txt,'=SUM(A1)\r\n"

    def test_non_string_value_passes_through(self):
        buf, w = self._writer(["n"])
        w.writerow({"n": 42})
        assert buf.getvalue() == "42\r\n"
