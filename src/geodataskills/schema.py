from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


FieldKind = Literal["number", "string", "boolean", "time", "uri", "object", "array", "null", "mixed"]


@dataclass(slots=True)
class FieldProfile:
    name: str
    kind: FieldKind
    count: int = 0
    missing_count: int = 0
    unique_count: int = 0
    examples: list[Any] = field(default_factory=list)
    min_value: float | None = None
    max_value: float | None = None


@dataclass(slots=True)
class SchemaProfile:
    total_records: int
    fields: list[FieldProfile] = field(default_factory=list)
    nested_detected: bool = False


def flatten_record(record: dict[str, Any], *, separator: str = ".", max_depth: int = 6) -> dict[str, Any]:
    flattened: dict[str, Any] = {}

    def walk(prefix: str, value: Any, depth: int) -> None:
        if depth > max_depth:
            flattened[prefix] = value
            return
        if isinstance(value, dict):
            if not value:
                flattened[prefix] = value
            for key, child in value.items():
                next_key = f"{prefix}{separator}{key}" if prefix else str(key)
                walk(next_key, child, depth + 1)
            return
        flattened[prefix] = value

    walk("", record, 0)
    return flattened


def flatten_records(records: list[dict[str, Any]], *, separator: str = ".") -> tuple[list[dict[str, Any]], bool]:
    nested = any(any(isinstance(value, dict) for value in row.values()) for row in records)
    if not nested:
        return records, False
    return [flatten_record(row, separator=separator) for row in records], True


def profile_records(records: list[dict[str, Any]], *, sample_size: int = 200) -> SchemaProfile:
    sample = records[:sample_size]
    all_fields = sorted({key for row in sample for key in row})
    profiles: list[FieldProfile] = []

    for field in all_fields:
        values = [row.get(field) for row in sample]
        present = [value for value in values if value not in (None, "")]
        kinds = {_kind(value) for value in present}
        kind: FieldKind
        if not kinds:
            kind = "null"
        elif len(kinds) == 1:
            kind = next(iter(kinds))
        elif kinds <= {"number", "string"} and _mostly_numeric_strings(present):
            kind = "number"
        else:
            kind = "mixed"

        numeric_values = [_to_float(value) for value in present]
        numeric_values = [value for value in numeric_values if value is not None]
        examples = []
        for value in present:
            if value not in examples:
                examples.append(value)
            if len(examples) >= 3:
                break

        profiles.append(
            FieldProfile(
                name=field,
                kind=kind,
                count=len(present),
                missing_count=len(values) - len(present),
                unique_count=len({str(value) for value in present}),
                examples=examples,
                min_value=min(numeric_values) if numeric_values else None,
                max_value=max(numeric_values) if numeric_values else None,
            )
        )

    return SchemaProfile(total_records=len(records), fields=profiles, nested_detected=False)


def _kind(value: Any) -> FieldKind:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        text = value.strip()
        if _to_float(text) is not None:
            return "number"
        if "://" in text or text.lower().startswith(("data:", "file:")):
            return "uri"
        if any(mark in text for mark in ("-", "/", "T", ":")) and len(text) >= 8:
            return "time"
        return "string"
    return "mixed"


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mostly_numeric_strings(values: list[Any]) -> bool:
    if not values:
        return False
    numeric = sum(1 for value in values if _to_float(value) is not None)
    return numeric / len(values) >= 0.8
