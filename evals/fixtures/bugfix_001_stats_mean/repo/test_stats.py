import unittest

from stats import mean


class MeanTests(unittest.TestCase):
    def test_mean_of_multiple_values(self):
        self.assertEqual(mean([2, 4, 6]), 4)

    def test_mean_of_single_value(self):
        self.assertEqual(mean([5]), 5)

    def test_empty_values_raise(self):
        with self.assertRaises(ValueError):
            mean([])


if __name__ == "__main__":
    unittest.main()

