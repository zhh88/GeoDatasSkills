from __future__ import annotations

import argparse
import json

from .output import dataset_to_dict
from .rules import OutputRules, RuleProfile
from .skill import GeoDataIngestionSkill


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert spatial/multimodal/spatiotemporal data into a unified data model.")
    parser.add_argument("source", help="Input CSV, TSV, JSON, GeoJSON, image, video, or text path.")
    parser.add_argument("--out", help="Write unified dataset JSON to this path.")
    parser.add_argument("--coordinate-system", default=None, help="Coordinate reference label, e.g. EPSG:4326.")
    parser.add_argument("--dataset-id", default=None, help="Optional dataset id.")
    parser.add_argument("--rules", default=None, help="Optional JSON rule profile path.")
    parser.add_argument("--output-mode", default=None, choices=["compact", "standard", "full", "debug"], help="Output shape.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON to stdout.")
    args = parser.parse_args()

    skill = GeoDataIngestionSkill()
    raw_rules = None
    if args.rules:
        with open(args.rules, "r", encoding="utf-8") as handle:
            raw_rules = json.load(handle)
    profile = RuleProfile.from_dict(raw_rules)
    if args.output_mode:
        profile.output.mode = args.output_mode
    dataset = skill.ingest(args.source, coordinate_system=args.coordinate_system, dataset_id=args.dataset_id, rules=profile)
    output_rules = profile.output

    if args.out:
        skill.export_json(dataset, args.out, pretty=True, output=output_rules)
        print(args.out)
        return

    print(json.dumps(dataset_to_dict(dataset, output_rules), ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
