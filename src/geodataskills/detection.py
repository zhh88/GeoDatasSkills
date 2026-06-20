from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import SourceType


def detect_source_type(source: str | Path | Any) -> SourceType:
    if isinstance(source, (str, Path)):
        path = Path(source)
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return "csv"
        if suffix == ".tsv":
            return "tsv"
        if suffix in {".geojson"}:
            return "geojson"
        if suffix == ".json":
            return "json"
        if suffix == ".wkt":
            return "wkt"
        if suffix == ".gpx":
            return "gpx"
        if suffix == ".shp":
            return "shapefile"
        if suffix == ".gpkg":
            return "geopackage"
        if suffix in {".kml", ".kmz"}:
            return "kml"
        if suffix in {".tif", ".tiff", ".geotiff"}:
            return "geotiff"
        if suffix in {".las", ".laz", ".ply", ".pcd"}:
            return "point-cloud"
        if suffix in {".glb", ".gltf"}:
            return "gltf"
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}:
            return "image"
        if suffix in {".mp4", ".mov", ".avi", ".mkv"}:
            return "video"
        if suffix in {".txt", ".md"}:
            return "text"
        return "unknown"

    if isinstance(source, dict):
        source_type = source.get("type")
        if source_type in {"Feature", "FeatureCollection"}:
            return "geojson"
        if source_type == "CityJSON" or "CityObjects" in source:
            return "cityjson"
        if "asset" in source and "geometricError" in source and "root" in source:
            return "3d-tiles"
        if "points" in source and isinstance(source["points"], list):
            return "trajectory"
        if "series" in source and isinstance(source["series"], list):
            return "sensor-series"
        if "geometry" in source:
            return "geojson"
        return "json"

    if isinstance(source, list):
        return "json"

    return "unknown"
