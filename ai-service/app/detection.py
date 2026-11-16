"""Tiled vehicle detection with one frame-level tracker."""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
import yaml
from ultralytics import YOLO
from ultralytics.engine.results import Boxes
from ultralytics.trackers.byte_tracker import BYTETracker

from . import config


def tile_count(width, height):
    return (2 if width >= config.TILE_MIN_WIDTH else 1) * (
        2 if height >= config.TILE_MIN_HEIGHT else 1
    )


def frame_tiles(frame, overlap=config.TILE_OVERLAP):
    height, width = frame.shape[:2]
    columns = 2 if width >= config.TILE_MIN_WIDTH else 1
    rows = 2 if height >= config.TILE_MIN_HEIGHT else 1
    tile_width = min(width, int(np.ceil(width / columns * (1 + overlap))))
    tile_height = min(height, int(np.ceil(height / rows * (1 + overlap))))
    x_starts = [0] if columns == 1 else [0, width - tile_width]
    y_starts = [0] if rows == 1 else [0, height - tile_height]
    return [
        (frame[y:y + tile_height, x:x + tile_width], x, y)
        for y in y_starts
        for x in x_starts
    ]


def suppress_duplicate_detections(detections, iou_threshold=config.TILE_NMS_IOU):
    """Class-wise NMS on [x1, y1, x2, y2, confidence, class_id] rows."""
    if not len(detections):
        return np.empty((0, 6), dtype=np.float32)

    kept = []
    for class_id in np.unique(detections[:, 5]):
        class_detections = detections[detections[:, 5] == class_id]
        order = np.argsort(class_detections[:, 4])[::-1]
        while order.size:
            best_index = order[0]
            best = class_detections[best_index]
            kept.append(best)
            remaining = order[1:]
            if not remaining.size:
                break

            other = class_detections[remaining]
            left = np.maximum(best[0], other[:, 0])
            top = np.maximum(best[1], other[:, 1])
            right = np.minimum(best[2], other[:, 2])
            bottom = np.minimum(best[3], other[:, 3])
            intersection = np.maximum(0, right - left) * np.maximum(0, bottom - top)
            best_area = (best[2] - best[0]) * (best[3] - best[1])
            other_areas = (other[:, 2] - other[:, 0]) * (other[:, 3] - other[:, 1])
            union = best_area + other_areas - intersection
            iou = np.divide(intersection, union, out=np.zeros_like(intersection), where=union > 0)
            order = remaining[iou <= iou_threshold]

    return np.asarray(kept, dtype=np.float32).reshape(-1, 6)


def summarize_tracks(tracks):
    """Count current tracked vehicles by supported COCO vehicle class."""
    counts = {"bikes": 0, "cars": 0}
    for track in tracks:
        class_id = int(track[6])
        if class_id == 3:
            counts["bikes"] += 1
        elif class_id in (2, 5, 7):
            counts["cars"] += 1
    counts["total"] = counts["bikes"] + counts["cars"]
    return counts


class VehicleDetector:
    def __init__(self, model_path=config.YOLO_MODEL, confidence=config.CONFIDENCE, image_size=config.YOLO_IMAGE_SIZE):
        self.model = YOLO(model_path)
        tracker_path = Path(__import__("ultralytics").__file__).resolve().parent / "cfg" / "trackers" / "bytetrack.yaml"
        with tracker_path.open(encoding="utf-8") as tracker_file:
            tracker_args = yaml.safe_load(tracker_file)
        self.tracker = BYTETracker(SimpleNamespace(**tracker_args))
        self.confidence = confidence
        self.image_size = image_size

    def track(self, frame):
        height, width = frame.shape[:2]
        tiles = frame_tiles(frame)
        predictions = self.model.predict(
            [tile for tile, _, _ in tiles],
            imgsz=self.image_size,
            conf=self.confidence,
            classes=config.VEHICLE_CLASSES,
            verbose=False,
        )

        detections = []
        for prediction, (_, x_offset, y_offset) in zip(predictions, tiles):
            if prediction.boxes is None:
                continue
            boxes = prediction.boxes.xyxy.cpu().numpy()
            confidences = prediction.boxes.conf.cpu().numpy()
            class_ids = prediction.boxes.cls.cpu().numpy()
            for box, score, class_id in zip(boxes, confidences, class_ids):
                x1, y1, x2, y2 = box
                detections.append([
                    x1 + x_offset, y1 + y_offset, x2 + x_offset, y2 + y_offset,
                    score, class_id,
                ])

        merged = suppress_duplicate_detections(np.asarray(detections, dtype=np.float32).reshape(-1, 6))
        tracker_boxes = Boxes(
            torch.as_tensor(merged, dtype=torch.float32),
            orig_shape=(height, width),
        )
        return self.tracker.update(tracker_boxes, img=frame)
