from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .detection import detect_source_type
from .models import SourceType
from .professional import load_professional_source


def load_source(source: str | Path | dict[str, Any] | list[dict[str, Any]]) -> tuple[SourceType, Any, str | None]:
    source_type = detect_source_type(source)
    original_name: str | None = None

    if isinstance(source, (str, Path)):
        path = Path(source)
        original_name = path.name
        if source_type in {"csv", "tsv"}:
            delimiter = "\t" if source_type == "tsv" else ","
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return source_type, list(csv.DictReader(handle, delimiter=delimiter)), original_name
        if source_type in {"json", "geojson"}:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            content_type = detect_source_type(data)
            if data.get("type") in {"Feature", "FeatureCollection"}:
                return "geojson", data, original_name
            if content_type in {"trajectory", "sensor-series", "geojson", "cityjson", "3d-tiles"}:
                return content_type, data, original_name
            return source_type, data, original_name
        if source_type == "wkt":
            return source_type, path.read_text(encoding="utf-8"), original_name
        if source_type == "gpx":
            return source_type, path.read_text(encoding="utf-8"), original_name
        if source_type in {"image", "video", "text", "document"}:
            return source_type, {"uri": str(path), "name": path.name}, original_name
        if source_type in {"shapefile", "geopackage", "geotiff", "point-cloud", "kml", "cityjson", "3d-tiles", "gltf"}:
            return source_type, load_professional_source(path, source_type), original_name
        raise ValueError(f"Unsupported source path type: {source_type}")

    return source_type, source, original_name


def geojson_features(data: dict[str, Any]) -> list[dict[str, Any]]:
    if data.get("type") == "FeatureCollection":
        return list(data.get("features", []))
    if data.get("type") == "Feature":
        return [data]
    if "geometry" in data:
        return [{"type": "Feature", "geometry": data["geometry"], "properties": data.get("properties", {})}]
    return []
