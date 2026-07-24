import unittest

from loader import load_scores


class LoadScoresTests(unittest.TestCase):
    def test_skips_blank_lines(self):
        text = "Ada,10\n\nGrace,20\n"
        self.assertEqual(
            load_scores(text),
            [{"name": "Ada", "score": 10}, {"name": "Grace", "score": 20}],
        )

    def test_handles_whitespace_only_lines(self):
        text = "Ada,10\n   \n"
        self.assertEqual(load_scores(text), [{"name": "Ada", "score": 10}])


if __name__ == "__main__":
    unittest.main()
