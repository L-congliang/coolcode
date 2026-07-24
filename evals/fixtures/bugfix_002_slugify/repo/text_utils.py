def slugify(title):
    cleaned = title.strip().lower().replace(" ", "-")
    return cleaned

