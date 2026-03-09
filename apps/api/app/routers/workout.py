from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core_engine import (
    build_repeat_failure_substitution_payload,
    build_workout_log_set_payload,
    build_workout_performance_summary,
    build_workout_summary_progression_lookup_runtime,
    build_workout_session_state_defaults,
    build_workout_today_log_runtime,
    build_workout_today_payload,
    build_workout_today_plan_runtime,
    build_workout_today_progression_lookup_runtime,
    build_workout_today_session_state_payloads,
    build_workout_today_state_payloads,
    build_workout_progress_payload,
    interpret_workout_set_feedback,
    prepare_workout_session_state_persistence_payload,
    resolve_latest_logged_workout_resume_state,
    resolve_workout_log_set_plan_context,
    resolve_starting_load,
    resolve_workout_completion_per_exercise,
    resolve_workout_plan_reference,
    resolve_workout_today_session_selection,
    resolve_workout_session_state_update,
    update_exercise_state_after_workout,
)
from core_engine.progression import ExerciseState as EngineExerciseState

from ..database import get_db
from ..deps import get_current_user
from ..models import ExerciseState, User, WorkoutPlan, WorkoutSessionState, WorkoutSetLog
from ..program_loader import load_program_rule_set, resolve_linked_program_id
from ..schemas import (
    WorkoutLiveRecommendationResponse,
    WorkoutSetLogRequest,
    WorkoutSetLogResponse,
    WorkoutSummaryResponse,
)
from ..stoic_quotes import daily_stoic_quote

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _list_workout_plan_payloads(db: Session, user_id: str) -> list[dict]:
    plans = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.created_at.desc())
        .all()
    )
    return [plan.payload if isinstance(plan.payload, dict) else {} for plan in plans]


def _resolve_workout_plan_context(
    db: Session,
    user_id: str,
    workout_id: str,
    exercise_id: str | None = None,
) -> dict:
    reference = resolve_workout_plan_reference(
        plan_payloads=_list_workout_plan_payloads(db, user_id),
        workout_id=workout_id,
        exercise_id=exercise_id,
    )
    session = reference["session"]
    exercise = reference["exercise"]
    program_id = reference["program_id"]
    return {
        "session": session if isinstance(session, dict) else None,
        "exercise": exercise if isinstance(exercise, dict) else None,
        "program_id": str(program_id) if program_id else None,
    }


def _load_workout_rule_set_from_program_id(program_id: str | None) -> dict | None:
    if not program_id:
        return None
    try:
        return load_program_rule_set(resolve_linked_program_id(program_id))
    except FileNotFoundError:
        return None


def _upsert_workout_session_state(
    *,
    db: Session,
    user_id: str,
    workout_id: str,
    primary_exercise_id: str,
    exercise_id: str,
    planned_sets: int,
    planned_rep_range: tuple[int, int],
    planned_weight: float,
    set_index: int,
    reps: int,
    weight: float,
    substitution_recommendation: dict | None,
    rule_set: dict | None,
) -> WorkoutLiveRecommendationResponse:
    planned_reps_min, planned_reps_max = planned_rep_range
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
            exercise_id=exercise_id,
            **build_workout_session_state_defaults(
                primary_exercise_id=primary_exercise_id,
                planned_sets=planned_sets,
                planned_reps_min=planned_reps_min,
                planned_reps_max=planned_reps_max,
                planned_weight=planned_weight,
            ),
        )

    reduction = prepare_workout_session_state_persistence_payload(
        existing_state=state,
        primary_exercise_id=primary_exercise_id,
        planned_sets=planned_sets,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
        set_index=set_index,
        reps=reps,
        weight=weight,
        substitution_recommendation=substitution_recommendation,
        rule_set=rule_set,
    )
    state_payload = reduction["state"]
    live = reduction["live_recommendation"]
    for key, value in state_payload.items():
        setattr(state, key, value)
    db.add(state)

    return WorkoutLiveRecommendationResponse(**live)

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
    plan_runtime = build_workout_today_plan_runtime(latest_plan_payload=latest if isinstance(latest, dict) else {})
    sessions = plan_runtime["sessions"]
    session_ids = plan_runtime["session_ids"]
    recent_logs = []
    if session_ids:
        recent_logs = (
            db.query(WorkoutSetLog)
            .filter(
                WorkoutSetLog.user_id == current_user.id,
                WorkoutSetLog.workout_id.in_(session_ids),
            )
            .order_by(WorkoutSetLog.created_at.desc())
            .all()
        )
    log_runtime = build_workout_today_log_runtime(
        recent_logs=recent_logs,
        selected_session_logs=[],
    )
    resume_runtime = resolve_latest_logged_workout_resume_state(
        sessions=sessions,
        performed_logs=list(log_runtime["resume_logs"]),
    )

    selection = resolve_workout_today_session_selection(
        sessions=sessions,
        latest_logged_workout_id=resume_runtime["latest_logged_workout_id"],
        latest_logged_session_incomplete=bool(resume_runtime["latest_logged_session_incomplete"]),
        today_iso=date.today().isoformat(),
    )
    selected = selection["selected_session"]
    resume_selected = bool(selection["resume_selected"])

    if not selected:
        raise HTTPException(status_code=404, detail="No workouts available")

    logs = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.workout_id == selected.get("session_id"),
        )
        .all()
    )
    log_runtime = build_workout_today_log_runtime(
        recent_logs=recent_logs,
        selected_session_logs=logs,
    )
    completed_by_ex = resolve_workout_completion_per_exercise(
        performed_logs=list(log_runtime["completion_logs"])
    )

    states = (
        db.query(WorkoutSessionState)
        .filter(
            WorkoutSessionState.user_id == current_user.id,
            WorkoutSessionState.workout_id == selected.get("session_id"),
        )
        .all()
    )
    selected_program_id = plan_runtime["selected_program_id"]
    rule_set = _load_workout_rule_set_from_program_id(selected_program_id)
    progression_states: list[ExerciseState] = []
    progression_lookup_runtime = build_workout_today_progression_lookup_runtime(session_states=states)
    primary_exercise_ids = set(progression_lookup_runtime["primary_exercise_ids"])
    if primary_exercise_ids:
        progression_states = (
            db.query(ExerciseState)
            .filter(
                ExerciseState.user_id == current_user.id,
                ExerciseState.exercise_id.in_(primary_exercise_ids),
            )
        )
    session_state_payloads = build_workout_today_session_state_payloads(
        session_states=states,
        planned_session=selected,
        progression_states=progression_states,
        equipment_profile=current_user.equipment_profile,
        rule_set=rule_set,
    )
    state_payloads = build_workout_today_state_payloads(
        session_states=session_state_payloads,
        completed_sets_by_exercise=completed_by_ex,
        rule_set=rule_set,
    )

    return build_workout_today_payload(
        selected_session=selected,
        mesocycle=plan_runtime["mesocycle"],
        deload=plan_runtime["deload"],
        completed_sets_by_exercise=dict(state_payloads["completed_sets_by_exercise"]),
        live_recommendations_by_exercise=dict(state_payloads["live_recommendations_by_exercise"]),
        resume_selected=resume_selected,
        daily_quote=daily_stoic_quote(),
    )


@router.post("/workout/{workout_id}/log-set")
def log_set(
    workout_id: str,
    payload: WorkoutSetLogRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> WorkoutSetLogResponse:
    primary_exercise_id = payload.primary_exercise_id or payload.exercise_id
    workout_plan_context = _resolve_workout_plan_context(
        db,
        user_id=current_user.id,
        workout_id=workout_id,
        exercise_id=payload.exercise_id,
    )
    planned_exercise = workout_plan_context["exercise"]
    log_set_plan_context = resolve_workout_log_set_plan_context(
        planned_exercise=planned_exercise,
        fallback_weight=payload.weight,
    )
    planned_reps_min = int(log_set_plan_context["planned_reps_min"])
    planned_reps_max = int(log_set_plan_context["planned_reps_max"])
    planned_sets = int(log_set_plan_context["planned_sets"])
    planned_weight = float(log_set_plan_context["planned_weight"])
    rule_set = _load_workout_rule_set_from_program_id(workout_plan_context["program_id"])

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
    starting_load_runtime: dict | None = None
    if not state:
        starting_load_runtime = resolve_starting_load(
            planned_exercise=planned_exercise,
            fallback_weight=planned_weight,
            rule_set=rule_set,
        )
        state = ExerciseState(
            user_id=current_user.id,
            exercise_id=primary_exercise_id,
            current_working_weight=float(starting_load_runtime["working_weight"]),
            exposure_count=0,
            consecutive_under_target_exposures=0,
            last_progression_action="hold",
            fatigue_score=0,
        )

    updated = update_exercise_state_after_workout(
        exercise_state=EngineExerciseState(
            exercise_id=primary_exercise_id,
            current_working_weight=state.current_working_weight,
            exposure_count=state.exposure_count,
            consecutive_under_target_exposures=state.consecutive_under_target_exposures,
            last_progression_action=state.last_progression_action,
            fatigue_score=state.fatigue_score,
        ),
        completed_reps=payload.reps,
        target_rep_range=(planned_reps_min, planned_reps_max),
        completed_sets=payload.set_index,
        planned_sets=planned_sets,
        phase_modifier=current_user.nutrition_phase or "maintenance",
        rule_set=rule_set,
    )

    state.current_working_weight = updated.current_working_weight
    state.exposure_count = updated.exposure_count
    state.consecutive_under_target_exposures = updated.consecutive_under_target_exposures
    state.last_progression_action = updated.last_progression_action
    state.fatigue_score = updated.fatigue_score

    substitution_recommendation = build_repeat_failure_substitution_payload(
        planned_exercise=planned_exercise,
        exercise_state=state,
        equipment_profile=current_user.equipment_profile,
        rule_set=rule_set,
    )

    live_recommendation = _upsert_workout_session_state(
        db=db,
        user_id=current_user.id,
        workout_id=workout_id,
        primary_exercise_id=primary_exercise_id,
        exercise_id=payload.exercise_id,
        planned_sets=planned_sets,
        planned_rep_range=(planned_reps_min, planned_reps_max),
        planned_weight=planned_weight,
        set_index=payload.set_index,
        reps=payload.reps,
        weight=payload.weight,
        substitution_recommendation=substitution_recommendation,
        rule_set=rule_set,
    )

    db.add(state)
    db.commit()
    db.refresh(record)

    feedback = interpret_workout_set_feedback(
        reps=payload.reps,
        weight=payload.weight,
        planned_reps_min=planned_reps_min,
        planned_reps_max=planned_reps_max,
        planned_weight=planned_weight,
        next_working_weight=updated.current_working_weight,
        rule_set=rule_set,
    )

    return WorkoutSetLogResponse(
        **build_workout_log_set_payload(
            record_id=record.id,
            primary_exercise_id=record.primary_exercise_id,
            exercise_id=record.exercise_id,
            set_index=record.set_index,
            reps=record.reps,
            weight=record.weight,
            planned_reps_min=planned_reps_min,
            planned_reps_max=planned_reps_max,
            planned_weight=planned_weight,
            feedback=feedback,
            starting_load_decision_trace=(
                dict(starting_load_runtime["decision_trace"]) if starting_load_runtime else None
            ),
            live_recommendation=live_recommendation,
            created_at=record.created_at,
        )
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
    log_runtime = build_workout_today_log_runtime(
        recent_logs=[],
        selected_session_logs=logs,
    )

    completed_by_ex = resolve_workout_completion_per_exercise(
        performed_logs=list(log_runtime["completion_logs"])
    )

    session = _resolve_workout_plan_context(db, current_user.id, workout_id)["session"]
    return build_workout_progress_payload(
        workout_id=workout_id,
        completed_sets_by_exercise=completed_by_ex,
        planned_session=session,
    )


@router.get(
    "/workout/{workout_id}/summary",
    responses={404: {"description": "Workout not found"}},
)
def workout_summary(
    workout_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> WorkoutSummaryResponse:
    plan_context = _resolve_workout_plan_context(db, current_user.id, workout_id)
    session = plan_context["session"]
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

    summary_runtime = build_workout_summary_progression_lookup_runtime(planned_session=session)
    primary_exercise_ids = set(summary_runtime["primary_exercise_ids"])
    progression_states: list[ExerciseState] = []
    if primary_exercise_ids:
        progression_states = (
            db.query(ExerciseState)
            .filter(
                ExerciseState.user_id == current_user.id,
                ExerciseState.exercise_id.in_(primary_exercise_ids),
            )
            .all()
        )

    rule_set = _load_workout_rule_set_from_program_id(plan_context["program_id"])

    return WorkoutSummaryResponse(
        **build_workout_performance_summary(
            workout_id=workout_id,
            planned_session=session,
            performed_logs=logs,
            progression_states=progression_states,
            rule_set=rule_set,
        )
    )
