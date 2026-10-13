"""Effective records and replay orchestration; core retains progression policy."""
from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace

from fastapi import HTTPException
from core_engine import prepare_workout_log_set_decision_route_runtime, resolve_workout_session_state_update

from core_engine.authored_constraints import requires_receipt_tracking
from .models import ExerciseState, WorkoutSetLog, WorkoutSessionState, User, CoachingRecommendation, WeeklyReviewCycle

STATE_FIELDS = ("current_working_weight", "exposure_count", "consecutive_under_target_exposures", "last_progression_action", "fatigue_score")


def effective_set_logs(db):
    return db.query(WorkoutSetLog).filter(WorkoutSetLog.voided_at.is_(None))


def state_snapshot(state):
    if state is None:
        return None
    return {**{key: getattr(state, key) for key in STATE_FIELDS}, "last_updated_at": state.last_updated_at.isoformat()}


def capture_replay_context(*, state, context, nutrition_phase, equipment_profile):
    return deepcopy({"version": 1, "owner": "core_engine.prepare_workout_log_set_decision_route_runtime",
        "state_before": state_snapshot(state), "request_runtime": context["request_runtime"],
        "planned_exercise": context["planned_exercise"], "rule_set": context["rule_set"],
        "nutrition_phase": nutrition_phase, "equipment_profile": equipment_profile})


def require_replay_context(record):
    context = record.replay_context
    valid = isinstance(context, dict) and (context.get("version") == 1 or
        (context.get("version") == 2 and context.get("owner") == "api.workout_load_state"
            and isinstance(context.get("load_intelligence"), dict)))
    if not record.workout_occurrence_id or not valid:
        raise HTTPException(409, "Historical replay context unavailable; original record retained without changes")
    return context


def rebuild_exercise_state(db, *, user_id, primary_exercise_id):
    # Include voids when finding the original baseline and amendment ordering.
    records = db.query(WorkoutSetLog).filter_by(user_id=user_id, primary_exercise_id=primary_exercise_id).all()
    by_id = {row.id: row for row in records}
    def root(row):
        seen = set()
        while row.supersedes_id:
            if row.id in seen or row.supersedes_id not in by_id:
                raise HTTPException(409, "Amendment lineage cannot be reconstructed")
            seen.add(row.id)
            row = by_id[row.supersedes_id]
        return row
    replayable = sorted([row for row in records if row.replay_context is not None and row.replay_context.get("version") == 1
        and not requires_receipt_tracking(row.replay_context.get("planned_exercise"))], key=lambda row: (root(row).created_at, root(row).id))
    if not replayable:
        raise HTTPException(409, "No captured progression replay context")
    first = require_replay_context(replayable[0])
    if any(row.replay_context is None and row.created_at >= root(replayable[0]).created_at for row in records):
        raise HTTPException(409, "Uncaptured history intersects replay coverage; no correction committed")
    values = deepcopy(first["state_before"])
    baseline = deepcopy(values)
    inputs_by_record = {}
    effective_ids = []
    for row in replayable:
        context = require_replay_context(row)
        if row.voided_at is not None:
            continue
        request = {**deepcopy(context["request_runtime"]), "reps": row.reps, "weight": row.weight, "rpe": row.rpe}
        decision = prepare_workout_log_set_decision_route_runtime(user_id=user_id, workout_id=row.workout_id,
            request_runtime=request, planned_exercise=deepcopy(context["planned_exercise"]),
            existing_exercise_state=SimpleNamespace(**values) if values is not None else None,
            nutrition_phase=context["nutrition_phase"], equipment_profile=deepcopy(context["equipment_profile"]),
            rule_set=deepcopy(context["rule_set"]))
        values = {**decision["exercise_state_update_values"], "last_updated_at": row.created_at.isoformat()}
        inputs_by_record[row.id] = decision["session_state_inputs"]
        effective_ids.append(row.id)
    states = db.query(ExerciseState).filter_by(user_id=user_id, exercise_id=primary_exercise_id).all()
    if len(states) > 1:
        raise HTTPException(409, "Ambiguous duplicate progression projections; no correction committed")
    state = states[0] if states else None
    if values is None:
        if state is not None:
            db.delete(state)
    else:
        if state is None:
            state = ExerciseState(user_id=user_id, exercise_id=primary_exercise_id)
            db.add(state)
        for key in STATE_FIELDS:
            setattr(state, key, values[key])
        state.last_updated_at = datetime.fromisoformat(values["last_updated_at"])
    return {"exercise_state": values, "session_inputs": inputs_by_record,
        "decision_trace": {"owner": "api.workout_history", "reducer": first["owner"], "version": 1,
            "effective_set_ids": effective_ids, "baseline": "captured_projection" if baseline else "no_prior_projection",
            "earlier_context_missing": any(row.replay_context is None for row in records)}}


def rebuild_session_state(db, *, user_id, occurrence_id, exercise_occurrence_id, session_inputs):
    state = db.query(WorkoutSessionState).filter_by(user_id=user_id, workout_occurrence_id=occurrence_id,
        exercise_occurrence_id=exercise_occurrence_id).first()
    if state is None:
        raise HTTPException(409, "Missing session projection; correction requires reconstruction context")
    rows = effective_set_logs(db).filter_by(user_id=user_id, workout_occurrence_id=occurrence_id,
        exercise_occurrence_id=exercise_occurrence_id).order_by(WorkoutSetLog.created_at, WorkoutSetLog.id).all()
    order = {record_id: index for index, record_id in enumerate(session_inputs)}
    rows.sort(key=lambda row: order.get(row.id, -1))
    history = []
    reduction = None
    for row in rows:
        if row.parent_set_index is not None or ((row.set_kind or "work").strip().lower() or "work") != "work":
            continue
        inputs = session_inputs.get(row.id)
        if inputs is None:
            raise HTTPException(409, "Session history contains uncaptured decision context")
        reduction = resolve_workout_session_state_update(existing_set_history=history,
            primary_exercise_id=state.primary_exercise_id, planned_sets=state.planned_sets,
            planned_reps_min=state.planned_reps_min, planned_reps_max=state.planned_reps_max,
            planned_weight=state.planned_weight, set_index=row.set_index, reps=row.reps, weight=row.weight,
            substitution_recommendation=inputs["substitution_recommendation"], rule_set=inputs["rule_set"])
        history = list(reduction["state"]["set_history"])
    if reduction is None:
        from core_engine import build_workout_session_state_defaults
        values = build_workout_session_state_defaults(primary_exercise_id=state.primary_exercise_id,
            planned_sets=state.planned_sets, planned_reps_min=state.planned_reps_min,
            planned_reps_max=state.planned_reps_max, planned_weight=state.planned_weight)
        from core_engine import hydrate_live_workout_recommendation
        live = hydrate_live_workout_recommendation(completed_sets=0, remaining_sets=state.planned_sets,
            recommended_reps_min=state.planned_reps_min, recommended_reps_max=state.planned_reps_max,
            recommended_weight=state.planned_weight, guidance=values["last_guidance"], substitution_recommendation=None, rule_set=None)
    else:
        values = reduction["state"]
        live = reduction["live_recommendation"]
    for key, value in values.items():
        setattr(state, key, value)
    return {"session_state": {key: values[key] for key in ("completed_sets", "total_logged_reps", "total_logged_weight", "remaining_sets", "recommended_weight")},
        "live_recommendation": live}


def lock_history_user(db, user_id):
    db.query(User).filter_by(id=user_id).with_for_update().one()


def valid_weekly_reviews(db):
    return db.query(WeeklyReviewCycle).filter(WeeklyReviewCycle.summary["history_invalidated_at"].as_string().is_(None))


def invalidate_history_advice(db, record, timestamp):
    # No evidence-link index exists yet: conservatively invalidate later previews.
    # Preserve payloads and applied decisions as audit records.
    db.query(CoachingRecommendation).filter(CoachingRecommendation.user_id == record.user_id,
        CoachingRecommendation.recommendation_type == "coach_preview",
        CoachingRecommendation.status == "previewed",
        CoachingRecommendation.created_at >= record.created_at).update({CoachingRecommendation.status: "invalidated_history"}, synchronize_session=False)
    cycles = db.query(WeeklyReviewCycle).filter(WeeklyReviewCycle.user_id == record.user_id,
        WeeklyReviewCycle.created_at >= record.created_at).all()
    for cycle in cycles:
        cycle.summary = {**(cycle.summary or {}), "history_invalidated_at": timestamp.isoformat(), "history_invalidated_by_set_id": record.id}
