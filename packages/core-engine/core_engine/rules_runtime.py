import re
from typing import Any

from .equipment import resolve_equipment_tags


_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
}


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _round_weight(value: float, increment: float) -> float:
    if increment <= 0:
        return round(value, 2)
    return round(round(value / increment) * increment, 2)


def _normalize_exercise_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _rule_rationale(rule_set: dict[str, Any] | None, key: str, fallback: str) -> str:
    rationale_templates = _coerce_dict(_coerce_dict(rule_set).get("rationale_templates"))
    value = rationale_templates.get(key)
    return value if isinstance(value, str) and value.strip() else fallback


def resolve_progression_rule_runtime(rule_set: dict[str, Any] | None) -> dict[str, float | int]:
    rule_payload = _coerce_dict(rule_set)
    progression_rules = _coerce_dict(rule_payload.get("progression_rules"))
    on_success = _coerce_dict(progression_rules.get("on_success"))
    on_under_target = _coerce_dict(progression_rules.get("on_under_target"))
    return {
        "increase_percent": float(on_success.get("percent") or 2.5),
        "reduce_percent": float(on_under_target.get("reduce_percent") or 2.0),
        "reduce_after_exposures": int(on_under_target.get("after_exposures") or 0),
    }


def extract_fatigue_rpe_threshold(rule_set: dict[str, Any] | None) -> float | None:
    fatigue_rules = _coerce_dict(_coerce_dict(rule_set).get("fatigue_rules"))
    trigger = _coerce_dict(fatigue_rules.get("high_fatigue_trigger"))

    for condition in trigger.get("conditions", []):
        if not isinstance(condition, str):
            continue
        match = re.search(r"session_rpe_avg\s*>=\s*(\d+(?:\.\d+)?)", condition)
        if match:
            return float(match.group(1))
    return None


def extract_intro_weeks(rule_set: dict[str, Any] | None) -> int:
    fatigue_rules = _coerce_dict(_coerce_dict(rule_set).get("fatigue_rules"))
    trigger = _coerce_dict(fatigue_rules.get("high_fatigue_trigger"))

    for condition in trigger.get("conditions", []):
        if not isinstance(condition, str):
            continue
        match = re.search(r"intro phase lasts\s+(\d+)\s+weeks", condition, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0


def resolve_adaptive_rule_runtime(rule_set: dict[str, Any] | None) -> dict[str, Any]:
    progression_rules = _coerce_dict(_coerce_dict(rule_set).get("progression_rules"))
    deload_rules = _coerce_dict(_coerce_dict(rule_set).get("deload_rules"))
    fatigue_rules = _coerce_dict(_coerce_dict(rule_set).get("fatigue_rules"))
    on_success = _coerce_dict(progression_rules.get("on_success"))
    on_under_target = _coerce_dict(progression_rules.get("on_under_target"))
    on_deload = _coerce_dict(deload_rules.get("on_deload"))
    on_high_fatigue = _coerce_dict(fatigue_rules.get("on_high_fatigue"))

    return {
        "underperf_threshold": int(on_under_target.get("after_exposures") or 2),
        "fatigue_rpe_threshold": extract_fatigue_rpe_threshold(rule_set),
        "progress_load_scale": 1.0 + (float(on_success.get("percent") or 2.5) / 100.0),
        "deload_load_scale": 1.0 - (float(on_deload.get("load_reduction_percent") or 10.0) / 100.0),
        "deload_set_delta": -max(1, int(on_high_fatigue.get("set_delta") or 1)),
        "progress_reason": _rule_rationale(rule_set, "increase_load", "high_readiness_progression"),
        "hold_reason": _rule_rationale(rule_set, "hold_load", "maintain_until_stable"),
        "deload_reason": _rule_rationale(rule_set, "deload", "deload"),
        "scheduled_deload_weeks": int(deload_rules.get("scheduled_every_n_weeks") or 4),
        "early_deload_trigger": str(deload_rules.get("early_deload_trigger") or ""),
        "intro_weeks": extract_intro_weeks(rule_set),
    }


def evaluate_deload_signal(
    *,
    completion_pct: int,
    adherence_score: int,
    soreness_rank: int,
    average_rpe: float | None = None,
    consecutive_underperformance_weeks: int = 0,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = resolve_adaptive_rule_runtime(rule_set)
    fatigue_rpe_threshold = runtime["fatigue_rpe_threshold"]
    underperf = max(0, int(consecutive_underperformance_weeks))

    forced_deload_reasons: list[str] = []
    if completion_pct < 70:
        forced_deload_reasons.append("low_completion")
    if adherence_score <= 2:
        forced_deload_reasons.append("low_adherence")
    if soreness_rank >= 3:
        forced_deload_reasons.append("high_soreness")

    high_fatigue = soreness_rank >= 3 or (
        average_rpe is not None
        and fatigue_rpe_threshold is not None
        and float(average_rpe) >= float(fatigue_rpe_threshold)
    )

    early_deload_trigger = str(runtime["early_deload_trigger"] or "")
    underperformance_deload_matched = False
    if underperf >= int(runtime["underperf_threshold"]):
        if early_deload_trigger == "repeated_under_target_plus_high_fatigue":
            underperformance_deload_matched = high_fatigue
        elif early_deload_trigger == "three_consecutive_under_target_sessions":
            underperformance_deload_matched = underperf >= 3
        else:
            underperformance_deload_matched = high_fatigue

    return {
        "forced_deload_reasons": forced_deload_reasons,
        "high_fatigue": high_fatigue,
        "underperformance_deload_matched": underperformance_deload_matched,
        "underperf_threshold": int(runtime["underperf_threshold"]),
        "early_deload_trigger": early_deload_trigger,
    }


def resolve_substitution_rule_runtime(rule_set: dict[str, Any] | None) -> dict[str, Any]:
    substitution_rules = _coerce_dict(_coerce_dict(rule_set).get("substitution_rules"))
    equipment_mismatch_strategy = str(
        substitution_rules.get("equipment_mismatch") or "use_first_compatible_substitution"
    )
    repeat_failure_trigger = str(substitution_rules.get("repeat_failure_trigger") or "")
    repeat_failure_threshold = 3
    match = re.search(r"switch_after_([a-z]+|\d+)_failed_exposures", repeat_failure_trigger)
    if match:
        raw_threshold = match.group(1)
        if raw_threshold.isdigit():
            repeat_failure_threshold = int(raw_threshold)
        else:
            repeat_failure_threshold = _NUMBER_WORDS.get(raw_threshold.lower())

    return {
        "equipment_mismatch_strategy": equipment_mismatch_strategy,
        "repeat_failure_trigger": repeat_failure_trigger,
        "repeat_failure_threshold": repeat_failure_threshold,
    }


def resolve_scheduler_mesocycle_runtime(
    *,
    template_deload: dict[str, Any] | None,
    prior_generated_weeks: int,
    latest_adherence_score: int | None,
    severe_soreness_count: int,
    authored_week_index: int | None,
    authored_week_role: str | None,
    authored_sequence_length: int | None,
    authored_sequence_complete: bool,
    stimulus_fatigue_response: dict[str, Any] | None,
    phase: str,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    deload_rules = _coerce_dict(_coerce_dict(rule_set).get("deload_rules"))
    template_deload = _coerce_dict(template_deload)
    rule_trigger_weeks = int(deload_rules.get("scheduled_every_n_weeks") or 0)
    if rule_trigger_weeks > 0:
        trigger_weeks_base = max(1, rule_trigger_weeks)
        trigger_weeks_source = "rule_set.deload_rules.scheduled_every_n_weeks"
    else:
        trigger_weeks_base = max(1, int(template_deload.get("trigger_weeks", 6) or 6))
        trigger_weeks_source = "template.deload.trigger_weeks"

    trigger_weeks_effective = trigger_weeks_base
    weeks_completed_prior = max(0, int(prior_generated_weeks))
    week_index = (weeks_completed_prior % trigger_weeks_effective) + 1
    scheduled_deload = week_index == trigger_weeks_effective

    normalized_adherence = None
    if latest_adherence_score is not None:
        normalized_adherence = max(1, min(5, int(latest_adherence_score)))
    early_soreness = max(0, int(severe_soreness_count)) >= 2
    early_adherence = normalized_adherence is not None and normalized_adherence <= 2

    normalized_sfr = _coerce_dict(stimulus_fatigue_response)
    early_sfr_recovery = (
        str(normalized_sfr.get("deload_pressure") or "low") == "high"
        and str(normalized_sfr.get("recoverability") or "moderate") == "low"
    )

    reasons: list[str] = []
    authored_deload = str(authored_week_role or "").lower() == "deload"
    if authored_deload:
        reasons.append("authored_deload")
    elif scheduled_deload:
        reasons.append("scheduled")
    if early_soreness:
        reasons.append("early_soreness")
    if early_adherence:
        reasons.append("early_adherence")
    if early_sfr_recovery and not (early_soreness or early_adherence):
        reasons.append("early_sfr_recovery")

    return {
        "weeks_completed_prior": weeks_completed_prior,
        "week_index": week_index,
        "authored_week_index": int(authored_week_index) if authored_week_index is not None else None,
        "authored_week_role": str(authored_week_role or "accumulation"),
        "authored_sequence_length": (
            int(authored_sequence_length)
            if authored_sequence_length is not None
            else None
        ),
        "authored_sequence_complete": bool(authored_sequence_complete),
        "phase_transition_pending": bool(authored_sequence_complete),
        "phase_transition_reason": (
            "authored_sequence_complete"
            if authored_sequence_complete
            else "none"
        ),
        "post_authored_behavior": (
            "hold_last_authored_week"
            if authored_sequence_complete
            else "in_authored_sequence"
        ),
        "trigger_weeks_base": trigger_weeks_base,
        "trigger_weeks_effective": trigger_weeks_effective,
        "is_deload_week": bool(reasons),
        "deload_reason": "+".join(reasons) if reasons else "none",
        "early_triggers": {
            "severe_soreness": early_soreness,
            "low_adherence": early_adherence,
            "sfr_recovery": early_sfr_recovery,
        },
        "decision_trace": {
            "interpreter": "resolve_scheduler_mesocycle_runtime",
            "version": "v1",
            "inputs": {
                "phase": str(phase or "maintenance"),
                "prior_generated_weeks": weeks_completed_prior,
                "latest_adherence_score": normalized_adherence,
                "severe_soreness_count": max(0, int(severe_soreness_count)),
                "authored_week_index": authored_week_index,
                "authored_week_role": str(authored_week_role or ""),
                "authored_sequence_length": authored_sequence_length,
                "authored_sequence_complete": bool(authored_sequence_complete),
                "template_trigger_weeks": int(template_deload.get("trigger_weeks", 6) or 6),
                "rule_trigger_weeks": rule_trigger_weeks if rule_trigger_weeks > 0 else None,
                "stimulus_fatigue_response": dict(normalized_sfr),
            },
            "steps": [
                {
                    "decision": "resolve_trigger_weeks",
                    "result": {
                        "trigger_weeks_base": trigger_weeks_base,
                        "trigger_weeks_effective": trigger_weeks_effective,
                        "trigger_weeks_source": trigger_weeks_source,
                    },
                },
                {
                    "decision": "evaluate_deload_triggers",
                    "result": {
                        "scheduled_deload": scheduled_deload,
                        "authored_deload": authored_deload,
                        "early_triggers": {
                            "severe_soreness": early_soreness,
                            "low_adherence": early_adherence,
                            "sfr_recovery": early_sfr_recovery,
                        },
                    },
                },
            ],
            "outcome": {
                "week_index": week_index,
                "is_deload_week": bool(reasons),
                "deload_reason": "+".join(reasons) if reasons else "none",
                "trigger_weeks_source": trigger_weeks_source,
            },
        },
    }


def _merge_substitution_pressure(*pressures: str | None) -> str:
    rank = {"low": 0, "moderate": 1, "high": 2}
    resolved = "low"
    for pressure in pressures:
        normalized = str(pressure or "low").lower()
        if rank.get(normalized, 0) > rank[resolved]:
            resolved = normalized
    return resolved


def resolve_scheduler_exercise_adjustment_runtime(
    *,
    progression_state: dict[str, Any] | None,
    stimulus_substitution_pressure: str | None,
) -> dict[str, Any]:
    state = _coerce_dict(progression_state)
    fatigue_score = max(0.0, min(1.0, float(state.get("fatigue_score") or 0.0)))
    failed_exposures = int(state.get("consecutive_under_target_exposures") or 0)
    last_action = str(state.get("last_progression_action") or "hold")

    if fatigue_score >= 0.8 and last_action == "reduce_load":
        load_scale = 0.95
        set_delta = -1
        progression_substitution_pressure = "high"
    elif fatigue_score >= 0.7 or failed_exposures >= 2 or last_action == "reduce_load":
        load_scale = 0.95 if fatigue_score >= 0.7 or last_action == "reduce_load" else 1.0
        set_delta = 0
        progression_substitution_pressure = "moderate"
    else:
        load_scale = 1.0
        set_delta = 0
        progression_substitution_pressure = "low"

    merged_substitution_pressure = _merge_substitution_pressure(
        stimulus_substitution_pressure,
        progression_substitution_pressure,
    )
    substitution_guidance = None
    if merged_substitution_pressure == "high":
        substitution_guidance = "prefer_compatible_variants_if_recovery_constraints_persist"
    elif merged_substitution_pressure == "moderate":
        substitution_guidance = "compatible_variants_available_if_recovery_constraints_persist"

    return {
        "load_scale": load_scale,
        "set_delta": set_delta,
        "substitution_pressure": merged_substitution_pressure,
        "substitution_guidance": substitution_guidance,
        "decision_trace": {
            "interpreter": "resolve_scheduler_exercise_adjustment_runtime",
            "version": "v1",
            "inputs": {
                "exercise_id": str(state.get("exercise_id") or ""),
                "fatigue_score": fatigue_score,
                "consecutive_under_target_exposures": failed_exposures,
                "last_progression_action": last_action,
                "stimulus_substitution_pressure": str(stimulus_substitution_pressure or "low"),
            },
            "steps": [
                {
                    "decision": "evaluate_progression_state_recovery_pressure",
                    "result": {
                        "load_scale": load_scale,
                        "set_delta": set_delta,
                        "progression_substitution_pressure": progression_substitution_pressure,
                    },
                },
                {
                    "decision": "merge_generation_substitution_pressure",
                    "result": {
                        "merged_substitution_pressure": merged_substitution_pressure,
                        "substitution_guidance": substitution_guidance,
                    },
                },
            ],
            "outcome": {
                "load_scale": load_scale,
                "set_delta": set_delta,
                "merged_substitution_pressure": merged_substitution_pressure,
                "substitution_guidance": substitution_guidance,
            },
        },
    }


def _spread_indices(total: int, count: int) -> list[int]:
    if count <= 1:
        return [0]
    return [round(step * (total - 1) / (count - 1)) for step in range(count)]


def _normalize_indices(indices: list[int], total: int, count: int) -> list[int]:
    normalized: list[int] = []
    for index in indices:
        if index not in normalized:
            normalized.append(index)
    if len(normalized) < count:
        for index in range(total):
            if index not in normalized:
                normalized.append(index)
            if len(normalized) == count:
                break
    normalized.sort()
    return normalized[:count]


def _select_session_indices_evenly(session_count: int, days_available: int) -> list[int]:
    return _normalize_indices(
        _spread_indices(session_count, days_available),
        session_count,
        days_available,
    )


def _history_exercise_key(history_item: dict[str, Any]) -> str | None:
    primary_exercise_id = str(history_item.get("primary_exercise_id") or "").strip()
    if primary_exercise_id:
        return primary_exercise_id

    exercise_id = str(history_item.get("exercise_id") or "").strip()
    return exercise_id or None


def _rank_history_priority_exercises(history: list[dict[str, Any]], limit: int = 6) -> list[str]:
    if not history:
        return []

    weighted_counts: dict[str, float] = {}
    total = len(history)
    denominator = max(1, total - 1)
    for index, item in enumerate(history):
        exercise_key = _history_exercise_key(item)
        if not exercise_key:
            continue

        recency_weight = 1.0 + ((total - index - 1) / denominator)
        weighted_counts[exercise_key] = weighted_counts.get(exercise_key, 0.0) + recency_weight

    ranked = sorted(weighted_counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return [exercise_id for exercise_id, _ in ranked[:limit]]


def _rank_structural_priority_exercises(
    session_profiles: list[dict[str, Any]],
    limit: int = 6,
) -> list[str]:
    ranked: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    ordinal = 0
    boosted_role_priority = {
        "weak_point": 120,
        "primary_compound": 110,
        "secondary_compound": 80,
    }
    for session in session_profiles:
        exercise_ids = [
            str(item).strip()
            for item in session.get("primary_exercise_ids") or []
            if str(item).strip()
        ]
        slot_roles = [
            str(item).strip().lower()
            for item in session.get("slot_roles") or []
            if str(item).strip()
        ]
        for exercise_id, slot_role in zip(exercise_ids, slot_roles):
            if slot_role not in boosted_role_priority or exercise_id in seen:
                continue
            seen.add(exercise_id)
            ranked.append((boosted_role_priority[slot_role], ordinal, exercise_id))
            ordinal += 1

    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [exercise_id for _, _, exercise_id in ranked[:limit]]


def _priority_weight(exercise_ids: set[str], priority_weights: dict[str, int]) -> int:
    return sum(priority_weights.get(exercise_id, 0) for exercise_id in exercise_ids)


def _session_distance_score(index: int, selected_indices: list[int], total_sessions: int) -> float:
    if not selected_indices:
        return 0.0
    nearest_distance = min(abs(index - selected) for selected in selected_indices)
    return nearest_distance / max(1, total_sessions - 1)


def _required_session_indices(session_profiles: list[dict[str, Any]]) -> list[int]:
    required: list[int] = []
    weak_point_index: int | None = None
    has_explicit_day_roles = any(str(session.get("day_role") or "").strip() for session in session_profiles)

    for session in session_profiles:
        index = int(session.get("index") or 0)
        day_role = str(session.get("day_role") or "").strip().lower()
        if day_role == "weak_point_arms" and weak_point_index is None:
            weak_point_index = index

    if session_profiles and has_explicit_day_roles:
        required.append(int(session_profiles[0].get("index") or 0))
    if weak_point_index is not None and weak_point_index not in required:
        required.append(weak_point_index)
    return required


def _select_sessions_with_continuity(
    session_profiles: list[dict[str, Any]],
    days_available: int,
    priority_targets: list[str],
) -> tuple[list[int], str]:
    priority_weights = {
        exercise_id: len(priority_targets) - index
        for index, exercise_id in enumerate(priority_targets)
    }
    normalized_profiles = [
        {
            "index": int(session.get("index") or 0),
            "day_role": str(session.get("day_role") or "").strip().lower(),
            "primary_exercise_ids": {
                str(item).strip()
                for item in session.get("primary_exercise_ids") or []
                if str(item).strip()
            },
            "muscles": {
                str(item).strip()
                for item in session.get("muscles") or []
                if str(item).strip()
            },
        }
        for session in session_profiles
    ]
    if not any(
        _priority_weight(profile["primary_exercise_ids"], priority_weights) > 0
        for profile in normalized_profiles
    ):
        return _select_session_indices_evenly(len(session_profiles), days_available), "even_spread_fallback"

    selected_indices: list[int] = []
    covered_priority: set[str] = set()
    covered_muscles: set[str] = set()
    day_role_priority = {
        "weak_point_arms": 100,
        "full_body_1": 80,
        "full_body_2": 80,
        "full_body_3": 80,
        "full_body_4": 80,
    }

    for index in _required_session_indices(session_profiles)[:days_available]:
        if index in selected_indices:
            continue
        selected_indices.append(index)
        profile = next(item for item in normalized_profiles if item["index"] == index)
        covered_priority.update(profile["primary_exercise_ids"])
        covered_muscles.update(profile["muscles"])

    while len(selected_indices) < days_available:
        best_index: int | None = None
        best_score: tuple[int, int, int, int, int, float] | None = None

        for profile in normalized_profiles:
            index = profile["index"]
            if index in selected_indices:
                continue

            new_priority_ids = profile["primary_exercise_ids"] - covered_priority
            score = (
                _priority_weight(new_priority_ids, priority_weights),
                day_role_priority.get(profile["day_role"], 0),
                len(profile["muscles"] - covered_muscles),
                _priority_weight(profile["primary_exercise_ids"], priority_weights),
                len(profile["muscles"]),
                _session_distance_score(index, selected_indices, len(session_profiles)),
            )
            if best_score is None or score > best_score or (score == best_score and index < best_index):
                best_index = index
                best_score = score

        if best_index is None:
            break

        selected_indices.append(best_index)
        profile = next(item for item in normalized_profiles if item["index"] == best_index)
        covered_priority.update(profile["primary_exercise_ids"])
        covered_muscles.update(profile["muscles"])

    if len(selected_indices) != days_available:
        return _select_session_indices_evenly(len(session_profiles), days_available), "even_spread_fallback"

    selected_indices.sort()
    return selected_indices, "continuity_priority"


def resolve_scheduler_session_selection(
    *,
    session_profiles: list[dict[str, Any]],
    history: list[dict[str, Any]],
    days_available: int,
) -> dict[str, Any]:
    normalized_days_available = max(1, int(days_available))
    if normalized_days_available >= len(session_profiles):
        selected_indices = [int(session.get("index") or 0) for session in session_profiles]
        selection_strategy = "all_sessions_retained"
        priority_targets: list[str] = []
        priority_target_source = "not_needed"
    else:
        priority_targets = _rank_history_priority_exercises(history)
        priority_target_source = "history"
        if not priority_targets:
            priority_targets = _rank_structural_priority_exercises(session_profiles)
            priority_target_source = "session_structure" if priority_targets else "none"

        if not priority_targets:
            selected_indices = _select_session_indices_evenly(len(session_profiles), normalized_days_available)
            selection_strategy = "even_spread_fallback"
        else:
            selected_indices, selection_strategy = _select_sessions_with_continuity(
                session_profiles,
                normalized_days_available,
                priority_targets,
            )

    required_indices = _required_session_indices(session_profiles)
    missed_day_policy = "roll-forward-priority-lifts"
    return {
        "selected_indices": selected_indices,
        "missed_day_policy": missed_day_policy,
        "decision_trace": {
            "interpreter": "resolve_scheduler_session_selection",
            "version": "v1",
            "inputs": {
                "session_count": len(session_profiles),
                "days_available": normalized_days_available,
                "history_count": len(history),
            },
            "steps": [
                {
                    "decision": "resolve_priority_targets",
                    "result": {
                        "priority_target_source": priority_target_source,
                        "priority_targets": list(priority_targets),
                        "required_session_indices": required_indices,
                    },
                },
                {
                    "decision": "select_session_indices",
                    "result": {
                        "selection_strategy": selection_strategy,
                        "selected_indices": list(selected_indices),
                    },
                },
            ],
            "outcome": {
                "selected_indices": list(selected_indices),
                "required_session_indices": required_indices,
                "selection_strategy": selection_strategy,
                "missed_day_policy": missed_day_policy,
            },
        },
    }


def resolve_scheduler_session_exercise_cap(
    *,
    session_time_budget_minutes: int | None,
    day_role: str | None,
    slot_roles: list[str],
) -> dict[str, Any]:
    normalized_day_role = str(day_role or "").strip().lower()
    if session_time_budget_minutes is None:
        limit = None
    elif session_time_budget_minutes <= 30:
        limit = 3
    elif session_time_budget_minutes <= 45:
        limit = 4
    elif session_time_budget_minutes <= 60:
        limit = 5
    else:
        limit = None

    role_priority = {
        "primary_compound": 100,
        "weak_point": 90,
        "secondary_compound": 80,
        "accessory": 50,
        "isolation": 40,
    }
    if normalized_day_role == "weak_point_arms":
        role_priority["weak_point"] = 120
        role_priority["primary_compound"] = 70
        role_priority["secondary_compound"] = 60

    normalized_slot_roles = [str(role or "").strip().lower() for role in slot_roles]
    if limit is None or limit >= len(normalized_slot_roles):
        kept_indices = list(range(len(normalized_slot_roles)))
    else:
        ranked = sorted(
            enumerate(normalized_slot_roles),
            key=lambda item: (-role_priority.get(item[1], 30), item[0]),
        )
        kept_indices = sorted(index for index, _ in ranked[:limit])

    return {
        "exercise_limit": limit,
        "kept_indices": kept_indices,
        "decision_trace": {
            "interpreter": "resolve_scheduler_session_exercise_cap",
            "version": "v1",
            "inputs": {
                "session_time_budget_minutes": (
                    int(session_time_budget_minutes)
                    if session_time_budget_minutes is not None
                    else None
                ),
                "day_role": normalized_day_role,
                "slot_roles": list(normalized_slot_roles),
            },
            "outcome": {
                "exercise_limit": limit,
                "kept_indices": list(kept_indices),
            },
        },
    }


def _compatible_substitution_candidates(
    *,
    substitution_candidates: list[str],
    equipment_set: set[str],
) -> list[str]:
    def is_compatible(tags: list[str]) -> bool:
        if not equipment_set:
            return True
        if not tags:
            return True
        return bool(equipment_set.intersection({tag.lower() for tag in tags}))

    compatible_candidates: list[str] = []
    for candidate in substitution_candidates:
        candidate_tags = resolve_equipment_tags(exercise_name=candidate, explicit_tags=None)
        if is_compatible(candidate_tags):
            compatible_candidates.append(candidate)
    return compatible_candidates


def resolve_equipment_substitution(
    *,
    exercise_id: str,
    exercise_name: str,
    exercise_equipment_tags: list[str],
    substitution_candidates: list[str],
    equipment_set: set[str],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    substitution_runtime = resolve_substitution_rule_runtime(rule_set)

    def is_compatible(tags: list[str]) -> bool:
        if not equipment_set:
            return True
        if not tags:
            return True
        return bool(equipment_set.intersection({tag.lower() for tag in tags}))

    compatible_candidates = _compatible_substitution_candidates(
        substitution_candidates=substitution_candidates,
        equipment_set=equipment_set,
    )

    original_compatible = is_compatible(exercise_equipment_tags)
    selected_exercise_id = exercise_id
    selected_name = exercise_name
    auto_substituted = False

    strategy = str(substitution_runtime["equipment_mismatch_strategy"])
    if not original_compatible and compatible_candidates:
        if strategy == "use_first_compatible_substitution":
            selected_name = compatible_candidates[0]
            auto_substituted = True

    return {
        "selected_exercise_id": selected_exercise_id if not auto_substituted else None,
        "selected_name": selected_name,
        "compatible_substitutions": compatible_candidates,
        "auto_substituted": auto_substituted,
        "decision_trace": {
            "interpreter": "resolve_equipment_substitution",
            "version": "v1",
            "inputs": {
                "exercise_id": exercise_id,
                "exercise_name": exercise_name,
                "exercise_equipment_tags": list(exercise_equipment_tags),
                "substitution_candidates": list(substitution_candidates),
                "equipment_set": sorted(equipment_set),
                "equipment_mismatch_strategy": strategy,
            },
            "steps": [
                {
                    "decision": "filter_compatible_substitutions",
                    "result": {
                        "original_compatible": original_compatible,
                        "compatible_substitutions": list(compatible_candidates),
                    },
                },
                {
                    "decision": "apply_equipment_mismatch_strategy",
                    "result": {
                        "auto_substituted": auto_substituted,
                        "selected_name": selected_name,
                    },
                },
            ],
            "outcome": {
                "original_compatible": original_compatible,
                "compatible_substitutions": list(compatible_candidates),
                "selected_name": selected_name,
                "auto_substituted": auto_substituted,
            },
        },
    }


def resolve_repeat_failure_substitution(
    *,
    exercise_id: str,
    exercise_name: str,
    substitution_candidates: list[str],
    consecutive_under_target_exposures: int,
    equipment_set: set[str],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    substitution_runtime = resolve_substitution_rule_runtime(rule_set)
    threshold = substitution_runtime["repeat_failure_threshold"]
    compatible_candidates = _compatible_substitution_candidates(
        substitution_candidates=substitution_candidates,
        equipment_set=equipment_set,
    )
    current_keys = {
        _normalize_exercise_key(exercise_id),
        _normalize_exercise_key(exercise_name),
    }
    compatible_alternatives = [
        candidate
        for candidate in compatible_candidates
        if _normalize_exercise_key(candidate) not in current_keys
    ]
    threshold_met = threshold is not None and consecutive_under_target_exposures >= int(threshold)
    recommended_name = compatible_alternatives[0] if threshold_met and compatible_alternatives else None

    return {
        "repeat_failure_threshold": threshold,
        "compatible_substitutions": compatible_alternatives,
        "recommended_name": recommended_name,
        "recommend_substitution": recommended_name is not None,
        "decision_trace": {
            "interpreter": "resolve_repeat_failure_substitution",
            "version": "v1",
            "inputs": {
                "exercise_id": exercise_id,
                "exercise_name": exercise_name,
                "substitution_candidates": list(substitution_candidates),
                "compatible_substitutions": list(compatible_alternatives),
                "consecutive_under_target_exposures": int(consecutive_under_target_exposures),
                "repeat_failure_threshold": threshold,
                "equipment_set": sorted(equipment_set),
            },
            "steps": [
                {
                    "decision": "evaluate_repeat_failure_trigger",
                    "result": {
                        "threshold_met": threshold_met,
                        "recommended_name": recommended_name,
                    },
                }
            ],
            "outcome": {
                "recommend_substitution": recommended_name is not None,
                "recommended_name": recommended_name,
                "compatible_substitutions": list(compatible_alternatives),
            },
        },
    }


def resolve_starting_load(
    *,
    planned_exercise: dict[str, Any] | None,
    fallback_weight: float,
    rule_set: dict[str, Any] | None,
    minimum_weight: float = 5.0,
    weight_increment: float = 2.5,
) -> dict[str, Any]:
    exercise = _coerce_dict(planned_exercise)
    starting_load_rules = _coerce_dict(_coerce_dict(rule_set).get("starting_load_rules"))
    method = str(starting_load_rules.get("method") or "planned_weight")
    default_rir_target = int(starting_load_rules.get("default_rir_target") or 0)
    fallback_percent_estimated_1rm = float(starting_load_rules.get("fallback_percent_estimated_1rm") or 0)

    estimated_1rm = _coerce_float(
        exercise.get("estimated_1rm")
        or exercise.get("estimated_one_rep_max")
        or _coerce_dict(exercise.get("performance_profile")).get("estimated_1rm")
    )

    working_weight = max(minimum_weight, float(fallback_weight))
    source = "planned_weight"
    steps: list[dict[str, Any]] = []

    if method == "rep_range_rir_start" and estimated_1rm is not None and fallback_percent_estimated_1rm > 0:
        working_weight = max(
            minimum_weight,
            _round_weight((estimated_1rm * fallback_percent_estimated_1rm) / 100.0, weight_increment),
        )
        source = "estimated_1rm_fallback_percent"
        steps.append(
            {
                "decision": "apply_estimated_1rm_fallback_percent",
                "result": {
                    "estimated_1rm": estimated_1rm,
                    "fallback_percent_estimated_1rm": fallback_percent_estimated_1rm,
                    "working_weight": working_weight,
                },
            }
        )
    else:
        steps.append(
            {
                "decision": "use_planned_weight_fallback",
                "result": {
                    "working_weight": working_weight,
                },
            }
        )

    return {
        "working_weight": working_weight,
        "default_rir_target": default_rir_target,
        "decision_trace": {
            "interpreter": "resolve_starting_load",
            "version": "v1",
            "inputs": {
                "method": method,
                "default_rir_target": default_rir_target,
                "fallback_percent_estimated_1rm": fallback_percent_estimated_1rm,
                "estimated_1rm": estimated_1rm,
                "fallback_weight": float(fallback_weight),
            },
            "steps": steps,
            "outcome": {
                "working_weight": working_weight,
                "source": source,
            },
        },
    }
