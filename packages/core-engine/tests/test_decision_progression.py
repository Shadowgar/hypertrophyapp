from core_engine.decision_progression import (
    derive_readiness_score,
    evaluate_schedule_adaptation,
    recommend_phase_transition,
    recommend_progression_action,
)


def _sample_rule_set() -> dict[str, object]:
    return {
        "progression_rules": {
            "on_success": {"percent": 2.5},
            "on_under_target": {"reduce_percent": 2.5, "after_exposures": 2},
        },
        "fatigue_rules": {
            "high_fatigue_trigger": {
                "conditions": [
                    "intro phase lasts 2 weeks; avoid interpreting early underperformance as stall",
                    "session_rpe_avg >= 9 for two exposures",
                ]
            },
            "on_high_fatigue": {"action": "reduce_volume", "set_delta": -1},
        },
        "deload_rules": {
            "scheduled_every_n_weeks": 6,
            "early_deload_trigger": "repeated_under_target_plus_high_fatigue",
            "on_deload": {"set_reduction_percent": 35, "load_reduction_percent": 10},
        },
        "rationale_templates": {
            "increase_load": "Performance exceeded target range. Increase load next exposure.",
            "hold_load": "Performance stayed in range. Hold load and chase the rep ceiling.",
            "deload": "Fatigue and underperformance indicate that a short deload is warranted.",
        },
    }


def _sample_template() -> dict[str, object]:
    return {
        "id": "intelligence_test_template",
        "sessions": [
            {
                "name": "Upper Push",
                "exercises": [
                    {
                        "id": "bench",
                        "name": "Bench Press",
                        "sets": 3,
                        "start_weight": 100,
                        "primary_muscles": ["chest", "triceps"],
                        "video": {"youtube_url": "https://www.youtube.com/watch?v=abc"},
                    }
                ],
            },
            {
                "name": "Upper Pull",
                "exercises": [
                    {
                        "id": "row",
                        "name": "Barbell Row",
                        "sets": 3,
                        "start_weight": 90,
                        "primary_muscles": ["back", "biceps"],
                        "video": None,
                    }
                ],
            },
            {
                "name": "Lower Quad",
                "exercises": [
                    {
                        "id": "squat",
                        "name": "Back Squat",
                        "sets": 4,
                        "start_weight": 120,
                        "primary_muscles": ["quads", "glutes"],
                    }
                ],
            },
            {
                "name": "Lower Hinge",
                "exercises": [
                    {
                        "id": "rdl",
                        "name": "Romanian Deadlift",
                        "sets": 3,
                        "start_weight": 110,
                        "primary_muscles": ["hamstrings", "glutes"],
                    }
                ],
            },
            {
                "name": "Shoulders Arms",
                "exercises": [
                    {
                        "id": "lateral_raise",
                        "name": "Lateral Raise",
                        "sets": 3,
                        "start_weight": 20,
                        "primary_muscles": ["shoulders"],
                    },
                    {
                        "id": "calf_raise",
                        "name": "Calf Raise",
                        "sets": 3,
                        "start_weight": 80,
                        "primary_muscles": ["calves"],
                    },
                ],
            },
        ],
        "blueprint": {
            "default_training_days": 5,
            "week_sequence": ["week_base"] * 8,
            "week_templates": [
                {
                    "week_template_id": "week_base",
                    "days": [
                        {"day_id": "d1", "slots": [{"exercise_id": "bench", "primary_muscles": ["chest"]}]},
                        {"day_id": "d2", "slots": [{"exercise_id": "squat", "primary_muscles": ["quads"]}]},
                        {"day_id": "d3", "slots": [{"exercise_id": "row", "primary_muscles": ["back"]}]},
                        {"day_id": "d4", "slots": [{"exercise_id": "rdl", "primary_muscles": ["hamstrings"]}]},
                        {"day_id": "d5", "slots": [{"exercise_id": "lateral_raise", "primary_muscles": ["shoulders"]}]},
                    ],
                }
            ],
        },
    }


def test_evaluate_schedule_adaptation_reports_tradeoffs_and_muscle_delta() -> None:
    result = evaluate_schedule_adaptation(
        user_profile={"name": "Test"},
        split_preference="full_body",
        program_template=_sample_template(),
        history=[],
        phase="maintenance",
        from_days=5,
        to_days=3,
    )

    assert result["from_days"] == 5
    assert result["to_days"] == 3
    assert result["dropped_sessions"]
    assert any("density" in item.lower() for item in result["tradeoffs"])
    assert isinstance(result["muscle_set_delta"], dict)


def test_recommend_progression_action_recommends_deload_for_low_readiness() -> None:
    decision = recommend_progression_action(
        completion_pct=62,
        adherence_score=2,
        soreness_level="severe",
        average_rpe=9.5,
        consecutive_underperformance_weeks=2,
    )

    assert decision["action"] == "deload"
    assert decision["set_delta"] == -1
    assert decision["load_scale"] < 1.0


def test_recommend_progression_action_holds_underperformance_without_high_fatigue_when_rules_loaded() -> None:
    decision = recommend_progression_action(
        completion_pct=90,
        adherence_score=4,
        soreness_level="mild",
        average_rpe=8.0,
        consecutive_underperformance_weeks=2,
        rule_set=_sample_rule_set(),
    )

    assert decision["action"] == "hold"
    assert decision["reason"] == "under_target_without_high_fatigue"


def test_recommend_phase_transition_respects_intro_phase_protection_from_rules() -> None:
    transition = recommend_phase_transition(
        current_phase="accumulation",
        weeks_in_phase=2,
        readiness_score=50,
        progression_action="hold",
        stagnation_weeks=1,
        rule_set=_sample_rule_set(),
    )

    assert transition["next_phase"] == "accumulation"
    assert transition["reason"] == "intro_phase_protection"


def test_recommend_phase_transition_moves_to_deload_when_stalled() -> None:
    transition = recommend_phase_transition(
        current_phase="intensification",
        weeks_in_phase=3,
        readiness_score=58,
        progression_action="hold",
        stagnation_weeks=2,
    )

    assert transition["next_phase"] == "deload"


def test_derive_readiness_score_penalizes_soreness_and_deload_state() -> None:
    readiness = derive_readiness_score(
        completion_pct=90,
        adherence_score=4,
        soreness_level="moderate",
        progression_action="deload",
    )

    assert readiness == 62
