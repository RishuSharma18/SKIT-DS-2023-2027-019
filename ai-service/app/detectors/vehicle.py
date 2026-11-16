"""YOLO vehicle detection, class normalization, and tile-aware ByteTrack."""
import numpy as np
import torch
from ultralytics import YOLO
from ultralytics.engine.results import Boxes

from .. import config
from ..detection import frame_tiles, suppress_duplicate_detections
from ..trackers.byte_tracker import CameraTracker

COCO_CATEGORY_MAP = {
    "motorcycle": "TWO_WHEELER",
    "car": "COMPACT_CAR",
    "bus": "HEAVY_VEHICLE",
    "truck": "HEAVY_VEHICLE",
}
VEHICLE_CATEGORIES = {
    "TWO_WHEELER",
    "COMPACT_CAR",
    "SUV_SEDAN",
    "HEAVY_VEHICLE",
}


def canonical_category(class_id, class_name, custom_class_map=None):
    overrides = custom_class_map or {}
    category = overrides.get(str(class_id), overrides.get(class_name))
    if category is None:
        category = COCO_CATEGORY_MAP.get(class_name.strip().lower())
    return category if category in VEHICLE_CATEGORIES else None


def dashboard_category(category):
    """Translate canonical classes for the existing dashboard/database enums."""
    return {
        "TWO_WHEELER": "bike",
        "COMPACT_CAR": "car",
        "SUV_SEDAN": "suv",
        "HEAVY_VEHICLE": "heavy_vehicle",
    }.get(category, "car")


class VehicleDetector:
    def __init__(self, model_path=config.YOLO_MODEL, confidence=config.CONFIDENCE,
                 image_size=config.YOLO_IMAGE_SIZE, tracker=config.TRACKER):
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.image_size = image_size
        self.tracker = CameraTracker(tracker)
        self.names = self.model.names

    def track(self, frame):
        height, width = frame.shape[:2]
        tiles = frame_tiles(frame)
        predictions = self.model.predict(
            [tile for tile, _, _ in tiles],
            imgsz=self.image_size,
            conf=self.confidence,
            classes=None if config.CUSTOM_CLASS_MAP else config.VEHICLE_CLASSES,
            verbose=False,
        )
        detections = []
        for prediction, (_, x_offset, y_offset) in zip(predictions, tiles):
            if prediction.boxes is None:
                continue
            for box, score, class_id in zip(
                prediction.boxes.xyxy.cpu().numpy(),
                prediction.boxes.conf.cpu().numpy(),
                prediction.boxes.cls.cpu().numpy(),
            ):
                name = str(self.names[int(class_id)]).strip().lower()
                category = canonical_category(class_id, name, config.CUSTOM_CLASS_MAP)
                if category is None:
                    continue
                x1, y1, x2, y2 = box
                detections.append([
                    x1 + x_offset, y1 + y_offset, x2 + x_offset, y2 + y_offset,
                    score, class_id,
                ])

        merged = suppress_duplicate_detections(
            np.asarray(detections, dtype=np.float32).reshape(-1, 6)
        )
        boxes = Boxes(torch.as_tensor(merged, dtype=torch.float32), orig_shape=(height, width))
        tracked = self.tracker.update(boxes, frame)
        return [
            {
                "box": row[:4],
                "track_id": int(row[4]),
                "confidence": float(row[5]),
                "class_id": int(row[6]),
                "category": canonical_category(
                    int(row[6]), str(self.names[int(row[6])]).strip().lower(),
                    config.CUSTOM_CLASS_MAP,
                ),
                "class_name": str(self.names[int(row[6])]),
            }
            for row in tracked
        ]
