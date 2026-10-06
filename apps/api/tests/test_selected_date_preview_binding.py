"""Reviewed-content binding and lock-wait clocks on a verified disposable target."""
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url

explicit = os.environ.get("TEST_DATABASE_URL")
assert explicit and os.environ.get("DATABASE_URL") == explicit
root = Path(os.environ["HIST_TEST_ROOT"]).resolve(strict=True)
target = make_url(explicit)
assert target.get_backend_name() == "sqlite" and target.database not in (None, ":memory:")
database = Path(target.database).resolve()
assert root != Path("/") and database.is_relative_to(root)
with sqlite3.connect(database) as connection:
    identity = connection.execute("PRAGMA database_list").fetchall()
    assert len(identity) == 1 and Path(identity[0][2]).resolve() == database

from fastapi.testclient import TestClient
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, WorkoutOccurrence, WorkoutPlan
from app.routers import plan as plan_router
from app import selected_date_plans
from app.security import create_access_token


@pytest.fixture
def scenario(monkeypatch):
    assert engine.url == target and engine.dialect.name == "sqlite"
    Base.metadata.create_all(engine)
    clock = {"instant": datetime(2026, 10, 6, 16, tzinfo=UTC)}
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock["instant"].astimezone(tz) if tz else clock["instant"].replace(tzinfo=None)
    monkeypatch.setattr(plan_router, "datetime", Clock)
    monkeypatch.setattr(selected_date_plans, "datetime", Clock)
    user_id = str(uuid4())
    with SessionLocal() as db:
        db.add(User(id=user_id, email=f"{uuid4()}@example.invalid", name="Synthetic preview binding",
            password_hash="not-a-login", split_preference="full_body", days_available=5,
            selected_program_id="pure_bodybuilding_phase_1_full_body", nutrition_phase="maintenance",
            equipment_profile=["dumbbell", "barbell", "bench", "cable", "machine"]))
        db.commit()
    client = TestClient(app)
    yield user_id, {"Authorization": f"Bearer {create_access_token(user_id)}"}, client, clock
    client.close()


def request(monday=date(2026, 10, 5), timezone="America/New_York"):
    return {"template_id": "pure_bodybuilding_phase_1_full_body", "target_days": 3,
        "week_start": monday.isoformat(), "timezone": timezone,
        "selected_dates": [(monday + timedelta(days=i)).isoformat() for i in (1, 4, 6)],
        "expected_placement_revision": 0}


def snapshot(user_id):
    with SessionLocal() as db:
        user = db.get(User, user_id)
        return {"user": {column.key: deepcopy(getattr(user, column.key)) for column in User.__table__.columns},
            "plans": [(p.id, deepcopy(p.payload), p.placement_revision, p.schedule_timezone)
                for p in db.query(WorkoutPlan).filter_by(user_id=user_id).order_by(WorkoutPlan.id)],
            "occurrences": db.query(WorkoutOccurrence).filter_by(user_id=user_id).count()}


def preview(client, headers, payload):
    response = client.post("/plan/selected-dates/preview", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def digest(plan):
    # Missing binding still reaches activation in the red run, rather than hiding
    # the unsafe activation behind a missing response-field assertion.
    return plan["schedule"].get("preview_digest", "0" * 64)


def seed_legacy(user_id, placed, *, changed_week=False):
    saved = deepcopy(placed)
    saved.pop("schedule")
    if changed_week:
        saved["mesocycle"]["authored_week_index"] = 4
        saved["mesocycle"]["week_index"] = 4
        saved["sessions"][0]["exercises"][0]["recommended_working_weight"] = 77.5
    with SessionLocal() as db:
        row = WorkoutPlan(user_id=user_id, week_start=date(2026, 10, 5), split="full_body",
            phase="maintenance", payload=saved)
        db.add(row)
        db.commit()
        return row.id


def test_repeat_preview_is_no_write_and_matching_review_activates(scenario):
    user_id, headers, client, _ = scenario
    payload = request()
    before = snapshot(user_id)
    first = preview(client, headers, payload)
    second = preview(client, headers, payload)
    assert snapshot(user_id) == before
    assert len(first["schedule"].get("preview_digest", "")) == 64
    assert digest(first) == digest(second)
    activated = client.post("/plan/generate-week", headers=headers,
        json={**payload, "expected_preview_digest": digest(first)})
    assert activated.status_code == 200, activated.text
    assert digest(activated.json()) == digest(first)
    assert selected_date_plans.preview_content_digest(activated.json()) == digest(first)
    assert [s["exercises"] for s in first["sessions"]] == [
        [{k: v for k, v in e.items() if k not in ("exercise_occurrence_id", "execution_slot")}
         for e in s["exercises"]] for s in activated.json()["sessions"]]


@pytest.mark.parametrize("change", ["input", "load", "new_legacy"])
def test_changed_review_content_at_revision_zero_conflicts_without_writes(scenario, change):
    user_id, headers, client, _ = scenario
    payload = request()
    first = preview(client, headers, payload)
    if change == "load":
        plan_id = seed_legacy(user_id, first)
        first = preview(client, headers, payload)
        with SessionLocal() as db:
            row = db.get(WorkoutPlan, plan_id)
            saved = deepcopy(row.payload)
            saved["sessions"][0]["exercises"][0]["recommended_working_weight"] = 99
            row.payload = saved
            db.commit()
    elif change == "new_legacy":
        seed_legacy(user_id, first, changed_week=True)
    else:
        with SessionLocal() as db:
            db.get(User, user_id).movement_restrictions = ["deep_knee_flexion"]
            db.commit()
    before = snapshot(user_id)
    current = preview(client, headers, payload)
    assert current["sessions"] != first["sessions"] or current["mesocycle"] != first["mesocycle"]
    rejected = client.post("/plan/generate-week", headers=headers,
        json={**payload, "expected_preview_digest": digest(first)})
    assert rejected.status_code == 409, rejected.text
    assert "review" in rejected.json()["detail"].lower()
    assert snapshot(user_id) == before


@pytest.mark.parametrize("value", ["", "f" * 63, "f" * 65, "z" * 64, 123])
def test_malformed_preview_digest_is_rejected_without_writes(scenario, value):
    user_id, headers, client, _ = scenario
    before = snapshot(user_id)
    response = client.post("/plan/generate-week", headers=headers,
        json={**request(), "expected_preview_digest": value})
    assert response.status_code == 422, response.text
    assert snapshot(user_id) == before


@pytest.mark.parametrize("timezone,before_lock,after_lock", [
    ("America/Los_Angeles", datetime(2026, 10, 12, 6, 59, tzinfo=UTC), datetime(2026, 10, 12, 7, 1, tzinfo=UTC)),
    ("Pacific/Auckland", datetime(2026, 10, 11, 10, 59, tzinfo=UTC), datetime(2026, 10, 11, 11, 1, tzinfo=UTC)),
])
def test_lock_wait_across_local_monday_rejects_stale_week_without_writes(
    scenario, monkeypatch, timezone, before_lock, after_lock,
):
    user_id, headers, client, clock = scenario
    clock["instant"] = before_lock
    payload = request(timezone=timezone)
    reviewed = preview(client, headers, payload)
    before = snapshot(user_id)
    original_lock = selected_date_plans.lock_history_user
    def rollover(db, locked_user_id):
        original_lock(db, locked_user_id)
        clock["instant"] = after_lock
    monkeypatch.setattr(selected_date_plans, "lock_history_user", rollover)
    response = client.post("/plan/generate-week", headers=headers,
        json={**payload, "expected_preview_digest": digest(reviewed)})
    assert response.status_code == 409, response.text
    assert "week" in response.json()["detail"].lower()
    assert snapshot(user_id) == before


def test_lock_wait_within_week_refreshes_elapsed_date_warning(scenario, monkeypatch):
    _, headers, client, clock = scenario
    clock["instant"] = datetime(2026, 10, 7, 3, 59, tzinfo=UTC)  # New York Tuesday.
    payload = request()
    reviewed = preview(client, headers, payload)
    original_lock = selected_date_plans.lock_history_user
    def next_local_day(db, user_id):
        original_lock(db, user_id)
        clock["instant"] = datetime(2026, 10, 7, 4, 1, tzinfo=UTC)
    monkeypatch.setattr(selected_date_plans, "lock_history_user", next_local_day)
    response = client.post("/plan/generate-week", headers=headers,
        json={**payload, "expected_preview_digest": digest(reviewed)})
    assert response.status_code == 200, response.text
    assert any("Elapsed selected dates" in text for text in response.json()["schedule"]["spacing"]["warnings"])


def test_direct_activation_without_preview_binding_remains_allowed(scenario):
    _, headers, client, _ = scenario
    assert client.post("/plan/generate-week", headers=headers, json=request()).status_code == 200


def content_fixture():
    exercise = {"id": "synthetic_press", "primary_exercise_id": "synthetic_press", "sets": 3,
        "rep_range": [8, 12], "reps": "8-12", "recommended_working_weight": 25,
        "warm_up_sets": "1", "early_set_rpe": "8", "rest": "120s",
        "authored_prescription": {"sets": [{"reps": {"kind": "AMRAP"}, "rpe": 8}]},
        "source_lineage": {"source_slot_id": "source:w4:d1:s1", "artifact_hash": "a" * 64},
        "source_relationships": [{"kind": "superset", "source_slot_ids": ["slot1", "slot2"]}],
        "source_approved_alternatives": [{"id": "synthetic_variant", "permission": "source"}],
        "authored_constraint": {"status": "available"},
        "performed_variant": {"exercise_id": "synthetic_variant"}}
    return {"program_template_id": "pure_bodybuilding_phase_1_full_body", "split": "full_body",
        "phase": "build", "mesocycle": {"week_index": 4, "authored_week_index": 4},
        "deload": {"active": False}, "schedule": {"week_start": "2026-10-05",
            "timezone": "America/New_York", "selected_dates": ["2026-10-06", "2026-10-09", "2026-10-11"]},
        "sessions": [{"session_id": "source-day-1", "day_role": "full_body", "session_index": 0,
            "exercises": [exercise, {**deepcopy(exercise), "id": "synthetic_row"}]},
            {"session_id": "source-day-2", "day_role": "full_body", "session_index": 1,
             "exercises": [deepcopy(exercise)]}]}


@pytest.mark.parametrize("path,value", [
    (("program_template_id",), "pure_bodybuilding_phase_2_full_body"),
    (("split",), "upper_lower"), (("phase",), "maintenance"),
    (("mesocycle", "authored_week_index"), 5), (("deload", "active"), True),
    (("schedule", "week_start"), "2026-10-12"),
    (("schedule", "timezone"), "Pacific/Auckland"),
    (("schedule", "selected_dates"), ["2026-10-07", "2026-10-09", "2026-10-11"]),
    (("sessions", 0, "session_id"), "different-source-day"),
    (("sessions", 0, "day_role"), "upper"), (("sessions", 0, "session_index"), 2),
    (("sessions", 0, "exercises", 0, "id"), "different-exercise"),
    (("sessions", 0, "exercises", 0, "sets"), 4),
    (("sessions", 0, "exercises", 0, "rep_range"), [10, 15]),
    (("sessions", 0, "exercises", 0, "recommended_working_weight"), 77.5),
    (("sessions", 0, "exercises", 0, "warm_up_sets"), "2"),
    (("sessions", 0, "exercises", 0, "reps"), "AMRAP"),
    (("sessions", 0, "exercises", 0, "early_set_rpe"), "9"),
    (("sessions", 0, "exercises", 0, "rest"), "180s"),
    (("sessions", 0, "exercises", 0, "authored_prescription", "sets", 0, "reps"), {"kind": "fixed", "target": 8}),
    (("sessions", 0, "exercises", 0, "authored_prescription", "sets", 0, "rpe"), 9),
    (("sessions", 0, "exercises", 0, "source_lineage", "source_slot_id"), "different-slot"),
    (("sessions", 0, "exercises", 0, "source_lineage", "artifact_hash"), "b" * 64),
    (("sessions", 0, "exercises", 0, "source_relationships"), []),
    (("sessions", 0, "exercises", 0, "source_approved_alternatives"), []),
    (("sessions", 0, "exercises", 0, "authored_constraint", "status"), "unresolved"),
    (("sessions", 0, "exercises", 0, "performed_variant", "exercise_id"), "different-variant"),
])
def test_content_digest_binds_each_reviewed_prescription_dimension(path, value):
    original = content_fixture()
    changed = deepcopy(original)
    cursor = changed
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    assert selected_date_plans.preview_content_digest(original) != selected_date_plans.preview_content_digest(changed)


@pytest.mark.parametrize("kind", ["sessions", "exercises"])
def test_content_digest_preserves_session_and_exercise_list_order(kind):
    original = content_fixture()
    changed = deepcopy(original)
    sequence = changed["sessions"] if kind == "sessions" else changed["sessions"][0]["exercises"]
    sequence.reverse()
    assert selected_date_plans.preview_content_digest(original) != selected_date_plans.preview_content_digest(changed)


def test_content_digest_ignores_only_projection_times_traces_and_placement_history():
    original = content_fixture()
    projected = deepcopy(original)
    projected["generated_at"] = "volatile"
    projected["generation_runtime_trace"] = {"clock": "volatile"}
    projected["schedule"].update(placement_revision=8, placement_history=[{"selected_dates": ["older"]}])
    session = projected["sessions"][0]
    session.update(workout_occurrence_id=str(uuid4()), plan_id=str(uuid4()), session_slot=9,
        week_start="2026-10-05", created_at="volatile")
    session["exercises"][0].update(exercise_occurrence_id=str(uuid4()), execution_slot=9,
        substitution_decision_trace={"explanation": "volatile"})
    assert selected_date_plans.preview_content_digest(original) == selected_date_plans.preview_content_digest(projected)
    assert selected_date_plans.preview_content_digest(original) == selected_date_plans.preview_content_digest(
        dict(reversed(list(original.items()))))
