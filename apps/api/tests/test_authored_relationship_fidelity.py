"""Source artifact to scheduler/Today stage-diff checks; no persistence required."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.adaptive_schema import AdaptiveGoldProgramTemplate
from app.program_loader import load_program_template
from app.routers.plan import _prepare_authored_frequency_adapted_template
from app.workout_identity import identified_sessions
from core_engine.authored_redistribution import redistribute_authored_sessions
from core_engine.scheduler import AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY, generate_week_plan
from core_engine.decision_workout_session import build_workout_today_payload
from importers.authored_lineage import annotate_source_relationships


GOLD = Path(__file__).resolve().parents[3] / "programs" / "gold"


def test_compiler_emits_only_explicit_source_links_and_set_parents():
    def slot(number, name, notes="", warmups="1"):
        slot_id = f"synthetic:w1:d1:s{number}"
        return {"exercise": name, "notes": notes, "warm_up_sets": warmups,
            "source_lineage": {"source_slot_id": slot_id, "source_row": number},
            "authored_prescription": {"sets": [{"source_set_id": f"{slot_id}:set1", "intensity_technique": "Dropset"}]}}
    slots = [
        slot(1, "Superset A1: Row"), slot(2, "Superset A2: Press"),
        slot(3, "Leg Curl", "Get warmed up before hack squats later."),
        slot(4, "Hack Squat"), slot(5, "Adjacent but unrelated"),
        slot(6, "A1: Curl"), slot(7, "A2: Extension"),
        slot(8, "No Warm-up", warmups="0.0"),
    ]
    annotate_source_relationships(slots)
    assert [r["kind"] for r in slots[0]["source_relationships"]] == [
        "warmup_to_working", "technique_child", "superset"]
    assert [r["kind"] for r in slots[2]["source_relationships"]][-1] == "primer"
    assert [r["kind"] for r in slots[3]["source_relationships"]][-1] == "primer"
    assert {r["kind"] for r in slots[4]["source_relationships"]} == {
        "warmup_to_working", "technique_child"}
    assert [r["raw"] for r in slots[5]["source_relationships"] if r["kind"] == "superset"] == ["A1"]
    assert [r["raw"] for r in slots[6]["source_relationships"] if r["kind"] == "superset"] == ["A2"]
    assert all(r["kind"] != "warmup_to_working" for r in slots[7]["source_relationships"])


def test_native_artifact_rejects_broken_hard_relationship():
    artifact = json.loads((GOLD / "pure_bodybuilding_phase_1_full_body.json").read_text())
    pair_member = artifact["phases"][0]["weeks"][0]["days"][2]["slots"][1]
    pair_member["source_relationships"] = [
        relation for relation in pair_member["source_relationships"] if relation["kind"] != "superset"]
    with pytest.raises(ValidationError, match="reciprocal source members"):
        AdaptiveGoldProgramTemplate.model_validate(artifact)


def _slots(sessions):
    return [exercise for session in sessions for exercise in session["exercises"]]


def _fingerprint(exercise):
    return (
        exercise["source_lineage"]["source_slot_id"],
        exercise["id"], exercise["sets"],
        exercise["authored_prescription"],
        exercise["source_relationships"],
        exercise["warm_up_sets"], exercise["rest"],
        exercise["last_set_intensity_technique"],
    )


def _assert_lossless(source, result):
    original = _slots(source)
    placed = _slots(result)
    assert len(placed) == len(original)
    assert {e["source_lineage"]["source_slot_id"]: _fingerprint(e) for e in placed} == {
        e["source_lineage"]["source_slot_id"]: _fingerprint(e) for e in original}
    assert [e["source_lineage"]["source_slot_id"] for e in placed] == [
        e["source_lineage"]["source_slot_id"] for e in original]
    positions = {e["source_lineage"]["source_slot_id"]: index for index, e in enumerate(original)}
    for session in result:
        indices = [positions[e["source_lineage"]["source_slot_id"]] for e in session["exercises"]]
        assert indices == sorted(indices)


def _plan(template, days, prior=0, **options):
    return generate_week_plan(
        user_profile={"name": "Synthetic"}, days_available=days,
        split_preference="full_body", program_template=template,
        history=[], phase="build", available_equipment=["barbell", "dumbbell", "bench", "machine", "cable", "bodyweight"],
        prior_generated_weeks=prior, session_time_budget_minutes=45,
        weak_areas=["chest", "hamstrings"], **options,
    )


@pytest.mark.parametrize("phase", [1, 2])
def test_native_authored_order_prescription_and_relationships_reach_today(phase):
    program_id = f"pure_bodybuilding_phase_{phase}_full_body"
    artifact = json.loads((GOLD / f"{program_id}.json").read_text())
    week = artifact["phases"][0]["weeks"][0]
    expected = [slot["source_lineage"]["source_slot_id"] for day in week["days"] for slot in day["slots"]]
    template = load_program_template(program_id)
    template[AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY] = True
    source = _slots(template["authored_weeks"][0]["sessions"])
    assert [e["source_lineage"]["source_slot_id"] for e in source] == expected

    plan = _plan(template, 5)
    planned = _slots(plan["sessions"])
    assert [_fingerprint(e) for e in planned] == [_fingerprint(e) for e in source]
    assert len(plan["sessions"]) == len(week["days"]) == 5
    if phase == 1:
        third = plan["sessions"][2]["exercises"]
        assert [r["kind"] for r in third[0]["source_relationships"] if r["kind"] == "superset"] == ["superset"]
        assert third[0]["source_relationships"][-1]["source_slot_ids"] == [
            third[0]["source_lineage"]["source_slot_id"], third[1]["source_lineage"]["source_slot_id"]]
        fourth = plan["sessions"][3]["exercises"]
        assert any(r["kind"] == "primer" and r["role"] == "primer" for r in fourth[0]["source_relationships"])

    synthetic_plan = SimpleNamespace(user_id="synthetic", id="synthetic-plan", week_start=date(2026, 9, 28), payload=plan)
    identified = identified_sessions(synthetic_plan)
    assert len({e["exercise_occurrence_id"] for s in identified for e in s["exercises"]}) == len(planned)
    for session in identified:
        today = build_workout_today_payload(selected_session=session, mesocycle=None, deload=None,
            completed_sets_by_exercise={}, live_recommendations_by_exercise={}, resume_selected=False,
            daily_quote={})
        assert [_fingerprint(e) for e in today["exercises"]] == [_fingerprint(e) for e in session["exercises"]]


@pytest.mark.parametrize("phase", [1, 2])
@pytest.mark.parametrize("days", [2, 3, 4])
def test_compressed_week_keeps_every_source_slot_set_and_relation(phase, days):
    template = load_program_template(f"pure_bodybuilding_phase_{phase}_full_body")
    source = template["authored_weeks"][0]["sessions"]
    target = [{"day_name": f"Adapted #{index + 1}"} for index in range(days)]
    adapted, trace = redistribute_authored_sessions(source, target)
    replay, _ = redistribute_authored_sessions(source, target)
    assert adapted == replay
    _assert_lossless(source, adapted)
    assert trace["authored_source_week_total_sets"] == trace["authored_redistribution_preserved_weekly_sets"]
    for session in adapted:
        slots = {e["source_lineage"]["source_slot_id"] for e in session["exercises"]}
        for exercise in session["exercises"]:
            for relation in exercise["source_relationships"]:
                if relation["kind"] in {"superset", "primer"}:
                    assert set(relation["source_slot_ids"]) <= slots

    runtime = deepcopy(template)
    runtime[AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY] = True
    runtime["authored_weeks"][0]["sessions"] = adapted
    plan = _plan(runtime, days)
    _assert_lossless(source, plan["sessions"])
    assert all(e["substitution_pressure"] == "none" for e in _slots(plan["sessions"]))


def test_restriction_is_slot_scoped_after_redistribution():
    template = load_program_template("pure_bodybuilding_phase_1_full_body")
    source = template["authored_weeks"][0]["sessions"]
    adapted, _ = redistribute_authored_sessions(source, [{}, {}, {}])
    runtime = deepcopy(template)
    runtime[AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY] = True
    runtime["authored_weeks"][0]["sessions"] = adapted
    plain = _plan(runtime, 3)
    restricted = _plan(runtime, 3, movement_restrictions=["deep_knee_flexion"])
    assert [_fingerprint(e) for e in _slots(plain["sessions"])] == [_fingerprint(e) for e in _slots(restricted["sessions"])]
    assert any(e["authored_constraint"]["status"] != "clear" for e in _slots(restricted["sessions"]))
    assert any(e["authored_constraint"]["status"] == "ready" for e in _slots(restricted["sessions"]))


def test_phase1_bare_pair_survives_four_day_compression():
    template = load_program_template("pure_bodybuilding_phase_1_full_body")
    source = next(
        week["sessions"] for week in template["authored_weeks"]
        if any(e["name"] == "A1: Machine Hip Abduction" for e in _slots(week["sessions"]))
    )
    pair = [e for e in _slots(source) if e["name"] in {
        "A1: Machine Hip Abduction", "A2: Machine Hip Adduction"}]
    assert len(pair) == 2
    links = [next(r for r in e["source_relationships"] if r["kind"] == "superset") for e in pair]
    assert links[0]["source_slot_ids"] == links[1]["source_slot_ids"]
    assert [r["raw"] for r in links] == ["A1", "A2"]
    adapted, _ = redistribute_authored_sessions(source, [{}, {}, {}, {}])
    _assert_lossless(source, adapted)
    assert any(all(e["source_lineage"]["source_slot_id"] in {
        item["source_lineage"]["source_slot_id"] for item in session["exercises"]}
        for e in pair) for session in adapted)


def test_compression_without_source_week_fails_explicitly():
    template = load_program_template("pure_bodybuilding_phase_1_full_body")
    template.pop("authored_weeks")
    with pytest.raises(HTTPException, match="source weeks unavailable") as error:
        _prepare_authored_frequency_adapted_template(
            selected_template_id="pure_bodybuilding_phase_1_full_body",
            program_template=template,
            current_days_available=3,
            active_frequency_adaptation=None,
            training_state={},
            stored_weak_areas=None,
            equipment_profile=None,
            session_time_budget_minutes=None,
            movement_restrictions=None,
            prior_generated_weeks=0,
        )
    assert error.value.status_code == 409
