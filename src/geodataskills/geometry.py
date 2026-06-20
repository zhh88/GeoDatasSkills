from __future__ import annotations

from typing import Any

from .models import TransformEvent, TransformReport
from .rules import GeometryRules


def clean_coordinates(coordinates: Any, geometry_type: str, rules: GeometryRules, report: TransformReport | None = None) -> Any:
    if geometry_type == "line" and isinstance(coordinates, list):
        return _dedupe_points(coordinates, rules, report)
    if geometry_type == "polygon" and isinstance(coordinates, list):
        rings = []
        for ring in coordinates:
            cleaned = _dedupe_points(ring, rules, report)
            if rules.close_polygons and cleaned and cleaned[0] != cleaned[-1]:
                cleaned.append(list(cleaned[0]))
                if report:
                    report.events.append(TransformEvent(level="info", code="polygon_closed", message="Polygon ring was closed"))
            rings.append(cleaned)
        return rings
    if geometry_type == "trajectory" and isinstance(coordinates, list):
        return _dedupe_points(coordinates, rules, report)
    return coordinates


def _dedupe_points(points: list[Any], rules: GeometryRules, report: TransformReport | None = None) -> list[Any]:
    if not rules.remove_duplicate_points:
        return points
    deduped = []
    previous = object()
    removed = 0
    for point in points:
        if point == previous:
            removed += 1
            continue
        deduped.append(point)
        previous = point
    if removed and report:
        report.events.append(TransformEvent(level="info", code="duplicate_points_removed", message=f"Removed {removed} duplicate points"))
    return deduped
