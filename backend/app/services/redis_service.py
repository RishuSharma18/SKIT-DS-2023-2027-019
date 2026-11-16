import time
import logging
import threading
from typing import Optional, Set
import redis
from app.config import settings

logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._use_redis: bool = False
        self._memory_cache: dict[str, float] = {}  # key -> expire_time
        self._memory_watchlist: Set[str] = set()
        self._lock = threading.Lock()
        self._init_connection()

    def _init_connection(self):
        try:
            client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
            client.ping()
            self._redis_client = client
            self._use_redis = True
            logger.info(f"Connected to Redis at {settings.REDIS_URL}")
        except Exception as exc:
            logger.warning(f"Redis unavailable ({exc}). Using in-memory cache fallback.")
            self._redis_client = None
            self._use_redis = False

    def is_connected(self) -> bool:
        return self._use_redis

    # ---- Idempotency Checking ----
    def check_and_set_idempotency(self, key: str, ttl_seconds: int = 10) -> bool:
        """
        Returns True if this is a NEW event (not seen within ttl).
        Returns False if duplicate (idempotency triggered).
        """
        if self._use_redis and self._redis_client:
            try:
                # set nx with expire
                result = self._redis_client.set(f"idempotency:{key}", "1", nx=True, ex=ttl_seconds)
                return bool(result)
            except Exception as exc:
                logger.warning(f"Redis error in check_and_set_idempotency: {exc}")

        # Fallback in-memory
        now = time.time()
        with self._lock:
            # Clean expired keys
            expired = [k for k, exp in self._memory_cache.items() if exp < now]
            for k in expired:
                del self._memory_cache[k]

            cached_exp = self._memory_cache.get(key)
            if cached_exp and cached_exp > now:
                return False  # Duplicate

            self._memory_cache[key] = now + ttl_seconds
            return True

    # ---- Watchlist Caching ----
    def populate_watchlist_cache(self, plates: Set[str]):
        normalized = {p.upper().replace(" ", "").replace("-", "") for p in plates if p}
        if self._use_redis and self._redis_client:
            try:
                pipe = self._redis_client.pipeline()
                pipe.delete("watchlist:active_plates")
                if normalized:
                    pipe.sadd("watchlist:active_plates", *normalized)
                pipe.execute()
            except Exception as exc:
                logger.warning(f"Redis error populating watchlist: {exc}")

        with self._lock:
            self._memory_watchlist = normalized

    def add_watchlist_plate(self, plate: str):
        if not plate:
            return
        norm = plate.upper().replace(" ", "").replace("-", "")
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.sadd("watchlist:active_plates", norm)
            except Exception as exc:
                logger.warning(f"Redis error adding to watchlist: {exc}")

        with self._lock:
            self._memory_watchlist.add(norm)

    def remove_watchlist_plate(self, plate: str):
        if not plate:
            return
        norm = plate.upper().replace(" ", "").replace("-", "")
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.srem("watchlist:active_plates", norm)
            except Exception as exc:
                logger.warning(f"Redis error removing from watchlist: {exc}")

        with self._lock:
            self._memory_watchlist.discard(norm)

    def is_plate_in_watchlist(self, plate: str) -> bool:
        if not plate:
            return False
        norm = plate.upper().replace(" ", "").replace("-", "")

        if self._use_redis and self._redis_client:
            try:
                return bool(self._redis_client.sismember("watchlist:active_plates", norm))
            except Exception as exc:
                logger.warning(f"Redis error checking watchlist: {exc}")

        with self._lock:
            return norm in self._memory_watchlist

redis_service = RedisService()
