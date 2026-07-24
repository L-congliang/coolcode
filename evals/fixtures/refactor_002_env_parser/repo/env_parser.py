def parse_bool(value):
    normalized = value.strip().lower()
    if normalized == "true" or normalized == "1" or normalized == "yes" or normalized == "on":
        return True
    if normalized == "false" or normalized == "0" or normalized == "no" or normalized == "off":
        return False
    raise ValueError(f"invalid boolean value: {value}")
