import unittest
from src.calc import calculate

class CalcTest(unittest.TestCase):
    def test_calculate(self):
        self.assertEqual(calculate(4), 28)
        self.assertEqual(calculate(7), 49)

if __name__ == '__main__':
    unittest.main()
