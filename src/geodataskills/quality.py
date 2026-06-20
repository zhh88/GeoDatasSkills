from __future__ import annotations

from .coordinates import compute_bbox_from_coordinates
from .models import DataQuality, UnifiedSpatialObject


def validate_object(obj: UnifiedSpatialObject) -> DataQuality:
    warnings: list[str] = []
    missing: list[str] = []

    coordinate_valid = compute_bbox_from_coordinates(obj.geometry.coordinates) is not None
    if not coordinate_valid:
        missing.append("geometry.coordinates")
        warnings.append("空间坐标缺失或格式不合法")

    time_valid = obj.time is None or (
        (obj.time.type == "instant" and obj.time.timestamp is not None)
        or (obj.time.type == "interval" and obj.time.start is not None and obj.time.end is not None)
        or (obj.time.type == "series" and bool(obj.time.timestamps))
    )
    if not time_valid:
        warnings.append("时间字段格式不合法")

    confidence = 1.0
    if warnings:
        confidence -= min(0.6, len(warnings) * 0.2)

    return DataQuality(
        valid=coordinate_valid and time_valid,
        missing_fields=missing,
        coordinate_valid=coordinate_valid,
        time_valid=time_valid,
        confidence=round(confidence, 2),
        warnings=warnings,
    )
