"""Prototype crash heuristic based on overlapping boxes and sudden deceleration."""
from itertools import combinations
from math import hypot


def report_crashes(detector, observations, send_event):
    """Detect collisions and send backend-compatible alert events."""
    crashes = detector.update(observations)
    for first, second in crashes:
        send_event(
            "crash",
            trackIds=[first, second],
            message=f"Possible collision between tracks {first} and {second}",
        )
    return crashes


class CrashDetector:
    def __init__(
        self,
        overlap_threshold=0.1,
        min_speed=3.0,
        speed_drop_ratio=0.5,
    ):
        self.overlap_threshold = overlap_threshold
        self.min_speed = min_speed
        self.speed_drop_ratio = speed_drop_ratio
        self._tracks = {}
        self._reported_pairs = set()

    def update(self, observations):
        """Return track-ID pairs that overlap while both suddenly decelerate.

        `observations` maps each track ID to `(box, center)`, both in pixels.
        Speed is measured as centroid pixels per frame.
        """
        speeds = {}
        for track_id, (box, center) in observations.items():
            center = tuple(center)
            previous = self._tracks.get(track_id)
            if previous is not None:
                speed = hypot(center[0] - previous["center"][0],
                              center[1] - previous["center"][1])
                previous_speed = previous["speed"]
                if previous_speed is not None:
                    speeds[track_id] = (
                        previous_speed >= self.min_speed
                        and speed <= previous_speed * self.speed_drop_ratio
                    )
            else:
                speed = None

            self._tracks[track_id] = {"box": tuple(box), "center": center, "speed": speed}

        overlapping_pairs = set()
        crashes = []
        track_ids = list(observations)
        for first, second in combinations(track_ids, 2):
            pair = frozenset((first, second))
            if self._iou(self._tracks[first]["box"], self._tracks[second]["box"]) < self.overlap_threshold:
                continue

            overlapping_pairs.add(pair)
            if speeds.get(first, False) and speeds.get(second, False) and pair not in self._reported_pairs:
                crashes.append(tuple(sorted((first, second), key=str)))

        self._reported_pairs.intersection_update(overlapping_pairs)
        self._reported_pairs.update(frozenset(pair) for pair in crashes)

        # A track missing in this frame has no reliable consecutive-frame speed.
        self._tracks = {track_id: state for track_id, state in self._tracks.items()
                        if track_id in observations}
        return crashes

    @staticmethod
    def _iou(first, second):
        left = max(first[0], second[0])
        top = max(first[1], second[1])
        right = min(first[2], second[2])
        bottom = min(first[3], second[3])
        intersection = max(0.0, right - left) * max(0.0, bottom - top)
        first_area = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
        second_area = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
        union = first_area + second_area - intersection
        return intersection / union if union > 0 else 0.0
