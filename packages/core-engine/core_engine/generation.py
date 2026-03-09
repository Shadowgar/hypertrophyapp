from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

from .intelligence import order_generation_template_candidates, recommend_generation_template_selection
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


def summarize_generation_template_viability(
    *,
    template: dict[str, Any],
    days_available: int,
    split_preference: str,
    nutrition_phase: str,
    available_equipment: list[str],
) -> dict[str, int]:
    preview = generate_week_plan(
        user_profile={"name": "preview"},
        days_available=days_available,
        split_preference=split_preference,
        program_template=template,
        history=[],
        phase=nutrition_phase,
        available_equipment=available_equipment,
    )
    sessions = preview.get("sessions") or []
    return {
        "session_count": len(sessions),
        "exercise_count": sum(len(session.get("exercises") or []) for session in sessions),
    }


def resolve_generation_template_choice(
    *,
    explicit_template_id: str | None,
    explicit_template: dict[str, Any] | None,
    profile_template_id: str | None,
    split_preference: str,
    days_available: int,
    nutrition_phase: str,
    available_equipment: list[str],
    candidate_summaries: list[dict[str, Any]],
    loaded_candidate_templates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if explicit_template_id:
        if explicit_template is None:
            raise FileNotFoundError("No valid program templates available for generation")
        selection = recommend_generation_template_selection(
            explicit_template_id=explicit_template_id,
            profile_template_id=profile_template_id,
            split_preference=split_preference,
            days_available=days_available,
            candidate_summaries=[],
            candidate_evaluations=[],
        )
        return {
            "selected_template_id": explicit_template_id,
            "selected_template": explicit_template,
            "decision_trace": dict(selection["decision_trace"]),
        }

    ordered_candidates = order_generation_template_candidates(
        preferred_template_id=profile_template_id,
        split_preference=split_preference,
        days_available=days_available,
        candidate_summaries=candidate_summaries,
    )

    candidate_evaluations: list[dict[str, Any]] = []
    templates_by_id: dict[str, dict[str, Any]] = {}
    for candidate_id in ordered_candidates:
        candidate_template = loaded_candidate_templates.get(candidate_id)
        if not isinstance(candidate_template, dict):
            candidate_evaluations.append({"template_id": candidate_id, "status": "unavailable"})
            continue
        templates_by_id[candidate_id] = candidate_template
        viability = summarize_generation_template_viability(
            template=candidate_template,
            days_available=days_available,
            split_preference=split_preference,
            nutrition_phase=nutrition_phase,
            available_equipment=available_equipment,
        )
        candidate_evaluations.append(
            {
                "template_id": candidate_id,
                "status": "loaded",
                **viability,
            }
        )

    selection = recommend_generation_template_selection(
        explicit_template_id=None,
        profile_template_id=profile_template_id,
        split_preference=split_preference,
        days_available=days_available,
        candidate_summaries=candidate_summaries,
        candidate_evaluations=candidate_evaluations,
    )
    selected_template_id = str(selection["selected_template_id"])
    selected_template = templates_by_id.get(selected_template_id)
    if selected_template is None:
        raise FileNotFoundError("No valid program templates available for generation")

    return {
        "selected_template_id": selected_template_id,
        "selected_template": selected_template,
        "decision_trace": dict(selection["decision_trace"]),
    }


def prepare_generation_template_runtime(
    *,
    explicit_template_id: str | None,
    profile_template_id: str | None,
    split_preference: str,
    days_available: int,
    nutrition_phase: str,
    available_equipment: list[str],
    candidate_summaries: list[dict[str, Any]],
    load_template: Callable[[str], dict[str, Any]],
    ignored_loader_exceptions: tuple[type[BaseException], ...] = (FileNotFoundError, KeyError),
) -> dict[str, Any]:
    if explicit_template_id:
        explicit_template = load_template(explicit_template_id)
        selection = resolve_generation_template_choice(
            explicit_template_id=explicit_template_id,
            explicit_template=explicit_template,
            profile_template_id=profile_template_id,
            split_preference=split_preference,
            days_available=days_available,
            nutrition_phase=nutrition_phase,
            available_equipment=available_equipment,
            candidate_summaries=[],
            loaded_candidate_templates={},
        )
        return {
            "selected_template_id": explicit_template_id,
            "selected_template": explicit_template,
            "decision_trace": dict(selection["decision_trace"]),
        }

    loaded_candidate_templates: dict[str, dict[str, Any]] = {}
    for summary in candidate_summaries:
        candidate_id = str(summary.get("id") or "")
        if not candidate_id:
            continue
        try:
            loaded_candidate_templates[candidate_id] = load_template(candidate_id)
        except ignored_loader_exceptions:
            continue

    selection = resolve_generation_template_choice(
        explicit_template_id=None,
        explicit_template=None,
        profile_template_id=profile_template_id,
        split_preference=split_preference,
        days_available=days_available,
        nutrition_phase=nutrition_phase,
        available_equipment=available_equipment,
        candidate_summaries=candidate_summaries,
        loaded_candidate_templates=loaded_candidate_templates,
    )
    return {
        "selected_template_id": str(selection["selected_template_id"]),
        "selected_template": dict(selection["selected_template"]),
        "decision_trace": dict(selection["decision_trace"]),
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

    return {
        "effective_days_available": int(effective_days_available),
        "history": history,
        "soreness_by_muscle": soreness_by_muscle,
        "severe_soreness_count": int(severe_soreness_count),
        "latest_adherence_score": int(latest_adherence_score) if latest_adherence_score is not None else None,
        "prior_generated_weeks": int(prior_generated_weeks),
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
            ],
            "outcome": {
                "effective_days_available": int(effective_days_available),
                "history_count": len(history),
                "severe_soreness_count": int(severe_soreness_count),
                "latest_adherence_score": int(latest_adherence_score) if latest_adherence_score is not None else None,
                "prior_generated_weeks": int(prior_generated_weeks),
            },
        },
    }
