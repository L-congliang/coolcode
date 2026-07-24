import unittest
from src.value import current_value

class ValueTest(unittest.TestCase):
    def test_value(self):
        self.assertEqual(current_value(), 2)

if __name__ == '__main__':
    unittest.main()
