import json
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.knowledge_loader import (
    load_compiled_manifest,
    load_doctrine_bundle,
    load_exercise_library,
    load_policy_bundle,
    load_source_registry,
)
from importers.source_to_knowledge_pipeline import build_compiled_knowledge


def _build_fixture_compiled_dir(tmp_path: Path) -> Path:
    guides_dir = tmp_path / "docs" / "guides"
    guides_dir.mkdir(parents=True)
    asset_catalog_path = guides_dir / "asset_catalog.json"
    provenance_index_path = guides_dir / "provenance_index.json"
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
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    compiled_dir = tmp_path / "knowledge" / "compiled"
    build_compiled_knowledge(
        asset_catalog_path=asset_catalog_path,
        provenance_index_path=provenance_index_path,
        overrides_path=REPO_ROOT / "knowledge" / "curation" / "source_registry_overrides.json",
        onboarding_dir=REPO_ROOT / "programs" / "gold",
        exercise_library_overrides_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_overrides.json",
        doctrine_seed_path=REPO_ROOT / "knowledge" / "curation" / "doctrine_bundles" / "multi_source_hypertrophy_v1.seed.json",
        policy_seed_path=REPO_ROOT / "knowledge" / "curation" / "policy_bundles" / "system_coaching_policy_v1.seed.json",
        output_dir=compiled_dir,
    )
    return compiled_dir


def test_knowledge_loader_reads_compiled_bundles_from_knowledge_compiled(tmp_path: Path) -> None:
    compiled_dir = _build_fixture_compiled_dir(tmp_path)

    manifest = load_compiled_manifest(compiled_dir)
    registry = load_source_registry(compiled_dir)
    exercise_library = load_exercise_library(compiled_dir)
    doctrine_bundle = load_doctrine_bundle("multi_source_hypertrophy_v1", compiled_dir)
    policy_bundle = load_policy_bundle("system_coaching_policy_v1", compiled_dir)

    assert manifest.bundle_id == "build_manifest"
    assert registry.bundle_id == "source_registry"
    assert exercise_library.bundle_id == "exercise_library_foundation"
    assert doctrine_bundle.bundle_id == "multi_source_hypertrophy_v1"
    assert policy_bundle.bundle_id == "system_coaching_policy_v1"
    assert policy_bundle.generated_full_body_adaptive_loop_policy is not None
    assert policy_bundle.generated_full_body_adaptive_loop_policy.policy_id == "generated_full_body_adaptive_loop_v1"


def test_knowledge_loader_rejects_non_knowledge_compiled_paths(tmp_path: Path) -> None:
    invalid_dir = tmp_path / "random"
    invalid_dir.mkdir(parents=True)

    with pytest.raises(ValueError):
        load_compiled_manifest(invalid_dir)


def test_knowledge_loader_surfaces_schema_validation_failures(tmp_path: Path) -> None:
    compiled_dir = tmp_path / "knowledge" / "compiled"
    compiled_dir.mkdir(parents=True)
    (compiled_dir / "build_manifest.v1.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_compiled_manifest(compiled_dir)
