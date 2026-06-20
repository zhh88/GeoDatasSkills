from pathlib import Path
import unittest

from geodataskills import GeoDataIngestionSkill


ROOT = Path(__file__).resolve().parents[1]


class SchemaAndQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = GeoDataIngestionSkill()

    def test_nested_json_flattening_and_schema_report(self) -> None:
        dataset = self.skill.ingest(
            ROOT / "examples" / "sample_nested.json",
            rules={
                "fields": {
                    "id": "id",
                    "x": "location.lng",
                    "y": "location.lat",
                    "z": "location.height",
                    "value": "metrics.risk",
                    "type": "meta.type",
                    "time": "meta.time",
                    "image": "media.photo",
                    "text": "media.note",
                },
                "validation": {"coordinate_range": "lnglat", "allow_invalid": True},
            },
        )

        self.assertEqual(dataset.statistics.input_count, 2)
        self.assertEqual(dataset.statistics.object_count, 2)
        self.assertTrue(dataset.report.schema["nested_detected"])
        field_names = {field["name"] for field in dataset.report.schema["fields"]}
        self.assertIn("location.lng", field_names)
        self.assertIn("metrics.risk", field_names)
        self.assertEqual(dataset.objects[0].geometry.coordinates, [120.12, 30.25, 15.0])
        self.assertTrue(dataset.objects[0].modality)

    def test_coordinate_quality_flags_out_of_range_lnglat(self) -> None:
        dataset = self.skill.ingest(
            [{"id": "BAD", "lng": 500, "lat": 30}],
            rules={
                "fields": {"id": "id", "x": "lng", "y": "lat"},
                "validation": {"coordinate_range": "lnglat", "allow_invalid": True},
            },
        )

        obj = dataset.objects[0]
        self.assertFalse(obj.quality.valid)
        self.assertTrue(any("outside longitude/latitude range" in warning for warning in obj.quality.warnings))
        self.assertEqual(dataset.statistics.invalid_count, 1)

    def test_coordinate_quality_warns_possible_reversal(self) -> None:
        dataset = self.skill.ingest(
            [{"id": "REV", "lng": 30.25, "lat": 120.12}],
            rules={
                "fields": {"id": "id", "x": "lng", "y": "lat"},
                "validation": {"coordinate_range": "auto"},
            },
        )

        warnings = dataset.objects[0].quality.warnings
        self.assertTrue(any("reversed" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
