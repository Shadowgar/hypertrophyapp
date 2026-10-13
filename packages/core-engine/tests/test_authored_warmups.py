"""Source fidelity and conservative authored-only warmup load qualification."""
from copy import deepcopy
import json
import math
from pathlib import Path

import pytest

PROGRAMS = ("pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body")
ROOT = Path(__file__).resolve().parents[3]


def protocol(program_id=PROGRAMS[0]):
    return json.loads((ROOT / "programs" / "gold" / f"{program_id}.onboarding.json").read_text())["warm_up_protocol"]


def exercise(count="3", **fields):
    return {"id": "bench", "exercise_occurrence_id": "occurrence-bench", "load_semantics": "external_load",
        "source_lineage": {"source_program_id": PROGRAMS[0], "source_sha256": "source-hash", "source_slot": 1},
        "authored_prescription": {"raw": {"warm_up_sets": count, "reps": "8-12"}, "sets": [
            {"set_index": 1, "rep_target": {"kind": "reps", "min": 8, "max": 12}}]}, **fields}


def context(**fields):
    return {"unit": "kg", "basis": "total_external", "increment": 2.5, "increment_unit": "kg",
        "equipment_key": "bench-bar", **fields}


def decision(**fields):
    return {"scope": "next_exposure", "prefill_available": True, "recommended_weight": 100.0,
        "id": "working-advice", "evidence_revision": "qualified-history", "decision_trace": {
            "owner": "core_engine.load_intelligence", "evidence_digests": ["completed-exposure"]}, **fields}


def build(*, count="3", ex=None, working=None, load=None, source=None, program_id=PROGRAMS[0]):
    from core_engine.authored_warmups import build_authored_warmup_guidance
    return build_authored_warmup_guidance(exercise=exercise(count) if ex is None else ex,
        working_decision=decision() if working is None else working,
        load_context=context() if load is None else load, program_id=program_id,
        source_protocol=protocol(program_id) if source is None else source)


@pytest.mark.parametrize("count,wanted", [
    ("1", [(60.0, 6, 10, 60)]),
    ("2", [(50.0, 6, 10, 50), (70.0, 4, 6, 70)]),
    ("3", [(45.0, 6, 10, 45), (65.0, 4, 6, 65), (85.0, 3, 4, 85)]),
])
@pytest.mark.parametrize("program_id", PROGRAMS)
def test_only_matching_source_ladder_supplies_preserved_count_reps_and_loads(count, wanted, program_id):
    ex = exercise(count)
    ex["source_lineage"]["source_program_id"] = program_id
    result = build(ex=ex, program_id=program_id)
    assert result["status"] == "suggested"
    assert result["count"] == int(count)
    assert [(row["suggested_weight"], row["reps_min"], row["reps_max"], row["percent"]) for row in result["sets"]] == wanted
    assert [row["set_index"] for row in result["sets"]] == list(range(1, int(count) + 1))
    instruction = protocol(program_id)["exercise_specific_warm_up"][int(count) - 1]["instruction"]
    assert instruction in result["source_instructions"]


@pytest.mark.parametrize("count", [None, "", "  ", "0", "0.0", "0.00", 0, 0.0])
def test_absent_or_exact_zero_never_fabricates_warmup_rows(count):
    result = build(count=count)
    assert result["status"] == "none"
    assert result["sets"] == []
    assert result["source_count"] == (None if count is None else str(count))
    assert protocol()["exercise_specific_warm_up_intro"] in result["source_instructions"]


@pytest.mark.parametrize("count", ["1-2", "As needed", "2 warm-ups", "-1", "1.5", "NaN", "Infinity", "1e0", "~3", True])
def test_textual_or_invalid_count_stays_raw_and_manual_without_numeric_interpretation(count):
    result = build(count=count)
    assert result["status"] == "manual"
    assert result["source_count"] == str(count)
    assert result["count"] is None
    assert result["sets"] == []
    assert "source_count_unresolved" in result["reason_codes"]


def test_integral_decimal_preserves_raw_cell_and_exact_count():
    result = build(count=" 2.0 ")
    assert result["source_count"] == " 2.0 "
    assert result["count"] == 2
    assert len(result["sets"]) == 2


def test_raw_authored_count_wins_over_compatibility_count():
    result = build(ex={**exercise("0.0"), "warm_up_sets": "3"})
    assert result["sets"] == []
    assert result["source_count"] == "0.0"


@pytest.mark.parametrize("count", ["4", "20", "1000000"])
def test_count_beyond_source_ladder_never_truncates_or_repeats_three_sets(count):
    result = build(count=count)
    assert result["count"] == int(count)
    assert result["status"] == "manual"
    assert result["sets"] == []
    assert "source_ladder_unavailable" in result["reason_codes"]


@pytest.mark.parametrize("source_mutation", ["percentage", "reps", "label", "missing", "extra"])
def test_altered_protocol_never_interprets_fixed_numeric_recipe(source_mutation):
    source = protocol()
    rows = source["exercise_specific_warm_up"]
    if source_mutation == "percentage":
        rows[0]["instruction"] = rows[0]["instruction"].replace("60%", "80%")
    elif source_mutation == "reps":
        rows[0]["instruction"] = rows[0]["instruction"].replace("6-10", "2-5")
    elif source_mutation == "label":
        rows[0]["label"] = "Other count"
    elif source_mutation == "missing":
        rows.pop()
    else:
        rows.append({"label": "4 Warm-Up Sets Listed", "instruction": "Manual source instruction"})
    result = build(source=source)
    assert result["status"] == "manual"
    assert result["sets"] == []
    assert "source_protocol_unqualified" in result["reason_codes"]
    assert rows[-1]["instruction"] in result["source_instructions"]


def test_missing_protocol_and_generated_program_do_not_gain_authored_source_authority():
    assert build(source={})["sets"] == []
    result = build(source=protocol(), program_id="generated")
    assert result["status"] == "manual"
    assert result["sets"] == []
    assert "authored_program_unqualified" in result["reason_codes"]


@pytest.mark.parametrize("working", [
    {}, decision(prefill_available=False), decision(scope="remaining_sets"),
    decision(recommended_weight=None), decision(recommended_weight=0), decision(recommended_weight=-1),
    decision(recommended_weight=math.nan), decision(recommended_weight=math.inf),
    decision(recommended_weight=True),
])
def test_unqualified_next_exposure_never_falls_back_to_planned_or_known_baseline(working):
    ex = {**exercise(), "recommended_working_weight": 100, "planned_weight": 100}
    result = build(ex=ex, working={**working, "known_baseline_weight": 100})
    assert result["status"] == "manual"
    assert len(result["sets"]) == 3
    assert all(row["suggested_weight"] is None for row in result["sets"])
    assert "qualified_working_load_unavailable" in result["reason_codes"]


@pytest.mark.parametrize("load,reason", [
    (context(increment=None), "declared_increment_unavailable"),
    (context(increment=0), "declared_increment_unavailable"),
    (context(increment=-2.5), "declared_increment_unavailable"),
    (context(increment=math.nan), "declared_increment_unavailable"),
    (context(increment=math.inf), "declared_increment_unavailable"),
    (context(increment=True), "declared_increment_unavailable"),
    (context(increment_unit=None), "declared_increment_unavailable"),
    (context(increment_unit="plates"), "declared_increment_unavailable"),
    (context(unit="lb"), "recorded_load_unit_unknown"),
    (context(basis="unknown"), "load_basis_unknown_or_unsupported"),
    (context(basis="assistance"), "load_basis_unknown_or_unsupported"),
    (context(basis="bodyweight"), "load_basis_unknown_or_unsupported"),
    (context(basis="machine_stack", equipment_key=None), "machine_equipment_identity_unknown"),
    (context(load_semantics="assistance"), "load_semantics_unsupported_or_contradictory"),
])
def test_unknown_increment_unit_basis_or_machine_identity_requires_manual_load(load, reason):
    result = build(load=load)
    assert result["status"] == "manual"
    assert all(row["suggested_weight"] is None for row in result["sets"])
    assert reason in result["reason_codes"]


@pytest.mark.parametrize("basis", ["per_hand", "machine_stack", "total_external"])
def test_load_basis_is_preserved_without_per_hand_total_or_stack_conversion(basis):
    result = build(count="1", working=decision(recommended_weight=20), load=context(basis=basis))
    assert result["status"] == "suggested"
    assert result["sets"][0]["suggested_weight"] == 12.5
    assert result["decision_trace"]["load_context"]["basis"] == basis


@pytest.mark.parametrize("ex,reason", [
    (exercise(load_semantics="bodyweight"), "load_semantics_unsupported_or_contradictory"),
    (exercise(load_semantics="assistance"), "load_semantics_unsupported_or_contradictory"),
    (exercise(load_semantics="unknown"), "load_semantics_unsupported_or_contradictory"),
    (exercise(id=None), "performed_variant_identity_unknown"),
    (exercise(performed_variant={"exercise_id": "confirmed-alternative"}), "performed_variant_warmup_unqualified"),
    (exercise(performed_variant={"load_semantics": "bodyweight"}), "performed_variant_warmup_unqualified"),
    (exercise(hard_load_instruction="use empty bar"), "source_hard_load_instruction"),
])
def test_source_and_variant_boundaries_abstain_even_with_apparently_qualified_working_advice(ex, reason):
    result = build(ex=ex)
    assert result["status"] == "manual"
    assert all(row["suggested_weight"] is None for row in result["sets"])
    assert reason in result["reason_codes"]


@pytest.mark.parametrize("container", ["prescription", "raw", "set"])
def test_source_hard_load_in_nested_prescription_cannot_be_overridden(container):
    ex = exercise()
    rx = ex["authored_prescription"]
    target = rx if container == "prescription" else rx["raw"] if container == "raw" else rx["sets"][0]
    target["load_target"] = "fixed source load"
    result = build(ex=ex)
    assert "source_hard_load_instruction" in result["reason_codes"]
    assert all(row["suggested_weight"] is None for row in result["sets"])


def test_amrap_target_remains_manual_and_never_uses_numeric_compatibility_reps():
    ex = exercise(reps_min=8, reps_max=12)
    ex["authored_prescription"]["sets"][0]["rep_target"] = {"kind": "amrap", "raw": "AMRAP"}
    result = build(ex=ex)
    assert result["status"] == "manual"
    assert "rep_target_unresolved_or_amrap" in result["reason_codes"]
    assert all(row["suggested_weight"] is None for row in result["sets"])


@pytest.mark.parametrize("weight,increment,wanted", [(23.0, 2.5, 13.0), (2.45, 0.28, 1.33)])
def test_declared_grid_is_anchored_on_working_load_with_decimal_midpoint_rounding(weight, increment, wanted):
    result = build(count="1", working=decision(recommended_weight=weight), load=context(increment=increment))
    assert result["status"] == "suggested"
    assert result["sets"][0]["suggested_weight"] == wanted
    assert result["equipment_feasibility"]["grid_anchor_weight"] == weight


def test_lb_increment_returns_exact_canonical_kg_without_changing_source_percentages():
    result = build(count="1", working=decision(recommended_weight=45.359237),
        load=context(increment=5, increment_unit="lb"))
    assert result["status"] == "suggested"
    assert result["sets"][0]["suggested_weight"] == 27.2155422
    assert result["sets"][0]["percent"] == 60


@pytest.mark.parametrize("weight,increment", [(1, 5), (5, 100), (5, 5)])
def test_unattainable_zero_negative_or_equal_working_warmup_abstains_without_minimum_load(weight, increment):
    result = build(working=decision(recommended_weight=weight), load=context(increment=increment))
    assert result["status"] == "manual"
    assert len(result["sets"]) == 3
    assert all(row["suggested_weight"] is None for row in result["sets"])
    assert "attainable_warmup_load_unresolved" in result["reason_codes"]


def test_equal_rounded_rows_do_not_deduplicate_source_count():
    result = build(working=decision(recommended_weight=10), load=context(increment=3))
    assert result["status"] == "suggested"
    assert [row["suggested_weight"] for row in result["sets"]] == [4, 7, 7]


def test_trace_preserves_protocol_and_advice_provenance_is_deterministic_and_cannot_mutate_inputs():
    inputs = {"exercise": exercise(), "working_decision": decision(), "load_context": context(),
        "source_protocol": protocol(), "program_id": PROGRAMS[0]}
    original = deepcopy(inputs)
    from core_engine.authored_warmups import build_authored_warmup_guidance
    result = build_authored_warmup_guidance(**inputs)
    assert result == build_authored_warmup_guidance(**inputs)
    assert inputs == original
    trace = result["decision_trace"]
    assert trace["owner"] == "core_engine.authored_warmups"
    assert trace["source_protocol"] == inputs["source_protocol"]
    assert trace["source_lineage"] == inputs["exercise"]["source_lineage"]
    assert trace["working_recommendation_id"] == "working-advice"
    assert trace["working_evidence_revision"] == "qualified-history"
    assert len(trace["source_protocol_digest"]) == 64
    result["decision_trace"]["source_protocol"]["exercise_specific_warm_up"][0]["instruction"] = "edited output"
    result["decision_trace"]["load_context"]["basis"] = "edited output"
    assert inputs == original


def test_evidence_correction_changes_warmup_trace_even_if_weights_remain_the_same():
    before = build()
    after = build(working=decision(evidence_revision="corrected-history"))
    assert before["sets"] == after["sets"]
    assert before["decision_trace"] != after["decision_trace"]


@pytest.mark.parametrize("location", ["exercise", "prescription", "context"])
def test_explicit_per_hand_semantics_cannot_be_reinterpreted_as_total_external(location):
    ex, load = exercise(), context()
    if location == "context":
        load["load_semantics"] = "per_hand"
    elif location == "prescription":
        ex["authored_prescription"]["load_semantics"] = "per_hand"
    else:
        ex["load_semantics"] = "per_hand"
    result = build(ex=ex, load=load)
    assert result["status"] == "manual"
    assert "load_semantics_unsupported_or_contradictory" in result["reason_codes"]
    assert all(row["suggested_weight"] is None for row in result["sets"])


@pytest.mark.parametrize("location", ["weight", "increment"])
def test_rejected_nonfinite_input_keeps_trace_json_safe(location):
    result = build(working=decision(recommended_weight=math.nan) if location == "weight" else decision(),
        load=context(increment=math.inf) if location == "increment" else context())
    assert result["status"] == "manual"
    json.dumps(result, allow_nan=False)


def test_absent_source_raw_cell_does_not_inherit_compatibility_warmup_count():
    result = build(ex={**exercise(None), "warm_up_sets": "3"})
    assert result["status"] == "none"
    assert result["source_count"] is None
    assert result["sets"] == []
