import time
import random
from datetime import datetime, timedelta, timezone
from collections import defaultdict

def run_hourly_analytics_benchmark(record_count=100000):
    """Benchmark processing throughput for large-scale session history aggregation."""
    base_time = datetime(2026, 10, 14, 0, 0, tzinfo=timezone.utc)
    timestamps = [
        base_time + timedelta(seconds=random.randint(0, 86399))
        for _ in range(record_count)
    ]

    start_time = time.perf_counter()
    hourly_bins = defaultdict(int)
    for ts in timestamps:
        hourly_bins[ts.hour] += 1
    
    res = [{"hour": h, "count": hourly_bins[h]} for h in range(24)]
    elapsed = time.perf_counter() - start_time

    print(f"Aggregated {record_count} records into 24 bins in {elapsed:.4f}s ({record_count/elapsed:.0f} records/s)")
    return elapsed

if __name__ == "__main__":
    run_hourly_analytics_benchmark()
