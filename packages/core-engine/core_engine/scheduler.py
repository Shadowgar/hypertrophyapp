from datetime import date, timedelta
from typing import Any
import re

from .equipment import resolve_equipment_tags


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
_MIN_SETS_PER_MUSCLE = 2


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


def _build_equipment_set(available_equipment: list[str] | None) -> set[str]:
    return {item.lower() for item in (available_equipment or []) if item}


def _is_equipment_compatible(tags: list[str], equipment_set: set[str]) -> bool:
    if not equipment_set:
        return True
    if not tags:
        return True
    return bool(equipment_set.intersection({tag.lower() for tag in tags}))


def _prefilter_substitutions(candidates: list[str], equipment_set: set[str]) -> list[str]:
    if not candidates:
        return []
    if not equipment_set:
        return candidates

    filtered: list[str] = []
    for candidate in candidates:
        candidate_tags = resolve_equipment_tags(exercise_name=candidate, explicit_tags=None)
        if _is_equipment_compatible(candidate_tags, equipment_set):
            filtered.append(candidate)
    return filtered


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "exercise"


def _build_planned_exercise(
    exercise: dict[str, Any],
    history_index: dict[str, dict[str, Any]],
    equipment_set: set[str],
    soreness_by_muscle: dict[str, str],
) -> dict[str, Any] | None:
    resolved_equipment_tags = resolve_equipment_tags(
        exercise_name=exercise.get("name", ""),
        explicit_tags=exercise.get("equipment_tags"),
    )
    previous = history_index.get(exercise.get("id"), {})
    recommended = float(previous.get("next_working_weight") or exercise.get("start_weight", 20))
    soreness_severity = _resolve_exercise_soreness(exercise, soreness_by_muscle)
    recommended = _apply_soreness_modifier(recommended, soreness_severity)
    substitutions = exercise.get("substitution_candidates") or exercise.get("substitutions") or []
    compatible_substitutions = _prefilter_substitutions(substitutions, equipment_set)

    planned_id = exercise.get("id")
    planned_name = exercise.get("name")
    if not _is_equipment_compatible(resolved_equipment_tags, equipment_set):
        if not compatible_substitutions:
            return None
        planned_name = compatible_substitutions[0]
        planned_id = _slugify(planned_name)

    return {
        "id": planned_id,
        "primary_exercise_id": exercise.get("primary_exercise_id") or exercise.get("id"),
        "name": planned_name,
        "sets": exercise.get("sets", 3),
        "rep_range": exercise.get("rep_range", [8, 12]),
        "recommended_working_weight": recommended,
        "priority": exercise.get("priority", "standard"),
        "movement_pattern": exercise.get("movement_pattern"),
        "primary_muscles": exercise.get("primary_muscles", []),
        "substitution_candidates": compatible_substitutions,
        "notes": exercise.get("notes"),
        "video": exercise.get("video"),
        "equipment_tags": resolved_equipment_tags,
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


def _select_sessions_for_days(base_sessions: list[dict[str, Any]], days_available: int) -> list[tuple[int, dict[str, Any]]]:
    if days_available >= len(base_sessions):
        return list(enumerate(base_sessions))

    selected_indices = _normalize_indices(
        _spread_indices(len(base_sessions), days_available),
        len(base_sessions),
        days_available,
    )
    return [(index, base_sessions[index]) for index in selected_indices]


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
) -> dict[str, Any]:
    days_available = max(2, min(7, days_available))
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    base_sessions = program_template.get("sessions", [])
    selected_sessions = _select_sessions_for_days(base_sessions, days_available)

    history_index = {
        item.get("exercise_id"): item for item in history if item.get("exercise_id")
    }
    equipment_set = _build_equipment_set(available_equipment)
    normalized_soreness = _normalize_soreness_by_muscle(soreness_by_muscle)

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
            )
            if planned_exercise is not None:
                exercises.append(planned_exercise)

        if not exercises:
            continue

        planned_sessions.append(
            {
                "session_id": f"{program_template.get('id', 'template')}-{template_index + 1}",
                "title": session.get("name", f"Session {order_idx + 1}"),
                "date": session_date.isoformat(),
                "exercises": exercises,
            }
        )

    weekly_volume_by_muscle, muscle_coverage = _compute_weekly_volume_and_coverage(planned_sessions)

    return {
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
    }
