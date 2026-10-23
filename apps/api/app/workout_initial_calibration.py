"""Account/occurrence binding for reports consumed by the existing load owner.

No numeric load policy lives here. Revisions are append-only and do not create
receipts, exposure state, or source-prescription changes.
"""
from copy import deepcopy
import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import func

from .models import AuthoredInitialCalibration


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def source_scope(exercise):
    source = exercise.get("source_lineage") or {}
    prescription = deepcopy(exercise.get("authored_prescription") or {})
    for row in prescription.get("sets") or []:
        row.pop("source_set_id", None)
    return digest({"source": {key: source.get(key) for key in (
        "source_program_id", "source_sha256", "importer_sha256", "artifact_version", "source_session", "source_slot")},
        "source_id": exercise.get("primary_exercise_id") or exercise.get("id"),
        "variant": exercise.get("performed_variant") or {"id": exercise.get("id")},
        "prescription": prescription, "load_semantics": exercise.get("load_semantics"),
        "execution_modifiers": exercise.get("execution_modifiers")})


def setup_scope(context):
    return digest({key: context.get(key) for key in ("unit", "basis", "equipment_key")})


def find_calibration(db, *, user_id, occurrence, exercise, supplied_context=None):
    query = db.query(AuthoredInitialCalibration).filter_by(user_id=user_id, source_scope=source_scope(exercise))
    if supplied_context is not None:
        context = supplied_context.model_dump(mode="json") if hasattr(supplied_context, "model_dump") else supplied_context
        query = query.filter_by(setup_scope=setup_scope(context))
    # Restore this occurrence's report before proposing a later occurrence's report.
    ordered = query.order_by(AuthoredInitialCalibration.revision.desc())
    current = ordered.filter_by(workout_occurrence_id=occurrence.id,
        exercise_occurrence_id=exercise["exercise_occurrence_id"]).first()
    return current or ordered.first()


def calibration_view(row, occurrence, exercise):
    if row is None:
        return None
    needs_confirmation = (row.workout_occurrence_id != occurrence.id or
        row.exercise_occurrence_id != exercise["exercise_occurrence_id"])
    return {"id": row.id, "revision": row.revision, "requires_confirmation": needs_confirmation,
        "input": deepcopy(row.data), "load_context": deepcopy(row.load_context)}


def save_calibration(db, *, user, occurrence, exercise, payload):
    """Caller holds the same user lock used by set/correction commands."""
    body = payload.model_dump(mode="json", exclude_none=True)
    fingerprint = digest({"occurrence": occurrence.id, "payload": body})
    existing = db.query(AuthoredInitialCalibration).filter_by(user_id=user.id, command_id=payload.command_id).one_or_none()
    if existing is not None:
        if existing.command_digest != fingerprint:
            raise HTTPException(409, "Calibration command already used with a different payload")
        return existing
    context = payload.load_context.model_dump(mode="json")
    prior_setup = db.query(AuthoredInitialCalibration).filter_by(user_id=user.id,
        source_scope=source_scope(exercise), setup_scope=setup_scope(context)).first()
    if prior_setup is not None and prior_setup.data.get("setup_details") != payload.calibration.setup_details:
        raise HTTPException(422, "This setup identity already describes different grip, side, range or settings. Use a different equipment/setup identity for the changed setup.")
    revision = (db.query(func.max(AuthoredInitialCalibration.revision)).filter_by(user_id=user.id).scalar() or 0) + 1
    row = AuthoredInitialCalibration(user_id=user.id, revision=revision, command_id=payload.command_id,
        command_digest=fingerprint, source_scope=source_scope(exercise), setup_scope=setup_scope(context),
        workout_occurrence_id=occurrence.id, exercise_occurrence_id=exercise["exercise_occurrence_id"],
        data=payload.calibration.model_dump(mode="json", exclude_none=True), load_context=context)
    db.add(row)
    db.flush()
    return row
