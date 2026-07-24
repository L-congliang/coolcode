import unittest

from config_loader import load_token


class ConfigLoaderTests(unittest.TestCase):
    def test_reads_api_token(self):
        self.assertEqual(load_token({"API_TOKEN": "abc"}), "abc")

    def test_returns_none_when_token_missing(self):
        self.assertIsNone(load_token({}))


if __name__ == "__main__":
    unittest.main()
