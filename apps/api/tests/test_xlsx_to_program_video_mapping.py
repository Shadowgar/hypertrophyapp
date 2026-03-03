import json
from pathlib import Path
import sys
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importers.xlsx_to_program import import_workbook


def _write_xlsx_with_video_column(path: Path, *, video_link: str, extra_link: str | None = None) -> None:
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
    shared = [
        "Session",
        "Exercise",
        "Working Sets",
        "Reps",
        "Video Link",
        "Push A",
        "DB Bench Press",
        video_link,
        extra_link or "",
    ]
    shared_strings_xml = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        f"<sst xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" count=\"{len(shared)}\" uniqueCount=\"{len(shared)}\">",
    ]
    shared_strings_xml.extend(f"  <si><t>{value}</t></si>" for value in shared)
    shared_strings_xml.append("</sst>")

    sheet_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">
  <sheetData>
    <row r=\"1\"><c r=\"A1\" t=\"s\"><v>0</v></c><c r=\"B1\" t=\"s\"><v>1</v></c><c r=\"C1\" t=\"s\"><v>2</v></c><c r=\"D1\" t=\"s\"><v>3</v></c><c r=\"E1\" t=\"s\"><v>4</v></c></row>
    <row r=\"2\"><c r=\"A2\" t=\"s\"><v>5</v></c><c r=\"B2\" t=\"s\"><v>6</v></c><c r=\"C2\" t=\"inlineStr\"><is><t>3</t></is></c><c r=\"D2\" t=\"inlineStr\"><is><t>8-10</t></is></c><c r=\"E2\" t=\"s\"><v>7</v></c></row>
  </sheetData>
</worksheet>
"""

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        archive.writestr("xl/sharedStrings.xml", "\n".join(shared_strings_xml))
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def test_import_workbook_maps_youtube_link_to_video_metadata(tmp_path: Path) -> None:
    workbook = tmp_path / "Edited PPL 5x.xlsx"
    output = tmp_path / "imported.json"
    _write_xlsx_with_video_column(workbook, video_link="https://www.youtube.com/watch?v=abc123")

    destination = import_workbook(workbook, output_file=output)
    data = json.loads(destination.read_text(encoding="utf-8"))

    exercise = data["sessions"][0]["exercises"][0]
    assert exercise["video"] == {"youtube_url": "https://www.youtube.com/watch?v=abc123"}


def test_import_workbook_ignores_non_youtube_links_for_video(tmp_path: Path) -> None:
    workbook = tmp_path / "Edited PPL 5x.xlsx"
    output = tmp_path / "imported.json"
    _write_xlsx_with_video_column(workbook, video_link="https://example.com/program-notes")

    destination = import_workbook(workbook, output_file=output)
    data = json.loads(destination.read_text(encoding="utf-8"))

    exercise = data["sessions"][0]["exercises"][0]
    assert exercise["video"] is None
