import unittest

from dedupe import dedupe


class DedupeTests(unittest.TestCase):
    def test_preserves_first_seen_order(self):
        self.assertEqual(dedupe(["b", "a", "b", "c", "a"]), ["b", "a", "c"])

    def test_handles_empty_list(self):
        self.assertEqual(dedupe([]), [])


if __name__ == "__main__":
    unittest.main()
