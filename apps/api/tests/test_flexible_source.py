"""Native source admission: regrouping, fabricated dates and dose loss must fail."""
from copy import deepcopy
from datetime import date
import importlib
import inspect

import pytest

from app.program_loader import load_program_template


PHASE1 = "pure_bodybuilding_phase_1_full_body"
PHASE2 = "pure_bodybuilding_phase_2_full_body"


def subject():
    return importlib.import_module("app.flexible_source")


@pytest.mark.parametrize("program_id,slot_count", [(PHASE1, 315), (PHASE2, 310)])
def test_native_source_keeps_fifty_original_sessions_and_all_typed_dose(program_id, slot_count):
    catalog = subject().native_source(program_id)
    admitted = load_program_template(program_id)
    assert catalog["program_id"] == program_id
    assert len(catalog["items"]) == 50
    assert [item["position"] for item in catalog["items"]] == list(range(50))
    assert [(item["source_week"], item["source_session"]) for item in catalog["items"]] == [
        (week, session) for week in range(1, 11) for session in range(1, 6)]
    assert [item["session"] for item in catalog["items"]] == [
        session for week in admitted["authored_weeks"] for session in week["sessions"]]
    exercises = [exercise for item in catalog["items"] for exercise in item["session"]["exercises"]]
    assert len(exercises) == slot_count
    assert len({exercise["source_lineage"]["source_slot_id"] for exercise in exercises}) == slot_count
    assert all(exercise["sets"] == len(exercise["authored_prescription"]["sets"]) for exercise in exercises)
    assert all("date" not in item["session"] and "scheduled_date" not in item["session"] for item in catalog["items"])
    assert "expected_frequency" not in inspect.signature(subject().native_source).parameters
    assert "limited" in catalog["coverage_notice"].lower()
    assert catalog["rest_rules"] == []
    if program_id == PHASE2:
        assert any(s["rep_target"]["kind"] == "amrap" for e in exercises for s in e["authored_prescription"]["sets"])


def test_source_digest_covers_prescription_changes_and_output_is_detached(monkeypatch):
    module = subject()
    template = load_program_template(PHASE1)
    monkeypatch.setattr(module, "load_program_template", lambda _: template)
    first = module.native_source(PHASE1)
    assert len(first["source_digest"]) == 64
    first["items"][0]["session"]["exercises"][0]["notes"] = "detached edit"
    second = module.native_source(PHASE1)
    assert second["source_digest"] == first["source_digest"]
    assert second["items"][0]["session"]["exercises"][0]["notes"] != "detached edit"
    template["authored_weeks"][0]["sessions"][0]["exercises"][0]["notes"] = "reviewed source change"
    assert module.native_source(PHASE1)["source_digest"] != second["source_digest"]


def with_rest(monkeypatch):
    module = subject()
    template = deepcopy(load_program_template(PHASE1))
    before = template["authored_weeks"][4]["sessions"][4]["exercises"][-1]
    after = template["authored_weeks"][5]["sessions"][0]["exercises"][0]
    slots = [before["source_lineage"]["source_slot_id"], after["source_lineage"]["source_slot_id"]]
    rule = {"kind": "minimum_rest", "group_id": "cross-block-rest", "hard": True,
        "source_slot_ids": slots, "minimum_rest_days": 2, "source_row": 1, "raw": "two full rest days"}
    before["source_relationships"].append(deepcopy(rule))
    after["source_relationships"].append(deepcopy(rule))
    monkeypatch.setattr(module, "load_program_template", lambda _: template)
    return module, template, before, after, slots


def test_cross_block_rest_uses_latest_multiday_evidence_and_full_rest_days(monkeypatch):
    module, _, _, _, slots = with_rest(monkeypatch)
    catalog = module.native_source(PHASE1)
    assert catalog["rest_rules"][0]["source_positions"] == [24, 25]
    days = {slots[0]: [date(2026, 10, 25), date(2026, 10, 27)]}
    waiting = module.evaluate_rest(catalog, 25, days, date(2026, 10, 29))
    assert waiting["earliest_day"] == "2026-10-30"
    assert waiting["blockers"][0]["code"] == "hard_rest_wait"
    assert module.evaluate_rest(catalog, 25, days, date(2026, 10, 30))["blockers"] == []
    assert module.evaluate_rest(catalog, 24, {}, date(2026, 10, 29))["blockers"] == []


def test_missing_mandatory_evidence_is_unknown_without_invented_date(monkeypatch):
    module, _, _, _, slots = with_rest(monkeypatch)
    for days in ({}, {slots[0]: []}):
        result = module.evaluate_rest(module.native_source(PHASE1), 25, days, date(2026, 10, 30))
        assert result["earliest_day"] is None
        assert result["blockers"][0]["code"] == "mandatory_evidence_unknown"


@pytest.mark.parametrize("mutation", ["missing_peer", "conflicting_peer", "reverse_order", "unknown_kind"])
def test_invalid_mandatory_relationships_fail_admission(monkeypatch, mutation):
    module, _, before, after, _ = with_rest(monkeypatch)
    if mutation == "missing_peer":
        after["source_relationships"].pop()
    elif mutation == "conflicting_peer":
        after["source_relationships"][-1]["minimum_rest_days"] = 3
    elif mutation == "reverse_order":
        for exercise in (before, after):
            exercise["source_relationships"][-1]["source_slot_ids"].reverse()
    else:
        before["source_relationships"][-1]["kind"] = "unreviewed_mandatory_recovery"
    with pytest.raises(ValueError):
        module.native_source(PHASE1)


@pytest.mark.parametrize("mutation", ["duplicate_slot", "dose_mismatch", "missing_prescription", "missing_source_set"])
def test_invalid_source_identity_or_typed_dose_is_not_admitted(monkeypatch, mutation):
    module = subject()
    template = deepcopy(load_program_template(PHASE1))
    exercises = template["authored_weeks"][0]["sessions"][0]["exercises"]
    if mutation == "duplicate_slot":
        exercises[1]["source_lineage"]["source_slot_id"] = exercises[0]["source_lineage"]["source_slot_id"]
    elif mutation == "dose_mismatch":
        exercises[0]["sets"] += 1
    elif mutation == "missing_prescription":
        exercises[0].pop("authored_prescription")
    else:
        exercises[0]["authored_prescription"]["sets"][0].pop("source_set_id")
    monkeypatch.setattr(module, "load_program_template", lambda _: template)
    with pytest.raises(ValueError):
        module.native_source(PHASE1)


def test_no_declared_rest_does_not_invent_recovery_rule():
    module = subject()
    result = module.evaluate_rest(module.native_source(PHASE1), 1, {}, date(2026, 10, 30))
    assert result == {"blockers": [], "earliest_day": "2026-10-30"}


def test_generated_program_cannot_enter_authored_source_sequence():
    with pytest.raises(ValueError):
        subject().native_source("full_body_v1")


def test_malformed_actual_evidence_fails_closed(monkeypatch):
    module, _, _, _, _ = with_rest(monkeypatch)
    result = module.evaluate_rest(module.native_source(PHASE1), 25, None, date(2026, 10, 30))
    assert result["earliest_day"] is None
    assert result["blockers"][0]["code"] == "mandatory_evidence_unknown"


def test_unknown_mandatory_relationship_in_frozen_catalog_is_a_conflict(monkeypatch):
    module, _, _, _, _ = with_rest(monkeypatch)
    catalog = module.native_source(PHASE1)
    catalog["items"][25]["session"]["exercises"][0]["source_relationships"][-1]["kind"] = "unknown_hard_kind"
    result = module.evaluate_rest(catalog, 25, {}, date(2026, 10, 30))
    assert result["earliest_day"] is None
    assert result["blockers"][0]["code"] == "source_admission_conflict"


def test_soft_unknown_relationship_is_preserved_without_becoming_a_hard_rule(monkeypatch):
    module = subject()
    template = deepcopy(load_program_template(PHASE1))
    relation = {"kind": "unqualified_recovery_advice", "hard": False, "raw": "Advisory only"}
    template["authored_weeks"][0]["sessions"][0]["exercises"][0]["source_relationships"].append(relation)
    monkeypatch.setattr(module, "load_program_template", lambda _: template)
    catalog = module.native_source(PHASE1)
    assert catalog["items"][0]["session"]["exercises"][0]["source_relationships"][-1] == relation
    assert catalog["rest_rules"] == []
