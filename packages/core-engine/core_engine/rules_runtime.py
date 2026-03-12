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


def _normalize_scheduler_label(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _coerce_percentage(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return max(0, min(100, parsed))


def _scheduler_rule_dict(rule_set: dict[str, Any] | None, key: str) -> dict[str, Any]:
    scheduler_rules = _coerce_dict(_coerce_dict(rule_set).get("generated_week_scheduler_rules"))
    return _coerce_dict(scheduler_rules.get(key))


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
    scheduler_rules = _scheduler_rule_dict(rule_set, "mesocycle")
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
    soreness_trigger = _coerce_dict(scheduler_rules.get("soreness_deload_trigger"))
    adherence_trigger = _coerce_dict(scheduler_rules.get("adherence_deload_trigger"))
    sfr_trigger = _coerce_dict(scheduler_rules.get("stimulus_fatigue_deload_trigger"))

    early_soreness = bool(soreness_trigger) and (
        max(0, int(severe_soreness_count)) >= int(soreness_trigger.get("minimum_severe_count") or 0)
    )
    early_adherence = (
        bool(adherence_trigger)
        and normalized_adherence is not None
        and normalized_adherence <= int(adherence_trigger.get("maximum_score") or 0)
    )

    normalized_sfr = _coerce_dict(stimulus_fatigue_response)
    early_sfr_recovery = (
        bool(sfr_trigger)
        and str(normalized_sfr.get("deload_pressure") or "").strip().lower()
        == str(sfr_trigger.get("deload_pressure") or "").strip().lower()
        and str(normalized_sfr.get("recoverability") or "").strip().lower()
        == str(sfr_trigger.get("recoverability") or "").strip().lower()
    )

    reasons: list[str] = []
    authored_deload = str(authored_week_role or "").lower() == "deload"
    if authored_deload:
        reasons.append("authored_deload")
    elif scheduled_deload:
        reasons.append("scheduled")
    if early_soreness:
        reasons.append(str(soreness_trigger.get("reason") or "early_soreness"))
    if early_adherence:
        reasons.append(str(adherence_trigger.get("reason") or "early_adherence"))
    if early_sfr_recovery:
        reasons.append(str(sfr_trigger.get("reason") or "early_sfr_recovery"))

    phase_transition_reason = None
    post_authored_behavior = None
    if authored_sequence_complete:
        phase_transition_reason = (
            str(scheduler_rules.get("sequence_completion_phase_transition_reason") or "").strip()
            or None
        )
        post_authored_behavior = (
            str(scheduler_rules.get("post_authored_sequence_behavior") or "").strip()
            or None
        )

    return {
        "weeks_completed_prior": weeks_completed_prior,
        "week_index": week_index,
        "authored_week_index": int(authored_week_index) if authored_week_index is not None else None,
        "authored_week_role": str(authored_week_role).strip() if str(authored_week_role or "").strip() else None,
        "authored_sequence_length": (
            int(authored_sequence_length)
            if authored_sequence_length is not None
            else None
        ),
        "authored_sequence_complete": bool(authored_sequence_complete),
        "phase_transition_pending": bool(authored_sequence_complete),
        "phase_transition_reason": phase_transition_reason,
        "post_authored_behavior": post_authored_behavior,
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


def _matches_exercise_adjustment_policy(
    conditions: dict[str, Any],
    *,
    fatigue_score: float,
    failed_exposures: int,
    last_action: str,
    match_policy: str,
) -> bool:
    checks: list[bool] = []
    minimum_fatigue_score = _coerce_float(conditions.get("minimum_fatigue_score"))
    if minimum_fatigue_score is not None:
        checks.append(fatigue_score >= minimum_fatigue_score)

    minimum_failed_exposures = conditions.get("minimum_consecutive_under_target_exposures")
    if isinstance(minimum_failed_exposures, (int, float)) or str(minimum_failed_exposures).isdigit():
        checks.append(failed_exposures >= int(minimum_failed_exposures))

    last_progression_actions = {
        str(item).strip().lower()
        for item in conditions.get("last_progression_actions") or []
        if str(item).strip()
    }
    if last_progression_actions:
        checks.append(last_action in last_progression_actions)

    if not checks:
        return False
    if match_policy == "any":
        return any(checks)
    return all(checks)


def resolve_scheduler_exercise_adjustment_runtime(
    *,
    progression_state: dict[str, Any] | None,
    stimulus_substitution_pressure: str | None,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = _coerce_dict(progression_state)
    fatigue_score = max(0.0, min(1.0, float(state.get("fatigue_score") or 0.0)))
    failed_exposures = int(state.get("consecutive_under_target_exposures") or 0)
    last_action = str(state.get("last_progression_action") or "hold").strip().lower()
    scheduler_rules = _scheduler_rule_dict(rule_set, "exercise_adjustment")

    selected_policy_id = "default_adjustment"
    selected_adjustment = _coerce_dict(scheduler_rules.get("default_adjustment"))
    for policy in scheduler_rules.get("policies") or []:
        policy_dict = _coerce_dict(policy)
        if _matches_exercise_adjustment_policy(
            _coerce_dict(policy_dict.get("conditions")),
            fatigue_score=fatigue_score,
            failed_exposures=failed_exposures,
            last_action=last_action,
            match_policy=str(policy_dict.get("match_policy") or "all").strip().lower(),
        ):
            selected_policy_id = str(policy_dict.get("policy_id") or "unnamed_policy")
            selected_adjustment = _coerce_dict(policy_dict.get("adjustment"))
            break

    load_scale = _coerce_float(selected_adjustment.get("load_scale")) or 1.0
    set_delta = int(selected_adjustment.get("set_delta") or 0)
    progression_substitution_pressure = str(
        selected_adjustment.get("substitution_pressure") or "low"
    ).strip().lower()

    merged_substitution_pressure = _merge_substitution_pressure(
        stimulus_substitution_pressure,
        progression_substitution_pressure,
    )
    substitution_guidance = selected_adjustment.get("substitution_guidance")
    if not isinstance(substitution_guidance, str) or not substitution_guidance.strip():
        substitution_guidance = _coerce_dict(
            scheduler_rules.get("substitution_pressure_guidance")
        ).get(merged_substitution_pressure)
    if not isinstance(substitution_guidance, str) or not substitution_guidance.strip():
        substitution_guidance = None

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
                        "selected_policy_id": selected_policy_id,
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

    ranked: list[str] = []
    for item in reversed(history):
        exercise_key = _history_exercise_key(item)
        if not exercise_key or exercise_key in ranked:
            continue
        ranked.append(exercise_key)
        if len(ranked) == limit:
            break
    return ranked


def _rank_structural_priority_exercises(
    session_profiles: list[dict[str, Any]],
    slot_role_priority: dict[str, int],
    limit: int = 6,
) -> list[str]:
    ranked: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    ordinal = 0
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
            role_priority = int(slot_role_priority.get(slot_role, 0))
            if role_priority <= 0 or exercise_id in seen:
                continue
            seen.add(exercise_id)
            ranked.append((role_priority, ordinal, exercise_id))
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


def _required_session_indices(
    session_profiles: list[dict[str, Any]],
    *,
    required_day_roles: set[str],
    anchor_first_session_when_day_roles_present: bool,
) -> list[int]:
    required: list[int] = []
    has_explicit_day_roles = any(str(session.get("day_role") or "").strip() for session in session_profiles)

    for session in session_profiles:
        index = int(session.get("index") or 0)
        day_role = str(session.get("day_role") or "").strip().lower()
        if day_role in required_day_roles and index not in required:
            required.append(index)

    if session_profiles and has_explicit_day_roles and anchor_first_session_when_day_roles_present:
        required.append(int(session_profiles[0].get("index") or 0))
    normalized_required: list[int] = []
    for index in sorted(required):
        if index not in normalized_required:
            normalized_required.append(index)
    return normalized_required


def _select_sessions_with_continuity(
    session_profiles: list[dict[str, Any]],
    days_available: int,
    priority_targets: list[str],
    *,
    required_indices: list[int],
    day_role_priority: dict[str, int],
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

    for index in required_indices[:days_available]:
        if index in selected_indices:
            continue
        selected_indices.append(index)
        profile = next(item for item in normalized_profiles if item["index"] == index)
        covered_priority.update(profile["primary_exercise_ids"])

    while len(selected_indices) < days_available:
        best_index: int | None = None
        best_score: tuple[int, int, float, int] | None = None

        for profile in normalized_profiles:
            index = profile["index"]
            if index in selected_indices:
                continue

            new_priority_ids = profile["primary_exercise_ids"] - covered_priority
            score = (
                _priority_weight(new_priority_ids, priority_weights),
                day_role_priority.get(profile["day_role"], 0),
                _session_distance_score(index, selected_indices, len(session_profiles)),
                _priority_weight(profile["primary_exercise_ids"], priority_weights),
            )
            if best_score is None or score > best_score or (score == best_score and index < best_index):
                best_index = index
                best_score = score

        if best_index is None:
            break

        selected_indices.append(best_index)
        profile = next(item for item in normalized_profiles if item["index"] == best_index)
        covered_priority.update(profile["primary_exercise_ids"])

    if len(selected_indices) != days_available:
        return _select_session_indices_evenly(len(session_profiles), days_available), "even_spread_fallback"

    selected_indices.sort()
    return selected_indices, "continuity_priority"


def resolve_scheduler_session_selection(
    *,
    session_profiles: list[dict[str, Any]],
    history: list[dict[str, Any]],
    days_available: int,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_days_available = max(1, int(days_available))
    session_selection_rules = _scheduler_rule_dict(rule_set, "session_selection")
    structural_slot_role_priority = {
        str(key).strip().lower(): int(value)
        for key, value in _coerce_dict(session_selection_rules.get("structural_slot_role_priority")).items()
        if str(key).strip()
    }
    required_day_roles = {
        str(item).strip().lower()
        for item in session_selection_rules.get("required_day_roles_when_compressed") or []
        if str(item).strip()
    }
    anchor_first_session = bool(session_selection_rules.get("anchor_first_session_when_day_roles_present"))
    day_role_priority = {
        str(key).strip().lower(): int(value)
        for key, value in _coerce_dict(session_selection_rules.get("day_role_priority")).items()
        if str(key).strip()
    }
    required_indices = _required_session_indices(
        session_profiles,
        required_day_roles=required_day_roles,
        anchor_first_session_when_day_roles_present=anchor_first_session,
    )

    if normalized_days_available >= len(session_profiles):
        selected_indices = [int(session.get("index") or 0) for session in session_profiles]
        selection_strategy = "all_sessions_retained"
        priority_targets: list[str] = []
        priority_target_source = "not_needed"
    elif not session_selection_rules:
        priority_targets = []
        priority_target_source = "no_canonical_scheduler_policy"
        selected_indices = _select_session_indices_evenly(len(session_profiles), normalized_days_available)
        selection_strategy = "bounded_even_spread_without_scheduler_rules"
    else:
        priority_targets = _rank_history_priority_exercises(
            history,
            limit=int(session_selection_rules.get("recent_history_exercise_limit") or 6),
        )
        priority_target_source = "history"
        if not priority_targets:
            priority_targets = _rank_structural_priority_exercises(
                session_profiles,
                structural_slot_role_priority,
            )
            priority_target_source = "session_structure" if priority_targets else "none"

        if not priority_targets:
            selected_indices = _select_session_indices_evenly(len(session_profiles), normalized_days_available)
            selection_strategy = "even_spread_fallback"
        else:
            selected_indices, selection_strategy = _select_sessions_with_continuity(
                session_profiles,
                normalized_days_available,
                priority_targets,
                required_indices=required_indices,
                day_role_priority=day_role_priority,
            )

    missed_day_policy = (
        str(session_selection_rules.get("missed_day_policy")).strip()
        if str(session_selection_rules.get("missed_day_policy") or "").strip()
        else None
    )
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
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_day_role = str(day_role or "").strip().lower()
    exercise_cap_rules = _scheduler_rule_dict(rule_set, "session_exercise_cap")
    limit = None
    if session_time_budget_minutes is not None:
        for threshold in exercise_cap_rules.get("time_budget_thresholds") or []:
            threshold_dict = _coerce_dict(threshold)
            maximum_minutes = int(threshold_dict.get("maximum_minutes") or 0)
            if maximum_minutes > 0 and int(session_time_budget_minutes) <= maximum_minutes:
                limit = int(threshold_dict.get("exercise_limit") or 0) or None
                break

    role_priority = {
        str(key).strip().lower(): int(value)
        for key, value in _coerce_dict(exercise_cap_rules.get("default_slot_role_priority")).items()
        if str(key).strip()
    }
    day_role_overrides = _coerce_dict(
        _coerce_dict(exercise_cap_rules.get("day_role_slot_role_priority_overrides")).get(normalized_day_role)
    )
    if day_role_overrides:
        role_priority.update(
            {
                str(key).strip().lower(): int(value)
                for key, value in day_role_overrides.items()
                if str(key).strip()
            }
        )

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


def resolve_scheduler_muscle_coverage_runtime(
    *,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    muscle_coverage_rules = _scheduler_rule_dict(rule_set, "muscle_coverage")
    tracked_muscles = [
        _normalize_scheduler_label(item)
        for item in muscle_coverage_rules.get("tracked_muscles") or []
        if _normalize_scheduler_label(item)
    ]
    minimum_sets_per_muscle = int(muscle_coverage_rules.get("minimum_sets_per_muscle") or 0)
    authored_label_normalization = {
        _normalize_scheduler_label(key): _normalize_scheduler_label(value)
        for key, value in _coerce_dict(muscle_coverage_rules.get("authored_label_normalization")).items()
        if _normalize_scheduler_label(key) and _normalize_scheduler_label(value)
    }

    return {
        "tracked_muscles": tracked_muscles,
        "minimum_sets_per_muscle": minimum_sets_per_muscle,
        "authored_label_normalization": authored_label_normalization,
        "decision_trace": {
            "interpreter": "resolve_scheduler_muscle_coverage_runtime",
            "version": "v1",
            "inputs": {
                "has_scheduler_rule_contract": bool(muscle_coverage_rules),
            },
            "outcome": {
                "tracked_muscles": list(tracked_muscles),
                "minimum_sets_per_muscle": minimum_sets_per_muscle,
                "normalization_label_count": len(authored_label_normalization),
            },
        },
    }


def resolve_scheduler_exercise_muscles_runtime(
    *,
    exercise: dict[str, Any] | None,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    exercise_dict = _coerce_dict(exercise)
    coverage_runtime = resolve_scheduler_muscle_coverage_runtime(rule_set=rule_set)
    normalization_map = coverage_runtime["authored_label_normalization"]

    explicit_labels: list[str] = []
    for field in ("primary_muscles", "secondary_muscles"):
        for item in exercise_dict.get(field) or []:
            normalized_label = _normalize_scheduler_label(item)
            if normalized_label:
                explicit_labels.append(normalized_label)

    normalized_muscles: list[str] = []
    unmapped_labels: list[str] = []
    for label in explicit_labels:
        normalized = normalization_map.get(label)
        if normalized and normalized not in normalized_muscles:
            normalized_muscles.append(normalized)
        elif normalized is None and label not in unmapped_labels:
            unmapped_labels.append(label)

    normalized_muscles.sort()
    unmapped_labels.sort()
    input_source = (
        "explicit_authored_muscle_metadata"
        if explicit_labels
        else "no_explicit_authored_muscle_metadata"
    )

    return {
        "normalized_muscles": normalized_muscles,
        "decision_trace": {
            "interpreter": "resolve_scheduler_exercise_muscles_runtime",
            "version": "v1",
            "inputs": {
                "exercise_id": str(exercise_dict.get("id") or ""),
                "exercise_name": str(exercise_dict.get("name") or ""),
                "primary_muscles": list(exercise_dict.get("primary_muscles") or []),
                "secondary_muscles": list(exercise_dict.get("secondary_muscles") or []),
            },
            "outcome": {
                "input_source": input_source,
                "normalized_muscles": list(normalized_muscles),
                "unmapped_authored_labels": list(unmapped_labels),
            },
        },
    }


def resolve_scheduler_deload_runtime(
    *,
    template_deload: dict[str, Any] | None,
    is_deload_week: bool,
    mesocycle_decision_trace: dict[str, Any] | None,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    template_deload_dict = _coerce_dict(template_deload)
    deload_rules = _coerce_dict(_coerce_dict(rule_set).get("deload_rules"))
    on_deload = _coerce_dict(deload_rules.get("on_deload"))

    source = "bounded_non_authoritative_noop"
    set_reduction_pct = 0
    load_reduction_pct = 0

    rule_set_set_reduction = _coerce_percentage(on_deload.get("set_reduction_percent"))
    rule_set_load_reduction = _coerce_percentage(on_deload.get("load_reduction_percent"))
    template_set_reduction = _coerce_percentage(template_deload_dict.get("set_reduction_pct"))
    template_load_reduction = _coerce_percentage(template_deload_dict.get("load_reduction_pct"))

    if rule_set_set_reduction is not None and rule_set_load_reduction is not None:
        source = "rule_set.deload_rules.on_deload"
        set_reduction_pct = rule_set_set_reduction
        load_reduction_pct = rule_set_load_reduction
    elif template_set_reduction is not None and template_load_reduction is not None:
        source = "template.deload"
        set_reduction_pct = template_set_reduction
        load_reduction_pct = template_load_reduction

    return {
        "active": bool(is_deload_week),
        "set_reduction_pct": set_reduction_pct,
        "load_reduction_pct": load_reduction_pct,
        "decision_trace": {
            "interpreter": "resolve_scheduler_deload_runtime",
            "version": "v1",
            "inputs": {
                "is_deload_week": bool(is_deload_week),
                "template_deload": dict(template_deload_dict),
                "mesocycle_interpreter": str(_coerce_dict(mesocycle_decision_trace).get("interpreter") or ""),
                "has_rule_set_on_deload": bool(on_deload),
            },
            "outcome": {
                "source": source,
                "active": bool(is_deload_week),
                "set_reduction_pct": set_reduction_pct,
                "load_reduction_pct": load_reduction_pct,
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
