from pathlib import Path
import unittest

from geodataskills import GeoDataIngestionSkill


ROOT = Path(__file__).resolve().parents[1]


class GovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = GeoDataIngestionSkill()

    def test_unit_conversion_and_attribute_projection(self) -> None:
        rows = [{"id": "A", "lng": 120, "lat": 30, "height_cm": 250, "secret": "drop-me"}]
        dataset = self.skill.ingest(
            rows,
            rules={
                "fields": {"id": "id", "x": "lng", "y": "lat", "z": "height_cm"},
                "unit_conversions": [{"field": "height_cm", "from_unit": "cm", "to_unit": "m"}],
                "attribute_exclude": ["secret"],
            },
        )

        self.assertEqual(dataset.objects[0].geometry.coordinates, [120.0, 30.0, 2.5])
        self.assertNotIn("secret", dataset.objects[0].attributes)
        self.assertTrue(any(event.code == "unit_converted" for event in dataset.report.events))

    def test_attribute_include(self) -> None:
        rows = [{"id": "A", "lng": 120, "lat": 30, "risk": 80, "noise": "x"}]
        dataset = self.skill.ingest(
            rows,
            rules={
                "fields": {"id": "id", "x": "lng", "y": "lat", "value": "risk"},
                "attribute_include": ["id", "lng", "lat", "risk"],
            },
        )

        self.assertEqual(set(dataset.objects[0].attributes), {"id", "lng", "lat", "risk"})

    def test_polygon_is_closed(self) -> None:
        dataset = self.skill.ingest(ROOT / "examples" / "sample_open_polygon.wkt")
        ring = dataset.objects[0].geometry.coordinates[0]

        self.assertEqual(ring[0], ring[-1])
        self.assertTrue(any(event.code == "polygon_closed" for event in dataset.report.events))

    def test_trajectory_sorted_by_time(self) -> None:
        data = {
            "trackId": "T-SORT",
            "points": [
                {"lng": 120.2, "lat": 30.2, "time": "2026-06-20T10:02:00Z"},
                {"lng": 120.1, "lat": 30.1, "time": "2026-06-20T10:01:00Z"},
            ],
        }
        dataset = self.skill.ingest(data)

        self.assertEqual(dataset.objects[0].geometry.coordinates[0][:2], [120.1, 30.1])


if __name__ == "__main__":
    unittest.main()
