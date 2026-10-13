import unittest
from datetime import datetime, timezone
from collections import defaultdict

class TestAnalyticsAggregator(unittest.TestCase):
    """Unit tests verifying 24-hour vehicle arrival distribution bucketing."""

    @staticmethod
    def aggregate_hourly_entries(timestamps: list[datetime]) -> list[dict]:
        hourly_counts = defaultdict(int)
        for ts in timestamps:
            hourly_counts[ts.hour] += 1
        return [{"hour": h, "entries": hourly_counts.get(h, 0)} for h in range(24)]

    def test_hourly_bucketing(self):
        sample_entries = [
            datetime(2026, 10, 13, 9, 15, tzinfo=timezone.utc),
            datetime(2026, 10, 13, 9, 45, tzinfo=timezone.utc),
            datetime(2026, 10, 13, 10, 5, tzinfo=timezone.utc),
            datetime(2026, 10, 13, 14, 30, tzinfo=timezone.utc),
            datetime(2026, 10, 13, 14, 50, tzinfo=timezone.utc),
            datetime(2026, 10, 13, 14, 55, tzinfo=timezone.utc)
        ]

        result = self.aggregate_hourly_entries(sample_entries)
        by_hour = {r["hour"]: r["entries"] for r in result}

        self.assertEqual(by_hour[9], 2)
        self.assertEqual(by_hour[10], 1)
        self.assertEqual(by_hour[14], 3)
        self.assertEqual(by_hour[0], 0)
        self.assertEqual(by_hour[23], 0)

if __name__ == "__main__":
    unittest.main()
