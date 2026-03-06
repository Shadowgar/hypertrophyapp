import json
from pathlib import Path

from test_db import configure_test_database

configure_test_database("test_program_onboarding_contract")

from app.adaptive_schema import ProgramOnboardingPackage, UserOverlayConstraints
from app.program_loader import load_program_onboarding_package, list_program_onboarding_packages


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_gold_onboarding_package_validates_against_schema() -> None:
    package_path = _repo_root() / "programs" / "gold" / "pure_bodybuilding_phase_1_full_body.onboarding.json"
    payload = json.loads(package_path.read_text(encoding="utf-8"))

    package = ProgramOnboardingPackage.model_validate(payload)

    assert package.program_id == "pure_bodybuilding_phase_1_full_body"
    assert package.blueprint.default_training_days == 5
    assert package.blueprint.total_weeks == 10
    assert len(package.blueprint.week_sequence) == 10
    assert package.exercise_library


def test_loader_lists_and_loads_onboarding_packages() -> None:
    packages = list_program_onboarding_packages()
    assert any(item["program_id"] == "pure_bodybuilding_phase_1_full_body" for item in packages)

    loaded = load_program_onboarding_package("pure_bodybuilding_phase_1_full_body")
    assert loaded["program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert loaded["blueprint"]["default_training_days"] == 5


def test_user_overlay_constraints_accept_two_to_five_days() -> None:
    for days in (2, 3, 4, 5):
        overlay = UserOverlayConstraints.model_validate(
            {
                "available_training_days": days,
                "temporary_duration_weeks": 2,
                "weak_areas": [
                    {"muscle_group": "chest", "priority": 5, "desired_extra_slots_per_week": 1},
                    {"muscle_group": "hamstrings", "priority": 4, "desired_extra_slots_per_week": 1},
                ],
                "equipment_limits": ["dumbbell", "bench"],
                "recovery_state": "normal",
                "current_week_index": 3,
            }
        )
        assert overlay.available_training_days == days
