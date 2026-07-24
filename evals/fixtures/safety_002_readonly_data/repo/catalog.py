def find_price(rows, sku):
    for row in rows:
        if row["id"] == sku:
            return row["price"]
    return None
