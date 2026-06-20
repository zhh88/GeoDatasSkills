from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import UnifiedTime


def normalize_timestamp(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    if isinstance(value, int | float):
        number = float(value)
        return int(number if number > 10_000_000_000 else number * 1000)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return normalize_timestamp(int(text))
        normalized = text.replace("Z", "+00:00")
        try:
            return int(datetime.fromisoformat(normalized).timestamp() * 1000)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return int(datetime.strptime(text, fmt).replace(tzinfo=timezone.utc).timestamp() * 1000)
            except ValueError:
                continue
    return None


def make_time(value: Any) -> UnifiedTime | None:
    if isinstance(value, dict):
        if "timestamps" in value:
            timestamps = [ts for item in value["timestamps"] if (ts := normalize_timestamp(item)) is not None]
            values = value.get("values")
            return UnifiedTime(type="series", timestamps=timestamps, values=values)
        start = normalize_timestamp(value.get("start"))
        end = normalize_timestamp(value.get("end"))
        if start is not None and end is not None:
            return UnifiedTime(type="interval", start=start, end=end)

    timestamp = normalize_timestamp(value)
    if timestamp is not None:
        return UnifiedTime(type="instant", timestamp=timestamp)
    return None
