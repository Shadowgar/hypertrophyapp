"""Initial estimates remain account/setup scoped reports, never performed work."""
from copy import deepcopy
from datetime import date, timedelta
from uuid import uuid4

import pytest

# This helper verifies explicit disposable DB identity before importing the app.
from test_authored_load_intelligence import (
    CONTEXT, SessionLocal, WorkoutPlan, WorkoutSetLog, models,
    scenario, plan as _base_plan, submit, log, guidance, undo, correct, counts, engine, _race,
    User, identified_sessions,
)


def plan(user, *args, **kwargs):
    """Explicit available barbell source/setup; shared progression fixture lacks it."""
    session = _base_plan(user, *args, **kwargs)
    with SessionLocal() as db:
        db.get(User, user).equipment_profile = ["barbell"]
        row = db.get(WorkoutPlan, session["plan_id"])
        payload = deepcopy(row.payload)
        exercise = payload["sessions"][0]["exercises"][0]
        exercise["equipment_tags"] = ["barbell"]
        if exercise.get("performed_variant"):
            exercise["performed_variant"]["equipment_tags"] = ["barbell"]
        row.payload = payload
        db.commit()
        return identified_sessions(row)[0]


def calibration_payload(session, **changes):
    calibration = {
        "method": "known_1rm", "load": 100, "unit": "kg",
        "observed_date": date.today().isoformat(), "confirmed": True,
        "variant_id": "same-catalog",
        "setup_details": "Bilateral full ROM, straight bar, standard grip, rack setting 4",
        "attainable": {"unit": "kg", "min": 5, "step": 2.5, "max": 100},
    }
    calibration.update(changes)
    return {
        "command_id": str(uuid4()),
        "exercise_occurrence_id": session["exercises"][0]["exercise_occurrence_id"],
        "load_context": deepcopy(CONTEXT), "calibration": calibration,
    }


def save(client, headers, session, payload=None):
    return client.post(f"/workout/{session['workout_occurrence_id']}/initial-calibration",
        headers=headers, json=payload or calibration_payload(session))


def test_calibration_save_replay_reload_never_fabricates_work(scenario):
    user, headers, client = scenario
    session = plan(user)
    prescription = deepcopy(session["exercises"][0]["authored_prescription"])
    payload = calibration_payload(session)
    response = save(client, headers, session, payload)
    assert response.status_code == 200, response.text
    result = response.json()
    estimate = result["initial_estimate"]
    assert estimate["status"] == "provisional", estimate["reason_codes"]
    assert estimate["scope"] == "initial_calibration"
    assert estimate["prefill_available"] is True
    # Source target 8-12 / RPE 8-9 => 100 / (1 + 14/30), floored on declared grid.
    assert estimate["recommended_weight"] == 67.5
    assert result["calibration"]["input"] == payload["calibration"]
    assert result["calibration"]["requires_confirmation"] is False
    assert save(client, headers, session, payload).json() == result
    reload = guidance(client, headers, session)
    assert reload.status_code == 200, reload.text
    assert reload.json()["calibration"] == result["calibration"]
    assert reload.json()["initial_estimate"] == estimate
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).filter_by(user_id=user).count() == 0
        stored = db.query(WorkoutPlan).filter_by(user_id=user).one().payload
        assert stored["sessions"][0]["exercises"][0]["authored_prescription"] == prescription


def calibration_count(user):
    with SessionLocal() as db:
        return db.query(models.AuthoredInitialCalibration).filter_by(user_id=user).count()


def test_command_replay_preserves_current_revision_and_payload_conflicts(scenario):
    user, headers, client = scenario
    session = plan(user)
    original = calibration_payload(session)
    first = save(client, headers, session, original)
    assert first.status_code == 200, first.text
    changed = calibration_payload(session, load=80)
    second = save(client, headers, session, changed)
    assert second.status_code == 200, second.text
    assert second.json()["calibration"]["revision"] == first.json()["calibration"]["revision"] + 1
    assert second.json()["calibration"]["id"] != first.json()["calibration"]["id"]
    # A calibration command retains its original report but reprojects current advice.
    # Unlike a performed-set receipt, retry must not re-offer an obsolete estimate.
    assert save(client, headers, session, original).json() == second.json()
    conflict = deepcopy(original)
    conflict["calibration"]["load"] = 81
    assert save(client, headers, session, conflict).status_code == 409
    assert calibration_count(user) == 2
    with SessionLocal() as db:
        retained = db.get(models.AuthoredInitialCalibration, first.json()["calibration"]["id"])
        assert retained.data == original["calibration"]
        assert retained.revision == first.json()["calibration"]["revision"]
    assert guidance(client, headers, session).json()["calibration"] == second.json()["calibration"]


def test_later_occurrence_requires_explicit_reconfirmation(scenario):
    user, headers, client = scenario
    week = date.today() - timedelta(days=date.today().weekday())
    earlier = plan(user, week - timedelta(days=7))
    first = save(client, headers, earlier)
    assert first.status_code == 200, first.text
    later = plan(user, week)
    before = calibration_count(user)
    restored = guidance(client, headers, later)
    assert restored.status_code == 200, restored.text
    result = restored.json()
    assert result["calibration"]["requires_confirmation"] is True
    assert result["calibration"]["input"] == first.json()["calibration"]["input"]
    assert result["initial_estimate"]["prefill_available"] is False
    assert result["initial_estimate"]["recommended_weight"] is None
    assert calibration_count(user) == before
    confirmed = save(client, headers, later)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["calibration"]["requires_confirmation"] is False
    assert confirmed.json()["initial_estimate"]["status"] == "provisional"


def test_foreign_account_cannot_save_read_or_replay_calibration(scenario):
    from test_authored_load_intelligence import create_access_token
    user, headers, client = scenario
    session = plan(user)
    payload = calibration_payload(session)
    assert save(client, headers, session, payload).status_code == 200
    with SessionLocal() as db:
        other = User(id=str(uuid4()), email=f"{uuid4()}@example.invalid",
            name="Synthetic other calibration", password_hash="unused")
        db.add(other)
        db.commit()
        other_id = other.id
    foreign = {"Authorization": f"Bearer {create_access_token(other_id)}"}
    assert save(client, foreign, session, payload).status_code == 404
    assert guidance(client, foreign, session).status_code == 404
    assert calibration_count(user) == 1
    assert calibration_count(other_id) == 0


@pytest.mark.parametrize("boundary", ["equipment", "basis", "source_slot", "variant"])
def test_calibration_does_not_cross_setup_source_or_variant(scenario, boundary):
    user, headers, client = scenario
    week = date.today() - timedelta(days=date.today().weekday())
    original = plan(user, week - timedelta(days=7))
    assert save(client, headers, original).status_code == 200
    changed = plan(user, week, slot=2 if boundary == "source_slot" else 1,
        variant="approved-variant" if boundary == "variant" else None)
    context = deepcopy(CONTEXT)
    if boundary == "equipment":
        context["equipment_key"] = "different-physical-setup"
    if boundary == "basis":
        context["basis"] = "per_hand"
    response = guidance(client, headers, changed, context)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result.get("calibration") is None
    estimate = result.get("initial_estimate")
    assert estimate is None or (estimate["recommended_weight"] is None and not estimate["prefill_available"])
    assert calibration_count(user) == 1


def test_equivalent_report_units_preserve_canonical_attainable_weight(scenario):
    user, headers, client = scenario
    session = plan(user)
    pounds = calibration_payload(session, load=100, unit="lb",
        attainable={"unit": "lb", "min": 5, "step": 2.5, "max": 100})
    first = save(client, headers, session, pounds)
    assert first.status_code == 200, first.text
    kilograms = calibration_payload(session, load=45.359237, unit="kg",
        attainable={"unit": "kg", "min": 2.26796185, "step": 1.133980925, "max": 45.359237})
    second = save(client, headers, session, kilograms)
    assert second.status_code == 200, second.text
    assert first.json()["initial_estimate"]["recommended_weight"] == pytest.approx(30.617484975)
    assert second.json()["initial_estimate"]["recommended_weight"] == first.json()["initial_estimate"]["recommended_weight"]
    assert first.json()["calibration"]["input"]["unit"] == "lb"
    assert second.json()["calibration"]["input"]["unit"] == "kg"


@pytest.mark.parametrize("completed", [False, True])
def test_effective_history_precedes_initial_estimate(scenario, completed):
    user, headers, client = scenario
    week = date.today() - timedelta(days=date.today().weekday())
    previous = plan(user, week - timedelta(days=7))
    for index in ((1, 2) if completed else (1,)):
        response = log(client, headers, previous, submit(previous, index, reps=11, rpe=9))
        assert response.status_code == 200, response.text
    current = plan(user, week)
    baseline = guidance(client, headers, current).json()["next_exposure"]
    response = save(client, headers, current)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["initial_estimate"]["status"] == "unavailable"
    assert result["initial_estimate"]["recommended_weight"] is None
    assert result["initial_estimate"]["prefill_available"] is False
    assert result["next_exposure"] == baseline
    if completed:
        assert baseline["action"] == "hold"
        assert baseline["recommended_weight"] == 40
    else:
        assert baseline["action"] == "monitor"
    assert result["next_exposure"]["evidence"]["completed_exposure_count"] == int(completed)


def test_first_actual_set_transitions_to_remaining_guidance_and_preserves_original_offer(scenario):
    user, headers, client = scenario
    session = plan(user)
    saved = save(client, headers, session)
    assert saved.status_code == 200, saved.text
    estimate = saved.json()["initial_estimate"]
    payload = submit(session, weight=60, reps=10, load_recommendation_id=estimate["id"],
        load_override_reason="Synthetic user edit")
    first = log(client, headers, session, payload)
    assert first.status_code == 200, first.text
    result = first.json()["load_intelligence"]
    assert result["remaining_sets"]["recommended_weight"] == 60
    assert result["initial_estimate"]["prefill_available"] is False
    with SessionLocal() as db:
        record = db.get(WorkoutSetLog, first.json()["id"])
        assert record.weight == 60
        captured = record.replay_context["load_intelligence"]["offered_recommendation"]
        assert captured == estimate
    amended = correct(client, headers, first.json()["id"], weight=57.5, reps=10)
    assert amended.status_code == 200, amended.text
    assert amended.json()["load_intelligence"]["remaining_sets"]["recommended_weight"] == 57.5
    refreshed = guidance(client, headers, session).json()
    assert refreshed["calibration"] == saved.json()["calibration"]
    assert refreshed["initial_estimate"]["prefill_available"] is False
    removed = undo(client, headers, session)
    assert removed.status_code == 200, removed.text
    restored = guidance(client, headers, session).json()
    assert restored["effective_sets"] == []
    assert restored["next_exposure"]["evidence"]["completed_exposure_count"] == 0
    assert restored["initial_estimate"]["recommended_weight"] == estimate["recommended_weight"]
    assert restored["calibration"] == saved.json()["calibration"]
    assert log(client, headers, session, payload).json() == first.json()
    assert guidance(client, headers, session).json()["effective_sets"] == []
    assert calibration_count(user) == 1


def test_customized_occurrence_rejects_authored_initial_calibration(scenario):
    user, headers, client = scenario
    session = plan(user, program="customized_full_body")
    before = counts(user)
    response = save(client, headers, session)
    assert response.status_code == 409, response.text
    assert calibration_count(user) == 0
    assert counts(user) == before


def test_new_calibration_invalidates_stale_initial_recommendation(scenario):
    user, headers, client = scenario
    session = plan(user)
    old = save(client, headers, session)
    assert old.status_code == 200, old.text
    changed = save(client, headers, session, calibration_payload(session, load=80))
    assert changed.status_code == 200, changed.text
    assert changed.json()["initial_estimate"]["id"] != old.json()["initial_estimate"]["id"]
    before = counts(user)
    stale = log(client, headers, session, submit(session, weight=67.5,
        load_recommendation_id=old.json()["initial_estimate"]["id"]))
    assert stale.status_code == 409, stale.text
    assert counts(user) == before
    assert calibration_count(user) == 2


def test_recent_report_is_distinct_from_completed_work_and_missing_rir_abstains(scenario):
    user, headers, client = scenario
    session = plan(user)
    reported = calibration_payload(session, method="recent_set", load=40, reps=8, rir=2)
    response = save(client, headers, session, reported)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["initial_estimate"]["status"] == "provisional"
    assert result["initial_estimate"]["recommended_weight"] == 35
    assert result["calibration"]["input"] == reported["calibration"]
    unknown = calibration_payload(session, method="recent_set", load=40, reps=8)
    response = save(client, headers, session, unknown)
    assert response.status_code == 200, response.text
    assert response.json()["initial_estimate"]["status"] == "unavailable"
    assert response.json()["initial_estimate"]["recommended_weight"] is None
    assert response.json()["initial_estimate"]["prefill_available"] is False
    assert "rir" not in response.json()["calibration"]["input"]
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).filter_by(user_id=user).count() == 0
    assert response.json()["next_exposure"]["evidence"]["completed_exposure_count"] == 0


@pytest.mark.parametrize("changes", [{"confirmed": False}, {"variant_id": "different-variant"}])
def test_unconfirmed_or_wrong_variant_report_rejects_without_persistence(scenario, changes):
    user, headers, client = scenario
    session = plan(user)
    before = counts(user)
    response = save(client, headers, session, calibration_payload(session, **changes))
    assert response.status_code == 422, response.text
    assert calibration_count(user) == 0
    assert counts(user) == before


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL user-row serialization")
@pytest.mark.parametrize("changed", [False, True])
def test_concurrent_calibration_retry_serializes_once_or_conflicts(scenario, changed):
    user, headers, _ = scenario
    session = plan(user)
    first = calibration_payload(session)
    second = deepcopy(first)
    if changed:
        second["calibration"]["load"] = 80
    responses = _race([
        lambda client: save(client, headers, session, first),
        lambda client: save(client, headers, session, second),
    ])
    assert sorted(response.status_code for response in responses) == ([200, 409] if changed else [200, 200])
    if not changed:
        assert responses[0].json() == responses[1].json()
    assert calibration_count(user) == 1
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).filter_by(user_id=user).count() == 0


def test_declared_setup_identity_cannot_silently_change_meaning(scenario):
    user, headers, client = scenario
    session = plan(user)
    original = save(client, headers, session)
    assert original.status_code == 200, original.text
    changed = calibration_payload(session, setup_details="Unilateral right side, partial ROM, wide grip, rack setting 9")
    before = counts(user)
    rejected = save(client, headers, session, changed)
    assert rejected.status_code == 422, rejected.status_code
    assert calibration_count(user) == 1
    assert counts(user) == before
    assert guidance(client, headers, session).json()["calibration"] == original.json()["calibration"]
    changed["load_context"]["equipment_key"] = "explicit-new-setup-identity"
    admitted = save(client, headers, session, changed)
    assert admitted.status_code == 200, admitted.text
    assert calibration_count(user) == 2


def test_revisiting_earlier_occurrence_restores_its_exact_saved_calibration(scenario):
    user, headers, client = scenario
    week = date.today() - timedelta(days=date.today().weekday())
    earlier = plan(user, week - timedelta(days=7))
    saved_earlier = save(client, headers, earlier)
    assert saved_earlier.status_code == 200, saved_earlier.text
    later = plan(user, week)
    saved_later = save(client, headers, later, calibration_payload(later, load=80))
    assert saved_later.status_code == 200, saved_later.text
    restored = guidance(client, headers, earlier)
    assert restored.status_code == 200, restored.text
    assert restored.json()["calibration"] == saved_earlier.json()["calibration"]
    assert restored.json()["initial_estimate"] == saved_earlier.json()["initial_estimate"]
    assert guidance(client, headers, later).json()["calibration"] == saved_later.json()["calibration"]


def test_oversized_integer_attainable_value_rejects_without_server_error_or_writes(scenario):
    user, headers, client = scenario
    session = plan(user)
    before = counts(user)
    payload = calibration_payload(session, attainable={"unit": "kg", "values": [10 ** 400]})
    response = save(client, headers, session, payload)
    assert response.status_code == 422, response.text
    assert calibration_count(user) == 0
    assert counts(user) == before


@pytest.mark.parametrize("field,value", [
    ("load", True), ("load", 0), ("load", -1), ("load", "100"),
    ("confirmed", 1), ("confirmed", "true"),
    ("reps", True), ("reps", 1.5), ("reps", 0), ("reps", 11),
    ("rir", True), ("rir", -0.1), ("rir", 3.1),
    ("observed_date", "not-a-date"), ("observed_date", (date.today() + timedelta(days=1)).isoformat()),
    ("attainable.min", True), ("attainable.min", 0),
    ("attainable.step", True), ("attainable.step", 0), ("attainable.step", -1),
    ("attainable.max", True), ("attainable.max", 0), ("attainable.max", 4),
    ("attainable.values", []), ("attainable.values", [True]),
    ("attainable.values", [0]), ("attainable.values", [-1]), ("attainable.values", ["10"]),
])
def test_invalid_calibration_scalars_reject_without_history_or_revision_writes(scenario, field, value):
    user, headers, client = scenario
    session = plan(user)
    payload = calibration_payload(session, method="recent_set", reps=8, rir=2)
    parent = payload["calibration"]
    if field.startswith("attainable."):
        parent = parent["attainable"]
        field = field.split(".")[1]
        if field == "values":
            payload["calibration"]["attainable"] = parent = {"unit": "kg"}
    parent[field] = value
    before = counts(user)
    response = save(client, headers, session, payload)
    assert response.status_code == 422, response.status_code
    assert calibration_count(user) == 0
    assert counts(user) == before


@pytest.mark.parametrize("field", ["load", "rir", "attainable.min", "attainable.step", "attainable.max", "attainable.values"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_raw_json_rejects_with_safe_422_and_no_writes(scenario, caplog, field, value):
    import json
    user, headers, client = scenario
    session = plan(user)
    payload = calibration_payload(session, method="recent_set", reps=8, rir=2)
    parent = payload["calibration"]
    if field.startswith("attainable."):
        parent = parent["attainable"]
        field = field.split(".")[1]
        if field == "values":
            payload["calibration"]["attainable"] = parent = {"unit": "kg"}
            value = [value]
    parent[field] = value
    payload["calibration"]["setup_details"] = "Private-synthetic-nonfinite-input"
    before = counts(user)
    response = client.post(f"/workout/{session['workout_occurrence_id']}/initial-calibration",
        headers={**headers, "Content-Type": "application/json"}, content=json.dumps(payload, allow_nan=True))
    assert response.status_code == 422, response.status_code
    # Non-finite values and submitted setup details must not be echoed in errors.
    assert "Private-synthetic-nonfinite-input" not in response.text
    assert "Private-synthetic-nonfinite-input" not in caplog.text
    json.dumps(response.json(), allow_nan=False)
    assert calibration_count(user) == 0
    assert counts(user) == before


def test_invalid_recent_effort_sum_and_mixed_attainable_forms_reject(scenario):
    user, headers, client = scenario
    session = plan(user)
    for changes in (
        {"method": "recent_set", "reps": 9, "rir": 2},
        {"method": "known_1rm", "reps": 1},
        {"attainable": {"unit": "kg", "min": 5, "step": 2.5, "max": 100, "values": [10, 20]}},
        {"attainable": {"unit": "kg", "min": 5, "max": 100}},
    ):
        before = counts(user)
        response = save(client, headers, session, calibration_payload(session, **changes))
        assert response.status_code == 422, response.status_code
        assert calibration_count(user) == 0
        assert counts(user) == before


def _later_amrap(session):
    with SessionLocal() as db:
        row = db.get(WorkoutPlan, session["plan_id"])
        payload = deepcopy(row.payload)
        payload["sessions"][0]["exercises"][0]["authored_prescription"]["sets"][1]["rep_target"] = {
            "kind": "amrap", "raw": "AMRAP", "min": None, "max": None}
        row.payload = payload
        db.commit()
        return identified_sessions(row)[0]


def test_later_unresolved_source_target_history_still_blocks_initial_estimate(scenario):
    user, headers, client = scenario
    week = date.today() - timedelta(days=date.today().weekday())
    previous = _later_amrap(plan(user, week - timedelta(days=7)))
    current = _later_amrap(plan(user, week))
    for index in (1, 2):
        response = log(client, headers, previous, submit(previous, index))
        assert response.status_code == 200, response.text
    response = save(client, headers, current)
    assert response.status_code == 200, response.text
    estimate = response.json()["initial_estimate"]
    assert estimate["status"] == "unavailable", estimate["reason_codes"]
    assert "effective_history_takes_precedence" in estimate["reason_codes"]
    assert estimate["recommended_weight"] is None


def test_current_restrictions_remove_saved_initial_offer_from_read_envelopes(scenario):
    user, headers, client = scenario
    session = plan(user, warm_up_sets="1")
    original = save(client, headers, session)
    assert original.status_code == 200, original.text
    assert original.json()["initial_estimate"]["status"] == "provisional"
    # An actual warm-up binds the source occurrence without creating working history.
    warmup = log(client, headers, session, submit(session, set_kind="warmup", weight=20))
    assert warmup.status_code == 200, warmup.text
    with SessionLocal() as db:
        db.get(User, user).movement_restrictions = ["deep_knee_flexion"]
        db.commit()
    before = counts(user)
    for path in ("/workout/today", f"/workout/{session['workout_occurrence_id']}/progress"):
        response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text
        exercise = next(item for item in response.json()["exercises"]
            if item["exercise_occurrence_id"] == session["exercises"][0]["exercise_occurrence_id"])
        estimate = exercise["load_intelligence"]["initial_estimate"]
        assert estimate["status"] == "unavailable", estimate["reason_codes"]
        assert estimate["recommended_weight"] is None
        assert estimate["prefill_available"] is False
    assert counts(user) == before


def test_initial_estimate_uses_source_warmup_owner_and_preserves_example_dose(scenario):
    from core_engine.authored_prescription import preserve_prescription
    user, headers, client = scenario
    session = plan(user, warm_up_sets="1")
    # Synthetic source row with the reviewed Cross-Body example's target/dose;
    # this does not claim source-import or real runner browser qualification.
    with SessionLocal() as db:
        row = db.get(WorkoutPlan, session["plan_id"])
        payload = deepcopy(row.payload)
        exercise = payload["sessions"][0]["exercises"][0]
        exercise["sets"] = 3
        exercise["rep_range"] = [10, 12]
        exercise["authored_prescription"] = preserve_prescription({
            "reps": "10-12", "working_sets": "3", "early_set_rpe": "7-8",
            "last_set_rpe": "8-9", "rest": "120", "warm_up_sets": "1"}, 3)
        for item in exercise["authored_prescription"]["sets"]:
            item["source_set_id"] = f"{exercise['source_lineage']['source_slot_id']}:set{item['set_index']}"
        original = deepcopy(exercise)
        row.payload = payload
        db.commit()
        session = identified_sessions(row)[0]
    payload = calibration_payload(session, load=100, unit="lb",
        attainable={"unit": "lb", "min": 5, "step": 2.5, "max": 100})
    response = save(client, headers, session, payload)
    assert response.status_code == 200, response.text
    feedback = response.json()
    assert feedback["initial_estimate"]["recommended_weight"] == 29.48350405  # 65 lb
    warmup = feedback["warmup_guidance"]
    assert warmup["status"] == "suggested", warmup["reason_codes"]
    assert warmup["count"] == 1
    assert [(item["percent"], item["reps_min"], item["reps_max"]) for item in warmup["sets"]] == [(60, 6, 10)]
    assert warmup["sets"][0]["suggested_weight"] == 17.009713875  # 37.5 lb, floor 60% of 65 lb
    assert warmup["decision_trace"]["owner"] == "core_engine.authored_warmups"
    assert warmup["decision_trace"]["provisional_working_weight"] == 29.48350405
    assert warmup["decision_trace"]["source_prescription"] == original["authored_prescription"]
    before = counts(user)
    assert guidance(client, headers, session).json()["warmup_guidance"] == warmup
    assert counts(user) == before
    with SessionLocal() as db:
        stored = db.get(WorkoutPlan, session["plan_id"]).payload["sessions"][0]["exercises"][0]
        assert stored == original
        assert db.query(WorkoutSetLog).filter_by(user_id=user).count() == 0


def test_existing_progression_history_cannot_be_hidden_by_raw_display_text(scenario):
    user, headers, client = scenario
    week = date.today() - timedelta(days=date.today().weekday())
    previous = plan(user, week - timedelta(days=7))
    for index in (1, 2):
        assert log(client, headers, previous, submit(previous, index, reps=11, rpe=9)).status_code == 200
    current = plan(user, week)
    with SessionLocal() as db:
        row = db.get(WorkoutPlan, current['plan_id'])
        value = deepcopy(row.payload)
        value['sessions'][0]['exercises'][0]['authored_prescription']['raw']['reps'] = '8 – 12'
        row.payload = value
        db.commit()
        current = identified_sessions(row)[0]
    result = save(client, headers, current)
    assert result.status_code == 200, result.text
    feedback = result.json()
    assert feedback['next_exposure']['recommended_weight'] == 40
    assert feedback['initial_estimate']['status'] == 'unavailable'


def test_resolved_frozen_constraint_uses_current_feasibility_for_warmups(scenario):
    user, headers, client = scenario
    session = plan(user, warm_up_sets='1')
    with SessionLocal() as db:
        row = db.get(WorkoutPlan, session['plan_id'])
        value = deepcopy(row.payload)
        value['sessions'][0]['exercises'][0]['authored_constraint'] = {
            'status': 'infeasible', 'execution_status': 'infeasible', 'revision': 0,
            'reasons': [{'kind': 'equipment', 'details': ['barbell']}], 'allowed_alternatives': []}
        row.payload = value
        db.commit()
        session = identified_sessions(row)[0]
    result = save(client, headers, session)
    assert result.status_code == 200, result.text
    feedback = result.json()
    assert feedback['initial_estimate']['status'] == 'provisional'
    assert feedback['warmup_guidance']['status'] == 'suggested', feedback['warmup_guidance']['reason_codes']
