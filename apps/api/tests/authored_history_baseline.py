"""Frozen pre-optimization projection oracle from main40a10cc.

Test-only reference algorithm; never an application runtime authority.
Unchanged receipt, core decision and wrapping owners are reused, while the
history traversal/filtering remains the exact original implementation.
"""
from datetime import datetime, timezone
from app.workout_load_state import (
    _all_groups, resolve_current_load_context, resolve_load_context, _summarize,
    _projection_key, _rules, _wrap, _warmup_guidance, effective_receipts, OWNER,
)
from core_engine.load_intelligence import decide_next_working_load, decide_remaining_working_load

def legacy_project_authored_load_feedback(db, *, user, occurrence, exercise, supplied_context=None,
        restore_warmup_context=True):
    """Pure reads with optional current warmup presentation-context restoration.

    Working-command capture disables restoration so an omitted declaration
    cannot turn a warmup's UI settings into actual working load evidence.
    """
    groups = _all_groups(db, user)
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
    context = context_resolver(user=user, supplied=supplied_context, records=records)
    # A new declaration never reinterprets already recorded or legacy set context.
    has_work = any(row.voided_at is None and row.parent_set_index is None
        and (row.set_kind or "work").strip().lower() in {"work", "top", "backoff"} for row in records)
    recorded_context = resolve_load_context(user=user, records=records) if has_work else context
    exposure = _summarize(occurrence, exercise, records, recorded_context)
    key = _projection_key(exposure)
    exposures = [group[5] for group in groups if _projection_key(group[5]) == key
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
    warmup = _warmup_guidance(occurrence=occurrence, exercise=exercise,
        next_decision=next_offered, context=context, user_id=user.id)
    return {"next_exposure": next_offered, "warmup_guidance": warmup,
        "remaining_sets": remaining, "load_context": context, "effective_sets": effective_receipts(records)}

