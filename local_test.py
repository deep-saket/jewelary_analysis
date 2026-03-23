import json
import logging
from pathlib import Path

import yaml

from services.vlm_service import analyze_image
from utils.helpers import guess_image_mime_type

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
DEFAULT_CONFIG_PATH = Path("local_test_args.yml")


def load_config(config_path: Path) -> dict[str, object]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file does not exist: {config_path}")

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("Config file must contain a YAML object.")
    if "input_path" not in data:
        raise ValueError("Config file must define input_path.")

    return data


def collect_images(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file():
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    pattern = "**/*" if recursive else "*"
    candidates = sorted(path for path in input_path.glob(pattern) if path.is_file())
    images = [path for path in candidates if path.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not images:
        raise ValueError(f"No supported images found in directory: {input_path}")
    return images


def process_image(path: Path) -> dict[str, str]:
    image_bytes = path.read_bytes()
    mime_type = guess_image_mime_type(image_bytes)
    if not mime_type.startswith("image/"):
        raise ValueError(f"Unsupported image type for file: {path}")

    result = analyze_image(
        image_bytes=image_bytes,
        mime_type=mime_type,
        source_name=path.name,
    )
    return {
        "input_file": str(path),
        "status": "success",
        "output_directory": result["output_directory"],
    }


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    config = load_config(DEFAULT_CONFIG_PATH.resolve())
    input_path = Path(str(config["input_path"])).expanduser().resolve()
    recursive = bool(config.get("recursive", False))

    results: list[dict[str, str]] = []
    exit_code = 0

    for image_path in collect_images(input_path, recursive=recursive):
        try:
            summary = process_image(image_path)
            results.append(summary)
            print(json.dumps(summary))
        except Exception as exc:
            exit_code = 1
            error_summary = {
                "input_file": str(image_path),
                "status": "error",
                "error": str(exc),
            }
            results.append(error_summary)
            print(json.dumps(error_summary))

    print(json.dumps({"processed": len(results), "failed": sum(r["status"] == "error" for r in results)}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
