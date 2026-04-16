from app.schemas import ProfileUpsert


def test_profile_upsert_accepts_equipment_profile() -> None:
    payload = ProfileUpsert(
        name="Test",
        age=30,
        weight=80,
        gender="male",
        split_preference="full_body",
        training_location="home",
        equipment_profile=["dumbbell", "bodyweight"],
        weak_areas=["chest", "hamstrings"],
        days_available=3,
        nutrition_phase="maintenance",
        calories=2500,
        protein=180,
        fat=70,
        carbs=260,
    )

    assert payload.training_location == "home"
    assert payload.equipment_profile == ["dumbbell", "bodyweight"]
    assert payload.weak_areas == ["chest", "hamstrings"]


def test_profile_upsert_rejects_invalid_days_available() -> None:
    raised = False
    try:
        ProfileUpsert(
            name="Test",
            age=30,
            weight=80,
            gender="male",
            split_preference="full_body",
            training_location="home",
            equipment_profile=["dumbbell"],
            weak_areas=["back"],
            days_available=1,
            nutrition_phase="maintenance",
            calories=2500,
            protein=180,
            fat=70,
            carbs=260,
        )
    except Exception:
        raised = True

    assert raised is True


def test_profile_upsert_accepts_five_days_available() -> None:
    payload = ProfileUpsert(
        name="Test",
        age=30,
        weight=80,
        gender="male",
        split_preference="full_body",
        training_location="gym",
        equipment_profile=["dumbbell", "machine"],
        days_available=5,
        nutrition_phase="maintenance",
        calories=2500,
        protein=180,
        fat=70,
        carbs=260,
    )

    assert payload.days_available == 5


def test_profile_upsert_accepts_null_selected_program_id() -> None:
    payload = ProfileUpsert(
        name="Test",
        age=30,
        weight=80,
        gender="male",
        split_preference="full_body",
        selected_program_id=None,
        training_location="gym",
        equipment_profile=["dumbbell", "machine"],
        weak_areas=[],
        days_available=4,
        nutrition_phase="maintenance",
        calories=2500,
        protein=180,
        fat=70,
        carbs=260,
    )

    assert payload.selected_program_id is None


def test_profile_upsert_accepts_onboarding_answers_payload() -> None:
    payload = ProfileUpsert(
        name="Test",
        age=30,
        weight=80,
        gender="male",
        split_preference="full_body",
        selected_program_id="full_body_v1",
        training_location="gym",
        equipment_profile=["dumbbell", "machine"],
        weak_areas=["chest"],
        onboarding_answers={
            "primary_goal": "build_muscle",
            "experience_level": "intermediate",
            "preferred_workout_duration_minutes": 45,
        },
        days_available=4,
        nutrition_phase="maintenance",
        calories=2500,
        protein=180,
        fat=70,
        carbs=260,
    )

    assert payload.onboarding_answers["primary_goal"] == "build_muscle"


def test_profile_upsert_accepts_coaching_constraint_fields() -> None:
    payload = ProfileUpsert(
        name="Test",
        age=30,
        weight=80,
        gender="male",
        split_preference="full_body",
        selected_program_id="full_body_v1",
        training_location="gym",
        equipment_profile=["dumbbell", "machine"],
        weak_areas=["chest"],
        onboarding_answers={},
        days_available=4,
        nutrition_phase="maintenance",
        calories=2500,
        protein=180,
        fat=70,
        carbs=260,
        session_time_budget_minutes=75,
        movement_restrictions=["deep_knee_flexion", "overhead_pressing"],
        near_failure_tolerance="moderate",
    )

    assert payload.session_time_budget_minutes == 75
    assert payload.movement_restrictions == ["deep_knee_flexion", "overhead_pressing"]
    assert payload.near_failure_tolerance == "moderate"


def test_profile_upsert_accepts_choose_for_me_diagnostic_contract() -> None:
    payload = ProfileUpsert(
        name="Test",
        age=30,
        weight=80,
        gender="male",
        split_preference="upper_lower",
        selected_program_id=None,
        program_selection_mode="auto",
        choose_for_me_family="upper_lower",
        choose_for_me_diagnostics={
            "movement_screen": {"movement_restrictions": ["deep_knee_flexion"]},
            "recovery_profile": {"days_available": 4, "preferred_workout_duration_minutes": 60},
        },
        training_location="gym",
        equipment_profile=["dumbbell", "machine"],
        weak_areas=["chest"],
        onboarding_answers={},
        days_available=4,
        nutrition_phase="maintenance",
        calories=2500,
        protein=180,
        fat=70,
        carbs=260,
    )
    assert payload.choose_for_me_family == "upper_lower"
    assert payload.choose_for_me_diagnostics["recovery_profile"]["days_available"] == 4
