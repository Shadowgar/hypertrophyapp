from datetime import date, timedelta
from typing import Any
import re

from .equipment import resolve_equipment_tags


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
) -> dict[str, Any] | None:
    resolved_equipment_tags = resolve_equipment_tags(
        exercise_name=exercise.get("name", ""),
        explicit_tags=exercise.get("equipment_tags"),
    )
    previous = history_index.get(exercise.get("id"), {})
    recommended = previous.get("next_working_weight") or exercise.get("start_weight", 20)
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


def generate_week_plan(
    user_profile: dict[str, Any],
    days_available: int,
    split_preference: str,
    program_template: dict[str, Any],
    history: list[dict[str, Any]],
    phase: str,
    available_equipment: list[str] | None = None,
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

    planned_sessions: list[dict[str, Any]] = []
    for order_idx, (template_index, session) in enumerate(selected_sessions):
        template_day_offset = session.get("day_offset")
        if isinstance(template_day_offset, int):
            session_date = week_start + timedelta(days=max(0, min(6, template_day_offset)))
        else:
            session_date = week_start + timedelta(days=order_idx * (7 // days_available))
        exercises: list[dict[str, Any]] = []
        for exercise in session.get("exercises", []):
            planned_exercise = _build_planned_exercise(exercise, history_index, equipment_set)
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
    }
