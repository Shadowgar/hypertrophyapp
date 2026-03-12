from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

from .decision_generated_week import (
    build_generated_week_plan_payload,
)
from .decision_progression import evaluate_stimulus_fatigue_response
from .decision_frequency_adaptation import build_generated_week_adaptation_persistence_payload
from .intelligence import prepare_generated_week_review_overlay
from .scheduler import generate_week_plan


def _read_attr(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _iso_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _coerce_training_state(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): str(item)
        for key, item in value.items()
        if str(key).strip() and str(item).strip()
    }


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _serialize_training_state_history(user_training_state: dict[str, Any]) -> list[dict[str, Any]]:
    performance_history = user_training_state.get("exercise_performance_history") or []
    if not isinstance(performance_history, list):
        return []

    serialized: list[dict[str, Any]] = []
    for entry in performance_history:
        normalized_entry = _read_attr(entry, "performed_at")
        serialized.append(
            {
                "primary_exercise_id": _read_attr(entry, "exercise_id"),
                "exercise_id": _read_attr(entry, "exercise_id"),
                "next_working_weight": _read_attr(entry, "weight"),
                "created_at": normalized_entry.isoformat() if normalized_entry else None,
            }
        )
    return serialized


def _resolve_frequency_adaptation_program(
    *,
    requested_program_id: str | None,
    selected_program_id: str | None,
    training_state_program_id: Any,
    default_program_id: str,
) -> tuple[str, str]:
    resolved_program_id = str(
        requested_program_id
        or selected_program_id
        or training_state_program_id
        or default_program_id
    )
    if requested_program_id:
        return resolved_program_id, "request"
    if selected_program_id:
        return resolved_program_id, "profile"
    if training_state_program_id:
        return resolved_program_id, "training_state"
    return resolved_program_id, "default"


def _resolve_frequency_adaptation_week_index(
    *,
    program_state: dict[str, Any],
    latest_plan: Any | None,
) -> tuple[int, str]:
    if program_state:
        return max(1, int(program_state.get("week_index", 1) or 1)), "training_state"

    latest_payload = _read_attr(latest_plan, "payload", {}) if latest_plan is not None else {}
    latest_payload = latest_payload if isinstance(latest_payload, dict) else {}
    mesocycle = latest_payload.get("mesocycle") if isinstance(latest_payload.get("mesocycle"), dict) else {}
    return max(1, int(mesocycle.get("week_index", 1) or 1)), "latest_plan"


def _resolve_frequency_adaptation_recovery(
    *,
    fatigue_state: dict[str, Any],
    latest_soreness_entry: Any | None,
) -> tuple[str, int, str]:
    recovery_state = str(fatigue_state.get("recovery_state") or "")
    severe_soreness_count = int(fatigue_state.get("severe_soreness_count") or 0)
    if recovery_state:
        return recovery_state, severe_soreness_count, "training_state"

    soreness_by_muscle = _read_attr(latest_soreness_entry, "severity_by_muscle", {}) if latest_soreness_entry else {}
    soreness_by_muscle = soreness_by_muscle if isinstance(soreness_by_muscle, dict) else {}
    severe_soreness_count = sum(
        1 for severity in soreness_by_muscle.values() if str(severity).lower() == "severe"
    )
    recovery_state = "high_fatigue" if severe_soreness_count >= 2 else "normal"
    return recovery_state, severe_soreness_count, "latest_soreness"


def format_program_display_name(program_id: str) -> str:
    normalized = program_id.replace("_v", " v").replace("_", " ").strip()
    return " ".join(part.capitalize() for part in normalized.split())


def resolve_program_display_name(
    *,
    program_id: str,
    available_program_summaries: list[dict[str, Any]],
) -> str:
    match = next((summary for summary in available_program_summaries if summary.get("id") == program_id), None)
    if isinstance(match, dict):
        name = str(match.get("name") or "").strip()
        if name:
            return name
    return format_program_display_name(program_id)


def resolve_optional_rule_set(
    *,
    template_id: str | None,
    resolve_linked_program_id: Callable[[str], str],
    load_rule_set: Callable[[str], dict[str, Any]],
) -> dict[str, Any] | None:
    if not template_id:
        return None
    try:
        return load_rule_set(resolve_linked_program_id(template_id))
    except FileNotFoundError:
        return None


def resolve_onboarding_program_id(
    *,
    template_id: str,
    resolve_linked_program_id: Callable[[str], str],
) -> str:
    return resolve_linked_program_id(template_id)


def resolve_program_guide_summary(
    *,
    program_id: str,
    available_program_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = next((item for item in available_program_summaries if item.get("id") == program_id), None)
    if summary is None:
        raise FileNotFoundError(f"Program template not found: {program_id}")
    return summary


def build_guide_programs_payload(available_program_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(item["id"]),
            "name": format_program_display_name(str(item["id"])),
            "split": str(item["split"]),
            "days_supported": list(item.get("days_supported") or []),
            "description": str(item.get("description") or ""),
        }
        for item in available_program_summaries
    ]


def build_program_guide_payload(
    *,
    program_id: str,
    program_summary: dict[str, Any],
    template: dict[str, Any],
) -> dict[str, Any]:
    sessions = template.get("sessions") or []
    days = [
        {
            "day_index": index,
            "day_name": str(session.get("name") or f"Day {index}"),
            "exercise_count": len(session.get("exercises") or []),
            "first_exercise_id": (session.get("exercises") or [{}])[0].get("id") if (session.get("exercises") or []) else None,
        }
        for index, session in enumerate(sessions, start=1)
    ]
    return {
        "id": program_id,
        "name": format_program_display_name(program_id),
        "description": str(program_summary.get("description") or ""),
        "split": str(program_summary.get("split") or ""),
        "days_supported": list(program_summary.get("days_supported") or []),
        "days": days,
    }


def build_program_day_guide_payload(
    *,
    program_id: str,
    template: dict[str, Any],
    day_index: int,
) -> dict[str, Any]:
    sessions = template.get("sessions") or []
    if day_index < 1 or day_index > len(sessions):
        raise IndexError("day index out of range")

    session = sessions[day_index - 1]
    exercises = [
        {
            "id": str(exercise.get("id", "")),
            "primary_exercise_id": exercise.get("primary_exercise_id"),
            "name": str(exercise.get("name", "")),
            "notes": exercise.get("notes"),
            "video_youtube_url": (exercise.get("video") or {}).get("youtube_url") if isinstance(exercise.get("video"), dict) else None,
        }
        for exercise in session.get("exercises") or []
    ]
    return {
        "program_id": program_id,
        "day_index": day_index,
        "day_name": str(session.get("name") or f"Day {day_index}"),
        "exercises": exercises,
    }


def resolve_program_exercise_guide(
    *,
    template: dict[str, Any],
    exercise_id: str,
) -> dict[str, Any] | None:
    sessions = template.get("sessions") or []
    for session in sessions:
        for exercise in session.get("exercises") or []:
            if exercise.get("id") == exercise_id or exercise.get("primary_exercise_id") == exercise_id:
                return {
                    "id": str(exercise.get("id", "")),
                    "primary_exercise_id": exercise.get("primary_exercise_id"),
                    "name": str(exercise.get("name", "")),
                    "notes": exercise.get("notes"),
                    "video_youtube_url": (exercise.get("video") or {}).get("youtube_url") if isinstance(exercise.get("video"), dict) else None,
                }
    return None


def build_program_exercise_guide_payload(
    *,
    program_id: str,
    exercise: dict[str, Any],
) -> dict[str, Any]:
    return {
        "program_id": program_id,
        "exercise": dict(exercise),
    }


def serialize_recent_training_history(history_rows: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "primary_exercise_id": _read_attr(row, "primary_exercise_id"),
            "exercise_id": _read_attr(row, "exercise_id"),
            "next_working_weight": _read_attr(row, "weight"),
            "created_at": _read_attr(row, "created_at").isoformat() if _read_attr(row, "created_at") else None,
        }
        for row in history_rows
    ]


def build_coach_preview_context(
    *,
    user_name: str | None,
    split_preference: str,
    template: dict[str, Any],
    history_rows: list[Any],
    user_training_state: dict[str, Any] | None = None,
    nutrition_phase: str,
    available_equipment: list[str],
) -> dict[str, Any]:
    normalized_training_state = _coerce_training_state(user_training_state)
    history = _serialize_training_state_history(normalized_training_state)
    if not history:
        history = serialize_recent_training_history(history_rows)

    return {
        "user_profile": {"name": user_name},
        "split_preference": split_preference,
        "program_template": template,
        "history": history,
        "coaching_state": _coerce_dict(normalized_training_state.get("coaching_state")),
        "phase": nutrition_phase,
        "available_equipment": available_equipment,
    }


def prepare_coach_preview_runtime_inputs(
    *,
    preview_request: dict[str, Any],
    profile_days_available: int | None,
) -> dict[str, Any]:
    normalized_request = dict(preview_request)
    from_days = int(normalized_request.get("from_days") or 2)
    to_days = int(normalized_request.get("to_days") or 2)
    normalized_request["from_days"] = from_days
    normalized_request["to_days"] = to_days

    profile_days_source = "profile"
    profile_days = profile_days_available
    if not isinstance(profile_days, int) or profile_days <= 0:
        profile_days = from_days
        profile_days_source = "request_from_days_fallback"

    max_requested_days = max(from_days, to_days, profile_days)
    return {
        "preview_request": normalized_request,
        "max_requested_days": int(max_requested_days),
        "decision_trace": {
            "interpreter": "prepare_coach_preview_runtime_inputs",
            "version": "v1",
            "inputs": {
                "from_days": from_days,
                "to_days": to_days,
                "profile_days_available": profile_days_available,
            },
            "steps": [
                {
                    "decision": "profile_days_resolution",
                    "result": {
                        "profile_days": int(profile_days),
                        "source": profile_days_source,
                    },
                },
                {
                    "decision": "max_requested_days",
                    "result": {
                        "max_requested_days": int(max_requested_days),
                    },
                },
            ],
            "outcome": {
                "from_days": from_days,
                "to_days": to_days,
                "profile_days": int(profile_days),
                "max_requested_days": int(max_requested_days),
            },
        },
    }


def resolve_frequency_adaptation_request_context(
    *,
    requested_program_id: str | None,
    selected_program_id: str | None,
    user_training_state: dict[str, Any] | None = None,
    latest_plan: Any | None,
    latest_soreness_entry: Any | None,
    default_program_id: str = "full_body_v1",
) -> dict[str, Any]:
    normalized_training_state = _coerce_training_state(user_training_state)
    program_state = _coerce_dict(normalized_training_state.get("user_program_state"))
    fatigue_state = _coerce_dict(normalized_training_state.get("fatigue_state"))

    resolved_program_id, program_source = _resolve_frequency_adaptation_program(
        requested_program_id=requested_program_id,
        selected_program_id=selected_program_id,
        training_state_program_id=program_state.get("program_id"),
        default_program_id=default_program_id,
    )
    current_week_index, week_index_source = _resolve_frequency_adaptation_week_index(
        program_state=program_state,
        latest_plan=latest_plan,
    )
    recovery_state, severe_soreness_count, recovery_source = _resolve_frequency_adaptation_recovery(
        fatigue_state=fatigue_state,
        latest_soreness_entry=latest_soreness_entry,
    )

    return {
        "program_id": resolved_program_id,
        "current_week_index": current_week_index,
        "recovery_state": recovery_state,
        "decision_trace": {
            "interpreter": "resolve_frequency_adaptation_request_context",
            "version": "v1",
            "inputs": {
                "requested_program_id": requested_program_id,
                "selected_program_id": selected_program_id,
                "has_user_training_state": bool(normalized_training_state),
                "has_latest_plan": latest_plan is not None,
                "has_latest_soreness_entry": latest_soreness_entry is not None,
            },
            "steps": [
                {
                    "decision": "program_resolution",
                    "result": {
                        "program_id": resolved_program_id,
                        "source": program_source,
                    },
                },
                {
                    "decision": "current_week_index",
                    "result": {
                        "current_week_index": current_week_index,
                        "source": week_index_source,
                    },
                },
                {
                    "decision": "recovery_state",
                    "result": {
                        "recovery_state": recovery_state,
                        "severe_soreness_count": severe_soreness_count,
                        "source": recovery_source,
                    },
                },
            ],
            "outcome": {
                "program_id": resolved_program_id,
                "current_week_index": current_week_index,
                "recovery_state": recovery_state,
            },
        },
    }


def prepare_frequency_adaptation_runtime_inputs(
    *,
    requested_program_id: str | None,
    selected_program_id: str | None,
    user_training_state: dict[str, Any] | None,
    current_days_available: int,
    target_days: int,
    duration_weeks: int,
    explicit_weak_areas: list[str],
    stored_weak_areas: list[str],
    equipment_profile: list[str],
) -> dict[str, Any]:
    adaptation_context = resolve_frequency_adaptation_request_context(
        requested_program_id=requested_program_id,
        selected_program_id=selected_program_id,
        user_training_state=user_training_state,
        latest_plan=None,
        latest_soreness_entry=None,
    )

    return {
        "program_id": str(adaptation_context["program_id"]),
        "current_days": int(current_days_available),
        "target_days": int(target_days),
        "duration_weeks": int(duration_weeks),
        "explicit_weak_areas": list(explicit_weak_areas),
        "stored_weak_areas": list(stored_weak_areas),
        "equipment_profile": list(equipment_profile),
        "recovery_state": str(adaptation_context["recovery_state"]),
        "current_week_index": int(adaptation_context["current_week_index"]),
        "context_trace": _coerce_dict(adaptation_context.get("decision_trace")),
        "decision_trace": {
            "interpreter": "prepare_frequency_adaptation_runtime_inputs",
            "version": "v1",
            "inputs": {
                "requested_program_id": requested_program_id,
                "selected_program_id": selected_program_id,
                "has_user_training_state": bool(_coerce_training_state(user_training_state)),
                "current_days_available": int(current_days_available),
                "target_days": int(target_days),
                "duration_weeks": int(duration_weeks),
                "explicit_weak_area_count": len(explicit_weak_areas),
                "stored_weak_area_count": len(stored_weak_areas),
                "equipment_profile_count": len(equipment_profile),
            },
            "outcome": {
                "program_id": str(adaptation_context["program_id"]),
                "recovery_state": str(adaptation_context["recovery_state"]),
                "current_week_index": int(adaptation_context["current_week_index"]),
            },
        },
    }


def prepare_frequency_adaptation_decision_runtime(
    *,
    requested_program_id: str | None,
    selected_program_id: str | None,
    latest_plan: Any | None,
    latest_soreness_entry: Any | None,
    current_days_available: int,
    target_days: int,
    duration_weeks: int,
    explicit_weak_areas: list[str],
    stored_weak_areas: list[str],
    equipment_profile: list[str],
    build_plan_decision_training_state: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    training_state = build_plan_decision_training_state(
        selected_program_id=selected_program_id,
        latest_plan=latest_plan,
        latest_soreness_entry=latest_soreness_entry,
    )
    adaptation_runtime = prepare_frequency_adaptation_runtime_inputs(
        requested_program_id=requested_program_id,
        selected_program_id=selected_program_id,
        user_training_state=training_state,
        current_days_available=current_days_available,
        target_days=target_days,
        duration_weeks=duration_weeks,
        explicit_weak_areas=explicit_weak_areas,
        stored_weak_areas=stored_weak_areas,
        equipment_profile=equipment_profile,
    )
    return {
        "training_state": training_state,
        "adaptation_runtime": adaptation_runtime,
        "context_trace": _coerce_dict(adaptation_runtime.get("context_trace")),
        "decision_trace": {
            "interpreter": "prepare_frequency_adaptation_decision_runtime",
            "version": "v1",
            "inputs": {
                "requested_program_id": requested_program_id,
                "selected_program_id": selected_program_id,
                "current_days_available": int(current_days_available),
                "target_days": int(target_days),
                "duration_weeks": int(duration_weeks),
                "explicit_weak_area_count": len(explicit_weak_areas),
                "stored_weak_area_count": len(stored_weak_areas),
                "equipment_profile_count": len(equipment_profile),
                "has_latest_plan": latest_plan is not None,
                "has_latest_soreness_entry": latest_soreness_entry is not None,
            },
            "outcome": {
                "program_id": str(adaptation_runtime.get("program_id") or ""),
                "recovery_state": str(adaptation_runtime.get("recovery_state") or ""),
                "current_week_index": int(adaptation_runtime.get("current_week_index") or 1),
            },
            "adaptation_runtime_trace": _coerce_dict(adaptation_runtime.get("decision_trace")),
        },
    }


def _count_prior_generated_weeks(selected_template_id: str, prior_plans: list[Any]) -> int:
    prior_weeks_for_template: set[str] = set()
    for existing_plan in prior_plans:
        payload_data = _read_attr(existing_plan, "payload")
        payload_data = payload_data if isinstance(payload_data, dict) else {}
        week_start = _read_attr(existing_plan, "week_start")
        week_key = _iso_date(week_start)
        program_id = payload_data.get("program_template_id")
        if program_id == selected_template_id:
            prior_weeks_for_template.add(week_key)
            continue

        sessions = payload_data.get("sessions") or []
        if any(
            str(session.get("session_id", "")).startswith(f"{selected_template_id}-")
            for session in sessions
        ):
            prior_weeks_for_template.add(week_key)

    return len(prior_weeks_for_template)


def _resolve_generation_history(
    *,
    normalized_training_state: dict[str, Any],
    history_rows: list[Any],
) -> tuple[list[dict[str, Any]], str]:
    history = _serialize_training_state_history(normalized_training_state)
    if history:
        return history, "training_state"
    return serialize_recent_training_history(history_rows), "history_rows"


def _resolve_generation_soreness(
    *,
    fatigue_state: dict[str, Any],
    latest_soreness_entry: Any | None,
) -> tuple[dict[str, str], int, str]:
    soreness_by_muscle = _coerce_string_map(fatigue_state.get("soreness_by_muscle"))
    if soreness_by_muscle:
        severe_soreness_count = sum(
            1 for severity in soreness_by_muscle.values() if str(severity).lower() == "severe"
        )
        return soreness_by_muscle, severe_soreness_count, "training_state"

    soreness_by_muscle = _coerce_string_map(
        _read_attr(latest_soreness_entry, "severity_by_muscle", {}) if latest_soreness_entry else {}
    )
    severe_soreness_count = sum(
        1 for severity in soreness_by_muscle.values() if str(severity).lower() == "severe"
    )
    return soreness_by_muscle, severe_soreness_count, "latest_soreness"


def _resolve_generation_adherence(
    *,
    adherence_state: dict[str, Any],
    latest_checkin: Any | None,
) -> tuple[int | None, str]:
    latest_adherence_score = adherence_state.get("latest_adherence_score")
    if latest_adherence_score is not None:
        return int(latest_adherence_score), "training_state"

    latest_adherence_score = _read_attr(latest_checkin, "adherence_score") if latest_checkin is not None else None
    return int(latest_adherence_score) if latest_adherence_score is not None else None, "latest_checkin"


def _resolve_generation_prior_weeks(
    *,
    selected_template_id: str,
    generation_state: dict[str, Any],
    prior_plans: list[Any],
) -> tuple[int, str]:
    prior_generated_weeks_by_program = _coerce_dict(generation_state.get("prior_generated_weeks_by_program"))
    if selected_template_id in prior_generated_weeks_by_program:
        return int(prior_generated_weeks_by_program[selected_template_id] or 0), "training_state"

    return _count_prior_generated_weeks(selected_template_id, prior_plans), "prior_plans"


def _resolve_generation_readiness_state(
    *,
    normalized_training_state: dict[str, Any],
    latest_checkin: Any | None,
) -> tuple[dict[str, Any], str]:
    readiness_state = _coerce_dict(normalized_training_state.get("readiness_state"))
    if readiness_state:
        return {
            "sleep_quality": readiness_state.get("sleep_quality"),
            "stress_level": readiness_state.get("stress_level"),
            "pain_flags": _coerce_string_list(readiness_state.get("pain_flags")),
            "recovery_risk_flags": _coerce_string_list(readiness_state.get("recovery_risk_flags")),
        }, "training_state"

    if latest_checkin is None:
        return {
            "sleep_quality": None,
            "stress_level": None,
            "pain_flags": [],
            "recovery_risk_flags": [],
        }, "default"

    pain_flags = _coerce_string_list(_read_attr(latest_checkin, "pain_flags", []))
    recovery_risk_flags: list[str] = []
    sleep_quality = _read_attr(latest_checkin, "sleep_quality")
    stress_level = _read_attr(latest_checkin, "stress_level")
    if sleep_quality is not None and int(sleep_quality) <= 2:
        recovery_risk_flags.append("low_sleep")
    if stress_level is not None and int(stress_level) >= 4:
        recovery_risk_flags.append("high_stress")
    if pain_flags:
        recovery_risk_flags.append("pain_flags_present")
    return {
        "sleep_quality": int(sleep_quality) if sleep_quality is not None else None,
        "stress_level": int(stress_level) if stress_level is not None else None,
        "pain_flags": pain_flags,
        "recovery_risk_flags": sorted(recovery_risk_flags),
    }, "latest_checkin"


def _generation_completion_proxy(adherence_score: int | None) -> tuple[int, str]:
    if adherence_score is None:
        return 85, "default"
    clamped = max(1, min(5, int(adherence_score)))
    return {
        1: 55,
        2: 68,
        3: 80,
        4: 90,
        5: 96,
    }[clamped], "latest_adherence_score"


def _generation_soreness_level(fatigue_state: dict[str, Any], severe_soreness_count: int) -> str:
    if severe_soreness_count >= 2:
        return "severe"
    if severe_soreness_count == 1:
        return "moderate"

    flagged_muscles = _coerce_string_list(fatigue_state.get("flagged_muscles"))
    if len(flagged_muscles) >= 2:
        return "moderate"
    if flagged_muscles:
        return "mild"
    return "none"


def _resolve_generation_stimulus_fatigue_response(
    *,
    fatigue_state: dict[str, Any],
    readiness_state: dict[str, Any],
    latest_adherence_score: int | None,
    severe_soreness_count: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    completion_pct_proxy, completion_proxy_source = _generation_completion_proxy(latest_adherence_score)
    soreness_level = _generation_soreness_level(fatigue_state, severe_soreness_count)
    average_rpe = fatigue_state.get("session_rpe_avg")
    sleep_quality = readiness_state.get("sleep_quality")
    stress_level = readiness_state.get("stress_level")
    pain_flags = _coerce_string_list(readiness_state.get("pain_flags"))

    snapshot = evaluate_stimulus_fatigue_response(
        completion_pct=completion_pct_proxy,
        adherence_score=max(1, min(5, int(latest_adherence_score or 3))),
        soreness_level=soreness_level,
        average_rpe=float(average_rpe) if isinstance(average_rpe, (int, float)) else None,
        consecutive_underperformance_weeks=0,
        sleep_quality=int(sleep_quality) if sleep_quality is not None else None,
        stress_level=int(stress_level) if stress_level is not None else None,
        pain_flags=pain_flags,
    )
    return snapshot, {
        "completion_pct_proxy": completion_pct_proxy,
        "completion_pct_proxy_source": completion_proxy_source,
        "soreness_level": soreness_level,
        "average_rpe": float(average_rpe) if isinstance(average_rpe, (int, float)) else None,
    }


def resolve_week_generation_runtime_inputs(
    *,
    selected_template_id: str,
    current_days_available: int,
    active_frequency_adaptation: dict[str, Any] | None,
    user_training_state: dict[str, Any] | None = None,
    history_rows: list[Any],
    latest_soreness_entry: Any | None,
    latest_checkin: Any | None,
    prior_plans: list[Any],
) -> dict[str, Any]:
    effective_days_available = current_days_available
    if isinstance(active_frequency_adaptation, dict) and active_frequency_adaptation.get("target_days") is not None:
        effective_days_available = int(active_frequency_adaptation["target_days"])

    normalized_training_state = _coerce_training_state(user_training_state)
    fatigue_state = _coerce_dict(normalized_training_state.get("fatigue_state"))
    adherence_state = _coerce_dict(normalized_training_state.get("adherence_state"))
    generation_state = _coerce_dict(normalized_training_state.get("generation_state"))

    history, history_source = _resolve_generation_history(
        normalized_training_state=normalized_training_state,
        history_rows=history_rows,
    )
    soreness_by_muscle, severe_soreness_count, soreness_source = _resolve_generation_soreness(
        fatigue_state=fatigue_state,
        latest_soreness_entry=latest_soreness_entry,
    )
    latest_adherence_score, adherence_source = _resolve_generation_adherence(
        adherence_state=adherence_state,
        latest_checkin=latest_checkin,
    )
    prior_generated_weeks, prior_generation_source = _resolve_generation_prior_weeks(
        selected_template_id=selected_template_id,
        generation_state=generation_state,
        prior_plans=prior_plans,
    )
    readiness_state, readiness_source = _resolve_generation_readiness_state(
        normalized_training_state=normalized_training_state,
        latest_checkin=latest_checkin,
    )
    constraint_state = _coerce_dict(normalized_training_state.get("constraint_state"))
    stimulus_fatigue_response, sfr_trace = _resolve_generation_stimulus_fatigue_response(
        fatigue_state=fatigue_state,
        readiness_state=readiness_state,
        latest_adherence_score=latest_adherence_score,
        severe_soreness_count=severe_soreness_count,
    )

    return {
        "effective_days_available": int(effective_days_available),
        "history": history,
        "soreness_by_muscle": soreness_by_muscle,
        "severe_soreness_count": int(severe_soreness_count),
        "latest_adherence_score": int(latest_adherence_score) if latest_adherence_score is not None else None,
        "prior_generated_weeks": int(prior_generated_weeks),
        "readiness_state": readiness_state,
        "movement_restrictions": list(constraint_state.get("movement_restrictions") or []),
        "session_time_budget_minutes": (
            int(constraint_state.get("session_time_budget_minutes"))
            if constraint_state.get("session_time_budget_minutes") is not None
            else None
        ),
        "progression_state_per_exercise": list(normalized_training_state.get("progression_state_per_exercise") or []),
        "stimulus_fatigue_response": stimulus_fatigue_response,
        "decision_trace": {
            "interpreter": "resolve_week_generation_runtime_inputs",
            "version": "v1",
            "inputs": {
                "selected_template_id": selected_template_id,
                "current_days_available": int(current_days_available),
                "active_frequency_adaptation": bool(active_frequency_adaptation),
                "has_user_training_state": bool(normalized_training_state),
                "history_row_count": len(history_rows),
                "prior_plan_count": len(prior_plans),
                "progression_state_count": len(list(normalized_training_state.get("progression_state_per_exercise") or [])),
            },
            "steps": [
                {
                    "decision": "frequency_adaptation_runtime",
                    "result": {
                        "active": bool(active_frequency_adaptation),
                        "effective_days_available": int(effective_days_available),
                    },
                },
                {
                    "decision": "recovery_inputs",
                    "result": {
                        "soreness_source": soreness_source,
                        "severe_soreness_count": int(severe_soreness_count),
                        "latest_adherence_score": int(latest_adherence_score) if latest_adherence_score is not None else None,
                        "latest_adherence_score_source": adherence_source,
                        "readiness_source": readiness_source,
                        "movement_restriction_count": len(list(constraint_state.get("movement_restrictions") or [])),
                        "session_time_budget_minutes": (
                            int(constraint_state.get("session_time_budget_minutes"))
                            if constraint_state.get("session_time_budget_minutes") is not None
                            else None
                        ),
                    },
                },
                {
                    "decision": "history_runtime",
                    "result": {
                        "history_count": len(history),
                        "history_source": history_source,
                    },
                },
                {
                    "decision": "prior_generation_context",
                    "result": {
                        "prior_generated_weeks": int(prior_generated_weeks),
                        "source": prior_generation_source,
                    },
                },
                {
                    "decision": "stimulus_fatigue_response",
                    "result": {
                        **sfr_trace,
                        **stimulus_fatigue_response,
                    },
                },
            ],
            "outcome": {
                "effective_days_available": int(effective_days_available),
                "history_count": len(history),
                "severe_soreness_count": int(severe_soreness_count),
                "latest_adherence_score": int(latest_adherence_score) if latest_adherence_score is not None else None,
                "prior_generated_weeks": int(prior_generated_weeks),
                "stimulus_fatigue_response": stimulus_fatigue_response,
            },
        },
    }


def prepare_plan_generation_decision_runtime(
    *,
    selected_template_id: str,
    current_days_available: int,
    active_frequency_adaptation: dict[str, Any] | None,
    selected_program_id: str | None,
    split_preference: str | None = None,
    training_location: str | None = None,
    equipment_profile: list[str] | None = None,
    weak_areas: list[str] | None = None,
    nutrition_phase: str | None = None,
    session_time_budget_minutes: int | None = None,
    movement_restrictions: list[str] | None = None,
    near_failure_tolerance: str | None = None,
    latest_plan: Any | None,
    latest_soreness_entry: Any | None,
    recent_workout_logs: list[Any],
    exercise_states: list[Any] | None = None,
    recent_checkins: list[Any],
    recent_review_cycles: list[Any],
    prior_plans: list[Any],
    build_plan_decision_training_state: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    latest_checkin = recent_checkins[0] if recent_checkins else None
    training_state = build_plan_decision_training_state(
        selected_program_id=selected_program_id,
        days_available=current_days_available,
        split_preference=split_preference,
        training_location=training_location,
        equipment_profile=equipment_profile,
        weak_areas=weak_areas,
        nutrition_phase=nutrition_phase,
        session_time_budget_minutes=session_time_budget_minutes,
        movement_restrictions=movement_restrictions,
        near_failure_tolerance=near_failure_tolerance,
        latest_plan=latest_plan,
        latest_soreness_entry=latest_soreness_entry,
        recent_workout_logs=recent_workout_logs,
        exercise_states=list(exercise_states or []),
        recent_checkins=recent_checkins,
        recent_review_cycles=recent_review_cycles,
        prior_plans=prior_plans,
    )
    generation_runtime = resolve_week_generation_runtime_inputs(
        selected_template_id=selected_template_id,
        current_days_available=current_days_available,
        active_frequency_adaptation=active_frequency_adaptation,
        user_training_state=training_state,
        history_rows=[],
        latest_soreness_entry=latest_soreness_entry,
        latest_checkin=latest_checkin,
        prior_plans=prior_plans,
    )
    return {
        "training_state": training_state,
        "generation_runtime": generation_runtime,
        "decision_trace": {
            "interpreter": "prepare_plan_generation_decision_runtime",
            "version": "v1",
            "inputs": {
                "selected_template_id": selected_template_id,
                "selected_program_id": selected_program_id,
                "current_days_available": int(current_days_available),
                "has_active_frequency_adaptation": bool(active_frequency_adaptation),
                "has_latest_plan": latest_plan is not None,
                "has_latest_soreness_entry": latest_soreness_entry is not None,
                "recent_workout_log_count": len(recent_workout_logs),
                "exercise_state_count": len(list(exercise_states or [])),
                "recent_checkin_count": len(recent_checkins),
                "recent_review_cycle_count": len(recent_review_cycles),
                "prior_plan_count": len(prior_plans),
            },
            "outcome": {
                "effective_days_available": int(generation_runtime.get("effective_days_available") or 0),
                "history_count": len(generation_runtime.get("history") or []),
                "severe_soreness_count": int(generation_runtime.get("severe_soreness_count") or 0),
                "latest_adherence_score": generation_runtime.get("latest_adherence_score"),
                "prior_generated_weeks": int(generation_runtime.get("prior_generated_weeks") or 0),
            },
            "user_training_state_trace": _coerce_dict(training_state.get("decision_trace")),
            "generation_runtime_trace": _coerce_dict(generation_runtime.get("decision_trace")),
        },
    }


def prepare_generate_week_plan_runtime_inputs(
    *,
    user_name: str | None,
    split_preference: str,
    nutrition_phase: str | None,
    available_equipment: list[str] | None,
    generation_runtime: dict[str, Any],
) -> dict[str, Any]:
    runtime = _coerce_dict(generation_runtime)
    history_raw = runtime.get("history")
    history = list(history_raw) if isinstance(history_raw, list) else []
    soreness_by_muscle = _coerce_string_map(runtime.get("soreness_by_muscle"))
    normalized_equipment = [str(item) for item in (available_equipment or []) if str(item).strip()]
    latest_adherence_score_raw = runtime.get("latest_adherence_score")
    latest_adherence_score = int(latest_adherence_score_raw) if latest_adherence_score_raw is not None else None
    progression_state_per_exercise = list(runtime.get("progression_state_per_exercise") or [])
    movement_restrictions = [str(item) for item in (runtime.get("movement_restrictions") or []) if str(item).strip()]
    session_time_budget_minutes_raw = runtime.get("session_time_budget_minutes")
    session_time_budget_minutes = (
        int(session_time_budget_minutes_raw) if session_time_budget_minutes_raw is not None else None
    )

    payload = {
        "user_profile": {
            "name": user_name,
            "session_time_budget_minutes": session_time_budget_minutes,
            "movement_restrictions": movement_restrictions,
        },
        "days_available": int(runtime.get("effective_days_available") or 0),
        "split_preference": split_preference,
        "phase": str(nutrition_phase or "maintenance"),
        "available_equipment": normalized_equipment,
        "history": history,
        "soreness_by_muscle": soreness_by_muscle,
        "prior_generated_weeks": int(runtime.get("prior_generated_weeks") or 0),
        "latest_adherence_score": latest_adherence_score,
        "severe_soreness_count": int(runtime.get("severe_soreness_count") or 0),
        "progression_state_per_exercise": progression_state_per_exercise,
        "stimulus_fatigue_response": _coerce_dict(runtime.get("stimulus_fatigue_response")),
        "decision_trace": {
            "interpreter": "prepare_generate_week_plan_runtime_inputs",
            "version": "v1",
            "inputs": {
                "split_preference": split_preference,
                "nutrition_phase": nutrition_phase,
                "available_equipment_count": len(normalized_equipment),
                "runtime_keys": sorted(runtime.keys()),
            },
            "outcome": {
                "days_available": int(runtime.get("effective_days_available") or 0),
                "history_count": len(history),
                "severe_soreness_count": int(runtime.get("severe_soreness_count") or 0),
                "latest_adherence_score": latest_adherence_score,
                "progression_state_count": len(progression_state_per_exercise),
                "prior_generated_weeks": int(runtime.get("prior_generated_weeks") or 0),
                "movement_restriction_count": len(movement_restrictions),
                "session_time_budget_minutes": session_time_budget_minutes,
                "stimulus_fatigue_response": _coerce_dict(runtime.get("stimulus_fatigue_response")),
            },
        },
    }
    return payload


def prepare_generate_week_scheduler_runtime(
    *,
    user_name: str | None,
    split_preference: str,
    nutrition_phase: str | None,
    available_equipment: list[str] | None,
    generation_runtime: dict[str, Any],
    program_template: dict[str, Any],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    plan_runtime_inputs = prepare_generate_week_plan_runtime_inputs(
        user_name=user_name,
        split_preference=split_preference,
        nutrition_phase=nutrition_phase,
        available_equipment=available_equipment,
        generation_runtime=generation_runtime,
    )
    scheduler_kwargs = {
        "user_profile": dict(plan_runtime_inputs.get("user_profile") or {}),
        "days_available": int(plan_runtime_inputs.get("days_available") or 0),
        "split_preference": str(plan_runtime_inputs.get("split_preference") or ""),
        "program_template": dict(program_template),
        "history": list(plan_runtime_inputs.get("history") or []),
        "phase": str(plan_runtime_inputs.get("phase") or "maintenance"),
        "available_equipment": list(plan_runtime_inputs.get("available_equipment") or []),
        "soreness_by_muscle": dict(plan_runtime_inputs.get("soreness_by_muscle") or {}),
        "prior_generated_weeks": int(plan_runtime_inputs.get("prior_generated_weeks") or 0),
        "latest_adherence_score": plan_runtime_inputs.get("latest_adherence_score"),
        "severe_soreness_count": int(plan_runtime_inputs.get("severe_soreness_count") or 0),
        "session_time_budget_minutes": _coerce_dict(plan_runtime_inputs.get("user_profile")).get(
            "session_time_budget_minutes"
        ),
        "movement_restrictions": list(
            _coerce_dict(plan_runtime_inputs.get("user_profile")).get("movement_restrictions") or []
        ),
        "progression_state_per_exercise": list(plan_runtime_inputs.get("progression_state_per_exercise") or []),
        "stimulus_fatigue_response": _coerce_dict(plan_runtime_inputs.get("stimulus_fatigue_response")) or None,
        "rule_set": _coerce_dict(rule_set) or None,
    }
    return {
        "scheduler_kwargs": scheduler_kwargs,
        "decision_trace": {
            "interpreter": "prepare_generate_week_scheduler_runtime",
            "version": "v1",
            "inputs": {
                "template_id": str(program_template.get("id") or ""),
                "has_rule_set": bool(rule_set),
            },
            "plan_input_trace": _coerce_dict(plan_runtime_inputs.get("decision_trace")),
            "outcome": {
                "days_available": int(scheduler_kwargs["days_available"]),
                "history_count": len(scheduler_kwargs["history"]),
                "severe_soreness_count": int(scheduler_kwargs["severe_soreness_count"]),
                "latest_adherence_score": scheduler_kwargs["latest_adherence_score"],
                "prior_generated_weeks": int(scheduler_kwargs["prior_generated_weeks"]),
            },
        },
    }


def prepare_generate_week_review_lookup_runtime(
    *,
    base_plan: dict[str, Any],
) -> dict[str, Any]:
    week_start = date.fromisoformat(str(base_plan.get("week_start") or ""))
    return {
        "week_start": week_start,
        "decision_trace": {
            "interpreter": "prepare_generate_week_review_lookup_runtime",
            "version": "v1",
            "inputs": {
                "has_week_start": bool(base_plan.get("week_start")),
            },
            "outcome": {
                "week_start": week_start.isoformat(),
            },
        },
    }


def prepare_generate_week_finalize_runtime(
    *,
    user_id: str,
    base_plan: dict[str, Any],
    template_selection_trace: dict[str, Any],
    generation_runtime_trace: dict[str, Any],
    selected_template_id: str,
    active_frequency_adaptation: dict[str, Any] | None,
    review_cycle: Any | None,
) -> dict[str, Any]:
    review_overlay = prepare_generated_week_review_overlay(review_cycle)
    finalized_plan = build_generated_week_plan_payload(
        base_plan=base_plan,
        template_selection_trace=template_selection_trace,
        generation_runtime_trace=generation_runtime_trace,
        selected_template_id=selected_template_id,
        active_frequency_adaptation=active_frequency_adaptation,
        review_adjustments=_coerce_dict(review_overlay.get("review_adjustments")) or None,
        review_context=_coerce_dict(review_overlay.get("review_context")) or None,
        review_overlay_trace=_coerce_dict(review_overlay.get("decision_trace")) or None,
    )
    response_payload = _coerce_dict(finalized_plan.get("plan"))
    adaptation_persistence_payload = build_generated_week_adaptation_persistence_payload(
        adaptation_runtime=_coerce_dict(finalized_plan.get("adaptation_runtime")),
    )
    week_start = date.fromisoformat(str(response_payload.get("week_start") or base_plan.get("week_start") or ""))
    record_values = {
        "user_id": user_id,
        "week_start": week_start,
        "split": str(response_payload.get("split") or ""),
        "phase": str(response_payload.get("phase") or ""),
        "payload": response_payload,
    }
    return {
        "week_start": week_start,
        "response_payload": response_payload,
        "record_values": record_values,
        "adaptation_persistence_payload": adaptation_persistence_payload,
        "decision_trace": {
            "interpreter": "prepare_generate_week_finalize_runtime",
            "version": "v1",
            "inputs": {
                "selected_template_id": selected_template_id,
                "has_active_frequency_adaptation": bool(active_frequency_adaptation),
                "has_review_cycle": review_cycle is not None,
            },
            "review_overlay_trace": _coerce_dict(review_overlay.get("decision_trace")),
            "outcome": {
                "week_start": week_start.isoformat(),
                "state_updated": bool(adaptation_persistence_payload.get("state_updated")),
                "session_count": len(response_payload.get("sessions") or []),
            },
        },
    }
