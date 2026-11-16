"""Per-camera ByteTrack state; never share a tracker across camera streams."""
from pathlib import Path
from types import SimpleNamespace

import yaml
from ultralytics.trackers.byte_tracker import BYTETracker


class CameraTracker:
    def __init__(self, tracker_config="bytetrack.yaml", frame_rate=30):
        if tracker_config.endswith(".yaml") and Path(tracker_config).is_file():
            tracker_path = Path(tracker_config)
        else:
            import ultralytics
            tracker_path = Path(ultralytics.__file__).resolve().parent / "cfg" / "trackers" / tracker_config
        with tracker_path.open(encoding="utf-8") as tracker_file:
            args = yaml.safe_load(tracker_file)
        args["frame_rate"] = frame_rate
        self.tracker = BYTETracker(SimpleNamespace(**args))

    def update(self, boxes, frame):
        return self.tracker.update(boxes, img=frame)
