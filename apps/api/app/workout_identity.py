"""Occurrence lineage only: this module has no prescription policy authority."""
from copy import deepcopy
from types import SimpleNamespace
from uuid import UUID, uuid5

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import WorkoutOccurrence, WorkoutPlan

NAMESPACE = UUID("bcb86edc-1d35-4a4d-9b99-adcc32cb7247")


def identified_sessions(plan: WorkoutPlan, snapshots: dict | None = None) -> list[dict]:
    sessions = []
    for slot, raw in enumerate(plan.payload.get("sessions") or []):
        occurrence_id = str(uuid5(NAMESPACE, f"{plan.user_id}/{plan.id}/{plan.week_start.isoformat()}/{slot}"))
        saved = (snapshots or {}).get(occurrence_id)
        session = deepcopy(saved.payload if saved else raw)
        session["workout_occurrence_id"] = occurrence_id
        session["plan_id"] = plan.id
        session["week_start"] = plan.week_start.isoformat()
        session["session_slot"] = slot
        for index, exercise in enumerate(session.get("exercises") or []):
            exercise["exercise_occurrence_id"] = str(uuid5(UUID(occurrence_id), f"exercise-slot/{index}"))
            exercise["execution_slot"] = index
        sessions.append(session)
    return sessions


def identified_plans(db: Session, plans: list[WorkoutPlan]) -> list:
    if not plans:
        return []
    snapshots = {row.id: row for row in db.query(WorkoutOccurrence).filter(
        WorkoutOccurrence.user_id == plans[0].user_id,
        WorkoutOccurrence.plan_id.in_([plan.id for plan in plans]),
    ).all()}
    return [SimpleNamespace(payload={**deepcopy(plan.payload), "sessions": identified_sessions(plan, snapshots)})
            for plan in plans]


def resolve_occurrence(db: Session, user_id: str, reference: str, plans: list[WorkoutPlan]) -> tuple[WorkoutOccurrence, dict]:
    saved = db.query(WorkoutOccurrence).filter_by(id=reference, user_id=user_id).first()
    if saved:
        return saved, deepcopy(saved.payload)
    # Compatibility: a template string means the unique slot in the latest plan,
    # never all weeks. Repeated template slots require an explicit occurrence ID.
    snapshots = {row.id: row for row in db.query(WorkoutOccurrence).filter_by(user_id=user_id).all()}
    for plan in plans:
        matches = [session for session in identified_sessions(plan, snapshots)
                   if reference == session["workout_occurrence_id"]]
        if matches:
            session = matches[0]
            break
    else:
        matches = [session for session in identified_sessions(plans[0], snapshots)
                   if reference == session.get("session_id")] if plans else []
        if len(matches) != 1:
            raise HTTPException(409 if matches else 404, "Use an unambiguous workout occurrence")
        session = matches[0]
        plan = plans[0]
    saved = snapshots.get(session["workout_occurrence_id"])
    if saved:
        return saved, deepcopy(saved.payload)
    occurrence = WorkoutOccurrence(
        id=session["workout_occurrence_id"], user_id=user_id, plan_id=plan.id,
        week_start=plan.week_start, session_slot=session["session_slot"],
        workout_id=session["session_id"], program_id=plan.payload.get("program_template_id"),
        payload=deepcopy(session),
    )
    return occurrence, session


def resolve_exercise(session: dict, exercise_id: str, occurrence_id: str | None) -> dict:
    exercises = session.get("exercises") or []
    matches = [exercise for exercise in exercises if (
        exercise.get("exercise_occurrence_id") == occurrence_id if occurrence_id else exercise.get("id") == exercise_id
    )]
    if len(matches) != 1:
        raise HTTPException(409 if len(matches) > 1 else 404, "Use an unambiguous exercise occurrence")
    exercise = matches[0]
    if exercise_id != exercise.get("id"):
        # Variant/consent modeling is a later package; never guess slot ownership.
        raise HTTPException(409, "Exercise does not match the occurrence")
    return exercise


def occurrence_plan(occurrence: WorkoutOccurrence, session: dict) -> list:
    return [SimpleNamespace(payload={"program_template_id": occurrence.program_id, "sessions": [session]})]
