import unittest

from app.cache import CachedToolRegistry, TTLCache
from app.tools.registry import ToolRegistry
from test_core import EchoTool


class TTLCacheTest(unittest.TestCase):
    def test_get_miss_then_hit(self):
        cache = TTLCache(default_ttl_seconds=5)
        self.assertIsNone(cache.get("a"))
        cache.set("a", 1)
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.stats.snapshot()["hits"], 1)
        self.assertEqual(cache.stats.snapshot()["misses"], 1)

    def test_expired_entry_is_miss(self):
        cache = TTLCache(default_ttl_seconds=0)
        cache.set("a", 1)
        self.assertIsNone(cache.get("a"))


class CachedToolRegistryTest(unittest.TestCase):
    def test_cached_read_only_tool_call(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        cached = CachedToolRegistry(registry, ttl_seconds=5)
        first = cached.call("echo", {"message": "hello"})
        second = cached.call("echo", {"message": "hello"})
        self.assertEqual(first.status, "SUCCESS")
        self.assertEqual(second.status, "SUCCESS")
        self.assertIs(first, second)
        stats = cached.stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)


if __name__ == "__main__":
    unittest.main()