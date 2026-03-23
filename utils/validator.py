from typing import Any


RETRY_NOTE = (
    "Possible under-segmentation: multiple items in different vertical regions may have been merged. "
    "Re-evaluate and split items. There appear to be multiple elongated items at different vertical "
    "positions. Ensure they are separated."
)


def _normalize_position(position: str) -> str:
    return position.strip().lower()


def _region_from_position(position: str) -> str | None:
    normalized = _normalize_position(position)
    if "top" in normalized:
        return "top"
    if "middle" in normalized or "center" in normalized:
        return "middle"
    if "bottom" in normalized:
        return "bottom"
    return None


def _looks_elongated(item: dict[str, Any]) -> bool:
    text = " ".join(
        str(item.get(field, "")).lower()
        for field in ("probable_item_type", "shape_and_design_cues", "grouping_hints")
    )
    keywords = ("necklace", "chain", "choker", "mala", "linked", "elongated", "strand")
    return any(keyword in text for keyword in keywords)


def validate_stage1_coverage(stage1_output: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure at least one item exists in each detected region
    (top / middle / bottom) if jewellery is present.
    """
    items = stage1_output.get("items", [])
    regions = {
        region
        for item in items
        if isinstance(item, dict)
        for region in [_region_from_position(str(item.get("position", "")))]
        if region is not None
    }
    elongated_items = [item for item in items if isinstance(item, dict) and _looks_elongated(item)]
    elongated_regions = {
        region
        for item in elongated_items
        for region in [_region_from_position(str(item.get("position", "")))]
        if region is not None
    }

    issues: list[str] = []
    if len(regions) >= 2 and len(items) < len(regions):
        issues.append("Not all detected vertical regions are represented by separate items.")
    if len(elongated_regions) >= 2 and len(elongated_items) <= 1:
        issues.append("Only one elongated item was identified across multiple vertical regions.")

    return {
        "is_valid": not issues,
        "issues": issues,
        "retry_note": RETRY_NOTE if issues else None,
    }
