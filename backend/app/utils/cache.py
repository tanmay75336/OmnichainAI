import threading
import time


class SimpleTTLCache:
    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None

            expires_at, value = entry
            if expires_at < time.time():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key, value, ttl=600):
        with self._lock:
            self._store[key] = (time.time() + ttl, value)

    def clear(self):
        with self._lock:
            self._store.clear()


shared_cache = SimpleTTLCache()
