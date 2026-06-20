from __future__ import annotations

from pathlib import Path
from typing import Any

from .coordinates import to_float
from .models import TransformEvent, TransformReport, UnifiedModality, UnifiedSpatialObject
from .parsers import load_source
from .rules import ModalityBindingRule
from .timeutils import normalize_timestamp


def apply_modality_bindings(
    objects: list[UnifiedSpatialObject],
    bindings: list[ModalityBindingRule],
    report: TransformReport,
) -> None:
    for binding in bindings:
        try:
            _, data, _ = load_source(Path(binding.source))
            records = _coerce_records(data)
        except Exception as exc:
            report.events.append(
                TransformEvent(level="error", code="modality_source_failed", message=str(exc), field=binding.source)
            )
            continue

        before = sum(len(obj.modality) for obj in objects)
        if binding.method == "id":
            _bind_by_id(objects, records, binding, report)
        elif binding.method == "nearest":
            _bind_by_nearest(objects, records, binding, report)
        after = sum(len(obj.modality) for obj in objects)
        report.events.append(
            TransformEvent(
                level="info",
                code="modality_binding_applied",
                message=f"Bound {after - before} modality records from {binding.source} by {binding.method}",
            )
        )


def _coerce_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("records", "items", "data"):
            if isinstance(data.get(key), list):
                return [item for item in data[key] if isinstance(item, dict)]
        return [data]
    return []


def _bind_by_id(
    objects: list[UnifiedSpatialObject],
    records: list[dict[str, Any]],
    binding: ModalityBindingRule,
    report: TransformReport,
) -> None:
    index = {obj.attributes.get(binding.object_id_field, obj.id): obj for obj in objects}
    index.update({obj.id: obj for obj in objects})
    for row_index, row in enumerate(records):
        key = row.get(binding.modality_id_field)
        obj = index.get(key)
        if not obj:
            report.events.append(
                TransformEvent(level="warning", code="modality_unmatched", message=f"No object for modality id {key}", row_index=row_index)
            )
            continue
        obj.modality.append(_row_to_modality(row, binding))


def _bind_by_nearest(
    objects: list[UnifiedSpatialObject],
    records: list[dict[str, Any]],
    binding: ModalityBindingRule,
    report: TransformReport,
) -> None:
    if not binding.x_field or not binding.y_field:
        report.events.append(
            TransformEvent(level="error", code="modality_nearest_missing_xy", message="Nearest binding requires x_field and y_field")
        )
        return
    point_objects = [
        obj for obj in objects
        if obj.geometry.type == "point" and isinstance(obj.geometry.coordinates, list) and len(obj.geometry.coordinates) >= 2
    ]
    for row_index, row in enumerate(records):
        x = to_float(row.get(binding.x_field))
        y = to_float(row.get(binding.y_field))
        nearest = None
        nearest_dist = None
        for obj in point_objects:
            ox, oy = obj.geometry.coordinates[0], obj.geometry.coordinates[1]
            dist = ((ox - x) ** 2 + (oy - y) ** 2) ** 0.5
            if nearest_dist is None or dist < nearest_dist:
                nearest = obj
                nearest_dist = dist
        if nearest is None or (binding.max_distance is not None and nearest_dist is not None and nearest_dist > binding.max_distance):
            report.events.append(
                TransformEvent(level="warning", code="modality_unmatched_nearest", message="No nearby object for modality", row_index=row_index)
            )
            continue
        modality = _row_to_modality(row, binding)
        modality.metadata["binding_distance"] = nearest_dist
        nearest.modality.append(modality)


def _row_to_modality(row: dict[str, Any], binding: ModalityBindingRule) -> UnifiedModality:
    modality_type = row.get(binding.modality_type_field) if binding.modality_type_field else None
    if modality_type not in {"image", "video", "text", "audio", "sensor", "document"}:
        if binding.uri_field and row.get(binding.uri_field):
            uri = str(row[binding.uri_field]).lower()
            if uri.endswith((".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")):
                modality_type = "image"
            elif uri.endswith((".mp4", ".mov", ".avi", ".mkv")):
                modality_type = "video"
            else:
                modality_type = "document"
        elif binding.content_field and row.get(binding.content_field):
            modality_type = "text"
        else:
            modality_type = "document"
    timestamp = normalize_timestamp(row.get(binding.time_field)) if binding.time_field else None
    return UnifiedModality(
        modality_type=modality_type,
        uri=str(row.get(binding.uri_field)) if binding.uri_field and row.get(binding.uri_field) else None,
        content=str(row.get(binding.content_field)) if binding.content_field and row.get(binding.content_field) else None,
        timestamp=timestamp,
        metadata={key: value for key, value in row.items() if key not in {binding.uri_field, binding.content_field}},
    )
