from pathlib import Path
import unittest

from geodataskills import GeoDataIngestionSkill
from geodataskills.detection import detect_source_type
from geodataskills.professional import dependency_status


ROOT = Path(__file__).resolve().parents[1]


class ProfessionalAndVisualizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = GeoDataIngestionSkill()

    def test_professional_extensions_detected(self) -> None:
        self.assertEqual(detect_source_type("data.shp"), "shapefile")
        self.assertEqual(detect_source_type("image.tif"), "geotiff")
        self.assertEqual(detect_source_type("cloud.las"), "point-cloud")
        self.assertEqual(detect_source_type("model.glb"), "gltf")

    def test_cityjson_metadata_ingestion(self) -> None:
        dataset = self.skill.ingest(ROOT / "examples" / "sample_city.json")

        self.assertEqual(dataset.objects[0].source.source_type, "cityjson")
        self.assertEqual(dataset.objects[0].geometry.type, "unknown")
        self.assertTrue(any(event.code == "professional_format_metadata_only" for event in dataset.report.events))

    def test_3d_tiles_metadata_ingestion(self) -> None:
        dataset = self.skill.ingest(ROOT / "examples" / "sample_tileset.json")

        self.assertEqual(dataset.objects[0].source.source_type, "3d-tiles")
        self.assertTrue(dataset.objects[0].attributes)

    def test_dependency_status_is_structured(self) -> None:
        status = dependency_status("geotiff")

        self.assertEqual(status["source_type"], "geotiff")
        self.assertIn("dependencies", status)

    def test_html_report_export(self) -> None:
        dataset = self.skill.ingest(ROOT / "examples" / "sample_points.csv")
        target = ROOT / "outputs" / "test_report.html"
        self.skill.export_html_report(dataset, target, title="Test Report")

        text = target.read_text(encoding="utf-8")
        self.assertIn("Test Report", text)
        self.assertIn("二维空间预览", text)
        self.assertIn("三维数值预览", text)
        target.unlink()
        target.parent.rmdir()


if __name__ == "__main__":
    unittest.main()
