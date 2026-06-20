from __future__ import annotations

from dataclasses import dataclass
from typing import Any


FIELD_ALIASES: dict[str, list[str]] = {
    "id": ["id", "objectid", "object_id", "fid", "uid", "编号"],
    "x": ["x", "lng", "lon", "longitude", "经度"],
    "y": ["y", "lat", "latitude", "纬度"],
    "z": ["z", "height", "altitude", "elevation", "高程", "高度"],
    "time": ["time", "timestamp", "datetime", "date", "采集时间", "时间"],
    "value": ["value", "count", "density", "risk", "intensity", "score", "数值", "风险"],
    "type": ["type", "category", "class", "kind", "分类", "类型"],
    "image": ["image", "img", "photo", "picture", "图片", "照片"],
    "video": ["video", "clip", "视频"],
    "text": ["text", "desc", "description", "note", "content", "文本", "说明", "描述"],
}


@dataclass(slots=True)
class FieldMapping:
    id_field: str | None = None
    x_field: str | None = None
    y_field: str | None = None
    z_field: str | None = None
    time_field: str | None = None
    value_field: str | None = None
    type_field: str | None = None
    image_field: str | None = None
    video_field: str | None = None
    text_field: str | None = None


def infer_field_mapping(records: list[dict[str, Any]]) -> FieldMapping:
    fields = list(records[0].keys()) if records else []

    def match(kind: str) -> str | None:
        aliases = FIELD_ALIASES[kind]
        lower = {field.lower(): field for field in fields}
        for alias in aliases:
            if alias.lower() in lower:
                return lower[alias.lower()]
        for field in fields:
            normalized = field.lower()
            if any(alias.lower() in normalized for alias in aliases):
                return field
        return None

    mapping = FieldMapping(
        id_field=match("id"),
        x_field=match("x"),
        y_field=match("y"),
        z_field=match("z"),
        time_field=match("time"),
        value_field=match("value"),
        type_field=match("type"),
        image_field=match("image"),
        video_field=match("video"),
        text_field=match("text"),
    )

    if not mapping.x_field or not mapping.y_field:
        inferred = infer_coordinate_fields_by_values(records)
        mapping.x_field = mapping.x_field or inferred[0]
        mapping.y_field = mapping.y_field or inferred[1]

    return mapping


def infer_coordinate_fields_by_values(records: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    if not records:
        return None, None

    numeric_fields: dict[str, list[float]] = {}
    sample = records[: min(len(records), 100)]
    for row in sample:
        for key, value in row.items():
            try:
                numeric_fields.setdefault(key, []).append(float(value))
            except (TypeError, ValueError):
                continue

    lng_candidates: list[str] = []
    lat_candidates: list[str] = []
    for key, values in numeric_fields.items():
        if len(values) < max(2, len(sample) // 3):
            continue
        if all(-180 <= value <= 180 for value in values):
            lng_candidates.append(key)
        if all(-90 <= value <= 90 for value in values):
            lat_candidates.append(key)

    if len(lng_candidates) >= 2:
        return lng_candidates[0], lng_candidates[1]
    if lng_candidates and lat_candidates:
        return lng_candidates[0], lat_candidates[-1]
    return None, None
