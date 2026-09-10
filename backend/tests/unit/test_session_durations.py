import unittest
from datetime import datetime, timezone, timedelta

class TestSessionDurationCalculations(unittest.TestCase):
    """Unit tests for precise session duration and overstay threshold logic."""

    @staticmethod
    def compute_duration_minutes(entry_dt: datetime, exit_dt: datetime) -> float:
        delta = exit_dt - entry_dt
        return round(delta.total_seconds() / 60.0, 2)

    @staticmethod
    def is_overstay(entry_dt: datetime, now_dt: datetime, threshold_minutes: float = 240.0) -> bool:
        duration = (now_dt - entry_dt).total_seconds() / 60.0
        return duration >= threshold_minutes

    def test_standard_duration(self):
        entry = datetime(2026, 9, 10, 9, 0, 0, tzinfo=timezone.utc)
        exit_ = datetime(2026, 9, 10, 11, 45, 30, tzinfo=timezone.utc)
        # 2 hours 45 mins 30 secs = 165.5 minutes
        self.assertEqual(self.compute_duration_minutes(entry, exit_), 165.5)

    def test_overnight_duration(self):
        entry = datetime(2026, 9, 10, 23, 0, 0, tzinfo=timezone.utc)
        exit_ = datetime(2026, 9, 11, 7, 0, 0, tzinfo=timezone.utc)
        # 8 hours = 480 minutes
        self.assertEqual(self.compute_duration_minutes(entry, exit_), 480.0)

    def test_overstay_boundary(self):
        base_time = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)
        
        # 239 minutes -> Not overstay
        self.assertFalse(self.is_overstay(base_time, base_time + timedelta(minutes=239)))
        
        # Exactly 240 minutes -> Overstay
        self.assertTrue(self.is_overstay(base_time, base_time + timedelta(minutes=240)))
        
        # 241 minutes -> Overstay
        self.assertTrue(self.is_overstay(base_time, base_time + timedelta(minutes=241)))

if __name__ == "__main__":
    unittest.main()
