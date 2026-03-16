from __future__ import annotations

from copy import deepcopy
from typing import Any


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


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _rule_dict(rule_set: dict[str, Any] | None, key: str) -> dict[str, Any]:
    if not isinstance(rule_set, dict):
        return {}
    value = rule_set.get(key)
    return value if isinstance(value, dict) else {}


def _rule_rationale(rule_set: dict[str, Any] | None, key: str, fallback: str) -> str:
    templates = _rule_dict(rule_set, "rationale_templates")
    value = templates.get(key)
    return str(value) if isinstance(value, str) and value.strip() else fallback


def _under_target_after_exposures(rule_set: dict[str, Any] | None) -> int:
    progression_rules = _rule_dict(rule_set, "progression_rules")
    on_under_target = _coerce_dict(progression_rules.get("on_under_target"))
    value = on_under_target.get("after_exposures")
    return int(value) if isinstance(value, int) and value > 0 else 1


def _humanize_workout_guidance(guidance: str) -> str:
    phrase = guidance.replace("_", " ").strip()
    if not phrase:
        return "Follow the planned progression."
    return phrase[:1].upper() + phrase[1:] + "."


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
    # Only treat a set as truly \"under target\" when it clearly undershoots the plan.
    # A single rep below the minimum is treated as a hold, not an automatic downshift.
    elif last_reps < max(planned_reps_min - 1, 0) or average_reps < max(planned_reps_min - 1, 0):
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
