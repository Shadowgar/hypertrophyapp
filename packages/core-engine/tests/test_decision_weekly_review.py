from datetime import date

from core_engine.decision_weekly_review import resolve_weekly_review_window


def test_resolve_weekly_review_window_rolls_to_next_week_on_sunday() -> None:
    window = resolve_weekly_review_window(today=date(2026, 3, 8))

    assert window["today_is_sunday"] is True
    assert window["current_week_start"] == date(2026, 3, 2)
    assert window["week_start"] == date(2026, 3, 9)
    assert window["previous_week_start"] == date(2026, 3, 2)
