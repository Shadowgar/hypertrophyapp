import json
from pathlib import Path
import sys
from typing import Any, cast
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importers.reference_corpus_ingest import build_reference_catalog


def _write_minimal_xlsx(path: Path) -> None:
    workbook_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">
  <sheets>
    <sheet name=\"Sheet1\" sheetId=\"1\" r:id=\"rId1\"/>
  </sheets>
</workbook>
"""
    rels_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/>
</Relationships>
"""
    shared_strings_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<sst xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" count=\"2\" uniqueCount=\"2\">
  <si><t>Exercise</t></si>
  <si><t>Bench Press</t></si>
</sst>
"""
    sheet_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">
  <sheetData>
    <row r=\"1\"><c r=\"A1\" t=\"s\"><v>0</v></c><c r=\"B1\"><v>3</v></c></row>
    <row r=\"2\"><c r=\"A2\" t=\"s\"><v>1</v></c><c r=\"B2\"><v>8</v></c></row>
  </sheetData>
</worksheet>
"""

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        archive.writestr("xl/sharedStrings.xml", shared_strings_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def _write_minimal_epub(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("OEBPS/ch1.xhtml", "<html><body><h1>Hypertrophy</h1><p>Progressive overload</p></body></html>")


def test_reference_ingestion_emits_catalog_and_provenance(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    guides_dir = tmp_path / "docs" / "guides"
    reference_dir.mkdir(parents=True)

    _write_minimal_xlsx(reference_dir / "Program Sheet.xlsx")
    _write_minimal_epub(reference_dir / "Guide.epub")

    result = build_reference_catalog(reference_dir=reference_dir, guides_dir=guides_dir)

    payload = cast(dict[str, Any], result)
    asset_catalog = cast(dict[str, Any], payload["asset_catalog"])
    provenance = cast(dict[str, Any], payload["provenance_index"])

    assert asset_catalog["asset_count"] == 2
    assert provenance["asset_count"] == 2
    assert len(asset_catalog["assets"]) == 2
    assert (guides_dir / "asset_catalog.json").exists()
    assert (guides_dir / "provenance_index.json").exists()

    generated_dir = guides_dir / "generated"
    assert generated_dir.exists()
    generated_docs = sorted(generated_dir.glob("*.md"))
    assert len(generated_docs) == 2


def test_reference_ingestion_is_deterministic(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    guides_dir = tmp_path / "docs" / "guides"
    reference_dir.mkdir(parents=True)

    _write_minimal_xlsx(reference_dir / "A.xlsx")
    _write_minimal_epub(reference_dir / "B.epub")

    first = cast(dict[str, Any], build_reference_catalog(reference_dir=reference_dir, guides_dir=guides_dir))
    second = cast(dict[str, Any], build_reference_catalog(reference_dir=reference_dir, guides_dir=guides_dir))

    assert first["asset_catalog"]["aggregate_signature"] == second["asset_catalog"]["aggregate_signature"]
    assert first["asset_catalog"] == second["asset_catalog"]
    assert first["provenance_index"] == second["provenance_index"]

    asset_catalog_file = json.loads((guides_dir / "asset_catalog.json").read_text(encoding="utf-8"))
    provenance_file = json.loads((guides_dir / "provenance_index.json").read_text(encoding="utf-8"))

    assert asset_catalog_file == second["asset_catalog"]
    assert provenance_file == second["provenance_index"]
