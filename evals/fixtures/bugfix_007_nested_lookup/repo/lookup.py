def get_path(data, path, default=None):
    current = data
    for part in path.split("."):
        current = current[part]
    return current
