import unittest
from task3_cache import YourCache
from cache_floor import floor
from bench import Upstream, workload


class CacheTests(unittest.TestCase):
    def test_expiry_boundary_and_zero_ttl(self):
        calls = []
        def upstream(name):
            calls.append(name)
            return str(len(calls)), 0 if name == "zero" else 20
        cache = YourCache(upstream)
        self.assertEqual(cache.lookup("x", 0), "1")
        self.assertEqual(cache.lookup("x", 19.999), "1")
        self.assertEqual(cache.lookup("x", 20), "2")
        self.assertNotEqual(cache.lookup("zero", 21), cache.lookup("zero", 21))

    def test_expired_address_is_replaced_and_names_are_independent(self):
        calls = []
        def upstream(name):
            calls.append(name)
            return (name, len(calls)), 10
        cache = YourCache(upstream)
        first = cache.lookup("a", 0)
        cache.lookup("b", 1)
        self.assertEqual(cache.lookup("a", 9), first)
        self.assertNotEqual(cache.lookup("a", 10), first)
        self.assertEqual(calls, ["a", "b", "a"])

    def test_matches_independent_floor(self):
        up = Upstream()
        cache = YourCache(up)
        for now, name in workload():
            up.now = now
            cache.lookup(name, now)
        self.assertEqual(up.calls, sum(floor().values()))
        self.assertEqual(up.calls, 275)


if __name__ == "__main__":
    unittest.main()
