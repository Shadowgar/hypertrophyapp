"""Read-only completion from occurrence prescriptions and effective receipts.

No training policy, clock, persistence, or legacy identity inference lives here.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta
from typing import Any


def value(row: Any, key: str, default=None):
    return row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)


def working(row: Any) -> bool:
    return value(row, "parent_set_index") is None and (value(row, "set_kind") or "work").strip().lower() in {"work", "top", "backoff"}


def occurrence_coverage(session: dict, rows: list[Any]) -> dict:
    """Effective required work, independent of placement, lifecycle and query window."""
    required: set[tuple[str, int]] = set()
    slots: set[str] = set()
    known = bool(session.get("exercises"))
    for exercise in session.get("exercises") or []:
        slot, count = exercise.get("exercise_occurrence_id"), exercise.get("sets")
        if not slot or slot in slots or type(count) is not int or count <= 0:
            known = False
            continue
        slots.add(slot)
        prescribed = (exercise.get("authored_prescription") or {}).get("sets")
        indices = [item.get("set_index") for item in prescribed] if prescribed else list(range(1, count + 1))
        if (len(indices) != count or any(type(index) is not int or index < 1 for index in indices)
                or len(set(indices)) != count):
            known = False
            continue
        required.update((slot, index) for index in indices)
    recorded: set[tuple[str, int]] = set()
    for row in rows:
        if value(row, "voided_at") is not None:
            continue
        slot = value(row, "exercise_occurrence_id")
        if slot not in slots or (value(row, "workout_occurrence_id") is not None
                and value(row, "workout_occurrence_id") != session.get("workout_occurrence_id")):
            known = False
        if working(row):
            key = (slot, value(row, "set_index"))
            if key in recorded:
                known = False
            recorded.add(key)
    if recorded - required:
        known = False
    return {"known": known, "complete": known and required == recorded,
        "required": [list(key) for key in sorted(required)],
        "recorded": [list(key) for key in sorted(recorded, key=lambda key: (str(key[0]), str(key[1])))],
        "missing": [list(key) for key in sorted(required - recorded)],
        "working_sets_completed": len(required & recorded),
        "working_sets_planned": len(required) if known else None}


def _flexible_status(session: dict, rows: list[Any]) -> dict:
    coverage = occurrence_coverage(session, rows)
    state = session.get("execution_state")
    status = "unknown" if not coverage["known"] else (
        "ended_early" if state == "ended_early" else
        "complete" if state == "finished" and coverage["complete"] else
        "amended_incomplete" if state == "finished" else state or "unknown")
    return {"workout_occurrence_id": session["workout_occurrence_id"],
        "workout_id": session.get("session_id"), "title": session.get("title") or "Workout",
        "program_id": session.get("program_id"), "sequence_id": session["sequence_id"],
        "status": status, "execution_state": state,
        "coverage_status": "unknown" if not coverage["known"] else "complete" if coverage["complete"] else "incomplete",
        "working_sets_completed": coverage["working_sets_completed"],
        "working_sets_planned": coverage["working_sets_planned"], "missing": coverage["missing"],
        "actual_dates": list(session.get("actual_dates") or []),
        "advancement": deepcopy(session.get("advancement"))}


def calendar_statuses(plans: list[Any], rows: list[Any]) -> dict[str, dict]:
    sessions: dict[str, dict] = {}
    dated: dict[str, list[dict]] = defaultdict(list)
    coverage: dict[str, int] = defaultdict(int)
    for plan in plans:
        payload = value(plan, "payload", {}) or {}
        schedule = payload.get("schedule") or {}
        if schedule.get("mode") == "selected_dates_superseded_v1":
            continue
        try:
            monday = date.fromisoformat(schedule["week_start"])
            selected = [date.fromisoformat(day) for day in schedule["selected_dates"]]
            if (schedule.get("mode") == "selected_dates_v1" and monday.weekday() == 0 and schedule.get("timezone")
                    and selected and len(set(selected)) == len(selected)
                    and {str(day) for day in selected} == {str(item.get("scheduled_date") or item.get("date")) for item in payload.get("sessions", [])}
                    and all(monday <= day < monday + timedelta(days=7) for day in selected)):
                for offset in range(7):
                    coverage[str(monday + timedelta(days=offset))] += 1
        except (KeyError, TypeError, ValueError):
            pass
        for session in payload.get("sessions") or []:
            identity = session.get("workout_occurrence_id")
            if identity:
                sessions[identity] = {**session, "program_id": payload.get("program_template_id")}
            else:
                dated[str(session.get("scheduled_date") or session.get("date") or "")].append({
                    "workout_occurrence_id": "", "workout_id": session.get("session_id"),
                    "title": session.get("title") or "Unresolved planned workout",
                    "program_id": payload.get("program_template_id"), "status": "unknown",
                    "working_sets_completed": 0, "working_sets_planned": None,
                })
    by_occurrence: dict[str, list] = defaultdict(list)
    ambiguous_days: set[str] = set()
    ambiguous_occurrences: set[str] = set()
    activity: set[str] = set()
    for row in rows:
        if value(row, "voided_at") is not None:
            continue
        performed = value(row, "performed_date") or value(row, "created_at").date()
        day = str(performed)
        activity.add(day)
        identity = value(row, "workout_occurrence_id")
        if not identity or identity not in sessions:
            ambiguous_days.add(day)
        else:
            if sessions[identity].get("sequence_id"):
                by_occurrence[identity].append(row)
                continue
            planned_day = str(sessions[identity].get("scheduled_date") or sessions[identity].get("date") or "")
            if planned_day != day:
                ambiguous_days.update((day, planned_day))
                ambiguous_occurrences.add(identity)
            else:
                by_occurrence[identity].append(row)
    for identity, session in sessions.items():
        if session.get("sequence_id"):
            recorded = session.get("coverage_rows", by_occurrence.get(identity, []))
            entry = _flexible_status(session, recorded)
            actual_dates = session.get("actual_dates") or sorted({str(value(row, "performed_date") or value(row, "created_at").date()) for row in recorded})
            for day in session.get("projection_dates") or actual_dates:
                date_role = "performed_work" if day in actual_dates else (
                    "advancement" if day == (session.get("advancement") or {}).get("local_day") else "execution_context")
                dated[str(day)].append({**deepcopy(entry), "date_role": date_role})
            continue
        day = str(session.get("scheduled_date") or session.get("date") or "")
        expected: set[tuple[str, int]] = set()
        slots: set[str] = set()
        known = bool(session.get("exercises")) and identity not in ambiguous_occurrences
        for exercise in session.get("exercises") or []:
            slot, count = exercise.get("exercise_occurrence_id"), exercise.get("sets")
            if not slot or slot in slots or type(count) is not int or count <= 0:
                known = False
                continue
            slots.add(slot)
            expected.update((slot, index) for index in range(1, count + 1))
        recorded = by_occurrence.get(identity, [])
        actual = {(value(row, "exercise_occurrence_id"), value(row, "set_index")) for row in recorded if working(row)}
        if any(value(row, "exercise_occurrence_id") not in slots for row in recorded) or actual - expected:
            known = False
        completed = len(actual & expected)
        status = "unknown" if not known else "complete" if expected == actual else "partial" if recorded else "scheduled"
        dated[day].append({"workout_occurrence_id": identity, "workout_id": session.get("session_id"),
            "title": session.get("title") or "Scheduled workout", "program_id": session.get("program_id"),
            "status": status, "working_sets_completed": completed, "working_sets_planned": len(expected) if known else None})
    result = {}
    for day in set(dated) | set(coverage) | activity:
        occurrences = dated.get(day, [])
        statuses = {item["status"] for item in occurrences}
        if day in ambiguous_days or "unknown" in statuses or coverage.get(day, 0) > 1:
            status = "unknown"
        elif occurrences:
            status = "complete" if statuses == {"complete"} else "partial" if day in activity or any(item.get("sequence_id") for item in occurrences) else "scheduled"
        else:
            status = "rest" if coverage.get(day) == 1 else "unknown"
        required = [item.get("working_sets_planned") for item in occurrences]
        result[day] = {"status": status, "working_sets_completed": sum(item.get("working_sets_completed", 0) for item in occurrences),
            "working_sets_planned": sum(required) if required and all(v is not None for v in required) else None,
            "occurrences": occurrences}
    return result
