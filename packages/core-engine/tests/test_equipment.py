from core_engine import infer_equipment_tags_from_name, resolve_equipment_tags


def test_infer_equipment_tags_from_name() -> None:
    assert infer_equipment_tags_from_name("Low Incline DB Press") == ["dumbbell"]
    assert infer_equipment_tags_from_name("Cable Fly") == ["cable"]
    assert infer_equipment_tags_from_name("Bodyweight Pull-up") == ["bodyweight"]


def test_explicit_tags_override_inference() -> None:
    assert resolve_equipment_tags("Bench Press", explicit_tags=["machine", "machine"]) == [
        "machine"
    ]
    assert resolve_equipment_tags("DB Curl", explicit_tags=None) == ["dumbbell"]
