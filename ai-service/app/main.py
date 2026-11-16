"""FastAPI endpoints for camera streams, health, and duration estimates."""
from contextlib import asynccontextmanager
from functools import lru_cache
import json
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config
from .api.event_dispatcher import EventDispatcher
from .api.streams import StreamManager


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


app.mount(
    "/media/alerts",
    StaticFiles(directory=str(config.EVENT_SNAPSHOT_DIR), check_dir=False),
    name="alert-snapshots",
)
