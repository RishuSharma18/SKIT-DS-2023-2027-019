"""Synthetic checks for the prototype crash heuristic: python tests_crash.py"""
import unittest

from app.crash import CrashDetector, report_crashes


def observations(positions, width=60, height=20):
    return {
        track_id: (
            (x - width / 2, y - height / 2, x + width / 2, y + height / 2),
            (x, y),
        )
        for track_id, (x, y) in positions.items()
    }


class CrashDetectorTests(unittest.TestCase):
    def setUp(self):
        self.detector = CrashDetector()

    def test_detects_overlapping_vehicles_that_both_suddenly_slow(self):
        self.detector.update(observations({1: (0, 0), 2: (30, 0)}))
        self.detector.update(observations({1: (10, 0), 2: (40, 0)}))
        self.detector.update(observations({1: (20, 0), 2: (50, 0)}))

        self.assertEqual(
            self.detector.update(observations({1: (21, 0), 2: (51, 0)})),
            [(1, 2)],
        )

    def test_does_not_detect_when_boxes_do_not_overlap(self):
        for first, second in ((0, 200), (10, 210), (20, 220), (21, 221)):
            crashes = self.detector.update(observations({1: (first, 0), 2: (second, 0)}))

        self.assertEqual(crashes, [])

    def test_does_not_detect_when_only_one_vehicle_suddenly_slows(self):
        self.detector.update(observations({1: (0, 0), 2: (30, 0)}))
        self.detector.update(observations({1: (10, 0), 2: (40, 0)}))
        self.detector.update(observations({1: (20, 0), 2: (50, 0)}))

        self.assertEqual(
            self.detector.update(observations({1: (21, 0), 2: (60, 0)})),
            [],
        )

    def test_reports_a_collision_only_once_while_boxes_remain_overlapping(self):
        self.detector.update(observations({1: (0, 0), 2: (30, 0)}))
        self.detector.update(observations({1: (10, 0), 2: (40, 0)}))
        self.detector.update(observations({1: (20, 0), 2: (50, 0)}))

        self.assertEqual(
            self.detector.update(observations({1: (21, 0), 2: (51, 0)})),
            [(1, 2)],
        )
        self.assertEqual(
            self.detector.update(observations({1: (21, 0), 2: (51, 0)})),
            [],
        )

    def test_resets_speed_history_after_track_is_missing(self):
        self.detector.update(observations({1: (0, 0), 2: (30, 0)}))
        self.detector.update(observations({1: (10, 0), 2: (40, 0)}))
        self.detector.update(observations({1: (20, 0)}))
        self.detector.update(observations({1: (21, 0), 2: (50, 0)}))

        self.assertEqual(
            self.detector.update(observations({1: (22, 0), 2: (51, 0)})),
            [],
        )

    def test_sends_backend_compatible_alert_with_both_track_ids(self):
        events = []
        send_event = lambda event_type, **payload: events.append((event_type, payload))
        for positions in (
            {1: (0, 0), 2: (30, 0)},
            {1: (10, 0), 2: (40, 0)},
            {1: (20, 0), 2: (50, 0)},
        ):
            report_crashes(self.detector, observations(positions), send_event)

        report_crashes(self.detector, observations({1: (21, 0), 2: (51, 0)}), send_event)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "crash")
        self.assertEqual(events[0][1]["trackIds"], [1, 2])
        self.assertIn("Possible collision", events[0][1]["message"])


if __name__ == "__main__":
    unittest.main()
