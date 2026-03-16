import json
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

from test_db import configure_test_database

configure_test_database("test_program_loader")

from app.config import settings
from app.program_loader import load_program_rule_set, load_program_template, resolve_runtime_template_id

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core_engine.rules_runtime import resolve_adaptive_rule_runtime, resolve_equipment_substitution
from importers.xlsx_to_onboarding_v2 import build_onboarding_package
from importers.xlsx_to_program_v2 import build_program_template


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

    assert template["id"] == "pure_bodybuilding_phase_1_full_body"
    assert template["split"] == "full_body"
    assert template["days_supported"] == [2, 3, 4, 5]
    assert len(sessions) == 5
    assert len(authored_weeks) == 10
    assert [week["week_index"] for week in authored_weeks] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert [week.get("week_role") for week in authored_weeks] == [
        "adaptation",
        "adaptation",
        "accumulation",
        "accumulation",
        "accumulation",
        "intensification",
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
        "cross_body_lat_pull_around",
        "low_incline_smith_machine_press",
        "machine_hip_adduction",
        "leg_press",
        "lying_paused_rope_face_pull",
        "cable_crunch",
    ]
    assert [exercise["slot_role"] for exercise in day_1] == [
        "accessory",
        "primary_compound",
        "accessory",
        "primary_compound",
        "accessory",
        "accessory",
    ]
    assert day_1[0]["name"] == "Cross-Body Lat Pull-Around"
    assert day_1[0]["rep_range"] == [10, 12]
    assert day_1[0]["movement_pattern"] == "vertical_pull"
    assert day_1[0]["substitution_candidates"] == ["Half Kneeling 1 Arm Lat Pulldown", "Neutral-Grip Pullup"]
    assert day_1[1]["name"] == "Low Incline Smith Machine Press"
    assert day_1[1]["rep_range"] == [8, 10]
    assert day_1[1]["movement_pattern"] == "horizontal_press"
    assert day_1[1]["substitution_candidates"] == ["Low Incline Machine Press", "Low Incline DB Press"]
    assert day_1[2]["name"] == "Machine Hip Adduction"
    assert day_1[2]["movement_pattern"] == "hip_adduction"
    assert day_1[3]["name"] == "Leg Press"
    assert day_1[3]["substitution_candidates"] == ["Belt Squat", "High Bar Back Squat"]

    assert [exercise["id"] for exercise in day_2] == [
        "seated_db_shoulder_press",
        "paused_barbell_rdl",
        "chest_supported_machine_row",
        "hammer_preacher_curl",
        "cuffed_behind_the_back_lateral_raise",
        "overhead_cable_triceps_extension_bar",
    ]
    assert [exercise["slot_role"] for exercise in day_2] == [
        "primary_compound",
        "secondary_compound",
        "primary_compound",
        "isolation",
        "isolation",
        "isolation",
    ]
    assert day_2[0]["movement_pattern"] == "vertical_press"
    assert day_2[0]["substitution_candidates"] == ["Seated Barbell Shoulder Press", "Standing Db Arnold Press"]
    assert day_2[1]["movement_pattern"] == "hinge"
    assert day_2[1]["substitution_candidates"] == ["Paused Db Rdl", "Glute Ham Raise"]
    assert day_2[5]["movement_pattern"] == "vertical_press"

    assert [exercise["id"] for exercise in day_3] == [
        "assisted_pull_up",
        "paused_assisted_dip",
        "seated_leg_curl",
        "leg_extension",
        "cable_paused_shrug_in",
        "roman_chair_leg_raise",
    ]
    assert day_3[0]["movement_pattern"] == "vertical_pull"
    assert day_3[1]["movement_pattern"] == "horizontal_press"
    assert day_3[5]["movement_pattern"] == "core"

    assert [exercise["id"] for exercise in day_4] == [
        "lying_leg_curl",
        "hack_squat",
        "bent_over_cable_pec_flye",
        "neutral_grip_lat_pulldown",
        "leg_press_calf_press",
        "cable_reverse_flye_mechanical_dropset",
    ]
    assert day_4[1]["movement_pattern"] == "squat"
    assert day_4[4]["movement_pattern"] == "plantar_flexion"
    assert day_4[5]["movement_pattern"] == "accessory"

    assert [exercise["id"] for exercise in day_5] == [
        "weak_point_exercise_1",
        "weak_point_exercise_2_optional",
        "bayesian_cable_curl",
        "triceps_pressdown_bar",
        "bottom_2_3_constant_tension_preacher_curl",
        "cable_triceps_kickback",
        "standing_calf_raise",
    ]
    assert [exercise["slot_role"] for exercise in day_5] == [
        "weak_point",
        "weak_point",
        "weak_point",
        "weak_point",
        "weak_point",
        "weak_point",
        "weak_point",
    ]
    assert day_5[0]["name"] == "Weak Point Exercise 1"
    assert day_5[1]["name"] == "Weak Point Exercise 2 (optional)"
    assert day_5[2]["name"] == "Bayesian Cable Curl"
    assert day_5[3]["name"] == "Triceps Pressdown (Bar)"

    assert week_two_day_a[0]["id"] == "cross_body_lat_pull_around"
    assert week_two_day_a[0]["rep_range"] == [10, 12]
    assert week_two_day_a[1]["id"] == "low_incline_smith_machine_press"
    assert week_two_day_a[1]["rep_range"] == [8, 10]
    assert week_two_day_a[1]["sets"] == 3


REFERENCE_PHASE1_WORKBOOK = REPO_ROOT / "reference" / "Pure Bodybuilding Phase 1 - Full Body Sheet.xlsx"


@pytest.mark.skipif(not REFERENCE_PHASE1_WORKBOOK.exists(), reason="reference workbook not available")
def test_load_program_template_flattens_all_authored_phase_weeks_for_source_backed_adaptive_gold(tmp_path: Path) -> None:
    gold_dir = tmp_path / "gold"
    gold_dir.mkdir(parents=True, exist_ok=True)

    build_onboarding_package(
        input_file=REFERENCE_PHASE1_WORKBOOK,
        source_pdf="reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf",
        program_id="pure_bodybuilding_phase_1_full_body",
        total_weeks=10,
        output_file=gold_dir / "pure_bodybuilding_phase_1_full_body.onboarding.json",
        sheet_name=None,
    )
    build_program_template(
        input_file=REFERENCE_PHASE1_WORKBOOK,
        program_id="adaptive_full_body_gold_v0_1",
        total_weeks=10,
        output_file=gold_dir / "adaptive_full_body_gold_v0_1.json",
        sheet_name=None,
        program_name="Adaptive Full Body Gold v0.1",
        report_output=gold_dir / "adaptive_full_body_gold_v0_1.import_report.json",
    )

    previous_programs_dir = settings.programs_dir
    settings.programs_dir = str(tmp_path)
    try:
        template = load_program_template("adaptive_full_body_gold_v0_1")
    finally:
        settings.programs_dir = previous_programs_dir

    assert len(template["sessions"]) == 5
    assert len(template["authored_weeks"]) == 10
    assert [week["week_index"] for week in template["authored_weeks"]] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert [exercise["id"] for exercise in template["sessions"][0]["exercises"][:3]] == [
        "cross_body_lat_pull_around",
        "low_incline_smith_machine_press",
        "machine_hip_adduction",
    ]


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


def test_load_program_rule_set_carries_traceable_phase1_manual_grounding() -> None:
    rule_set = load_program_rule_set("pure_bodybuilding_phase_1_full_body")

    source_sections = {section["field"]: section for section in rule_set["source_sections"]}

    assert set(source_sections) == {
        "starting_load_rules.default_rir_target",
        "starting_load_rules.method",
        "progression_rules.success_condition",
        "fatigue_rules.high_fatigue_trigger.conditions[0]",
        "substitution_rules.equipment_mismatch",
    }
    assert source_sections["starting_load_rules.default_rir_target"]["source_pdf"] == (
        "reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf"
    )
    assert "first 2 weeks" in source_sections["starting_load_rules.default_rir_target"]["excerpt"]
    assert "leaving 1-3 reps in the tank" in source_sections["starting_load_rules.default_rir_target"]["excerpt"]
    assert "progress through the rep ranges given" in source_sections["progression_rules.success_condition"]["excerpt"]
    assert "Substitution Option 1" in source_sections["substitution_rules.equipment_mismatch"]["excerpt"]
    assert "intro phase lasts 2 weeks" in rule_set["fatigue_rules"]["high_fatigue_trigger"]["conditions"][0]
    assert "fatigue_rules.high_fatigue_trigger.conditions[1]" not in source_sections
    assert "deload_rules.scheduled_every_n_weeks" not in source_sections
    assert "substitution_rules.repeat_failure_trigger" not in source_sections


def test_phase1_manual_grounding_survives_runtime_without_fallback_substitution_strategy() -> None:
    rule_set = load_program_rule_set("pure_bodybuilding_phase_1_full_body")

    adaptive_runtime = resolve_adaptive_rule_runtime(rule_set)
    substitution_runtime = resolve_equipment_substitution(
        exercise_id="machine_hip_adduction",
        exercise_name="Machine Hip Adduction",
        exercise_equipment_tags=["machine"],
        substitution_candidates=["Cable Hip Adduction", "Copenhagen Hip Adduction"],
        equipment_set={"cable"},
        rule_set=rule_set,
    )

    assert adaptive_runtime["intro_weeks"] == 2
    assert rule_set["substitution_rules"]["equipment_mismatch"] == "use_authored_substitution_columns"
    assert substitution_runtime["auto_substituted"] is True
    assert substitution_runtime["selected_name"] == "Cable Hip Adduction"
    assert substitution_runtime["decision_trace"]["inputs"]["equipment_mismatch_strategy"] == (
        "use_authored_substitution_columns"
    )


def test_load_program_rule_set_normalizes_adaptive_gold_alias_to_phase1_canonical_rules() -> None:
    rule_set = load_program_rule_set("adaptive_full_body_gold_v0_1")

    assert rule_set["rule_set_id"] == "pure_bodybuilding_phase_1_full_body_rules"
    assert "pure_bodybuilding_phase_1_full_body" in rule_set["program_scope"]
    assert rule_set["deload_rules"]["scheduled_every_n_weeks"] == 6
    assert rule_set["substitution_rules"]["equipment_mismatch"] == "use_authored_substitution_columns"
    assert rule_set["starting_load_rules"]["method"] == "rep_range_rir_start"


def test_load_program_template_normalizes_phase1_aliases_to_canonical_identity() -> None:
    from_legacy_v1 = load_program_template("full_body_v1")
    from_legacy_gold = load_program_template("adaptive_full_body_gold_v0_1")
    from_canonical = load_program_template("pure_bodybuilding_phase_1_full_body")

    assert from_legacy_v1["id"] == "pure_bodybuilding_phase_1_full_body"
    assert from_legacy_gold["id"] == "pure_bodybuilding_phase_1_full_body"
    assert from_canonical["id"] == "pure_bodybuilding_phase_1_full_body"


def test_phase1_runtime_template_source_resolution_prefers_canonical_source_id() -> None:
    assert resolve_runtime_template_id("pure_bodybuilding_phase_1_full_body") == "pure_bodybuilding_phase_1_full_body"
    assert resolve_runtime_template_id("full_body_v1") == "pure_bodybuilding_phase_1_full_body"
    assert resolve_runtime_template_id("adaptive_full_body_gold_v0_1") == "pure_bodybuilding_phase_1_full_body"


def test_phase1_canonical_runtime_template_artifact_exists() -> None:
    runtime_template_path = REPO_ROOT / "programs" / "gold" / "pure_bodybuilding_phase_1_full_body.json"
    payload = json.loads(runtime_template_path.read_text(encoding="utf-8"))

    assert runtime_template_path.exists()
    assert payload["program_id"] == "pure_bodybuilding_phase_1_full_body"
    assert isinstance(payload.get("phases"), list)
    assert len(payload["phases"]) >= 1


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
