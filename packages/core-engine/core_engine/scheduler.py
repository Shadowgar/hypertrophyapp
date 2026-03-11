from datetime import date, timedelta
from typing import Any
import re
from copy import deepcopy

from .equipment import resolve_equipment_tags
from .rules_runtime import resolve_equipment_substitution, resolve_repeat_failure_substitution


_SORENESS_LEVEL_ORDER = {"none": 0, "mild": 1, "moderate": 2, "severe": 3}
_SORENESS_WEIGHT_FACTOR = {
    "none": 1.0,
    "mild": 1.0,
    "moderate": 0.975,
    "severe": 0.925,
}

_MUSCLE_ALIASES = {
    "chest": "chest",
    "pec": "chest",
    "pecs": "chest",
    "back": "back",
    "lats": "back",
    "lat": "back",
    "mid_back": "back",
    "upper_back": "back",
    "erectors": "back",
    "quads": "quads",
    "quadriceps": "quads",
    "hamstrings": "hamstrings",
    "glutes": "glutes",
    "shoulders": "shoulders",
    "delts": "shoulders",
    "front_delts": "shoulders",
    "rear_delts": "shoulders",
    "side_delts": "shoulders",
    "biceps": "biceps",
    "triceps": "triceps",
    "calves": "calves",
}

_TRACKED_MUSCLES = (
    "chest",
    "back",
    "quads",
    "hamstrings",
    "glutes",
    "shoulders",
    "biceps",
    "triceps",
    "calves",
)

_SLOT_ROLE_PRIORITY = {
    "primary_compound": 100,
    "weak_point": 90,
    "secondary_compound": 80,
    "accessory": 50,
    "isolation": 40,
}
_MIN_SETS_PER_MUSCLE = 2
_DAY_ROLE_PRIORITY = {
    "weak_point_arms": 100,
    "full_body_1": 80,
    "full_body_2": 80,
    "full_body_3": 80,
    "full_body_4": 80,
}


def _normalize_muscle_label(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^a-z]+", "_", value.strip().lower()).strip("_")
    return _MUSCLE_ALIASES.get(normalized)


def _token_mapped_muscles(name: str) -> set[str]:
    lowered = name.lower()
    mapped: set[str] = set()

    if any(token in lowered for token in ("bench", "chest", "pec", "fly", "press")):
        mapped.add("chest")
    if any(token in lowered for token in ("row", "pulldown", "pull up", "pull-up", "pullup", "lat")):
        mapped.add("back")
    if any(token in lowered for token in ("squat", "leg press", "lunge", "extension", "adductor")):
        mapped.add("quads")
    if any(token in lowered for token in ("rdl", "deadlift", "leg curl", "hamstring")):
        mapped.add("hamstrings")
    if any(token in lowered for token in ("glute", "hip thrust")):
        mapped.add("glutes")
    if any(token in lowered for token in ("shoulder", "delt", "lateral raise", "ohp", "overhead")):
        mapped.add("shoulders")
    if "curl" in lowered and "leg curl" not in lowered:
        mapped.add("biceps")
    if any(token in lowered for token in ("tricep", "pushdown", "skull crusher", "extension")):
        mapped.add("triceps")
    if "calf" in lowered:
        mapped.add("calves")

    return mapped


def _resolve_exercise_muscles(exercise: dict[str, Any]) -> set[str]:
    resolved: set[str] = set()

    for muscle in exercise.get("primary_muscles") or []:
        normalized = _normalize_muscle_label(muscle)
        if normalized:
            resolved.add(normalized)

    movement_pattern = exercise.get("movement_pattern")
    normalized_movement = _normalize_muscle_label(movement_pattern)
    if normalized_movement:
        resolved.add(normalized_movement)

    if not resolved:
        resolved.update(_token_mapped_muscles(exercise.get("name", "")))

    return resolved


def _normalize_soreness_by_muscle(soreness_by_muscle: dict[str, str] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for muscle, severity in (soreness_by_muscle or {}).items():
        normalized_muscle = _normalize_muscle_label(muscle)
        if not normalized_muscle:
            continue
        normalized_severity = (severity or "none").lower()
        if normalized_severity not in _SORENESS_LEVEL_ORDER:
            normalized_severity = "none"

        existing = normalized.get(normalized_muscle, "none")
        if _SORENESS_LEVEL_ORDER[normalized_severity] >= _SORENESS_LEVEL_ORDER[existing]:
            normalized[normalized_muscle] = normalized_severity

    return normalized


def _resolve_exercise_soreness(exercise: dict[str, Any], soreness_by_muscle: dict[str, str]) -> str:
    muscles = _resolve_exercise_muscles(exercise)
    if not muscles:
        return "none"

    severity = "none"
    for muscle in muscles:
        candidate = soreness_by_muscle.get(muscle, "none")
        if _SORENESS_LEVEL_ORDER[candidate] > _SORENESS_LEVEL_ORDER[severity]:
            severity = candidate

    return severity


def _apply_soreness_modifier(weight: float, severity: str) -> float:
    factor = _SORENESS_WEIGHT_FACTOR.get(severity, 1.0)
    adjusted = max(5.0, weight * factor)
    return round(adjusted / 2.5) * 2.5


def _normalize_percentage(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = fallback
    return max(0, min(100, parsed))


def _compute_mesocycle_state(
    program_template: dict[str, Any],
    phase: str,
    prior_generated_weeks: int,
    latest_adherence_score: int | None,
    severe_soreness_count: int,
    authored_week_index: int | None = None,
    authored_week_role: str | None = None,
    authored_sequence_length: int | None = None,
    authored_sequence_complete: bool = False,
    stimulus_fatigue_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    deload = program_template.get("deload") or {}
    base_trigger_weeks = max(1, int(deload.get("trigger_weeks", 6) or 6))
    if phase == "cut":
        trigger_weeks_effective = max(3, base_trigger_weeks - 1)
    else:
        trigger_weeks_effective = base_trigger_weeks

    weeks_completed_prior = max(0, int(prior_generated_weeks))
    week_index = (weeks_completed_prior % trigger_weeks_effective) + 1
    scheduled_deload = week_index == trigger_weeks_effective
    early_soreness = severe_soreness_count >= 2
    early_adherence = latest_adherence_score is not None and latest_adherence_score <= 2
    normalized_sfr = stimulus_fatigue_response if isinstance(stimulus_fatigue_response, dict) else {}
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
        "trigger_weeks_base": base_trigger_weeks,
        "trigger_weeks_effective": trigger_weeks_effective,
        "is_deload_week": bool(reasons),
        "deload_reason": "+".join(reasons) if reasons else "none",
        "early_triggers": {
            "severe_soreness": early_soreness,
            "low_adherence": early_adherence,
            "sfr_recovery": early_sfr_recovery,
        },
    }


def _apply_deload_modifiers(sets: int, weight: float, *, set_reduction_pct: int, load_reduction_pct: int) -> tuple[int, float]:
    adjusted_sets = max(1, int(round(sets * (100 - set_reduction_pct) / 100)))
    adjusted_weight = max(5.0, weight * (100 - load_reduction_pct) / 100)
    rounded_weight = round(adjusted_weight / 2.5) * 2.5
    return adjusted_sets, rounded_weight


def _merge_substitution_pressure(*pressures: str | None) -> str:
    rank = {"low": 0, "moderate": 1, "high": 2}
    resolved = "low"
    for pressure in pressures:
        normalized = str(pressure or "low").lower()
        if rank.get(normalized, 0) > rank[resolved]:
            resolved = normalized
    return resolved


def _resolve_exercise_recovery_pressure(
    progression_state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = progression_state if isinstance(progression_state, dict) else {}
    fatigue_score = max(0.0, min(1.0, float(state.get("fatigue_score") or 0.0)))
    failed_exposures = int(state.get("consecutive_under_target_exposures") or 0)
    last_action = str(state.get("last_progression_action") or "hold")

    if fatigue_score >= 0.8 and last_action == "reduce_load":
        return {
            "load_scale": 0.95,
            "set_delta": -1,
            "substitution_pressure": "high",
        }
    if fatigue_score >= 0.7 or failed_exposures >= 2 or last_action == "reduce_load":
        return {
            "load_scale": 0.95 if fatigue_score >= 0.7 or last_action == "reduce_load" else 1.0,
            "set_delta": 0,
            "substitution_pressure": "moderate",
        }
    return {
        "load_scale": 1.0,
        "set_delta": 0,
        "substitution_pressure": "low",
    }


def _build_equipment_set(available_equipment: list[str] | None) -> set[str]:
    return {item.lower() for item in (available_equipment or []) if item}


def _resolve_session_exercise_cap(session_time_budget_minutes: int | None) -> int | None:
    if session_time_budget_minutes is None:
        return None
    if session_time_budget_minutes <= 30:
        return 3
    if session_time_budget_minutes <= 45:
        return 4
    if session_time_budget_minutes <= 60:
        return 5
    return None


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


def _is_equipment_compatible(tags: list[str], equipment_set: set[str]) -> bool:
    if not equipment_set:
        return True
    if not tags:
        return True
    return bool(equipment_set.intersection({tag.lower() for tag in tags}))


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "exercise"


def _build_planned_exercise(
    exercise: dict[str, Any],
    history_index: dict[str, dict[str, Any]],
    equipment_set: set[str],
    soreness_by_muscle: dict[str, str],
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
    soreness_severity = _resolve_exercise_soreness(exercise, soreness_by_muscle)
    recommended = _apply_soreness_modifier(recommended, soreness_severity)
    planned_sets = int(exercise.get("sets", 3) or 3)
    if is_deload_week:
        planned_sets, recommended = _apply_deload_modifiers(
            planned_sets,
            recommended,
            set_reduction_pct=set_reduction_pct,
            load_reduction_pct=load_reduction_pct,
        )
    exercise_recovery_pressure = _resolve_exercise_recovery_pressure(progression_state)
    planned_sets = max(1, planned_sets + int(exercise_recovery_pressure["set_delta"]))
    recommended = max(5.0, recommended * float(exercise_recovery_pressure["load_scale"]))
    recommended = round(recommended / 2.5) * 2.5
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

    normalized_substitution_pressure = _merge_substitution_pressure(
        substitution_pressure,
        str(exercise_recovery_pressure["substitution_pressure"]),
    )
    substitution_guidance = None
    if compatible_substitutions:
        if normalized_substitution_pressure == "high":
            substitution_guidance = "prefer_compatible_variants_if_recovery_constraints_persist"
        elif normalized_substitution_pressure == "moderate":
            substitution_guidance = "compatible_variants_available_if_recovery_constraints_persist"

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
        "substitution_decision_trace": dict(substitution_runtime["decision_trace"]),
        "repeat_failure_substitution": repeat_failure_substitution,
        "notes": exercise.get("notes"),
        "video": planned_video,
        "equipment_tags": planned_equipment_tags,
        "slot_role": exercise.get("slot_role"),
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


def _select_sessions_evenly(base_sessions: list[dict[str, Any]], days_available: int) -> list[tuple[int, dict[str, Any]]]:
    selected_indices = _normalize_indices(
        _spread_indices(len(base_sessions), days_available),
        len(base_sessions),
        days_available,
    )
    return [(index, base_sessions[index]) for index in selected_indices]


def _history_exercise_key(history_item: dict[str, Any]) -> str | None:
    primary_exercise_id = str(history_item.get("primary_exercise_id") or "").strip()
    if primary_exercise_id:
        return primary_exercise_id

    exercise_id = str(history_item.get("exercise_id") or "").strip()
    return exercise_id or None


def _exercise_slot_role(exercise: dict[str, Any]) -> str:
    return str(exercise.get("slot_role") or "").strip().lower()


def _rank_structural_priority_exercises(base_sessions: list[dict[str, Any]], limit: int = 6) -> list[str]:
    ranked: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    ordinal = 0
    boosted_role_priority = {
        "weak_point": 120,
        "primary_compound": 110,
        "secondary_compound": 80,
    }
    for session in base_sessions:
        for exercise in session.get("exercises") or []:
            role = _exercise_slot_role(exercise)
            if role not in boosted_role_priority:
                continue
            exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
            if not exercise_id or exercise_id in seen:
                continue
            seen.add(exercise_id)
            ranked.append((boosted_role_priority[role], ordinal, exercise_id))
            ordinal += 1

    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [exercise_id for _, _, exercise_id in ranked[:limit]]


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

        # Favor recent exposures while preserving determinism.
        recency_weight = 1.0 + ((total - index - 1) / denominator)
        weighted_counts[exercise_key] = weighted_counts.get(exercise_key, 0.0) + recency_weight

    ranked = sorted(weighted_counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return [exercise_id for exercise_id, _ in ranked[:limit]]


def _session_profile(session: dict[str, Any]) -> tuple[set[str], set[str]]:
    primary_exercise_ids: set[str] = set()
    muscles: set[str] = set()

    for exercise in session.get("exercises") or []:
        primary_exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
        if primary_exercise_id:
            primary_exercise_ids.add(primary_exercise_id)
        muscles.update(_resolve_exercise_muscles(exercise))

    return primary_exercise_ids, muscles


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


def _select_capped_exercises(
    exercises: list[dict[str, Any]],
    limit: int,
    *,
    day_role: str | None = None,
) -> list[dict[str, Any]]:
    if limit >= len(exercises):
        return exercises

    role_priority = dict(_SLOT_ROLE_PRIORITY)
    if str(day_role or "").strip().lower() == "weak_point_arms":
        role_priority["weak_point"] = 120
        role_priority["primary_compound"] = 70
        role_priority["secondary_compound"] = 60

    ranked = sorted(
        enumerate(exercises),
        key=lambda item: (
            -role_priority.get(_exercise_slot_role(item[1]), 30),
            item[0],
        ),
    )
    kept_indexes = sorted(index for index, _ in ranked[:limit])
    return [exercise for index, exercise in enumerate(exercises) if index in kept_indexes]


def _priority_weight(exercise_ids: set[str], priority_weights: dict[str, int]) -> int:
    return sum(priority_weights.get(exercise_id, 0) for exercise_id in exercise_ids)


def _session_distance_score(index: int, selected_indices: list[int], total_sessions: int) -> float:
    if not selected_indices:
        return 0.0
    nearest_distance = min(abs(index - selected) for selected in selected_indices)
    return nearest_distance / max(1, total_sessions - 1)


def _select_sessions_with_continuity(
    base_sessions: list[dict[str, Any]],
    days_available: int,
    priority_targets: list[str],
) -> list[tuple[int, dict[str, Any]]]:
    priority_weights = {
        exercise_id: len(priority_targets) - index
        for index, exercise_id in enumerate(priority_targets)
    }

    session_profiles = [_session_profile(session) for session in base_sessions]
    if not any(_priority_weight(primary_ids, priority_weights) > 0 for primary_ids, _ in session_profiles):
        return _select_sessions_evenly(base_sessions, days_available)

    selected_indices: list[int] = []
    covered_priority: set[str] = set()
    covered_muscles: set[str] = set()

    # Preserve the first authored day as the block anchor and keep the explicit
    # weak-point / arms day when we compress a fuller authored week.
    required_indices: list[int] = []
    weak_point_index: int | None = None
    for index, session in enumerate(base_sessions):
        day_role = _session_day_role(session)
        if day_role == "weak_point_arms" and weak_point_index is None:
            weak_point_index = index

    if base_sessions:
        required_indices.append(0)
    if weak_point_index is not None and weak_point_index not in required_indices:
        required_indices.append(weak_point_index)

    for index in required_indices[:days_available]:
        if index in selected_indices:
            continue
        selected_indices.append(index)
        session_primary_ids, session_muscles = session_profiles[index]
        covered_priority.update(session_primary_ids)
        covered_muscles.update(session_muscles)

    while len(selected_indices) < days_available:
        best_index: int | None = None
        best_score: tuple[int, int, int, int, float] | None = None

        for index, (session_primary_ids, session_muscles) in enumerate(session_profiles):
            if index in selected_indices:
                continue

            new_priority_ids = session_primary_ids - covered_priority
            day_role = _session_day_role(base_sessions[index])
            score = (
                _priority_weight(new_priority_ids, priority_weights),
                _DAY_ROLE_PRIORITY.get(day_role, 0),
                len(session_muscles - covered_muscles),
                _priority_weight(session_primary_ids, priority_weights),
                len(session_muscles),
                _session_distance_score(index, selected_indices, len(base_sessions)),
            )

            if best_score is None or score > best_score or (score == best_score and index < best_index):
                best_index = index
                best_score = score

        if best_index is None:
            break

        selected_indices.append(best_index)
        session_primary_ids, session_muscles = session_profiles[best_index]
        covered_priority.update(session_primary_ids)
        covered_muscles.update(session_muscles)

    if len(selected_indices) != days_available:
        return _select_sessions_evenly(base_sessions, days_available)

    selected_indices.sort()
    return [(index, base_sessions[index]) for index in selected_indices]


def _select_sessions_for_days(
    base_sessions: list[dict[str, Any]],
    days_available: int,
    history: list[dict[str, Any]],
) -> list[tuple[int, dict[str, Any]]]:
    if days_available >= len(base_sessions):
        return list(enumerate(base_sessions))

    priority_targets = _rank_history_priority_exercises(history)
    if not priority_targets:
        priority_targets = _rank_structural_priority_exercises(base_sessions)
    if not priority_targets:
        selected = _select_sessions_evenly(base_sessions, days_available)
    else:
        selected = _select_sessions_with_continuity(base_sessions, days_available, priority_targets)

    return _merge_dropped_sessions_into_selected(base_sessions, selected)


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


def _compute_weekly_volume_and_coverage(planned_sessions: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, Any]]:
    volume_by_muscle = dict.fromkeys(_TRACKED_MUSCLES, 0)
    untracked_exercise_count = 0

    for session in planned_sessions:
        for exercise in session.get("exercises", []):
            resolved_muscles = _resolve_exercise_muscles(exercise)
            tracked_muscles = [muscle for muscle in resolved_muscles if muscle in volume_by_muscle]
            if not tracked_muscles:
                untracked_exercise_count += 1
                continue

            sets = int(exercise.get("sets", 0) or 0)
            for muscle in tracked_muscles:
                volume_by_muscle[muscle] += sets

    under_target_muscles = [
        muscle for muscle in _TRACKED_MUSCLES if volume_by_muscle[muscle] < _MIN_SETS_PER_MUSCLE
    ]
    covered_muscles = [
        muscle for muscle in _TRACKED_MUSCLES if volume_by_muscle[muscle] >= _MIN_SETS_PER_MUSCLE
    ]

    return volume_by_muscle, {
        "minimum_sets_per_muscle": _MIN_SETS_PER_MUSCLE,
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
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    days_available = max(2, min(7, days_available))
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    authored_week_runtime = _resolve_authored_week_runtime(program_template, prior_generated_weeks)
    base_sessions = list(authored_week_runtime.get("sessions") or [])
    selected_sessions = _select_sessions_for_days(base_sessions, days_available, history)

    history_index = {
        item.get("exercise_id"): item for item in history if item.get("exercise_id")
    }
    progression_state_index = {
        str(item.get("exercise_id")): item
        for item in (progression_state_per_exercise or [])
        if str(item.get("exercise_id") or "").strip()
    }
    equipment_set = _build_equipment_set(available_equipment)
    normalized_soreness = _normalize_soreness_by_muscle(soreness_by_muscle)
    normalized_movement_restrictions = _normalize_movement_restrictions(movement_restrictions)
    session_exercise_cap = _resolve_session_exercise_cap(session_time_budget_minutes)
    mesocycle = _compute_mesocycle_state(
        program_template=program_template,
        phase=phase,
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
    )

    deload_config = program_template.get("deload") or {}
    set_reduction_pct = _normalize_percentage(deload_config.get("set_reduction_pct"), 35)
    load_reduction_pct = _normalize_percentage(deload_config.get("load_reduction_pct"), 10)
    deload = {
        "active": mesocycle["is_deload_week"],
        "set_reduction_pct": set_reduction_pct,
        "load_reduction_pct": load_reduction_pct,
        "reason": mesocycle["deload_reason"],
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
                normalized_soreness,
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
        if session_exercise_cap is not None:
            exercises = _select_capped_exercises(
                exercises,
                session_exercise_cap,
                day_role=str(session.get("day_role") or "").strip() or None,
            )

        planned_sessions.append(
            {
                "session_id": f"{program_template.get('id', 'template')}-{template_index + 1}",
                "title": session.get("name", f"Session {order_idx + 1}"),
                "day_role": session.get("day_role"),
                "date": session_date.isoformat(),
                "exercises": exercises,
            }
        )

    weekly_volume_by_muscle, muscle_coverage = _compute_weekly_volume_and_coverage(planned_sessions)

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
        "missed_day_policy": "roll-forward-priority-lifts",
        "weekly_volume_by_muscle": weekly_volume_by_muscle,
        "muscle_coverage": muscle_coverage,
        "mesocycle": mesocycle,
        "deload": deload,
    }
