from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import UnifiedDataSet
from .rules import OutputRules


def dataset_to_dict(dataset: UnifiedDataSet, output: OutputRules | None = None) -> dict[str, Any]:
    output = output or OutputRules()
    raw = asdict(dataset)

    if not output.include_report:
        raw.pop("report", None)

    if output.mode == "compact":
        raw = _compact_dataset(raw)
    elif output.mode == "debug":
        raw["debug"] = {
            "object_ids": [obj.get("id") for obj in raw.get("objects", [])],
            "quality_warnings": [
                {
                    "id": obj.get("id"),
                    "warnings": ((obj.get("quality") or {}).get("warnings") or []),
                }
                for obj in raw.get("objects", [])
                if ((obj.get("quality") or {}).get("warnings") or [])
            ],
        }

    if output.summary:
        raw["summary"] = _summary(raw)

    if not output.include_raw_attributes:
        for obj in raw.get("objects", []):
            obj.pop("attributes", None)

    if output.drop_empty:
        raw = drop_empty(raw)

    return raw


def drop_empty(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {
            key: drop_empty(item)
            for key, item in value.items()
            if item is not None and item != [] and item != {}
        }
        return {key: item for key, item in cleaned.items() if item is not None and item != [] and item != {}}
    if isinstance(value, list):
        return [drop_empty(item) for item in value if item is not None and item != [] and item != {}]
    return value


def _compact_dataset(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_id": raw.get("dataset_id"),
        "objects": [
            {
                "id": obj.get("id"),
                "geometry": obj.get("geometry"),
                "time": obj.get("time"),
                "attributes": obj.get("attributes"),
                "render": obj.get("render"),
                "quality": obj.get("quality"),
            }
            for obj in raw.get("objects", [])
        ],
        "bounds": raw.get("bounds"),
        "time_range": raw.get("time_range"),
        "statistics": raw.get("statistics"),
        "report": raw.get("report"),
    }


def _summary(raw: dict[str, Any]) -> dict[str, Any]:
    statistics = raw.get("statistics") or {}
    report = raw.get("report") or {}
    objects = raw.get("objects") or []
    modality_count = sum(len(obj.get("modality") or []) for obj in objects)
    warning_count = sum(len((obj.get("quality") or {}).get("warnings") or []) for obj in objects)
    field_map = {
        item.get("role"): {
            "field": item.get("field"),
            "source": item.get("source"),
            "confidence": item.get("confidence"),
        }
        for item in report.get("field_decisions") or []
        if item.get("role")
    }
    return {
        "object_count": statistics.get("object_count", len(objects)),
        "input_count": statistics.get("input_count"),
        "filtered_count": statistics.get("filtered_count"),
        "invalid_count": statistics.get("invalid_count"),
        "repaired_count": statistics.get("repaired_count"),
        "modality_count": modality_count,
        "quality_warning_count": warning_count,
        "field_map": field_map,
    }
