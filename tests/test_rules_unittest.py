from pathlib import Path
import unittest

from geodataskills import GeoDataIngestionSkill
from geodataskills.output import dataset_to_dict
from geodataskills.rules import OutputRules


ROOT = Path(__file__).resolve().parents[1]


class RuleDrivenIngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = GeoDataIngestionSkill()

    def test_filter_and_report(self) -> None:
        dataset = self.skill.ingest(
            ROOT / "examples" / "sample_points.csv",
            rules={
                "fields": {"x": "lng", "y": "lat", "value": "risk", "type": "type"},
                "filters": [{"field": "risk", "op": "gte", "value": 70}],
            },
        )

        self.assertEqual(dataset.statistics.input_count, 3)
        self.assertEqual(dataset.statistics.object_count, 2)
        self.assertEqual(dataset.statistics.filtered_count, 1)
        self.assertIsNotNone(dataset.report)
        self.assertEqual(dataset.report.filtered_count, 1)

    def test_defaults_repair_missing_z_and_type(self) -> None:
        rows = [{"id": "A", "lng": "120.1", "lat": "30.2", "risk": 10}]
        dataset = self.skill.ingest(
            rows,
            rules={
                "fields": {"id": "id", "x": "lng", "y": "lat", "value": "risk"},
                "defaults": {"z": 5, "type": "unknown"},
            },
        )

        obj = dataset.objects[0]
        self.assertEqual(obj.geometry.coordinates, [120.1, 30.2, 5.0])
        self.assertEqual(obj.semantic.category, "unknown")
        self.assertGreaterEqual(dataset.report.repaired_count, 2)

    def test_missing_required_can_drop_row(self) -> None:
        rows = [
            {"id": "A", "lng": "120.1", "lat": "30.2"},
            {"id": "B", "lng": "120.2"},
        ]
        dataset = self.skill.ingest(
            rows,
            rules={
                "fields": {"id": "id", "x": "lng", "y": "lat"},
                "validation": {"required": ["x", "y"], "missing_policy": "drop"},
            },
        )

        self.assertEqual(dataset.statistics.input_count, 2)
        self.assertEqual(dataset.statistics.object_count, 1)
        self.assertEqual(dataset.statistics.filtered_count, 1)

    def test_compact_output_drops_empty_fields(self) -> None:
        dataset = self.skill.ingest(ROOT / "examples" / "sample_points.csv")
        result = dataset_to_dict(dataset, OutputRules(mode="compact", drop_empty=True, include_report=True))

        self.assertIn("objects", result)
        self.assertIn("report", result)
        self.assertNotIn("source", result["objects"][0])
        self.assertNotIn("semantic", result["objects"][0])


if __name__ == "__main__":
    unittest.main()
