from datetime import date, timedelta

import pytest

from core_engine import generate_week_plan


def test_generate_week_plan_respects_days_available() -> None:
    template = {
        "id": "full_body_v1",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "bench",
                        "name": "Bench Press",
                        "substitution_candidates": ["db_bench", "machine_press"],
                        "notes": "Quick pause on chest",
                    }
                ],
            },
            {"name": "B", "exercises": [{"id": "squat", "name": "Squat"}]},
            {"name": "C", "exercises": [{"id": "row", "name": "Row"}]},
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
    )

    assert len(plan["sessions"]) == 2
    assert plan["split"] == "full_body"
    first_exercise = plan["sessions"][0]["exercises"][0]
    assert first_exercise["primary_exercise_id"] == "bench"
    assert first_exercise["substitution_candidates"] == ["db_bench", "machine_press"]
    assert first_exercise["notes"] == "Quick pause on chest"
    assert first_exercise["equipment_tags"] == []


def test_generate_week_plan_filters_by_available_equipment() -> None:
    template = {
        "id": "equipment_filter_test",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "barbell_row",
                        "name": "Barbell Row",
                        "equipment_tags": ["barbell"],
                        "substitution_candidates": ["Cable Row", "DB Row"],
                    },
                    {
                        "id": "db_press",
                        "name": "DB Shoulder Press",
                        "equipment_tags": ["dumbbell"],
                        "substitution_candidates": ["Machine Shoulder Press", "DB Arnold Press"],
                    },
                ],
            }
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
        available_equipment=["dumbbell"],
    )

    exercises = plan["sessions"][0]["exercises"]
    assert len(exercises) == 2
    assert [exercise["id"] for exercise in exercises] == ["db_row", "db_press"]
    assert exercises[0]["primary_exercise_id"] == "barbell_row"
    assert exercises[0]["substitution_candidates"] == ["DB Row"]
    assert exercises[1]["substitution_candidates"] == ["DB Arnold Press"]


def test_generate_week_plan_compresses_sessions_evenly_for_two_days() -> None:
    template = {
        "id": "compression_two_day",
        "sessions": [
            {"name": "Day A", "exercises": [{"id": "a", "name": "A"}]},
            {"name": "Day B", "exercises": [{"id": "b", "name": "B"}]},
            {"name": "Day C", "exercises": [{"id": "c", "name": "C"}]},
            {"name": "Day D", "exercises": [{"id": "d", "name": "D"}]},
            {"name": "Day E", "exercises": [{"id": "e", "name": "E"}]},
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
    )

    assert [session["title"] for session in plan["sessions"]] == ["Day A", "Day E"]
    assert [session["session_id"] for session in plan["sessions"]] == [
        "compression_two_day-1",
        "compression_two_day-5",
    ]


def test_generate_week_plan_compresses_sessions_evenly_for_three_days() -> None:
    template = {
        "id": "compression_three_day",
        "sessions": [
            {"name": "Day A", "exercises": [{"id": "a", "name": "A"}]},
            {"name": "Day B", "exercises": [{"id": "b", "name": "B"}]},
            {"name": "Day C", "exercises": [{"id": "c", "name": "C"}]},
            {"name": "Day D", "exercises": [{"id": "d", "name": "D"}]},
            {"name": "Day E", "exercises": [{"id": "e", "name": "E"}]},
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=3,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
    )

    assert [session["title"] for session in plan["sessions"]] == ["Day A", "Day C", "Day E"]


def test_generate_week_plan_honors_template_day_offsets() -> None:
    template = {
        "id": "offset_schedule",
        "sessions": [
            {"name": "Full Body #1", "day_offset": 0, "exercises": [{"id": "a", "name": "A"}]},
            {"name": "Full Body #2", "day_offset": 1, "exercises": [{"id": "b", "name": "B"}]},
            {"name": "Full Body #3", "day_offset": 3, "exercises": [{"id": "c", "name": "C"}]},
            {"name": "Full Body #4", "day_offset": 4, "exercises": [{"id": "d", "name": "D"}]},
            {"name": "Arms + Weak Points", "day_offset": 5, "exercises": [{"id": "e", "name": "E"}]},
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=5,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
    )

    week_start = date.fromisoformat(plan["week_start"])
    assert [session["title"] for session in plan["sessions"]] == [
        "Full Body #1",
        "Full Body #2",
        "Full Body #3",
        "Full Body #4",
        "Arms + Weak Points",
    ]
    assert [session["date"] for session in plan["sessions"]] == [
        week_start.isoformat(),
        (week_start + timedelta(days=1)).isoformat(),
        (week_start + timedelta(days=3)).isoformat(),
        (week_start + timedelta(days=4)).isoformat(),
        (week_start + timedelta(days=5)).isoformat(),
    ]


def test_generate_week_plan_applies_deterministic_soreness_modifiers() -> None:
    template = {
        "id": "soreness_modifier_test",
        "sessions": [
            {
                "name": "Session A",
                "exercises": [
                    {
                        "id": "bench",
                        "name": "Bench Press",
                        "start_weight": 100,
                        "primary_muscles": ["chest", "triceps"],
                    },
                    {
                        "id": "row",
                        "name": "Barbell Row",
                        "start_weight": 100,
                        "primary_muscles": ["lats", "mid_back", "biceps"],
                    },
                ],
            }
        ],
    }

    baseline = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
    )
    soreness_adjusted = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
        soreness_by_muscle={"chest": "severe", "back": "moderate", "biceps": "mild"},
    )

    baseline_exercises = baseline["sessions"][0]["exercises"]
    adjusted_exercises = soreness_adjusted["sessions"][0]["exercises"]

    assert baseline["sessions"][0]["session_id"] == soreness_adjusted["sessions"][0]["session_id"]
    assert [item["id"] for item in baseline_exercises] == [item["id"] for item in adjusted_exercises]
    assert baseline_exercises[0]["recommended_working_weight"] == 100
    assert adjusted_exercises[0]["recommended_working_weight"] == pytest.approx(92.5)
    assert baseline_exercises[1]["recommended_working_weight"] == 100
    assert adjusted_exercises[1]["recommended_working_weight"] == pytest.approx(97.5)


def test_generate_week_plan_mild_soreness_does_not_change_weight() -> None:
    template = {
        "id": "mild_soreness_no_change",
        "sessions": [
            {
                "name": "Session A",
                "exercises": [
                    {
                        "id": "curl",
                        "name": "DB Curl",
                        "start_weight": 32.5,
                        "primary_muscles": ["biceps"],
                    }
                ],
            }
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
        soreness_by_muscle={"biceps": "mild"},
    )

    assert plan["sessions"][0]["exercises"][0]["recommended_working_weight"] == pytest.approx(32.5)
