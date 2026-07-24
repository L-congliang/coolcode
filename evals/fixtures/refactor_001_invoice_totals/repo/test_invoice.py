import unittest

from invoice import grand_total, subtotal, tax


class InvoiceTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            {"quantity": 2, "unit_price": 100},
            {"quantity": 1, "unit_price": 250},
        ]

    def test_subtotal(self):
        self.assertEqual(subtotal(self.items), 450)

    def test_tax(self):
        self.assertEqual(tax(self.items, 0.1), 45)

    def test_grand_total(self):
        self.assertEqual(grand_total(self.items, 0.1), 495)


if __name__ == "__main__":
    unittest.main()
