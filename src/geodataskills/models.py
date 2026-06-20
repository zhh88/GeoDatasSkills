from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


SourceType = Literal[
    "csv",
    "tsv",
    "json",
    "geojson",
    "point-cloud",
    "trajectory",
    "sensor-series",
    "image",
    "video",
    "text",
    "document",
    "api",
    "wkt",
    "gpx",
    "unknown",
]

GeometryType = Literal[
    "point",
    "line",
    "polygon",
    "multi-point",
    "multi-line",
    "multi-polygon",
    "volume",
    "voxel",
    "mesh",
    "trajectory",
    "unknown",
]

TimeType = Literal["instant", "interval", "series"]
ModalityType = Literal["image", "video", "text", "audio", "sensor", "document"]
RenderGeometry = Literal[
    "point",
    "column",
    "heatmap",
    "path",
    "polygon",
    "mesh",
    "voxel",
    "billboard",
    "unknown",
]


@dataclass(slots=True)
class DataSourceMeta:
    source_id: str
    source_type: SourceType
    original_name: str | None = None
    coordinate_system: str | None = None
    imported_at: int | None = None


@dataclass(slots=True)
class UnifiedGeometry:
    type: GeometryType
    coordinates: Any
    bbox: tuple[float, float, float, float] | None = None
    altitude: float | None = None
    spatial_ref: str | None = None


@dataclass(slots=True)
class UnifiedTime:
    type: TimeType
    timestamp: int | None = None
    start: int | None = None
    end: int | None = None
    timestamps: list[int] | None = None
    values: list[float] | None = None


@dataclass(slots=True)
class UnifiedModality:
    modality_type: ModalityType
    uri: str | None = None
    content: str | None = None
    embedding: list[float] | None = None
    timestamp: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UnifiedSemantic:
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    confidence: float | None = None
    relation_ids: list[str] = field(default_factory=list)
    event_type: str | None = None


@dataclass(slots=True)
class RenderHint:
    preferred_geometry: RenderGeometry = "unknown"
    color_field: str | None = None
    height_field: str | None = None
    size_field: str | None = None
    opacity_field: str | None = None
    lod_priority: int | None = None


@dataclass(slots=True)
class DataQuality:
    valid: bool
    missing_fields: list[str] = field(default_factory=list)
    coordinate_valid: bool = True
    time_valid: bool = True
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UnifiedSpatialObject:
    id: str
    source: DataSourceMeta
    geometry: UnifiedGeometry
    attributes: dict[str, Any] = field(default_factory=dict)
    time: UnifiedTime | None = None
    modality: list[UnifiedModality] = field(default_factory=list)
    semantic: UnifiedSemantic | None = None
    render: RenderHint | None = None
    quality: DataQuality | None = None


@dataclass(slots=True)
class DatasetBounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    min_z: float | None = None
    max_z: float | None = None


@dataclass(slots=True)
class DatasetTimeRange:
    start: int
    end: int


@dataclass(slots=True)
class DatasetStatistics:
    object_count: int
    input_count: int = 0
    filtered_count: int = 0
    repaired_count: int = 0
    geometry_types: dict[str, int] = field(default_factory=dict)
    source_types: dict[str, int] = field(default_factory=dict)
    invalid_count: int = 0


@dataclass(slots=True)
class TransformEvent:
    level: Literal["info", "warning", "error"]
    code: str
    message: str
    row_index: int | None = None
    field: str | None = None


@dataclass(slots=True)
class FieldDecision:
    role: str
    field: str | None
    source: Literal["rule", "inferred", "default", "missing"]
    confidence: float = 1.0


@dataclass(slots=True)
class TransformReport:
    input_count: int = 0
    output_count: int = 0
    filtered_count: int = 0
    invalid_count: int = 0
    repaired_count: int = 0
    schema: dict[str, Any] | None = None
    field_decisions: list[FieldDecision] = field(default_factory=list)
    events: list[TransformEvent] = field(default_factory=list)


@dataclass(slots=True)
class UnifiedDataSet:
    dataset_id: str
    objects: list[UnifiedSpatialObject]
    bounds: DatasetBounds | None = None
    time_range: DatasetTimeRange | None = None
    statistics: DatasetStatistics | None = None
    report: TransformReport | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
