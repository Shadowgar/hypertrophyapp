import json
from pathlib import Path
import sys
from typing import Any, cast
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importers.reference_corpus_ingest import build_reference_catalog
from importers.reference_corpus_ingest import ExtractionResult


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


def _write_minimal_pdf(path: Path, payload: bytes | None = None) -> None:
    path.write_bytes(payload or b"%PDF-1.4 synthetic")


def test_reference_ingestion_emits_catalog_and_provenance(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    guides_dir = tmp_path / "docs" / "guides"
    reference_dir.mkdir(parents=True)

    _write_minimal_xlsx(reference_dir / "Program Sheet.xlsx")
    _write_minimal_pdf(reference_dir / "Program Sheet.pdf")
    _write_minimal_epub(reference_dir / "Guide.epub")

    result = build_reference_catalog(reference_dir=reference_dir, guides_dir=guides_dir)

    payload = cast(dict[str, Any], result)
    asset_catalog = cast(dict[str, Any], payload["asset_catalog"])
    provenance = cast(dict[str, Any], payload["provenance_index"])

    assert asset_catalog["asset_count"] == 3
    assert asset_catalog["source_asset_count"] == 3
    assert asset_catalog["workbook_pdf_pair_count"] == 1
    assert provenance["asset_count"] == 3
    assert len(asset_catalog["assets"]) == 3
    assert (guides_dir / "asset_catalog.json").exists()
    assert (guides_dir / "provenance_index.json").exists()

    generated_dir = guides_dir / "generated"
    assert generated_dir.exists()
    generated_docs = sorted(generated_dir.glob("*.md"))
    assert len(generated_docs) == 3


def test_reference_ingestion_is_deterministic(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    guides_dir = tmp_path / "docs" / "guides"
    reference_dir.mkdir(parents=True)

    _write_minimal_xlsx(reference_dir / "A.xlsx")
    _write_minimal_pdf(reference_dir / "A.pdf")
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


def test_reference_ingestion_has_no_orphan_assets_against_real_corpus(
    tmp_path: Path,
    monkeypatch,
) -> None:
    reference_dir = tmp_path / "reference"
    guides_dir = tmp_path / "docs" / "guides"
    reference_dir.mkdir(parents=True)

    _write_minimal_xlsx(reference_dir / "Program Sheet.xlsx")
    _write_minimal_epub(reference_dir / "Guide.epub")
    _write_minimal_pdf(reference_dir / "Program Sheet.pdf")
    (reference_dir / "ignore.txt").write_text("unsupported", encoding="utf-8")

    def _fast_extract(_path: Path, *, metadata_only: bool = False) -> ExtractionResult:
        return ExtractionResult(text="coverage-only", method="coverage_stub")

    monkeypatch.setattr("importers.reference_corpus_ingest.extract_asset_text", _fast_extract)

    result = cast(dict[str, Any], build_reference_catalog(reference_dir=reference_dir, guides_dir=guides_dir))
    asset_catalog = cast(dict[str, Any], result["asset_catalog"])
    provenance = cast(dict[str, Any], result["provenance_index"])

    supported_files = sorted(
        path.relative_to(reference_dir.parent).as_posix()
        for path in reference_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".pdf", ".epub", ".xlsx"}
    )

    catalog_assets = sorted(item["asset_path"] for item in asset_catalog["assets"])
    provenance_assets = sorted(item["asset"] for item in provenance["provenance"])

    assert asset_catalog["asset_count"] == len(supported_files)
    assert provenance["asset_count"] == len(supported_files)
    assert catalog_assets == supported_files
    assert provenance_assets == supported_files

    for item in asset_catalog["assets"]:
        derived_doc = Path(str(item["derived_doc"]))
        derived_path = derived_doc if derived_doc.is_absolute() else reference_dir.parent / derived_doc
        assert derived_path.exists()


def test_reference_ingestion_deduplicates_assets_by_checksum(tmp_path: Path, monkeypatch) -> None:
    reference_dir = tmp_path / "reference"
    guides_dir = tmp_path / "docs" / "guides"
    reference_dir.mkdir(parents=True)

    _write_minimal_xlsx(reference_dir / "The_Ultimate_Push_Pull_Legs_System_-_5x.xlsx")
    duplicate_payload = b"%PDF-1.4 duplicate"
    _write_minimal_pdf(reference_dir / "The_Ultimate_Push_Pull_Legs_System_5X.pdf", payload=duplicate_payload)
    _write_minimal_pdf(reference_dir / "Copy of The_Ultimate_Push_Pull_Legs_System_5X.pdf", payload=duplicate_payload)

    def _fast_extract(_path: Path, *, metadata_only: bool = False) -> ExtractionResult:
        return ExtractionResult(text="coverage-only", method="coverage_stub")

    monkeypatch.setattr("importers.reference_corpus_ingest.extract_asset_text", _fast_extract)

    result = cast(dict[str, Any], build_reference_catalog(reference_dir=reference_dir, guides_dir=guides_dir))
    asset_catalog = cast(dict[str, Any], result["asset_catalog"])

    assert asset_catalog["source_asset_count"] == 3
    assert asset_catalog["asset_count"] == 2
    assert asset_catalog["duplicate_asset_count"] == 1
    assert asset_catalog["workbook_pdf_pair_count"] == 1
    assert len(asset_catalog["duplicate_assets"]) == 1


def test_reference_ingestion_enforces_workbook_pdf_pairing(tmp_path: Path, monkeypatch) -> None:
    reference_dir = tmp_path / "reference"
    guides_dir = tmp_path / "docs" / "guides"
    reference_dir.mkdir(parents=True)

    _write_minimal_xlsx(reference_dir / "Unpaired Program.xlsx")
    _write_minimal_pdf(reference_dir / "Totally Different Guide.pdf")

    def _fast_extract(_path: Path, *, metadata_only: bool = False) -> ExtractionResult:
        return ExtractionResult(text="coverage-only", method="coverage_stub")

    monkeypatch.setattr("importers.reference_corpus_ingest.extract_asset_text", _fast_extract)

    try:
        build_reference_catalog(reference_dir=reference_dir, guides_dir=guides_dir)
        assert False, "Expected workbook/PDF pairing enforcement to fail"
    except ValueError as exc:
        assert "Workbook/PDF pairing enforcement failed" in str(exc)


def test_reference_ingestion_metadata_only_mode(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    guides_dir = tmp_path / "docs" / "guides"
    reference_dir.mkdir(parents=True)

    _write_minimal_xlsx(reference_dir / "Program Sheet.xlsx")
    _write_minimal_pdf(reference_dir / "Program Sheet.pdf")

    result = cast(
        dict[str, Any],
        build_reference_catalog(reference_dir=reference_dir, guides_dir=guides_dir, metadata_only=True),
    )
    asset_catalog = cast(dict[str, Any], result["asset_catalog"])
    assets = cast(list[dict[str, Any]], asset_catalog["assets"])

    assert asset_catalog["asset_count"] == 2
    assert asset_catalog["workbook_pdf_pair_count"] == 1
    assert all(int(item["extracted_characters"]) == 0 for item in assets)
    assert all(str(item["extraction_method"]).endswith("_metadata_only") for item in assets)


def test_reference_ingestion_pairing_override_for_my_new_program(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    guides_dir = tmp_path / "docs" / "guides"
    reference_dir.mkdir(parents=True)

    _write_minimal_xlsx(reference_dir / "my_new_program.xlsx")
    _write_minimal_pdf(reference_dir / "The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf")

    result = cast(
        dict[str, Any],
        build_reference_catalog(reference_dir=reference_dir, guides_dir=guides_dir, metadata_only=True),
    )
    pairs = cast(list[dict[str, Any]], result["asset_catalog"]["workbook_pdf_pairs"])

    assert len(pairs) == 1
    assert pairs[0]["workbook_asset_path"] == "reference/my_new_program.xlsx"
    assert pairs[0]["guide_asset_path"] == "reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf"
