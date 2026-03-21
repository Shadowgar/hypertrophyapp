from __future__ import annotations

from copy import deepcopy

from core_engine.decision_generated_full_body_block_review import recommend_generated_full_body_block_review


_POLICY = {
    "policy_id": "generated_full_body_block_review_v1",
    "program_scope": ["pure_bodybuilding_phase_1_full_body"],
    "explicit_review_precedence": True,
    "require_generated_constructor_output": True,
    "minimum_generated_weeks_for_block_review": 3,
    "minimum_review_window_weeks": 3,
    "stalled_block_underperformance_threshold": 2,
    "fatigued_block_recovery_threshold": 2,
    "continue_block_conservative_restrict_up_axes": ["volume_increase", "load_increase", "weak_point_increase"],
    "recovery_pivot_restricted_axes": ["volume_increase", "load_increase", "weak_point_increase"],
    "block_reset_resets_adaptive_persistence": True,
}


def _plan(*, mesocycle: dict | None = None) -> dict:
    return {
        "week_start": "2026-03-23",
        "program_template_id": "pure_bodybuilding_phase_1_full_body",
        "mesocycle": mesocycle
        or {
            "week_index": 3,
            "trigger_weeks_effective": 5,
            "is_deload_week": False,
        },
        "sessions": [{"session_id": "pure_bodybuilding_phase_1_full_body-day-1", "exercises": []}],
    }


def _template_trace(generated: bool = True) -> dict:
    return {
        "generated_full_body_runtime_trace": {
            "generated_constructor_applied": generated,
            "content_origin": "generated_constructor_applied" if generated else "fallback_to_selected_template",
        }
    }


def _training_state(
    *,
    adherence_score: int,
    stimulus_quality: str,
    fatigue_cost: str,
    recoverability: str,
    progression_eligibility: bool,
    deload_pressure: str,
    pain_flags: list[str] | None = None,
    under_target_muscles: list[str] | None = None,
    stalled_exercise_ids: list[str] | None = None,
    consecutive_underperformance_weeks: int = 0,
) -> dict:
    return {
        "adherence_state": {
            "latest_adherence_score": adherence_score,
            "missed_session_count": 0,
        },
        "readiness_state": {
            "sleep_quality": 3,
            "stress_level": 2,
            "pain_flags": pain_flags or [],
            "recovery_risk_flags": [],
        },
        "stimulus_fatigue_response": {
            "stimulus_quality": stimulus_quality,
            "fatigue_cost": fatigue_cost,
            "recoverability": recoverability,
            "progression_eligibility": progression_eligibility,
            "deload_pressure": deload_pressure,
            "substitution_pressure": "low",
            "signals": {"stimulus": [], "fatigue": [], "recoverability": []},
        },
        "stall_state": {
            "stalled_exercise_ids": stalled_exercise_ids or [],
            "consecutive_underperformance_weeks": consecutive_underperformance_weeks,
        },
        "generation_state": {
            "under_target_muscles": under_target_muscles or [],
            "latest_mesocycle": {
                "week_index": 3,
                "trigger_weeks_effective": 5,
            },
        },
    }


def _generation_runtime(
    *,
    prior_generated_weeks: int = 4,
    recent_entries: list[dict] | None = None,
    recent_hold_count: int = 0,
    recent_down_axis_count: int = 0,
    recent_up_axis_count: int = 0,
    recent_conservative_decision_count: int = 0,
    recent_recovery_pivot_count: int = 0,
    recent_reset_count: int = 0,
    adaptation_history: dict | None = None,
) -> dict:
    entries = recent_entries or [
        {"week_start": "2026-03-16"},
        {"week_start": "2026-03-09"},
        {"week_start": "2026-03-02"},
    ]
    return {
        "prior_generated_weeks": prior_generated_weeks,
        "generated_block_review_history": {
            "recent_entries": entries,
            "recent_entry_count": len(entries),
            "recent_hold_count": recent_hold_count,
            "recent_down_axis_count": recent_down_axis_count,
            "recent_up_axis_count": recent_up_axis_count,
            "recent_conservative_decision_count": recent_conservative_decision_count,
            "recent_recovery_pivot_count": recent_recovery_pivot_count,
            "recent_reset_count": recent_reset_count,
            "last_block_classification": "productive",
            "last_block_decision": "continue_block",
            "last_week_start": entries[0]["week_start"] if entries else None,
        },
        "generated_adaptation_history": adaptation_history
        or {
            "recent_entries": [],
            "last_primary_axis": None,
            "last_axis_direction": None,
            "last_streak_weeks": 0,
        },
    }


def test_generated_full_body_block_review_continues_productive_block_without_restriction() -> None:
    decision = recommend_generated_full_body_block_review(
        plan_payload=_plan(),
        selected_template_id="pure_bodybuilding_phase_1_full_body",
        template_selection_trace=_template_trace(),
        training_state=_training_state(
            adherence_score=4,
            stimulus_quality="high",
            fatigue_cost="low",
            recoverability="high",
            progression_eligibility=True,
            deload_pressure="low",
        ),
        generation_runtime=_generation_runtime(recent_up_axis_count=1),
        block_review_policy=_POLICY,
        review_adjustments_present=False,
    )

    assert decision["status"] == "apply"
    assert decision["decision_trace"]["outcome"]["block_classification"] == "productive"
    assert decision["decision_trace"]["outcome"]["block_decision"] == "continue_block"
    assert decision["adaptive_gate"]["restricted_axis_tokens"] == []
    assert decision["adaptive_gate"]["reset_adaptive_persistence_context"] is False


def test_generated_full_body_block_review_uses_recovery_pivot_for_fatigued_trend() -> None:
    decision = recommend_generated_full_body_block_review(
        plan_payload=_plan(mesocycle={"week_index": 5, "trigger_weeks_effective": 5, "is_deload_week": True}),
        selected_template_id="pure_bodybuilding_phase_1_full_body",
        template_selection_trace=_template_trace(),
        training_state=_training_state(
            adherence_score=2,
            stimulus_quality="low",
            fatigue_cost="high",
            recoverability="low",
            progression_eligibility=False,
            deload_pressure="high",
            pain_flags=["shoulder"],
        ),
        generation_runtime=_generation_runtime(recent_down_axis_count=2, recent_recovery_pivot_count=1),
        block_review_policy=_POLICY,
        review_adjustments_present=False,
    )

    assert decision["status"] == "apply"
    assert decision["decision_trace"]["outcome"]["block_classification"] == "fatigued"
    assert decision["decision_trace"]["outcome"]["block_decision"] == "recovery_pivot_next_week"
    assert set(decision["adaptive_gate"]["restricted_axis_tokens"]) == {
        "volume_increase",
        "load_increase",
        "weak_point_increase",
    }
    assert decision["adaptive_gate"]["reset_adaptive_persistence_context"] is False


def test_generated_full_body_block_review_resets_stalled_block_without_assigning_axis() -> None:
    decision = recommend_generated_full_body_block_review(
        plan_payload=_plan(),
        selected_template_id="pure_bodybuilding_phase_1_full_body",
        template_selection_trace=_template_trace(),
        training_state=_training_state(
            adherence_score=4,
            stimulus_quality="moderate",
            fatigue_cost="low",
            recoverability="high",
            progression_eligibility=False,
            deload_pressure="low",
            under_target_muscles=["hamstrings"],
            stalled_exercise_ids=["bench"],
            consecutive_underperformance_weeks=2,
        ),
        generation_runtime=_generation_runtime(recent_hold_count=2),
        block_review_policy=_POLICY,
        review_adjustments_present=False,
    )

    assert decision["status"] == "apply"
    assert decision["decision_trace"]["outcome"]["block_classification"] == "stalled"
    assert decision["decision_trace"]["outcome"]["block_decision"] == "block_reset_next_week"
    assert decision["adaptive_gate"]["restricted_axis_tokens"] == []
    assert decision["adaptive_gate"]["reset_adaptive_persistence_context"] is True


def test_generated_full_body_block_review_uses_conservative_gate_for_cautionary_productive_trend() -> None:
    decision = recommend_generated_full_body_block_review(
        plan_payload=_plan(mesocycle={"week_index": 4, "trigger_weeks_effective": 5, "is_deload_week": False}),
        selected_template_id="pure_bodybuilding_phase_1_full_body",
        template_selection_trace=_template_trace(),
        training_state=_training_state(
            adherence_score=3,
            stimulus_quality="moderate",
            fatigue_cost="moderate",
            recoverability="moderate",
            progression_eligibility=True,
            deload_pressure="moderate",
        ),
        generation_runtime=_generation_runtime(recent_conservative_decision_count=1),
        block_review_policy=_POLICY,
        review_adjustments_present=False,
    )

    assert decision["status"] == "apply"
    assert decision["decision_trace"]["outcome"]["block_classification"] == "productive"
    assert decision["decision_trace"]["outcome"]["block_decision"] == "continue_block_conservative"
    assert set(decision["adaptive_gate"]["restricted_axis_tokens"]) == {
        "volume_increase",
        "load_increase",
        "weak_point_increase",
    }


def test_generated_full_body_block_review_holds_when_review_window_is_insufficient() -> None:
    decision = recommend_generated_full_body_block_review(
        plan_payload=_plan(),
        selected_template_id="pure_bodybuilding_phase_1_full_body",
        template_selection_trace=_template_trace(),
        training_state=_training_state(
            adherence_score=4,
            stimulus_quality="high",
            fatigue_cost="low",
            recoverability="high",
            progression_eligibility=True,
            deload_pressure="low",
        ),
        generation_runtime=_generation_runtime(prior_generated_weeks=2, recent_entries=[{"week_start": "2026-03-16"}]),
        block_review_policy=_POLICY,
        review_adjustments_present=False,
    )

    assert decision["status"] == "hold"
    assert decision["adaptive_gate"] is None
    assert decision["decision_trace"]["outcome"]["reason"] == "insufficient_review_window"


def test_generated_full_body_block_review_defers_to_explicit_review_precedence() -> None:
    decision = recommend_generated_full_body_block_review(
        plan_payload=_plan(),
        selected_template_id="pure_bodybuilding_phase_1_full_body",
        template_selection_trace=_template_trace(),
        training_state=_training_state(
            adherence_score=4,
            stimulus_quality="high",
            fatigue_cost="low",
            recoverability="high",
            progression_eligibility=True,
            deload_pressure="low",
        ),
        generation_runtime=_generation_runtime(),
        block_review_policy=_POLICY,
        review_adjustments_present=True,
    )

    assert decision["status"] == "suppressed"
    assert decision["decision_trace"]["outcome"]["reason"] == "explicit_review_precedence"


def test_generated_full_body_block_review_is_deterministic_for_identical_inputs() -> None:
    kwargs = {
        "plan_payload": _plan(),
        "selected_template_id": "pure_bodybuilding_phase_1_full_body",
        "template_selection_trace": _template_trace(),
        "training_state": _training_state(
            adherence_score=4,
            stimulus_quality="moderate",
            fatigue_cost="moderate",
            recoverability="moderate",
            progression_eligibility=True,
            deload_pressure="moderate",
        ),
        "generation_runtime": _generation_runtime(recent_conservative_decision_count=1),
        "block_review_policy": _POLICY,
        "review_adjustments_present": False,
    }

    first = recommend_generated_full_body_block_review(**deepcopy(kwargs))
    second = recommend_generated_full_body_block_review(**deepcopy(kwargs))

    assert first == second
