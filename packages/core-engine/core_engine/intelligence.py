from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
import re
from typing import Any, Literal, cast

from .decision_frequency_adaptation import (
    apply_active_frequency_adaptation_runtime as _apply_active_frequency_adaptation_runtime,
    build_frequency_adaptation_apply_payload as _build_frequency_adaptation_apply_payload,
    build_frequency_adaptation_persistence_state as _build_frequency_adaptation_persistence_state,
    build_generated_week_adaptation_persistence_payload as _build_generated_week_adaptation_persistence_payload,
    interpret_frequency_adaptation_apply as _interpret_frequency_adaptation_apply,
    prepare_frequency_adaptation_route_runtime as _prepare_frequency_adaptation_route_runtime,
    recommend_frequency_adaptation_preview as _recommend_frequency_adaptation_preview,
    resolve_active_frequency_adaptation_runtime as _resolve_active_frequency_adaptation_runtime,
)
from .decision_coach_preview import (
    build_applied_coaching_recommendation_record_values as _build_applied_coaching_recommendation_record_values,
    build_applied_coaching_recommendation_response as _build_applied_coaching_recommendation_response,
    finalize_applied_coaching_recommendation_commit_runtime as _finalize_applied_coaching_recommendation_commit_runtime,
    prepare_coaching_apply_route_finalize_runtime as _prepare_coaching_apply_route_finalize_runtime,
    build_coaching_recommendation_timeline_entry as _build_coaching_recommendation_timeline_entry,
    build_coaching_recommendation_timeline_payload as _build_coaching_recommendation_timeline_payload,
    build_phase_applied_recommendation_record as _build_phase_applied_recommendation_record,
    build_coach_preview_payloads as _build_coach_preview_payloads,
    build_coach_preview_recommendation_record_fields as _build_coach_preview_recommendation_record_fields,
    finalize_coach_preview_commit_runtime as _finalize_coach_preview_commit_runtime,
    build_specialization_applied_recommendation_record as _build_specialization_applied_recommendation_record,
    extract_coaching_recommendation_focus_muscles as _extract_coaching_recommendation_focus_muscles,
    finalize_applied_coaching_recommendation as _finalize_applied_coaching_recommendation,
    interpret_coach_phase_apply_decision as _interpret_coach_phase_apply_decision,
    interpret_coach_specialization_apply_decision as _interpret_coach_specialization_apply_decision,
    normalize_coaching_recommendation_timeline_limit as _normalize_coaching_recommendation_timeline_limit,
    prepare_coaching_apply_runtime_source as _prepare_coaching_apply_runtime_source,
    prepare_applied_coaching_recommendation_commit_runtime as _prepare_applied_coaching_recommendation_commit_runtime,
    prepare_coach_preview_commit_runtime as _prepare_coach_preview_commit_runtime,
    prepare_coaching_apply_commit_runtime as _prepare_coaching_apply_commit_runtime,
    prepare_coaching_apply_decision_runtime as _prepare_coaching_apply_decision_runtime,
    prepare_coaching_apply_route_runtime as _prepare_coaching_apply_route_runtime,
    prepare_phase_apply_runtime as _prepare_phase_apply_runtime,
    prepare_specialization_apply_runtime as _prepare_specialization_apply_runtime,
    recommend_coach_intelligence_preview as _recommend_coach_intelligence_preview,
)
from .decision_program_recommendation import (
    build_program_recommendation_payload as _build_program_recommendation_payload,
    build_program_switch_payload as _build_program_switch_payload,
    humanize_program_reason as _humanize_program_reason,
    prepare_profile_program_recommendation_inputs as _prepare_profile_program_recommendation_inputs,
    prepare_profile_program_recommendation_route_runtime as _prepare_profile_program_recommendation_route_runtime,
    prepare_program_recommendation_runtime as _prepare_program_recommendation_runtime,
    prepare_program_switch_runtime as _prepare_program_switch_runtime,
    recommend_program_selection as _recommend_program_selection,
    resolve_program_recommendation_candidates as _resolve_program_recommendation_candidates,
)
from .decision_progression import (
    derive_readiness_score as _derive_readiness_score,
    evaluate_schedule_adaptation as _evaluate_schedule_adaptation,
    humanize_phase_transition_reason as _humanize_phase_transition_reason,
    humanize_progression_reason as _humanize_progression_reason,
    recommend_phase_transition as _recommend_phase_transition,
    recommend_progression_action as _recommend_progression_action,
)
from .decision_weekly_review import (
    apply_weekly_review_adjustments_to_plan as _apply_weekly_review_adjustments_to_plan,
    build_weekly_review_performance_summary as _build_weekly_review_performance_summary,
    build_weekly_review_decision_payload as _build_weekly_review_decision_payload,
    build_weekly_review_cycle_persistence_payload as _build_weekly_review_cycle_persistence_payload,
    build_weekly_review_status_payload as _build_weekly_review_status_payload,
    build_weekly_review_submit_payload as _build_weekly_review_submit_payload,
    build_weekly_review_user_update_payload as _build_weekly_review_user_update_payload,
    interpret_weekly_review_decision as _interpret_weekly_review_decision,
    prepare_weekly_review_log_window_runtime as _prepare_weekly_review_log_window_runtime,
    prepare_weekly_review_submit_window as _prepare_weekly_review_submit_window,
    resolve_weekly_review_window as _resolve_weekly_review_window,
    summarize_weekly_review_performance as _summarize_weekly_review_performance,
)
from .decision_live_workout_guidance import (
    _humanize_workout_guidance as _decision_humanize_workout_guidance,
    _resolve_workout_set_guidance as _decision_resolve_workout_set_guidance,
    _workout_guidance_rationale as _decision_workout_guidance_rationale,
    hydrate_live_workout_recommendation as _hydrate_live_workout_recommendation,
    interpret_workout_set_feedback as _interpret_workout_set_feedback,
    recommend_live_workout_adjustment as _recommend_live_workout_adjustment,
    resolve_workout_session_state_update as _resolve_workout_session_state_update,
    summarize_workout_session_guidance as _summarize_workout_session_guidance,
)
from .progression import ExerciseState as _ProgressionExerciseState
from .progression import update_exercise_state_after_workout as _update_exercise_state_after_workout
from .scheduler import generate_week_plan
from .rules_runtime import (
    evaluate_deload_signal,
    resolve_adaptive_rule_runtime,
    resolve_repeat_failure_substitution,
    resolve_starting_load,
)
from .warmups import compute_warmups


ProgressionAction = Literal["progress", "hold", "deload"]
ProgramPhase = Literal["accumulation", "intensification", "deload"]

_WEAK_POINT_MAX_BOOSTED_EXERCISES = 2
_WEAK_POINT_SET_DELTA_CAP = 1
_WEAK_POINT_TOTAL_SET_BUDGET = 2
_WEAK_POINT_MIN_COMPLETION_FOR_BOOST = 90
_WEAK_POINT_MIN_READINESS_FOR_BOOST = 65
_WEAK_POINT_INTENSITY_MIN_SCALE = 0.93
_WEAK_POINT_INTENSITY_MAX_SCALE = 1.03


_SORENESS_LEVEL = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3,
}


def _normalized_soreness_level(value: str | None) -> int:
    key = (value or "none").strip().lower()
    return _SORENESS_LEVEL.get(key, 0)


def _clamp_days(value: int) -> int:
    return max(2, min(7, int(value)))


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _clamp_scale(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _joined_clauses(clauses: list[str]) -> str:
    if not clauses:
        return "training stress and recovery signals are not aligned"
    if len(clauses) == 1:
        return clauses[0]
    if len(clauses) == 2:
        return f"{clauses[0]} and {clauses[1]}"
    return ", ".join(clauses[:-1]) + f", and {clauses[-1]}"


def _rule_dict(rule_set: dict[str, Any] | None, key: str) -> dict[str, Any]:
    if not isinstance(rule_set, dict):
        return {}
    value = rule_set.get(key)
    return value if isinstance(value, dict) else {}


def _rule_rationale(rule_set: dict[str, Any] | None, key: str, fallback: str) -> str:
    templates = _rule_dict(rule_set, "rationale_templates")
    value = templates.get(key)
    return value if isinstance(value, str) and value.strip() else fallback


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_training_state(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_attr(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _resolve_rep_range(rep_range: Any) -> tuple[int, int]:
    if not isinstance(rep_range, list):
        return 8, 12
    minimum = int(rep_range[0]) if len(rep_range) > 0 else 8
    maximum = int(rep_range[1]) if len(rep_range) > 1 else minimum
    if minimum > maximum:
        minimum, maximum = maximum, minimum
    return minimum, maximum


def _deload_response(config: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "action": "deload",
        "load_scale": config["deload_load_scale"],
        "set_delta": config["deload_set_delta"],
        "reason": reason,
    }


def _hold_response(reason: str) -> dict[str, Any]:
    return {
        "action": "hold",
        "load_scale": 1.0,
        "set_delta": 0,
        "reason": reason,
    }


def _progress_response(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": "progress",
        "load_scale": config["progress_load_scale"],
        "set_delta": 0,
        "reason": config["progress_reason"],
    }


def _accumulation_phase_transition(
    *,
    weeks_in_phase: int,
    readiness_score: int,
    progression_action: ProgressionAction,
    stagnation_weeks: int,
    intro_weeks: int,
) -> dict[str, Any]:
    if intro_weeks and weeks_in_phase <= intro_weeks and stagnation_weeks >= 1:
        return {"next_phase": "accumulation", "reason": "intro_phase_protection"}
    if stagnation_weeks >= 2 or readiness_score < 55:
        return {"next_phase": "deload", "reason": "accumulation_stall"}
    if weeks_in_phase >= 6 and progression_action == "progress" and readiness_score >= 65:
        return {"next_phase": "intensification", "reason": "accumulation_complete"}
    return {"next_phase": "accumulation", "reason": "continue_accumulation"}


def summarize_weekly_review_performance(
    *,
    previous_week_start: date,
    week_start: date,
    previous_plan_payload: dict[str, Any],
    performed_logs: list[dict[str, Any]],
) -> dict[str, Any]:
    return _summarize_weekly_review_performance(
        previous_week_start=previous_week_start,
        week_start=week_start,
        previous_plan_payload=previous_plan_payload,
        performed_logs=performed_logs,
    )


def build_weekly_review_performance_summary(
    *,
    previous_week_start: date,
    week_start: date,
    previous_plan: Any | None,
    performed_logs: list[Any],
) -> dict[str, Any]:
    return _build_weekly_review_performance_summary(
        previous_week_start=previous_week_start,
        week_start=week_start,
        previous_plan=previous_plan,
        performed_logs=performed_logs,
    )


def interpret_weekly_review_decision(
    *,
    summary: dict[str, Any],
    body_weight: float,
    calories: int,
    protein: int,
    adherence_score: int,
    readiness_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _interpret_weekly_review_decision(
        summary=summary,
        body_weight=body_weight,
        calories=calories,
        protein=protein,
        adherence_score=adherence_score,
        readiness_state=readiness_state,
    )


def apply_weekly_review_adjustments_to_plan(
    *,
    plan: dict[str, Any],
    review_adjustments: dict[str, Any] | None,
    review_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _apply_weekly_review_adjustments_to_plan(
        plan_payload=plan,
        review_adjustments=review_adjustments,
        review_context=review_context,
    )


def _humanize_workout_guidance(guidance: str) -> str:
    return _decision_humanize_workout_guidance(guidance)


def _workout_guidance_rationale(guidance: str, *, rule_set: dict[str, Any] | None = None) -> str:
    return _decision_workout_guidance_rationale(guidance, rule_set=rule_set)


def _resolve_workout_set_guidance(reps: int, min_reps: int, max_reps: int) -> str:
    return _decision_resolve_workout_set_guidance(reps, min_reps, max_reps)


def _resolve_workout_summary_guidance(
    performed_sets: int,
    planned_sets: int,
    avg_reps: float,
    planned_min: int,
    planned_max: int,
) -> str:
    if performed_sets < planned_sets:
        return "incomplete_session_finish_remaining_sets_next_exposure"
    if avg_reps < planned_min:
        return "below_target_reps_reduce_or_hold_load"
    if avg_reps > planned_max:
        return "above_target_reps_increase_load_next_exposure"
    return "within_target_reps_hold_or_microload"


def _resolve_workout_overall_guidance(percent_complete: int, exercise_summaries: list[dict[str, Any]]) -> str:
    if percent_complete < 100:
        return "finish_all_planned_sets_for_reliable_progression"
    if any(str(item.get("guidance") or "") == "below_target_reps_reduce_or_hold_load" for item in exercise_summaries):
        return "performance_below_target_adjust_load_and_recover"
    if any(str(item.get("guidance") or "") == "above_target_reps_increase_load_next_exposure" for item in exercise_summaries):
        return "performance_above_target_progress_load"
    return "solid_execution_maintain_progression"


def hydrate_live_workout_recommendation(
    *,
    completed_sets: int,
    remaining_sets: int,
    recommended_reps_min: int,
    recommended_reps_max: int,
    recommended_weight: float,
    guidance: str,
    substitution_recommendation: dict[str, Any] | None = None,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _hydrate_live_workout_recommendation(
        completed_sets=completed_sets,
        remaining_sets=remaining_sets,
        recommended_reps_min=recommended_reps_min,
        recommended_reps_max=recommended_reps_max,
        recommended_weight=recommended_weight,
        guidance=guidance,
        substitution_recommendation=substitution_recommendation,
        rule_set=rule_set,
    )


def resolve_workout_session_state_update(
    *,
    existing_set_history: list[dict[str, Any]] | None,
    primary_exercise_id: str,
    planned_sets: int,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
    set_index: int,
    reps: int,
    weight: float,
    substitution_recommendation: dict[str, Any] | None = None,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _resolve_workout_session_state_update(
        existing_set_history=existing_set_history,
        primary_exercise_id=primary_exercise_id,
        planned_sets=planned_sets,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
        set_index=set_index,
        reps=reps,
        weight=weight,
        substitution_recommendation=substitution_recommendation,
        rule_set=rule_set,
    )


def recommend_live_workout_adjustment(
    *,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_sets: int,
    completed_sets: int,
    last_reps: int,
    last_weight: float,
    average_reps: float,
    substitution_recommendation: dict[str, Any] | None = None,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _recommend_live_workout_adjustment(
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_sets=planned_sets,
        completed_sets=completed_sets,
        last_reps=last_reps,
        last_weight=last_weight,
        average_reps=average_reps,
        substitution_recommendation=substitution_recommendation,
        rule_set=rule_set,
    )


def interpret_workout_set_feedback(
    *,
    reps: int,
    weight: float,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
    next_working_weight: float,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _interpret_workout_set_feedback(
        reps=reps,
        weight=weight,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
        next_working_weight=next_working_weight,
        rule_set=rule_set,
    )


def build_workout_progress_payload(
    *,
    workout_id: str,
    completed_sets_by_exercise: dict[str, int],
    planned_session: dict[str, Any] | None,
) -> dict[str, Any]:
    session = _coerce_dict(planned_session)
    planned_total = 0
    exercises: list[dict[str, Any]] = []

    for exercise in session.get("exercises") or []:
        exercise_id = str(exercise.get("id") or "")
        if not exercise_id:
            continue
        planned_sets = int(exercise.get("sets", 3) or 3)
        planned_total += planned_sets
        exercises.append(
            {
                "exercise_id": exercise_id,
                "planned_sets": planned_sets,
                "completed_sets": int(completed_sets_by_exercise.get(exercise_id, 0) or 0),
            }
        )

    completed_total = sum(int(value or 0) for value in completed_sets_by_exercise.values())
    percent_complete = int((completed_total / planned_total) * 100) if planned_total > 0 else 0

    return {
        "workout_id": workout_id,
        "completed_total": completed_total,
        "planned_total": planned_total,
        "percent_complete": percent_complete,
        "exercises": exercises,
    }


def build_workout_log_set_payload(
    *,
    record_id: str,
    primary_exercise_id: str,
    exercise_id: str,
    set_index: int,
    reps: int,
    weight: float,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
    feedback: dict[str, Any],
    starting_load_decision_trace: dict[str, Any] | None,
    live_recommendation: dict[str, Any],
    created_at: Any,
) -> dict[str, Any]:
    return {
        "id": record_id,
        "primary_exercise_id": primary_exercise_id,
        "exercise_id": exercise_id,
        "set_index": int(set_index),
        "reps": int(reps),
        "weight": float(weight),
        "planned_reps_min": int(planned_reps_min),
        "planned_reps_max": int(planned_reps_max),
        "planned_weight": float(planned_weight),
        "rep_delta": int(feedback["rep_delta"]),
        "weight_delta": float(feedback["weight_delta"]),
        "next_working_weight": float(feedback["next_working_weight"]),
        "guidance": str(feedback["guidance"]),
        "guidance_rationale": str(feedback["guidance_rationale"]),
        "decision_trace": deepcopy(dict(feedback["decision_trace"])),
        "starting_load_decision_trace": deepcopy(starting_load_decision_trace),
        "live_recommendation": deepcopy(live_recommendation),
        "created_at": created_at,
    }


def _normalized_equipment_profile(equipment_profile: list[str] | None) -> set[str]:
    return {
        str(item).strip().lower()
        for item in (equipment_profile or [])
        if str(item).strip()
    }


def build_repeat_failure_substitution_payload(
    *,
    planned_exercise: dict[str, Any] | None,
    exercise_state: Any,
    equipment_profile: list[str] | None,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any] | None:
    from .decision_workout_session import build_repeat_failure_substitution_payload as _impl

    return _impl(
        planned_exercise=planned_exercise,
        exercise_state=exercise_state,
        equipment_profile=equipment_profile,
        rule_set=rule_set,
    )


def prepare_workout_log_set_request_runtime(
    *,
    primary_exercise_id: str | None,
    exercise_id: str,
    set_index: int,
    reps: int,
    weight: float,
    rpe: float | None,
) -> dict[str, Any]:
    from .decision_workout_session import prepare_workout_log_set_request_runtime as _impl

    return _impl(
        primary_exercise_id=primary_exercise_id,
        exercise_id=exercise_id,
        set_index=set_index,
        reps=reps,
        weight=weight,
        rpe=rpe,
    )


def prepare_workout_exercise_state_runtime(
    *,
    existing_state: Any | None,
    primary_exercise_id: str,
    planned_exercise: dict[str, Any] | None,
    planned_weight: float,
    planned_sets: int,
    planned_reps_min: int,
    planned_reps_max: int,
    completed_set_index: int,
    completed_reps: int,
    nutrition_phase: str | None,
    equipment_profile: list[str] | None,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    from .decision_workout_session import prepare_workout_exercise_state_runtime as _impl

    return _impl(
        existing_state=existing_state,
        primary_exercise_id=primary_exercise_id,
        planned_exercise=planned_exercise,
        planned_weight=planned_weight,
        planned_sets=planned_sets,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        completed_set_index=completed_set_index,
        completed_reps=completed_reps,
        nutrition_phase=nutrition_phase,
        equipment_profile=equipment_profile,
        rule_set=rule_set,
    )


def prepare_workout_log_set_decision_runtime(
    *,
    user_id: str,
    workout_id: str,
    request_runtime: dict[str, Any],
    planned_exercise: dict[str, Any] | None,
    existing_exercise_state: Any | None,
    nutrition_phase: str | None,
    equipment_profile: list[str] | None,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    from .decision_workout_session import prepare_workout_log_set_decision_runtime as _impl

    return _impl(
        user_id=user_id,
        workout_id=workout_id,
        request_runtime=request_runtime,
        planned_exercise=planned_exercise,
        existing_exercise_state=existing_exercise_state,
        nutrition_phase=nutrition_phase,
        equipment_profile=equipment_profile,
        rule_set=rule_set,
    )


def resolve_workout_log_set_plan_context(
    *,
    planned_exercise: dict[str, Any] | None,
    fallback_weight: float,
) -> dict[str, Any]:
    from .decision_workout_session import resolve_workout_log_set_plan_context as _impl

    return _impl(planned_exercise=planned_exercise, fallback_weight=fallback_weight)


def build_workout_session_state_defaults(
    *,
    primary_exercise_id: str,
    planned_sets: int,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
) -> dict[str, Any]:
    from .decision_workout_session import build_workout_session_state_defaults as _impl

    return _impl(
        primary_exercise_id=primary_exercise_id,
        planned_sets=planned_sets,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
    )


def prepare_workout_session_state_persistence_payload(
    *,
    existing_state: Any | None,
    primary_exercise_id: str,
    planned_sets: int,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
    set_index: int,
    reps: int,
    weight: float,
    substitution_recommendation: dict[str, Any] | None,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    from .decision_workout_session import prepare_workout_session_state_persistence_payload as _impl

    return _impl(
        existing_state=existing_state,
        primary_exercise_id=primary_exercise_id,
        planned_sets=planned_sets,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
        set_index=set_index,
        reps=reps,
        weight=weight,
        substitution_recommendation=substitution_recommendation,
        rule_set=rule_set,
    )


def prepare_workout_session_state_upsert_runtime(
    *,
    existing_state: Any | None,
    primary_exercise_id: str,
    planned_sets: int,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
    set_index: int,
    reps: int,
    weight: float,
    substitution_recommendation: dict[str, Any] | None,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    from .decision_workout_session import prepare_workout_session_state_upsert_runtime as _impl

    return _impl(
        existing_state=existing_state,
        primary_exercise_id=primary_exercise_id,
        planned_sets=planned_sets,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
        set_index=set_index,
        reps=reps,
        weight=weight,
        substitution_recommendation=substitution_recommendation,
        rule_set=rule_set,
    )


def build_workout_today_plan_runtime(
    *,
    latest_plan_payload: dict[str, Any] | None,
    selected_program_name: str | None = None,
) -> dict[str, Any]:
    from .decision_workout_session import build_workout_today_plan_runtime as _impl

    return _impl(
        latest_plan_payload=latest_plan_payload,
    )


def resolve_workout_today_plan_payload(
    *,
    plan_rows: list[Any],
) -> dict[str, Any]:
    latest_row = plan_rows[0] if plan_rows else None
    latest_plan_payload = _coerce_dict(_read_attr(latest_row, "payload", {}))
    has_plan = latest_row is not None
    return {
        "has_plan": has_plan,
        "latest_plan_payload": latest_plan_payload,
        "decision_trace": {
            "interpreter": "resolve_workout_today_plan_payload",
            "version": "v1",
            "inputs": {
                "plan_row_count": len(plan_rows),
            },
            "outcome": {
                "has_plan": has_plan,
                "has_latest_payload_dict": bool(latest_plan_payload),
            },
        },
    }


def build_workout_today_log_runtime(
    *,
    recent_logs: list[Any],
    selected_session_logs: list[Any],
) -> dict[str, Any]:
    from .decision_workout_session import build_workout_today_log_runtime as _impl

    return _impl(recent_logs=recent_logs, selected_session_logs=selected_session_logs)


def build_workout_summary_progression_lookup_runtime(
    *,
    planned_session: dict[str, Any] | None,
) -> dict[str, Any]:
    from .decision_workout_session import build_workout_summary_progression_lookup_runtime as _impl

    return _impl(planned_session=planned_session)


def build_workout_today_progression_lookup_runtime(
    *,
    session_states: list[Any],
) -> dict[str, Any]:
    from .decision_workout_session import build_workout_today_progression_lookup_runtime as _impl

    return _impl(session_states=session_states)


def build_workout_today_session_state_payloads(
    *,
    session_states: list[Any],
    planned_session: dict[str, Any],
    progression_states: list[Any],
    equipment_profile: list[str] | None,
    rule_set: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    from .decision_workout_session import build_workout_today_session_state_payloads as _impl

    return _impl(
        session_states=session_states,
        planned_session=planned_session,
        progression_states=progression_states,
        equipment_profile=equipment_profile,
        rule_set=rule_set,
    )


def resolve_latest_logged_workout_resume_state(
    *,
    sessions: list[dict[str, Any]],
    performed_logs: list[dict[str, Any]],
) -> dict[str, Any]:
    from .decision_workout_session import resolve_latest_logged_workout_resume_state as _impl

    return _impl(
        sessions=sessions,
        performed_logs=performed_logs,
    )


def resolve_workout_today_session_selection(
    *,
    sessions: list[dict[str, Any]],
    latest_logged_workout_id: str | None,
    latest_logged_session_incomplete: bool,
    today_iso: str,
) -> dict[str, Any]:
    from .decision_workout_session import resolve_workout_today_session_selection as _impl

    return _impl(
        sessions=sessions,
        latest_logged_workout_id=latest_logged_workout_id,
        latest_logged_session_incomplete=latest_logged_session_incomplete,
        today_iso=today_iso,
    )


def resolve_workout_plan_reference(
    *,
    plan_payloads: list[dict[str, Any]],
    workout_id: str,
    exercise_id: str | None = None,
) -> dict[str, Any]:
    for payload in plan_payloads:
        normalized_payload = _coerce_dict(payload)
        sessions = normalized_payload.get("sessions") or []
        session = next(
            (item for item in sessions if str(_coerce_dict(item).get("session_id") or "") == workout_id),
            None,
        )
        if session is None:
            continue

        normalized_session = _coerce_dict(session)
        program_id = str(normalized_payload.get("program_template_id") or "").strip() or None
        if not exercise_id:
            return {
                "session": normalized_session,
                "exercise": None,
                "program_id": program_id,
            }

        exercises = normalized_session.get("exercises") or []
        exercise = next(
            (item for item in exercises if str(_coerce_dict(item).get("id") or "") == exercise_id),
            None,
        )
        return {
            "session": normalized_session,
            "exercise": _coerce_dict(exercise) if exercise is not None else None,
            "program_id": program_id,
        }

    return {
        "session": None,
        "exercise": None,
        "program_id": None,
    }


def resolve_workout_plan_context(
    *,
    plan_rows: list[Any],
    workout_id: str,
    exercise_id: str | None = None,
) -> dict[str, Any]:
    plan_payloads = [
        _coerce_dict(_read_attr(row, "payload", {}))
        for row in plan_rows
    ]
    reference = resolve_workout_plan_reference(
        plan_payloads=plan_payloads,
        workout_id=workout_id,
        exercise_id=exercise_id,
    )
    session = _coerce_dict(reference.get("session"))
    exercise = _coerce_dict(reference.get("exercise"))
    program_id = str(reference.get("program_id") or "").strip() or None
    return {
        "session": session or None,
        "exercise": exercise or None,
        "program_id": program_id,
        "decision_trace": {
            "interpreter": "resolve_workout_plan_context",
            "version": "v1",
            "inputs": {
                "plan_row_count": len(plan_rows),
                "workout_id": workout_id,
                "has_exercise_id": bool(exercise_id),
            },
            "outcome": {
                "matched_session": bool(session),
                "matched_exercise": bool(exercise),
                "program_id": program_id,
            },
        },
    }


def resolve_weekly_review_window(*, today: date) -> dict[str, date | bool]:
    return _resolve_weekly_review_window(today=today)


def prepare_weekly_review_submit_window(
    *,
    today: date,
    requested_week_start: date | None,
) -> dict[str, Any]:
    return _prepare_weekly_review_submit_window(
        today=today,
        requested_week_start=requested_week_start,
    )


def build_weekly_review_status_payload(
    *,
    today: date,
    existing_review_submitted: bool,
    previous_week_summary: dict[str, Any],
) -> dict[str, Any]:
    return _build_weekly_review_status_payload(
        today=today,
        existing_review_submitted=existing_review_submitted,
        previous_week_summary=previous_week_summary,
    )


def build_weekly_review_decision_payload(
    *,
    summary: dict[str, Any],
    body_weight: float,
    calories: int,
    protein: int,
    adherence_score: int,
    readiness_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _build_weekly_review_decision_payload(
        summary=summary,
        body_weight=body_weight,
        calories=calories,
        protein=protein,
        adherence_score=adherence_score,
        readiness_state=readiness_state,
    )


def build_weekly_review_submit_payload(
    *,
    week_start: date,
    previous_week_start: date,
    summary: dict[str, Any],
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    return _build_weekly_review_submit_payload(
        week_start=week_start,
        previous_week_start=previous_week_start,
        summary=summary,
        decision_payload=decision_payload,
    )


def build_weekly_review_cycle_persistence_payload(
    *,
    summary: dict[str, Any],
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    return _build_weekly_review_cycle_persistence_payload(
        summary=summary,
        decision_payload=decision_payload,
    )


def build_soreness_entry_persistence_payload(
    *,
    entry_date: date,
    severity_by_muscle: dict[str, str],
    notes: str | None,
) -> dict[str, Any]:
    return {
        "entry_date": entry_date,
        "severity_by_muscle": deepcopy(dict(severity_by_muscle)),
        "notes": notes,
    }


def build_body_measurement_create_payload(
    *,
    measured_on: date,
    name: str,
    value: float,
    unit: str,
) -> dict[str, Any]:
    return {
        "measured_on": measured_on,
        "name": name,
        "value": value,
        "unit": unit,
    }


def build_body_measurement_update_payload(
    *,
    measured_on: date | None,
    name: str | None,
    value: float | None,
    unit: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if measured_on is not None:
        payload["measured_on"] = measured_on
    if name is not None:
        payload["name"] = name
    if value is not None:
        payload["value"] = value
    if unit is not None:
        payload["unit"] = unit
    return payload


def prepare_profile_date_window_runtime(
    *,
    start_date: date | None,
    end_date: date | None,
) -> dict[str, Any]:
    return {
        "start_date": start_date,
        "end_date": end_date,
        "decision_trace": {
            "interpreter": "prepare_profile_date_window_runtime",
            "version": "v1",
            "inputs": {
                "has_start_date": start_date is not None,
                "has_end_date": end_date is not None,
            },
        },
    }


def build_profile_upsert_persistence_payload(
    *,
    name: str,
    age: int,
    weight: float,
    gender: str,
    split_preference: str,
    selected_program_id: str | None,
    training_location: str,
    equipment_profile: list[str],
    weak_areas: list[str] | None,
    onboarding_answers: dict[str, Any] | None,
    days_available: int,
    session_time_budget_minutes: int | None,
    movement_restrictions: list[str] | None,
    near_failure_tolerance: str | None,
    nutrition_phase: str,
    calories: int,
    protein: int,
    fat: int,
    carbs: int,
) -> dict[str, Any]:
    return {
        "name": name,
        "age": age,
        "weight": weight,
        "gender": gender,
        "split_preference": split_preference,
        "selected_program_id": selected_program_id or "full_body_v1",
        "training_location": training_location,
        "equipment_profile": list(equipment_profile),
        "weak_areas": list(weak_areas or []),
        "onboarding_answers": deepcopy(onboarding_answers) if isinstance(onboarding_answers, dict) else None,
        "days_available": days_available,
        "session_time_budget_minutes": session_time_budget_minutes,
        "movement_restrictions": list(movement_restrictions or []),
        "near_failure_tolerance": near_failure_tolerance,
        "nutrition_phase": nutrition_phase,
        "calories": calories,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
    }


def build_profile_response_payload(
    *,
    email: str,
    name: str | None,
    age: int | None,
    weight: float | None,
    gender: str | None,
    split_preference: str | None,
    selected_program_id: str | None,
    training_location: str | None,
    equipment_profile: list[str] | None,
    weak_areas: list[str] | None,
    onboarding_answers: dict[str, Any] | None,
    days_available: int | None,
    session_time_budget_minutes: int | None,
    movement_restrictions: list[str] | None,
    near_failure_tolerance: str | None,
    nutrition_phase: str | None,
    calories: int | None,
    protein: int | None,
    fat: int | None,
    carbs: int | None,
) -> dict[str, Any]:
    return {
        "email": email,
        "name": name,
        "age": age or 0,
        "weight": weight or 0,
        "gender": gender or "",
        "split_preference": split_preference or "",
        "selected_program_id": selected_program_id or "full_body_v1",
        "training_location": training_location,
        "equipment_profile": list(equipment_profile or []),
        "weak_areas": list(weak_areas or []),
        "onboarding_answers": deepcopy(onboarding_answers) if isinstance(onboarding_answers, dict) else {},
        "days_available": days_available or 2,
        "session_time_budget_minutes": session_time_budget_minutes,
        "movement_restrictions": list(movement_restrictions or []),
        "near_failure_tolerance": near_failure_tolerance,
        "nutrition_phase": nutrition_phase or "maintenance",
        "calories": calories or 0,
        "protein": protein or 0,
        "fat": fat or 0,
        "carbs": carbs or 0,
    }


def build_frequency_adaptation_persistence_state(
    *,
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    return _build_frequency_adaptation_persistence_state(decision_payload=decision_payload)


def build_generated_week_adaptation_persistence_payload(
    *,
    adaptation_runtime: dict[str, Any],
) -> dict[str, Any]:
    return _build_generated_week_adaptation_persistence_payload(adaptation_runtime=adaptation_runtime)


def build_weekly_checkin_persistence_payload(
    *,
    week_start: date,
    body_weight: float,
    adherence_score: int,
    sleep_quality: int | None,
    stress_level: int | None,
    pain_flags: list[str] | None,
    notes: str | None,
) -> dict[str, Any]:
    return {
        "week_start": week_start,
        "body_weight": body_weight,
        "adherence_score": adherence_score,
        "sleep_quality": sleep_quality,
        "stress_level": stress_level,
        "pain_flags": list(pain_flags or []),
        "notes": notes,
    }


def build_weekly_checkin_response_payload(
    *,
    nutrition_phase: str | None,
) -> dict[str, str]:
    return {
        "status": "logged",
        "phase": nutrition_phase or "maintenance",
    }


def build_weekly_review_user_update_payload(
    *,
    body_weight: float,
    calories: int,
    protein: int,
    fat: int,
    carbs: int,
    nutrition_phase: str | None,
) -> dict[str, Any]:
    return _build_weekly_review_user_update_payload(
        body_weight=body_weight,
        calories=calories,
        protein=protein,
        fat=fat,
        carbs=carbs,
        nutrition_phase=nutrition_phase,
    )


def prepare_weekly_review_log_window_runtime(
    *,
    previous_week_start: date,
    week_start: date,
) -> dict[str, Any]:
    return _prepare_weekly_review_log_window_runtime(
        previous_week_start=previous_week_start,
        week_start=week_start,
    )


def resolve_workout_completion_per_exercise(
    *,
    performed_logs: list[dict[str, Any]],
) -> dict[str, int]:
    completed_by_exercise: dict[str, int] = {}
    for row in performed_logs:
        exercise_id = str(row.get("exercise_id") or "")
        if not exercise_id:
            continue
        set_index = int(row.get("set_index") or 0)
        previous_completed_sets = completed_by_exercise.get(exercise_id, 0)
        if set_index > previous_completed_sets:
            completed_by_exercise[exercise_id] = set_index
    return completed_by_exercise


def group_workout_logs_by_exercise(
    *,
    performed_logs: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in performed_logs:
        exercise_id = str(row.get("exercise_id") or "")
        if not exercise_id:
            continue
        grouped.setdefault(exercise_id, []).append(dict(row))
    for exercise_logs in grouped.values():
        exercise_logs.sort(key=lambda row: int(row.get("set_index") or 0))
    return grouped


def _serialize_workout_summary_log_row(row: Any) -> dict[str, Any]:
    return {
        "exercise_id": _read_attr(row, "exercise_id"),
        "set_index": _read_attr(row, "set_index"),
        "reps": _read_attr(row, "reps"),
        "weight": _read_attr(row, "weight"),
    }


def _progression_weight_by_exercise(progression_states: list[Any]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for row in progression_states:
        exercise_id = str(_read_attr(row, "exercise_id") or "")
        if not exercise_id:
            continue
        weights[exercise_id] = float(_read_attr(row, "current_working_weight") or 0)
    return weights


def _build_workout_summary_exercise_summaries(
    *,
    planned_session: dict[str, Any],
    logs_by_exercise: dict[str, list[dict[str, Any]]],
    next_working_weight_by_exercise: dict[str, float],
    rule_set: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], int, int]:
    exercise_summaries: list[dict[str, Any]] = []
    planned_total = 0
    completed_total = 0

    for raw_exercise in planned_session.get("exercises") or []:
        exercise = _coerce_dict(raw_exercise)
        exercise_id = str(exercise.get("id") or "")
        if not exercise_id:
            continue

        primary_exercise_id = str(exercise.get("primary_exercise_id") or exercise_id)
        next_working_weight = next_working_weight_by_exercise.get(
            primary_exercise_id,
            float(exercise.get("recommended_working_weight", 0) or 0),
        )
        summary = summarize_workout_exercise_performance(
            exercise=exercise,
            performed_logs=[
                {
                    "set_index": row.get("set_index"),
                    "reps": row.get("reps"),
                    "weight": row.get("weight"),
                }
                for row in logs_by_exercise.get(exercise_id, [])
            ],
            next_working_weight=next_working_weight,
            rule_set=rule_set,
        )
        exercise_summaries.append(summary)
        planned_total += int(summary.get("planned_sets") or 0)
        completed_total += int(summary.get("performed_sets") or 0)

    return exercise_summaries, planned_total, completed_total


def build_workout_performance_summary(
    *,
    workout_id: str,
    planned_session: dict[str, Any],
    performed_logs: list[Any],
    progression_states: list[Any],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    from .decision_workout_session import build_workout_performance_summary as _impl

    return _impl(
        workout_id=workout_id,
        planned_session=planned_session,
        performed_logs=performed_logs,
        progression_states=progression_states,
        rule_set=rule_set,
    )


def build_workout_summary_payload(
    *,
    workout_id: str,
    completed_total: int,
    planned_total: int,
    exercise_summaries: list[dict[str, Any]],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    from .decision_workout_session import build_workout_summary_payload as _impl

    return _impl(
        workout_id=workout_id,
        completed_total=completed_total,
        planned_total=planned_total,
        exercise_summaries=exercise_summaries,
        rule_set=rule_set,
    )


def build_workout_today_state_payloads(
    *,
    session_states: list[dict[str, Any]],
    completed_sets_by_exercise: dict[str, int],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    from .decision_workout_session import build_workout_today_state_payloads as _impl

    return _impl(
        session_states=session_states,
        completed_sets_by_exercise=completed_sets_by_exercise,
        rule_set=rule_set,
    )


def build_workout_today_payload(
    *,
    selected_session: dict[str, Any],
    mesocycle: dict[str, Any] | None,
    deload: dict[str, Any] | None,
    completed_sets_by_exercise: dict[str, int],
    live_recommendations_by_exercise: dict[str, dict[str, Any]],
    resume_selected: bool,
    daily_quote: dict[str, Any],
) -> dict[str, Any]:
    from .decision_workout_session import build_workout_today_payload as _impl

    return _impl(
        selected_session=selected_session,
        mesocycle=mesocycle,
        deload=deload,
        completed_sets_by_exercise=completed_sets_by_exercise,
        live_recommendations_by_exercise=live_recommendations_by_exercise,
        resume_selected=resume_selected,
        daily_quote=daily_quote,
    )


def summarize_workout_exercise_performance(
    *,
    exercise: dict[str, Any],
    performed_logs: list[dict[str, Any]],
    next_working_weight: float,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .decision_workout_session import summarize_workout_exercise_performance as _impl

    return _impl(
        exercise=exercise,
        performed_logs=performed_logs,
        next_working_weight=next_working_weight,
        rule_set=rule_set,
    )


def summarize_workout_session_guidance(
    *,
    workout_id: str,
    completed_total: int,
    planned_total: int,
    exercise_summaries: list[dict[str, Any]],
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _summarize_workout_session_guidance(
        workout_id=workout_id,
        completed_total=completed_total,
        planned_total=planned_total,
        exercise_summaries=exercise_summaries,
        rule_set=rule_set,
    )


def _muscle_set_delta(
    from_volume: dict[str, int],
    to_volume: dict[str, int],
) -> dict[str, int]:
    muscles = sorted(set(from_volume).union(to_volume))
    return {muscle: int(to_volume.get(muscle, 0)) - int(from_volume.get(muscle, 0)) for muscle in muscles}


def _tradeoff_risk_level(delta_by_muscle: dict[str, int]) -> str:
    steep_losses = [delta for delta in delta_by_muscle.values() if delta <= -3]
    moderate_losses = [delta for delta in delta_by_muscle.values() if -3 < delta <= -1]
    if steep_losses:
        return "high"
    if moderate_losses:
        return "medium"
    return "low"


def _sorted_session_titles(plan: dict[str, Any]) -> list[str]:
    return [str(session.get("title") or session.get("session_id") or "") for session in plan.get("sessions", [])]


def _normalized_weak_areas(values: list[str] | None) -> list[str]:
    normalized = [str(item).strip().lower() for item in (values or []) if str(item).strip()]
    return list(dict.fromkeys(normalized))


def recommend_frequency_adaptation_preview(
    *,
    onboarding_package: dict[str, Any],
    program_id: str,
    current_days: int,
    target_days: int,
    duration_weeks: int,
    explicit_weak_areas: list[str] | None,
    stored_weak_areas: list[str] | None,
    equipment_profile: list[str] | None,
    recovery_state: str,
    current_week_index: int,
    request_runtime_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _recommend_frequency_adaptation_preview(
        onboarding_package=onboarding_package,
        program_id=program_id,
        current_days=current_days,
        target_days=target_days,
        duration_weeks=duration_weeks,
        explicit_weak_areas=explicit_weak_areas,
        stored_weak_areas=stored_weak_areas,
        equipment_profile=equipment_profile,
        recovery_state=recovery_state,
        current_week_index=current_week_index,
        request_runtime_trace=request_runtime_trace,
    )


def interpret_frequency_adaptation_apply(
    *,
    onboarding_package: dict[str, Any],
    program_id: str,
    current_days: int,
    target_days: int,
    duration_weeks: int,
    explicit_weak_areas: list[str] | None,
    stored_weak_areas: list[str] | None,
    equipment_profile: list[str] | None,
    recovery_state: str,
    current_week_index: int,
    applied_at: str,
    request_runtime_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _interpret_frequency_adaptation_apply(
        onboarding_package=onboarding_package,
        program_id=program_id,
        current_days=current_days,
        target_days=target_days,
        duration_weeks=duration_weeks,
        explicit_weak_areas=explicit_weak_areas,
        stored_weak_areas=stored_weak_areas,
        equipment_profile=equipment_profile,
        recovery_state=recovery_state,
        current_week_index=current_week_index,
        applied_at=applied_at,
        request_runtime_trace=request_runtime_trace,
    )


def build_frequency_adaptation_apply_payload(decision: dict[str, Any]) -> dict[str, Any]:
    return _build_frequency_adaptation_apply_payload(decision)


def prepare_frequency_adaptation_route_runtime(
    *,
    adaptation_runtime: dict[str, Any],
    onboarding_package: dict[str, Any],
    decision_kind: str,
    applied_at: str | None = None,
) -> dict[str, Any]:
    return _prepare_frequency_adaptation_route_runtime(
        adaptation_runtime=adaptation_runtime,
        onboarding_package=onboarding_package,
        decision_kind=decision_kind,
        applied_at=applied_at,
    )


def resolve_active_frequency_adaptation_runtime(
    *,
    active_state: dict[str, Any] | None,
    selected_template_id: str,
) -> dict[str, Any] | None:
    return _resolve_active_frequency_adaptation_runtime(
        active_state=active_state,
        selected_template_id=selected_template_id,
    )


def apply_active_frequency_adaptation_runtime(
    *,
    plan: dict[str, Any],
    selected_template_id: str,
    active_frequency_adaptation: dict[str, Any] | None,
) -> dict[str, Any]:
    return _apply_active_frequency_adaptation_runtime(
        plan=plan,
        selected_template_id=selected_template_id,
        active_frequency_adaptation=active_frequency_adaptation,
    )


def build_generated_week_plan_payload(
    *,
    base_plan: dict[str, Any],
    template_selection_trace: dict[str, Any],
    generation_runtime_trace: dict[str, Any],
    selected_template_id: str,
    active_frequency_adaptation: dict[str, Any] | None,
    review_adjustments: dict[str, Any] | None = None,
    review_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = deepcopy(base_plan)
    plan["template_selection_trace"] = deepcopy(template_selection_trace)
    plan["generation_runtime_trace"] = deepcopy(generation_runtime_trace)

    if review_adjustments is not None:
        plan = apply_weekly_review_adjustments_to_plan(
            plan=plan,
            review_adjustments=review_adjustments,
            review_context=review_context,
        )

    adaptation_runtime = apply_active_frequency_adaptation_runtime(
        plan=plan,
        selected_template_id=selected_template_id,
        active_frequency_adaptation=active_frequency_adaptation,
    )
    return {
        "plan": cast(dict[str, Any], adaptation_runtime["plan"]),
        "adaptation_runtime": adaptation_runtime,
    }


def prepare_generated_week_review_overlay(review_cycle: Any | None) -> dict[str, Any]:
    if review_cycle is None:
        return {
            "review_adjustments": None,
            "review_context": None,
            "decision_trace": {
                "interpreter": "prepare_generated_week_review_overlay",
                "version": "v1",
                "inputs": {"has_review_cycle": False},
                "outcome": {"review_available": False},
            },
        }

    raw_adjustments = _read_attr(review_cycle, "adjustments")
    review_adjustments = raw_adjustments if isinstance(raw_adjustments, dict) else {}
    week_start = _read_attr(review_cycle, "week_start")
    reviewed_on = _read_attr(review_cycle, "reviewed_on")

    week_start_iso = week_start.isoformat() if hasattr(week_start, "isoformat") else None
    reviewed_on_iso = reviewed_on.isoformat() if hasattr(reviewed_on, "isoformat") else None
    review_context = None
    if isinstance(week_start_iso, str) and isinstance(reviewed_on_iso, str):
        review_context = {
            "week_start": week_start_iso,
            "reviewed_on": reviewed_on_iso,
        }

    return {
        "review_adjustments": review_adjustments,
        "review_context": review_context,
        "decision_trace": {
            "interpreter": "prepare_generated_week_review_overlay",
            "version": "v1",
            "inputs": {
                "has_review_cycle": True,
                "adjustments_is_dict": isinstance(raw_adjustments, dict),
                "has_week_start": week_start_iso is not None,
                "has_reviewed_on": reviewed_on_iso is not None,
            },
            "outcome": {
                "review_available": True,
                "has_review_context": review_context is not None,
                "review_adjustment_keys": sorted(review_adjustments.keys()),
            },
        },
    }


def _is_program_adaptation_upgrade(summary: dict[str, Any], days_available: int) -> bool:
    if days_available < 2 or days_available > 4:
        return False
    session_count = int(summary.get("session_count") or 0)
    return session_count >= 5


def _program_catalog_rank(
    summary: dict[str, Any],
    *,
    days_available: int,
    split_preference: str,
) -> tuple[int, int, int, str]:
    split_rank = 0 if str(summary.get("split") or "") == split_preference else 1
    adaptation_rank = 0 if _is_program_adaptation_upgrade(summary, days_available) else 1
    session_rank = -int(summary.get("session_count") or 0)
    return (split_rank, adaptation_rank, session_rank, str(summary.get("id") or ""))


def _rotate_for_program_adaptation_upgrade(
    *,
    current_program_id: str,
    compatible_program_ids: list[str],
    compatible_program_summaries: list[dict[str, Any]],
    days_available: int,
) -> str | None:
    if days_available < 2 or days_available > 4:
        return None
    if len(compatible_program_ids) <= 1:
        return None

    summary_by_id = {str(item.get("id") or ""): item for item in compatible_program_summaries}
    current_summary = summary_by_id.get(current_program_id)
    if current_summary and _is_program_adaptation_upgrade(current_summary, days_available):
        return None

    for candidate in compatible_program_ids:
        if candidate == current_program_id:
            continue
        summary = summary_by_id.get(candidate)
        if summary and _is_program_adaptation_upgrade(summary, days_available):
            return candidate
    return None


def _rotate_for_program_coverage_gap(
    current_program_id: str,
    compatible_program_ids: list[str],
    latest_plan_payload: dict[str, Any],
) -> str | None:
    if len(compatible_program_ids) <= 1:
        return None
    under_target = (latest_plan_payload.get("muscle_coverage") or {}).get("under_target_muscles")
    if not isinstance(under_target, list) or len(under_target) < 4:
        return None
    return next((candidate for candidate in compatible_program_ids if candidate != current_program_id), None)


def _rotate_for_program_mesocycle_completion(
    current_program_id: str,
    compatible_program_ids: list[str],
    latest_plan_payload: dict[str, Any],
) -> str | None:
    if len(compatible_program_ids) <= 1:
        return None
    mesocycle = latest_plan_payload.get("mesocycle")
    if not isinstance(mesocycle, dict):
        return None

    week_index = int(mesocycle.get("week_index", 1) or 1)
    trigger_weeks = int(mesocycle.get("trigger_weeks_effective", 6) or 6)
    if week_index < trigger_weeks:
        return None

    index = compatible_program_ids.index(current_program_id)
    next_index = (index + 1) % len(compatible_program_ids)
    recommended = compatible_program_ids[next_index]
    return recommended if recommended != current_program_id else None


def _decision_step(rule: str, matched: bool, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "rule": rule,
        "matched": matched,
    }
    if details:
        payload["details"] = details
    return payload


def _compatible_program_ids(compatible_program_summaries: list[dict[str, Any]]) -> list[str]:
    program_ids = [str(item.get("id") or "") for item in compatible_program_summaries]
    return [item for item in program_ids if item]


def _resolve_program_recommendation_adherence_score(
    *,
    user_training_state: dict[str, Any],
    latest_adherence_score: int | None,
) -> tuple[int | None, str]:
    adherence_state = _coerce_dict(user_training_state.get("adherence_state"))
    canonical_score = adherence_state.get("latest_adherence_score")
    if canonical_score is not None:
        return int(canonical_score), "training_state"
    if latest_adherence_score is not None:
        return int(latest_adherence_score), "latest_checkin"
    return None, "default"


def _resolve_program_recommendation_plan_context(
    *,
    user_training_state: dict[str, Any],
    latest_plan_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    resolved_payload = dict(_coerce_dict(latest_plan_payload))
    sources = {
        "under_target_muscles_source": "latest_plan_payload",
        "mesocycle_context_source": "latest_plan_payload",
    }

    program_state = _coerce_dict(user_training_state.get("user_program_state"))
    generation_state = _coerce_dict(user_training_state.get("generation_state"))

    under_target_muscles = generation_state.get("under_target_muscles")
    if isinstance(under_target_muscles, list):
        resolved_payload["muscle_coverage"] = {
            **_coerce_dict(resolved_payload.get("muscle_coverage")),
            "under_target_muscles": [str(muscle) for muscle in under_target_muscles if str(muscle).strip()],
        }
        sources["under_target_muscles_source"] = "training_state"

    week_index = program_state.get("week_index")
    trigger_weeks_effective = generation_state.get("mesocycle_trigger_weeks_effective")
    if week_index is not None or trigger_weeks_effective is not None:
        resolved_payload["mesocycle"] = {
            **_coerce_dict(resolved_payload.get("mesocycle")),
            **({"week_index": int(week_index)} if week_index is not None else {}),
            **(
                {"trigger_weeks_effective": int(trigger_weeks_effective)}
                if trigger_weeks_effective is not None
                else {}
            ),
        }
        sources["mesocycle_context_source"] = "training_state"

    return resolved_payload, sources


def _program_selection_initial_decision(
    *,
    current_program_id: str,
    compatible_program_ids: list[str],
    latest_adherence_score: int | None,
) -> tuple[str, str, list[dict[str, Any]]] | None:
    if not compatible_program_ids:
        return "no_compatible_programs", current_program_id, [_decision_step("no_compatible_programs", True)]

    if current_program_id not in compatible_program_ids:
        recommended_program_id = compatible_program_ids[0]
        return (
            "current_not_compatible",
            recommended_program_id,
            [
                _decision_step(
                    "current_not_compatible",
                    True,
                    {"fallback_recommended_program_id": recommended_program_id},
                )
            ],
        )

    if latest_adherence_score is not None and latest_adherence_score <= 2:
        return (
            "low_adherence_keep_program",
            current_program_id,
            [
                _decision_step(
                    "low_adherence_keep_program",
                    True,
                    {"latest_adherence_score": latest_adherence_score},
                )
            ],
        )

    return None


def _program_selection_rotation_decision(
    *,
    current_program_id: str,
    compatible_program_ids: list[str],
    compatible_program_summaries: list[dict[str, Any]],
    days_available: int,
    latest_adherence_score: int | None,
    latest_plan_payload: dict[str, Any],
) -> tuple[str, str, list[dict[str, Any]]]:
    steps = [
        _decision_step("current_not_compatible", False),
        _decision_step(
            "low_adherence_keep_program",
            False,
            {"latest_adherence_score": latest_adherence_score},
        ),
    ]

    rotated = _rotate_for_program_adaptation_upgrade(
        current_program_id=current_program_id,
        compatible_program_ids=compatible_program_ids,
        compatible_program_summaries=compatible_program_summaries,
        days_available=days_available,
    )
    steps.append(
        _decision_step(
            "days_adaptation_upgrade",
            bool(rotated),
            {"candidate_program_id": rotated, "days_available": days_available},
        )
    )
    if rotated:
        return "days_adaptation_upgrade", rotated, steps

    rotated = _rotate_for_program_coverage_gap(
        current_program_id,
        compatible_program_ids,
        latest_plan_payload,
    )
    under_target = (latest_plan_payload.get("muscle_coverage") or {}).get("under_target_muscles")
    steps.append(
        _decision_step(
            "coverage_gap_rotate",
            bool(rotated),
            {
                "candidate_program_id": rotated,
                "under_target_muscle_count": len(under_target) if isinstance(under_target, list) else 0,
            },
        )
    )
    if rotated:
        return "coverage_gap_rotate", rotated, steps

    rotated = _rotate_for_program_mesocycle_completion(
        current_program_id,
        compatible_program_ids,
        latest_plan_payload,
    )
    mesocycle = latest_plan_payload.get("mesocycle") if isinstance(latest_plan_payload.get("mesocycle"), dict) else {}
    steps.append(
        _decision_step(
            "mesocycle_complete_rotate",
            bool(rotated),
            {
                "candidate_program_id": rotated,
                "week_index": int(mesocycle.get("week_index", 1) or 1),
                "trigger_weeks_effective": int(mesocycle.get("trigger_weeks_effective", 6) or 6),
            },
        )
    )
    if rotated:
        return "mesocycle_complete_rotate", rotated, steps

    steps.append(_decision_step("maintain_current_program", True))
    return "maintain_current_program", current_program_id, steps


# Stable compatibility surface while program recommendation ownership moves into
# the dedicated decision-family module.
humanize_program_reason = _humanize_program_reason
resolve_program_recommendation_candidates = _resolve_program_recommendation_candidates
recommend_program_selection = _recommend_program_selection
build_program_recommendation_payload = _build_program_recommendation_payload
prepare_program_recommendation_runtime = _prepare_program_recommendation_runtime
prepare_profile_program_recommendation_inputs = _prepare_profile_program_recommendation_inputs
prepare_profile_program_recommendation_route_runtime = _prepare_profile_program_recommendation_route_runtime
build_program_switch_payload = _build_program_switch_payload
prepare_program_switch_runtime = _prepare_program_switch_runtime


def humanize_specialization_reason(specialization: dict[str, Any]) -> str:
    rationale = str(specialization.get("rationale") or "").strip()
    if rationale:
        return rationale
    reason = str(specialization.get("reason") or "").strip()
    return reason


def resolve_coaching_recommendation_rationale(recommendation_payload: dict[str, Any]) -> str:
    phase_transition = _coerce_dict(recommendation_payload.get("phase_transition"))
    progression = _coerce_dict(recommendation_payload.get("progression"))
    specialization = _coerce_dict(recommendation_payload.get("specialization"))

    for container in (phase_transition, progression, specialization):
        rationale = str(container.get("rationale") or "").strip()
        if rationale:
            return rationale

    for container in (phase_transition, progression, specialization):
        reason = str(container.get("reason") or "").strip()
        if reason:
            return reason

    return "No rationale recorded"


def extract_coaching_recommendation_focus_muscles(recommendation_payload: dict[str, Any]) -> list[str]:
    return _extract_coaching_recommendation_focus_muscles(recommendation_payload)


def build_coaching_recommendation_timeline_entry(
    *,
    recommendation_id: str,
    recommendation_type: str,
    status: str,
    template_id: str,
    current_phase: str,
    recommended_phase: str,
    progression_action: str,
    recommendation_payload: dict[str, Any],
    created_at: datetime,
    applied_at: datetime | None,
) -> dict[str, Any]:
    return _build_coaching_recommendation_timeline_entry(
        recommendation_id=recommendation_id,
        recommendation_type=recommendation_type,
        status=status,
        template_id=template_id,
        current_phase=current_phase,
        recommended_phase=recommended_phase,
        progression_action=progression_action,
        recommendation_payload=recommendation_payload,
        created_at=created_at,
        applied_at=applied_at,
        humanize_phase_transition_reason=humanize_phase_transition_reason,
        humanize_progression_reason=humanize_progression_reason,
        humanize_specialization_reason=humanize_specialization_reason,
    )


def normalize_coaching_recommendation_timeline_limit(limit: int) -> int:
    return _normalize_coaching_recommendation_timeline_limit(limit)


def build_coaching_recommendation_timeline_payload(rows: list[Any]) -> dict[str, Any]:
    return _build_coaching_recommendation_timeline_payload(
        rows,
        humanize_phase_transition_reason=humanize_phase_transition_reason,
        humanize_progression_reason=humanize_progression_reason,
        humanize_specialization_reason=humanize_specialization_reason,
    )


def build_phase_applied_recommendation_record(
    *,
    template_id: str,
    current_phase: str,
    progression_action: str,
    source_recommendation_id: str,
    next_phase: str,
) -> dict[str, Any]:
    return _build_phase_applied_recommendation_record(
        template_id=template_id,
        current_phase=current_phase,
        progression_action=progression_action,
        source_recommendation_id=source_recommendation_id,
        next_phase=next_phase,
    )


def build_specialization_applied_recommendation_record(
    *,
    template_id: str,
    current_phase: str,
    recommended_phase: str,
    progression_action: str,
    source_recommendation_id: str,
) -> dict[str, Any]:
    return _build_specialization_applied_recommendation_record(
        template_id=template_id,
        current_phase=current_phase,
        recommended_phase=recommended_phase,
        progression_action=progression_action,
        source_recommendation_id=source_recommendation_id,
    )


def prepare_coaching_apply_runtime_source(source_recommendation: Any) -> dict[str, Any]:
    return _prepare_coaching_apply_runtime_source(source_recommendation)


def prepare_coaching_apply_decision_runtime(
    *,
    decision_kind: str,
    source_runtime: dict[str, Any],
    confirm: bool,
) -> dict[str, Any]:
    return _prepare_coaching_apply_decision_runtime(
        decision_kind=decision_kind,
        source_runtime=source_runtime,
        confirm=confirm,
        prepare_phase_runtime=prepare_phase_apply_runtime,
        prepare_specialization_runtime=prepare_specialization_apply_runtime,
    )


def prepare_phase_apply_runtime(
    *,
    recommendation_id: str,
    recommendation_payload: dict[str, Any],
    fallback_next_phase: str | None,
    confirm: bool,
    template_id: str,
    current_phase: str,
    progression_action: str,
) -> dict[str, Any]:
    return _prepare_phase_apply_runtime(
        recommendation_id=recommendation_id,
        recommendation_payload=recommendation_payload,
        fallback_next_phase=fallback_next_phase,
        confirm=confirm,
        template_id=template_id,
        current_phase=current_phase,
        progression_action=progression_action,
        interpret_phase_apply_decision=interpret_coach_phase_apply_decision,
        build_phase_applied_record=build_phase_applied_recommendation_record,
    )


def prepare_specialization_apply_runtime(
    *,
    recommendation_id: str,
    recommendation_payload: dict[str, Any],
    confirm: bool,
    template_id: str,
    current_phase: str,
    recommended_phase: str,
    progression_action: str,
) -> dict[str, Any]:
    return _prepare_specialization_apply_runtime(
        recommendation_id=recommendation_id,
        recommendation_payload=recommendation_payload,
        confirm=confirm,
        template_id=template_id,
        current_phase=current_phase,
        recommended_phase=recommended_phase,
        progression_action=progression_action,
        interpret_specialization_apply_decision=interpret_coach_specialization_apply_decision,
        build_specialization_applied_record=build_specialization_applied_recommendation_record,
    )


def finalize_applied_coaching_recommendation(
    *,
    payload_key: str,
    payload_value: dict[str, Any],
    decision_payload: dict[str, Any],
    applied_recommendation_id: str,
) -> dict[str, Any]:
    return _finalize_applied_coaching_recommendation(
        payload_key=payload_key,
        payload_value=payload_value,
        decision_payload=decision_payload,
        applied_recommendation_id=applied_recommendation_id,
    )


def build_applied_coaching_recommendation_response(
    *,
    payload_key: str,
    payload_value: dict[str, Any],
    decision_payload: dict[str, Any],
    applied_recommendation_id: str,
) -> dict[str, Any]:
    return _build_applied_coaching_recommendation_response(
        payload_key=payload_key,
        payload_value=payload_value,
        decision_payload=decision_payload,
        applied_recommendation_id=applied_recommendation_id,
    )


def build_applied_coaching_recommendation_record_values(
    *,
    user_id: str,
    applied_at: Any,
    record_fields: dict[str, Any],
) -> dict[str, Any]:
    return _build_applied_coaching_recommendation_record_values(
        user_id=user_id,
        applied_at=applied_at,
        record_fields=record_fields,
    )


def prepare_applied_coaching_recommendation_commit_runtime(
    *,
    user_id: str,
    applied_at: Any,
    record_fields: dict[str, Any],
    payload_key: str,
    payload_value: dict[str, Any],
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    return _prepare_applied_coaching_recommendation_commit_runtime(
        user_id=user_id,
        applied_at=applied_at,
        record_fields=record_fields,
        payload_key=payload_key,
        payload_value=payload_value,
        decision_payload=decision_payload,
    )


def prepare_coaching_apply_commit_runtime(
    *,
    decision_kind: str,
    user_id: str,
    applied_at: Any,
    apply_runtime: dict[str, Any],
) -> dict[str, Any]:
    return _prepare_coaching_apply_commit_runtime(
        decision_kind=decision_kind,
        user_id=user_id,
        applied_at=applied_at,
        apply_runtime=apply_runtime,
    )


def prepare_coaching_apply_route_runtime(
    *,
    decision_kind: str,
    source_runtime: dict[str, Any],
    confirm: bool,
    user_id: str,
    applied_at: Any,
) -> dict[str, Any]:
    return _prepare_coaching_apply_route_runtime(
        decision_kind=decision_kind,
        source_runtime=source_runtime,
        confirm=confirm,
        user_id=user_id,
        applied_at=applied_at,
        prepare_apply_decision_runtime=prepare_coaching_apply_decision_runtime,
        prepare_apply_commit_runtime=prepare_coaching_apply_commit_runtime,
    )


def finalize_applied_coaching_recommendation_commit_runtime(
    *,
    prepared_runtime: dict[str, Any],
    applied_recommendation_id: str,
) -> dict[str, Any]:
    return _finalize_applied_coaching_recommendation_commit_runtime(
        prepared_runtime=prepared_runtime,
        applied_recommendation_id=applied_recommendation_id,
    )


def prepare_coaching_apply_route_finalize_runtime(
    *,
    route_runtime: dict[str, Any],
    applied_recommendation_id: str | None = None,
) -> dict[str, Any]:
    return _prepare_coaching_apply_route_finalize_runtime(
        route_runtime=route_runtime,
        applied_recommendation_id=applied_recommendation_id,
    )


def recommend_coach_intelligence_preview(
    *,
    template_id: str,
    context: dict[str, Any],
    preview_request: dict[str, Any],
    rule_set: dict[str, Any] | None = None,
    request_runtime_trace: dict[str, Any] | None = None,
    template_runtime_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _recommend_coach_intelligence_preview(
        template_id=template_id,
        context=context,
        preview_request=preview_request,
        rule_set=rule_set,
        request_runtime_trace=request_runtime_trace,
        template_runtime_trace=template_runtime_trace,
        evaluate_schedule_adaptation=evaluate_schedule_adaptation,
        recommend_progression_action=recommend_progression_action,
        humanize_progression_reason=humanize_progression_reason,
        derive_readiness_score=derive_readiness_score,
        recommend_phase_transition=recommend_phase_transition,
        humanize_phase_transition_reason=humanize_phase_transition_reason,
        recommend_specialization_adjustments=recommend_specialization_adjustments,
        summarize_program_media_and_warmups=summarize_program_media_and_warmups,
    )


def build_coach_preview_payloads(
    *,
    recommendation_id: str,
    preview_payload: dict[str, Any],
    program_name: str,
) -> dict[str, dict[str, Any]]:
    return _build_coach_preview_payloads(
        recommendation_id=recommendation_id,
        preview_payload=preview_payload,
        program_name=program_name,
    )


def build_coach_preview_recommendation_record_fields(
    *,
    template_id: str,
    preview_request: dict[str, Any],
    preview_payload: dict[str, Any],
) -> dict[str, Any]:
    return _build_coach_preview_recommendation_record_fields(
        template_id=template_id,
        preview_request=preview_request,
        preview_payload=preview_payload,
    )


def prepare_coach_preview_commit_runtime(
    *,
    user_id: str,
    template_id: str,
    preview_request: dict[str, Any],
    preview_payload: dict[str, Any],
    program_name: str,
) -> dict[str, Any]:
    return _prepare_coach_preview_commit_runtime(
        user_id=user_id,
        template_id=template_id,
        preview_request=preview_request,
        preview_payload=preview_payload,
        program_name=program_name,
    )


def finalize_coach_preview_commit_runtime(
    *,
    prepared_runtime: dict[str, Any],
    recommendation_id: str,
) -> dict[str, Any]:
    return _finalize_coach_preview_commit_runtime(
        prepared_runtime=prepared_runtime,
        recommendation_id=recommendation_id,
    )


def interpret_coach_phase_apply_decision(
    *,
    recommendation_id: str,
    phase_transition: dict[str, Any],
    confirm: bool,
) -> dict[str, Any]:
    return _interpret_coach_phase_apply_decision(
        recommendation_id=recommendation_id,
        phase_transition=phase_transition,
        confirm=confirm,
        humanize_phase_transition_reason=humanize_phase_transition_reason,
    )


def interpret_coach_specialization_apply_decision(
    *,
    recommendation_id: str,
    specialization: dict[str, Any],
    confirm: bool,
) -> dict[str, Any]:
    return _interpret_coach_specialization_apply_decision(
        recommendation_id=recommendation_id,
        specialization=specialization,
        confirm=confirm,
    )


# Stable compatibility surface while progression/phase-transition ownership
# moves into the dedicated decision-family module.
evaluate_schedule_adaptation = _evaluate_schedule_adaptation
humanize_progression_reason = _humanize_progression_reason
humanize_phase_transition_reason = _humanize_phase_transition_reason
derive_readiness_score = _derive_readiness_score
recommend_progression_action = _recommend_progression_action
recommend_phase_transition = _recommend_phase_transition


def recommend_specialization_adjustments(
    *,
    weekly_volume_by_muscle: dict[str, int],
    lagging_muscles: list[str],
    max_focus_muscles: int = 2,
    target_min_sets: int = 8,
) -> dict[str, Any]:
    from .decision_coach_preview import recommend_specialization_adjustments as _recommend_specialization_adjustments

    return _recommend_specialization_adjustments(
        weekly_volume_by_muscle=weekly_volume_by_muscle,
        lagging_muscles=lagging_muscles,
        max_focus_muscles=max_focus_muscles,
        target_min_sets=target_min_sets,
    )


def summarize_program_media_and_warmups(program_template: dict[str, Any]) -> dict[str, Any]:
    from .decision_coach_preview import summarize_program_media_and_warmups as _summarize_program_media_and_warmups

    return _summarize_program_media_and_warmups(program_template)
