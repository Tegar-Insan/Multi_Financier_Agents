import time


class TTLCache:
    def __init__(self):
        self._store: dict[str, tuple[any, float]] = {}

    def get(self, key: str):
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value, ttl_seconds: int):
        self._store[key] = (value, time.time() + ttl_seconds)

    def has(self, key: str) -> bool:
        return self.get(key) is not None


_cache = TTLCache()

TTL_QUOTE = 300
TTL_MARKET = 300
TTL_CRYPTO = 300
TTL_NEWS = 1800
TTL_STATEMENTS = 86400
TTL_EARNINGS = 3600
TTL_METRICS = 3600
