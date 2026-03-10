from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from .generation import resolve_optional_rule_set
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
    resolve_latest_logged_workout_resume_state,
    resolve_workout_completion_per_exercise,
    resolve_workout_plan_context,
    resolve_workout_today_plan_payload,
    resolve_workout_today_session_selection,
)


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_attr(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


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
