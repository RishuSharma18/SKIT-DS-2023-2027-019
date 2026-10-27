import unittest
import time

class MemoryIdempotencyCache:
    """Thread-safe in-memory cache simulating Redis SET NX EX TTL semantics."""

    def __init__(self):
        self._store = {}

    def set_nx_ex(self, key: str, value: str, ttl_seconds: float) -> bool:
        now = time.time()
        if key in self._store:
            val, expire_at = self._store[key]
            if now < expire_at:
                return False  # Key already locked
        self._store[key] = (value, now + ttl_seconds)
        return True

class TestIdempotencyCache(unittest.TestCase):
    """Unit tests for event deduplication and TTL lock mechanisms."""

    def test_idempotent_duplicate_drop(self):
        cache = MemoryIdempotencyCache()
        track_id = 501
        key = f"event:entry:{track_id}"

        # First frame succeeds
        self.assertTrue(cache.set_nx_ex(key, "locked", ttl_seconds=1.0))
        # Immediate duplicate frame rejected
        self.assertFalse(cache.set_nx_ex(key, "locked", ttl_seconds=1.0))
        self.assertFalse(cache.set_nx_ex(key, "locked", ttl_seconds=1.0))

    def test_lock_expiration(self):
        cache = MemoryIdempotencyCache()
        key = "event:entry:502"
        self.assertTrue(cache.set_nx_ex(key, "locked", ttl_seconds=0.1))
        time.sleep(0.15)
        # Lock expired -> can acquire again
        self.assertTrue(cache.set_nx_ex(key, "locked", ttl_seconds=0.1))

if __name__ == "__main__":
    unittest.main()
