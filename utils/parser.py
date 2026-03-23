import json
from typing import Any


REQUIRED_STAGE1_TOP_LEVEL_FIELDS = {"items", "ambiguities_and_occlusions"}
REQUIRED_STAGE1_ITEM_FIELDS = {
    "item_id",
    "probable_item_type",
    "shape_and_design_cues",
    "material_clues",
    "position",
    "overlap",
    "grouping_hints",
    "visual_confidence",
}
REQUIRED_TOP_LEVEL_FIELDS = {"items", "total_estimated_value_inr", "assumptions"}
REQUIRED_ITEM_FIELDS = {
    "item_id",
    "type",
    "count",
    "shape_or_design",
    "position",
    "estimated_material",
    "estimated_weight_grams_range",
    "estimated_purity",
    "estimated_value_inr",
    "confidence",
    "rationale",
}


def extract_json_candidate(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")
    return text[start : end + 1]


def parse_json_object(raw_text: str) -> dict[str, Any]:
    candidate = extract_json_candidate(raw_text)
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("Parsed response must be a JSON object.")
    return parsed


def _validate_range_object(value: Any, field_name: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")
    if "min" not in value or "max" not in value:
        raise ValueError(f"{field_name} must contain min and max.")
    if not isinstance(value["min"], (int, float)) or not isinstance(value["max"], (int, float)):
        raise ValueError(f"{field_name} min and max must be numeric.")
    if value["min"] > value["max"]:
        raise ValueError(f"{field_name} min cannot exceed max.")


def _validate_valuation_structure(parsed: dict[str, Any]) -> tuple[float, float]:
    missing_top_level = REQUIRED_TOP_LEVEL_FIELDS - set(parsed.keys())
    if missing_top_level:
        raise ValueError(f"Missing top-level fields: {sorted(missing_top_level)}")

    if not isinstance(parsed["items"], list):
        raise ValueError("items must be a list.")
    if not isinstance(parsed["assumptions"], list):
        raise ValueError("assumptions must be a list.")

    _validate_range_object(parsed["total_estimated_value_inr"], "total_estimated_value_inr")

    total_min = 0.0
    total_max = 0.0
    for index, item in enumerate(parsed["items"]):
        if not isinstance(item, dict):
            raise ValueError(f"Item at index {index} must be an object.")

        missing_item_fields = REQUIRED_ITEM_FIELDS - set(item.keys())
        if missing_item_fields:
            raise ValueError(f"Item at index {index} is missing fields: {sorted(missing_item_fields)}")

        if not isinstance(item["count"], (int, float)):
            raise ValueError(f"Item at index {index} has a non-numeric count.")
        if item["confidence"] not in {"low", "medium", "high"}:
            raise ValueError(f"Item at index {index} has invalid confidence.")

        _validate_range_object(item["estimated_weight_grams_range"], f"items[{index}].estimated_weight_grams_range")
        _validate_range_object(item["estimated_value_inr"], f"items[{index}].estimated_value_inr")

        total_min += float(item["estimated_value_inr"]["min"])
        total_max += float(item["estimated_value_inr"]["max"])

    return total_min, total_max


def parse_stage1_json(raw_text: str) -> dict[str, Any]:
    parsed = parse_json_object(raw_text)

    missing_top_level = REQUIRED_STAGE1_TOP_LEVEL_FIELDS - set(parsed.keys())
    if missing_top_level:
        raise ValueError(f"Stage 1 is missing top-level fields: {sorted(missing_top_level)}")

    if not isinstance(parsed["items"], list):
        raise ValueError("Stage 1 items must be a list.")
    if not isinstance(parsed["ambiguities_and_occlusions"], list):
        raise ValueError("Stage 1 ambiguities_and_occlusions must be a list.")

    for index, item in enumerate(parsed["items"]):
        if not isinstance(item, dict):
            raise ValueError(f"Stage 1 item at index {index} must be an object.")
        missing_item_fields = REQUIRED_STAGE1_ITEM_FIELDS - set(item.keys())
        if missing_item_fields:
            raise ValueError(f"Stage 1 item at index {index} is missing fields: {sorted(missing_item_fields)}")
        if item["visual_confidence"] not in {"low", "medium", "high"}:
            raise ValueError(f"Stage 1 item at index {index} has invalid visual_confidence.")

    return parsed


def parse_valuation_json(raw_text: str) -> dict[str, Any]:
    parsed = parse_json_object(raw_text)
    total_min, total_max = _validate_valuation_structure(parsed)

    reported_total = parsed["total_estimated_value_inr"]
    if abs(total_min - float(reported_total["min"])) > 1e-6 or abs(total_max - float(reported_total["max"])) > 1e-6:
        raise ValueError("total_estimated_value_inr must equal the sum of item estimated_value_inr ranges.")

    return parsed


def coerce_valuation_totals(raw_text: str) -> dict[str, Any]:
    parsed = parse_json_object(raw_text)
    total_min, total_max = _validate_valuation_structure(parsed)
    parsed["total_estimated_value_inr"] = {
        "min": total_min,
        "max": total_max,
    }
    return parsed
