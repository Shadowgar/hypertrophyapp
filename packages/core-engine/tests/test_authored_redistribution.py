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
