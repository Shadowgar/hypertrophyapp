"""Persistence of typed authored set receipts without inventing numeric policy."""
from copy import deepcopy
from fastapi import HTTPException
from core_engine.authored_constraints import typed_tracking_feedback, is_bodyweight_authored
from .models import WorkoutSetLog, WorkoutLogCommand
from .schemas import WorkoutSetLogResponse
from .workout_history import capture_replay_context, effective_set_logs
from .workout_load_state import (
    project_authored_load_feedback, rebuild_authored_load_state, capture_authored_context,
)


def typed_projection(db, record):
    exercise = record.replay_context["planned_exercise"]
    rows = effective_set_logs(db).filter_by(user_id=record.user_id,
        workout_occurrence_id=record.workout_occurrence_id,
        exercise_occurrence_id=record.exercise_occurrence_id).all()
    working = [row for row in rows if row.parent_set_index is None and (row.set_kind or "work").strip().lower() == "work"]
    live = typed_tracking_feedback(exercise, completed_sets=len({row.set_index for row in working}),
        set_index=record.parent_set_index or record.set_index)
    return {"live_recommendation": live, "exercise_state": None,
        "session_state": {"completed_sets": live["completed_sets"], "remaining_sets": live["remaining_sets"],
            "total_logged_reps": sum(row.reps for row in working), "total_logged_weight": sum(row.weight for row in working)},
        "decision_trace": deepcopy(live["decision_trace"])}


def log_typed_set(db, *, current_user, occurrence, exercise, payload, command_id, digest, context, state):
    source_index = payload.parent_set_index or payload.set_index
    if source_index > len(exercise["authored_prescription"]["sets"]):
        raise HTTPException(409, "Set does not match the authored working-set prescription")
    record = WorkoutSetLog(user_id=current_user.id, workout_id=occurrence.workout_id,
        workout_occurrence_id=occurrence.id, exercise_occurrence_id=exercise["exercise_occurrence_id"],
        primary_exercise_id=exercise.get("primary_exercise_id") or exercise["id"], exercise_id=payload.exercise_id,
        set_index=payload.set_index, reps=payload.reps, weight=payload.weight, rpe=payload.rpe,
        set_kind=payload.set_kind, parent_set_index=payload.parent_set_index, technique=deepcopy(payload.technique),
        command_id=command_id, request_digest=digest,
        replay_context=capture_replay_context(state=state, context=context,
            nutrition_phase=current_user.nutrition_phase, equipment_profile=current_user.equipment_profile))
    db.add(record)
    db.flush()
    projection = typed_projection(db, record)
    live = projection["live_recommendation"]
    weight = 0.0 if is_bodyweight_authored(exercise) or exercise.get("performed_variant") else float(exercise["recommended_working_weight"])
    trace = {**live["decision_trace"], "occurrence_identity": {"workout_occurrence_id": occurrence.id,
        "exercise_occurrence_id": exercise["exercise_occurrence_id"], "execution_slot": exercise["execution_slot"]}}
    response = WorkoutSetLogResponse(id=record.id, primary_exercise_id=record.primary_exercise_id,
        exercise_id=record.exercise_id, set_index=record.set_index, reps=record.reps, weight=record.weight,
        set_kind=record.set_kind, parent_set_index=record.parent_set_index, technique=record.technique,
        planned_reps_min=live["recommended_reps_min"], planned_reps_max=live["recommended_reps_max"], planned_weight=weight, rep_delta=None,
        weight_delta=record.weight - weight, next_working_weight=weight,
        guidance=live["guidance"], guidance_rationale=live["guidance_rationale"], decision_trace=trace,
        live_recommendation=live, created_at=record.created_at,
        workout_occurrence_id=occurrence.id, exercise_occurrence_id=record.exercise_occurrence_id, command_id=command_id)
    db.add(WorkoutLogCommand(user_id=current_user.id, command_id=command_id, request_digest=digest,
        workout_occurrence_id=occurrence.id, exercise_occurrence_id=record.exercise_occurrence_id,
        response=response.model_dump(mode="json")))
    db.commit()
    return response


def authored_feedback_projection(db, *, user, occurrence, exercise, supplied_context=None):
    feedback = project_authored_load_feedback(db, user=user, occurrence=occurrence,
        exercise=exercise, supplied_context=supplied_context)
    effective = feedback["effective_sets"]
    working = [row for row in effective if row["parent_set_index"] is None
        and (row["set_kind"] or "work").strip().lower() in {"work", "top", "backoff"}]
    completed = len({row["set_index"] for row in working})
    prescribed = exercise.get("authored_prescription") or {}
    source_sets = prescribed.get("sets") or []
    planned = len(source_sets) if source_sets else int(exercise.get("sets") or 0)
    if source_sets:
        live = typed_tracking_feedback(exercise, completed_sets=completed)
    else:
        live = {"completed_sets": completed, "remaining_sets": max(0, planned - completed),
            "recommended_reps_min": None, "recommended_reps_max": None,
            "recommended_weight": 0.0, "guidance": "Source prescription is unavailable; record actual work without progression advice.",
            "guidance_rationale": "legacy_authored_source_unknown",
            "decision_trace": {"owner": "api.workout_load_state", "numeric_progression": "not_applicable", "source_context": "unknown"}}
    offered = feedback["remaining_sets"] or feedback["next_exposure"]
    live.update(recommended_weight=offered["recommended_weight"], guidance=offered["explanation"],
        guidance_rationale=offered["reason_codes"][0])
    live["decision_trace"]["load_intelligence"] = deepcopy(offered["decision_trace"])
    next_decision = feedback["next_exposure"]
    state = {"exposure_count": next_decision["evidence"]["completed_exposure_count"],
        "qualified_exposure_count": next_decision["evidence"]["comparable_completed_exposure_count"],
        "current_working_weight": next_decision["recommended_weight"],
        "last_progression_action": next_decision["action"],
        "consecutive_under_target_exposures": next_decision["evidence"]["consecutive_underperformance_count"]}
    return {"load_intelligence": feedback, "live_recommendation": live, "exercise_state": state,
        "session_state": {"completed_sets": completed, "remaining_sets": max(0, planned - completed),
            "total_logged_reps": sum(row["reps"] for row in working),
            "total_logged_weight": sum(row["weight"] for row in working)}, "decision_trace": deepcopy(live["decision_trace"])}


def log_authored_set(db, *, current_user, occurrence, exercise, payload, command_id, digest, context):
    prescribed = (exercise.get("authored_prescription") or {}).get("sets") or []
    kind = (payload.set_kind or "work").strip().lower() or "work"
    index = payload.parent_set_index or payload.set_index
    if prescribed and kind != "warmup" and index not in {row["set_index"] for row in prescribed}:
        raise HTTPException(409, "Set does not match the authored working-set prescription")
    before = project_authored_load_feedback(db, user=current_user, occurrence=occurrence,
        exercise=exercise, supplied_context=payload.load_context)
    captured = capture_authored_context(exercise=exercise, context=context, feedback=before, payload=payload)
    # Advice validation precedes the first INSERT, including occurrence creation.
    db.add(occurrence)
    db.flush()
    record = WorkoutSetLog(user_id=current_user.id, workout_id=occurrence.workout_id,
        workout_occurrence_id=occurrence.id, exercise_occurrence_id=exercise["exercise_occurrence_id"],
        primary_exercise_id=exercise.get("primary_exercise_id") or exercise["id"], exercise_id=payload.exercise_id,
        set_index=payload.set_index, reps=payload.reps, weight=payload.weight, rpe=payload.rpe,
        set_kind=kind, parent_set_index=payload.parent_set_index, technique=deepcopy(payload.technique),
        command_id=command_id, request_digest=digest, replay_context=captured)
    db.add(record)
    rebuild_authored_load_state(db, user=current_user)
    projection = authored_feedback_projection(db, user=current_user, occurrence=occurrence,
        exercise=exercise, supplied_context=payload.load_context)
    live = projection["live_recommendation"]
    planned_weight = float(exercise.get("recommended_working_weight") or 0)
    response = WorkoutSetLogResponse(id=record.id, primary_exercise_id=record.primary_exercise_id,
        exercise_id=record.exercise_id, set_index=record.set_index, reps=record.reps, weight=record.weight, rpe=record.rpe,
        set_kind=record.set_kind, parent_set_index=record.parent_set_index, technique=record.technique,
        planned_reps_min=live["recommended_reps_min"], planned_reps_max=live["recommended_reps_max"], planned_weight=planned_weight,
        rep_delta=None, weight_delta=record.weight - planned_weight,
        next_working_weight=projection["load_intelligence"]["next_exposure"]["recommended_weight"],
        guidance=live["guidance"], guidance_rationale=live["guidance_rationale"], decision_trace=projection["decision_trace"],
        live_recommendation=live, load_intelligence=projection["load_intelligence"], exercise_state=projection["exercise_state"],
        created_at=record.created_at, workout_occurrence_id=occurrence.id,
        exercise_occurrence_id=record.exercise_occurrence_id, command_id=command_id)
    db.add(WorkoutLogCommand(user_id=current_user.id, command_id=command_id, request_digest=digest,
        workout_occurrence_id=occurrence.id, exercise_occurrence_id=record.exercise_occurrence_id,
        response=response.model_dump(mode="json")))
    db.commit()
    return response
