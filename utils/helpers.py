import base64
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml


def load_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def load_yaml(path: str | Path) -> dict[str, str]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain an object: {path}")
    return {str(key): str(value) for key, value in data.items()}


def encode_image_to_data_url(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def guess_image_mime_type(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def sanitize_filename_component(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    sanitized = sanitized.strip(".-")
    return sanitized or "image"


def build_output_run_name(source_name: str) -> str:
    stem = Path(source_name).stem if source_name else "image"
    safe_stem = sanitize_filename_component(stem)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{safe_stem}-{timestamp}"
