from __future__ import annotations

from copy import deepcopy
from typing import Any


_PRODUCTIVE = "productive"
_FATIGUED = "fatigued"
_STALLED = "stalled"
_GENERATED_FULL_BODY_SCOPE_IDS = {"full_body_v1", "adaptive_full_body_gold_v0_1"}
_GENERATED_FULL_BODY_POLICY_CANONICAL_ID = "pure_bodybuilding_phase_1_full_body"


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _supports_generated_constructor(template_selection_trace: dict[str, Any]) -> bool:
    generated_runtime_trace = _coerce_dict(template_selection_trace.get("generated_full_body_runtime_trace"))
    return bool(generated_runtime_trace.get("generated_constructor_applied"))


def _selected_template_in_generated_scope(*, selected_template_id: str, program_scope: list[str]) -> bool:
    normalized_scope = {str(item).strip() for item in program_scope if str(item).strip()}
    if selected_template_id in normalized_scope:
        return True
    return selected_template_id in _GENERATED_FULL_BODY_SCOPE_IDS and _GENERATED_FULL_BODY_POLICY_CANONICAL_ID in normalized_scope


def _build_adaptive_gate(
    *,
    block_decision: str,
    normalized_policy: dict[str, Any],
) -> dict[str, Any]:
    if block_decision == "continue_block":
        restricted_axis_tokens: list[str] = []
        reset_persistence = False
    elif block_decision == "continue_block_conservative":
        restricted_axis_tokens = _coerce_string_list(
            normalized_policy.get("continue_block_conservative_restrict_up_axes")
        )
        reset_persistence = False
    elif block_decision == "recovery_pivot_next_week":
        restricted_axis_tokens = _coerce_string_list(normalized_policy.get("recovery_pivot_restricted_axes"))
        reset_persistence = False
    elif block_decision == "block_reset_next_week":
        restricted_axis_tokens = []
        reset_persistence = bool(normalized_policy.get("block_reset_resets_adaptive_persistence", True))
    else:
        raise ValueError(f"Unsupported block decision: {block_decision}")

    return {
        "allowed_axis_tokens": [],
        "restricted_axis_tokens": restricted_axis_tokens,
        "reset_adaptive_persistence_context": reset_persistence,
    }


def recommend_generated_full_body_block_review(
    *,
    plan_payload: dict[str, Any],
    selected_template_id: str,
    template_selection_trace: dict[str, Any],
    training_state: dict[str, Any] | None,
    generation_runtime: dict[str, Any] | None,
    block_review_policy: dict[str, Any] | None,
    review_adjustments_present: bool,
) -> dict[str, Any]:
    normalized_policy = _coerce_dict(block_review_policy)
    normalized_training_state = _coerce_dict(training_state)
    normalized_generation_runtime = _coerce_dict(generation_runtime)
    adherence_state = _coerce_dict(normalized_training_state.get("adherence_state"))
    readiness_state = _coerce_dict(normalized_training_state.get("readiness_state"))
    generation_state = _coerce_dict(normalized_training_state.get("generation_state"))
    stall_state = _coerce_dict(normalized_training_state.get("stall_state"))
    stimulus_fatigue_response = _coerce_dict(normalized_training_state.get("stimulus_fatigue_response"))
    block_history = _coerce_dict(normalized_generation_runtime.get("generated_block_review_history"))
    adaptation_history = _coerce_dict(normalized_generation_runtime.get("generated_adaptation_history"))
    current_mesocycle = _coerce_dict(plan_payload.get("mesocycle"))
    latest_mesocycle = _coerce_dict(generation_state.get("latest_mesocycle"))

    decision_trace: dict[str, Any] = {
        "interpreter": "recommend_generated_full_body_block_review",
        "version": "v1",
        "inputs": {
            "selected_template_id": selected_template_id,
            "review_adjustments_present": bool(review_adjustments_present),
            "has_policy": bool(normalized_policy),
            "generated_constructor_applied": _supports_generated_constructor(template_selection_trace),
            "prior_generated_weeks": int(normalized_generation_runtime.get("prior_generated_weeks") or 0),
            "recent_block_entry_count": int(block_history.get("recent_entry_count") or 0),
        },
        "steps": [],
        "trend_summary": {},
        "interaction_with_weekly_loop": {},
        "outcome": {},
    }

    if not normalized_policy:
        decision_trace["outcome"] = {"status": "suppressed", "reason": "block_review_policy_missing"}
        return {"status": "suppressed", "adaptive_gate": None, "decision_trace": decision_trace}

    if review_adjustments_present and bool(normalized_policy.get("explicit_review_precedence", True)):
        decision_trace["outcome"] = {"status": "suppressed", "reason": "explicit_review_precedence"}
        return {"status": "suppressed", "adaptive_gate": None, "decision_trace": decision_trace}

    if not _supports_generated_constructor(template_selection_trace) and bool(
        normalized_policy.get("require_generated_constructor_output", True)
    ):
        decision_trace["outcome"] = {"status": "suppressed", "reason": "generated_constructor_not_applied"}
        return {"status": "suppressed", "adaptive_gate": None, "decision_trace": decision_trace}

    if not _selected_template_in_generated_scope(
        selected_template_id=selected_template_id,
        program_scope=_coerce_string_list(normalized_policy.get("program_scope")),
    ):
        decision_trace["outcome"] = {"status": "suppressed", "reason": "selected_template_out_of_scope"}
        return {"status": "suppressed", "adaptive_gate": None, "decision_trace": decision_trace}

    prior_generated_weeks = int(normalized_generation_runtime.get("prior_generated_weeks") or 0)
    minimum_generated_weeks = int(normalized_policy.get("minimum_generated_weeks_for_block_review") or 0)
    recent_entry_count = int(block_history.get("recent_entry_count") or 0)
    minimum_review_window_weeks = int(normalized_policy.get("minimum_review_window_weeks") or 1)
    if prior_generated_weeks < minimum_generated_weeks or recent_entry_count < minimum_review_window_weeks:
        decision_trace["outcome"] = {
            "status": "hold",
            "reason": "insufficient_review_window",
            "prior_generated_weeks": prior_generated_weeks,
            "minimum_generated_weeks_for_block_review": minimum_generated_weeks,
            "recent_entry_count": recent_entry_count,
            "minimum_review_window_weeks": minimum_review_window_weeks,
        }
        return {"status": "hold", "adaptive_gate": None, "decision_trace": decision_trace}

    latest_adherence_score = adherence_state.get("latest_adherence_score")
    if latest_adherence_score is not None:
        latest_adherence_score = int(latest_adherence_score)
    pain_flags = _coerce_string_list(readiness_state.get("pain_flags"))
    recovery_risk_flags = _coerce_string_list(readiness_state.get("recovery_risk_flags"))
    recoverability = str(stimulus_fatigue_response.get("recoverability") or "").strip().lower()
    fatigue_cost = str(stimulus_fatigue_response.get("fatigue_cost") or "").strip().lower()
    deload_pressure = str(stimulus_fatigue_response.get("deload_pressure") or "").strip().lower()
    progression_eligibility = bool(stimulus_fatigue_response.get("progression_eligibility"))
    under_target_muscles = _coerce_string_list(generation_state.get("under_target_muscles"))
    stalled_exercise_ids = _coerce_string_list(stall_state.get("stalled_exercise_ids"))
    consecutive_underperformance_weeks = int(stall_state.get("consecutive_underperformance_weeks") or 0)
    recent_hold_count = int(block_history.get("recent_hold_count") or 0)
    recent_down_axis_count = int(block_history.get("recent_down_axis_count") or 0)
    recent_conservative_decision_count = int(block_history.get("recent_conservative_decision_count") or 0)
    recent_recovery_pivot_count = int(block_history.get("recent_recovery_pivot_count") or 0)
    current_week_index = (
        int(current_mesocycle.get("week_index"))
        if isinstance(current_mesocycle.get("week_index"), int | float) or str(current_mesocycle.get("week_index") or "").isdigit()
        else (
            int(latest_mesocycle.get("week_index"))
            if isinstance(latest_mesocycle.get("week_index"), int | float)
            or str(latest_mesocycle.get("week_index") or "").isdigit()
            else None
        )
    )
    trigger_weeks_effective = (
        int(current_mesocycle.get("trigger_weeks_effective"))
        if isinstance(current_mesocycle.get("trigger_weeks_effective"), int | float)
        or str(current_mesocycle.get("trigger_weeks_effective") or "").isdigit()
        else (
            int(latest_mesocycle.get("trigger_weeks_effective"))
            if isinstance(latest_mesocycle.get("trigger_weeks_effective"), int | float)
            or str(latest_mesocycle.get("trigger_weeks_effective") or "").isdigit()
            else None
        )
    )

    fatigued_score = sum(
        1
        for condition in (
            deload_pressure == "high",
            recoverability == "low",
            fatigue_cost == "high",
            bool(pain_flags),
            bool(recovery_risk_flags),
            latest_adherence_score is not None and latest_adherence_score <= 2,
            bool(current_mesocycle.get("is_deload_week")),
            recent_down_axis_count >= int(normalized_policy.get("fatigued_block_recovery_threshold") or 1),
            recent_recovery_pivot_count >= 1,
        )
        if condition
    )
    stall_score = sum(
        1
        for condition in (
            consecutive_underperformance_weeks >= int(normalized_policy.get("stalled_block_underperformance_threshold") or 1),
            bool(stalled_exercise_ids),
            bool(under_target_muscles),
            recent_hold_count >= int(normalized_policy.get("stalled_block_underperformance_threshold") or 1),
            not progression_eligibility,
        )
        if condition
    )
    conservative_pressure = sum(
        1
        for condition in (
            recoverability == "moderate",
            fatigue_cost == "moderate",
            deload_pressure == "moderate",
            latest_adherence_score is not None and latest_adherence_score == 3,
            recent_down_axis_count >= 1,
            recent_conservative_decision_count >= 1,
            current_week_index is not None
            and trigger_weeks_effective is not None
            and current_week_index >= max(1, trigger_weeks_effective - 1),
        )
        if condition
    )

    trend_summary = {
        "prior_generated_weeks": prior_generated_weeks,
        "review_window_weeks": recent_entry_count,
        "mesocycle_week_index": current_week_index,
        "trigger_weeks_effective": trigger_weeks_effective,
        "stimulus_fatigue_response": {
            "recoverability": recoverability,
            "fatigue_cost": fatigue_cost,
            "deload_pressure": deload_pressure,
            "progression_eligibility": progression_eligibility,
        },
        "adherence": {
            "latest_adherence_score": latest_adherence_score,
            "missed_session_count": int(adherence_state.get("missed_session_count") or 0),
        },
        "readiness": {
            "pain_flags": pain_flags,
            "recovery_risk_flags": recovery_risk_flags,
            "sleep_quality": readiness_state.get("sleep_quality"),
            "stress_level": readiness_state.get("stress_level"),
        },
        "stall": {
            "stalled_exercise_ids": stalled_exercise_ids,
            "consecutive_underperformance_weeks": consecutive_underperformance_weeks,
        },
        "under_target_muscles": list(under_target_muscles),
        "recent_adaptive_history": {
            "recent_entries": deepcopy(adaptation_history.get("recent_entries") or []),
            "last_primary_axis": adaptation_history.get("last_primary_axis"),
            "last_axis_direction": adaptation_history.get("last_axis_direction"),
            "last_streak_weeks": int(adaptation_history.get("last_streak_weeks") or 0),
            "recent_hold_count": recent_hold_count,
            "recent_down_axis_count": recent_down_axis_count,
            "recent_up_axis_count": int(block_history.get("recent_up_axis_count") or 0),
        },
        "recent_block_history": {
            "recent_entries": deepcopy(block_history.get("recent_entries") or []),
            "recent_conservative_decision_count": recent_conservative_decision_count,
            "recent_recovery_pivot_count": recent_recovery_pivot_count,
            "recent_reset_count": int(block_history.get("recent_reset_count") or 0),
            "last_block_classification": block_history.get("last_block_classification"),
            "last_block_decision": block_history.get("last_block_decision"),
        },
        "scores": {
            "fatigued_score": fatigued_score,
            "stall_score": stall_score,
            "conservative_pressure": conservative_pressure,
        },
    }
    decision_trace["trend_summary"] = deepcopy(trend_summary)
    decision_trace["steps"].append({"decision": "trend_summary", "result": deepcopy(trend_summary)})

    if fatigued_score >= int(normalized_policy.get("fatigued_block_recovery_threshold") or 1):
        block_classification = _FATIGUED
        block_decision = "recovery_pivot_next_week"
    elif stall_score >= int(normalized_policy.get("stalled_block_underperformance_threshold") or 1):
        block_classification = _STALLED
        block_decision = "block_reset_next_week"
    elif conservative_pressure > 0:
        block_classification = _PRODUCTIVE
        block_decision = "continue_block_conservative"
    else:
        block_classification = _PRODUCTIVE
        block_decision = "continue_block"

    adaptive_gate = _build_adaptive_gate(block_decision=block_decision, normalized_policy=normalized_policy)
    decision_trace["steps"].append(
        {
            "decision": "block_classification",
            "result": {
                "block_classification": block_classification,
                "block_decision": block_decision,
                "adaptive_gate": deepcopy(adaptive_gate),
            },
        }
    )
    decision_trace["outcome"] = {
        "status": "apply",
        "block_classification": block_classification,
        "block_decision": block_decision,
        "adaptive_gate": deepcopy(adaptive_gate),
    }
    return {
        "status": "apply",
        "adaptive_gate": adaptive_gate,
        "decision_trace": decision_trace,
    }
