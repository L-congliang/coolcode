def is_allowed(events, now, window_seconds, limit):
    start = now - window_seconds
    count = 0
    for event_time in events:
        if start <= event_time <= now:
            count += 1
    return count < limit
