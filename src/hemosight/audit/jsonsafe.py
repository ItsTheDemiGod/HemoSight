"""Coercion of analysis payloads into things JSON can actually hold.

WHY THIS EXISTS. Every check in this package computes with NumPy and pandas, and both
hand back types that look like Python natives and are not: `numpy.bool_` is not a
subclass of `bool`, `numpy.float64` survives `round()` as `numpy.float64`, and an
`ndarray` is not a list. None of them are JSON-serialisable, and the failure surfaces
far from its cause - as a 500 from an HTTP endpoint, with a final line reading
"Object of type bool is not JSON serializable", which is about as unhelpful as an error
message gets.

NaN and Infinity are the second half of the problem and fail more quietly. Python's
`json.dumps` emits them as the bare tokens `NaN` and `Infinity` WITHOUT raising, which
is not valid JSON: SQLite stores the text and Python reads it back, so the defect is
invisible until a PostgreSQL `json` column or a non-Python client rejects it. This
project's service is declared PostgreSQL-ready, so they are coerced to null here rather
than left to fail after a migration.

Use this at the boundary - where a payload leaves the analysis and enters storage or the
wire - never at individual call sites. A per-field fix moves the bug to the next field
somebody adds.
"""

from __future__ import annotations

import datetime as _dt
import math
from decimal import Decimal
from pathlib import Path, PurePath
from typing import Any

import numpy as np


def _clean_float(v: float) -> float | None:
    """NaN and +/-Inf become None; every other float passes through."""
    return None if (math.isnan(v) or math.isinf(v)) else v


def to_jsonable(obj: Any) -> Any:
    """Return a structure built only from str, int, float, bool, None, list and dict.

    Recursive, and total: anything it does not recognise is stringified rather than
    raising, because the job of this function is to make a payload storable, and a
    surprising string in one field is a better outcome than a 500 that loses the whole
    audit.
    """
    # None first - cheapest and most common.
    if obj is None:
        return None

    # bool BEFORE int: bool is a subclass of int, and testing int first would turn
    # True into 1.
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        return _clean_float(obj)
    if isinstance(obj, str):
        return obj

    # NumPy scalars: .item() yields the Python native, which is then re-checked so a
    # numpy.float64 holding NaN still becomes None.
    if isinstance(obj, np.generic):
        return to_jsonable(obj.item())
    if isinstance(obj, np.ndarray):
        return [to_jsonable(x) for x in obj.tolist()]

    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [to_jsonable(x) for x in obj]

    if isinstance(obj, Decimal):
        return _clean_float(float(obj))
    if isinstance(obj, (PurePath, Path)):
        return str(obj)
    if isinstance(obj, (_dt.datetime, _dt.date, _dt.time)):
        return obj.isoformat()
    if isinstance(obj, _dt.timedelta):
        return obj.total_seconds()
    if isinstance(obj, (bytes, bytearray)):
        return obj.decode("utf-8", errors="replace")

    # pandas, imported lazily so this module stays usable without it.
    try:
        import pandas as pd
    except ImportError:                                  # pragma: no cover
        pd = None
    if pd is not None:
        if obj is getattr(pd, "NaT", object()):
            return None
        if isinstance(obj, pd.Timestamp):
            return None if pd.isna(obj) else obj.isoformat()
        if isinstance(obj, pd.Series):
            return [to_jsonable(x) for x in obj.tolist()]
        if isinstance(obj, pd.Index):
            return [to_jsonable(x) for x in obj.tolist()]
        if isinstance(obj, pd.DataFrame):
            return [to_jsonable(r) for r in obj.to_dict(orient="records")]

    return str(obj)
