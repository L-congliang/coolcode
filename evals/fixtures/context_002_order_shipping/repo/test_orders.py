import unittest

from orders import shipping_cents


class ShippingTests(unittest.TestCase):
    def test_charges_standard_shipping_below_threshold(self):
        items = [{"price_cents": 1000, "quantity": 2}]
        self.assertEqual(shipping_cents(items), 799)

    def test_free_shipping_at_threshold(self):
        items = [{"price_cents": 2500, "quantity": 2}]
        self.assertEqual(shipping_cents(items), 0)


if __name__ == "__main__":
    unittest.main()
