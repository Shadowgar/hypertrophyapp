from datetime import date, datetime, time, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from core_engine import build_history_analytics, build_history_calendar, build_history_day_detail
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import BodyMeasurementEntry, User, WeeklyCheckin, WorkoutPlan, WorkoutSetLog
from ..program_loader import resolve_administered_program_id

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

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


def _date_window(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    start_datetime = datetime.combine(start_date, time.min)
    end_datetime = datetime.combine(end_date + timedelta(days=1), time.min)
    return start_datetime, end_datetime


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
    rows = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.exercise_id == exercise_id,
        )
        .order_by(WorkoutSetLog.created_at.desc())
        .limit(50)
        .all()
    )
    history = [
        {
            "id": row.id,
            "primary_exercise_id": row.primary_exercise_id,
            "reps": row.reps,
            "weight": row.weight,
            "set_index": row.set_index,
            "created_at": row.created_at.isoformat(),
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
    start_date = _monday_of(date.today()) - timedelta(days=(capped_weeks - 1) * 7)
    start_datetime = datetime.combine(start_date, time.min)

    checkin_rows = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.user_id == current_user.id)
        .order_by(WeeklyCheckin.week_start.desc())
        .limit(capped_checkin_limit)
        .all()
    )

    log_rows = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.created_at >= start_datetime,
        )
        .order_by(WorkoutSetLog.created_at.asc())
        .all()
    )

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
    )
    return _normalize_program_identity_payload(payload)


@router.get("/history/calendar")
def get_history_calendar(
    db: DbSession,
    current_user: CurrentUser,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    today = date.today()
    resolved_end = end_date or today
    resolved_start = start_date or (resolved_end - timedelta(days=27))

    if resolved_start > resolved_end:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    if (resolved_end - resolved_start).days > 180:
        raise HTTPException(status_code=400, detail="date window too large (max 180 days)")

    start_dt, end_dt = _date_window(resolved_start, resolved_end)

    rows = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.created_at >= start_dt,
            WorkoutSetLog.created_at < end_dt,
        )
        .order_by(WorkoutSetLog.created_at.asc())
        .all()
    )

    rows_until_end = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.created_at < end_dt,
        )
        .order_by(WorkoutSetLog.created_at.asc())
        .all()
    )

    plans = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == current_user.id)
        .order_by(WorkoutPlan.created_at.desc())
        .limit(24)
        .all()
    )
    payload = build_history_calendar(
        log_rows=rows,
        all_log_rows_until_end=rows_until_end,
        plans=plans,
        start_date=resolved_start,
        end_date=resolved_end,
    )
    return _normalize_program_identity_payload(payload)


@router.get("/history/day/{day}")
def get_history_day_detail(
    day: date,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    start_dt, end_dt = _date_window(day, day)
    rows = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.created_at >= start_dt,
            WorkoutSetLog.created_at < end_dt,
        )
        .order_by(WorkoutSetLog.created_at.asc(), WorkoutSetLog.set_index.asc())
        .all()
    )

    plans = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == current_user.id)
        .order_by(WorkoutPlan.created_at.desc())
        .limit(12)
        .all()
    )
    payload = build_history_day_detail(day=day, log_rows=rows, plans=plans)
    return _normalize_program_identity_payload(payload)
