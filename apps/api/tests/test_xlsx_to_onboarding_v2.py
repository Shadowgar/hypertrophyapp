import json
from pathlib import Path
import sys
import zipfile


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
