"""Customized working-load calibration, independent of authored rule IDs.

Reuses M2A's exact-cohort, required-completed-coverage, performed-load and unknown
actual-effort semantics. The M2A authored progression owner is deliberately not
called: it requires source slots and source-specific percentages. Here all
thresholds are injected, no working weight is inferred from a 1RM, and possible
underchallenge is a request to recalibrate, not automatic progression.
"""
from datetime import date
from decimal import Decimal

from .audit import content_hash, policy_content_hash, policy_is_approved
from .models import (
    Exercise, ExposureTarget, SciencePolicy, CompletedExposure, StrengthReport,
    CompletedSet, EvidenceAssessment, CalibrationDecision, finite,
)

VERSION = "customized-calibration-c1-v1"
_NEXT_STEPS = ("observe_comfortable_technique_and_actual_effort", "record_actual_load_reps_and_load_basis",
               "stop_on_pain_or_technique_deterioration", "no_maximal_or_failure_test_required")


def calibration_policy_reasons(policy):
    p = policy.calibration
    if (any(type(v) is not int or v < 0 for v in (p.history_max_age_days, p.self_report_max_age_days))
            or type(p.minimum_completed_sets) is not int or p.minimum_completed_sets < 1
            or not finite(p.underchallenge_rir) or p.underchallenge_rir < 0
            or not finite(p.underchallenge_rpe) or not 0 <= p.underchallenge_rpe <= 10):
        return ("invalid_calibration_policy",)
    return ()


def _identity_supported(identity):
    return (all((identity.variant_id, identity.implement, identity.equipment_key, identity.rom, identity.setup))
            and identity.unit in {"kg", "lb"} and identity.basis in {"per_hand", "total_external", "machine_stack"})


def _target_valid(target):
    return (type(target.reps_min) is int and type(target.reps_max) is int
            and 1 <= target.reps_min <= target.reps_max and target.effort_kind in {"rir", "rpe10"}
            and finite(target.effort_min) and finite(target.effort_max)
            and 0 <= target.effort_min <= target.effort_max
            and (target.effort_kind != "rpe10" or target.effort_max <= 10))


def _effective_records(exposure):
    """Resolve explicit logical-set revision chains before counting work.

    No timestamp ordering, inferred supersession or last-row-wins. Identical
    receipt retries collapse; conflicting receipts/revisions fail closed.
    """
    reasons, by_receipt, by_logical, excluded = [], {}, {}, set()
    for r in exposure.records:
        if (not isinstance(r, CompletedSet) or not r.record_id or not r.logical_set_id
                or type(r.revision) is not int or r.revision < 0 or type(r.set_index) is not int or r.set_index < 1
                or r.state not in {"completed", "incomplete", "voided"}):
            reasons.append("invalid_set_record")
            continue
        if r.record_id in by_receipt:
            if content_hash(r) != content_hash(by_receipt[r.record_id]):
                reasons.append("conflicting_receipt_identity")
            continue
        by_receipt[r.record_id] = r
        by_logical.setdefault(r.logical_set_id, []).append(r)
    effective = []
    for revisions in by_logical.values():
        revision_numbers = [r.revision for r in revisions]
        if len(revision_numbers) != len(set(revision_numbers)):
            reasons.append("conflicting_set_revision")
        if len({r.set_index for r in revisions}) != 1:
            reasons.append("logical_set_index_changed")
        latest = max(revisions, key=lambda r: (r.revision, r.record_id))
        excluded.update(r.record_id for r in revisions if r != latest)
        if latest.state != "completed" or latest.parent_set_id is not None or latest.set_kind != "work":
            excluded.add(latest.record_id)
            continue
        effective.append(latest)
    effective.sort(key=lambda r: (r.set_index, r.record_id))
    if len(effective) != len({r.set_index for r in effective}):
        reasons.append("duplicate_working_set_index")
    return tuple(effective), tuple(sorted(excluded)), reasons


def _assess(exposure, identity, target, policy, as_of):
    records, excluded, reasons = _effective_records(exposure)
    if (exposure.version != "c1-exposure-v1" or not exposure.workout_occurrence_id
            or not exposure.exercise_occurrence_id or not exposure.provenance_reference):
        reasons.append("exposure_identity_or_provenance_missing")
    required = exposure.required_set_indices
    if (not required or any(type(i) is not int or i < 1 for i in required) or len(set(required)) != len(required)):
        reasons.append("required_set_identity_invalid")
    if set(r.set_index for r in records) != set(required):
        reasons.append("incomplete_effective_exposure")
    if exposure.finalized is not True:
        reasons.append("exposure_not_finalized")
    if type(exposure.performed_on) is not date or not 0 <= (as_of - exposure.performed_on).days <= policy.calibration.history_max_age_days:
        reasons.append("exposure_stale_or_future")
    if exposure.identity != identity or exposure.target != target:
        reasons.append("exposure_target_or_variant_incomparable")
    if len(records) < policy.calibration.minimum_completed_sets:
        reasons.append("too_few_qualifying_completed_sets")
    for r in records:
        if r.load_identity != identity:
            reasons.append("recorded_load_identity_incomparable")
        if not finite(r.actual_load) or r.actual_load <= 0:
            reasons.append("actual_load_unknown_or_invalid")
        if type(r.performed_reps) is not int or r.performed_reps < 1:
            reasons.append("actual_reps_unknown_or_invalid")
        elif r.performed_reps < target.reps_min:
            reasons.append("performed_reps_below_target")
        if r.effort_kind != target.effort_kind:
            reasons.append("actual_effort_scale_incomparable")
        if (not finite(r.actual_effort) or r.actual_effort < 0
                or (r.effort_kind == "rpe10" and r.actual_effort > 10)):
            reasons.append("actual_effort_unknown_or_invalid")
        if r.technique != "acceptable":
            reasons.append("technique_not_qualified")
        if r.pain is True:
            reasons.append("pain_reported")
        elif r.pain is not False:
            reasons.append("pain_status_unknown")
    if records and len({r.actual_load for r in records}) != 1:
        reasons.append("mixed_working_loads")
    return EvidenceAssessment(exposure.workout_occurrence_id, exposure.exercise_occurrence_id,
        not reasons, records, excluded, tuple(dict.fromkeys(reasons)))


def calibrate_working_load(*, exercise: Exercise, target: ExposureTarget, policy: SciencePolicy | None,
        as_of: date, exposures: tuple[CompletedExposure, ...] = (), strength_reports: tuple[StrengthReport, ...] = (),
        allow_provisional_preview: bool = False) -> CalibrationDecision:
    """History first, optional strength information second, coached calibration last.

    Attainable loads are an explicitly supplied finite inventory in exactly the
    requested unit/basis. Decimal comparison avoids binary arithmetic/grid drift;
    no new plate, stack or per-hand increment is fabricated. Inventory must be
    qualified by its future upstream owner; C1 neither enumerates real plates nor
    reads a gym database. All returned loads are non-prescriptive draft facts.
    """
    if (not isinstance(exercise, Exercise) or not isinstance(target, ExposureTarget)
            or type(as_of) is not date or (policy is not None and not isinstance(policy, SciencePolicy))
            or any(not isinstance(e, CompletedExposure) for e in exposures)
            or any(not isinstance(r, StrengthReport) for r in strength_reports)):
        raise TypeError("C1 calibration requires typed normalized inputs and an explicit date")
    identity = exercise.load_identity
    evidence_hash = content_hash((exposures, strength_reports, as_of))
    comparison_key = content_hash((VERSION, identity, target))
    assessments = []
    def result(status, reasons, *, working=None, baseline=None, origin="none", under=False,
               next_load=None, records=(), excluded=(), information=()):
        return CalibrationDecision(VERSION, "approved" if approved else "not_approved", status, working, baseline, identity.unit, identity.basis, origin,
            under, next_load, tuple(r.record_id for r in records), tuple(excluded), len(records),
            comparison_key, evidence_hash, policy_content_hash(policy), tuple(dict.fromkeys(reasons)),
            _NEXT_STEPS if status in {"requires_calibration", "insufficient_history"} else (),
            tuple(information), tuple(assessments))
    approved = policy is not None and policy_is_approved(policy)
    if (policy is None or policy.status == "disabled" or policy.status not in {"approved", "provisional"}
            or (not approved and not allow_provisional_preview)):
        return result("policy_not_approved", ("policy_not_approved",))
    if not policy.version or not policy.sources or calibration_policy_reasons(policy) or not _target_valid(target):
        return result("invalid_input", ("invalid_calibration_policy_or_target",))
    if not _identity_supported(identity) or identity.variant_id != exercise.variant_id:
        return result("unsupported_variant", ("load_semantics_or_variant_unsupported",))
    if (any(not finite(w) or w <= 0 for w in exercise.attainable_loads)
            or len(set(exercise.attainable_loads)) != len(exercise.attainable_loads)):
        return result("invalid_input", ("invalid_attainable_inventory",))
    if not exercise.attainable_loads:
        return result("requires_calibration", ("attainable_inventory_unknown",))
    if any(type(e.performed_on) is not date for e in exposures):
        return result("invalid_input", ("invalid_performed_date",))
    distinct, conflict = {}, False
    for e in exposures:
        key = (e.workout_occurrence_id, e.exercise_occurrence_id)
        if key in distinct and content_hash(e) != content_hash(distinct[key]):
            conflict = True
        distinct[key] = e
    if conflict:
        return result("insufficient_history", ("conflicting_exposure_identity",))
    relevant = sorted((e for e in distinct.values() if e.identity == identity),
        key=lambda e: (e.performed_on, e.workout_occurrence_id, e.exercise_occurrence_id))
    # Assess all relevant evidence, but never bypass the newest uncertain/painful
    # exposure with an older good one. Date-only ties cannot establish recency.
    assessments.extend(_assess(e, identity, target, policy, as_of) for e in relevant)
    reasons = []
    if relevant:
        latest = assessments[-1]
        reasons.extend(latest.reasons)
        if len(relevant) > 1 and relevant[-2].performed_on == relevant[-1].performed_on:
            reasons.append("latest_exposure_order_unknown")
        if latest.comparable and not reasons:
            rows = latest.effective_records
            baseline = rows[0].actual_load
            inventory = sorted(Decimal(str(w)) for w in exercise.attainable_loads)
            if Decimal(str(baseline)) not in inventory:
                return result("insufficient_history", ("performed_load_not_in_inventory",), records=rows, excluded=latest.excluded_ids)
            effort_easy = all(r.actual_effort >= policy.calibration.underchallenge_rir if target.effort_kind == "rir"
                              else r.actual_effort <= policy.calibration.underchallenge_rpe for r in rows)
            reps_high = all(r.performed_reps >= target.reps_max for r in rows)
            if effort_easy and reps_high:
                higher = next((float(w) for w in inventory if w > Decimal(str(baseline))), None)
                codes = ["possibly_requires_recalibration"]
                if higher is None:
                    codes.append("no_higher_attainable_load")
                return result("requires_calibration", codes, baseline=baseline, origin="comparable_completed_exposure",
                    under=True, next_load=higher, records=rows, excluded=latest.excluded_ids)
            # Harder/uncertain actual effort cannot justify retaining a working
            # baseline against a different target, even if the weight is known.
            if any(not target.effort_min <= r.actual_effort <= target.effort_max for r in rows):
                reasons.append("actual_effort_outside_target")
            else:
                return result("known_working_load", ("qualified_actual_working_load",), working=baseline, baseline=baseline,
                    origin="comparable_completed_exposure", records=rows, excluded=latest.excluded_ids)
        if any(r in reasons for r in ("pain_reported", "pain_status_unknown", "technique_not_qualified",
                "conflicting_receipt_identity", "conflicting_set_revision", "duplicate_working_set_index", "latest_exposure_order_unknown")):
            return result("insufficient_history", reasons, excluded=latest.excluded_ids)
    else:
        reasons.append("no_comparable_exposure" if exposures else "no_completed_exposure_evidence")
    credible = []
    reports_by_id = {}
    for report in strength_reports:
        if report.report_id in reports_by_id and reports_by_id[report.report_id] != report:
            return result("insufficient_history", (*reasons, "conflicting_strength_report_identity"))
        reports_by_id[report.report_id] = report
    for report in reports_by_id.values():
        if (report.identity == identity and report.report_id and report.kind in {"1rm", "e1rm"}
                and report.credible is True and report.provenance_reference
                and finite(report.load) and report.load > 0 and type(report.observed_on) is date
                and 0 <= (as_of - report.observed_on).days <= policy.calibration.self_report_max_age_days
                and (report.kind != "e1rm" or report.method_reference)):
            credible.append(report)
    credible.sort(key=lambda r: (r.observed_on, r.report_id))
    if credible:
        return result("requires_calibration", (*reasons, "self_report_information_only_no_working_load_conversion"),
            origin="credible_recent_self_report", information=credible)
    return result("insufficient_history" if relevant else "requires_calibration", reasons,
        excluded=assessments[-1].excluded_ids if assessments else ())
