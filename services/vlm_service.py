import json
import logging
import time
from pathlib import Path
from typing import Any

import requests
from openai import APIError, APITimeoutError, OpenAI, RateLimitError

from config import (
    API_RETRY_DELAY_SECONDS,
    MAX_API_RETRIES,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OUTPUT_ROOT,
)
from utils.helpers import (
    build_output_run_name,
    encode_image_to_data_url,
    load_yaml,
    sanitize_filename_component,
)
from services.gold_price_service import GoldPriceServiceError, format_gold_rate_context, get_live_gold_rates
from utils.parser import parse_json_object, parse_stage1_json, parse_valuation_json
from utils.validator import validate_stage1_coverage

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"

client = OpenAI(api_key=OPENAI_API_KEY)
STAGE1_PROMPT = load_yaml(PROMPTS_DIR / "stage1.yml")
STAGE2_PROMPT = load_yaml(PROMPTS_DIR / "stage2.yml")


class VLMServiceError(RuntimeError):
    pass


def _call_openai(system_prompt: str, content: list[dict[str, Any]]) -> str:
    attempts = MAX_API_RETRIES + 1
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = client.responses.create(
                model=OPENAI_MODEL,
                instructions=system_prompt,
                input=[{"role": "user", "content": content}],
            )
            output_text = getattr(response, "output_text", "").strip()
            if not output_text:
                raise VLMServiceError("The model returned an empty response.")
            return output_text
        except (APIError, APITimeoutError, RateLimitError, VLMServiceError) as exc:
            last_error = exc
            logger.warning("OpenAI call attempt %s/%s failed: %s", attempt, attempts, exc)
            if attempt == attempts:
                break
            time.sleep(API_RETRY_DELAY_SECONDS * attempt)

    raise VLMServiceError(f"OpenAI request failed after {attempts} attempts.") from last_error


def _build_stage1_content(image_data_url: str, retry_note: str | None = None) -> list[dict[str, Any]]:
    prompt_text = STAGE1_PROMPT["user_prompt"]
    prompt_text = prompt_text.replace("{retry_note}", retry_note or "No correction note.")
    return [
        {"type": "input_text", "text": prompt_text},
        {"type": "input_image", "image_url": image_data_url},
    ]


def _build_stage2_content(
    image_data_url: str,
    stage1_output: dict[str, Any],
    gold_rate_context: str | None = None,
    retry_note: str | None = None,
) -> list[dict[str, Any]]:
    prompt_text = STAGE2_PROMPT["user_prompt"]
    prompt_text = prompt_text.replace("{stage1_output}", json.dumps(stage1_output, indent=2))
    prompt_text = prompt_text.replace("{retry_note}", retry_note or "No correction note.")
    prompt_text = prompt_text.replace("{gold_rate}", gold_rate_context or "Gold rate unavailable.")

    return [
        {
            "type": "input_text",
            "text": prompt_text,
        },
        {"type": "input_image", "image_url": image_data_url},
    ]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _persist_model_json_attempt(path: Path, raw_text: str) -> None:
    try:
        payload = parse_json_object(raw_text)
    except ValueError:
        payload = {
            "parse_error": "Model response could not be parsed as a JSON object.",
            "raw_response": raw_text,
        }
    _write_json(path, payload)


def _prepare_run_directory(source_name: str, image_bytes: bytes, mime_type: str) -> Path:
    run_dir = OUTPUT_ROOT / build_output_run_name(source_name)
    run_dir.mkdir(parents=True, exist_ok=False)

    extension = mime_type.split("/")[-1].replace("jpeg", "jpg")
    image_name = f"{sanitize_filename_component(Path(source_name or 'image').stem)}.{extension}"
    (run_dir / image_name).write_bytes(image_bytes)

    return run_dir


def analyze_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    source_name: str = "uploaded-image",
) -> dict[str, Any]:

    if not mime_type.startswith("image/"):
        raise ValueError("mime_type must be an image content type.")

    run_dir = _prepare_run_directory(source_name, image_bytes, mime_type)
    image_data_url = encode_image_to_data_url(image_bytes, mime_type)
    _write_json(
        run_dir / "request_metadata.json",
        {
            "source_name": source_name,
            "mime_type": mime_type,
            "image_size_bytes": len(image_bytes),
        },
    )

    logger.info("Starting Stage 1 decomposition")
    stage1_raw = _call_openai(STAGE1_PROMPT["system_prompt"], _build_stage1_content(image_data_url))
    logger.info("Stage 1 raw output: %s", stage1_raw)
    stage1_output = parse_stage1_json(stage1_raw)
    _persist_model_json_attempt(run_dir / "stage1_attempt1.json", stage1_raw)

    coverage_validation = validate_stage1_coverage(stage1_output)
    if not coverage_validation["is_valid"]:
        logger.info("Stage 1 retry triggered: %s", "; ".join(coverage_validation["issues"]))
        stage1_retry_raw = _call_openai(
            STAGE1_PROMPT["system_prompt"],
            _build_stage1_content(image_data_url, retry_note=str(coverage_validation["retry_note"])),
        )
        logger.info("Stage 1 retry raw output: %s", stage1_retry_raw)
        _persist_model_json_attempt(run_dir / "stage1_attempt2.json", stage1_retry_raw)
        stage1_output = parse_stage1_json(stage1_retry_raw)

    logger.info("Final Stage 1 output: %s", json.dumps(stage1_output, indent=2))
    _write_json(run_dir / "stage1_output.json", stage1_output)

    gold_rate_data: dict[str, Any] | None = None
    try:
        gold_rate_data = get_live_gold_rates()
        _write_json(run_dir / "gold_rate_reference.json", gold_rate_data)
    except (GoldPriceServiceError, requests.RequestException) as exc:
        logger.warning("Failed to fetch live gold rates: %s", exc)
        _write_json(
            run_dir / "gold_rate_reference.json",
            {
                "error": str(exc),
                "source": "Goodreturns",
                "source_url": "https://www.goodreturns.in/gold-rates/",
            },
        )

    logger.info("Starting Stage 2 valuation")
    stage2_raw = _call_openai(
        STAGE2_PROMPT["system_prompt"],
        _build_stage2_content(
            image_data_url,
            stage1_output,
            gold_rate_context=format_gold_rate_context(gold_rate_data) if gold_rate_data else None,
        ),
    )
    _persist_model_json_attempt(run_dir / "stage2_attempt1.json", stage2_raw)

    try:
        final_json = parse_valuation_json(stage2_raw)
        _write_json(run_dir / "stage2_attempt1.json", final_json)
    except ValueError as exc:
        logger.warning("Stage 2 JSON parsing failed, retrying once: %s", exc)
        retry_note = (
            "Your previous response was not valid JSON or did not match the required schema. "
            "Return strict JSON only and ensure all required fields are present."
        )
        stage2_retry_raw = _call_openai(
            STAGE2_PROMPT["system_prompt"],
            _build_stage2_content(
                image_data_url,
                stage1_output,
                gold_rate_context=format_gold_rate_context(gold_rate_data) if gold_rate_data else None,
                retry_note=retry_note,
            ),
        )
        _persist_model_json_attempt(run_dir / "stage2_attempt2.json", stage2_retry_raw)
        try:
            final_json = parse_valuation_json(stage2_retry_raw)
            _write_json(run_dir / "stage2_attempt2.json", final_json)
        except ValueError as retry_exc:
            _write_json(
                run_dir / "error.json",
                {
                    "error": str(retry_exc),
                    "stage": "stage2_validation",
                },
            )
            raise

    final_json["output_directory"] = str(run_dir)
    final_json["stage1_visual_decomposition"] = stage1_output
    if gold_rate_data:
        final_json["gold_rate_reference"] = gold_rate_data
    _write_json(run_dir / "analysis_output.json", final_json)
    return final_json
