import importlib
import importlib.util


MODULE_NAME = "core_engine.decision_live_workout_guidance"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None, "decision_live_workout_guidance module should exist"
    return importlib.import_module(MODULE_NAME)


def _sample_rule_set() -> dict:
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


def test_interpret_workout_set_feedback_owner_module_returns_trace_and_rationale() -> None:
    module = _load_module()

    decision = module.interpret_workout_set_feedback(
        reps=6,
        weight=100,
        planned_reps_min=8,
        planned_reps_max=12,
        planned_weight=100,
        next_working_weight=100,
        rule_set=_sample_rule_set(),
    )

    assert decision["guidance"] == "below_target_reps_reduce_or_hold_load"
    assert decision["guidance_rationale"].startswith("Performance fell below the target range.")
    assert decision["decision_trace"]["interpreter"] == "interpret_workout_set_feedback"


def test_recommend_live_workout_adjustment_owner_module_returns_trace() -> None:
    module = _load_module()

    live = module.recommend_live_workout_adjustment(
        planned_reps_min=8,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=1,
        last_reps=6,
        last_weight=100,
        average_reps=6.0,
        rule_set=_sample_rule_set(),
    )

    assert live["guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert live["decision_trace"]["interpreter"] == "recommend_live_workout_adjustment"


def test_hydrate_live_workout_recommendation_owner_module_keeps_substitution_trace() -> None:
    module = _load_module()

    hydrated = module.hydrate_live_workout_recommendation(
        completed_sets=1,
        remaining_sets=2,
        recommended_reps_min=8,
        recommended_reps_max=10,
        recommended_weight=97.5,
        guidance="remaining_sets_reduce_load_focus_target_reps",
        substitution_recommendation={
            "recommended_name": "Chest Supported Row",
            "compatible_substitutions": ["Chest Supported Row", "1-Arm Cable Row"],
            "failed_exposure_count": 3,
            "trigger_threshold": 3,
            "reason": "repeat_failure_threshold_reached",
            "decision_trace": {"interpreter": "resolve_repeat_failure_substitution"},
        },
        rule_set=_sample_rule_set(),
    )

    assert hydrated["decision_trace"]["interpreter"] == "hydrate_live_workout_recommendation"
    assert hydrated["guidance_rationale"].startswith("Reps dropped below target.")
    assert hydrated["substitution_recommendation"]["recommended_name"] == "Chest Supported Row"


def test_summarize_workout_session_guidance_owner_module_returns_structured_trace() -> None:
    module = _load_module()

    summary = module.summarize_workout_session_guidance(
        workout_id="workout_a",
        completed_total=3,
        planned_total=3,
        exercise_summaries=[
            {
                "exercise_id": "bench",
                "guidance": "below_target_reps_reduce_or_hold_load",
            }
        ],
        rule_set=_sample_rule_set(),
    )

    assert summary["decision_trace"]["interpreter"] == "summarize_workout_session_guidance"
    assert summary["overall_guidance"] == "performance_below_target_adjust_load_and_recover"
