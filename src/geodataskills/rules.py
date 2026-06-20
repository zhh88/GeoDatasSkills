from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


FilterOp = Literal["eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "exists", "missing"]
MissingPolicy = Literal["invalid", "drop", "default", "keep"]
OutputMode = Literal["compact", "standard", "full", "debug"]


@dataclass(slots=True)
class FilterRule:
    field: str
    op: FilterOp
    value: Any = None


@dataclass(slots=True)
class ValidationRules:
    required: list[str] = field(default_factory=list)
    missing_policy: MissingPolicy = "invalid"
    coordinate_range: Literal["auto", "lnglat", "cartesian"] = "auto"
    allow_invalid: bool = True


@dataclass(slots=True)
class OutputRules:
    mode: OutputMode = "standard"
    drop_empty: bool = True
    include_report: bool = True
    include_raw_attributes: bool = True


@dataclass(slots=True)
class RuleProfile:
    fields: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    filters: list[FilterRule] = field(default_factory=list)
    validation: ValidationRules = field(default_factory=ValidationRules)
    output: OutputRules = field(default_factory=OutputRules)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "RuleProfile":
        if not raw:
            return cls()
        filters = [
            FilterRule(field=item["field"], op=item.get("op", "eq"), value=item.get("value"))
            for item in raw.get("filters", [])
        ]
        validation_raw = raw.get("validation", {})
        output_raw = raw.get("output", {})
        return cls(
            fields=dict(raw.get("fields", {})),
            defaults=dict(raw.get("defaults", {})),
            filters=filters,
            validation=ValidationRules(
                required=list(validation_raw.get("required", [])),
                missing_policy=validation_raw.get("missing_policy", "invalid"),
                coordinate_range=validation_raw.get("coordinate_range", "auto"),
                allow_invalid=validation_raw.get("allow_invalid", True),
            ),
            output=OutputRules(
                mode=output_raw.get("mode", "standard"),
                drop_empty=output_raw.get("drop_empty", True),
                include_report=output_raw.get("include_report", True),
                include_raw_attributes=output_raw.get("include_raw_attributes", True),
            ),
        )


def evaluate_filter(row: dict[str, Any], rule: FilterRule) -> bool:
    exists = rule.field in row and row.get(rule.field) not in (None, "")
    value = row.get(rule.field)
    if rule.op == "exists":
        return exists
    if rule.op == "missing":
        return not exists
    if rule.op == "eq":
        return value == rule.value
    if rule.op == "ne":
        return value != rule.value
    if rule.op == "in":
        return value in (rule.value or [])
    if rule.op == "not_in":
        return value not in (rule.value or [])
    left = _as_number(value)
    right = _as_number(rule.value)
    if left is None or right is None:
        return False
    if rule.op == "gt":
        return left > right
    if rule.op == "gte":
        return left >= right
    if rule.op == "lt":
        return left < right
    if rule.op == "lte":
        return left <= right
    return True


def _as_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
