from pathlib import Path

from geodataskills import GeoDataIngestionSkill


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    skill = GeoDataIngestionSkill()

    for filename in ["sample_points.csv", "sample_geojson.json", "sample_trajectory.json"]:
        dataset = skill.ingest(ROOT / "examples" / filename, coordinate_system="EPSG:4326")
        print(f"\n{filename}")
        print(f"  objects: {dataset.statistics.object_count if dataset.statistics else 0}")
        print(f"  bounds: {dataset.bounds}")
        print(f"  geometry_types: {dataset.statistics.geometry_types if dataset.statistics else {}}")


if __name__ == "__main__":
    main()
