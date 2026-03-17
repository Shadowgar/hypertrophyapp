from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core_engine import (
    prepare_workout_log_set_context_route_runtime,
    prepare_workout_log_set_decision_route_runtime,
    prepare_workout_log_set_response_runtime,
    prepare_workout_progress_route_runtime,
    prepare_workout_session_state_route_runtime,
    prepare_workout_summary_response_runtime,
    prepare_workout_summary_route_runtime,
    prepare_workout_today_plan_route_runtime,
    prepare_workout_today_progression_route_runtime,
    prepare_workout_today_response_runtime,
    prepare_workout_today_selection_route_runtime,
)

from ..database import get_db
from ..deps import get_current_user
from ..models import ExerciseState, User, WorkoutPlan, WorkoutSessionState, WorkoutSetLog
from ..program_loader import (
    load_program_rule_set,
    resolve_active_administered_program_id,
    resolve_rule_program_id,
)
from ..schemas import (
    WorkoutLiveRecommendationResponse,
    WorkoutSetLogRequest,
    WorkoutSetLogResponse,
    WorkoutSummaryResponse,
    WorkoutUndoLastSetRequest,
)
from ..stoic_quotes import daily_stoic_quote

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _list_workout_plans(db: Session, user_id: str) -> list[WorkoutPlan]:
    return (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.created_at.desc())
        .all()
    )


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
    state = (
        db.query(WorkoutSessionState)
        .filter(
            WorkoutSessionState.user_id == user_id,
            WorkoutSessionState.workout_id == workout_id,
            WorkoutSessionState.exercise_id == exercise_id,
        )
        .first()
    )

    upsert_runtime = prepare_workout_session_state_route_runtime(
        existing_state=state,
        user_id=user_id,
        workout_id=workout_id,
        exercise_id=exercise_id,
        primary_exercise_id=primary_exercise_id,
        planned_sets=planned_sets,
        planned_rep_range=planned_rep_range,
        planned_weight=planned_weight,
        set_index=set_index,
        reps=reps,
        weight=weight,
        substitution_recommendation=substitution_recommendation,
        rule_set=rule_set,
    )
    if not state:
        state = WorkoutSessionState(
            **cast(dict, upsert_runtime["create_values"]),
        )

    state_payload = upsert_runtime["update_values"]
    live = upsert_runtime["live_recommendation"]
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
    plan_runtime = prepare_workout_today_plan_route_runtime(plan_rows=plans)
    if not bool(plan_runtime["has_plan"]):
        raise HTTPException(status_code=404, detail="No plan generated")

    sessions = cast(list[dict], plan_runtime["sessions"])
    session_ids = cast(list[str], plan_runtime["session_ids"])
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
    selection_runtime = prepare_workout_today_selection_route_runtime(
        sessions=sessions,
        recent_logs=recent_logs,
        today_iso=date.today().isoformat(),
    )
    selected = cast(dict, selection_runtime["selected_session"])
    resume_selected = bool(selection_runtime["resume_selected"])

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
    states = (
        db.query(WorkoutSessionState)
        .filter(
            WorkoutSessionState.user_id == current_user.id,
            WorkoutSessionState.workout_id == selected.get("session_id"),
        )
        .all()
    )
    selected_program_id = plan_runtime["selected_program_id"]
    normalized_selected_program_id = resolve_active_administered_program_id(cast(str | None, selected_program_id))
    progression_runtime = prepare_workout_today_progression_route_runtime(
        session_states=states,
        selected_program_id=normalized_selected_program_id,
        resolve_linked_program_id=resolve_rule_program_id,
        load_rule_set=load_program_rule_set,
    )
    progression_states: list[ExerciseState] = []
    primary_exercise_ids = set(cast(list[str], progression_runtime["primary_exercise_ids"]))
    if primary_exercise_ids:
        progression_states = (
            db.query(ExerciseState)
            .filter(
                ExerciseState.user_id == current_user.id,
                ExerciseState.exercise_id.in_(primary_exercise_ids),
            )
            .all()
        )
    response_runtime = prepare_workout_today_response_runtime(
        selected_session=selected,
        mesocycle=plan_runtime["mesocycle"],
        deload=plan_runtime["deload"],
        selected_session_logs=logs,
        session_states=states,
        progression_states=progression_states,
        equipment_profile=current_user.equipment_profile,
        rule_set=cast(dict | None, progression_runtime["rule_set"]),
        resume_selected=resume_selected,
        daily_quote=daily_stoic_quote(),
    )
    return cast(dict, response_runtime["response_payload"])


@router.post("/workout/{workout_id}/log-set")
def log_set(
    workout_id: str,
    payload: WorkoutSetLogRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> WorkoutSetLogResponse:
    context_runtime = prepare_workout_log_set_context_route_runtime(
        workout_id=workout_id,
        plan_rows=_list_workout_plans(db, current_user.id),
        primary_exercise_id=payload.primary_exercise_id,
        exercise_id=payload.exercise_id,
        set_index=payload.set_index,
        reps=payload.reps,
        weight=payload.weight,
        rpe=payload.rpe,
        resolve_linked_program_id=resolve_rule_program_id,
        load_rule_set=load_program_rule_set,
    )
    primary_exercise_id = str(context_runtime["primary_exercise_id"])

    state = (
        db.query(ExerciseState)
        .filter(
            ExerciseState.user_id == current_user.id,
            ExerciseState.exercise_id == primary_exercise_id,
        )
        .first()
    )
    log_set_runtime = prepare_workout_log_set_decision_route_runtime(
        user_id=current_user.id,
        workout_id=workout_id,
        request_runtime=cast(dict, context_runtime["request_runtime"]),
        planned_exercise=cast(dict | None, context_runtime["planned_exercise"]),
        existing_exercise_state=state,
        nutrition_phase=current_user.nutrition_phase,
        equipment_profile=current_user.equipment_profile,
        rule_set=cast(dict | None, context_runtime["rule_set"]),
    )
    record = WorkoutSetLog(
        **cast(dict, log_set_runtime["record_values"]),
    )
    db.add(record)

    if not state:
        state = ExerciseState(
            **cast(dict, log_set_runtime["exercise_state_create_values"]),
        )
    for key, value in cast(dict, log_set_runtime["exercise_state_update_values"]).items():
        setattr(state, key, value)

    live_recommendation = _upsert_workout_session_state(
        db=db,
        user_id=current_user.id,
        workout_id=workout_id,
        **cast(dict, log_set_runtime["session_state_inputs"]),
    )

    db.add(state)
    db.commit()
    db.refresh(record)
    response_runtime = prepare_workout_log_set_response_runtime(
        record=record,
        decision_runtime=cast(dict, log_set_runtime),
        live_recommendation=cast(dict, live_recommendation.model_dump()),
    )
    return WorkoutSetLogResponse(**cast(dict, response_runtime["response_payload"]))


@router.post("/workout/{workout_id}/undo-last-set")
def undo_last_set(
    workout_id: str,
    payload: WorkoutUndoLastSetRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """
    Remove the last logged set for a given exercise in this workout and
    recompute the in-session state for that exercise.
    """
    logs = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.workout_id == workout_id,
            WorkoutSetLog.exercise_id == payload.exercise_id,
        )
        .order_by(WorkoutSetLog.set_index.asc(), WorkoutSetLog.created_at.asc())
        .all()
    )
    if not logs:
        # Nothing to undo; treat as successful no-op.
        return {"status": "no_sets"}

    # Delete the last-set log entry.
    last_log = logs[-1]
    db.delete(last_log)
    db.flush()

    # Rebuild session state for this exercise from remaining logs using the
    # existing planned_* fields as the authoritative prescription.
    state = (
        db.query(WorkoutSessionState)
        .filter(
            WorkoutSessionState.user_id == current_user.id,
            WorkoutSessionState.workout_id == workout_id,
            WorkoutSessionState.exercise_id == payload.exercise_id,
        )
        .first()
    )
    if not state:
        db.commit()
        return {"status": "ok"}

    from core_engine import resolve_workout_session_state_update  # local import to avoid cycle at module load

    history: list[dict] = []
    latest_reduction: dict | None = None

    remaining_logs = [
        log
        for log in logs
        if log.id != last_log.id
    ]
    for entry in remaining_logs:
        latest_reduction = resolve_workout_session_state_update(
            existing_set_history=history,
            primary_exercise_id=state.primary_exercise_id,
            planned_sets=state.planned_sets,
            planned_reps_min=state.planned_reps_min,
            planned_reps_max=state.planned_reps_max,
            planned_weight=state.planned_weight,
            set_index=entry.set_index,
            reps=entry.reps,
            weight=entry.weight,
            substitution_recommendation=None,
            rule_set=None,
        )
        history = list(latest_reduction["state"]["set_history"])

    if latest_reduction is None:
        # All sets were removed; reset state to defaults.
        state.completed_sets = 0
        state.total_logged_reps = 0
        state.total_logged_weight = 0.0
        state.set_history = []
        state.remaining_sets = state.planned_sets
        state.recommended_reps_min = state.planned_reps_min
        state.recommended_reps_max = state.planned_reps_max
        state.recommended_weight = state.planned_weight
        state.last_guidance = "remaining_sets_hold_load_and_match_target_reps"
    else:
        reduced_state = latest_reduction["state"]
        state.completed_sets = int(reduced_state["completed_sets"])
        state.total_logged_reps = int(reduced_state["total_logged_reps"])
        state.total_logged_weight = float(reduced_state["total_logged_weight"])
        state.set_history = list(reduced_state["set_history"])
        state.remaining_sets = int(reduced_state["remaining_sets"])
        state.recommended_reps_min = int(reduced_state["recommended_reps_min"])
        state.recommended_reps_max = int(reduced_state["recommended_reps_max"])
        state.recommended_weight = float(reduced_state["recommended_weight"])
        state.last_guidance = str(reduced_state["last_guidance"])

    db.add(state)
    db.commit()
    return {"status": "ok"}


@router.get("/workout/{workout_id}/progress")
def workout_progress(
    workout_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Return per-exercise completed sets and an overall percent complete."""
    logs = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.workout_id == workout_id,
        )
        .all()
    )
    route_runtime = prepare_workout_progress_route_runtime(
        workout_id=workout_id,
        plan_rows=_list_workout_plans(db, current_user.id),
        selected_session_logs=logs,
    )
    return cast(dict, route_runtime["response_payload"])


@router.get(
    "/workout/{workout_id}/summary",
    responses={404: {"description": "Workout not found"}},
)
def workout_summary(
    workout_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> WorkoutSummaryResponse:
    route_runtime = prepare_workout_summary_route_runtime(
        workout_id=workout_id,
        plan_rows=_list_workout_plans(db, current_user.id),
        resolve_linked_program_id=resolve_rule_program_id,
        load_rule_set=load_program_rule_set,
    )
    session = cast(dict | None, route_runtime["session"])
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

    primary_exercise_ids = set(cast(list[str], route_runtime["primary_exercise_ids"]))
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

    response_runtime = prepare_workout_summary_response_runtime(
        workout_id=workout_id,
        planned_session=session,
        performed_logs=logs,
        progression_states=progression_states,
        rule_set=cast(dict | None, route_runtime["rule_set"]),
    )
    return WorkoutSummaryResponse(**cast(dict, response_runtime["response_payload"]))
