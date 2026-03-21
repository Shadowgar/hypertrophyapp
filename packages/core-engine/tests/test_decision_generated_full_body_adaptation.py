from __future__ import annotations

from core_engine.decision_generated_full_body_adaptation import (
    GENERATED_FULL_BODY_ADAPTIVE_REVIEW_SOURCE,
    apply_generated_full_body_adaptation_to_plan,
    recommend_generated_full_body_adaptation,
)


_POLICY = {
    "policy_id": "generated_full_body_adaptive_loop_v1",
    "program_scope": ["pure_bodybuilding_phase_1_full_body"],
    "explicit_review_precedence": True,
    "require_generated_constructor_output": True,
    "max_primary_axes_per_week": 1,
    "minimum_axis_persistence_weeks": 2,
    "minimum_prior_generated_weeks": 1,
    "minimum_logged_sessions_for_auto_adjustment": 4,
    "safety_override_allowed": True,
    "load_adjustment_requires_exact_exercise_match": True,
    "minimum_exact_match_exposures_for_load_adjustment": 2,
    "max_volume_targets_per_week": 2,
    "max_load_targets_per_week": 2,
    "volume_increase_set_delta": 1,
    "volume_decrease_set_delta": -1,
    "load_increase_scale": 1.025,
    "load_decrease_scale": 0.95,
    "weak_point_set_delta": 1,
    "weak_point_max_boosted_exercises": 2,
}


def _plan(*, include_weak_point: bool = False, include_optional_fill: bool = False) -> dict:
    exercises = [
        {
            "id": "bench",
            "primary_exercise_id": "bench",
            "slot_role": "primary_compound",
            "sets": 3,
            "recommended_working_weight": 100.0,
            "primary_muscles": ["chest"],
        },
        {
            "id": "row",
            "primary_exercise_id": "row",
            "slot_role": "secondary_compound",
            "sets": 3,
            "recommended_working_weight": 90.0,
            "primary_muscles": ["back"],
        },
    ]
    if include_optional_fill:
        exercises.append(
            {
                "id": "lateral_raise",
                "primary_exercise_id": "lateral_raise",
                "slot_role": "optional_fill",
                "sets": 2,
                "recommended_working_weight": 20.0,
                "primary_muscles": ["shoulders"],
            }
        )
    if include_weak_point:
        exercises.append(
            {
                "id": "leg_curl",
                "primary_exercise_id": "leg_curl",
                "slot_role": "weak_point",
                "sets": 2,
                "recommended_working_weight": 55.0,
                "primary_muscles": ["hamstrings"],
            }
        )
    return {
        "week_start": "2026-03-23",
        "program_template_id": "pure_bodybuilding_phase_1_full_body",
        "sessions": [{"session_id": "pure_bodybuilding_phase_1_full_body-day-1", "exercises": exercises}],
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
    pain_flags: list[str],
    progression_entries: list[dict] | None = None,
) -> dict:
    return {
        "adherence_state": {
            "latest_adherence_score": adherence_score,
            "missed_session_count": 0,
        },
        "readiness_state": {
            "sleep_quality": 3,
            "stress_level": 2,
            "pain_flags": pain_flags,
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
        "progression_state_per_exercise": progression_entries or [],
    }


def _generation_runtime(*, prior_generated_weeks: int = 1, history_days: int = 4, history=None, adaptation_history=None) -> dict:
    if history is None:
        history = [
            {"created_at": "2026-03-01T10:00:00"},
            {"created_at": "2026-03-03T10:00:00"},
            {"created_at": "2026-03-05T10:00:00"},
            {"created_at": "2026-03-07T10:00:00"},
        ][:history_days]
    return {
        "prior_generated_weeks": prior_generated_weeks,
        "history": history,
        "weak_areas": ["hamstrings"],
        "generated_adaptation_history": adaptation_history or {},
    }


def test_recommend_generated_full_body_adaptation_selects_volume_down_under_high_recovery_pressure() -> None:
    decision = recommend_generated_full_body_adaptation(
        plan_payload=_plan(include_weak_point=True, include_optional_fill=True),
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
        generation_runtime=_generation_runtime(history_days=1),
        adaptive_policy=_POLICY,
        review_adjustments_present=False,
    )

    assert decision["status"] == "apply"
    assert decision["decision_trace"]["outcome"]["primary_axis"] == "volume"
    assert decision["decision_trace"]["outcome"]["axis_direction"] == "decrease"
    assert decision["adjustments"]["global"]["set_delta"] == 0
    assert decision["decision_trace"]["outcome"]["selected_target_ids"] == ["lateral_raise", "leg_curl"]
    assert decision["adjustments"]["exercise_overrides"]["lateral_raise"]["set_delta"] == -1
    assert decision["adjustments"]["exercise_overrides"]["leg_curl"]["set_delta"] == -1
    assert decision["adjustments"]["exercise_overrides"]["lateral_raise"]["weight_scale"] == 1.0
    assert decision["adjustments"]["exercise_overrides"]["leg_curl"]["weight_scale"] == 1.0


def test_generated_full_body_adaptation_load_axis_uses_exact_match_only() -> None:
    decision = recommend_generated_full_body_adaptation(
        plan_payload=_plan(),
        selected_template_id="pure_bodybuilding_phase_1_full_body",
        template_selection_trace=_template_trace(),
        training_state=_training_state(
            adherence_score=5,
            stimulus_quality="high",
            fatigue_cost="low",
            recoverability="high",
            progression_eligibility=True,
            deload_pressure="low",
            pain_flags=[],
            progression_entries=[
                {
                    "exercise_id": "bench",
                    "exposure_count": 3,
                    "consecutive_under_target_exposures": 0,
                    "fatigue_score": 0.2,
                }
            ],
        ),
        generation_runtime=_generation_runtime(),
        adaptive_policy=_POLICY,
        review_adjustments_present=False,
    )

    assert decision["status"] == "apply"
    assert decision["decision_trace"]["outcome"]["primary_axis"] == "load"
    assert decision["decision_trace"]["outcome"]["axis_direction"] == "increase"
    assert decision["adjustments"]["global"]["set_delta"] == 0
    assert decision["decision_trace"]["outcome"]["selected_target_ids"] == ["bench"]
    assert decision["adjustments"]["exercise_overrides"] == {
        "bench": {
            "set_delta": 0,
            "weight_scale": 1.025,
            "rationale": "generated_adaptive_load_up_exact_match",
        }
    }
    adjusted = apply_generated_full_body_adaptation_to_plan(plan_payload=_plan(), decision_payload=decision)
    bench = adjusted["sessions"][0]["exercises"][0]
    row = adjusted["sessions"][0]["exercises"][1]
    assert bench["recommended_working_weight"] == 102.5
    assert row["recommended_working_weight"] == 90.0
    assert adjusted["adaptive_review"]["source"] == GENERATED_FULL_BODY_ADAPTIVE_REVIEW_SOURCE
    assert adjusted["adaptive_review"]["decision_trace"]["selected_targets"] == [
        {
            "exercise_id": "bench",
            "slot_role": "primary_compound",
            "selection_reasons": ["exact_match_progression_ready"],
        }
    ]
    held_ids = {item["exercise_id"] for item in adjusted["adaptive_review"]["decision_trace"]["held_targets"]}
    assert "row" in held_ids


def test_generated_full_body_adaptation_persists_prior_axis_for_second_week() -> None:
    decision = recommend_generated_full_body_adaptation(
        plan_payload=_plan(),
        selected_template_id="pure_bodybuilding_phase_1_full_body",
        template_selection_trace=_template_trace(),
        training_state=_training_state(
            adherence_score=4,
            stimulus_quality="moderate",
            fatigue_cost="low",
            recoverability="high",
            progression_eligibility=True,
            deload_pressure="low",
            pain_flags=[],
            progression_entries=[
                {
                    "exercise_id": "bench",
                    "exposure_count": 3,
                    "consecutive_under_target_exposures": 0,
                    "fatigue_score": 0.2,
                }
            ],
        ),
        generation_runtime=_generation_runtime(
            adaptation_history={
                "last_primary_axis": "volume",
                "last_axis_direction": "decrease",
                "last_streak_weeks": 1,
                "last_week_start": "2026-03-16",
                "last_selected_target_ids": ["row"],
            }
        ),
        adaptive_policy=_POLICY,
        review_adjustments_present=False,
    )

    assert decision["status"] == "apply"
    assert decision["decision_trace"]["outcome"]["primary_axis"] == "volume"
    assert decision["decision_trace"]["outcome"]["axis_direction"] == "decrease"
    assert decision["decision_trace"]["outcome"]["persisted_from_prior_week"] is True
    assert decision["decision_trace"]["outcome"]["reversal_applied"] is False
    assert decision["decision_trace"]["outcome"]["selected_target_ids"] == ["row"]


def test_generated_full_body_adaptation_holds_when_persisted_load_axis_has_no_exact_match_targets() -> None:
    decision = recommend_generated_full_body_adaptation(
        plan_payload=_plan(),
        selected_template_id="pure_bodybuilding_phase_1_full_body",
        template_selection_trace=_template_trace(),
        training_state=_training_state(
            adherence_score=4,
            stimulus_quality="low",
            fatigue_cost="low",
            recoverability="high",
            progression_eligibility=True,
            deload_pressure="low",
            pain_flags=[],
            progression_entries=[],
        ),
        generation_runtime=_generation_runtime(
            adaptation_history={
                "last_primary_axis": "load",
                "last_axis_direction": "increase",
                "last_streak_weeks": 1,
                "last_week_start": "2026-03-16",
                "last_selected_target_ids": ["bench"],
            }
        ),
        adaptive_policy=_POLICY,
        review_adjustments_present=False,
    )

    assert decision["status"] == "hold"
    assert decision["decision_trace"]["outcome"]["reason"] == "persisted_targets_not_actionable"
    assert decision["decision_trace"]["outcome"]["primary_axis"] == "load"
    assert decision["decision_trace"]["outcome"]["persisted_from_prior_week"] is True


def test_generated_full_body_adaptation_allows_strong_opposing_signal_reversal() -> None:
    decision = recommend_generated_full_body_adaptation(
        plan_payload=_plan(),
        selected_template_id="pure_bodybuilding_phase_1_full_body",
        template_selection_trace=_template_trace(),
        training_state=_training_state(
            adherence_score=2,
            stimulus_quality="low",
            fatigue_cost="high",
            recoverability="low",
            progression_eligibility=False,
            deload_pressure="high",
            pain_flags=["back"],
        ),
        generation_runtime=_generation_runtime(
            history_days=1,
            adaptation_history={
                "last_primary_axis": "load",
                "last_axis_direction": "increase",
                "last_streak_weeks": 1,
                "last_week_start": "2026-03-16",
            },
        ),
        adaptive_policy=_POLICY,
        review_adjustments_present=False,
    )

    assert decision["status"] == "apply"
    assert decision["decision_trace"]["outcome"]["primary_axis"] == "volume"
    assert decision["decision_trace"]["outcome"]["axis_direction"] == "decrease"
    assert decision["decision_trace"]["outcome"]["reversal_applied"] is True
    assert decision["decision_trace"]["outcome"]["reversal_reason"] == "strong_opposing_signal_reversal"


def test_generated_full_body_adaptation_defers_to_explicit_weekly_review() -> None:
    decision = recommend_generated_full_body_adaptation(
        plan_payload=_plan(include_weak_point=True),
        selected_template_id="pure_bodybuilding_phase_1_full_body",
        template_selection_trace=_template_trace(),
        training_state=_training_state(
            adherence_score=5,
            stimulus_quality="high",
            fatigue_cost="low",
            recoverability="high",
            progression_eligibility=True,
            deload_pressure="low",
            pain_flags=[],
        ),
        generation_runtime=_generation_runtime(),
        adaptive_policy=_POLICY,
        review_adjustments_present=True,
    )

    assert decision["status"] == "suppressed"
    assert decision["decision_trace"]["outcome"]["reason"] == "explicit_review_precedence"


def test_generated_full_body_adaptation_is_deterministic_for_identical_inputs() -> None:
    kwargs = {
        "plan_payload": _plan(include_weak_point=True),
        "selected_template_id": "pure_bodybuilding_phase_1_full_body",
        "template_selection_trace": _template_trace(),
        "training_state": _training_state(
            adherence_score=5,
            stimulus_quality="high",
            fatigue_cost="low",
            recoverability="high",
            progression_eligibility=True,
            deload_pressure="low",
            pain_flags=[],
            progression_entries=[
                {
                    "exercise_id": "bench",
                    "exposure_count": 3,
                    "consecutive_under_target_exposures": 0,
                    "fatigue_score": 0.2,
                }
            ],
        ),
        "generation_runtime": _generation_runtime(),
        "adaptive_policy": _POLICY,
        "review_adjustments_present": False,
    }

    first = recommend_generated_full_body_adaptation(**kwargs)
    second = recommend_generated_full_body_adaptation(**kwargs)

    assert first == second


def test_generated_full_body_adaptation_preserves_exercise_identity_and_trace_shape() -> None:
    plan = _plan(include_weak_point=True, include_optional_fill=True)
    decision = recommend_generated_full_body_adaptation(
        plan_payload=plan,
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
        generation_runtime=_generation_runtime(history_days=1),
        adaptive_policy=_POLICY,
        review_adjustments_present=False,
    )

    before_ids = [exercise["primary_exercise_id"] for exercise in plan["sessions"][0]["exercises"]]
    adjusted = apply_generated_full_body_adaptation_to_plan(plan_payload=plan, decision_payload=decision)
    after_ids = [exercise["primary_exercise_id"] for exercise in adjusted["sessions"][0]["exercises"]]

    assert before_ids == after_ids
    trace = adjusted["adaptive_review"]["decision_trace"]
    assert trace["axis_choice"]["primary_axis"] == "volume"
    assert trace["eligible_targets"]
    assert trace["selected_targets"]
    assert trace["held_targets"]
    assert trace["hold_reasons"]
