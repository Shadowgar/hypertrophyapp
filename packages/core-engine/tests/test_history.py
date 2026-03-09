from datetime import date, datetime, time, timedelta
from types import SimpleNamespace

from core_engine import build_history_analytics, build_history_calendar, build_history_day_detail


def test_build_history_analytics_returns_pr_trends_measurements_and_heatmap() -> None:
    current_day = date(2026, 3, 5)
    current_monday = current_day - timedelta(days=current_day.weekday())
    week_one = current_monday - timedelta(days=14)
    week_two = current_monday - timedelta(days=7)

    checkin_rows = [
        SimpleNamespace(
            week_start=week_one,
            body_weight=82.5,
            adherence_score=4,
            notes="Week one",
            created_at=datetime.combine(week_one, time(8, 0)),
        ),
        SimpleNamespace(
            week_start=week_two,
            body_weight=81.8,
            adherence_score=5,
            notes="Week two",
            created_at=datetime.combine(week_two, time(8, 0)),
        ),
    ]
    log_rows = [
        SimpleNamespace(
            workout_id="w1",
            primary_exercise_id="bench",
            exercise_id="bench",
            set_index=1,
            reps=8,
            weight=80,
            rpe=None,
            created_at=datetime.combine(week_one + timedelta(days=1), time(9, 0)),
        ),
        SimpleNamespace(
            workout_id="w2",
            primary_exercise_id="bench",
            exercise_id="bench",
            set_index=1,
            reps=7,
            weight=90,
            rpe=None,
            created_at=datetime.combine(week_two + timedelta(days=2), time(9, 0)),
        ),
        SimpleNamespace(
            workout_id="w3",
            primary_exercise_id="squat",
            exercise_id="squat",
            set_index=1,
            reps=5,
            weight=110,
            rpe=None,
            created_at=datetime.combine(week_two + timedelta(days=3), time(9, 0)),
        ),
    ]
    measurement_rows = [
        SimpleNamespace(
            measured_on=week_one,
            name="Waist",
            value=84.0,
            unit="cm",
            created_at=datetime.combine(week_one, time(7, 0)),
        ),
        SimpleNamespace(
            measured_on=week_two,
            name="Waist",
            value=82.0,
            unit="cm",
            created_at=datetime.combine(week_two, time(7, 0)),
        ),
    ]

    payload = build_history_analytics(
        checkin_rows=checkin_rows,
        log_rows=log_rows,
        measurement_rows=measurement_rows,
        limit_weeks=4,
        checkin_limit=12,
        today=current_day,
    )

    assert payload["window"]["limit_weeks"] == 4
    assert len(payload["checkins"]) == 2
    assert len(payload["bodyweight_trend"]) == 2
    assert payload["adherence"]["average_pct"] == 90

    exercise_ids = {entry["exercise_id"] for entry in payload["strength_trends"]}
    assert "bench" in exercise_ids

    bench_pr = next(item for item in payload["pr_highlights"] if item["exercise_id"] == "bench")
    assert bench_pr["pr_weight"] == 90
    assert bench_pr["pr_delta"] == 10

    waist = next(item for item in payload["body_measurement_trends"] if item["name"] == "waist")
    assert waist["latest_value"] == 82
    assert waist["delta"] == -2

    assert len(payload["volume_heatmap"]["weeks"]) == 4


def test_build_history_calendar_includes_planned_metadata_prs_and_streaks() -> None:
    today = date(2026, 3, 3)
    day_one = today - timedelta(days=2)
    day_two = today - timedelta(days=1)
    day_three = today

    plans = [
        SimpleNamespace(
            payload={
                "sessions": [
                    {
                        "session_id": "workout_a",
                        "date": day_one.isoformat(),
                        "exercises": [
                            {"id": "bench_press", "name": "Bench Press", "sets": 3, "primary_muscles": ["chest"]},
                        ],
                    },
                    {
                        "session_id": "workout_c",
                        "date": day_three.isoformat(),
                        "exercises": [
                            {"id": "incline_press", "name": "Incline Press", "sets": 2, "primary_muscles": ["chest"]},
                        ],
                    },
                ],
                "program_template_id": "full_body_v1",
            }
        )
    ]
    log_rows = [
        SimpleNamespace(
            workout_id="workout_a",
            primary_exercise_id="bench_press",
            exercise_id="bench_press",
            set_index=1,
            reps=8,
            weight=80,
            rpe=None,
            created_at=datetime.combine(day_one, time(9, 0)),
        ),
        SimpleNamespace(
            workout_id="workout_a",
            primary_exercise_id="bench_press",
            exercise_id="bench_press",
            set_index=2,
            reps=7,
            weight=82.5,
            rpe=None,
            created_at=datetime.combine(day_one, time(9, 5)),
        ),
        SimpleNamespace(
            workout_id="workout_b",
            primary_exercise_id="romanian_deadlift",
            exercise_id="romanian_deadlift",
            set_index=1,
            reps=10,
            weight=100,
            rpe=None,
            created_at=datetime.combine(day_two, time(10, 0)),
        ),
    ]

    payload = build_history_calendar(
        log_rows=log_rows,
        all_log_rows_until_end=log_rows,
        plans=plans,
        start_date=today - timedelta(days=3),
        end_date=today,
        today=today,
    )

    assert payload["active_days"] == 2
    assert payload["current_streak_days"] == 0
    assert payload["longest_streak_days"] == 2

    day_one_entry = next(day for day in payload["days"] if day["date"] == day_one.isoformat())
    assert day_one_entry["set_count"] == 2
    assert day_one_entry["exercise_count"] == 1
    assert day_one_entry["completed"] is True
    assert day_one_entry["program_ids"] == ["full_body_v1"]
    assert day_one_entry["muscles"] == ["chest"]
    assert day_one_entry["pr_count"] == 1
    assert day_one_entry["pr_exercises"] == ["bench_press"]


def test_build_history_day_detail_includes_logged_and_missed_planned_workouts() -> None:
    today = date(2026, 3, 3)
    day_one = today - timedelta(days=2)

    plans = [
        SimpleNamespace(
            payload={
                "sessions": [
                    {
                        "session_id": "workout_a",
                        "date": day_one.isoformat(),
                        "exercises": [
                            {"id": "bench_press", "name": "Bench Press", "sets": 3, "primary_muscles": ["chest"]},
                        ],
                    },
                    {
                        "session_id": "workout_c",
                        "date": today.isoformat(),
                        "exercises": [
                            {"id": "incline_press", "name": "Incline Press", "sets": 2, "primary_muscles": ["chest"]},
                        ],
                    },
                ],
                "program_template_id": "full_body_v1",
            }
        )
    ]
    logged_rows = [
        SimpleNamespace(
            workout_id="workout_a",
            primary_exercise_id="bench_press",
            exercise_id="bench_press",
            set_index=1,
            reps=8,
            weight=80,
            rpe=None,
            created_at=datetime.combine(day_one, time(9, 0)),
        ),
        SimpleNamespace(
            workout_id="workout_a",
            primary_exercise_id="bench_press",
            exercise_id="bench_press",
            set_index=2,
            reps=7,
            weight=82.5,
            rpe=None,
            created_at=datetime.combine(day_one, time(9, 5)),
        ),
    ]

    detail_payload = build_history_day_detail(day=day_one, log_rows=logged_rows, plans=plans)

    assert detail_payload["date"] == day_one.isoformat()
    assert detail_payload["totals"]["set_count"] == 2
    assert detail_payload["totals"]["planned_set_count"] == 3
    assert detail_payload["totals"]["set_delta"] == -1
    assert detail_payload["totals"]["exercise_count"] == 1
    assert len(detail_payload["workouts"]) == 1
    assert detail_payload["workouts"][0]["workout_id"] == "workout_a"
    assert detail_payload["workouts"][0]["program_id"] == "full_body_v1"
    assert detail_payload["workouts"][0]["planned_sets_total"] == 3
    assert detail_payload["workouts"][0]["set_delta"] == -1
    assert detail_payload["workouts"][0]["exercises"][0]["exercise_id"] == "bench_press"
    assert detail_payload["workouts"][0]["exercises"][0]["planned_name"] == "Bench Press"
    assert detail_payload["workouts"][0]["exercises"][0]["primary_muscles"] == ["chest"]
    assert detail_payload["workouts"][0]["exercises"][0]["planned_sets"] == 3
    assert detail_payload["workouts"][0]["exercises"][0]["set_delta"] == -1

    missed_payload = build_history_day_detail(day=today, log_rows=[], plans=plans)
    assert missed_payload["totals"]["set_count"] == 0
    assert missed_payload["totals"]["planned_set_count"] == 2
    assert missed_payload["totals"]["set_delta"] == -2
    assert len(missed_payload["workouts"]) == 1
    assert missed_payload["workouts"][0]["workout_id"] == "workout_c"
    assert missed_payload["workouts"][0]["exercises"][0]["planned_name"] == "Incline Press"