import unittest

from inventory import total_value


class InventoryTests(unittest.TestCase):
    def test_multiplies_price_by_quantity(self):
        items = [
            {"sku": "A", "price": 4, "quantity": 3},
            {"sku": "B", "price": 10, "quantity": 2},
        ]
        self.assertEqual(total_value(items), 32)

    def test_default_quantity_is_one(self):
        self.assertEqual(total_value([{"sku": "C", "price": 7}]), 7)


if __name__ == "__main__":
    unittest.main()

