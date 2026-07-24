def contains_range(value, ranges):
    for start, end in ranges:
        if start < value < end:
            return True
    return False

