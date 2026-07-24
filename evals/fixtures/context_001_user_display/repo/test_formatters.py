import unittest

from formatters import display_name
from models import User


class DisplayNameTests(unittest.TestCase):
    def test_uses_full_name_when_available(self):
        user = User("Ada", "Lovelace", "ada@example.com")
        self.assertEqual(display_name(user), "Ada Lovelace")

    def test_falls_back_to_email_when_name_missing(self):
        user = User("", "", "missing@example.com")
        self.assertEqual(display_name(user), "missing@example.com")


if __name__ == "__main__":
    unittest.main()
