from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from .warmups import compute_warmups


def _decision_step(rule: str, matched: bool, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "rule": rule,
        "matched": matched,
    }
    if details:
        payload["details"] = details
    return payload


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_attr(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def build_coach_preview_payloads(
    *,
    recommendation_id: str,
    preview_payload: dict[str, Any],
    program_name: str,
) -> dict[str, dict[str, Any]]:
    response_payload = {
        **deepcopy(preview_payload),
        "recommendation_id": recommendation_id,
        "program_name": program_name,
    }
    return {
        "response_payload": deepcopy(response_payload),
        "recommendation_payload": deepcopy(response_payload),
    }


def build_coach_preview_recommendation_record_fields(
    *,
    template_id: str,
    preview_request: dict[str, Any],
    preview_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "template_id": template_id,
        "recommendation_type": "coach_preview",
        "current_phase": str(preview_request.get("current_phase") or ""),
        "recommended_phase": str(_coerce_dict(preview_payload.get("phase_transition")).get("next_phase") or ""),
        "progression_action": str(_coerce_dict(preview_payload.get("progression")).get("action") or ""),
        "request_payload": deepcopy(preview_request),
        "recommendation_payload": {},
        "status": "previewed",
    }


def prepare_coach_preview_commit_runtime(
    *,
    user_id: str,
    template_id: str,
    preview_request: dict[str, Any],
    preview_payload: dict[str, Any],
    program_name: str,
) -> dict[str, Any]:
    record_values = {
        "user_id": user_id,
        **build_coach_preview_recommendation_record_fields(
            template_id=template_id,
            preview_request=preview_request,
            preview_payload=preview_payload,
        ),
    }
    return {
        "record_values": record_values,
        "payload_runtime": {
            "preview_payload": deepcopy(preview_payload),
            "program_name": str(program_name),
        },
        "decision_trace": {
            "interpreter": "prepare_coach_preview_commit_runtime",
            "version": "v1",
            "inputs": {
                "user_id": user_id,
                "template_id": template_id,
                "current_phase": str(preview_request.get("current_phase") or ""),
            },
            "outcome": {
                "recommended_phase": str(record_values.get("recommended_phase") or ""),
                "progression_action": str(record_values.get("progression_action") or ""),
            },
        },
    }


def prepare_coach_preview_route_runtime(
    *,
    user_id: str,
    template_id: str,
    context: dict[str, Any],
    preview_request: dict[str, Any],
    rule_set: dict[str, Any] | None,
    request_runtime_trace: dict[str, Any] | None,
    template_runtime_trace: dict[str, Any] | None,
    program_name: str,
    recommend_coach_intelligence_preview: Callable[..., dict[str, Any]],
    prepare_coach_preview_commit_runtime: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    preview_payload = recommend_coach_intelligence_preview(
        template_id=template_id,
        context=context,
        preview_request=preview_request,
        rule_set=rule_set,
        request_runtime_trace=request_runtime_trace,
        template_runtime_trace=template_runtime_trace,
    )
    commit_runtime = prepare_coach_preview_commit_runtime(
        user_id=user_id,
        template_id=template_id,
        preview_request=preview_request,
        preview_payload=preview_payload,
        program_name=program_name,
    )
    return {
        "preview_payload": preview_payload,
        "commit_runtime": commit_runtime,
        "decision_trace": {
            "interpreter": "prepare_coach_preview_route_runtime",
            "version": "v1",
            "inputs": {
                "user_id": user_id,
                "template_id": template_id,
                "program_name": program_name,
            },
            "outcome": {
                "recommended_phase": str(_coerce_dict(preview_payload.get("phase_transition")).get("next_phase") or ""),
                "progression_action": str(_coerce_dict(preview_payload.get("progression")).get("action") or ""),
            },
        },
    }


def finalize_coach_preview_commit_runtime(
    *,
    prepared_runtime: dict[str, Any],
    recommendation_id: str,
) -> dict[str, Any]:
    payload_runtime = _coerce_dict(prepared_runtime.get("payload_runtime"))
    return build_coach_preview_payloads(
        recommendation_id=recommendation_id,
        preview_payload=_coerce_dict(payload_runtime.get("preview_payload")),
        program_name=str(payload_runtime.get("program_name") or ""),
    )


def prepare_coach_preview_decision_context(
    *,
    user_name: str | None,
    split_preference: str,
    template: dict[str, Any],
    latest_plan: Any | None,
    recent_workout_logs: list[Any],
    recent_checkins: list[Any] | None = None,
    selected_program_id: str | None,
    nutrition_phase: str | None,
    available_equipment: list[str] | None,
    build_plan_decision_training_state: Callable[..., dict[str, Any]],
    build_coach_preview_context: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    training_state = build_plan_decision_training_state(
        selected_program_id=selected_program_id,
        latest_plan=latest_plan,
        latest_soreness_entry=None,
        recent_workout_logs=recent_workout_logs,
        recent_checkins=list(recent_checkins or []),
    )
    context = build_coach_preview_context(
        user_name=user_name,
        split_preference=split_preference,
        template=template,
        history_rows=[],
        user_training_state=training_state,
        nutrition_phase=nutrition_phase or "maintenance",
        available_equipment=list(available_equipment or []),
    )
    return {
        "training_state": training_state,
        "context": context,
        "decision_trace": {
            "interpreter": "prepare_coach_preview_decision_context",
            "version": "v1",
            "inputs": {
                "split_preference": split_preference,
                "selected_program_id": selected_program_id,
                "recent_log_count": len(recent_workout_logs),
                "recent_checkin_count": len(recent_checkins or []),
                "nutrition_phase_provided": bool(nutrition_phase),
                "equipment_count": len(available_equipment or []),
            },
            "outcome": {
                "nutrition_phase": nutrition_phase or "maintenance",
                "available_equipment_count": len(available_equipment or []),
            },
        },
    }


def prepare_coaching_apply_runtime_source(source_recommendation: Any) -> dict[str, Any]:
    recommendation_payload_raw = _read_attr(source_recommendation, "recommendation_payload", {})
    recommendation_payload = _coerce_dict(recommendation_payload_raw)
    return {
        "recommendation_id": str(_read_attr(source_recommendation, "id", "") or ""),
        "recommendation_payload": recommendation_payload,
        "template_id": str(_read_attr(source_recommendation, "template_id", "") or ""),
        "current_phase": str(_read_attr(source_recommendation, "current_phase", "") or ""),
        "recommended_phase": str(_read_attr(source_recommendation, "recommended_phase", "") or ""),
        "progression_action": str(_read_attr(source_recommendation, "progression_action", "") or ""),
        "decision_trace": {
            "interpreter": "prepare_coaching_apply_runtime_source",
            "version": "v1",
            "inputs": {
                "has_recommendation_payload_dict": isinstance(recommendation_payload_raw, dict),
            },
            "outcome": {
                "recommendation_id": str(_read_attr(source_recommendation, "id", "") or ""),
                "template_id": str(_read_attr(source_recommendation, "template_id", "") or ""),
            },
        },
    }


def prepare_phase_apply_runtime(
    *,
    recommendation_id: str,
    recommendation_payload: dict[str, Any],
    fallback_next_phase: str | None,
    confirm: bool,
    template_id: str,
    current_phase: str,
    progression_action: str,
    interpret_phase_apply_decision: Callable[..., dict[str, Any]],
    build_phase_applied_record: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    phase_transition = recommendation_payload.get("phase_transition")
    if not isinstance(phase_transition, dict):
        raise ValueError("Recommendation is missing phase transition details")

    normalized_phase_transition = dict(phase_transition)
    if "next_phase" not in normalized_phase_transition and fallback_next_phase:
        normalized_phase_transition["next_phase"] = str(fallback_next_phase)

    decision_payload = interpret_phase_apply_decision(
        recommendation_id=recommendation_id,
        phase_transition=normalized_phase_transition,
        confirm=confirm,
    )

    runtime_payload: dict[str, Any] = {
        "payload_value": normalized_phase_transition,
        "decision_payload": decision_payload,
    }
    if confirm:
        runtime_payload["record_fields"] = build_phase_applied_record(
            template_id=template_id,
            current_phase=current_phase,
            progression_action=progression_action,
            source_recommendation_id=recommendation_id,
            next_phase=str(decision_payload["next_phase"]),
        )
    return runtime_payload


def prepare_specialization_apply_runtime(
    *,
    recommendation_id: str,
    recommendation_payload: dict[str, Any],
    confirm: bool,
    template_id: str,
    current_phase: str,
    recommended_phase: str,
    progression_action: str,
    interpret_specialization_apply_decision: Callable[..., dict[str, Any]],
    build_specialization_applied_record: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    specialization = recommendation_payload.get("specialization")
    if not isinstance(specialization, dict):
        raise ValueError("Recommendation is missing specialization details")

    normalized_specialization = dict(specialization)
    decision_payload = interpret_specialization_apply_decision(
        recommendation_id=recommendation_id,
        specialization=normalized_specialization,
        confirm=confirm,
    )

    runtime_payload: dict[str, Any] = {
        "payload_value": normalized_specialization,
        "decision_payload": decision_payload,
    }
    if confirm:
        runtime_payload["record_fields"] = build_specialization_applied_record(
            template_id=template_id,
            current_phase=current_phase,
            recommended_phase=recommended_phase,
            progression_action=progression_action,
            source_recommendation_id=recommendation_id,
        )
    return runtime_payload


def prepare_coaching_apply_decision_runtime(
    *,
    decision_kind: str,
    source_runtime: dict[str, Any],
    confirm: bool,
    prepare_phase_runtime: Callable[..., dict[str, Any]],
    prepare_specialization_runtime: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    normalized_source = _coerce_dict(source_runtime)
    recommendation_id = str(normalized_source.get("recommendation_id") or "")
    recommendation_payload = _coerce_dict(normalized_source.get("recommendation_payload"))
    template_id = str(normalized_source.get("template_id") or "")
    current_phase = str(normalized_source.get("current_phase") or "")
    recommended_phase = str(normalized_source.get("recommended_phase") or "")
    progression_action = str(normalized_source.get("progression_action") or "")

    if decision_kind == "phase":
        runtime = prepare_phase_runtime(
            recommendation_id=recommendation_id,
            recommendation_payload=recommendation_payload,
            fallback_next_phase=recommended_phase,
            confirm=confirm,
            template_id=template_id,
            current_phase=current_phase,
            progression_action=progression_action,
        )
    elif decision_kind == "specialization":
        runtime = prepare_specialization_runtime(
            recommendation_id=recommendation_id,
            recommendation_payload=recommendation_payload,
            confirm=confirm,
            template_id=template_id,
            current_phase=current_phase,
            recommended_phase=recommended_phase,
            progression_action=progression_action,
        )
    else:
        raise ValueError("Unsupported coaching apply decision kind")

    decision_payload = _coerce_dict(_coerce_dict(runtime).get("decision_payload"))
    return {
        "decision_kind": decision_kind,
        "runtime": runtime,
        "decision_trace": {
            "interpreter": "prepare_coaching_apply_decision_runtime",
            "version": "v1",
            "inputs": {
                "decision_kind": decision_kind,
                "confirm": bool(confirm),
                "has_recommendation_payload": bool(recommendation_payload),
            },
            "outcome": {
                "recommendation_id": recommendation_id,
                "status": str(decision_payload.get("status") or ""),
            },
        },
    }


def interpret_coach_phase_apply_decision(
    *,
    recommendation_id: str,
    phase_transition: dict[str, Any],
    confirm: bool,
    humanize_phase_transition_reason: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    next_phase_raw = str(phase_transition.get("next_phase") or "").strip()
    allowed_phases = {"accumulation", "intensification", "deload"}
    if next_phase_raw not in allowed_phases:
        raise ValueError("Recommendation has unsupported next phase")

    reason = str(phase_transition.get("reason") or "phase_apply")
    rationale = str(phase_transition.get("rationale") or humanize_phase_transition_reason({"reason": reason}))
    status = "applied" if confirm else "confirmation_required"
    applied = bool(confirm)

    return {
        "status": status,
        "recommendation_id": recommendation_id,
        "requires_confirmation": not confirm,
        "applied": applied,
        "next_phase": next_phase_raw,
        "reason": reason,
        "rationale": rationale,
        "decision_trace": {
            "interpreter": "interpret_coach_phase_apply_decision",
            "version": "v1",
            "inputs": {
                "recommendation_id": recommendation_id,
                "confirm": confirm,
                "next_phase": next_phase_raw,
                "reason": reason,
            },
            "steps": [
                _decision_step("phase_transition_present", True, {"next_phase": next_phase_raw}),
                _decision_step("confirmation_received", confirm),
            ],
            "outcome": {
                "status": status,
                "applied": applied,
                "next_phase": next_phase_raw,
                "reason": reason,
                "rationale": rationale,
            },
        },
    }


def interpret_coach_specialization_apply_decision(
    *,
    recommendation_id: str,
    specialization: dict[str, Any],
    confirm: bool,
) -> dict[str, Any]:
    focus_muscles = [str(item) for item in specialization.get("focus_muscles") or []]
    focus_adjustments = {str(key): int(value) for key, value in (specialization.get("focus_adjustments") or {}).items()}
    donor_adjustments = {str(key): int(value) for key, value in (specialization.get("donor_adjustments") or {}).items()}
    uncompensated_added_sets = int(specialization.get("uncompensated_added_sets") or 0)

    status = "applied" if confirm else "confirmation_required"
    applied = bool(confirm)

    return {
        "status": status,
        "recommendation_id": recommendation_id,
        "requires_confirmation": not confirm,
        "applied": applied,
        "focus_muscles": focus_muscles,
        "focus_adjustments": focus_adjustments,
        "donor_adjustments": donor_adjustments,
        "uncompensated_added_sets": uncompensated_added_sets,
        "decision_trace": {
            "interpreter": "interpret_coach_specialization_apply_decision",
            "version": "v1",
            "inputs": {
                "recommendation_id": recommendation_id,
                "confirm": confirm,
                "focus_muscles": focus_muscles,
                "focus_adjustment_keys": sorted(focus_adjustments.keys()),
                "donor_adjustment_keys": sorted(donor_adjustments.keys()),
            },
            "steps": [
                _decision_step("specialization_present", True, {"focus_muscle_count": len(focus_muscles)}),
                _decision_step("confirmation_received", confirm),
            ],
            "outcome": {
                "status": status,
                "applied": applied,
                "focus_muscles": focus_muscles,
                "uncompensated_added_sets": uncompensated_added_sets,
            },
        },
    }


def build_phase_applied_recommendation_record(
    *,
    template_id: str,
    current_phase: str,
    progression_action: str,
    source_recommendation_id: str,
    next_phase: str,
) -> dict[str, Any]:
    return {
        "template_id": template_id,
        "recommendation_type": "phase_decision",
        "current_phase": current_phase,
        "recommended_phase": next_phase,
        "progression_action": progression_action,
        "request_payload": {
            "source_recommendation_id": source_recommendation_id,
            "confirm": True,
        },
        "status": "applied",
    }


def build_specialization_applied_recommendation_record(
    *,
    template_id: str,
    current_phase: str,
    recommended_phase: str,
    progression_action: str,
    source_recommendation_id: str,
) -> dict[str, Any]:
    return {
        "template_id": template_id,
        "recommendation_type": "specialization_decision",
        "current_phase": current_phase,
        "recommended_phase": recommended_phase,
        "progression_action": progression_action,
        "request_payload": {
            "source_recommendation_id": source_recommendation_id,
            "confirm": True,
        },
        "status": "applied",
    }


def recommend_specialization_adjustments(
    *,
    weekly_volume_by_muscle: dict[str, int],
    lagging_muscles: list[str],
    max_focus_muscles: int = 2,
    target_min_sets: int = 8,
) -> dict[str, Any]:
    normalized_lagging = {
        muscle.strip().lower()
        for muscle in lagging_muscles
        if muscle and muscle.strip().lower() in weekly_volume_by_muscle
    }
    ranked_focus = sorted(
        normalized_lagging,
        key=lambda muscle: (int(weekly_volume_by_muscle.get(muscle, 0)), muscle),
    )[: max(1, int(max_focus_muscles))]

    focus_adjustments: dict[str, int] = {}
    for muscle in ranked_focus:
        current_sets = int(weekly_volume_by_muscle.get(muscle, 0))
        focus_adjustments[muscle] = 2 if current_sets < target_min_sets else 1

    total_added_sets = sum(focus_adjustments.values())
    donor_candidates = sorted(
        [
            (muscle, int(sets))
            for muscle, sets in weekly_volume_by_muscle.items()
            if muscle not in ranked_focus and int(sets) > target_min_sets
        ],
        key=lambda row: (-row[1], row[0]),
    )

    donor_adjustments: dict[str, int] = {}
    remaining = total_added_sets
    for donor, sets in donor_candidates:
        if remaining <= 0:
            break
        allowed_drop = min(1, sets - target_min_sets)
        if allowed_drop <= 0:
            continue
        donor_adjustments[donor] = -allowed_drop
        remaining -= allowed_drop

    return {
        "focus_muscles": ranked_focus,
        "focus_adjustments": focus_adjustments,
        "donor_adjustments": donor_adjustments,
        "uncompensated_added_sets": max(0, remaining),
    }


def summarize_program_media_and_warmups(program_template: dict[str, Any]) -> dict[str, Any]:
    exercises: list[dict[str, Any]] = []
    for session in program_template.get("sessions", []):
        exercises.extend(session.get("exercises", []))

    total_exercises = len(exercises)
    with_video = 0
    sample_warmups: list[dict[str, Any]] = []

    for exercise in exercises:
        video = exercise.get("video") if isinstance(exercise.get("video"), dict) else {}
        if isinstance(video, dict) and str(video.get("youtube_url") or "").strip():
            with_video += 1

        start_weight = float(exercise.get("start_weight") or 0)
        if start_weight > 0 and len(sample_warmups) < 3:
            sample_warmups.append(
                {
                    "exercise_id": str(exercise.get("id") or ""),
                    "warmups": compute_warmups(start_weight),
                }
            )

    coverage_pct = round((with_video / total_exercises) * 100, 1) if total_exercises else 0.0
    return {
        "total_exercises": total_exercises,
        "video_linked_exercises": with_video,
        "video_coverage_pct": coverage_pct,
        "sample_warmups": sample_warmups,
    }


def finalize_applied_coaching_recommendation(
    *,
    payload_key: str,
    payload_value: dict[str, Any],
    decision_payload: dict[str, Any],
    applied_recommendation_id: str,
) -> dict[str, Any]:
    decision_trace = _coerce_dict(decision_payload.get("decision_trace"))
    outcome = _coerce_dict(decision_trace.get("outcome"))
    finalized_trace = {
        **decision_trace,
        "outcome": {
            **outcome,
            "applied_recommendation_id": applied_recommendation_id,
        },
    }
    return {
        "recommendation_payload": {
            payload_key: dict(payload_value),
            "decision_trace": finalized_trace,
        },
        "response_payload": {
            **decision_payload,
            "applied_recommendation_id": applied_recommendation_id,
            "decision_trace": finalized_trace,
        },
    }


def _coach_preview_schedule_payload(schedule: dict[str, Any], *, from_days: int, to_days: int) -> dict[str, Any]:
    return {
        "from_days": int(schedule.get("from_days") or from_days),
        "to_days": int(schedule.get("to_days") or to_days),
        "kept_sessions": [str(item) for item in schedule.get("kept_sessions") or []],
        "dropped_sessions": [str(item) for item in schedule.get("dropped_sessions") or []],
        "added_sessions": [str(item) for item in schedule.get("added_sessions") or []],
        "risk_level": str(schedule.get("risk_level") or "low"),
        "muscle_set_delta": {str(key): int(value) for key, value in (schedule.get("muscle_set_delta") or {}).items()},
        "tradeoffs": [str(item) for item in schedule.get("tradeoffs") or []],
    }


def _coach_preview_effective_readiness_score(
    *,
    readiness_state: dict[str, Any],
    preview_request: dict[str, Any],
    progression_payload: dict[str, Any],
    derive_readiness_score: Callable[..., int],
) -> tuple[int, str]:
    provided = preview_request.get("readiness_score")
    if provided is not None:
        return int(provided), "request_readiness_score"

    sleep_quality = readiness_state.get("sleep_quality")
    stress_level = readiness_state.get("stress_level")
    pain_flags = [str(item) for item in readiness_state.get("pain_flags") or [] if str(item).strip()]

    return derive_readiness_score(
        completion_pct=int(preview_request.get("completion_pct") or 0),
        adherence_score=int(preview_request.get("adherence_score") or 1),
        soreness_level=str(preview_request.get("soreness_level") or "none"),
        progression_action=str(progression_payload.get("action") or "hold"),
        sleep_quality=int(sleep_quality) if sleep_quality is not None else None,
        stress_level=int(stress_level) if stress_level is not None else None,
        pain_flags=pain_flags,
    ), ("context_coaching_state" if readiness_state else "request_metrics_only")


def _coach_preview_progression_payload(
    *,
    readiness_state: dict[str, Any],
    stagnation_weeks: int,
    preview_request: dict[str, Any],
    rule_set: dict[str, Any] | None,
    recommend_progression_action: Callable[..., dict[str, Any]],
    humanize_progression_reason: Callable[..., str],
) -> dict[str, Any]:
    sleep_quality = readiness_state.get("sleep_quality")
    stress_level = readiness_state.get("stress_level")
    pain_flags = [str(item) for item in readiness_state.get("pain_flags") or [] if str(item).strip()]

    progression = recommend_progression_action(
        completion_pct=int(preview_request.get("completion_pct") or 0),
        adherence_score=int(preview_request.get("adherence_score") or 1),
        soreness_level=str(preview_request.get("soreness_level") or "none"),
        average_rpe=preview_request.get("average_rpe"),
        consecutive_underperformance_weeks=int(stagnation_weeks),
        rule_set=rule_set,
        sleep_quality=int(sleep_quality) if sleep_quality is not None else None,
        stress_level=int(stress_level) if stress_level is not None else None,
        pain_flags=pain_flags,
    )
    return {
        **progression,
        "rationale": humanize_progression_reason(progression, rule_set=rule_set),
    }


def _resolve_coach_preview_canonical_state(
    context: dict[str, Any],
    preview_request: dict[str, Any],
) -> dict[str, Any]:
    coaching_state = _coerce_dict(context.get("coaching_state"))

    readiness_state = _coerce_dict(coaching_state.get("readiness"))
    readiness_source = "coaching_state.readiness"
    if not readiness_state:
        readiness_state = _coerce_dict(context.get("readiness_state"))
        readiness_source = "legacy_context.readiness_state" if readiness_state else "unavailable"

    stall_state = _coerce_dict(coaching_state.get("stall"))
    stall_source = "coaching_state.stall" if stall_state else "preview_request"

    mesocycle_state = _coerce_dict(coaching_state.get("mesocycle"))
    mesocycle_source = "coaching_state.mesocycle"
    if not mesocycle_state:
        mesocycle_state = _coerce_dict(context.get("latest_mesocycle"))
        mesocycle_source = "legacy_context.latest_mesocycle" if mesocycle_state else "unavailable"

    stagnation_weeks_raw = preview_request.get("stagnation_weeks")
    if stagnation_weeks_raw is not None:
        stagnation_weeks = int(stagnation_weeks_raw)
        stagnation_source = "preview_request"
    else:
        stagnation_weeks = int(
            stall_state.get("consecutive_underperformance_weeks")
            or stall_state.get("phase_stagnation_weeks")
            or 0
        )
        stagnation_source = "coaching_state.stall" if stall_state else "default_zero"

    return {
        "readiness_state": readiness_state,
        "stall_state": stall_state,
        "mesocycle_state": mesocycle_state,
        "readiness_source": readiness_source,
        "stall_source": stall_source,
        "mesocycle_source": mesocycle_source,
        "stagnation_weeks": stagnation_weeks,
        "stagnation_source": stagnation_source,
    }


def _coach_preview_trace(
    *,
    template_id: str,
    split_preference: str,
    phase: str,
    preview_request: dict[str, Any],
    canonical_state: dict[str, Any],
    schedule_payload: dict[str, Any],
    progression_payload: dict[str, Any],
    effective_readiness_score: int,
    effective_readiness_source: str,
    phase_transition_payload: dict[str, Any],
    specialization: dict[str, Any],
    media_warmups: dict[str, Any],
    request_runtime_trace: dict[str, Any] | None = None,
    template_runtime_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "interpreter": "recommend_coach_intelligence_preview",
        "version": "v1",
        "inputs": {
            "template_id": template_id,
            "split_preference": split_preference,
            "phase": phase,
            "from_days": int(preview_request.get("from_days") or 0),
            "to_days": int(preview_request.get("to_days") or 0),
            "completion_pct": int(preview_request.get("completion_pct") or 0),
            "adherence_score": int(preview_request.get("adherence_score") or 1),
            "soreness_level": str(preview_request.get("soreness_level") or "none"),
            "average_rpe": preview_request.get("average_rpe"),
            "current_phase": str(preview_request.get("current_phase") or "accumulation"),
            "weeks_in_phase": int(preview_request.get("weeks_in_phase") or 1),
            "stagnation_weeks": int(preview_request.get("stagnation_weeks") or 0),
            "readiness_score_provided": preview_request.get("readiness_score"),
            "lagging_muscles": [str(item) for item in preview_request.get("lagging_muscles") or []],
            "target_min_sets": int(preview_request.get("target_min_sets") or 8),
        },
        "steps": [
            {"decision": "schedule_adaptation", "result": schedule_payload},
            {
                "decision": "canonical_coaching_state",
                "result": {
                    "readiness_source": str(canonical_state.get("readiness_source") or "unavailable"),
                    "stall_source": str(canonical_state.get("stall_source") or "preview_request"),
                    "mesocycle_source": str(canonical_state.get("mesocycle_source") or "unavailable"),
                    "stagnation_source": str(canonical_state.get("stagnation_source") or "default_zero"),
                    "stagnation_weeks": int(canonical_state.get("stagnation_weeks") or 0),
                },
            },
            {"decision": "progression", "result": progression_payload},
            {
                "decision": "readiness_score",
                "result": {
                    "provided": preview_request.get("readiness_score") is not None,
                    "source": effective_readiness_source,
                    "value": effective_readiness_score,
                },
            },
            {"decision": "phase_transition", "result": phase_transition_payload},
            {"decision": "specialization", "result": specialization},
            {
                "decision": "media_warmups",
                "result": {
                    "total_exercises": int(media_warmups.get("total_exercises") or 0),
                    "video_linked_exercises": int(media_warmups.get("video_linked_exercises") or 0),
                    "video_coverage_pct": float(media_warmups.get("video_coverage_pct") or 0.0),
                    "sample_warmup_count": len(media_warmups.get("sample_warmups") or []),
                },
            },
        ],
        "outputs": {
            "template_id": template_id,
            "progression_action": progression_payload.get("action"),
            "next_phase": phase_transition_payload.get("next_phase"),
            "phase_transition_pending": bool(phase_transition_payload.get("transition_pending")),
            "focus_muscles": specialization.get("focus_muscles") or [],
            "risk_level": schedule_payload.get("risk_level"),
        },
        "request_runtime_trace": deepcopy(_coerce_dict(request_runtime_trace)),
        "template_runtime_trace": deepcopy(_coerce_dict(template_runtime_trace)),
    }


def recommend_coach_intelligence_preview(
    *,
    template_id: str,
    context: dict[str, Any],
    preview_request: dict[str, Any],
    rule_set: dict[str, Any] | None = None,
    request_runtime_trace: dict[str, Any] | None = None,
    template_runtime_trace: dict[str, Any] | None = None,
    evaluate_schedule_adaptation: Callable[..., dict[str, Any]],
    recommend_progression_action: Callable[..., dict[str, Any]],
    humanize_progression_reason: Callable[..., str],
    derive_readiness_score: Callable[..., int],
    recommend_phase_transition: Callable[..., dict[str, Any]],
    humanize_phase_transition_reason: Callable[..., str],
    recommend_specialization_adjustments: Callable[..., dict[str, Any]],
    summarize_program_media_and_warmups: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    split_preference = str(context.get("split_preference") or "full_body")
    program_template = _coerce_dict(context.get("program_template"))
    phase = str(context.get("phase") or "maintenance")
    from_days = int(preview_request.get("from_days") or 2)
    to_days = int(preview_request.get("to_days") or 2)

    schedule = evaluate_schedule_adaptation(
        user_profile=_coerce_dict(context.get("user_profile")),
        split_preference=split_preference,
        program_template=program_template,
        history=list(preview_request.get("history") or context.get("history") or []),
        phase=phase,
        from_days=from_days,
        to_days=to_days,
        available_equipment=context.get("available_equipment"),
    )
    schedule_payload = _coach_preview_schedule_payload(schedule, from_days=from_days, to_days=to_days)
    canonical_state = _resolve_coach_preview_canonical_state(context, preview_request)

    progression_payload = _coach_preview_progression_payload(
        readiness_state=_coerce_dict(canonical_state.get("readiness_state")),
        stagnation_weeks=int(canonical_state.get("stagnation_weeks") or 0),
        preview_request=preview_request,
        rule_set=rule_set,
        recommend_progression_action=recommend_progression_action,
        humanize_progression_reason=humanize_progression_reason,
    )

    effective_readiness_score, effective_readiness_source = _coach_preview_effective_readiness_score(
        readiness_state=_coerce_dict(canonical_state.get("readiness_state")),
        preview_request=preview_request,
        progression_payload=progression_payload,
        derive_readiness_score=derive_readiness_score,
    )
    latest_mesocycle = _coerce_dict(canonical_state.get("mesocycle_state"))

    phase_transition = recommend_phase_transition(
        current_phase=str(preview_request.get("current_phase") or "accumulation"),
        weeks_in_phase=int(preview_request.get("weeks_in_phase") or 1),
        readiness_score=effective_readiness_score,
        progression_action=str(progression_payload.get("action") or "hold"),
        stagnation_weeks=int(canonical_state.get("stagnation_weeks") or 0),
        rule_set=rule_set,
        authored_sequence_complete=bool(latest_mesocycle.get("authored_sequence_complete")),
        phase_transition_pending=bool(latest_mesocycle.get("phase_transition_pending")),
        phase_transition_reason=(
            str(latest_mesocycle.get("phase_transition_reason"))
            if str(latest_mesocycle.get("phase_transition_reason") or "").strip()
            else None
        ),
        post_authored_behavior=(
            str(latest_mesocycle.get("post_authored_behavior"))
            if str(latest_mesocycle.get("post_authored_behavior") or "").strip()
            else None
        ),
    )
    phase_transition_payload = {
        **phase_transition,
        "rationale": humanize_phase_transition_reason(phase_transition),
    }

    specialization = recommend_specialization_adjustments(
        weekly_volume_by_muscle=(schedule.get("to_plan") or {}).get("weekly_volume_by_muscle", {}),
        lagging_muscles=[str(item) for item in preview_request.get("lagging_muscles") or []],
        target_min_sets=int(preview_request.get("target_min_sets") or 8),
    )
    media_warmups = summarize_program_media_and_warmups(program_template)

    return {
        "template_id": template_id,
        "schedule": schedule_payload,
        "progression": progression_payload,
        "phase_transition": phase_transition_payload,
        "specialization": specialization,
        "media_warmups": media_warmups,
        "decision_trace": _coach_preview_trace(
            template_id=template_id,
            split_preference=split_preference,
            phase=phase,
            preview_request=preview_request,
            canonical_state=canonical_state,
            schedule_payload=schedule_payload,
            progression_payload=progression_payload,
            effective_readiness_score=effective_readiness_score,
            effective_readiness_source=effective_readiness_source,
            phase_transition_payload=phase_transition_payload,
            specialization=specialization,
            media_warmups=media_warmups,
            request_runtime_trace=request_runtime_trace,
            template_runtime_trace=template_runtime_trace,
        ),
    }


def resolve_coaching_recommendation_rationale(
    recommendation_payload: dict[str, Any],
    *,
    humanize_phase_transition_reason: Callable[[dict[str, Any]], str],
    humanize_progression_reason: Callable[[dict[str, Any]], str],
    humanize_specialization_reason: Callable[[dict[str, Any]], str],
) -> str:
    phase_transition = _coerce_dict(recommendation_payload.get("phase_transition"))
    progression = _coerce_dict(recommendation_payload.get("progression"))
    specialization = _coerce_dict(recommendation_payload.get("specialization"))

    for candidate in (
        phase_transition.get("rationale"),
        progression.get("rationale"),
    ):
        text = str(candidate or "").strip()
        if text:
            return text

    if str(phase_transition.get("reason") or "").strip():
        return humanize_phase_transition_reason(phase_transition)

    if str(progression.get("reason") or "").strip():
        return humanize_progression_reason(progression)

    specialization_rationale = humanize_specialization_reason(specialization)
    if specialization_rationale:
        return specialization_rationale

    return "No rationale recorded"


def humanize_specialization_reason(specialization: dict[str, Any]) -> str:
    for candidate in (
        specialization.get("rationale"),
        specialization.get("reason"),
    ):
        text = str(candidate or "").strip()
        if text:
            return text
    return ""


def resolve_authoritative_coaching_recommendation_rationale(recommendation_payload: dict[str, Any]) -> str:
    phase_transition = _coerce_dict(recommendation_payload.get("phase_transition"))
    progression = _coerce_dict(recommendation_payload.get("progression"))
    specialization = _coerce_dict(recommendation_payload.get("specialization"))

    for candidate in (
        phase_transition.get("rationale"),
        progression.get("rationale"),
        specialization.get("rationale"),
    ):
        text = str(candidate or "").strip()
        if text:
            return text

    for candidate in (
        phase_transition.get("reason"),
        progression.get("reason"),
        specialization.get("reason"),
    ):
        text = str(candidate or "").strip()
        if text:
            return text

    return "No rationale recorded"


def extract_coaching_recommendation_focus_muscles(recommendation_payload: dict[str, Any]) -> list[str]:
    specialization = _coerce_dict(recommendation_payload.get("specialization"))
    raw_focus = specialization.get("focus_muscles")
    if not isinstance(raw_focus, list):
        return []
    return [str(item) for item in raw_focus if str(item).strip()]


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
    created_at: Any,
    applied_at: Any,
    humanize_phase_transition_reason: Callable[[dict[str, Any]], str],
    humanize_progression_reason: Callable[[dict[str, Any]], str],
    humanize_specialization_reason: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    payload = _coerce_dict(recommendation_payload)
    return {
        "recommendation_id": recommendation_id,
        "recommendation_type": recommendation_type,
        "status": status,
        "template_id": template_id,
        "current_phase": current_phase,
        "recommended_phase": recommended_phase,
        "progression_action": progression_action,
        "rationale": resolve_coaching_recommendation_rationale(
            payload,
            humanize_phase_transition_reason=humanize_phase_transition_reason,
            humanize_progression_reason=humanize_progression_reason,
            humanize_specialization_reason=humanize_specialization_reason,
        ),
        "focus_muscles": extract_coaching_recommendation_focus_muscles(payload),
        "created_at": created_at,
        "applied_at": applied_at,
    }


def normalize_coaching_recommendation_timeline_limit(limit: int) -> int:
    return max(1, min(100, int(limit)))


def build_coaching_recommendation_timeline_payload(
    rows: list[Any],
    *,
    humanize_phase_transition_reason: Callable[[dict[str, Any]], str],
    humanize_progression_reason: Callable[[dict[str, Any]], str],
    humanize_specialization_reason: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    entries = [
        build_coaching_recommendation_timeline_entry(
            recommendation_id=str(_read_attr(row, "id", "") or ""),
            recommendation_type=str(_read_attr(row, "recommendation_type", "") or ""),
            status=str(_read_attr(row, "status", "") or ""),
            template_id=str(_read_attr(row, "template_id", "") or ""),
            current_phase=str(_read_attr(row, "current_phase", "") or ""),
            recommended_phase=str(_read_attr(row, "recommended_phase", "") or ""),
            progression_action=str(_read_attr(row, "progression_action", "") or ""),
            recommendation_payload=_coerce_dict(_read_attr(row, "recommendation_payload", {})),
            created_at=_read_attr(row, "created_at"),
            applied_at=_read_attr(row, "applied_at"),
            humanize_phase_transition_reason=humanize_phase_transition_reason,
            humanize_progression_reason=humanize_progression_reason,
            humanize_specialization_reason=humanize_specialization_reason,
        )
        for row in rows
    ]
    return {"entries": entries}


def build_applied_coaching_recommendation_response(
    *,
    payload_key: str,
    payload_value: dict[str, Any],
    decision_payload: dict[str, Any],
    applied_recommendation_id: str,
) -> dict[str, Any]:
    return finalize_applied_coaching_recommendation(
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
    return {
        "user_id": user_id,
        "recommendation_payload": {},
        "applied_at": applied_at,
        **dict(record_fields),
    }


def prepare_applied_coaching_recommendation_commit_runtime(
    *,
    user_id: str,
    applied_at: Any,
    record_fields: dict[str, Any],
    payload_key: str,
    payload_value: dict[str, Any],
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "record_values": build_applied_coaching_recommendation_record_values(
            user_id=user_id,
            applied_at=applied_at,
            record_fields=record_fields,
        ),
        "payload_runtime": {
            "payload_key": str(payload_key),
            "payload_value": dict(payload_value),
            "decision_payload": dict(decision_payload),
        },
        "decision_trace": {
            "interpreter": "prepare_applied_coaching_recommendation_commit_runtime",
            "version": "v1",
            "outcome": {
                "recommendation_type": str(record_fields.get("recommendation_type") or ""),
                "payload_key": str(payload_key),
            },
        },
    }


def prepare_coaching_apply_commit_runtime(
    *,
    decision_kind: str,
    user_id: str,
    applied_at: Any,
    apply_runtime: dict[str, Any],
) -> dict[str, Any]:
    payload_key_by_kind = {
        "phase": "phase_transition",
        "specialization": "specialization",
    }
    payload_key = payload_key_by_kind.get(decision_kind)
    if payload_key is None:
        raise ValueError("Unsupported coaching apply decision kind")

    runtime = _coerce_dict(apply_runtime)
    return prepare_applied_coaching_recommendation_commit_runtime(
        user_id=user_id,
        applied_at=applied_at,
        record_fields=_coerce_dict(runtime.get("record_fields")),
        payload_key=payload_key,
        payload_value=_coerce_dict(runtime.get("payload_value")),
        decision_payload=_coerce_dict(runtime.get("decision_payload")),
    )


def prepare_coaching_apply_route_runtime(
    *,
    decision_kind: str,
    source_runtime: dict[str, Any],
    confirm: bool,
    user_id: str,
    applied_at: Any,
    prepare_apply_decision_runtime: Callable[..., dict[str, Any]],
    prepare_apply_commit_runtime: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    decision_runtime = prepare_apply_decision_runtime(
        decision_kind=decision_kind,
        source_runtime=source_runtime,
        confirm=confirm,
    )
    apply_runtime = _coerce_dict(decision_runtime.get("runtime"))
    response_payload = _coerce_dict(apply_runtime.get("decision_payload"))
    route_runtime: dict[str, Any] = {
        "decision_runtime": decision_runtime,
        "apply_runtime": apply_runtime,
        "response_payload": response_payload,
    }
    if confirm:
        route_runtime["commit_runtime"] = prepare_apply_commit_runtime(
            decision_kind=decision_kind,
            user_id=user_id,
            applied_at=applied_at,
            apply_runtime=apply_runtime,
        )
    return route_runtime


def finalize_applied_coaching_recommendation_commit_runtime(
    *,
    prepared_runtime: dict[str, Any],
    applied_recommendation_id: str,
) -> dict[str, Any]:
    payload_runtime = _coerce_dict(prepared_runtime.get("payload_runtime"))
    return build_applied_coaching_recommendation_response(
        payload_key=str(payload_runtime.get("payload_key") or ""),
        payload_value=_coerce_dict(payload_runtime.get("payload_value")),
        decision_payload=_coerce_dict(payload_runtime.get("decision_payload")),
        applied_recommendation_id=applied_recommendation_id,
    )


def prepare_coaching_apply_route_finalize_runtime(
    *,
    route_runtime: dict[str, Any],
    applied_recommendation_id: str | None = None,
) -> dict[str, Any]:
    commit_runtime = route_runtime.get("commit_runtime")
    if not isinstance(commit_runtime, dict):
        response_payload = deepcopy(_coerce_dict(route_runtime.get("response_payload")))
        return {
            "response_payload": response_payload,
            "recommendation_payload": None,
            "decision_trace": {
                "interpreter": "prepare_coaching_apply_route_finalize_runtime",
                "version": "v1",
                "inputs": {
                    "has_commit_runtime": False,
                    "applied_recommendation_id": None,
                },
                "outcome": {
                    "status": str(response_payload.get("status") or ""),
                    "has_recommendation_payload": False,
                },
            },
        }

    if not isinstance(applied_recommendation_id, str) or not applied_recommendation_id.strip():
        raise ValueError("applied_recommendation_id is required when commit runtime is present")

    finalized = finalize_applied_coaching_recommendation_commit_runtime(
        prepared_runtime=commit_runtime,
        applied_recommendation_id=applied_recommendation_id,
    )
    response_payload = deepcopy(_coerce_dict(finalized.get("response_payload")))
    recommendation_payload = deepcopy(_coerce_dict(finalized.get("recommendation_payload")))
    return {
        "response_payload": response_payload,
        "recommendation_payload": recommendation_payload,
        "decision_trace": {
            "interpreter": "prepare_coaching_apply_route_finalize_runtime",
            "version": "v1",
            "inputs": {
                "has_commit_runtime": True,
                "applied_recommendation_id": applied_recommendation_id,
            },
            "outcome": {
                "status": str(response_payload.get("status") or ""),
                "has_recommendation_payload": bool(recommendation_payload),
            },
        },
    }
