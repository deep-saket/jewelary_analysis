import logging
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import MAX_UPLOAD_SIZE_BYTES
from services.vlm_service import analyze_image
from utils.helpers import guess_image_mime_type

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jewellery Valuation API",
    description="Two-stage OpenAI vision pipeline for jewellery valuation.",
    version="1.0.0",
)


class ErrorResponse(BaseModel):
    detail: str


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/analyze",
    responses={
        200: {"description": "Structured jewellery valuation"},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def analyze(file: UploadFile = File(...)) -> JSONResponse:
    logger.info("Received analyze request for filename=%s", file.filename)

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(image_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file exceeds the {MAX_UPLOAD_SIZE_BYTES} byte limit.",
        )

    mime_type = file.content_type or ""
    if not mime_type.startswith("image/"):
        mime_type = guess_image_mime_type(image_bytes)
    if not mime_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload an image.")

    try:
        result: dict[str, Any] = analyze_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            source_name=file.filename or "uploaded-image",
        )
        return JSONResponse(content=result)
    except ValueError as exc:
        logger.warning("Validation error during analysis: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected failure during analysis")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze the image. Check server logs for details.",
        ) from exc
