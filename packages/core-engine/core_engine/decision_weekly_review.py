from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Any, cast

from .decision_progression import evaluate_stimulus_fatigue_response


_WEEKLY_REVIEW_GUIDANCE_MESSAGES = {
    "recovery_limited_reduce_load_and_complete_quality_volume": "Recovery signals are limited. Reduce load slightly and complete high-quality volume before pushing progression.",
    "target_fault_exercises_with_controlled_progression": "Several exercises need cleaner execution. Target those faults with controlled progression before raising overall stress.",
    "progressive_overload_ready": "Readiness is solid. Continue progressive overload next week.",
}

_WEEKLY_REVIEW_ADJUSTMENT_MESSAGES = {
    "maintain": "No exercise-specific override is required.",
    "missed_exercise_restart_conservative": "This exercise was missed last week. Restart slightly lighter and rebuild exposure.",
    "low_completion_secure_volume": "Completion was low. Trim intensity slightly and secure the planned volume first.",
    "below_target_reps_reduce_or_hold": "Reps fell below target. Hold or slightly reduce load until rep quality returns.",
    "above_target_reps_progress_load": "Reps exceeded target with sufficient readiness. Progress load next week.",
    "recovery_limited_hold_progression": "Recovery is constrained. Hold progression on this exercise until recoverability improves.",
    "weak_point_bounded_extra_practice": "This is a weak-point candidate with good readiness, so add a small bounded practice set.",
}

_WEEKLY_REVIEW_FAULT_GUIDANCE_MESSAGES = {
    "rebuild_exposure_with_conservative_load": "Rebuild exposure with a slightly conservative load after the missed exercise.",
    "complete_all_planned_sets_before_progression": "Complete all planned sets before pushing progression again.",
    "reduce_or_hold_load_and_recover": "Hold or slightly reduce load and recover until reps return to target.",
    "increase_load_next_exposure": "Performance was above target. Increase load on the next exposure.",
    "maintain_or_microload": "Performance stayed in range. Maintain load or microload if the next exposure stays clean.",
}

_WEAK_POINT_MAX_BOOSTED_EXERCISES = 2
_WEAK_POINT_SET_DELTA_CAP = 1
_WEAK_POINT_TOTAL_SET_BUDGET = 2
_WEAK_POINT_MIN_COMPLETION_FOR_BOOST = 90
_WEAK_POINT_MIN_READINESS_FOR_BOOST = 65
_WEAK_POINT_INTENSITY_MIN_SCALE = 0.93
_WEAK_POINT_INTENSITY_MAX_SCALE = 1.03
_REVIEW_SET_DELTA_MIN = -1
_REVIEW_SET_DELTA_MAX = 1
_REVIEW_ADDITIONAL_SET_CAP = 2
_REVIEW_INTENSITY_MIN_SCALE = 0.93
_REVIEW_INTENSITY_MAX_SCALE = 1.03


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_attr(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _normalize_string_list(values: list[str] | None) -> list[str]:
    return [str(item).strip() for item in (values or []) if str(item).strip()]


def _looks_like_human_rationale(value: str) -> bool:
    text = value.strip()
    return bool(text) and "_" not in text and "+" not in text


def _humanize_reason_code(reason: str, *, empty_message: str = "No rationale recorded.") -> str:
    normalized = reason.strip()
    if not normalized:
        return empty_message
    if _looks_like_human_rationale(normalized):
        return normalized
    text = normalized.replace("_", " ").replace("+", " and ").strip()
    if not text:
        return empty_message
    return text[:1].upper() + text[1:] + "."


def _weekly_review_adjustment_rationale(rationale: str) -> str:
    return _WEEKLY_REVIEW_ADJUSTMENT_MESSAGES.get(rationale, _humanize_reason_code(rationale))


def _weekly_review_global_guidance_rationale(guidance: str) -> str:
    return _WEEKLY_REVIEW_GUIDANCE_MESSAGES.get(guidance, _humanize_reason_code(guidance))


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _clamp_scale(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _round_to_increment(weight: float, increment: float = 2.5) -> float:
    return round(max(5.0, weight) / increment) * increment


def _resolve_rep_range(rep_range: Any) -> tuple[int, int]:
    if not isinstance(rep_range, list):
        return 8, 12
    minimum = int(rep_range[0]) if len(rep_range) > 0 else 8
    maximum = int(rep_range[1]) if len(rep_range) > 1 else minimum
    if minimum > maximum:
        minimum, maximum = maximum, minimum
    return minimum, maximum


def _empty_performance_bucket() -> dict[str, float]:
    return {"sets": 0.0, "reps_sum": 0.0, "weight_sum": 0.0}


def _clamp_review_set_delta(value: int) -> int:
    return max(_REVIEW_SET_DELTA_MIN, min(_REVIEW_SET_DELTA_MAX, value))


def _clamp_review_intensity_scale(value: float) -> float:
    return max(_REVIEW_INTENSITY_MIN_SCALE, min(_REVIEW_INTENSITY_MAX_SCALE, value))


def _resolve_global_review_adjustments(
    *,
    calories_per_kg: float,
    protein_per_kg: float,
    adherence_score: int,
    base_set_delta: int,
    base_weight_scale: float,
    base_readiness: int,
) -> tuple[int, float, int, list[dict[str, Any]]]:
    global_set_delta = base_set_delta
    global_weight_scale = base_weight_scale
    readiness_score = base_readiness
    applied_rules: list[dict[str, Any]] = []

    if calories_per_kg < 24:
        global_set_delta -= 1
        global_weight_scale *= 0.95
        readiness_score -= 20
        applied_rules.append({"rule": "low_calories_per_kg", "matched": True, "details": {"calories_per_kg": round(calories_per_kg, 2)}})
    elif calories_per_kg < 28:
        global_weight_scale *= 0.975
        readiness_score -= 10
        applied_rules.append({"rule": "moderate_calories_per_kg", "matched": True, "details": {"calories_per_kg": round(calories_per_kg, 2)}})
    elif calories_per_kg > 35 and adherence_score >= 4:
        global_weight_scale *= 1.01
        readiness_score += 5
        applied_rules.append({"rule": "surplus_with_adherence", "matched": True, "details": {"calories_per_kg": round(calories_per_kg, 2), "adherence_score": adherence_score}})

    if protein_per_kg < 1.6:
        global_weight_scale *= 0.98
        readiness_score -= 15
        applied_rules.append({"rule": "low_protein_per_kg", "matched": True, "details": {"protein_per_kg": round(protein_per_kg, 2)}})
    elif protein_per_kg >= 2.0:
        readiness_score += 3
        applied_rules.append({"rule": "high_protein_per_kg", "matched": True, "details": {"protein_per_kg": round(protein_per_kg, 2)}})

    if adherence_score <= 2:
        global_weight_scale *= 0.98
        readiness_score -= 15
        applied_rules.append({"rule": "low_adherence", "matched": True, "details": {"adherence_score": adherence_score}})

    return global_set_delta, global_weight_scale, readiness_score, applied_rules


def _resolve_readiness_state_adjustments(
    *,
    readiness_state: dict[str, Any] | None,
    base_readiness: int,
) -> tuple[int, str, list[dict[str, Any]]]:
    normalized_readiness_state = _coerce_dict(readiness_state)
    if not normalized_readiness_state:
        return base_readiness, "none", []

    sleep_quality_raw = normalized_readiness_state.get("sleep_quality")
    stress_level_raw = normalized_readiness_state.get("stress_level")
    pain_flags = _normalize_string_list(normalized_readiness_state.get("pain_flags"))

    sleep_quality = int(sleep_quality_raw) if sleep_quality_raw is not None else None
    stress_level = int(stress_level_raw) if stress_level_raw is not None else None
    readiness_score = base_readiness
    applied_rules: list[dict[str, Any]] = []

    if sleep_quality is not None:
        normalized_sleep = _clamp_int(sleep_quality, 1, 5)
        if normalized_sleep <= 2:
            readiness_score -= 8
            applied_rules.append({"rule": "low_sleep", "matched": True, "details": {"sleep_quality": normalized_sleep}})
        elif normalized_sleep == 3:
            readiness_score -= 3
            applied_rules.append({"rule": "moderate_sleep", "matched": True, "details": {"sleep_quality": normalized_sleep}})

    if stress_level is not None:
        normalized_stress = _clamp_int(stress_level, 1, 5)
        if normalized_stress >= 4:
            readiness_score -= 8
            applied_rules.append({"rule": "high_stress", "matched": True, "details": {"stress_level": normalized_stress}})
        elif normalized_stress == 3:
            readiness_score -= 3
            applied_rules.append({"rule": "moderate_stress", "matched": True, "details": {"stress_level": normalized_stress}})

    if pain_flags:
        readiness_score -= 6
        applied_rules.append({"rule": "pain_flags_present", "matched": True, "details": {"pain_flags": pain_flags}})

    return readiness_score, "context_readiness_state", applied_rules


def _coerce_stimulus_fatigue_response_snapshot(value: Any) -> dict[str, Any]:
    snapshot = _coerce_dict(value)
    if not snapshot:
        return {}

    signals = _coerce_dict(snapshot.get("signals"))
    normalized = {
        "stimulus_quality": str(snapshot.get("stimulus_quality") or "").strip().lower(),
        "fatigue_cost": str(snapshot.get("fatigue_cost") or "").strip().lower(),
        "recoverability": str(snapshot.get("recoverability") or "").strip().lower(),
        "progression_eligibility": bool(snapshot.get("progression_eligibility")),
        "deload_pressure": str(snapshot.get("deload_pressure") or "").strip().lower(),
        "substitution_pressure": str(snapshot.get("substitution_pressure") or "").strip().lower(),
        "signals": {
            "stimulus": _normalize_string_list(signals.get("stimulus")),
            "fatigue": _normalize_string_list(signals.get("fatigue")),
            "recoverability": _normalize_string_list(signals.get("recoverability")),
        },
    }
    required_fields = (
        "stimulus_quality",
        "fatigue_cost",
        "recoverability",
        "deload_pressure",
        "substitution_pressure",
    )
    if any(not normalized[field] for field in required_fields):
        return {}
    return normalized


def _resolve_weekly_review_stimulus_fatigue_response(
    *,
    summary: dict[str, Any],
    adherence_score: int,
    readiness_state: dict[str, Any] | None,
    coaching_state: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    canonical_snapshot = _coerce_stimulus_fatigue_response_snapshot(
        _coerce_dict(coaching_state).get("stimulus_fatigue_response")
    )
    if canonical_snapshot:
        return canonical_snapshot, "coaching_state.stimulus_fatigue_response"

    normalized_readiness_state = _coerce_dict(readiness_state)
    sleep_quality_raw = normalized_readiness_state.get("sleep_quality")
    stress_level_raw = normalized_readiness_state.get("stress_level")
    pain_flags = _normalize_string_list(normalized_readiness_state.get("pain_flags"))
    sleep_quality = int(sleep_quality_raw) if sleep_quality_raw is not None else None
    stress_level = int(stress_level_raw) if stress_level_raw is not None else None

    snapshot = evaluate_stimulus_fatigue_response(
        completion_pct=int(summary.get("completion_pct", 0) or 0),
        adherence_score=adherence_score,
        soreness_level="none",
        average_rpe=None,
        consecutive_underperformance_weeks=0,
        sleep_quality=sleep_quality,
        stress_level=stress_level,
        pain_flags=pain_flags,
    )
    return _coerce_stimulus_fatigue_response_snapshot(snapshot), "weekly_review_inputs"


def _resolve_weekly_review_exercise_override(
    row: dict[str, Any],
    *,
    readiness_score: int,
    allow_weak_point_boost: bool,
    allow_positive_progression: bool = True,
) -> dict[str, Any] | None:
    if int(row.get("fault_score", 0) or 0) <= 0:
        return None

    fault_reasons = [str(reason) for reason in row.get("fault_reasons") or []]
    set_delta = 0
    weight_scale = 1.0
    rationale = "maintain"

    if "missed_exercise" in fault_reasons:
        weight_scale *= 0.95
        rationale = "missed_exercise_restart_conservative"
    elif "low_completion" in fault_reasons:
        weight_scale *= 0.975
        rationale = "low_completion_secure_volume"

    if "below_target_reps" in fault_reasons:
        weight_scale *= 0.975
        rationale = "below_target_reps_reduce_or_hold"

    if "above_target_reps" in fault_reasons and readiness_score >= 70 and allow_positive_progression:
        weight_scale *= 1.025
        rationale = "above_target_reps_progress_load"
    elif "above_target_reps" in fault_reasons and not allow_positive_progression:
        rationale = "recovery_limited_hold_progression"

    weak_point_boost_blocked = any(reason in fault_reasons for reason in ("missed_exercise", "low_completion", "below_target_reps"))
    if (
        allow_weak_point_boost
        and not weak_point_boost_blocked
        and int(row.get("completion_pct", 0) or 0) >= _WEAK_POINT_MIN_COMPLETION_FOR_BOOST
        and readiness_score >= _WEAK_POINT_MIN_READINESS_FOR_BOOST
    ):
        set_delta = min(_WEAK_POINT_SET_DELTA_CAP, set_delta + 1)
        rationale = "weak_point_bounded_extra_practice"

    set_delta = _clamp_int(set_delta, -1, _WEAK_POINT_SET_DELTA_CAP)
    weight_scale = _clamp_scale(weight_scale, _WEAK_POINT_INTENSITY_MIN_SCALE, _WEAK_POINT_INTENSITY_MAX_SCALE)
    return {
        "primary_exercise_id": str(row.get("primary_exercise_id") or ""),
        "set_delta": set_delta,
        "weight_scale": round(weight_scale, 3),
        "rationale": rationale,
    }


def _resolve_stimulus_fatigue_adjustments(
    *,
    stimulus_fatigue_response: dict[str, Any] | None,
    base_set_delta: int,
    base_weight_scale: float,
) -> tuple[int, float, bool, bool, list[dict[str, Any]]]:
    sfr = _coerce_dict(stimulus_fatigue_response)
    if not sfr:
        return (
            _clamp_review_set_delta(base_set_delta),
            _clamp_review_intensity_scale(base_weight_scale),
            True,
            True,
            [],
        )

    deload_pressure = str(sfr.get("deload_pressure") or "low")
    recoverability = str(sfr.get("recoverability") or "moderate")
    fatigue_cost = str(sfr.get("fatigue_cost") or "moderate")
    substitution_pressure = str(sfr.get("substitution_pressure") or "low")

    global_set_delta = base_set_delta
    global_weight_scale = base_weight_scale
    allow_positive_progression = True
    allow_weak_point_boost = True
    applied_rules: list[dict[str, Any]] = []

    if deload_pressure == "high" and recoverability == "low":
        global_set_delta -= 1
        global_weight_scale *= 0.95
        allow_positive_progression = False
        allow_weak_point_boost = False
        applied_rules.append(
            {
                "rule": "sfr_recovery_limited_deload_pressure",
                "matched": True,
                "details": {
                    "deload_pressure": deload_pressure,
                    "recoverability": recoverability,
                },
            }
        )
    elif recoverability == "low" or fatigue_cost == "high" or substitution_pressure == "high":
        global_weight_scale *= 0.975
        allow_positive_progression = False
        allow_weak_point_boost = False
        applied_rules.append(
            {
                "rule": "sfr_recovery_limited_progression_cap",
                "matched": True,
                "details": {
                    "fatigue_cost": fatigue_cost,
                    "recoverability": recoverability,
                    "substitution_pressure": substitution_pressure,
                },
            }
        )

    return (
        _clamp_review_set_delta(global_set_delta),
        _clamp_review_intensity_scale(global_weight_scale),
        allow_positive_progression,
        allow_weak_point_boost,
        applied_rules,
    )


def _resolve_weekly_review_global_guidance(
    readiness_score: int,
    faulty_exercise_count: int,
    *,
    stimulus_fatigue_response: dict[str, Any] | None = None,
) -> str:
    sfr = _coerce_dict(stimulus_fatigue_response)
    if str(sfr.get("recoverability") or "") == "low" or str(sfr.get("deload_pressure") or "") == "high":
        return "recovery_limited_reduce_load_and_complete_quality_volume"
    if readiness_score < 55:
        return "recovery_limited_reduce_load_and_complete_quality_volume"
    if faulty_exercise_count > 0:
        return "target_fault_exercises_with_controlled_progression"
    return "progressive_overload_ready"


def _accumulate_single_planned_exercise(planned_index: dict[str, dict[str, Any]], exercise: dict[str, Any]) -> None:
    primary_exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or "")
    if not primary_exercise_id:
        return

    planned_sets = int(exercise.get("sets", 0) or 0)
    target_min, target_max = _resolve_rep_range(exercise.get("rep_range"))
    target_weight = float(exercise.get("recommended_working_weight", 0) or 0)
    bucket = planned_index.setdefault(
        primary_exercise_id,
        {
            "exercise_id": str(exercise.get("id") or primary_exercise_id),
            "name": str(exercise.get("name") or primary_exercise_id),
            "planned_sets": 0,
            "target_min_sum": 0,
            "target_max_sum": 0,
            "target_count": 0,
            "target_weight_sum": 0.0,
            "target_weight_count": 0,
        },
    )
    bucket["planned_sets"] += max(0, planned_sets)
    bucket["target_min_sum"] += target_min
    bucket["target_max_sum"] += target_max
    bucket["target_count"] += 1
    if target_weight > 0:
        bucket["target_weight_sum"] += target_weight
        bucket["target_weight_count"] += 1


def _accumulate_planned_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    planned_index: dict[str, dict[str, Any]] = {}
    for session in payload.get("sessions") or []:
        for exercise in session.get("exercises") or []:
            if isinstance(exercise, dict):
                _accumulate_single_planned_exercise(planned_index, exercise)
    return planned_index


def _collect_performed_index(logs: list[dict[str, Any]], planned_index: dict[str, dict[str, Any]]) -> dict[str, dict[str, float]]:
    performed_index: dict[str, dict[str, float]] = {}
    for row in logs:
        key = str(row.get("primary_exercise_id") or row.get("exercise_id") or "")
        if key not in planned_index:
            continue
        bucket = performed_index.setdefault(key, _empty_performance_bucket())
        bucket["sets"] += 1
        bucket["reps_sum"] += float(row.get("reps", 0) or 0)
        bucket["weight_sum"] += float(row.get("weight", 0) or 0)
    return performed_index


def _resolve_weekly_fault_reasons(
    completed_sets: int,
    completion_pct: int,
    average_reps: float,
    target_min: int,
    target_max: int,
) -> tuple[int, list[str]]:
    fault_score = 0
    fault_reasons: list[str] = []

    if completed_sets == 0:
        return 3, ["missed_exercise"]

    if completion_pct < 85:
        fault_score += 2
        fault_reasons.append("low_completion")
    if average_reps < target_min:
        fault_score += 2
        fault_reasons.append("below_target_reps")
    if average_reps > target_max:
        fault_score += 1
        fault_reasons.append("above_target_reps")
    return fault_score, fault_reasons


def _resolve_weekly_fault_guidance(
    completed_sets: int,
    completion_pct: int,
    average_reps: float,
    target_min: int,
    target_max: int,
) -> str:
    if completed_sets == 0:
        return "rebuild_exposure_with_conservative_load"
    if completion_pct < 85:
        return "complete_all_planned_sets_before_progression"
    if average_reps < target_min:
        return "reduce_or_hold_load_and_recover"
    if average_reps > target_max:
        return "increase_load_next_exposure"
    return "maintain_or_microload"


def _resolve_weekly_fault_level(fault_score: int) -> str:
    if fault_score >= 3:
        return "high"
    if fault_score == 2:
        return "medium"
    if fault_score == 1:
        return "low"
    return "none"


def _build_weekly_exercise_fault(
    primary_exercise_id: str,
    planned: dict[str, Any],
    performed: dict[str, float],
) -> tuple[dict[str, Any], int, int]:
    planned_sets = int(planned["planned_sets"])
    target_count = max(1, int(planned["target_count"]))
    target_min = int(round(planned["target_min_sum"] / target_count))
    target_max = int(round(planned["target_max_sum"] / target_count))

    target_weight_count = int(planned["target_weight_count"])
    target_weight = (
        float(planned["target_weight_sum"]) / max(1, target_weight_count)
        if target_weight_count > 0
        else 0.0
    )
    completed_sets = int(performed["sets"])
    average_reps = float(performed["reps_sum"]) / completed_sets if completed_sets > 0 else 0.0
    average_weight = float(performed["weight_sum"]) / completed_sets if completed_sets > 0 else 0.0
    completion_pct = int((completed_sets / max(1, planned_sets)) * 100)

    fault_score, fault_reasons = _resolve_weekly_fault_reasons(completed_sets, completion_pct, average_reps, target_min, target_max)
    return (
        {
            "primary_exercise_id": primary_exercise_id,
            "exercise_id": str(planned["exercise_id"]),
            "name": str(planned["name"]),
            "planned_sets": planned_sets,
            "completed_sets": completed_sets,
            "completion_pct": completion_pct,
            "target_reps_min": target_min,
            "target_reps_max": target_max,
            "average_performed_reps": round(average_reps, 2),
            "target_weight": round(target_weight, 2),
            "average_performed_weight": round(average_weight, 2),
            "guidance": _resolve_weekly_fault_guidance(completed_sets, completion_pct, average_reps, target_min, target_max),
            "fault_score": fault_score,
            "fault_level": _resolve_weekly_fault_level(fault_score),
            "fault_reasons": fault_reasons,
        },
        planned_sets,
        completed_sets,
    )


def _weekly_review_fault_guidance_rationale(guidance: str) -> str:
    return _WEEKLY_REVIEW_FAULT_GUIDANCE_MESSAGES.get(guidance, _humanize_reason_code(guidance))


def resolve_weekly_review_window(*, today: date) -> dict[str, date | bool]:
    current_week_start = today - timedelta(days=today.weekday())
    today_is_sunday = today.weekday() == 6
    week_start = current_week_start + timedelta(days=7) if today_is_sunday else current_week_start
    previous_week_start = week_start - timedelta(days=7)
    return {
        "today_is_sunday": today_is_sunday,
        "current_week_start": current_week_start,
        "week_start": week_start,
        "previous_week_start": previous_week_start,
        "previous_week_end": week_start - timedelta(days=1),
    }


def prepare_weekly_review_submit_window(
    *,
    today: date,
    requested_week_start: date | None,
) -> dict[str, Any]:
    window = resolve_weekly_review_window(today=today)
    source = "request" if requested_week_start is not None else "window_default"
    week_start = requested_week_start or cast(date, window["week_start"])
    previous_week_start = week_start - timedelta(days=7)
    return {
        "week_start": week_start,
        "previous_week_start": previous_week_start,
        "decision_trace": {
            "interpreter": "prepare_weekly_review_submit_window",
            "version": "v1",
            "inputs": {
                "today": today.isoformat(),
                "requested_week_start": requested_week_start.isoformat() if requested_week_start else None,
            },
            "outcome": {
                "source": source,
                "week_start": week_start.isoformat(),
                "previous_week_start": previous_week_start.isoformat(),
            },
        },
    }


def build_weekly_review_status_payload(
    *,
    today: date,
    existing_review_submitted: bool,
    previous_week_summary: dict[str, Any],
) -> dict[str, Any]:
    window = resolve_weekly_review_window(today=today)
    today_is_sunday = bool(window["today_is_sunday"])
    return {
        "today_is_sunday": today_is_sunday,
        "review_required": today_is_sunday and not existing_review_submitted,
        "current_week_start": window["current_week_start"],
        "week_start": window["week_start"],
        "previous_week_start": window["previous_week_start"],
        "previous_week_end": window["previous_week_end"],
        "existing_review_submitted": existing_review_submitted,
        "previous_week_summary": previous_week_summary,
    }


def prepare_weekly_review_status_route_runtime(
    *,
    today: date,
    existing_review_submitted: bool,
    previous_week_summary: dict[str, Any],
) -> dict[str, Any]:
    window = resolve_weekly_review_window(today=today)
    response_payload = build_weekly_review_status_payload(
        today=today,
        existing_review_submitted=existing_review_submitted,
        previous_week_summary=previous_week_summary,
    )
    return {
        "window": window,
        "response_payload": response_payload,
        "decision_trace": {
            "interpreter": "prepare_weekly_review_status_route_runtime",
            "version": "v1",
            "inputs": {
                "today": today.isoformat(),
                "existing_review_submitted": existing_review_submitted,
                "faulty_exercise_count": int(previous_week_summary.get("faulty_exercise_count") or 0),
            },
            "outcome": {
                "week_start": cast(date, window["week_start"]).isoformat(),
                "previous_week_start": cast(date, window["previous_week_start"]).isoformat(),
                "review_required": bool(response_payload.get("review_required")),
            },
        },
    }


def summarize_weekly_review_performance(
    *,
    previous_week_start: date,
    week_start: date,
    previous_plan_payload: dict[str, Any],
    performed_logs: list[dict[str, Any]],
) -> dict[str, Any]:
    planned_index = _accumulate_planned_index(previous_plan_payload)
    performed_index = _collect_performed_index(performed_logs, planned_index)

    exercise_faults: list[dict[str, Any]] = []
    planned_sets_total = 0
    completed_sets_total = 0
    fault_steps: list[dict[str, Any]] = []

    for primary_exercise_id, planned in planned_index.items():
        fault, planned_sets, completed_sets = _build_weekly_exercise_fault(
            primary_exercise_id,
            planned,
            performed_index.get(primary_exercise_id, _empty_performance_bucket()),
        )
        planned_sets_total += planned_sets
        completed_sets_total += completed_sets
        exercise_faults.append(fault)
        fault_steps.append(
            {
                "exercise_id": primary_exercise_id,
                "fault_score": fault["fault_score"],
                "fault_reasons": list(fault["fault_reasons"]),
                "guidance": fault["guidance"],
                "guidance_rationale": _weekly_review_fault_guidance_rationale(str(fault["guidance"])),
            }
        )

    exercise_faults.sort(key=lambda row: (-int(row["fault_score"]), int(row["completion_pct"]), str(row["name"])))
    completion_pct = int((completed_sets_total / max(1, planned_sets_total)) * 100)
    faulty_exercise_count = sum(1 for row in exercise_faults if int(row["fault_score"]) > 0)

    return {
        "previous_week_start": previous_week_start,
        "previous_week_end": week_start - timedelta(days=1),
        "planned_sets_total": planned_sets_total,
        "completed_sets_total": completed_sets_total,
        "completion_pct": completion_pct,
        "faulty_exercise_count": faulty_exercise_count,
        "exercise_faults": exercise_faults,
        "decision_trace": {
            "interpreter": "summarize_weekly_review_performance",
            "version": "v1",
            "inputs": {
                "previous_week_start": previous_week_start.isoformat(),
                "week_start": week_start.isoformat(),
                "planned_exercise_count": len(planned_index),
                "performed_log_count": len(performed_logs),
            },
            "steps": fault_steps,
            "outcome": {
                "planned_sets_total": planned_sets_total,
                "completed_sets_total": completed_sets_total,
                "completion_pct": completion_pct,
                "faulty_exercise_count": faulty_exercise_count,
            },
        },
    }


def build_weekly_review_performance_summary(
    *,
    previous_week_start: date,
    week_start: date,
    previous_plan: Any | None,
    performed_logs: list[Any],
) -> dict[str, Any]:
    previous_plan_payload = _coerce_dict(_read_attr(previous_plan, "payload", {}))
    serialized_logs = [
        {
            "primary_exercise_id": _read_attr(row, "primary_exercise_id"),
            "exercise_id": _read_attr(row, "exercise_id"),
            "reps": _read_attr(row, "reps"),
            "weight": _read_attr(row, "weight"),
        }
        for row in performed_logs
    ]
    return summarize_weekly_review_performance(
        previous_week_start=previous_week_start,
        week_start=week_start,
        previous_plan_payload=previous_plan_payload,
        performed_logs=serialized_logs,
    )


def prepare_weekly_review_summary_route_runtime(
    *,
    previous_week_start: date,
    week_start: date,
    previous_plan: Any | None,
    performed_logs: list[Any],
) -> dict[str, Any]:
    summary_payload = build_weekly_review_performance_summary(
        previous_week_start=previous_week_start,
        week_start=week_start,
        previous_plan=previous_plan,
        performed_logs=performed_logs,
    )
    return {
        "summary_payload": summary_payload,
        "decision_trace": {
            "interpreter": "prepare_weekly_review_summary_route_runtime",
            "version": "v1",
            "inputs": {
                "previous_week_start": previous_week_start.isoformat(),
                "week_start": week_start.isoformat(),
                "has_previous_plan": previous_plan is not None,
                "performed_log_count": len(performed_logs),
            },
            "outcome": {
                "planned_sets_total": int(summary_payload.get("planned_sets_total") or 0),
                "completed_sets_total": int(summary_payload.get("completed_sets_total") or 0),
                "faulty_exercise_count": int(summary_payload.get("faulty_exercise_count") or 0),
            },
        },
    }


def interpret_weekly_review_decision(
    *,
    summary: dict[str, Any],
    body_weight: float,
    calories: int,
    protein: int,
    adherence_score: int,
    readiness_state: dict[str, Any] | None = None,
    coaching_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    calories_per_kg = float(calories) / max(1.0, body_weight)
    protein_per_kg = float(protein) / max(1.0, body_weight)
    global_set_delta = 0
    global_weight_scale = 1.0
    readiness_score = 100

    global_set_delta, global_weight_scale, readiness_score, applied_global_rules = _resolve_global_review_adjustments(
        calories_per_kg=calories_per_kg,
        protein_per_kg=protein_per_kg,
        adherence_score=adherence_score,
        base_set_delta=global_set_delta,
        base_weight_scale=global_weight_scale,
        base_readiness=readiness_score,
    )
    readiness_score, readiness_source, readiness_state_rules = _resolve_readiness_state_adjustments(
        readiness_state=readiness_state,
        base_readiness=readiness_score,
    )
    stimulus_fatigue_response, stimulus_fatigue_response_source = _resolve_weekly_review_stimulus_fatigue_response(
        summary=summary,
        adherence_score=adherence_score,
        readiness_state=readiness_state,
        coaching_state=coaching_state,
    )
    global_set_delta, global_weight_scale, allow_positive_progression, allow_weak_point_boosts, sfr_adjustment_rules = (
        _resolve_stimulus_fatigue_adjustments(
            stimulus_fatigue_response=stimulus_fatigue_response,
            base_set_delta=global_set_delta,
            base_weight_scale=global_weight_scale,
        )
    )

    exercise_faults = [item for item in summary.get("exercise_faults") or [] if isinstance(item, dict)]
    weak_point_exercises = [str(row.get("primary_exercise_id") or "") for row in exercise_faults if int(row.get("fault_score", 0) or 0) > 0][:3]
    overrides: list[dict[str, Any]] = []
    override_steps: list[dict[str, Any]] = []
    boosted_exercise_ids: list[str] = []
    remaining_set_budget = _WEAK_POINT_TOTAL_SET_BUDGET

    for row in exercise_faults:
        primary_exercise_id = str(row.get("primary_exercise_id") or "")
        allow_weak_point_boost = (
            primary_exercise_id in weak_point_exercises
            and len(boosted_exercise_ids) < _WEAK_POINT_MAX_BOOSTED_EXERCISES
            and remaining_set_budget > 0
            and allow_weak_point_boosts
        )
        override = _resolve_weekly_review_exercise_override(
            row,
            readiness_score=readiness_score,
            allow_weak_point_boost=allow_weak_point_boost,
            allow_positive_progression=allow_positive_progression,
        )
        if override is not None:
            overrides.append(override)
            override_steps.append(
                {
                    "exercise_id": primary_exercise_id,
                    "fault_reasons": list(row.get("fault_reasons") or []),
                    "override": {
                        **override,
                        "rationale_text": _weekly_review_adjustment_rationale(str(override["rationale"])),
                    },
                }
            )
            if int(override["set_delta"]) > 0:
                boosted_exercise_ids.append(primary_exercise_id)
                remaining_set_budget = max(0, remaining_set_budget - int(override["set_delta"]))

    readiness_score = _clamp_int(readiness_score, 1, 100)
    global_guidance = _resolve_weekly_review_global_guidance(
        readiness_score,
        int(summary.get("faulty_exercise_count", 0) or 0),
        stimulus_fatigue_response=stimulus_fatigue_response,
    )
    global_guidance_rationale = _weekly_review_global_guidance_rationale(global_guidance)
    response_adjustments = {
        "global_set_delta": global_set_delta,
        "global_weight_scale": round(global_weight_scale, 3),
        "weak_point_exercises": weak_point_exercises,
        "exercise_overrides": overrides,
    }
    decision_trace = {
        "interpreter": "interpret_weekly_review_decision",
        "version": "v1",
        "inputs": {
            "body_weight": body_weight,
            "calories": calories,
            "protein": protein,
            "adherence_score": adherence_score,
            "calories_per_kg": round(calories_per_kg, 3),
            "protein_per_kg": round(protein_per_kg, 3),
            "summary_completion_pct": int(summary.get("completion_pct", 0) or 0),
            "faulty_exercise_count": int(summary.get("faulty_exercise_count", 0) or 0),
            "readiness_state_present": bool(_coerce_dict(readiness_state)),
            "coaching_state_sfr_present": bool(
                _coerce_stimulus_fatigue_response_snapshot(
                    _coerce_dict(coaching_state).get("stimulus_fatigue_response")
                )
            ),
        },
        "steps": [
            {
                "decision": "global_adjustments",
                "result": {
                    "global_set_delta": global_set_delta,
                    "global_weight_scale": round(global_weight_scale, 3),
                    "readiness_score": readiness_score,
                    "matched_rules": applied_global_rules,
                },
            },
            {
                "decision": "readiness_state_adjustments",
                "result": {
                    "source": readiness_source,
                    "readiness_score": readiness_score,
                    "matched_rules": readiness_state_rules,
                },
            },
            {
                "decision": "stimulus_fatigue_response",
                "result": {
                    "source": stimulus_fatigue_response_source,
                    **deepcopy(stimulus_fatigue_response),
                },
            },
            {
                "decision": "stimulus_fatigue_adjustments",
                "result": {
                    "global_set_delta": global_set_delta,
                    "global_weight_scale": round(global_weight_scale, 3),
                    "allow_positive_progression": allow_positive_progression,
                    "allow_weak_point_boost": allow_weak_point_boosts,
                    "matched_rules": sfr_adjustment_rules,
                },
            },
            {
                "decision": "weak_point_candidates",
                "result": {
                    "weak_point_exercises": weak_point_exercises,
                    "max_boosted_exercises": _WEAK_POINT_MAX_BOOSTED_EXERCISES,
                    "remaining_set_budget": remaining_set_budget,
                },
            },
            {"decision": "exercise_overrides", "result": override_steps},
        ],
        "outcome": {
            "readiness_score": readiness_score,
            "global_guidance": global_guidance,
            "global_guidance_rationale": global_guidance_rationale,
            "global_set_delta": response_adjustments["global_set_delta"],
            "global_weight_scale": response_adjustments["global_weight_scale"],
            "weak_point_exercises": weak_point_exercises,
            "boosted_exercise_ids": boosted_exercise_ids,
            "stimulus_fatigue_response_source": stimulus_fatigue_response_source,
            "stimulus_fatigue_response": deepcopy(stimulus_fatigue_response),
        },
    }
    storage_adjustments = {
        "global": {
            "set_delta": response_adjustments["global_set_delta"],
            "weight_scale": response_adjustments["global_weight_scale"],
        },
        "weak_point_exercises": response_adjustments["weak_point_exercises"],
        "exercise_overrides": {
            item["primary_exercise_id"]: {
                "set_delta": item["set_delta"],
                "weight_scale": item["weight_scale"],
                "rationale": item["rationale"],
            }
            for item in response_adjustments["exercise_overrides"]
        },
        "weak_point_boosted_exercises": boosted_exercise_ids,
        "weak_point_caps": {
            "max_boosted_exercises": _WEAK_POINT_MAX_BOOSTED_EXERCISES,
            "max_set_delta_per_exercise": _WEAK_POINT_SET_DELTA_CAP,
            "max_total_weak_point_set_delta": _WEAK_POINT_TOTAL_SET_BUDGET,
            "intensity_min_scale": _WEAK_POINT_INTENSITY_MIN_SCALE,
            "intensity_max_scale": _WEAK_POINT_INTENSITY_MAX_SCALE,
        },
        "decision_trace": decision_trace,
    }
    return {
        "readiness_score": readiness_score,
        "global_guidance": global_guidance,
        "adjustments": response_adjustments,
        "storage_adjustments": storage_adjustments,
        "decision_trace": decision_trace,
    }


def build_weekly_review_decision_payload(
    *,
    summary: dict[str, Any],
    body_weight: float,
    calories: int,
    protein: int,
    adherence_score: int,
    readiness_state: dict[str, Any] | None = None,
    coaching_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = interpret_weekly_review_decision(
        summary=summary,
        body_weight=body_weight,
        calories=calories,
        protein=protein,
        adherence_score=adherence_score,
        readiness_state=readiness_state,
        coaching_state=coaching_state,
    )
    return {
        "readiness_score": int(decision.get("readiness_score") or 0),
        "global_guidance": str(decision.get("global_guidance") or ""),
        "adjustments": deepcopy(_coerce_dict(decision.get("adjustments"))),
        "storage_adjustments": deepcopy(_coerce_dict(decision.get("storage_adjustments"))),
        "decision_trace": deepcopy(_coerce_dict(decision.get("decision_trace"))),
    }


def _resolve_weekly_review_plan_adjustments(
    adjustments: dict[str, Any],
) -> tuple[int, float, dict[str, Any], list[str]]:
    global_adjustments = _coerce_dict(adjustments.get("global"))
    global_set_delta = _clamp_review_set_delta(int(global_adjustments.get("set_delta", 0) or 0))
    global_weight_scale = _clamp_review_intensity_scale(
        _clamp_scale(float(global_adjustments.get("weight_scale", 1.0) or 1.0), 0.8, 1.2)
    )
    exercise_overrides = _coerce_dict(adjustments.get("exercise_overrides"))
    weak_points_raw = adjustments.get("weak_point_exercises")
    weak_points = [str(item) for item in weak_points_raw] if isinstance(weak_points_raw, list) else []
    return global_set_delta, global_weight_scale, exercise_overrides, weak_points


def _apply_weekly_review_adjustment_to_exercise(
    exercise: dict[str, Any],
    *,
    global_set_delta: int,
    global_weight_scale: float,
    exercise_overrides: dict[str, Any],
) -> None:
    primary_exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or "")
    per_exercise = _coerce_dict(exercise_overrides.get(primary_exercise_id))
    exercise_set_delta = _clamp_review_set_delta(int(per_exercise.get("set_delta", 0) or 0))
    exercise_weight_scale = _clamp_review_intensity_scale(
        _clamp_scale(float(per_exercise.get("weight_scale", 1.0) or 1.0), 0.8, 1.2)
    )

    original_sets = int(exercise.get("sets", 1) or 1)
    adjusted_sets = original_sets + global_set_delta + exercise_set_delta
    max_sets = max(1, original_sets + _REVIEW_ADDITIONAL_SET_CAP)
    exercise["sets"] = max(1, min(max_sets, adjusted_sets))

    original_weight = float(exercise.get("recommended_working_weight", 20) or 20)
    scaled_weight = original_weight * global_weight_scale * exercise_weight_scale
    exercise["recommended_working_weight"] = _round_to_increment(scaled_weight)

    rationale = per_exercise.get("rationale")
    if rationale:
        exercise["adaptive_rationale"] = str(rationale)


def _build_weekly_review_adaptive_review(
    *,
    global_set_delta: int,
    global_weight_scale: float,
    weak_points: list[str],
    review_context: dict[str, Any] | None,
    decision_trace: dict[str, Any] | None,
) -> dict[str, Any]:
    adaptive_review = {
        "global_set_delta": global_set_delta,
        "global_weight_scale": global_weight_scale,
        "weak_point_exercises": weak_points,
    }
    if isinstance(review_context, dict):
        week_start = review_context.get("week_start")
        reviewed_on = review_context.get("reviewed_on")
        if week_start:
            adaptive_review["week_start"] = str(week_start)
        if reviewed_on:
            adaptive_review["reviewed_on"] = str(reviewed_on)
    if isinstance(decision_trace, dict):
        adaptive_review["decision_trace"] = decision_trace
    return adaptive_review


def apply_weekly_review_adjustments_to_plan(
    *,
    plan_payload: dict[str, Any],
    review_adjustments: dict[str, Any] | None,
    review_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(review_adjustments, dict):
        return deepcopy(plan_payload)

    plan = deepcopy(plan_payload)
    global_set_delta, global_weight_scale, exercise_overrides, weak_points = _resolve_weekly_review_plan_adjustments(
        review_adjustments
    )
    decision_trace = _coerce_dict(review_adjustments.get("decision_trace")) or None

    for session in plan.get("sessions") or []:
        if not isinstance(session, dict):
            continue
        for exercise in session.get("exercises") or []:
            if not isinstance(exercise, dict):
                continue
            _apply_weekly_review_adjustment_to_exercise(
                exercise,
                global_set_delta=global_set_delta,
                global_weight_scale=global_weight_scale,
                exercise_overrides=exercise_overrides,
            )

    plan["adaptive_review"] = _build_weekly_review_adaptive_review(
        global_set_delta=global_set_delta,
        global_weight_scale=global_weight_scale,
        weak_points=weak_points,
        review_context=review_context,
        decision_trace=decision_trace,
    )
    return plan


def build_weekly_review_submit_payload(
    *,
    week_start: date,
    previous_week_start: date,
    summary: dict[str, Any],
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "review_logged",
        "week_start": week_start,
        "previous_week_start": previous_week_start,
        "readiness_score": int(decision_payload.get("readiness_score") or 0),
        "global_guidance": str(decision_payload.get("global_guidance") or ""),
        "fault_count": int(summary.get("faulty_exercise_count", 0) or 0),
        "summary": deepcopy(summary),
        "adjustments": deepcopy(_coerce_dict(decision_payload.get("adjustments"))),
        "decision_trace": deepcopy(_coerce_dict(decision_payload.get("decision_trace"))),
    }


def build_weekly_review_cycle_persistence_payload(
    *,
    summary: dict[str, Any],
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    exercise_faults = [
        deepcopy(_coerce_dict(item))
        for item in (summary.get("exercise_faults") or [])
        if isinstance(item, dict)
    ]
    storage_adjustments = deepcopy(_coerce_dict(decision_payload.get("storage_adjustments")))
    return {
        "faults": {"exercise_faults": exercise_faults},
        "adjustments": storage_adjustments,
        "decision_trace": {
            "interpreter": "build_weekly_review_cycle_persistence_payload",
            "version": "v1",
            "inputs": {
                "fault_count": len(exercise_faults),
                "has_storage_adjustments": bool(storage_adjustments),
            },
            "outcome": {
                "fault_count": len(exercise_faults),
                "adjustment_keys": sorted(storage_adjustments.keys()),
            },
        },
    }


def prepare_weekly_review_submit_persistence_values(
    *,
    user_id: str,
    reviewed_on: date,
    week_start: date,
    previous_week_start: date,
    body_weight: float,
    calories: int,
    protein: int,
    fat: int,
    carbs: int,
    adherence_score: int,
    notes: str | None,
    summary_payload: dict[str, Any],
    review_persistence_payload: dict[str, Any],
) -> dict[str, Any]:
    checkin_values = {
        "user_id": user_id,
        "week_start": week_start,
        "body_weight": body_weight,
        "adherence_score": adherence_score,
        "notes": notes,
    }
    review_values = {
        "user_id": user_id,
        "reviewed_on": reviewed_on,
        "week_start": week_start,
        "previous_week_start": previous_week_start,
        "body_weight": body_weight,
        "calories": calories,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
        "adherence_score": adherence_score,
        "notes": notes,
        "faults": deepcopy(_coerce_dict(review_persistence_payload.get("faults"))),
        "adjustments": deepcopy(_coerce_dict(review_persistence_payload.get("adjustments"))),
        "summary": deepcopy(summary_payload),
    }
    return {
        "checkin_values": checkin_values,
        "review_values": review_values,
        "decision_trace": {
            "interpreter": "prepare_weekly_review_submit_persistence_values",
            "version": "v1",
            "inputs": {
                "user_id": user_id,
                "week_start": week_start.isoformat(),
                "previous_week_start": previous_week_start.isoformat(),
                "reviewed_on": reviewed_on.isoformat(),
                "has_notes": bool((notes or "").strip()),
            },
            "outcome": {
                "fault_count": len(_coerce_dict(review_values["faults"]).get("exercise_faults") or []),
                "has_adjustments": bool(review_values["adjustments"]),
            },
        },
    }


def prepare_weekly_review_submit_route_runtime(
    *,
    user_id: str,
    reviewed_on: date,
    week_start: date,
    previous_week_start: date,
    body_weight: float,
    calories: int,
    protein: int,
    fat: int,
    carbs: int,
    adherence_score: int,
    notes: str | None,
    nutrition_phase: str | None,
    summary_payload: dict[str, Any],
    readiness_state: dict[str, Any] | None = None,
    coaching_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision_payload = build_weekly_review_decision_payload(
        summary=summary_payload,
        body_weight=body_weight,
        calories=calories,
        protein=protein,
        adherence_score=adherence_score,
        readiness_state=readiness_state,
        coaching_state=coaching_state,
    )
    review_persistence_payload = build_weekly_review_cycle_persistence_payload(
        summary=summary_payload,
        decision_payload=decision_payload,
    )
    user_update_payload = build_weekly_review_user_update_payload(
        body_weight=body_weight,
        calories=calories,
        protein=protein,
        fat=fat,
        carbs=carbs,
        nutrition_phase=nutrition_phase,
    )
    submit_persistence_values = prepare_weekly_review_submit_persistence_values(
        user_id=user_id,
        reviewed_on=reviewed_on,
        week_start=week_start,
        previous_week_start=previous_week_start,
        body_weight=body_weight,
        calories=calories,
        protein=protein,
        fat=fat,
        carbs=carbs,
        adherence_score=adherence_score,
        notes=notes,
        summary_payload=summary_payload,
        review_persistence_payload=review_persistence_payload,
    )
    response_payload = build_weekly_review_submit_payload(
        week_start=week_start,
        previous_week_start=previous_week_start,
        summary=summary_payload,
        decision_payload=decision_payload,
    )
    return {
        "decision_payload": decision_payload,
        "review_persistence_payload": review_persistence_payload,
        "user_update_payload": user_update_payload,
        "submit_persistence_values": submit_persistence_values,
        "response_payload": response_payload,
        "decision_trace": {
            "interpreter": "prepare_weekly_review_submit_route_runtime",
            "version": "v1",
            "inputs": {
                "user_id": user_id,
                "week_start": week_start.isoformat(),
                "previous_week_start": previous_week_start.isoformat(),
                "reviewed_on": reviewed_on.isoformat(),
                "fault_count": int(summary_payload.get("faulty_exercise_count", 0) or 0),
            },
            "outcome": {
                "readiness_score": int(decision_payload.get("readiness_score") or 0),
                "global_guidance": str(decision_payload.get("global_guidance") or ""),
                "has_review_adjustments": bool(_coerce_dict(review_persistence_payload.get("adjustments"))),
                "updates_nutrition_phase": "nutrition_phase" in user_update_payload,
            },
        },
    }


def build_weekly_review_user_update_payload(
    *,
    body_weight: float,
    calories: int,
    protein: int,
    fat: int,
    carbs: int,
    nutrition_phase: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "weight": body_weight,
        "calories": calories,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
    }
    if nutrition_phase:
        payload["nutrition_phase"] = nutrition_phase
    return payload


def prepare_weekly_review_log_window_runtime(
    *,
    previous_week_start: date,
    week_start: date,
) -> dict[str, Any]:
    window_start = datetime.combine(previous_week_start, datetime.min.time())
    window_end = datetime.combine(week_start, datetime.min.time())
    return {
        "window_start": window_start,
        "window_end": window_end,
        "decision_trace": {
            "interpreter": "prepare_weekly_review_log_window_runtime",
            "version": "v1",
            "inputs": {
                "previous_week_start": previous_week_start.isoformat(),
                "week_start": week_start.isoformat(),
            },
        },
    }
