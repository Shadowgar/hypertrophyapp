from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from .onboarding_adaptation import adapt_onboarding_frequency


_PHASE1_PROGRAM_ID = "pure_bodybuilding_phase_1_full_body"
_PHASE1_5_TO_3_POLICY_ID = "pure_bodybuilding_phase_1_full_body_5_to_3"
_PHASE1_5_TO_3_PRESERVATION_FOCUS = [
    "full_body_intent",
    "weak_point_intent",
    "progression_continuity",
]


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalized_weak_areas(values: list[str] | None) -> list[str]:
    normalized = [str(item).strip().lower() for item in (values or []) if str(item).strip()]
    return list(dict.fromkeys(normalized))


def _normalized_string_list(values: list[Any] | None) -> list[str]:
    normalized = [str(item).strip() for item in (values or []) if str(item).strip()]
    return list(dict.fromkeys(normalized))


def _stripped_string_list(values: list[Any] | None) -> list[str]:
    return [str(item).strip() for item in (values or []) if str(item).strip()]


def _resolve_week_template(
    *,
    onboarding_package: dict[str, Any],
    week_index: int,
) -> dict[str, Any] | None:
    blueprint = _coerce_dict(onboarding_package.get("blueprint"))
    week_sequence = [str(item).strip() for item in blueprint.get("week_sequence") or [] if str(item).strip()]
    if not week_sequence:
        return None
    template_id = week_sequence[(max(1, int(week_index)) - 1) % len(week_sequence)]
    week_templates = {
        str(item.get("week_template_id") or "").strip(): item
        for item in blueprint.get("week_templates") or []
        if isinstance(item, dict) and str(item.get("week_template_id") or "").strip()
    }
    candidate = week_templates.get(template_id)
    return candidate if isinstance(candidate, dict) else None


def _should_apply_phase1_5_to_3_policy(
    *,
    onboarding_package: dict[str, Any],
    current_days: int,
    target_days: int,
) -> bool:
    blueprint = _coerce_dict(onboarding_package.get("blueprint"))
    default_training_days = int(
        blueprint.get("default_training_days")
        or _coerce_dict(onboarding_package.get("frequency_adaptation_rules")).get("default_training_days")
        or 0
    )
    return (
        str(onboarding_package.get("program_id") or "").strip() == _PHASE1_PROGRAM_ID
        and int(current_days) == 5
        and int(target_days) == 3
        and default_training_days == 5
    )


def _decorate_phase1_5_to_3_week(
    *,
    week_result: dict[str, Any],
    week_template: dict[str, Any] | None,
) -> dict[str, Any]:
    decorated = dict(week_result)
    template = week_template or {}
    days_by_id = {
        str(day.get("day_id") or "").strip(): day
        for day in template.get("days") or []
        if isinstance(day, dict) and str(day.get("day_id") or "").strip()
    }

    decorated["week_label"] = str(template.get("week_label") or "").strip() or None
    decorated["block_label"] = str(template.get("block_label") or "").strip() or None
    decorated["special_banners"] = _stripped_string_list(template.get("special_banners"))
    decorated["program_policy"] = _PHASE1_5_TO_3_POLICY_ID
    decorated["preservation_focus"] = list(_PHASE1_5_TO_3_PRESERVATION_FOCUS)
    action_summary = Counter(
        str(decision.get("action") or "").strip().lower()
        for decision in decorated.get("decisions") or []
        if str(decision.get("action") or "").strip()
    )
    decorated["action_summary"] = {action: count for action, count in sorted(action_summary.items()) if count > 0}

    adapted_days: list[dict[str, Any]] = []
    for day in decorated.get("adapted_days") or []:
        adapted_day = dict(day)
        source_day_ids = _normalized_string_list(adapted_day.get("source_day_ids"))
        source_days = [days_by_id[source_day_id] for source_day_id in source_day_ids if source_day_id in days_by_id]
        source_day_names = _normalized_string_list(
            [
                source_day.get("day_name") or source_day.get("label") or source_day.get("day_id")
                for source_day in source_days
            ]
        )
        source_day_roles = _normalized_string_list([source_day.get("day_role") for source_day in source_days])
        anchor_day = days_by_id.get(str(adapted_day.get("day_id") or "").strip(), {})
        anchor_day_name = str(anchor_day.get("day_name") or anchor_day.get("label") or adapted_day.get("day_id") or "").strip()

        adapted_day["source_day_names"] = source_day_names
        adapted_day["source_day_roles"] = source_day_roles
        adapted_day["day_role"] = str(anchor_day.get("day_role") or "").strip() or None
        adapted_day["day_name"] = " + ".join(source_day_names) if len(source_day_names) > 1 else (source_day_names[0] if source_day_names else anchor_day_name or None)
        adapted_days.append(adapted_day)

    decorated["adapted_days"] = adapted_days
    return decorated


def _build_phase1_5_to_3_policy_trace(weeks: list[dict[str, Any]]) -> dict[str, Any]:
    first_week = weeks[0] if weeks else {}
    adapted_days = first_week.get("adapted_days") or []
    preserved_day_roles = [
        str(day.get("day_role") or "").strip()
        for day in adapted_days
        if str(day.get("day_role") or "").strip()
    ]
    merged_day_roles: list[dict[str, str]] = []
    for day in adapted_days:
        target_day_role = str(day.get("day_role") or "").strip()
        if not target_day_role:
            continue
        for source_day_role in _normalized_string_list(day.get("source_day_roles")):
            if source_day_role != target_day_role:
                merged_day_roles.append(
                    {
                        "source_day_role": source_day_role,
                        "target_day_role": target_day_role,
                    }
                )
    return {
        "policy_mode": "program_specific",
        "policy_id": _PHASE1_5_TO_3_POLICY_ID,
        "preservation_focus": list(_PHASE1_5_TO_3_PRESERVATION_FOCUS),
        "preserved_day_roles": preserved_day_roles,
        "merged_day_roles": merged_day_roles,
    }


def _resolve_frequency_adaptation_context(
    *,
    explicit_weak_areas: list[str] | None,
    stored_weak_areas: list[str] | None,
    equipment_profile: list[str] | None,
    recovery_state: str,
    current_week_index: int,
) -> dict[str, Any]:
    resolved_weak_areas = _normalized_weak_areas(explicit_weak_areas)
    weak_area_source = "request"
    if not resolved_weak_areas:
        resolved_weak_areas = _normalized_weak_areas(stored_weak_areas)
        weak_area_source = "profile"
    return {
        "weak_areas": resolved_weak_areas,
        "weak_area_source": weak_area_source,
        "equipment_profile": list(equipment_profile or []),
        "recovery_state": recovery_state,
        "current_week_index": int(current_week_index),
    }


def recommend_frequency_adaptation_preview(
    *,
    onboarding_package: dict[str, Any],
    program_id: str,
    template_id: str | None = None,
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
    adaptation_rules = _coerce_dict(onboarding_package.get("frequency_adaptation_rules"))
    weak_area_bonus_slots = max(0, int(adaptation_rules.get("weak_area_bonus_slots") or 1))
    resolved_context = _resolve_frequency_adaptation_context(
        explicit_weak_areas=explicit_weak_areas,
        stored_weak_areas=stored_weak_areas,
        equipment_profile=equipment_profile,
        recovery_state=recovery_state,
        current_week_index=current_week_index,
    )
    resolved_weak_areas = list(resolved_context["weak_areas"])

    overlay = {
        "available_training_days": int(target_days),
        "temporary_duration_weeks": int(duration_weeks),
        "weak_areas": [
            {
                "muscle_group": item,
                "priority": 5,
                "desired_extra_slots_per_week": weak_area_bonus_slots,
            }
            for item in resolved_weak_areas
        ],
        "equipment_limits": list(resolved_context["equipment_profile"]),
        "recovery_state": str(resolved_context["recovery_state"]),
        "current_week_index": int(resolved_context["current_week_index"]),
    }
    result = dict(adapt_onboarding_frequency(onboarding_package=onboarding_package, overlay=overlay))
    policy_trace: dict[str, Any] = {
        "policy_mode": "generic",
        "policy_id": None,
        "preservation_focus": [],
        "preserved_day_roles": [],
        "merged_day_roles": [],
    }
    if _should_apply_phase1_5_to_3_policy(
        onboarding_package=onboarding_package,
        current_days=current_days,
        target_days=target_days,
    ):
        decorated_weeks: list[dict[str, Any]] = []
        for week in result.get("weeks") or []:
            week_dict = dict(week)
            week_template = _resolve_week_template(
                onboarding_package=onboarding_package,
                week_index=int(week_dict.get("week_index") or current_week_index),
            )
            decorated_weeks.append(
                _decorate_phase1_5_to_3_week(
                    week_result=week_dict,
                    week_template=week_template,
                )
            )
        result["weeks"] = decorated_weeks
        policy_trace = _build_phase1_5_to_3_policy_trace(decorated_weeks)
    result["decision_trace"] = {
        "interpreter": "recommend_frequency_adaptation_preview",
        "version": "v1",
        "program_id": program_id,
        "request": {
            "current_days": int(current_days),
            "target_days": int(target_days),
            "duration_weeks": int(duration_weeks),
        },
        "resolved_context": dict(resolved_context),
        "steps": [
            {
                "decision": "resolved_context",
                "result": {
                    "weak_area_source": resolved_context["weak_area_source"],
                    "weak_area_count": len(resolved_weak_areas),
                    "weak_area_bonus_slots": weak_area_bonus_slots,
                    "equipment_profile_count": len(resolved_context["equipment_profile"]),
                },
            },
            {
                "decision": "generate_preview",
                "result": {
                    "week_count": len(result.get("weeks") or []),
                    "rejoin_policy": result.get("rejoin_policy"),
                },
            },
            {
                "decision": "apply_program_policy",
                "result": dict(policy_trace),
            },
        ],
        "outcome": {
            "week_count": len(result.get("weeks") or []),
            "rejoin_policy": result.get("rejoin_policy"),
            "reason_code": "preview_generated",
            "weak_area_bonus_slots": weak_area_bonus_slots,
            **policy_trace,
        },
        "request_runtime_trace": deepcopy(_coerce_dict(request_runtime_trace)),
    }
    return result


def interpret_frequency_adaptation_apply(
    *,
    onboarding_package: dict[str, Any],
    program_id: str,
    template_id: str | None = None,
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
    preview = recommend_frequency_adaptation_preview(
        onboarding_package=onboarding_package,
        program_id=program_id,
        current_days=int(current_days),
        target_days=target_days,
        duration_weeks=duration_weeks,
        explicit_weak_areas=explicit_weak_areas,
        stored_weak_areas=stored_weak_areas,
        equipment_profile=equipment_profile,
        recovery_state=recovery_state,
        current_week_index=current_week_index,
        request_runtime_trace=request_runtime_trace,
    )
    preview_trace = _coerce_dict(preview.get("decision_trace"))
    resolved_context = _coerce_dict(preview_trace.get("resolved_context"))
    resolved_weak_areas = [
        str(item).strip().lower()
        for item in (resolved_context.get("weak_areas") or preview.get("weak_areas") or [])
        if str(item).strip()
    ]
    resolved_weak_areas = list(dict.fromkeys(resolved_weak_areas))
    decision_trace = {
        "interpreter": "interpret_frequency_adaptation_apply",
        "version": "v1",
        "program_id": program_id,
        "request": {
            "target_days": int(target_days),
            "duration_weeks": int(duration_weeks),
        },
        "resolved_context": {
            "weak_areas": resolved_weak_areas,
            "weak_area_source": str(resolved_context.get("weak_area_source") or "preview"),
            "recovery_state": str(resolved_context.get("recovery_state") or recovery_state),
            "current_week_index": int(resolved_context.get("current_week_index") or current_week_index),
        },
        "steps": [
            {
                "decision": "reuse_preview_context",
                "result": {
                    "has_preview_trace": bool(preview_trace),
                    "weak_area_count": len(resolved_weak_areas),
                },
            },
            {
                "decision": "prepare_persistence_state",
                "result": {
                    "target_days": int(target_days),
                    "weeks_remaining": int(duration_weeks),
                },
            },
        ],
        "preview_trace": dict(preview_trace),
        "request_runtime_trace": deepcopy(_coerce_dict(request_runtime_trace)),
        "outcome": {
            "status": "applied",
            "weeks_remaining": int(duration_weeks),
            "reason_code": "adaptation_applied",
        },
    }
    persistence_state = {
        "template_id": str(template_id or program_id),
        "program_id": program_id,
        "target_days": int(target_days),
        "duration_weeks": int(duration_weeks),
        "weeks_remaining": int(duration_weeks),
        "weak_areas": resolved_weak_areas,
        "last_applied_week_start": None,
        "applied_at": applied_at,
        "decision_trace": decision_trace,
    }
    return {
        "status": "applied",
        "program_id": program_id,
        "target_days": int(target_days),
        "duration_weeks": int(duration_weeks),
        "weeks_remaining": int(duration_weeks),
        "weak_areas": resolved_weak_areas,
        "decision_trace": decision_trace,
        "persistence_state": persistence_state,
    }


def build_frequency_adaptation_apply_payload(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": str(decision.get("status") or "applied"),
        "program_id": str(decision.get("program_id") or ""),
        "target_days": int(decision.get("target_days") or 0),
        "duration_weeks": int(decision.get("duration_weeks") or 0),
        "weeks_remaining": int(decision.get("weeks_remaining") or 0),
        "weak_areas": list(decision.get("weak_areas") or []),
        "decision_trace": deepcopy(dict(decision.get("decision_trace") or {})),
    }


def build_frequency_adaptation_persistence_state(
    *,
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    return deepcopy(_coerce_dict(decision_payload.get("persistence_state")))


def build_generated_week_adaptation_persistence_payload(
    *,
    adaptation_runtime: dict[str, Any],
) -> dict[str, Any]:
    runtime = _coerce_dict(adaptation_runtime)
    return {
        "state_updated": bool(runtime.get("state_updated")),
        "next_state": deepcopy(_coerce_dict(runtime.get("next_state"))) or None,
    }


def prepare_frequency_adaptation_route_runtime(
    *,
    adaptation_runtime: dict[str, Any],
    onboarding_package: dict[str, Any],
    decision_kind: str,
    applied_at: str | None = None,
) -> dict[str, Any]:
    runtime = _coerce_dict(adaptation_runtime)
    decision_mode = str(decision_kind).strip().lower()
    if decision_mode not in {"preview", "apply"}:
        raise ValueError(f"Unsupported decision kind: {decision_kind}")

    shared_kwargs = {
        "onboarding_package": onboarding_package,
        "program_id": str(runtime["program_id"]),
        "template_id": str(runtime.get("template_id") or runtime["program_id"]),
        "current_days": int(runtime["current_days"]),
        "target_days": int(runtime["target_days"]),
        "duration_weeks": int(runtime["duration_weeks"]),
        "explicit_weak_areas": list(runtime.get("explicit_weak_areas") or []),
        "stored_weak_areas": list(runtime.get("stored_weak_areas") or []),
        "equipment_profile": list(runtime.get("equipment_profile") or []),
        "recovery_state": str(runtime["recovery_state"]),
        "current_week_index": int(runtime["current_week_index"]),
        "request_runtime_trace": deepcopy(_coerce_dict(runtime.get("decision_trace"))),
    }

    if decision_mode == "preview":
        preview_payload = recommend_frequency_adaptation_preview(**shared_kwargs)
        return {
            "decision_kind": "preview",
            "preview_payload": preview_payload,
            "decision_trace": {
                "interpreter": "prepare_frequency_adaptation_route_runtime",
                "version": "v1",
                "inputs": {
                    "decision_kind": "preview",
                    "program_id": shared_kwargs["program_id"],
                    "target_days": shared_kwargs["target_days"],
                    "duration_weeks": shared_kwargs["duration_weeks"],
                },
                "outcome": {
                    "week_count": len(preview_payload.get("weeks") or []),
                },
            },
        }

    if not isinstance(applied_at, str) or not applied_at.strip():
        raise ValueError("applied_at is required for adaptation apply runtime")

    decision = interpret_frequency_adaptation_apply(
        **shared_kwargs,
        applied_at=applied_at,
    )
    persistence_state = build_frequency_adaptation_persistence_state(
        decision_payload=decision,
    )
    response_payload = build_frequency_adaptation_apply_payload(decision)
    return {
        "decision_kind": "apply",
        "decision": decision,
        "persistence_state": persistence_state,
        "response_payload": response_payload,
        "decision_trace": {
            "interpreter": "prepare_frequency_adaptation_route_runtime",
            "version": "v1",
            "inputs": {
                "decision_kind": "apply",
                "program_id": shared_kwargs["program_id"],
                "target_days": shared_kwargs["target_days"],
                "duration_weeks": shared_kwargs["duration_weeks"],
            },
            "outcome": {
                "status": str(decision.get("status") or ""),
                "weeks_remaining": int(decision.get("weeks_remaining") or 0),
            },
        },
    }


def resolve_active_frequency_adaptation_runtime(
    *,
    active_state: dict[str, Any] | None,
    selected_template_id: str,
) -> dict[str, Any] | None:
    if not isinstance(active_state, dict):
        return None

    target_days_raw = active_state.get("target_days")
    weeks_remaining_raw = active_state.get("weeks_remaining")
    template_id = str(active_state.get("template_id") or active_state.get("program_id") or "").strip()
    if not template_id or template_id != selected_template_id:
        return None

    if not isinstance(target_days_raw, (int, float, str)) or not isinstance(
        weeks_remaining_raw,
        (int, float, str),
    ):
        return None
    try:
        target_days = int(target_days_raw)
        weeks_remaining = int(weeks_remaining_raw)
    except (TypeError, ValueError):
        return None

    if target_days < 2 or target_days > 5 or weeks_remaining <= 0:
        return None

    duration_weeks = active_state.get("duration_weeks")
    weak_areas = _normalized_weak_areas(active_state.get("weak_areas"))
    decision_trace = dict(active_state.get("decision_trace") or {})
    return {
        "program_id": template_id,
        "template_id": template_id,
        "target_days": target_days,
        "duration_weeks": int(duration_weeks) if isinstance(duration_weeks, int) else weeks_remaining,
        "weeks_remaining": weeks_remaining,
        "last_applied_week_start": active_state.get("last_applied_week_start"),
        "weak_areas": weak_areas,
        "decision_trace": decision_trace,
    }


def apply_active_frequency_adaptation_runtime(
    *,
    plan: dict[str, Any],
    selected_template_id: str,
    active_frequency_adaptation: dict[str, Any] | None,
) -> dict[str, Any]:
    if active_frequency_adaptation is None:
        return {
            "plan": plan,
            "next_state": None,
            "state_updated": False,
        }

    adaptation_summary: dict[str, Any] = {
        "active": True,
        "template_id": selected_template_id,
        "target_days": int(active_frequency_adaptation["target_days"]),
        "duration_weeks": int(active_frequency_adaptation["duration_weeks"]),
        "weeks_remaining_before_apply": int(active_frequency_adaptation["weeks_remaining"]),
        "weak_areas": list(active_frequency_adaptation.get("weak_areas") or []),
    }
    week_start_iso = plan.get("week_start")
    already_applied_for_week = active_frequency_adaptation.get("last_applied_week_start") == week_start_iso
    base_trace = dict(active_frequency_adaptation.get("decision_trace") or {})
    preview_trace = _coerce_dict(base_trace.get("preview_trace"))
    preview_outcome = _coerce_dict(preview_trace.get("outcome"))
    if preview_outcome.get("policy_mode") is not None:
        adaptation_summary["policy_mode"] = preview_outcome.get("policy_mode")
    if preview_outcome.get("policy_id") is not None:
        adaptation_summary["policy_id"] = preview_outcome.get("policy_id")
    preservation_focus = list(preview_outcome.get("preservation_focus") or [])
    if preservation_focus:
        adaptation_summary["preservation_focus"] = preservation_focus

    if already_applied_for_week:
        adaptation_summary["weeks_remaining_after_apply"] = int(active_frequency_adaptation["weeks_remaining"])
        adaptation_summary["decision_trace"] = {
            "interpreter": "apply_active_frequency_adaptation_runtime",
            "source_trace": base_trace,
            "outcome": {
                "status": "already_applied_for_week",
                "week_start": week_start_iso,
            },
        }
        plan["applied_frequency_adaptation"] = adaptation_summary
        return {
            "plan": plan,
            "next_state": active_frequency_adaptation,
            "state_updated": False,
        }

    remaining_after = max(0, int(active_frequency_adaptation["weeks_remaining"]) - 1)
    next_state = None
    if remaining_after > 0:
        next_state = {
            "template_id": selected_template_id,
            "program_id": selected_template_id,
            "target_days": int(active_frequency_adaptation["target_days"]),
            "duration_weeks": int(active_frequency_adaptation["duration_weeks"]),
            "weeks_remaining": remaining_after,
            "weak_areas": list(active_frequency_adaptation.get("weak_areas") or []),
            "last_applied_week_start": week_start_iso,
            "decision_trace": base_trace,
        }

    adaptation_summary["weeks_remaining_after_apply"] = remaining_after
    if remaining_after == 0:
        adaptation_summary["completed"] = True
    adaptation_summary["decision_trace"] = {
        "interpreter": "apply_active_frequency_adaptation_runtime",
        "source_trace": base_trace,
        "outcome": {
            "status": "completed" if remaining_after == 0 else "applied",
            "week_start": week_start_iso,
            "weeks_remaining_after_apply": remaining_after,
        },
    }
    plan["applied_frequency_adaptation"] = adaptation_summary
    return {
        "plan": plan,
        "next_state": next_state,
        "state_updated": True,
    }
