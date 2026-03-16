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


# ---------------------------------------------------------------------------
# interpret_workout_set_feedback
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# recommend_live_workout_adjustment — core in-session logic
# ---------------------------------------------------------------------------

def test_recommend_live_significant_undershoot_reduces_load() -> None:
    """6 reps in an 8-12 slot → significant undershoot → reduce."""
    module = _load_module()

    live = module.recommend_live_workout_adjustment(
        planned_reps_min=8,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=1,
        last_reps=5,
        last_weight=100,
        average_reps=5.0,
        rule_set=_sample_rule_set(),
    )

    assert live["guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert live["recommended_weight"] < 100
    assert live["decision_trace"]["interpreter"] == "recommend_live_workout_adjustment"


def test_recommend_live_in_target_holds_weight() -> None:
    """10 reps in an 8-12 slot → in target → hold at exact weight."""
    module = _load_module()

    live = module.recommend_live_workout_adjustment(
        planned_reps_min=8,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=1,
        last_reps=10,
        last_weight=80.0,
        average_reps=10.0,
        rule_set=_sample_rule_set(),
    )

    assert live["recommended_weight"] == 80.0
    assert live["guidance"] == "remaining_sets_hold_load_and_match_target_reps"


def test_recommend_live_at_min_boundary_holds_weight() -> None:
    """Exactly at the minimum (8 reps in 8-12 slot) → hold."""
    module = _load_module()

    live = module.recommend_live_workout_adjustment(
        planned_reps_min=8,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=1,
        last_reps=8,
        last_weight=80.0,
        average_reps=8.0,
        rule_set=_sample_rule_set(),
    )

    assert live["recommended_weight"] >= 80.0
    assert "hold" in live["guidance"] or "match_target" in live["guidance"]


def test_recommend_live_at_max_boundary_holds_weight() -> None:
    """Exactly at the maximum (12 reps in 8-12 slot) → hold."""
    module = _load_module()

    live = module.recommend_live_workout_adjustment(
        planned_reps_min=8,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=1,
        last_reps=12,
        last_weight=80.0,
        average_reps=12.0,
        rule_set=_sample_rule_set(),
    )

    assert live["recommended_weight"] >= 80.0


def test_recommend_live_above_target_increases_weight() -> None:
    """14 reps in an 8-12 slot → clearly above → increase load."""
    module = _load_module()

    live = module.recommend_live_workout_adjustment(
        planned_reps_min=8,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=1,
        last_reps=14,
        last_weight=80.0,
        average_reps=14.0,
        rule_set=_sample_rule_set(),
    )

    assert live["recommended_weight"] > 80.0
    assert live["guidance"] == "remaining_sets_increase_load_keep_reps_controlled"


def test_recommend_live_slightly_above_target_holds() -> None:
    """13 reps in an 8-12 slot (1 above max) → hold, don't over-correct."""
    module = _load_module()

    live = module.recommend_live_workout_adjustment(
        planned_reps_min=8,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=1,
        last_reps=13,
        last_weight=80.0,
        average_reps=13.0,
        rule_set=_sample_rule_set(),
    )

    assert live["recommended_weight"] >= 80.0


def test_recommend_live_minor_undershoot_holds() -> None:
    """7 reps in an 8-12 slot (1 below min) → minor undershoot → hold."""
    module = _load_module()

    live = module.recommend_live_workout_adjustment(
        planned_reps_min=8,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=1,
        last_reps=7,
        last_weight=80.0,
        average_reps=7.0,
        rule_set=_sample_rule_set(),
    )

    assert live["recommended_weight"] >= 80.0
    assert "hold" in live["guidance"] or "match_target" in live["guidance"]


def test_recommend_live_two_below_min_holds() -> None:
    """6 reps in an 8-12 slot (2 below min) → still minor → hold."""
    module = _load_module()

    live = module.recommend_live_workout_adjustment(
        planned_reps_min=8,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=1,
        last_reps=6,
        last_weight=80.0,
        average_reps=6.0,
        rule_set=_sample_rule_set(),
    )

    assert live["recommended_weight"] >= 80.0


def test_recommend_live_session_complete_holds() -> None:
    """All sets done → session complete."""
    module = _load_module()

    live = module.recommend_live_workout_adjustment(
        planned_reps_min=8,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=3,
        last_reps=10,
        last_weight=80.0,
        average_reps=10.0,
        rule_set=_sample_rule_set(),
    )

    assert live["guidance"] == "session_complete_hold_load_for_next_exposure"


# ---------------------------------------------------------------------------
# The user's exact scenario: hammer preacher curls
# 35 lb × 6 (baseline on frontend, not logged to backend)
# Suggested working weight: 30 lb → API receives ~13.6 kg
# Set 1: 30 lb × 10 → should NOT reduce
# Set 2: 30 lb × 12 → should NOT reduce
# ---------------------------------------------------------------------------

def test_user_scenario_30lb_x10_in_10_12_slot_holds() -> None:
    """30 lb = ~13.6 kg via lbsToKg. 10 reps in 10-12 slot → hold at 13.6."""
    module = _load_module()

    live = module.recommend_live_workout_adjustment(
        planned_reps_min=10,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=1,
        last_reps=10,
        last_weight=13.6,
        average_reps=10.0,
        rule_set=_sample_rule_set(),
    )

    assert live["recommended_weight"] == 13.6, (
        f"Expected 13.6 kg (30 lb), got {live['recommended_weight']}"
    )


def test_user_scenario_30lb_x12_in_10_12_slot_holds() -> None:
    """30 lb = ~13.6 kg. 12 reps in 10-12 slot → hold at 13.6."""
    module = _load_module()

    live = module.recommend_live_workout_adjustment(
        planned_reps_min=10,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=2,
        last_reps=12,
        last_weight=13.6,
        average_reps=11.0,
        rule_set=_sample_rule_set(),
    )

    assert live["recommended_weight"] == 13.6


def test_user_scenario_full_session_via_state_update() -> None:
    """Simulate: set1 30lb×10, set2 30lb×12 through resolve_workout_session_state_update."""
    module = _load_module()
    weight_kg = 13.6  # lbsToKg(30)

    # Set 1
    result1 = module.resolve_workout_session_state_update(
        existing_set_history=[],
        primary_exercise_id="hammer_preacher_curl",
        planned_sets=3,
        planned_reps_min=10,
        planned_reps_max=12,
        planned_weight=20.0,
        set_index=1,
        reps=10,
        weight=weight_kg,
    )
    rec1 = result1["live_recommendation"]
    assert rec1["recommended_weight"] == weight_kg, (
        f"After set 1 (10 reps in-range): expected {weight_kg}, got {rec1['recommended_weight']}"
    )

    # Set 2
    result2 = module.resolve_workout_session_state_update(
        existing_set_history=result1["state"]["set_history"],
        primary_exercise_id="hammer_preacher_curl",
        planned_sets=3,
        planned_reps_min=10,
        planned_reps_max=12,
        planned_weight=20.0,
        set_index=2,
        reps=12,
        weight=weight_kg,
    )
    rec2 = result2["live_recommendation"]
    assert rec2["recommended_weight"] == weight_kg, (
        f"After set 2 (12 reps in-range): expected {weight_kg}, got {rec2['recommended_weight']}"
    )


# ---------------------------------------------------------------------------
# Weight preservation across kg ↔ lb boundary
# ---------------------------------------------------------------------------

def test_round_to_microload_preserves_lb_values() -> None:
    """Common lb-to-kg values should survive _round_to_microload."""
    module = _load_module()

    test_cases = [
        (13.6, 13.5),   # 30 lb
        (22.7, 22.5),   # 50 lb
        (45.4, 45.5),   # 100 lb
        (11.3, 11.5),   # 25 lb
        (15.9, 16.0),   # 35 lb
    ]
    for kg_input, expected_nearest in test_cases:
        result = module._round_to_microload(kg_input)
        assert abs(result - kg_input) <= 0.5, (
            f"_round_to_microload({kg_input}) = {result}, expected within 0.5 of input"
        )


def test_hold_preserves_exact_weight() -> None:
    """When scale=1.0 (hold), weight should be returned exactly."""
    module = _load_module()

    for kg in [13.6, 22.7, 45.4, 11.3, 15.9, 100.0]:
        live = module.recommend_live_workout_adjustment(
            planned_reps_min=8,
            planned_reps_max=12,
            planned_sets=3,
            completed_sets=1,
            last_reps=10,
            last_weight=kg,
            average_reps=10.0,
        )
        assert live["recommended_weight"] == kg, (
            f"Hold at {kg} kg: expected {kg}, got {live['recommended_weight']}"
        )


# ---------------------------------------------------------------------------
# hydrate + summarize
# ---------------------------------------------------------------------------

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
