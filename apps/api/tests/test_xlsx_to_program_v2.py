import json
from pathlib import Path
import sys
import zipfile

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.adaptive_schema import AdaptiveGoldProgramTemplate
from importers.xlsx_to_program_v2 import build_program_template


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


def test_build_program_template_emits_valid_adaptive_gold_template_and_report(tmp_path: Path) -> None:
    workbook = tmp_path / "Pure Bodybuilding Phase 1 - Full Body Sheet.xlsx"
    output = tmp_path / "adaptive_full_body_test.json"
    report = tmp_path / "adaptive_full_body_test.import_report.json"
    rows = [
        ["Session", "Exercise", "Working Sets", "Reps", "Video Link", "Notes"],
        ["BLOCK 1: 5-WEEK BUILD PHASE", "Week 1", "1", "1", "", ""],
        ["Full Body #1", "DB Bench Press", "3", "8-10", "https://youtu.be/bench", "Control the eccentric. Drive hard."],
        ["Full Body #1", "Chest Supported Row", "3", "10-12", "", "Pause at the top."],
        ["Full Body #2", "Leg Press", "4", "10-12", "", ""],
        ["Full Body #2", "Mandatory Rest Day", "3", "8-12", "", ""],
        ["Full Body #3", "Lateral Raise", "3", "12-15", "", "Soft elbows."],
    ]
    _write_xlsx_with_rows(workbook, rows)

    destination, report_destination = build_program_template(
        input_file=workbook,
        program_id="adaptive_full_body_test",
        total_weeks=4,
        output_file=output,
        sheet_name=None,
        program_name="Adaptive Full Body Test",
        report_output=report,
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))
    template = AdaptiveGoldProgramTemplate.model_validate(payload)
    report_payload = json.loads(report_destination.read_text(encoding="utf-8"))

    assert template.program_id == "adaptive_full_body_test"
    assert template.program_name == "Adaptive Full Body Test"
    assert len(template.phases) == 1
    assert len(template.phases[0].weeks) == 4
    assert len(template.phases[0].weeks[0].days) == 3
    assert template.phases[0].weeks[0].days[0].slots[0].exercise_id == "db_bench_press"
    assert template.phases[0].weeks[0].days[0].slots[0].video_url == "https://youtu.be/bench"
    assert template.phases[0].weeks[0].days[0].slots[0].work_sets[0].rep_target.min == 8
    assert template.phases[0].weeks[0].days[0].slots[0].work_sets[0].rep_target.max == 10
    assert report_payload["export_type"] == "adaptive_gold_program_template"
    assert report_payload["diagnostic_status"] == "warnings"
    assert report_payload["diagnostic_count"] >= 2
    codes = {item["code"] for item in report_payload["items"]}
    assert "structural_session_label_skipped" in codes
    assert "structural_exercise_label_skipped" in codes


def test_build_program_template_preserves_authored_phases_weeks_and_set_semantics(tmp_path: Path) -> None:
    workbook = tmp_path / "Powerbuilding 3.0.xlsx"
    output = tmp_path / "powerbuilding_structured.json"
    rows = [
        ["Session", "Exercise", "Warm-up Sets", "Working Sets", "Reps", "Load", "RPE", "Rest", "Notes"],
        ["BLOCK 1: BUILD", "Week 1", "", "", "", "", "", "", ""],
        ["Full Body #1", "Back Squat (Top Single)", "4", "1", "1", "85-87.5%", "6-8", "3-5 min", "Top set. Focus on technique."],
        ["Full Body #1", "Back Squat", "0", "3", "5", "75-77.5%", "7", "3-5 min", "Competition style squat."],
        ["BLOCK 2: INTENSIFICATION", "Week 2", "", "", "", "", "", "", ""],
        ["Full Body #1", "Back Squat (Back off)", "0", "2", "5", "72.5-75%", "8", "3-5 min", "Drop the load after the top set."],
    ]
    _write_xlsx_with_rows(workbook, rows)

    destination, _report_destination = build_program_template(
        input_file=workbook,
        program_id="powerbuilding_structured",
        total_weeks=8,
        output_file=output,
        sheet_name=None,
        program_name="Powerbuilding Structured",
        report_output=tmp_path / "powerbuilding_structured.import_report.json",
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))
    template = AdaptiveGoldProgramTemplate.model_validate(payload)

    assert len(template.phases) == 2
    assert template.phases[0].phase_name == "BLOCK 1: BUILD"
    assert template.phases[1].phase_name == "BLOCK 2: INTENSIFICATION"
    assert len(template.phases[0].weeks) == 1
    assert len(template.phases[1].weeks) == 1

    top_slot = template.phases[0].weeks[0].days[0].slots[0]
    backoff_slot = template.phases[1].weeks[0].days[0].slots[0]

    assert len(top_slot.warmup_prescription) == 4
    assert top_slot.work_sets[0].set_type == "top"
    assert top_slot.work_sets[0].load_target == "85-87.5%"
    assert top_slot.work_sets[0].rpe_target == pytest.approx(7.0)
    assert backoff_slot.work_sets[0].set_type == "backoff"
    assert backoff_slot.work_sets[0].load_target == "72.5-75%"
    assert backoff_slot.work_sets[0].rpe_target == pytest.approx(8.0)


REFERENCE_PHASE1_WORKBOOK = REPO_ROOT / "reference" / "Pure Bodybuilding Phase 1 - Full Body Sheet.xlsx"


@pytest.mark.skipif(not REFERENCE_PHASE1_WORKBOOK.exists(), reason="reference workbook not available")
def test_build_program_template_parses_phase1_reference_workbook_structure(tmp_path: Path) -> None:
    output = tmp_path / "phase1_reference_program.json"
    report = tmp_path / "phase1_reference_program.import_report.json"

    destination, report_destination = build_program_template(
        input_file=REFERENCE_PHASE1_WORKBOOK,
        program_id="phase1_reference_program",
        total_weeks=10,
        output_file=output,
        sheet_name=None,
        program_name="Phase 1 Reference Program",
        report_output=report,
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))
    template = AdaptiveGoldProgramTemplate.model_validate(payload)
    report_payload = json.loads(report_destination.read_text(encoding="utf-8"))

    assert len(template.phases) >= 2
    assert sum(len(phase.weeks) for phase in template.phases) >= 10
    first_week_days = template.phases[0].weeks[0].days
    assert [day.day_name for day in first_week_days] == [
        "Full Body #1",
        "Full Body #2",
        "Full Body #3",
        "Full Body #4",
        "Arms & Weak Points",
    ]
    assert [day.day_role for day in first_week_days] == [
        "full_body_1",
        "full_body_2",
        "full_body_3",
        "full_body_4",
        "weak_point_arms",
    ]
    first_day_exercises = [slot.exercise_id for slot in first_week_days[0].slots]
    assert first_day_exercises[:3] == [
        "cross_body_lat_pull_around",
        "low_incline_smith_machine_press",
        "machine_hip_adduction",
    ]
    assert first_week_days[0].slots[1].exercise_id == "low_incline_smith_machine_press"
    assert first_week_days[0].slots[1].slot_role == "primary_compound"
    assert report_payload["day_count"] == 5
    assert report_payload["diagnostic_count"] < 40
