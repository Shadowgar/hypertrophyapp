"""History read boundaries; run only with the explicitly configured test DB."""
from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from test_history_calendar import _register_token, _reset_db
from app.database import SessionLocal
from app.main import app
from app.models import User, WorkoutOccurrence, WorkoutSetLog


@pytest.mark.parametrize("zone,scheduled,recorded", [
    ("America/Los_Angeles", date(2026, 10, 11), datetime(2026, 10, 12, 1)),
    ("Pacific/Auckland", date(2026, 10, 12), datetime(2026, 10, 11, 13)),
])
def test_history_occurrence_day_and_audit_time_remain_distinct(zone, scheduled, recorded):
    _reset_db()
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_register_token(client)}"}
    with SessionLocal() as db:
        owner = db.query(User).filter_by(email="calendar@example.com").one()
        owner.scheduling_timezone = zone
        db.add(WorkoutOccurrence(id="date-occurrence", user_id=owner.id, plan_id="retained-plan", week_start=scheduled-timedelta(days=scheduled.weekday()),
            scheduled_date=scheduled, schedule_timezone=zone, session_slot=0, workout_id="date-workout", payload={"session_id":"date-workout", "title":"Dated workout",
                "exercises":[{"id":"press", "name":"Press", "exercise_occurrence_id":"date-slot", "sets":1}]}))
        db.flush()
        db.add(WorkoutSetLog(id="dated-receipt", user_id=owner.id, workout_id="date-workout", workout_occurrence_id="date-occurrence",
            exercise_occurrence_id="date-slot",primary_exercise_id="press",exercise_id="press",set_index=1,reps=8,weight=45.359237,set_kind="work",created_at=recorded))
        db.commit()
    for day, count in [(scheduled, 1), (recorded.date(), 0)]:
        calendar = client.get("/history/calendar",headers=headers,params={"start_date":str(day),"end_date":str(day)})
        assert calendar.status_code == 200, calendar.text
        entry = calendar.json()["days"][0]
        assert entry["set_count"] == count
        assert entry["status"] == ("complete" if count else "unknown")
        detail = client.get(f"/history/day/{day}",headers=headers)
        assert detail.status_code == 200, detail.text
        assert detail.json()["totals"]["set_count"] == count
        if count:
            receipt = detail.json()["workouts"][0]["exercises"][0]["sets"][0]
            assert receipt["weight"] == 45.359237
            assert receipt["created_at"] == recorded.isoformat()
    with SessionLocal() as db:
        saved = db.get(WorkoutSetLog,"dated-receipt")
        assert saved.weight == 45.359237 and saved.created_at == recorded
        assert db.query(WorkoutSetLog).count() == db.query(WorkoutOccurrence).count() == 1


def test_foreign_occurrence_never_supplies_history_date_title_or_completion():
    _reset_db()
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_register_token(client)}"}
    with SessionLocal() as db:
        owner = db.query(User).filter_by(email="calendar@example.com").one()
        outsider = User(id=str(uuid4()),email="outside-history@example.invalid",name="Synthetic outsider",password_hash="not-a-login")
        db.add(outsider);db.flush()
        db.add(WorkoutOccurrence(id="outside-occurrence",user_id=outsider.id,plan_id="outside-plan",week_start=date(2026,10,5),scheduled_date=date(2026,10,11),
            session_slot=0,workout_id="outside-workout",payload={"title":"Private other account title","exercises":[{"id":"press","sets":1,"exercise_occurrence_id":"outside-slot"}]}))
        db.flush()
        db.add(WorkoutSetLog(user_id=owner.id,workout_id="legacy-corrupt-reference",workout_occurrence_id="outside-occurrence",exercise_occurrence_id="outside-slot",
            primary_exercise_id="press",exercise_id="press",set_index=1,reps=8,weight=10,created_at=datetime(2026,10,12,1)))
        db.commit()
    calendar = client.get("/history/calendar?start_date=2026-10-11&end_date=2026-10-12",headers=headers)
    assert calendar.status_code == 200,calendar.text
    assert "Private other account title" not in calendar.text
    assert [(day["set_count"],day["status"]) for day in calendar.json()["days"]] == [(0,"unknown"),(1,"unknown")]
    detail = client.get("/history/day/2026-10-12",headers=headers)
    assert detail.status_code == 200 and detail.json()["totals"]["set_count"] == 1
    assert "Private other account title" not in detail.text


def test_analytics_setup_series_keep_canonical_load_and_owner_effective_work_boundaries():
    _reset_db()
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_register_token(client)}"}
    recorded = datetime.combine(date.today()-timedelta(days=1),datetime.min.time())
    with SessionLocal() as db:
        owner = db.query(User).filter_by(email="calendar@example.com").one()
        outsider = User(id=str(uuid4()),email="outside-analytics@example.invalid",name="Synthetic outsider",password_hash="not-a-login")
        db.add(outsider);db.flush()
        def row(identity, equipment, weight, **extra):
            return WorkoutSetLog(id=identity,user_id=extra.pop("user_id",owner.id),workout_id="recorded",primary_exercise_id="press",exercise_id="press",
                set_index=1,reps=8,weight=weight,created_at=recorded,replay_context={"planned_exercise":{"name":"Cable press"},
                    "load_intelligence":{"load_context":{"unit":"kg","basis":"machine_stack","equipment_key":equipment}}},**extra)
        db.add_all([row("canonical-work","cable-a",45.359237,set_kind="work"),row("other-setup","cable-b",10,set_kind="work"),
            row("warmup","cable-a",99,set_kind="warmup"),row("technique","cable-a",200,set_kind="drop",parent_set_index=1),
            row("voided","cable-a",300,set_kind="work",voided_at=recorded),row("foreign-work","cable-a",400,set_kind="work",user_id=outsider.id)])
        db.commit()
    response = client.get("/history/analytics?limit_weeks=4",headers=headers)
    assert response.status_code == 200,response.text
    series = response.json()["load_series"]
    assert {item["equipment_key"]:item["points"][0]["max_weight"] for item in series} == {"cable-a":45.36,"cable-b":10}
    assert all(item["unit"] == "kg" and item["exercise_name"] == "Cable press" for item in series)
    assert response.json()["load_series_unknown_sets"] == 0
    with SessionLocal() as db:
        assert db.get(WorkoutSetLog,"canonical-work").weight == 45.359237
        assert db.query(WorkoutSetLog).count() == 6
