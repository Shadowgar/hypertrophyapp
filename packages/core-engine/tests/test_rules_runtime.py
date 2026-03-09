import pytest

from core_engine.rules_runtime import (
    evaluate_deload_signal,
    extract_fatigue_rpe_threshold,
    extract_intro_weeks,
    resolve_equipment_substitution,
    resolve_repeat_failure_substitution,
    resolve_adaptive_rule_runtime,
    resolve_progression_rule_runtime,
    resolve_starting_load,
    resolve_substitution_rule_runtime,
)


def test_resolve_progression_rule_runtime_uses_rule_overrides() -> None:
    runtime = resolve_progression_rule_runtime(
        {
            "progression_rules": {
                "on_success": {"percent": 5},
                "on_under_target": {"reduce_percent": 3, "after_exposures": 2},
            }
        }
    )

    assert runtime == {
        "increase_percent": 5.0,
        "reduce_percent": 3.0,
        "reduce_after_exposures": 2,
    }


def test_resolve_starting_load_uses_estimated_1rm_fallback_when_available() -> None:
    runtime = resolve_starting_load(
        planned_exercise={"estimated_1rm": 155.0},
        fallback_weight=90.0,
        rule_set={
            "starting_load_rules": {
                "method": "rep_range_rir_start",
                "default_rir_target": 2,
                "fallback_percent_estimated_1rm": 72,
            }
        },
    )

    assert runtime["working_weight"] == pytest.approx(112.5)
    assert runtime["decision_trace"]["interpreter"] == "resolve_starting_load"
    assert runtime["decision_trace"]["outcome"] == {
        "working_weight": 112.5,
        "source": "estimated_1rm_fallback_percent",
    }


def test_resolve_starting_load_falls_back_to_planned_weight_without_estimated_1rm() -> None:
    runtime = resolve_starting_load(
        planned_exercise={"recommended_working_weight": 95.0},
        fallback_weight=95.0,
        rule_set={
            "starting_load_rules": {
                "method": "rep_range_rir_start",
                "default_rir_target": 2,
                "fallback_percent_estimated_1rm": 72,
            }
        },
    )

    assert runtime["working_weight"] == pytest.approx(95.0)
    assert runtime["decision_trace"]["outcome"] == {
        "working_weight": 95.0,
        "source": "planned_weight",
    }


def test_resolve_adaptive_rule_runtime_extracts_fatigue_and_deload_config() -> None:
    runtime = resolve_adaptive_rule_runtime(
        {
            "progression_rules": {
                "on_success": {"percent": 5},
                "on_under_target": {"reduce_percent": 3, "after_exposures": 2},
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
                "increase_load": "increase",
                "hold_load": "hold",
                "deload": "deload",
            },
        }
    )

    assert runtime["fatigue_rpe_threshold"] == pytest.approx(9.0)
    assert runtime["intro_weeks"] == 2
    assert runtime["scheduled_deload_weeks"] == 6
    assert runtime["early_deload_trigger"] == "repeated_under_target_plus_high_fatigue"
    assert runtime["deload_load_scale"] == pytest.approx(0.9)


def test_extract_rule_threshold_helpers_parse_conditions() -> None:
    rule_set = {
        "fatigue_rules": {
            "high_fatigue_trigger": {
                "conditions": [
                    "intro phase lasts 3 weeks; avoid interpreting early underperformance as stall",
                    "session_rpe_avg >= 8.5 for two exposures",
                ]
            }
        }
    }

    assert extract_intro_weeks(rule_set) == 3
    assert extract_fatigue_rpe_threshold(rule_set) == pytest.approx(8.5)


def test_evaluate_deload_signal_matches_rule_based_underperformance_and_high_fatigue() -> None:
    signal = evaluate_deload_signal(
        completion_pct=92,
        adherence_score=4,
        soreness_rank=2,
        average_rpe=9.1,
        consecutive_underperformance_weeks=2,
        rule_set={
            "progression_rules": {
                "on_under_target": {"after_exposures": 2},
            },
            "fatigue_rules": {
                "high_fatigue_trigger": {
                    "conditions": ["session_rpe_avg >= 9 for two exposures"]
                }
            },
            "deload_rules": {
                "early_deload_trigger": "repeated_under_target_plus_high_fatigue"
            },
        },
    )

    assert signal["high_fatigue"] is True
    assert signal["underperformance_deload_matched"] is True
    assert signal["forced_deload_reasons"] == []


def test_evaluate_deload_signal_collects_forced_deload_reasons() -> None:
    signal = evaluate_deload_signal(
        completion_pct=65,
        adherence_score=2,
        soreness_rank=3,
        rule_set=None,
    )

    assert signal["forced_deload_reasons"] == ["low_completion", "low_adherence", "high_soreness"]


def test_resolve_substitution_rule_runtime_extracts_repeat_failure_threshold() -> None:
    runtime = resolve_substitution_rule_runtime(
        {
            "substitution_rules": {
                "equipment_mismatch": "use_first_compatible_substitution",
                "repeat_failure_trigger": "switch_after_three_failed_exposures",
            }
        }
    )

    assert runtime["equipment_mismatch_strategy"] == "use_first_compatible_substitution"
    assert runtime["repeat_failure_threshold"] == 3


def test_resolve_equipment_substitution_chooses_first_compatible_candidate() -> None:
    result = resolve_equipment_substitution(
        exercise_id="barbell_row",
        exercise_name="Barbell Row",
        exercise_equipment_tags=["barbell"],
        substitution_candidates=["Cable Row", "DB Row"],
        equipment_set={"dumbbell"},
        rule_set={
            "substitution_rules": {
                "equipment_mismatch": "use_first_compatible_substitution",
                "repeat_failure_trigger": "switch_after_three_failed_exposures",
            }
        },
    )

    assert result["compatible_substitutions"] == ["DB Row"]
    assert result["selected_name"] == "DB Row"
    assert result["auto_substituted"] is True
    assert result["decision_trace"]["interpreter"] == "resolve_equipment_substitution"


def test_resolve_repeat_failure_substitution_recommends_compatible_alternative_after_threshold() -> None:
    result = resolve_repeat_failure_substitution(
        exercise_id="lat_cable_row",
        exercise_name="Lat-Focused Cable Row",
        substitution_candidates=["Chest Supported Row", "1-Arm Cable Row"],
        consecutive_under_target_exposures=3,
        equipment_set={"cable", "dumbbell", "machine"},
        rule_set={
            "substitution_rules": {
                "equipment_mismatch": "use_first_compatible_substitution",
                "repeat_failure_trigger": "switch_after_three_failed_exposures",
            }
        },
    )

    assert result["recommend_substitution"] is True
    assert result["recommended_name"] == "Chest Supported Row"
    assert result["decision_trace"]["interpreter"] == "resolve_repeat_failure_substitution"