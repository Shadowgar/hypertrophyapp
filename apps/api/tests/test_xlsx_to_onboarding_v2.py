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
