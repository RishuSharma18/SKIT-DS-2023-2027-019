"""Per-camera detection, tracking, OCR, spatial rules, and overlays."""
import logging
from time import time
from uuid import uuid4

import cv2
import numpy as np

from .. import config
from ..api.event_dispatcher import EventDispatcher
from ..detectors.vehicle import VehicleDetector
from ..ocr.plate_reader import PlateReader
from .zones import ZoneEngine

logger = logging.getLogger(__name__)
CATEGORY_COLORS = {
    "TWO_WHEELER": (0, 200, 255),
    "COMPACT_CAR": (255, 160, 0),
    "SUV_SEDAN": (255, 0, 220),
    "HEAVY_VEHICLE": (0, 220, 220),
}
ALERT_TYPES = {"WRONG_PARKING", "ACCIDENT", "STOLEN_VEHICLE", "OVERSTAY"}


class VideoProcessor:
    def __init__(self, camera_id, source, source_mode, zone_map, dispatcher):
        self.camera_id = camera_id
        self.source = source
        self.source_mode = source_mode
        self.zone_map = zone_map
        self.dispatcher = dispatcher
        self.detector = VehicleDetector()
        self.zone_engine = ZoneEngine(zone_map, config.WRONG_PARKING_SECONDS)
        self.ocr = PlateReader() if config.ENABLE_OCR else None
        self.crash_history = {}
        self.track_state = {}
        self.active_collision_pairs = set()
        self.frame_index = 0
        self.last_occupancy_at = 0.0

    def process(self, frame, captured_at=None):
        timestamp = captured_at or time()
        self.frame_index += 1
        if self.frame_index % (config.FRAME_SKIP + 1):
            return frame

        observations = self.detector.track(frame)
        counts = {category: 0 for category in (
            "TWO_WHEELER", "COMPACT_CAR", "SUV_SEDAN", "HEAVY_VEHICLE"
        )}
        occupied = set()
        current_tracks = set()
        crash_observations = {}

        for observation in observations:
            track_id = observation["track_id"]
            category = observation["category"]
            box = observation["box"]
            x1, y1, x2, y2 = map(int, box)
            current_tracks.add(track_id)
            counts[category] += 1
            state = self.track_state.setdefault(track_id, {
                "plate": None, "plate_confidence": None, "last_ocr_frame": 0,
                "entry_sent": False, "missed_frames": 0, "previous_center": None,
                "previous_time": None, "speed": None, "decelerated": False,
                "category": category,
            })
            state["missed_frames"] = 0
            state["category"] = category
            previous = self.crash_history.get(track_id)
            slot, transitions = self.zone_engine.update(observation, timestamp)
            slot_id = slot["slot_id"] if slot else None
            state["last_slot"] = slot_id
            if slot_id:
                occupied.add(slot_id)
            crossed = self.zone_engine.crossed_tripwires(observation, previous)
            for event_kind in crossed:
                self._send({
                    "event_type": event_kind,
                    "track_id": track_id,
                    "vehicle_category": category,
                    "plate_number": state["plate"],
                    "plate_confidence": state["plate_confidence"],
                    "slot_id": slot_id,
                })
                state["entry_sent"] = event_kind == "ENTRY"
            for transition in transitions:
                if transition["event_type"] == "ENTRY" and not state["entry_sent"]:
                    self._send({
                        "event_type": "ENTRY",
                        "track_id": track_id,
                        "vehicle_category": category,
                        "plate_number": state["plate"],
                        "plate_confidence": state["plate_confidence"],
                        "slot_id": transition["slot_id"],
                    })
                    state["entry_sent"] = True
                elif transition["event_type"] == "EXIT" and state["entry_sent"]:
                    self._send({
                        "event_type": "EXIT",
                        "track_id": track_id,
                        "vehicle_category": category,
                        "plate_number": state["plate"],
                        "plate_confidence": state["plate_confidence"],
                        "slot_id": transition["slot_id"],
                    })
                    state["entry_sent"] = False
            for transition in transitions:
                if transition["event_type"] == "ALERT":
                    self._send_alert(
                        transition["alert_type"], track_id, category, state, slot_id,
                        frame, transition["message"],
                    )

            if (self.ocr and state["plate"] is None
                    and self.frame_index - state["last_ocr_frame"] >= config.OCR_EVERY_N_FRAMES):
                crop = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
                plate_result = self.ocr.read_with_confidence(crop, track_id)
                state["last_ocr_frame"] = self.frame_index
                if plate_result:
                    state["plate"], state["plate_confidence"] = plate_result
                    if state["entry_sent"]:
                        self._send({
                            "event_type": "ENTRY",
                            "track_id": track_id,
                            "vehicle_category": category,
                            "plate_number": state["plate"],
                            "plate_confidence": state["plate_confidence"],
                            "slot_id": slot_id,
                        })

            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            elapsed = max(0.001, timestamp - state["previous_time"]) if state["previous_time"] else 0
            speed = (
                float(np.hypot(center[0] - state["previous_center"][0],
                               center[1] - state["previous_center"][1]))
                / max(1.0, y2 - y1)
                / elapsed
            ) if elapsed and state["previous_center"] else None
            previous_speed = state["speed"]
            state["decelerated"] = (
                previous_speed is not None
                and previous_speed >= 0.4
                and speed is not None
                and speed < max(0.12, previous_speed * 0.4)
            )
            state["speed"] = speed
            state["previous_center"] = center
            state["previous_time"] = timestamp
            crash_observations[track_id] = (box, center, state, category)
            self.crash_history[track_id] = {"box": box}
            self._draw_vehicle(frame, observation, state)

        self._report_collisions(crash_observations, frame)
        for track_id in list(self.track_state):
            if track_id not in current_tracks:
                state = self.track_state[track_id]
                state["missed_frames"] += 1
                if state["missed_frames"] >= config.EXIT_AFTER_MISSING_FRAMES:
                    if state["entry_sent"]:
                        self._send({
                            "event_type": "EXIT",
                            "track_id": track_id,
                            "vehicle_category": state["category"],
                            "plate_number": state["plate"],
                            "plate_confidence": state["plate_confidence"],
                            "slot_id": state.get("last_slot"),
                        })
                    self.zone_engine.forget(track_id)
                    self.track_state.pop(track_id, None)
                    self.crash_history.pop(track_id, None)
                    if self.ocr:
                        self.ocr.forget(track_id)

        self._draw_hud(frame, counts, sum(counts.values()))

        now = time()
        if now - self.last_occupancy_at >= 5:
            legacy_slots = [
                {"slotId": slot["slot_id"], "type": self._dashboard_slot_type(slot)}
                for slot in self.zone_map.slots
            ]
            if legacy_slots:
                self.dispatcher.publish({
                    "type": "occupancy",
                    "cameraId": self.camera_id,
                    "slots": legacy_slots,
                    "occupiedSlotIds": sorted(occupied),
                    "sourceMode": self.source_mode,
                    "detectionSummary": {
                        "total": sum(counts.values()),
                        "bikes": counts["TWO_WHEELER"],
                        "cars": counts["COMPACT_CAR"] + counts["SUV_SEDAN"] + counts["HEAVY_VEHICLE"],
                    },
                }, endpoint=f"{config.BACKEND_URL.rstrip('/')}/api/events")
            self.last_occupancy_at = now
        return frame

    def _send(self, payload):
        if self.source_mode == "video":
            return
        self.dispatcher.publish({
            "camera_id": self.camera_id,
            **payload,
        })

    def _send_alert(self, alert_type, track_id, category, state, slot_id, frame, message,
                    related_track_ids=None):
        if alert_type not in ALERT_TYPES or self.source_mode == "video":
            return
        snapshot_url = self._save_snapshot(frame)
        self.dispatcher.publish({
            "camera_id": self.camera_id,
            "track_id": track_id,
            "vehicle_category": category,
            "plate_number": state["plate"],
            "plate_confidence": state["plate_confidence"],
            "slot_id": slot_id,
            "event_type": "ALERT",
            "alert_type": alert_type,
            "snapshot_url": snapshot_url,
            "message": message,
            **({"related_track_ids": related_track_ids} if related_track_ids else {}),
        })

    def _save_snapshot(self, frame):
        filename = f"{uuid4()}.jpg"
        config.EVENT_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = config.EVENT_SNAPSHOT_DIR / filename
        if not cv2.imwrite(str(path), frame):
            logger.error("Could not save event snapshot: %s", path)
            return None
        return f"/media/alerts/{filename}"

    def _report_collisions(self, observations, frame):
        overlapping_pairs = set()
        reported_pairs = set()
        track_ids = list(observations)
        for index, track_id in enumerate(track_ids):
            box, _, state, category = observations[track_id]
            for other_id in track_ids[index + 1:]:
                other_box, _, other_state, _ = observations[other_id]
                pair = tuple(sorted((track_id, other_id)))
                if self._iou(box, other_box) <= 0.1:
                    continue
                overlapping_pairs.add(pair)
                if pair in self.active_collision_pairs:
                    continue
                if not (state["decelerated"] or other_state["decelerated"]):
                    continue
                self._send_alert(
                    "ACCIDENT", track_id, category, state, None, frame,
                    f"Possible collision involving tracks {track_id} and {other_id}",
                    related_track_ids=[other_id],
                )
                reported_pairs.add(pair)
        self.active_collision_pairs = (
            self.active_collision_pairs.intersection(overlapping_pairs) | reported_pairs
        )

    @staticmethod
    def _iou(first, second):
        left, top = max(first[0], second[0]), max(first[1], second[1])
        right, bottom = min(first[2], second[2]), min(first[3], second[3])
        intersection = max(0, right - left) * max(0, bottom - top)
        area_a = max(0, first[2] - first[0]) * max(0, first[3] - first[1])
        area_b = max(0, second[2] - second[0]) * max(0, second[3] - second[1])
        union = area_a + area_b - intersection
        return intersection / union if union else 0

    @staticmethod
    def _dashboard_slot_type(slot):
        return {
            "TWO_WHEELER": "bike",
            "COMPACT_CAR": "car",
            "SUV_SEDAN": "suv",
            "HEAVY_VEHICLE": "heavy_vehicle",
        }.get(slot.get("vehicle_category"), "car")

    @staticmethod
    def _draw_vehicle(frame, observation, state):
        x1, y1, x2, y2 = map(int, observation["box"])
        color = CATEGORY_COLORS[observation["category"]]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"#{observation['track_id']} {observation['category']} {observation['confidence']:.0%}"
        if state["plate"]:
            label += f" {state['plate']}"
        cv2.putText(frame, label, (x1, max(16, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    @staticmethod
    def _draw_hud(frame, counts, total):
        text = f"Vehicles {total} | 2W {counts['TWO_WHEELER']} | Cars {counts['COMPACT_CAR'] + counts['SUV_SEDAN']} | Heavy {counts['HEAVY_VEHICLE']}"
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 28), (15, 24, 38), -1)
        cv2.putText(frame, text, (10, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (245, 248, 250), 1)
