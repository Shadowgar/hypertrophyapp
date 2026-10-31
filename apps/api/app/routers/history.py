from copy import deepcopy
from types import SimpleNamespace
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from core_engine import build_history_analytics, build_history_calendar, build_history_day_detail
from core_engine.history_status import calendar_statuses
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..history_dates import performed_log_rows
from ..selected_date_plans import local_week
from ..deps import get_current_user
from ..models import BodyMeasurementEntry, User, WeeklyCheckin, WorkoutOccurrence, WorkoutPlan
from ..program_loader import resolve_administered_program_id
from ..workout_identity import identified_sessions

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _visible_history_plans(db: Session, user_id: str, limit: int) -> list[WorkoutPlan]:
    """Retained unstarted replacements are provenance, not active planned work."""
    mode = WorkoutPlan.payload["schedule"]["mode"].as_string()
    return (db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id,
        func.coalesce(mode, "") != "selected_dates_superseded_v1")
        .order_by(WorkoutPlan.created_at.desc()).limit(limit).all())


def _history_projection_plans(db: Session, user_id: str, start: date, end: date, rows: list[dict]) -> list:
    """Owner-bound immutable execution snapshots override replaceable plan views."""
    plans = _visible_history_plans(db, user_id, 24)
    referenced = {row["workout_occurrence_id"] for row in rows if row.get("workout_occurrence_id")}
    snapshots = {row.id: row for row in db.query(WorkoutOccurrence).filter(
        WorkoutOccurrence.user_id == user_id,
        or_(WorkoutOccurrence.scheduled_date.between(start, end), WorkoutOccurrence.id.in_(referenced),
            and_(WorkoutOccurrence.sequence_id.is_not(None), or_(
                WorkoutOccurrence.advancement["local_day"].as_string().between(str(start), str(end)),
                WorkoutOccurrence.execution_context["local_day"].as_string().between(str(start), str(end))))),
    ).all()}
    projected = [SimpleNamespace(payload={**deepcopy(plan.payload), "sessions": identified_sessions(plan, snapshots)}) for plan in plans]
    included = {session["workout_occurrence_id"] for plan in projected for session in plan.payload["sessions"]}
    flexible_ids = {identity for identity, occurrence in snapshots.items() if occurrence.sequence_id}
    # Coverage is lifetime evidence for these exact owned occurrences; activity
    # counts retain the caller's date window and never use these extra rows.
    coverage_rows = performed_log_rows(db, user_id=user_id, occurrence_ids=flexible_ids) if flexible_ids else []
    by_occurrence: dict[str, list[dict]] = {}
    for row in coverage_rows:
        by_occurrence.setdefault(row["workout_occurrence_id"], []).append(row)
    for identity, occurrence in snapshots.items():
        if identity in included:
            continue
        session = deepcopy(occurrence.payload)
        session["workout_occurrence_id"] = identity
        if occurrence.sequence_id:
            effective_rows = by_occurrence.get(identity, [])
            actual_dates = {row["performed_date"].isoformat() for row in effective_rows}
            projection_dates = set(actual_dates)
            for context in (occurrence.advancement, occurrence.execution_context):
                day = (context or {}).get("local_day")
                if day:
                    projection_dates.add(day)
            session.pop("scheduled_date", None)
            session.update(sequence_id=occurrence.sequence_id, execution_state=occurrence.execution_state,
                advancement=deepcopy(occurrence.advancement), actual_dates=sorted(actual_dates),
                projection_dates=sorted(projection_dates), coverage_rows=effective_rows)
            for day in sorted(projection_dates):
                if str(start) <= day <= str(end):
                    projected.append(SimpleNamespace(payload={"program_template_id": occurrence.program_id,
                        "sessions": [{**session, "date": day}]}))
            continue
        if occurrence.scheduled_date:
            session["date"] = session["scheduled_date"] = occurrence.scheduled_date.isoformat()
        projected.append(SimpleNamespace(payload={"program_template_id": occurrence.program_id, "sessions": [session]}))
    return projected


_PROGRAM_ID_SCALAR_KEYS = {
    "program_id",
    "template_id",
    "current_program_id",
    "recommended_program_id",
}
_PROGRAM_ID_LIST_KEYS = {
    "program_ids",
    "compatible_program_ids",
}


def _monday_of(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _history_today(user: User) -> date:
    if user.scheduling_timezone:
        return local_week(user.scheduling_timezone, datetime.now(UTC))[0]
    return date.today()


def _normalize_program_identity_payload(value: Any, *, key_hint: str | None = None) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if key in _PROGRAM_ID_SCALAR_KEYS and isinstance(item, str):
                normalized[key] = resolve_administered_program_id(item) or item
                continue
            if key in _PROGRAM_ID_LIST_KEYS and isinstance(item, list):
                collapsed: list[str] = []
                for candidate in item:
                    if not isinstance(candidate, str):
                        continue
                    resolved = resolve_administered_program_id(candidate) or candidate
                    if resolved not in collapsed:
                        collapsed.append(resolved)
                normalized[key] = collapsed
                continue
            normalized[key] = _normalize_program_identity_payload(item, key_hint=key)
        return normalized
    if isinstance(value, list):
        return [_normalize_program_identity_payload(item, key_hint=key_hint) for item in value]
    return value


@router.get("/history/exercise/{exercise_id}")
def get_exercise_history(
    exercise_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    rows = performed_log_rows(db, user_id=current_user.id, exercise_id=exercise_id,
        descending=True, limit=50)
    history = [
        {
            "id": row['id'],
            "primary_exercise_id": row['primary_exercise_id'],
            "workout_occurrence_id": row['workout_occurrence_id'],
            "exercise_occurrence_id": row['exercise_occurrence_id'],
            "source_lineage": (row['replay_context'] or {}).get("planned_exercise", {}).get("source_lineage"),
            "performed_variant": (row['replay_context'] or {}).get("planned_exercise", {}).get("performed_variant"),
            "substitution_consent": (row['replay_context'] or {}).get("planned_exercise", {}).get("substitution_consent"),
            "reps": row['reps'],
            "weight": row['weight'],
            "set_index": row['set_index'],
            "created_at": row['created_at'].isoformat(),
            "performed_date": row['performed_date'].isoformat(),
            "performed_date_source": row["performed_date_source"],
            **({"performed_timezone": row["performed_timezone"], "execution_context_id": row["execution_context_id"]}
               if row["performed_local_date"] is not None else {}),
        }
        for row in rows
    ]
    return {"exercise_id": exercise_id, "history": history}


@router.get("/history/weekly-checkins")
def get_weekly_checkin_history(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = 12,
) -> dict:
    capped_limit = max(1, min(52, int(limit)))
    rows = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.user_id == current_user.id)
        .order_by(WeeklyCheckin.week_start.desc())
        .limit(capped_limit)
        .all()
    )
    entries = [
        {
            "week_start": row.week_start.isoformat(),
            "body_weight": float(row.body_weight),
            "adherence_score": int(row.adherence_score),
            "notes": row.notes,
            "created_at": row.created_at.isoformat(),
        }
        for row in reversed(rows)
    ]
    return {"entries": entries}


@router.get("/history/analytics")
def get_history_analytics(
    db: DbSession,
    current_user: CurrentUser,
    limit_weeks: int = 8,
    checkin_limit: int = 24,
) -> dict[str, Any]:
    capped_weeks = max(2, min(26, int(limit_weeks)))
    capped_checkin_limit = max(4, min(52, int(checkin_limit)))
    today = _history_today(current_user)
    start_date = _monday_of(today) - timedelta(days=(capped_weeks - 1) * 7)

    checkin_rows = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.user_id == current_user.id)
        .order_by(WeeklyCheckin.week_start.desc())
        .limit(capped_checkin_limit)
        .all()
    )

    log_rows = performed_log_rows(db, user_id=current_user.id, start_date=start_date, end_date=today)

    measurement_rows = (
        db.query(BodyMeasurementEntry)
        .filter(
            BodyMeasurementEntry.user_id == current_user.id,
            BodyMeasurementEntry.measured_on >= start_date,
        )
        .order_by(BodyMeasurementEntry.measured_on.asc(), BodyMeasurementEntry.created_at.asc())
        .all()
    )

    payload = build_history_analytics(
        checkin_rows=checkin_rows,
        log_rows=log_rows,
        measurement_rows=measurement_rows,
        limit_weeks=capped_weeks,
        checkin_limit=capped_checkin_limit,
        today=today,
    )
    return _normalize_program_identity_payload(payload)


@router.get("/history/calendar")
def get_history_calendar(
    db: DbSession,
    current_user: CurrentUser,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    today = _history_today(current_user)
    resolved_end = end_date or today
    resolved_start = start_date or (resolved_end - timedelta(days=27))

    if resolved_start > resolved_end:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    if (resolved_end - resolved_start).days > 180:
        raise HTTPException(status_code=400, detail="date window too large (max 180 days)")

    rows = performed_log_rows(db, user_id=current_user.id, start_date=resolved_start, end_date=resolved_end)
    rows_until_end = performed_log_rows(db, user_id=current_user.id, end_date=resolved_end)

    plans = _history_projection_plans(db, current_user.id, resolved_start, resolved_end, rows)
    payload = build_history_calendar(
        log_rows=rows,
        all_log_rows_until_end=rows_until_end,
        plans=plans,
        start_date=resolved_start,
        end_date=resolved_end,
        today=today,
    )
    return _normalize_program_identity_payload(payload)


@router.get("/history/day/{day}")
def get_history_day_detail(
    day: date,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    rows = performed_log_rows(db, user_id=current_user.id, start_date=day, end_date=day)

    plans = _history_projection_plans(db, current_user.id, day, day, rows)
    payload = build_history_day_detail(day=day, log_rows=rows, plans=plans)
    statuses = {item["workout_occurrence_id"]: item
        for item in calendar_statuses(plans, rows).get(day.isoformat(), {}).get("occurrences", [])
        if item.get("sequence_id")}
    receipt_dates = {row["id"]: row for row in rows}
    for workout in payload["workouts"]:
        status = statuses.get(workout.get("workout_occurrence_id"))
        if status:
            workout.update(status)
        for exercise in workout["exercises"]:
            for receipt in exercise["sets"]:
                row = receipt_dates[receipt["id"]]
                receipt.update(performed_date=row["performed_date"].isoformat(),
                    performed_date_source=row["performed_date_source"])
                if row["performed_local_date"] is not None:
                    receipt.update(performed_timezone=row["performed_timezone"], execution_context_id=row["execution_context_id"])
    return _normalize_program_identity_payload(payload)
