"""Frozen c656988 calibration projection, before response-local batching/indexes.

Test-only equivalence reference; shared core decision/wrapping owners remain
unchanged. Do not use this algorithm as application runtime authority.
"""
from copy import deepcopy
from datetime import datetime, timezone
from fastapi import HTTPException
from core_engine.authored_constraints import refresh_constraints
from core_engine.load_intelligence import decide_next_working_load, decide_remaining_working_load, decide_initial_working_load
from app.workout_initial_calibration import find_calibration, calibration_view, source_scope, setup_scope
from app.workout_load_state import (
    load_authored_history_snapshot, resolve_current_load_context, resolve_load_context,
    _summarize, _projection_key, _rules, _wrap, _warmup_guidance, effective_receipts, OWNER,
)

def pre_perf_calibration_projection(db, *, user, occurrence, exercise, supplied_context=None,
        restore_warmup_context=True, history_snapshot=None):
    """Pure reads with optional current warmup presentation-context restoration.

    Working-command capture disables restoration so an omitted declaration
    cannot turn a warmup's UI settings into actual working load evidence.
    """
    if history_snapshot is None:
        history_snapshot = load_authored_history_snapshot(db, user=user)
    if (history_snapshot.user_id != user.id or history_snapshot.session is not db
            or occurrence.user_id != user.id):
        raise HTTPException(409, "History snapshot does not belong to this projection")
    groups = history_snapshot.groups
    current = next((group for group in groups if group[2].id == occurrence.id
        and group[3]["exercise_occurrence_id"] == exercise["exercise_occurrence_id"]), None)
    records = current[4] if current else []
    # Occurrence advice is bounded by its performed date, even when missed work
    # is entered after later completed exposures. Undated work uses the original
    # working receipt's UTC audit date, or today's pending-receipt date before
    # any work exists; legacy plan dates and warm-ups cannot invent that date.
    has_working_root = any(row.parent_set_index is None
        and (row.set_kind or "work").strip().lower() in {"work", "top", "backoff"} for row in records)
    if occurrence.scheduled_date is not None:
        cutoff_date, cutoff_source = occurrence.scheduled_date, "owner_occurrence_scheduled_date"
    elif current and has_working_root:
        cutoff_date, cutoff_source = current[0][0], "original_working_receipt_audit_date"
    else:
        cutoff_date, cutoff_source = datetime.now(timezone.utc).date(), "pending_working_receipt_utc_date"
    history_scope = {"owner": OWNER, "policy": "occurrence-performed-date-v1",
        "cutoff_date": cutoff_date.isoformat(), "cutoff_source": cutoff_source,
        "inclusive": True}
    groups = [group for group in groups if group[0][0] <= cutoff_date]
    context_resolver = resolve_current_load_context if restore_warmup_context else resolve_load_context
    saved_calibration = find_calibration(db, user_id=user.id, occurrence=occurrence, exercise=exercise,
        supplied_context=supplied_context)
    declaration = supplied_context
    if declaration is None and restore_warmup_context and not has_working_root and saved_calibration is not None:
        declaration = saved_calibration.load_context
    context = context_resolver(user=user, supplied=declaration, records=records)
    # A new declaration never reinterprets already recorded or legacy set context.
    has_work = any(row.voided_at is None and row.parent_set_index is None
        and (row.set_kind or "work").strip().lower() in {"work", "top", "backoff"} for row in records)
    recorded_context = resolve_load_context(user=user, records=records) if has_work else context
    exposure = _summarize(occurrence, exercise, records, recorded_context)
    key = _projection_key(exposure)
    exposures = [group[5] for group in history_snapshot.cohorts.get(key, ()) if group[0][0] <= cutoff_date
        and not (group[2].id == occurrence.id and group[3]["exercise_occurrence_id"] == exercise["exercise_occurrence_id"])]
    exposures.append(exposure)
    if current:
        order = {(group[2].id, group[3]["exercise_occurrence_id"]): index for index, group in enumerate(groups)}
        exposures.sort(key=lambda item: order.get((item["workout_occurrence_id"], item["exercise_occurrence_id"]), len(order)))
    rule_set = _rules(occurrence)
    decision_exposures = exposures if exposure["effective_sets"] else [item for item in exposures
        if not (item["workout_occurrence_id"] == occurrence.id and item["exercise_occurrence_id"] == exercise["exercise_occurrence_id"])]
    next_decision = decide_next_working_load(exposures=decision_exposures, rule_set=rule_set, load_context=context)
    wrapper = dict(user_id=user.id, occurrence_id=occurrence.id, exercise_id=exercise["exercise_occurrence_id"],
        context=context, exposures=exposures, history_scope=history_scope)
    remaining = None
    if not exposure["complete"] and exposure["completed_working_set_count"] > 0:
        remaining = _wrap(decide_remaining_working_load(exposure=exposure, rule_set=rule_set, load_context=context),
            scope="remaining_sets", **wrapper)
    next_offered = _wrap(next_decision, scope="next_exposure", **wrapper)
    saved_view = calibration_view(saved_calibration, occurrence, exercise)
    initial_input = deepcopy(saved_view["input"]) if saved_view else None
    if initial_input and saved_view["requires_confirmation"]:
        initial_input["confirmed"] = False
    # Presence is distinct from progression qualification. Later unresolved source
    # targets must not hide real work merely because the progression key abstains.
    has_initial_history = any(group[5]["effective_sets"]
        and source_scope(group[3]) == source_scope(exercise)
        and setup_scope(group[5]["load_context"]) == setup_scope(context) for group in groups)
    current_exercise = {**deepcopy(exercise), "authored_constraint": refresh_constraints(exercise,
        equipment=user.equipment_profile, restrictions=user.movement_restrictions)}
    initial = decide_initial_working_load(exercise=current_exercise, program_id=occurrence.program_id,
        calibration=initial_input, load_context=context, has_current_work=has_work,
        has_effective_history=has_initial_history or any(item["effective_sets"] for item in decision_exposures),
        today=datetime.now(timezone.utc).date())
    initial.update(action="estimate", recommended_weight=initial["recommended_working_weight"],
        known_baseline_weight=None, prefill_available=initial["status"] == "provisional",
        evidence=deepcopy(next_decision["evidence"]), equipment_feasibility={
            "status": "declared_inventory" if initial["status"] == "provisional" else "unknown",
            "limitations": ["User-declared exact setup; not verified machine calibration"]})
    initial["decision_trace"]["calibration_revision"] = saved_view["revision"] if saved_view else None
    initial["decision_trace"]["calibration_id"] = saved_view["id"] if saved_view else None
    initial_offered = _wrap(initial, scope="initial_calibration", **wrapper)
    warmup = _warmup_guidance(occurrence=occurrence, exercise=current_exercise,
        next_decision=next_offered, context=context, user_id=user.id, provisional_decision=initial_offered)
    return {"next_exposure": next_offered, "initial_estimate": initial_offered, "calibration": saved_view, "warmup_guidance": warmup,
        "remaining_sets": remaining, "load_context": context, "effective_sets": effective_receipts(records)}

