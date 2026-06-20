from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


def parse_gpx(text: str) -> dict[str, Any]:
    root = ET.fromstring(text)
    points = []
    for elem in root.iter():
        if _strip_ns(elem.tag) not in {"trkpt", "rtept", "wpt"}:
            continue
        lat = elem.attrib.get("lat")
        lon = elem.attrib.get("lon")
        if lat is None or lon is None:
            continue
        point: dict[str, Any] = {"lng": float(lon), "lat": float(lat)}
        for child in elem:
            name = _strip_ns(child.tag)
            if name == "ele" and child.text:
                point["z"] = float(child.text)
            if name == "time" and child.text:
                point["time"] = child.text
        points.append(point)
    return {"trackId": "gpx-track", "points": points}


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag
