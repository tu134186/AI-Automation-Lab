def success_rate(conclusions):
    """Percentage of finished success/failure tasks that succeeded."""
    return round(100 * conclusions.count("success") / len(conclusions), 1)
