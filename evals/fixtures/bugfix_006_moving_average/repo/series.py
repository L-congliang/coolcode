def moving_average(values, window):
    if window <= 0:
        raise ValueError("window must be positive")
    if window > len(values):
        return []
    averages = []
    for index in range(len(values) - window):
        averages.append(sum(values[index:index + window]) / window)
    return averages
