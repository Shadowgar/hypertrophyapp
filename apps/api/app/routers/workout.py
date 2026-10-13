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
    build_workout_session_state_defaults,
    hydrate_live_workout_recommendation,
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
from core_engine.authored_constraints import requires_receipt_tracking, is_bodyweight_authored, annotate_constraints, refresh_constraints, project_variant_load, restriction_conflicts, equipment_conflicts
from ..workout_authored import log_typed_set, typed_projection, log_authored_set, authored_feedback_projection
from ..workout_load_state import is_authored_occurrence, project_authored_load_feedback, rebuild_authored_load_state
from ..deps import get_current_user
from ..models import ExerciseState, User, WorkoutPlan, WorkoutSessionState, WorkoutSetLog, WorkoutOccurrence, WorkoutLogCommand
from ..workout_identity import identified_plans, resolve_occurrence, resolve_exercise, occurrence_plan
from ..workout_history import effective_set_logs, capture_replay_context, require_replay_context, rebuild_exercise_state, rebuild_session_state, invalidate_history_advice
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
    WorkoutSetCorrectionRequest,
    AuthoredSubstitutionRequest,
    WorkoutLoadGuidanceRequest,
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


def _validate_authored_load_permission(user, occurrence, exercise):
    if not is_authored_occurrence(occurrence):
        raise HTTPException(409, "Load guidance requires an authored workout occurrence")
    constraint = refresh_constraints(exercise, equipment=user.equipment_profile, restrictions=user.movement_restrictions)
    if constraint.get("execution_status", constraint.get("status")) in {"unresolved", "infeasible", "declined"}:
        raise HTTPException(409, "Authored slot is unresolved; confirm a source-approved alternative before load guidance")
    if exercise.get("performed_variant"):
        consent = exercise.get("substitution_consent") or {}
        if not consent.get("confirmed") or consent.get("user_id") != user.id:
            raise HTTPException(409, "Performed variant requires occurrence-bound source consent")


def _attach_authored_load_feedback(db, user, occurrence, session, response):
    if not is_authored_occurrence(occurrence):
        return
    snapshots = {exercise["exercise_occurrence_id"]: exercise for exercise in session.get("exercises") or []}
    for projected in response.get("exercises") or []:
        exercise = snapshots.get(projected.get("exercise_occurrence_id"))
        if exercise is None:
            continue
        projection = authored_feedback_projection(db, user=user, occurrence=occurrence, exercise=exercise)
        projected["load_intelligence"] = projection["load_intelligence"]
        projected["exercise_state"] = projection["exercise_state"]
        offered = projection["load_intelligence"]["remaining_sets"] or projection["load_intelligence"]["next_exposure"]
        projected["load_recommendation_available"] = offered["prefill_available"]
        projected["live_recommendation"] = projection["live_recommendation"]
        if "completed_sets" in projected:
            projected["completed_sets"] = projection["session_state"]["completed_sets"]
        if "recommended_working_weight" in projected:
            projected["recommended_working_weight"] = offered["recommended_weight"]
        if "next_working_weight" in projected:
            projected["next_working_weight"] = projection["load_intelligence"]["next_exposure"]["recommended_weight"]


@router.post("/workout/{workout_id}/load-guidance")
def workout_load_guidance(workout_id: str, payload: WorkoutLoadGuidanceRequest, db: DbSession, current_user: CurrentUser) -> dict:
    """Preview explicit authored load context without saving an occurrence/advice."""
    occurrence, session = resolve_occurrence(db, current_user.id, workout_id, _list_workout_plans(db, current_user.id))
    matches = [exercise for exercise in session.get("exercises") or []
        if exercise.get("exercise_occurrence_id") == payload.exercise_occurrence_id]
    if len(matches) != 1:
        raise HTTPException(404, "Exercise occurrence not found")
    exercise = matches[0]
    _validate_authored_load_permission(current_user, occurrence, exercise)
    return project_authored_load_feedback(db, user=current_user, occurrence=occurrence,
        exercise=exercise, supplied_context=payload.load_context)


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
    qualifying: bool = True,
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

    if not qualifying:
        if state is None:
            state = WorkoutSessionState(user_id=user_id, workout_id=workout_id, exercise_id=exercise_id,
                workout_occurrence_id=workout_occurrence_id, exercise_occurrence_id=exercise_occurrence_id,
                **build_workout_session_state_defaults(primary_exercise_id=primary_exercise_id, planned_sets=planned_sets,
                    planned_reps_min=planned_rep_range[0], planned_reps_max=planned_rep_range[1], planned_weight=planned_weight))
            db.add(state)
        return WorkoutLiveRecommendationResponse(**hydrate_live_workout_recommendation(completed_sets=state.completed_sets,
            remaining_sets=state.remaining_sets, recommended_reps_min=state.recommended_reps_min,
            recommended_reps_max=state.recommended_reps_max, recommended_weight=state.recommended_weight,
            guidance=state.last_guidance, substitution_recommendation=substitution_recommendation, rule_set=rule_set))
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
    raw_plans = _list_current_workout_plans(db, current_user)
    today_iso = date.today().isoformat()
    if current_user.scheduling_timezone:
        from ..selected_date_plans import active_selected_plans, local_week
        today, monday = local_week(current_user.scheduling_timezone, datetime.now(UTC))
        today_iso = today.isoformat()
        raw_plans = active_selected_plans(raw_plans, monday)
        if not raw_plans:
            raise HTTPException(404, "No workout scheduled today")
        if len(raw_plans) != 1:
            raise HTTPException(409, "Multiple active dated plans require reconciliation")
    plans = identified_plans(db, raw_plans)
    plan_runtime = prepare_workout_today_plan_route_runtime(plan_rows=plans)
    if not bool(plan_runtime["has_plan"]):
        raise HTTPException(status_code=404, detail="No plan generated")

    sessions = cast(list[dict], plan_runtime["sessions"])
    latest_payload = plans[0].payload if plans else {}
    schedule = latest_payload.get("schedule") if isinstance(latest_payload, dict) else None
    if isinstance(schedule, dict) and schedule.get("mode") == "selected_dates_v1":
        sessions = [session for session in sessions if session.get("scheduled_date") == today_iso]
        if not sessions:
            raise HTTPException(status_code=404, detail="No workout scheduled today")
        if len(sessions) != 1:
            raise HTTPException(status_code=409, detail="Conflicting workouts share today's selected date")
    session_ids = [session["workout_occurrence_id"] for session in sessions]
    recent_logs = []
    if session_ids:
        recent_logs = (
            effective_set_logs(db)
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
        today_iso=today_iso,
    )
    selected = cast(dict, selection_runtime["selected_session"])
    resume_selected = bool(selection_runtime["resume_selected"])

    if not selected:
        raise HTTPException(status_code=404, detail="No workouts available")

    authored_selected = any(plan.payload.get("program_template_id") in
        {"pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"} and
        any(session.get("workout_occurrence_id") == selected.get("workout_occurrence_id")
            for session in plan.payload.get("sessions") or []) for plan in plans)
    for exercise in selected.get("exercises") or []:
        if authored_selected:
            exercise["authored_constraint"] = refresh_constraints(exercise,
                equipment=current_user.equipment_profile, restrictions=current_user.movement_restrictions)
            exercise.update(project_variant_load(exercise))

    logs = (
        effective_set_logs(db)
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

    if authored_selected:
        occurrence, frozen = resolve_occurrence(db, current_user.id, selected["workout_occurrence_id"], raw_plans)
        _attach_authored_load_feedback(db, current_user, occurrence, frozen, response_payload)
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
        if command.response.get("operation"):
            raise HTTPException(409, "Command already used for another history action")
        return WorkoutSetLogResponse(**command.response)
    return None


@router.post("/workout/{workout_id}/log-set")
def log_set(workout_id: str, payload: WorkoutSetLogRequest, db: DbSession, current_user: CurrentUser) -> WorkoutSetLogResponse:
    normalized = payload.model_dump(mode="json", exclude={"command_id"})
    # New absent fields must not change the digest of a pre-M2A command.
    for field in ("load_context", "load_recommendation_id", "load_override_reason"):
        if normalized[field] is None:
            normalized.pop(field)
    normalized["set_kind"] = (payload.set_kind or "work").strip().lower() or "work"
    normalized["primary_exercise_id"] = payload.primary_exercise_id or payload.exercise_id
    try:
        digest = hashlib.sha256(json.dumps({"workout": workout_id, **normalized},
            sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    except ValueError as exc:
        raise HTTPException(422, "Log payload must contain finite numbers") from exc
    _lock_history_user(db, current_user.id)
    db.refresh(current_user)
    if payload.command_id:
        replay = _replay_command(db, current_user.id, payload.command_id, digest)
        if replay:
            return replay
    occurrence, session = resolve_occurrence(db, current_user.id, workout_id, _list_workout_plans(db, current_user.id))
    exercise = resolve_exercise(session, payload.exercise_id, payload.exercise_occurrence_id)
    constraint = exercise.get("authored_constraint") or {}
    if occurrence.program_id in {"pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"}:
        constraint = refresh_constraints(exercise, equipment=current_user.equipment_profile,
            restrictions=current_user.movement_restrictions)
        exercise["authored_constraint"] = constraint
    if constraint.get("execution_status", constraint.get("status")) in {"unresolved", "infeasible", "declined"}:
        raise HTTPException(409, "Authored slot is unresolved; confirm a source-approved alternative before logging")
    if payload.weight == 0 and not is_bodyweight_authored(exercise):
        raise HTTPException(422, "Zero external load requires an explicitly bodyweight authored exercise")
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
    # User lock held by log_set: distinct commands cannot both claim one slot.
    existing_slots = effective_set_logs(db).filter_by(
        user_id=current_user.id, workout_occurrence_id=occurrence.id,
        exercise_occurrence_id=exercise["exercise_occurrence_id"], set_index=payload.set_index,
    ).all()
    kind = (payload.set_kind or "work").strip().lower() or "work"
    ordinal = (payload.technique or {}).get("ordinal") if payload.parent_set_index is not None or kind != "work" else None
    for entry in existing_slots:
        if (is_authored_occurrence(occurrence) and entry.parent_set_index is None and payload.parent_set_index is None
                and (entry.set_kind or "work").strip().lower() in {"work", "top", "backoff"}
                and kind in {"work", "top", "backoff"}):
            raise HTTPException(409, "Logical working set already logged; undo before starting a new attempt")
        if ((entry.set_kind or "work").strip().lower() or "work") == kind and entry.parent_set_index == payload.parent_set_index and ((entry.technique or {}).get("ordinal") if entry.parent_set_index is not None or kind != "work" else None) == ordinal:
            raise HTTPException(409, "Logical set already logged; undo before starting a new attempt")
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

    if is_authored_occurrence(occurrence):
        _validate_authored_load_permission(current_user, occurrence, exercise)
        return log_authored_set(db, current_user=current_user, occurrence=occurrence, exercise=exercise,
            payload=payload, command_id=command_id, digest=digest, context=context_runtime)

    db.add(occurrence)
    db.flush()

    state = (
        db.query(ExerciseState)
        .filter(
            ExerciseState.user_id == current_user.id,
            ExerciseState.exercise_id == primary_exercise_id,
        )
        .first()
    )
    if requires_receipt_tracking(exercise):
        return log_typed_set(db, current_user=current_user, occurrence=occurrence, exercise=exercise,
            payload=payload, command_id=command_id, digest=digest, context=context_runtime, state=state)
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
        replay_context=capture_replay_context(state=state, context=context_runtime,
            nutrition_phase=current_user.nutrition_phase, equipment_profile=current_user.equipment_profile),
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
        qualifying=payload.parent_set_index is None and ((payload.set_kind or "work").strip().lower() or "work") == "work",
        **cast(dict, log_set_runtime["session_state_inputs"]),
    )

    db.add(state)
    db.flush()
    state.last_updated_at = record.created_at
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


def _history_digest(operation: str, reference: str, payload: dict) -> str:
    return hashlib.sha256(json.dumps({"operation": operation, "reference": reference, **payload},
        sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _replay_history_action(db, user_id, command_id, digest):
    if not command_id:
        return None
    command = db.query(WorkoutLogCommand).filter_by(user_id=user_id, command_id=command_id).first()
    if command:
        if command.request_digest != digest or not command.response.get("operation"):
            raise HTTPException(409, "Command already used with different history inputs")
        return command.response["result"]
    return None


def _save_history_action(db, *, user_id, command_id, digest, operation, occurrence, exercise_occurrence_id, result):
    if command_id:
        db.add(occurrence)
        db.flush()
        db.add(WorkoutLogCommand(user_id=user_id, command_id=command_id, request_digest=digest,
            workout_occurrence_id=occurrence.id, exercise_occurrence_id=exercise_occurrence_id,
            response={"operation": operation, "result": result}))


def _void_set(db, record, *, reason, source, timestamp):
    record.voided_at = timestamp
    record.void_reason = reason
    record.void_source = source
    invalidate_history_advice(db, record, timestamp)
    if record.command_id:
        command = db.query(WorkoutLogCommand).filter_by(user_id=record.user_id, command_id=record.command_id).first()
        if command:
            command.undone_at = timestamp


def _reconstruct_history(db, record):
    db.flush()
    if record.replay_context["version"] == 2:
        user = db.query(User).filter_by(id=record.user_id).one()
        occurrence = db.query(WorkoutOccurrence).filter_by(id=record.workout_occurrence_id, user_id=record.user_id).one()
        exercise = resolve_exercise(occurrence.payload, record.exercise_id, record.exercise_occurrence_id)
        rebuild_authored_load_state(db, user=user)
        return authored_feedback_projection(db, user=user, occurrence=occurrence, exercise=exercise)
    if requires_receipt_tracking(record.replay_context["planned_exercise"]):
        legacy = typed_projection(db, record)
    else:
        progression = rebuild_exercise_state(db, user_id=record.user_id, primary_exercise_id=record.primary_exercise_id)
        session = rebuild_session_state(db, user_id=record.user_id, occurrence_id=record.workout_occurrence_id,
            exercise_occurrence_id=record.exercise_occurrence_id, session_inputs=progression["session_inputs"])
        legacy = {**session, "exercise_state": progression["exercise_state"], "decision_trace": progression["decision_trace"]}
    occurrence = db.query(WorkoutOccurrence).filter_by(id=record.workout_occurrence_id, user_id=record.user_id).one()
    if is_authored_occurrence(occurrence):
        user = db.query(User).filter_by(id=record.user_id).one()
        exercise = resolve_exercise(occurrence.payload, record.exercise_id, record.exercise_occurrence_id)
        rebuild_authored_load_state(db, user=user)
        projection = authored_feedback_projection(db, user=user, occurrence=occurrence, exercise=exercise)
        projection["decision_trace"]["legacy_replay"] = legacy["decision_trace"]
        return {**legacy, **projection}
    return legacy


@router.post("/workout/{workout_id}/undo-last-set")
def undo_last_set(workout_id: str, payload: WorkoutUndoLastSetRequest, db: DbSession, current_user: CurrentUser) -> dict:
    _lock_history_user(db, current_user.id)
    db.refresh(current_user)
    digest = _history_digest("undo", workout_id, payload.model_dump(mode="json", exclude={"command_id"}))
    replay = _replay_history_action(db, current_user.id, payload.command_id, digest)
    if replay is not None:
        return replay
    occurrence, session = resolve_occurrence(db, current_user.id, workout_id, _list_workout_plans(db, current_user.id))
    exercise = resolve_exercise(session, payload.exercise_id, payload.exercise_occurrence_id)
    record = effective_set_logs(db).filter_by(user_id=current_user.id, workout_occurrence_id=occurrence.id,
        exercise_occurrence_id=exercise["exercise_occurrence_id"]).order_by(WorkoutSetLog.created_at.desc(), WorkoutSetLog.id.desc()).first()
    result = {"status": "no_sets"}
    if record:
        require_replay_context(record)
        _void_set(db, record, reason=payload.reason or "undo_last_set", source="user_undo", timestamp=datetime.now(UTC).replace(tzinfo=None))
        result = {"status": "ok", "voided_set_id": record.id, **_reconstruct_history(db, record)}
    _save_history_action(db, user_id=current_user.id, command_id=payload.command_id, digest=digest, operation="undo",
        occurrence=occurrence, exercise_occurrence_id=exercise["exercise_occurrence_id"], result=result)
    db.commit()
    return result


@router.post("/workout/set/{set_id}/correct")
def correct_set(set_id: str, payload: WorkoutSetCorrectionRequest, db: DbSession, current_user: CurrentUser) -> dict:
    _lock_history_user(db, current_user.id)
    db.refresh(current_user)
    digest = _history_digest("correct", set_id, payload.model_dump(mode="json", exclude={"command_id"}) | {"rpe_supplied": "rpe" in payload.model_fields_set})
    replay = _replay_history_action(db, current_user.id, payload.command_id, digest)
    if replay is not None:
        return replay
    original = db.query(WorkoutSetLog).filter_by(id=set_id, user_id=current_user.id).first()
    if original is None:
        raise HTTPException(404, "Set not found")
    context = require_replay_context(original)
    if payload.weight == 0 and not is_bodyweight_authored(context["planned_exercise"]):
        raise HTTPException(422, "Zero external load requires an explicitly bodyweight authored exercise")
    if original.voided_at:
        raise HTTPException(409, "Set already voided or superseded; correct its effective replacement")
    now = datetime.now(UTC).replace(tzinfo=None)
    _void_set(db, original, reason=payload.reason, source="user_correction", timestamp=now)
    replacement = WorkoutSetLog(user_id=current_user.id, workout_id=original.workout_id,
        workout_occurrence_id=original.workout_occurrence_id, exercise_occurrence_id=original.exercise_occurrence_id,
        primary_exercise_id=original.primary_exercise_id, exercise_id=original.exercise_id,
        set_index=original.set_index, reps=payload.reps, weight=payload.weight,
        rpe=payload.rpe if "rpe" in payload.model_fields_set else original.rpe,
        set_kind=original.set_kind, parent_set_index=original.parent_set_index, technique=deepcopy(original.technique),
        created_at=original.created_at, amended_at=now, supersedes_id=original.id,
        replay_context=deepcopy(context), command_id=payload.command_id, request_digest=digest)
    if context["version"] == 2:
        # Retain the original command's offered advice/choice verbatim. Amendment
        # performance is the new row; this metadata explains its distinct origin.
        replacement.replay_context["amendment"] = {"supersedes_id": original.id,
            "effective_chosen_weight": replacement.weight, "actual_rpe": replacement.rpe,
            "rpe_supplied": "rpe" in payload.model_fields_set, "reason": payload.reason}
    db.add(replacement)
    result = {"status": "corrected", "original_set_id": original.id, "effective_set_id": replacement.id,
        **_reconstruct_history(db, replacement)}
    # UUID defaults are assigned by the reconstruction flush.
    result["effective_set_id"] = replacement.id
    occurrence = db.query(WorkoutOccurrence).filter_by(id=original.workout_occurrence_id, user_id=current_user.id).one()
    _save_history_action(db, user_id=current_user.id, command_id=payload.command_id, digest=digest, operation="correct",
        occurrence=occurrence, exercise_occurrence_id=original.exercise_occurrence_id, result=result)
    db.commit()
    return result


@router.get("/workout/set/{set_id}/audit")
def set_audit(set_id: str, db: DbSession, current_user: CurrentUser) -> dict:
    record = db.query(WorkoutSetLog).filter_by(id=set_id, user_id=current_user.id).first()
    if record is None:
        raise HTTPException(404, "Set not found")
    parent = record
    while parent.supersedes_id:
        parent = db.query(WorkoutSetLog).filter_by(id=parent.supersedes_id, user_id=current_user.id).one()
    chain = []
    while parent:
        chain.append({"id": parent.id, "supersedes_id": parent.supersedes_id, "effective": parent.voided_at is None,
            "reps": parent.reps, "weight": parent.weight, "rpe": parent.rpe, "created_at": parent.created_at,
            "amended_at": parent.amended_at, "voided_at": parent.voided_at, "reason": parent.void_reason, "source": parent.void_source,
            "workout_occurrence_id": parent.workout_occurrence_id, "exercise_occurrence_id": parent.exercise_occurrence_id,
            "replay_context_available": parent.replay_context is not None})
        parent = db.query(WorkoutSetLog).filter_by(supersedes_id=parent.id, user_id=current_user.id).first()
    return {"original_set_id": chain[0]["id"], "revisions": chain}


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
        effective_set_logs(db)
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
    _attach_authored_load_feedback(db, current_user, occurrence, session_snapshot, response_payload)
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
        effective_set_logs(db)
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
    response_payload = cast(dict, response_runtime["response_payload"])
    _attach_authored_load_feedback(db, current_user, occurrence, session, response_payload)
    return WorkoutSummaryResponse(**response_payload, workout_occurrence_id=occurrence.id)


@router.post("/workout/{workout_id}/authored-substitution")
def authored_substitution(workout_id: str, payload: AuthoredSubstitutionRequest,
                          db: DbSession, current_user: CurrentUser) -> dict:
    """Explicit occurrence consent; source prescription is never replaced."""
    _lock_history_user(db, current_user.id)
    digest = _history_digest("authored_substitution", workout_id,
        payload.model_dump(mode="json", exclude={"command_id"}))
    replay = _replay_history_action(db, current_user.id, payload.command_id, digest)
    if replay is not None:
        return replay
    occurrence, session = resolve_occurrence(db, current_user.id, workout_id, _list_workout_plans(db, current_user.id))
    if occurrence.program_id not in {"pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"}:
        raise HTTPException(409, "This command requires an authored program occurrence")
    exercise = resolve_exercise(session, payload.exercise_id, payload.exercise_occurrence_id)
    if payload.action == "confirm" and (not exercise.get("authored_prescription") or not exercise.get("source_lineage")):
        raise HTTPException(409, "Source permission is unavailable for this legacy slot")
    if payload.expected_source_lineage != (exercise.get("source_lineage") or {}):
        raise HTTPException(409, "Source revision changed")
    old = deepcopy(exercise.get("authored_constraint") or {})
    if payload.expected_revision != int(old.get("revision") or 0):
        raise HTTPException(409, "Substitution decision changed; refresh the occurrence")
    if payload.action != "report" and effective_set_logs(db).filter_by(user_id=current_user.id,
            workout_occurrence_id=occurrence.id, exercise_occurrence_id=exercise["exercise_occurrence_id"]).first():
        raise HTTPException(409, "Started occurrence retains its performed variant and consent")
    refreshed = refresh_constraints(exercise, equipment=current_user.equipment_profile,
        restrictions=current_user.movement_restrictions)
    reasons = deepcopy(refreshed["reasons"])
    reports = deepcopy(refreshed["reported_conflicts"])
    if payload.action == "report":
        if payload.reason is None:
            raise HTTPException(422, "Select an equipment, pain or safety reason")
        reason = {"kind": payload.reason, "details": ["user_reported"]}
        if reason not in reports:
            reports.append(reason)
        if reason not in reasons:
            reasons.append(reason)
    if not reasons:
        raise HTTPException(409, "No authored slot conflict was declared")
    choices = refreshed["allowed_alternatives"]
    execution_status = "unresolved" if choices else "infeasible"
    constraint = {**refreshed, "reasons": reasons, "reported_conflicts": reports,
        "revision": int(old.get("revision") or 0) + 1,
        "status": "confirmed" if exercise.get("performed_variant") else execution_status,
        "execution_status": execution_status}
    now = datetime.now(UTC).isoformat()
    if payload.action == "confirm":
        if exercise.get("performed_variant"):
            raise HTTPException(409, "A confirmed variant cannot be silently replaced; use a new occurrence")
        matches = [choice for choice in choices if choice["option_id"] == payload.option_id]
        if len(matches) != 1:
            raise HTTPException(409, "Alternative lacks source permission or is incompatible with current constraints")
        choice = deepcopy(matches[0])
        exercise["performed_variant"] = choice
        exercise["substitution_consent"] = {"confirmed": True, "user_id": current_user.id,
            "timestamp": now, "reasons": deepcopy(reasons), "permission": deepcopy(choice["permission"]),
            "original_exercise": {"id": exercise["id"], "name": exercise["name"]},
            "original_prescription": deepcopy(exercise["authored_prescription"]),
            "workout_occurrence_id": occurrence.id, "exercise_occurrence_id": exercise["exercise_occurrence_id"]}
        constraint.update(status="confirmed", execution_status="ready", reasons=[], reported_conflicts=[])
    elif payload.action == "decline":
        if exercise.get("performed_variant"):
            raise HTTPException(409, "Confirmed consent remains bound to this occurrence")
        constraint.update(status="declined", execution_status="declined")
    exercise["authored_constraint"] = constraint
    exercise.setdefault("substitution_decisions", []).append({"action": payload.action,
        "timestamp": now, "user_id": current_user.id, "revision": constraint["revision"],
        "reasons": deepcopy(reasons), "option_id": payload.option_id if payload.action == "confirm" else None})
    occurrence.payload = deepcopy(session)
    result = {"workout_occurrence_id": occurrence.id, "exercise_occurrence_id": exercise["exercise_occurrence_id"],
        "exercise": project_variant_load(exercise)}
    _save_history_action(db, user_id=current_user.id, command_id=payload.command_id, digest=digest,
        operation="authored_substitution", occurrence=occurrence,
        exercise_occurrence_id=exercise["exercise_occurrence_id"], result=result)
    db.commit()
    return result
