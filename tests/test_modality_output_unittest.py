from pathlib import Path
import unittest

from geodataskills import GeoDataIngestionSkill
from geodataskills.output import dataset_to_dict
from geodataskills.rules import OutputRules


ROOT = Path(__file__).resolve().parents[1]


class ModalityAndOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = GeoDataIngestionSkill()

    def test_bind_modalities_by_id(self) -> None:
        dataset = self.skill.ingest(
            ROOT / "examples" / "sample_points.csv",
            rules={
                "modality_bindings": [
                    {
                        "source": str(ROOT / "examples" / "sample_modalities.csv"),
                        "method": "id",
                        "object_id_field": "id",
                        "modality_id_field": "object_id",
                        "modality_type_field": "modality",
                        "uri_field": "uri",
                        "content_field": "content",
                        "time_field": "time",
                    }
                ]
            },
        )

        p001 = next(obj for obj in dataset.objects if obj.id == "P001")
        self.assertGreaterEqual(len(p001.modality), 4)
        event_codes = [event.code for event in dataset.report.events]
        self.assertIn("modality_binding_applied", event_codes)
        self.assertIn("modality_unmatched", event_codes)

    def test_bind_modalities_by_nearest(self) -> None:
        dataset = self.skill.ingest(
            ROOT / "examples" / "sample_points.csv",
            rules={
                "modality_bindings": [
                    {
                        "source": str(ROOT / "examples" / "sample_nearest_modalities.csv"),
                        "method": "nearest",
                        "x_field": "lng",
                        "y_field": "lat",
                        "modality_type_field": "modality",
                        "uri_field": "uri",
                        "content_field": "content",
                        "max_distance": 0.01,
                    }
                ]
            },
        )

        p001 = next(obj for obj in dataset.objects if obj.id == "P001")
        self.assertTrue(any(item.metadata.get("binding_distance") is not None for item in p001.modality))

    def test_output_summary_contains_quality_and_field_map(self) -> None:
        dataset = self.skill.ingest(
            ROOT / "examples" / "sample_points.csv",
            rules={"fields": {"x": "lng", "y": "lat", "value": "risk"}},
        )
        result = dataset_to_dict(dataset, OutputRules(mode="standard", summary=True))

        self.assertIn("summary", result)
        self.assertEqual(result["summary"]["object_count"], 3)
        self.assertIn("x", result["summary"]["field_map"])
        self.assertEqual(result["summary"]["field_map"]["x"]["source"], "rule")


if __name__ == "__main__":
    unittest.main()
