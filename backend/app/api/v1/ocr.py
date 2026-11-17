import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, ValidationError

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ocr", tags=["Plate OCR"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/x-ms-bmp",
}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


class OCRCandidate(BaseModel):
    text: str
    confidence: float = Field(ge=0.0, le=1.0)


class PlateOCRResponse(BaseModel):
    success: bool
    plate_detected: bool
    text: str | None
    raw_text: str | None
    normalized_text: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    is_low_confidence: bool
    candidates: list[OCRCandidate]
    error: str | None


async def forward_plate_image(contents: bytes, filename: str, content_type: str):
    endpoint = f"{settings.AI_SERVICE_URL.rstrip('/')}/ocr/plate"
    timeout = httpx.Timeout(connect=5.0, read=120.0, write=15.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.post(
            endpoint,
            headers={"x-api-key": settings.AI_API_KEY},
            files={"file": (filename, contents, content_type)},
        )


@router.post("/plate", response_model=PlateOCRResponse)
async def recognize_plate(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Choose a plate photo to upload.")

    content_type = (file.content_type or "").lower()
    extension = Path(file.filename).suffix.lower()
    if content_type not in ALLOWED_CONTENT_TYPES and extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image type. Upload JPEG, PNG, WebP, or BMP.",
        )

    try:
        contents = await file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
    finally:
        await file.close()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(contents) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the 10MB upload limit.")

    safe_filename = f"plate-image{extension}" if extension in ALLOWED_EXTENSIONS else "plate-image"
    try:
        response = await forward_plate_image(contents, safe_filename, content_type or "application/octet-stream")
    except httpx.TimeoutException as error:
        logger.warning("AI OCR service timed out")
        raise HTTPException(status_code=504, detail="Plate OCR timed out. Try again with a smaller image.") from error
    except httpx.RequestError as error:
        logger.warning("AI OCR service is unavailable: %s", error.__class__.__name__)
        raise HTTPException(status_code=503, detail="Plate OCR service is unavailable. Check that the AI service is running.") from error

    if response.status_code >= 400:
        try:
            upstream_body = response.json()
        except ValueError:
            upstream_body = None
        upstream_detail = upstream_body.get("detail") if isinstance(upstream_body, dict) else None
        if response.status_code in {400, 413, 415} and isinstance(upstream_detail, str):
            raise HTTPException(status_code=response.status_code, detail=upstream_detail)
        logger.error("AI OCR service returned HTTP %s", response.status_code)
        raise HTTPException(status_code=503, detail="Plate OCR service could not process the request.")

    try:
        result = response.json()
    except ValueError as error:
        logger.error("AI OCR service returned an invalid response")
        raise HTTPException(status_code=502, detail="Plate OCR service returned an invalid response.") from error

    try:
        return PlateOCRResponse.model_validate(result)
    except ValidationError as error:
        logger.error("AI OCR service response did not match the required result shape")
        raise HTTPException(status_code=502, detail="Plate OCR service returned an invalid response.") from error
