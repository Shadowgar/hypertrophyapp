import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importers.source_to_knowledge_pipeline import build_compiled_knowledge


def test_source_to_knowledge_pipeline_writes_expected_artifacts(tmp_path: Path) -> None:
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

    output_dir = tmp_path / "knowledge" / "compiled"
    manifest = build_compiled_knowledge(
        asset_catalog_path=asset_catalog_path,
        provenance_index_path=provenance_index_path,
        overrides_path=REPO_ROOT / "knowledge" / "curation" / "source_registry_overrides.json",
        onboarding_dir=REPO_ROOT / "programs" / "gold",
        doctrine_seed_path=REPO_ROOT / "knowledge" / "curation" / "doctrine_bundles" / "multi_source_hypertrophy_v1.seed.json",
        policy_seed_path=REPO_ROOT / "knowledge" / "curation" / "policy_bundles" / "system_coaching_policy_v1.seed.json",
        output_dir=output_dir,
    )

    assert manifest.bundle_id == "build_manifest"
    assert manifest.artifacts
    assert (output_dir / "source_registry.v1.json").exists()
    assert (output_dir / "exercise_library.foundation.v1.json").exists()
    assert (output_dir / "doctrine_bundles" / "multi_source_hypertrophy_v1.bundle.json").exists()
    assert (output_dir / "policy_bundles" / "system_coaching_policy_v1.bundle.json").exists()
    assert (output_dir / "build_manifest.v1.json").exists()

    policy_payload = json.loads(
        (output_dir / "policy_bundles" / "system_coaching_policy_v1.bundle.json").read_text(encoding="utf-8")
    )
    assert policy_payload["constraint_resolution_policy"]["resolution_order"] == [
        "safety",
        "recoverability",
        "day_and_time_feasibility",
        "adherence_and_skill_feasibility",
        "locked_user_constraints_when_feasible",
        "active_specialization_priority",
        "hypertrophy_ideality",
        "variety_and_preference_refinement",
    ]
    assert policy_payload["minimum_viable_program_policy"]["fallback_order"] == [
        "reduce_exercise_variety",
        "reduce_optional_work",
        "reduce_frequency_before_violating_hard_constraints",
    ]

    second = build_compiled_knowledge(
        asset_catalog_path=asset_catalog_path,
        provenance_index_path=provenance_index_path,
        overrides_path=REPO_ROOT / "knowledge" / "curation" / "source_registry_overrides.json",
        onboarding_dir=REPO_ROOT / "programs" / "gold",
        doctrine_seed_path=REPO_ROOT / "knowledge" / "curation" / "doctrine_bundles" / "multi_source_hypertrophy_v1.seed.json",
        policy_seed_path=REPO_ROOT / "knowledge" / "curation" / "policy_bundles" / "system_coaching_policy_v1.seed.json",
        output_dir=output_dir,
    )
    assert manifest.model_dump(mode="json") == second.model_dump(mode="json")
