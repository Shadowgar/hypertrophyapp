#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"
FIXTURES_ROOT = API_ROOT / "tests" / "fixtures"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
if str(FIXTURES_ROOT) not in sys.path:
    sys.path.insert(0, str(FIXTURES_ROOT))

from app.generated_assessment_builder import build_user_assessment
from app.generated_assessment_schema import ProfileAssessmentInput
from app.generated_full_body_blueprint_builder import build_generated_full_body_blueprint_input
from app.knowledge_loader import load_doctrine_bundle, load_exercise_library, load_policy_bundle
from app.knowledge_schema import CanonicalExerciseLibraryBundle, CanonicalExerciseRecord, ProvenanceRef, SourceRegistryBundle
from generated_full_body_archetypes import get_generated_full_body_archetypes
from importers.doctrine_extraction import (
    ClaimCandidate,
    ResolvedClaim,
    SourceEnvelope,
    UnresolvedConflict,
    cluster_claims,
    load_resolutions,
    normalize_ascii_text,
    normalize_day_role,
    normalize_movement_pattern,
    normalize_slot_role,
    select_cluster_winner,
    write_unresolved_conflicts,
)


EXTRACTION_BUNDLE_ID = "exercise_library_extraction"
ALLOWED_ONBOARDING_FILENAMES = (
    "pure_bodybuilding_phase_1_full_body.onboarding.json",
    "pure_bodybuilding_phase_2_full_body.onboarding.json",
)
PROGRAM_ID_TO_FAMILY = {
    "pure_bodybuilding_phase_1_full_body": "pure_bodybuilding_phase_1",
    "pure_bodybuilding_phase_2_full_body": "pure_bodybuilding_phase_2",
}
ALLOWED_SOURCE_FAMILIES = frozenset(PROGRAM_ID_TO_FAMILY.values())
COMPOUND_MOVEMENT_PATTERNS = frozenset(
    {
        "squat",
        "hinge",
        "horizontal_press",
        "horizontal_pull",
        "vertical_pull",
        "vertical_press",
    }
)
LOW_DEMAND_SLOT_ROLES = frozenset({"accessory", "isolation", "weak_point"})
SUPPORT_ASSISTIVE_EQUIPMENT_TAGS = frozenset({"cable", "machine"})
FREEWEIGHT_EQUIPMENT_TAGS = frozenset({"barbell", "dumbbell", "kettlebell", "bodyweight"})
FIELD_THRESHOLDS = {
    "fatigue_cost": 0.85,
    "skill_demand": 0.85,
    "stability_demand": 0.85,
    "progression_compatibility": 0.90,
}
HIGH_FATIGUE_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\ba lot of muscle damage\b",
        r"\bvery fatiguing\b",
        r"\bdon t be tempted to go too heavy\b",
    )
)
HIGH_SKILL_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bbalance\b",
        r"\bbrace\b",
        r"\bbracing\b",
        r"\bone arm at a time\b",
        r"\bsingle arm\b",
        r"\bsingle leg\b",
    )
)
HIGH_STABILITY_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bbalance\b",
        r"\bstability\b",
        r"\bbrace\b",
        r"\bbracing\b",
    )
)
MODERATE_STABILITY_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bone arm at a time\b",
        r"\bsingle arm\b",
        r"\bsingle leg\b",
    )
)
UNILATERAL_OR_UNSUPPORTED_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bsingle arm\b",
        r"\bsingle leg\b",
        r"\bunilateral\b",
        r"\bone arm at a time\b",
        r"\bstanding\b",
        r"\bsplit stance\b",
        r"\bstaggered stance\b",
        r"\blunge\b",
        r"\bsplit squat\b",
        r"\bbalance\b",
        r"\bbrace\b",
        r"\bbracing\b",
        r"\bcuff\b",
        r"\blateral raise\b",
        r"\btorso is parallel\b",
        r"\bparallel with the floor\b",
        r"\bbent over\b",
    )
)
SUPPORTED_ACCESSORY_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bseated machine\b",
        r"\bseated\b",
        r"\bmachine\b",
        r"\bsmith\b",
        r"\bpinned against the pad\b",
        r"\bpad\b",
        r"\bbench\b",
        r"\bbench support\b",
        r"\btriceps firmly pinned\b",
        r"\bpreacher\b",
        r"\bpec deck\b",
        r"\bchest supported\b",
        r"\bchest-supported\b",
        r"\blying machine\b",
        r"\blying cable\b",
        r"\bguided path\b",
        r"\bback support\b",
    )
)
COMPOUND_ROLE_FALLBACK_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bdeadlift\b",
        r"\brdl\b",
        r"\bromanian deadlift\b",
        r"\bsquat\b",
        r"\bhinge\b",
        r"\brow\b",
        r"\bpull ?up\b",
        r"\bchin ?up\b",
        r"\bpress\b",
        r"\boverhead press\b",
        r"\blunge\b",
        r"\bsplit squat\b",
    )
)
HIGH_PROGRESSION_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\btry to add (a little )?weight each week\b",
        r"\badd (a little )?weight each week\b",
        r"\bkeep a logbook\b",
    )
)
LOW_PROGRESSION_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bmechanical dropset\b",
        r"\blong length partials?\b",
        r"\bpartials?\b",
        r"\bprogressively increase the rom week to week\b",
    )
)
_WEAK_POINT_PLACEHOLDER_RE = re.compile(r"^weak_point_exercise", re.IGNORECASE)


@dataclass(frozen=True)
class LocalExerciseEvidence:
    exercise_id: str
    source_program_id: str
    source: SourceEnvelope
    movement_pattern: str
    equipment_tags: tuple[str, ...]
    slot_roles: tuple[str, ...]
    day_roles: tuple[str, ...]
    max_work_sets: int
    normalized_text: str
    descriptor_text: str


@dataclass(frozen=True)
class LocalRuleOutcome:
    value: str
    evidence_type: str
    local_rule_id: str
    excerpt_quality: float


@dataclass(frozen=True)
class ExerciseIntelligenceExtractionResult:
    reachable_exercise_ids: tuple[str, ...]
    extracted_claims: tuple[ClaimCandidate, ...]
    resolved_claims: tuple[ResolvedClaim, ...]
    unresolved_conflicts: tuple[UnresolvedConflict, ...]
    metadata_by_exercise_id: dict[str, dict[str, Any]]
    input_signature_parts: tuple[str, ...]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _safe_relative(path: Path, root: Path = REPO_ROOT) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _claim_digest(*, source_id: str, exercise_id: str, field_name: str, value: str, local_rule_id: str) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "source_id": source_id,
                "exercise_id": exercise_id,
                "field_name": field_name,
                "value": value,
                "local_rule_id": local_rule_id,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:12]


def _is_placeholder_exercise(entry: dict[str, Any]) -> bool:
    exercise_id = str(entry.get("exercise_id") or "").strip()
    canonical_name = str(entry.get("canonical_name") or "").strip()
    return bool(_WEAK_POINT_PLACEHOLDER_RE.search(exercise_id) or _WEAK_POINT_PLACEHOLDER_RE.search(canonical_name))


def _iter_allowed_onboarding_paths(onboarding_dir: Path) -> tuple[Path, ...]:
    paths = tuple(onboarding_dir / file_name for file_name in ALLOWED_ONBOARDING_FILENAMES)
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        joined = ", ".join(sorted(missing))
        raise ValueError(f"missing required onboarding packages for exercise extraction: {joined}")
    return paths


def _resolve_allowed_source(
    *,
    program_id: str,
    source_registry_bundle: SourceRegistryBundle,
) -> SourceEnvelope:
    family_id = PROGRAM_ID_TO_FAMILY.get(program_id)
    if family_id is None:
        raise ValueError(f"program_id is out of scope for exercise extraction: {program_id}")
    matches = [
        entry
        for entry in source_registry_bundle.entries
        if entry.program_family == family_id
        and entry.source_kind == "authored_program_workbook"
        and "full_body" in entry.split_scope
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one authored workbook source for {program_id}, found {len(matches)}")
    entry = matches[0]
    return SourceEnvelope(
        source_id=entry.source_id,
        source_family_id=family_id,
        source_path=entry.source_path,
        source_kind=entry.source_kind,
        split_scope=tuple(entry.split_scope),
        authority_weight=float(entry.authority_weight),
        classification_confidence=float(entry.classification_confidence),
        program_id=program_id,
    )


def _current_compiled_signature_parts(compiled_dir: Path) -> tuple[str, ...]:
    paths = (
        compiled_dir / "exercise_library.foundation.v1.json",
        compiled_dir / "doctrine_bundles" / "multi_source_hypertrophy_v1.bundle.json",
        compiled_dir / "policy_bundles" / "system_coaching_policy_v1.bundle.json",
    )
    return tuple(_sha256_text(path.read_text(encoding="utf-8")) for path in paths)


def compute_reachable_generated_full_body_candidate_set(
    *,
    compiled_dir: Path | None = None,
) -> tuple[str, ...]:
    resolved_compiled_dir = (compiled_dir or (REPO_ROOT / "knowledge" / "compiled")).resolve()
    doctrine_bundle = load_doctrine_bundle("multi_source_hypertrophy_v1", base_dir=resolved_compiled_dir)
    policy_bundle = load_policy_bundle("system_coaching_policy_v1", base_dir=resolved_compiled_dir)
    exercise_library_bundle = load_exercise_library(base_dir=resolved_compiled_dir)

    reachable: set[str] = set()
    for fixture in get_generated_full_body_archetypes().values():
        assessment = build_user_assessment(
            profile_input=ProfileAssessmentInput.model_validate(fixture["profile_input"]),
            training_state=fixture["training_state"],
            doctrine_bundle=doctrine_bundle,
            policy_bundle=policy_bundle,
        )
        blueprint_input = build_generated_full_body_blueprint_input(
            assessment=assessment,
            doctrine_bundle=doctrine_bundle,
            policy_bundle=policy_bundle,
            exercise_library=exercise_library_bundle,
        )
        for exercise_ids in blueprint_input.candidate_exercise_ids_by_pattern.values():
            reachable.update(exercise_ids)
        for exercise_ids in blueprint_input.weak_point_candidate_exercise_ids_by_muscle.values():
            reachable.update(exercise_ids)
    return tuple(sorted(reachable))


def _build_slot_usage_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    exercise_entry_by_id = {
        str(entry["exercise_id"]): entry
        for entry in list(payload.get("exercise_library") or [])
        if not _is_placeholder_exercise(entry)
    }
    slot_usage_index: dict[str, dict[str, Any]] = {
        exercise_id: {
            "slot_roles": set(),
            "day_roles": set(),
            "max_work_sets": 0,
            "text_parts": [
                str(entry.get("execution") or ""),
                " ".join(str(item) for item in list(entry.get("coaching_cues") or [])),
                str(entry.get("slot_usage_rationale") or ""),
            ],
        }
        for exercise_id, entry in exercise_entry_by_id.items()
    }

    week_templates = list(((payload.get("blueprint") or {}).get("week_templates") or []))
    for week_template in week_templates:
        for day in list(week_template.get("days") or []):
            raw_day_role = str(day.get("day_role") or "")
            try:
                normalized_day_role, _, _ = normalize_day_role(raw_day_role)
            except ValueError:
                continue
            for slot in list(day.get("slots") or []):
                exercise_id = str(slot.get("exercise_id") or "")
                if exercise_id not in slot_usage_index:
                    continue
                raw_slot_role = str(slot.get("slot_role") or "")
                try:
                    normalized_slot_role, _, _ = normalize_slot_role(raw_slot_role)
                except ValueError:
                    continue
                usage = slot_usage_index[exercise_id]
                usage["slot_roles"].add(normalized_slot_role)
                usage["day_roles"].add(normalized_day_role)
                max_sets = max(
                    (
                        int(item.get("sets") or 0)
                        for item in list(slot.get("work_sets") or [])
                    ),
                    default=0,
                )
                usage["max_work_sets"] = max(int(usage["max_work_sets"]), max_sets)
                usage["text_parts"].extend(
                    [
                        str(slot.get("notes") or ""),
                        str(slot.get("last_set_intensity_technique") or ""),
                    ]
                )
    return slot_usage_index


def _matches_any(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _has_low_demand_slot_usage(evidence: LocalExerciseEvidence) -> bool:
    slot_roles = set(evidence.slot_roles)
    return bool(slot_roles) and slot_roles.issubset(LOW_DEMAND_SLOT_ROLES)


def _has_support_assistive_equipment(evidence: LocalExerciseEvidence) -> bool:
    return bool(set(evidence.equipment_tags).intersection(SUPPORT_ASSISTIVE_EQUIPMENT_TAGS))


def _has_unilateral_or_unsupported_context(evidence: LocalExerciseEvidence) -> bool:
    return _matches_any(UNILATERAL_OR_UNSUPPORTED_PATTERNS, evidence.descriptor_text)


def _has_supported_accessory_context(evidence: LocalExerciseEvidence) -> bool:
    return _matches_any(SUPPORTED_ACCESSORY_PATTERNS, evidence.descriptor_text)


def _has_compound_role_fallback_context(evidence: LocalExerciseEvidence) -> bool:
    return _matches_any(COMPOUND_ROLE_FALLBACK_PATTERNS, evidence.descriptor_text)


def _evaluate_field_outcome(
    *,
    field_name: str,
    evidence: LocalExerciseEvidence,
) -> LocalRuleOutcome | None:
    slot_roles = set(evidence.slot_roles)
    equipment_tags = set(evidence.equipment_tags)
    machine_only = bool(equipment_tags) and equipment_tags.issubset({"machine"})
    freeweight_or_bodyweight = bool(equipment_tags.intersection(FREEWEIGHT_EQUIPMENT_TAGS))
    compound_pattern = evidence.movement_pattern in COMPOUND_MOVEMENT_PATTERNS
    compound_role_fallback = _has_compound_role_fallback_context(evidence)
    primary_compound_used = "primary_compound" in slot_roles
    compound_used = bool(slot_roles.intersection({"primary_compound", "secondary_compound"}))
    isolation_only = bool(slot_roles) and slot_roles.issubset({"accessory", "isolation"})
    low_demand_slot_usage = _has_low_demand_slot_usage(evidence)
    unilateral_or_unsupported = _has_unilateral_or_unsupported_context(evidence)
    supported_accessory_context = _has_supported_accessory_context(evidence)
    supported_accessory = low_demand_slot_usage and (
        _has_support_assistive_equipment(evidence) or supported_accessory_context
    )
    unsupported_accessory = low_demand_slot_usage and (
        unilateral_or_unsupported
        or (
            freeweight_or_bodyweight
            and not supported_accessory_context
            and not _has_support_assistive_equipment(evidence)
        )
    )
    compound_like = (compound_used and compound_pattern) or compound_role_fallback
    max_work_sets = int(evidence.max_work_sets)
    text = evidence.normalized_text

    if field_name == "fatigue_cost":
        if _matches_any(HIGH_FATIGUE_PATTERNS, text):
            return LocalRuleOutcome("high", "regex", "fatigue_high_regex", 0.90)
        if primary_compound_used and evidence.movement_pattern in {"squat", "hinge"} and max_work_sets >= 3:
            return LocalRuleOutcome("high", "structured", "fatigue_high_primary_compound_sets", 1.00)
        if compound_used and compound_pattern:
            return LocalRuleOutcome("moderate", "structured", "fatigue_moderate_compound_pattern", 1.00)
        if isolation_only and max_work_sets <= 3:
            return LocalRuleOutcome("low", "structured", "fatigue_low_isolation_only", 1.00)
        return None

    if field_name == "skill_demand":
        if _matches_any(HIGH_SKILL_PATTERNS, text):
            return LocalRuleOutcome("high", "regex", "skill_high_regex", 0.90)
        if low_demand_slot_usage and unsupported_accessory:
            return LocalRuleOutcome(
                "moderate",
                "regex",
                "skill_moderate_unilateral_or_unsupported_accessory_regex",
                0.90,
            )
        if supported_accessory:
            return LocalRuleOutcome(
                "low",
                "structured",
                "skill_low_supported_accessory_or_isolation_local",
                1.00,
            )
        if low_demand_slot_usage and supported_accessory_context:
            return LocalRuleOutcome(
                "low",
                "regex",
                "skill_low_supported_accessory_regex",
                0.90,
            )
        if machine_only and isolation_only:
            return LocalRuleOutcome("low", "structured", "skill_low_machine_isolation", 1.00)
        if (
            freeweight_or_bodyweight
            and compound_like
            and not low_demand_slot_usage
            and unilateral_or_unsupported
            and not supported_accessory_context
        ):
            return LocalRuleOutcome("high", "structured", "skill_high_unilateral_or_unsupported_compound_local", 1.00)
        if (
            freeweight_or_bodyweight
            and compound_like
            and not low_demand_slot_usage
            and not supported_accessory_context
        ):
            return LocalRuleOutcome("high", "structured", "skill_high_freeweight_compound_local", 1.00)
        if compound_like:
            return LocalRuleOutcome(
                "moderate",
                "structured",
                "skill_moderate_compound_role_fallback",
                1.00,
            )
        return None

    if field_name == "stability_demand":
        if _matches_any(HIGH_STABILITY_PATTERNS, text):
            return LocalRuleOutcome("high", "regex", "stability_high_regex", 0.90)
        if _matches_any(MODERATE_STABILITY_PATTERNS, text):
            return LocalRuleOutcome("moderate", "regex", "stability_moderate_regex", 0.90)
        if (
            freeweight_or_bodyweight
            and compound_like
            and not low_demand_slot_usage
            and unilateral_or_unsupported
            and not supported_accessory_context
        ):
            return LocalRuleOutcome("high", "structured", "stability_high_unilateral_or_unsupported_compound_local", 1.00)
        if (
            freeweight_or_bodyweight
            and compound_like
            and not low_demand_slot_usage
            and not supported_accessory_context
        ):
            return LocalRuleOutcome("high", "structured", "stability_high_freeweight_compound_local", 1.00)
        if low_demand_slot_usage and unsupported_accessory:
            return LocalRuleOutcome(
                "moderate",
                "regex",
                "stability_moderate_unilateral_or_unsupported_accessory_regex",
                0.90,
            )
        if supported_accessory:
            return LocalRuleOutcome(
                "low",
                "structured",
                "stability_low_supported_accessory_or_isolation_local",
                1.00,
            )
        if low_demand_slot_usage and supported_accessory_context:
            return LocalRuleOutcome(
                "low",
                "regex",
                "stability_low_supported_accessory_regex",
                0.90,
            )
        if machine_only:
            return LocalRuleOutcome("low", "structured", "stability_low_machine_only", 1.00)
        if freeweight_or_bodyweight and compound_like:
            return LocalRuleOutcome("moderate", "structured", "stability_moderate_freeweight_compound", 1.00)
        if compound_like:
            return LocalRuleOutcome(
                "moderate",
                "structured",
                "stability_moderate_compound_role_fallback",
                1.00,
            )
        return None

    if field_name == "progression_compatibility":
        if _matches_any(LOW_PROGRESSION_PATTERNS, text):
            return LocalRuleOutcome("low", "regex", "progression_low_regex", 0.90)
        if _matches_any(HIGH_PROGRESSION_PATTERNS, text):
            return LocalRuleOutcome("high", "regex", "progression_high_regex", 0.90)
        if compound_used and max_work_sets >= 2:
            return LocalRuleOutcome("moderate", "structured", "progression_moderate_compound_sets", 1.00)
        return None

    raise ValueError(f"unsupported field_name={field_name}")


def _build_claim(
    *,
    evidence: LocalExerciseEvidence,
    field_name: str,
    outcome: LocalRuleOutcome,
) -> ClaimCandidate:
    return ClaimCandidate(
        claim_key=f"exercise:{evidence.exercise_id}:{field_name}",
        target_type="exercise_field",
        target_id=evidence.exercise_id,
        payload_path=field_name,
        normalized_value=outcome.value,
        scope={
            "split_scope": "full_body",
            "source_program_id": evidence.source_program_id,
            "source_path": evidence.source.source_path,
            "evidence_type": outcome.evidence_type,
            "local_rule_id": outcome.local_rule_id,
        },
        normalization_method="direct_enum_mapping",
        normalization_confidence=1.0,
        evidence_fragment_id=_claim_digest(
            source_id=evidence.source.source_id,
            exercise_id=evidence.exercise_id,
            field_name=field_name,
            value=outcome.value,
            local_rule_id=outcome.local_rule_id,
        ),
        source_id=evidence.source.source_id,
        source_family_id=evidence.source.source_family_id,
        authority_weight=evidence.source.authority_weight,
        classification_confidence=evidence.source.classification_confidence,
        excerpt_quality=outcome.excerpt_quality,
    )


def _build_local_evidence_by_exercise_id(
    *,
    payload: dict[str, Any],
    source: SourceEnvelope,
    current_compiled_exercise_library: CanonicalExerciseLibraryBundle,
    reachable_exercise_ids: set[str],
) -> dict[str, LocalExerciseEvidence]:
    exercise_entry_by_id = {
        str(entry["exercise_id"]): entry
        for entry in list(payload.get("exercise_library") or [])
        if not _is_placeholder_exercise(entry)
    }
    slot_usage_index = _build_slot_usage_index(payload)
    evidence_by_exercise_id: dict[str, LocalExerciseEvidence] = {}
    for exercise_id in sorted(set(exercise_entry_by_id).intersection(reachable_exercise_ids)):
        movement_pattern, _, _ = normalize_movement_pattern(
            exercise_id=exercise_id,
            exercise_library_bundle=current_compiled_exercise_library,
        )
        exercise_entry = exercise_entry_by_id[exercise_id]
        usage = slot_usage_index.get(exercise_id) or {
            "slot_roles": set(),
            "day_roles": set(),
            "max_work_sets": 0,
            "text_parts": [],
        }
        evidence_by_exercise_id[exercise_id] = LocalExerciseEvidence(
            exercise_id=exercise_id,
            source_program_id=source.program_id,
            source=source,
            movement_pattern=movement_pattern,
            equipment_tags=tuple(sorted(str(tag) for tag in list(exercise_entry.get("equipment_tags") or []))),
            slot_roles=tuple(sorted(str(role) for role in usage["slot_roles"])),
            day_roles=tuple(sorted(str(role) for role in usage["day_roles"])),
            max_work_sets=int(usage["max_work_sets"]),
            normalized_text=normalize_ascii_text(" ".join(str(item) for item in usage["text_parts"] if item)),
            descriptor_text=normalize_ascii_text(
                " ".join(
                    [
                        str(exercise_entry.get("canonical_name") or ""),
                        " ".join(str(alias) for alias in list(exercise_entry.get("aliases") or [])),
                        " ".join(str(item) for item in usage["text_parts"] if item),
                    ]
                )
            ),
        )
    return evidence_by_exercise_id


def extract_exercise_intelligence_claims(
    *,
    onboarding_dir: Path,
    source_registry_bundle: SourceRegistryBundle,
    current_compiled_exercise_library: CanonicalExerciseLibraryBundle,
    reachable_exercise_ids: tuple[str, ...],
) -> tuple[ClaimCandidate, ...]:
    reachable_lookup = set(reachable_exercise_ids)
    claims: list[ClaimCandidate] = []
    for onboarding_path in _iter_allowed_onboarding_paths(onboarding_dir):
        payload = json.loads(onboarding_path.read_text(encoding="utf-8"))
        source = _resolve_allowed_source(
            program_id=str(payload.get("program_id") or ""),
            source_registry_bundle=source_registry_bundle,
        )
        evidence_by_exercise_id = _build_local_evidence_by_exercise_id(
            payload=payload,
            source=source,
            current_compiled_exercise_library=current_compiled_exercise_library,
            reachable_exercise_ids=reachable_lookup,
        )
        for exercise_id in sorted(evidence_by_exercise_id):
            evidence = evidence_by_exercise_id[exercise_id]
            for field_name in ("fatigue_cost", "skill_demand", "stability_demand", "progression_compatibility"):
                outcome = _evaluate_field_outcome(field_name=field_name, evidence=evidence)
                if outcome is None:
                    continue
                claims.append(
                    _build_claim(
                        evidence=evidence,
                        field_name=field_name,
                        outcome=outcome,
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


def resolve_exercise_intelligence_claims(
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
        field_name = claim_key.rsplit(":", 1)[-1]
        threshold = FIELD_THRESHOLDS[field_name]
        winner = select_cluster_winner(
            cluster=clusters[claim_key],
            threshold=threshold,
            resolutions=resolutions,
        )
        if isinstance(winner, ResolvedClaim):
            resolved.append(winner)
        else:
            unresolved.append(winner)

    write_unresolved_conflicts(
        path=unresolved_path,
        bundle_id=EXTRACTION_BUNDLE_ID,
        conflicts=unresolved,
    )
    return tuple(resolved), tuple(unresolved)


def _resolved_claims_to_metadata_map(resolved_claims: tuple[ResolvedClaim, ...]) -> dict[str, dict[str, Any]]:
    metadata_by_exercise_id: dict[str, dict[str, Any]] = {}
    for claim in resolved_claims:
        _, exercise_id, field_name = claim.claim_key.split(":", 2)
        metadata_by_exercise_id.setdefault(exercise_id, {})[field_name] = claim.chosen_value
    return metadata_by_exercise_id


def build_exercise_intelligence_extraction_result(
    *,
    onboarding_dir: Path,
    source_registry_bundle: SourceRegistryBundle,
    current_compiled_dir: Path | None,
    resolutions_path: Path | None,
    unresolved_path: Path,
) -> ExerciseIntelligenceExtractionResult:
    resolved_compiled_dir = (current_compiled_dir or (REPO_ROOT / "knowledge" / "compiled")).resolve()
    current_compiled_exercise_library = load_exercise_library(base_dir=resolved_compiled_dir)
    reachable_exercise_ids = compute_reachable_generated_full_body_candidate_set(compiled_dir=resolved_compiled_dir)
    extracted_claims = extract_exercise_intelligence_claims(
        onboarding_dir=onboarding_dir,
        source_registry_bundle=source_registry_bundle,
        current_compiled_exercise_library=current_compiled_exercise_library,
        reachable_exercise_ids=reachable_exercise_ids,
    )
    resolved_claims, unresolved_conflicts = resolve_exercise_intelligence_claims(
        claims=extracted_claims,
        resolutions_path=resolutions_path,
        unresolved_path=unresolved_path,
    )
    resolution_signature = (
        _sha256_text(resolutions_path.read_text(encoding="utf-8"))
        if resolutions_path is not None and resolutions_path.exists()
        else "no_resolutions"
    )
    return ExerciseIntelligenceExtractionResult(
        reachable_exercise_ids=reachable_exercise_ids,
        extracted_claims=extracted_claims,
        resolved_claims=resolved_claims,
        unresolved_conflicts=unresolved_conflicts,
        metadata_by_exercise_id=_resolved_claims_to_metadata_map(resolved_claims),
        input_signature_parts=_current_compiled_signature_parts(resolved_compiled_dir) + (resolution_signature,),
    )


def _build_extracted_provenance(
    *,
    record: CanonicalExerciseRecord,
    field_name: str,
    claim: ResolvedClaim,
) -> list[ProvenanceRef]:
    provenance_refs: list[ProvenanceRef] = []
    seen_entries: set[tuple[str, str, str]] = set()
    for supporting_claim in sorted(
        claim.supporting_claims,
        key=lambda item: (item.source_family_id, item.source_id, item.scope.get("local_rule_id", "")),
    ):
        note = (
            f"field={field_name}; value={claim.chosen_value}; "
            f"source_program_id={supporting_claim.scope.get('source_program_id')}; "
            f"evidence_type={supporting_claim.scope.get('evidence_type')}; "
            f"rule={supporting_claim.scope.get('local_rule_id')}; "
            f"resolution_basis={claim.resolution_basis}"
        )
        key = (
            supporting_claim.source_id,
            f"exercise_intelligence_extraction:{record.exercise_id}:{field_name}",
            note,
        )
        if key in seen_entries:
            continue
        seen_entries.add(key)
        provenance_refs.append(
            ProvenanceRef(
                source_id=supporting_claim.source_id,
                source_path=str(supporting_claim.scope.get("source_path") or ""),
                section_ref=f"exercise_intelligence_extraction:{record.exercise_id}:{field_name}",
                confidence=claim.confidence,
                curation_status="curated",
                note=note,
            )
        )
    return provenance_refs


def apply_exercise_intelligence_metadata(
    *,
    records: list[CanonicalExerciseRecord],
    resolved_claims: tuple[ResolvedClaim, ...],
) -> list[CanonicalExerciseRecord]:
    claims_by_exercise_id: dict[str, dict[str, ResolvedClaim]] = {}
    for claim in resolved_claims:
        _, exercise_id, field_name = claim.claim_key.split(":", 2)
        claims_by_exercise_id.setdefault(exercise_id, {})[field_name] = claim

    updated_records: list[CanonicalExerciseRecord] = []
    for record in records:
        record_claims = claims_by_exercise_id.get(record.exercise_id)
        if not record_claims:
            updated_records.append(record)
            continue
        payload = record.model_dump(mode="json")
        provenance = list(record.provenance)
        record_confidence = float(record.confidence)
        for field_name in sorted(record_claims):
            claim = record_claims[field_name]
            if field_name == "progression_compatibility":
                payload[field_name] = [str(claim.chosen_value)]
            else:
                payload[field_name] = str(claim.chosen_value)
            provenance.extend(
                _build_extracted_provenance(
                    record=record,
                    field_name=field_name,
                    claim=claim,
                )
            )
            record_confidence = max(record_confidence, float(claim.confidence))
        payload["provenance"] = [item.model_dump(mode="json") for item in provenance]
        payload["confidence"] = record_confidence
        payload["curation_status"] = "curated"
        updated_records.append(CanonicalExerciseRecord.model_validate(payload))
    return updated_records
