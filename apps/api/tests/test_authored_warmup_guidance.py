"""Source-bound warmup advice and receipts on explicit disposable databases."""
from copy import deepcopy
from datetime import date, timedelta

import pytest

# This module verifies disposable target identity before importing the app.
from test_authored_load_intelligence import (
    scenario, plan, submit, log, guidance, undo, correct, counts, _race,
    SessionLocal, engine, models, WorkoutOccurrence, WorkoutSetLog,
    CONTEXT, PROGRAM,
)


@pytest.mark.parametrize("source", [None, "", "0", "0.0", "0.00"])
def test_zero_or_absent_source_does_not_invent_rows_or_accept_receipts(scenario, source):
    user, headers, client = scenario
    session = plan(user, warm_up_sets=source)
    before = counts(user)
    preview = guidance(client, headers, session)
    assert preview.status_code == 200, preview.text
    warmup = preview.json()["warmup_guidance"]
    assert warmup["status"] == "none" and warmup["sets"] == []
    rejected = log(client, headers, session, submit(session, set_kind="warmup"))
    assert rejected.status_code == 409, rejected.text
    assert counts(user) == before


@pytest.mark.parametrize("extra", [
    {"set_index": 3}, {"parent_set_index": 1}, {"technique": {"ordinal": 1}}, {"technique": {}},
])
def test_known_count_and_independent_warmup_identity_validate_before_writes(scenario, extra):
    user, headers, client = scenario
    session = plan(user, warm_up_sets="2")
    before = counts(user)
    rejected = log(client, headers, session, submit(session, set_kind="warmup", **extra))
    assert rejected.status_code == 409, rejected.text
    assert counts(user) == before


def test_textual_source_preserves_unknown_count_and_allows_actual_manual_ordinal(scenario):
    user, headers, client = scenario
    session = plan(user, warm_up_sets="1-3 as needed")
    preview = guidance(client, headers, session).json()["warmup_guidance"]
    assert preview["source_count"] == "1-3 as needed"
    assert preview["count"] is None and preview["status"] == "manual" and preview["sets"] == []
    logged = log(client, headers, session, submit(session, 4, set_kind="warmup", weight=12.345, rpe=None))
    assert logged.status_code == 200, logged.text
    assert logged.json()["weight"] == 12.345 and logged.json()["set_index"] == 4
    assert logged.json()["load_intelligence"]["next_exposure"]["evidence"]["completed_exposure_count"] == 0


def test_guidance_uses_compiled_protocol_and_qualified_next_exposure_only_without_writes(scenario):
    user, headers, client = scenario
    week = date.today() - timedelta(days=date.today().weekday())
    prior = plan(user, week - timedelta(days=7), warm_up_sets="2")
    current = plan(user, week, warm_up_sets="2")
    before = counts(user)
    first = guidance(client, headers, current).json()
    assert first["warmup_guidance"]["status"] == "manual"
    assert all(row["suggested_weight"] is None for row in first["warmup_guidance"]["sets"])
    assert counts(user) == before
    for index in (1, 2):
        assert log(client, headers, prior, submit(prior, index)).status_code == 200
    before = counts(user)
    qualified = guidance(client, headers, current).json()
    warmup = qualified["warmup_guidance"]
    assert warmup["status"] == "suggested" and warmup["count"] == 2
    assert [(row["set_index"], row["reps_min"], row["reps_max"]) for row in warmup["sets"]] == [(1, 6, 10), (2, 4, 6)]
    assert [row["suggested_weight"] for row in warmup["sets"]] == [20.5, 28.5]
    assert "~50%" in warmup["source_instructions"] and "~70%" in warmup["source_instructions"]
    assert len(warmup["id"]) == len(warmup["evidence_revision"]) == 64
    trace = warmup["decision_trace"]
    assert trace["working_recommendation_id"] == qualified["next_exposure"]["id"]
    assert trace["source_protocol_provenance"]["program_id"] == PROGRAM
    assert counts(user) == before
    assert guidance(client, headers, current).json()["warmup_guidance"] == warmup
    warmup_receipt = log(client, headers, current, submit(current, 2, set_kind="warmup",
        weight=28.5, load_recommendation_id=warmup["id"]))
    assert warmup_receipt.status_code == 200, warmup_receipt.text
    assert warmup_receipt.json()["planned_weight"] == 28.5
    assert warmup_receipt.json()["weight_delta"] == 0
    assert (warmup_receipt.json()["planned_reps_min"], warmup_receipt.json()["planned_reps_max"]) == (4, 6)
    # Partial current work has remaining-set advice, but cannot substitute that
    # advice for the next-exposure-qualified warmup baseline.
    logged = log(client, headers, current, submit(current, reps=7, rpe=10))
    assert logged.status_code == 200, logged.text
    partial = logged.json()["load_intelligence"]
    assert partial["remaining_sets"]["prefill_available"] is True
    assert partial["warmup_guidance"]["status"] == "manual"
    assert all(row["suggested_weight"] is None for row in partial["warmup_guidance"]["sets"])


def test_warmup_capture_is_separate_and_correction_undo_retry_preserve_canonical_actual(scenario):
    user, headers, client = scenario
    session = plan(user, warm_up_sets="2")
    offered = guidance(client, headers, session).json()["warmup_guidance"]
    payload = submit(session, set_kind="warmup", weight=12.345,
        load_recommendation_id=offered["id"], load_override_reason="Actual warmup chosen")
    result = log(client, headers, session, payload)
    assert result.status_code == 200, result.text
    original = result.json()
    assert original["planned_weight"] is None and original["weight_delta"] is None
    assert original["planned_reps_min"] == 6 and original["planned_reps_max"] == 10
    with SessionLocal() as db:
        row = db.get(WorkoutSetLog, original["id"])
        captured = deepcopy(row.replay_context["load_intelligence"])
        assert captured["offered_warmup_guidance"] == offered
        assert captured["offered_warmup_set"]["set_index"] == 1
        assert "offered_recommendation" not in captured
        assert captured["advice_scope"] == "warmup"
        assert captured["offered_advice_origin"] == "client_acknowledged_guidance"
        assert captured["chosen_weight"] == 12.345
        assert row.weight == 12.345
        assert db.query(models.AuthoredLoadState).filter_by(user_id=user).one().state["completed_exposure_count"] == 0
    changed = correct(client, headers, original["id"], weight=11.111, rpe=None)
    assert changed.status_code == 200, changed.text
    with SessionLocal() as db:
        row = db.get(WorkoutSetLog, changed.json()["effective_set_id"])
        assert row.weight == 11.111 and row.set_kind == "warmup" and row.parent_set_index is None
        assert row.replay_context["load_intelligence"] == captured
    assert undo(client, headers, session).status_code == 200
    before = counts(user)
    assert log(client, headers, session, payload).json() == original
    assert counts(user) == before
    assert guidance(client, headers, session).json()["effective_sets"] == []
    fresh = log(client, headers, session, submit(session, set_kind="warmup", weight=12.345))
    assert fresh.status_code == 200, fresh.text
    with SessionLocal() as db:
        captured = db.get(WorkoutSetLog, fresh.json()["id"]).replay_context["load_intelligence"]
        assert captured["offered_advice_origin"] == "server_command_preview"


def test_old_exact_warmup_retry_precedes_new_source_validation(scenario):
    user, headers, client = scenario
    session = plan(user, warm_up_sets="2")
    payload = submit(session, set_kind="warmup")
    original = log(client, headers, session, payload)
    assert original.status_code == 200, original.text
    assert undo(client, headers, session).status_code == 200
    # Synthetic historical snapshot represents a receipt admitted before the new
    # source guard. Retry preserves the immutable ACK even after it was voided.
    with SessionLocal() as db:
        occurrence = db.get(WorkoutOccurrence, session["workout_occurrence_id"])
        value = deepcopy(occurrence.payload)
        value["exercises"][0]["authored_prescription"]["raw"]["warm_up_sets"] = None
        occurrence.payload = value
        db.commit()
    before = counts(user)
    assert log(client, headers, session, payload).json() == original.json()
    assert log(client, headers, session, submit(session, set_kind="warmup")).status_code == 409
    assert counts(user) == before


def test_stale_warmup_advice_rejects_without_claiming_current_offer(scenario):
    user, headers, client = scenario
    session = plan(user, warm_up_sets="2")
    offered = guidance(client, headers, session).json()["warmup_guidance"]
    assert log(client, headers, session, submit(session)).status_code == 200
    before = counts(user)
    result = log(client, headers, session, submit(session, set_kind="warmup", load_recommendation_id=offered["id"]))
    assert result.status_code == 409, result.text
    assert result.json()["detail"]["code"] == "stale_load_recommendation"
    assert counts(user) == before


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL user-row serialization")
@pytest.mark.parametrize("same_command", [False, True])
def test_postgres_concurrent_warmup_ordinals_return_retry_or_conflict(scenario, same_command):
    user, headers, _ = scenario
    session = plan(user, warm_up_sets="2")
    payload = submit(session, set_kind="warmup")
    second = deepcopy(payload) if same_command else submit(session, set_kind="warmup")
    results = _race([lambda client: log(client, headers, session, payload), lambda client: log(client, headers, session, second)])
    assert sorted(row.status_code for row in results) == ([200, 200] if same_command else [200, 409])
    if same_command:
        assert results[0].json() == results[1].json()
    assert counts(user) == (1, 1, 1, 1)
    assert next(row for row in results if row.status_code == 200).json()["load_intelligence"]["next_exposure"]["evidence"]["completed_exposure_count"] == 0


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL user-row serialization")
def test_postgres_warmup_and_working_ordinal_overlap_retains_both_without_extra_exposure(scenario):
    user, headers, client = scenario
    session = plan(user, warm_up_sets="2")
    payloads = [submit(session, set_kind="warmup"), submit(session)]
    results = _race([lambda other, payload=payload: log(other, headers, session, payload) for payload in payloads])
    assert [row.status_code for row in results] == [200, 200]
    assert counts(user)[:3] == (2, 2, 1)
    with SessionLocal() as db:
        assert all(row.state["completed_exposure_count"] == 0 for row in
            db.query(models.AuthoredLoadState).filter_by(user_id=user).all())
    last = log(client, headers, session, submit(session, 2))
    assert last.status_code == 200, last.text
    assert last.json()["load_intelligence"]["next_exposure"]["evidence"]["completed_exposure_count"] == 1
    with SessionLocal() as db:
        rows = db.query(WorkoutSetLog).filter_by(user_id=user, set_index=1).all()
        assert sorted(row.set_kind for row in rows) == ["warmup", "work"]


@pytest.mark.parametrize("program", [PROGRAM, "pure_bodybuilding_phase_2_full_body"])
def test_read_envelopes_keep_program_protocol_and_receipts_without_write(scenario, program):
    user, headers, client = scenario
    session = plan(user, program=program, warm_up_sets="2.0")
    response = log(client, headers, session, submit(session, set_kind="warmup", weight=12.345))
    assert response.status_code == 200, response.text
    before = counts(user)
    for route in ("progress", "summary"):
        projected = client.get(f"/workout/{session['workout_occurrence_id']}/{route}", headers=headers)
        assert projected.status_code == 200, projected.text
        feedback = projected.json()["exercises"][0]["load_intelligence"]
        assert feedback["warmup_guidance"]["count"] == 2
        assert feedback["warmup_guidance"]["decision_trace"]["source_protocol_provenance"]["program_id"] == program
        assert [(row["set_kind"], row["weight"]) for row in feedback["effective_sets"]] == [("warmup", 12.345)]
        assert feedback["next_exposure"]["evidence"]["completed_exposure_count"] == 0
    assert counts(user) == before


def test_missing_compiled_protocol_abstains_even_with_qualified_working_load(scenario, monkeypatch):
    from app import workout_load_state
    user, headers, client = scenario
    session = plan(user, warm_up_sets="2")
    for index in (1, 2):
        assert log(client, headers, session, submit(session, index)).status_code == 200
    def unavailable(_program):
        raise FileNotFoundError("Synthetic unavailable compiled protocol")
    monkeypatch.setattr(workout_load_state, "load_program_onboarding_package", unavailable)
    before = counts(user)
    feedback = guidance(client, headers, session).json()
    assert feedback["next_exposure"]["prefill_available"] is True
    warmup = feedback["warmup_guidance"]
    assert warmup["status"] == "manual"
    assert all(row["suggested_weight"] is None for row in warmup["sets"])
    assert warmup["decision_trace"]["source_protocol_provenance"]["status"] == "compiled_source_protocol_unavailable"
    assert counts(user) == before


def test_warmup_actual_cannot_become_prior_working_override_or_completed_exposure(scenario):
    user, headers, client = scenario
    session = plan(user, warm_up_sets="2")
    assert log(client, headers, session, submit(session, set_kind="warmup", weight=12.345)).status_code == 200
    result = log(client, headers, session, submit(session, weight=40))
    assert result.status_code == 200, result.text
    with SessionLocal() as db:
        captured = db.get(WorkoutSetLog, result.json()["id"]).replay_context["load_intelligence"]
        assert captured["prior_chosen_weight"] is None
        assert "offered_warmup_guidance" not in captured
        assert "offered_recommendation" in captured
    assert result.json()["live_recommendation"]["completed_sets"] == 1
    assert result.json()["load_intelligence"]["next_exposure"]["evidence"]["completed_exposure_count"] == 0


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL persisted reconstruction")
def test_postgres_warmup_correction_reconstruction_keeps_working_evidence_and_original_offer(scenario):
    from app.workout_history import lock_history_user
    from app.workout_load_state import rebuild_authored_load_state
    user, headers, client = scenario
    session = plan(user, warm_up_sets="2")
    payload = submit(session, set_kind="warmup", weight=12.345)
    warmup = log(client, headers, session, payload)
    assert warmup.status_code == 200, warmup.text
    for index in (1, 2):
        result = log(client, headers, session, submit(session, index))
        assert result.status_code == 200, result.text
    before = guidance(client, headers, session).json()["next_exposure"]
    corrected = correct(client, headers, warmup.json()["id"], weight=11.111)
    assert corrected.status_code == 200, corrected.text
    decision = corrected.json()["load_intelligence"]["next_exposure"]
    assert (decision["action"], decision["recommended_weight"], decision["evidence"]["completed_exposure_count"]) == ("increase", 41, 1)
    assert decision["evidence"] == before["evidence"]
    assert decision["evidence_revision"] != before["evidence_revision"]  # excluded receipt identity still invalidates advice
    with SessionLocal() as db:
        lock_history_user(db, user)
        retained = db.query(models.AuthoredLoadState).filter_by(user_id=user).all()
        states = {row.comparison_key: deepcopy(row.state) for row in retained}
        for row in retained:
            row.state = {**row.state, "completed_exposure_count": 999, "current_working_weight": 999}
        db.flush()
        rebuild_authored_load_state(db, user=db.get(models.User, user))
        db.commit()
        assert {row.comparison_key: row.state for row in db.query(models.AuthoredLoadState).filter_by(user_id=user).all()} == states
        original = db.get(WorkoutSetLog, warmup.json()["id"])
        replacement = db.get(WorkoutSetLog, corrected.json()["effective_set_id"])
        assert original.voided_at is not None and replacement.weight == 11.111
        assert replacement.replay_context["load_intelligence"] == original.replay_context["load_intelligence"]
    assert log(client, headers, session, payload).json() == warmup.json()
    assert guidance(client, headers, session).json()["next_exposure"] == decision
