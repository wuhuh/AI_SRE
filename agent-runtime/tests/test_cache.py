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

    def test_never_reread_key_does_not_grow_unbounded(self):
        """红线 40 回归：写入后不再被读的 key 之前永久驻留，store 无界增长。"""
        cache = TTLCache(default_ttl_seconds=5, maxsize=10)
        for i in range(100):
            cache.set("key-%d" % i, i)
        self.assertLessEqual(len(cache), 10)

    def test_evicts_oldest_first(self):
        cache = TTLCache(default_ttl_seconds=5, maxsize=3)
        for i in range(3):
            cache.set("k%d" % i, i)
        cache.set("k3", 3)
        # k0 是最早写入的，应被淘汰
        self.assertIsNone(cache.get("k0"))
        self.assertEqual(cache.get("k3"), 3)

    def test_moves_recently_used_to_safe_end(self):
        cache = TTLCache(default_ttl_seconds=5, maxsize=3)
        for i in range(3):
            cache.set("k%d" % i, i)
        cache.get("k0")  # 变成最近使用
        cache.set("k3", 3)
        self.assertEqual(cache.get("k0"), 0)

    def test_evictions_are_counted(self):
        cache = TTLCache(default_ttl_seconds=5, maxsize=2)
        for i in range(5):
            cache.set("k%d" % i, i)
        self.assertGreater(cache.stats.snapshot()["evictions"], 0)

    def test_rejects_non_positive_maxsize(self):
        with self.assertRaises(ValueError):
            TTLCache(maxsize=0)


class CacheKeyTest(unittest.TestCase):
    def test_long_promql_key_is_hashed(self):
        """红线 40：key 含 PromQL 全文时单条 key 数百字符，改为哈希后长度固定。"""
        from app.cache import _hash_key
        promql = "sum(rate(http_requests_total{service=\"payment\",code=~\"5..\"}[5m])) / " * 10
        self.assertLess(len(_hash_key(promql)), 64)

    def test_hash_is_stable(self):
        from app.cache import _hash_key
        self.assertEqual(_hash_key("a"), _hash_key("a"))
        self.assertNotEqual(_hash_key("a"), _hash_key("b"))


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
