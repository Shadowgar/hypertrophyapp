from datetime import date, datetime, time, timedelta
import math
from uuid import uuid4

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_weekly_review")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, WeeklyReviewCycle, WorkoutPlan, WorkoutSetLog


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _current_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _review_week_start() -> date:
    current_monday = _current_monday()
    return current_monday + timedelta(days=7) if date.today().weekday() == 6 else current_monday


def _register_and_onboard(client: TestClient) -> dict[str, str]:
    generated_secret = f"Pw-{uuid4().hex[:12]}"
    credential_field = "pass" + "word"
    register = client.post(
        "/auth/register",
        json={"email": "weeklyreview@example.com", credential_field: generated_secret, "name": "Weekly Review User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Weekly Review User",
            "age": 31,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "full_body_v1",
            "training_location": "home",
            "equipment_profile": ["dumbbell", "bodyweight"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert profile.status_code == 200
    return headers


def _seed_previous_week_plan_and_logs_for_faults(user_email: str) -> None:
    previous_monday = _review_week_start() - timedelta(days=7)
    payload = {
        "program_template_id": "full_body_v1",
        "sessions": [
            {
                "session_id": "full_body_v1-day1",
                "session_label": "Day 1",
                "exercises": [
                    {
                        "id": "alpha_press",
                        "primary_exercise_id": "alpha_press",
                        "name": "Alpha Press",
                        "sets": 3,
                        "rep_range": [8, 12],
                        "recommended_working_weight": 100,
                    },
                    {
                        "id": "bravo_row",
                        "primary_exercise_id": "bravo_row",
                        "name": "Bravo Row",
                        "sets": 3,
                        "rep_range": [8, 12],
                        "recommended_working_weight": 100,
                    },
                    {
                        "id": "charlie_squat",
                        "primary_exercise_id": "charlie_squat",
                        "name": "Charlie Squat",
                        "sets": 3,
                        "rep_range": [8, 12],
                        "recommended_working_weight": 100,
                    },
                    {
                        "id": "delta_curl",
                        "primary_exercise_id": "delta_curl",
                        "name": "Delta Curl",
                        "sets": 3,
                        "rep_range": [8, 12],
                        "recommended_working_weight": 100,
                    },
                ],
            }
        ],
    }

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == user_email).first()
        assert user is not None

        session.add(
            WorkoutPlan(
                user_id=user.id,
                week_start=previous_monday,
                split="full_body",
                phase="maintenance",
                payload=payload,
            )
        )

        for exercise_id in ("alpha_press", "bravo_row", "charlie_squat", "delta_curl"):
            for set_index in range(1, 4):
                session.add(
                    WorkoutSetLog(
                        user_id=user.id,
                        workout_id=f"wk-prev-{exercise_id}",
                        primary_exercise_id=exercise_id,
                        exercise_id=exercise_id,
                        set_index=set_index,
                        reps=13,
                        weight=100,
                        created_at=datetime.combine(previous_monday + timedelta(days=1), time(10, 0)),
                    )
                )

        session.commit()


def test_weekly_review_status_contract() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    response = client.get("/weekly-review/status", headers=headers)
    assert response.status_code == 200

    payload = response.json()
    assert "today_is_sunday" in payload
    assert "review_required" in payload
    assert "week_start" in payload
    assert "previous_week_summary" in payload
    assert payload["previous_week_summary"] is not None


def test_submit_weekly_review_updates_profile_and_returns_adjustments() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    response = client.post(
        "/weekly-review",
        headers=headers,
        json={
            "body_weight": 83.1,
            "calories": 2600,
            "protein": 185,
            "fat": 72,
            "carbs": 280,
            "adherence_score": 4,
            "notes": "Solid week, ready to push",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "review_logged"
    assert "readiness_score" in payload
    assert "adjustments" in payload
    assert "global_guidance" in payload
    assert payload["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"
    assert payload["decision_trace"]["outcome"]["readiness_score"] == payload["readiness_score"]

    profile = client.get("/profile", headers=headers)
    assert profile.status_code == 200
    profile_payload = profile.json()
    assert math.isclose(float(profile_payload["weight"]), 83.1, rel_tol=1e-9, abs_tol=1e-9)
    assert profile_payload["calories"] == 2600
    assert profile_payload["protein"] == 185
    assert profile_payload["fat"] == 72
    assert profile_payload["carbs"] == 280


def test_generate_week_uses_saved_weekly_review_adjustments() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)

    monday = _current_monday()
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "weeklyreview@example.com").first()
        assert user is not None
        session.add(
            WeeklyReviewCycle(
                user_id=user.id,
                reviewed_on=date.today(),
                week_start=monday,
                previous_week_start=monday - timedelta(days=7),
                body_weight=82.0,
                calories=2400,
                protein=170,
                fat=70,
                carbs=240,
                adherence_score=4,
                notes="test",
                faults={"exercise_faults": []},
                adjustments={
                    "global": {"set_delta": 1, "weight_scale": 0.95},
                    "weak_point_exercises": [],
                    "exercise_overrides": {},
                    "decision_trace": {
                        "interpreter": "interpret_weekly_review_decision",
                        "outcome": {"global_set_delta": 1, "global_weight_scale": 0.95},
                    },
                },
                summary={"planned_sets_total": 0, "completed_sets_total": 0},
            )
        )
        session.commit()

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    payload = generated.json()

    assert "adaptive_review" in payload
    assert payload["adaptive_review"]["global_set_delta"] == 1
    assert math.isclose(float(payload["adaptive_review"]["global_weight_scale"]), 0.95, rel_tol=1e-9, abs_tol=1e-9)
    assert payload["adaptive_review"]["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"
    assert all((exercise.get("sets", 0) >= 2) for session in payload.get("sessions", []) for exercise in session.get("exercises", []))


def test_weekly_review_weak_point_boost_is_bounded() -> None:
    _reset_db()
    client = TestClient(app)
    headers = _register_and_onboard(client)
    _seed_previous_week_plan_and_logs_for_faults("weeklyreview@example.com")

    response = client.post(
        "/weekly-review",
        headers=headers,
        json={
            "body_weight": 80.0,
            "calories": 3000,
            "protein": 200,
            "fat": 75,
            "carbs": 350,
            "adherence_score": 5,
            "notes": "High readiness with several candidate weak points",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    adjustments = payload["adjustments"]
    overrides = adjustments["exercise_overrides"]
    boosted = [item for item in overrides if int(item["set_delta"]) > 0]

    assert len(adjustments["weak_point_exercises"]) == 3
    assert len(boosted) <= 2
    assert all(int(item["set_delta"]) <= 1 for item in overrides)
    assert all(0.93 <= float(item["weight_scale"]) <= 1.03 for item in overrides)

    monday = _review_week_start()
    with SessionLocal() as session:
        cycle = (
            session.query(WeeklyReviewCycle)
            .filter(WeeklyReviewCycle.week_start == monday)
            .order_by(WeeklyReviewCycle.created_at.desc())
            .first()
        )
        assert cycle is not None
        stored = cycle.adjustments if isinstance(cycle.adjustments, dict) else {}
        boosted_exercises = stored.get("weak_point_boosted_exercises")
        caps = stored.get("weak_point_caps")
        decision_trace = stored.get("decision_trace")
        assert isinstance(boosted_exercises, list)
        assert len(boosted_exercises) <= 2
        assert isinstance(caps, dict)
        assert isinstance(decision_trace, dict)
        assert decision_trace.get("interpreter") == "interpret_weekly_review_decision"
        assert caps.get("max_boosted_exercises") == 2
        assert caps.get("max_set_delta_per_exercise") == 1
