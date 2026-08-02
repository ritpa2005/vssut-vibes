import asyncio
import time
from typing import Any


class TTLCache:
    def __init__(self):
        self._store: dict[str, dict] = {}
        self._lock  = asyncio.Lock()

    # Core operations
    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry["expires_at"]:
                del self._store[key]
                return None
            return entry["value"]

    async def set(self, key: str, value: Any, ttl: int = 600) -> None:
        """
        Store value under key with TTL in seconds.
        Default TTL is 10 minutes.
        """
        async with self._lock:
            self._store[key] = {
                "value":      value,
                "expires_at": time.monotonic() + ttl
            }

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def delete_pattern(self, prefix: str) -> None:
        """
        Delete all keys that start with prefix.
        Used for group invalidation e.g. all suggestion keys for a user.
        """
        async with self._lock:
            keys_to_delete = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._store[k]

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    # Cleanup every 15 minutes
    async def _cleanup_expired(self) -> None:
        while True:
            await asyncio.sleep(900)
            now = time.monotonic()
            async with self._lock:
                expired = [k for k, v in self._store.items() if now > v["expires_at"]]
                for k in expired:
                    del self._store[k]

    def stats(self) -> dict:
        """Return current cache size — useful for debugging."""
        return {
            "total_keys": len(self._store),
            "keys":       list(self._store.keys())
        }

cache = TTLCache()

# TTL constants 
class CacheTTL:
    SUGGESTIONS  = 24 * 60 * 60
    FEED         = 15 * 60
    JOB_LIST     = 60 * 60
    JOB_DETAIL   = 5 * 60
    USER_PROFILE = 5 * 60

# Cache key builders
class CacheKey:
    @staticmethod
    def suggestions(user_id: str) -> str:
        return f"suggestions:all:{user_id}"

    @staticmethod
    def suggestions_dept(user_id: str) -> str:
        return f"suggestions:dept:{user_id}"

    @staticmethod
    def suggestions_skills(user_id: str) -> str:
        return f"suggestions:skills:{user_id}"

    @staticmethod
    def feed(skip: int, limit: int) -> str:
        return f"feed:{skip}:{limit}"

    @staticmethod
    def job_list(job_type: str, location: str, company: str, search: str, skip: int, limit: int) -> str:
        return f"jobs:{job_type}:{location}:{company}:{search}:{skip}:{limit}"

    @staticmethod
    def job_detail(job_id: str) -> str:
        return f"job:{job_id}"

    @staticmethod
    def user_suggestions_prefix(user_id: str) -> str:
        """Prefix for all suggestion keys for a user — used in invalidation."""
        return f"suggestions::{user_id}"