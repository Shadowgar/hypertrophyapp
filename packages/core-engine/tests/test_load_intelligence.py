from copy import deepcopy
import math

import pytest

from core_engine.load_intelligence import (
    comparison_key_for_exposure,
    decide_next_working_load,
    decide_remaining_working_load,
    summarize_completed_exercise_exposure,
)


def prescription():
    return {"version": "authored-prescription-v1", "raw": {"reps": "8-12"}, "sets": [
        {"set_index": index, "source_set_id": f"week1:slot1:set{index}", "set_type": "work",
         "rep_target": {"kind": "reps", "min": 8, "max": 12, "raw": "8-12"},
         "effort_target": {"kind": "rpe", "min": 8, "max": 9, "raw": "8-9"},
         "intensity_technique": None, "rest": "120"}
        for index in (1, 2)]}


def source_context():
    return {"source_program_id": "phase1", "source_sha256": "source-hash", "importer_sha256": "importer-hash",
        "artifact_version": "0.3", "source_session": 1, "source_slot": 1, "source_week": 1,
        "source_slot_id": "phase1:w1:d1:s1"}


def load_context():
    return {"unit": "kg", "display_unit": "kg", "basis": "total_external", "increment": 0.5,
        "increment_unit": "kg", "equipment_key": "test-barbell"}


def rules():
    return {"rule_set_id": "pure_bodybuilding_phase_1_full_body_rules", "version": "0.2.0", "progression_rules": {
        "success_condition": "reach_top_of_rep_range_then_add_load", "on_success": {"action": "increase_load", "percent": 2.5},
        "on_in_range": {"action": "hold_load_chase_reps"},
        "on_under_target": {"action": "hold_or_reduce", "reduce_percent": 2.5, "after_exposures": 2}}}


def receipt(index, *, reps=12, weight=100.0, rpe=9.0, **fields):
    return {"id": f"receipt-{index}", "set_index": index, "reps": reps, "weight": weight, "rpe": rpe,
        "set_kind": "work", "parent_set_index": None, **fields}


def exposure(number=1, *, rows=None, rx=None, context=None, source=None, variant="bench", closure="all_required_sets"):
    rows = [receipt(1), receipt(2)] if rows is None else rows
    return summarize_completed_exercise_exposure(workout_occurrence_id=f"workout-{number}",
        exercise_occurrence_id=f"exercise-{number}", prescription=rx or prescription(), effective_sets=rows,
        performed_variant_id=variant, load_context=load_context() if context is None else context,
        source_context=source_context() if source is None else source, closure=closure)


def decision(*items, context=None):
    return decide_next_working_load(exposures=list(items), rule_set=rules(),
        load_context=load_context() if context is None else context)


def test_individual_set_is_incomplete_and_does_not_add_a_completed_exposure():
    first = exposure(rows=[receipt(1)])
    result = decision(first)
    assert first["complete"] is False
    assert result["action"] == "monitor"
    assert result["evidence"]["completed_exposure_count"] == 0
    assert result["recommended_weight"] is None


def test_exact_required_working_coverage_counts_once_and_ignores_warmup_child_void_retry():
    rows = [receipt(1), receipt(2), receipt(2), receipt(1, id="warm", set_kind="warmup"),
        receipt(1, id="child", parent_set_index=1, set_kind="drop"), receipt(2, id="void", voided_at="2026-10-06")]
    item = exposure(rows=rows)
    result = decision(item, item)
    assert item["complete"] is True
    assert item["completed_working_set_count"] == 2
    assert item["effective_set_ids"] == ["receipt-1", "receipt-2"]
    assert result["evidence"]["completed_exposure_count"] == 1


@pytest.mark.parametrize("rows", [[receipt(2), receipt(3)], [receipt(1), receipt(1, id="duplicate"), receipt(2)]])
def test_count_without_exact_distinct_required_slots_cannot_complete(rows):
    item = exposure(rows=rows)
    assert item["complete"] is False
    assert decision(item)["action"] == "monitor"


def test_explicit_partial_closure_does_not_become_a_completed_exposure():
    item = exposure(closure="partial")
    assert item["completion"] == "partial"
    assert decision(item)["evidence"]["completed_exposure_count"] == 0


def test_qualified_top_range_increases_after_one_complete_exposure_and_uses_actual_load():
    rows = [receipt(1, weight=40), receipt(2, weight=40)]
    for row in rows:
        row["planned_weight"] = 100
    result = decision(exposure(rows=rows))
    assert result["action"] == "increase"
    assert result["recommended_weight"] == 41
    assert result["known_baseline_weight"] == 40
    assert result["prefill_available"] is True
    assert result["evidence"]["completed_exposure_count"] == 1


def test_in_range_complete_exposure_is_a_qualified_hold():
    result = decision(exposure(rows=[receipt(1, reps=10), receipt(2, reps=10)]))
    assert result["action"] == "hold"
    assert result["recommended_weight"] == 100
    assert result["evidence"]["actual_rpe_sufficient"] is True


def test_single_poor_exposure_does_not_decrease_after_many_successful_exposures():
    history = [exposure(number) for number in range(1, 8)]
    bad = exposure(8, rows=[receipt(1, reps=6), receipt(2, reps=7)])
    result = decision(*history, bad)
    assert result["action"] == "hold"
    assert result["recommended_weight"] == 100
    assert result["evidence"]["consecutive_underperformance_count"] == 1


def test_two_consecutive_comparable_completed_failures_use_named_source_reduction():
    bad1 = exposure(rows=[receipt(1, reps=6), receipt(2, reps=7)])
    bad2 = exposure(2, rows=[receipt(1, reps=7), receipt(2, reps=7)])
    result = decision(bad1, bad2)
    assert result["action"] == "decrease"
    assert result["recommended_weight"] == 97.5
    assert result["evidence"]["consecutive_underperformance_count"] == 2


def test_success_between_failures_resets_the_failure_streak():
    bad1 = exposure(rows=[receipt(1, reps=6), receipt(2, reps=7)])
    bad2 = exposure(3, rows=[receipt(1, reps=6), receipt(2, reps=7)])
    assert decision(bad1, exposure(2), bad2)["action"] == "hold"


def test_missing_actual_rpe_stays_unknown_and_monitor_is_not_a_qualified_hold():
    item = exposure(rows=[receipt(1, rpe=None), receipt(2, rpe=None)])
    result = decision(item)
    assert item["effective_sets"][0]["rpe"] is None
    assert result["action"] == "monitor"
    assert result["recommended_weight"] is None
    assert result["known_baseline_weight"] == 100
    assert result["prefill_available"] is False
    assert result["evidence"]["actual_rpe_count"] == 0
    assert result["evidence"]["completed_exposure_count"] == 1


def test_top_reps_at_effort_above_explicit_source_target_does_not_increase():
    assert decision(exposure(rows=[receipt(1, rpe=10), receipt(2, rpe=10)]))["action"] == "monitor"


@pytest.mark.parametrize("basis", ["unknown", "bodyweight", "added_bodyweight", "assistance"])
def test_unsupported_or_unknown_basis_does_not_force_external_load_progression(basis):
    context = {**load_context(), "basis": basis}
    result = decision(exposure(context=context), context=context)
    assert result["action"] == "monitor"
    assert result["recommended_weight"] is None


@pytest.mark.parametrize("kind", ["rir", "text", "unknown"])
def test_unresolved_effort_never_converts_rpe_to_rir(kind):
    rx = prescription()
    for item in rx["sets"]:
        item["effort_target"]["kind"] = kind
    assert decision(exposure(rx=rx))["action"] == "monitor"


def test_amrap_and_mixed_working_loads_monitor_without_invented_aggregate():
    rx = prescription()
    rx["sets"][1]["rep_target"] = {"kind": "amrap", "raw": "AMRAP"}
    assert decision(exposure(rx=rx))["action"] == "monitor"
    mixed = exposure(rows=[receipt(1, weight=100), receipt(2, weight=90)])
    assert decision(mixed)["action"] == "monitor"
    assert mixed["known_baseline_weight"] is None


def test_cohort_excludes_week_and_source_set_ids_but_preserves_repeated_source_positions_and_variants():
    first = exposure()
    other_source = {**source_context(), "source_week": 2, "source_slot_id": "phase1:w2:d1:s1"}
    rx = prescription()
    for item in rx["sets"]:
        item["source_set_id"] = f"week2:set{item['set_index']}"
    second = exposure(2, source=other_source, rx=rx)
    assert comparison_key_for_exposure(first) == comparison_key_for_exposure(second)
    assert comparison_key_for_exposure(first) != comparison_key_for_exposure(exposure(source={**source_context(), "source_slot": 2}))
    assert comparison_key_for_exposure(first) != comparison_key_for_exposure(exposure(variant="confirmed-machine-press"))


def test_unknown_source_metadata_is_not_fabricated_and_equipment_change_does_not_pool_failures():
    assert comparison_key_for_exposure(exposure(source={})) is None
    bad1 = exposure(rows=[receipt(1, reps=6), receipt(2, reps=7)])
    new_context = {**load_context(), "equipment_key": "another-barbell"}
    bad2 = exposure(2, context=new_context, rows=[receipt(1, reps=6), receipt(2, reps=7)])
    assert decision(bad1, bad2, context=new_context)["action"] == "hold"


def test_machine_stack_requires_equipment_identity():
    context = {**load_context(), "basis": "machine_stack", "equipment_key": None}
    assert decision(exposure(context=context), context=context)["action"] == "monitor"


def test_declared_lb_increment_rounds_in_lb_then_returns_canonical_kg():
    context = {**load_context(), "display_unit": "lb", "increment": 5, "increment_unit": "lb"}
    item = exposure(context=context, rows=[receipt(1, weight=81.6466266), receipt(2, weight=81.6466266)])
    result = decision(item, context=context)
    assert result["recommended_weight"] == pytest.approx(83.91458845)
    assert result["equipment_feasibility"]["status"] == "declared_increment"


def test_missing_increment_is_explicit_unverified_compatibility_rounding():
    context = {key: value for key, value in load_context().items() if key not in {"increment", "increment_unit"}}
    result = decision(exposure(context=context), context=context)
    assert result["recommended_weight"] == 102.5
    assert result["equipment_feasibility"]["status"] == "compatibility_increment_unverified"
    assert result["equipment_feasibility"]["limitations"]


def test_current_session_reduction_is_temporary_load_only_and_not_a_completed_exposure():
    item = exposure(rows=[receipt(1, reps=6, rpe=10)])
    before = deepcopy(item)
    result = decide_remaining_working_load(exposure=item, rule_set=rules())
    assert result["action"] == "decrease"
    assert result["recommended_weight"] == 97.5
    assert result["scope"] == "remaining_sets"
    assert result["evidence"]["completed_exposure_count"] == 0
    assert item == before
    assert "recommended_reps_min" not in result
    assert "recommended_reps_max" not in result


@pytest.mark.parametrize("reps,rpe", [(10, 9), (6, 9), (6, None)])
def test_current_session_never_reduces_without_both_below_reps_and_above_explicit_effort(reps, rpe):
    result = decide_remaining_working_load(exposure=exposure(rows=[receipt(1, reps=reps, rpe=rpe)]), rule_set=rules())
    assert result["action"] != "decrease"


def test_undo_or_correction_reconstructs_completion_failure_streak_and_action():
    first = exposure(rows=[receipt(1, reps=6), receipt(2, reps=7)])
    second = exposure(2, rows=[receipt(1, reps=6), receipt(2, reps=7)])
    assert decision(first, second)["action"] == "decrease"
    corrected = exposure(rows=[receipt(1, reps=12), receipt(2, reps=12)])
    assert decision(corrected, second)["action"] == "hold"
    undone = exposure(2, rows=[receipt(1, reps=6)])
    result = decision(first, undone)
    assert result["action"] == "monitor"
    assert result["evidence"]["completed_exposure_count"] == 1


def test_determinism_and_input_prescription_immutability():
    rows, rx, context, source = [receipt(1), receipt(2)], prescription(), load_context(), source_context()
    originals = deepcopy((rows, rx, context, source))
    first = exposure(rows=rows, rx=rx, context=context, source=source)
    second = exposure(rows=list(reversed(rows)), rx=rx, context=context, source=source)
    assert first == second
    assert decision(first) == decision(second)
    assert (rows, rx, context, source) == originals


@pytest.mark.parametrize("value", [math.nan, math.inf, -1])
def test_invalid_actual_numbers_cannot_create_qualified_load_advice(value):
    assert decision(exposure(rows=[receipt(1, weight=value), receipt(2, weight=value)]))["action"] == "monitor"


def test_unsupported_source_rule_or_source_hard_load_returns_monitor():
    invalid = rules()
    invalid["progression_rules"]["success_condition"] = "invented_condition"
    assert decide_next_working_load(exposures=[exposure()], rule_set=invalid, load_context=load_context())["action"] == "monitor"
    rx = {**prescription(), "hard_load_instruction": "source fixed load"}
    assert decision(exposure(rx=rx))["action"] == "monitor"


def test_unknown_or_changed_recorded_load_context_cannot_be_requalified_by_current_context():
    for recorded in ({"unit": "kg", "basis": "unknown"}, {**load_context(), "equipment_key": "another-stack"}):
        item = exposure(rows=[receipt(1, load_context=load_context()), receipt(2, load_context=recorded)])
        assert decision(item)["action"] == "monitor"
        assert "recorded_load_context_incomparable" in item["reason_codes"]


def test_different_source_cohort_between_two_failures_does_not_change_the_same_cohort_streak():
    first = exposure(rows=[receipt(1, reps=6), receipt(2, reps=7)])
    other = exposure(2, source={**source_context(), "source_slot": 2})
    last = exposure(3, rows=[receipt(1, reps=6), receipt(2, reps=7)])
    result = decision(first, other, last)
    assert result["action"] == "decrease"
    assert result["evidence"]["consecutive_underperformance_count"] == 2
    assert result["evidence"]["comparable_completed_exposure_count"] == 2


def test_declared_increment_uses_actual_attainable_load_as_grid_anchor():
    context = {**load_context(), "increment": 3}
    result = decision(exposure(context=context), context=context)
    assert result["recommended_weight"] == 103
    assert (result["recommended_weight"] - result["known_baseline_weight"]) / 3 == 1


def test_invalid_actual_rpe_is_not_reported_as_sufficient_evidence():
    result = decision(exposure(rows=[receipt(1, rpe=-1), receipt(2, rpe=11)]))
    assert result["action"] == "monitor"
    assert result["evidence"]["actual_rpe_sufficient"] is False


def test_conflicting_retry_cannot_replace_the_original_performed_receipt():
    item = exposure(rows=[receipt(1), receipt(1, weight=110), receipt(2)])
    assert item["complete"] is False
    assert "conflicting_retry_receipt" in item["reason_codes"]
    assert decision(item)["action"] == "monitor"


def test_unknown_increment_unit_fails_closed_without_claiming_equipment_feasibility():
    context = {**load_context(), "increment": 5, "increment_unit": None}
    result = decision(exposure(context=context), context=context)
    assert result["action"] == "monitor"
    assert result["prefill_available"] is False
    assert result["equipment_feasibility"]["status"] == "unknown"


def test_new_requested_basis_cannot_present_previous_basis_weight_as_its_baseline():
    changed = {**load_context(), "basis": "per_hand"}
    result = decision(exposure(), context=changed)
    assert result["action"] == "monitor"
    assert result["known_baseline_weight"] is None
    assert "requested_load_context_incomparable" in result["reason_codes"]


@pytest.mark.parametrize("changed", [{"basis": "per_hand"}, {"equipment_key": "other-barbell"}])
def test_remaining_advice_cannot_carry_recorded_weight_into_a_different_requested_context(changed):
    item = exposure(rows=[receipt(1, reps=7, weight=40, rpe=10)])
    result = decide_remaining_working_load(exposure=item, rule_set=rules(),
        load_context={**load_context(), **changed})
    assert result["action"] == "monitor"
    assert result["known_baseline_weight"] is None
    assert result["recommended_weight"] is None
    assert result["prefill_available"] is False
    assert "requested_load_context_incomparable" in result["reason_codes"]


def test_remaining_advice_uses_requested_increment_without_reinterpreting_recorded_load():
    item = exposure(rows=[receipt(1, reps=7, weight=100, rpe=10)])
    result = decide_remaining_working_load(exposure=item, rule_set=rules(),
        load_context={**load_context(), "increment": 3})
    assert result["action"] == "decrease"
    assert result["recommended_weight"] == 97
    assert result["equipment_feasibility"]["increment"] == 3


def test_source_percentage_keeps_exact_half_increment_before_rounding():
    result = decision(exposure(rows=[receipt(1, weight=50), receipt(2, weight=50)]))
    assert result["action"] == "increase"
    assert result["recommended_weight"] == 51.5


@pytest.mark.parametrize("scope", ["next_exposure", "remaining_sets"])
def test_source_reduction_rounds_exact_half_increment_from_actual_baseline(scope):
    if scope == "next_exposure":
        rows = [receipt(1, reps=7, weight=50, rpe=10), receipt(2, reps=7, weight=50, rpe=10)]
        result = decision(exposure(1, rows=rows), exposure(2, rows=rows))
    else:
        result = decide_remaining_working_load(exposure=exposure(rows=[receipt(1, reps=7, weight=50, rpe=10)]),
            rule_set=rules())
    assert result["action"] == "decrease"
    assert result["recommended_weight"] == 48.5


def test_source_percentage_rounds_in_declared_pounds_after_exact_decimal_percentage():
    # This canonical kg input equals 50lb. A 2.5% change is exactly1.25lb;
    # the declared2.5lb step places it at a midpoint, rounded away from zero.
    item = exposure(rows=[receipt(1, weight=22.6796185), receipt(2, weight=22.6796185)])
    result = decision(item, context={**load_context(), "increment": 2.5, "increment_unit": "lb"})
    assert result["recommended_weight"] == 23.813599425


def test_source_percentage_keeps_exact_midpoint_with_unverified_compatibility_increment():
    result = decision(exposure(rows=[receipt(1, weight=50), receipt(2, weight=50)]),
        context={**load_context(), "increment": None})
    assert result["recommended_weight"] == 51.5
    assert result["equipment_feasibility"]["status"] == "compatibility_increment_unverified"


def test_remaining_reduction_retains_compatibility_increment_zero_origin_rounding():
    item = exposure(rows=[receipt(1, reps=7, weight=50, rpe=10)],
        context={**load_context(), "increment": None})
    result = decide_remaining_working_load(exposure=item, rule_set=rules())
    assert result["recommended_weight"] == 49
    assert result["equipment_feasibility"]["grid_anchor_weight"] == 0


@pytest.mark.parametrize("recorded_context", [None, {**load_context(), "basis": "per_hand"}])
def test_incomparable_receipt_context_cannot_supply_a_known_exposure_baseline(recorded_context):
    item = exposure(rows=[receipt(1, load_context=load_context()), receipt(2, load_context=recorded_context)])
    assert "recorded_load_context_incomparable" in item["reason_codes"]
    assert item["known_baseline_weight"] is None
    assert decision(item)["known_baseline_weight"] is None


def test_disclosed_confidence_describes_evidence_and_not_outcome_probability():
    result = decision(exposure())
    assert result["evidence_quality"] == "complete_comparable"
    assert result["decision_trace"]["permission"] == "working_load_only"
    assert result["decision_trace"]["rule_set_id"] == "pure_bodybuilding_phase_1_full_body_rules"
    assert result["decision_trace"]["rule_inputs"]["after_exposures"] == 2


def test_source_prescribed_target_does_not_replace_null_actual_effort_on_one_set():
    item = exposure(rows=[receipt(1, rpe=9), receipt(2, rpe=None)])
    result = decision(item)
    assert result["action"] == "monitor"
    assert result["evidence"]["actual_rpe_count"] == 1
    assert result["evidence"]["actual_rpe_sufficient"] is False
    assert item["effective_sets"][1]["rpe"] is None
