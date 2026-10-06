from copy import deepcopy

import pytest

from core_engine.authored_redistribution import AuthoredAllocationInfeasible, redistribute_authored_sessions


def _exercise(slot, exercise_id="same", sets=2, relationships=None):
    return {
        "id": exercise_id, "name": exercise_id, "sets": sets,
        "source_lineage": {"source_slot_id": slot},
        "source_relationships": relationships or [],
        "authored_prescription": {"sets": [{"source_set_id": f"{slot}:set{i}"} for i in range(1, sets + 1)]},
    }


def _pair(first, second, kind="superset"):
    group = f"{first}:{kind}"
    return [{"kind": kind, "group_id": group, "source_slot_ids": [first, second],
             "role": str(index), "hard": True} for index in (1, 2)]


@pytest.mark.parametrize("days", [2, 3, 4])
def test_redistribution_keeps_order_dose_relationships_and_repeated_slots(days):
    first, second = _pair("slot-1", "slot-2")
    primer, primed = _pair("slot-4", "slot-5", "primer")
    source = [{"name": "source", "exercises": [
        _exercise("slot-1", relationships=[first]), _exercise("slot-2", relationships=[second]),
        _exercise("slot-3"), _exercise("slot-4", relationships=[primer]),
        _exercise("slot-5", relationships=[primed]), _exercise("slot-6"),
    ]}]
    original = deepcopy(source)
    target = [{"day_name": f"Day {index + 1}"} for index in range(days)]
    output, trace = redistribute_authored_sessions(source, target)
    replay, _ = redistribute_authored_sessions(source, target)
    assert output == replay
    assert source == original
    slots = [e["source_lineage"]["source_slot_id"] for session in output for e in session["exercises"]]
    assert slots == [f"slot-{index}" for index in range(1, 7)]
    for session in output:
        indices = [int(e["source_lineage"]["source_slot_id"].split("-")[-1]) for e in session["exercises"]]
        assert indices == sorted(indices)
    assert all(e["id"] == "same" for session in output for e in session["exercises"])
    assert trace["authored_redistribution_preserved_weekly_sets"] == 12
    assert trace["authored_hard_relationship_count"] == 2
    placement = {e["source_lineage"]["source_slot_id"]: index for index, session in enumerate(output) for e in session["exercises"]}
    assert placement["slot-1"] == placement["slot-2"]
    assert placement["slot-4"] == placement["slot-5"]
    assert {e["source_lineage"]["source_slot_id"]: e["authored_prescription"] for session in output for e in session["exercises"]} == {
        e["source_lineage"]["source_slot_id"]: e["authored_prescription"] for e in source[0]["exercises"]}


def test_missing_hard_member_is_explicitly_infeasible():
    first, _ = _pair("slot-1", "missing")
    source = [{"exercises": [_exercise("slot-1", relationships=[first]), _exercise("slot-2")]}]
    with pytest.raises(AuthoredAllocationInfeasible, match="Incomplete authored hard relationship"):
        redistribute_authored_sessions(source, [{}, {}])


def test_hard_group_cannot_be_split_to_fill_target_days():
    first, second = _pair("slot-1", "slot-2")
    source = [{"exercises": [_exercise("slot-1", relationships=[first]), _exercise("slot-2", relationships=[second])]}]
    with pytest.raises(AuthoredAllocationInfeasible, match="fewer units"):
        redistribute_authored_sessions(source, [{}, {}])


def test_explicit_day_limit_can_make_complete_allocation_infeasible():
    source = [{"exercises": [_exercise("slot-1", sets=4), _exercise("slot-2", sets=4)]}]
    with pytest.raises(AuthoredAllocationInfeasible, match="cannot fit"):
        redistribute_authored_sessions(source, [{"max_working_sets": 3}, {"max_working_sets": 3}])


def test_adjacent_unlabeled_exercises_are_not_grouped():
    source = [{"exercises": [_exercise("slot-1"), _exercise("slot-2")]}]
    output, trace = redistribute_authored_sessions(source, [{}, {}])
    assert [len(session["exercises"]) for session in output] == [1, 1]
    assert trace["authored_hard_relationship_count"] == 0


def test_mismatched_hard_link_cannot_be_treated_as_reciprocal():
    first, second = _pair("slot-1", "slot-2")
    second["source_slot_ids"] = ["slot-2", "slot-1"]
    source = [{"exercises": [
        _exercise("slot-1", relationships=[first]),
        _exercise("slot-2", relationships=[second]),
        _exercise("slot-3"),
    ]}]
    with pytest.raises(AuthoredAllocationInfeasible, match="Conflicting authored hard relationship"):
        redistribute_authored_sessions(source, [{}, {}])


def test_malformed_source_slot_cannot_be_silently_dropped():
    source = [{"exercises": [_exercise("slot-1"), None, _exercise("slot-2")]}]
    with pytest.raises(AuthoredAllocationInfeasible, match="Malformed authored source slot"):
        redistribute_authored_sessions(source, [{}, {}])


def _date_sensitive_source():
    return [{"exercises": [
        {**_exercise(f"slot-{index}"), "primary_muscles": ["chest" if index <= 3 else "back"]}
        for index in range(1, 7)
    ]}]


def test_actual_date_gaps_change_grouping_before_workload_balance():
    from datetime import date
    source = _date_sensitive_source()
    target = [{}, {}, {}]
    spread, _ = redistribute_authored_sessions(source, target, selected_dates=[
        date(2026, 9, 29), date(2026, 10, 2), date(2026, 10, 4)])
    consecutive, trace = redistribute_authored_sessions(source, target, selected_dates=[
        date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 1)])
    assert [len(s["exercises"]) for s in spread] == [2, 2, 2]
    assert [len(s["exercises"]) for s in consecutive] == [1, 2, 3]
    assert trace["selected_date_allocation"]["objective"]["consecutive_overlapping_working_sets"] == 2
    replay, replay_trace = redistribute_authored_sessions(source, target, selected_dates=[
        date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 1)])
    assert (replay, replay_trace) == (consecutive, trace)
    assert [e for s in consecutive for e in s["exercises"]] == source[0]["exercises"]


def test_only_consecutive_edge_changes_the_cut_for_mixed_gaps():
    from datetime import date
    output, _ = redistribute_authored_sessions(_date_sensitive_source(), [{}, {}, {}],
        selected_dates=[date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 4)])
    assert [len(s["exercises"]) for s in output] == [3, 1, 2]


def test_neighbor_work_is_evaluated_and_date_only_context_stays_unknown():
    from datetime import date
    output, trace = redistribute_authored_sessions(_date_sensitive_source(), [{}, {}],
        selected_dates=[date(2026, 9, 28), date(2026, 10, 2)],
        previous_context={"date": date(2026, 9, 27), "exercises": [
            {"sets": 6, "primary_muscles": ["chest"]}]})
    assert [len(s["exercises"]) for s in output] == [1, 5]
    assert trace["selected_date_allocation"]["context_completeness"] == {"previous": "known", "next": "unknown"}


def test_explicit_source_minimum_rest_rejects_consecutive_dates_without_pruning():
    from datetime import date
    relation = {"kind": "minimum_rest", "group_id": "rest", "hard": True,
        "source_slot_ids": ["slot-1", "slot-2"], "minimum_rest_days": 1}
    source = [{"exercises": [_exercise("slot-1", relationships=[relation]),
        _exercise("slot-2", relationships=[relation])]}]
    with pytest.raises(AuthoredAllocationInfeasible, match="minimum rest"):
        redistribute_authored_sessions(source, [{}, {}], selected_dates=[date(2026, 9, 29), date(2026, 9, 30)])
    output, _ = redistribute_authored_sessions(source, [{}, {}], selected_dates=[date(2026, 9, 29), date(2026, 10, 2)])
    assert [e for s in output for e in s["exercises"]] == source[0]["exercises"]


def test_unsupported_hard_relationship_is_infeasible_for_selected_dates():
    from datetime import date
    relation = {"kind": "unsupported", "group_id": "unsupported", "hard": True,
        "source_slot_ids": ["slot-1", "slot-2"]}
    source = [{"exercises": [_exercise("slot-1", relationships=[relation]), _exercise("slot-2")]}]
    with pytest.raises(AuthoredAllocationInfeasible, match="Unsupported authored hard"):
        redistribute_authored_sessions(source, [{}, {}], selected_dates=[date(2026, 9, 29), date(2026, 10, 2)])


def test_selected_dates_can_place_five_lossless_days_without_changing_legacy_bounds():
    from datetime import date
    source = _date_sensitive_source()
    output, _ = redistribute_authored_sessions(source, [{}] * 5,
        selected_dates=[date(2026, 9, day) for day in range(28, 31)] + [date(2026, 10, 1), date(2026, 10, 2)])
    assert len(output) == 5
    assert [e for s in output for e in s["exercises"]] == source[0]["exercises"]
    with pytest.raises(AuthoredAllocationInfeasible, match="2–4"):
        redistribute_authored_sessions(source, [{}] * 5)


def test_missing_neighbor_muscle_evidence_is_visible_in_trace():
    from datetime import date
    _, trace = redistribute_authored_sessions(_date_sensitive_source(), [{}, {}],
        selected_dates=[date(2026, 9, 28), date(2026, 10, 2)],
        previous_context={"date": date(2026, 9, 27), "exercises": [{"id": "unknown", "sets": 6}]})
    assert trace["selected_date_allocation"]["neighbor_unknown_primary_muscle_slot_counts"] == {"previous": 1, "next": None}


@pytest.mark.parametrize("kind", ["warmup_to_working", "technique_child"])
def test_internal_set_relationships_remain_on_the_same_source_slot(kind):
    from datetime import date
    relation = {"kind": kind, "group_id": f"slot-1:{kind}", "hard": True,
        "source_slot_ids": ["slot-1"], "source_set_ids": ["slot-1:set1"],
        "role": "parent_working_set", "source_row": 1, "raw": "Synthetic source instruction"}
    source = [{"exercises": [_exercise("slot-1", relationships=[relation]), _exercise("slot-2")]}]
    output, _ = redistribute_authored_sessions(source, [{}, {}], selected_dates=[date(2026, 9, 29), date(2026, 10, 2)])
    assert [e for s in output for e in s["exercises"]] == source[0]["exercises"]


@pytest.mark.parametrize("members,parents", [(["slot-1", "slot-2"], ["slot-1:set1"]), (["slot-1"], ["missing:set1"]),
    (["slot-1"], ["slot-1:set1", "slot-1:set2"])])
def test_internal_technique_relationship_cannot_reference_another_slot_or_multiple_sets(members, parents):
    from datetime import date
    relation = {"kind": "technique_child", "group_id": "invalid", "hard": True,
        "source_slot_ids": members, "source_set_ids": parents}
    source = [{"exercises": [_exercise("slot-1", relationships=[relation]), _exercise("slot-2")]}]
    with pytest.raises(AuthoredAllocationInfeasible, match="internal source-set"):
        redistribute_authored_sessions(source, [{}, {}], selected_dates=[date(2026, 9, 29), date(2026, 10, 2)])


@pytest.mark.parametrize("phase", [1, 2])
@pytest.mark.parametrize("days", [2, 3, 4, 5])
def test_compiled_phase_first_week_retains_all_set_and_slot_relationships_on_actual_dates(phase, days):
    from datetime import date
    import json
    from pathlib import Path
    gold = Path(__file__).resolve().parents[3] / "programs" / "gold" / f"pure_bodybuilding_phase_{phase}_full_body.json"
    artifact = json.loads(gold.read_text())
    source = [{"exercises": [{**slot, "sets": len(slot["authored_prescription"]["sets"])} for slot in day["slots"]]}
        for day in artifact["phases"][0]["weeks"][0]["days"]]
    output, trace = redistribute_authored_sessions(source, [{}] * days,
        selected_dates=[date(2026, 9, 28), date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 1), date(2026, 10, 2)][:days])
    assert [e for s in output for e in s["exercises"]] == [e for s in source for e in s["exercises"]]
    assert trace["authored_redistribution_preserved_weekly_sets"] == sum(e["sets"] for s in source for e in s["exercises"])
