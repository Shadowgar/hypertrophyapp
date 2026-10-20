from copy import deepcopy
from datetime import date, timedelta
import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_program_catalog_and_selection")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import ExerciseState, User, WeeklyReviewCycle, WorkoutPlan, WorkoutSetLog
from app.routers import plan as plan_router

TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"
CANONICAL_GENERATED_FULL_BODY_ID = "full_body_v1"


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _seed_historical_generated_plan(client: TestClient, headers: dict[str, str], *, empty: bool = False) -> dict:
    """Explicit synthetic stored history; never constructs a new Customized program."""
    profile = client.get('/profile', headers=headers)
    assert profile.status_code == 200
    monday = date.today() - timedelta(days=date.today().weekday())
    exercises = [dict(id=id, primary_exercise_id=id, name=name, sets=3, rep_range=[8, 12],
        recommended_working_weight=20.0, start_weight=20.0, movement_pattern=pattern,
        primary_muscles=[muscle], equipment_tags=['machine'], substitution_candidates=[])
        for id, name, pattern, muscle in [('hack_squat', 'Hack squat', 'squat', 'quads'),
            ('chest_supported_machine_row', 'Machine row', 'horizontal_pull', 'back')]]
    payload = {'program_template_id': 'full_body_v1', 'split': 'full_body', 'phase': 'maintenance',
        'week_start': monday.isoformat(), 'historical_fixture': True,
        'mesocycle': {'week_index': 1, 'authored_week_index': 1},
        'weekly_volume_by_muscle': {'quads': 3, 'back': 3},
        'muscle_coverage': {'minimum_sets_per_muscle': 1, 'covered_muscles': ['quads', 'back'],
            'under_target_muscles': [], 'untracked_exercise_count': 0},
        'sessions': [] if empty else [{'session_id': 'full_body_v1-historical-day1',
            'title': 'Historical day 1', 'date': date.today().isoformat(), 'exercises': exercises}]}
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == profile.json()['email']).one()
        db.add(WorkoutPlan(user_id=user.id, week_start=monday, split='full_body',
            phase='maintenance', payload=deepcopy(payload)))
        db.commit()
    return payload


def _seed_prior_generated_weeks(*, user_id: str, weeks: int, program_template_id: str, gap_week_offsets: set[int] | None = None) -> None:
    monday = date.today() - timedelta(days=date.today().weekday())
    skipped_offsets = set(gap_week_offsets or set())
    with SessionLocal() as db:
        for offset in range(weeks):
            if offset in skipped_offsets:
                continue
            db.add(
                WorkoutPlan(
                    user_id=user_id,
                    week_start=monday - timedelta(days=7 * (weeks - offset)),
                    split="full_body",
                    phase="accumulation",
                    payload={"program_template_id": program_template_id, "sessions": []},
                )
            )
        db.commit()


def _assert_generated_full_body_runtime(plan: dict) -> dict:
    assert plan["program_template_id"] == CANONICAL_GENERATED_FULL_BODY_ID
    assert plan["template_selection_trace"]["selected_template_id"] == CANONICAL_GENERATED_FULL_BODY_ID
    runtime_trace = plan["template_selection_trace"]["generated_full_body_runtime_trace"]
    assert runtime_trace["compatibility_selected_template_id"] == CANONICAL_GENERATED_FULL_BODY_ID
    assert runtime_trace["compatibility_program_template_id"] == CANONICAL_GENERATED_FULL_BODY_ID
    assert runtime_trace["content_origin"] == "generated_constructor_applied"
    assert runtime_trace["generated_constructor_applied"] is True
    return runtime_trace


def _assert_minimum_generated_exercise_fields(exercise: dict) -> None:
    assert exercise["id"]
    assert exercise["name"]
    assert exercise["sets"] >= 1
    assert isinstance(exercise["rep_range"], list)
    assert len(exercise["rep_range"]) == 2
    assert float(exercise["recommended_working_weight"]) >= 0
    assert exercise["movement_pattern"]
    assert exercise["primary_muscles"]
    assert exercise["primary_exercise_id"]
    assert isinstance(exercise["substitution_candidates"], list)


def _advance_weeks_with_next_week(
    client: TestClient,
    headers: dict[str, str],
    *,
    weeks: int,
    request_payload: dict | None = None,
) -> dict:
    latest_payload: dict = {}
    for _ in range(weeks):
        response = client.post("/plan/next-week", headers=headers, json=request_payload or {})
        assert response.status_code == 200
        latest_payload = response.json()
    return latest_payload


# The retired live generated constructor scenarios are consolidated in
# test_generated_full_body_runtime_integration.test_retired_generated_writers_require_explicit_original_preview_without_mutation.
# Catalog, Authored selection and retained historical execution remain tested here.
def test_program_catalog_lists_templates() -> None:
    _reset_db()
    client = TestClient(app)

    response = client.get("/plan/programs")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert any(item["id"] == "pure_bodybuilding_phase_1_full_body" for item in payload)
    assert any(item["id"] == "pure_bodybuilding_phase_2_full_body" for item in payload)
    assert any(item["id"] == "full_body_v1" for item in payload)

    ids = {str(item.get("id")) for item in payload}
    assert ids == {
        "pure_bodybuilding_phase_1_full_body",
        "pure_bodybuilding_phase_2_full_body",
        "full_body_v1",
    }
    assert "adaptive_full_body_gold_v0_1" not in ids
    # These duplicate payload pairs exist in source imports and must collapse in API catalog.
    assert not {"my_new_program", "pure_bodybuilding_full_body"}.issubset(ids)
    assert not {
        "pure_bodybuilding_phase_2_full_body_sheet",
        "pure_bodybuilding_phase_2_full_body_sheet_1",
    }.issubset(ids)


def test_inactive_program_fallback_cannot_grant_customized_generation() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "catalog@example.com", "password": TEST_CREDENTIAL, "name": "Catalog User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Catalog User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "ppl",
            "selected_program_id": "ppl_v1",
            "training_location": "home",
            "equipment_profile": ["dumbbell", "bodyweight"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    before = client.get('/profile', headers=headers).json()
    generate = client.post('/plan/generate-week', headers=headers, json={})
    assert generate.status_code == 409
    assert generate.json()['detail']['code'] == 'customized_preview_required'
    assert generate.json()['detail']['path'] == '/customize'
    assert client.get('/profile', headers=headers).json() == before
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).count() == 0


def test_historical_generated_log_and_weekly_review_survive_writer_retirement() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-runtime-flow@example.com", "password": TEST_CREDENTIAL, "name": "Gold Flow User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Flow User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    initial_plan = _seed_historical_generated_plan(client, headers)
    first_session = initial_plan["sessions"][0]
    first_exercise = first_session["exercises"][0]

    log_response = client.post(
        f"/workout/{first_session['session_id']}/log-set",
        headers=headers,
        json={
            "primary_exercise_id": first_exercise.get("primary_exercise_id"),
            "exercise_id": first_exercise["id"],
            "set_index": 1,
            "reps": max(1, first_exercise["rep_range"][0] - 2),
            "weight": float(first_exercise["recommended_working_weight"]),
        },
    )
    assert log_response.status_code == 200
    log_payload = log_response.json()
    assert log_payload["decision_trace"]["interpreter"] == "interpret_workout_set_feedback"
    assert log_payload["guidance"] == "below_target_reps_reduce_or_hold_load"

    review_response = client.post(
        "/weekly-review",
        headers=headers,
        json={
            "body_weight": 81.5,
            "calories": 2550,
            "protein": 180,
            "fat": 70,
            "carbs": 270,
            "adherence_score": 2,
            "notes": "Gold path recovery and adherence check",
        },
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["status"] == "review_logged"
    assert review_payload["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"

    for route in ('/plan/generate-week', '/plan/next-week'):
        rejected = client.post(route, headers=headers, json={})
        assert rejected.status_code == 409
        assert rejected.json()['detail']['code'] == 'customized_preview_required'
        assert rejected.json()['detail']['path'] == '/customize'
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).count() == 1
        assert db.query(WeeklyReviewCycle).count() == 1
        assert db.query(WorkoutPlan).count() == 1
        assert db.query(WorkoutPlan).one().payload == initial_plan


def test_generate_week_does_not_invent_soreness_weight_adjustments_without_scheduler_doctrine() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "soreness-catalog@example.com", "password": TEST_CREDENTIAL, "name": "Soreness User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Soreness User",
            "age": 31,
            "weight": 84,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_1_full_body",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "rack"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2700,
            "protein": 190,
            "fat": 75,
            "carbs": 300,
        },
    )
    assert profile.status_code == 200

    baseline_response = client.post("/plan/generate-week", headers=headers, json={})
    assert baseline_response.status_code == 200
    baseline_plan = baseline_response.json()

    soreness_response = client.post(
        "/soreness",
        headers=headers,
        json={
            "entry_date": date.today().isoformat(),
            "severity_by_muscle": {
                "chest": "severe",
                "back": "moderate",
                "quads": "mild",
            },
            "notes": "Pre-workout soreness log",
        },
    )
    assert soreness_response.status_code == 201

    adjusted_response = client.post("/plan/generate-week", headers=headers, json={})
    assert adjusted_response.status_code == 200
    adjusted_plan = adjusted_response.json()

    baseline_push = baseline_plan["sessions"][0]["exercises"][0]
    baseline_pull = baseline_plan["sessions"][1]["exercises"][0]
    adjusted_push = adjusted_plan["sessions"][0]["exercises"][0]
    adjusted_pull = adjusted_plan["sessions"][1]["exercises"][0]

    assert adjusted_push["id"] == baseline_push["id"]
    assert adjusted_pull["id"] == baseline_pull["id"]
    assert adjusted_push["recommended_working_weight"] == baseline_push["recommended_working_weight"]
    assert adjusted_pull["recommended_working_weight"] == baseline_pull["recommended_working_weight"]


def test_authored_generate_week_includes_weekly_volume_and_coverage_payload() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "volume-catalog@example.com", "password": TEST_CREDENTIAL, "name": "Volume User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Volume User",
            "age": 29,
            "weight": 80,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_1_full_body",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "rack"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    assert "weekly_volume_by_muscle" in plan
    assert "muscle_coverage" in plan
    assert isinstance(plan["weekly_volume_by_muscle"], dict)
    assert isinstance(plan["muscle_coverage"], dict)
    assert "minimum_sets_per_muscle" in plan["muscle_coverage"]
    assert "under_target_muscles" in plan["muscle_coverage"]
    assert "covered_muscles" in plan["muscle_coverage"]


def test_generate_week_uses_repeat_failure_state_to_substitute_exercise(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)

    template = {
        "id": "repeat_failure_generation_v1",
        "sessions": [
            {
                "name": "Upper",
                "exercises": [
                    {
                        "id": "db_press",
                        "name": "DB Press",
                        "sets": 3,
                        "rep_range": [8, 10],
                        "start_weight": 25,
                        "equipment_tags": ["dumbbell"],
                        "substitution_candidates": ["DB Floor Press"],
                    }
                ],
            }
        ],
    }

    monkeypatch.setattr(
        plan_router,
        "list_program_templates",
        lambda: [{"id": "repeat_failure_generation_v1", "split": "full_body", "days_supported": [3]}],
    )
    monkeypatch.setattr(plan_router, "load_program_template", lambda template_id: template)

    register = client.post(
        "/auth/register",
        json={"email": "repeat-failure-generate@example.com", "password": TEST_CREDENTIAL, "name": "Repeat Failure User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Repeat Failure User",
            "age": 29,
            "weight": 81,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "repeat_failure_generation_v1",
            "training_location": "home",
            "equipment_profile": ["dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "repeat-failure-generate@example.com").first()
        assert user is not None
        session.add(
            ExerciseState(
                user_id=user.id,
                exercise_id="db_press",
                current_working_weight=25.0,
                exposure_count=5,
                consecutive_under_target_exposures=3,
                last_progression_action="hold",
                fatigue_score=0,
            )
        )
        session.commit()

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    exercise = plan["sessions"][0]["exercises"][0]
    assert exercise["id"] == "db_floor_press"
    assert exercise["name"] == "DB Floor Press"
    assert exercise["primary_exercise_id"] == "db_press"
    assert exercise["repeat_failure_substitution"]["recommended_name"] == "DB Floor Press"
    assert exercise["repeat_failure_substitution"]["failed_exposure_count"] == 3


def test_generate_week_keeps_all_exercises_without_canonical_time_budget_cap_rules(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)

    template = {
        "id": "time_budget_generation_v1",
        "sessions": [
            {
                "name": "Upper",
                "exercises": [
                    {"id": "lift_1", "name": "Lift 1", "sets": 3},
                    {"id": "lift_2", "name": "Lift 2", "sets": 3},
                    {"id": "lift_3", "name": "Lift 3", "sets": 3},
                    {"id": "lift_4", "name": "Lift 4", "sets": 3},
                    {"id": "lift_5", "name": "Lift 5", "sets": 3},
                    {"id": "lift_6", "name": "Lift 6", "sets": 3},
                ],
            }
        ],
    }

    monkeypatch.setattr(
        plan_router,
        "list_program_templates",
        lambda: [{"id": "time_budget_generation_v1", "split": "full_body", "days_supported": [3]}],
    )
    monkeypatch.setattr(plan_router, "load_program_template", lambda template_id: template)

    register = client.post(
        "/auth/register",
        json={"email": "time-budget-generate@example.com", "password": TEST_CREDENTIAL, "name": "Time Budget User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Time Budget User",
            "age": 29,
            "weight": 81,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "time_budget_generation_v1",
            "training_location": "home",
            "equipment_profile": ["dumbbell"],
            "days_available": 3,
            "session_time_budget_minutes": 30,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    assert [exercise["id"] for exercise in plan["sessions"][0]["exercises"]] == [
        "lift_1",
        "lift_2",
        "lift_3",
        "lift_4",
        "lift_5",
        "lift_6",
    ]


def test_generate_week_respects_profile_movement_restrictions(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)

    template = {
        "id": "movement_restriction_generation_v1",
        "sessions": [
            {
                "name": "Upper",
                "exercises": [
                    {"id": "ohp", "name": "Overhead Press", "sets": 3, "movement_pattern": "vertical_press"},
                    {"id": "row", "name": "Chest Supported Row", "sets": 3, "movement_pattern": "horizontal_pull"},
                ],
            }
        ],
    }

    monkeypatch.setattr(
        plan_router,
        "list_program_templates",
        lambda: [{"id": "movement_restriction_generation_v1", "split": "full_body", "days_supported": [3]}],
    )
    monkeypatch.setattr(plan_router, "load_program_template", lambda template_id: template)

    register = client.post(
        "/auth/register",
        json={"email": "movement-restriction-generate@example.com", "password": TEST_CREDENTIAL, "name": "Movement Restriction User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Movement Restriction User",
            "age": 29,
            "weight": 81,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "movement_restriction_generation_v1",
            "training_location": "home",
            "equipment_profile": ["dumbbell"],
            "days_available": 3,
            "movement_restrictions": ["overhead_pressing"],
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    assert [exercise["id"] for exercise in plan["sessions"][0]["exercises"]] == ["row"]


def test_generate_week_falls_back_to_equipment_safe_template(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)

    template_unusable = {
        "id": "ppl_v1",
        "sessions": [
            {
                "name": "Push",
                "exercises": [
                    {
                        "id": "bench",
                        "name": "Bench Press",
                        "sets": 3,
                        "rep_range": [8, 10],
                        "start_weight": 60,
                        "equipment_tags": ["barbell"],
                        "substitution_candidates": [],
                    }
                ],
            }
        ],
    }
    template_fallback = {
        "id": "upper_lower_v1",
        "sessions": [
            {
                "name": "Upper",
                "exercises": [
                    {
                        "id": "db_press",
                        "name": "DB Press",
                        "sets": 3,
                        "rep_range": [8, 10],
                        "start_weight": 25,
                        "equipment_tags": ["dumbbell"],
                        "substitution_candidates": [],
                    }
                ],
            }
        ],
    }
    template_map = {
        "ppl_v1": template_unusable,
        "upper_lower_v1": template_fallback,
    }

    monkeypatch.setattr(
        plan_router,
        "list_program_templates",
        lambda: [
            {"id": "ppl_v1", "split": "ppl", "days_supported": [3]},
            {"id": "upper_lower_v1", "split": "ppl", "days_supported": [3]},
        ],
    )
    monkeypatch.setattr(plan_router, "load_program_template", lambda template_id: template_map[template_id])

    register = client.post(
        "/auth/register",
        json={"email": "fallback-catalog@example.com", "password": TEST_CREDENTIAL, "name": "Fallback User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Fallback User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "ppl",
            "selected_program_id": "ppl_v1",
            "training_location": "home",
            "equipment_profile": ["dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    assert plan["program_template_id"] == "upper_lower_v1"
    assert plan["template_selection_trace"]["selected_template_id"] == "upper_lower_v1"
    assert plan["template_selection_trace"]["reason"] == "first_viable_candidate"
    assert len(plan["sessions"]) == 1
    assert plan["sessions"][0]["exercises"][0]["id"] == "db_press"


def test_generate_week_explicit_template_override_is_respected(monkeypatch) -> None:
    _reset_db()
    client = TestClient(app)

    explicit_template = {
        "id": "explicit_template",
        "sessions": [
            {
                "name": "Only Session",
                "exercises": [
                    {
                        "id": "bw_pushup",
                        "name": "Push-up",
                        "sets": 3,
                        "rep_range": [8, 12],
                        "start_weight": 5,
                        "equipment_tags": ["bodyweight"],
                    }
                ],
            }
        ],
    }

    monkeypatch.setattr(plan_router, "list_program_templates", lambda: [])
    monkeypatch.setattr(plan_router, "load_program_template", lambda template_id: explicit_template)

    register = client.post(
        "/auth/register",
        json={"email": "explicit-catalog@example.com", "password": TEST_CREDENTIAL, "name": "Explicit User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Explicit User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_1_full_body",
            "training_location": "home",
            "equipment_profile": ["bodyweight"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    generate = client.post(
        "/plan/generate-week",
        headers=headers,
        json={"template_id": "explicit_template"},
    )
    assert generate.status_code == 200
    plan = generate.json()

    assert plan["program_template_id"] == "explicit_template"
    assert plan["template_selection_trace"]["reason"] == "explicit_template_override"
    assert plan["sessions"][0]["session_id"].startswith("explicit_template-")


def test_phase2_generate_week_uses_canonical_template_and_keeps_week1_non_deload() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "phase2-week1@example.com", "password": TEST_CREDENTIAL, "name": "Phase2 Week1 User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Phase2 Week1 User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_2_full_body",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()
    assert plan["program_template_id"] == "pure_bodybuilding_phase_2_full_body"
    assert plan["mesocycle"]["authored_week_index"] == 1
    assert plan["mesocycle"]["authored_week_role"] == "intensification"
    assert plan["mesocycle"]["is_deload_week"] is False
    assert plan["mesocycle"]["deload_reason"] == "none"
    assert plan["mesocycle"]["transition_checkpoint"] is False


def test_phase2_generate_week_uses_week_five_before_transition() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "phase2-week5@example.com", "password": TEST_CREDENTIAL, "name": "Phase2 Week5 User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Phase2 Week5 User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_2_full_body",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200
    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = _advance_weeks_with_next_week(client, headers, weeks=4)
    assert plan["mesocycle"]["authored_week_index"] == 5
    assert plan["mesocycle"]["authored_week_role"] == "intensification"
    assert plan["mesocycle"]["is_deload_week"] is False


def test_phase2_generate_week_week_five_to_six_transition_is_checkpoint() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "phase2-week6@example.com", "password": TEST_CREDENTIAL, "name": "Phase2 Week6 User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Phase2 Week6 User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_2_full_body",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200
    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = _advance_weeks_with_next_week(client, headers, weeks=5)
    assert plan["mesocycle"]["authored_week_index"] == 6
    assert plan["mesocycle"]["authored_week_role"] == "intensification"
    assert plan["mesocycle"]["is_deload_week"] is True
    assert plan["mesocycle"]["transition_checkpoint"] is False
    assert plan["mesocycle"]["deload_reason"] == "scheduled"


def test_phase2_generate_week_supports_interruption_and_resume_and_week_ten() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "phase2-week10@example.com", "password": TEST_CREDENTIAL, "name": "Phase2 Week10 User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Phase2 Week10 User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_2_full_body",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200
    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    # Current-week regenerate should not advance progression state.
    regenerate = client.post("/plan/generate-week", headers=headers, json={})
    assert regenerate.status_code == 200
    plan = _advance_weeks_with_next_week(client, headers, weeks=9)
    assert plan["mesocycle"]["authored_week_index"] == 10
    assert plan["mesocycle"]["authored_week_role"] == "intensification"


def test_phase2_time_budget_compression_applies_across_block_transition() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "phase2-budget@example.com", "password": TEST_CREDENTIAL, "name": "Phase2 Budget User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Phase2 Budget User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_2_full_body",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 3,
            "session_time_budget_minutes": 30,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200
    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = _advance_weeks_with_next_week(client, headers, weeks=5)
    assert plan["mesocycle"]["authored_week_index"] == 6
    recovery_step = next(
        step
        for step in plan["generation_runtime_trace"]["steps"]
        if step["decision"] == "recovery_inputs"
    )
    assert recovery_step["result"]["session_time_budget_minutes"] == 30


def test_phase2_movement_restrictions_remain_enforced_on_rotated_weeks() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "phase2-restrict@example.com", "password": TEST_CREDENTIAL, "name": "Phase2 Restriction User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Phase2 Restriction User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "pure_bodybuilding_phase_2_full_body",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 3,
            "movement_restrictions": ["overhead_pressing"],
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "phase2-restrict@example.com").first()
        assert user is not None
        _seed_prior_generated_weeks(
            user_id=user.id,
            weeks=7,
            program_template_id="pure_bodybuilding_phase_2_full_body",
        )

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()
    patterns = {
        str(exercise.get("movement_pattern") or "")
        for session in plan["sessions"]
        for exercise in session["exercises"]
    }
    assert "vertical_press" in patterns  # Preserve source slots; conflict blocks execution, not dose.
    conflicts = [e for session in plan['sessions'] for e in session['exercises'] if e.get('movement_pattern') == 'vertical_press']
    assert conflicts and all(e['authored_constraint']['status'] in {'unresolved', 'infeasible'} for e in conflicts)
    assert all(any(r['kind'] == 'restriction' and 'overhead_pressing' in r['details']
        for r in e['authored_constraint']['reasons']) for e in conflicts)
