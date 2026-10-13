"""Owner-bound persistence/projection of core authored completed-exposure decisions.

Core owns qualification and dose decisions. This adapter owns receipt provenance,
effective-history selection, content-bound advice and the reconstructible cache.
"""
from collections import defaultdict
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace, MappingProxyType
import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import and_

from core_engine.authored_warmups import build_authored_warmup_guidance
from core_engine.load_intelligence import (
    summarize_completed_exercise_exposure, comparison_key_for_exposure,
    decide_next_working_load, decide_remaining_working_load,
)
from .models import AuthoredLoadState, WorkoutOccurrence, WorkoutSetLog
from .schemas import WorkoutLoadContext
from .program_loader import load_program_rule_set, resolve_rule_program_id, load_program_onboarding_package

AUTHORED_PROGRAMS = {"pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"}
OWNER = "api.workout_load_state"
VERSION = "authored-load-state-v1"


def is_authored_occurrence(occurrence):
    return occurrence.program_id in AUTHORED_PROGRAMS


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        allow_nan=False, default=lambda item: item.isoformat()).encode()).hexdigest()


def _rules(occurrence):
    linked = resolve_rule_program_id(occurrence.program_id)
    return load_program_rule_set(linked) if linked else {}


def _source_warmup_protocol(program_id):
    """Read only the existing validated compiled onboarding artifact."""
    try:
        package = load_program_onboarding_package(program_id)
    except (OSError, ValueError):
        return {}, {"owner": "api.program_loader", "program_id": program_id,
            "status": "compiled_source_protocol_unavailable"}
    return deepcopy(package.get("warm_up_protocol") or {}), {
        "owner": "api.program_loader", "program_id": package["program_id"],
        "version": package.get("version"), "status": "compiled_source_protocol",
        "source_provenance": deepcopy(package.get("source_provenance") or {})}


def _warmup_guidance(*, occurrence, exercise, next_decision, context, user_id):
    protocol, provenance = _source_warmup_protocol(occurrence.program_id)
    guidance = build_authored_warmup_guidance(exercise=exercise,
        working_decision=next_decision, load_context=context,
        program_id=occurrence.program_id, source_protocol=protocol)
    guidance["decision_trace"].update(source_protocol_provenance=provenance,
        working_recommendation_id=next_decision["id"],
        working_evidence_revision=next_decision["evidence_revision"])
    evidence_revision = _digest({"working_evidence_revision": next_decision["evidence_revision"],
        "source_lineage": exercise.get("source_lineage"), "guidance": guidance})
    identity = _digest({"owner": OWNER, "scope": "warmup", "user_id": user_id,
        "workout_occurrence_id": occurrence.id,
        "exercise_occurrence_id": exercise["exercise_occurrence_id"],
        "working_recommendation_id": next_decision["id"],
        "evidence_revision": evidence_revision, "guidance": guidance})
    return {**guidance, "id": identity, "evidence_revision": evidence_revision, "scope": "warmup"}


def _variant(exercise):
    variant = exercise.get("performed_variant") or {}
    return variant.get("exercise_id") or variant.get("id") or variant.get("variant_id") or variant.get("option_id")


def resolve_load_context(*, user, supplied=None, records=()):
    if supplied is not None:
        context = supplied.model_dump(mode="json") if isinstance(supplied, WorkoutLoadContext) else deepcopy(supplied)
        return {**context, "version": "declared-load-context-v1",
            "equipment_tags": sorted(user.equipment_profile or []),
            "equipment_provenance": "profile_tags_not_inventory"}
    working = [record for record in records if record.parent_set_index is None
        and (record.set_kind or "work").strip().lower() in {"work", "top", "backoff"}]
    for record in [row for row in working if row.voided_at is None] + [row for row in working if row.voided_at is not None]:
        captured = (record.replay_context or {}).get("load_intelligence") or {}
        if (record.replay_context or {}).get("version") == 2 and captured.get("load_context"):
            return deepcopy(captured["load_context"])
    return {**WorkoutLoadContext().model_dump(mode="json"), "version": "declared-load-context-v1",
        "equipment_tags": sorted(user.equipment_profile or []), "equipment_provenance": "profile_tags_not_inventory"}


def resolve_current_load_context(*, user, supplied=None, records=()):
    """Restore only the current occurrence's effective warmup UI declaration.

    Historical grouping and working-command capture use resolve_load_context.
    Any retained working root, including unknown or voided work, keeps that
    resolver authoritative. A warmup declaration supplies no working evidence.
    """
    context = resolve_load_context(user=user, supplied=supplied, records=records)
    if supplied is not None or any(record.parent_set_index is None
            and (record.set_kind or "work").strip().lower() in {"work", "top", "backoff"}
            for record in records):
        return context
    for record in reversed(records):
        if (record.voided_at is not None or record.parent_set_index is not None
                or record.technique is not None or (record.set_kind or "work").strip().lower() != "warmup"):
            continue
        captured = (record.replay_context or {}).get("load_intelligence") or {}
        if (record.replay_context or {}).get("version") == 2 and captured.get("load_context"):
            return deepcopy(captured["load_context"])
    return context


def effective_receipts(records):
    return [{"id": row.id, "command_id": row.command_id, "set_index": row.set_index, "reps": row.reps, "weight": row.weight,
        "rpe": row.rpe, "set_kind": row.set_kind, "parent_set_index": row.parent_set_index,
        "technique": deepcopy(row.technique), "created_at": row.created_at.isoformat(),
        "amended_at": row.amended_at.isoformat() if row.amended_at else None,
        "supersedes_id": row.supersedes_id,
        "load_context": deepcopy(((row.replay_context or {}).get("load_intelligence") or {}).get("load_context"))
    } for row in records if row.voided_at is None]


def _ordered_records(records):
    by_id = {row.id: row for row in records}
    def root(row):
        visited = set()
        while row.supersedes_id:
            if row.id in visited or row.supersedes_id not in by_id:
                raise HTTPException(409, "Amendment lineage cannot be reconstructed")
            visited.add(row.id)
            row = by_id[row.supersedes_id]
        return row
    return sorted(records, key=lambda row: (root(row).created_at, root(row).id, row.id))


def _snapshot_exercise(occurrence, exercise_occurrence_id):
    matches = [exercise for exercise in occurrence.payload.get("exercises") or []
        if exercise.get("exercise_occurrence_id") == exercise_occurrence_id]
    if len(matches) != 1:
        raise HTTPException(409, "Frozen exercise occurrence cannot be reconstructed")
    return matches[0]


def _summarize(occurrence, exercise, records, context):
    prescribed = deepcopy(exercise.get("authored_prescription") or {"sets": []})
    # Source load semantics remain authoritative, including bodyweight/assistance.
    for key in ("load_semantics", "execution_modifiers"):
        if exercise.get(key) is not None:
            prescribed[key] = deepcopy(exercise[key])
    variant = exercise.get("performed_variant") or {}
    if variant.get("load_semantics") is not None:
        prescribed["load_semantics"] = variant["load_semantics"]
    return summarize_completed_exercise_exposure(
        workout_occurrence_id=occurrence.id, exercise_occurrence_id=exercise["exercise_occurrence_id"],
        prescription=prescribed, effective_sets=effective_receipts(records),
        performed_variant_id=_variant(exercise) or exercise.get("id"), load_context=context,
        source_context={**deepcopy(exercise.get("source_lineage") or {}),
            "load_semantics": variant.get("load_semantics", exercise.get("load_semantics"))})


def _all_groups(db, user):
    occurrences = {row.id: row for row in db.query(WorkoutOccurrence).filter(
        WorkoutOccurrence.user_id == user.id, WorkoutOccurrence.program_id.in_(AUTHORED_PROGRAMS)).all()}
    rows = db.query(WorkoutSetLog).join(WorkoutOccurrence, and_(
        WorkoutSetLog.workout_occurrence_id == WorkoutOccurrence.id,
        WorkoutSetLog.user_id == WorkoutOccurrence.user_id)).filter(
        WorkoutSetLog.user_id == user.id, WorkoutOccurrence.user_id == user.id,
        WorkoutOccurrence.program_id.in_(AUTHORED_PROGRAMS)).all()
    groups = defaultdict(list)
    for row in rows:
        if row.exercise_occurrence_id:
            groups[(row.workout_occurrence_id, row.exercise_occurrence_id)].append(row)
    ordered = []
    for identity, records in groups.items():
        records = _ordered_records(records)
        occurrence = occurrences[identity[0]]
        exercise = _snapshot_exercise(occurrence, identity[1])
        context = resolve_load_context(user=user, records=records)
        anchor = next((row for row in records if row.parent_set_index is None
            and (row.set_kind or "work").strip().lower() in {"work", "top", "backoff"}), records[0])
        # Match occurrence-performed-date-v1. Retain the original receipt audit
        # time as a legacy fallback and deterministic same-date tie-breaker.
        chronology = (occurrence.scheduled_date or anchor.created_at.date(), anchor.created_at)
        ordered.append((chronology, anchor.id, occurrence, exercise, records,
            _summarize(occurrence, exercise, records, context)))
    return sorted(ordered, key=lambda group: (group[0], group[1]))


def _projection_key(exposure):
    return comparison_key_for_exposure(exposure) or _digest({"version": VERSION, "unknown_comparison": True,
        "workout_occurrence_id": exposure["workout_occurrence_id"], "exercise_occurrence_id": exposure["exercise_occurrence_id"]})


@dataclass(frozen=True)
class AuthoredHistorySnapshot:
    """Read history shared only by projections in one response/session.

    Keep the existing grouped receipts, chronology and exposure summaries intact.
    Never retain this object in a session cache, global or command/retry state.
    """
    user_id: str
    groups: tuple
    cohorts: Mapping[str, tuple]
    session: object = field(repr=False, compare=False)


def load_authored_history_snapshot(db, *, user):
    groups = tuple(_all_groups(db, user))
    cohorts = defaultdict(list)
    for group in groups:
        cohorts[_projection_key(group[5])].append(group)
    return AuthoredHistorySnapshot(user_id=user.id, groups=groups,
        cohorts=MappingProxyType({key: tuple(rows) for key, rows in cohorts.items()}), session=db)


def _wrap(decision, *, user_id, occurrence_id, exercise_id, context, exposures, scope, history_scope):
    decision = deepcopy(decision)
    decision["decision_trace"]["history_scope"] = deepcopy(history_scope)
    evidence_revision = _digest({"version": VERSION, "context": context, "history_scope": history_scope,
        "exposures": [{"workout_occurrence_id": item["workout_occurrence_id"],
            "exercise_occurrence_id": item["exercise_occurrence_id"], "evidence_digest": item["evidence_digest"]}
            for item in exposures]})
    identity = _digest({"owner": OWNER, "version": VERSION, "user_id": user_id,
        "workout_occurrence_id": occurrence_id, "exercise_occurrence_id": exercise_id,
        "scope": scope, "evidence_revision": evidence_revision, "decision": decision})
    return {**deepcopy(decision), "id": identity, "evidence_revision": evidence_revision, "scope": scope}


def project_authored_load_feedback(db, *, user, occurrence, exercise, supplied_context=None,
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
    context = context_resolver(user=user, supplied=supplied_context, records=records)
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
    warmup = _warmup_guidance(occurrence=occurrence, exercise=exercise,
        next_decision=next_offered, context=context, user_id=user.id)
    return {"next_exposure": next_offered, "warmup_guidance": warmup,
        "remaining_sets": remaining, "load_context": context, "effective_sets": effective_receipts(records)}


def rebuild_authored_load_state(db, *, user):
    """Rebuild all affected authored cohorts under the caller's user-row lock.

    Including voided roots retains cohort identity and resets a now-incomplete
    projection without deleting audit evidence or promoting an old baseline.
    """
    db.flush()
    groups = _all_groups(db, user)
    cohorts = defaultdict(list)
    for group in groups:
        cohorts[_projection_key(group[5])].append(group)
    for key, cohort in cohorts.items():
        occurrence, exercise, exposure = cohort[-1][2], cohort[-1][3], cohort[-1][5]
        context = exposure["load_context"]
        decision = decide_next_working_load(exposures=[group[5] for group in cohort],
            rule_set=_rules(occurrence), load_context=context)
        state = db.query(AuthoredLoadState).filter_by(user_id=user.id, comparison_key=key).one_or_none()
        if state is None:
            state = AuthoredLoadState(user_id=user.id, comparison_key=key,
                primary_exercise_id=str(exercise.get("primary_exercise_id") or exercise["id"]))
            db.add(state)
        state.source_identity = deepcopy(exercise.get("source_lineage") or {})
        state.state = _state_values(decision, context=context, program_id=occurrence.program_id,
            evidence_revision=_digest([group[5]["evidence_digest"] for group in cohort]))
    db.flush()
    for state in db.query(AuthoredLoadState).filter_by(user_id=user.id).all():
        if state.comparison_key in cohorts:
            continue
        previous = state.state
        context = previous["comparison_context"]
        program_id = previous.get("program_id") or state.source_identity.get("source_program_id")
        decision = decide_next_working_load(exposures=[], rule_set=_rules(SimpleNamespace(program_id=program_id)),
            load_context=context)
        state.state = {**_state_values(decision, context=context, program_id=program_id,
            evidence_revision=_digest([])), "projection_invalidation": {
                "reason": "cohort_no_longer_has_effective_evidence", "prior_evidence_revision": previous["evidence_revision"]}}


def _state_values(decision, *, context, program_id, evidence_revision):
    evidence = decision["evidence"]
    return {"version": VERSION, "owner": OWNER, "program_id": program_id, "comparison_context": deepcopy(context),
        "completed_exposure_count": evidence["completed_exposure_count"],
        "qualified_exposure_count": evidence["comparable_completed_exposure_count"],
        "current_working_weight": decision["recommended_weight"], "known_baseline_weight": decision["known_baseline_weight"],
        "consecutive_under_target_exposures": evidence["consecutive_underperformance_count"],
        "last_progression_action": decision["action"], "evidence": deepcopy(evidence),
        "evidence_revision": evidence_revision, "decision_trace": deepcopy(decision["decision_trace"]),
        "baseline_status": "effective_occurrences_only"}


def capture_authored_context(*, exercise, context, feedback, payload):
    warmup = (payload.set_kind or "work").strip().lower() == "warmup"
    offered = feedback["warmup_guidance"] if warmup else feedback["remaining_sets"] or feedback["next_exposure"]
    if payload.load_recommendation_id is not None and payload.load_recommendation_id != offered["id"]:
        raise HTTPException(409, {"code": "stale_load_recommendation",
            "message": "Load advice changed; refresh and review the current recommendation"})
    prior = [row for row in feedback["effective_sets"] if
        (row["set_kind"] or "work").strip().lower() == "warmup"] if warmup else [
        row for row in feedback["effective_sets"] if row["parent_set_index"] is None
        and (row["set_kind"] or "work").strip().lower() in {"work", "top", "backoff"}]
    captured = {"snapshot_scope": "original_log_command", "load_context": deepcopy(feedback["load_context"]),
        "chosen_weight": payload.weight, "prior_chosen_weight": prior[-1]["weight"] if prior else None,
        "override_reason": payload.load_override_reason,
        "provided_recommendation_id": payload.load_recommendation_id}
    if warmup:
        captured.update(advice_scope="warmup",
            offered_advice_origin="client_acknowledged_guidance" if payload.load_recommendation_id else "server_command_preview",
            offered_warmup_guidance=deepcopy(offered),
            offered_warmup_set=deepcopy(next((row for row in offered["sets"]
                if row["set_index"] == payload.set_index), None)))
    else:
        captured["offered_recommendation"] = deepcopy(offered)
    return {"version": 2, "owner": OWNER, "planned_exercise": deepcopy(exercise),
        "rule_set": deepcopy(context["rule_set"]), "load_intelligence": captured}
