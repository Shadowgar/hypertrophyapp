"""Synthetic calendar fixtures only; the application remains the scheduling authority."""
from datetime import date, timedelta


def recovery_dates(today: date) -> list[date]:
    monday = today - timedelta(days=today.weekday())
    # Reuse the three already-qualified fixture patterns, including today's slot.
    offsets = (1, 4, 6) if today.weekday() == 6 else (0, 2, 4) if today.weekday() % 2 == 0 else (1, 3, 5)
    return [monday + timedelta(days=offset) for offset in offsets]
