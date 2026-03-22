from __future__ import annotations

from copy import deepcopy
from typing import Any

from .decision_weekly_review import apply_weekly_review_adjustments_to_plan


GENERATED_FULL_BODY_ADAPTIVE_REVIEW_SOURCE = "generated_full_body_adaptive_loop_v1"
_SUPPORTED_AXES = {"volume", "load", "weak_point"}
_GENERATED_FULL_BODY_SCOPE_IDS = {"full_body_v1", "adaptive_full_body_gold_v0_1"}
_GENERATED_FULL_BODY_POLICY_CANONICAL_ID = "pure_bodybuilding_phase_1_full_body"


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _axis_token(axis: str, direction: str) -> str:
    return f"{str(axis).strip()}_{str(direction).strip()}"


def _resolve_adaptive_axis_from_plan(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    adaptive_review = _coerce_dict(payload.get("adaptive_review"))
    if str(adaptive_review.get("source") or "").strip() != GENERATED_FULL_BODY_ADAPTIVE_REVIEW_SOURCE:
        return None, None
    primary_axis = str(adaptive_review.get("primary_axis") or "").strip()
    axis_direction = str(adaptive_review.get("axis_direction") or "").strip()
    if primary_axis not in _SUPPORTED_AXES or not axis_direction:
        return None, None
    return primary_axis, axis_direction


def _count_logged_history_days(history: list[dict[str, Any]]) -> int:
    return len(
        {
            str(entry.get("created_at") or "").strip()[:10]
            for entry in history
            if str(entry.get("created_at") or "").strip()[:10]
        }
    )


def _matching_exact_exercises(
    plan_payload: dict[str, Any],
    *,
    progression_state_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for session in _coerce_list(plan_payload.get("sessions")):
        if not isinstance(session, dict):
            continue
        for exercise in _coerce_list(session.get("exercises")):
            if not isinstance(exercise, dict):
                continue
            exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
            if not exercise_id:
                continue
            state = _coerce_dict(progression_state_map.get(exercise_id))
            if not state:
                continue
            matches.append(
                {
                    "exercise_id": exercise_id,
                    "slot_role": str(exercise.get("slot_role") or "").strip(),
                    "state": state,
                }
            )
    return matches


def _existing_weak_point_exercises(
    plan_payload: dict[str, Any],
    *,
    weak_areas: list[str],
) -> list[str]:
    normalized_weak_areas = {item.strip().lower() for item in weak_areas if item and item.strip()}
    if not normalized_weak_areas:
        return []

    matching_ids: list[str] = []
    for session in _coerce_list(plan_payload.get("sessions")):
        if not isinstance(session, dict):
            continue
        for exercise in _coerce_list(session.get("exercises")):
            if not isinstance(exercise, dict):
                continue
            if str(exercise.get("slot_role") or "").strip() != "weak_point":
                continue
            muscles = {
                str(item).strip().lower()
                for item in _coerce_list(exercise.get("primary_muscles"))
                if str(item).strip()
            }
            if normalized_weak_areas and not (normalized_weak_areas & muscles):
                continue
            exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
            if exercise_id:
                matching_ids.append(exercise_id)
    return matching_ids


def _supports_generated_constructor(template_selection_trace: dict[str, Any]) -> bool:
    generated_runtime_trace = _coerce_dict(template_selection_trace.get("generated_full_body_runtime_trace"))
    return bool(generated_runtime_trace.get("generated_constructor_applied"))


def _selected_template_in_generated_scope(*, selected_template_id: str, program_scope: list[str]) -> bool:
    normalized_scope = {str(item).strip() for item in program_scope if str(item).strip()}
    if selected_template_id in normalized_scope:
        return True
    return selected_template_id in _GENERATED_FULL_BODY_SCOPE_IDS and _GENERATED_FULL_BODY_POLICY_CANONICAL_ID in normalized_scope


def _strong_positive_reversal(
    *,
    stimulus_quality: str,
    fatigue_cost: str,
    recoverability: str,
    progression_eligibility: bool,
    latest_adherence_score: int | None,
    pain_flags: list[str],
) -> bool:
    return (
        stimulus_quality == "high"
        and fatigue_cost == "low"
        and recoverability == "high"
        and progression_eligibility
        and (latest_adherence_score is not None and latest_adherence_score >= 4)
        and not pain_flags
    )


def _strong_negative_reversal(
    *,
    deload_pressure: str,
    fatigue_cost: str,
    recoverability: str,
    latest_adherence_score: int | None,
    pain_flags: list[str],
) -> bool:
    return (
        deload_pressure == "high"
        or recoverability == "low"
        or fatigue_cost == "high"
        or bool(pain_flags)
        or (latest_adherence_score is not None and latest_adherence_score <= 2)
    )


def _build_history_stability(adaptation_history: dict[str, Any]) -> dict[str, Any]:
    return {
        "last_primary_axis": str(adaptation_history.get("last_primary_axis") or "").strip() or None,
        "last_axis_direction": str(adaptation_history.get("last_axis_direction") or "").strip() or None,
        "streak_weeks": int(adaptation_history.get("last_streak_weeks") or 0),
        "last_week_start": str(adaptation_history.get("last_week_start") or "").strip() or None,
        "last_selected_target_ids": _coerce_string_list(adaptation_history.get("last_selected_target_ids")),
    }


def _slot_priority(*, axis: str, direction: str, slot_role: str) -> int:
    normalized_role = str(slot_role or "").strip()
    volume_decrease = {
        "optional_fill": 0,
        "weak_point": 1,
        "accessory": 2,
        "secondary_compound": 3,
        "primary_compound": 4,
    }
    volume_increase = {
        "weak_point": 0,
        "secondary_compound": 1,
        "accessory": 2,
        "primary_compound": 3,
        "optional_fill": 4,
    }
    load_up = {
        "primary_compound": 0,
        "secondary_compound": 1,
        "accessory": 2,
        "weak_point": 3,
        "optional_fill": 4,
    }
    load_down = {
        "optional_fill": 0,
        "weak_point": 1,
        "accessory": 2,
        "secondary_compound": 3,
        "primary_compound": 4,
    }
    if axis == "volume" and direction == "decrease":
        return volume_decrease.get(normalized_role, 9)
    if axis == "volume" and direction == "increase":
        return volume_increase.get(normalized_role, 9)
    if axis == "load" and direction == "increase":
        return load_up.get(normalized_role, 9)
    if axis == "load" and direction == "decrease":
        return load_down.get(normalized_role, 9)
    return volume_increase.get(normalized_role, 9)


def _plan_exercise_rows(plan_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for session_index, session in enumerate(_coerce_list(plan_payload.get("sessions"))):
        if not isinstance(session, dict):
            continue
        session_id = str(session.get("session_id") or f"session-{session_index + 1}")
        day_role = str(session.get("day_role") or "").strip()
        for exercise_index, exercise in enumerate(_coerce_list(session.get("exercises"))):
            if not isinstance(exercise, dict):
                continue
            exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
            if not exercise_id:
                continue
            rows.append(
                {
                    "exercise_id": exercise_id,
                    "slot_role": str(exercise.get("slot_role") or "").strip(),
                    "sets": max(0, int(exercise.get("sets") or 0)),
                    "primary_muscles": _coerce_string_list(exercise.get("primary_muscles")),
                    "session_index": session_index,
                    "exercise_index": exercise_index,
                    "session_id": session_id,
                    "day_role": day_role,
                }
            )
    return rows


def _focus_match_count(*, row: dict[str, Any], focus_muscles: set[str]) -> int:
    row_muscles = {
        str(item).strip().lower()
        for item in _coerce_list(row.get("primary_muscles"))
        if str(item).strip()
    }
    return len(row_muscles & focus_muscles)


def _build_axis_adjustments(
    *,
    axis: str,
    direction: str,
    normalized_policy: dict[str, Any],
    selected_target_ids: list[str],
) -> tuple[int, dict[str, Any], list[str]]:
    global_set_delta = 0
    exercise_overrides: dict[str, Any] = {}
    weak_point_exercises: list[str] = []

    if axis == "volume":
        set_delta = (
            int(normalized_policy.get("volume_decrease_set_delta") or -1)
            if direction == "decrease"
            else int(normalized_policy.get("volume_increase_set_delta") or 1)
        )
        rationale = (
            "generated_adaptive_volume_down_targeted"
            if direction == "decrease"
            else "generated_adaptive_volume_up_targeted"
        )
        for exercise_id in selected_target_ids:
            exercise_overrides[exercise_id] = {
                "set_delta": set_delta,
                "weight_scale": 1.0,
                "rationale": rationale,
            }
        return global_set_delta, exercise_overrides, weak_point_exercises

    if axis == "load":
        scale = (
            float(normalized_policy.get("load_decrease_scale") or 0.95)
            if direction == "decrease"
            else float(normalized_policy.get("load_increase_scale") or 1.025)
        )
        rationale = (
            "generated_adaptive_load_down_exact_match"
            if direction == "decrease"
            else "generated_adaptive_load_up_exact_match"
        )
        for exercise_id in selected_target_ids:
            exercise_overrides[exercise_id] = {
                "set_delta": 0,
                "weight_scale": scale,
                "rationale": rationale,
            }
        return global_set_delta, exercise_overrides, weak_point_exercises

    if axis == "weak_point" and direction == "increase":
        weak_point_exercises = list(selected_target_ids)
        for exercise_id in selected_target_ids:
            exercise_overrides[exercise_id] = {
                "set_delta": int(normalized_policy.get("weak_point_set_delta") or 1),
                "weight_scale": 1.0,
                "rationale": "generated_adaptive_weak_point_boost",
            }
        return global_set_delta, exercise_overrides, weak_point_exercises

    return global_set_delta, exercise_overrides, weak_point_exercises


def _count_primary_axes(
    *,
    global_set_delta: int,
    exercise_overrides: dict[str, Any],
    weak_point_exercises: list[str],
) -> int:
    has_set_axis = global_set_delta != 0 or any(
        int(_coerce_dict(override).get("set_delta") or 0) != 0 for override in exercise_overrides.values()
    )
    has_load_axis = any(
        float(_coerce_dict(override).get("weight_scale", 1.0) or 1.0) != 1.0
        for override in exercise_overrides.values()
    )
    axes = 0
    if has_set_axis:
        axes += 1
    if has_load_axis:
        axes += 1
    return axes


def _select_axis_targets(
    *,
    axis: str,
    direction: str,
    plan_rows: list[dict[str, Any]],
    normalized_policy: dict[str, Any],
    progression_state: dict[str, dict[str, Any]],
    focus_muscles: set[str],
    stalled_exercise_ids: set[str],
    substitution_pressure: str,
    previous_selected_target_ids: list[str],
    persisted_from_prior_week: bool,
) -> dict[str, Any]:
    eligible_targets: list[dict[str, Any]] = []
    held_targets: list[dict[str, Any]] = []
    overall_hold_reasons: list[str] = []

    max_targets = (
        int(normalized_policy.get("max_load_targets_per_week") or 1)
        if axis == "load"
        else int(
            normalized_policy.get(
                "weak_point_max_boosted_exercises" if axis == "weak_point" else "max_volume_targets_per_week"
            )
            or 1
        )
    )
    exact_match_min_exposures = int(normalized_policy.get("minimum_exact_match_exposures_for_load_adjustment") or 1)
    previous_target_set = set(previous_selected_target_ids)

    for row in plan_rows:
        exercise_id = str(row["exercise_id"])
        slot_role = str(row["slot_role"])
        focus_match_count = _focus_match_count(row=row, focus_muscles=focus_muscles)
        persistent_preferred = exercise_id in previous_target_set
        hold_reasons: list[str] = []
        local_state = _coerce_dict(progression_state.get(exercise_id))

        if axis == "load":
            if not local_state:
                hold_reasons.append("no_exact_match_state")
            else:
                exposures = int(local_state.get("exposure_count") or 0)
                under_target = int(local_state.get("consecutive_under_target_exposures") or 0)
                fatigue_score = float(local_state.get("fatigue_score") or 0.0)
                last_action = str(local_state.get("last_progression_action") or "hold").strip().lower()
                stalled = exercise_id in stalled_exercise_ids
                if exposures < exact_match_min_exposures:
                    hold_reasons.append("insufficient_exact_match_exposures")
                elif direction == "increase":
                    if fatigue_score >= 0.7:
                        hold_reasons.append("high_local_fatigue")
                    if under_target > 0:
                        hold_reasons.append("under_target_history")
                    if stalled:
                        hold_reasons.append("stalled_exercise")
                    if last_action == "deload":
                        hold_reasons.append("recent_deload_action")
                    if substitution_pressure == "high":
                        hold_reasons.append("substitution_pressure_blocks_load_up")
                    if not hold_reasons:
                        eligible_targets.append(
                            {
                                **row,
                                "local_state": {
                                    "exposure_count": exposures,
                                    "consecutive_under_target_exposures": under_target,
                                    "fatigue_score": fatigue_score,
                                    "last_progression_action": last_action,
                                    "stalled": stalled,
                                },
                                "persistent_preferred": persistent_preferred,
                                "selection_reasons": ["exact_match_progression_ready"],
                                "sort_key": (
                                    0 if persistent_preferred else 1,
                                    _slot_priority(axis=axis, direction=direction, slot_role=slot_role),
                                    fatigue_score,
                                    -exposures,
                                    exercise_id,
                                ),
                            }
                        )
                else:
                    down_reasons: list[str] = []
                    if under_target >= 2:
                        down_reasons.append("under_target_history")
                    if fatigue_score >= 0.7:
                        down_reasons.append("high_local_fatigue")
                    if stalled:
                        down_reasons.append("stalled_exercise")
                    if last_action == "deload":
                        down_reasons.append("recent_deload_action")
                    if down_reasons:
                        eligible_targets.append(
                            {
                                **row,
                                "local_state": {
                                    "exposure_count": exposures,
                                    "consecutive_under_target_exposures": under_target,
                                    "fatigue_score": fatigue_score,
                                    "last_progression_action": last_action,
                                    "stalled": stalled,
                                },
                                "persistent_preferred": persistent_preferred,
                                "selection_reasons": down_reasons,
                                "sort_key": (
                                    0 if persistent_preferred else 1,
                                    _slot_priority(axis=axis, direction=direction, slot_role=slot_role),
                                    -under_target,
                                    -fatigue_score,
                                    exercise_id,
                                ),
                            }
                        )
                    else:
                        hold_reasons.append("no_local_load_down_signal")
        elif axis == "volume":
            current_sets = int(row.get("sets") or 0)
            if direction == "decrease" and current_sets <= 1:
                hold_reasons.append("minimum_sets_protected")
            else:
                selection_reasons = ["volume_axis_candidate"]
                if direction == "increase" and focus_match_count > 0:
                    selection_reasons.append("focus_muscle_match")
                eligible_targets.append(
                    {
                        **row,
                        "local_state": {"current_sets": current_sets, "focus_match_count": focus_match_count},
                        "persistent_preferred": persistent_preferred,
                        "selection_reasons": selection_reasons,
                        "sort_key": (
                            0 if persistent_preferred else 1,
                            0 if direction == "increase" and focus_match_count > 0 else 1,
                            _slot_priority(axis=axis, direction=direction, slot_role=slot_role),
                            -current_sets if direction == "decrease" else current_sets,
                            int(row.get("session_index") or 0),
                            int(row.get("exercise_index") or 0),
                            exercise_id,
                        ),
                    }
                )
        elif axis == "weak_point":
            if slot_role != "weak_point":
                hold_reasons.append("not_weak_point_slot")
            elif focus_match_count <= 0:
                hold_reasons.append("weak_point_not_in_focus")
            else:
                eligible_targets.append(
                    {
                        **row,
                        "local_state": {"focus_match_count": focus_match_count, "current_sets": int(row.get("sets") or 0)},
                        "persistent_preferred": persistent_preferred,
                        "selection_reasons": ["weak_point_focus_match"],
                        "sort_key": (
                            0 if persistent_preferred else 1,
                            -focus_match_count,
                            int(row.get("sets") or 0),
                            exercise_id,
                        ),
                    }
                )

        if hold_reasons:
            held_targets.append(
                {
                    "exercise_id": exercise_id,
                    "slot_role": slot_role,
                    "hold_reasons": hold_reasons,
                }
            )
            overall_hold_reasons.extend(hold_reasons)

    eligible_targets.sort(key=lambda item: item["sort_key"])
    selected_target_ids: list[str] = []

    if persisted_from_prior_week and previous_selected_target_ids:
        for exercise_id in previous_selected_target_ids:
            if any(str(target["exercise_id"]) == exercise_id for target in eligible_targets):
                selected_target_ids.append(exercise_id)
            if len(selected_target_ids) >= max_targets:
                break
        if not selected_target_ids:
            overall_hold_reasons.append("persisted_targets_not_actionable")
    else:
        for exercise_id in previous_selected_target_ids:
            if any(str(target["exercise_id"]) == exercise_id for target in eligible_targets):
                selected_target_ids.append(exercise_id)
            if len(selected_target_ids) >= max_targets:
                break
        for target in eligible_targets:
            exercise_id = str(target["exercise_id"])
            if exercise_id in selected_target_ids:
                continue
            selected_target_ids.append(exercise_id)
            if len(selected_target_ids) >= max_targets:
                break

    selected_target_set = set(selected_target_ids)
    selected_targets: list[dict[str, Any]] = []
    for target in eligible_targets:
        exercise_id = str(target["exercise_id"])
        if exercise_id in selected_target_set:
            selected_targets.append(
                {
                    "exercise_id": exercise_id,
                    "slot_role": str(target["slot_role"]),
                    "selection_reasons": list(target["selection_reasons"]),
                }
            )
        else:
            hold_reason = (
                "target_persistence_preferred_prior_selection"
                if persisted_from_prior_week and previous_selected_target_ids
                else "not_selected_within_target_cap"
            )
            held_targets.append(
                {
                    "exercise_id": exercise_id,
                    "slot_role": str(target["slot_role"]),
                    "hold_reasons": [hold_reason],
                }
            )
            overall_hold_reasons.append(hold_reason)

    deduped_hold_reasons: list[str] = []
    for reason in overall_hold_reasons:
        if reason not in deduped_hold_reasons:
            deduped_hold_reasons.append(reason)

    return {
        "eligible_targets": [
            {
                "exercise_id": str(target["exercise_id"]),
                "slot_role": str(target["slot_role"]),
                "selection_reasons": list(target["selection_reasons"]),
            }
            for target in eligible_targets
        ],
        "selected_targets": selected_targets,
        "selected_target_ids": selected_target_ids,
        "held_targets": held_targets,
        "hold_reasons": deduped_hold_reasons,
        "persistence_block_reason": "persisted_targets_not_actionable"
        if persisted_from_prior_week and previous_selected_target_ids and not selected_target_ids
        else None,
    }


def recommend_generated_full_body_adaptation(
    *,
    plan_payload: dict[str, Any],
    selected_template_id: str,
    template_selection_trace: dict[str, Any],
    training_state: dict[str, Any] | None,
    generation_runtime: dict[str, Any] | None,
    adaptive_policy: dict[str, Any] | None,
    block_review_gate: dict[str, Any] | None = None,
    review_adjustments_present: bool,
) -> dict[str, Any]:
    normalized_policy = _coerce_dict(adaptive_policy)
    normalized_training_state = _coerce_dict(training_state)
    normalized_generation_runtime = _coerce_dict(generation_runtime)
    weak_areas = _coerce_string_list(normalized_generation_runtime.get("weak_areas"))
    adherence_state = _coerce_dict(normalized_training_state.get("adherence_state"))
    readiness_state = _coerce_dict(normalized_training_state.get("readiness_state"))
    generation_state = _coerce_dict(normalized_training_state.get("generation_state"))
    stall_state = _coerce_dict(normalized_training_state.get("stall_state"))
    progression_state = {
        str(_coerce_dict(entry).get("exercise_id") or "").strip(): _coerce_dict(entry)
        for entry in _coerce_list(normalized_training_state.get("progression_state_per_exercise"))
        if str(_coerce_dict(entry).get("exercise_id") or "").strip()
    }
    stimulus_fatigue_response = _coerce_dict(normalized_training_state.get("stimulus_fatigue_response"))
    history = _coerce_list(normalized_generation_runtime.get("history"))
    adaptation_history = _coerce_dict(normalized_generation_runtime.get("generated_adaptation_history"))
    normalized_block_review_gate = _coerce_dict(block_review_gate)

    decision_trace: dict[str, Any] = {
        "interpreter": "recommend_generated_full_body_adaptation",
        "version": "v1.6",
        "inputs": {
            "selected_template_id": selected_template_id,
            "review_adjustments_present": bool(review_adjustments_present),
            "has_policy": bool(normalized_policy),
            "generated_constructor_applied": _supports_generated_constructor(template_selection_trace),
            "logged_history_days": _count_logged_history_days(history),
            "prior_generated_weeks": int(normalized_generation_runtime.get("prior_generated_weeks") or 0),
            "latest_adherence_score": adherence_state.get("latest_adherence_score"),
            "stimulus_fatigue_response": deepcopy(stimulus_fatigue_response),
            "adaptation_history": deepcopy(adaptation_history),
            "block_review_gate": deepcopy(normalized_block_review_gate),
        },
        "steps": [],
        "outcome": {},
    }

    if not normalized_policy:
        decision_trace["outcome"] = {"status": "suppressed", "reason": "adaptive_policy_missing"}
        return {"status": "suppressed", "adjustments": None, "decision_trace": decision_trace}

    if review_adjustments_present and bool(normalized_policy.get("explicit_review_precedence", True)):
        decision_trace["outcome"] = {"status": "suppressed", "reason": "explicit_review_precedence"}
        return {"status": "suppressed", "adjustments": None, "decision_trace": decision_trace}

    if not _supports_generated_constructor(template_selection_trace) and bool(
        normalized_policy.get("require_generated_constructor_output", True)
    ):
        decision_trace["outcome"] = {"status": "suppressed", "reason": "generated_constructor_not_applied"}
        return {"status": "suppressed", "adjustments": None, "decision_trace": decision_trace}

    if not _selected_template_in_generated_scope(
        selected_template_id=selected_template_id,
        program_scope=_coerce_string_list(normalized_policy.get("program_scope")),
    ):
        decision_trace["outcome"] = {"status": "suppressed", "reason": "selected_template_out_of_scope"}
        return {"status": "suppressed", "adjustments": None, "decision_trace": decision_trace}

    prior_generated_weeks = int(normalized_generation_runtime.get("prior_generated_weeks") or 0)
    if prior_generated_weeks < int(normalized_policy.get("minimum_prior_generated_weeks") or 0):
        decision_trace["outcome"] = {
            "status": "hold",
            "reason": "insufficient_prior_generated_weeks",
            "prior_generated_weeks": prior_generated_weeks,
        }
        return {"status": "hold", "adjustments": None, "decision_trace": decision_trace}

    logged_history_days = _count_logged_history_days(history)
    minimum_logged_sessions = int(normalized_policy.get("minimum_logged_sessions_for_auto_adjustment") or 0)
    safety_override_allowed = bool(normalized_policy.get("safety_override_allowed", True))

    latest_adherence_score = adherence_state.get("latest_adherence_score")
    if latest_adherence_score is not None:
        latest_adherence_score = int(latest_adherence_score)
    pain_flags = _coerce_string_list(readiness_state.get("pain_flags"))
    recoverability = str(stimulus_fatigue_response.get("recoverability") or "").strip().lower()
    fatigue_cost = str(stimulus_fatigue_response.get("fatigue_cost") or "").strip().lower()
    stimulus_quality = str(stimulus_fatigue_response.get("stimulus_quality") or "").strip().lower()
    deload_pressure = str(stimulus_fatigue_response.get("deload_pressure") or "").strip().lower()
    substitution_pressure = str(stimulus_fatigue_response.get("substitution_pressure") or "").strip().lower()
    progression_eligibility = bool(stimulus_fatigue_response.get("progression_eligibility"))
    under_target_muscles = {
        item.strip().lower()
        for item in _coerce_string_list(generation_state.get("under_target_muscles"))
        if item and item.strip()
    }
    stalled_exercise_ids = {
        item.strip()
        for item in _coerce_string_list(stall_state.get("stalled_exercise_ids"))
        if item and item.strip()
    }

    has_safety_pressure = _strong_negative_reversal(
        deload_pressure=deload_pressure,
        fatigue_cost=fatigue_cost,
        recoverability=recoverability,
        latest_adherence_score=latest_adherence_score,
        pain_flags=pain_flags,
    )
    if logged_history_days < minimum_logged_sessions and not (safety_override_allowed and has_safety_pressure):
        decision_trace["outcome"] = {
            "status": "hold",
            "reason": "insufficient_logged_history_days",
            "logged_history_days": logged_history_days,
            "minimum_logged_sessions_for_auto_adjustment": minimum_logged_sessions,
        }
        return {"status": "hold", "adjustments": None, "decision_trace": decision_trace}

    exact_matches = _matching_exact_exercises(plan_payload, progression_state_map=progression_state)
    weak_point_exercise_ids = _existing_weak_point_exercises(plan_payload, weak_areas=weak_areas)

    exact_match_min_exposures = int(normalized_policy.get("minimum_exact_match_exposures_for_load_adjustment") or 1)
    load_up_ids: list[str] = []
    load_down_ids: list[str] = []
    for match in exact_matches:
        state = _coerce_dict(match["state"])
        exposures = int(state.get("exposure_count") or 0)
        under_target = int(state.get("consecutive_under_target_exposures") or 0)
        fatigue_score = float(state.get("fatigue_score") or 0.0)
        if exposures < exact_match_min_exposures:
            continue
        if under_target >= 2 or fatigue_score >= 0.7:
            load_down_ids.append(str(match["exercise_id"]))
            continue
        if progression_eligibility and fatigue_score < 0.7:
            load_up_ids.append(str(match["exercise_id"]))

    candidate_options: list[dict[str, Any]] = []
    if has_safety_pressure:
        candidate_options.append(
            {"axis": "volume", "direction": "decrease", "reasons": ["recovery_pressure"], "candidate_ids": []}
        )
    if load_down_ids:
        candidate_options.append(
            {
                "axis": "load",
                "direction": "decrease",
                "reasons": ["exact_match_underperformance"],
                "candidate_ids": list(load_down_ids),
            }
        )
    if load_up_ids:
        candidate_options.append(
            {
                "axis": "load",
                "direction": "increase",
                "reasons": ["exact_match_progression_ready"],
                "candidate_ids": list(load_up_ids),
            }
        )
    if weak_point_exercise_ids and recoverability in {"high", "moderate"} and deload_pressure == "low":
        candidate_options.append(
            {
                "axis": "weak_point",
                "direction": "increase",
                "reasons": ["existing_weak_point_focus_match"],
                "candidate_ids": list(weak_point_exercise_ids),
            }
        )
    if (
        stimulus_quality == "low"
        and fatigue_cost == "low"
        and recoverability == "high"
        and (latest_adherence_score is not None and latest_adherence_score >= 4)
        and not pain_flags
    ):
        candidate_options.append(
            {"axis": "volume", "direction": "increase", "reasons": ["low_stimulus_high_recoverability"], "candidate_ids": []}
        )

    allowed_axis_tokens = set(_coerce_string_list(normalized_block_review_gate.get("allowed_axis_tokens")))
    restricted_axis_tokens = set(_coerce_string_list(normalized_block_review_gate.get("restricted_axis_tokens")))
    blocked_candidates: list[dict[str, Any]] = []
    candidate_axis: str | None = None
    axis_direction: str | None = None
    for option in candidate_options:
        option_axis = str(option["axis"])
        option_direction = str(option["direction"])
        axis_token = _axis_token(option_axis, option_direction)
        blocked_reason: str | None = None
        if allowed_axis_tokens and axis_token not in allowed_axis_tokens:
            blocked_reason = "not_in_allowed_axis_space"
        elif axis_token in restricted_axis_tokens:
            blocked_reason = "blocked_by_block_review"
        if blocked_reason:
            blocked_candidates.append(
                {
                    "axis_token": axis_token,
                    "primary_axis": option_axis,
                    "axis_direction": option_direction,
                    "reasons": list(option.get("reasons") or []),
                    "blocked_reason": blocked_reason,
                }
            )
            continue
        candidate_axis = option_axis
        axis_direction = option_direction
        break

    decision_trace["steps"].append(
        {
            "decision": "candidate_axis_selection",
            "result": {
                "candidate_axis": candidate_axis,
                "axis_direction": axis_direction,
                "candidate_options": [
                    {
                        "axis_token": _axis_token(str(option["axis"]), str(option["direction"])),
                        "primary_axis": str(option["axis"]),
                        "axis_direction": str(option["direction"]),
                        "reasons": list(option.get("reasons") or []),
                        "candidate_ids": list(option.get("candidate_ids") or []),
                    }
                    for option in candidate_options
                ],
                "blocked_candidates": deepcopy(blocked_candidates),
                "block_review_gate": {
                    "allowed_axis_tokens": sorted(allowed_axis_tokens),
                    "restricted_axis_tokens": sorted(restricted_axis_tokens),
                    "reset_adaptive_persistence_context": bool(
                        normalized_block_review_gate.get("reset_adaptive_persistence_context")
                    ),
                },
                "load_up_ids": load_up_ids,
                "load_down_ids": load_down_ids,
                "weak_point_exercises": weak_point_exercise_ids,
            },
        }
    )

    if candidate_axis is None or axis_direction is None:
        decision_trace["outcome"] = {
            "status": "hold",
            "reason": "block_review_restricted_all_candidate_axes" if blocked_candidates else "no_adaptive_axis_triggered",
            "blocked_candidates": deepcopy(blocked_candidates),
        }
        return {"status": "hold", "adjustments": None, "decision_trace": decision_trace}

    if bool(normalized_block_review_gate.get("reset_adaptive_persistence_context")):
        adaptation_history = {}

    stability = _build_history_stability(adaptation_history)
    previous_axis = stability["last_primary_axis"]
    previous_direction = stability["last_axis_direction"]
    previous_streak = int(stability["streak_weeks"] or 0)
    minimum_persist_weeks = int(normalized_policy.get("minimum_axis_persistence_weeks") or 1)
    previous_selected_target_ids = list(stability.get("last_selected_target_ids") or [])
    persisted_from_prior_week = False
    reversal_applied = False
    reversal_reason: str | None = None

    if previous_axis and previous_direction and previous_streak < minimum_persist_weeks:
        candidate_differs = previous_axis != candidate_axis or previous_direction != axis_direction
        if candidate_differs:
            strong_positive = _strong_positive_reversal(
                stimulus_quality=stimulus_quality,
                fatigue_cost=fatigue_cost,
                recoverability=recoverability,
                progression_eligibility=progression_eligibility,
                latest_adherence_score=latest_adherence_score,
                pain_flags=pain_flags,
            )
            strong_negative = has_safety_pressure
            allow_reversal = (
                (previous_direction == "decrease" and strong_positive)
                or (previous_direction == "increase" and strong_negative)
            )
            if allow_reversal:
                reversal_applied = True
                reversal_reason = "strong_opposing_signal_reversal"
            else:
                persisted_from_prior_week = True
                candidate_axis = previous_axis
                axis_direction = previous_direction

    current_streak_weeks = (
        previous_streak + 1 if previous_axis == candidate_axis and previous_direction == axis_direction else 1
    )
    stability_result = {
        "previous_axis": previous_axis,
        "previous_direction": previous_direction,
        "previous_streak_weeks": previous_streak,
        "minimum_axis_persistence_weeks": minimum_persist_weeks,
        "reset_adaptive_persistence_context": bool(normalized_block_review_gate.get("reset_adaptive_persistence_context")),
        "persisted_from_prior_week": persisted_from_prior_week,
        "reversal_applied": reversal_applied,
        "reversal_reason": reversal_reason,
        "previous_selected_target_ids": previous_selected_target_ids,
        "streak_weeks": current_streak_weeks,
    }
    decision_trace["steps"].append(
        {
            "decision": "stability_rule",
            "result": stability_result,
        }
    )

    target_selection = _select_axis_targets(
        axis=candidate_axis,
        direction=axis_direction,
        plan_rows=_plan_exercise_rows(plan_payload),
        normalized_policy=normalized_policy,
        progression_state=progression_state,
        focus_muscles={
            item.strip().lower()
            for item in [*weak_areas, *list(under_target_muscles)]
            if item and item.strip()
        },
        stalled_exercise_ids=stalled_exercise_ids,
        substitution_pressure=substitution_pressure,
        previous_selected_target_ids=previous_selected_target_ids,
        persisted_from_prior_week=persisted_from_prior_week,
    )
    decision_trace["steps"].append(
        {
            "decision": "target_selection",
            "result": deepcopy(target_selection),
        }
    )

    if not target_selection["selected_target_ids"]:
        decision_trace["outcome"] = {
            "status": "hold",
            "reason": target_selection.get("persistence_block_reason") or "no_eligible_targets_for_axis",
            "primary_axis": candidate_axis,
            "axis_direction": axis_direction,
            "persisted_from_prior_week": persisted_from_prior_week,
            "hold_reasons": list(target_selection.get("hold_reasons") or []),
        }
        return {"status": "hold", "adjustments": None, "decision_trace": decision_trace}

    global_set_delta, exercise_overrides, weak_point_exercises = _build_axis_adjustments(
        axis=candidate_axis,
        direction=axis_direction,
        normalized_policy=normalized_policy,
        selected_target_ids=list(target_selection["selected_target_ids"]),
    )

    non_neutral_axes = _count_primary_axes(
        global_set_delta=global_set_delta,
        exercise_overrides=exercise_overrides,
        weak_point_exercises=weak_point_exercises,
    )
    if non_neutral_axes > int(normalized_policy.get("max_primary_axes_per_week") or 1):
        raise ValueError("generated adaptive loop produced multiple primary adaptation axes")

    adjustments = {
        "global": {
            "set_delta": global_set_delta,
            "weight_scale": 1.0,
        },
        "weak_point_exercises": weak_point_exercises,
        "exercise_overrides": exercise_overrides,
        "decision_trace": {
            "interpreter": "recommend_generated_full_body_adaptation",
            "version": "v1.6",
            "primary_axis": candidate_axis,
            "axis_direction": axis_direction,
            "persisted_from_prior_week": persisted_from_prior_week,
            "reversal_applied": reversal_applied,
            "reversal_reason": reversal_reason,
            "axis_choice": {
                "primary_axis": candidate_axis,
                "axis_direction": axis_direction,
                "persisted_from_prior_week": persisted_from_prior_week,
                "reversal_applied": reversal_applied,
                "reversal_reason": reversal_reason,
            },
            "eligible_targets": deepcopy(target_selection["eligible_targets"]),
            "selected_targets": deepcopy(target_selection["selected_targets"]),
            "held_targets": deepcopy(target_selection["held_targets"]),
            "hold_reasons": list(target_selection["hold_reasons"]),
            "cause": {
                "stimulus_fatigue_response": deepcopy(stimulus_fatigue_response),
                "latest_adherence_score": latest_adherence_score,
                "pain_flags": pain_flags,
                "exact_match_candidates": [item["exercise_id"] for item in exact_matches],
                "under_target_muscles": sorted(under_target_muscles),
                "stalled_exercise_ids": sorted(stalled_exercise_ids),
                "substitution_pressure": substitution_pressure,
                "adaptation_history": deepcopy(adaptation_history),
                "block_review_gate": deepcopy(normalized_block_review_gate),
            },
            "effect": {
                "global_set_delta": global_set_delta,
                "selected_target_ids": list(target_selection["selected_target_ids"]),
                "exercise_override_ids": sorted(exercise_overrides.keys()),
                "weak_point_exercises": list(weak_point_exercises),
            },
            "block_review": {
                "restricted_axis_tokens": sorted(restricted_axis_tokens),
                "blocked_candidates": deepcopy(blocked_candidates),
                "reset_adaptive_persistence_context": bool(
                    normalized_block_review_gate.get("reset_adaptive_persistence_context")
                ),
            },
        },
    }
    decision_trace["outcome"] = {
        "status": "apply",
        "primary_axis": candidate_axis,
        "axis_direction": axis_direction,
        "streak_weeks": current_streak_weeks,
        "minimum_axis_persistence_weeks": minimum_persist_weeks,
        "reset_adaptive_persistence_context": bool(normalized_block_review_gate.get("reset_adaptive_persistence_context")),
        "persisted_from_prior_week": persisted_from_prior_week,
        "reversal_applied": reversal_applied,
        "reversal_reason": reversal_reason,
        "global_set_delta": global_set_delta,
        "selected_target_ids": list(target_selection["selected_target_ids"]),
        "exercise_override_ids": sorted(exercise_overrides.keys()),
        "weak_point_exercises": list(weak_point_exercises),
        "hold_reasons": list(target_selection["hold_reasons"]),
    }
    return {
        "status": "apply",
        "adjustments": adjustments,
        "decision_trace": decision_trace,
    }


def apply_generated_full_body_adaptation_to_plan(
    *,
    plan_payload: dict[str, Any],
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(decision_payload, dict) or str(decision_payload.get("status") or "") != "apply":
        return deepcopy(plan_payload)

    adjustments = _coerce_dict(decision_payload.get("adjustments"))
    decision_trace = _coerce_dict(decision_payload.get("decision_trace"))
    adjusted = apply_weekly_review_adjustments_to_plan(
        plan_payload=plan_payload,
        review_adjustments=adjustments,
        review_context=None,
    )
    adaptive_review = _coerce_dict(adjusted.get("adaptive_review"))
    decision_outcome = _coerce_dict(decision_trace.get("outcome"))
    adaptive_review["source"] = GENERATED_FULL_BODY_ADAPTIVE_REVIEW_SOURCE
    adaptive_review["primary_axis"] = decision_outcome.get("primary_axis")
    adaptive_review["axis_direction"] = decision_outcome.get("axis_direction")
    adaptive_review["stability"] = {
        "persist_min_weeks": int(decision_outcome.get("minimum_axis_persistence_weeks") or 1),
        "streak_weeks": int(decision_outcome.get("streak_weeks") or 1),
        "persisted_from_prior_week": bool(decision_outcome.get("persisted_from_prior_week")),
        "reversal_applied": bool(decision_outcome.get("reversal_applied")),
        "reversal_reason": decision_outcome.get("reversal_reason"),
    }
    adjusted["adaptive_review"] = adaptive_review
    return adjusted
