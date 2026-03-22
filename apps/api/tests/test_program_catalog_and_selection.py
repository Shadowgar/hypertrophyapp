from datetime import date, timedelta
import uuid

from fastapi.testclient import TestClient

from test_db import configure_test_database

configure_test_database("test_program_catalog_and_selection")

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import ExerciseState, User, WeeklyReviewCycle, WorkoutPlan
from app.routers import plan as plan_router

TEST_CREDENTIAL = f"T{uuid.uuid4().hex[:15]}"
CANONICAL_GENERATED_FULL_BODY_ID = "full_body_v1"


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


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
    assert "ppl_v1" not in ids
    assert "upper_lower_v1" not in ids
    # These duplicate payload pairs exist in source imports and must collapse in API catalog.
    assert not {"my_new_program", "pure_bodybuilding_full_body"}.issubset(ids)
    assert not {
        "pure_bodybuilding_phase_2_full_body_sheet",
        "pure_bodybuilding_phase_2_full_body_sheet_1",
    }.issubset(ids)


def test_generate_week_uses_canonical_template_when_non_active_program_is_selected() -> None:
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
    assert plan["sessions"][0]["session_id"].startswith("full_body_v1-")
    assert plan["decision_trace"]["owner_family"] == "generated_week"
    assert plan["decision_trace"]["canonical_inputs"]["selected_template_id"] == "full_body_v1"
    assert plan["decision_trace"]["execution_steps"][0]["step"] == "template_selection"
    assert plan["decision_trace"]["reason_summary"]
    assert plan["template_selection_trace"]["interpreter"] == "recommend_generation_template_selection"
    assert plan["template_selection_trace"]["selected_template_id"] == "full_body_v1"
    assert plan["generation_runtime_trace"]["interpreter"] == "resolve_week_generation_runtime_inputs"
    assert plan["generation_runtime_trace"]["outcome"]["effective_days_available"] == 3


def test_generate_week_supports_adaptive_gold_runtime_program() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-catalog@example.com", "password": TEST_CREDENTIAL, "name": "Gold User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold User",
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

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    _assert_generated_full_body_runtime(plan)
    assert len(plan["sessions"]) == 3
    assert [session["title"] for session in plan["sessions"]] == [
        "Generated Full Body 1",
        "Generated Full Body 2",
        "Generated Full Body 3",
    ]
    assert [len(session["exercises"]) for session in plan["sessions"]] == [4, 4, 4]
    assert plan["mesocycle"]["authored_week_index"] == 1
    assert plan["mesocycle"]["week_index"] == 1
    assert any(exercise["movement_pattern"] == "hinge" for session in plan["sessions"] for exercise in session["exercises"])


def test_generate_week_preserves_generated_full_body_identity() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "legacy-full-body@example.com", "password": TEST_CREDENTIAL, "name": "Legacy Full Body User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Legacy Full Body User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "full_body_v1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 5,
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

    assert plan["program_template_id"] == "full_body_v1"
    assert plan["template_selection_trace"]["selected_template_id"] == "full_body_v1"


def test_adaptive_gold_generate_week_exposes_minimum_generated_exercise_fields() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-authored-runtime@example.com", "password": TEST_CREDENTIAL, "name": "Gold Runtime User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Runtime User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 5,
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

    _assert_generated_full_body_runtime(plan)
    first_exercise = plan["sessions"][0]["exercises"][0]
    _assert_minimum_generated_exercise_fields(first_exercise)
    assert first_exercise.get("demo_url") is None
    assert first_exercise.get("video_url") is None
    assert first_exercise.get("notes") is None


def test_adaptive_gold_generate_week_includes_core_slot_when_equipment_available() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-core-slot@example.com", "password": TEST_CREDENTIAL, "name": "Gold Core User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Core User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine"],
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

    _assert_generated_full_body_runtime(plan)
    assert [len(session["exercises"]) for session in plan["sessions"]] == [4, 4, 4]
    exercises = [exercise for session in plan["sessions"] for exercise in session["exercises"]]
    assert any(
        "cable" in item.get("equipment_tags", []) or "machine" in item.get("equipment_tags", [])
        for item in exercises
    )


def test_adaptive_gold_generate_week_includes_hinge_slot_when_equipment_available() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-hinge-slot@example.com", "password": TEST_CREDENTIAL, "name": "Gold Hinge User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Hinge User",
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

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    _assert_generated_full_body_runtime(plan)
    exercises = [exercise for session in plan["sessions"] for exercise in session["exercises"]]
    hinge_exercise = next(item for item in exercises if item["movement_pattern"] == "hinge")
    assert any(tag in hinge_exercise["equipment_tags"] for tag in {"barbell", "dumbbell", "machine"})


def test_adaptive_gold_generate_week_includes_weak_point_slots_when_equipment_available() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-weak-slots@example.com", "password": TEST_CREDENTIAL, "name": "Gold Weak User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Weak User",
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

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    _assert_generated_full_body_runtime(plan)
    exercises = [exercise for session in plan["sessions"] for exercise in session["exercises"]]
    assert not any(exercise["id"].startswith("weak_point_exercise_") for exercise in exercises)


def test_adaptive_gold_generate_week_uses_generated_accessory_fill_patterns_when_equipment_available() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-arm-slots@example.com", "password": TEST_CREDENTIAL, "name": "Gold Arm User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Arm User",
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

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    _assert_generated_full_body_runtime(plan)
    exercises = [exercise for session in plan["sessions"] for exercise in session["exercises"]]
    assert any(
        exercise["movement_pattern"] in {"knee_extension", "triceps_extension", "leg_curl", "curl"}
        for exercise in exercises
    )


def test_adaptive_gold_generate_week_preserves_weak_point_days_when_frequency_compresses() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-weak-compression@example.com", "password": TEST_CREDENTIAL, "name": "Gold Compression User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Compression User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 2,
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

    _assert_generated_full_body_runtime(plan)
    titles = [session["title"] for session in plan["sessions"]]
    assert len(titles) == 2
    assert titles == ["Generated Full Body 1", "Generated Full Body 2"]
    assert [len(session["exercises"]) for session in plan["sessions"]] == [4, 4]


def test_adaptive_gold_generate_week_bounds_time_budget_for_generated_runtime() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-weak-time-budget@example.com", "password": TEST_CREDENTIAL, "name": "Gold Time User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Time User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
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
    plan = generate.json()

    _assert_generated_full_body_runtime(plan)
    assert [len(session["exercises"]) for session in plan["sessions"]] == [3, 3, 3]


def test_adaptive_gold_generate_week_selects_second_authored_week_after_prior_week() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-week-two@example.com", "password": TEST_CREDENTIAL, "name": "Gold Week Two User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Week Two User",
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

    monday = date.today() - timedelta(days=date.today().weekday())
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "gold-week-two@example.com").first()
        assert user is not None
        db.add(
            WorkoutPlan(
                user_id=user.id,
                week_start=monday - timedelta(days=7),
                split="full_body",
                phase="accumulation",
                payload={
                    "program_template_id": "adaptive_full_body_gold_v0_1",
                    "sessions": [],
                },
            )
        )
        db.commit()

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    _assert_generated_full_body_runtime(plan)
    assert plan["generation_runtime_trace"]["outcome"]["prior_generated_weeks"] == 1
    assert plan["mesocycle"]["authored_week_index"] == 2
    assert plan["mesocycle"]["authored_week_role"] == "adaptation"
    assert all(session["exercises"] for session in plan["sessions"])


def test_adaptive_gold_week_two_preserves_weak_point_structure_under_constraints() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-week-two-constraints@example.com", "password": TEST_CREDENTIAL, "name": "Gold Week Two Constraints"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Week Two Constraints",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "cable", "machine", "dumbbell"],
            "days_available": 2,
            "session_time_budget_minutes": 30,
            "nutrition_phase": "maintenance",
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
        },
    )
    assert profile.status_code == 200

    monday = date.today() - timedelta(days=date.today().weekday())
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "gold-week-two-constraints@example.com").first()
        assert user is not None
        db.add(
            WorkoutPlan(
                user_id=user.id,
                week_start=monday - timedelta(days=7),
                split="full_body",
                phase="accumulation",
                payload={
                    "program_template_id": "adaptive_full_body_gold_v0_1",
                    "sessions": [],
                },
            )
        )
        db.commit()

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    _assert_generated_full_body_runtime(plan)
    titles = [session["title"] for session in plan["sessions"]]
    assert titles == ["Generated Full Body 1", "Generated Full Body 2"]
    assert all(len(session["exercises"]) <= 3 for session in plan["sessions"])
    assert not any(
        exercise["id"].startswith("weak_point_exercise_")
        for session in plan["sessions"]
        for exercise in session["exercises"]
    )


def test_adaptive_gold_generate_week_selects_third_authored_week_after_two_prior_weeks() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-week-three@example.com", "password": TEST_CREDENTIAL, "name": "Gold Week Three User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Week Three User",
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

    monday = date.today() - timedelta(days=date.today().weekday())
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "gold-week-three@example.com").first()
        assert user is not None
        db.add_all(
            [
                WorkoutPlan(
                    user_id=user.id,
                    week_start=monday - timedelta(days=14),
                    split="full_body",
                    phase="accumulation",
                    payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []},
                ),
                WorkoutPlan(
                    user_id=user.id,
                    week_start=monday - timedelta(days=7),
                    split="full_body",
                    phase="accumulation",
                    payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []},
                ),
            ]
        )
        db.commit()

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    _assert_generated_full_body_runtime(plan)
    assert plan["generation_runtime_trace"]["outcome"]["prior_generated_weeks"] == 2
    assert plan["mesocycle"]["authored_week_index"] == 3
    assert plan["mesocycle"]["authored_week_role"] == "accumulation"
    assert all(session["exercises"] for session in plan["sessions"])


def test_adaptive_gold_generate_week_uses_authored_deload_week_six() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-week-six-deload@example.com", "password": TEST_CREDENTIAL, "name": "Gold Week Six User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Week Six User",
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

    monday = date.today() - timedelta(days=date.today().weekday())
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "gold-week-six-deload@example.com").first()
        assert user is not None
        db.add_all(
            [
                WorkoutPlan(
                    user_id=user.id,
                    week_start=monday - timedelta(days=35),
                    split="full_body",
                    phase="accumulation",
                    payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []},
                ),
                WorkoutPlan(
                    user_id=user.id,
                    week_start=monday - timedelta(days=28),
                    split="full_body",
                    phase="accumulation",
                    payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []},
                ),
                WorkoutPlan(
                    user_id=user.id,
                    week_start=monday - timedelta(days=21),
                    split="full_body",
                    phase="accumulation",
                    payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []},
                ),
                WorkoutPlan(
                    user_id=user.id,
                    week_start=monday - timedelta(days=14),
                    split="full_body",
                    phase="accumulation",
                    payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []},
                ),
                WorkoutPlan(
                    user_id=user.id,
                    week_start=monday - timedelta(days=7),
                    split="full_body",
                    phase="accumulation",
                    payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []},
                ),
            ]
        )
        db.commit()

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    _assert_generated_full_body_runtime(plan)
    assert plan["generation_runtime_trace"]["outcome"]["prior_generated_weeks"] == 5
    assert plan["mesocycle"]["authored_week_index"] == 6
    assert plan["mesocycle"]["authored_week_role"] == "intensification"
    assert plan["mesocycle"]["is_deload_week"] is True
    assert plan["mesocycle"]["deload_reason"] == "scheduled"
    assert plan["deload"]["active"] is True
    assert all(exercise["sets"] < 3 for exercise in plan["sessions"][0]["exercises"])


def test_adaptive_gold_generate_week_selects_week_eight_intensification() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-week-eight@example.com", "password": TEST_CREDENTIAL, "name": "Gold Week Eight User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Week Eight User",
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

    monday = date.today() - timedelta(days=date.today().weekday())
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "gold-week-eight@example.com").first()
        assert user is not None
        db.add_all(
            [
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=49), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=42), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=35), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=28), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=21), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=14), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=7), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
            ]
        )
        db.commit()

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    _assert_generated_full_body_runtime(plan)
    assert plan["generation_runtime_trace"]["outcome"]["prior_generated_weeks"] == 7
    assert plan["mesocycle"]["authored_week_index"] == 8
    assert plan["mesocycle"]["authored_week_role"] == "intensification"
    assert all(session["exercises"] for session in plan["sessions"])


def test_adaptive_gold_generate_week_selects_week_ten_intensification() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-week-ten@example.com", "password": TEST_CREDENTIAL, "name": "Gold Week Ten User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Week Ten User",
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

    monday = date.today() - timedelta(days=date.today().weekday())
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "gold-week-ten@example.com").first()
        assert user is not None
        db.add_all(
            [
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=63), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=56), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=49), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=42), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=35), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=28), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=21), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=14), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=7), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
            ]
        )
        db.commit()

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    _assert_generated_full_body_runtime(plan)
    assert plan["generation_runtime_trace"]["outcome"]["prior_generated_weeks"] == 9
    assert plan["mesocycle"]["authored_week_index"] == 10
    assert plan["mesocycle"]["authored_week_role"] == "intensification"
    assert all(session["exercises"] for session in plan["sessions"])


def test_adaptive_gold_generate_week_marks_transition_pending_after_authored_sequence_complete() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-post-week-ten@example.com", "password": TEST_CREDENTIAL, "name": "Gold Post Week Ten User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Post Week Ten User",
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

    monday = date.today() - timedelta(days=date.today().weekday())
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "gold-post-week-ten@example.com").first()
        assert user is not None
        db.add_all(
            [
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=70), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=63), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=56), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=49), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=42), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=35), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=28), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=21), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=14), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
                WorkoutPlan(user_id=user.id, week_start=monday - timedelta(days=7), split="full_body", phase="accumulation", payload={"program_template_id": "adaptive_full_body_gold_v0_1", "sessions": []}),
            ]
        )
        db.commit()

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    _assert_generated_full_body_runtime(plan)
    assert plan["generation_runtime_trace"]["outcome"]["prior_generated_weeks"] == 10
    assert plan["mesocycle"]["authored_week_index"] == 10
    assert plan["mesocycle"]["authored_week_role"] == "intensification"
    assert plan["mesocycle"]["authored_sequence_complete"] is True
    assert plan["mesocycle"]["phase_transition_pending"] is True
    assert plan["mesocycle"]["phase_transition_reason"] == "authored_sequence_complete"
    assert plan["mesocycle"]["post_authored_behavior"] == "hold_last_authored_week"


def test_adaptive_gold_runtime_path_survives_logset_and_weekly_review() -> None:
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

    initial_generate = client.post("/plan/generate-week", headers=headers, json={})
    assert initial_generate.status_code == 200
    initial_plan = initial_generate.json()
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

    next_generate = client.post("/plan/generate-week", headers=headers, json={})
    assert next_generate.status_code == 200
    next_plan = next_generate.json()

    _assert_generated_full_body_runtime(next_plan)
    # adaptive_review is present when the generated week has a matching saved review (same week_start)
    if next_plan.get("adaptive_review"):
        assert next_plan["adaptive_review"]["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"
        assert next_plan["adaptive_review"]["global_weight_scale"] <= 1.0
    assert len(next_plan["sessions"]) == 3
    assert any(exercise["movement_pattern"] == "hinge" for session in next_plan["sessions"] for exercise in session["exercises"])


def test_adaptive_gold_generate_week_uses_repeat_failure_substitution() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-repeat-failure@example.com", "password": TEST_CREDENTIAL, "name": "Gold Repeat User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Repeat User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "dumbbell"],
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
        user = session.query(User).filter(User.email == "gold-repeat-failure@example.com").first()
        assert user is not None
        session.add(
            ExerciseState(
                user_id=user.id,
                exercise_id="bottom_half_low_incline_db_press",
                current_working_weight=20.0,
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
    _assert_generated_full_body_runtime(plan)

    exercise = next(
        item
        for session in plan["sessions"]
        for item in session["exercises"]
        if item.get("primary_exercise_id") == "bottom_half_low_incline_db_press"
    )
    assert exercise["id"] == "bottom_half_low_incline_db_press"
    assert exercise["name"] == "Bottom-Half Low Incline DB Press"
    assert exercise["primary_exercise_id"] == "bottom_half_low_incline_db_press"
    assert exercise["movement_pattern"] == "horizontal_press"
    assert exercise["repeat_failure_substitution"] is None


def test_adaptive_gold_generate_week_uses_repeat_failure_substitution_for_second_exercise() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-repeat-failure-row@example.com", "password": TEST_CREDENTIAL, "name": "Gold Repeat Row User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Repeat Row User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["dumbbell", "machine"],
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
        user = session.query(User).filter(User.email == "gold-repeat-failure-row@example.com").first()
        assert user is not None
        session.add(
            ExerciseState(
                user_id=user.id,
                exercise_id="chest_supported_machine_row",
                current_working_weight=20.0,
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
    _assert_generated_full_body_runtime(plan)

    exercise = next(
        item
        for session in plan["sessions"]
        for item in session["exercises"]
        if item.get("primary_exercise_id") == "chest_supported_machine_row"
    )
    assert exercise["id"] == "chest_supported_machine_row"
    assert exercise["name"] == "Chest-Supported Machine Row"
    assert exercise["primary_exercise_id"] == "chest_supported_machine_row"
    assert exercise["movement_pattern"] == "horizontal_pull"
    assert exercise["repeat_failure_substitution"] is None


def test_adaptive_gold_generate_week_uses_repeat_failure_substitution_for_third_exercise() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-repeat-failure-pulldown@example.com", "password": TEST_CREDENTIAL, "name": "Gold Repeat Pulldown User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Repeat Pulldown User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["bodyweight", "machine"],
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
        user = session.query(User).filter(User.email == "gold-repeat-failure-pulldown@example.com").first()
        assert user is not None
        session.add(
            ExerciseState(
                user_id=user.id,
                exercise_id="cross_body_lat_pull_around",
                current_working_weight=20.0,
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

    exercise = next(
        item
        for item in plan["sessions"][0]["exercises"]
        if item.get("primary_exercise_id") == "cross_body_lat_pull_around"
    )
    assert exercise["id"] == "half_kneeling_1_arm_lat_pulldown"
    assert exercise["name"] == "Half Kneeling 1 Arm Lat Pulldown"
    assert exercise["primary_exercise_id"] == "cross_body_lat_pull_around"
    assert exercise["movement_pattern"] == "vertical_pull"
    assert exercise["repeat_failure_substitution"]["recommended_name"] == "Half Kneeling 1 Arm Lat Pulldown"
    assert exercise["repeat_failure_substitution"]["failed_exposure_count"] == 3


def test_adaptive_gold_generate_week_uses_repeat_failure_substitution_for_fourth_exercise() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-repeat-failure-squat@example.com", "password": TEST_CREDENTIAL, "name": "Gold Repeat Squat User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Repeat Squat User",
            "age": 30,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["machine", "dumbbell", "barbell", "bench"],
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
        user = session.query(User).filter(User.email == "gold-repeat-failure-squat@example.com").first()
        assert user is not None
        session.add(
            ExerciseState(
            user_id=user.id,
                    exercise_id="hack_squat",
                    current_working_weight=20.0,
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
    _assert_generated_full_body_runtime(plan)

    exercise = next(
        item
        for item in plan["sessions"][0]["exercises"]
        if item.get("primary_exercise_id") == "hack_squat"
    )
    assert exercise["id"] == "hack_squat"
    assert exercise["name"] == "Hack Squat"
    assert exercise["primary_exercise_id"] == "hack_squat"
    assert exercise["movement_pattern"] == "squat"
    assert exercise["repeat_failure_substitution"] is None


def test_adaptive_gold_generate_week_uses_canonical_readiness_state_for_sfr_recovery_deload() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-sfr@example.com", "password": TEST_CREDENTIAL, "name": "Gold SFR User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold SFR User",
            "age": 33,
            "weight": 85,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "dumbbell"],
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
            "adherence_score": 3,
            "sleep_quality": 1,
            "stress_level": 5,
            "pain_flags": ["shoulder_irritation"],
            "notes": "gold path recovery is poor",
        },
    )
    assert weekly_checkin.status_code == 200

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    assert plan["program_template_id"] == "full_body_v1"
    assert plan["mesocycle"]["is_deload_week"] is True
    assert plan["mesocycle"]["deload_reason"] == "early_sfr_recovery"
    assert plan["deload"]["active"] is True
    assert plan["decision_trace"]["canonical_inputs"]["stimulus_fatigue_response_source"] == (
        "coaching_state.stimulus_fatigue_response"
    )
    assert plan["decision_trace"]["policy_basis"]["week_generation"]["stimulus_fatigue_response_source"] == (
        "coaching_state.stimulus_fatigue_response"
    )
    assert plan["decision_trace"]["outcome"]["stimulus_fatigue_response_source"] == (
        "coaching_state.stimulus_fatigue_response"
    )
    assert plan["generation_runtime_trace"]["outcome"]["stimulus_fatigue_response"]["deload_pressure"] == "high"
    assert plan["generation_runtime_trace"]["outcome"]["stimulus_fatigue_response"]["substitution_pressure"] == "high"


def test_adaptive_gold_generate_week_uses_saved_weekly_review_adjustments() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "gold-adaptive-review@example.com", "password": TEST_CREDENTIAL, "name": "Gold Review User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Gold Review User",
            "age": 31,
            "weight": 82,
            "gender": "male",
            "split_preference": "full_body",
            "selected_program_id": "adaptive_full_body_gold_v0_1",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bench", "dumbbell"],
            "days_available": 3,
            "nutrition_phase": "maintenance",
            "calories": 2500,
            "protein": 170,
            "fat": 70,
            "carbs": 260,
        },
    )
    assert profile.status_code == 200

    monday = date.today() - timedelta(days=date.today().weekday())
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == "gold-adaptive-review@example.com").first()
        assert user is not None
        session.add(
            WeeklyReviewCycle(
                user_id=user.id,
                reviewed_on=date.today(),
                week_start=monday,
                previous_week_start=monday - timedelta(days=7),
                body_weight=81.5,
                calories=2450,
                protein=175,
                fat=68,
                carbs=250,
                adherence_score=3,
                notes="gold adaptive review",
                faults={"exercise_faults": []},
                adjustments={
                    "global": {"set_delta": -1, "weight_scale": 0.95},
                    "weak_point_exercises": [],
                    "exercise_overrides": {},
                    "decision_trace": {
                        "interpreter": "interpret_weekly_review_decision",
                        "outcome": {"global_set_delta": -1, "global_weight_scale": 0.95},
                    },
                },
                summary={"planned_sets_total": 0, "completed_sets_total": 0},
            )
        )
        session.commit()

    generated = client.post("/plan/generate-week", headers=headers, json={})
    assert generated.status_code == 200
    payload = generated.json()

    assert payload["program_template_id"] == "full_body_v1"
    assert payload["adaptive_review"]["global_set_delta"] == -1
    assert float(payload["adaptive_review"]["global_weight_scale"]) == 0.95
    assert payload["adaptive_review"]["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"
    assert payload["sessions"][0]["exercises"][0]["sets"] >= 2


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
    assert plan["mesocycle"]["deload_reason"] != "none"
    assert plan["deload"]["active"] is True
    assert plan["generation_runtime_trace"]["outcome"]["severe_soreness_count"] == 2
    assert plan["generation_runtime_trace"]["outcome"]["latest_adherence_score"] == 2


def test_generate_week_uses_canonical_readiness_state_for_sfr_recovery_deload() -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "generation-sfr@example.com", "password": TEST_CREDENTIAL, "name": "Generation SFR User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Generation SFR User",
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
            "adherence_score": 3,
            "sleep_quality": 1,
            "stress_level": 5,
            "pain_flags": ["shoulder_irritation"],
            "notes": "recovery is poor",
        },
    )
    assert weekly_checkin.status_code == 200

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    assert plan["mesocycle"]["is_deload_week"] is True
    assert plan["mesocycle"]["deload_reason"] != "none"
    assert plan["deload"]["active"] is True
    assert plan["decision_trace"]["canonical_inputs"]["stimulus_fatigue_response_source"] == (
        "coaching_state.stimulus_fatigue_response"
    )
    assert plan["decision_trace"]["policy_basis"]["week_generation"]["stimulus_fatigue_response_source"] == (
        "coaching_state.stimulus_fatigue_response"
    )
    assert plan["decision_trace"]["outcome"]["stimulus_fatigue_response_source"] == (
        "coaching_state.stimulus_fatigue_response"
    )
    assert plan["generation_runtime_trace"]["outcome"]["stimulus_fatigue_response"]["deload_pressure"] == "high"
    assert plan["generation_runtime_trace"]["outcome"]["stimulus_fatigue_response"]["substitution_pressure"] == "high"


def test_generate_week_response_falls_back_to_generation_runtime_sfr_source_when_mesocycle_trace_missing(
    monkeypatch,
) -> None:
    _reset_db()
    client = TestClient(app)

    register = client.post(
        "/auth/register",
        json={"email": "generation-sfr-fallback@example.com", "password": TEST_CREDENTIAL, "name": "Fallback User"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post(
        "/profile",
        headers=headers,
        json={
            "name": "Fallback User",
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

    original_prepare_runtime = plan_router._prepare_plan_generation_runtime
    original_generate_week_plan = plan_router.generate_week_plan

    def _patched_prepare_runtime(*args, **kwargs):
        runtime = original_prepare_runtime(*args, **kwargs)
        generation_runtime = dict(runtime["generation_runtime"])
        generation_runtime_trace = dict(generation_runtime.get("decision_trace") or {})
        generation_runtime_outcome = dict(generation_runtime_trace.get("outcome") or {})
        generation_runtime_outcome["stimulus_fatigue_response_source"] = "derived_from_training_state_inputs"
        generation_runtime_trace["outcome"] = generation_runtime_outcome
        generation_runtime["decision_trace"] = generation_runtime_trace
        return {
            **runtime,
            "generation_runtime": generation_runtime,
        }

    def _patched_generate_week_plan(*args, **kwargs):
        plan = original_generate_week_plan(*args, **kwargs)
        mesocycle = dict(plan.get("mesocycle") or {})
        mesocycle.pop("decision_trace", None)
        plan["mesocycle"] = mesocycle
        return plan

    monkeypatch.setattr(plan_router, "_prepare_plan_generation_runtime", _patched_prepare_runtime)
    monkeypatch.setattr(plan_router, "generate_week_plan", _patched_generate_week_plan)

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()

    assert "decision_trace" not in plan["mesocycle"]
    assert plan["generation_runtime_trace"]["outcome"]["stimulus_fatigue_response_source"] == (
        "derived_from_training_state_inputs"
    )
    assert plan["decision_trace"]["canonical_inputs"]["stimulus_fatigue_response_source"] == (
        "derived_from_training_state_inputs"
    )
    assert plan["decision_trace"]["policy_basis"]["week_generation"]["stimulus_fatigue_response_source"] == (
        "derived_from_training_state_inputs"
    )
    assert plan["decision_trace"]["execution_steps"][1]["result"]["stimulus_fatigue_response_source"] == (
        "derived_from_training_state_inputs"
    )
    assert plan["decision_trace"]["outcome"]["stimulus_fatigue_response_source"] == (
        "derived_from_training_state_inputs"
    )


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
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "phase2-week5@example.com").first()
        assert user is not None
        _seed_prior_generated_weeks(
            user_id=user.id,
            weeks=4,
            program_template_id="pure_bodybuilding_phase_2_full_body",
        )

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()
    assert plan["generation_runtime_trace"]["outcome"]["prior_generated_weeks"] == 4
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
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "phase2-week6@example.com").first()
        assert user is not None
        _seed_prior_generated_weeks(
            user_id=user.id,
            weeks=5,
            program_template_id="pure_bodybuilding_phase_2_full_body",
        )

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()
    assert plan["generation_runtime_trace"]["outcome"]["prior_generated_weeks"] == 5
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
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "phase2-week10@example.com").first()
        assert user is not None
        # Leave one historical week gap to emulate interruption and ensure resumed counting still works.
        _seed_prior_generated_weeks(
            user_id=user.id,
            weeks=10,
            program_template_id="pure_bodybuilding_phase_2_full_body",
            gap_week_offsets={1},
        )

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()
    assert plan["generation_runtime_trace"]["outcome"]["prior_generated_weeks"] == 9
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
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "phase2-budget@example.com").first()
        assert user is not None
        _seed_prior_generated_weeks(
            user_id=user.id,
            weeks=5,
            program_template_id="pure_bodybuilding_phase_2_full_body",
        )

    generate = client.post("/plan/generate-week", headers=headers, json={})
    assert generate.status_code == 200
    plan = generate.json()
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
    assert "vertical_press" not in patterns
