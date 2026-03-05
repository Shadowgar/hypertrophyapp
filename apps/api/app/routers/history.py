from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, WeeklyCheckin, WorkoutSetLog

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


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
