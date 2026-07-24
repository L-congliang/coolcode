def discounted_price(cents, percent):
    if cents < 0:
        raise ValueError("price cannot be negative")
    if percent < 0 or percent > 100:
        raise ValueError("discount percent must be between 0 and 100")
    return round(cents * (100 - percent) / 100)
