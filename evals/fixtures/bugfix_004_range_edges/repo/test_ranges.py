import unittest

from ranges import contains_range


class RangeTests(unittest.TestCase):
    def test_middle_value(self):
        self.assertTrue(contains_range(5, [(1, 10)]))

    def test_start_edge_is_included(self):
        self.assertTrue(contains_range(1, [(1, 10)]))

    def test_end_edge_is_included(self):
        self.assertTrue(contains_range(10, [(1, 10)]))

    def test_outside_value(self):
        self.assertFalse(contains_range(11, [(1, 10)]))


if __name__ == "__main__":
    unittest.main()

