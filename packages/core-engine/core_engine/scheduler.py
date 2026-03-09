from datetime import date, timedelta
from typing import Any
import re

from .equipment import resolve_equipment_tags
from .rules_runtime import resolve_equipment_substitution


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

    reasons: list[str] = []
    if scheduled_deload:
        reasons.append("scheduled")
    if early_soreness:
        reasons.append("early_soreness")
    if early_adherence:
        reasons.append("early_adherence")

    return {
        "weeks_completed_prior": weeks_completed_prior,
        "week_index": week_index,
        "trigger_weeks_base": base_trigger_weeks,
        "trigger_weeks_effective": trigger_weeks_effective,
        "is_deload_week": bool(reasons),
        "deload_reason": "+".join(reasons) if reasons else "none",
        "early_triggers": {
            "severe_soreness": early_soreness,
            "low_adherence": early_adherence,
        },
    }


def _apply_deload_modifiers(sets: int, weight: float, *, set_reduction_pct: int, load_reduction_pct: int) -> tuple[int, float]:
    adjusted_sets = max(1, int(round(sets * (100 - set_reduction_pct) / 100)))
    adjusted_weight = max(5.0, weight * (100 - load_reduction_pct) / 100)
    rounded_weight = round(adjusted_weight / 2.5) * 2.5
    return adjusted_sets, rounded_weight


def _build_equipment_set(available_equipment: list[str] | None) -> set[str]:
    return {item.lower() for item in (available_equipment or []) if item}


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
) -> dict[str, Any] | None:
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
    substitutions = exercise.get("substitution_candidates") or exercise.get("substitutions") or []
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
    if not bool(substitution_runtime["decision_trace"]["outcome"]["original_compatible"]):
        if not compatible_substitutions:
            return None
        planned_name = str(substitution_runtime["selected_name"])
        planned_id = _slugify(planned_name)

    return {
        "id": planned_id,
        "primary_exercise_id": exercise.get("primary_exercise_id") or exercise.get("id"),
        "name": planned_name,
        "sets": planned_sets,
        "rep_range": exercise.get("rep_range", [8, 12]),
        "recommended_working_weight": recommended,
        "priority": exercise.get("priority", "standard"),
        "movement_pattern": exercise.get("movement_pattern"),
        "primary_muscles": exercise.get("primary_muscles", []),
        "substitution_candidates": compatible_substitutions,
        "substitution_decision_trace": dict(substitution_runtime["decision_trace"]),
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

    while len(selected_indices) < days_available:
        best_index: int | None = None
        best_score: tuple[int, int, int, int, float] | None = None

        for index, (session_primary_ids, session_muscles) in enumerate(session_profiles):
            if index in selected_indices:
                continue

            new_priority_ids = session_primary_ids - covered_priority
            score = (
                _priority_weight(new_priority_ids, priority_weights),
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
        return _select_sessions_evenly(base_sessions, days_available)

    return _select_sessions_with_continuity(base_sessions, days_available, priority_targets)


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
    rule_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    days_available = max(2, min(7, days_available))
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    base_sessions = program_template.get("sessions", [])
    selected_sessions = _select_sessions_for_days(base_sessions, days_available, history)

    history_index = {
        item.get("exercise_id"): item for item in history if item.get("exercise_id")
    }
    equipment_set = _build_equipment_set(available_equipment)
    normalized_soreness = _normalize_soreness_by_muscle(soreness_by_muscle)
    mesocycle = _compute_mesocycle_state(
        program_template=program_template,
        phase=phase,
        prior_generated_weeks=prior_generated_weeks,
        latest_adherence_score=latest_adherence_score,
        severe_soreness_count=severe_soreness_count,
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
