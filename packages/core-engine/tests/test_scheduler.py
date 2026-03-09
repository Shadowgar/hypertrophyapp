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
    assert exercises[0]["substitution_decision_trace"]["interpreter"] == "resolve_equipment_substitution"
    assert exercises[0]["substitution_decision_trace"]["outcome"]["selected_name"] == "DB Row"
    assert exercises[1]["substitution_candidates"] == ["DB Arnold Press"]


def test_generate_week_plan_threads_substitution_rules_into_equipment_swap_policy() -> None:
    template = {
        "id": "equipment_rule_runtime_test",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "barbell_row",
                        "name": "Barbell Row",
                        "equipment_tags": ["barbell"],
                        "substitution_candidates": ["Cable Row", "DB Row"],
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
        available_equipment=["dumbbell"],
        rule_set={
            "substitution_rules": {
                "equipment_mismatch": "use_first_compatible_substitution",
                "repeat_failure_trigger": "switch_after_three_failed_exposures",
            }
        },
    )

    exercise = plan["sessions"][0]["exercises"][0]
    assert exercise["id"] == "db_row"
    assert exercise["name"] == "DB Row"
    assert exercise["substitution_decision_trace"]["outcome"]["auto_substituted"] is True


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


def test_generate_week_plan_preserves_priority_lifts_when_days_compress() -> None:
    template = {
        "id": "compression_priority_continuity",
        "sessions": [
            {
                "name": "Day A",
                "exercises": [{"id": "bench", "name": "Bench Press", "primary_muscles": ["chest"]}],
            },
            {
                "name": "Day B",
                "exercises": [{"id": "squat", "name": "Back Squat", "primary_muscles": ["quads"]}],
            },
            {
                "name": "Day C",
                "exercises": [{"id": "row", "name": "Barbell Row", "primary_muscles": ["back"]}],
            },
            {
                "name": "Day D",
                "exercises": [{"id": "press", "name": "Overhead Press", "primary_muscles": ["shoulders"]}],
            },
            {
                "name": "Day E",
                "exercises": [{"id": "rdl", "name": "Romanian Deadlift", "primary_muscles": ["hamstrings"]}],
            },
        ],
    }

    history = [
        {"primary_exercise_id": "squat", "exercise_id": "squat", "next_working_weight": 100},
        {"primary_exercise_id": "squat", "exercise_id": "squat", "next_working_weight": 100},
        {"primary_exercise_id": "row", "exercise_id": "row", "next_working_weight": 80},
        {"primary_exercise_id": "row", "exercise_id": "row", "next_working_weight": 80},
    ]

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=history,
        phase="maintenance",
    )

    assert [session["title"] for session in plan["sessions"]] == ["Day B", "Day C"]
    assert [session["session_id"] for session in plan["sessions"]] == [
        "compression_priority_continuity-2",
        "compression_priority_continuity-3",
    ]


def test_generate_week_plan_falls_back_to_even_compression_when_history_unknown() -> None:
    template = {
        "id": "compression_history_fallback",
        "sessions": [
            {"name": "Day A", "exercises": [{"id": "a", "name": "A"}]},
            {"name": "Day B", "exercises": [{"id": "b", "name": "B"}]},
            {"name": "Day C", "exercises": [{"id": "c", "name": "C"}]},
            {"name": "Day D", "exercises": [{"id": "d", "name": "D"}]},
            {"name": "Day E", "exercises": [{"id": "e", "name": "E"}]},
        ],
    }

    history = [
        {"primary_exercise_id": "unknown_1", "exercise_id": "unknown_1", "next_working_weight": 50},
        {"primary_exercise_id": "unknown_2", "exercise_id": "unknown_2", "next_working_weight": 50},
    ]

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=history,
        phase="maintenance",
    )

    assert [session["title"] for session in plan["sessions"]] == ["Day A", "Day E"]


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


def test_generate_week_plan_tracks_weekly_volume_and_coverage() -> None:
    template = {
        "id": "volume_tracking_test",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "bench",
                        "name": "Bench Press",
                        "sets": 3,
                        "primary_muscles": ["chest", "triceps"],
                    },
                    {
                        "id": "row",
                        "name": "Barbell Row",
                        "sets": 4,
                        "primary_muscles": ["lats", "mid_back", "biceps"],
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
    )

    volume = plan["weekly_volume_by_muscle"]
    coverage = plan["muscle_coverage"]

    assert volume["chest"] == 3
    assert volume["triceps"] == 3
    assert volume["back"] == 4
    assert volume["biceps"] == 4
    assert volume["quads"] == 0
    assert coverage["minimum_sets_per_muscle"] == 2
    assert coverage["untracked_exercise_count"] == 0
    assert "chest" in coverage["covered_muscles"]
    assert "back" in coverage["covered_muscles"]
    assert "quads" in coverage["under_target_muscles"]
    assert "hamstrings" in coverage["under_target_muscles"]


def test_generate_week_plan_counts_untracked_exercises_for_coverage() -> None:
    template = {
        "id": "coverage_untracked_test",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "mystery",
                        "name": "X1",
                        "sets": 3,
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
    )

    coverage = plan["muscle_coverage"]
    assert coverage["untracked_exercise_count"] == 1
    assert all(value == 0 for value in plan["weekly_volume_by_muscle"].values())


def test_generate_week_plan_applies_scheduled_deload_at_trigger_week() -> None:
    template = {
        "id": "scheduled_deload_test",
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 40, "load_reduction_pct": 10},
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "bench",
                        "name": "Bench Press",
                        "sets": 5,
                        "start_weight": 100,
                        "primary_muscles": ["chest"],
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
        prior_generated_weeks=5,
    )

    ex = plan["sessions"][0]["exercises"][0]
    assert plan["mesocycle"]["is_deload_week"] is True
    assert plan["mesocycle"]["deload_reason"] == "scheduled"
    assert plan["mesocycle"]["week_index"] == 6
    assert plan["deload"]["active"] is True
    assert ex["sets"] == 3
    assert ex["recommended_working_weight"] == pytest.approx(90.0)


def test_generate_week_plan_applies_early_deload_trigger_from_soreness_or_adherence() -> None:
    template = {
        "id": "early_deload_test",
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "row",
                        "name": "Barbell Row",
                        "sets": 4,
                        "start_weight": 80,
                        "primary_muscles": ["back", "biceps"],
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
        prior_generated_weeks=1,
        latest_adherence_score=2,
        severe_soreness_count=2,
    )

    ex = plan["sessions"][0]["exercises"][0]
    assert plan["mesocycle"]["is_deload_week"] is True
    assert plan["mesocycle"]["deload_reason"] == "early_soreness+early_adherence"
    assert plan["deload"]["active"] is True
    assert ex["sets"] == 3
    assert ex["recommended_working_weight"] == pytest.approx(72.5)
