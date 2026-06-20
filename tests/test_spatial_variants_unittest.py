from pathlib import Path
import unittest

from geodataskills import GeoDataIngestionSkill


ROOT = Path(__file__).resolve().parents[1]


class SpatialVariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = GeoDataIngestionSkill()

    def test_wkt_polygon_ingestion(self) -> None:
        dataset = self.skill.ingest(ROOT / "examples" / "sample_polygon.wkt", coordinate_system="EPSG:4326")

        self.assertEqual(len(dataset.objects), 1)
        self.assertEqual(dataset.objects[0].geometry.type, "polygon")
        self.assertIsNotNone(dataset.bounds)
        self.assertEqual(dataset.objects[0].render.preferred_geometry, "polygon")

    def test_gpx_track_ingestion(self) -> None:
        dataset = self.skill.ingest(ROOT / "examples" / "sample_track.gpx", coordinate_system="EPSG:4326")

        self.assertEqual(len(dataset.objects), 1)
        self.assertEqual(dataset.objects[0].geometry.type, "trajectory")
        self.assertEqual(dataset.objects[0].render.preferred_geometry, "path")
        self.assertIsNotNone(dataset.time_range)


if __name__ == "__main__":
    unittest.main()
