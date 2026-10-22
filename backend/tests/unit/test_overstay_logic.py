import unittest
from datetime import datetime, timezone, timedelta

class TestOverstayWorkerLogic(unittest.TestCase):
    """Unit tests for overstay daemon worker threshold evaluations."""

    MAX_ALLOWED_DURATION_MINUTES = 240.0

    def evaluate_session(self, entry_dt: datetime, now_dt: datetime, already_alerted: bool):
        duration = (now_dt - entry_dt).total_seconds() / 60.0
        should_alert = False
        new_status = "ACTIVE"

        if duration >= self.MAX_ALLOWED_DURATION_MINUTES:
            new_status = "OVERSTAY"
            if not already_alerted:
                should_alert = True

        return {
            "duration_minutes": round(duration, 2),
            "status": new_status,
            "trigger_alert": should_alert
        }

    def test_under_threshold(self):
        now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
        entry = now - timedelta(minutes=180)
        res = self.evaluate_session(entry, now, already_alerted=False)
        self.assertEqual(res["status"], "ACTIVE")
        self.assertFalse(res["trigger_alert"])

    def test_overstay_first_trigger(self):
        now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
        entry = now - timedelta(minutes=245)
        res = self.evaluate_session(entry, now, already_alerted=False)
        self.assertEqual(res["status"], "OVERSTAY")
        self.assertTrue(res["trigger_alert"])

    def test_overstay_deduplication(self):
        now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
        entry = now - timedelta(minutes=250)
        # Already alerted in a previous cycle
        res = self.evaluate_session(entry, now, already_alerted=True)
        self.assertEqual(res["status"], "OVERSTAY")
        self.assertFalse(res["trigger_alert"])  # No duplicate alert

if __name__ == "__main__":
    unittest.main()
