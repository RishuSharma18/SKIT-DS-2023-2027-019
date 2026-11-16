"""Main video loop: detect -> track -> classify -> OCR -> slot logic -> events."""
from time import monotonic

import cv2
import numpy as np

from . import config, events
from .crash import CrashDetector, report_crashes
from .detection import VehicleDetector
from .plate_reader import PlateReader
from .slots import SlotMap
from .vehicle import categorize


class Pipeline:
    def __init__(self):
        self.detector = VehicleDetector()
        self.slots = SlotMap(config.SLOTS_PATH)
        self.ocr = PlateReader() if config.ENABLE_OCR else None
        self.crash_detector = CrashDetector()
        self.tracks = {}   # track_id -> state dict
        self.last_occupancy = None
        self.last_attempted_occupancy = None
        self.last_occupancy_attempt_at = 0.0

    def run(self):
        """Generator: yields annotated BGR frames. Sends events as a side effect."""
        cap = cv2.VideoCapture(config.VIDEO_SOURCE)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(f"Unable to open configured video source: {config.VIDEO_SOURCE}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        frame_idx = 0
        stationary_frames = int(config.STATIONARY_SECONDS * fps)
        occupancy_retry_seconds = 5

        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1
            tracked = self.detector.track(frame)

            seen = set()
            crash_observations = {}
            if len(tracked):
                for track in tracked:
                    box = track[:4]
                    tid = int(track[4])
                    cls_id = int(track[6])
                    seen.add(tid)
                    x1, y1, x2, y2 = map(int, box)
                    centre = ((x1 + x2) / 2, y2 - (y2 - y1) * 0.15)  # near wheels
                    crash_observations[tid] = (box, centre)
                    st = self.tracks.setdefault(tid, {
                        "frames": 0, "missing": 0, "entered": False, "plate": None,
                        "cat": categorize(cls_id), "last": centre,
                        "still": 0, "slot": None, "slot_missing": 0,
                        "parked_sent": False,
                    })
                    st["frames"] += 1
                    st["missing"] = 0

                    # --- plate OCR every N frames until we have one
                    if self.ocr and st["entered"] and not st["plate"] and frame_idx % config.OCR_EVERY_N_FRAMES == 0:
                        crop = frame[y1 + (y2 - y1) // 2: y2, x1:x2]   # lower half of vehicle
                        plate = self.ocr.read(crop, tid)
                        if plate:
                            st["plate"] = plate
                            events.send("plate", trackId=tid, plate=plate)

                    # Confirm parking only after a stable dwell inside a configured bay.
                    moved = np.hypot(centre[0] - st["last"][0], centre[1] - st["last"][1])
                    stationary_limit = max(
                        config.STATIONARY_MIN_MOVEMENT,
                        (x2 - x1) * 0.025,
                    )
                    st["still"] = st["still"] + 1 if moved < stationary_limit else 0
                    st["last"] = centre
                    slot = self.slots.locate(centre, st["cat"])
                    if not st["entered"]:
                        if (slot and st["frames"] >= config.ENTRY_CONFIRM_FRAMES
                                and st["still"] >= stationary_frames):
                            st["entered"] = True
                            st["slot"] = slot["slotId"]
                            events.send("entry", trackId=tid, vehicleType=st["cat"])
                    elif slot and slot["slotId"] == st["slot"]:
                        st["slot_missing"] = 0
                    else:
                        st["slot_missing"] += 1
                        if slot is not None or st["slot_missing"] >= config.EXIT_AFTER_MISSING_FRAMES:
                            events.send("exit", trackId=tid)
                            st["entered"] = False
                            st["slot"] = None
                            st["slot_missing"] = 0
                            st["parked_sent"] = False

                    if (st["entered"] and slot and st["still"] >= stationary_frames
                            and not st["parked_sent"]):
                        st["slot"] = slot["slotId"]
                        st["parked_sent"] = True
                        events.send("parked", trackId=tid, slotId=slot["slotId"],
                                    plate=st["plate"], vehicleType=st["cat"])

                    color = (0, 0, 255) if st["slot"] else (255, 160, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"#{tid} {st['cat']} {st['plate'] or ''}"
                    cv2.putText(frame, label, (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            report_crashes(self.crash_detector, crash_observations, events.send)

            # --- exits: tracks not seen for a while
            for tid in list(self.tracks):
                if tid not in seen:
                    self.tracks[tid]["missing"] += 1
                    if self.tracks[tid]["missing"] >= config.EXIT_AFTER_MISSING_FRAMES:
                        if self.tracks[tid]["entered"]:
                            events.send("exit", trackId=tid)
                        del self.tracks[tid]

            occupied = {t["slot"] for t in self.tracks.values() if t["slot"]}
            occupied_key = tuple(sorted(occupied))
            occupancy_changed = occupied_key != self.last_occupancy
            now = monotonic()
            retry_due = now - self.last_occupancy_attempt_at >= occupancy_retry_seconds
            if retry_due or (occupancy_changed and occupied_key != self.last_attempted_occupancy):
                result = events.send(
                    "occupancy",
                    slots=[{"slotId": slot["slotId"], "type": slot["type"]} for slot in self.slots.slots],
                    occupiedSlotIds=list(occupied_key),
                    sourceMode=config.SOURCE_MODE,
                )
                self.last_occupancy_attempt_at = now
                self.last_attempted_occupancy = occupied_key
                if result is not None:
                    self.last_occupancy = occupied_key
            yield self.slots.draw(frame, occupied)

        cap.release()
