"""Deterministic helpers for feature construction."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import math
import pandas as pd

from app.services.features.constants import UNKNOWN_CATEGORY


def as_datetime(value: Any) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    ts = parsed.to_pydatetime()
    return ts.replace(tzinfo=None) if getattr(ts, "tzinfo", None) else ts


def to_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return float(value)
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def to_int(value: Any, default: int | None = None) -> int | None:
    number = to_float(value, default=None)
    if number is None:
        return default
    return int(number)


def normalize_category(value: Any) -> str:
    if value is None:
        return UNKNOWN_CATEGORY
    try:
        if pd.isna(value):
            return UNKNOWN_CATEGORY
    except TypeError:
        pass
    text = str(value).strip().lower()
    if text in {"", "nan", "none", "null"}:
        return UNKNOWN_CATEGORY
    return text


def days_between(later: datetime | None, earlier: datetime | None) -> float | None:
    if later is None or earlier is None:
        return None
    return max((later - earlier).total_seconds() / 86400.0, 0.0)


def ordered_frame(rows: list[dict[str, Any]], columns: tuple[str, ...]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for column in columns:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame.loc[:, list(columns)]
