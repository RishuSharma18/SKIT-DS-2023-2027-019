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

        font_scale = max(0.45, min(0.65, frame.shape[1] / 4000))
        legend = [
            ((255, 160, 0), "BLUE BOX: detected vehicle"),
            ((0, 0, 255), "RED BOX: parked in mapped bay"),
            ((0, 200, 0), "GREEN BAY: available"),
            ((0, 0, 255), "RED BAY: occupied"),
        ]
        line_height = max(20, int(27 * font_scale))
        panel_width = min(frame.shape[1] - 16, 1040)
        panel_height = line_height * len(legend) + 12
        x0, y0 = 8, max(8, frame.shape[0] - panel_height - 8)
        overlay = frame.copy()
        cv2.rectangle(overlay, (x0, y0), (x0 + panel_width, y0 + panel_height), (20, 28, 38), -1)
        cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)
        for index, (color, text) in enumerate(legend):
            y = y0 + 8 + (index + 1) * line_height
            cv2.rectangle(frame, (x0 + 10, y - line_height + 5), (x0 + 24, y - 4), color, -1)
            cv2.putText(frame, text, (x0 + 32, y), cv2.FONT_HERSHEY_SIMPLEX,
                        font_scale, (245, 248, 250), 1, cv2.LINE_AA)
        return frame
