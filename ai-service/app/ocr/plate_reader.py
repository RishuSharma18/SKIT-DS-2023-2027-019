"""Plate OCR with image preprocessing and bounded temporal voting per track."""
from collections import Counter, defaultdict, deque
import re

import cv2

from .. import config

PLATE_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$")
_TO_DIGIT = {"O": "0", "I": "1", "Z": "2", "S": "5", "B": "8"}
_TO_LETTER = {value: key for key, value in _TO_DIGIT.items()}


def normalize(text):
    cleaned = re.sub(r"[^A-Z0-9]", "", text.upper())
    if len(cleaned) < 9 or len(cleaned) > 11:
        return None
    chars = list(cleaned)
    for index in (0, 1):
        chars[index] = _TO_LETTER.get(chars[index], chars[index])
    for index in (2, 3):
        chars[index] = _TO_DIGIT.get(chars[index], chars[index])
    for index in range(len(chars) - 4, len(chars)):
        chars[index] = _TO_DIGIT.get(chars[index], chars[index])
    normalized = "".join(chars)
    return normalized if PLATE_RE.fullmatch(normalized) else None


class PlateVoteBuffer:
    def __init__(self, max_frames=config.OCR_VOTE_FRAMES, min_votes=3):
        self.max_frames = max_frames
        self.min_votes = min(min_votes, max_frames)
        self._votes = defaultdict(lambda: deque(maxlen=self.max_frames))

    def add(self, track_id, plate, confidence):
        if plate:
            self._votes[track_id].append((plate, float(confidence)))
        votes = self._votes.get(track_id, ())
        counts = Counter(value for value, _ in votes)
        if not counts:
            return None
        selected, count = counts.most_common(1)[0]
        if count < self.min_votes:
            return None
        score = sum(score for value, score in votes if value == selected) / count
        return selected, score

    def forget(self, track_id):
        self._votes.pop(track_id, None)


class PlateReader:
    def __init__(self):
        import easyocr

        self.reader = easyocr.Reader(["en"], gpu=False)
        self.plate_model = None
        if config.PLATE_MODEL:
            from ultralytics import YOLO

            self.plate_model = YOLO(config.PLATE_MODEL)
        self.votes = PlateVoteBuffer()

    @staticmethod
    def _candidates(crop):
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        scale = max(2, min(4, 240 // max(1, gray.shape[1])))
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        threshold = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
        )
        return gray, threshold

    def _plate_crops(self, crop):
        if self.plate_model is None:
            return [crop]
        predictions = self.plate_model.predict(crop, conf=0.25, verbose=False)
        crops = []
        if predictions and predictions[0].boxes is not None:
            height, width = crop.shape[:2]
            for box in predictions[0].boxes.xyxy.cpu().numpy():
                x1, y1, x2, y2 = map(int, box)
                plate_crop = crop[max(0, y1):min(height, y2), max(0, x1):min(width, x2)]
                if plate_crop.size:
                    crops.append(plate_crop)
        return crops

    def read_with_confidence(self, crop, track_id):
        if crop is None or crop.size == 0:
            return None
        candidates = []
        for plate_crop in self._plate_crops(crop):
            for image in self._candidates(plate_crop):
                for _, text, confidence in self.reader.readtext(image):
                    plate = normalize(text)
                    if plate and confidence >= 0.3:
                        candidates.append((plate, float(confidence)))
        best = max(candidates, key=lambda item: item[1]) if candidates else (None, 0)
        return self.votes.add(track_id, best[0], best[1])

    def read(self, crop, track_id):
        result = self.read_with_confidence(crop, track_id)
        return result[0] if result else None

    def forget(self, track_id):
        self.votes.forget(track_id)
