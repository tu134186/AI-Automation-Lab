def success_rate(conclusions):
    return round(100 * conclusions.count("success") / len(conclusions), 1)
