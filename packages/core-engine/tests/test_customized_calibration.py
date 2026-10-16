"""Exercise-specific actual-evidence cases with non-prescriptive fixture policy."""
from dataclasses import replace
from datetime import date
import math

import pytest

from core_engine.customized.calibration import calibrate_working_load
from core_engine.customized.models import (
    CompletedSet, CompletedExposure, ExposureTarget, StrengthReport, PolicyApproval,
)
from core_engine.customized.audit import policy_content_hash
from test_customized_planner import exercise, policy, preview, profile, catalog


AS_OF = date(2026, 10, 26)


def target(**overrides):
    return replace(ExposureTarget(7, 11, "rir", 2, 3), **overrides)


def row(index=1, **overrides):
    return replace(CompletedSet(
        record_id=f"receipt-{index}", logical_set_id=f"set-{index}", set_index=index,
        revision=0, state="completed", set_kind="work", parent_set_id=None,
        actual_load=7.0, performed_reps=11, effort_kind="rir", actual_effort=3,
        technique="acceptable", pain=False, load_identity=exercise("horizontal_press").load_identity,
        planned_load=99.0,
    ), **overrides)


def exposure(**overrides):
    return replace(CompletedExposure(
        version="c1-exposure-v1", workout_occurrence_id="workout-1", exercise_occurrence_id="exercise-1",
        performed_on=date(2026, 10, 25), identity=exercise("horizontal_press").load_identity,
        target=target(), required_set_indices=(1, 2), finalized=True, records=(row(1), row(2)),
        provenance_reference="synthetic-effective-history-v1",
    ), **overrides)


def report(**overrides):
    return replace(StrengthReport("synthetic-report-1", "e1rm", exercise("horizontal_press").load_identity,
        date(2026, 10, 24), 13.0, True, "synthetic-user-report", "declared-formula-v1"), **overrides)


def calibrate(**overrides):
    args = dict(exercise=exercise("horizontal_press"), target=target(), policy=policy(),
        as_of=AS_OF, exposures=(), strength_reports=(), allow_provisional_preview=True)
    args.update(overrides)
    return calibrate_working_load(**args)


def test_actual_completed_load_wins_over_prefill_and_self_report():
    result = calibrate(exposures=(exposure(),), strength_reports=(report(),))
    assert result.status == "known_working_load" and result.working_load == 7
    assert result.evidence_ids == ("receipt-1", "receipt-2")
    assert result.origin == "comparable_completed_exposure"
    assert result.unit == "kg" and result.basis == "per_hand"
    assert result.strength_information == ()
    assert len(result.comparison_key) == len(result.evidence_hash) == 64
    assert not result.prescriptive


def test_no_history_is_coached_calibration_without_guessed_load_or_max_test():
    result = calibrate()
    assert result.status == "requires_calibration" and result.working_load is None
    assert "observe_comfortable_technique_and_actual_effort" in result.next_steps
    assert "no_maximal_or_failure_test_required" in result.next_steps


@pytest.mark.parametrize("effort", [None, math.nan])
def test_missing_or_invalid_actual_effort_never_uses_target(effort):
    result = calibrate(exposures=(exposure(records=(row(1, actual_effort=effort), row(2))),))
    assert result.status == "insufficient_history" and result.working_load is None
    assert "actual_effort_unknown_or_invalid" in result.reasons


def test_underchallenging_completed_exposure_requests_recalibration_without_inventing_increment():
    result = calibrate(exposures=(exposure(records=(row(1, actual_effort=6), row(2, actual_effort=6))),))
    assert result.status == "requires_calibration" and result.possibly_underchallenging
    assert result.working_load is None and result.known_baseline == 7
    assert "possibly_requires_recalibration" in result.reasons
    assert result.attainable_next_load == 9


@pytest.mark.parametrize("fields,reason", [
    ({"technique": "poor"}, "technique_not_qualified"),
    ({"pain": True}, "pain_reported"),
    ({"pain": None}, "pain_status_unknown"),
])
def test_quality_or_pain_cannot_be_bypassed_by_older_good_history_or_self_report(fields, reason):
    old = exposure(exercise_occurrence_id="old", performed_on=date(2026, 10, 24))
    latest = exposure(records=(row(1, actual_effort=6, **fields), row(2, actual_effort=6, **fields)))
    result = calibrate(exposures=(old, latest), strength_reports=(report(),))
    assert result.status == "insufficient_history" and result.working_load is None
    assert result.known_baseline is None and reason in result.reasons
    assert not result.possibly_underchallenging and not result.strength_information


def test_effective_correction_replaces_prior_actual_and_void_removes_its_effect():
    records = (row(1), row(2), row(1, record_id="correction-1", revision=1, actual_load=9),
        row(2, record_id="correction-2", revision=1, actual_load=9))
    result = calibrate(exposures=(exposure(records=records),))
    assert result.working_load == 9 and result.evidence_ids == ("correction-1", "correction-2")
    void = row(2, record_id="void-2", revision=2, state="voided")
    result = calibrate(exposures=(exposure(records=records + (void,)),))
    assert result.status == "insufficient_history" and result.working_load is None
    assert "incomplete_effective_exposure" in result.reasons
    assert "void-2" in result.excluded_ids


def test_identical_retries_count_once_and_incomplete_child_warmup_are_not_work():
    records = (row(1), row(2), row(2), row(1, record_id="warm", logical_set_id="warm", set_kind="warmup"),
        row(1, record_id="child", logical_set_id="child", parent_set_id="set-1"))
    result = calibrate(exposures=(exposure(records=records), exposure(records=records)))
    assert result.working_load == 7 and result.completed_sets == 2
    assert result.excluded_ids == ("child", "warm")
    assert calibrate(exposures=(exposure(records=(row(1),)),)).working_load is None


@pytest.mark.parametrize("records,reason", [
    ((row(1), row(2), row(2, actual_load=9)), "conflicting_receipt_identity"),
    ((row(1), row(2), row(1, record_id="duplicate", logical_set_id="other")), "duplicate_working_set_index"),
    ((row(1), row(2), row(2, record_id="conflict", actual_load=9)), "conflicting_set_revision"),
])
def test_ambiguous_duplicate_or_conflicting_correction_abstains(records, reason):
    result = calibrate(exposures=(exposure(records=records),))
    assert result.status == "insufficient_history" and reason in result.reasons


@pytest.mark.parametrize("change", [dict(variant_id="changed"), dict(implement="cable"), dict(rom="partial"), dict(setup="different-grip"), dict(unit="lb"), dict(basis="total_external"), dict(equipment_key="different-machine")])
def test_changed_identity_cannot_inherit_weight(change):
    old = exposure(identity=replace(exposure().identity, **change))
    result = calibrate(exposures=(old,))
    assert result.working_load is None and "no_comparable_exposure" in result.reasons


@pytest.mark.parametrize("basis", ["assistance", "bodyweight", "unknown"])
def test_unsupported_load_semantics_do_not_use_external_load_calibration(basis):
    e = exercise("horizontal_press")
    result = calibrate(exercise=replace(e, load_identity=replace(e.load_identity, basis=basis)), strength_reports=(report(),))
    assert result.status == "unsupported_variant" and result.working_load is None


def test_machine_stack_only_matches_exact_equipment_and_available_stack_values():
    e = exercise("horizontal_press")
    identity = replace(e.load_identity, implement="machine", basis="machine_stack", equipment_key="stack-42")
    e = replace(e, load_identity=identity, attainable_loads=(7, 10, 15))
    exp = exposure(identity=identity, records=tuple(replace(row(i, actual_effort=6), load_identity=identity) for i in (1, 2)))
    result = calibrate(exercise=e, exposures=(exp,))
    assert result.attainable_next_load == 10
    result = calibrate(exercise=replace(e, attainable_loads=(10, 15)), exposures=(exp,))
    assert result.working_load is None and "performed_load_not_in_inventory" in result.reasons


def test_credible_recent_self_report_is_information_only_never_percent_based_working_load():
    result = calibrate(strength_reports=(report(),))
    assert result.status == "requires_calibration" and result.working_load is None
    assert result.origin == "credible_recent_self_report"
    assert result.strength_information == (report(),)
    for bad in (report(credible=False), report(observed_on=date(2025, 1, 1)), report(observed_on=date(2026, 10, 27)), report(kind="e1rm", method_reference="")):
        result = calibrate(strength_reports=(bad,))
        assert not result.strength_information and result.working_load is None


def test_unavailable_inventory_never_fabricates_rounding_grid_or_plate_increment():
    result = calibrate(exercise=replace(exercise("horizontal_press"), attainable_loads=()), exposures=(exposure(),))
    assert result.working_load is None and "attainable_inventory_unknown" in result.reasons
    result = calibrate(exposures=(exposure(records=(row(1, actual_load=8), row(2, actual_load=8))),))
    assert result.working_load is None and "performed_load_not_in_inventory" in result.reasons


def test_last_available_weight_cannot_invent_higher_dumbbell():
    records = (row(1, actual_load=11, actual_effort=6), row(2, actual_load=11, actual_effort=6))
    result = calibrate(exposures=(exposure(records=records),))
    assert result.possibly_underchallenging and result.attainable_next_load is None
    assert "no_higher_attainable_load" in result.reasons


@pytest.mark.parametrize("exp,reason", [
    (exposure(finalized=False), "exposure_not_finalized"),
    (exposure(performed_on=date(2026, 8, 1)), "exposure_stale_or_future"),
    (exposure(performed_on=date(2026, 10, 27)), "exposure_stale_or_future"),
    (exposure(records=(row(1, state="incomplete"), row(2))), "incomplete_effective_exposure"),
    (exposure(records=(row(1, performed_reps=6), row(2))), "performed_reps_below_target"),
    (exposure(records=(row(1, actual_load=9), row(2))), "mixed_working_loads"),
    (exposure(records=(row(1, load_identity=None), row(2))), "recorded_load_identity_incomparable"),
])
def test_incomplete_stale_future_or_incomparable_work_abstains(exp, reason):
    result = calibrate(exposures=(exp,))
    assert result.working_load is None and reason in result.reasons


def test_unknown_effort_can_still_become_self_report_information_but_not_working_load():
    result = calibrate(exposures=(exposure(records=(row(1, actual_effort=None), row(2))),), strength_reports=(report(),))
    assert result.working_load is None and result.strength_information == (report(),)


def test_changed_target_cannot_be_pooled_and_rpe_is_not_converted_from_rir():
    exp = exposure(target=target(effort_kind="rpe10", effort_min=7, effort_max=8))
    assert calibrate(exposures=(exp,)).working_load is None
    exp = exposure(records=(row(1, effort_kind="rpe10", actual_effort=7), row(2)))
    assert "actual_effort_scale_incomparable" in calibrate(exposures=(exp,)).reasons


def test_policy_gates_apply_to_calibration_and_content_bound_approval():
    assert calibrate(policy=None).status == "policy_not_approved"
    assert calibrate(policy=policy(status="disabled")).status == "policy_not_approved"
    assert calibrate(allow_provisional_preview=False).status == "policy_not_approved"
    p = policy()
    approved = replace(p, status="approved", approval=PolicyApproval(policy_content_hash(p), "synthetic-reviewer", "synthetic-decision"))
    result = calibrate(policy=approved, exposures=(exposure(),), allow_provisional_preview=False)
    assert result.working_load == 7 and not result.prescriptive
    altered = replace(approved, calibration=replace(p.calibration, minimum_completed_sets=3))
    assert calibrate(policy=altered, allow_provisional_preview=False).status == "policy_not_approved"


def test_planner_attaches_exercise_specific_calibration_and_hashes_history():
    first = preview(exposures=(exposure(),))
    press = next(e for e in first.sessions[0].exercises if e.exercise.action == "horizontal_press")
    assert press.calibration.working_load == 7
    assert all(e.calibration.status == "requires_calibration" for e in first.sessions[0].exercises if e.exercise.action != "horizontal_press")
    second = preview(exposures=())
    assert first.trace.evidence_hash != second.trace.evidence_hash
    assert first.trace.input_hash != second.trace.input_hash
    assert first.sessions[0].session_id == second.sessions[0].session_id


def test_replay_and_input_objects_remain_immutable():
    e, hist, p = exercise("horizontal_press"), exposure(), policy()
    before = (repr(e), repr(hist), repr(p))
    assert calibrate(exercise=e, exposures=(hist,), policy=p) == calibrate(exercise=e, exposures=(hist,), policy=p)
    assert (repr(e), repr(hist), repr(p)) == before


def test_single_well_formed_set_can_signal_underchallenge_only_when_injected_policy_permits():
    p = policy(calibration=replace(policy().calibration, minimum_completed_sets=1))
    exp = exposure(required_set_indices=(1,), records=(row(1, actual_effort=6),))
    assert calibrate(policy=p, exposures=(exp,)).possibly_underchallenging
    assert not calibrate(exposures=(exp,)).possibly_underchallenging


def test_newer_missing_effort_does_not_restore_older_working_load():
    old = exposure(exercise_occurrence_id="old", performed_on=date(2026, 10, 24))
    new = exposure(records=(row(1, actual_effort=None), row(2)))
    assert calibrate(exposures=(old, new)).working_load is None


def test_conflicting_exposure_snapshots_and_same_date_order_abstain():
    changed = exposure(records=(row(1, actual_load=9), row(2, actual_load=9)))
    assert "conflicting_exposure_identity" in calibrate(exposures=(exposure(), changed)).reasons
    other = replace(changed, exercise_occurrence_id="other")
    assert "latest_exposure_order_unknown" in calibrate(exposures=(exposure(), other)).reasons


def test_unfinalized_flag_and_invalid_performed_date_fail_closed():
    assert calibrate(exposures=(exposure(finalized="false"),)).working_load is None
    assert calibrate(exposures=(exposure(performed_on=None), exposure())).status == "invalid_input"


def test_actual_pounds_remain_pounds_and_cannot_join_kilograms():
    identity = replace(exercise("horizontal_press").load_identity, unit="lb")
    e = replace(exercise("horizontal_press"), load_identity=identity)
    exp = exposure(identity=identity, records=tuple(replace(row(i), load_identity=identity) for i in (1, 2)))
    result = calibrate(exercise=e, exposures=(exp,))
    assert result.working_load == 7 and result.unit == "lb"
    assert calibrate(exposures=(exp,)).working_load is None


def test_standalone_calibration_explicitly_labels_provisional_policy():
    result = calibrate(exposures=(exposure(),))
    assert result.policy_status == "not_approved"
    p = policy()
    approved = replace(p, status="approved", approval=PolicyApproval(policy_content_hash(p), "synthetic-reviewer", "synthetic-decision"))
    assert calibrate(policy=approved).policy_status == "approved"
