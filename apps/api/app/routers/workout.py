from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core_engine import compute_warmups, update_exercise_state_after_workout
from core_engine.progression import ExerciseState as EngineExerciseState

from ..database import get_db
from ..deps import get_current_user
from ..models import ExerciseState, User, WorkoutPlan, WorkoutSetLog
from ..schemas import WorkoutSetLogRequest, WorkoutSetLogResponse

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get(
    "/workout/today",
    responses={404: {"description": "No plan generated or no workouts available"}},
)
def workout_today(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    plans = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == current_user.id)
        .order_by(WorkoutPlan.created_at.desc())
        .all()
    )
    if not plans:
        raise HTTPException(status_code=404, detail="No plan generated")

    today = date.today().isoformat()
    latest = plans[0].payload
    sessions = latest.get("sessions", [])
    selected = next((session for session in sessions if session.get("date") == today), None)
    if not selected and sessions:
        selected = sessions[0]

    if not selected:
        raise HTTPException(status_code=404, detail="No workouts available")

    for ex in selected.get("exercises", []):
        ex["warmups"] = compute_warmups(ex.get("recommended_working_weight", 20), 3)

    return selected


@router.post("/workout/{workout_id}/log-set")
def log_set(
    workout_id: str,
    payload: WorkoutSetLogRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> WorkoutSetLogResponse:
    primary_exercise_id = payload.primary_exercise_id or payload.exercise_id

    record = WorkoutSetLog(
        user_id=current_user.id,
        workout_id=workout_id,
        primary_exercise_id=primary_exercise_id,
        exercise_id=payload.exercise_id,
        set_index=payload.set_index,
        reps=payload.reps,
        weight=payload.weight,
        rpe=payload.rpe,
    )
    db.add(record)

    state = (
        db.query(ExerciseState)
        .filter(
            ExerciseState.user_id == current_user.id,
            ExerciseState.exercise_id == primary_exercise_id,
        )
        .first()
    )
    if not state:
        state = ExerciseState(
            user_id=current_user.id,
            exercise_id=primary_exercise_id,
            current_working_weight=payload.weight,
            exposure_count=0,
            fatigue_score=0,
        )

    updated = update_exercise_state_after_workout(
        exercise_state=EngineExerciseState(
            exercise_id=primary_exercise_id,
            current_working_weight=state.current_working_weight,
            exposure_count=state.exposure_count,
            fatigue_score=state.fatigue_score,
        ),
        completed_reps=payload.reps,
        target_rep_range=(8, 12),
        completed_sets=payload.set_index,
        planned_sets=3,
        phase_modifier=current_user.nutrition_phase or "maintenance",
    )

    state.current_working_weight = updated.current_working_weight
    state.exposure_count = updated.exposure_count
    state.fatigue_score = updated.fatigue_score

    db.add(state)
    db.commit()
    db.refresh(record)

    return WorkoutSetLogResponse(
        id=record.id,
        primary_exercise_id=record.primary_exercise_id,
        exercise_id=record.exercise_id,
        reps=record.reps,
        weight=record.weight,
        created_at=record.created_at,
    )
