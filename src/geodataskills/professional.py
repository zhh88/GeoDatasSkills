from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


OPTIONAL_DEPENDENCIES = {
    "shapefile": ["geopandas", "fiona", "pyshp"],
    "geopackage": ["geopandas", "fiona"],
    "geotiff": ["rasterio"],
    "point-cloud": ["laspy"],
    "kml": ["fastkml"],
    "cityjson": [],
    "3d-tiles": [],
    "gltf": [],
}


def dependency_status(source_type: str) -> dict[str, Any]:
    deps = OPTIONAL_DEPENDENCIES.get(source_type, [])
    return {
        "source_type": source_type,
        "dependencies": [
            {"name": dep, "available": importlib.util.find_spec(dep) is not None}
            for dep in deps
        ],
    }


def load_professional_source(path: Path, source_type: str) -> Any:
    if source_type in {"cityjson", "3d-tiles", "gltf"}:
        return _load_metadata_or_json(path, source_type)

    status = dependency_status(source_type)
    available = [dep["name"] for dep in status["dependencies"] if dep["available"]]
    if not available:
        return {
            "source_type": source_type,
            "uri": str(path),
            "name": path.name,
            "adapter_status": "metadata-only",
            "dependency_status": status,
            "suggestions": _install_suggestions(source_type),
            "note": f"{source_type} detected; install optional dependencies to enable deep conversion.",
        }
    return {
        "source_type": source_type,
        "uri": str(path),
        "name": path.name,
        "adapter_status": "dependency-detected",
        "dependency_status": status,
        "suggestions": [
            "Use GeoJSON/WKT export as an interchange format for now.",
            "Next step: implement a geopandas/rasterio/laspy backed adapter in this module.",
        ],
        "note": f"{source_type} dependency detected; deep conversion adapter is ready to be implemented.",
    }


def _load_metadata_or_json(path: Path, source_type: str) -> dict[str, Any]:
    import json

    if path.suffix.lower() in {".json", ".gltf"}:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return {"source_type": source_type, "metadata": data}
    return {
        "source_type": source_type,
        "uri": str(path),
        "name": path.name,
        "note": "Binary model registered as metadata-only asset.",
    }


def _install_suggestions(source_type: str) -> list[str]:
    if source_type == "shapefile":
        return ["pip install geopandas", "pip install pyshp"]
    if source_type == "geopackage":
        return ["pip install geopandas"]
    if source_type == "geotiff":
        return ["pip install rasterio"]
    if source_type == "point-cloud":
        return ["pip install laspy"]
    if source_type == "kml":
        return ["pip install fastkml"]
    return []
