# backend/src/utils/json_utils.py
import math
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


def make_jsonable(obj: Any) -> Any:
    """Recursively convert Pandas/NumPy/Datetime types to JSON-serializable primitives."""
    # Scalars first
    if obj is None:
        return None

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
        return {str(k): make_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [make_jsonable(v) for v in obj]

    # fall back to string for exotic objects (rare)
    try:
        # primitive (str/int/float/bool) pass through
        _ = obj + 0  # quick path for numbers, will raise for non-numbers
        return obj
    except Exception:
        pass
    return obj
