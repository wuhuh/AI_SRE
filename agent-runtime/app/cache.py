"""Short-TTL cache for tool results and retrieval.

The cache is intentionally simple and dependency-free. It is used to avoid
repeatedly querying the same metric/log/trace endpoint within a short window.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.models import ToolCall
from app.tools.registry import ToolRegistry


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0

    def snapshot(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses}


class TTLCache:
    def __init__(self, default_ttl_seconds: float = 5.0):
        self.default_ttl_seconds = default_ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
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
        self.stats.hits += 1
        return value

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        self._store[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        self._store.clear()


class CachedToolRegistry:
    """Wraps a ToolRegistry and caches successful READ_ONLY tool results."""

    def __init__(self, registry: ToolRegistry, ttl_seconds: float = 5.0):
        self.registry = registry
        self.cache = TTLCache(ttl_seconds)

    def call(self, name: str, arguments: dict[str, Any], principal: str = "agent") -> ToolCall:
        spec = self.registry.get(name).spec if name in self.registry.names() else None
        if spec is None or spec.risk_level != "READ_ONLY":
            return self.registry.call(name, arguments, principal=principal)

        key = f"{name}:{principal}:{sorted(arguments.items())}"
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