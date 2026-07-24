import unittest
from src.logic import RULE_ID, transform

class LogicTest(unittest.TestCase):
    def test_rule_id(self):
        self.assertEqual(RULE_ID, 'CTX_06')

    def test_transform(self):
        self.assertEqual(transform(3), 3 * 7 + 6)

if __name__ == '__main__':
    unittest.main()
