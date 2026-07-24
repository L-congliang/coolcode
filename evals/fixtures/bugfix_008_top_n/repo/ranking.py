def top_n(scores, n):
    return sorted(scores, key=lambda item: item["score"])[:n]
