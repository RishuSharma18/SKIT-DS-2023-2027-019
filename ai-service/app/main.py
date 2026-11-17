"""FastAPI endpoints for camera streams, health, and duration estimates."""
from contextlib import asynccontextmanager
from functools import lru_cache
import json
import logging
from pathlib import Path
import secrets
from typing import Literal

import joblib
import pandas as pd
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from . import config
from .api.event_dispatcher import EventDispatcher
from .api.streams import StreamManager
from .ocr.image_validation import InvalidImageError, UnsupportedImageError, decode_plate_image

logger = logging.getLogger(__name__)
MAX_OCR_UPLOAD_BYTES = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(application):
    dispatcher = EventDispatcher().start()
    stream_manager = StreamManager(dispatcher=dispatcher).start()
    application.state.dispatcher = dispatcher
    application.state.stream_manager = stream_manager
    try:
        yield
    finally:
        stream_manager.stop()
        dispatcher.close()


app = FastAPI(title="Smart CCTV AI Service", lifespan=lifespan)
MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "models" / "duration.joblib"
METRICS_PATH = MODEL_PATH.with_name("duration_metrics.json")
FEATURE_COLUMNS = [
    "arrival_hour",
    "weekday",
    "vehicle_type_bike",
    "vehicle_type_car",
    "vehicle_type_suv",
]


class DurationRequest(BaseModel):
    vehicleType: Literal["bike", "car", "suv"]
    arrivalHour: int = Field(ge=0, le=23)
    weekday: int = Field(ge=0, le=6)


def verify_ocr_api_key(x_api_key: str | None = Header(default=None)):
    if not x_api_key or not secrets.compare_digest(x_api_key, config.API_KEY):
        raise HTTPException(status_code=401, detail="A valid x-api-key header is required.")
    return True


@lru_cache(maxsize=1)
def _load_duration_model():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(MODEL_PATH)
    return joblib.load(MODEL_PATH)


@app.get("/health")
def health(request: Request):
    metrics = None
    if METRICS_PATH.is_file():
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    manager = getattr(request.app.state, "stream_manager", None)
    cameras = manager.health() if manager else [
        {
            "cameraId": camera_id,
            "sourceMode": config.source_mode(source),
            "configuredSlotIds": [],
            "configuredSlots": [],
            "status": "starting",
            "error": None,
        }
        for camera_id, source in config.CAMERA_STREAMS.items()
    ]
    return {
        "ok": True,
        "cameraId": config.CAMERA_ID,
        "ocrEnabled": config.ENABLE_OCR,
        "durationModelAvailable": MODEL_PATH.is_file(),
        "durationModelMetrics": metrics,
        "cameras": cameras,
        "inferenceImageSize": config.YOLO_IMAGE_SIZE,
        "confidence": config.CONFIDENCE,
        "tiledInference": True,
        "tileOverlap": config.TILE_OVERLAP,
        "tracker": config.TRACKER,
    }


@app.get("/health/cameras")
def camera_health(request: Request):
    manager = getattr(request.app.state, "stream_manager", None)
    if manager is None:
        return {"cameras": []}
    return {"cameras": manager.health()}


@app.post("/ml/predict-duration")
def predict_duration(request: DurationRequest):
    try:
        model = _load_duration_model()
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Duration model is not trained. Run ml/train_duration_model.py.",
        )

    vehicle_type_features = {
        f"vehicle_type_{vehicle_type}": int(request.vehicleType == vehicle_type)
        for vehicle_type in ("bike", "car", "suv")
    }
    features = pd.DataFrame(
        [
            {
                "arrival_hour": request.arrivalHour,
                "weekday": request.weekday,
                **vehicle_type_features,
            }
        ],
        columns=FEATURE_COLUMNS,
    )
    estimate = float(model.predict(features)[0])
    return {
        "estimatedDurationMin": max(1, round(estimate)),
        "vehicleType": request.vehicleType,
        "arrivalHour": request.arrivalHour,
        "weekday": request.weekday,
        "model": "random_forest",
    }


@app.get("/stream")
def stream(request: Request):
    return video_feed(config.CAMERA_ID, request)


@app.get("/video_feed/{camera_id}")
def video_feed(camera_id: str, request: Request):
    manager = getattr(request.app.state, "stream_manager", None)
    worker = manager.get(camera_id) if manager else None
    if worker is None:
        raise HTTPException(status_code=404, detail=f"Unknown camera: {camera_id}")
    if worker.status == "error":
        raise HTTPException(status_code=503, detail=worker.error or "Camera stream failed to start")
    return StreamingResponse(
        worker.iter_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@lru_cache(maxsize=1)
def get_plate_reader():
    from .ocr.plate_reader import PlateReader
    return PlateReader()


@app.post("/ocr/plate")
async def ocr_plate_endpoint(
    file: UploadFile = File(...),
    _authorized: bool = Depends(verify_ocr_api_key),
):
    """Recognize license plate text from an uploaded image photo.

    Processes in memory with zero image retention. Returns structured OCR
    results with confidence, normalization, and alternative candidates.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    try:
        contents = await file.read(MAX_OCR_UPLOAD_BYTES + 1)
    finally:
        await file.close()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(contents) > MAX_OCR_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File size exceeds maximum 10MB limit.")

    try:
        image = decode_plate_image(contents)
    except UnsupportedImageError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except InvalidImageError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        reader = get_plate_reader()
    except (ImportError, FileNotFoundError, RuntimeError) as error:
        logger.exception("Could not initialize the local plate OCR model")
        raise HTTPException(
            status_code=503,
            detail="Plate OCR model is unavailable. Check EasyOCR weights and any configured PLATE_MODEL path.",
        ) from error

    try:
        return await run_in_threadpool(reader.recognize_plate_image, image)
    except Exception as error:
        logger.exception("Plate OCR processing failed")
        raise HTTPException(status_code=500, detail="Plate OCR could not process this image.") from error



app.mount(
    "/media/alerts",
    StaticFiles(directory=str(config.EVENT_SNAPSHOT_DIR), check_dir=False),
    name="alert-snapshots",
)
