"""Explicit local-week placement; this module never changes a prescription."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from hashlib import sha256
import json

from .authored_redistribution import AuthoredAllocationInfeasible, redistribute_authored_sessions


class SelectedDateError(ValueError):
    """The requested local dates cannot be used as a current-week schedule."""


@dataclass(frozen=True)
class SelectedWeek:
    week_start: date
    dates: tuple[date, ...]
    timezone: str
    local_today: date


def validate_selected_week(
    *, week_start: date, selected_dates: list[date], timezone: str,
    planning_instant: datetime,
) -> SelectedWeek:
    if planning_instant.tzinfo is None or planning_instant.utcoffset() is None:
        raise SelectedDateError("Planning instant must include a timezone")
    if not timezone or len(timezone) > 64:
        raise SelectedDateError("Select a valid IANA timezone")
    try:
        local_today = planning_instant.astimezone(ZoneInfo(timezone)).date()
    except (ZoneInfoNotFoundError, ValueError, KeyError) as exc:
        raise SelectedDateError("Select a valid IANA timezone") from exc
    current_monday = local_today - timedelta(days=local_today.weekday())
    if type(week_start) is not date or week_start != current_monday:
        raise SelectedDateError("Select dates in the current local Monday–Sunday week")
    if not 2 <= len(selected_dates) <= 5:
        raise SelectedDateError("Select 2–5 workout dates")
    if any(type(value) is not date for value in selected_dates):
        raise SelectedDateError("Workout dates must be local calendar dates")
    if len(set(selected_dates)) != len(selected_dates):
        raise SelectedDateError("Duplicate workout dates are not allowed")
    if any(value < week_start or value > week_start + timedelta(days=6) for value in selected_dates):
        raise SelectedDateError("Workout date is outside the selected local week")
    return SelectedWeek(week_start, tuple(sorted(selected_dates)), timezone, local_today)



def _neighbor_trace_summary(context):
    """Record only inputs used by spacing, without copying load or private prescription data."""
    if context is None:
        return None
    exercises = context.get("exercises")
    muscle_work = {}
    if exercises is not None:
        for exercise in exercises:
            for muscle in sorted(set(str(value).strip().lower() for value in exercise.get("primary_muscles") or [] if str(value).strip())):
                muscle_work[muscle] = muscle_work.get(muscle, 0) + int(exercise.get("sets") or 0)
    summary = {
        "date": context["date"].isoformat(),
        "working_sets": sum(int(exercise.get("sets") or 0) for exercise in exercises) if exercises is not None else None,
        "primary_muscle_working_sets": dict(sorted(muscle_work.items())) if exercises is not None else None,
        "unknown_primary_muscle_slot_count": sum(not exercise.get("primary_muscles") for exercise in exercises) if exercises is not None else None,
    }
    summary["context_digest"] = sha256(json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return summary


def place_on_selected_dates(
    plan: dict, selected: SelectedWeek, *, placement_revision: int,
    previous_date: date | None = None, next_date: date | None = None,
    previous_context: dict | None = None, next_context: dict | None = None,
    preserve_grouping: bool = False,
) -> dict:
    """Allocate complete ordered work to local dates, or retain frozen grouping on reschedule."""
    sessions = plan.get("sessions") or []
    if preserve_grouping and len(sessions) != len(selected.dates):
        raise SelectedDateError("Complete workout sessions cannot fit the selected date count")
    if placement_revision < 1:
        raise SelectedDateError("Placement revision must be positive")
    for side, context, explicit_date in (("previous", previous_context, previous_date), ("next", next_context, next_date)):
        if context is not None and explicit_date is not None and context.get("date") != explicit_date:
            raise SelectedDateError(f"Conflicting {side} neighbor date inputs")
    previous_context = previous_context if previous_context is not None else ({"date": previous_date} if previous_date is not None else None)
    next_context = next_context if next_context is not None else ({"date": next_date} if next_date is not None else None)
    adapted_days = [{**(sessions[index] if len(sessions) == len(selected.dates) else {}),
        "day_name": (sessions[index].get("name") if len(sessions) == len(selected.dates) else None)}
        for index in range(len(selected.dates))]
    try:
        allocated, allocation_trace = redistribute_authored_sessions(sessions, adapted_days,
            selected_dates=selected.dates, previous_context=previous_context, next_context=next_context,
            preserve_grouping=preserve_grouping)
    except AuthoredAllocationInfeasible as exc:
        raise SelectedDateError(str(exc)) from exc
    allocation = allocation_trace["selected_date_allocation"]
    previous_date = previous_context["date"] if previous_context is not None else None
    next_date = next_context["date"] if next_context is not None else None
    result = deepcopy(plan)
    if not preserve_grouping:
        projected = []
        for index, allocated_session in enumerate(allocated):
            source_session = sessions[index] if index < len(sessions) else {}
            # Same-count initial placement retains runtime metadata. Changed-count
            # allocation retains only the source template header/keys; execution
            # occurrence identities belong to the API's new-plan projection.
            metadata = deepcopy(source_session) if len(sessions) == len(allocated) else {
                key: deepcopy(source_session[key]) for key in ("session_id", "title", "session_index") if key in source_session
            }
            session = {**metadata, **allocated_session}
            session["session_id"] = source_session.get("session_id") or f"selected-date-{index + 1}"
            session["title"] = source_session.get("title") or source_session.get("name") or allocated_session["name"]
            session["session_index"] = source_session.get("session_index", index)
            projected.append(session)
        result["sessions"] = projected
    previous_schedule = result.get("schedule") if isinstance(result.get("schedule"), dict) else None
    history = list(previous_schedule.get("placement_history") or []) if previous_schedule else []
    if previous_schedule and previous_schedule.get("mode") == "selected_dates_v1":
        history.append({
            "placement_revision": previous_schedule.get("placement_revision"),
            "selected_dates": list(previous_schedule.get("selected_dates") or []),
            "timezone": previous_schedule.get("timezone"),
        })

    for session, scheduled_date in zip(result["sessions"], selected.dates, strict=True):
        session["date"] = scheduled_date.isoformat()
        session["scheduled_date"] = scheduled_date.isoformat()
        session["schedule_timezone"] = selected.timezone
        session["placement_revision"] = placement_revision

    neighboring = [previous_date, *selected.dates, next_date]
    gaps = [(right - left).days for left, right in zip(neighboring, neighboring[1:])
            if left is not None and right is not None]
    warnings = []
    if any(gap == 1 for gap in gaps):
        warnings.append("Consecutive workout dates leave no full rest day; review the workload.")
    if previous_date is None or next_date is None:
        warnings.append("Adjacent-week workout dates are unknown; cross-week spacing is not qualified.")
    elif "unknown" in allocation["context_completeness"].values():
        warnings.append("Adjacent-week workload context is unknown; cross-week spacing is not qualified.")
    warnings.append("Session duration is uncalibrated; working-set counts do not predict elapsed time.")
    if allocation["unknown_primary_muscle_slot_count"] or any(allocation["neighbor_unknown_primary_muscle_slot_counts"].values()):
        warnings.append("Some primary-muscle labels are unknown; overlap accounting is incomplete.")
    result["week_start"] = selected.week_start.isoformat()
    result["schedule"] = {
        "mode": "selected_dates_v1",
        "week_start": selected.week_start.isoformat(),
        "timezone": selected.timezone,
        "selected_dates": [value.isoformat() for value in selected.dates],
        "placement_revision": placement_revision,
        "placement_history": history,
        "spacing": {"gap_days": gaps, "warnings": warnings,
                    "previous_date": previous_date.isoformat() if previous_date else None,
                    "next_date": next_date.isoformat() if next_date else None},
        "decision_trace": {
            "owner": "core_engine.selected_date_scheduler",
            "version": "selected-dates-v1",
            "inputs": {"week_start": selected.week_start.isoformat(),
                       "timezone": selected.timezone,
                       "selected_dates": [value.isoformat() for value in selected.dates],
                       "previous_date": previous_date.isoformat() if previous_date else None,
                       "next_date": next_date.isoformat() if next_date else None,
                       "previous_context": _neighbor_trace_summary(previous_context),
                       "next_context": _neighbor_trace_summary(next_context)},
            "allocation": allocation,
            "source_digest": allocation["source_digest"],
            "rule_digest": allocation["rule_digest"],
            "spacing_policy": "consecutive-calendar-day advisory; hard minimum rest only where explicitly represented in source",
            "result": "placed_without_prescription_change",
            "workload": {"working_sets": allocation_trace["authored_redistributed_session_set_actuals"],
                "duration": "unknown; set counts alone do not establish session duration"},
            "limitations": ["Advisory overlap uses declared primary muscles only; missing labels remain unknown.",
                "Calendar gaps do not establish recovery or clinical safety."],
        },
    }
    return result
