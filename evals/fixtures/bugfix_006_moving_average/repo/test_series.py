import unittest

from series import moving_average


class MovingAverageTests(unittest.TestCase):
    def test_three_point_window(self):
        self.assertEqual(moving_average([1, 2, 3, 4, 5], 3), [2, 3, 4])

    def test_window_equal_to_length(self):
        self.assertEqual(moving_average([2, 4, 6], 3), [4])

    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            moving_average([1, 2, 3], 0)


if __name__ == "__main__":
    unittest.main()
