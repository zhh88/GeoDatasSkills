from __future__ import annotations

import math
from typing import Iterable


def to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def lnglat_to_local(
    lng: float,
    lat: float,
    origin_lng: float,
    origin_lat: float,
    z: float = 0.0,
) -> tuple[float, float, float]:
    earth_radius = 6_378_137
    x = (lng - origin_lng) * math.pi / 180 * earth_radius * math.cos(origin_lat * math.pi / 180)
    y = (lat - origin_lat) * math.pi / 180 * earth_radius
    return x, y, z


def is_lnglat(x: float, y: float) -> bool:
    return -180 <= x <= 180 and -90 <= y <= 90


def compute_bbox_from_coordinates(coordinates: object) -> tuple[float, float, float, float] | None:
    points = list(flatten_points(coordinates))
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def flatten_points(coordinates: object) -> Iterable[tuple[float, float, float | None]]:
    if not isinstance(coordinates, list | tuple):
        return
    if len(coordinates) >= 2 and all(isinstance(v, int | float) for v in coordinates[:2]):
        z = float(coordinates[2]) if len(coordinates) > 2 and isinstance(coordinates[2], int | float) else None
        yield float(coordinates[0]), float(coordinates[1]), z
        return
    for item in coordinates:
        yield from flatten_points(item)
