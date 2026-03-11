from __future__ import annotations

from datetime import datetime
from typing import Any, cast


_PROGRAM_REASON_MESSAGES = {
    "no_compatible_programs": "No compatible program was found for the current availability, so keep the current selection.",
    "current_not_compatible": "The current program no longer matches the available training days or split preference. Move to the first compatible option.",
    "low_adherence_keep_program": "Recent adherence is low. Keep the current program stable before rotating templates.",
    "days_adaptation_upgrade": "A different compatible template can preserve weekly coverage better at the current day availability.",
    "coverage_gap_rotate": "The latest plan left a coverage gap. Rotate to a compatible template with better distribution.",
    "mesocycle_complete_rotate": "The current authored mesocycle appears complete. Rotate to a fresh compatible template instead of extending the same block indefinitely.",
    "maintain_current_program": "The current program remains compatible and no stronger rotation signal is present.",
    "target_matches_current": "The requested program already matches the current selection.",
}


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_training_state(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_attr(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _looks_like_human_rationale(value: str) -> bool:
    text = value.strip()
    return bool(text) and "_" not in text and "+" not in text


def humanize_program_reason(reason: str) -> str:
    normalized = reason.strip()
    if not normalized:
        return "No rationale recorded."
    if _looks_like_human_rationale(normalized):
        return normalized
    return _PROGRAM_REASON_MESSAGES.get(normalized, normalized.replace("_", " ").capitalize() + ".")


def _is_program_adaptation_upgrade(summary: dict[str, Any], days_available: int) -> bool:
    if days_available < 2 or days_available > 4:
        return False
    return int(summary.get("session_count") or 0) >= 5


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


def resolve_program_recommendation_candidates(
    *,
    available_program_summaries: list[dict[str, Any]],
    days_available: int,
    split_preference: str,
) -> dict[str, Any]:
    compatible = [
        item for item in available_program_summaries if days_available in (item.get("days_supported") or [])
    ]
    source = compatible if compatible else available_program_summaries
    compatibility_mode = "days_supported_match" if compatible else "fallback_all_templates"
    ordered_summaries = sorted(
        source,
        key=lambda item: _program_catalog_rank(
            item,
            days_available=days_available,
            split_preference=split_preference,
        ),
    )
    compatible_program_ids = [str(item.get("id") or "") for item in ordered_summaries]
    compatible_program_ids = [item for item in compatible_program_ids if item]
    return {
        "compatible_program_summaries": ordered_summaries,
        "compatible_program_ids": compatible_program_ids,
        "decision_trace": {
            "interpreter": "resolve_program_recommendation_candidates",
            "days_available": int(days_available),
            "split_preference": split_preference,
            "compatibility_mode": compatibility_mode,
            "available_program_ids": [str(item.get("id") or "") for item in available_program_summaries if str(item.get("id") or "")],
            "compatible_program_ids": compatible_program_ids,
        },
    }


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

    if bool(mesocycle.get("authored_sequence_complete")) or bool(mesocycle.get("phase_transition_pending")):
        index = compatible_program_ids.index(current_program_id)
        next_index = (index + 1) % len(compatible_program_ids)
        recommended = compatible_program_ids[next_index]
        return recommended if recommended != current_program_id else None

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
    latest_mesocycle = _coerce_dict(generation_state.get("latest_mesocycle"))
    if week_index is not None or trigger_weeks_effective is not None or latest_mesocycle:
        resolved_payload["mesocycle"] = {
            **_coerce_dict(resolved_payload.get("mesocycle")),
            **({"week_index": int(week_index)} if week_index is not None else {}),
            **(
                {"trigger_weeks_effective": int(trigger_weeks_effective)}
                if trigger_weeks_effective is not None
                else {}
            ),
            **latest_mesocycle,
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
    mesocycle = latest_plan_payload.get("mesocycle") if isinstance(latest_plan_payload.get("mesocycle"), dict) else {}
    explicit_mesocycle_complete = bool(
        mesocycle.get("authored_sequence_complete") or mesocycle.get("phase_transition_pending")
    )
    steps = [
        _decision_step("current_not_compatible", False),
        _decision_step(
            "low_adherence_keep_program",
            False,
            {"latest_adherence_score": latest_adherence_score},
        ),
    ]

    if explicit_mesocycle_complete:
        rotated = _rotate_for_program_mesocycle_completion(
            current_program_id,
            compatible_program_ids,
            latest_plan_payload,
        )
        steps.append(
            _decision_step(
                "mesocycle_complete_rotate",
                bool(rotated),
                {
                    "candidate_program_id": rotated,
                    "week_index": int(mesocycle.get("week_index", 1) or 1),
                    "trigger_weeks_effective": int(mesocycle.get("trigger_weeks_effective", 6) or 6),
                    "authored_sequence_complete": bool(mesocycle.get("authored_sequence_complete")),
                    "phase_transition_pending": bool(mesocycle.get("phase_transition_pending")),
                },
            )
        )
        if rotated:
            return "mesocycle_complete_rotate", rotated, steps

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
    steps.append(
        _decision_step(
            "mesocycle_complete_rotate",
            bool(rotated),
            {
                "candidate_program_id": rotated,
                "week_index": int(mesocycle.get("week_index", 1) or 1),
                "trigger_weeks_effective": int(mesocycle.get("trigger_weeks_effective", 6) or 6),
                "authored_sequence_complete": bool(mesocycle.get("authored_sequence_complete")),
                "phase_transition_pending": bool(mesocycle.get("phase_transition_pending")),
            },
        )
    )
    if rotated:
        return "mesocycle_complete_rotate", rotated, steps

    steps.append(_decision_step("maintain_current_program", True))
    return "maintain_current_program", current_program_id, steps


def recommend_program_selection(
    *,
    current_program_id: str,
    compatible_program_summaries: list[dict[str, Any]],
    days_available: int,
    latest_adherence_score: int | None,
    latest_plan_payload: dict[str, Any],
    context_sources: dict[str, str] | None = None,
) -> dict[str, Any]:
    compatible_program_ids = _compatible_program_ids(compatible_program_summaries)
    initial_decision = _program_selection_initial_decision(
        current_program_id=current_program_id,
        compatible_program_ids=compatible_program_ids,
        latest_adherence_score=latest_adherence_score,
    )
    if initial_decision is not None:
        reason, recommended_program_id, steps = initial_decision
    else:
        reason, recommended_program_id, steps = _program_selection_rotation_decision(
            current_program_id=current_program_id,
            compatible_program_ids=compatible_program_ids,
            compatible_program_summaries=compatible_program_summaries,
            days_available=days_available,
            latest_adherence_score=latest_adherence_score,
            latest_plan_payload=latest_plan_payload,
        )

    rationale = humanize_program_reason(reason)
    return {
        "current_program_id": current_program_id,
        "recommended_program_id": recommended_program_id,
        "reason": reason,
        "rationale": rationale,
        "compatible_program_ids": compatible_program_ids,
        "decision_trace": {
            "interpreter": "recommend_program_selection",
            "version": "v1",
            "inputs": {
                "current_program_id": current_program_id,
                "days_available": days_available,
                "latest_adherence_score": latest_adherence_score,
                "latest_adherence_score_source": str((context_sources or {}).get("latest_adherence_score_source") or "unknown"),
                "under_target_muscles_source": str((context_sources or {}).get("under_target_muscles_source") or "unknown"),
                "mesocycle_context_source": str((context_sources or {}).get("mesocycle_context_source") or "unknown"),
                "compatible_program_ids": compatible_program_ids,
            },
            "steps": steps,
            "selected_program_id": recommended_program_id,
            "reason": reason,
            "rationale": rationale,
        },
    }


def build_program_recommendation_payload(
    *,
    decision: dict[str, Any],
    candidate_resolution_trace: dict[str, Any],
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        "current_program_id": str(decision.get("current_program_id") or ""),
        "recommended_program_id": str(decision.get("recommended_program_id") or ""),
        "reason": str(decision.get("reason") or ""),
        "rationale": str(decision.get("rationale") or ""),
        "decision_trace": {
            **dict(_coerce_dict(decision.get("decision_trace"))),
            "candidate_resolution": dict(candidate_resolution_trace),
        },
        "compatible_program_ids": [
            str(program_id)
            for program_id in decision.get("compatible_program_ids") or []
            if str(program_id)
        ],
        "generated_at": generated_at,
    }


def prepare_program_recommendation_runtime(
    *,
    current_program_id: str,
    available_program_summaries: list[dict[str, Any]],
    days_available: int,
    split_preference: str,
    latest_adherence_score: int | None,
    latest_plan_payload: dict[str, Any],
    user_training_state: dict[str, Any] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    normalized_training_state = _coerce_training_state(user_training_state)
    resolved_adherence_score, adherence_source = _resolve_program_recommendation_adherence_score(
        user_training_state=normalized_training_state,
        latest_adherence_score=latest_adherence_score,
    )
    resolved_plan_payload, plan_context_sources = _resolve_program_recommendation_plan_context(
        user_training_state=normalized_training_state,
        latest_plan_payload=latest_plan_payload,
    )
    candidate_resolution = resolve_program_recommendation_candidates(
        available_program_summaries=available_program_summaries,
        days_available=days_available,
        split_preference=split_preference,
    )
    compatible_program_summaries = list(candidate_resolution["compatible_program_summaries"])
    compatible_program_ids = list(candidate_resolution["compatible_program_ids"])
    candidate_resolution_trace = dict(candidate_resolution["decision_trace"])
    decision = recommend_program_selection(
        current_program_id=current_program_id,
        compatible_program_summaries=compatible_program_summaries,
        days_available=days_available,
        latest_adherence_score=resolved_adherence_score,
        latest_plan_payload=resolved_plan_payload,
        context_sources={
            "latest_adherence_score_source": adherence_source,
            **plan_context_sources,
        },
    )

    runtime_payload: dict[str, Any] = {
        "decision": decision,
        "compatible_program_ids": compatible_program_ids,
        "candidate_resolution_trace": candidate_resolution_trace,
    }
    if generated_at is not None:
        runtime_payload["response_payload"] = build_program_recommendation_payload(
            decision=decision,
            candidate_resolution_trace=candidate_resolution_trace,
            generated_at=generated_at,
        )
    return runtime_payload


def prepare_profile_program_recommendation_inputs(
    *,
    selected_program_id: str | None,
    days_available: int | None,
    split_preference: str | None,
    latest_plan: Any | None,
) -> dict[str, Any]:
    latest_plan_payload = _coerce_dict(_read_attr(latest_plan, "payload", {}))
    return {
        "current_program_id": selected_program_id or "full_body_v1",
        "days_available": days_available or 2,
        "split_preference": split_preference or "full_body",
        "latest_plan_payload": latest_plan_payload,
    }


def prepare_profile_program_recommendation_route_runtime(
    *,
    selected_program_id: str | None,
    days_available: int | None,
    split_preference: str | None,
    latest_plan: Any | None,
    available_program_summaries: list[dict[str, Any]],
    latest_adherence_score: int | None,
    user_training_state: dict[str, Any] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    recommendation_inputs = prepare_profile_program_recommendation_inputs(
        selected_program_id=selected_program_id,
        days_available=days_available,
        split_preference=split_preference,
        latest_plan=latest_plan,
    )
    recommendation_runtime = prepare_program_recommendation_runtime(
        current_program_id=cast(str, recommendation_inputs["current_program_id"]),
        available_program_summaries=available_program_summaries,
        days_available=cast(int, recommendation_inputs["days_available"]),
        split_preference=cast(str, recommendation_inputs["split_preference"]),
        latest_adherence_score=latest_adherence_score,
        latest_plan_payload=cast(dict[str, Any], recommendation_inputs["latest_plan_payload"]),
        user_training_state=user_training_state,
        generated_at=generated_at,
    )
    decision = _coerce_dict(recommendation_runtime.get("decision"))
    return {
        "recommendation_inputs": recommendation_inputs,
        "recommendation_runtime": recommendation_runtime,
        "decision_trace": {
            "interpreter": "prepare_profile_program_recommendation_route_runtime",
            "version": "v1",
            "inputs": {
                "selected_program_id": selected_program_id,
                "days_available": days_available,
                "split_preference": split_preference,
                "generated_at_provided": generated_at is not None,
            },
            "outcome": {
                "current_program_id": recommendation_inputs["current_program_id"],
                "compatible_program_count": len(recommendation_runtime.get("compatible_program_ids") or []),
                "recommended_program_id": str(decision.get("recommended_program_id") or ""),
            },
        },
    }


def build_program_switch_payload(
    *,
    current_program_id: str,
    target_program_id: str,
    confirm: bool,
    decision: dict[str, Any],
    candidate_resolution_trace: dict[str, Any],
) -> dict[str, Any]:
    recommended_program_id = str(decision.get("recommended_program_id") or "")
    status = "switched"
    reason = str(decision.get("reason") or "")
    rationale = str(decision.get("rationale") or "")
    requires_confirmation = False
    applied = True

    if target_program_id == current_program_id:
        status = "unchanged"
        reason = "target_matches_current"
        rationale = humanize_program_reason(reason)
        applied = False
    elif not confirm:
        status = "confirmation_required"
        requires_confirmation = True
        applied = False

    return {
        "status": status,
        "current_program_id": current_program_id,
        "target_program_id": target_program_id,
        "recommended_program_id": recommended_program_id,
        "reason": reason,
        "rationale": rationale,
        "decision_trace": {
            **dict(_coerce_dict(decision.get("decision_trace"))),
            "candidate_resolution": dict(candidate_resolution_trace),
            "switch_request": {"target_program_id": target_program_id, "confirm": confirm},
            "switch_outcome": {"status": status, "reason": reason},
        },
        "requires_confirmation": requires_confirmation,
        "applied": applied,
    }


def prepare_program_switch_runtime(
    *,
    current_program_id: str,
    target_program_id: str,
    confirm: bool,
    compatible_program_ids: list[str],
    decision: dict[str, Any],
    candidate_resolution_trace: dict[str, Any],
) -> dict[str, Any]:
    normalized_compatible_program_ids = [str(program_id) for program_id in compatible_program_ids if str(program_id)]
    if target_program_id not in normalized_compatible_program_ids:
        raise ValueError("Target program is not compatible")

    response_payload = build_program_switch_payload(
        current_program_id=current_program_id,
        target_program_id=target_program_id,
        confirm=confirm,
        decision=decision,
        candidate_resolution_trace=candidate_resolution_trace,
    )
    return {
        "response_payload": response_payload,
        "should_apply": bool(confirm and target_program_id != current_program_id),
    }
