import unittest

from ranking import top_n


class RankingTests(unittest.TestCase):
    def test_returns_highest_scores_first(self):
        scores = [
            {"name": "low", "score": 10},
            {"name": "high", "score": 99},
            {"name": "mid", "score": 50},
        ]
        self.assertEqual([item["name"] for item in top_n(scores, 2)], ["high", "mid"])

    def test_handles_more_requested_than_available(self):
        scores = [{"name": "only", "score": 1}]
        self.assertEqual(top_n(scores, 5), scores)


if __name__ == "__main__":
    unittest.main()
