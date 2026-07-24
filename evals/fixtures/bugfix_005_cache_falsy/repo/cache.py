def get_or_compute(cache, key, compute):
    if cache.get(key):
        return cache[key]
    cache[key] = compute()
    return cache[key]

