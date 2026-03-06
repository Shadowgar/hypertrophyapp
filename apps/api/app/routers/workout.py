from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core_engine import compute_warmups, update_exercise_state_after_workout
from core_engine.progression import ExerciseState as EngineExerciseState

from ..database import get_db
from ..deps import get_current_user
from ..models import ExerciseState, User, WorkoutPlan, WorkoutSessionState, WorkoutSetLog
from ..schemas import (
    WorkoutExerciseSummaryResponse,
    WorkoutLiveRecommendationResponse,
    WorkoutSetLogRequest,
    WorkoutSetLogResponse,
    WorkoutSummaryResponse,
)
from ..stoic_quotes import daily_stoic_quote

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

IN_SESSION_WEIGHT_SCALE_UP = 1.025
IN_SESSION_WEIGHT_SCALE_DOWN_MILD = 0.975
IN_SESSION_WEIGHT_SCALE_DOWN_AGGRESSIVE = 0.95
IN_SESSION_WEIGHT_SCALE_MIN = 0.9
IN_SESSION_WEIGHT_SCALE_MAX = 1.05


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


def _find_planned_exercise(
    db: Session,
    user_id: str,
    workout_id: str,
    exercise_id: str,
) -> dict | None:
    plans = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.created_at.desc())
        .all()
    )
    for plan in plans:
        payload = plan.payload if isinstance(plan.payload, dict) else {}
        sessions = payload.get("sessions") or []
        session = next((item for item in sessions if item.get("session_id") == workout_id), None)
        if not session:
            continue
        exercises = session.get("exercises") or []
        return next((item for item in exercises if item.get("id") == exercise_id), None)
    return None


def _resolve_guidance(reps: int, min_reps: int, max_reps: int) -> str:
    if reps < min_reps:
        return "below_target_reps_reduce_or_hold_load"
    if reps > max_reps:
        return "above_target_reps_increase_load_next_exposure"
    return "within_target_reps_hold_or_microload"


def _round_to_microload(weight: float) -> float:
    return round(max(5.0, weight) / 2.5) * 2.5


def _bounded_weight_scale(scale: float) -> float:
    return max(IN_SESSION_WEIGHT_SCALE_MIN, min(IN_SESSION_WEIGHT_SCALE_MAX, scale))


def _build_live_recommendation(
    *,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_sets: int,
    completed_sets: int,
    last_reps: int,
    last_weight: float,
    average_reps: float,
) -> WorkoutLiveRecommendationResponse:
    remaining_sets = max(planned_sets - completed_sets, 0)
    reps_min = planned_reps_min
    reps_max = planned_reps_max
    guidance = "remaining_sets_hold_load_and_match_target_reps"
    scale = 1.0

    if remaining_sets <= 0:
        guidance = "session_complete_hold_load_for_next_exposure"
    elif last_reps < planned_reps_min or average_reps < planned_reps_min:
        guidance = "remaining_sets_reduce_load_focus_target_reps"
        scale = IN_SESSION_WEIGHT_SCALE_DOWN_AGGRESSIVE if completed_sets >= 2 else IN_SESSION_WEIGHT_SCALE_DOWN_MILD
        reps_max = min(planned_reps_max, planned_reps_min + 2)
    elif last_reps > planned_reps_max + 1 and average_reps >= planned_reps_max:
        guidance = "remaining_sets_increase_load_keep_reps_controlled"
        scale = IN_SESSION_WEIGHT_SCALE_UP
        reps_min = max(planned_reps_min, planned_reps_max - 2)

    recommended_weight = _round_to_microload(last_weight * _bounded_weight_scale(scale))

    return WorkoutLiveRecommendationResponse(
        completed_sets=completed_sets,
        remaining_sets=remaining_sets,
        recommended_reps_min=reps_min,
        recommended_reps_max=max(reps_min, reps_max),
        recommended_weight=recommended_weight,
        guidance=guidance,
    )


def _upsert_workout_session_state(
    *,
    db: Session,
    user_id: str,
    workout_id: str,
    primary_exercise_id: str,
    exercise_id: str,
    planned_sets: int,
    planned_reps_min: int,
    planned_reps_max: int,
    planned_weight: float,
    set_index: int,
    reps: int,
    weight: float,
) -> WorkoutLiveRecommendationResponse:
    state = (
        db.query(WorkoutSessionState)
        .filter(
            WorkoutSessionState.user_id == user_id,
            WorkoutSessionState.workout_id == workout_id,
            WorkoutSessionState.exercise_id == exercise_id,
        )
        .first()
    )

    if not state:
        state = WorkoutSessionState(
            user_id=user_id,
            workout_id=workout_id,
            primary_exercise_id=primary_exercise_id,
            exercise_id=exercise_id,
            planned_sets=planned_sets,
            planned_reps_min=planned_reps_min,
            planned_reps_max=planned_reps_max,
            planned_weight=planned_weight,
            completed_sets=0,
            total_logged_reps=0,
            total_logged_weight=0,
            set_history=[],
            remaining_sets=planned_sets,
            recommended_reps_min=planned_reps_min,
            recommended_reps_max=planned_reps_max,
            recommended_weight=planned_weight,
            last_guidance="remaining_sets_hold_load_and_match_target_reps",
        )

    history = list(state.set_history or [])
    next_entry = {
        "set_index": set_index,
        "reps": reps,
        "weight": float(weight),
    }
    replaced = False
    for idx, item in enumerate(history):
        if int(item.get("set_index", -1)) == set_index:
            history[idx] = next_entry
            replaced = True
            break
    if not replaced:
        history.append(next_entry)
    history.sort(key=lambda row: int(row.get("set_index", 0)))

    completed_sets = min(planned_sets, len(history))
    total_reps = sum(int(item.get("reps", 0) or 0) for item in history)
    total_weight = sum(float(item.get("weight", 0) or 0) for item in history)
    average_reps = (total_reps / len(history)) if history else float(reps)

    live = _build_live_recommendation(
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_sets=planned_sets,
        completed_sets=completed_sets,
        last_reps=reps,
        last_weight=weight,
        average_reps=average_reps,
    )

    state.primary_exercise_id = primary_exercise_id
    state.planned_sets = planned_sets
    state.planned_reps_min = planned_reps_min
    state.planned_reps_max = planned_reps_max
    state.planned_weight = planned_weight
    state.completed_sets = live.completed_sets
    state.total_logged_reps = total_reps
    state.total_logged_weight = round(total_weight, 2)
    state.set_history = history
    state.remaining_sets = live.remaining_sets
    state.recommended_reps_min = live.recommended_reps_min
    state.recommended_reps_max = live.recommended_reps_max
    state.recommended_weight = live.recommended_weight
    state.last_guidance = live.guidance
    db.add(state)

    return live


def _find_planned_session(db: Session, user_id: str, workout_id: str) -> dict | None:
    plans = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.created_at.desc())
        .all()
    )
    for plan in plans:
        payload = plan.payload if isinstance(plan.payload, dict) else {}
        sessions = payload.get("sessions") or []
        session = next((item for item in sessions if item.get("session_id") == workout_id), None)
        if session:
            return session
    return None


def _group_logs_by_exercise(logs: list[WorkoutSetLog]) -> dict[str, list[WorkoutSetLog]]:
    grouped: dict[str, list[WorkoutSetLog]] = {}
    for item in logs:
        grouped.setdefault(item.exercise_id, []).append(item)
    for exercise_logs in grouped.values():
        exercise_logs.sort(key=lambda row: row.set_index)
    return grouped


def _resolve_summary_guidance(performed_sets: int, planned_sets: int, avg_reps: float, planned_min: int, planned_max: int) -> str:
    if performed_sets < planned_sets:
        return "incomplete_session_finish_remaining_sets_next_exposure"
    if avg_reps < planned_min:
        return "below_target_reps_reduce_or_hold_load"
    if avg_reps > planned_max:
        return "above_target_reps_increase_load_next_exposure"
    return "within_target_reps_hold_or_microload"


def _resolve_overall_summary_guidance(percent_complete: int, items: list[WorkoutExerciseSummaryResponse]) -> str:
    if percent_complete < 100:
        return "finish_all_planned_sets_for_reliable_progression"
    if any(item.guidance == "below_target_reps_reduce_or_hold_load" for item in items):
        return "performance_below_target_adjust_load_and_recover"
    if any(item.guidance == "above_target_reps_increase_load_next_exposure" for item in items):
        return "performance_above_target_progress_load"
    return "solid_execution_maintain_progression"


def _build_exercise_summary(
    *,
    db: Session,
    user_id: str,
    exercise: dict,
    exercise_logs: list[WorkoutSetLog],
) -> tuple[WorkoutExerciseSummaryResponse, int, int]:
    exercise_id = str(exercise.get("id") or "")
    planned_sets = int(exercise.get("sets", 3) or 3)
    rep_range = exercise.get("rep_range") or [8, 12]
    planned_min = int(rep_range[0]) if len(rep_range) > 0 else 8
    planned_max = int(rep_range[1]) if len(rep_range) > 1 else planned_min
    if planned_min > planned_max:
        planned_min, planned_max = planned_max, planned_min
    planned_weight = float(exercise.get("recommended_working_weight", 0) or 0)

    performed_sets = len(exercise_logs)
    if exercise_logs:
        avg_reps = sum(float(row.reps) for row in exercise_logs) / len(exercise_logs)
        avg_weight = sum(float(row.weight) for row in exercise_logs) / len(exercise_logs)
    else:
        avg_reps = 0.0
        avg_weight = 0.0

    completion_pct = int((performed_sets / max(planned_sets, 1)) * 100)
    rep_target_mid = (planned_min + planned_max) / 2
    rep_delta = round(avg_reps - rep_target_mid, 2) if performed_sets else round(-rep_target_mid, 2)
    weight_delta = round(avg_weight - planned_weight, 2) if performed_sets else round(-planned_weight, 2)

    primary_exercise_id = exercise.get("primary_exercise_id") or exercise_id
    state = (
        db.query(ExerciseState)
        .filter(
            ExerciseState.user_id == user_id,
            ExerciseState.exercise_id == primary_exercise_id,
        )
        .first()
    )
    next_weight = float(state.current_working_weight) if state else planned_weight
    guidance = _resolve_summary_guidance(performed_sets, planned_sets, avg_reps, planned_min, planned_max)

    return (
        WorkoutExerciseSummaryResponse(
            exercise_id=exercise_id,
            primary_exercise_id=exercise.get("primary_exercise_id"),
            name=str(exercise.get("name") or exercise_id),
            planned_sets=planned_sets,
            planned_reps_min=planned_min,
            planned_reps_max=planned_max,
            planned_weight=planned_weight,
            performed_sets=performed_sets,
            average_performed_reps=round(avg_reps, 2),
            average_performed_weight=round(avg_weight, 2),
            completion_pct=completion_pct,
            rep_delta=rep_delta,
            weight_delta=weight_delta,
            next_working_weight=round(next_weight, 2),
            guidance=guidance,
        ),
        planned_sets,
        performed_sets,
    )


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

    selected["mesocycle"] = latest.get("mesocycle")
    selected["deload"] = latest.get("deload")

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

    states = (
        db.query(WorkoutSessionState)
        .filter(
            WorkoutSessionState.user_id == current_user.id,
            WorkoutSessionState.workout_id == selected.get("session_id"),
        )
        .all()
    )
    state_by_exercise = {row.exercise_id: row for row in states}

    for ex in selected.get("exercises", []):
        ex_id = ex.get("id")
        state = state_by_exercise.get(ex_id)
        ex["completed_sets"] = int(state.completed_sets) if state else completed_by_ex.get(ex_id, 0)
        if state:
            ex["live_recommendation"] = {
                "completed_sets": int(state.completed_sets),
                "remaining_sets": int(state.remaining_sets),
                "recommended_reps_min": int(state.recommended_reps_min),
                "recommended_reps_max": int(state.recommended_reps_max),
                "recommended_weight": float(state.recommended_weight),
                "guidance": state.last_guidance,
            }

    selected["resume"] = resume_selected
    selected["daily_quote"] = daily_stoic_quote()

    return selected


@router.post("/workout/{workout_id}/log-set")
def log_set(
    workout_id: str,
    payload: WorkoutSetLogRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> WorkoutSetLogResponse:
    primary_exercise_id = payload.primary_exercise_id or payload.exercise_id
    planned_exercise = _find_planned_exercise(
        db,
        user_id=current_user.id,
        workout_id=workout_id,
        exercise_id=payload.exercise_id,
    )
    planned_rep_range_raw = (planned_exercise or {}).get("rep_range") or [8, 12]
    planned_reps_min = int(planned_rep_range_raw[0]) if len(planned_rep_range_raw) > 0 else 8
    planned_reps_max = int(planned_rep_range_raw[1]) if len(planned_rep_range_raw) > 1 else planned_reps_min
    if planned_reps_min > planned_reps_max:
        planned_reps_min, planned_reps_max = planned_reps_max, planned_reps_min
    planned_sets = int((planned_exercise or {}).get("sets", 3) or 3)
    planned_weight = float((planned_exercise or {}).get("recommended_working_weight", payload.weight) or payload.weight)

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
            current_working_weight=planned_weight,
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
        target_rep_range=(planned_reps_min, planned_reps_max),
        completed_sets=payload.set_index,
        planned_sets=planned_sets,
        phase_modifier=current_user.nutrition_phase or "maintenance",
    )

    state.current_working_weight = updated.current_working_weight
    state.exposure_count = updated.exposure_count
    state.fatigue_score = updated.fatigue_score

    live_recommendation = _upsert_workout_session_state(
        db=db,
        user_id=current_user.id,
        workout_id=workout_id,
        primary_exercise_id=primary_exercise_id,
        exercise_id=payload.exercise_id,
        planned_sets=planned_sets,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
        set_index=payload.set_index,
        reps=payload.reps,
        weight=payload.weight,
    )

    db.add(state)
    db.commit()
    db.refresh(record)

    rep_delta = 0
    if payload.reps > planned_reps_max:
        rep_delta = payload.reps - planned_reps_max
    elif payload.reps < planned_reps_min:
        rep_delta = payload.reps - planned_reps_min
    weight_delta = round(payload.weight - planned_weight, 2)
    guidance = _resolve_guidance(payload.reps, planned_reps_min, planned_reps_max)

    return WorkoutSetLogResponse(
        id=record.id,
        primary_exercise_id=record.primary_exercise_id,
        exercise_id=record.exercise_id,
        set_index=record.set_index,
        reps=record.reps,
        weight=record.weight,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
        rep_delta=rep_delta,
        weight_delta=weight_delta,
        next_working_weight=updated.current_working_weight,
        guidance=guidance,
        live_recommendation=live_recommendation,
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


@router.get(
    "/workout/{workout_id}/summary",
    responses={404: {"description": "Workout not found"}},
)
def workout_summary(
    workout_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> WorkoutSummaryResponse:
    session = _find_planned_session(db, current_user.id, workout_id)
    if not session:
        raise HTTPException(status_code=404, detail="Workout not found")

    logs = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.workout_id == workout_id,
        )
        .all()
    )

    logs_by_exercise = _group_logs_by_exercise(logs)

    summary_items: list[WorkoutExerciseSummaryResponse] = []
    planned_total = 0
    completed_total = 0

    for exercise in session.get("exercises", []):
        exercise_id = str(exercise.get("id") or "")
        if not exercise_id:
            continue
        item, item_planned_sets, item_completed_sets = _build_exercise_summary(
            db=db,
            user_id=current_user.id,
            exercise=exercise,
            exercise_logs=logs_by_exercise.get(exercise_id, []),
        )
        summary_items.append(item)
        planned_total += item_planned_sets
        completed_total += item_completed_sets

    percent_complete = int((completed_total / max(planned_total, 1)) * 100)
    overall_guidance = _resolve_overall_summary_guidance(percent_complete, summary_items)

    return WorkoutSummaryResponse(
        workout_id=workout_id,
        completed_total=completed_total,
        planned_total=planned_total,
        percent_complete=percent_complete,
        overall_guidance=overall_guidance,
        exercises=summary_items,
    )
