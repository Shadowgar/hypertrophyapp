from datetime import date, timedelta
import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_program_catalog_and_selection")

from app.database import Base, engine
from app.main import app
from app.routers import plan as plan_router

TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_program_catalog_lists_templates() -> None:
    _reset_db()
    client = TestClient(app)

    response = client.get("/plan/programs")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert any(item["id"] == "full_body_v1" for item in payload)

    ids = {str(item.get("id")) for item in payload}
    # These duplicate payload pairs exist in source imports and must collapse in API catalog.
    assert not {"my_new_program", "pure_bodybuilding_full_body"}.issubset(ids)
    assert not {
        "pure_bodybuilding_phase_2_full_body_sheet",
        "pure_bodybuilding_phase_2_full_body_sheet_1",
    }.issubset(ids)


def test_generate_week_uses_selected_program_when_template_not_passed() -> None:
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

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()
    assert len(plan["sessions"]) > 0
    assert plan["sessions"][0]["session_id"].startswith("ppl_v1-")
    assert plan["template_selection_trace"]["interpreter"] == "recommend_generation_template_selection"
    assert plan["template_selection_trace"]["selected_template_id"] == "ppl_v1"
    assert plan["generation_runtime_trace"]["interpreter"] == "resolve_week_generation_runtime_inputs"
    assert plan["generation_runtime_trace"]["outcome"]["effective_days_available"] == 3


def test_generate_week_applies_latest_soreness_modifiers() -> None:
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
            "split_preference": "ppl",
            "selected_program_id": "ppl_v1",
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

    assert baseline_push["id"] == "bench"
    assert baseline_pull["id"] == "row"
    assert adjusted_push["id"] == "bench"
    assert adjusted_pull["id"] == "row"
    assert adjusted_push["recommended_working_weight"] < baseline_push["recommended_working_weight"]
    assert adjusted_pull["recommended_working_weight"] < baseline_pull["recommended_working_weight"]


def test_generate_week_includes_weekly_volume_and_coverage_payload() -> None:
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
            "split_preference": "ppl",
            "selected_program_id": "ppl_v1",
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


def test_generate_week_includes_mesocycle_and_deload_payload() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "mesocycle-catalog@example.com", "password": TEST_CREDENTIAL, "name": "Mesocycle User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Mesocycle User",
            "age": 33,
            "weight": 85,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "full_body_v1",
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

    monday = date.today() - timedelta(days=date.today().weekday())
    weekly_checkin = client.post(
        "/weekly-checkin",
        headers=headers,
        json={
            "week_start": monday.isoformat(),
            "body_weight": 84.5,
            "adherence_score": 2,
            "notes": "high fatigue",
        },
    )
    assert weekly_checkin.status_code == 200

    soreness_response = client.post(
        "/soreness",
        headers=headers,
        json={
            "entry_date": date.today().isoformat(),
            "severity_by_muscle": {
                "chest": "severe",
                "back": "severe",
            },
            "notes": "high soreness",
        },
    )
    assert soreness_response.status_code == 201

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    assert plan["program_template_id"] == "full_body_v1"
    assert plan["mesocycle"]["is_deload_week"] is True
    assert plan["mesocycle"]["deload_reason"] == "early_soreness+early_adherence"
    assert plan["deload"]["active"] is True
    assert plan["generation_runtime_trace"]["outcome"]["severe_soreness_count"] == 2
    assert plan["generation_runtime_trace"]["outcome"]["latest_adherence_score"] == 2


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
            "selected_program_id": "full_body_v1",
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
