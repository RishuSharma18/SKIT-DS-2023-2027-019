"""Plate OCR validation and response checks without loading EasyOCR weights."""
import unittest
from unittest.mock import patch

import cv2
import httpx
import numpy as np

from app import config
from app.main import app
from app.ocr.image_validation import UnsupportedImageError, decode_plate_image
from app.ocr.plate_reader import PlateReader, PlateVoteBuffer, normalize


assert normalize("RJ14 AB 1234") == "RJ14AB1234"
assert normalize("RJ14AB12O4") == "RJ14AB1204"
assert normalize("RJILCVO002") == "RJ14CV0002"
assert normalize("hello") is None

votes = PlateVoteBuffer(max_frames=5, min_votes=3)
assert votes.add(7, "RJ14AB1234", 0.8) is None
assert votes.add(7, "RJ14AB1234", 0.9) is None
assert votes.add(7, "RJ14AB1234", 1.0) == ("RJ14AB1234", 0.9)
votes.forget(7)
assert votes.add(7, "RJ14AB1234", 1.0) is None


class FakeReader:
    def recognize_plate_image(self, image):
        assert image.shape == (32, 96, 3)
        return {
            "success": True,
            "plate_detected": True,
            "text": "RJ14 AB 1234",
            "raw_text": "RJ14 AB 1234",
            "normalized_text": "RJ14AB1234",
            "confidence": 0.92,
            "is_low_confidence": False,
            "candidates": [{"text": "RJ14 AB 1234", "confidence": 0.92}],
            "error": None,
        }


def sample_png():
    ok, encoded = cv2.imencode(".png", np.zeros((32, 96, 3), dtype=np.uint8))
    assert ok
    return encoded.tobytes()


class PlateUploadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_ai_ocr_endpoint_requires_service_api_key(self):
        response = await self.client.post(
            "/ocr/plate",
            files={"file": ("plate.png", sample_png(), "image/png")},
        )
        self.assertEqual(response.status_code, 401)

    async def test_ai_ocr_endpoint_rejects_non_image_payload(self):
        response = await self.client.post(
            "/ocr/plate",
            headers={"x-api-key": config.API_KEY},
            files={"file": ("plate.png", b"not an image", "image/png")},
        )
        self.assertEqual(response.status_code, 415)

    async def test_ai_ocr_endpoint_returns_recognition_result(self):
        with patch("app.main.get_plate_reader", return_value=FakeReader()):
            response = await self.client.post(
                "/ocr/plate",
                headers={"x-api-key": config.API_KEY},
                files={"file": ("plate.png", sample_png(), "image/png")},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["raw_text"], "RJ14 AB 1234")
        self.assertEqual(response.json()["normalized_text"], "RJ14AB1234")


class PlateImageValidationTests(unittest.TestCase):
    def test_decodes_supported_image_signatures(self):
        image = decode_plate_image(sample_png())
        self.assertEqual(image.shape, (32, 96, 3))

    def test_rejects_unknown_file_signatures(self):
        with self.assertRaises(UnsupportedImageError):
            decode_plate_image(b"not an image")

    def test_ocr_keeps_raw_text_separate_from_normalized_suggestion(self):
        class FakeEasyOCR:
            def readtext(self, image, **kwargs):
                return [([], "RJ14 AB 1234", 0.91)]

        reader = PlateReader.__new__(PlateReader)
        reader.reader = FakeEasyOCR()
        reader.plate_model = None
        image = np.full((80, 320, 3), 255, dtype=np.uint8)
        result = reader.recognize_plate_image(image)
        self.assertEqual(result["raw_text"], "RJ14 AB 1234")
        self.assertEqual(result["normalized_text"], "RJ14AB1234")
        self.assertTrue(result["plate_detected"])

    def test_plate_region_detection_is_bounded_and_finds_horizontal_plate(self):
        image = np.full((300, 600, 3), 245, dtype=np.uint8)
        cv2.rectangle(image, (180, 110), (420, 175), (20, 20, 20), 3)
        cv2.putText(
            image,
            "RJ14CV0002",
            (190, 155),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.1,
            (10, 10, 10),
            2,
            cv2.LINE_AA,
        )
        regions = PlateReader._plate_image_regions(image)
        self.assertLessEqual(len(regions), 5)
        self.assertTrue(any(region.shape[1] > region.shape[0] * 2 for region in regions))

    def test_extracts_valid_plate_from_other_ocr_text(self):
        results = [
            ([], "PARKING OPERATIONS", 0.9),
            ([], "RJILCVOOO2", 0.42),
        ]
        self.assertEqual(PlateReader._recognized_plate(results), "RJ14CV0002")

    def test_uploaded_screenshot_uses_plate_region_without_detection_model(self):
        image = np.full((300, 600, 3), 245, dtype=np.uint8)
        cv2.rectangle(image, (180, 110), (420, 175), (20, 20, 20), 3)
        cv2.putText(
            image,
            "RJ14CV0002",
            (190, 155),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.1,
            (10, 10, 10),
            2,
            cv2.LINE_AA,
        )

        class FakeEasyOCR:
            input_shapes = []

            def readtext(self, crop, **kwargs):
                self.input_shapes.append(crop.shape[:2])
                return [([], "RJ14CV0002", 0.91)]

        reader = PlateReader.__new__(PlateReader)
        reader.reader = FakeEasyOCR()
        reader.plate_model = None
        result = reader.recognize_plate_image(image)

        self.assertEqual(result["normalized_text"], "RJ14CV0002")
        self.assertLess(reader.reader.input_shapes[0][1], image.shape[1] * 2)


if __name__ == "__main__":
    unittest.main()
