from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
import re
from typing import Any, Literal, cast

from .onboarding_adaptation import adapt_onboarding_frequency
from .scheduler import generate_week_plan
from .rules_runtime import evaluate_deload_signal, resolve_adaptive_rule_runtime, resolve_repeat_failure_substitution
from .warmups import compute_warmups


ProgressionAction = Literal["progress", "hold", "deload"]
ProgramPhase = Literal["accumulation", "intensification", "deload"]


_PROGRAM_REASON_MESSAGES = {
    "no_compatible_programs": "No compatible program was found for the current availability, so keep the current selection.",
    "current_not_compatible": "The current program no longer matches the available training days or split preference. Move to the first compatible option.",
    "low_adherence_keep_program": "Recent adherence is low. Keep the current program stable before rotating templates.",
    "days_adaptation_upgrade": "A different compatible template can preserve weekly coverage better at the current day availability.",
    "coverage_gap_rotate": "The latest plan left a coverage gap. Rotate to a compatible template with better distribution.",
    "mesocycle_complete_rotate": "The current mesocycle appears complete. Rotate to a fresh compatible template.",
    "maintain_current_program": "The current program remains compatible and no stronger rotation signal is present.",
    "target_matches_current": "The requested program already matches the current selection.",
}

_PROGRESSION_REASON_CLAUSES = {
    "low_completion": "session completion has been too low",
    "low_adherence": "adherence has dropped below the target threshold",
    "high_soreness": "fatigue and soreness are elevated",
}

_PHASE_TRANSITION_REASON_MESSAGES = {
    "resume_accumulation": "Deload work appears sufficient. Resume accumulation and rebuild workload.",
    "extend_deload_low_readiness": "Stay in deload because readiness is still too low to resume hard training.",
    "intro_phase_protection": "Stay in accumulation. Early underperformance is still within the intro phase and should not be treated as a true stall.",
    "accumulation_stall": "Accumulation has stalled. Transition into deload to recover before rebuilding momentum.",
    "accumulation_complete": "Accumulation has run its course and readiness is high enough to move into intensification.",
    "continue_accumulation": "Stay in accumulation. Current readiness and momentum do not justify a phase change yet.",
    "intensification_fatigue_cap": "End intensification and deload before fatigue outpaces recovery.",
    "continue_intensification": "Stay in intensification. Current performance still supports heavier work in this phase.",
    "phase_apply": "Apply the recommended phase transition.",
}

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
    "weak_point_bounded_extra_practice": "This is a weak-point candidate with good readiness, so add a small bounded practice set.",
}

_WEEKLY_REVIEW_FAULT_GUIDANCE_MESSAGES = {
    "rebuild_exposure_with_conservative_load": "Rebuild exposure with a slightly conservative load after the missed exercise.",
    "complete_all_planned_sets_before_progression": "Complete all planned sets before pushing progression again.",
    "reduce_or_hold_load_and_recover": "Hold or slightly reduce load and recover until reps return to target.",
    "increase_load_next_exposure": "Performance was above target. Increase load on the next exposure.",
    "maintain_or_microload": "Performance stayed in range. Maintain load or microload if the next exposure stays clean.",
}

_WORKOUT_GUIDANCE_STATIC_MESSAGES = {
    "remaining_sets_hold_load_and_match_target_reps": "Keep the same load for the remaining sets and match the programmed rep target.",
    "remaining_sets_increase_load_keep_reps_controlled": "Reps are well above target. Increase load slightly and keep the next sets controlled.",
    "incomplete_session_finish_remaining_sets_next_exposure": "Finish the remaining planned sets before making a progression decision.",
    "finish_all_planned_sets_for_reliable_progression": "Complete every planned set so the next load decision is based on a full session.",
    "solid_execution_maintain_progression": "Execution matched the plan. Keep the current progression path.",
}

_WORKOUT_GUIDANCE_TEMPLATE_MESSAGES = {
    "above_target_reps_increase_load_next_exposure": (
        "increase_load",
        "Performance exceeded the target range. Increase load next exposure.",
    ),
    "within_target_reps_hold_or_microload": (
        "hold_load",
        "Performance stayed in range. Hold load and keep building reps.",
    ),
    "session_complete_hold_load_for_next_exposure": (
        "hold_load",
        "Session complete. Hold load for the next exposure unless performance trends clearly change.",
    ),
    "performance_below_target_adjust_load_and_recover": (
        "reduce_load",
        "Session performance stayed below target. Adjust load down and recover before the next exposure.",
    ),
    "performance_above_target_progress_load": (
        "increase_load",
        "Session performance was above target. Progress load next exposure.",
    ),
}

_IN_SESSION_WEIGHT_SCALE_UP = 1.025
_IN_SESSION_WEIGHT_SCALE_DOWN_MILD = 0.975
_IN_SESSION_WEIGHT_SCALE_DOWN_AGGRESSIVE = 0.95
_IN_SESSION_WEIGHT_SCALE_MIN = 0.9
_IN_SESSION_WEIGHT_SCALE_MAX = 1.05

_REVIEW_SET_DELTA_MIN = -1
_REVIEW_SET_DELTA_MAX = 1
_REVIEW_ADDITIONAL_SET_CAP = 2
_REVIEW_INTENSITY_MIN_SCALE = 0.93
_REVIEW_INTENSITY_MAX_SCALE = 1.03
_WEAK_POINT_MAX_BOOSTED_EXERCISES = 2
_WEAK_POINT_SET_DELTA_CAP = 1
_WEAK_POINT_TOTAL_SET_BUDGET = 2
_WEAK_POINT_MIN_COMPLETION_FOR_BOOST = 90
_WEAK_POINT_MIN_READINESS_FOR_BOOST = 65
_WEAK_POINT_INTENSITY_MIN_SCALE = 0.93
_WEAK_POINT_INTENSITY_MAX_SCALE = 1.03


_SORENESS_LEVEL = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3,
}


def _normalized_soreness_level(value: str | None) -> int:
    key = (value or "none").strip().lower()
    return _SORENESS_LEVEL.get(key, 0)


def _clamp_days(value: int) -> int:
    return max(2, min(7, int(value)))


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _clamp_scale(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


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


def _joined_clauses(clauses: list[str]) -> str:
    if not clauses:
        return "training stress and recovery signals are not aligned"
    if len(clauses) == 1:
        return clauses[0]
    if len(clauses) == 2:
        return f"{clauses[0]} and {clauses[1]}"
    return ", ".join(clauses[:-1]) + f", and {clauses[-1]}"


def _rule_dict(rule_set: dict[str, Any] | None, key: str) -> dict[str, Any]:
    if not isinstance(rule_set, dict):
        return {}
    value = rule_set.get(key)
    return value if isinstance(value, dict) else {}


def _rule_rationale(rule_set: dict[str, Any] | None, key: str, fallback: str) -> str:
    templates = _rule_dict(rule_set, "rationale_templates")
    value = templates.get(key)
    return value if isinstance(value, str) and value.strip() else fallback


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_training_state(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_attr(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


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


def _deload_response(config: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "action": "deload",
        "load_scale": config["deload_load_scale"],
        "set_delta": config["deload_set_delta"],
        "reason": reason,
    }


def _hold_response(reason: str) -> dict[str, Any]:
    return {
        "action": "hold",
        "load_scale": 1.0,
        "set_delta": 0,
        "reason": reason,
    }


def _progress_response(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": "progress",
        "load_scale": config["progress_load_scale"],
        "set_delta": 0,
        "reason": config["progress_reason"],
    }


def _accumulation_phase_transition(
    *,
    weeks_in_phase: int,
    readiness_score: int,
    progression_action: ProgressionAction,
    stagnation_weeks: int,
    intro_weeks: int,
) -> dict[str, Any]:
    if intro_weeks and weeks_in_phase <= intro_weeks and stagnation_weeks >= 1:
        return {"next_phase": "accumulation", "reason": "intro_phase_protection"}
    if stagnation_weeks >= 2 or readiness_score < 55:
        return {"next_phase": "deload", "reason": "accumulation_stall"}
    if weeks_in_phase >= 6 and progression_action == "progress" and readiness_score >= 65:
        return {"next_phase": "intensification", "reason": "accumulation_complete"}
    return {"next_phase": "accumulation", "reason": "continue_accumulation"}


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


def _weekly_review_adjustment_rationale(rationale: str) -> str:
    return _WEEKLY_REVIEW_ADJUSTMENT_MESSAGES.get(rationale, _humanize_reason_code(rationale))


def _weekly_review_global_guidance_rationale(guidance: str) -> str:
    return _WEEKLY_REVIEW_GUIDANCE_MESSAGES.get(guidance, _humanize_reason_code(guidance))


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


def _resolve_weekly_review_exercise_override(
    row: dict[str, Any],
    *,
    readiness_score: int,
    allow_weak_point_boost: bool,
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

    if "above_target_reps" in fault_reasons and readiness_score >= 70:
        weight_scale *= 1.025
        rationale = "above_target_reps_progress_load"

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


def _resolve_weekly_review_global_guidance(readiness_score: int, faulty_exercise_count: int) -> str:
    if readiness_score < 55:
        return "recovery_limited_reduce_load_and_complete_quality_volume"
    if faulty_exercise_count > 0:
        return "target_fault_exercises_with_controlled_progression"
    return "progressive_overload_ready"


def _round_to_increment(weight: float, increment: float = 2.5) -> float:
    return round(max(5.0, weight) / increment) * increment


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


def interpret_weekly_review_decision(
    *,
    summary: dict[str, Any],
    body_weight: float,
    calories: int,
    protein: int,
    adherence_score: int,
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
        )
        override = _resolve_weekly_review_exercise_override(
            row,
            readiness_score=readiness_score,
            allow_weak_point_boost=allow_weak_point_boost,
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
    global_guidance = _resolve_weekly_review_global_guidance(readiness_score, int(summary.get("faulty_exercise_count", 0) or 0))
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
    plan: dict[str, Any],
    review_adjustments: dict[str, Any],
    review_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    adjustments = review_adjustments if isinstance(review_adjustments, dict) else {}
    global_set_delta, global_weight_scale, exercise_overrides, weak_points = _resolve_weekly_review_plan_adjustments(
        adjustments
    )

    for session in plan.get("sessions") or []:
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
        decision_trace=_coerce_dict(adjustments.get("decision_trace")) or None,
    )
    return plan


def _humanize_workout_guidance(guidance: str) -> str:
    phrase = guidance.replace("_", " ").strip()
    if not phrase:
        return "Follow the planned progression."
    return phrase[:1].upper() + phrase[1:] + "."


def _under_target_after_exposures(rule_set: dict[str, Any] | None) -> int:
    progression_rules = _rule_dict(rule_set, "progression_rules")
    on_under_target = _coerce_dict(progression_rules.get("on_under_target"))
    value = on_under_target.get("after_exposures")
    return int(value) if isinstance(value, int) and value > 0 else 1


def _workout_guidance_rationale(guidance: str, *, rule_set: dict[str, Any] | None = None) -> str:
    static_message = _WORKOUT_GUIDANCE_STATIC_MESSAGES.get(guidance)
    if static_message is not None:
        return static_message

    template_message = _WORKOUT_GUIDANCE_TEMPLATE_MESSAGES.get(guidance)
    if template_message is not None:
        template_key, fallback = template_message
        return _rule_rationale(rule_set, template_key, fallback)

    under_target_after = _under_target_after_exposures(rule_set)
    if guidance == "below_target_reps_reduce_or_hold_load":
        if under_target_after > 1:
            return (
                "Performance fell below the target range. Hold load on the first miss and "
                f"only reduce if it repeats across {under_target_after} exposures."
            )
        return _rule_rationale(
            rule_set,
            "reduce_load",
            "Performance fell below target. Reduce load next exposure to restore rep quality.",
        )

    if guidance == "remaining_sets_reduce_load_focus_target_reps":
        if under_target_after > 1:
            return "Reps dropped below target. Trim load slightly within the session so the remaining sets stay on target."
        return _rule_rationale(
            rule_set,
            "reduce_load",
            "Reps dropped below target. Reduce load slightly and bring the remaining sets back into range.",
        )

    return _humanize_workout_guidance(guidance)


def _resolve_workout_set_guidance(reps: int, min_reps: int, max_reps: int) -> str:
    if reps < min_reps:
        return "below_target_reps_reduce_or_hold_load"
    if reps > max_reps:
        return "above_target_reps_increase_load_next_exposure"
    return "within_target_reps_hold_or_microload"


def _round_to_microload(weight: float) -> float:
    return round(max(5.0, weight) / 2.5) * 2.5


def _bounded_in_session_weight_scale(scale: float) -> float:
    return max(_IN_SESSION_WEIGHT_SCALE_MIN, min(_IN_SESSION_WEIGHT_SCALE_MAX, scale))


def _resolve_workout_summary_guidance(
    performed_sets: int,
    planned_sets: int,
    avg_reps: float,
    planned_min: int,
    planned_max: int,
) -> str:
    if performed_sets < planned_sets:
        return "incomplete_session_finish_remaining_sets_next_exposure"
    if avg_reps < planned_min:
        return "below_target_reps_reduce_or_hold_load"
    if avg_reps > planned_max:
        return "above_target_reps_increase_load_next_exposure"
    return "within_target_reps_hold_or_microload"


def _resolve_workout_overall_guidance(percent_complete: int, exercise_summaries: list[dict[str, Any]]) -> str:
    if percent_complete < 100:
        return "finish_all_planned_sets_for_reliable_progression"
    if any(str(item.get("guidance") or "") == "below_target_reps_reduce_or_hold_load" for item in exercise_summaries):
        return "performance_below_target_adjust_load_and_recover"
    if any(str(item.get("guidance") or "") == "above_target_reps_increase_load_next_exposure" for item in exercise_summaries):
        return "performance_above_target_progress_load"
    return "solid_execution_maintain_progression"


def hydrate_live_workout_recommendation(
    *,
    completed_sets: int,
    remaining_sets: int,
    recommended_reps_min: int,
    recommended_reps_max: int,
    recommended_weight: float,
    guidance: str,
    substitution_recommendation: dict[str, Any] | None = None,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    guidance_rationale = _workout_guidance_rationale(guidance, rule_set=rule_set)
    decision_trace = {
        "interpreter": "hydrate_live_workout_recommendation",
        "version": "v1",
        "inputs": {
            "completed_sets": completed_sets,
            "remaining_sets": remaining_sets,
            "recommended_reps_min": recommended_reps_min,
            "recommended_reps_max": recommended_reps_max,
            "recommended_weight": recommended_weight,
            "guidance": guidance,
        },
        "steps": [],
        "outcome": {
            "guidance": guidance,
            "guidance_rationale": guidance_rationale,
            "substitution_recommendation": deepcopy(substitution_recommendation),
        },
    }
    payload = {
        "completed_sets": completed_sets,
        "remaining_sets": remaining_sets,
        "recommended_reps_min": recommended_reps_min,
        "recommended_reps_max": recommended_reps_max,
        "recommended_weight": recommended_weight,
        "guidance": guidance,
        "guidance_rationale": guidance_rationale,
        "decision_trace": decision_trace,
    }
    if substitution_recommendation is not None:
        payload["substitution_recommendation"] = deepcopy(substitution_recommendation)
    return payload


def resolve_workout_session_state_update(
    *,
    existing_set_history: list[dict[str, Any]] | None,
    primary_exercise_id: str,
    planned_sets: int,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
    set_index: int,
    reps: int,
    weight: float,
    substitution_recommendation: dict[str, Any] | None = None,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    history = [_coerce_dict(item) for item in (existing_set_history or [])]
    next_entry = {
        "set_index": set_index,
        "reps": reps,
        "weight": float(weight),
    }

    replaced = False
    for idx, item in enumerate(history):
        if int(item.get("set_index", -1)) == set_index:
            history[idx] = next_entry
            replaced = True
            break
    if not replaced:
        history.append(next_entry)

    history.sort(key=lambda row: int(row.get("set_index", 0)))

    completed_sets = min(planned_sets, len(history))
    total_reps = sum(int(item.get("reps", 0) or 0) for item in history)
    total_weight = sum(float(item.get("weight", 0) or 0) for item in history)
    average_reps = (total_reps / len(history)) if history else float(reps)

    live_recommendation = recommend_live_workout_adjustment(
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_sets=planned_sets,
        completed_sets=completed_sets,
        last_reps=reps,
        last_weight=weight,
        average_reps=average_reps,
        substitution_recommendation=substitution_recommendation,
        rule_set=rule_set,
    )

    return {
        "state": {
            "primary_exercise_id": primary_exercise_id,
            "planned_sets": planned_sets,
            "planned_reps_min": planned_reps_min,
            "planned_reps_max": planned_reps_max,
            "planned_weight": planned_weight,
            "completed_sets": int(live_recommendation["completed_sets"]),
            "total_logged_reps": total_reps,
            "total_logged_weight": round(total_weight, 2),
            "set_history": history,
            "remaining_sets": int(live_recommendation["remaining_sets"]),
            "recommended_reps_min": int(live_recommendation["recommended_reps_min"]),
            "recommended_reps_max": int(live_recommendation["recommended_reps_max"]),
            "recommended_weight": float(live_recommendation["recommended_weight"]),
            "last_guidance": str(live_recommendation["guidance"]),
        },
        "live_recommendation": live_recommendation,
    }


def recommend_live_workout_adjustment(
    *,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_sets: int,
    completed_sets: int,
    last_reps: int,
    last_weight: float,
    average_reps: float,
    substitution_recommendation: dict[str, Any] | None = None,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    remaining_sets = max(planned_sets - completed_sets, 0)
    recommended_reps_min = planned_reps_min
    recommended_reps_max = planned_reps_max
    guidance = "remaining_sets_hold_load_and_match_target_reps"
    scale = 1.0
    matched_rule = "hold_remaining_sets"

    if remaining_sets <= 0:
        guidance = "session_complete_hold_load_for_next_exposure"
        matched_rule = "session_complete"
    elif last_reps < planned_reps_min or average_reps < planned_reps_min:
        guidance = "remaining_sets_reduce_load_focus_target_reps"
        scale = _IN_SESSION_WEIGHT_SCALE_DOWN_AGGRESSIVE if completed_sets >= 2 else _IN_SESSION_WEIGHT_SCALE_DOWN_MILD
        recommended_reps_max = min(planned_reps_max, planned_reps_min + 2)
        matched_rule = "under_target_reps"
    elif last_reps > planned_reps_max + 1 and average_reps >= planned_reps_max:
        guidance = "remaining_sets_increase_load_keep_reps_controlled"
        scale = _IN_SESSION_WEIGHT_SCALE_UP
        recommended_reps_min = max(planned_reps_min, planned_reps_max - 2)
        matched_rule = "above_target_reps"

    recommended_weight = _round_to_microload(last_weight * _bounded_in_session_weight_scale(scale))
    guidance_rationale = _workout_guidance_rationale(guidance, rule_set=rule_set)
    decision_trace = {
        "interpreter": "recommend_live_workout_adjustment",
        "version": "v1",
        "inputs": {
            "planned_reps_min": planned_reps_min,
            "planned_reps_max": planned_reps_max,
            "planned_sets": planned_sets,
            "completed_sets": completed_sets,
            "remaining_sets": remaining_sets,
            "last_reps": last_reps,
            "last_weight": last_weight,
            "average_reps": round(average_reps, 2),
        },
        "steps": [
            {
                "decision": "in_session_adjustment_rule",
                "result": {
                    "matched_rule": matched_rule,
                    "guidance": guidance,
                    "weight_scale": round(scale, 3),
                },
            }
        ],
        "outcome": {
            "recommended_reps_min": recommended_reps_min,
            "recommended_reps_max": max(recommended_reps_min, recommended_reps_max),
            "recommended_weight": recommended_weight,
            "guidance": guidance,
            "guidance_rationale": guidance_rationale,
            "substitution_recommendation": deepcopy(substitution_recommendation),
        },
    }
    payload = {
        "completed_sets": completed_sets,
        "remaining_sets": remaining_sets,
        "recommended_reps_min": recommended_reps_min,
        "recommended_reps_max": max(recommended_reps_min, recommended_reps_max),
        "recommended_weight": recommended_weight,
        "guidance": guidance,
        "guidance_rationale": guidance_rationale,
        "decision_trace": decision_trace,
    }
    if substitution_recommendation is not None:
        payload["substitution_recommendation"] = deepcopy(substitution_recommendation)
    return payload


def interpret_workout_set_feedback(
    *,
    reps: int,
    weight: float,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
    next_working_weight: float,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    guidance = _resolve_workout_set_guidance(reps, planned_reps_min, planned_reps_max)
    rep_delta = 0
    if reps > planned_reps_max:
        rep_delta = reps - planned_reps_max
    elif reps < planned_reps_min:
        rep_delta = reps - planned_reps_min
    weight_delta = round(weight - planned_weight, 2)
    guidance_rationale = _workout_guidance_rationale(guidance, rule_set=rule_set)
    decision_trace = {
        "interpreter": "interpret_workout_set_feedback",
        "version": "v1",
        "inputs": {
            "reps": reps,
            "weight": weight,
            "planned_reps_min": planned_reps_min,
            "planned_reps_max": planned_reps_max,
            "planned_weight": planned_weight,
        },
        "steps": [
            {
                "decision": "set_feedback_guidance",
                "result": {
                    "guidance": guidance,
                    "rep_delta": rep_delta,
                    "weight_delta": weight_delta,
                },
            }
        ],
        "outcome": {
            "guidance": guidance,
            "guidance_rationale": guidance_rationale,
            "next_working_weight": next_working_weight,
        },
    }
    return {
        "rep_delta": rep_delta,
        "weight_delta": weight_delta,
        "next_working_weight": next_working_weight,
        "guidance": guidance,
        "guidance_rationale": guidance_rationale,
        "decision_trace": decision_trace,
    }


def build_workout_progress_payload(
    *,
    workout_id: str,
    completed_sets_by_exercise: dict[str, int],
    planned_session: dict[str, Any] | None,
) -> dict[str, Any]:
    session = _coerce_dict(planned_session)
    planned_total = 0
    exercises: list[dict[str, Any]] = []

    for exercise in session.get("exercises") or []:
        exercise_id = str(exercise.get("id") or "")
        if not exercise_id:
            continue
        planned_sets = int(exercise.get("sets", 3) or 3)
        planned_total += planned_sets
        exercises.append(
            {
                "exercise_id": exercise_id,
                "planned_sets": planned_sets,
                "completed_sets": int(completed_sets_by_exercise.get(exercise_id, 0) or 0),
            }
        )

    completed_total = sum(int(value or 0) for value in completed_sets_by_exercise.values())
    percent_complete = int((completed_total / planned_total) * 100) if planned_total > 0 else 0

    return {
        "workout_id": workout_id,
        "completed_total": completed_total,
        "planned_total": planned_total,
        "percent_complete": percent_complete,
        "exercises": exercises,
    }


def build_workout_log_set_payload(
    *,
    record_id: str,
    primary_exercise_id: str,
    exercise_id: str,
    set_index: int,
    reps: int,
    weight: float,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
    feedback: dict[str, Any],
    starting_load_decision_trace: dict[str, Any] | None,
    live_recommendation: dict[str, Any],
    created_at: Any,
) -> dict[str, Any]:
    return {
        "id": record_id,
        "primary_exercise_id": primary_exercise_id,
        "exercise_id": exercise_id,
        "set_index": int(set_index),
        "reps": int(reps),
        "weight": float(weight),
        "planned_reps_min": int(planned_reps_min),
        "planned_reps_max": int(planned_reps_max),
        "planned_weight": float(planned_weight),
        "rep_delta": int(feedback["rep_delta"]),
        "weight_delta": float(feedback["weight_delta"]),
        "next_working_weight": float(feedback["next_working_weight"]),
        "guidance": str(feedback["guidance"]),
        "guidance_rationale": str(feedback["guidance_rationale"]),
        "decision_trace": deepcopy(dict(feedback["decision_trace"])),
        "starting_load_decision_trace": deepcopy(starting_load_decision_trace),
        "live_recommendation": deepcopy(live_recommendation),
        "created_at": created_at,
    }


def _normalized_equipment_profile(equipment_profile: list[str] | None) -> set[str]:
    return {
        str(item).strip().lower()
        for item in (equipment_profile or [])
        if str(item).strip()
    }


def build_repeat_failure_substitution_payload(
    *,
    planned_exercise: dict[str, Any] | None,
    exercise_state: Any,
    equipment_profile: list[str] | None,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any] | None:
    exercise = _coerce_dict(planned_exercise)
    if exercise_state is None:
        return None

    substitutions = exercise.get("substitution_candidates") or exercise.get("substitutions") or []
    if not isinstance(substitutions, list) or not substitutions:
        return None

    runtime = resolve_repeat_failure_substitution(
        exercise_id=str(exercise.get("primary_exercise_id") or exercise.get("id") or _read_attr(exercise_state, "exercise_id") or ""),
        exercise_name=str(exercise.get("name") or _read_attr(exercise_state, "exercise_id") or ""),
        substitution_candidates=[str(candidate) for candidate in substitutions if str(candidate).strip()],
        consecutive_under_target_exposures=int(_read_attr(exercise_state, "consecutive_under_target_exposures") or 0),
        equipment_set=_normalized_equipment_profile(equipment_profile),
        rule_set=rule_set,
    )
    if not runtime["recommend_substitution"]:
        return None

    threshold = runtime["repeat_failure_threshold"]
    if threshold is None:
        return None

    return {
        "recommended_name": str(runtime["recommended_name"]),
        "compatible_substitutions": list(runtime["compatible_substitutions"]),
        "failed_exposure_count": int(_read_attr(exercise_state, "consecutive_under_target_exposures") or 0),
        "trigger_threshold": int(threshold),
        "reason": "repeat_failure_threshold_reached",
        "decision_trace": dict(runtime["decision_trace"]),
    }


def prepare_workout_log_set_request_runtime(
    *,
    primary_exercise_id: str | None,
    exercise_id: str,
    set_index: int,
    reps: int,
    weight: float,
    rpe: float | None,
) -> dict[str, Any]:
    resolved_primary_exercise_id = primary_exercise_id or exercise_id
    return {
        "primary_exercise_id": resolved_primary_exercise_id,
        "exercise_id": exercise_id,
        "set_index": set_index,
        "reps": reps,
        "weight": weight,
        "rpe": rpe,
    }


def resolve_workout_log_set_plan_context(
    *,
    planned_exercise: dict[str, Any] | None,
    fallback_weight: float,
) -> dict[str, Any]:
    exercise = _coerce_dict(planned_exercise)
    planned_reps_min, planned_reps_max = _resolve_rep_range(exercise.get("rep_range"))
    planned_sets = int(exercise.get("sets", 3) or 3)
    planned_weight = float(exercise.get("recommended_working_weight", fallback_weight) or fallback_weight)
    return {
        "planned_reps_min": planned_reps_min,
        "planned_reps_max": planned_reps_max,
        "planned_sets": planned_sets,
        "planned_weight": planned_weight,
    }


def build_workout_session_state_defaults(
    *,
    primary_exercise_id: str,
    planned_sets: int,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
) -> dict[str, Any]:
    return {
        "primary_exercise_id": primary_exercise_id,
        "planned_sets": planned_sets,
        "planned_reps_min": planned_reps_min,
        "planned_reps_max": planned_reps_max,
        "planned_weight": planned_weight,
        "completed_sets": 0,
        "total_logged_reps": 0,
        "total_logged_weight": 0.0,
        "set_history": [],
        "remaining_sets": planned_sets,
        "recommended_reps_min": planned_reps_min,
        "recommended_reps_max": planned_reps_max,
        "recommended_weight": planned_weight,
        "last_guidance": "remaining_sets_hold_load_and_match_target_reps",
    }


def prepare_workout_session_state_persistence_payload(
    *,
    existing_state: Any | None,
    primary_exercise_id: str,
    planned_sets: int,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
    set_index: int,
    reps: int,
    weight: float,
    substitution_recommendation: dict[str, Any] | None,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    reduction = resolve_workout_session_state_update(
        existing_set_history=list(_read_attr(existing_state, "set_history") or []),
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
    return {
        "state": deepcopy(_coerce_dict(reduction.get("state"))),
        "live_recommendation": deepcopy(_coerce_dict(reduction.get("live_recommendation"))),
    }


def build_workout_today_plan_runtime(
    *,
    latest_plan_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = _coerce_dict(latest_plan_payload)
    sessions = [
        _coerce_dict(session)
        for session in (payload.get("sessions") or [])
        if isinstance(session, dict)
    ]
    session_ids = [
        str(session.get("session_id") or "")
        for session in sessions
        if str(session.get("session_id") or "")
    ]
    selected_program_id = str(payload.get("program_template_id") or "").strip() or None
    mesocycle = _coerce_dict(payload.get("mesocycle")) if isinstance(payload.get("mesocycle"), dict) else None
    deload = _coerce_dict(payload.get("deload")) if isinstance(payload.get("deload"), dict) else None

    return {
        "sessions": sessions,
        "session_ids": session_ids,
        "selected_program_id": selected_program_id,
        "mesocycle": mesocycle,
        "deload": deload,
        "decision_trace": {
            "interpreter": "build_workout_today_plan_runtime",
            "version": "v1",
            "inputs": {"has_latest_plan_payload": bool(payload)},
            "outcome": {
                "session_count": len(sessions),
                "session_id_count": len(session_ids),
                "selected_program_id": selected_program_id,
                "has_mesocycle": mesocycle is not None,
                "has_deload": deload is not None,
            },
        },
    }


def resolve_workout_today_plan_payload(
    *,
    plan_rows: list[Any],
) -> dict[str, Any]:
    latest_row = plan_rows[0] if plan_rows else None
    latest_plan_payload = _coerce_dict(_read_attr(latest_row, "payload", {}))
    has_plan = latest_row is not None
    return {
        "has_plan": has_plan,
        "latest_plan_payload": latest_plan_payload,
        "decision_trace": {
            "interpreter": "resolve_workout_today_plan_payload",
            "version": "v1",
            "inputs": {
                "plan_row_count": len(plan_rows),
            },
            "outcome": {
                "has_plan": has_plan,
                "has_latest_payload_dict": bool(latest_plan_payload),
            },
        },
    }


def build_workout_today_log_runtime(
    *,
    recent_logs: list[Any],
    selected_session_logs: list[Any],
) -> dict[str, Any]:
    resume_logs = [
        {"workout_id": str(_read_attr(row, "workout_id") or "")}
        for row in recent_logs
        if str(_read_attr(row, "workout_id") or "")
    ]
    completion_logs = [
        {
            "exercise_id": str(_read_attr(row, "exercise_id") or ""),
            "set_index": int(_read_attr(row, "set_index") or 0),
        }
        for row in selected_session_logs
        if str(_read_attr(row, "exercise_id") or "")
    ]
    return {
        "resume_logs": resume_logs,
        "completion_logs": completion_logs,
        "decision_trace": {
            "interpreter": "build_workout_today_log_runtime",
            "version": "v1",
            "inputs": {
                "recent_log_count": len(recent_logs),
                "selected_session_log_count": len(selected_session_logs),
            },
            "outcome": {
                "resume_log_count": len(resume_logs),
                "completion_log_count": len(completion_logs),
            },
        },
    }


def build_workout_summary_progression_lookup_runtime(
    *,
    planned_session: dict[str, Any] | None,
) -> dict[str, Any]:
    session = _coerce_dict(planned_session)
    primary_exercise_ids: list[str] = []
    seen: set[str] = set()
    for exercise in session.get("exercises") or []:
        if not isinstance(exercise, dict):
            continue
        normalized = str(exercise.get("primary_exercise_id") or exercise.get("id") or "")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        primary_exercise_ids.append(normalized)

    return {
        "primary_exercise_ids": primary_exercise_ids,
        "decision_trace": {
            "interpreter": "build_workout_summary_progression_lookup_runtime",
            "version": "v1",
            "inputs": {
                "planned_exercise_count": len(
                    [exercise for exercise in session.get("exercises") or [] if isinstance(exercise, dict)]
                ),
            },
            "outcome": {
                "primary_exercise_id_count": len(primary_exercise_ids),
            },
        },
    }


def build_workout_today_progression_lookup_runtime(
    *,
    session_states: list[Any],
) -> dict[str, Any]:
    primary_exercise_ids: list[str] = []
    seen: set[str] = set()
    for row in session_states:
        normalized = str(_read_attr(row, "primary_exercise_id") or "")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        primary_exercise_ids.append(normalized)

    return {
        "primary_exercise_ids": primary_exercise_ids,
        "decision_trace": {
            "interpreter": "build_workout_today_progression_lookup_runtime",
            "version": "v1",
            "inputs": {
                "session_state_count": len(session_states),
            },
            "outcome": {
                "primary_exercise_id_count": len(primary_exercise_ids),
            },
        },
    }


def build_workout_today_session_state_payloads(
    *,
    session_states: list[Any],
    planned_session: dict[str, Any],
    progression_states: list[Any],
    equipment_profile: list[str] | None,
    rule_set: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    planned_exercise_by_id = {
        str(_coerce_dict(exercise).get("id") or ""): _coerce_dict(exercise)
        for exercise in planned_session.get("exercises") or []
        if str(_coerce_dict(exercise).get("id") or "")
    }
    progression_state_by_exercise = {
        str(_read_attr(row, "exercise_id") or ""): row
        for row in progression_states
        if str(_read_attr(row, "exercise_id") or "")
    }

    payloads: list[dict[str, Any]] = []
    for row in session_states:
        exercise_id = str(_read_attr(row, "exercise_id") or "")
        primary_exercise_id = str(_read_attr(row, "primary_exercise_id") or "")
        substitution_recommendation = build_repeat_failure_substitution_payload(
            planned_exercise=planned_exercise_by_id.get(exercise_id),
            exercise_state=progression_state_by_exercise.get(primary_exercise_id),
            equipment_profile=equipment_profile,
            rule_set=rule_set,
        )
        payloads.append(
            {
                "exercise_id": exercise_id,
                "completed_sets": int(_read_attr(row, "completed_sets") or 0),
                "remaining_sets": int(_read_attr(row, "remaining_sets") or 0),
                "recommended_reps_min": int(_read_attr(row, "recommended_reps_min") or 0),
                "recommended_reps_max": int(_read_attr(row, "recommended_reps_max") or 0),
                "recommended_weight": float(_read_attr(row, "recommended_weight") or 0),
                "last_guidance": str(_read_attr(row, "last_guidance") or ""),
                "substitution_recommendation": substitution_recommendation,
            }
        )

    return payloads


def resolve_latest_logged_workout_resume_state(
    *,
    sessions: list[dict[str, Any]],
    performed_logs: list[dict[str, Any]],
) -> dict[str, Any]:
    session_by_id = {
        str(session.get("session_id") or ""): session
        for session in sessions
        if str(session.get("session_id") or "")
    }
    if not session_by_id or not performed_logs:
        return {
            "latest_logged_workout_id": None,
            "latest_logged_session_incomplete": False,
        }

    latest_logged_workout_id = str(performed_logs[0].get("workout_id") or "")
    latest_logged_session = session_by_id.get(latest_logged_workout_id)
    if latest_logged_session is None:
        return {
            "latest_logged_workout_id": latest_logged_workout_id or None,
            "latest_logged_session_incomplete": False,
        }

    planned_sets = sum(int(exercise.get("sets", 3) or 3) for exercise in latest_logged_session.get("exercises", []))
    logged_sets = sum(
        1 for row in performed_logs if str(row.get("workout_id") or "") == latest_logged_workout_id
    )
    return {
        "latest_logged_workout_id": latest_logged_workout_id,
        "latest_logged_session_incomplete": logged_sets < planned_sets,
    }


def resolve_workout_today_session_selection(
    *,
    sessions: list[dict[str, Any]],
    latest_logged_workout_id: str | None,
    latest_logged_session_incomplete: bool,
    today_iso: str,
) -> dict[str, Any]:
    session_by_id = {
        str(session.get("session_id") or ""): session
        for session in sessions
        if str(session.get("session_id") or "")
    }

    if latest_logged_workout_id:
        candidate = session_by_id.get(str(latest_logged_workout_id))
        if candidate is not None and latest_logged_session_incomplete:
            return {
                "selected_session": candidate,
                "resume_selected": True,
                "selection_reason": "resume_incomplete_session",
            }

    today_match = next((session for session in sessions if str(session.get("date") or "") == today_iso), None)
    if today_match is not None:
        return {
            "selected_session": today_match,
            "resume_selected": False,
            "selection_reason": "today_match",
        }

    first_session = sessions[0] if sessions else None
    return {
        "selected_session": first_session,
        "resume_selected": False,
        "selection_reason": "first_session_fallback" if first_session is not None else "no_sessions",
    }


def resolve_workout_plan_reference(
    *,
    plan_payloads: list[dict[str, Any]],
    workout_id: str,
    exercise_id: str | None = None,
) -> dict[str, Any]:
    for payload in plan_payloads:
        normalized_payload = _coerce_dict(payload)
        sessions = normalized_payload.get("sessions") or []
        session = next(
            (item for item in sessions if str(_coerce_dict(item).get("session_id") or "") == workout_id),
            None,
        )
        if session is None:
            continue

        normalized_session = _coerce_dict(session)
        program_id = str(normalized_payload.get("program_template_id") or "").strip() or None
        if not exercise_id:
            return {
                "session": normalized_session,
                "exercise": None,
                "program_id": program_id,
            }

        exercises = normalized_session.get("exercises") or []
        exercise = next(
            (item for item in exercises if str(_coerce_dict(item).get("id") or "") == exercise_id),
            None,
        )
        return {
            "session": normalized_session,
            "exercise": _coerce_dict(exercise) if exercise is not None else None,
            "program_id": program_id,
        }

    return {
        "session": None,
        "exercise": None,
        "program_id": None,
    }


def resolve_workout_plan_context(
    *,
    plan_rows: list[Any],
    workout_id: str,
    exercise_id: str | None = None,
) -> dict[str, Any]:
    plan_payloads = [
        _coerce_dict(_read_attr(row, "payload", {}))
        for row in plan_rows
    ]
    reference = resolve_workout_plan_reference(
        plan_payloads=plan_payloads,
        workout_id=workout_id,
        exercise_id=exercise_id,
    )
    session = _coerce_dict(reference.get("session"))
    exercise = _coerce_dict(reference.get("exercise"))
    program_id = str(reference.get("program_id") or "").strip() or None
    return {
        "session": session or None,
        "exercise": exercise or None,
        "program_id": program_id,
        "decision_trace": {
            "interpreter": "resolve_workout_plan_context",
            "version": "v1",
            "inputs": {
                "plan_row_count": len(plan_rows),
                "workout_id": workout_id,
                "has_exercise_id": bool(exercise_id),
            },
            "outcome": {
                "matched_session": bool(session),
                "matched_exercise": bool(exercise),
                "program_id": program_id,
            },
        },
    }


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


def build_weekly_review_decision_payload(
    *,
    summary: dict[str, Any],
    body_weight: float,
    calories: int,
    protein: int,
    adherence_score: int,
) -> dict[str, Any]:
    decision = interpret_weekly_review_decision(
        summary=summary,
        body_weight=body_weight,
        calories=calories,
        protein=protein,
        adherence_score=adherence_score,
    )
    return {
        "readiness_score": int(decision.get("readiness_score") or 0),
        "global_guidance": str(decision.get("global_guidance") or ""),
        "adjustments": deepcopy(_coerce_dict(decision.get("adjustments"))),
        "storage_adjustments": deepcopy(_coerce_dict(decision.get("storage_adjustments"))),
        "decision_trace": deepcopy(_coerce_dict(decision.get("decision_trace"))),
    }


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


def build_soreness_entry_persistence_payload(
    *,
    entry_date: date,
    severity_by_muscle: dict[str, str],
    notes: str | None,
) -> dict[str, Any]:
    return {
        "entry_date": entry_date,
        "severity_by_muscle": deepcopy(dict(severity_by_muscle)),
        "notes": notes,
    }


def build_body_measurement_create_payload(
    *,
    measured_on: date,
    name: str,
    value: float,
    unit: str,
) -> dict[str, Any]:
    return {
        "measured_on": measured_on,
        "name": name,
        "value": value,
        "unit": unit,
    }


def build_body_measurement_update_payload(
    *,
    measured_on: date | None,
    name: str | None,
    value: float | None,
    unit: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if measured_on is not None:
        payload["measured_on"] = measured_on
    if name is not None:
        payload["name"] = name
    if value is not None:
        payload["value"] = value
    if unit is not None:
        payload["unit"] = unit
    return payload


def prepare_profile_date_window_runtime(
    *,
    start_date: date | None,
    end_date: date | None,
) -> dict[str, Any]:
    return {
        "start_date": start_date,
        "end_date": end_date,
        "decision_trace": {
            "interpreter": "prepare_profile_date_window_runtime",
            "version": "v1",
            "inputs": {
                "has_start_date": start_date is not None,
                "has_end_date": end_date is not None,
            },
        },
    }


def build_profile_upsert_persistence_payload(
    *,
    name: str,
    age: int,
    weight: float,
    gender: str,
    split_preference: str,
    selected_program_id: str | None,
    training_location: str,
    equipment_profile: list[str],
    weak_areas: list[str] | None,
    onboarding_answers: dict[str, Any] | None,
    days_available: int,
    nutrition_phase: str,
    calories: int,
    protein: int,
    fat: int,
    carbs: int,
) -> dict[str, Any]:
    return {
        "name": name,
        "age": age,
        "weight": weight,
        "gender": gender,
        "split_preference": split_preference,
        "selected_program_id": selected_program_id or "full_body_v1",
        "training_location": training_location,
        "equipment_profile": list(equipment_profile),
        "weak_areas": list(weak_areas or []),
        "onboarding_answers": deepcopy(onboarding_answers) if isinstance(onboarding_answers, dict) else None,
        "days_available": days_available,
        "nutrition_phase": nutrition_phase,
        "calories": calories,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
    }


def build_profile_response_payload(
    *,
    email: str,
    name: str | None,
    age: int | None,
    weight: float | None,
    gender: str | None,
    split_preference: str | None,
    selected_program_id: str | None,
    training_location: str | None,
    equipment_profile: list[str] | None,
    weak_areas: list[str] | None,
    onboarding_answers: dict[str, Any] | None,
    days_available: int | None,
    nutrition_phase: str | None,
    calories: int | None,
    protein: int | None,
    fat: int | None,
    carbs: int | None,
) -> dict[str, Any]:
    return {
        "email": email,
        "name": name,
        "age": age or 0,
        "weight": weight or 0,
        "gender": gender or "",
        "split_preference": split_preference or "",
        "selected_program_id": selected_program_id or "full_body_v1",
        "training_location": training_location,
        "equipment_profile": list(equipment_profile or []),
        "weak_areas": list(weak_areas or []),
        "onboarding_answers": deepcopy(onboarding_answers) if isinstance(onboarding_answers, dict) else {},
        "days_available": days_available or 2,
        "nutrition_phase": nutrition_phase or "maintenance",
        "calories": calories or 0,
        "protein": protein or 0,
        "fat": fat or 0,
        "carbs": carbs or 0,
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


def build_weekly_checkin_persistence_payload(
    *,
    week_start: date,
    body_weight: float,
    adherence_score: int,
    notes: str | None,
) -> dict[str, Any]:
    return {
        "week_start": week_start,
        "body_weight": body_weight,
        "adherence_score": adherence_score,
        "notes": notes,
    }


def build_weekly_checkin_response_payload(
    *,
    nutrition_phase: str | None,
) -> dict[str, str]:
    return {
        "status": "logged",
        "phase": nutrition_phase or "maintenance",
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


def resolve_workout_completion_per_exercise(
    *,
    performed_logs: list[dict[str, Any]],
) -> dict[str, int]:
    completed_by_exercise: dict[str, int] = {}
    for row in performed_logs:
        exercise_id = str(row.get("exercise_id") or "")
        if not exercise_id:
            continue
        set_index = int(row.get("set_index") or 0)
        previous_completed_sets = completed_by_exercise.get(exercise_id, 0)
        if set_index > previous_completed_sets:
            completed_by_exercise[exercise_id] = set_index
    return completed_by_exercise


def group_workout_logs_by_exercise(
    *,
    performed_logs: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in performed_logs:
        exercise_id = str(row.get("exercise_id") or "")
        if not exercise_id:
            continue
        grouped.setdefault(exercise_id, []).append(dict(row))
    for exercise_logs in grouped.values():
        exercise_logs.sort(key=lambda row: int(row.get("set_index") or 0))
    return grouped


def _serialize_workout_summary_log_row(row: Any) -> dict[str, Any]:
    return {
        "exercise_id": _read_attr(row, "exercise_id"),
        "set_index": _read_attr(row, "set_index"),
        "reps": _read_attr(row, "reps"),
        "weight": _read_attr(row, "weight"),
    }


def _progression_weight_by_exercise(progression_states: list[Any]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for row in progression_states:
        exercise_id = str(_read_attr(row, "exercise_id") or "")
        if not exercise_id:
            continue
        weights[exercise_id] = float(_read_attr(row, "current_working_weight") or 0)
    return weights


def _build_workout_summary_exercise_summaries(
    *,
    planned_session: dict[str, Any],
    logs_by_exercise: dict[str, list[dict[str, Any]]],
    next_working_weight_by_exercise: dict[str, float],
    rule_set: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], int, int]:
    exercise_summaries: list[dict[str, Any]] = []
    planned_total = 0
    completed_total = 0

    for raw_exercise in planned_session.get("exercises") or []:
        exercise = _coerce_dict(raw_exercise)
        exercise_id = str(exercise.get("id") or "")
        if not exercise_id:
            continue

        primary_exercise_id = str(exercise.get("primary_exercise_id") or exercise_id)
        next_working_weight = next_working_weight_by_exercise.get(
            primary_exercise_id,
            float(exercise.get("recommended_working_weight", 0) or 0),
        )
        summary = summarize_workout_exercise_performance(
            exercise=exercise,
            performed_logs=[
                {
                    "set_index": row.get("set_index"),
                    "reps": row.get("reps"),
                    "weight": row.get("weight"),
                }
                for row in logs_by_exercise.get(exercise_id, [])
            ],
            next_working_weight=next_working_weight,
            rule_set=rule_set,
        )
        exercise_summaries.append(summary)
        planned_total += int(summary.get("planned_sets") or 0)
        completed_total += int(summary.get("performed_sets") or 0)

    return exercise_summaries, planned_total, completed_total


def build_workout_performance_summary(
    *,
    workout_id: str,
    planned_session: dict[str, Any],
    performed_logs: list[Any],
    progression_states: list[Any],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    logs_by_exercise = group_workout_logs_by_exercise(
        performed_logs=[_serialize_workout_summary_log_row(row) for row in performed_logs]
    )
    next_working_weight_by_exercise = _progression_weight_by_exercise(progression_states)
    exercise_summaries, planned_total, completed_total = _build_workout_summary_exercise_summaries(
        planned_session=planned_session,
        logs_by_exercise=logs_by_exercise,
        next_working_weight_by_exercise=next_working_weight_by_exercise,
        rule_set=rule_set,
    )

    return build_workout_summary_payload(
        workout_id=workout_id,
        completed_total=completed_total,
        planned_total=planned_total,
        exercise_summaries=exercise_summaries,
        rule_set=rule_set,
    )


def build_workout_summary_payload(
    *,
    workout_id: str,
    completed_total: int,
    planned_total: int,
    exercise_summaries: list[dict[str, Any]],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    overall_summary = summarize_workout_session_guidance(
        workout_id=workout_id,
        completed_total=completed_total,
        planned_total=planned_total,
        exercise_summaries=exercise_summaries,
        rule_set=rule_set,
    )
    return {
        "workout_id": workout_id,
        "completed_total": completed_total,
        "planned_total": planned_total,
        "percent_complete": int(overall_summary["percent_complete"]),
        "overall_guidance": str(overall_summary["overall_guidance"]),
        "overall_rationale": str(overall_summary["overall_rationale"]),
        "decision_trace": dict(overall_summary["decision_trace"]),
        "exercises": exercise_summaries,
    }


def build_workout_today_state_payloads(
    *,
    session_states: list[dict[str, Any]],
    completed_sets_by_exercise: dict[str, int],
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    merged_completed_sets = dict(completed_sets_by_exercise)
    live_recommendations_by_exercise: dict[str, dict[str, Any]] = {}

    for state in session_states:
        exercise_id = str(state.get("exercise_id") or "")
        if not exercise_id:
            continue
        merged_completed_sets[exercise_id] = int(state.get("completed_sets") or 0)
        live_recommendations_by_exercise[exercise_id] = hydrate_live_workout_recommendation(
            completed_sets=int(state.get("completed_sets") or 0),
            remaining_sets=int(state.get("remaining_sets") or 0),
            recommended_reps_min=int(state.get("recommended_reps_min") or 0),
            recommended_reps_max=int(state.get("recommended_reps_max") or 0),
            recommended_weight=float(state.get("recommended_weight") or 0),
            guidance=str(state.get("last_guidance") or ""),
            substitution_recommendation=_coerce_dict(state.get("substitution_recommendation")) or None,
            rule_set=rule_set,
        )

    return {
        "completed_sets_by_exercise": merged_completed_sets,
        "live_recommendations_by_exercise": live_recommendations_by_exercise,
    }


def build_workout_today_payload(
    *,
    selected_session: dict[str, Any],
    mesocycle: dict[str, Any] | None,
    deload: dict[str, Any] | None,
    completed_sets_by_exercise: dict[str, int],
    live_recommendations_by_exercise: dict[str, dict[str, Any]],
    resume_selected: bool,
    daily_quote: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(selected_session)
    exercises: list[dict[str, Any]] = []

    for raw_exercise in selected_session.get("exercises") or []:
        exercise = dict(_coerce_dict(raw_exercise))
        exercise_id = str(exercise.get("id") or "")
        recommended_weight = float(exercise.get("recommended_working_weight", 20) or 20)
        exercise["warmups"] = compute_warmups(recommended_weight, 3)
        exercise["completed_sets"] = int(completed_sets_by_exercise.get(exercise_id, 0) or 0)

        live_recommendation = live_recommendations_by_exercise.get(exercise_id)
        if isinstance(live_recommendation, dict):
            exercise["live_recommendation"] = dict(live_recommendation)

        exercises.append(exercise)

    payload["exercises"] = exercises
    payload["mesocycle"] = _coerce_dict(mesocycle) if mesocycle is not None else mesocycle
    payload["deload"] = _coerce_dict(deload) if deload is not None else deload
    payload["resume"] = resume_selected
    payload["daily_quote"] = dict(_coerce_dict(daily_quote))
    return payload


def summarize_workout_exercise_performance(
    *,
    exercise: dict[str, Any],
    performed_logs: list[dict[str, Any]],
    next_working_weight: float,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    exercise_id = str(exercise.get("id") or "")
    planned_sets = int(exercise.get("sets", 3) or 3)
    rep_range = exercise.get("rep_range") or [8, 12]
    planned_min = int(rep_range[0]) if len(rep_range) > 0 else 8
    planned_max = int(rep_range[1]) if len(rep_range) > 1 else planned_min
    if planned_min > planned_max:
        planned_min, planned_max = planned_max, planned_min
    planned_weight = float(exercise.get("recommended_working_weight", 0) or 0)

    performed_sets = len(performed_logs)
    if performed_logs:
        average_reps = sum(float(row.get("reps", 0) or 0) for row in performed_logs) / performed_sets
        average_weight = sum(float(row.get("weight", 0) or 0) for row in performed_logs) / performed_sets
    else:
        average_reps = 0.0
        average_weight = 0.0

    completion_pct = int((performed_sets / max(planned_sets, 1)) * 100)
    rep_target_mid = (planned_min + planned_max) / 2
    rep_delta = round(average_reps - rep_target_mid, 2) if performed_sets else round(-rep_target_mid, 2)
    weight_delta = round(average_weight - planned_weight, 2) if performed_sets else round(-planned_weight, 2)
    guidance = _resolve_workout_summary_guidance(performed_sets, planned_sets, average_reps, planned_min, planned_max)
    guidance_rationale = _workout_guidance_rationale(guidance, rule_set=rule_set)
    decision_trace = {
        "interpreter": "summarize_workout_exercise_performance",
        "version": "v1",
        "inputs": {
            "exercise_id": exercise_id,
            "planned_sets": planned_sets,
            "planned_reps_min": planned_min,
            "planned_reps_max": planned_max,
            "planned_weight": planned_weight,
            "performed_set_count": performed_sets,
        },
        "steps": [
            {
                "decision": "exercise_summary_guidance",
                "result": {
                    "guidance": guidance,
                    "completion_pct": completion_pct,
                    "average_reps": round(average_reps, 2),
                    "average_weight": round(average_weight, 2),
                },
            }
        ],
        "outcome": {
            "guidance": guidance,
            "guidance_rationale": guidance_rationale,
            "next_working_weight": round(next_working_weight, 2),
        },
    }
    return {
        "exercise_id": exercise_id,
        "primary_exercise_id": exercise.get("primary_exercise_id"),
        "name": str(exercise.get("name") or exercise_id),
        "planned_sets": planned_sets,
        "planned_reps_min": planned_min,
        "planned_reps_max": planned_max,
        "planned_weight": planned_weight,
        "performed_sets": performed_sets,
        "average_performed_reps": round(average_reps, 2),
        "average_performed_weight": round(average_weight, 2),
        "completion_pct": completion_pct,
        "rep_delta": rep_delta,
        "weight_delta": weight_delta,
        "next_working_weight": round(next_working_weight, 2),
        "guidance": guidance,
        "guidance_rationale": guidance_rationale,
        "decision_trace": decision_trace,
    }


def summarize_workout_session_guidance(
    *,
    workout_id: str,
    completed_total: int,
    planned_total: int,
    exercise_summaries: list[dict[str, Any]],
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    percent_complete = int((completed_total / max(planned_total, 1)) * 100)
    overall_guidance = _resolve_workout_overall_guidance(percent_complete, exercise_summaries)
    overall_rationale = _workout_guidance_rationale(overall_guidance, rule_set=rule_set)
    decision_trace = {
        "interpreter": "summarize_workout_session_guidance",
        "version": "v1",
        "inputs": {
            "workout_id": workout_id,
            "completed_total": completed_total,
            "planned_total": planned_total,
            "exercise_count": len(exercise_summaries),
        },
        "steps": [
            {
                "decision": "overall_summary_guidance",
                "result": {
                    "percent_complete": percent_complete,
                    "exercise_guidance": [str(item.get("guidance") or "") for item in exercise_summaries],
                },
            }
        ],
        "outcome": {
            "overall_guidance": overall_guidance,
            "overall_rationale": overall_rationale,
        },
    }
    return {
        "workout_id": workout_id,
        "completed_total": completed_total,
        "planned_total": planned_total,
        "percent_complete": percent_complete,
        "overall_guidance": overall_guidance,
        "overall_rationale": overall_rationale,
        "decision_trace": decision_trace,
    }


def _muscle_set_delta(
    from_volume: dict[str, int],
    to_volume: dict[str, int],
) -> dict[str, int]:
    muscles = sorted(set(from_volume).union(to_volume))
    return {muscle: int(to_volume.get(muscle, 0)) - int(from_volume.get(muscle, 0)) for muscle in muscles}


def _tradeoff_risk_level(delta_by_muscle: dict[str, int]) -> str:
    steep_losses = [delta for delta in delta_by_muscle.values() if delta <= -3]
    moderate_losses = [delta for delta in delta_by_muscle.values() if -3 < delta <= -1]
    if steep_losses:
        return "high"
    if moderate_losses:
        return "medium"
    return "low"


def _sorted_session_titles(plan: dict[str, Any]) -> list[str]:
    return [str(session.get("title") or session.get("session_id") or "") for session in plan.get("sessions", [])]


def evaluate_schedule_adaptation(
    *,
    user_profile: dict[str, Any],
    split_preference: str,
    program_template: dict[str, Any],
    history: list[dict[str, Any]],
    phase: str,
    from_days: int,
    to_days: int,
    available_equipment: list[str] | None = None,
    soreness_by_muscle: dict[str, str] | None = None,
) -> dict[str, Any]:
    from_days = _clamp_days(from_days)
    to_days = _clamp_days(to_days)

    base_plan = generate_week_plan(
        user_profile=user_profile,
        days_available=from_days,
        split_preference=split_preference,
        program_template=program_template,
        history=history,
        phase=phase,
        available_equipment=available_equipment,
        soreness_by_muscle=soreness_by_muscle,
    )
    adapted_plan = generate_week_plan(
        user_profile=user_profile,
        days_available=to_days,
        split_preference=split_preference,
        program_template=program_template,
        history=history,
        phase=phase,
        available_equipment=available_equipment,
        soreness_by_muscle=soreness_by_muscle,
    )

    base_titles = _sorted_session_titles(base_plan)
    adapted_titles = _sorted_session_titles(adapted_plan)
    kept_titles = sorted(set(base_titles).intersection(adapted_titles))
    dropped_titles = [title for title in base_titles if title not in kept_titles]
    added_titles = [title for title in adapted_titles if title not in kept_titles]

    volume_delta = _muscle_set_delta(
        from_volume=base_plan.get("weekly_volume_by_muscle", {}),
        to_volume=adapted_plan.get("weekly_volume_by_muscle", {}),
    )
    changed_muscles = {
        muscle: delta for muscle, delta in volume_delta.items() if delta != 0
    }

    tradeoffs: list[str] = []
    if to_days < from_days:
        tradeoffs.append("Higher per-session density due to fewer training days.")
    if to_days > from_days:
        tradeoffs.append("Lower per-session density with more distributed weekly stress.")
    if dropped_titles:
        tradeoffs.append("Some original sessions are dropped to preserve priority lift continuity.")
    if changed_muscles:
        tradeoffs.append("Weekly set distribution shifts across muscle groups.")

    return {
        "from_days": from_days,
        "to_days": to_days,
        "kept_sessions": kept_titles,
        "dropped_sessions": dropped_titles,
        "added_sessions": added_titles,
        "muscle_set_delta": changed_muscles,
        "risk_level": _tradeoff_risk_level(changed_muscles),
        "tradeoffs": tradeoffs,
        "from_plan": base_plan,
        "to_plan": adapted_plan,
    }


def _normalized_weak_areas(values: list[str] | None) -> list[str]:
    normalized = [str(item).strip().lower() for item in (values or []) if str(item).strip()]
    return list(dict.fromkeys(normalized))


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
        ],
        "outcome": {
            "week_count": len(result.get("weeks") or []),
            "rejoin_policy": result.get("rejoin_policy"),
            "reason_code": "preview_generated",
            "weak_area_bonus_slots": weak_area_bonus_slots,
        },
        "request_runtime_trace": deepcopy(_coerce_dict(request_runtime_trace)),
    }
    return result


def interpret_frequency_adaptation_apply(
    *,
    onboarding_package: dict[str, Any],
    program_id: str,
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
        "template_id": program_id,
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
    weak_areas = _normalized_weak_areas(cast(list[str] | None, active_state.get("weak_areas")))
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


def build_generated_week_plan_payload(
    *,
    base_plan: dict[str, Any],
    template_selection_trace: dict[str, Any],
    generation_runtime_trace: dict[str, Any],
    selected_template_id: str,
    active_frequency_adaptation: dict[str, Any] | None,
    review_adjustments: dict[str, Any] | None = None,
    review_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = deepcopy(base_plan)
    plan["template_selection_trace"] = deepcopy(template_selection_trace)
    plan["generation_runtime_trace"] = deepcopy(generation_runtime_trace)

    if review_adjustments is not None:
        plan = apply_weekly_review_adjustments_to_plan(
            plan=plan,
            review_adjustments=review_adjustments,
            review_context=review_context,
        )

    adaptation_runtime = apply_active_frequency_adaptation_runtime(
        plan=plan,
        selected_template_id=selected_template_id,
        active_frequency_adaptation=active_frequency_adaptation,
    )
    return {
        "plan": cast(dict[str, Any], adaptation_runtime["plan"]),
        "adaptation_runtime": adaptation_runtime,
    }


def prepare_generated_week_review_overlay(review_cycle: Any | None) -> dict[str, Any]:
    if review_cycle is None:
        return {
            "review_adjustments": None,
            "review_context": None,
            "decision_trace": {
                "interpreter": "prepare_generated_week_review_overlay",
                "version": "v1",
                "inputs": {"has_review_cycle": False},
                "outcome": {"review_available": False},
            },
        }

    raw_adjustments = _read_attr(review_cycle, "adjustments")
    review_adjustments = raw_adjustments if isinstance(raw_adjustments, dict) else {}
    week_start = _read_attr(review_cycle, "week_start")
    reviewed_on = _read_attr(review_cycle, "reviewed_on")

    week_start_iso = week_start.isoformat() if hasattr(week_start, "isoformat") else None
    reviewed_on_iso = reviewed_on.isoformat() if hasattr(reviewed_on, "isoformat") else None
    review_context = None
    if isinstance(week_start_iso, str) and isinstance(reviewed_on_iso, str):
        review_context = {
            "week_start": week_start_iso,
            "reviewed_on": reviewed_on_iso,
        }

    return {
        "review_adjustments": review_adjustments,
        "review_context": review_context,
        "decision_trace": {
            "interpreter": "prepare_generated_week_review_overlay",
            "version": "v1",
            "inputs": {
                "has_review_cycle": True,
                "adjustments_is_dict": isinstance(raw_adjustments, dict),
                "has_week_start": week_start_iso is not None,
                "has_reviewed_on": reviewed_on_iso is not None,
            },
            "outcome": {
                "review_available": True,
                "has_review_context": review_context is not None,
                "review_adjustment_keys": sorted(review_adjustments.keys()),
            },
        },
    }


def _template_summary_rank(
    summary: dict[str, Any],
    *,
    split_preference: str,
    days_available: int,
) -> tuple[int, int, int, str]:
    split_rank = 0 if str(summary.get("split") or "") == split_preference else 1
    session_count = int(summary.get("session_count") or 0)
    adaptation_rank = 0 if 2 <= days_available <= 4 and session_count >= 5 else 1
    return (split_rank, adaptation_rank, -session_count, str(summary.get("id") or ""))


def _append_ordered_candidate_ids(
    *,
    ordered: list[str],
    candidate_summaries: list[dict[str, Any]],
    predicate,
) -> None:
    for summary in candidate_summaries:
        template_id = str(summary.get("id") or "")
        if not template_id or template_id in ordered:
            continue
        if predicate(summary):
            ordered.append(template_id)


def _ordered_generation_candidate_ids(
    *,
    preferred_template_id: str | None,
    split_preference: str,
    days_available: int,
    candidate_summaries: list[dict[str, Any]],
) -> list[str]:
    sorted_summaries = sorted(
        candidate_summaries,
        key=lambda summary: _template_summary_rank(
            summary,
            split_preference=split_preference,
            days_available=days_available,
        ),
    )
    ordered: list[str] = []

    preferred_id = str(preferred_template_id or "")
    if preferred_id:
        ordered.append(preferred_id)

    _append_ordered_candidate_ids(
        ordered=ordered,
        candidate_summaries=sorted_summaries,
        predicate=lambda summary: (
            summary.get("split") == split_preference and days_available in (summary.get("days_supported") or [])
        ),
    )
    _append_ordered_candidate_ids(
        ordered=ordered,
        candidate_summaries=sorted_summaries,
        predicate=lambda summary: days_available in (summary.get("days_supported") or []),
    )

    if "full_body_v1" not in ordered:
        ordered.append("full_body_v1")
    return ordered


def order_generation_template_candidates(
    *,
    preferred_template_id: str | None,
    split_preference: str,
    days_available: int,
    candidate_summaries: list[dict[str, Any]],
) -> list[str]:
    return _ordered_generation_candidate_ids(
        preferred_template_id=preferred_template_id,
        split_preference=split_preference,
        days_available=days_available,
        candidate_summaries=candidate_summaries,
    )


def _generation_selection_trace(
    *,
    reason: str,
    explicit_template_id: str,
    profile_template_id: str | None,
    split_preference: str,
    days_available: int,
    ordered_candidate_ids: list[str],
    evaluations: list[dict[str, Any]],
    selected_template_id: str,
) -> dict[str, Any]:
    return {
        "interpreter": "recommend_generation_template_selection",
        "reason": reason,
        "explicit_template_id": explicit_template_id,
        "profile_template_id": str(profile_template_id or ""),
        "split_preference": split_preference,
        "days_available": int(days_available),
        "ordered_candidate_ids": ordered_candidate_ids,
        "evaluations": evaluations,
        "selected_template_id": selected_template_id,
    }


def _summarize_generation_evaluation(template_id: str, evaluation: dict[str, Any] | None) -> dict[str, Any]:
    if evaluation is None:
        return {"template_id": template_id, "status": "not_evaluated"}

    status = str(evaluation.get("status") or "unknown")
    session_count = int(evaluation.get("session_count") or 0)
    exercise_count = int(evaluation.get("exercise_count") or 0)
    return {
        "template_id": template_id,
        "status": status,
        "session_count": session_count,
        "exercise_count": exercise_count,
        "viable": status == "loaded" and session_count > 0 and exercise_count > 0,
    }


def _select_viable_generation_candidate(
    *,
    ordered_candidate_ids: list[str],
    evaluation_by_id: dict[str, dict[str, Any]],
) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    fallback_template_id: str | None = None
    evaluation_trace: list[dict[str, Any]] = []

    for template_id in ordered_candidate_ids:
        summary = _summarize_generation_evaluation(template_id, evaluation_by_id.get(template_id))
        evaluation_trace.append(summary)

        if summary["status"] == "loaded" and fallback_template_id is None:
            fallback_template_id = template_id

        if summary["viable"]:
            return template_id, fallback_template_id, evaluation_trace

    return None, fallback_template_id, evaluation_trace


def recommend_generation_template_selection(
    *,
    explicit_template_id: str | None,
    profile_template_id: str | None,
    split_preference: str,
    days_available: int,
    candidate_summaries: list[dict[str, Any]],
    candidate_evaluations: list[dict[str, Any]],
) -> dict[str, Any]:
    explicit_id = str(explicit_template_id or "").strip()
    if explicit_id:
        decision_trace = _generation_selection_trace(
            reason="explicit_template_override",
            explicit_template_id=explicit_id,
            profile_template_id=profile_template_id,
            split_preference=split_preference,
            days_available=days_available,
            ordered_candidate_ids=[explicit_id],
            evaluations=[{"template_id": explicit_id, "status": "explicit_override"}],
            selected_template_id=explicit_id,
        )
        return {
            "selected_template_id": explicit_id,
            "reason": "explicit_template_override",
            "decision_trace": decision_trace,
        }

    ordered_candidate_ids = _ordered_generation_candidate_ids(
        preferred_template_id=profile_template_id,
        split_preference=split_preference,
        days_available=days_available,
        candidate_summaries=candidate_summaries,
    )
    evaluation_by_id = {
        str(item.get("template_id") or ""): item
        for item in candidate_evaluations
        if str(item.get("template_id") or "")
    }

    selected_template_id, fallback_template_id, evaluation_trace = _select_viable_generation_candidate(
        ordered_candidate_ids=ordered_candidate_ids,
        evaluation_by_id=evaluation_by_id,
    )
    if selected_template_id:
        decision_trace = _generation_selection_trace(
            reason="first_viable_candidate",
            explicit_template_id="",
            profile_template_id=profile_template_id,
            split_preference=split_preference,
            days_available=days_available,
            ordered_candidate_ids=ordered_candidate_ids,
            evaluations=evaluation_trace,
            selected_template_id=selected_template_id,
        )
        return {
            "selected_template_id": selected_template_id,
            "reason": "first_viable_candidate",
            "decision_trace": decision_trace,
        }

    if fallback_template_id:
        decision_trace = _generation_selection_trace(
            reason="fallback_loaded_candidate",
            explicit_template_id="",
            profile_template_id=profile_template_id,
            split_preference=split_preference,
            days_available=days_available,
            ordered_candidate_ids=ordered_candidate_ids,
            evaluations=evaluation_trace,
            selected_template_id=fallback_template_id,
        )
        return {
            "selected_template_id": fallback_template_id,
            "reason": "fallback_loaded_candidate",
            "decision_trace": decision_trace,
        }

    raise FileNotFoundError("No valid program templates available for generation")


def _is_program_adaptation_upgrade(summary: dict[str, Any], days_available: int) -> bool:
    if days_available < 2 or days_available > 4:
        return False
    session_count = int(summary.get("session_count") or 0)
    return session_count >= 5


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
    if week_index is not None or trigger_weeks_effective is not None:
        resolved_payload["mesocycle"] = {
            **_coerce_dict(resolved_payload.get("mesocycle")),
            **({"week_index": int(week_index)} if week_index is not None else {}),
            **(
                {"trigger_weeks_effective": int(trigger_weeks_effective)}
                if trigger_weeks_effective is not None
                else {}
            ),
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
    steps = [
        _decision_step("current_not_compatible", False),
        _decision_step(
            "low_adherence_keep_program",
            False,
            {"latest_adherence_score": latest_adherence_score},
        ),
    ]

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
    mesocycle = latest_plan_payload.get("mesocycle") if isinstance(latest_plan_payload.get("mesocycle"), dict) else {}
    steps.append(
        _decision_step(
            "mesocycle_complete_rotate",
            bool(rotated),
            {
                "candidate_program_id": rotated,
                "week_index": int(mesocycle.get("week_index", 1) or 1),
                "trigger_weeks_effective": int(mesocycle.get("trigger_weeks_effective", 6) or 6),
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


def humanize_progression_reason(
    progression: dict[str, Any],
    *,
    rule_set: dict[str, Any] | None = None,
) -> str:
    reason = str(progression.get("reason") or "").strip()
    if _looks_like_human_rationale(reason):
        return reason

    if "+" in reason:
        clauses = [_PROGRESSION_REASON_CLAUSES.get(token, token.replace("_", " ")) for token in reason.split("+") if token]
        return f"Deload because {_joined_clauses(clauses)}."

    if reason == "under_target_without_high_fatigue":
        return "Performance is below target without clear high-fatigue signals. Hold load and accumulate cleaner exposures before changing phase or deloading."

    action = str(progression.get("action") or "hold")
    if action == "progress":
        return _rule_rationale(
            rule_set,
            "increase_load",
            "Readiness and performance support progressing load on the next exposure.",
        )
    if action == "deload":
        return _rule_rationale(
            rule_set,
            "deload",
            "Current fatigue and performance signals support a short deload before pushing harder again.",
        )
    if action == "hold":
        return _rule_rationale(
            rule_set,
            "hold_load",
            "Current performance supports holding load while accumulating more stable work.",
        )
    return _humanize_reason_code(reason)


def humanize_phase_transition_reason(phase_transition: dict[str, Any]) -> str:
    reason = str(phase_transition.get("reason") or "").strip()
    if _looks_like_human_rationale(reason):
        return reason
    return _PHASE_TRANSITION_REASON_MESSAGES.get(reason, _humanize_reason_code(reason))


def humanize_specialization_reason(specialization: dict[str, Any]) -> str:
    reason = str(specialization.get("reason") or "").strip()
    if not reason:
        return ""
    if _looks_like_human_rationale(reason):
        return reason
    return _humanize_reason_code(reason)


def resolve_coaching_recommendation_rationale(recommendation_payload: dict[str, Any]) -> str:
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
    created_at: datetime,
    applied_at: datetime | None,
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
        "rationale": resolve_coaching_recommendation_rationale(payload),
        "focus_muscles": extract_coaching_recommendation_focus_muscles(payload),
        "created_at": created_at,
        "applied_at": applied_at,
    }


def normalize_coaching_recommendation_timeline_limit(limit: int) -> int:
    return max(1, min(100, int(limit)))


def build_coaching_recommendation_timeline_payload(rows: list[Any]) -> dict[str, Any]:
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
            created_at=cast(datetime, _read_attr(row, "created_at")),
            applied_at=cast(datetime | None, _read_attr(row, "applied_at")),
        )
        for row in rows
    ]
    return {"entries": entries}


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
) -> dict[str, Any]:
    phase_transition = recommendation_payload.get("phase_transition")
    if not isinstance(phase_transition, dict):
        raise ValueError("Recommendation is missing phase transition details")

    normalized_phase_transition = dict(phase_transition)
    if "next_phase" not in normalized_phase_transition and fallback_next_phase:
        normalized_phase_transition["next_phase"] = str(fallback_next_phase)

    decision_payload = interpret_coach_phase_apply_decision(
        recommendation_id=recommendation_id,
        phase_transition=normalized_phase_transition,
        confirm=confirm,
    )

    runtime_payload: dict[str, Any] = {
        "payload_value": normalized_phase_transition,
        "decision_payload": decision_payload,
    }
    if confirm:
        runtime_payload["record_fields"] = build_phase_applied_recommendation_record(
            template_id=template_id,
            current_phase=current_phase,
            progression_action=progression_action,
            source_recommendation_id=recommendation_id,
            next_phase=cast(str, decision_payload["next_phase"]),
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
) -> dict[str, Any]:
    specialization = recommendation_payload.get("specialization")
    if not isinstance(specialization, dict):
        raise ValueError("Recommendation is missing specialization details")

    normalized_specialization = dict(specialization)
    decision_payload = interpret_coach_specialization_apply_decision(
        recommendation_id=recommendation_id,
        specialization=normalized_specialization,
        confirm=confirm,
    )

    runtime_payload: dict[str, Any] = {
        "payload_value": normalized_specialization,
        "decision_payload": decision_payload,
    }
    if confirm:
        runtime_payload["record_fields"] = build_specialization_applied_recommendation_record(
            template_id=template_id,
            current_phase=current_phase,
            recommended_phase=recommended_phase,
            progression_action=progression_action,
            source_recommendation_id=recommendation_id,
        )
    return runtime_payload


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


def derive_readiness_score(
    *,
    completion_pct: int,
    adherence_score: int,
    soreness_level: str,
    progression_action: str,
) -> int:
    soreness_penalty_by_level = {
        "none": 0,
        "mild": 4,
        "moderate": 10,
        "severe": 18,
    }
    action_penalty = {
        "progress": 0,
        "hold": 5,
        "deload": 18,
    }
    soreness_penalty = soreness_penalty_by_level.get(soreness_level.lower(), 0)
    readiness = int((0.65 * completion_pct) + (8 * adherence_score))
    readiness -= soreness_penalty
    readiness -= action_penalty.get(progression_action, 0)
    return max(0, min(100, readiness))


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
    preview_request: dict[str, Any],
    progression_payload: dict[str, Any],
) -> int:
    provided = preview_request.get("readiness_score")
    if provided is not None:
        return int(provided)
    return derive_readiness_score(
        completion_pct=int(preview_request.get("completion_pct") or 0),
        adherence_score=int(preview_request.get("adherence_score") or 1),
        soreness_level=str(preview_request.get("soreness_level") or "none"),
        progression_action=str(progression_payload.get("action") or "hold"),
    )


def _coach_preview_progression_payload(
    preview_request: dict[str, Any],
    *,
    rule_set: dict[str, Any] | None,
) -> dict[str, Any]:
    progression = recommend_progression_action(
        completion_pct=int(preview_request.get("completion_pct") or 0),
        adherence_score=int(preview_request.get("adherence_score") or 1),
        soreness_level=str(preview_request.get("soreness_level") or "none"),
        average_rpe=cast(float | None, preview_request.get("average_rpe")),
        consecutive_underperformance_weeks=int(preview_request.get("stagnation_weeks") or 0),
        rule_set=rule_set,
    )
    return {
        **progression,
        "rationale": humanize_progression_reason(progression, rule_set=rule_set),
    }


def _coach_preview_trace(
    *,
    template_id: str,
    split_preference: str,
    phase: str,
    preview_request: dict[str, Any],
    schedule_payload: dict[str, Any],
    progression_payload: dict[str, Any],
    effective_readiness_score: int,
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
            {"decision": "progression", "result": progression_payload},
            {
                "decision": "readiness_score",
                "result": {
                    "provided": preview_request.get("readiness_score") is not None,
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
            "progression_action": progression_payload["action"],
            "next_phase": phase_transition_payload["next_phase"],
            "focus_muscles": specialization.get("focus_muscles") or [],
            "risk_level": schedule_payload["risk_level"],
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

    progression_payload = _coach_preview_progression_payload(preview_request, rule_set=rule_set)

    effective_readiness_score = _coach_preview_effective_readiness_score(preview_request, progression_payload)

    phase_transition = recommend_phase_transition(
        current_phase=cast(ProgramPhase, str(preview_request.get("current_phase") or "accumulation")),
        weeks_in_phase=int(preview_request.get("weeks_in_phase") or 1),
        readiness_score=effective_readiness_score,
        progression_action=cast(ProgressionAction, str(progression_payload.get("action") or "hold")),
        stagnation_weeks=int(preview_request.get("stagnation_weeks") or 0),
        rule_set=rule_set,
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
            schedule_payload=schedule_payload,
            progression_payload=progression_payload,
            effective_readiness_score=effective_readiness_score,
            phase_transition_payload=phase_transition_payload,
            specialization=specialization,
            media_warmups=media_warmups,
            request_runtime_trace=request_runtime_trace,
            template_runtime_trace=template_runtime_trace,
        ),
    }


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


def interpret_coach_phase_apply_decision(
    *,
    recommendation_id: str,
    phase_transition: dict[str, Any],
    confirm: bool,
) -> dict[str, Any]:
    next_phase_raw = str(phase_transition.get("next_phase") or "").strip()
    allowed_phases = {"accumulation", "intensification", "deload"}
    if next_phase_raw not in allowed_phases:
        raise ValueError("Recommendation has unsupported next phase")
    next_phase = cast(ProgramPhase, next_phase_raw)

    reason = str(phase_transition.get("reason") or "phase_apply")
    rationale = str(phase_transition.get("rationale") or humanize_phase_transition_reason({"reason": reason}))
    status = "applied" if confirm else "confirmation_required"
    applied = bool(confirm)

    return {
        "status": status,
        "recommendation_id": recommendation_id,
        "requires_confirmation": not confirm,
        "applied": applied,
        "next_phase": next_phase,
        "reason": reason,
        "rationale": rationale,
        "decision_trace": {
            "interpreter": "interpret_coach_phase_apply_decision",
            "version": "v1",
            "inputs": {
                "recommendation_id": recommendation_id,
                "confirm": confirm,
                "next_phase": next_phase,
                "reason": reason,
            },
            "steps": [
                _decision_step("phase_transition_present", True, {"next_phase": next_phase}),
                _decision_step("confirmation_received", confirm),
            ],
            "outcome": {
                "status": status,
                "applied": applied,
                "next_phase": next_phase,
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


def recommend_progression_action(
    *,
    completion_pct: int,
    adherence_score: int,
    soreness_level: str,
    average_rpe: float | None = None,
    consecutive_underperformance_weeks: int = 0,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    completion_pct = max(0, min(100, int(completion_pct)))
    adherence_score = max(1, min(5, int(adherence_score)))
    soreness_rank = _normalized_soreness_level(soreness_level)
    underperf = max(0, int(consecutive_underperformance_weeks))
    config = resolve_adaptive_rule_runtime(rule_set)
    deload_signal = evaluate_deload_signal(
        completion_pct=completion_pct,
        adherence_score=adherence_score,
        soreness_rank=soreness_rank,
        average_rpe=average_rpe,
        consecutive_underperformance_weeks=underperf,
        rule_set=rule_set,
    )

    if deload_signal["forced_deload_reasons"]:
        return _deload_response(
            config,
            "+".join(cast(list[str], deload_signal["forced_deload_reasons"])) or str(config["deload_reason"]),
        )

    if underperf >= int(config["underperf_threshold"]):
        if bool(deload_signal["underperformance_deload_matched"]):
            return _deload_response(config, str(config["deload_reason"]))
        return _hold_response("under_target_without_high_fatigue")

    if (
        completion_pct >= 95
        and adherence_score >= 4
        and soreness_rank <= 1
        and (average_rpe is None or float(average_rpe) <= 9.0)
    ):
        return _progress_response(config)

    return _hold_response(config["hold_reason"])


def recommend_phase_transition(
    *,
    current_phase: ProgramPhase,
    weeks_in_phase: int,
    readiness_score: int,
    progression_action: ProgressionAction,
    stagnation_weeks: int = 0,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    weeks_in_phase = max(1, int(weeks_in_phase))
    readiness_score = max(0, min(100, int(readiness_score)))
    stagnation_weeks = max(0, int(stagnation_weeks))
    adaptive_runtime = resolve_adaptive_rule_runtime(rule_set)
    intro_weeks = int(adaptive_runtime["intro_weeks"])
    scheduled_deload_weeks = int(adaptive_runtime["scheduled_deload_weeks"])

    if current_phase == "deload":
        if readiness_score >= 70:
            return {"next_phase": "accumulation", "reason": "deload_complete"}
        return {"next_phase": "deload", "reason": "extend_deload_low_readiness"}

    if current_phase == "accumulation":
        return _accumulation_phase_transition(
            weeks_in_phase=weeks_in_phase,
            readiness_score=readiness_score,
            progression_action=progression_action,
            stagnation_weeks=stagnation_weeks,
            intro_weeks=intro_weeks,
        )

    # intensification
    if progression_action == "deload" or weeks_in_phase >= min(4, scheduled_deload_weeks) or stagnation_weeks >= 2:
        return {"next_phase": "deload", "reason": "intensification_fatigue_cap"}
    return {"next_phase": "intensification", "reason": "continue_intensification"}


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
