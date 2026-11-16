"""Concurrent per-camera workers that publish the latest annotated MJPEG frame."""
from threading import Condition, Event, Thread
from time import time

import cv2

from ..analytics.processor import VideoProcessor
from .. import config
from ..ingestion.frame_reader import FrameReader
from .zones_client import fetch_zone_map


class CameraWorker:
    def __init__(self, camera_id, source, dispatcher):
        self.camera_id = camera_id
        self.source = source
        self.dispatcher = dispatcher
        self.source_mode = config.source_mode(source)
        self.status = "starting"
        self.error = None
        self.processor = None
        self.reader = None
        self._condition = Condition()
        self._stop_event = Event()
        self._frame_index = 0
        self._jpeg = None
        self._stopped = False
        self._thread = Thread(target=self._run, name=f"camera-{camera_id}", daemon=True)

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._stopped = True
        self._stop_event.set()
        if self.reader:
            self.reader.stop()
        with self._condition:
            self._condition.notify_all()
        if self._thread.is_alive():
            self._thread.join(timeout=3)

    def latest(self, after_frame=0, timeout=5.0):
        with self._condition:
            self._condition.wait_for(
                lambda: self._stopped or self._frame_index > after_frame,
                timeout=timeout,
            )
            if self._frame_index <= after_frame or self._jpeg is None:
                return None
            return self._frame_index, self._jpeg

    def iter_mjpeg(self):
        frame_index = 0
        while not self._stopped:
            latest = self.latest(frame_index, timeout=10)
            if latest is None:
                if self.error:
                    break
                continue
            frame_index, jpeg = latest
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"

    def _run(self):
        sequence = 0
        try:
            zones = None
            while not self._stopped and zones is None:
                try:
                    zones = fetch_zone_map(self.camera_id)
                except RuntimeError as error:
                    self.status = "reconnecting"
                    self.error = str(error)
                    if self._stop_event.wait(5):
                        return
            if self._stopped:
                return
            self.processor = VideoProcessor(
                self.camera_id, self.source, self.source_mode, zones, self.dispatcher
            )
            self.error = None
            self.reader = FrameReader(self.source, self.camera_id).start()
            while not self._stopped:
                latest = self.reader.read(after_sequence=sequence, timeout=2)
                if latest is None:
                    self.status = self.reader.status
                    continue
                sequence, frame = latest
                annotated = self.processor.process(frame, captured_at=time())
                ok, encoded = cv2.imencode(".jpg", annotated)
                if not ok:
                    raise RuntimeError(f"Could not encode camera frame for {self.camera_id}")
                with self._condition:
                    self._frame_index += 1
                    self._jpeg = encoded.tobytes()
                    self.status = "online"
                    self.error = None
                    self._condition.notify_all()
        except Exception as error:
            self.status = "error"
            self.error = str(error)
        finally:
            if self.reader:
                self.reader.stop()


class StreamManager:
    def __init__(self, streams=None, dispatcher=None):
        self.streams = streams or config.CAMERA_STREAMS
        self.dispatcher = dispatcher
        self.workers = {}

    def start(self):
        for camera_id, source in self.streams.items():
            self.workers[camera_id] = CameraWorker(camera_id, source, self.dispatcher).start()
        return self

    def stop(self):
        for worker in self.workers.values():
            worker.stop()

    def get(self, camera_id):
        return self.workers.get(camera_id)

    def health(self):
        return [
            {
                "cameraId": camera_id,
                "sourceMode": worker.source_mode,
                "status": worker.status,
                "error": worker.error or (worker.reader.error if worker.reader else None),
                "configuredSlotIds": [
                    slot["slot_id"] for slot in worker.processor.zone_map.slots
                ] if worker.processor else [],
                "configuredSlots": [
                    {
                        "slotId": slot["slot_id"],
                        "type": {
                            "TWO_WHEELER": "bike",
                            "COMPACT_CAR": "car",
                            "SUV_SEDAN": "suv",
                            "HEAVY_VEHICLE": "heavy_vehicle",
                        }.get(slot.get("vehicle_category"), "car"),
                    }
                    for slot in worker.processor.zone_map.slots
                ] if worker.processor else [],
            }
            for camera_id, worker in self.workers.items()
        ]
