"""Local occurrence dates group receipts without rewriting audit timestamps."""
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from core_engine import build_history_analytics, build_history_calendar, build_history_day_detail


@pytest.mark.parametrize("local_day,recorded_at", [
    (date(2026, 10, 11), datetime(2026, 10, 12, 3)),  # Los Angeles Sunday.
    (date(2026, 10, 12), datetime(2026, 10, 11, 12)),  # Auckland Monday.
])
@pytest.mark.parametrize("as_mapping", [False, True])
def test_occurrence_date_owns_calendar_pr_strength_week_and_heatmap(local_day, recorded_at, as_mapping):
    values = dict(workout_id="dated-session", exercise_id="press", primary_exercise_id="press",
        set_index=1, reps=8, weight=20, rpe=None, created_at=recorded_at, performed_date=local_day)
    row = values if as_mapping else SimpleNamespace(**values)
    start, end = sorted((local_day, recorded_at.date()))
    calendar = build_history_calendar(log_rows=[row], all_log_rows_until_end=[row], plans=[],
        start_date=start, end_date=end, today=local_day)
    by_day = {item["date"]: item for item in calendar["days"]}
    assert by_day[local_day.isoformat()]["set_count"] == 1
    assert by_day[local_day.isoformat()]["pr_count"] == 1
    assert by_day[recorded_at.date().isoformat()]["set_count"] == 0
    assert by_day[recorded_at.date().isoformat()]["pr_count"] == 0
    assert calendar["current_streak_days"] == 1

    analytics = build_history_analytics(checkin_rows=[], log_rows=[row], measurement_rows=[],
        limit_weeks=2, checkin_limit=4, today=end)
    monday = date.fromordinal(local_day.toordinal() - local_day.weekday()).isoformat()
    strength = analytics["strength_trends"][0]
    assert strength["points"][0]["week_start"] == monday
    weeks = {item["week_start"]: item for item in analytics["volume_heatmap"]["weeks"]}
    assert weeks[monday]["days"][local_day.weekday()]["sets"] == 1
    assert sum(cell["sets"] for week in weeks.values() for cell in week["days"]) == 1

    detail = build_history_day_detail(day=local_day, log_rows=[row], plans=[])
    assert detail["totals"]["set_count"] == 1
    assert detail["workouts"][0]["exercises"][0]["sets"][0]["created_at"] == recorded_at.isoformat()
    assert (row["created_at"] if as_mapping else row.created_at) == recorded_at


@pytest.mark.parametrize("projection", [{}, {"performed_date": None}])
def test_legacy_calendar_and_strength_keep_original_timestamp_date(projection):
    recorded_at = datetime(2026, 10, 11, 12)
    row = dict(workout_id="legacy", exercise_id="press", primary_exercise_id="press",
        set_index=1, reps=8, weight=20, rpe=None, created_at=recorded_at, **projection)
    calendar = build_history_calendar(log_rows=[row], all_log_rows_until_end=[row], plans=[],
        start_date=date(2026, 10, 11), end_date=date(2026, 10, 12), today=date(2026, 10, 11))
    assert calendar["days"][0]["set_count"] == 1
    assert calendar["days"][1]["set_count"] == 0
    analytics = build_history_analytics(checkin_rows=[], log_rows=[row], measurement_rows=[],
        limit_weeks=2, checkin_limit=4, today=date(2026, 10, 12))
    assert analytics["strength_trends"][0]["points"][0]["week_start"] == "2026-10-05"
