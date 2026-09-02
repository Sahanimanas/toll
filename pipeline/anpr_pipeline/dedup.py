"""Duplicate suppression: the same plate on the same camera within a TTL
window is published once. Redis-backed for multi-process deployments, with an
in-memory implementation for tests and single-process edge use."""

import time


class MemoryDuplicateFilter:
    def __init__(self, ttl_seconds: int = 30):
        self.ttl = ttl_seconds
        self._seen: dict[str, float] = {}

    def is_duplicate(self, camera_id: int, plate_text: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        key = f"{camera_id}:{plate_text}"
        # Opportunistic cleanup keeps the dict bounded.
        expired = [k for k, t in self._seen.items() if now - t > self.ttl]
        for k in expired:
            del self._seen[k]
        if key in self._seen:
            return True
        self._seen[key] = now
        return False


class RedisDuplicateFilter:
    def __init__(self, redis_url: str, ttl_seconds: int = 30):
        import redis

        self.client = redis.Redis.from_url(redis_url)
        self.ttl = ttl_seconds

    def is_duplicate(self, camera_id: int, plate_text: str, now: float | None = None) -> bool:
        key = f"anpr:dedup:{camera_id}:{plate_text}"
        # SET NX EX is atomic: returns None when the key already exists.
        return self.client.set(key, "1", nx=True, ex=self.ttl) is None


def build_duplicate_filter(redis_url: str, ttl_seconds: int):
    try:
        dedup = RedisDuplicateFilter(redis_url, ttl_seconds)
        dedup.client.ping()
        return dedup
    except Exception:
        return MemoryDuplicateFilter(ttl_seconds)
