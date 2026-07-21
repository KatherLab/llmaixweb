# backend/tests/test_json_utils.py
"""Pure-unit tests for backend/src/utils/json_utils.py.

These are logic-only helpers (no DB / network), so no fixtures or mocking.
Focus: NUL stripping, pandas/numpy coercion, datetime isoformat, recursive
containers, the numeric ``obj + 0`` fallback, and the final ``str()`` fallback.
"""

import math
from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from backend.src.utils.json_utils import case_id_str, make_jsonable, strip_nul


class TestStripNul:
    def test_removes_nul_bytes(self):
        assert strip_nul("a\x00b\x00c") == "abc"

    def test_no_nul_unchanged(self):
        assert strip_nul("hello") == "hello"

    def test_empty(self):
        assert strip_nul("") == ""

    def test_only_nul(self):
        assert strip_nul("\x00\x00") == ""


class TestCaseIdStr:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (3.0, "3"),  # whole-number float -> int rendering
            (123.0, "123"),
            (-4.0, "-4"),
            (0.0, "0"),
            (-0.0, "0"),  # negative zero collapses to "0"
            (3.5, "3.5"),  # fractional stays as-is
            (123, "123"),  # plain int
            ("abc", "abc"),
            ("  spaced  ", "spaced"),
            ("id\x00x", "idx"),  # NUL stripped
            (True, "True"),  # bool is not float-integer branch
        ],
    )
    def test_values(self, value, expected):
        assert case_id_str(value) == expected

    def test_nul_and_trim_combined(self):
        assert case_id_str("  a\x00b  ") == "ab"

    # ------------------------------------------------------------------
    # Missing values (None / NaN / NaT) normalize to "" rather than leaking a
    # literal "None"/"nan" key — otherwise two missing ids would collide on
    # that literal and spuriously match in evaluation. (Guards the fix in
    # json_utils.case_id_str.)
    # ------------------------------------------------------------------
    def test_none_normalizes_to_empty(self):
        assert case_id_str(None) == ""

    def test_nan_normalizes_to_empty(self):
        assert case_id_str(float("nan")) == ""

    def test_pandas_na_and_nat_normalize_to_empty(self):
        import pandas as pd

        assert case_id_str(pd.NA) == ""
        assert case_id_str(pd.NaT) == ""


class TestMakeJsonableScalars:
    def test_none(self):
        assert make_jsonable(None) is None

    def test_plain_str_passes_through(self):
        assert make_jsonable("hello") == "hello"

    def test_str_nul_stripped(self):
        assert make_jsonable("a\x00b") == "ab"

    def test_python_nan_becomes_none(self):
        # pd.isna catches a plain float nan first.
        assert make_jsonable(math.nan) is None

    def test_pandas_nat_becomes_none(self):
        assert make_jsonable(pd.NaT) is None

    def test_pandas_na_becomes_none(self):
        assert make_jsonable(pd.NA) is None

    def test_plain_int_passes_through(self):
        # Not caught by any earlier branch; survives the `obj + 0` fast path.
        result = make_jsonable(5)
        assert result == 5 and isinstance(result, int)

    def test_plain_float_passes_through(self):
        result = make_jsonable(2.5)
        assert result == 2.5 and isinstance(result, float)

    def test_plain_bool_passes_through(self):
        result = make_jsonable(True)
        assert result is True

    def test_zero_passes_through(self):
        # `obj + 0` == 0 is falsy but the function returns obj, not the sum.
        assert make_jsonable(0) == 0


class TestMakeJsonableNumpy:
    def test_numpy_integer(self):
        result = make_jsonable(np.int64(42))
        assert (
            result == 42
            and isinstance(result, int)
            and not isinstance(result, np.integer)
        )

    def test_numpy_float(self):
        result = make_jsonable(np.float64(3.5))
        assert (
            result == 3.5
            and isinstance(result, float)
            and not isinstance(result, np.floating)
        )

    def test_numpy_float_nan_becomes_none(self):
        # pd.isna handles this before the np.floating branch, but result is None.
        assert make_jsonable(np.float64("nan")) is None

    def test_numpy_bool(self):
        result = make_jsonable(np.bool_(True))
        assert result is True and isinstance(result, bool)

    def test_numpy_bool_false(self):
        assert make_jsonable(np.bool_(False)) is False


class TestMakeJsonableDatetime:
    def test_pandas_timestamp(self):
        ts = pd.Timestamp("2024-01-02T03:04:05")
        assert make_jsonable(ts) == ts.isoformat()

    def test_python_datetime(self):
        dt = datetime(2024, 1, 2, 3, 4, 5)
        assert make_jsonable(dt) == "2024-01-02T03:04:05"

    def test_python_date(self):
        assert make_jsonable(date(2024, 1, 2)) == "2024-01-02"


class TestMakeJsonableContainers:
    def test_dict_recurses_and_strips_key_nul(self):
        out = make_jsonable({"a\x00b": np.int64(1), "c": "d\x00e"})
        assert out == {"ab": 1, "c": "de"}

    def test_dict_non_string_key_stringified(self):
        out = make_jsonable({1: "x", 2.0: "y"})
        # keys are str()'d (NUL-stripped)
        assert out == {"1": "x", "2.0": "y"}

    def test_list_recurses(self):
        assert make_jsonable([np.int64(1), "a\x00", None]) == [1, "a", None]

    def test_tuple_becomes_list(self):
        result = make_jsonable((1, 2, 3))
        assert result == [1, 2, 3] and isinstance(result, list)

    def test_set_becomes_list(self):
        result = make_jsonable({7})
        assert result == [7] and isinstance(result, list)

    def test_nested_structure(self):
        payload = {
            "vals": [np.int64(1), {"ts": pd.Timestamp("2024-01-01")}],
            "flag": np.bool_(False),
            "missing": pd.NaT,
        }
        assert make_jsonable(payload) == {
            "vals": [1, {"ts": pd.Timestamp("2024-01-01").isoformat()}],
            "flag": False,
            "missing": None,
        }


class TestMakeJsonableFallback:
    def test_non_numeric_object_becomes_str(self):
        class Weird:
            def __str__(self):
                return "weird\x00repr"

        # obj + 0 raises -> str() fallback, then NUL stripped.
        assert make_jsonable(Weird()) == "weirdrepr"

    def test_bytes_falls_through_to_str(self):
        # bytes + 0 raises TypeError -> str(b'x') == "b'x'".
        assert make_jsonable(b"x") == "b'x'"

    def test_object_with_working_add_returns_itself(self):
        # An exotic numeric-like that supports + 0 is returned as-is (NOT
        # JSON-native). Documents a latent surprise for e.g. Decimal/complex.
        import decimal

        d = decimal.Decimal("1.5")
        result = make_jsonable(d)
        assert result == d and isinstance(result, decimal.Decimal)
