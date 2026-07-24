import unittest
from src.calc import calculate

class CalcTest(unittest.TestCase):
    def test_calculate(self):
        self.assertEqual(calculate(4), 36)
        self.assertEqual(calculate(7), 63)

if __name__ == '__main__':
    unittest.main()
