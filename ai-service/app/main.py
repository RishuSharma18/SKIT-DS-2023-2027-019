"""FastAPI endpoints for AI service health, duration estimates, and video."""
from functools import lru_cache
import json
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import config

app = FastAPI(title="Smart CCTV AI Service")
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
def health():
    metrics = None
    if METRICS_PATH.is_file():
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    try:
        slot_data = json.loads(config.SLOTS_PATH.read_text(encoding="utf-8"))
        configured_slot_ids = [slot["slotId"] for slot in slot_data["slots"]]
        slot_config_error = None
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        configured_slot_ids = []
        slot_config_error = str(error)

    return {
        "ok": True,
        "ocrEnabled": config.ENABLE_OCR,
        "durationModelAvailable": MODEL_PATH.is_file(),
        "durationModelMetrics": metrics,
        "cameraId": config.CAMERA_ID,
        "sourceMode": config.SOURCE_MODE,
        "configuredSlotIds": configured_slot_ids,
        "configuredSlots": [
            {"slotId": slot["slotId"], "type": slot["type"]}
            for slot in slot_data.get("slots", [])
        ] if slot_config_error is None else [],
        "slotConfigError": slot_config_error,
        "inferenceImageSize": config.YOLO_IMAGE_SIZE,
        "confidence": config.CONFIDENCE,
        "tiledInference": True,
        "tileOverlap": config.TILE_OVERLAP,
        "tracker": "ByteTrack",
    }


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


def _mjpeg():
    import cv2

    from .pipeline import Pipeline

    for frame in Pipeline().run():
        ok, buf = cv2.imencode(".jpg", frame)
        if ok:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")


@app.get("/stream")
def stream():
    return StreamingResponse(_mjpeg(), media_type="multipart/x-mixed-replace; boundary=frame")
