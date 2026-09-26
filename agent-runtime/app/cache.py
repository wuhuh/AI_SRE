"""Short-TTL cache for tool results and retrieval.

The cache is intentionally simple and dependency-free. It is used to avoid
repeatedly querying the same metric/log/trace endpoint within a short window.

Design notes (红线 40):
  * The store is **bounded** (``maxsize``) with FIFO eviction of expired entries
    first, then oldest-inserted. A plain dict grew without limit because expired
    entries were only removed when that exact key was queried again — a key
    written once and never re-read stayed resident forever.
  * Cache keys are **hashed**. Raw keys embedded whole PromQL/log queries
    (hundreds of chars), so the *effective* hit rate was near zero: any tiny
    formatting difference produced a different key. Hashing also keeps memory
    predictable.
  * ``CacheStats`` now counts evictions and is exported, so the cache is
    observable instead of being a silent optimisation.
"""
from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from app.models import ToolCall
from app.tools.registry import ToolRegistry

DEFAULT_MAXSIZE = 512


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0

    def snapshot(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "evictions": self.evictions}


def _hash_key(raw: str) -> str:
    """Stable short key — avoids storing megabyte-long PromQL strings as keys."""
    return hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:32]


class TTLCache:
    def __init__(self, default_ttl_seconds: float = 5.0, maxsize: int = DEFAULT_MAXSIZE):
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self.default_ttl_seconds = default_ttl_seconds
        self.maxsize = maxsize
        # OrderedDict: insertion order doubles as the eviction order.
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self.stats = CacheStats()

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item is None:
            self.stats.misses += 1
            return None
        expire_at, value = item
        if time.monotonic() > expire_at:
            self._store.pop(key, None)
            self.stats.misses += 1
            return None
        self._store.move_to_end(key)
        self.stats.hits += 1
        return value

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        self._store[key] = (time.monotonic() + ttl, value)
        self._store.move_to_end(key)
        self._evict()

    def _evict(self) -> None:
        """Drop expired entries first; if still over capacity, drop oldest."""
        if len(self._store) <= self.maxsize:
            return
        now = time.monotonic()
        for k in [k for k, (expire_at, _) in self._store.items() if expire_at < now]:
            self._store.pop(k, None)
            self.stats.evictions += 1
        while len(self._store) > self.maxsize:
            self._store.popitem(last=False)
            self.stats.evictions += 1

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


class CachedToolRegistry:
    """Wraps a ToolRegistry and caches successful READ_ONLY tool results."""

    def __init__(self, registry: ToolRegistry, ttl_seconds: float = 5.0,
                 maxsize: int = DEFAULT_MAXSIZE):
        self.registry = registry
        self.cache = TTLCache(ttl_seconds, maxsize=maxsize)

    def call(self, name: str, arguments: dict[str, Any], principal: str = "agent") -> ToolCall:
        spec = self.registry.get(name).spec if name in self.registry.names() else None
        if spec is None or spec.risk_level != "READ_ONLY":
            return self.registry.call(name, arguments, principal=principal)

        # 红线 40：key 先哈希——原来直接把 sorted(arguments.items()) 拼进 key，
        # PromQL 全文进 key 使条目近乎永不命中，且单条 key 长达数百字符。
        raw_key = "%s:%s:%s" % (name, principal, sorted(arguments.items()))
        key = _hash_key(raw_key)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        call = self.registry.call(name, arguments, principal=principal)
        if call.status == "SUCCESS":
            self.cache.set(key, call)
        return call

    def names(self) -> list[str]:
        return self.registry.names()

    def specs(self) -> list[dict[str, Any]]:
        return self.registry.specs()

    def stats(self) -> dict[str, int]:
        return self.cache.stats.snapshot()
