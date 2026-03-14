from datetime import date, timedelta
import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_profile_training_state")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import ExerciseState, SorenessEntry, User, WeeklyCheckin, WeeklyReviewCycle, WorkoutPlan, WorkoutSetLog

TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_and_onboard(client: TestClient) -> tuple[dict[str, str], str]:
    register = client.post(
        "/auth/register",
        json={"email": "trainingstate@example.com", "password": TEST_CREDENTIAL, "name": "Training State"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Training State",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_1_full_body",
            "training_location": "gym",
            "equipment_profile": ["barbell", "dumbbell", "bench", "rack"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
            "session_time_budget_minutes": 75,
            "movement_restrictions": ["deep_knee_flexion"],
            "near_failure_tolerance": "moderate",
        },
    )
    assert profile.status_code == 200
    return headers, "trainingstate@example.com"


def test_profile_training_state_returns_canonical_runtime_payload() -> None:
    _reset_db()
    client = TestClient(app)
    headers, email = _register_and_onboard(client)

    current_week_start = date.today() - timedelta(days=date.today().weekday())
    today_iso = date.today().isoformat()

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == email).first()
        assert user is not None
        session.add(
            WorkoutPlan(
                user_id=user.id,
                week_start=current_week_start,
                split="full_body",
                phase="accumulation",
                payload={
                    "program_template_id": "pure_bodybuilding_phase_1_full_body",
                    "phase": "accumulation",
                    "week_start": current_week_start.isoformat(),
                    "mesocycle": {"week_index": 3, "trigger_weeks_effective": 5},
                    "muscle_coverage": {"under_target_muscles": ["biceps", "rear_delts"]},
                    "sessions": [
                        {
                            "session_id": "pure_bodybuilding_phase_1_full_body-session-today",
                            "title": "Today Session",
                            "date": today_iso,
                            "exercises": [{"id": "bench_press_barbell", "sets": 3}],
                        }
                    ],
                },
            )
        )
        session.add(
                WorkoutSetLog(
                    user_id=user.id,
                    workout_id="pure_bodybuilding_phase_1_full_body-session-today",
                    primary_exercise_id="bench_press_barbell",
                    exercise_id="bench_press_barbell",
                set_index=1,
                reps=8,
                weight=100.0,
                rpe=8.5,
            )
        )
        session.add(
            ExerciseState(
                user_id=user.id,
                exercise_id="bench_press_barbell",
                current_working_weight=100.0,
                exposure_count=6,
                consecutive_under_target_exposures=3,
                last_progression_action="hold",
                fatigue_score=0.85,
            )
        )
        session.add(
            SorenessEntry(
                user_id=user.id,
                entry_date=date.today(),
                severity_by_muscle={"chest": "severe", "back": "severe"},
                notes="high fatigue",
            )
        )
        session.add(
            WeeklyCheckin(
                user_id=user.id,
                week_start=current_week_start,
                body_weight=82.0,
                adherence_score=4,
                sleep_quality=2,
                stress_level=4,
                pain_flags=["elbow_flexion"],
                notes="solid week",
            )
        )
        session.add(
            WeeklyReviewCycle(
                user_id=user.id,
                reviewed_on=date.today(),
                week_start=current_week_start,
                previous_week_start=current_week_start - timedelta(days=7),
                body_weight=82.0,
                calories=2600,
                protein=180,
                fat=70,
                carbs=280,
                adherence_score=4,
                notes="some stall signs",
                faults={"exercise_faults": [{"exercise_id": "bench_press_barbell"}]},
                adjustments={"global": {"set_delta": -1, "weight_scale": 0.95}},
                summary={"faulty_exercise_count": 1},
            )
        )
        session.commit()

    response = client.get("/profile/training-state", headers=headers)
    assert response.status_code == 200

    payload = response.json()
    assert payload["user_program_state"]["program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert payload["user_program_state"]["phase_id"] == "accumulation"
    assert payload["user_program_state"]["week_index"] == 3
    assert payload["user_program_state"]["session_id"] == "pure_bodybuilding_phase_1_full_body-session-today"
    assert payload["user_program_state"]["last_generated_week_start"] == current_week_start.isoformat()
    assert payload["exercise_performance_history"][0]["exercise_id"] == "bench_press_barbell"
    assert payload["progression_state_per_exercise"][0] == {
        "exercise_id": "bench_press_barbell",
        "current_working_weight": 100.0,
        "exposure_count": 6,
        "consecutive_under_target_exposures": 3,
        "last_progression_action": "hold",
        "fatigue_score": 0.85,
        "last_updated_at": payload["progression_state_per_exercise"][0]["last_updated_at"],
    }
    assert payload["fatigue_state"]["recovery_state"] == "high_fatigue"
    assert payload["fatigue_state"]["soreness_by_muscle"] == {"chest": "severe", "back": "severe"}
    assert payload["adherence_state"] == {
        "latest_adherence_score": 4,
        "rolling_average_score": 4.0,
        "missed_session_count": 0,
    }
    assert payload["readiness_state"] == {
        "sleep_quality": 2,
        "stress_level": 4,
        "pain_flags": ["elbow_flexion"],
        "recovery_risk_flags": ["high_stress", "low_sleep", "pain_flags_present"],
    }
    assert payload["stimulus_fatigue_response"] == {
        "stimulus_quality": "moderate",
        "fatigue_cost": "high",
        "recoverability": "low",
        "progression_eligibility": False,
        "deload_pressure": "high",
        "substitution_pressure": "high",
        "signals": {
            "stimulus": ["high_completion", "high_adherence"],
            "fatigue": ["elevated_soreness", "low_sleep", "high_stress", "pain_flags_present"],
            "recoverability": ["sleep_limited", "stress_limited", "pain_limited", "fatigue_limited"],
        },
    }
    assert payload["constraint_state"] == {
        "days_available": 3,
        "split_preference": "full_body",
        "training_location": "gym",
        "equipment_profile": ["barbell", "dumbbell", "bench", "rack"],
        "weak_areas": [],
        "nutrition_phase": "maintenance",
        "session_time_budget_minutes": 75,
        "movement_restrictions": ["deep_knee_flexion"],
        "near_failure_tolerance": "moderate",
    }
    assert payload["stall_state"] == {
        "stalled_exercise_ids": ["bench_press_barbell"],
        "consecutive_underperformance_weeks": 1,
        "phase_stagnation_weeks": 1,
    }
    assert payload["coaching_state"]["stimulus_fatigue_response"] == payload["stimulus_fatigue_response"]
    assert payload["generation_state"] == {
        "prior_generated_weeks_by_program": {"pure_bodybuilding_phase_1_full_body": 1},
        "under_target_muscles": ["biceps", "rear_delts"],
        "mesocycle_trigger_weeks_effective": 5,
        "latest_mesocycle": {
            "week_index": 3,
            "trigger_weeks_effective": 5,
            "authored_week_index": None,
            "authored_week_role": None,
            "authored_sequence_length": None,
            "authored_sequence_complete": False,
            "phase_transition_pending": False,
            "phase_transition_reason": None,
            "post_authored_behavior": None,
        },
    }
