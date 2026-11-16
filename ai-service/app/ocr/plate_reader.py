"""Plate OCR with image preprocessing and bounded temporal voting per track."""
from collections import Counter, defaultdict, deque
import re

import cv2

from .. import config

PLATE_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$")
BH_PLATE_RE = re.compile(r"^\d{2}BH\d{4}[A-Z]{1,2}$")
STD_PLATE_RE = re.compile(
    r"^(?:AN|AP|AR|AS|BR|CG|CH|DD|DL|DN|GA|GJ|HP|HR|JH|JK|KA|KL|"
    r"LA|LD|MH|ML|MN|MP|MZ|NL|OD|PB|PY|RJ|SK|TN|TR|TS|UK|UP|WB)"
    r"\d{1,2}[A-Z]{1,3}\d{1,4}$"
)
_TO_DIGIT = {"O": "0", "I": "1", "L": "4", "G": "4", "Z": "2", "S": "5", "B": "8"}
_TO_LETTER = {value: key for key, value in _TO_DIGIT.items()}


def normalize(text):
    if not text:
        return None
    cleaned = re.sub(r"[^A-Z0-9]", "", text.upper())
    if len(cleaned) < 8 or len(cleaned) > 12:
        return None
    chars = list(cleaned)
    for index in (0, 1):
        chars[index] = _TO_LETTER.get(chars[index], chars[index])
    for index in (2, 3):
        chars[index] = _TO_DIGIT.get(chars[index], chars[index])
    for index in range(len(chars) - 4, len(chars)):
        chars[index] = _TO_DIGIT.get(chars[index], chars[index])
    normalized = "".join(chars)
    if PLATE_RE.fullmatch(normalized) or BH_PLATE_RE.fullmatch(cleaned) or STD_PLATE_RE.fullmatch(cleaned):
        return normalized if PLATE_RE.fullmatch(normalized) else cleaned
    return None


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

        model_dir = str(config.EASYOCR_MODEL_DIR)
        self.reader = easyocr.Reader(
            ["en"],
            gpu=False,
            model_storage_directory=model_dir,
            user_network_directory=model_dir,
            download_enabled=False,
        )
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

    @staticmethod
    def _plate_image_regions(image, max_regions=3):
        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        masks = [
            cv2.Canny(gray, 30, 120),
            cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)[1],
            cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1],
        ]
        candidates = []
        minimum_area = max(1200, int(width * height * 0.001))
        maximum_area = int(width * height * 0.35)
        for mask in masks:
            for kernel_width in (7, 13):
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 3))
                joined = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                contours, _ = cv2.findContours(
                    joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                for contour in contours:
                    x, y, region_width, region_height = cv2.boundingRect(contour)
                    area = region_width * region_height
                    aspect = region_width / max(1, region_height)
                    if (
                        region_width < 60
                        or region_height < 15
                        or not 2.0 <= aspect <= 7.0
                        or not minimum_area <= area <= maximum_area
                    ):
                        continue
                    padding_x = max(2, int(region_width * 0.04))
                    padding_y = max(2, int(region_height * 0.12))
                    left = max(0, x - padding_x)
                    top = max(0, y - padding_y)
                    right = min(width, x + region_width + padding_x)
                    bottom = min(height, y + region_height + padding_y)
                    box = (left, top, right, bottom)
                    if any(
                        PlateReader._box_iou(box, existing) > 0.75
                        for _, existing in candidates
                    ):
                        continue
                    region = image[top:bottom, left:right]
                    saturation = cv2.cvtColor(
                        region, cv2.COLOR_BGR2HSV
                    )[:, :, 1].mean() / 255
                    score = abs(aspect - 3.5) - min(
                        area / max(1.0, width * height * 0.02), 1.0
                    ) * 0.4 + saturation * 1.5
                    candidates.append((score, box))

        candidates.sort(key=lambda item: item[0])
        return [
            image[top:bottom, left:right]
            for _, (left, top, right, bottom) in candidates[:max_regions]
        ]

    @staticmethod
    def _box_iou(first, second):
        left = max(first[0], second[0])
        top = max(first[1], second[1])
        right = min(first[2], second[2])
        bottom = min(first[3], second[3])
        intersection = max(0, right - left) * max(0, bottom - top)
        first_area = (first[2] - first[0]) * (first[3] - first[1])
        second_area = (second[2] - second[0]) * (second[3] - second[1])
        union = first_area + second_area - intersection
        return intersection / union if union else 0

    @staticmethod
    def _recognized_plate(results):
        candidates = []
        for _, text, confidence in results:
            for token in re.findall(r"[A-Z0-9]+", text.upper()):
                plate = normalize(token)
                if plate:
                    candidates.append((float(confidence), plate))
        return max(candidates, default=(0.0, None))[1]

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

    def recognize_plate_image(self, image_or_bytes):
        """Process a standalone uploaded plate image.

        Returns structured dictionary with recognized text, normalized text,
        confidence, and ranked alternative candidates. Zero image retention.
        """
        image = image_or_bytes

        if image is None or not getattr(image, "size", 0):
            return {
                "success": False,
                "plate_detected": False,
                "text": None,
                "raw_text": None,
                "normalized_text": None,
                "confidence": 0.0,
                "is_low_confidence": True,
                "candidates": [],
                "error": "Could not decode image or image is empty.",
            }

        detected_items = {}
        plate_crops = self._plate_crops(image) if self.plate_model is not None else []
        crops = plate_crops or self._plate_image_regions(image) or [image]
        for crop in crops:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            scale = max(2, min(3, 900 // max(1, max(gray.shape[:2]))))
            if scale > 1:
                gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
            blur = cv2.GaussianBlur(gray, (3, 3), 0)
            _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            padded_gray = cv2.copyMakeBorder(
                blur, 16, 16, 24, 24, cv2.BORDER_CONSTANT, value=255
            )
            padded_otsu = cv2.copyMakeBorder(
                otsu, 16, 16, 24, 24, cv2.BORDER_CONSTANT, value=255
            )
            results = self.reader.readtext(
                padded_gray,
                allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                detail=1,
                paragraph=False,
            )
            raw_text = " ".join(text.strip() for _, text, _ in results if text.strip())
            confidence_values = [float(conf) for _, text, conf in results if text.strip()]
            if raw_text and confidence_values:
                detected_items[raw_text] = (
                    sum(confidence_values) / len(confidence_values),
                    self._recognized_plate(results),
                )
                if detected_items[raw_text][1]:
                    break

            if not results:
                results = self.reader.readtext(
                    padded_otsu,
                    allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                    detail=1,
                    paragraph=False,
                )
                raw_text = " ".join(text.strip() for _, text, _ in results if text.strip())
                confidence_values = [float(conf) for _, text, conf in results if text.strip()]
                if raw_text and confidence_values:
                    detected_items[raw_text] = (
                        sum(confidence_values) / len(confidence_values),
                        self._recognized_plate(results),
                    )
                    if detected_items[raw_text][1]:
                        break

        if not detected_items:
            return {
                "success": True,
                "plate_detected": False,
                "text": None,
                "raw_text": None,
                "normalized_text": None,
                "confidence": 0.0,
                "is_low_confidence": True,
                "candidates": [],
                "error": "No plate or text could be detected in the image.",
            }

        ranked_candidates = sorted(
            [{"text": text, "confidence": round(confidence, 3)}
             for text, (confidence, _) in detected_items.items()],
            key=lambda c: c["confidence"],
            reverse=True,
        )

        best_candidate = next(
            (
                candidate for candidate in ranked_candidates
                if detected_items[candidate["text"]][1]
            ),
            ranked_candidates[0],
        )
        normalized_plate = (
            detected_items[best_candidate["text"]][1]
            or normalize(best_candidate["text"])
        )

        confidence = float(best_candidate["confidence"])
        is_low = confidence < config.OCR_CONFIDENCE_THRESHOLD or normalized_plate is None

        return {
            "success": True,
            "plate_detected": normalized_plate is not None,
            "text": best_candidate["text"],
            "raw_text": best_candidate["text"],
            "normalized_text": normalized_plate,
            "confidence": round(confidence, 3),
            "is_low_confidence": is_low,
            "candidates": ranked_candidates[:10],
            "error": None if normalized_plate else "Text was read, but no valid plate format could be confirmed.",
        }
