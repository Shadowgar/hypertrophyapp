from datetime import date, timedelta
from typing import Any

from .equipment import resolve_equipment_tags


def generate_week_plan(
    user_profile: dict[str, Any],
    days_available: int,
    split_preference: str,
    program_template: dict[str, Any],
    history: list[dict[str, Any]],
    phase: str,
) -> dict[str, Any]:
    days_available = max(2, min(4, days_available))
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    base_sessions = program_template.get("sessions", [])
    selected_sessions = base_sessions[:days_available]

    history_index = {
        item.get("exercise_id"): item for item in history if item.get("exercise_id")
    }

    planned_sessions: list[dict[str, Any]] = []
    for idx, session in enumerate(selected_sessions):
        session_date = week_start + timedelta(days=idx * (7 // days_available))
        exercises = []
        for ex in session.get("exercises", []):
            prev = history_index.get(ex.get("id"), {})
            recommended = prev.get("next_working_weight") or ex.get("start_weight", 20)
            substitutions = ex.get("substitution_candidates") or ex.get("substitutions") or []
            primary_exercise_id = ex.get("primary_exercise_id") or ex.get("id")
            exercises.append(
                {
                    "id": ex.get("id"),
                    "primary_exercise_id": primary_exercise_id,
                    "name": ex.get("name"),
                    "sets": ex.get("sets", 3),
                    "rep_range": ex.get("rep_range", [8, 12]),
                    "recommended_working_weight": recommended,
                    "priority": ex.get("priority", "standard"),
                    "movement_pattern": ex.get("movement_pattern"),
                    "primary_muscles": ex.get("primary_muscles", []),
                    "substitution_candidates": substitutions,
                    "notes": ex.get("notes"),
                    "video": ex.get("video"),
                    "equipment_tags": resolve_equipment_tags(
                        exercise_name=ex.get("name", ""),
                        explicit_tags=ex.get("equipment_tags"),
                    ),
                }
            )

        planned_sessions.append(
            {
                "session_id": f"{program_template.get('id', 'template')}-{idx + 1}",
                "title": session.get("name", f"Session {idx + 1}"),
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
