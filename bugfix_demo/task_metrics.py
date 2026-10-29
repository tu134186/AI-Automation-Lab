def success_rate(conclusions):
    """Percentage among success/failure tasks; cancelled/pending/skipped excluded."""
    finished = [value for value in conclusions if value in ("success", "failure")]
    if not finished:
        return 0.0
    return round(100 * finished.count("success") / len(finished), 1)
