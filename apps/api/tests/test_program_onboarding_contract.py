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
    assert "Session exercise ordering inside authored day intent." not in intent["flexible_elements"]
    assert intent["preserve_when_frequency_reduced"] == []


def test_gold_onboarding_package_preserves_phase1_workbook_sections_and_authored_slot_columns() -> None:
    payload = _gold_onboarding_payload()
    blueprint = payload["blueprint"]

    first_slot = blueprint["week_templates"][0]["days"][0]["slots"][0]
    first_catalog_entry = next(
        entry for entry in payload["exercise_catalog"] if entry["exercise_id"] == first_slot["exercise_id"]
    )
    week_5 = blueprint["week_templates"][4]
    week_6 = blueprint["week_templates"][5]
    week_7 = blueprint["week_templates"][6]
    week_8 = blueprint["week_templates"][7]
    week_9 = blueprint["week_templates"][8]
    week_10 = blueprint["week_templates"][9]

    for key in (
        "exercise",
        "last_set_intensity_technique",
        "warm_up_sets",
        "working_sets",
        "reps",
        "early_set_rpe",
        "last_set_rpe",
        "rest",
        "tracking_set_1",
        "tracking_set_2",
        "tracking_set_3",
        "tracking_set_4",
        "substitution_option_1",
        "substitution_option_2",
        "notes",
        "video_url",
    ):
        assert key in first_slot

    assert first_slot["exercise"] == "Cross-Body Lat Pull-Around"
    assert first_slot["last_set_intensity_technique"] == "Long-length Partials (on all reps of the last set)"
    assert first_slot["warm_up_sets"] == "1.0"
    assert first_slot["working_sets"] == "3.0"
    assert first_slot["reps"] == "10-12"
    assert first_slot["early_set_rpe"] == "~7-8"
    assert first_slot["last_set_rpe"] == "~8-9"
    assert first_slot["rest"] == "~2-3 min"
    assert first_slot["tracking_set_1"] is None
    assert first_slot["tracking_set_2"] is None
    assert first_slot["tracking_set_3"] is None
    assert first_slot["tracking_set_4"] is None
    assert first_slot["substitution_option_1"] == "Half-Kneeling 1-Arm Lat Pulldown"
    assert first_slot["substitution_option_2"] == "Neutral-Grip Pullup"
    assert first_slot["video_url"] == "https://youtu.be/8W67lZ5mwTU?si=Xri6ms5QPmM-PZc8"
    assert first_slot["demo_url"] == first_slot["video_url"]
    assert first_slot["notes"].startswith("Try to keep the cable and your wrist aligned in a straight line")
    assert first_catalog_entry["default_video_url"] == first_slot["video_url"]

    assert "exercise_catalog" in payload
    assert "important_program_notes" in payload
    assert "warm_up_protocol" in payload
    assert "weak_points_table" in payload
    assert payload["important_program_notes"][0].startswith("Perform a full general warm-up")
    assert payload["warm_up_protocol"]["general_warm_up"][0] == {
        "label": "5-10 minutes",
        "instruction": "Light cardio on machine on your choice of machine (treadmill, stairmaster, elliptical, bike, etc.)",
    }
    assert payload["weak_points_table"][0]["weak_point"] == "Shoulders"
    assert "important_program_notes" in blueprint
    assert "warm_up_protocol" in blueprint
    assert "weak_points_table" in blueprint
    assert blueprint["important_program_notes"][0].startswith("Perform a full general warm-up")
    assert blueprint["warm_up_protocol"]["general_warm_up"][0] == {
        "label": "5-10 minutes",
        "instruction": "Light cardio on machine on your choice of machine (treadmill, stairmaster, elliptical, bike, etc.)",
    }
    assert blueprint["weak_points_table"][0]["weak_point"] == "Shoulders"
    assert blueprint["week_templates"][0]["block_label"] == "BLOCK 1: 5-WEEK BUILD PHASE"
    assert blueprint["week_templates"][0]["week_label"] == "Week 1"
    assert blueprint["week_templates"][0]["special_banners"] == ["Mandatory Rest Day", "Mandatory Rest Day"]
    week_2 = blueprint["week_templates"][1]
    assert week_2["block_label"] == "BLOCK 1: 5-WEEK BUILD PHASE"
    assert week_2["week_label"] == "Week 2"
    assert week_2["special_banners"] == ["Mandatory Rest Day", "Mandatory Rest Day"]
    week_2_fb2_slot5 = week_2["days"][1]["slots"][4]
    assert week_2_fb2_slot5["exercise"] == "Cuffed Behind-The-Back Lateral Raise"
    assert week_2_fb2_slot5["last_set_intensity_technique"] == "Myo-reps"
    assert week_2_fb2_slot5["substitution_option_1"] == "Cross-Body Cable Y-Raise"
    assert week_2_fb2_slot5["substitution_option_2"] == "DB Lateral Raise"
    assert week_2_fb2_slot5["video_url"] is not None
    week_3 = blueprint["week_templates"][2]
    assert week_3["block_label"] == "BLOCK 1: 5-WEEK BUILD PHASE"
    assert week_3["week_label"] == "Week 3"
    assert week_3["special_banners"] == ["Mandatory Rest Day", "Mandatory Rest Day"]
    week_3_fb1_slot6 = week_3["days"][0]["slots"][5]
    assert week_3_fb1_slot6["exercise"] == "Cable Crunch"
    assert week_3_fb1_slot6["last_set_intensity_technique"] == "Myo-reps"
    assert week_3_fb1_slot6["early_set_rpe"] == "~9-10"
    assert week_3_fb1_slot6["last_set_rpe"] == "10.0"
    assert week_3_fb1_slot6["substitution_option_1"] == "Machine Crunch"
    assert week_3_fb1_slot6["substitution_option_2"] == "Plate-Weighted Crunch"
    assert week_3_fb1_slot6["video_url"] is not None
    week_4 = blueprint["week_templates"][3]
    assert week_4["block_label"] == "BLOCK 1: 5-WEEK BUILD PHASE"
    assert week_4["week_label"] == "Week 4"
    assert week_4["special_banners"] == ["Mandatory Rest Day", "Mandatory Rest Day"]
    week_4_fb3_slot1 = week_4["days"][2]["slots"][0]
    assert week_4_fb3_slot1["exercise"] == "Superset A1: Assisted Pull-Up"
    assert week_4_fb3_slot1["last_set_intensity_technique"] == "Long-length Partials (on all reps of the last set)"
    assert week_4_fb3_slot1["working_sets"] == "4.0"
    assert week_4_fb3_slot1["last_set_rpe"] == "10"
    assert week_4_fb3_slot1["substitution_option_1"] == "Lat Pulldown"
    assert week_4_fb3_slot1["substitution_option_2"] == "Machine Pulldown"
    assert week_4_fb3_slot1["video_url"] is not None
    assert week_5["special_banners"] == [
        "SEMI-DELOAD WEEK: AVOID FAILURE AND TRAIN LIGHTER THIS WEEK TO PROMOTE RECOVERY AND TO PREPARE FOR THE NEXT 5 WEEKS!",
        "Mandatory Rest Day",
        "Mandatory Rest Day",
    ]
    week_5_fb1_slot1 = week_5["days"][0]["slots"][0]
    assert week_5_fb1_slot1["exercise"] == "Cross-Body Lat Pull-Around"
    assert week_5_fb1_slot1["early_set_rpe"] == "~7"
    assert week_5_fb1_slot1["last_set_rpe"] == "~8"
    assert week_5_fb1_slot1["video_url"] is not None
    week_5_fb2_slot2 = week_5["days"][1]["slots"][1]
    assert week_5_fb2_slot2["exercise"] == "Paused Barbell RDL"
    assert week_5_fb2_slot2["working_sets"] == "2.0"
    assert week_5_fb2_slot2["early_set_rpe"] == "~5"
    assert week_5_fb2_slot2["last_set_rpe"] == "~5-6"
    assert week_5_fb2_slot2["video_url"] is not None
    assert week_6["block_label"] == "BLOCK 2: 5-WEEK NOVELTY PHASE"
    assert week_6["week_label"] == "Week 6"
    assert week_6["special_banners"] == ["Mandatory Rest Day", "Mandatory Rest Day"]
    week_6_fb1_slot1 = week_6["days"][0]["slots"][0]
    assert week_6_fb1_slot1["exercise"] == "Lat-Focused Cable Row"
    assert week_6_fb1_slot1["last_set_intensity_technique"] == "Long-length Partials (on all reps of the last set)"
    assert week_6_fb1_slot1["early_set_rpe"] == "~9"
    assert week_6_fb1_slot1["last_set_rpe"] == "10"
    assert week_6_fb1_slot1["substitution_option_1"] == "Half-Kneeling 1-Arm Lat Pulldown"
    assert week_6_fb1_slot1["substitution_option_2"] == "Elbows-In 1-Arm DB Row"
    assert week_6_fb1_slot1["video_url"] is not None
    week_6_fb2_slot7 = week_6["days"][1]["slots"][6]
    assert week_6_fb2_slot7["exercise"] == "A2: Single-arm Overhead Cable Triceps Extension"
    assert week_6_fb2_slot7["last_set_intensity_technique"] == "Dropset"
    assert week_6_fb2_slot7["early_set_rpe"] == "~9-10"
    assert week_6_fb2_slot7["last_set_rpe"] == "10.0"
    assert week_6_fb2_slot7["substitution_option_1"] == "DB Skull Crusher"
    assert week_6_fb2_slot7["substitution_option_2"] == "Floor Skull Crusher"
    assert week_6_fb2_slot7["video_url"] is not None
    assert week_7["block_label"] == "BLOCK 2: 5-WEEK NOVELTY PHASE"
    assert week_7["week_label"] == "Week 7"
    assert week_7["special_banners"] == ["Mandatory Rest Day", "Mandatory Rest Day"]
    week_7_fb1_slot1 = week_7["days"][0]["slots"][0]
    assert week_7_fb1_slot1["exercise"] == "Lat-Focused Cable Row"
    assert week_7_fb1_slot1["last_set_intensity_technique"] == "Long-length Partials (on all reps of the last set)"
    assert week_7_fb1_slot1["early_set_rpe"] == "~9"
    assert week_7_fb1_slot1["last_set_rpe"] == "10"
    assert week_7_fb1_slot1["substitution_option_1"] == "Half-Kneeling 1-Arm Lat Pulldown"
    assert week_7_fb1_slot1["substitution_option_2"] == "Elbows-In 1-Arm DB Row"
    assert week_7_fb1_slot1["video_url"] is not None
    week_7_fb2_slot2 = week_7["days"][1]["slots"][1]
    assert week_7_fb2_slot2["exercise"] == "Chest-Supported T-Bar Row + Kelso Shrug"
    assert week_7_fb2_slot2["working_sets"] == "3.0"
    assert week_7_fb2_slot2["reps"] == "8-10 + 4-6"
    assert week_7_fb2_slot2["substitution_option_1"] == "Machine Chest-Supported Row + Kelso Shrug"
    assert week_7_fb2_slot2["substitution_option_2"] == "Incline Chest-Supported DB Row + Kelso Shrug"
    assert week_7_fb2_slot2["video_url"] is not None
    assert week_8["block_label"] == "BLOCK 2: 5-WEEK NOVELTY PHASE"
    assert week_8["week_label"] == "Week 8"
    assert week_8["special_banners"] == ["Mandatory Rest Day", "Mandatory Rest Day"]
    week_8_fb1_slot1 = week_8["days"][0]["slots"][0]
    assert week_8_fb1_slot1["exercise"] == "Lat-Focused Cable Row"
    assert week_8_fb1_slot1["last_set_intensity_technique"] == "Long-length Partials (on all reps of the last set)"
    assert week_8_fb1_slot1["early_set_rpe"] == "~9"
    assert week_8_fb1_slot1["last_set_rpe"] == "10"
    assert week_8_fb1_slot1["substitution_option_1"] == "Half-Kneeling 1-Arm Lat Pulldown"
    assert week_8_fb1_slot1["substitution_option_2"] == "Elbows-In 1-Arm DB Row"
    assert week_8_fb1_slot1["video_url"] is not None
    week_8_arms_slot4 = week_8["days"][4]["slots"][3]
    assert week_8_arms_slot4["exercise"] == "Slow-Eccentric Bayesian Curl"
    assert week_8_arms_slot4["last_set_intensity_technique"] == "Long-length Partials (on all reps of the last set)"
    assert week_8_arms_slot4["working_sets"] == "3.0"
    assert week_8_arms_slot4["reps"] == "10-12"
    assert week_8_arms_slot4["substitution_option_1"] == "Slow-Eccentric DB Incline Curl"
    assert week_8_arms_slot4["substitution_option_2"] == "Slow-Eccentric DB Scott Curl"
    assert week_8_arms_slot4["video_url"] is not None
    assert week_9["block_label"] == "BLOCK 2: 5-WEEK NOVELTY PHASE"
    assert week_9["week_label"] == "Week 9"
    assert week_9["special_banners"] == ["Mandatory Rest Day", "Mandatory Rest Day"]
    week_9_fb1_slot1 = week_9["days"][0]["slots"][0]
    assert week_9_fb1_slot1["exercise"] == "Lat-Focused Cable Row"
    assert week_9_fb1_slot1["last_set_intensity_technique"] == "Long-length Partials (on all reps of the last set)"
    assert week_9_fb1_slot1["tracking_set_1"] == "150.0"
    assert week_9_fb1_slot1["tracking_set_2"] == "150.0"
    assert week_9_fb1_slot1["tracking_set_3"] == "135.0"
    assert week_9_fb1_slot1["tracking_set_4"] is None
    assert week_9_fb1_slot1["video_url"] is not None
    week_9_arms_slot4 = week_9["days"][4]["slots"][3]
    assert week_9_arms_slot4["exercise"] == "Slow-Eccentric Bayesian Curl"
    assert week_9_arms_slot4["last_set_intensity_technique"] == "Long-length Partials"
    assert week_9_arms_slot4["working_sets"] == "3.0"
    assert week_9_arms_slot4["reps"] == "10-12"
    assert week_9_arms_slot4["substitution_option_1"] == "Slow-Eccentric DB Incline Curl"
    assert week_9_arms_slot4["substitution_option_2"] == "Slow-Eccentric DB Scott Curl"
    assert week_9_arms_slot4["video_url"] is not None
    assert week_10["block_label"] == "BLOCK 2: 5-WEEK NOVELTY PHASE"
    assert week_10["week_label"] == "Week 10"
    assert week_10["special_banners"] == ["Mandatory Rest Day", "Mandatory Rest Day"]
    week_10_fb1_slot1 = week_10["days"][0]["slots"][0]
    assert week_10_fb1_slot1["exercise"] == "Lat-Focused Cable Row"
    assert week_10_fb1_slot1["last_set_intensity_technique"] == "Long-length Partials (on all reps of the last set)"
    assert week_10_fb1_slot1["early_set_rpe"] == "~9"
    assert week_10_fb1_slot1["last_set_rpe"] == "10"
    assert week_10_fb1_slot1["tracking_set_1"] is None
    assert week_10_fb1_slot1["tracking_set_2"] is None
    assert week_10_fb1_slot1["tracking_set_3"] is None
    assert week_10_fb1_slot1["tracking_set_4"] is None
    assert week_10_fb1_slot1["substitution_option_1"] == "Half-Kneeling 1-Arm Lat Pulldown"
    assert week_10_fb1_slot1["substitution_option_2"] == "Elbows-In 1-Arm DB Row"
    assert week_10_fb1_slot1["video_url"] is not None
    week_10_arms_slot4 = week_10["days"][4]["slots"][3]
    assert week_10_arms_slot4["exercise"] == "Slow-Eccentric Bayesian Curl"
    assert week_10_arms_slot4["last_set_intensity_technique"] == "Long-length Partials (on all reps of the last set)"
    assert week_10_arms_slot4["working_sets"] == "3.0"
    assert week_10_arms_slot4["reps"] == "10-12"
    assert week_10_arms_slot4["substitution_option_1"] == "Slow-Eccentric DB Incline Curl"
    assert week_10_arms_slot4["substitution_option_2"] == "Slow-Eccentric DB Scott Curl"
    assert week_10_arms_slot4["video_url"] is not None


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
