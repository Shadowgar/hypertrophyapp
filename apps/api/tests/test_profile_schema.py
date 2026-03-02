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
        days_available=3,
        nutrition_phase="maintenance",
        calories=2500,
        protein=180,
        fat=70,
        carbs=260,
    )

    assert payload.training_location == "home"
    assert payload.equipment_profile == ["dumbbell", "bodyweight"]


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
