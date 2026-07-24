def subtotal(items):
    total = 0
    for item in items:
        total += item["quantity"] * item["unit_price"]
    return total


def tax(items, rate):
    total = 0
    for item in items:
        total += item["quantity"] * item["unit_price"]
    return round(total * rate)


def grand_total(items, rate):
    total = 0
    for item in items:
        total += item["quantity"] * item["unit_price"]
    return total + round(total * rate)
