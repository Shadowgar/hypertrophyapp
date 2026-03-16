from datetime import date, timedelta
from pathlib import Path

import pytest

import core_engine.scheduler as scheduler_module
from core_engine import generate_week_plan


def _scheduler_rule_set() -> dict[str, object]:
    return {
        "progression_rules": {
            "on_success": {"percent": 2.5},
            "on_under_target": {"reduce_percent": 2.5, "after_exposures": 2},
        },
        "fatigue_rules": {
            "high_fatigue_trigger": {
                "conditions": ["session_rpe_avg >= 9", "under_target_exposures >= 2"]
            },
            "on_high_fatigue": {"action": "reduce_volume", "set_delta": -1},
        },
        "deload_rules": {
            "scheduled_every_n_weeks": 6,
            "early_deload_trigger": "three_consecutive_under_target_sessions",
            "on_deload": {"set_reduction_percent": 35, "load_reduction_percent": 10},
        },
        "substitution_rules": {
            "equipment_mismatch": "use_first_compatible_substitution",
            "repeat_failure_trigger": "switch_after_three_failed_exposures",
        },
        "generated_week_scheduler_rules": {
            "mesocycle": {
                "sequence_completion_phase_transition_reason": "authored_sequence_complete",
                "post_authored_sequence_behavior": "hold_last_authored_week",
                "soreness_deload_trigger": {
                    "minimum_severe_count": 2,
                    "reason": "early_soreness",
                },
                "adherence_deload_trigger": {
                    "maximum_score": 2,
                    "reason": "early_adherence",
                },
                "stimulus_fatigue_deload_trigger": {
                    "deload_pressure": "high",
                    "recoverability": "low",
                    "reason": "early_sfr_recovery",
                },
            },
            "exercise_adjustment": {
                "policies": [
                    {
                        "policy_id": "high_fatigue_reduce_load_and_sets",
                        "match_policy": "all",
                        "conditions": {
                            "minimum_fatigue_score": 0.8,
                            "last_progression_actions": ["reduce_load"],
                        },
                        "adjustment": {
                            "load_scale": 0.95,
                            "set_delta": -1,
                            "substitution_pressure": "high",
                            "substitution_guidance": (
                                "prefer_compatible_variants_if_recovery_constraints_persist"
                            ),
                        },
                    },
                    {
                        "policy_id": "moderate_recovery_pressure",
                        "match_policy": "any",
                        "conditions": {
                            "minimum_fatigue_score": 0.7,
                            "minimum_consecutive_under_target_exposures": 2,
                            "last_progression_actions": ["reduce_load"],
                        },
                        "adjustment": {
                            "load_scale": 0.95,
                            "set_delta": 0,
                            "substitution_pressure": "moderate",
                            "substitution_guidance": (
                                "compatible_variants_available_if_recovery_constraints_persist"
                            ),
                        },
                    },
                ],
                "default_adjustment": {
                    "load_scale": 1.0,
                    "set_delta": 0,
                    "substitution_pressure": "low",
                    "substitution_guidance": None,
                },
                "substitution_pressure_guidance": {
                    "moderate": "compatible_variants_available_if_recovery_constraints_persist",
                    "high": "prefer_compatible_variants_if_recovery_constraints_persist",
                },
            },
            "session_selection": {
                "recent_history_exercise_limit": 6,
                "anchor_first_session_when_day_roles_present": True,
                "required_day_roles_when_compressed": ["weak_point_arms"],
                "structural_slot_role_priority": {
                    "weak_point": 120,
                    "primary_compound": 110,
                    "secondary_compound": 80,
                },
                "day_role_priority": {
                    "weak_point_arms": 100,
                    "full_body_1": 80,
                    "full_body_2": 80,
                    "full_body_3": 80,
                    "full_body_4": 80,
                },
                "missed_day_policy": "roll-forward-priority-lifts",
            },
            "session_exercise_cap": {
                "time_budget_thresholds": [
                    {"maximum_minutes": 30, "exercise_limit": 3},
                    {"maximum_minutes": 45, "exercise_limit": 4},
                    {"maximum_minutes": 60, "exercise_limit": 5},
                ],
                "default_slot_role_priority": {
                    "primary_compound": 100,
                    "weak_point": 90,
                    "secondary_compound": 80,
                    "accessory": 50,
                    "isolation": 40,
                },
                "day_role_slot_role_priority_overrides": {
                    "weak_point_arms": {
                        "weak_point": 120,
                        "primary_compound": 30,
                        "secondary_compound": 20,
                    }
                },
            },
            "muscle_coverage": {
                "tracked_muscles": [
                    "chest",
                    "back",
                    "quads",
                    "hamstrings",
                    "glutes",
                    "shoulders",
                    "biceps",
                    "triceps",
                    "calves",
                ],
                "minimum_sets_per_muscle": 2,
                "authored_label_normalization": {
                    "chest": "chest",
                    "pec": "chest",
                    "pecs": "chest",
                    "back": "back",
                    "lats": "back",
                    "lat": "back",
                    "mid_back": "back",
                    "upper_back": "back",
                    "erectors": "back",
                    "quads": "quads",
                    "quadriceps": "quads",
                    "hamstrings": "hamstrings",
                    "glutes": "glutes",
                    "shoulders": "shoulders",
                    "delts": "shoulders",
                    "front_delts": "shoulders",
                    "rear_delts": "shoulders",
                    "side_delts": "shoulders",
                    "biceps": "biceps",
                    "triceps": "triceps",
                    "calves": "calves",
                },
            },
        },
    }


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


def test_generate_week_plan_preserves_authored_execution_details() -> None:
    template = {
        "id": "authored_slot_runtime_test",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "bayesian_curl",
                        "primary_exercise_id": "bayesian_curl",
                        "name": "Bayesian Curl",
                        "sets": 3,
                        "rep_range": [10, 12],
                        "start_weight": 17.5,
                        "slot_role": "weak_point",
                        "substitution_candidates": ["Cable Curl", "Machine Curl"],
                        "last_set_intensity_technique": "Dropset",
                        "warm_up_sets": "1",
                        "working_sets": "3",
                        "reps": "10-12",
                        "early_set_rpe": "~9",
                        "last_set_rpe": "10",
                        "rest": "~1-2 min",
                        "tracking_set_1": "20",
                        "tracking_set_2": "22.5",
                        "tracking_set_3": "25",
                        "tracking_set_4": None,
                        "substitution_option_1": "Cable Curl",
                        "substitution_option_2": "Machine Curl",
                        "demo_url": "https://example.com/bayesian-curl-demo",
                        "video_url": "https://example.com/bayesian-curl-video",
                        "notes": "Keep your upper arm fixed behind your torso.",
                        "video": {"youtube_url": "https://example.com/bayesian-curl-video"},
                    }
                ],
            }
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

    first_exercise = plan["sessions"][0]["exercises"][0]
    assert first_exercise["last_set_intensity_technique"] == "Dropset"
    assert first_exercise["warm_up_sets"] == "1"
    assert first_exercise["working_sets"] == "3"
    assert first_exercise["reps"] == "10-12"
    assert first_exercise["early_set_rpe"] == "~9"
    assert first_exercise["last_set_rpe"] == "10"
    assert first_exercise["rest"] == "~1-2 min"
    assert first_exercise["tracking_set_1"] == "20"
    assert first_exercise["tracking_set_2"] == "22.5"
    assert first_exercise["tracking_set_3"] == "25"
    assert first_exercise["tracking_set_4"] is None
    assert first_exercise["substitution_option_1"] == "Cable Curl"
    assert first_exercise["substitution_option_2"] == "Machine Curl"
    assert first_exercise["demo_url"] == "https://example.com/bayesian-curl-demo"
    assert first_exercise["video_url"] == "https://example.com/bayesian-curl-video"
    assert first_exercise["video"] == {"youtube_url": "https://example.com/bayesian-curl-video"}
    assert first_exercise["notes"] == "Keep your upper arm fixed behind your torso."


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


def test_generate_week_plan_auto_substitutes_after_repeat_failure_threshold() -> None:
    template = {
        "id": "repeat_failure_generation_test",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "db_press",
                        "name": "DB Press",
                        "equipment_tags": ["dumbbell"],
                        "substitution_candidates": ["DB Floor Press"],
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
        progression_state_per_exercise=[
            {
                "exercise_id": "db_press",
                "consecutive_under_target_exposures": 3,
                "last_progression_action": "hold",
            }
        ],
        rule_set={
            "substitution_rules": {
                "repeat_failure_trigger": "switch_after_three_failed_exposures",
            }
        },
    )

    exercise = plan["sessions"][0]["exercises"][0]
    assert exercise["id"] == "db_floor_press"
    assert exercise["name"] == "DB Floor Press"
    assert exercise["primary_exercise_id"] == "db_press"
    assert exercise["repeat_failure_substitution"]["recommended_name"] == "DB Floor Press"
    assert exercise["repeat_failure_substitution"]["failed_exposure_count"] == 3
    assert exercise["repeat_failure_substitution"]["decision_trace"]["interpreter"] == "resolve_repeat_failure_substitution"


def test_generate_week_plan_applies_exercise_recovery_pressure_from_progression_state() -> None:
    template = {
        "id": "exercise_recovery_pressure_test",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "incline_press",
                        "name": "Incline DB Press",
                        "sets": 4,
                        "start_weight": 100,
                        "substitution_candidates": ["Machine Incline Press", "DB Floor Press"],
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
        available_equipment=["machine", "dumbbell"],
        progression_state_per_exercise=[
            {
                "exercise_id": "incline_press",
                "consecutive_under_target_exposures": 2,
                "last_progression_action": "reduce_load",
                "fatigue_score": 0.85,
            }
        ],
        rule_set=_scheduler_rule_set(),
    )

    exercise = plan["sessions"][0]["exercises"][0]
    assert exercise["sets"] == 3
    assert exercise["recommended_working_weight"] == 95.0
    assert exercise["substitution_pressure"] == "high"
    assert exercise["substitution_guidance"] == "prefer_compatible_variants_if_recovery_constraints_persist"
    assert exercise["recovery_adjustment_trace"]["interpreter"] == "resolve_scheduler_exercise_adjustment_runtime"
    assert exercise["recovery_adjustment_trace"]["outcome"]["merged_substitution_pressure"] == "high"
    assert exercise["repeat_failure_substitution"] is None


def test_generate_week_plan_limits_session_exercises_for_low_time_budget() -> None:
    template = {
        "id": "time_budget_generation_test",
        "sessions": [
            {
                "name": "A",
                "exercises": [{"id": f"lift_{idx}", "name": f"Lift {idx}", "sets": 3} for idx in range(1, 7)],
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
        session_time_budget_minutes=30,
        rule_set=_scheduler_rule_set(),
    )

    exercises = plan["sessions"][0]["exercises"]
    assert [exercise["id"] for exercise in exercises] == ["lift_1", "lift_2", "lift_3"]


def test_generate_week_plan_preserves_weak_point_slots_when_time_budget_caps_session() -> None:
    template = {
        "id": "time_budget_weak_point_preservation",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {"id": "bench", "name": "Bench", "sets": 3, "slot_role": "primary_compound"},
                    {"id": "row", "name": "Row", "sets": 3, "slot_role": "secondary_compound"},
                    {"id": "curl", "name": "Curl", "sets": 2, "slot_role": "isolation"},
                    {"id": "weak_chest", "name": "Weak Chest Fly", "sets": 2, "slot_role": "weak_point"},
                    {"id": "pushdown", "name": "Pushdown", "sets": 2, "slot_role": "isolation"},
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
        session_time_budget_minutes=30,
        rule_set=_scheduler_rule_set(),
    )

    exercises = plan["sessions"][0]["exercises"]
    assert [exercise["id"] for exercise in exercises] == ["bench", "row", "weak_chest"]


def test_generate_week_plan_preserves_weak_point_day_under_frequency_compression() -> None:
    template = {
        "id": "frequency_weak_point_preservation",
        "sessions": [
            {
                "name": "Day A",
                "exercises": [{"id": "bench", "name": "Bench", "slot_role": "primary_compound", "primary_muscles": ["chest"]}],
            },
            {
                "name": "Day B",
                "exercises": [{"id": "row", "name": "Row", "slot_role": "secondary_compound", "primary_muscles": ["back"]}],
            },
            {
                "name": "Day C",
                "exercises": [
                    {"id": "weak_chest", "name": "Weak Chest Fly", "slot_role": "weak_point", "primary_muscles": ["chest"]},
                    {"id": "weak_ham", "name": "Weak Ham Curl", "slot_role": "weak_point", "primary_muscles": ["hamstrings"]},
                ],
            },
            {
                "name": "Day D",
                "exercises": [{"id": "rdl", "name": "RDL", "slot_role": "primary_compound", "primary_muscles": ["hamstrings"]}],
            },
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
        rule_set=_scheduler_rule_set(),
    )

    titles = [session["title"] for session in plan["sessions"]]
    assert len(titles) == 2
    assert "Day C" in titles


def test_generate_week_plan_filters_restricted_movement_patterns() -> None:
    template = {
        "id": "movement_restriction_generation_test",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "ohp",
                        "name": "Overhead Press",
                        "sets": 3,
                        "movement_pattern": "vertical_press",
                    },
                    {
                        "id": "row",
                        "name": "Chest Supported Row",
                        "sets": 3,
                        "movement_pattern": "horizontal_pull",
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
        movement_restrictions=["overhead_pressing"],
    )

    exercises = plan["sessions"][0]["exercises"]
    assert [exercise["id"] for exercise in exercises] == ["row"]


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
        rule_set=_scheduler_rule_set(),
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


def test_generate_week_plan_does_not_invent_soreness_load_modifiers() -> None:
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
    assert adjusted_exercises[0]["recommended_working_weight"] == pytest.approx(100.0)
    assert baseline_exercises[1]["recommended_working_weight"] == 100
    assert adjusted_exercises[1]["recommended_working_weight"] == pytest.approx(100.0)


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


def test_generate_week_plan_uses_sfr_for_early_recovery_deload_and_substitution_pressure() -> None:
    template = {
        "id": "sfr_recovery_deload_test",
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "sessions": [
            {
                "name": "Session A",
                "exercises": [
                    {
                        "id": "press",
                        "name": "DB Press",
                        "sets": 4,
                        "start_weight": 50,
                        "primary_muscles": ["chest", "triceps"],
                        "substitution_candidates": ["Machine Press"],
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
        stimulus_fatigue_response={
            "stimulus_quality": "low",
            "fatigue_cost": "high",
            "recoverability": "low",
            "progression_eligibility": False,
            "deload_pressure": "high",
            "substitution_pressure": "high",
        },
        rule_set=_scheduler_rule_set(),
    )

    assert plan["mesocycle"]["is_deload_week"] is True
    assert plan["mesocycle"]["deload_reason"] == "early_sfr_recovery"
    exercise = plan["sessions"][0]["exercises"][0]
    assert exercise["sets"] == 3
    assert exercise["substitution_pressure"] == "high"
    assert exercise["substitution_guidance"] == "prefer_compatible_variants_if_recovery_constraints_persist"


def test_generate_week_plan_tracks_weekly_volume_and_coverage_from_canonical_muscle_contract() -> None:
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
        rule_set=_scheduler_rule_set(),
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


def test_generate_week_plan_does_not_infer_muscle_coverage_from_exercise_name_tokens() -> None:
    template = {
        "id": "coverage_untracked_test",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "mystery",
                        "name": "Lat Raise Pec Deck",
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
        rule_set=_scheduler_rule_set(),
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
    assert plan["mesocycle"]["decision_trace"]["interpreter"] == "resolve_scheduler_mesocycle_runtime"
    assert plan["deload"]["active"] is True
    assert ex["sets"] == 3
    assert ex["recommended_working_weight"] == pytest.approx(90.0)


def test_generate_week_plan_applies_authored_deload_week() -> None:
    template = {
        "id": "authored_deload_test",
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 40, "load_reduction_pct": 10},
        "sessions": [
            {
                "name": "Week 1 A",
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
        "authored_weeks": [
            {
                "week_index": 1,
                "sessions": [
                    {
                        "name": "Week 1 A",
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
            },
            {
                "week_index": 4,
                "week_role": "deload",
                "sessions": [
                    {
                        "name": "Week 4 Deload",
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
            },
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
        prior_generated_weeks=3,
    )

    ex = plan["sessions"][0]["exercises"][0]
    assert plan["mesocycle"]["is_deload_week"] is True
    assert plan["mesocycle"]["deload_reason"] == "authored_deload"
    assert plan["mesocycle"]["authored_week_index"] == 4
    assert plan["mesocycle"]["authored_week_role"] == "deload"
    assert plan["deload"]["active"] is True
    assert ex["sets"] == 3
    assert ex["recommended_working_weight"] == pytest.approx(90.0)


def test_generate_week_plan_uses_bounded_deload_noop_without_authoritative_policy() -> None:
    template = {
        "id": "authored_deload_noop_test",
        "sessions": [
            {
                "name": "Base Week",
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
        "authored_weeks": [
            {
                "week_index": 1,
                "week_role": "deload",
                "sessions": [
                    {
                        "name": "Deload Week",
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
        ],
    }

    rule_set = _scheduler_rule_set()
    rule_set["deload_rules"] = {
        "scheduled_every_n_weeks": 6,
        "early_deload_trigger": "three_consecutive_under_target_sessions",
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
        rule_set=rule_set,
    )

    ex = plan["sessions"][0]["exercises"][0]
    assert plan["mesocycle"]["is_deload_week"] is True
    assert plan["deload"]["active"] is True
    assert plan["deload"]["set_reduction_pct"] == 0
    assert plan["deload"]["load_reduction_pct"] == 0
    assert plan["deload"]["decision_trace"]["outcome"]["source"] == "bounded_non_authoritative_noop"
    assert ex["sets"] == 5
    assert ex["recommended_working_weight"] == pytest.approx(100.0)


def test_scheduler_source_does_not_define_local_soreness_or_muscle_doctrine_helpers() -> None:
    source = Path(scheduler_module.__file__).read_text(encoding="utf-8")

    forbidden_names = [
        "_SORENESS_WEIGHT_FACTOR",
        "_apply_soreness_modifier",
        "_MUSCLE_ALIASES",
        "_TRACKED_MUSCLES",
        "_MIN_SETS_PER_MUSCLE",
        "_normalize_muscle_label",
        "_token_mapped_muscles",
        "_resolve_exercise_muscles",
    ]

    for name in forbidden_names:
        assert name not in source


def test_generate_week_plan_prefers_authored_deload_reason_when_scheduled_and_authored_overlap() -> None:
    template = {
        "id": "authored_deload_overlap_test",
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 40, "load_reduction_pct": 10},
        "sessions": [
            {
                "name": "Week 1 A",
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
        "authored_weeks": [
            {
                "week_index": 1,
                "week_role": "accumulation",
                "sessions": [
                    {
                        "name": "Week 1 A",
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
            },
            {
                "week_index": 6,
                "week_role": "deload",
                "sessions": [
                    {
                        "name": "Week 6 Deload",
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
            },
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

    assert plan["mesocycle"]["is_deload_week"] is True
    assert plan["mesocycle"]["deload_reason"] == "authored_deload"
    assert plan["mesocycle"]["authored_week_role"] == "deload"


def test_generate_week_plan_marks_authored_sequence_complete_after_last_authored_week() -> None:
    template = {
        "id": "authored_sequence_complete_test",
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "sessions": [
            {
                "name": "Week 1 A",
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
        "authored_weeks": [
            {
                "week_index": 1,
                "week_role": "accumulation",
                "sessions": [
                    {
                        "name": "Week 1 A",
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
            },
            {
                "week_index": 10,
                "week_role": "intensification",
                "sessions": [
                    {
                        "name": "Week 10 A",
                        "exercises": [
                            {
                                "id": "bench",
                                "name": "Bench Press",
                                "sets": 4,
                                "start_weight": 105,
                                "primary_muscles": ["chest"],
                            }
                        ],
                    }
                ],
            },
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
        prior_generated_weeks=10,
        rule_set=_scheduler_rule_set(),
    )

    assert plan["mesocycle"]["authored_week_index"] == 10
    assert plan["mesocycle"]["authored_week_role"] == "intensification"
    assert plan["mesocycle"]["authored_sequence_length"] == 2
    assert plan["mesocycle"]["authored_sequence_complete"] is True
    assert plan["mesocycle"]["phase_transition_pending"] is True
    assert plan["mesocycle"]["phase_transition_reason"] == "authored_sequence_complete"
    assert plan["mesocycle"]["post_authored_behavior"] == "hold_last_authored_week"


def test_generate_week_plan_preserves_weak_point_arms_day_when_compressing_five_day_authored_source() -> None:
    template = {
        "id": "five_day_authored_test",
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "sessions": [
            {"name": "Full Body #1", "day_role": "full_body_1", "exercises": [{"id": "lat", "name": "Lat Pulldown", "sets": 3, "start_weight": 100, "slot_role": "primary_compound", "primary_muscles": ["back"]}]},
            {"name": "Full Body #2", "day_role": "full_body_2", "exercises": [{"id": "rdl", "name": "RDL", "sets": 3, "start_weight": 100, "slot_role": "primary_compound", "primary_muscles": ["hamstrings"]}]},
            {"name": "Full Body #3", "day_role": "full_body_3", "exercises": [{"id": "ohp", "name": "OHP", "sets": 3, "start_weight": 60, "slot_role": "primary_compound", "primary_muscles": ["shoulders"]}]},
            {"name": "Full Body #4", "day_role": "full_body_4", "exercises": [{"id": "hack", "name": "Hack Squat", "sets": 3, "start_weight": 140, "slot_role": "primary_compound", "primary_muscles": ["quads"]}]},
            {"name": "Arms & Weak Points", "day_role": "weak_point_arms", "exercises": [{"id": "weak_chest", "name": "Weak Chest Fly", "sets": 2, "start_weight": 30, "slot_role": "weak_point", "primary_muscles": ["chest"]}]},
        ],
        "authored_weeks": [
            {
                "week_index": 1,
                "week_role": "accumulation",
                "sessions": [
                    {"name": "Full Body #1", "day_role": "full_body_1", "exercises": [{"id": "lat", "name": "Lat Pulldown", "sets": 3, "start_weight": 100, "slot_role": "primary_compound", "primary_muscles": ["back"]}]},
                    {"name": "Full Body #2", "day_role": "full_body_2", "exercises": [{"id": "rdl", "name": "RDL", "sets": 3, "start_weight": 100, "slot_role": "primary_compound", "primary_muscles": ["hamstrings"]}]},
                    {"name": "Full Body #3", "day_role": "full_body_3", "exercises": [{"id": "ohp", "name": "OHP", "sets": 3, "start_weight": 60, "slot_role": "primary_compound", "primary_muscles": ["shoulders"]}]},
                    {"name": "Full Body #4", "day_role": "full_body_4", "exercises": [{"id": "hack", "name": "Hack Squat", "sets": 3, "start_weight": 140, "slot_role": "primary_compound", "primary_muscles": ["quads"]}]},
                    {"name": "Arms & Weak Points", "day_role": "weak_point_arms", "exercises": [{"id": "weak_chest", "name": "Weak Chest Fly", "sets": 2, "start_weight": 30, "slot_role": "weak_point", "primary_muscles": ["chest"]}]},
                ],
            }
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=4,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
        prior_generated_weeks=0,
    )

    assert any(session["title"] == "Arms & Weak Points" for session in plan["sessions"])


def test_generate_week_plan_keeps_first_authored_day_when_compressing_five_days_to_three() -> None:
    template = {
        "id": "five_day_anchor_test",
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "sessions": [],
        "authored_weeks": [
            {
                "week_index": 1,
                "week_role": "adaptation",
                "sessions": [
                    {"name": "Full Body #1", "day_role": "full_body_1", "exercises": [{"id": "lat", "name": "Lat Pulldown", "sets": 3, "start_weight": 100, "slot_role": "accessory", "primary_muscles": ["back"]}]},
                    {"name": "Full Body #2", "day_role": "full_body_2", "exercises": [{"id": "rdl", "name": "RDL", "sets": 3, "start_weight": 100, "slot_role": "secondary_compound", "primary_muscles": ["hamstrings"]}]},
                    {"name": "Full Body #3", "day_role": "full_body_3", "exercises": [{"id": "pullup", "name": "Pull-Up", "sets": 3, "start_weight": 0, "slot_role": "primary_compound", "primary_muscles": ["back"]}]},
                    {"name": "Full Body #4", "day_role": "full_body_4", "exercises": [{"id": "hack", "name": "Hack Squat", "sets": 3, "start_weight": 140, "slot_role": "primary_compound", "primary_muscles": ["quads"]}]},
                    {"name": "Arms & Weak Points", "day_role": "weak_point_arms", "exercises": [{"id": "weak_chest", "name": "Weak Chest Fly", "sets": 2, "start_weight": 30, "slot_role": "weak_point", "primary_muscles": ["chest"]}]},
                ],
            }
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=3,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
        prior_generated_weeks=0,
    )

    titles = [session["title"] for session in plan["sessions"]]
    assert "Full Body #1" in titles
    assert "Arms & Weak Points" in titles


def test_generate_week_plan_keeps_first_authored_day_when_compressing_five_days_to_two() -> None:
    template = {
        "id": "five_day_two_day_anchor_test",
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "sessions": [],
        "authored_weeks": [
            {
                "week_index": 1,
                "week_role": "adaptation",
                "sessions": [
                    {"name": "Full Body #1", "day_role": "full_body_1", "exercises": [{"id": "lat", "name": "Lat Pulldown", "sets": 3, "start_weight": 100, "slot_role": "accessory", "primary_muscles": ["back"]}]},
                    {"name": "Full Body #2", "day_role": "full_body_2", "exercises": [{"id": "rdl", "name": "RDL", "sets": 3, "start_weight": 100, "slot_role": "secondary_compound", "primary_muscles": ["hamstrings"]}]},
                    {"name": "Full Body #3", "day_role": "full_body_3", "exercises": [{"id": "pullup", "name": "Pull-Up", "sets": 3, "start_weight": 0, "slot_role": "primary_compound", "primary_muscles": ["back"]}]},
                    {"name": "Full Body #4", "day_role": "full_body_4", "exercises": [{"id": "hack", "name": "Hack Squat", "sets": 3, "start_weight": 140, "slot_role": "primary_compound", "primary_muscles": ["quads"]}]},
                    {"name": "Arms & Weak Points", "day_role": "weak_point_arms", "exercises": [{"id": "weak_chest", "name": "Weak Chest Fly", "sets": 2, "start_weight": 30, "slot_role": "weak_point", "primary_muscles": ["chest"]}]},
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
        prior_generated_weeks=0,
        rule_set=_scheduler_rule_set(),
    )

    titles = [session["title"] for session in plan["sessions"]]
    assert titles == ["Full Body #1", "Arms & Weak Points"]
    assert plan["session_selection_trace"]["interpreter"] == "resolve_scheduler_session_selection"
    assert plan["missed_day_policy"] == "roll-forward-priority-lifts"
    assert plan["missed_day_policy_trace"]["interpreter"] == "resolve_scheduler_session_selection"
    assert plan["missed_day_policy_trace"]["outcome"]["missed_day_policy"] == "roll-forward-priority-lifts"


def test_generate_week_plan_preserves_weak_point_slots_when_capping_merged_weak_point_day() -> None:
    template = {
        "id": "five_day_weak_point_cap_test",
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "sessions": [],
        "authored_weeks": [
            {
                "week_index": 1,
                "week_role": "adaptation",
                "sessions": [
                    {"name": "Full Body #1", "day_role": "full_body_1", "exercises": [{"id": "press", "name": "Press", "sets": 3, "start_weight": 100, "slot_role": "primary_compound", "primary_muscles": ["chest"]}]},
                    {"name": "Full Body #2", "day_role": "full_body_2", "exercises": [{"id": "rdl", "name": "RDL", "sets": 3, "start_weight": 100, "slot_role": "secondary_compound", "primary_muscles": ["hamstrings"]}]},
                    {"name": "Full Body #3", "day_role": "full_body_3", "exercises": [{"id": "pullup", "name": "Pull-Up", "sets": 3, "start_weight": 0, "slot_role": "primary_compound", "primary_muscles": ["back"]}]},
                    {"name": "Full Body #4", "day_role": "full_body_4", "exercises": [{"id": "hack", "name": "Hack Squat", "sets": 3, "start_weight": 140, "slot_role": "primary_compound", "primary_muscles": ["quads"]}]},
                    {
                        "name": "Arms & Weak Points",
                        "day_role": "weak_point_arms",
                        "exercises": [
                            {"id": "weak_1", "name": "Weak Point 1", "sets": 2, "start_weight": 30, "slot_role": "weak_point", "primary_muscles": ["chest"]},
                            {"id": "weak_2", "name": "Weak Point 2", "sets": 2, "start_weight": 30, "slot_role": "weak_point", "primary_muscles": ["hamstrings"]},
                            {"id": "curl", "name": "Curl", "sets": 2, "start_weight": 20, "slot_role": "weak_point", "primary_muscles": ["biceps"]},
                        ],
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
        prior_generated_weeks=0,
        session_time_budget_minutes=30,
        rule_set=_scheduler_rule_set(),
    )

    weak_day = next(session for session in plan["sessions"] if session["title"] == "Arms & Weak Points")
    assert [exercise["id"] for exercise in weak_day["exercises"]] == ["weak_1", "weak_2", "curl"]


def test_generate_week_plan_keeps_all_primary_compound_patterns_when_compressing_five_days_to_three() -> None:
    template = {
        "id": "five_day_primary_patterns_test",
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "sessions": [],
        "authored_weeks": [
            {
                "week_index": 1,
                "week_role": "accumulation",
                "sessions": [
                    {"name": "Full Body #1", "day_role": "full_body_1", "exercises": [{"id": "lat", "name": "Lat Pulldown", "sets": 3, "start_weight": 100, "slot_role": "primary_compound", "primary_muscles": ["back"]}]},
                    {"name": "Full Body #2", "day_role": "full_body_2", "exercises": [{"id": "rdl", "name": "RDL", "sets": 3, "start_weight": 100, "slot_role": "primary_compound", "primary_muscles": ["hamstrings"]}]},
                    {"name": "Full Body #3", "day_role": "full_body_3", "exercises": [{"id": "ohp", "name": "OHP", "sets": 3, "start_weight": 60, "slot_role": "primary_compound", "primary_muscles": ["shoulders"]}]},
                    {"name": "Full Body #4", "day_role": "full_body_4", "exercises": [{"id": "hack", "name": "Hack Squat", "sets": 3, "start_weight": 140, "slot_role": "primary_compound", "primary_muscles": ["quads"]}]},
                    {"name": "Arms & Weak Points", "day_role": "weak_point_arms", "exercises": [{"id": "weak_chest", "name": "Weak Chest Fly", "sets": 2, "start_weight": 30, "slot_role": "weak_point", "primary_muscles": ["chest"]}]},
                ],
            }
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=3,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
        prior_generated_weeks=0,
    )

    movement_patterns = {
        exercise["id"]
        for session in plan["sessions"]
        for exercise in session["exercises"]
    }
    assert {"lat", "rdl", "ohp", "hack"}.issubset(movement_patterns)


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
        rule_set=_scheduler_rule_set(),
    )

    ex = plan["sessions"][0]["exercises"][0]
    assert plan["mesocycle"]["is_deload_week"] is True
    assert plan["mesocycle"]["deload_reason"] == "early_soreness+early_adherence"
    assert plan["deload"]["active"] is True
    assert ex["sets"] == 3
    assert ex["recommended_working_weight"] == pytest.approx(72.0)


def test_generate_week_plan_does_not_invent_cut_specific_mesocycle_cadence() -> None:
    template = {
        "id": "cut_mesocycle_trace_test",
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "bench",
                        "name": "Bench Press",
                        "sets": 4,
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
        phase="cut",
        prior_generated_weeks=4,
    )

    assert plan["mesocycle"]["trigger_weeks_effective"] == 6
    assert plan["mesocycle"]["week_index"] == 5
    assert plan["mesocycle"]["decision_trace"]["inputs"]["phase"] == "cut"
