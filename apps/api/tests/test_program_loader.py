import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from test_db import configure_test_database

configure_test_database("test_program_loader")

from app.config import settings
from app.program_loader import load_program_rule_set, load_program_template


def test_load_program_template_validates_existing_template() -> None:
    template = load_program_template("ppl_v1")
    assert template["id"] == "ppl_v1"
    assert len(template["sessions"]) >= 1


def test_load_program_template_supports_adaptive_gold_runtime_template() -> None:
    template = load_program_template("adaptive_full_body_gold_v0_1")
    sessions = template["sessions"]
    authored_weeks = template["authored_weeks"]
    session_by_name = {session["name"]: session for session in sessions}
    day_1 = session_by_name["Full Body #1"]["exercises"]
    day_2 = session_by_name["Full Body #2"]["exercises"]
    day_3 = session_by_name["Full Body #3"]["exercises"]
    day_4 = session_by_name["Full Body #4"]["exercises"]
    day_5 = session_by_name["Arms & Weak Points"]["exercises"]
    week_two_day_a = authored_weeks[1]["sessions"][0]["exercises"]

    assert template["id"] == "adaptive_full_body_gold_v0_1"
    assert template["split"] == "full_body"
    assert template["days_supported"] == [2, 3, 4, 5]
    assert len(sessions) == 5
    assert len(authored_weeks) == 10
    assert [week["week_index"] for week in authored_weeks] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert [week.get("week_role") for week in authored_weeks] == [
        "accumulation",
        "accumulation",
        "accumulation",
        "accumulation",
        "accumulation",
        "deload",
        "intensification",
        "intensification",
        "intensification",
        "intensification",
    ]
    assert [session.get("day_role") for session in sessions] == [
        "full_body_1",
        "full_body_2",
        "full_body_3",
        "full_body_4",
        "weak_point_arms",
    ]

    assert [exercise["id"] for exercise in day_1] == [
        "lat_pulldown_wide",
        "bench_press_barbell",
        "hack_squat",
        "lateral_raise_cable",
        "cable_crunch",
    ]
    assert [exercise["slot_role"] for exercise in day_1] == [
        "primary_compound",
        "primary_compound",
        "secondary_compound",
        "isolation",
        "accessory",
    ]
    assert day_1[0]["name"] == "Wide Grip Lat Pulldown"
    assert day_1[0]["rep_range"] == [8, 10]
    assert day_1[0]["movement_pattern"] == "vertical_pull"
    assert day_1[0]["substitution_candidates"] == ["Neutral Grip Assisted Pull-Up"]
    assert day_1[1]["name"] == "Barbell Bench Press"
    assert day_1[1]["rep_range"] == [6, 8]
    assert day_1[1]["movement_pattern"] == "horizontal_press"
    assert day_1[1]["substitution_candidates"] == ["Incline Dumbbell Press"]
    assert day_1[2]["name"] == "Hack Squat"
    assert day_1[2]["substitution_candidates"] == ["Split Squat Db"]

    assert [exercise["id"] for exercise in day_2] == [
        "romanian_deadlift",
        "incline_dumbbell_press",
        "row_chest_supported",
        "leg_curl_seated",
    ]
    assert [exercise["slot_role"] for exercise in day_2] == [
        "primary_compound",
        "secondary_compound",
        "secondary_compound",
        "isolation",
    ]
    assert day_2[0]["movement_pattern"] == "hinge"
    assert day_2[0]["substitution_candidates"] == ["Leg Curl Seated"]

    assert [exercise["id"] for exercise in day_3] == [
        "pullup_assisted_neutral",
        "overhead_press_seated_db",
        "split_squat_db",
        "triceps_pushdown_rope",
    ]
    assert day_3[0]["movement_pattern"] == "vertical_pull"
    assert day_3[1]["movement_pattern"] == "vertical_press"

    assert [exercise["id"] for exercise in day_4] == [
        "hack_squat",
        "row_machine_chest_supported",
        "dumbbell_curl_incline",
        "calf_raise_seated",
    ]
    assert day_4[2]["movement_pattern"] == "elbow_flexion"
    assert day_4[3]["movement_pattern"] == "plantar_flexion"

    assert [exercise["id"] for exercise in day_5] == [
        "weak_chest_cable_fly",
        "weak_ham_leg_curl",
        "dumbbell_curl_incline",
        "triceps_pushdown_rope",
    ]
    assert [exercise["slot_role"] for exercise in day_5] == [
        "weak_point",
        "weak_point",
        "isolation",
        "isolation",
    ]
    assert day_5[0]["name"] == "Cable Fly (Weak-Point Chest)"
    assert day_5[1]["name"] == "Leg Curl (Weak-Point Hamstrings)"
    assert day_5[2]["name"] == "Incline Dumbbell Curl"
    assert day_5[3]["name"] == "Rope Triceps Pushdown"

    assert week_two_day_a[0]["id"] == "lat_pulldown_wide"
    assert week_two_day_a[0]["rep_range"] == [8, 11]
    assert week_two_day_a[1]["id"] == "bench_press_barbell"
    assert week_two_day_a[1]["rep_range"] == [6, 9]
    assert week_two_day_a[1]["sets"] == 3


def test_load_program_template_raises_on_invalid_schema(tmp_path: Path) -> None:
    broken = {
        "id": "broken_template",
        "version": "1.0.0",
        "split": "ppl",
        "days_supported": [3],
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "progression": {"mode": "double_progression", "increment_kg": 2.5},
    }

    template_path = tmp_path / "broken_template.json"
    template_path.write_text(json.dumps(broken), encoding="utf-8")

    previous_programs_dir = settings.programs_dir
    settings.programs_dir = str(tmp_path)
    try:
        with pytest.raises(ValidationError):
            load_program_template("broken_template")
    finally:
        settings.programs_dir = previous_programs_dir


def test_load_program_rule_set_validates_existing_rules() -> None:
    rule_set = load_program_rule_set("pure_bodybuilding_phase_1_full_body")

    assert rule_set["rule_set_id"] == "pure_bodybuilding_phase_1_full_body_rules"
    assert "pure_bodybuilding_phase_1_full_body" in rule_set["program_scope"]
    assert rule_set["progression_rules"]["on_success"]["percent"] == pytest.approx(2.5)


def test_load_program_rule_set_supports_adaptive_gold_runtime_program() -> None:
    rule_set = load_program_rule_set("adaptive_full_body_gold_v0_1")

    assert rule_set["rule_set_id"] == "adaptive_full_body_gold_v0_1_rules"
    assert "adaptive_full_body_gold_v0_1" in rule_set["program_scope"]
    assert rule_set["deload_rules"]["scheduled_every_n_weeks"] == 6


@pytest.mark.parametrize(
    ("program_id", "expected_program_scope"),
    [
        ("ppl_v1", "pure_bodybuilding_phase_2_ppl_sheet"),
        ("upper_lower_v1", "pure_bodybuilding_phase_2_upper_lower_sheet"),
        ("pure_bodybuilding_full_body", "pure_bodybuilding_phase_1_full_body"),
        ("pure_bodybuilding_phase_2_full_body_sheet_1", "pure_bodybuilding_phase_2_full_body_sheet"),
        ("powerbuilding_3_0", "powerbuilding_3_0"),
        ("the_bodybuilding_transformation_system_beginner", "the_bodybuilding_transformation_system_beginner"),
        ("the_bodybuilding_transformation_system_intermediate_advanced", "the_bodybuilding_transformation_system_intermediate_advanced"),
        ("the_ultimate_push_pull_legs_system_4x", "the_ultimate_push_pull_legs_system_4x"),
        ("the_ultimate_push_pull_legs_system_5x", "the_ultimate_push_pull_legs_system_5x"),
        ("the_ultimate_push_pull_legs_system_6x", "the_ultimate_push_pull_legs_system_6x"),
    ],
)
def test_load_program_rule_set_resolves_runtime_program_aliases(
    program_id: str,
    expected_program_scope: str,
) -> None:
    rule_set = load_program_rule_set(program_id)

    assert expected_program_scope in rule_set["program_scope"]
    assert rule_set["progression_rules"]["on_under_target"]["after_exposures"] == 2
    assert isinstance(rule_set["source_sections"], list)


@pytest.mark.parametrize(
    "program_id",
    [
        "powerbuilding_3_0",
        "the_bodybuilding_transformation_system_beginner",
        "the_ultimate_push_pull_legs_system_4x",
    ],
)
def test_load_program_rule_set_loads_newly_distilled_catalog_rules(program_id: str) -> None:
    rule_set = load_program_rule_set(program_id)

    assert rule_set["source_pdf"]
    assert rule_set["rule_set_id"].endswith("_rules")
