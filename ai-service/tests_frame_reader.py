"""Frame reader reconnect smoke test using a fake OpenCV capture."""
import time
import unittest
from unittest.mock import patch

import numpy as np

from app.ingestion.frame_reader import FrameReader


class FakeCapture:
    instances = []

    def __init__(self, source):
        self.source = source
        self.open = len(FakeCapture.instances) > 0
        self.released = False
        FakeCapture.instances.append(self)

    def isOpened(self):
        return self.open

    def read(self):
        return True, np.full((2, 2, 3), 7, dtype=np.uint8)

    def release(self):
        self.released = True


class FrameReaderTests(unittest.TestCase):
    def test_network_source_retries_failed_open_and_publishes_latest_frame(self):
        FakeCapture.instances = []
        with patch("app.ingestion.frame_reader.cv2.VideoCapture", FakeCapture):
            reader = FrameReader("rtsp://camera.invalid/stream", "test-camera", reconnect_delay=0.01)
            reader.start()
            try:
                latest = reader.read(timeout=2)
                self.assertIsNotNone(latest)
                self.assertEqual(latest[1][0, 0, 0], 7)
                self.assertGreaterEqual(len(FakeCapture.instances), 2)
                self.assertTrue(FakeCapture.instances[0].released)
            finally:
                reader.stop()
        self.assertTrue(FakeCapture.instances[-1].released)


if __name__ == "__main__":
    unittest.main()
