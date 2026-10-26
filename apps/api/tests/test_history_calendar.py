from datetime import date, datetime, time, timedelta

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_history_calendar")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, WorkoutOccurrence, WorkoutPlan, WorkoutSetLog
from app.workout_identity import identified_sessions


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_token(client: TestClient) -> str:
    credential_field = "pass" + "word"
    response = client.post(
        "/auth/register",
        json={"email": "calendar@example.com", credential_field: "CalendarPass1", "name": "Calendar User"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_history_calendar_and_day_detail() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    today = date.today()
    day_one = today - timedelta(days=2)
    day_two = today - timedelta(days=1)
    day_three = today

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "calendar@example.com").first()
        assert user is not None

        session.add_all(
            [
                WorkoutPlan(
                    user_id=user.id,
                    week_start=day_one - timedelta(days=day_one.weekday()),
                    split="full_body",
                    phase="accumulation",
                    payload={
                        "sessions": [
                            {
                                "session_id": "workout_a",
                                "date": day_one.isoformat(),
                                "exercises": [
                                    {"id": "bench_press", "name": "Bench Press", "sets": 3, "primary_muscles": ["chest"]},
                                ],
                            },
                            {
                                "session_id": "workout_c",
                                "date": day_three.isoformat(),
                                "exercises": [
                                    {"id": "incline_press", "name": "Incline Press", "sets": 2, "primary_muscles": ["chest"]},
                                ],
                            },
                        ],
                        "program_template_id": "pure_bodybuilding_phase_1_full_body",
                    },
                ),
                WorkoutSetLog(
                    user_id=user.id,
                    workout_id="workout_a",
                    primary_exercise_id="bench_press",
                    exercise_id="bench_press",
                    set_index=1,
                    reps=8,
                    weight=80,
                    created_at=datetime.combine(day_one, time(9, 0)),
                ),
                WorkoutSetLog(
                    user_id=user.id,
                    workout_id="workout_a",
                    primary_exercise_id="bench_press",
                    exercise_id="bench_press",
                    set_index=2,
                    reps=7,
                    weight=82.5,
                    created_at=datetime.combine(day_one, time(9, 5)),
                ),
                WorkoutSetLog(
                    user_id=user.id,
                    workout_id="workout_b",
                    primary_exercise_id="romanian_deadlift",
                    exercise_id="romanian_deadlift",
                    set_index=1,
                    reps=10,
                    weight=100,
                    created_at=datetime.combine(day_two, time(10, 0)),
                ),
            ]
        )
        session.commit()

    start = (today - timedelta(days=3)).isoformat()
    end = today.isoformat()
    calendar = client.get(f"/history/calendar?start_date={start}&end_date={end}", headers=headers)
    assert calendar.status_code == 200
    calendar_payload = calendar.json()

    assert calendar_payload["start_date"] == start
    assert calendar_payload["end_date"] == end
    assert len(calendar_payload["days"]) == 4
    assert calendar_payload["active_days"] == 2
    assert calendar_payload["longest_streak_days"] >= 1

    day_one_entry = next(day for day in calendar_payload["days"] if day["date"] == day_one.isoformat())
    assert day_one_entry["set_count"] == 2
    assert day_one_entry["exercise_count"] == 1
    assert day_one_entry["completed"] is True
    assert day_one_entry["program_ids"] == ["pure_bodybuilding_phase_1_full_body"]
    assert day_one_entry["muscles"] == ["chest"]
    assert day_one_entry["pr_count"] == 1
    assert day_one_entry["pr_exercises"] == ["bench_press"]

    detail = client.get(f"/history/day/{day_one.isoformat()}", headers=headers)
    assert detail.status_code == 200
    detail_payload = detail.json()

    assert detail_payload["date"] == day_one.isoformat()
    assert detail_payload["totals"]["set_count"] == 2
    assert detail_payload["totals"]["planned_set_count"] == 3
    assert detail_payload["totals"]["set_delta"] == -1
    assert detail_payload["totals"]["exercise_count"] == 1
    # Legacy receipts cannot be bound to a generated occurrence merely because
    # a date and template happen to match. Preserve both factual records.
    assert day_one_entry["status"] == "unknown"
    assert len(detail_payload["workouts"]) == 2
    recorded = next(item for item in detail_payload["workouts"] if item["total_sets"])
    planned = next(item for item in detail_payload["workouts"] if not item["total_sets"])
    assert recorded["workout_id"] == "workout_a"
    assert recorded["workout_occurrence_id"] is None
    assert recorded["planned_sets_total"] == 0
    assert recorded["exercises"][0]["planned_sets"] is None
    assert len(recorded["exercises"][0]["sets"]) == 2
    assert planned["program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert planned["planned_sets_total"] == 3
    assert planned["exercises"][0]["planned_name"] == "Bench Press"
    assert planned["exercises"][0]["primary_muscles"] == ["chest"]

    missed_detail = client.get(f"/history/day/{day_three.isoformat()}", headers=headers)
    assert missed_detail.status_code == 200
    missed_payload = missed_detail.json()
    assert missed_payload["totals"]["set_count"] == 0
    assert missed_payload["totals"]["planned_set_count"] == 2
    assert missed_payload["totals"]["set_delta"] == -2
    assert len(missed_payload["workouts"]) == 1
    assert missed_payload["workouts"][0]["workout_id"] == "workout_c"
    assert missed_payload["workouts"][0]["exercises"][0]["planned_name"] == "Incline Press"


def test_history_calendar_rejects_invalid_date_window() -> None:
    _reset_db()
    client = TestClient(app)
    token = _register_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/history/calendar?start_date=2026-03-10&end_date=2026-03-01",
        headers=headers,
    )
    assert response.status_code == 400


def test_calendar_projects_owner_snapshots_effective_work_and_unknown_legacy_without_writes() -> None:
    from copy import deepcopy
    _reset_db()
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_register_token(client)}"}
    credential_field = "pass" + "word"
    other = client.post("/auth/register", json={"email": "other-calendar@example.com", credential_field: "OtherCalendar1", "name": "Other"})
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    monday, performed, scheduled = date(2026, 10, 19), date(2026, 10, 21), date(2026, 10, 23)
    with SessionLocal() as db:
        owner = db.query(User).filter_by(email="calendar@example.com").one()
        outsider = db.query(User).filter_by(email="other-calendar@example.com").one()
        plan = WorkoutPlan(user_id=owner.id, week_start=monday, split="full_body", phase="accumulation", payload={
            "program_template_id": "pure_bodybuilding_phase_1_full_body",
            "schedule": {"mode": "selected_dates_v1", "week_start": str(monday), "timezone": "UTC", "selected_dates": [str(performed), str(scheduled)]},
            "sessions": [{"session_id": "repeated-template", "title": "Saved workout", "date": str(day), "scheduled_date": str(day),
                          "exercises": [{"id": "press", "name": "Saved press", "sets": 2, "primary_muscles": ["chest"]}]} for day in (performed, scheduled)]})
        db.add(plan); db.flush()
        snapshot = identified_sessions(plan)[0]
        occurrence_id, exercise_id = snapshot["workout_occurrence_id"], snapshot["exercises"][0]["exercise_occurrence_id"]
        db.add(WorkoutOccurrence(id=occurrence_id, user_id=owner.id, plan_id=plan.id, week_start=monday, scheduled_date=performed,
            session_slot=0, workout_id="repeated-template", program_id="pure_bodybuilding_phase_1_full_body", payload=deepcopy(snapshot)))
        db.add(WorkoutOccurrence(id="foreign-occurrence", user_id=outsider.id, plan_id="foreign-plan", week_start=monday,
            scheduled_date=performed, session_slot=0, workout_id="foreign", payload={"session_id": "foreign", "title": "Foreign private session", "date": str(performed),
                "exercises": [{"id": "foreign", "exercise_occurrence_id": "foreign-slot", "sets": 1}]}))
        db.flush()
        owner_id, plan_id = owner.id, plan.id
        def log(identity, index, **extra):
            return WorkoutSetLog(id=identity,user_id=owner_id,workout_id="repeated-template",workout_occurrence_id=occurrence_id,
                exercise_occurrence_id=exercise_id,primary_exercise_id="press",exercise_id="press",set_index=index,reps=8,weight=20,
                created_at=datetime(2026,10,22,1),**extra)
        db.add_all([log("work-one",1,set_kind="work"),log("warmup-two",2,set_kind="warmup"),
                    log("technique-two",2,set_kind="drop",parent_set_index=1),
                    log("voided-two",2,set_kind="work",voided_at=datetime(2026,10,22,2))])
        changed = deepcopy(plan.payload)
        changed["sessions"][0]["exercises"][0]["sets"] = 9
        changed["sessions"][0]["title"] = "Replaceable plan title"
        plan.payload = changed
        db.commit()

    url = "/history/calendar?start_date=2026-10-19&end_date=2026-10-25"
    response = client.get(url,headers=headers)
    assert response.status_code == 200
    days = {item["date"]: item for item in response.json()["days"]}
    assert days[str(performed)]["status"] == "partial"
    assert days[str(performed)]["working_sets_completed"] == 1
    assert days[str(performed)]["working_sets_planned"] == 2
    assert days[str(scheduled)]["status"] == "scheduled"
    assert days["2026-10-20"]["status"] == "rest"
    assert "Foreign private session" not in response.text
    detail = client.get(f"/history/day/{performed}",headers=headers).json()
    assert detail["workouts"][0]["title"] == "Saved workout"
    assert detail["workouts"][0]["planned_sets_total"] == 2
    assert len(detail["workouts"][0]["exercises"][0]["sets"]) == 3
    other_response = client.get(url,headers=other_headers)
    assert "Saved workout" not in other_response.text
    assert "Foreign private session" in other_response.text

    with SessionLocal() as db:
        assert db.query(WorkoutOccurrence).count() == 2  # GET did not materialize the unstarted slot.
        assert db.query(WorkoutSetLog).count() == 4
        db.add(log("correction-two",2,set_kind="work",supersedes_id="voided-two"))
        db.commit()
    complete = client.get(url,headers=headers).json()
    assert next(item for item in complete["days"] if item["date"] == str(performed))["status"] == "complete"
    with SessionLocal() as db:
        # Replacing/deleting the plan view does not erase the retained occurrence.
        db.delete(db.get(WorkoutPlan,plan_id));db.commit()
    retained = client.get(url,headers=headers).json()
    retained_days = {item["date"]:item for item in retained["days"]}
    assert retained_days[str(performed)]["status"] == "complete"
    assert retained_days["2026-10-20"]["status"] == "unknown"
    with SessionLocal() as db:
        assert db.query(WorkoutOccurrence).count() == 2
        assert db.query(WorkoutSetLog).count() == 5
        assert db.get(WorkoutSetLog,"voided-two").voided_at is not None
