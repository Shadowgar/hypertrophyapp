import json
from pathlib import Path
import sys
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importers.xlsx_to_program import import_workbook


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


def test_import_workbook_sanitizes_structural_rows(tmp_path: Path) -> None:
    workbook = tmp_path / "Hypertrophy Phase 1 Sheet.xlsx"
    output = tmp_path / "imported.json"
    rows = [
        ["Session", "Exercise", "Working Sets", "Reps", "Video Link"],
        ["BLOCK 1: 5-WEEK BUILD PHASE", "Week 1", "1", "1", ""],
        ["Full Body #1", "Full Body #1", "1", "1", ""],
        ["Full Body #1", "DB Bench Press", "3", "8-10", ""],
        ["Full Body #1", "Mandatory Rest Day", "3", "8-12", ""],
        ["Full Body #2", "Seated Cable Row", "4", "10-12", ""],
        ["Full Body #2", "Face Pull", "", "", ""],
    ]
    _write_xlsx_with_rows(workbook, rows)

    destination = import_workbook(workbook, output_file=output)
    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["source_workbook"] == str(workbook)
    assert [session["name"] for session in payload["sessions"]] == ["Full Body #1", "Full Body #2"]
    assert [exercise["name"] for exercise in payload["sessions"][0]["exercises"]] == ["DB Bench Press"]
    assert [exercise["name"] for exercise in payload["sessions"][1]["exercises"]] == ["Seated Cable Row"]

    diagnostics = payload["import_diagnostics"]
    assert diagnostics["status"] == "warnings"
    assert diagnostics["diagnostic_count"] >= 4
    codes = {item["code"] for item in diagnostics["items"]}
    assert "structural_session_label_skipped" in codes
    assert "structural_exercise_label_skipped" in codes
    assert "missing_working_sets" in codes


def test_import_workbook_emits_defaulted_session_name_diagnostic(tmp_path: Path) -> None:
    workbook = tmp_path / "Upper Lower Example.xlsx"
    output = tmp_path / "imported.json"
    rows = [
        ["Session", "Exercise", "Working Sets", "Reps", "Video Link"],
        ["", "DB Bench Press", "3", "8-10", ""],
    ]
    _write_xlsx_with_rows(workbook, rows)

    destination = import_workbook(workbook, output_file=output)
    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert [session["name"] for session in payload["sessions"]] == ["Main"]
    diagnostics = payload["import_diagnostics"]
    assert diagnostics["status"] == "warnings"
    assert any(item["code"] == "defaulted_session_name" for item in diagnostics["items"])
