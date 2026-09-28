from datetime import date, datetime, UTC
import hashlib
import json
from uuid import uuid5, UUID
from copy import deepcopy
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

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
from ..models import ExerciseState, User, WorkoutPlan, WorkoutSessionState, WorkoutSetLog, WorkoutOccurrence, WorkoutLogCommand
from ..workout_identity import identified_plans, resolve_occurrence, resolve_exercise, occurrence_plan
from ..observability import log_event
from ..program_loader import (
    load_program_rule_set,
    resolve_active_administered_program_id,
    resolve_rule_program_id,
)
from .plan import ensure_current_workout_plans_for_user
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


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _extract_session_observability_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    exercises = payload.get("exercises") if isinstance(payload.get("exercises"), list) else []
    total_sets = 0
    first_five_exercises: list[str] = []

    for exercise in exercises:
        if not isinstance(exercise, dict):
            continue
        if len(first_five_exercises) < 5:
            label = str(exercise.get("name") or exercise.get("title") or exercise.get("id") or "")
            if label:
                first_five_exercises.append(label)

        sets_value = exercise.get("sets")
        if isinstance(sets_value, list):
            total_sets += len(cast(list[Any], sets_value))
            continue
        if sets_value is not None:
            total_sets += _coerce_int(sets_value)
            continue
        planned_sets = exercise.get("planned_sets")
        if planned_sets is not None:
            total_sets += _coerce_int(planned_sets)
            continue
        total_sets += _coerce_int(exercise.get("target_sets"))

    if total_sets == 0:
        total_sets = _coerce_int(payload.get("total_sets"))

    return {
        "total_exercises": len(exercises),
        "total_sets": total_sets,
        "first_5_exercise_names": first_five_exercises,
    }


def _list_workout_plans(db: Session, user_id: str) -> list[WorkoutPlan]:
    return (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.created_at.desc())
        .all()
    )


def _list_current_workout_plans(db: Session, current_user: User) -> list[WorkoutPlan]:
    return ensure_current_workout_plans_for_user(db=db, current_user=current_user)


def _upsert_workout_session_state(
    *,
    db: Session,
    user_id: str,
    workout_id: str,
    workout_occurrence_id: str,
    exercise_occurrence_id: str,
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
            WorkoutSessionState.workout_occurrence_id == workout_occurrence_id,
            WorkoutSessionState.exercise_occurrence_id == exercise_occurrence_id,
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
            workout_occurrence_id=workout_occurrence_id, exercise_occurrence_id=exercise_occurrence_id,
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
    log_event(
        "today_workout_fetch_started",
        route="/workout/today",
        action="today_fetch",
        user_id=current_user.id,
    )
    plans = identified_plans(db, _list_current_workout_plans(db, current_user))
    plan_runtime = prepare_workout_today_plan_route_runtime(plan_rows=plans)
    if not bool(plan_runtime["has_plan"]):
        raise HTTPException(status_code=404, detail="No plan generated")

    sessions = cast(list[dict], plan_runtime["sessions"])
    session_ids = [session["workout_occurrence_id"] for session in sessions]
    recent_logs = []
    if session_ids:
        recent_logs = (
            db.query(WorkoutSetLog)
            .filter(
                WorkoutSetLog.user_id == current_user.id,
                WorkoutSetLog.workout_occurrence_id.in_(session_ids),
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
            WorkoutSetLog.workout_occurrence_id == selected.get("workout_occurrence_id"),
        )
        .all()
    )
    states = (
        db.query(WorkoutSessionState)
        .filter(
            WorkoutSessionState.user_id == current_user.id,
            WorkoutSessionState.workout_occurrence_id == selected.get("workout_occurrence_id"),
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
    response_payload = cast(dict, response_runtime["response_payload"])
    progress_runtime = prepare_workout_progress_route_runtime(
        workout_id=str(response_payload.get("session_id") or selected.get("session_id") or ""),
        plan_rows=[{"payload": {"sessions": [selected]}}],
        selected_session_logs=logs,
    )
    progress_payload = cast(dict[str, Any], progress_runtime.get("response_payload") or {})
    progress_planned_total = _coerce_int(progress_payload.get("planned_total"))
    response_payload.setdefault("program_template_id", plan_runtime.get("selected_program_id"))
    response_payload["selected_program_id"] = plan_runtime.get("selected_program_id")
    if progress_planned_total > 0:
        response_payload["total_sets"] = progress_planned_total
        response_payload["planned_total"] = progress_planned_total
    else:
        inferred_total = _extract_session_observability_metrics(cast(dict[str, Any], response_payload)).get("total_sets") or 0
        inferred_total = _coerce_int(inferred_total)
        if inferred_total > 0:
            response_payload["total_sets"] = inferred_total
            response_payload["planned_total"] = inferred_total

    constructed_payload = cast(dict[str, Any], deepcopy(response_payload))
    mesocycle = cast(dict, response_payload.get("mesocycle") or {})
    session_metrics = _extract_session_observability_metrics(cast(dict[str, Any], response_payload))

    log_event(
        "session_constructed",
        route="/workout/today",
        action="today_fetch",
        user_id=current_user.id,
        selected_program_id=plan_runtime["selected_program_id"],
        template_id=response_payload.get("program_template_id"),
        session_id=response_payload.get("session_id"),
        week_index=mesocycle.get("week_index"),
        session_index=response_payload.get("session_index") or selected.get("session_index"),
        session_title=response_payload.get("title") or selected.get("title"),
        total_exercises=session_metrics["total_exercises"],
        total_sets=session_metrics["total_sets"],
        first_5_exercise_names=session_metrics["first_5_exercise_names"],
    )

    log_event(
        "today_workout_fetched",
        route="/workout/today",
        action="today_fetch",
        user_id=current_user.id,
        selected_program_id=plan_runtime["selected_program_id"],
        template_id=response_payload.get("program_template_id"),
        session_id=response_payload.get("session_id"),
        week_index=mesocycle.get("week_index"),
        displayed_week_index=mesocycle.get("week_index"),
        authored_week_index=mesocycle.get("authored_week_index"),
        week_start=response_payload.get("week_start"),
    )

    session_unchanged = constructed_payload == cast(dict[str, Any], response_payload)
    if not session_unchanged:
        log_event(
            "session_constructed_mismatch",
            level="warning",
            route="/workout/today",
            action="today_fetch",
            user_id=current_user.id,
            selected_program_id=plan_runtime["selected_program_id"],
            template_id=response_payload.get("program_template_id"),
            session_id=response_payload.get("session_id"),
            week_index=mesocycle.get("week_index"),
            session_title=response_payload.get("title") or selected.get("title"),
            error_message="Constructed session differs from returned session payload",
        )

    log_event(
        "session_returned_to_client",
        route="/workout/today",
        action="today_fetch",
        user_id=current_user.id,
        selected_program_id=plan_runtime["selected_program_id"],
        template_id=response_payload.get("program_template_id"),
        session_id=response_payload.get("session_id"),
        week_index=mesocycle.get("week_index"),
        session_index=response_payload.get("session_index") or selected.get("session_index"),
        session_title=response_payload.get("title") or selected.get("title"),
        total_exercises=session_metrics["total_exercises"],
        total_sets=session_metrics["total_sets"],
        first_5_exercise_names=session_metrics["first_5_exercise_names"],
        payload_match=session_unchanged,
    )
    return response_payload


def _lock_history_user(db: Session, user_id: str) -> None:
    # PostgreSQL serializes record/projection writes for this user, including undo.
    # This also prevents lost ExerciseState updates without changing its policy.
    db.query(User).filter(User.id == user_id).with_for_update().one()


def _replay_command(db: Session, user_id: str, command_id: str, digest: str):
    command = db.query(WorkoutLogCommand).filter_by(user_id=user_id, command_id=command_id).first()
    if command:
        if command.request_digest != digest:
            raise HTTPException(409, "Log command was already used with a different payload")
        return WorkoutSetLogResponse(**command.response)
    return None


@router.post("/workout/{workout_id}/log-set")
def log_set(workout_id: str, payload: WorkoutSetLogRequest, db: DbSession, current_user: CurrentUser) -> WorkoutSetLogResponse:
    normalized = payload.model_dump(mode="json", exclude={"command_id"})
    normalized["set_kind"] = (payload.set_kind or "work").strip().lower() or "work"
    normalized["primary_exercise_id"] = payload.primary_exercise_id or payload.exercise_id
    try:
        digest = hashlib.sha256(json.dumps({"workout": workout_id, **normalized},
            sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    except ValueError as exc:
        raise HTTPException(422, "Log payload must contain finite numbers") from exc
    _lock_history_user(db, current_user.id)
    if payload.command_id:
        replay = _replay_command(db, current_user.id, payload.command_id, digest)
        if replay:
            return replay
    occurrence, session = resolve_occurrence(db, current_user.id, workout_id, _list_workout_plans(db, current_user.id))
    exercise = resolve_exercise(session, payload.exercise_id, payload.exercise_occurrence_id)
    primary = str(exercise.get("primary_exercise_id") or exercise["id"])
    if normalized["primary_exercise_id"] != primary:
        raise HTTPException(409, "Primary exercise does not match the occurrence")
    # Old clients lack command IDs: one deterministic command per logical slot.
    # Modern clients always send explicit IDs, including new attempts after undo.
    command_id = payload.command_id or str(uuid5(UUID(occurrence.id), json.dumps([
        exercise["exercise_occurrence_id"], payload.set_index, normalized["set_kind"],
        payload.parent_set_index, (payload.technique or {}).get("ordinal")], separators=(",", ":"))))
    replay = _replay_command(db, current_user.id, command_id, digest)
    if replay:
        return replay
    try:
        db.add(occurrence)
        db.flush()
        return _apply_log_set(workout_id, payload, db, current_user, occurrence, session, exercise, command_id, digest)
    except IntegrityError:
        db.rollback()
        replay = _replay_command(db, current_user.id, command_id, digest)
        if replay:
            return replay
        raise HTTPException(409, "Concurrent workout update; retry this command")


def _apply_log_set(
    workout_id: str,
    payload: WorkoutSetLogRequest,
    db: DbSession,
    current_user: CurrentUser,
    occurrence: WorkoutOccurrence,
    session: dict,
    exercise: dict,
    command_id: str,
    digest: str,
) -> WorkoutSetLogResponse:
    context_runtime = prepare_workout_log_set_context_route_runtime(
        workout_id=occurrence.workout_id,
        plan_rows=occurrence_plan(occurrence, session),
        primary_exercise_id=payload.primary_exercise_id,
        exercise_id=payload.exercise_id,
        set_index=payload.set_index,
        reps=payload.reps,
        weight=payload.weight,
        rpe=payload.rpe,
        set_kind=payload.set_kind,
        parent_set_index=payload.parent_set_index,
        technique=payload.technique,
        resolve_linked_program_id=resolve_rule_program_id,
        load_rule_set=load_program_rule_set,
    )
    context_runtime["planned_exercise"] = exercise
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
        workout_id=occurrence.workout_id,
        request_runtime=cast(dict, context_runtime["request_runtime"]),
        planned_exercise=cast(dict | None, context_runtime["planned_exercise"]),
        existing_exercise_state=state,
        nutrition_phase=current_user.nutrition_phase,
        equipment_profile=current_user.equipment_profile,
        rule_set=cast(dict | None, context_runtime["rule_set"]),
    )
    record = WorkoutSetLog(
        **cast(dict, log_set_runtime["record_values"]),
        workout_occurrence_id=occurrence.id, exercise_occurrence_id=exercise["exercise_occurrence_id"],
        command_id=command_id, request_digest=digest,
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
        workout_id=occurrence.workout_id,
        workout_occurrence_id=occurrence.id, exercise_occurrence_id=exercise["exercise_occurrence_id"],
        **cast(dict, log_set_runtime["session_state_inputs"]),
    )

    db.add(state)
    db.flush()
    response_runtime = prepare_workout_log_set_response_runtime(
        record=record,
        decision_runtime=cast(dict, log_set_runtime),
        live_recommendation=cast(dict, live_recommendation.model_dump()),
    )
    response_payload = cast(dict, response_runtime["response_payload"])
    response_payload["decision_trace"]["occurrence_identity"] = {
        "owner": "api.workout_identity", "workout_occurrence_id": occurrence.id,
        "plan_id": occurrence.plan_id, "week_start": occurrence.week_start.isoformat(),
        "session_slot": occurrence.session_slot, "exercise_occurrence_id": exercise["exercise_occurrence_id"],
        "execution_slot": exercise["execution_slot"],
    }
    response = WorkoutSetLogResponse(**response_payload,
        workout_occurrence_id=occurrence.id, exercise_occurrence_id=exercise["exercise_occurrence_id"], command_id=command_id)
    db.add(WorkoutLogCommand(user_id=current_user.id, command_id=command_id, request_digest=digest,
        workout_occurrence_id=occurrence.id, exercise_occurrence_id=exercise["exercise_occurrence_id"],
        response=response.model_dump(mode="json")))
    db.commit()
    return response


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
    _lock_history_user(db, current_user.id)
    occurrence, session = resolve_occurrence(db, current_user.id, workout_id, _list_workout_plans(db, current_user.id))
    exercise = resolve_exercise(session, payload.exercise_id, payload.exercise_occurrence_id)
    logs = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.workout_occurrence_id == occurrence.id,
            WorkoutSetLog.exercise_occurrence_id == exercise["exercise_occurrence_id"],
        )
        .order_by(WorkoutSetLog.created_at.asc(), WorkoutSetLog.id.asc())
        .all()
    )
    if not logs:
        # Nothing to undo; treat as successful no-op.
        return {"status": "no_sets"}

    # Delete the last-set log entry.
    last_log = logs[-1]
    command = db.query(WorkoutLogCommand).filter_by(user_id=current_user.id, command_id=last_log.command_id).first()
    if command:
        command.undone_at = datetime.now(UTC).replace(tzinfo=None)
    db.delete(last_log)
    db.flush()

    # Rebuild session state for this exercise from remaining logs using the
    # existing planned_* fields as the authoritative prescription.
    state = (
        db.query(WorkoutSessionState)
        .filter(
            WorkoutSessionState.user_id == current_user.id,
            WorkoutSessionState.workout_occurrence_id == occurrence.id,
            WorkoutSessionState.exercise_occurrence_id == exercise["exercise_occurrence_id"],
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
    log_event(
        "workout_progress_fetch_started",
        route="/workout/{session_id}/progress",
        action="progress_fetch",
        user_id=current_user.id,
        session_id=workout_id,
    )
    occurrence, session_snapshot = resolve_occurrence(db, current_user.id, workout_id, _list_workout_plans(db, current_user.id))
    logs = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.workout_occurrence_id == occurrence.id,
        )
        .all()
    )
    route_runtime = prepare_workout_progress_route_runtime(
        workout_id=occurrence.workout_id,
        plan_rows=occurrence_plan(occurrence, session_snapshot),
        selected_session_logs=logs,
    )
    response_payload = cast(dict, route_runtime["response_payload"])
    log_event(
        "workout_progress_fetched",
        route="/workout/{session_id}/progress",
        action="progress_fetch",
        user_id=current_user.id,
        session_id=workout_id,
        planned_total=response_payload.get("planned_total"),
    )
    response_payload["workout_occurrence_id"] = occurrence.id
    return response_payload


@router.get(
    "/workout/{workout_id}/summary",
    responses={404: {"description": "Workout not found"}},
)
def workout_summary(
    workout_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> WorkoutSummaryResponse:
    occurrence, session_snapshot = resolve_occurrence(db, current_user.id, workout_id, _list_workout_plans(db, current_user.id))
    route_runtime = prepare_workout_summary_route_runtime(
        workout_id=occurrence.workout_id,
        plan_rows=occurrence_plan(occurrence, session_snapshot),
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
            WorkoutSetLog.workout_occurrence_id == occurrence.id,
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
        workout_id=occurrence.workout_id,
        planned_session=session,
        performed_logs=logs,
        progression_states=progression_states,
        rule_set=cast(dict | None, route_runtime["rule_set"]),
    )
    return WorkoutSummaryResponse(**cast(dict, response_runtime["response_payload"]), workout_occurrence_id=occurrence.id)
