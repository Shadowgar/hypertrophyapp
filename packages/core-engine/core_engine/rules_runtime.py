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
