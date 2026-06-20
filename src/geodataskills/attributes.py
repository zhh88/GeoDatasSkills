from __future__ import annotations

from typing import Any

from .models import TransformEvent, TransformReport
from .rules import RuleProfile, UnitConversionRule


UNIT_FACTORS: dict[tuple[str, str], float] = {
    ("cm", "m"): 0.01,
    ("mm", "m"): 0.001,
    ("km", "m"): 1000.0,
    ("m", "km"): 0.001,
    ("m", "cm"): 100.0,
    ("m", "mm"): 1000.0,
}


def apply_attribute_rules(row: dict[str, Any], rules: RuleProfile, report: TransformReport, row_index: int | None = None) -> dict[str, Any]:
    result = dict(row)
    for conversion in rules.unit_conversions:
        result = apply_unit_conversion(result, conversion, report, row_index)
    result = apply_attribute_projection(result, rules)
    return result


def apply_unit_conversion(
    row: dict[str, Any],
    conversion: UnitConversionRule,
    report: TransformReport,
    row_index: int | None = None,
) -> dict[str, Any]:
    if conversion.field not in row or row.get(conversion.field) in (None, ""):
        return row
    factor = UNIT_FACTORS.get((conversion.from_unit, conversion.to_unit))
    if factor is None:
        report.events.append(
            TransformEvent(level="warning", code="unit_conversion_unsupported", message=f"Unsupported conversion {conversion.from_unit}->{conversion.to_unit}", row_index=row_index, field=conversion.field)
        )
        return row
    try:
        row[conversion.field] = float(row[conversion.field]) * factor
        report.events.append(
            TransformEvent(level="info", code="unit_converted", message=f"Converted {conversion.field} from {conversion.from_unit} to {conversion.to_unit}", row_index=row_index, field=conversion.field)
        )
    except (TypeError, ValueError):
        report.events.append(
            TransformEvent(level="warning", code="unit_conversion_failed", message=f"Could not convert field {conversion.field}", row_index=row_index, field=conversion.field)
        )
    return row


def apply_attribute_projection(row: dict[str, Any], rules: RuleProfile) -> dict[str, Any]:
    if rules.attribute_include:
        keep = set(rules.attribute_include)
        row = {key: value for key, value in row.items() if key in keep}
    if rules.attribute_exclude:
        drop = set(rules.attribute_exclude)
        row = {key: value for key, value in row.items() if key not in drop}
    return row
