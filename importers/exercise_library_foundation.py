#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.adaptive_schema import ProgramOnboardingPackage
from app.knowledge_schema import (
    CanonicalExerciseLibraryBundle,
    CanonicalExerciseRecord,
    ExerciseLibraryOverrideBundle,
    ExerciseLibraryOverrideRecord,
    ProvenanceRef,
    SourceRegistryBundle,
)
from importers.exercise_intelligence_extraction import (
    apply_exercise_intelligence_metadata,
    build_exercise_intelligence_extraction_result,
)


DEFAULT_SCHEMA_VERSION = "knowledge-1"
DEFAULT_BUNDLE_ID = "exercise_library_foundation"
DEFAULT_BUNDLE_VERSION = "0.1.0"
DEFAULT_OVERRIDE_PATH = REPO_ROOT / "knowledge" / "curation" / "exercise_library_overrides.json"
DEFAULT_EXTRACTION_RESOLUTIONS_PATH = REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.resolutions.json"
DEFAULT_EXTRACTION_UNRESOLVED_PATH = REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.unresolved.json"
CURATED_OVERRIDE_SOURCE_ID = "curated-exercise-library-override-v1"
_WEAK_POINT_PLACEHOLDER_RE = re.compile(r"^weak_point_exercise", re.IGNORECASE)


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


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "exercise"


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({value.strip() for value in values if value and value.strip()})


def _is_placeholder(entry: dict[str, Any]) -> bool:
    exercise_id = str(entry.get("exercise_id") or "").strip()
    canonical_name = str(entry.get("canonical_name") or "").strip()
    return bool(_WEAK_POINT_PLACEHOLDER_RE.search(exercise_id) or _WEAK_POINT_PLACEHOLDER_RE.search(canonical_name))


def _first_non_empty(values: list[str | None]) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _merge_record(group_key: str, members: list[dict[str, Any]]) -> CanonicalExerciseRecord:
    member_ids = sorted({str(member["exercise_id"]) for member in members})
    canonical_names = sorted({str(member["canonical_name"]) for member in members})
    exercise_id = sorted(member_ids, key=lambda item: (len(item), item))[0]
    canonical_name = sorted(canonical_names, key=lambda item: (len(item), item))[0]
    aliases = _sorted_unique(
        [alias for member in members for alias in list(member.get("aliases") or [])] + [canonical_name]
    )
    equipment_tags = _sorted_unique(
        [tag for member in members for tag in list(member.get("equipment_tags") or [])]
    )
    primary_muscles = _sorted_unique(
        [muscle for member in members for muscle in list(member.get("primary_muscles") or [])]
    )
    secondary_muscles = _sorted_unique(
        [muscle for member in members for muscle in list(member.get("secondary_muscles") or [])]
    )
    technique_guidance = _sorted_unique(
        [str(member.get("execution") or "") for member in members]
        + [cue for member in members for cue in list(member.get("coaching_cues") or [])]
    )
    movement_pattern = _first_non_empty([str(member.get("movement_pattern") or "").strip() or None for member in members])
    source_program_ids = _sorted_unique([str(member["source_program_id"]) for member in members])

    provenance = sorted(
        [
            ProvenanceRef(
                source_id=f"onboarding-{member['source_program_id']}",
                source_path=str(member["source_path"]),
                section_ref=f"exercise_library:{member['exercise_id']}",
                confidence=0.7,
                curation_status="seeded",
                note="Foundation-stage exercise record derived from onboarding package; final /reference-sourced exercise provenance is deferred.",
            )
            for member in members
        ],
        key=lambda item: (item.source_id, item.section_ref or ""),
    )

    confidence = 0.85 if len(source_program_ids) > 1 else 0.7
    return CanonicalExerciseRecord(
        exercise_id=exercise_id,
        canonical_name=canonical_name,
        aliases=aliases,
        family_id=group_key,
        movement_pattern=movement_pattern,
        primary_muscles=primary_muscles,
        secondary_muscles=secondary_muscles,
        equipment_tags=equipment_tags,
        contraindications=[],
        technique_guidance=technique_guidance,
        progression_compatibility=[],
        substitution_class=group_key,
        fatigue_cost=None,
        skill_demand=None,
        stability_demand=None,
        overlap_relations=[],
        source_program_ids=source_program_ids,
        provenance=provenance,
        confidence=confidence,
        curation_status="seeded",
    )


def _load_overrides(override_path: Path | None) -> tuple[dict[str, ExerciseLibraryOverrideRecord], str | None]:
    if override_path is None:
        return {}, None
    if not override_path.exists():
        raise ValueError(f"exercise library override file not found: {override_path}")
    override_text = override_path.read_text(encoding="utf-8")
    override_bundle = ExerciseLibraryOverrideBundle.model_validate(json.loads(override_text))
    return {record.exercise_id: record for record in override_bundle.records}, _sha256_text(override_text)


def _apply_override(
    record: CanonicalExerciseRecord,
    override: ExerciseLibraryOverrideRecord,
    *,
    override_path: Path,
) -> CanonicalExerciseRecord:
    provenance = list(record.provenance)
    provenance.append(
        ProvenanceRef(
            source_id=CURATED_OVERRIDE_SOURCE_ID,
            source_path=_safe_relative(override_path, REPO_ROOT),
            section_ref=f"exercise_library_override:{record.exercise_id}",
            confidence=1.0,
            curation_status="curated",
            note="Curated augmentation for deterministic scored-selection metadata; not a source-derived exercise fact.",
        )
    )
    payload = record.model_dump(mode="json")
    payload.update(
        {
            "fatigue_cost": override.fatigue_cost,
            "skill_demand": override.skill_demand,
            "stability_demand": override.stability_demand,
            "progression_compatibility": list(override.progression_compatibility),
            "provenance": [item.model_dump(mode="json") for item in provenance],
            "curation_status": "curated",
        }
    )
    return CanonicalExerciseRecord.model_validate(payload)


def _finalize_bundle_payload(payload: dict[str, Any]) -> dict[str, Any]:
    base_payload = dict(payload)
    base_payload.pop("output_signature", None)
    base_payload.pop("aggregate_signature", None)
    output_signature = _sha256_text(_stable_json(base_payload))
    final_payload = dict(base_payload)
    final_payload["output_signature"] = output_signature
    final_payload["aggregate_signature"] = _sha256_text(_stable_json(final_payload))
    return final_payload


def build_exercise_library_foundation(
    *,
    onboarding_dir: Path,
    source_registry_bundle: SourceRegistryBundle | None = None,
    override_path: Path | None = DEFAULT_OVERRIDE_PATH,
    extraction_resolutions_path: Path | None = DEFAULT_EXTRACTION_RESOLUTIONS_PATH,
    extraction_unresolved_output_path: Path | None = DEFAULT_EXTRACTION_UNRESOLVED_PATH,
    current_compiled_dir: Path | None = None,
    schema_version: str = DEFAULT_SCHEMA_VERSION,
    bundle_version: str = DEFAULT_BUNDLE_VERSION,
) -> tuple[CanonicalExerciseLibraryBundle, list[str]]:
    onboarding_paths = sorted(onboarding_dir.glob("*.onboarding.json"))
    grouped_members: dict[str, list[dict[str, Any]]] = {}
    warnings: list[str] = []
    input_signature_parts: list[str] = []
    overrides_by_exercise_id, override_signature = _load_overrides(override_path)

    for onboarding_path in onboarding_paths:
        input_signature_parts.append(_sha256_text(onboarding_path.read_text(encoding="utf-8")))
        payload = json.loads(onboarding_path.read_text(encoding="utf-8"))
        package = ProgramOnboardingPackage.model_validate(payload)
        source_path = _safe_relative(onboarding_path, REPO_ROOT)

        for entry in package.exercise_library:
            member = entry.model_dump(mode="json")
            if _is_placeholder(member):
                warnings.append(
                    f"Skipped placeholder exercise from {package.program_id}: {member['exercise_id']}"
                )
                continue

            group_key = _slugify(str(member["canonical_name"]))
            member["source_program_id"] = package.program_id
            member["source_path"] = source_path
            grouped_members.setdefault(group_key, []).append(member)

    records = [
        _merge_record(group_key, members)
        for group_key, members in sorted(grouped_members.items(), key=lambda item: item[0])
    ]
    records_by_id = {record.exercise_id: record for record in records}
    unknown_override_ids = sorted(set(overrides_by_exercise_id).difference(records_by_id))
    if unknown_override_ids:
        joined = ", ".join(unknown_override_ids)
        raise ValueError(f"exercise library overrides reference unknown exercise ids: {joined}")
    if source_registry_bundle is not None and extraction_unresolved_output_path is not None:
        extraction_result = build_exercise_intelligence_extraction_result(
            onboarding_dir=onboarding_dir,
            source_registry_bundle=source_registry_bundle,
            current_compiled_dir=current_compiled_dir,
            resolutions_path=extraction_resolutions_path,
            unresolved_path=extraction_unresolved_output_path,
        )
        records = apply_exercise_intelligence_metadata(
            records=records,
            resolved_claims=extraction_result.resolved_claims,
        )
        input_signature_parts.append(source_registry_bundle.output_signature)
        input_signature_parts.extend(extraction_result.input_signature_parts)
    if override_signature is not None:
        input_signature_parts.append(override_signature)
    if override_path is not None:
        records = [
            _apply_override(record, overrides_by_exercise_id[record.exercise_id], override_path=override_path)
            if record.exercise_id in overrides_by_exercise_id
            else record
            for record in records
        ]
    input_signature = _sha256_text("\n".join(input_signature_parts))
    payload = {
        "schema_version": schema_version,
        "bundle_id": DEFAULT_BUNDLE_ID,
        "bundle_version": bundle_version,
        "input_signature": input_signature,
        "output_signature": "pending",
        "aggregate_signature": "pending",
        "records": [record.model_dump(mode="json") for record in records],
    }
    bundle = CanonicalExerciseLibraryBundle.model_validate(_finalize_bundle_payload(payload))
    return bundle, sorted(set(warnings))


def write_exercise_library(bundle: CanonicalExerciseLibraryBundle, output_path: Path) -> None:
    _write_json(output_path, bundle.model_dump(mode="json"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile the exercise library foundation bundle.")
    parser.add_argument(
        "--onboarding-dir",
        type=Path,
        default=REPO_ROOT / "programs" / "gold",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "knowledge" / "compiled" / "exercise_library.foundation.v1.json",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=DEFAULT_OVERRIDE_PATH,
    )
    args = parser.parse_args()

    bundle, warnings = build_exercise_library_foundation(
        onboarding_dir=args.onboarding_dir,
        override_path=args.overrides,
    )
    write_exercise_library(bundle, args.output)
    print(_safe_relative(args.output, REPO_ROOT))
    for warning in warnings:
        print(f"[warn] {warning}")


if __name__ == "__main__":
    main()
