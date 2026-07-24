import unittest

from cache import get_or_compute


class CacheTests(unittest.TestCase):
    def test_reuses_cached_zero(self):
        calls = {"count": 0}

        def compute():
            calls["count"] += 1
            return 99

        cache = {"answer": 0}
        self.assertEqual(get_or_compute(cache, "answer", compute), 0)
        self.assertEqual(calls["count"], 0)

    def test_computes_missing_key(self):
        cache = {}
        self.assertEqual(get_or_compute(cache, "name", lambda: ""), "")
        self.assertIn("name", cache)


if __name__ == "__main__":
    unittest.main()

