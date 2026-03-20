import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importers.source_registry_builder import build_source_registry


def test_source_registry_builds_deterministic_entries_with_overrides(tmp_path: Path) -> None:
    guides_dir = tmp_path / "docs" / "guides"
    guides_dir.mkdir(parents=True)
    asset_catalog_path = guides_dir / "asset_catalog.json"
    provenance_index_path = guides_dir / "provenance_index.json"
    overrides_path = tmp_path / "knowledge" / "curation" / "source_registry_overrides.json"
    overrides_path.parent.mkdir(parents=True)

    asset_catalog_path.write_text(
        json.dumps(
            {
                "aggregate_signature": "asset-signature",
                "assets": [
                    {
                        "asset_path": "reference/Program Sheet.xlsx",
                        "asset_sha256": "a" * 64,
                        "asset_type": "xlsx",
                        "derived_doc": "docs/guides/generated/program-sheet.md",
                    },
                    {
                        "asset_path": "reference/Program Manual.pdf",
                        "asset_sha256": "b" * 64,
                        "asset_type": "pdf",
                        "derived_doc": "docs/guides/generated/program-manual.md",
                    },
                    {
                        "asset_path": "reference/Technique-Handbook.pdf",
                        "asset_sha256": "c" * 64,
                        "asset_type": "pdf",
                        "derived_doc": "docs/guides/generated/technique.md",
                    },
                ],
                "workbook_pdf_pairs": [
                    {
                        "workbook_asset_path": "reference/Program Sheet.xlsx",
                        "guide_asset_path": "reference/Program Manual.pdf",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    provenance_index_path.write_text(
        json.dumps(
            {
                "aggregate_signature": "provenance-signature",
                "provenance": [
                    {
                        "asset": "reference/Program Sheet.xlsx",
                        "derived_entities": [{"path": "docs/guides/generated/program-sheet.md"}],
                    },
                    {
                        "asset": "reference/Program Manual.pdf",
                        "derived_entities": [{"path": "docs/guides/generated/program-manual.md"}],
                    },
                    {
                        "asset": "reference/Technique-Handbook.pdf",
                        "derived_entities": [{"path": "docs/guides/generated/technique.md"}],
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    overrides_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "match_path": "reference/Technique-Handbook.pdf",
                        "source_kind": "technique_guide",
                        "classification_confidence": 1.0,
                        "curation_status": "curated",
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    first = build_source_registry(
        asset_catalog_path=asset_catalog_path,
        provenance_index_path=provenance_index_path,
        overrides_path=overrides_path,
    )
    second = build_source_registry(
        asset_catalog_path=asset_catalog_path,
        provenance_index_path=provenance_index_path,
        overrides_path=overrides_path,
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.bundle_id == "source_registry"
    assert first.schema_version == "knowledge-1"
    assert len(first.entries) == 3

    by_path = {entry.source_path: entry for entry in first.entries}
    workbook = by_path["reference/Program Sheet.xlsx"]
    guide = by_path["reference/Program Manual.pdf"]
    technique = by_path["reference/Technique-Handbook.pdf"]

    assert workbook.source_kind == "authored_program_workbook"
    assert guide.source_kind == "program_manual"
    assert technique.source_kind == "technique_guide"
    assert workbook.paired_source_ids == [guide.source_id]
    assert guide.paired_source_ids == [workbook.source_id]
    assert workbook.derived_doc_paths == ["docs/guides/generated/program-sheet.md"]
    assert technique.curation_status == "curated"
    assert technique.classification_confidence == 1.0
