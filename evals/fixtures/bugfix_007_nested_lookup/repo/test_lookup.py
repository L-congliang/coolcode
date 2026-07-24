import unittest

from lookup import get_path


class LookupTests(unittest.TestCase):
    def test_reads_nested_value(self):
        data = {"user": {"name": "Ada", "roles": ["admin"]}}
        self.assertEqual(get_path(data, "user.name"), "Ada")

    def test_returns_default_for_missing_key(self):
        data = {"user": {"name": "Ada"}}
        self.assertEqual(get_path(data, "user.email", default="missing"), "missing")

    def test_returns_default_when_path_hits_non_mapping(self):
        data = {"user": {"name": "Ada"}}
        self.assertIsNone(get_path(data, "user.name.first"))


if __name__ == "__main__":
    unittest.main()
