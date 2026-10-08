import re
from collections import Counter, defaultdict

import cv2

# Indian format: 2 letters, 2 digits, 1-3 letters, 4 digits  (e.g. RJ14AB1234)
PLATE_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$")
_TO_DIGIT = {"O": "0", "I": "1", "Z": "2", "S": "5", "B": "8"}
_TO_LETTER = {v: k for k, v in _TO_DIGIT.items()}


def normalize(text: str):
    """Clean OCR text and fix common letter/digit confusions by position."""
    t = re.sub(r"[^A-Z0-9]", "", text.upper())
    if len(t) < 9 or len(t) > 11:
        return None
    chars = list(t)
    for i in (0, 1):                      # state code -> letters
        chars[i] = _TO_LETTER.get(chars[i], chars[i])
    for i in (2, 3):                      # district code -> digits
        chars[i] = _TO_DIGIT.get(chars[i], chars[i])
    for i in range(len(chars) - 4, len(chars)):   # last 4 -> digits
        chars[i] = _TO_DIGIT.get(chars[i], chars[i])
    t = "".join(chars)
    return t if PLATE_RE.match(t) else None


class PlateReader:
    def __init__(self):
        import easyocr  # heavy import, so keep it lazy
        self.reader = easyocr.Reader(["en"], gpu=False)
        self.votes = defaultdict(Counter)   # track_id -> Counter(plate)

    @staticmethod
    def _prep(crop):
        g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)

    def read(self, crop, track_id):
        """Run OCR on a vehicle crop; return a plate once 2 reads agree."""
        if crop is None or crop.size == 0:
            return None
        for _, text, conf in self.reader.readtext(self._prep(crop)):
            plate = normalize(text)
            if plate and conf > 0.3:
                self.votes[track_id][plate] += 1
        if self.votes[track_id]:
            plate, n = self.votes[track_id].most_common(1)[0]
            if n >= 2:
                return plate
        return None
