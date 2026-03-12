import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_db import configure_test_database
from pydantic import ValidationError

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


def test_gold_onboarding_package_preserves_manual_backed_phase_intent() -> None:
    loaded = load_program_onboarding_package("pure_bodybuilding_phase_1_full_body")
    intent = loaded["program_intent"]

    assert "Arms & Weak Points day" in intent["phase_goal"]
    assert "rep ranges" in intent["progression_philosophy"]
    assert "first 2 weeks" in intent["fatigue_management"]
    assert any(item.startswith("Weak Point Exercise 2 only when recovered") for item in intent["flexible_elements"])
    assert "Weak-point chest and hamstrings coverage." not in intent["preserve_when_frequency_reduced"]
    assert "User-selected weak-point stimulus." in intent["preserve_when_frequency_reduced"]


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


def _gold_onboarding_payload() -> dict:
    package_path = _repo_root() / "programs" / "gold" / "pure_bodybuilding_phase_1_full_body.onboarding.json"
    return json.loads(package_path.read_text(encoding="utf-8"))


def test_onboarding_package_rejects_mismatched_program_ids() -> None:
    payload = _gold_onboarding_payload()
    payload["program_intent"]["program_id"] = "wrong_program_id"

    with pytest.raises(ValidationError, match="program_id must match program_intent.program_id"):
        ProgramOnboardingPackage.model_validate(payload)


def test_onboarding_package_rejects_unknown_week_template_in_sequence() -> None:
    payload = _gold_onboarding_payload()
    payload["blueprint"]["week_sequence"][0] = "unknown_week_template"

    with pytest.raises(ValidationError, match="week_sequence references unknown week_template_id"):
        ProgramOnboardingPackage.model_validate(payload)


def test_onboarding_package_rejects_duplicate_slot_order_index_per_day() -> None:
    payload = _gold_onboarding_payload()
    mutated = deepcopy(payload)

    first_day_slots = mutated["blueprint"]["week_templates"][0]["days"][0]["slots"]
    assert len(first_day_slots) >= 2
    first_day_slots[1]["order_index"] = first_day_slots[0]["order_index"]

    with pytest.raises(ValidationError, match="slots must have unique order_index values per day"):
        ProgramOnboardingPackage.model_validate(mutated)
