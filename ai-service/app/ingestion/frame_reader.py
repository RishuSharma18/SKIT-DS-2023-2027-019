"""Latest-frame video reader with file looping and network reconnection."""
from threading import Condition, Thread
from time import monotonic, sleep

import cv2

from .. import config


class FrameReader:
    def __init__(self, source, camera_id, reconnect_delay=2.0):
        self.source = source
        self.camera_id = camera_id
        self.reconnect_delay = reconnect_delay
        self._condition = Condition()
        self._latest = None
        self._sequence = 0
        self._stopped = False
        self.status = "connecting"
        self.error = None
        self._thread = Thread(target=self._read_loop, name=f"capture-{camera_id}", daemon=True)

    def start(self):
        self._thread.start()
        return self

    def read(self, after_sequence=0, timeout=5.0):
        deadline = monotonic() + timeout
        with self._condition:
            while not self._stopped and self._sequence <= after_sequence:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return None
                self._condition.wait(remaining)
            if self._sequence <= after_sequence or self._latest is None:
                return None
            sequence, frame = self._sequence, self._latest.copy()
            return sequence, frame

    def stop(self):
        with self._condition:
            self._stopped = True
            self._condition.notify_all()
        if self._thread.is_alive():
            self._thread.join(timeout=3)

    def _read_loop(self):
        is_file = isinstance(self.source, str) and config.source_mode(self.source) == "video"
        capture = None
        try:
            while not self._stopped:
                if capture is None or not capture.isOpened():
                    capture = cv2.VideoCapture(self.source)
                    if not capture.isOpened():
                        capture.release()
                        capture = None
                        self.status = "reconnecting"
                        self.error = "Unable to open camera source"
                        sleep(self.reconnect_delay)
                        continue

                ok, frame = capture.read()
                if not ok:
                    if is_file:
                        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ok, frame = capture.read()
                    if not ok:
                        capture.release()
                        capture = None
                        self.status = "reconnecting"
                        self.error = "Camera source did not return a frame"
                        sleep(self.reconnect_delay)
                        continue

                with self._condition:
                    self._sequence += 1
                    self._latest = frame
                    self.status = "online"
                    self.error = None
                    self._condition.notify_all()
        finally:
            if capture is not None:
                capture.release()
