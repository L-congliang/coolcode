from config import FREE_SHIPPING_THRESHOLD, STANDARD_SHIPPING_CENTS


def order_total(items):
    return sum(item["price_cents"] * item["quantity"] for item in items)


def shipping_cents(items):
    total = order_total(items)
    if total > FREE_SHIPPING_THRESHOLD:
        return 0
    return STANDARD_SHIPPING_CENTS
