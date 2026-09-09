import logging
import time
from threading import Lock
from typing import Any

from core.config import settings

logger = logging.getLogger(__name__)


class TTLCache:
    """
    Thread-safe in-memory cache with Time-To-Live (TTL) expiration.
    Default TTL is 1 day (86400 seconds) for JioSaavn home sections.
    """

    def __init__(self, default_ttl: int | None = None):
        self.default_ttl = default_ttl or settings.HOME_CACHE_TTL_SECONDS
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                self._misses += 1
                logger.debug(f"Cache key expired: {key}")
                return None

            self._hits += 1
            logger.debug(f"Cache hit for key: {key}")
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        with self._lock:
            effective_ttl = ttl if ttl is not None else self.default_ttl
            expiry = time.time() + effective_ttl
            self._cache[key] = (value, expiry)
            logger.debug(f"Cache set for key: {key} with TTL: {effective_ttl}s")

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("Cache cleared.")

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            # Clean expired items
            now = time.time()
            active_keys = [k for k, (_, exp) in self._cache.items() if exp > now]
            return {
                "active_items": len(active_keys),
                "total_items": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "default_ttl_seconds": self.default_ttl,
            }


# Global cache instance
ttl_cache = TTLCache()
