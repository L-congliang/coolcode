import unittest

from text_utils import slugify


class SlugifyTests(unittest.TestCase):
    def test_replaces_repeated_whitespace(self):
        self.assertEqual(slugify("Hello    World"), "hello-world")

    def test_removes_punctuation(self):
        self.assertEqual(slugify("Ship it, please!"), "ship-it-please")

    def test_strips_edge_separators(self):
        self.assertEqual(slugify("  Already Done?  "), "already-done")


if __name__ == "__main__":
    unittest.main()

