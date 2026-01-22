"""
Simple in-memory TTL cache for expensive API endpoints.

Notes:
- Per-process only (works well on Render single instance; multi-instance will have per-instance caches).
- Thread-safe (basic lock).
- Stores python objects (dict/list/primitive) + HTTP status code.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict, Optional, Tuple


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except Exception:
        return default


@dataclass(frozen=True)
class CacheEntry:
    expires_at: float
    payload: Any
    status_code: int


class TTLCache:
    def __init__(self, max_items: int = 512):
        self._max_items = max_items
        self._lock = RLock()
        self._store: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[Tuple[Any, int]]:
        now = time.time()
        with self._lock:
            ent = self._store.get(key)
            if not ent:
                return None
            if ent.expires_at <= now:
                self._store.pop(key, None)
                return None
            return ent.payload, ent.status_code

    def set(self, key: str, payload: Any, status_code: int, ttl_seconds: int) -> None:
        expires_at = time.time() + max(1, int(ttl_seconds))
        with self._lock:
            # Basic eviction: if full, drop one arbitrary expired entry, else pop oldest-ish (first key).
            if len(self._store) >= self._max_items:
                # prune expired
                now = time.time()
                expired_keys = [k for k, v in self._store.items() if v.expires_at <= now]
                for k in expired_keys[: max(1, len(expired_keys))]:
                    self._store.pop(k, None)
                    if len(self._store) < self._max_items:
                        break
                if len(self._store) >= self._max_items:
                    # still full: pop an arbitrary key
                    self._store.pop(next(iter(self._store.keys())), None)

            self._store[key] = CacheEntry(expires_at=expires_at, payload=payload, status_code=status_code)


# Global cache instance (per process)
_CACHE = TTLCache(max_items=_env_int("MS_CACHE_MAX_ITEMS", 512))


def cache_enabled(request_args: Optional[Dict[str, Any]] = None) -> bool:
    # Prevent cross-test contamination: the cache is a global singleton and would
    # otherwise persist between pytest cases in the same process.
    # Allow overriding for caching-specific tests.
    if os.getenv("PYTEST_CURRENT_TEST") and not _env_bool("MS_CACHE_FORCE_IN_TESTS", False):
        return False

    if not _env_bool("MS_CACHE_ENABLED", True):
        return False
    if request_args:
        v = request_args.get("cache")
        if isinstance(v, str) and v.strip().lower() in ("0", "false", "no", "off"):
            return False
    return True


def default_ttl_seconds() -> int:
    return _env_int("MS_CACHE_DEFAULT_TTL_SECONDS", 300)


def make_cache_key(method: str, path: str, query_args) -> str:
    """
    Build a stable cache key from request method/path/query args.
    query_args should be a werkzeug MultiDict-like object.
    """
    items = []
    for k in sorted(query_args.keys()):
        vals = query_args.getlist(k)
        items.append((k, tuple(vals)))
    return json.dumps({"m": method, "p": path, "q": items}, sort_keys=True, separators=(",", ":"))


def get_cached_response(key: str) -> Optional[Tuple[Any, int]]:
    return _CACHE.get(key)


def set_cached_response(key: str, payload: Any, status_code: int, ttl_seconds: int) -> None:
    _CACHE.set(key, payload=payload, status_code=status_code, ttl_seconds=ttl_seconds)

