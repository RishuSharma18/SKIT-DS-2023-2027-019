import json
import cv2
import numpy as np

# Which slot types can hold which vehicle category.
FIT = {"bike": {"bike"}, "car": {"car", "suv"}, "suv": {"suv"}}


class SlotMap:
    def __init__(self, path: str):
        with open(path) as f:
            data = json.load(f)
        self.slots = [
            {**s, "poly": np.array(s["polygon"], dtype=np.int32)} for s in data["slots"]
        ]

    def locate(self, point, category=None):
        """Return the slot containing `point` (and, if category given, that fits it)."""
        for s in self.slots:
            if cv2.pointPolygonTest(s["poly"], (float(point[0]), float(point[1])), False) >= 0:
                if category is None or s["type"] in FIT.get(category, {category}):
                    return s
        return None

    def draw(self, frame, occupied_ids):
        for s in self.slots:
            color = (0, 0, 255) if s["slotId"] in occupied_ids else (0, 200, 0)
            cv2.polylines(frame, [s["poly"]], True, color, 2)
            x, y = s["poly"][0]
            cv2.putText(frame, s["slotId"], (int(x), int(y) - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return frame
