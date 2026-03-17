from datetime import date, timedelta
from typing import Any
import re
from copy import deepcopy

from .equipment import resolve_equipment_tags
from .rules_runtime import (
    resolve_equipment_substitution,
    resolve_repeat_failure_substitution,
    resolve_scheduler_deload_runtime,
    resolve_scheduler_exercise_adjustment_runtime,
    resolve_scheduler_exercise_muscles_runtime,
    resolve_scheduler_mesocycle_runtime,
    resolve_scheduler_muscle_coverage_runtime,
    resolve_scheduler_session_exercise_cap,
    resolve_scheduler_session_selection,
)


def _apply_deload_modifiers(sets: int, weight: float, *, set_reduction_pct: int, load_reduction_pct: int) -> tuple[int, float]:
    adjusted_sets = max(1, int(round(sets * (100 - set_reduction_pct) / 100)))
    adjusted_weight = max(2.0, weight * (100 - load_reduction_pct) / 100)
    rounded_weight = round(adjusted_weight / 0.5) * 0.5
    return adjusted_sets, rounded_weight


def _build_equipment_set(available_equipment: list[str] | None) -> set[str]:
    return {item.lower() for item in (available_equipment or []) if item}


def _normalize_movement_restrictions(movement_restrictions: list[str] | None) -> set[str]:
    return {
        re.sub(r"[^a-z]+", "_", str(item).strip().lower()).strip("_")
        for item in (movement_restrictions or [])
        if str(item).strip()
    }


def _is_restricted_movement_pattern(exercise: dict[str, Any], movement_restrictions: set[str]) -> bool:
    if not movement_restrictions:
        return False
    movement_pattern = re.sub(
        r"[^a-z]+",
        "_",
        str(exercise.get("movement_pattern") or "").strip().lower(),
    ).strip("_")
    restriction_map = {
        "vertical_press": "overhead_pressing",
        "squat": "deep_knee_flexion",
        "lunge": "deep_knee_flexion",
    }
    return bool(movement_pattern and restriction_map.get(movement_pattern) in movement_restrictions)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "exercise"


def _authored_execution_fields(exercise: dict[str, Any]) -> dict[str, Any]:
    return {
        "last_set_intensity_technique": exercise.get("last_set_intensity_technique"),
        "warm_up_sets": exercise.get("warm_up_sets"),
        "working_sets": exercise.get("working_sets"),
        "reps": exercise.get("reps"),
        "early_set_rpe": exercise.get("early_set_rpe"),
        "last_set_rpe": exercise.get("last_set_rpe"),
        "rest": exercise.get("rest"),
        "tracking_set_1": exercise.get("tracking_set_1"),
        "tracking_set_2": exercise.get("tracking_set_2"),
        "tracking_set_3": exercise.get("tracking_set_3"),
        "tracking_set_4": exercise.get("tracking_set_4"),
        "substitution_option_1": exercise.get("substitution_option_1"),
        "substitution_option_2": exercise.get("substitution_option_2"),
        "demo_url": exercise.get("demo_url"),
        "video_url": exercise.get("video_url"),
    }


def _build_planned_exercise(
    exercise: dict[str, Any],
    history_index: dict[str, dict[str, Any]],
    equipment_set: set[str],
    *,
    is_deload_week: bool,
    set_reduction_pct: int,
    load_reduction_pct: int,
    rule_set: dict[str, Any] | None,
    progression_state: dict[str, Any] | None = None,
    substitution_pressure: str | None = None,
    movement_restrictions: set[str] | None = None,
) -> dict[str, Any] | None:
    if _is_restricted_movement_pattern(exercise, movement_restrictions or set()):
        return None
    resolved_equipment_tags = resolve_equipment_tags(
        exercise_name=exercise.get("name", ""),
        explicit_tags=exercise.get("equipment_tags"),
    )
    previous = history_index.get(exercise.get("id"), {})
    recommended = float(previous.get("next_working_weight") or exercise.get("start_weight", 20))
    planned_sets = int(exercise.get("sets", 3) or 3)
    if is_deload_week:
        planned_sets, recommended = _apply_deload_modifiers(
            planned_sets,
            recommended,
            set_reduction_pct=set_reduction_pct,
            load_reduction_pct=load_reduction_pct,
        )
    exercise_adjustment_runtime = resolve_scheduler_exercise_adjustment_runtime(
        progression_state=progression_state,
        stimulus_substitution_pressure=substitution_pressure,
        rule_set=rule_set,
    )
    authored_working = exercise.get("working_sets")
    min_sets = 1
    if authored_working is not None:
        try:
            min_sets = max(1, int(float(str(authored_working))))
        except (TypeError, ValueError):
            pass
    planned_sets = max(min_sets, planned_sets + int(exercise_adjustment_runtime["set_delta"]))
    recommended = max(2.0, recommended * float(exercise_adjustment_runtime["load_scale"]))
    recommended = round(recommended / 0.5) * 0.5
    substitutions = exercise.get("substitution_candidates") or exercise.get("substitutions") or []
    failed_exposure_count = int((progression_state or {}).get("consecutive_under_target_exposures") or 0)
    repeat_failure_runtime = resolve_repeat_failure_substitution(
        exercise_id=str(exercise.get("id") or ""),
        exercise_name=str(exercise.get("name") or ""),
        substitution_candidates=list(substitutions),
        consecutive_under_target_exposures=failed_exposure_count,
        equipment_set=equipment_set,
        rule_set=rule_set,
    )
    substitution_runtime = resolve_equipment_substitution(
        exercise_id=str(exercise.get("id") or ""),
        exercise_name=str(exercise.get("name") or ""),
        exercise_equipment_tags=resolved_equipment_tags,
        substitution_candidates=list(substitutions),
        equipment_set=equipment_set,
        rule_set=rule_set,
    )
    compatible_substitutions = list(substitution_runtime["compatible_substitutions"])

    planned_id = exercise.get("id")
    planned_name = exercise.get("name")
    planned_movement_pattern = exercise.get("movement_pattern")
    planned_primary_muscles = exercise.get("primary_muscles", [])
    planned_equipment_tags = resolved_equipment_tags
    planned_video = exercise.get("video")
    substitution_metadata = exercise.get("substitution_metadata") or {}
    repeat_failure_substitution = None
    if bool(repeat_failure_runtime.get("recommend_substitution")):
        planned_name = str(repeat_failure_runtime.get("recommended_name"))
        selected_metadata = substitution_metadata.get(planned_name) or {}
        planned_id = selected_metadata.get("id") or _slugify(planned_name)
        planned_movement_pattern = selected_metadata.get("movement_pattern") or planned_movement_pattern
        planned_primary_muscles = selected_metadata.get("primary_muscles") or planned_primary_muscles
        planned_equipment_tags = selected_metadata.get("equipment_tags") or planned_equipment_tags
        planned_video = selected_metadata.get("video") or planned_video
        repeat_failure_substitution = {
            "recommended_name": planned_name,
            "failed_exposure_count": failed_exposure_count,
            "decision_trace": dict(repeat_failure_runtime["decision_trace"]),
        }
    elif not bool(substitution_runtime["decision_trace"]["outcome"]["original_compatible"]):
        if not compatible_substitutions:
            return None
        planned_name = str(substitution_runtime["selected_name"])
        selected_metadata = substitution_metadata.get(planned_name) or {}
        planned_id = selected_metadata.get("id") or _slugify(planned_name)
        planned_movement_pattern = selected_metadata.get("movement_pattern") or planned_movement_pattern
        planned_primary_muscles = selected_metadata.get("primary_muscles") or planned_primary_muscles
        planned_equipment_tags = selected_metadata.get("equipment_tags") or planned_equipment_tags
        planned_video = selected_metadata.get("video") or planned_video

    normalized_substitution_pressure = str(exercise_adjustment_runtime["substitution_pressure"])
    substitution_guidance = (
        exercise_adjustment_runtime["substitution_guidance"]
        if compatible_substitutions
        else None
    )

    return {
        "id": planned_id,
        "primary_exercise_id": exercise.get("primary_exercise_id") or exercise.get("id"),
        "name": planned_name,
        "sets": planned_sets,
        "rep_range": exercise.get("rep_range", [8, 12]),
        "recommended_working_weight": recommended,
        "priority": exercise.get("priority", "standard"),
        "movement_pattern": planned_movement_pattern,
        "primary_muscles": planned_primary_muscles,
        "substitution_candidates": compatible_substitutions,
        "substitution_pressure": normalized_substitution_pressure,
        "substitution_guidance": substitution_guidance,
        "recovery_adjustment_trace": dict(exercise_adjustment_runtime["decision_trace"]),
        "substitution_decision_trace": dict(substitution_runtime["decision_trace"]),
        "repeat_failure_substitution": repeat_failure_substitution,
        "notes": exercise.get("notes"),
        "video": planned_video,
        "equipment_tags": planned_equipment_tags,
        "slot_role": exercise.get("slot_role"),
        **_authored_execution_fields(exercise),
    }


def _exercise_slot_role(exercise: dict[str, Any]) -> str:
    return str(exercise.get("slot_role") or "").strip().lower()


def _session_profile(
    session: dict[str, Any],
    *,
    muscle_coverage_runtime: dict[str, Any],
) -> tuple[set[str], set[str]]:
    primary_exercise_ids: set[str] = set()
    muscles: set[str] = set()

    for exercise in session.get("exercises") or []:
        primary_exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
        if primary_exercise_id:
            primary_exercise_ids.add(primary_exercise_id)
        exercise_muscle_runtime = resolve_scheduler_exercise_muscles_runtime(
            exercise=exercise,
            muscle_coverage_runtime=muscle_coverage_runtime,
        )
        muscles.update(exercise_muscle_runtime["normalized_muscles"])

    return primary_exercise_ids, muscles


def _build_session_selection_profiles(
    base_sessions: list[dict[str, Any]],
    *,
    muscle_coverage_runtime: dict[str, Any],
) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for index, session in enumerate(base_sessions):
        primary_exercise_ids, muscles = _session_profile(
            session,
            muscle_coverage_runtime=muscle_coverage_runtime,
        )
        slot_roles = [
            _exercise_slot_role(exercise)
            for exercise in session.get("exercises") or []
        ]
        ordered_primary_ids = [
            str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
            for exercise in session.get("exercises") or []
            if str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
        ]
        profiles.append(
            {
                "index": index,
                "day_role": _session_day_role(session),
                "primary_exercise_ids": ordered_primary_ids,
                "muscles": sorted(muscles),
                "slot_roles": slot_roles,
            }
        )
    return profiles


def _session_day_role(session: dict[str, Any]) -> str:
    return str(session.get("day_role") or "").strip().lower()


def _nearest_selected_session_index(index: int, selected_indices: list[int]) -> int:
    return min(selected_indices, key=lambda item: (abs(item - index), item))


def _merge_dropped_sessions_into_selected(
    base_sessions: list[dict[str, Any]],
    selected_sessions: list[tuple[int, dict[str, Any]]],
) -> list[tuple[int, dict[str, Any]]]:
    if len(selected_sessions) >= len(base_sessions):
        return [(index, deepcopy(session)) for index, session in selected_sessions]

    merged_by_index: dict[int, dict[str, Any]] = {
        index: deepcopy(session) for index, session in selected_sessions
    }
    selected_indices = sorted(merged_by_index)

    for index, session in enumerate(base_sessions):
        if index in merged_by_index:
            continue

        target_index = _nearest_selected_session_index(index, selected_indices)
        target_session = merged_by_index[target_index]
        existing_ids = {
            str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
            for exercise in target_session.get("exercises") or []
        }

        additions: list[dict[str, Any]] = []
        for exercise in session.get("exercises") or []:
            primary_exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
            if primary_exercise_id and primary_exercise_id in existing_ids:
                continue
            additions.append(deepcopy(exercise))
            if primary_exercise_id:
                existing_ids.add(primary_exercise_id)

        if additions:
            target_session.setdefault("exercises", []).extend(additions)

    return [(index, merged_by_index[index]) for index in selected_indices]


def _resolve_authored_week_runtime(
    program_template: dict[str, Any],
    prior_generated_weeks: int,
) -> dict[str, Any]:
    authored_weeks = program_template.get("authored_weeks") or []
    if not isinstance(authored_weeks, list) or not authored_weeks:
        return {
            "week_index": 1,
            "week_role": None,
            "sessions": list(program_template.get("sessions") or []),
            "sequence_length": None,
            "sequence_complete": False,
        }

    sequence_length = len(authored_weeks)
    normalized_prior_weeks = max(0, int(prior_generated_weeks))
    bounded_index = min(normalized_prior_weeks, sequence_length - 1)
    selected_week = authored_weeks[bounded_index] if isinstance(authored_weeks[bounded_index], dict) else {}
    selected_sessions = selected_week.get("sessions") or []
    return {
        "week_index": int(selected_week.get("week_index") or bounded_index + 1),
        "week_role": str(selected_week.get("week_role") or "").strip() or None,
        "sessions": (
            list(selected_sessions)
            if isinstance(selected_sessions, list)
            else list(program_template.get("sessions") or [])
        ),
        "sequence_length": sequence_length,
        "sequence_complete": normalized_prior_weeks >= sequence_length,
    }


def _compute_weekly_volume_and_coverage(
    planned_sessions: list[dict[str, Any]],
    *,
    muscle_coverage_runtime: dict[str, Any],
) -> tuple[dict[str, int], dict[str, Any]]:
    tracked_muscles = list(muscle_coverage_runtime["tracked_muscles"])
    minimum_sets_per_muscle = int(muscle_coverage_runtime["minimum_sets_per_muscle"])
    volume_by_muscle = dict.fromkeys(tracked_muscles, 0)
    untracked_exercise_count = 0

    for session in planned_sessions:
        for exercise in session.get("exercises", []):
            exercise_muscle_runtime = resolve_scheduler_exercise_muscles_runtime(
                exercise=exercise,
                muscle_coverage_runtime=muscle_coverage_runtime,
            )
            resolved_muscles = set(exercise_muscle_runtime["normalized_muscles"])
            tracked_exercise_muscles = [
                muscle for muscle in resolved_muscles if muscle in volume_by_muscle
            ]
            if not tracked_exercise_muscles:
                untracked_exercise_count += 1
                continue

            sets = int(exercise.get("sets", 0) or 0)
            for muscle in tracked_exercise_muscles:
                volume_by_muscle[muscle] += sets

    under_target_muscles = [
        muscle for muscle in volume_by_muscle if volume_by_muscle[muscle] < minimum_sets_per_muscle
    ]
    covered_muscles = [
        muscle for muscle in volume_by_muscle if volume_by_muscle[muscle] >= minimum_sets_per_muscle
    ]

    return volume_by_muscle, {
        "minimum_sets_per_muscle": minimum_sets_per_muscle,
        "covered_muscles": covered_muscles,
        "under_target_muscles": under_target_muscles,
        "untracked_exercise_count": untracked_exercise_count,
    }


def generate_week_plan(
    user_profile: dict[str, Any],
    days_available: int,
    split_preference: str,
    program_template: dict[str, Any],
    history: list[dict[str, Any]],
    phase: str,
    available_equipment: list[str] | None = None,
    soreness_by_muscle: dict[str, str] | None = None,
    prior_generated_weeks: int = 0,
    latest_adherence_score: int | None = None,
    severe_soreness_count: int = 0,
    session_time_budget_minutes: int | None = None,
    movement_restrictions: list[str] | None = None,
    progression_state_per_exercise: list[dict[str, Any]] | None = None,
    stimulus_fatigue_response: dict[str, Any] | None = None,
    stimulus_fatigue_response_source: str | None = None,
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    days_available = max(2, min(7, days_available))
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    authored_week_runtime = _resolve_authored_week_runtime(program_template, prior_generated_weeks)
    base_sessions = list(authored_week_runtime.get("sessions") or [])
    muscle_coverage_runtime = resolve_scheduler_muscle_coverage_runtime(rule_set=rule_set)
    session_selection_runtime = resolve_scheduler_session_selection(
        session_profiles=_build_session_selection_profiles(
            base_sessions,
            muscle_coverage_runtime=muscle_coverage_runtime,
        ),
        history=history,
        days_available=days_available,
        rule_set=rule_set,
    )
    selected_base_sessions = [
        (index, base_sessions[index])
        for index in session_selection_runtime["selected_indices"]
        if 0 <= index < len(base_sessions)
    ]
    selected_sessions = _merge_dropped_sessions_into_selected(base_sessions, selected_base_sessions)

    history_index = {
        item.get("exercise_id"): item for item in history if item.get("exercise_id")
    }
    progression_state_index = {
        str(item.get("exercise_id")): item
        for item in (progression_state_per_exercise or [])
        if str(item.get("exercise_id") or "").strip()
    }
    equipment_set = _build_equipment_set(available_equipment)
    normalized_movement_restrictions = _normalize_movement_restrictions(movement_restrictions)
    mesocycle = resolve_scheduler_mesocycle_runtime(
        template_deload=program_template.get("deload"),
        prior_generated_weeks=prior_generated_weeks,
        latest_adherence_score=latest_adherence_score,
        severe_soreness_count=severe_soreness_count,
        authored_week_index=(
            int(authored_week_runtime.get("week_index"))
            if authored_week_runtime.get("week_index") is not None
            else None
        ),
        authored_week_role=str(authored_week_runtime.get("week_role") or "").strip() or None,
        authored_sequence_length=(
            int(authored_week_runtime.get("sequence_length"))
            if authored_week_runtime.get("sequence_length") is not None
            else None
        ),
        authored_sequence_complete=bool(authored_week_runtime.get("sequence_complete")),
        stimulus_fatigue_response=stimulus_fatigue_response,
        stimulus_fatigue_response_source=stimulus_fatigue_response_source,
        phase=phase,
        rule_set=rule_set,
    )

    deload_runtime = resolve_scheduler_deload_runtime(
        template_deload=program_template.get("deload"),
        is_deload_week=bool(mesocycle["is_deload_week"]),
        mesocycle_decision_trace=mesocycle["decision_trace"],
        rule_set=rule_set,
    )
    set_reduction_pct = int(deload_runtime["set_reduction_pct"])
    load_reduction_pct = int(deload_runtime["load_reduction_pct"])
    deload = {
        "active": bool(deload_runtime["active"]),
        "set_reduction_pct": set_reduction_pct,
        "load_reduction_pct": load_reduction_pct,
        "reason": mesocycle["deload_reason"],
        "decision_trace": dict(deload_runtime["decision_trace"]),
    }

    planned_sessions: list[dict[str, Any]] = []
    for order_idx, (template_index, session) in enumerate(selected_sessions):
        template_day_offset = session.get("day_offset")
        if isinstance(template_day_offset, int):
            session_date = week_start + timedelta(days=max(0, min(6, template_day_offset)))
        else:
            session_date = week_start + timedelta(days=order_idx * (7 // days_available))
        exercises: list[dict[str, Any]] = []
        for exercise in session.get("exercises", []):
            planned_exercise = _build_planned_exercise(
                exercise,
                history_index,
                equipment_set,
                is_deload_week=bool(deload["active"]),
                set_reduction_pct=set_reduction_pct,
                load_reduction_pct=load_reduction_pct,
                rule_set=rule_set,
                progression_state=progression_state_index.get(str(exercise.get("id") or "")),
                substitution_pressure=(
                    str(stimulus_fatigue_response.get("substitution_pressure"))
                    if isinstance(stimulus_fatigue_response, dict)
                    else None
                ),
                movement_restrictions=normalized_movement_restrictions,
            )
            if planned_exercise is not None:
                exercises.append(planned_exercise)

        if not exercises:
            continue
        cap_runtime = resolve_scheduler_session_exercise_cap(
            session_time_budget_minutes=session_time_budget_minutes,
            day_role=str(session.get("day_role") or "").strip() or None,
            slot_roles=[_exercise_slot_role(exercise) for exercise in exercises],
            rule_set=rule_set,
        )
        exercises = [
            exercise
            for index, exercise in enumerate(exercises)
            if index in set(cap_runtime["kept_indices"])
        ]

        planned_sessions.append(
            {
                "session_id": f"{program_template.get('id', 'template')}-{template_index + 1}",
                "title": session.get("name", f"Session {order_idx + 1}"),
                "day_role": session.get("day_role"),
                "date": session_date.isoformat(),
                "exercises": exercises,
                "exercise_cap_trace": dict(cap_runtime["decision_trace"]),
            }
        )

    weekly_volume_by_muscle, muscle_coverage = _compute_weekly_volume_and_coverage(
        planned_sessions,
        muscle_coverage_runtime=muscle_coverage_runtime,
    )

    return {
        "program_template_id": program_template.get("id", "template"),
        "split": split_preference,
        "phase": phase,
        "week_start": week_start.isoformat(),
        "user": {
            "name": user_profile.get("name"),
            "days_available": days_available,
        },
        "sessions": planned_sessions,
        "missed_day_policy": session_selection_runtime["missed_day_policy"],
        "missed_day_policy_trace": dict(session_selection_runtime["decision_trace"]),
        "session_selection_trace": dict(session_selection_runtime["decision_trace"]),
        "weekly_volume_by_muscle": weekly_volume_by_muscle,
        "muscle_coverage": muscle_coverage,
        "mesocycle": mesocycle,
        "deload": deload,
    }
