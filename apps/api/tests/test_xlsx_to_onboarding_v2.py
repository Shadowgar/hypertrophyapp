import json
from pathlib import Path
import sys
import zipfile

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.adaptive_schema import ProgramOnboardingPackage
from importers.xlsx_to_onboarding_v2 import build_onboarding_package


def _worksheet_row_xml(row_index: int, values: list[str]) -> str:
    cells: list[str] = []
    for col_offset, value in enumerate(values):
        column = chr(ord("A") + col_offset)
        ref = f"{column}{row_index}"
        escaped = (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escaped}</t></is></c>')
    return f'<row r="{row_index}">{"".join(cells)}</row>'


def _write_xlsx_with_rows(path: Path, rows: list[list[str]]) -> None:
    workbook_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">
  <sheets>
    <sheet name=\"Main\" sheetId=\"1\" r:id=\"rId1\"/>
  </sheets>
</workbook>
"""
    rels_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/>
</Relationships>
"""

    row_xml = "".join(_worksheet_row_xml(index, row) for index, row in enumerate(rows, start=1))
    sheet_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">"
        "<sheetData>"
        f"{row_xml}"
        "</sheetData>"
        "</worksheet>"
    )

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def test_build_onboarding_package_uses_current_parser_result_shape(tmp_path: Path) -> None:
    workbook = tmp_path / "Pure Bodybuilding Phase 1 - Full Body Sheet.xlsx"
    output = tmp_path / "pure_bodybuilding_full_body.onboarding.json"
    rows = [
        ["Session", "Exercise", "Working Sets", "Reps", "Video Link", "Notes"],
        ["Full Body #1", "DB Bench Press", "3", "8-10", "https://youtu.be/bench", "Control the eccentric."],
        ["Full Body #2", "Chest Supported Row", "3", "10-12", "", "Pause at the top."],
        ["Full Body #3", "Leg Press", "4", "10-12", "", "Drive through full foot."],
    ]
    _write_xlsx_with_rows(workbook, rows)

    destination = build_onboarding_package(
        input_file=workbook,
        source_pdf="reference/Pure Bodybuilding Phase 1 Full Body.pdf",
        program_id="pure_bodybuilding_full_body",
        total_weeks=8,
        output_file=output,
        sheet_name=None,
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))
    package = ProgramOnboardingPackage.model_validate(payload)

    assert package.program_id == "pure_bodybuilding_full_body"
    assert package.blueprint.total_weeks == 8
    assert len(package.blueprint.week_templates[0].days) == 3
    assert package.exercise_library


def test_build_onboarding_package_preserves_tracking_sets_when_present(tmp_path: Path) -> None:
    workbook = tmp_path / "Pure Bodybuilding Phase 1 - Full Body Sheet.xlsx"
    output = tmp_path / "pure_bodybuilding_full_body.onboarding.json"
    rows = [
        [
            "Session",
            "Exercise",
            "Last-Set Intensity Technique",
            "Warm-up Sets",
            "Working Sets",
            "Reps",
            "Tracking Load and Reps",
            "",
            "",
            "",
            "Early Set RPE",
            "Last Set RPE",
            "Rest",
            "Substitution Option 1",
            "Substitution Option 2",
            "Notes",
        ],
        [
            "Full Body #1",
            "DB Bench Press",
            "Drop Set",
            "2",
            "3",
            "8-10",
            "100x10",
            "105x9",
            "110x8",
            "115x7",
            "~7-8",
            "~8-9",
            "~2-3 min",
            "Machine Chest Press",
            "Barbell Bench Press",
            "Control the eccentric.",
        ],
        [
            "Full Body #2",
            "Chest Supported Row",
            "N/A",
            "1",
            "3",
            "10-12",
            "",
            "",
            "",
            "",
            "~7-8",
            "~8-9",
            "~2-3 min",
            "Seated Cable Row",
            "Machine Row",
            "Pause at peak contraction.",
        ],
        [
            "Full Body #3",
            "Leg Press",
            "N/A",
            "2",
            "3",
            "8-10",
            "",
            "",
            "",
            "",
            "~7-8",
            "~8-9",
            "~3-4 min",
            "Hack Squat",
            "Smith Squat",
            "Drive through full foot.",
        ],
    ]
    _write_xlsx_with_rows(workbook, rows)

    destination = build_onboarding_package(
        input_file=workbook,
        source_pdf="reference/Pure Bodybuilding Phase 1 Full Body.pdf",
        program_id="pure_bodybuilding_full_body",
        total_weeks=8,
        output_file=output,
        sheet_name=None,
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))
    package = ProgramOnboardingPackage.model_validate(payload)
    slot = package.blueprint.week_templates[0].days[0].slots[0]

    assert slot.tracking_set_1 == "100x10"
    assert slot.tracking_set_2 == "105x9"
    assert slot.tracking_set_3 == "110x8"
    assert slot.tracking_set_4 == "115x7"


REFERENCE_PHASE1_WORKBOOK = REPO_ROOT / "reference" / "Pure Bodybuilding Phase 1 - Full Body Sheet.xlsx"


@pytest.mark.skipif(not REFERENCE_PHASE1_WORKBOOK.exists(), reason="reference workbook not available")
def test_build_onboarding_package_parses_phase1_reference_workbook_structure(tmp_path: Path) -> None:
    output = tmp_path / "phase1_reference.onboarding.json"

    destination = build_onboarding_package(
        input_file=REFERENCE_PHASE1_WORKBOOK,
        source_pdf="reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf",
        program_id="phase1_reference",
        total_weeks=10,
        output_file=output,
        sheet_name=None,
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))
    package = ProgramOnboardingPackage.model_validate(payload)

    assert len(package.blueprint.week_templates) >= 10
    assert len(package.blueprint.week_templates[0].days) == 5
    assert [day.day_name for day in package.blueprint.week_templates[0].days] == [
        "Full Body #1",
        "Full Body #2",
        "Full Body #3",
        "Full Body #4",
        "Arms & Weak Points",
    ]
    assert [day.day_role for day in package.blueprint.week_templates[0].days] == [
        "full_body_1",
        "full_body_2",
        "full_body_3",
        "full_body_4",
        "weak_point_arms",
    ]
    first_day_slots = package.blueprint.week_templates[0].days[0].slots
    assert first_day_slots[1].exercise_id == "low_incline_smith_machine_press"
    assert first_day_slots[1].slot_role == "primary_compound"
    exercise_ids = {exercise.exercise_id for exercise in package.exercise_library}
    assert "cross_body_lat_pull_around" in exercise_ids
    assert "low_incline_smith_machine_press" in exercise_ids
    assert "assisted_pull_up" in exercise_ids
    assert "bayesian_cable_curl" in exercise_ids


@pytest.mark.skipif(not REFERENCE_PHASE1_WORKBOOK.exists(), reason="reference workbook not available")
def test_build_onboarding_package_preserves_phase1_reference_exercise_metadata(tmp_path: Path) -> None:
    output = tmp_path / "phase1_reference.onboarding.json"

    destination = build_onboarding_package(
        input_file=REFERENCE_PHASE1_WORKBOOK,
        source_pdf="reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf",
        program_id="phase1_reference",
        total_weeks=10,
        output_file=output,
        sheet_name=None,
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))
    package = ProgramOnboardingPackage.model_validate(payload)
    library = {exercise.exercise_id: exercise for exercise in package.exercise_library}

    low_incline_press = library["low_incline_smith_machine_press"]
    leg_press = library["leg_press"]
    shoulder_press = library["seated_db_shoulder_press"]
    triceps_pressdown = library["triceps_pressdown_bar"]
    cable_curl = library["bayesian_cable_curl"]

    assert low_incline_press.movement_pattern == "horizontal_press"
    assert low_incline_press.primary_muscles == ["chest", "triceps", "front_delts"]
    assert "machine" in low_incline_press.equipment_tags

    assert leg_press.movement_pattern == "squat"
    assert leg_press.primary_muscles == ["quads", "glutes"]
    assert "machine" in leg_press.equipment_tags

    assert shoulder_press.movement_pattern == "vertical_press"
    assert shoulder_press.primary_muscles == ["front_delts", "triceps"]
    assert "dumbbell" in shoulder_press.equipment_tags

    assert triceps_pressdown.movement_pattern == "triceps_extension"
    assert triceps_pressdown.primary_muscles == ["triceps"]
    assert "cable" in triceps_pressdown.equipment_tags

    assert cable_curl.movement_pattern == "curl"
    assert cable_curl.primary_muscles == ["biceps"]
    assert "cable" in cable_curl.equipment_tags


@pytest.mark.skipif(not REFERENCE_PHASE1_WORKBOOK.exists(), reason="reference workbook not available")
def test_build_onboarding_package_preserves_phase1_reference_workout_table_columns_losslessly(tmp_path: Path) -> None:
    output = tmp_path / "phase1_reference.onboarding.json"

    destination = build_onboarding_package(
        input_file=REFERENCE_PHASE1_WORKBOOK,
        source_pdf="reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf",
        program_id="phase1_reference",
        total_weeks=10,
        output_file=output,
        sheet_name=None,
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))
    package = ProgramOnboardingPackage.model_validate(payload)

    week_1 = package.blueprint.week_templates[0]
    first_slot = week_1.days[0].slots[0]
    weak_point_slot = week_1.days[4].slots[0]

    assert first_slot.exercise == "Cross-Body Lat Pull-Around"
    assert first_slot.last_set_intensity_technique == "Long-length Partials (on all reps of the last set)"
    assert first_slot.warm_up_sets == "1.0"
    assert first_slot.working_sets == "3.0"
    assert first_slot.reps == "10-12"
    assert first_slot.early_set_rpe == "~7-8"
    assert first_slot.last_set_rpe == "~8-9"
    assert first_slot.rest == "~2-3 min"
    assert first_slot.tracking_set_1 is None
    assert first_slot.tracking_set_2 is None
    assert first_slot.tracking_set_3 is None
    assert first_slot.tracking_set_4 is None
    assert first_slot.substitution_option_1 == "Half-Kneeling 1-Arm Lat Pulldown"
    assert first_slot.substitution_option_2 == "Neutral-Grip Pullup"
    assert first_slot.notes == (
        "Try to keep the cable and your wrist aligned in a straight line throughout the pull. "
        "Feel a nice, deep lat stretch at the top."
    )
    assert first_slot.demo_url == "https://youtu.be/8W67lZ5mwTU?si=Xri6ms5QPmM-PZc8"
    assert first_slot.video_url == first_slot.demo_url

    assert weak_point_slot.exercise == "Weak Point Exercise 1"
    assert weak_point_slot.substitution_option_1 == "See The Weak Point Table for sub options"
    assert weak_point_slot.substitution_option_2 == "See The Weak Point Table for sub options"
    assert weak_point_slot.notes == (
        "Decide on your weak point using The Weak Point Table in your Hypertrophy Handbook. "
        "Perform ONE of the exercises listed under Exercise 1 for the sets and reps provided here."
    )


@pytest.mark.skipif(not REFERENCE_PHASE1_WORKBOOK.exists(), reason="reference workbook not available")
def test_build_onboarding_package_preserves_phase1_reference_sections_and_week_banners(tmp_path: Path) -> None:
    output = tmp_path / "phase1_reference.onboarding.json"

    destination = build_onboarding_package(
        input_file=REFERENCE_PHASE1_WORKBOOK,
        source_pdf="reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf",
        program_id="phase1_reference",
        total_weeks=10,
        output_file=output,
        sheet_name=None,
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))
    package = ProgramOnboardingPackage.model_validate(payload)

    assert package.important_program_notes[0] == (
        "Perform a full general warm-up and exercise-specific warm-up every workout as outlined below "
        "(should only take 5-10 mins max)"
    )
    assert package.warm_up_protocol is not None
    assert package.warm_up_protocol.general_warm_up[0].label == "5-10 minutes"
    assert package.weak_points_table[0].weak_point == "Shoulders"
    assert package.exercise_catalog[0].default_video_url is not None

    assert package.blueprint.important_program_notes[0] == (
        "Perform a full general warm-up and exercise-specific warm-up every workout as outlined below "
        "(should only take 5-10 mins max)"
    )
    assert package.blueprint.important_program_notes[-1].startswith(
        "All other aspects of the program, including how to understand the Last-Set Intensity Technique column"
    )

    warm_up_protocol = package.blueprint.warm_up_protocol
    assert warm_up_protocol is not None
    assert warm_up_protocol.general_warm_up_intro.startswith(
        "Perform the following general warm-up before every workout"
    )
    assert warm_up_protocol.general_warm_up[0].label == "5-10 minutes"
    assert warm_up_protocol.general_warm_up[0].instruction.startswith("Light cardio on machine")
    assert warm_up_protocol.exercise_specific_warm_up_intro.startswith(
        "Perform the following exercise-specific warm-up"
    )
    assert warm_up_protocol.exercise_specific_warm_up[1].label == "2 Warm-Up Sets Listed"
    assert warm_up_protocol.exercise_specific_warm_up[1].instruction.startswith(
        "Perform a mini warm-up pyramid"
    )

    first_weak_point = package.blueprint.weak_points_table[0]
    hamstrings = next(entry for entry in package.blueprint.weak_points_table if entry.weak_point == "Hamstrings")
    assert first_weak_point.weak_point == "Shoulders"
    assert first_weak_point.exercise_1_options == [
        "1. Cuffed Behind-The-Back Lateral Raise",
        "2. Machine Lateral Raise",
        "3. Dumbbell Lateral Raise",
    ]
    assert first_weak_point.exercise_2_options == [
        "1. Machine Shoulder Press",
        "2. Smith Machine Shoulder Press",
        "3. Standing DB Arnold Press",
    ]
    assert first_weak_point.guidance == [
        "Pick one of the options above. Do not do all of them in one day!",
    ]
    assert hamstrings.exercise_1_options == []
    assert hamstrings.exercise_2_options == []
    assert hamstrings.guidance == [
        "There is a lot of hamstrings volume in this program. If they are a weak point for you, simply focus on executing the exercises listed with your best effort and execution rather than adding more volume.",
    ]

    week_1 = package.blueprint.week_templates[0]
    week_2 = package.blueprint.week_templates[1]
    week_5 = package.blueprint.week_templates[4]
    week_6 = package.blueprint.week_templates[5]
    assert week_1.block_label == "BLOCK 1: 5-WEEK BUILD PHASE"
    assert week_1.week_label == "Week 1"
    assert week_1.special_banners == ["Mandatory Rest Day", "Mandatory Rest Day"]
    assert week_2.block_label == "BLOCK 1: 5-WEEK BUILD PHASE"
    assert week_2.week_label == "Week 2"
    assert week_2.special_banners == ["Mandatory Rest Day", "Mandatory Rest Day"]
    week_2_fb2_slot5 = week_2.days[1].slots[4]
    assert week_2_fb2_slot5.exercise == "Cuffed Behind-The-Back Lateral Raise"
    assert week_2_fb2_slot5.last_set_intensity_technique == "Myo-reps"
    assert week_2_fb2_slot5.substitution_option_1 == "Cross-Body Cable Y-Raise"
    assert week_2_fb2_slot5.substitution_option_2 == "DB Lateral Raise"
    assert week_2_fb2_slot5.video_url is not None
    assert week_5.week_label == "Week 5"
    assert week_5.special_banners == [
        "SEMI-DELOAD WEEK: AVOID FAILURE AND TRAIN LIGHTER THIS WEEK TO PROMOTE RECOVERY AND TO PREPARE FOR THE NEXT 5 WEEKS!",
        "Mandatory Rest Day",
        "Mandatory Rest Day",
    ]
    assert week_6.block_label == "BLOCK 2: 5-WEEK NOVELTY PHASE"
    assert week_6.week_label == "Week 6"
