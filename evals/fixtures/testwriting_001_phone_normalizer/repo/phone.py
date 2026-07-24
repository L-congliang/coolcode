import re


def normalize_phone(raw):
    digits = re.sub(r"\D+", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError("phone number must contain 10 digits")
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
