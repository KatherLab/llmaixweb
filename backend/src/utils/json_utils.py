# backend/src/utils/json_utils.py
import math
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


def strip_nul(value: str) -> str:
    """Remove NUL bytes — PostgreSQL rejects them in text/varchar columns."""
    return value.replace("\x00", "")


def case_id_str(value: Any) -> str:
    """Normalize a case/document ID cell to a stable string.

    pandas reads integer ID columns that contain blanks as floats, so a case
    ID of 123 arrives as 123.0 — ``str()`` would produce "123.0" and break
    matching. Whole-number floats are rendered as ints; everything else is
    str()'d, NUL-stripped, and whitespace-trimmed.

    Shared by preprocessing (document naming) and ground-truth parsing so
    both sides produce identical keys and evaluation matching works.
    """
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return strip_nul(str(value)).strip()


def make_jsonable(obj: Any) -> Any:
    """Recursively convert Pandas/NumPy/Datetime types to JSON-serializable primitives."""
    # Scalars first
    if obj is None:
        return None

    # Strings pass through, minus NUL bytes (PostgreSQL rejects the NUL
    # escape in JSONB and NUL bytes in text columns).
    if isinstance(obj, str):
        return strip_nul(obj)

    # pandas NA/NaT / numpy nan
    try:
        if pd.isna(obj):  # handles NaN, NaT, pd.NA
            return None
    except Exception:
        pass

    # numpy scalar types
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        val = float(obj)
        return None if math.isnan(val) else val
    if isinstance(obj, (np.bool_,)):
        return bool(obj)

    # pandas timestamp / python datetime / date
    if isinstance(obj, (pd.Timestamp, datetime, date)):
        # ISO 8601 string keeps it simple for storage; comparison converts back later
        return obj.isoformat()

    # containers
    if isinstance(obj, dict):
        return {strip_nul(str(k)): make_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [make_jsonable(v) for v in obj]

    # fall back to string for exotic objects (rare)
    try:
        # primitive (int/float/bool) pass through; str raises here and is
        # handled by the fallback below.
        _ = obj + 0  # quick path for numbers, will raise for non-numbers
        return obj
    except Exception:
        pass
    return strip_nul(str(obj))
