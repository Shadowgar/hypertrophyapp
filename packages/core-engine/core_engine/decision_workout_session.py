from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, cast

from .decision_live_workout_guidance import (
    hydrate_live_workout_recommendation,
    _workout_guidance_rationale,
    interpret_workout_set_feedback,
    resolve_workout_session_state_update,
    summarize_workout_session_guidance,
)
from .generation import resolve_optional_rule_set
from .equipment_profile import canonicalize_equipment_profile
from .progression import ExerciseState as _ProgressionExerciseState
from .progression import update_exercise_state_after_workout as _update_exercise_state_after_workout
from .intelligence import (
    build_workout_log_set_payload,
    build_workout_performance_summary,
    build_workout_progress_payload,
    build_workout_today_progression_lookup_runtime,
    build_workout_summary_progression_lookup_runtime,
    build_workout_today_log_runtime,
    build_workout_today_payload,
    build_workout_today_plan_runtime,
    build_workout_today_session_state_payloads,
    build_workout_today_state_payloads,
    prepare_workout_log_set_decision_runtime,
    prepare_workout_log_set_request_runtime,
    prepare_workout_session_state_upsert_runtime,
    resolve_workout_completion_per_exercise,
    resolve_workout_plan_context,
    resolve_workout_today_plan_payload,
)
from .rules_runtime import resolve_repeat_failure_substitution, resolve_starting_load
from .warmups import compute_warmups


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_attr(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _normalized_equipment_profile(equipment_profile: list[str] | None) -> set[str]:
    return set(canonicalize_equipment_profile(equipment_profile))

def build_repeat_failure_substitution_payload(
    *,
    planned_exercise: dict[str, Any] | None,
    exercise_state: Any,
    equipment_profile: list[str] | None,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any] | None:
    exercise = _coerce_dict(planned_exercise)
    if exercise_state is None:
        return None

    substitutions = exercise.get("substitution_candidates") or exercise.get("substitutions") or []
    if not isinstance(substitutions, list) or not substitutions:
        return None

    runtime = resolve_repeat_failure_substitution(
        exercise_id=str(exercise.get("primary_exercise_id") or exercise.get("id") or _read_attr(exercise_state, "exercise_id") or ""),
        exercise_name=str(exercise.get("name") or _read_attr(exercise_state, "exercise_id") or ""),
        substitution_candidates=[str(candidate) for candidate in substitutions if str(candidate).strip()],
        consecutive_under_target_exposures=int(_read_attr(exercise_state, "consecutive_under_target_exposures") or 0),
        equipment_set=_normalized_equipment_profile(equipment_profile),
        rule_set=rule_set,
    )
    if not runtime["recommend_substitution"]:
        return None

    threshold = runtime["repeat_failure_threshold"]
    if threshold is None:
        return None

    return {
        "recommended_name": str(runtime["recommended_name"]),
        "compatible_substitutions": list(runtime["compatible_substitutions"]),
        "failed_exposure_count": int(_read_attr(exercise_state, "consecutive_under_target_exposures") or 0),
        "trigger_threshold": int(threshold),
        "reason": "repeat_failure_threshold_reached",
        "decision_trace": dict(runtime["decision_trace"]),
    }

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
    set_kind: str | None = None,
    parent_set_index: int | None = None,
) -> dict[str, Any]:
    starting_load_runtime: dict[str, Any] | None = None
    if existing_state is not None:
        initial_state_values = {
            "current_working_weight": float(_read_attr(existing_state, "current_working_weight") or planned_weight),
            "exposure_count": int(_read_attr(existing_state, "exposure_count") or 0),
            "consecutive_under_target_exposures": int(_read_attr(existing_state, "consecutive_under_target_exposures") or 0),
            "last_progression_action": str(_read_attr(existing_state, "last_progression_action") or "hold"),
            "fatigue_score": int(_read_attr(existing_state, "fatigue_score") or 0),
        }
    else:
        starting_load_runtime = resolve_starting_load(
            planned_exercise=planned_exercise,
            fallback_weight=planned_weight,
            rule_set=rule_set,
        )
        initial_state_values = {
            "current_working_weight": float(starting_load_runtime["working_weight"]),
            "exposure_count": 0,
            "consecutive_under_target_exposures": 0,
            "last_progression_action": "hold",
            "fatigue_score": 0,
        }

    normalized_set_kind = str(set_kind or "").strip().lower()
    participates_in_progression = parent_set_index is None and (
        not normalized_set_kind or normalized_set_kind == "work"
    )
    if participates_in_progression:
        updated_state = _update_exercise_state_after_workout(
            exercise_state=_ProgressionExerciseState(
                exercise_id=primary_exercise_id,
                current_working_weight=float(initial_state_values["current_working_weight"]),
                exposure_count=int(initial_state_values["exposure_count"]),
                consecutive_under_target_exposures=int(initial_state_values["consecutive_under_target_exposures"]),
                last_progression_action=str(initial_state_values["last_progression_action"]),
                fatigue_score=int(initial_state_values["fatigue_score"]),
            ),
            completed_reps=int(completed_reps),
            target_rep_range=(int(planned_reps_min), int(planned_reps_max)),
            completed_sets=int(completed_set_index),
            planned_sets=max(1, int(planned_sets)),
            phase_modifier=nutrition_phase or "maintenance",
            load_semantics=str(_coerce_dict(planned_exercise).get("load_semantics") or "") or None,
            rule_set=rule_set,
        )
    else:
        updated_state = _ProgressionExerciseState(
            exercise_id=primary_exercise_id,
            current_working_weight=float(initial_state_values["current_working_weight"]),
            exposure_count=int(initial_state_values["exposure_count"]),
            consecutive_under_target_exposures=int(initial_state_values["consecutive_under_target_exposures"]),
            last_progression_action=str(initial_state_values["last_progression_action"]),
            fatigue_score=int(initial_state_values["fatigue_score"]),
        )
    state_values = {
        "current_working_weight": float(updated_state.current_working_weight),
        "exposure_count": int(updated_state.exposure_count),
        "consecutive_under_target_exposures": int(updated_state.consecutive_under_target_exposures),
        "last_progression_action": str(updated_state.last_progression_action),
        "fatigue_score": int(updated_state.fatigue_score),
    }
    substitution_recommendation = build_repeat_failure_substitution_payload(
        planned_exercise=planned_exercise,
        exercise_state=updated_state,
        equipment_profile=equipment_profile,
        rule_set=rule_set,
    )
    return {
        "initial_state_values": initial_state_values,
        "state_values": state_values,
        "starting_load_runtime": deepcopy(starting_load_runtime),
        "substitution_recommendation": deepcopy(substitution_recommendation),
        "decision_trace": {
            "interpreter": "prepare_workout_exercise_state_runtime",
            "version": "v1",
            "inputs": {
                "primary_exercise_id": primary_exercise_id,
                "planned_reps_min": int(planned_reps_min),
                "planned_reps_max": int(planned_reps_max),
                "planned_sets": int(planned_sets),
                "completed_set_index": int(completed_set_index),
                "completed_reps": int(completed_reps),
                "set_kind": set_kind,
                "parent_set_index": parent_set_index,
                "has_existing_state": existing_state is not None,
                "has_rule_set": isinstance(rule_set, dict),
            },
            "outcome": {
                "current_working_weight": float(updated_state.current_working_weight),
                "exposure_count": int(updated_state.exposure_count),
                "consecutive_under_target_exposures": int(updated_state.consecutive_under_target_exposures),
                "last_progression_action": str(updated_state.last_progression_action),
                "has_starting_load_runtime": starting_load_runtime is not None,
                "has_substitution_recommendation": substitution_recommendation is not None,
                "participates_in_progression": participates_in_progression,
            },
        },
    }

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

def summarize_workout_exercise_performance(
    *,
    exercise: dict[str, Any],
    performed_logs: list[dict[str, Any]],
    next_working_weight: float,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    exercise_id = str(exercise.get("id") or "")
    planned_sets = int(exercise.get("sets", 3) or 3)
    rep_range = exercise.get("rep_range") or [8, 12]
    planned_min = int(rep_range[0]) if len(rep_range) > 0 else 8
    planned_max = int(rep_range[1]) if len(rep_range) > 1 else planned_min
    if planned_min > planned_max:
        planned_min, planned_max = planned_max, planned_min
    planned_weight = float(exercise.get("recommended_working_weight", 0) or 0)

    performed_sets = len(performed_logs)
    if performed_logs:
        average_reps = sum(float(row.get("reps", 0) or 0) for row in performed_logs) / performed_sets
        average_weight = sum(float(row.get("weight", 0) or 0) for row in performed_logs) / performed_sets
    else:
        average_reps = 0.0
        average_weight = 0.0

    completion_pct = int((performed_sets / max(planned_sets, 1)) * 100)
    rep_target_mid = (planned_min + planned_max) / 2
    rep_delta = round(average_reps - rep_target_mid, 2) if performed_sets else round(-rep_target_mid, 2)
    weight_delta = round(average_weight - planned_weight, 2) if performed_sets else round(-planned_weight, 2)
    guidance = _resolve_workout_summary_guidance(performed_sets, planned_sets, average_reps, planned_min, planned_max)
    guidance_rationale = _workout_guidance_rationale(guidance, rule_set=rule_set)
    decision_trace = {
        "interpreter": "summarize_workout_exercise_performance",
        "version": "v1",
        "inputs": {
            "exercise_id": exercise_id,
            "planned_sets": planned_sets,
            "planned_reps_min": planned_min,
            "planned_reps_max": planned_max,
            "planned_weight": planned_weight,
            "performed_set_count": performed_sets,
        },
        "steps": [
            {
                "decision": "exercise_summary_guidance",
                "result": {
                    "guidance": guidance,
                    "completion_pct": completion_pct,
                    "average_reps": round(average_reps, 2),
                    "average_weight": round(average_weight, 2),
                },
            }
        ],
        "outcome": {
            "guidance": guidance,
            "guidance_rationale": guidance_rationale,
            "next_working_weight": round(next_working_weight, 2),
        },
    }
    return {
        "exercise_id": exercise_id,
        "primary_exercise_id": exercise.get("primary_exercise_id"),
        "name": str(exercise.get("name") or exercise_id),
        "planned_sets": planned_sets,
        "planned_reps_min": planned_min,
        "planned_reps_max": planned_max,
        "planned_weight": planned_weight,
        "performed_sets": performed_sets,
        "average_performed_reps": round(average_reps, 2),
        "average_performed_weight": round(average_weight, 2),
        "completion_pct": completion_pct,
        "rep_delta": rep_delta,
        "weight_delta": weight_delta,
        "next_working_weight": round(next_working_weight, 2),
        "guidance": guidance,
        "guidance_rationale": guidance_rationale,
        "decision_trace": decision_trace,
    }

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

def build_workout_summary_payload(
    *,
    workout_id: str,
    completed_total: int,
    planned_total: int,
    exercise_summaries: list[dict[str, Any]],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    overall_summary = summarize_workout_session_guidance(
        workout_id=workout_id,
        completed_total=completed_total,
        planned_total=planned_total,
        exercise_summaries=exercise_summaries,
        rule_set=rule_set,
    )
    return {
        "workout_id": workout_id,
        "completed_total": completed_total,
        "planned_total": planned_total,
        "percent_complete": int(overall_summary["percent_complete"]),
        "overall_guidance": str(overall_summary["overall_guidance"]),
        "overall_rationale": str(overall_summary["overall_rationale"]),
        "decision_trace": dict(overall_summary["decision_trace"]),
        "exercises": exercise_summaries,
    }

def build_workout_performance_summary(
    *,
    workout_id: str,
    planned_session: dict[str, Any],
    performed_logs: list[Any],
    progression_states: list[Any],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    logs_by_exercise = group_workout_logs_by_exercise(
        performed_logs=[_serialize_workout_summary_log_row(row) for row in performed_logs]
    )
    next_working_weight_by_exercise = _progression_weight_by_exercise(progression_states)
    exercise_summaries, planned_total, completed_total = _build_workout_summary_exercise_summaries(
        planned_session=planned_session,
        logs_by_exercise=logs_by_exercise,
        next_working_weight_by_exercise=next_working_weight_by_exercise,
        rule_set=rule_set,
    )

    return build_workout_summary_payload(
        workout_id=workout_id,
        completed_total=completed_total,
        planned_total=planned_total,
        exercise_summaries=exercise_summaries,
        rule_set=rule_set,
    )

def build_workout_today_plan_runtime(
    *,
    latest_plan_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = _coerce_dict(latest_plan_payload)
    sessions = [
        _coerce_dict(session)
        for session in (payload.get("sessions") or [])
        if isinstance(session, dict)
    ]
    session_ids = [
        str(session.get("session_id") or "")
        for session in sessions
        if str(session.get("session_id") or "")
    ]
    selected_program_id = str(payload.get("program_template_id") or "").strip() or None
    mesocycle = _coerce_dict(payload.get("mesocycle")) if isinstance(payload.get("mesocycle"), dict) else None
    deload = _coerce_dict(payload.get("deload")) if isinstance(payload.get("deload"), dict) else None

    return {
        "sessions": sessions,
        "session_ids": session_ids,
        "selected_program_id": selected_program_id,
        "mesocycle": mesocycle,
        "deload": deload,
        "decision_trace": {
            "interpreter": "build_workout_today_plan_runtime",
            "version": "v1",
            "inputs": {"has_latest_plan_payload": bool(payload)},
            "outcome": {
                "session_count": len(sessions),
                "session_id_count": len(session_ids),
                "selected_program_id": selected_program_id,
                "has_mesocycle": mesocycle is not None,
                "has_deload": deload is not None,
            },
        },
    }


def resolve_latest_logged_workout_resume_state(
    *,
    sessions: list[dict[str, Any]],
    performed_logs: list[dict[str, Any]],
) -> dict[str, Any]:
    session_by_id = {
        str(session.get("session_id") or ""): session
        for session in sessions
        if str(session.get("session_id") or "")
    }
    latest_logged_workout_id = None
    latest_logged_session_incomplete = False

    if session_by_id and performed_logs:
        latest_logged_workout_id = str(performed_logs[0].get("workout_id") or "") or None
        latest_logged_session = session_by_id.get(str(latest_logged_workout_id or ""))
        if latest_logged_session is not None:
            planned_sets = sum(int(exercise.get("sets", 3) or 3) for exercise in latest_logged_session.get("exercises", []))
            logged_sets = sum(
                1
                for row in performed_logs
                if str(row.get("workout_id") or "") == latest_logged_workout_id
                and row.get("parent_set_index") is None
                and (
                    not str(row.get("set_kind") or "").strip()
                    or str(row.get("set_kind") or "").strip().lower() == "work"
                )
            )
            latest_logged_session_incomplete = logged_sets < planned_sets

    return {
        "latest_logged_workout_id": latest_logged_workout_id,
        "latest_logged_session_incomplete": latest_logged_session_incomplete,
        "decision_trace": {
            "interpreter": "resolve_latest_logged_workout_resume_state",
            "version": "v1",
            "inputs": {
                "session_count": len(sessions),
                "performed_log_count": len(performed_logs),
            },
            "outcome": {
                "latest_logged_workout_id": latest_logged_workout_id,
                "latest_logged_session_incomplete": latest_logged_session_incomplete,
            },
        },
    }


def resolve_workout_today_session_selection(
    *,
    sessions: list[dict[str, Any]],
    latest_logged_workout_id: str | None,
    latest_logged_session_incomplete: bool,
    today_iso: str,
    performed_logs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    session_by_id = {
        str(session.get("session_id") or ""): session
        for session in sessions
        if str(session.get("session_id") or "")
    }

    selected_session: dict[str, Any] | None = None
    resume_selected = False
    selection_reason = "no_sessions"

    if latest_logged_workout_id:
        candidate = session_by_id.get(str(latest_logged_workout_id))
        if candidate is not None and latest_logged_session_incomplete:
            selected_session = candidate
            resume_selected = True
            selection_reason = "resume_incomplete_session"

    if selected_session is None:
        log_rows = list(performed_logs or [])
        log_counts: dict[str, int] = {}
        for row in log_rows:
            workout_id = str(row.get("workout_id") or "")
            if not workout_id:
                continue
            if row.get("parent_set_index") is not None:
                continue
            set_kind = str(row.get("set_kind") or "").strip().lower()
            if set_kind and set_kind != "work":
                continue
            log_counts[workout_id] = log_counts.get(workout_id, 0) + 1

        def _planned_set_count(session: dict[str, Any]) -> int:
            return sum(int(exercise.get("sets", 3) or 3) for exercise in session.get("exercises", []))

        queue_candidate = None
        for session in sessions:
            session_id = str(session.get("session_id") or "")
            if not session_id:
                continue
            planned_sets = _planned_set_count(session)
            logged_sets = log_counts.get(session_id, 0)
            if logged_sets < planned_sets:
                queue_candidate = session
                break

        if queue_candidate is not None:
            selected_session = queue_candidate
            selection_reason = "queue_next_incomplete_session"

    if selected_session is None and sessions:
        selected_session = sessions[0]
        selection_reason = "first_session_fallback"

    return {
        "selected_session": selected_session,
        "resume_selected": resume_selected,
        "selection_reason": selection_reason,
        "decision_trace": {
            "interpreter": "resolve_workout_today_session_selection",
            "version": "v1",
            "inputs": {
                "session_count": len(sessions),
                "latest_logged_workout_id": latest_logged_workout_id,
                "latest_logged_session_incomplete": latest_logged_session_incomplete,
                "today_iso": today_iso,
                "performed_log_count": len(performed_logs or []),
            },
            "outcome": {
                "selected_session_id": str(_coerce_dict(selected_session).get("session_id") or "") or None,
                "resume_selected": resume_selected,
                "selection_reason": selection_reason,
            },
        },
    }

def _resolve_rep_range(rep_range: Any) -> tuple[int, int]:
    if not isinstance(rep_range, list):
        return 8, 12
    minimum = int(rep_range[0]) if len(rep_range) > 0 else 8
    maximum = int(rep_range[1]) if len(rep_range) > 1 else minimum
    if minimum > maximum:
        minimum, maximum = maximum, minimum
    return minimum, maximum

def prepare_workout_log_set_request_runtime(
    *,
    primary_exercise_id: str | None,
    exercise_id: str,
    set_index: int,
    reps: int,
    weight: float,
    rpe: float | None,
    set_kind: str | None = None,
    parent_set_index: int | None = None,
    technique: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_primary_exercise_id = primary_exercise_id or exercise_id
    return {
        "primary_exercise_id": resolved_primary_exercise_id,
        "exercise_id": exercise_id,
        "set_index": set_index,
        "reps": reps,
        "weight": weight,
        "rpe": rpe,
        "set_kind": set_kind,
        "parent_set_index": parent_set_index,
        "technique": deepcopy(_coerce_dict(technique)) if technique is not None else None,
    }

def resolve_workout_log_set_plan_context(
    *,
    planned_exercise: dict[str, Any] | None,
    fallback_weight: float,
) -> dict[str, Any]:
    exercise = _coerce_dict(planned_exercise)
    planned_reps_min, planned_reps_max = _resolve_rep_range(exercise.get("rep_range"))
    planned_sets = int(exercise.get("sets", 3) or 3)
    planned_weight = float(exercise.get("recommended_working_weight", fallback_weight) or fallback_weight)
    return {
        "planned_reps_min": planned_reps_min,
        "planned_reps_max": planned_reps_max,
        "planned_sets": planned_sets,
        "planned_weight": planned_weight,
    }

def build_workout_session_state_defaults(
    *,
    primary_exercise_id: str,
    planned_sets: int,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
) -> dict[str, Any]:
    return {
        "primary_exercise_id": primary_exercise_id,
        "planned_sets": planned_sets,
        "planned_reps_min": planned_reps_min,
        "planned_reps_max": planned_reps_max,
        "planned_weight": planned_weight,
        "completed_sets": 0,
        "total_logged_reps": 0,
        "total_logged_weight": 0.0,
        "set_history": [],
        "remaining_sets": planned_sets,
        "recommended_reps_min": planned_reps_min,
        "recommended_reps_max": planned_reps_max,
        "recommended_weight": planned_weight,
        "last_guidance": "remaining_sets_hold_load_and_match_target_reps",
    }

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
    load_semantics: str | None = None,
    substitution_recommendation: dict[str, Any] | None,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    reduction = resolve_workout_session_state_update(
        existing_set_history=list(_read_attr(existing_state, "set_history") or []),
        primary_exercise_id=primary_exercise_id,
        planned_sets=planned_sets,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
        set_index=set_index,
        reps=reps,
        weight=weight,
        load_semantics=load_semantics,
        substitution_recommendation=substitution_recommendation,
        rule_set=rule_set,
    )
    return {
        "state": deepcopy(_coerce_dict(reduction.get("state"))),
        "live_recommendation": deepcopy(_coerce_dict(reduction.get("live_recommendation"))),
    }

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
    load_semantics: str | None = None,
    substitution_recommendation: dict[str, Any] | None,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    create_values: dict[str, Any] | None = None
    if existing_state is None:
        create_values = build_workout_session_state_defaults(
            primary_exercise_id=primary_exercise_id,
            planned_sets=planned_sets,
            planned_reps_min=planned_reps_min,
            planned_reps_max=planned_reps_max,
            planned_weight=planned_weight,
        )

    reduction = prepare_workout_session_state_persistence_payload(
        existing_state=existing_state,
        primary_exercise_id=primary_exercise_id,
        planned_sets=planned_sets,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
        set_index=set_index,
        reps=reps,
        weight=weight,
        load_semantics=load_semantics,
        substitution_recommendation=substitution_recommendation,
        rule_set=rule_set,
    )
    update_values = _coerce_dict(reduction.get("state"))
    live_recommendation = _coerce_dict(reduction.get("live_recommendation"))
    return {
        "create_values": deepcopy(create_values),
        "update_values": update_values,
        "live_recommendation": live_recommendation,
        "decision_trace": {
            "interpreter": "prepare_workout_session_state_upsert_runtime",
            "version": "v1",
            "inputs": {
                "has_existing_state": existing_state is not None,
                "primary_exercise_id": primary_exercise_id,
                "planned_sets": planned_sets,
                "planned_reps_min": planned_reps_min,
                "planned_reps_max": planned_reps_max,
            },
            "outcome": {
                "created_state_defaults": create_values is not None,
                "completed_sets": int(update_values.get("completed_sets") or 0),
                "remaining_sets": int(update_values.get("remaining_sets") or 0),
                "guidance": str(live_recommendation.get("guidance") or ""),
            },
        },
    }

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
    log_set_plan_context = resolve_workout_log_set_plan_context(
        planned_exercise=planned_exercise,
        fallback_weight=float(request_runtime["weight"]),
    )
    planned_reps_min = int(log_set_plan_context["planned_reps_min"])
    planned_reps_max = int(log_set_plan_context["planned_reps_max"])
    planned_sets = int(log_set_plan_context["planned_sets"])
    planned_weight = float(log_set_plan_context["planned_weight"])
    primary_exercise_id = str(request_runtime["primary_exercise_id"])
    exercise_id = str(request_runtime["exercise_id"])
    set_index = int(request_runtime["set_index"])
    reps = int(request_runtime["reps"])
    weight = float(request_runtime["weight"])

    exercise_state_runtime = prepare_workout_exercise_state_runtime(
        existing_state=existing_exercise_state,
        primary_exercise_id=primary_exercise_id,
        planned_exercise=planned_exercise,
        planned_weight=planned_weight,
        planned_sets=planned_sets,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        completed_set_index=set_index,
        completed_reps=reps,
        nutrition_phase=nutrition_phase,
        equipment_profile=equipment_profile,
        rule_set=rule_set,
        set_kind=cast(str | None, request_runtime.get("set_kind")),
        parent_set_index=cast(int | None, request_runtime.get("parent_set_index")),
    )
    next_working_weight = float(_coerce_dict(exercise_state_runtime["state_values"])["current_working_weight"])
    feedback = interpret_workout_set_feedback(
        reps=reps,
        weight=weight,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
        next_working_weight=next_working_weight,
        rule_set=rule_set,
    )
    initial_state_values = _coerce_dict(exercise_state_runtime["initial_state_values"])
    state_values = _coerce_dict(exercise_state_runtime["state_values"])
    starting_load_runtime = cast(dict[str, Any] | None, exercise_state_runtime["starting_load_runtime"])
    substitution_recommendation = cast(dict[str, Any] | None, exercise_state_runtime["substitution_recommendation"])
    return {
        "record_values": {
            "user_id": user_id,
            "workout_id": workout_id,
            "primary_exercise_id": primary_exercise_id,
            "exercise_id": exercise_id,
            "set_index": set_index,
            "reps": reps,
            "weight": weight,
            "rpe": request_runtime.get("rpe"),
            "set_kind": request_runtime.get("set_kind"),
            "parent_set_index": request_runtime.get("parent_set_index"),
            "technique": deepcopy(_coerce_dict(request_runtime.get("technique")))
            if request_runtime.get("technique") is not None
            else None,
        },
        "planned_reps_min": planned_reps_min,
        "planned_reps_max": planned_reps_max,
        "planned_sets": planned_sets,
        "planned_weight": planned_weight,
        "exercise_state_runtime": exercise_state_runtime,
        "exercise_state_create_values": {
            "user_id": user_id,
            "exercise_id": primary_exercise_id,
            **initial_state_values,
        },
        "exercise_state_update_values": state_values,
        "starting_load_runtime": deepcopy(starting_load_runtime),
        "substitution_recommendation": deepcopy(substitution_recommendation),
        "feedback": feedback,
        "session_state_inputs": {
            "primary_exercise_id": primary_exercise_id,
            "exercise_id": exercise_id,
            "planned_sets": planned_sets,
            "planned_rep_range": (planned_reps_min, planned_reps_max),
            "planned_weight": planned_weight,
            "set_index": set_index,
            "reps": reps,
            "weight": weight,
            "substitution_recommendation": substitution_recommendation,
            "rule_set": rule_set,
        },
        "decision_trace": {
            "interpreter": "prepare_workout_log_set_decision_runtime",
            "version": "v1",
            "inputs": {
                "user_id": user_id,
                "workout_id": workout_id,
                "primary_exercise_id": primary_exercise_id,
                "exercise_id": exercise_id,
                "set_index": set_index,
                "reps": reps,
                "weight": weight,
                "has_existing_exercise_state": existing_exercise_state is not None,
            },
            "outcome": {
                "planned_reps_min": planned_reps_min,
                "planned_reps_max": planned_reps_max,
                "planned_sets": planned_sets,
                "planned_weight": planned_weight,
                "next_working_weight": next_working_weight,
                "guidance": str(_coerce_dict(feedback).get("guidance") or ""),
                "has_starting_load_runtime": starting_load_runtime is not None,
                "has_substitution_recommendation": substitution_recommendation is not None,
            },
        },
    }

def build_workout_today_log_runtime(
    *,
    recent_logs: list[Any],
    selected_session_logs: list[Any],
) -> dict[str, Any]:
    resume_logs = [
        {
            "workout_id": str(_read_attr(row, "workout_id") or ""),
            "set_kind": str(_read_attr(row, "set_kind") or "") or None,
            "parent_set_index": _read_attr(row, "parent_set_index"),
        }
        for row in recent_logs
        if str(_read_attr(row, "workout_id") or "")
    ]
    completion_logs = [
        {
            "exercise_id": str(_read_attr(row, "exercise_id") or ""),
            "set_index": int(_read_attr(row, "set_index") or 0),
            "set_kind": str(_read_attr(row, "set_kind") or "") or None,
            "parent_set_index": _read_attr(row, "parent_set_index"),
        }
        for row in selected_session_logs
        if str(_read_attr(row, "exercise_id") or "")
    ]
    return {
        "resume_logs": resume_logs,
        "completion_logs": completion_logs,
        "decision_trace": {
            "interpreter": "build_workout_today_log_runtime",
            "version": "v1",
            "inputs": {
                "recent_log_count": len(recent_logs),
                "selected_session_log_count": len(selected_session_logs),
            },
            "outcome": {
                "resume_log_count": len(resume_logs),
                "completion_log_count": len(completion_logs),
            },
        },
    }

def build_workout_summary_progression_lookup_runtime(
    *,
    planned_session: dict[str, Any] | None,
) -> dict[str, Any]:
    session = _coerce_dict(planned_session)
    primary_exercise_ids: list[str] = []
    seen: set[str] = set()
    for exercise in session.get("exercises") or []:
        if not isinstance(exercise, dict):
            continue
        normalized = str(exercise.get("primary_exercise_id") or exercise.get("id") or "")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        primary_exercise_ids.append(normalized)

    return {
        "primary_exercise_ids": primary_exercise_ids,
        "decision_trace": {
            "interpreter": "build_workout_summary_progression_lookup_runtime",
            "version": "v1",
            "inputs": {
                "planned_exercise_count": len(
                    [exercise for exercise in session.get("exercises") or [] if isinstance(exercise, dict)]
                ),
            },
            "outcome": {
                "primary_exercise_id_count": len(primary_exercise_ids),
            },
        },
    }

def build_workout_today_progression_lookup_runtime(
    *,
    session_states: list[Any],
) -> dict[str, Any]:
    primary_exercise_ids: list[str] = []
    seen: set[str] = set()
    for row in session_states:
        normalized = str(_read_attr(row, "primary_exercise_id") or "")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        primary_exercise_ids.append(normalized)

    return {
        "primary_exercise_ids": primary_exercise_ids,
        "decision_trace": {
            "interpreter": "build_workout_today_progression_lookup_runtime",
            "version": "v1",
            "inputs": {
                "session_state_count": len(session_states),
            },
            "outcome": {
                "primary_exercise_id_count": len(primary_exercise_ids),
            },
        },
    }

def build_workout_today_session_state_payloads(
    *,
    session_states: list[Any],
    planned_session: dict[str, Any],
    progression_states: list[Any],
    equipment_profile: list[str] | None,
    rule_set: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    planned_exercise_by_id = {
        str(_coerce_dict(exercise).get("id") or ""): _coerce_dict(exercise)
        for exercise in planned_session.get("exercises") or []
        if str(_coerce_dict(exercise).get("id") or "")
    }
    progression_state_by_exercise = {
        str(_read_attr(row, "exercise_id") or ""): row
        for row in progression_states
        if str(_read_attr(row, "exercise_id") or "")
    }

    payloads: list[dict[str, Any]] = []
    for row in session_states:
        exercise_id = str(_read_attr(row, "exercise_id") or "")
        primary_exercise_id = str(_read_attr(row, "primary_exercise_id") or "")
        substitution_recommendation = build_repeat_failure_substitution_payload(
            planned_exercise=planned_exercise_by_id.get(exercise_id),
            exercise_state=progression_state_by_exercise.get(primary_exercise_id),
            equipment_profile=equipment_profile,
            rule_set=rule_set,
        )
        payloads.append(
            {
                "exercise_id": exercise_id,
                "completed_sets": int(_read_attr(row, "completed_sets") or 0),
                "remaining_sets": int(_read_attr(row, "remaining_sets") or 0),
                "recommended_reps_min": int(_read_attr(row, "recommended_reps_min") or 0),
                "recommended_reps_max": int(_read_attr(row, "recommended_reps_max") or 0),
                "recommended_weight": float(_read_attr(row, "recommended_weight") or 0),
                "last_guidance": str(_read_attr(row, "last_guidance") or ""),
                "substitution_recommendation": substitution_recommendation,
            }
        )

    return payloads

def build_workout_today_state_payloads(
    *,
    session_states: list[dict[str, Any]],
    completed_sets_by_exercise: dict[str, int],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    merged_completed_sets = dict(completed_sets_by_exercise)
    live_recommendations_by_exercise: dict[str, dict[str, Any]] = {}

    for state in session_states:
        exercise_id = str(state.get("exercise_id") or "")
        if not exercise_id:
            continue
        merged_completed_sets[exercise_id] = int(state.get("completed_sets") or 0)
        live_recommendations_by_exercise[exercise_id] = hydrate_live_workout_recommendation(
            completed_sets=int(state.get("completed_sets") or 0),
            remaining_sets=int(state.get("remaining_sets") or 0),
            recommended_reps_min=int(state.get("recommended_reps_min") or 0),
            recommended_reps_max=int(state.get("recommended_reps_max") or 0),
            recommended_weight=float(state.get("recommended_weight") or 0),
            guidance=str(state.get("last_guidance") or ""),
            substitution_recommendation=_coerce_dict(state.get("substitution_recommendation")) or None,
            rule_set=rule_set,
        )

    return {
        "completed_sets_by_exercise": merged_completed_sets,
        "live_recommendations_by_exercise": live_recommendations_by_exercise,
    }

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
    payload = dict(selected_session)
    exercises: list[dict[str, Any]] = []

    for raw_exercise in selected_session.get("exercises") or []:
        exercise = dict(_coerce_dict(raw_exercise))
        exercise_id = str(exercise.get("id") or "")
        # Align scheduled sets to authored working_sets minimum so prescription and counts match
        authored_working = exercise.get("working_sets")
        if authored_working is not None:
            try:
                min_sets = max(1, int(float(str(authored_working))))
                current_sets = int(exercise.get("sets", 0) or 0)
                if current_sets < min_sets:
                    exercise["sets"] = min_sets
            except (TypeError, ValueError):
                pass
        recommended_weight = float(exercise.get("recommended_working_weight", 20) or 20)
        exercise["warmups"] = compute_warmups(recommended_weight, 3)
        exercise["completed_sets"] = int(completed_sets_by_exercise.get(exercise_id, 0) or 0)

        live_recommendation = live_recommendations_by_exercise.get(exercise_id)
        if isinstance(live_recommendation, dict):
            exercise["live_recommendation"] = dict(live_recommendation)

        exercises.append(exercise)

    payload["exercises"] = exercises
    payload["mesocycle"] = _coerce_dict(mesocycle) if mesocycle is not None else mesocycle
    payload["deload"] = _coerce_dict(deload) if deload is not None else deload
    payload["resume"] = resume_selected
    payload["daily_quote"] = dict(_coerce_dict(daily_quote))
    return payload

def prepare_workout_today_plan_route_runtime(
    *,
    plan_rows: list[Any],
) -> dict[str, Any]:
    plan_source = resolve_workout_today_plan_payload(plan_rows=plan_rows)
    plan_runtime = build_workout_today_plan_runtime(
        latest_plan_payload=_coerce_dict(plan_source.get("latest_plan_payload"))
    )
    return {
        "has_plan": bool(plan_source.get("has_plan")),
        "sessions": list(plan_runtime.get("sessions") or []),
        "session_ids": list(plan_runtime.get("session_ids") or []),
        "selected_program_id": plan_runtime.get("selected_program_id"),
        "mesocycle": deepcopy(plan_runtime.get("mesocycle")),
        "deload": deepcopy(plan_runtime.get("deload")),
        "decision_trace": {
            "interpreter": "prepare_workout_today_plan_route_runtime",
            "version": "v1",
            "inputs": {
                "plan_row_count": len(plan_rows),
            },
            "plan_source_trace": deepcopy(_coerce_dict(plan_source.get("decision_trace"))),
            "plan_runtime_trace": deepcopy(_coerce_dict(plan_runtime.get("decision_trace"))),
            "outcome": {
                "has_plan": bool(plan_source.get("has_plan")),
                "session_id_count": len(plan_runtime.get("session_ids") or []),
                "selected_program_id": plan_runtime.get("selected_program_id"),
            },
        },
    }


def prepare_workout_today_progression_route_runtime(
    *,
    session_states: list[Any],
    selected_program_id: str | None,
    resolve_linked_program_id: Callable[[str], str | None],
    load_rule_set: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    progression_lookup_runtime = build_workout_today_progression_lookup_runtime(
        session_states=session_states,
    )
    primary_exercise_ids = list(progression_lookup_runtime.get("primary_exercise_ids") or [])
    rule_set = resolve_optional_rule_set(
        template_id=selected_program_id,
        resolve_linked_program_id=resolve_linked_program_id,
        load_rule_set=load_rule_set,
    )
    return {
        "primary_exercise_ids": primary_exercise_ids,
        "rule_set": deepcopy(rule_set),
        "decision_trace": {
            "interpreter": "prepare_workout_today_progression_route_runtime",
            "version": "v1",
            "inputs": {
                "selected_program_id": selected_program_id,
                "session_state_count": len(session_states),
            },
            "progression_lookup_trace": deepcopy(_coerce_dict(progression_lookup_runtime.get("decision_trace"))),
            "outcome": {
                "primary_exercise_id_count": len(primary_exercise_ids),
                "has_rule_set": isinstance(rule_set, dict),
            },
        },
    }


def prepare_workout_today_selection_route_runtime(
    *,
    sessions: list[dict[str, Any]],
    recent_logs: list[Any],
    today_iso: str,
) -> dict[str, Any]:
    log_runtime = build_workout_today_log_runtime(
        recent_logs=recent_logs,
        selected_session_logs=[],
    )
    resume_runtime = resolve_latest_logged_workout_resume_state(
        sessions=sessions,
        performed_logs=list(log_runtime.get("resume_logs") or []),
    )
    selection = resolve_workout_today_session_selection(
        sessions=sessions,
        latest_logged_workout_id=resume_runtime.get("latest_logged_workout_id"),
        latest_logged_session_incomplete=bool(resume_runtime.get("latest_logged_session_incomplete")),
        today_iso=today_iso,
        performed_logs=list(log_runtime.get("resume_logs") or []),
    )
    selected_session = _coerce_dict(selection.get("selected_session"))
    selected_session_id = str(selected_session.get("session_id") or "").strip() or None
    return {
        "selected_session": selected_session,
        "selected_session_id": selected_session_id,
        "resume_selected": bool(selection.get("resume_selected")),
        "selection_reason": str(selection.get("selection_reason") or ""),
        "decision_trace": {
            "interpreter": "prepare_workout_today_selection_route_runtime",
            "version": "v1",
            "inputs": {
                "session_count": len(sessions),
                "today_iso": today_iso,
            },
            "log_runtime_trace": deepcopy(_coerce_dict(log_runtime.get("decision_trace"))),
            "resume_runtime_trace": deepcopy(_coerce_dict(resume_runtime.get("decision_trace"))),
            "selection_trace": deepcopy(_coerce_dict(selection.get("decision_trace"))),
            "steps": [
                {
                    "decision": "resolve_resume_context",
                    "result": {
                        "latest_logged_workout_id": resume_runtime.get("latest_logged_workout_id"),
                        "latest_logged_session_incomplete": bool(
                            resume_runtime.get("latest_logged_session_incomplete")
                        ),
                    },
                },
                {
                    "decision": "select_session",
                    "result": {
                        "selection_reason": str(selection.get("selection_reason") or ""),
                        "resume_selected": bool(selection.get("resume_selected")),
                    },
                },
            ],
            "outcome": {
                "selected_session_id": selected_session_id,
                "resume_selected": bool(selection.get("resume_selected")),
                "selection_reason": str(selection.get("selection_reason") or ""),
            },
        },
    }


def prepare_workout_log_set_context_route_runtime(
    *,
    workout_id: str,
    plan_rows: list[Any],
    primary_exercise_id: str | None,
    exercise_id: str,
    set_index: int,
    reps: int,
    weight: float,
    rpe: float | None,
    set_kind: str | None = None,
    parent_set_index: int | None = None,
    technique: dict[str, Any] | None = None,
    resolve_linked_program_id: Callable[[str], str | None],
    load_rule_set: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    request_runtime = prepare_workout_log_set_request_runtime(
        primary_exercise_id=primary_exercise_id,
        exercise_id=exercise_id,
        set_index=set_index,
        reps=reps,
        weight=weight,
        rpe=rpe,
        set_kind=set_kind,
        parent_set_index=parent_set_index,
        technique=technique,
    )
    plan_context = resolve_workout_plan_context(
        plan_rows=plan_rows,
        workout_id=workout_id,
        exercise_id=str(request_runtime.get("exercise_id") or ""),
    )
    program_id = plan_context.get("program_id")
    rule_set = resolve_optional_rule_set(
        template_id=program_id,
        resolve_linked_program_id=resolve_linked_program_id,
        load_rule_set=load_rule_set,
    )
    resolved_primary_exercise_id = str(request_runtime.get("primary_exercise_id") or "")
    planned_exercise = _coerce_dict(plan_context.get("exercise")) or None
    return {
        "request_runtime": request_runtime,
        "primary_exercise_id": resolved_primary_exercise_id,
        "planned_exercise": deepcopy(planned_exercise),
        "program_id": program_id,
        "rule_set": deepcopy(rule_set),
        "decision_trace": {
            "interpreter": "prepare_workout_log_set_context_route_runtime",
            "version": "v1",
            "inputs": {
                "workout_id": workout_id,
                "exercise_id": exercise_id,
                "set_index": int(set_index),
                "reps": int(reps),
                "weight": float(weight),
                "has_primary_exercise_id": primary_exercise_id is not None,
                "plan_row_count": len(plan_rows),
            },
            "outcome": {
                "primary_exercise_id": resolved_primary_exercise_id,
                "program_id": program_id,
                "has_planned_exercise": planned_exercise is not None,
                "has_rule_set": isinstance(rule_set, dict),
            },
        },
    }


def prepare_workout_log_set_decision_route_runtime(
    *,
    user_id: str,
    workout_id: str,
    existing_exercise_state: Any | None,
    request_runtime: dict[str, Any],
    planned_exercise: dict[str, Any] | None,
    nutrition_phase: str | None,
    equipment_profile: list[str] | None,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    runtime = prepare_workout_log_set_decision_runtime(
        user_id=user_id,
        workout_id=workout_id,
        request_runtime=request_runtime,
        planned_exercise=planned_exercise,
        existing_exercise_state=existing_exercise_state,
        nutrition_phase=nutrition_phase,
        equipment_profile=equipment_profile,
        rule_set=rule_set,
    )
    return {
        **runtime,
        "decision_trace": {
            "interpreter": "prepare_workout_log_set_decision_route_runtime",
            "version": "v1",
            "inputs": {
                "user_id": user_id,
                "workout_id": workout_id,
                "has_existing_exercise_state": existing_exercise_state is not None,
                "has_planned_exercise": planned_exercise is not None,
                "has_rule_set": isinstance(rule_set, dict),
            },
            "log_set_runtime_trace": deepcopy(_coerce_dict(runtime.get("decision_trace"))),
            "outcome": {
                "planned_sets": int(runtime.get("planned_sets") or 0),
                "planned_reps_min": int(runtime.get("planned_reps_min") or 0),
                "planned_reps_max": int(runtime.get("planned_reps_max") or 0),
                "has_starting_load_runtime": runtime.get("starting_load_runtime") is not None,
            },
        },
    }


def prepare_workout_session_state_route_runtime(
    *,
    existing_state: Any | None,
    user_id: str,
    workout_id: str,
    exercise_id: str,
    primary_exercise_id: str,
    planned_sets: int,
    planned_rep_range: tuple[int, int],
    planned_weight: float,
    set_index: int,
    reps: int,
    weight: float,
    load_semantics: str | None = None,
    substitution_recommendation: dict[str, Any] | None,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    planned_reps_min, planned_reps_max = planned_rep_range
    upsert_runtime = prepare_workout_session_state_upsert_runtime(
        existing_state=existing_state,
        primary_exercise_id=primary_exercise_id,
        planned_sets=planned_sets,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
        set_index=set_index,
        reps=reps,
        weight=weight,
        load_semantics=load_semantics,
        substitution_recommendation=substitution_recommendation,
        rule_set=rule_set,
    )
    create_values = _coerce_dict(upsert_runtime.get("create_values"))
    if create_values:
        create_values = {
            "user_id": user_id,
            "workout_id": workout_id,
            "exercise_id": exercise_id,
            **create_values,
        }
    return {
        "create_values": deepcopy(create_values) if create_values else None,
        "update_values": deepcopy(_coerce_dict(upsert_runtime.get("update_values"))),
        "live_recommendation": deepcopy(_coerce_dict(upsert_runtime.get("live_recommendation"))),
        "decision_trace": {
            "interpreter": "prepare_workout_session_state_route_runtime",
            "version": "v1",
            "inputs": {
                "user_id": user_id,
                "workout_id": workout_id,
                "exercise_id": exercise_id,
                "has_existing_state": existing_state is not None,
            },
            "upsert_runtime_trace": deepcopy(_coerce_dict(upsert_runtime.get("decision_trace"))),
            "outcome": {
                "created_state_defaults": create_values is not None,
                "completed_sets": int(_coerce_dict(upsert_runtime.get("update_values")).get("completed_sets") or 0),
                "remaining_sets": int(_coerce_dict(upsert_runtime.get("update_values")).get("remaining_sets") or 0),
            },
        },
    }


def prepare_workout_log_set_response_runtime(
    *,
    record: Any,
    decision_runtime: dict[str, Any],
    live_recommendation: dict[str, Any],
) -> dict[str, Any]:
    starting_load_runtime = _coerce_dict(decision_runtime.get("starting_load_runtime")) or None
    response_payload = build_workout_log_set_payload(
        record_id=str(_read_attr(record, "id") or ""),
        primary_exercise_id=str(_read_attr(record, "primary_exercise_id") or ""),
        exercise_id=str(_read_attr(record, "exercise_id") or ""),
        set_index=int(_read_attr(record, "set_index") or 0),
        reps=int(_read_attr(record, "reps") or 0),
        weight=float(_read_attr(record, "weight") or 0),
        set_kind=str(_read_attr(record, "set_kind") or "") or None,
        parent_set_index=(
            int(_read_attr(record, "parent_set_index"))
            if _read_attr(record, "parent_set_index") is not None
            else None
        ),
        technique=_coerce_dict(_read_attr(record, "technique")) or None,
        planned_reps_min=int(decision_runtime.get("planned_reps_min") or 0),
        planned_reps_max=int(decision_runtime.get("planned_reps_max") or 0),
        planned_weight=float(decision_runtime.get("planned_weight") or 0),
        feedback=_coerce_dict(decision_runtime.get("feedback")),
        starting_load_decision_trace=(
            deepcopy(_coerce_dict(starting_load_runtime.get("decision_trace"))) if starting_load_runtime else None
        ),
        live_recommendation=live_recommendation,
        created_at=_read_attr(record, "created_at"),
    )
    return {
        "response_payload": response_payload,
        "decision_trace": {
            "interpreter": "prepare_workout_log_set_response_runtime",
            "version": "v1",
            "inputs": {
                "record_id": str(_read_attr(record, "id") or ""),
                "has_starting_load_runtime": starting_load_runtime is not None,
            },
            "outcome": {
                "guidance": str(response_payload.get("guidance") or ""),
                "has_live_recommendation": isinstance(response_payload.get("live_recommendation"), dict),
            },
        },
    }


def prepare_workout_today_response_runtime(
    *,
    selected_session: dict[str, Any],
    selected_session_logs: list[Any],
    session_states: list[Any],
    progression_states: list[Any],
    equipment_profile: list[str] | None,
    rule_set: dict[str, Any] | None,
    mesocycle: dict[str, Any] | None,
    deload: dict[str, Any] | None,
    resume_selected: bool,
    daily_quote: dict[str, Any],
) -> dict[str, Any]:
    normalized_session_logs = list(selected_session_logs)
    normalized_session_states = list(session_states)
    normalized_progression_states = list(progression_states)
    log_runtime = build_workout_today_log_runtime(
        recent_logs=[],
        selected_session_logs=normalized_session_logs,
    )
    completed_by_exercise = resolve_workout_completion_per_exercise(
        performed_logs=list(log_runtime.get("completion_logs") or [])
    )
    session_state_payloads = build_workout_today_session_state_payloads(
        session_states=normalized_session_states,
        planned_session=selected_session,
        progression_states=normalized_progression_states,
        equipment_profile=equipment_profile,
        rule_set=rule_set,
    )
    state_payloads = build_workout_today_state_payloads(
        session_states=session_state_payloads,
        completed_sets_by_exercise=completed_by_exercise,
        rule_set=rule_set,
    )
    response_payload = build_workout_today_payload(
        selected_session=selected_session,
        mesocycle=mesocycle,
        deload=deload,
        completed_sets_by_exercise=dict(state_payloads.get("completed_sets_by_exercise") or {}),
        live_recommendations_by_exercise=dict(
            state_payloads.get("live_recommendations_by_exercise") or {}
        ),
        resume_selected=resume_selected,
        daily_quote=daily_quote,
    )
    return {
        "response_payload": response_payload,
        "decision_trace": {
            "interpreter": "prepare_workout_today_response_runtime",
            "version": "v1",
            "inputs": {
                "selected_session_log_count": len(normalized_session_logs),
                "session_state_count": len(normalized_session_states),
                "progression_state_count": len(normalized_progression_states),
                "resume_selected": resume_selected,
            },
            "log_runtime_trace": deepcopy(_coerce_dict(log_runtime.get("decision_trace"))),
            "outcome": {
                "exercise_count": len(response_payload.get("exercises") or []),
                "completed_exercise_count": len(state_payloads.get("completed_sets_by_exercise") or {}),
                "live_recommendation_count": len(
                    state_payloads.get("live_recommendations_by_exercise") or {}
                ),
                "resume_selected": resume_selected,
            },
        },
    }


def prepare_workout_progress_route_runtime(
    *,
    workout_id: str,
    plan_rows: list[Any],
    selected_session_logs: list[Any],
) -> dict[str, Any]:
    log_runtime = build_workout_today_log_runtime(
        recent_logs=[],
        selected_session_logs=selected_session_logs,
    )
    completed_by_exercise = resolve_workout_completion_per_exercise(
        performed_logs=list(log_runtime.get("completion_logs") or [])
    )
    plan_context = resolve_workout_plan_context(
        plan_rows=plan_rows,
        workout_id=workout_id,
    )
    session = _coerce_dict(plan_context.get("session"))
    response_payload = build_workout_progress_payload(
        workout_id=workout_id,
        completed_sets_by_exercise=completed_by_exercise,
        planned_session=session,
    )
    return {
        "response_payload": response_payload,
        "decision_trace": {
            "interpreter": "prepare_workout_progress_route_runtime",
            "version": "v1",
            "inputs": {
                "selected_session_log_count": len(selected_session_logs),
                "has_planned_session": bool(session),
            },
            "log_runtime_trace": deepcopy(_coerce_dict(log_runtime.get("decision_trace"))),
            "outcome": {
                "completed_total": int(response_payload.get("completed_total") or 0),
                "planned_total": int(response_payload.get("planned_total") or 0),
                "percent_complete": int(response_payload.get("percent_complete") or 0),
            },
        },
    }


def prepare_workout_summary_route_runtime(
    *,
    workout_id: str,
    plan_rows: list[Any],
    resolve_linked_program_id: Callable[[str], str | None] | None = None,
    load_rule_set: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    plan_context = resolve_workout_plan_context(
        plan_rows=plan_rows,
        workout_id=workout_id,
    )
    session = _coerce_dict(plan_context.get("session"))
    program_id = plan_context.get("program_id")
    progression_lookup_runtime = build_workout_summary_progression_lookup_runtime(
        planned_session=session,
    )
    rule_set = None
    if resolve_linked_program_id is not None and load_rule_set is not None:
        rule_set = resolve_optional_rule_set(
            template_id=program_id,
            resolve_linked_program_id=resolve_linked_program_id,
            load_rule_set=load_rule_set,
        )
    return {
        "has_session": bool(session),
        "session": session or None,
        "program_id": program_id,
        "rule_set": deepcopy(rule_set),
        "primary_exercise_ids": list(progression_lookup_runtime.get("primary_exercise_ids") or []),
        "decision_trace": {
            "interpreter": "prepare_workout_summary_route_runtime",
            "version": "v1",
            "inputs": {
                "workout_id": workout_id,
                "plan_row_count": len(plan_rows),
                "loads_rule_set": resolve_linked_program_id is not None and load_rule_set is not None,
            },
            "progression_lookup_trace": deepcopy(
                _coerce_dict(progression_lookup_runtime.get("decision_trace"))
            ),
            "outcome": {
                "has_session": bool(session),
                "program_id": program_id,
                "primary_exercise_id_count": len(
                    progression_lookup_runtime.get("primary_exercise_ids") or []
                ),
                "has_rule_set": isinstance(rule_set, dict),
            },
        },
    }


def prepare_workout_summary_response_runtime(
    *,
    workout_id: str,
    planned_session: dict[str, Any],
    performed_logs: list[Any],
    progression_states: list[Any],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    response_payload = build_workout_performance_summary(
        workout_id=workout_id,
        planned_session=planned_session,
        performed_logs=performed_logs,
        progression_states=progression_states,
        rule_set=rule_set,
    )
    return {
        "response_payload": response_payload,
        "decision_trace": {
            "interpreter": "prepare_workout_summary_response_runtime",
            "version": "v1",
            "inputs": {
                "workout_id": workout_id,
                "performed_log_count": len(performed_logs),
                "progression_state_count": len(progression_states),
                "has_rule_set": isinstance(rule_set, dict),
            },
            "outcome": {
                "completed_total": int(response_payload.get("completed_total") or 0),
                "planned_total": int(response_payload.get("planned_total") or 0),
                "percent_complete": int(response_payload.get("percent_complete") or 0),
            },
        },
    }
