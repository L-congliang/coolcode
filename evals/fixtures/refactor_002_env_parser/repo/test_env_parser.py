import unittest

from env_parser import parse_bool


class ParseBoolTests(unittest.TestCase):
    def test_true_values(self):
        self.assertTrue(parse_bool("YES"))
        self.assertTrue(parse_bool(" on "))

    def test_false_values(self):
        self.assertFalse(parse_bool("0"))
        self.assertFalse(parse_bool("off"))

    def test_invalid_value(self):
        with self.assertRaises(ValueError):
            parse_bool("maybe")


if __name__ == "__main__":
    unittest.main()
