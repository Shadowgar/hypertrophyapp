from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, WorkoutSetLog

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
