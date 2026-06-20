from pathlib import Path

from geodataskills import GeoDataIngestionSkill
from geodataskills.fields import infer_field_mapping
from geodataskills.timeutils import normalize_timestamp


ROOT = Path(__file__).resolve().parents[1]


def test_csv_ingestion() -> None:
    skill = GeoDataIngestionSkill()
    dataset = skill.ingest(ROOT / "examples" / "sample_points.csv", coordinate_system="EPSG:4326")

    assert dataset.statistics is not None
    assert dataset.statistics.object_count == 3
    assert dataset.objects[0].geometry.type == "point"
    assert dataset.objects[0].render is not None
    assert dataset.objects[0].render.preferred_geometry == "column"
    assert dataset.objects[0].modality
    assert dataset.time_range is not None


def test_geojson_ingestion() -> None:
    skill = GeoDataIngestionSkill()
    dataset = skill.ingest(ROOT / "examples" / "sample_geojson.json")

    assert dataset.statistics is not None
    assert dataset.statistics.geometry_types["polygon"] == 1
    assert dataset.bounds is not None
    assert dataset.objects[0].semantic is not None
    assert dataset.objects[0].semantic.category == "risk-area"


def test_trajectory_ingestion() -> None:
    skill = GeoDataIngestionSkill()
    dataset = skill.ingest(ROOT / "examples" / "sample_trajectory.json")

    assert len(dataset.objects) == 1
    assert dataset.objects[0].geometry.type == "trajectory"
    assert dataset.objects[0].render is not None
    assert dataset.objects[0].render.preferred_geometry == "path"


def test_field_mapping_aliases() -> None:
    mapping = infer_field_mapping([{"longitude": "120", "latitude": "30", "risk": 10}])
    assert mapping.x_field == "longitude"
    assert mapping.y_field == "latitude"
    assert mapping.value_field == "risk"


def test_time_normalization() -> None:
    assert normalize_timestamp("2026-06-20T10:00:00Z") is not None
    assert normalize_timestamp(1_700_000_000) == 1_700_000_000_000
