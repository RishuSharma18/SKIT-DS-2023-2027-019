"""Main video loop: detect -> track -> classify -> OCR -> slot logic -> events."""
import time
import cv2
import numpy as np
from ultralytics import YOLO

from . import config, events
from .plate_reader import PlateReader
from .slots import SlotMap

CLASS_TO_CATEGORY = {2: "car", 3: "bike", 5: "suv", 7: "suv"}


class Pipeline:
    def __init__(self):
        self.model = YOLO(config.YOLO_MODEL)
        self.slots = SlotMap(config.SLOTS_FILE)
        self.ocr = PlateReader()
        self.tracks = {}   # track_id -> state dict

    def _category(self, cls_id, box, frame_area):
        cat = CLASS_TO_CATEGORY.get(cls_id, "car")
        if cat == "car":   # YOLO/COCO has no SUV class -> use relative size
            x1, y1, x2, y2 = box
            if (x2 - x1) * (y2 - y1) / frame_area > config.SUV_AREA_RATIO:
                cat = "suv"
        return cat

    def run(self):
        """Generator: yields annotated BGR frames. Sends events as a side effect."""
        cap = cv2.VideoCapture(config.VIDEO_SOURCE)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        frame_idx = 0
        stationary_frames = int(config.STATIONARY_SECONDS * fps)
        wrong_frames = int(config.WRONG_PARK_SECONDS * fps)

        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1
            h, w = frame.shape[:2]

            res = self.model.track(
                frame, persist=True, classes=config.VEHICLE_CLASSES,
                tracker="bytetrack.yaml", conf=config.CONFIDENCE, verbose=False,
            )[0]

            seen = set()
            if res.boxes is not None and res.boxes.id is not None:
                boxes = res.boxes.xyxy.cpu().numpy()
                ids = res.boxes.id.int().cpu().tolist()
                clss = res.boxes.cls.int().cpu().tolist()
                for box, tid, cls_id in zip(boxes, ids, clss):
                    seen.add(tid)
                    x1, y1, x2, y2 = map(int, box)
                    centre = ((x1 + x2) / 2, y2 - (y2 - y1) * 0.15)  # near wheels
                    st = self.tracks.setdefault(tid, {
                        "frames": 0, "missing": 0, "entered": False, "plate": None,
                        "cat": self._category(cls_id, box, w * h), "last": centre,
                        "still": 0, "slot": None, "wrong_sent": False,
                    })
                    st["frames"] += 1
                    st["missing"] = 0

                    # --- entry (confirmed after N frames to ignore flicker)
                    if not st["entered"] and st["frames"] >= config.ENTRY_CONFIRM_FRAMES:
                        st["entered"] = True
                        events.send("entry", trackId=tid, vehicleType=st["cat"])

                    # --- plate OCR every N frames until we have one
                    if st["entered"] and not st["plate"] and frame_idx % config.OCR_EVERY_N_FRAMES == 0:
                        crop = frame[y1 + (y2 - y1) // 2: y2, x1:x2]   # lower half of vehicle
                        plate = self.ocr.read(crop, tid)
                        if plate:
                            st["plate"] = plate
                            events.send("plate", trackId=tid, plate=plate)

                    # --- stationary => parked? in a valid slot or wrong parking?
                    moved = np.hypot(centre[0] - st["last"][0], centre[1] - st["last"][1])
                    st["still"] = st["still"] + 1 if moved < 3 else 0
                    st["last"] = centre
                    if st["entered"] and st["still"] == stationary_frames:
                        slot = self.slots.locate(centre, st["cat"])
                        if slot:
                            st["slot"] = slot["slotId"]
                            events.send("parked", trackId=tid, slotId=slot["slotId"],
                                        plate=st["plate"], vehicleType=st["cat"])
                    if (st["entered"] and st["still"] >= wrong_frames
                            and not st["slot"] and not st["wrong_sent"]):
                        st["wrong_sent"] = True
                        events.send("wrong_parking", trackId=tid, plate=st["plate"])

                    color = (0, 0, 255) if st["wrong_sent"] else (255, 160, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"#{tid} {st['cat']} {st['plate'] or ''}"
                    cv2.putText(frame, label, (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # --- exits: tracks not seen for a while
            for tid in list(self.tracks):
                if tid not in seen:
                    self.tracks[tid]["missing"] += 1
                    if self.tracks[tid]["missing"] >= config.EXIT_AFTER_MISSING_FRAMES:
                        if self.tracks[tid]["entered"]:
                            events.send("exit", trackId=tid)
                        del self.tracks[tid]

            occupied = {t["slot"] for t in self.tracks.values() if t["slot"]}
            yield self.slots.draw(frame, occupied)

        cap.release()
