from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import UnifiedDataSet, UnifiedModality, UnifiedSpatialObject
from .normalize import normalize_loaded
from .parsers import load_source


class GeoDataIngestionSkill:
    """Convert heterogeneous spatial, multimodal, and spatiotemporal sources
    into a unified browser-ready data model.
    """

    def ingest(
        self,
        source: str | Path | dict[str, Any] | list[dict[str, Any]],
        *,
        coordinate_system: str | None = None,
        dataset_id: str | None = None,
    ) -> UnifiedDataSet:
        source_type, data, original_name = load_source(source)
        return normalize_loaded(
            data,
            source_type,
            original_name=original_name,
            coordinate_system=coordinate_system,
            dataset_id=dataset_id,
        )

    def attach_modality(
        self,
        obj: UnifiedSpatialObject,
        modality: UnifiedModality,
    ) -> UnifiedSpatialObject:
        obj.modality.append(modality)
        return obj

    def export_json(self, dataset: UnifiedDataSet, path: str | Path, *, pretty: bool = True) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            json.dump(dataset.to_dict(), handle, ensure_ascii=False, indent=2 if pretty else None)
