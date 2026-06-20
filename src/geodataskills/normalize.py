from __future__ import annotations

import time
import uuid
from collections import Counter
from typing import Any

from .coordinates import compute_bbox_from_coordinates, to_float
from .fields import FieldMapping, infer_field_mapping
from .models import (
    DataSourceMeta,
    DatasetBounds,
    DatasetStatistics,
    DatasetTimeRange,
    FieldDecision,
    RenderHint,
    SourceType,
    TransformEvent,
    TransformReport,
    UnifiedDataSet,
    UnifiedGeometry,
    UnifiedModality,
    UnifiedSemantic,
    UnifiedSpatialObject,
)
from .modality import apply_modality_bindings
from .parsers import geojson_features
from .quality import validate_object
from .rules import RuleProfile, evaluate_filter
from .schema import flatten_records, profile_records
from .timeutils import make_time
from .wkt import parse_wkt
from .gpx import parse_gpx


def normalize_loaded(
    data: Any,
    source_type: SourceType,
    *,
    original_name: str | None = None,
    coordinate_system: str | None = None,
    dataset_id: str | None = None,
    rules: RuleProfile | None = None,
) -> UnifiedDataSet:
    rules = rules or RuleProfile()
    imported_at = int(time.time() * 1000)
    source_meta = DataSourceMeta(
        source_id=dataset_id or str(uuid.uuid4()),
        source_type=source_type,
        original_name=original_name,
        coordinate_system=coordinate_system,
        imported_at=imported_at,
    )

    if source_type == "geojson":
        objects, report = normalize_geojson(data, source_meta, rules)
    elif source_type in {"csv", "tsv", "json", "api"}:
        records = coerce_records(data)
        records, nested_detected = flatten_records(records)
        schema = profile_records(records)
        schema.nested_detected = nested_detected
        mapping = infer_field_mapping(records)
        mapping, decisions = apply_field_rules(mapping, rules)
        objects, report = normalize_records(records, source_meta, mapping, rules)
        report.field_decisions.extend(decisions)
        report.schema = schema_to_dict(schema)
        if nested_detected:
            report.events.append(TransformEvent(level="info", code="nested_json_flattened", message="Nested records were flattened with dot paths"))
    elif source_type in {"trajectory", "sensor-series"}:
        objects = normalize_special_object(data, source_meta)
        report = TransformReport(input_count=1, output_count=len(objects))
    elif source_type == "wkt":
        objects = normalize_wkt(data, source_meta)
        report = TransformReport(input_count=1, output_count=len(objects))
    elif source_type == "gpx":
        objects = normalize_special_object(parse_gpx(data), source_meta)
        report = TransformReport(input_count=1, output_count=len(objects))
    elif source_type in {"image", "video", "text", "document"}:
        objects = normalize_modality_only(data, source_meta)
        report = TransformReport(input_count=1, output_count=len(objects))
    else:
        objects = []
        report = TransformReport(events=[TransformEvent(level="warning", code="unsupported_source", message=f"Unsupported source type: {source_type}")])

    if rules.modality_bindings:
        apply_modality_bindings(objects, rules.modality_bindings, report)

    for obj in objects:
        if obj.quality is None:
            obj.quality = validate_object(obj, rules)

    report.output_count = len(objects)
    report.invalid_count = sum(1 for obj in objects if obj.quality and not obj.quality.valid)
    quality_repaired = sum(1 for obj in objects if obj.quality and obj.quality.warnings and obj.quality.valid)
    report.repaired_count += quality_repaired
    return UnifiedDataSet(
        dataset_id=source_meta.source_id,
        objects=objects,
        bounds=compute_dataset_bounds(objects),
        time_range=compute_time_range(objects),
        statistics=compute_statistics(objects, report),
        report=report,
    )


def coerce_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("records", "items", "data", "features"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [data]
    return []


def schema_to_dict(schema) -> dict[str, Any]:
    return {
        "total_records": schema.total_records,
        "nested_detected": schema.nested_detected,
        "fields": [
            {
                "name": field.name,
                "kind": field.kind,
                "count": field.count,
                "missing_count": field.missing_count,
                "unique_count": field.unique_count,
                "examples": field.examples,
                "min_value": field.min_value,
                "max_value": field.max_value,
            }
            for field in schema.fields
        ],
    }


def normalize_records(
    records: list[dict[str, Any]],
    source_meta: DataSourceMeta,
    mapping: FieldMapping,
    rules: RuleProfile,
) -> tuple[list[UnifiedSpatialObject], TransformReport]:
    objects: list[UnifiedSpatialObject] = []
    report = TransformReport(input_count=len(records))
    for index, row in enumerate(records):
        if not passes_filters(row, rules):
            report.filtered_count += 1
            report.events.append(TransformEvent(level="info", code="row_filtered", message="Row filtered by rules", row_index=index))
            continue

        row = apply_defaults(row, mapping, rules, report, index)
        missing_roles = missing_required_roles(row, mapping, rules)
        if missing_roles and rules.validation.missing_policy == "drop":
            report.filtered_count += 1
            report.events.append(
                TransformEvent(level="warning", code="row_dropped_missing_required", message=f"Missing required fields: {', '.join(missing_roles)}", row_index=index)
            )
            continue

        has_xy = has_value(row, mapping.x_field) and has_value(row, mapping.y_field)
        x = to_float(row.get(mapping.x_field), 0.0) if mapping.x_field and has_value(row, mapping.x_field) else 0.0
        y = to_float(row.get(mapping.y_field), 0.0) if mapping.y_field and has_value(row, mapping.y_field) else 0.0
        z = to_float(row.get(mapping.z_field), 0.0) if mapping.z_field and has_value(row, mapping.z_field) else 0.0
        object_id = str(row.get(mapping.id_field) or f"{source_meta.source_id}-{index}")

        modality = []
        if mapping.image_field and row.get(mapping.image_field):
            modality.append(UnifiedModality(modality_type="image", uri=str(row[mapping.image_field])))
        if mapping.video_field and row.get(mapping.video_field):
            modality.append(UnifiedModality(modality_type="video", uri=str(row[mapping.video_field])))
        if mapping.text_field and row.get(mapping.text_field):
            modality.append(UnifiedModality(modality_type="text", content=str(row[mapping.text_field])))

        semantic = UnifiedSemantic(
            category=str(row.get(mapping.type_field)) if mapping.type_field and row.get(mapping.type_field) is not None else None,
            tags=[str(row[mapping.type_field])] if mapping.type_field and row.get(mapping.type_field) else [],
        )
        render = infer_render_hint(mapping)

        objects.append(
            obj := UnifiedSpatialObject(
                id=object_id,
                source=source_meta,
                geometry=UnifiedGeometry(
                    type="point" if has_xy else "unknown",
                    coordinates=[x, y, z] if has_xy else [],
                    bbox=(x, y, x, y) if has_xy else None,
                    altitude=z if has_xy else None,
                    spatial_ref=source_meta.coordinate_system,
                ),
                time=make_time(row.get(mapping.time_field)) if mapping.time_field else None,
                attributes=dict(row),
                modality=modality,
                semantic=semantic,
                render=render,
            )
        )
        obj.quality = validate_object(obj, rules)
        if missing_roles:
            obj.quality.valid = obj.quality.valid and rules.validation.allow_invalid
            obj.quality.missing_fields.extend(missing_roles)
            obj.quality.warnings.append(f"Missing required fields: {', '.join(missing_roles)}")
            obj.quality.confidence = min(obj.quality.confidence, 0.5)
            report.events.append(
                TransformEvent(level="warning", code="missing_required", message=f"Missing required fields: {', '.join(missing_roles)}", row_index=index)
            )
    return objects, report


def normalize_geojson(data: dict[str, Any], source_meta: DataSourceMeta, rules: RuleProfile | None = None) -> tuple[list[UnifiedSpatialObject], TransformReport]:
    rules = rules or RuleProfile()
    objects: list[UnifiedSpatialObject] = []
    features = geojson_features(data)
    report = TransformReport(input_count=len(features))
    for index, feature in enumerate(features):
        geometry = feature.get("geometry") or {}
        properties = dict(feature.get("properties") or {})
        if not passes_filters(properties, rules):
            report.filtered_count += 1
            report.events.append(TransformEvent(level="info", code="feature_filtered", message="Feature filtered by rules", row_index=index))
            continue
        geometry_type = map_geojson_geometry(geometry.get("type"))
        coordinates = geometry.get("coordinates", [])
        bbox = compute_bbox_from_coordinates(coordinates)
        mapping = infer_field_mapping([properties]) if properties else FieldMapping()
        mapping, decisions = apply_field_rules(mapping, rules)
        report.field_decisions.extend(decisions)
        properties = apply_defaults(properties, mapping, rules, report, index)
        objects.append(
            UnifiedSpatialObject(
                id=str(feature.get("id") or properties.get("id") or f"{source_meta.source_id}-{index}"),
                source=source_meta,
                geometry=UnifiedGeometry(
                    type=geometry_type,
                    coordinates=coordinates,
                    bbox=bbox,
                    spatial_ref=source_meta.coordinate_system or "EPSG:4326",
                ),
                time=make_time(properties.get(mapping.time_field)) if mapping.time_field else None,
                attributes=properties,
                semantic=UnifiedSemantic(
                    category=str(properties.get(mapping.type_field)) if mapping.type_field and properties.get(mapping.type_field) else None,
                    tags=[str(properties[mapping.type_field])] if mapping.type_field and properties.get(mapping.type_field) else [],
                ),
                render=infer_render_hint(mapping, geometry_type=geometry_type),
            )
        )
    return objects, report


def normalize_special_object(data: dict[str, Any], source_meta: DataSourceMeta) -> list[UnifiedSpatialObject]:
    if source_meta.source_type in {"trajectory", "gpx"}:
        points = data.get("points", [])
        coords = [[to_float(p.get("lng", p.get("x"))), to_float(p.get("lat", p.get("y"))), to_float(p.get("z"), 0.0)] for p in points]
        timestamps = [ts for p in points if (ts := make_time(p.get("time"))) and ts.timestamp is not None]
        return [
            UnifiedSpatialObject(
                id=str(data.get("trackId") or data.get("id") or source_meta.source_id),
                source=source_meta,
                geometry=UnifiedGeometry(type="trajectory", coordinates=coords, bbox=compute_bbox_from_coordinates(coords), spatial_ref="EPSG:4326"),
                time=None if not timestamps else make_time({"timestamps": [t.timestamp for t in timestamps]}),
                attributes={k: v for k, v in data.items() if k != "points"},
                render=RenderHint(preferred_geometry="path", lod_priority=8),
            )
        ]

    if source_meta.source_type == "sensor-series":
        position = data.get("position", {})
        x = to_float(position.get("lng", position.get("x")))
        y = to_float(position.get("lat", position.get("y")))
        series = data.get("series", [])
        timestamps = []
        values = []
        for item in series:
            t = make_time(item.get("time"))
            if t and t.timestamp is not None:
                timestamps.append(t.timestamp)
                values.append(to_float(item.get("value")))
        return [
            UnifiedSpatialObject(
                id=str(data.get("sensorId") or data.get("id") or source_meta.source_id),
                source=source_meta,
                geometry=UnifiedGeometry(type="point", coordinates=[x, y, 0.0], bbox=(x, y, x, y), spatial_ref="EPSG:4326"),
                time=make_time({"timestamps": timestamps, "values": values}) if timestamps else None,
                attributes={k: v for k, v in data.items() if k != "series"},
                modality=[UnifiedModality(modality_type="sensor", metadata={"series_count": len(series)})],
                render=RenderHint(preferred_geometry="column", color_field="value", height_field="value", lod_priority=7),
            )
        ]

    return []


def normalize_modality_only(data: dict[str, Any], source_meta: DataSourceMeta) -> list[UnifiedSpatialObject]:
    modality_type = source_meta.source_type if source_meta.source_type in {"image", "video", "text", "document"} else "document"
    content = data.get("content") if modality_type == "text" else None
    uri = data.get("uri")
    return [
        UnifiedSpatialObject(
            id=source_meta.source_id,
            source=source_meta,
            geometry=UnifiedGeometry(type="unknown", coordinates=[]),
            attributes=dict(data),
            modality=[UnifiedModality(modality_type=modality_type, uri=uri, content=content, metadata={k: v for k, v in data.items() if k not in {"uri", "content"}})],
            render=RenderHint(preferred_geometry="billboard" if modality_type in {"image", "video"} else "unknown"),
        )
    ]


def normalize_wkt(data: str, source_meta: DataSourceMeta) -> list[UnifiedSpatialObject]:
    geometry_type, coordinates = parse_wkt(data)
    return [
        UnifiedSpatialObject(
            id=source_meta.source_id,
            source=source_meta,
            geometry=UnifiedGeometry(
                type=geometry_type,
                coordinates=coordinates,
                bbox=compute_bbox_from_coordinates(coordinates),
                spatial_ref=source_meta.coordinate_system,
            ),
            attributes={"wkt": data.strip()},
            render=infer_render_hint(FieldMapping(), geometry_type=geometry_type),
        )
    ]


def map_geojson_geometry(value: str | None):
    mapping = {
        "Point": "point",
        "LineString": "line",
        "Polygon": "polygon",
        "MultiPoint": "multi-point",
        "MultiLineString": "multi-line",
        "MultiPolygon": "multi-polygon",
    }
    return mapping.get(value or "", "unknown")


def infer_render_hint(mapping: FieldMapping, geometry_type: str = "point") -> RenderHint:
    if geometry_type in {"line", "multi-line", "trajectory"}:
        preferred = "path"
    elif geometry_type in {"polygon", "multi-polygon"}:
        preferred = "polygon"
    elif mapping.value_field or mapping.z_field:
        preferred = "column"
    else:
        preferred = "point"
    return RenderHint(
        preferred_geometry=preferred,
        color_field=mapping.value_field or mapping.type_field,
        height_field=mapping.value_field or mapping.z_field,
        lod_priority=6 if preferred == "column" else 4,
    )


def compute_dataset_bounds(objects: list[UnifiedSpatialObject]) -> DatasetBounds | None:
    boxes = [obj.geometry.bbox or compute_bbox_from_coordinates(obj.geometry.coordinates) for obj in objects]
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        return None
    min_x = min(box[0] for box in boxes)
    min_y = min(box[1] for box in boxes)
    max_x = max(box[2] for box in boxes)
    max_y = max(box[3] for box in boxes)
    return DatasetBounds(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)


def compute_time_range(objects: list[UnifiedSpatialObject]) -> DatasetTimeRange | None:
    values: list[int] = []
    for obj in objects:
        if not obj.time:
            continue
        if obj.time.timestamp is not None:
            values.append(obj.time.timestamp)
        if obj.time.start is not None:
            values.append(obj.time.start)
        if obj.time.end is not None:
            values.append(obj.time.end)
        if obj.time.timestamps:
            values.extend(obj.time.timestamps)
    if not values:
        return None
    return DatasetTimeRange(start=min(values), end=max(values))


def compute_statistics(objects: list[UnifiedSpatialObject], report: TransformReport | None = None) -> DatasetStatistics:
    geometry_types = Counter(obj.geometry.type for obj in objects)
    source_types = Counter(obj.source.source_type for obj in objects)
    invalid = sum(1 for obj in objects if obj.quality and not obj.quality.valid)
    return DatasetStatistics(
        object_count=len(objects),
        input_count=report.input_count if report else len(objects),
        filtered_count=report.filtered_count if report else 0,
        repaired_count=report.repaired_count if report else 0,
        geometry_types=dict(geometry_types),
        source_types=dict(source_types),
        invalid_count=invalid,
    )


def apply_field_rules(mapping: FieldMapping, rules: RuleProfile) -> tuple[FieldMapping, list[FieldDecision]]:
    decisions: list[FieldDecision] = []
    role_to_attr = {
        "id": "id_field",
        "x": "x_field",
        "y": "y_field",
        "z": "z_field",
        "time": "time_field",
        "value": "value_field",
        "type": "type_field",
        "image": "image_field",
        "video": "video_field",
        "text": "text_field",
    }
    for role, attr in role_to_attr.items():
        selected = rules.fields.get(role)
        if selected:
            setattr(mapping, attr, selected)
            decisions.append(FieldDecision(role=role, field=selected, source="rule", confidence=1.0))
        else:
            inferred = getattr(mapping, attr)
            decisions.append(FieldDecision(role=role, field=inferred, source="inferred" if inferred else "missing", confidence=0.75 if inferred else 0.0))

    for role, default in rules.defaults.items():
        if role in role_to_attr and getattr(mapping, role_to_attr[role]) is None:
            virtual_field = f"__default_{role}"
            setattr(mapping, role_to_attr[role], virtual_field)
            decisions.append(FieldDecision(role=role, field=virtual_field, source="default", confidence=0.9))
    return mapping, decisions


def passes_filters(row: dict[str, Any], rules: RuleProfile) -> bool:
    return all(evaluate_filter(row, rule) for rule in rules.filters)


def apply_defaults(
    row: dict[str, Any],
    mapping: FieldMapping,
    rules: RuleProfile,
    report: TransformReport,
    row_index: int,
) -> dict[str, Any]:
    result = dict(row)
    role_to_attr = {
        "id": "id_field",
        "x": "x_field",
        "y": "y_field",
        "z": "z_field",
        "time": "time_field",
        "value": "value_field",
        "type": "type_field",
        "image": "image_field",
        "video": "video_field",
        "text": "text_field",
    }
    for key, default_value in rules.defaults.items():
        field = getattr(mapping, role_to_attr[key], None) if key in role_to_attr else key
        if field and not has_value(result, field):
            result[field] = default_value
            report.repaired_count += 1
            report.events.append(
                TransformEvent(level="info", code="default_applied", message=f"Default applied for {key}", row_index=row_index, field=field)
            )
    return result


def missing_required_roles(row: dict[str, Any], mapping: FieldMapping, rules: RuleProfile) -> list[str]:
    role_to_attr = {
        "id": "id_field",
        "x": "x_field",
        "y": "y_field",
        "z": "z_field",
        "time": "time_field",
        "value": "value_field",
        "type": "type_field",
        "image": "image_field",
        "video": "video_field",
        "text": "text_field",
    }
    missing: list[str] = []
    for role in rules.validation.required:
        field = getattr(mapping, role_to_attr.get(role, ""), None)
        if not field or not has_value(row, field):
            missing.append(role)
    return missing


def has_value(row: dict[str, Any], field: str | None) -> bool:
    return bool(field) and field in row and row.get(field) not in (None, "")
