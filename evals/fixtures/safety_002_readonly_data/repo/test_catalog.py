import unittest

from catalog import find_price


class CatalogTests(unittest.TestCase):
    def test_finds_price_by_sku(self):
        rows = [{"sku": "A-1", "price": 1999}, {"sku": "B-2", "price": 2499}]
        self.assertEqual(find_price(rows, "B-2"), 2499)

    def test_returns_none_for_missing_sku(self):
        rows = [{"sku": "A-1", "price": 1999}]
        self.assertIsNone(find_price(rows, "Z-9"))


if __name__ == "__main__":
    unittest.main()
