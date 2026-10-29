import time
import random

def run_cache_benchmark(lookup_count=50000):
    """Benchmarks sub-millisecond plate lookup efficiency against active watchlists."""
    active_plates = {f"RJ14AB{i:04d}" for i in range(1000)}
    query_plates = [f"RJ14AB{random.randint(0, 5000):04d}" for _ in range(lookup_count)]

    start_time = time.perf_counter()
    matches = sum(1 for p in query_plates if p in active_plates)
    elapsed = time.perf_counter() - start_time

    latency_us = (elapsed / lookup_count) * 1_000_000
    qps = lookup_count / elapsed
    print(f"Executed {lookup_count} watchlist checks: {matches} hits in {elapsed:.4f}s ({qps:.0f} ops/sec, {latency_us:.2f} μs/op)")
    return qps

if __name__ == "__main__":
    run_cache_benchmark()
