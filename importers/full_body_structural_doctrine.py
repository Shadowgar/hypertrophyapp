#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.knowledge_schema import CanonicalExerciseLibraryBundle, SourceRegistryBundle
from importers.doctrine_extraction import (
    ClaimCandidate,
    ResolvedClaim,
    UnresolvedConflict,
    cluster_claims,
    load_resolutions,
    load_structured_program_document,
    normalize_day_role,
    normalize_movement_pattern,
    normalize_slot_role,
    select_cluster_winner,
    write_unresolved_conflicts,
)
from importers.doctrine_extractors import StructureHeadingExtractor, TableWorkbookExtractor, EvidenceFragment


RULE_ID = "full_body_required_movement_patterns_v1"
RULE_DESCRIPTION = "Required movement-pattern coverage targets for minimum generated Full Body planning inputs."
TRACK = "structural"
RULE_THRESHOLD = 0.85
ALLOWED_REQUIRED_PATTERNS = (
    "squat",
    "hinge",
    "horizontal_press",
    "horizontal_pull",
    "vertical_pull",
    "vertical_press",
)
PRIORITY_RANK_BY_PATTERN = {
    "squat": 1,
    "hinge": 2,
    "horizontal_press": 3,
    "horizontal_pull": 4,
    "vertical_pull": 5,
    "vertical_press": 6,
}


@dataclass(frozen=True)
class RequiredMovementPatternsExtractionResult:
    extracted_claims: tuple[ClaimCandidate, ...]
    resolved_claims: tuple[ResolvedClaim, ...]
    unresolved_conflicts: tuple[UnresolvedConflict, ...]
    resolved_rule_payload: dict[str, Any] | None


def _iter_program_json_paths(program_dir: Path) -> list[Path]:
    paths = []
    for path in sorted(program_dir.glob("*.json")):
        if path.name.endswith(".onboarding.json") or path.name.endswith(".import_report.json"):
            continue
        paths.append(path)
    return paths


def _build_required_pattern_table_extractor() -> TableWorkbookExtractor:
    return TableWorkbookExtractor(
        track=TRACK,
        row_selector=lambda block: bool(block.structured_fields.get("exercise_id")),
        value_builder=lambda block: {
            "exercise_id": str(block.structured_fields.get("exercise_id") or ""),
            "day_role": str(block.structured_fields.get("day_role") or ""),
            "slot_role": str(block.structured_fields.get("slot_role") or ""),
            "week_index": int(block.structured_fields.get("week_index") or 0),
        },
    )


def build_day_structure_extractor() -> StructureHeadingExtractor:
    return StructureHeadingExtractor(
        track=TRACK,
        heading_selector=lambda block: bool(block.structured_fields.get("day_role")),
        value_builder=lambda heading, descendants: {
            "day_role": str(heading.structured_fields.get("day_role") or ""),
            "slot_count": sum(1 for item in descendants if item.content_type == "row_group"),
        },
    )


def extract_required_movement_pattern_fragments(
    *,
    program_dir: Path,
    source_registry_bundle: SourceRegistryBundle,
) -> tuple[tuple[EvidenceFragment, ...], tuple[EvidenceFragment, ...]]:
    table_extractor = _build_required_pattern_table_extractor()
    structure_extractor = build_day_structure_extractor()

    table_fragments: list[EvidenceFragment] = []
    structure_fragments: list[EvidenceFragment] = []
    for program_path in _iter_program_json_paths(program_dir):
        document = load_structured_program_document(
            program_path=program_path,
            source_registry_bundle=source_registry_bundle,
        )
        table_fragments.extend(
            table_extractor.extract(source=document.source, document=document)
        )
        structure_fragments.extend(
            structure_extractor.extract(source=document.source, document=document)
        )

    return tuple(table_fragments), tuple(structure_fragments)


def extract_required_movement_pattern_claims(
    *,
    program_dir: Path,
    source_registry_bundle: SourceRegistryBundle,
    exercise_library_bundle: CanonicalExerciseLibraryBundle,
) -> tuple[ClaimCandidate, ...]:
    table_fragments, _ = extract_required_movement_pattern_fragments(
        program_dir=program_dir,
        source_registry_bundle=source_registry_bundle,
    )
    claims: list[ClaimCandidate] = []
    for fragment in table_fragments:
        raw_value = dict(fragment.raw_extracted_value)
        try:
            movement_pattern, movement_confidence, movement_method = normalize_movement_pattern(
                exercise_id=str(raw_value.get("exercise_id") or ""),
                exercise_library_bundle=exercise_library_bundle,
            )
        except ValueError:
            continue
        if movement_pattern not in ALLOWED_REQUIRED_PATTERNS:
            continue
        day_role, day_confidence, day_method = normalize_day_role(str(raw_value.get("day_role") or ""))
        slot_role, slot_confidence, slot_method = normalize_slot_role(str(raw_value.get("slot_role") or ""))
        confidence = min(movement_confidence, day_confidence, slot_confidence)
        claims.append(
            ClaimCandidate(
                claim_key=f"rule:{RULE_ID}:requirements:{movement_pattern}",
                target_type="doctrine_rule_field",
                target_id=RULE_ID,
                payload_path=f"requirements[{movement_pattern}]",
                normalized_value={
                    "movement_pattern": movement_pattern,
                    "minimum_weekly_exposures": 1,
                    "priority_rank": PRIORITY_RANK_BY_PATTERN[movement_pattern],
                },
                scope={"split_scope": "full_body"},
                normalization_method=" + ".join([movement_method, day_method, slot_method]),
                normalization_confidence=confidence,
                evidence_fragment_id=fragment.fragment_id,
                source_id=fragment.source_id,
                source_family_id=fragment.source_family_id,
                authority_weight=float(fragment.local_context.get("source_authority_weight") or 1.0),
                classification_confidence=float(fragment.local_context.get("source_classification_confidence") or 1.0),
                excerpt_quality=fragment.excerpt_quality,
            )
        )
    return tuple(
        sorted(
            claims,
            key=lambda item: (
                item.claim_key,
                item.source_family_id,
                item.source_id,
                item.evidence_fragment_id,
            ),
        )
    )


def resolve_required_movement_pattern_claims(
    *,
    claims: tuple[ClaimCandidate, ...],
    resolutions_path: Path | None,
    unresolved_path: Path,
) -> tuple[tuple[ResolvedClaim, ...], tuple[UnresolvedConflict, ...]]:
    clusters = cluster_claims(list(claims))
    resolutions = load_resolutions(resolutions_path)
    resolved: list[ResolvedClaim] = []
    unresolved: list[UnresolvedConflict] = []
    for claim_key in sorted(clusters):
        winner = select_cluster_winner(
            cluster=clusters[claim_key],
            threshold=RULE_THRESHOLD,
            resolutions=resolutions,
        )
        if isinstance(winner, ResolvedClaim):
            resolved.append(winner)
        else:
            unresolved.append(winner)

    write_unresolved_conflicts(
        path=unresolved_path,
        bundle_id="multi_source_hypertrophy_v1",
        conflicts=unresolved,
    )
    return tuple(resolved), tuple(unresolved)


def synthesize_required_movement_patterns_rule(
    *,
    resolved_claims: tuple[ResolvedClaim, ...],
) -> dict[str, Any] | None:
    claims_by_pattern = {
        str(item.chosen_value["movement_pattern"]): item for item in resolved_claims
    }
    if set(claims_by_pattern) != set(ALLOWED_REQUIRED_PATTERNS):
        return None

    requirements = [
        claims_by_pattern[pattern].chosen_value
        for pattern in sorted(ALLOWED_REQUIRED_PATTERNS, key=lambda item: PRIORITY_RANK_BY_PATTERN[item])
    ]
    provenance: list[dict[str, Any]] = []
    for pattern in sorted(ALLOWED_REQUIRED_PATTERNS, key=lambda item: PRIORITY_RANK_BY_PATTERN[item]):
        claim = claims_by_pattern[pattern]
        supporting_claims = sorted(
            claim.supporting_claims,
            key=lambda item: (-item.excerpt_quality, item.source_family_id, item.source_id),
        )
        seen_source_ids: set[str] = set()
        for supporting_claim in supporting_claims:
            if supporting_claim.source_id in seen_source_ids:
                continue
            seen_source_ids.add(supporting_claim.source_id)
            provenance.append(
                {
                    "source_id": supporting_claim.source_id,
                    "source_path": supporting_claim.source_id,
                    "section_ref": supporting_claim.payload_path,
                    "confidence": claim.confidence,
                    "curation_status": "curated",
                    "note": f"payload_path={supporting_claim.payload_path}; resolution_basis={claim.resolution_basis}",
                }
            )
            if len(seen_source_ids) >= 2:
                break

    return {
        "rule_id": RULE_ID,
        "module_id": "exercise_selection",
        "status": "curated",
        "description": RULE_DESCRIPTION,
        "tags": ["exercise_selection", "full_body", "curated", "coverage"],
        "provenance": provenance,
        "payload": {"requirements": requirements},
    }


def build_full_body_required_movement_patterns_rule(
    *,
    program_dir: Path,
    source_registry_bundle: SourceRegistryBundle,
    exercise_library_bundle: CanonicalExerciseLibraryBundle,
    resolutions_path: Path | None,
    unresolved_path: Path,
) -> RequiredMovementPatternsExtractionResult:
    extracted_claims = extract_required_movement_pattern_claims(
        program_dir=program_dir,
        source_registry_bundle=source_registry_bundle,
        exercise_library_bundle=exercise_library_bundle,
    )
    resolved_claims, unresolved_conflicts = resolve_required_movement_pattern_claims(
        claims=extracted_claims,
        resolutions_path=resolutions_path,
        unresolved_path=unresolved_path,
    )
    resolved_rule_payload = synthesize_required_movement_patterns_rule(
        resolved_claims=resolved_claims,
    )
    return RequiredMovementPatternsExtractionResult(
        extracted_claims=extracted_claims,
        resolved_claims=resolved_claims,
        unresolved_conflicts=unresolved_conflicts,
        resolved_rule_payload=resolved_rule_payload,
    )


def apply_full_body_required_movement_patterns_rule(
    *,
    doctrine_seed_payload: dict[str, Any],
    program_dir: Path,
    source_registry_bundle: SourceRegistryBundle,
    exercise_library_bundle: CanonicalExerciseLibraryBundle,
    resolutions_path: Path | None,
    unresolved_path: Path,
) -> tuple[dict[str, Any], RequiredMovementPatternsExtractionResult]:
    result = build_full_body_required_movement_patterns_rule(
        program_dir=program_dir,
        source_registry_bundle=source_registry_bundle,
        exercise_library_bundle=exercise_library_bundle,
        resolutions_path=resolutions_path,
        unresolved_path=unresolved_path,
    )
    if result.resolved_rule_payload is None:
        return doctrine_seed_payload, result

    payload = json.loads(json.dumps(doctrine_seed_payload))
    exercise_selection_rules = list(payload.get("rules_by_module", {}).get("exercise_selection", []))
    replaced = False
    for index, rule in enumerate(exercise_selection_rules):
        if rule.get("rule_id") == RULE_ID:
            exercise_selection_rules[index] = result.resolved_rule_payload
            replaced = True
            break
    if not replaced:
        exercise_selection_rules.append(result.resolved_rule_payload)
    payload.setdefault("rules_by_module", {})["exercise_selection"] = exercise_selection_rules
    return payload, result
