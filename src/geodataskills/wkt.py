from __future__ import annotations

import re
from typing import Any


def parse_wkt(text: str) -> tuple[str, Any]:
    value = text.strip()
    head = value.split("(", 1)[0].strip().upper()
    body_match = re.search(r"\((.*)\)", value, flags=re.DOTALL)
    if not body_match:
        return "unknown", []
    body = body_match.group(1).strip()
    if head == "POINT":
        return "point", _parse_point(body)
    if head == "LINESTRING":
        return "line", _parse_points(body)
    if head == "POLYGON":
        rings = []
        for ring in re.findall(r"\(([^()]+)\)", body):
            rings.append(_parse_points(ring))
        if not rings:
            rings = [_parse_points(body)]
        return "polygon", rings
    return "unknown", []


def _parse_point(text: str) -> list[float]:
    parts = [part for part in re.split(r"\s+", text.strip()) if part]
    return [float(part) for part in parts]


def _parse_points(text: str) -> list[list[float]]:
    points = []
    for raw in text.split(","):
        points.append(_parse_point(raw))
    return points
