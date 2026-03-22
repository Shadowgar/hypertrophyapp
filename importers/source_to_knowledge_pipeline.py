#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.knowledge_schema import (
    CanonicalExerciseLibraryBundle,
    CompiledArtifactManifestEntry,
    CompiledKnowledgeManifest,
    DoctrineBundle,
    PolicyBundle,
)
from app.knowledge_loader import load_source_registry as load_current_source_registry
from importers.exercise_library_foundation import build_exercise_library_foundation, write_exercise_library
from importers.full_body_structural_doctrine import apply_full_body_required_movement_patterns_rule
from importers.source_registry_builder import build_source_registry, write_source_registry


DEFAULT_SCHEMA_VERSION = "knowledge-1"
DEFAULT_BUNDLE_VERSION = "0.1.0"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_stable_json(payload), encoding="utf-8")


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _finalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    base_payload = dict(payload)
    base_payload.pop("output_signature", None)
    base_payload.pop("aggregate_signature", None)
    output_signature = _sha256_text(_stable_json(base_payload))
    final_payload = dict(base_payload)
    final_payload["output_signature"] = output_signature
    final_payload["aggregate_signature"] = _sha256_text(_stable_json(final_payload))
    return final_payload


def _compile_seed_bundle(seed_path: Path, model_type: type[DoctrineBundle] | type[PolicyBundle]) -> tuple[DoctrineBundle | PolicyBundle, str]:
    seed_text = seed_path.read_text(encoding="utf-8")
    seed_payload = json.loads(seed_text)
    seed_model = model_type.model_validate(seed_payload)
    compiled_payload = seed_model.model_dump(mode="json")
    compiled_payload["input_signature"] = _sha256_text(seed_text)
    compiled_bundle = model_type.model_validate(_finalize_payload(compiled_payload))
    return compiled_bundle, _sha256_text(seed_text)


def _compile_doctrine_bundle_with_precompile_hooks(
    *,
    doctrine_seed_path: Path,
    source_registry_bundle: Any,
    exercise_library_bundle: CanonicalExerciseLibraryBundle,
    program_dir: Path,
    doctrine_resolutions_path: Path | None,
    doctrine_unresolved_output_path: Path,
) -> tuple[DoctrineBundle, str]:
    seed_text = doctrine_seed_path.read_text(encoding="utf-8")
    seed_payload = json.loads(seed_text)
    hydrated_seed_payload, _ = apply_full_body_required_movement_patterns_rule(
        doctrine_seed_payload=seed_payload,
        program_dir=program_dir,
        source_registry_bundle=source_registry_bundle,
        exercise_library_bundle=exercise_library_bundle,
        resolutions_path=doctrine_resolutions_path,
        unresolved_path=doctrine_unresolved_output_path,
    )
    seed_model = DoctrineBundle.model_validate(hydrated_seed_payload)
    compiled_payload = seed_model.model_dump(mode="json")
    compiled_payload["input_signature"] = _sha256_text(seed_text)
    compiled_bundle = DoctrineBundle.model_validate(_finalize_payload(compiled_payload))
    return compiled_bundle, _sha256_text(seed_text)


def _validate_doctrine_bundle_against_exercise_library(
    doctrine_bundle: DoctrineBundle,
    exercise_library: CanonicalExerciseLibraryBundle,
) -> None:
    available_patterns = {record.movement_pattern for record in exercise_library.records if record.movement_pattern}
    for rule in doctrine_bundle.rules_by_module.get("exercise_selection", []):
        if rule.rule_id != "full_body_required_movement_patterns_v1":
            continue
        requirements = rule.payload.get("requirements", [])
        missing_patterns = sorted(
            {
                requirement.get("movement_pattern")
                for requirement in requirements
                if requirement.get("movement_pattern") not in available_patterns
            }
        )
        if missing_patterns:
            joined = ", ".join(missing_patterns)
            raise ValueError(f"full_body_required_movement_patterns_v1 references unavailable movement patterns: {joined}")


def build_compiled_knowledge(
    *,
    asset_catalog_path: Path,
    provenance_index_path: Path,
    overrides_path: Path,
    onboarding_dir: Path,
    exercise_library_overrides_path: Path,
    doctrine_seed_path: Path,
    policy_seed_path: Path,
    output_dir: Path,
    exercise_library_extraction_resolutions_path: Path | None = None,
    exercise_library_extraction_unresolved_output_path: Path | None = None,
    doctrine_resolutions_path: Path | None = None,
    doctrine_unresolved_output_path: Path | None = None,
) -> CompiledKnowledgeManifest:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "doctrine_bundles").mkdir(parents=True, exist_ok=True)
    (output_dir / "policy_bundles").mkdir(parents=True, exist_ok=True)

    source_registry = build_source_registry(
        asset_catalog_path=asset_catalog_path,
        provenance_index_path=provenance_index_path,
        overrides_path=overrides_path,
    )
    source_registry_path = output_dir / "source_registry.v1.json"
    write_source_registry(source_registry, source_registry_path)

    exercise_library, warnings = build_exercise_library_foundation(
        onboarding_dir=onboarding_dir,
        source_registry_bundle=load_current_source_registry(),
        override_path=exercise_library_overrides_path,
        extraction_resolutions_path=exercise_library_extraction_resolutions_path,
        extraction_unresolved_output_path=exercise_library_extraction_unresolved_output_path,
    )
    exercise_library_path = output_dir / "exercise_library.foundation.v1.json"
    write_exercise_library(exercise_library, exercise_library_path)

    unresolved_output_path = doctrine_unresolved_output_path or doctrine_seed_path.with_name(
        doctrine_seed_path.name.replace(".seed.json", ".unresolved.json")
    )
    doctrine_bundle, doctrine_seed_signature = _compile_doctrine_bundle_with_precompile_hooks(
        doctrine_seed_path=doctrine_seed_path,
        source_registry_bundle=source_registry,
        exercise_library_bundle=exercise_library,
        program_dir=onboarding_dir,
        doctrine_resolutions_path=doctrine_resolutions_path,
        doctrine_unresolved_output_path=unresolved_output_path,
    )
    _validate_doctrine_bundle_against_exercise_library(doctrine_bundle, exercise_library)
    doctrine_bundle_path = output_dir / "doctrine_bundles" / f"{doctrine_bundle.bundle_id}.bundle.json"
    _write_json(doctrine_bundle_path, doctrine_bundle.model_dump(mode="json"))

    policy_bundle, policy_seed_signature = _compile_seed_bundle(policy_seed_path, PolicyBundle)
    policy_bundle_path = output_dir / "policy_bundles" / f"{policy_bundle.bundle_id}.bundle.json"
    _write_json(policy_bundle_path, policy_bundle.model_dump(mode="json"))

    artifacts = [
        CompiledArtifactManifestEntry(
            artifact_id="source_registry",
            artifact_type="source_registry_bundle",
            path=_safe_relative(source_registry_path, REPO_ROOT),
            input_signature=source_registry.input_signature,
            output_signature=source_registry.output_signature,
        ),
        CompiledArtifactManifestEntry(
            artifact_id="exercise_library_foundation",
            artifact_type="exercise_library_bundle",
            path=_safe_relative(exercise_library_path, REPO_ROOT),
            input_signature=exercise_library.input_signature,
            output_signature=exercise_library.output_signature,
        ),
        CompiledArtifactManifestEntry(
            artifact_id=doctrine_bundle.bundle_id,
            artifact_type="doctrine_bundle",
            path=_safe_relative(doctrine_bundle_path, REPO_ROOT),
            input_signature=doctrine_bundle.input_signature,
            output_signature=doctrine_bundle.output_signature,
        ),
        CompiledArtifactManifestEntry(
            artifact_id=policy_bundle.bundle_id,
            artifact_type="policy_bundle",
            path=_safe_relative(policy_bundle_path, REPO_ROOT),
            input_signature=policy_bundle.input_signature,
            output_signature=policy_bundle.output_signature,
        ),
    ]
    artifacts = sorted(artifacts, key=lambda item: item.artifact_id)

    input_signature = _sha256_text(
        "\n".join(
            [
                source_registry.input_signature,
                exercise_library.input_signature,
                doctrine_seed_signature,
                policy_seed_signature,
            ]
        )
    )
    payload = {
        "schema_version": DEFAULT_SCHEMA_VERSION,
        "bundle_id": "build_manifest",
        "bundle_version": DEFAULT_BUNDLE_VERSION,
        "input_signature": input_signature,
        "output_signature": "pending",
        "aggregate_signature": "pending",
        "artifacts": [artifact.model_dump(mode="json") for artifact in artifacts],
        "warnings": warnings,
    }
    manifest = CompiledKnowledgeManifest.model_validate(_finalize_payload(payload))
    _write_json(output_dir / "build_manifest.v1.json", manifest.model_dump(mode="json"))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile deterministic knowledge bundles for runtime use.")
    parser.add_argument(
        "--asset-catalog",
        type=Path,
        default=REPO_ROOT / "docs" / "guides" / "asset_catalog.json",
    )
    parser.add_argument(
        "--provenance-index",
        type=Path,
        default=REPO_ROOT / "docs" / "guides" / "provenance_index.json",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=REPO_ROOT / "knowledge" / "curation" / "source_registry_overrides.json",
    )
    parser.add_argument(
        "--onboarding-dir",
        type=Path,
        default=REPO_ROOT / "programs" / "gold",
    )
    parser.add_argument(
        "--exercise-library-overrides",
        type=Path,
        default=REPO_ROOT / "knowledge" / "curation" / "exercise_library_overrides.json",
    )
    parser.add_argument(
        "--doctrine-seed",
        type=Path,
        default=REPO_ROOT / "knowledge" / "curation" / "doctrine_bundles" / "multi_source_hypertrophy_v1.seed.json",
    )
    parser.add_argument(
        "--policy-seed",
        type=Path,
        default=REPO_ROOT / "knowledge" / "curation" / "policy_bundles" / "system_coaching_policy_v1.seed.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "knowledge" / "compiled",
    )
    parser.add_argument(
        "--exercise-library-extraction-resolutions",
        type=Path,
        default=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.resolutions.json",
    )
    parser.add_argument(
        "--exercise-library-extraction-unresolved-output",
        type=Path,
        default=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.unresolved.json",
    )
    parser.add_argument(
        "--doctrine-resolutions",
        type=Path,
        default=REPO_ROOT / "knowledge" / "curation" / "doctrine_bundles" / "multi_source_hypertrophy_v1.resolutions.json",
    )
    parser.add_argument(
        "--doctrine-unresolved-output",
        type=Path,
        default=REPO_ROOT / "knowledge" / "curation" / "doctrine_bundles" / "multi_source_hypertrophy_v1.unresolved.json",
    )
    args = parser.parse_args()

    manifest = build_compiled_knowledge(
        asset_catalog_path=args.asset_catalog,
        provenance_index_path=args.provenance_index,
        overrides_path=args.overrides,
        onboarding_dir=args.onboarding_dir,
        exercise_library_overrides_path=args.exercise_library_overrides,
        doctrine_seed_path=args.doctrine_seed,
        policy_seed_path=args.policy_seed,
        output_dir=args.output_dir,
        exercise_library_extraction_resolutions_path=args.exercise_library_extraction_resolutions,
        exercise_library_extraction_unresolved_output_path=args.exercise_library_extraction_unresolved_output,
        doctrine_resolutions_path=args.doctrine_resolutions,
        doctrine_unresolved_output_path=args.doctrine_unresolved_output,
    )
    print(_safe_relative(args.output_dir / "build_manifest.v1.json", REPO_ROOT))
    for warning in manifest.warnings:
        print(f"[warn] {warning}")


if __name__ == "__main__":
    main()
