import unittest

from report import build_summary


class ReportTests(unittest.TestCase):
    def test_builds_summary_lines(self):
        rows = [{"name": "alpha", "score": 3}, {"name": "beta", "score": 5}]
        self.assertEqual(build_summary(rows), "alpha: 3\nbeta: 5\n")

    def test_empty_rows(self):
        self.assertEqual(build_summary([]), "")


if __name__ == "__main__":
    unittest.main()
