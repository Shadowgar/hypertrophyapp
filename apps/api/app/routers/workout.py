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


def _session_by_id(sessions: list[dict]) -> dict[str, dict]:
    return {
        session.get("session_id"): session
        for session in sessions
        if session.get("session_id")
    }


def _is_session_incomplete(db: Session, user_id: str, workout_id: str, session: dict) -> bool:
    planned_sets = sum(int(exercise.get("sets", 3)) for exercise in session.get("exercises", []))
    logged_sets = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == user_id,
            WorkoutSetLog.workout_id == workout_id,
        )
        .count()
    )
    return logged_sets < planned_sets


def _find_resume_session(db: Session, user_id: str, sessions: list[dict]) -> dict | None:
    session_by_id = _session_by_id(sessions)
    if not session_by_id:
        return None

    latest_log = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == user_id,
            WorkoutSetLog.workout_id.in_(list(session_by_id.keys())),
        )
        .order_by(WorkoutSetLog.created_at.desc())
        .first()
    )
    if not latest_log:
        return None

    candidate = session_by_id.get(latest_log.workout_id)
    if not candidate:
        return None

    if _is_session_incomplete(db, user_id, latest_log.workout_id, candidate):
        return candidate
    return None


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

    latest = plans[0].payload
    sessions = latest.get("sessions", [])
    selected = _find_resume_session(db, current_user.id, sessions)
    resume_selected = selected is not None

    if not selected:
        today = date.today().isoformat()
        selected = next((session for session in sessions if session.get("date") == today), None)
    if not selected and sessions:
        selected = sessions[0]

    if not selected:
        raise HTTPException(status_code=404, detail="No workouts available")

    for ex in selected.get("exercises", []):
        ex["warmups"] = compute_warmups(ex.get("recommended_working_weight", 20), 3)

    # Attach completed set counts per exercise for resume UI
    logs = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.workout_id == selected.get("session_id"),
        )
        .all()
    )
    completed_by_ex: dict[str, int] = {}
    for l in logs:
        # use highest set_index seen for the exercise
        prev = completed_by_ex.get(l.exercise_id, 0)
        if l.set_index > prev:
            completed_by_ex[l.exercise_id] = l.set_index

    for ex in selected.get("exercises", []):
        ex_id = ex.get("id")
        ex["completed_sets"] = completed_by_ex.get(ex_id, 0)

    selected["resume"] = resume_selected

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


@router.get("/workout/{workout_id}/progress")
def workout_progress(
    workout_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Return per-exercise completed sets and an overall percent complete."""
    # gather logs for this workout
    logs = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.workout_id == workout_id,
        )
        .all()
    )

    completed_by_ex: dict[str, int] = {}
    for l in logs:
        prev = completed_by_ex.get(l.exercise_id, 0)
        if l.set_index > prev:
            completed_by_ex[l.exercise_id] = l.set_index

    # try to find the plan session to calculate planned sets
    plans = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == current_user.id)
        .order_by(WorkoutPlan.created_at.desc())
        .all()
    )
    planned_total = 0
    exercises_info: list[dict] = []
    if plans:
        latest = plans[0].payload
        sessions = latest.get("sessions", [])
        session = next((s for s in sessions if s.get("session_id") == workout_id), None)
        if session:
            for ex in session.get("exercises", []):
                planned_sets = int(ex.get("sets", 3))
                planned_total += planned_sets
                exercises_info.append({
                    "exercise_id": ex.get("id"),
                    "planned_sets": planned_sets,
                    "completed_sets": completed_by_ex.get(ex.get("id"), 0),
                })

    completed_total = sum(completed_by_ex.values())
    percent = 0
    if planned_total > 0:
        percent = int((completed_total / planned_total) * 100)

    return {
        "workout_id": workout_id,
        "completed_total": completed_total,
        "planned_total": planned_total,
        "percent_complete": percent,
        "exercises": exercises_info,
    }
