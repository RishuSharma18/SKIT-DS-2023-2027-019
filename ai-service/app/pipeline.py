"""Single-source CLI pipeline using backend-managed camera zones."""
import cv2

from . import config
from .analytics.processor import VideoProcessor
from .api.event_dispatcher import EventDispatcher
from .api.zones_client import fetch_zone_map


class Pipeline:
    def __init__(self):
        self.dispatcher = EventDispatcher()

    def run(self):
        """Yield annotated frames from the configured primary camera source."""
        cap = cv2.VideoCapture(config.VIDEO_SOURCE)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(f"Unable to open configured video source: {config.VIDEO_SOURCE}")
        try:
            zones = fetch_zone_map(config.CAMERA_ID)
            processor = VideoProcessor(
                config.CAMERA_ID,
                config.VIDEO_SOURCE,
                config.source_mode(config.VIDEO_SOURCE),
                zones,
                self.dispatcher,
            )
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                yield processor.process(frame)
        finally:
            cap.release()
            self.dispatcher.close()
