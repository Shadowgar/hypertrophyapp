#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable

from app.knowledge_schema import CanonicalExerciseLibraryBundle, SourceRegistryBundle


REPO_ROOT = Path(__file__).resolve().parents[1]

_MOVEMENT_PATTERN_MAP = {
    "bench_press": "horizontal_press",
    "chin_up": "vertical_pull",
    "horizontal_press": "horizontal_press",
    "horizontal_pull": "horizontal_pull",
    "hip_hinge": "hinge",
    "hinge": "hinge",
    "lat_pulldown": "vertical_pull",
    "overhead_press": "vertical_press",
    "pull_up": "vertical_pull",
    "push_up": "horizontal_press",
    "quad_dominant": "squat",
    "row": "horizontal_pull",
    "squat": "squat",
    "vertical_press": "vertical_press",
    "vertical_pull": "vertical_pull",
}
_DAY_ROLE_MAP = {
    "full body #1": "full_body_1",
    "full body #2": "full_body_2",
    "full body #3": "full_body_3",
    "full body #4": "full_body_4",
    "full body #5": "full_body_5",
    "full_body_1": "full_body_1",
    "full_body_2": "full_body_2",
    "full_body_3": "full_body_3",
    "full_body_4": "full_body_4",
    "full_body_5": "full_body_5",
}
_SLOT_ROLE_MAP = {
    "accessory": "accessory",
    "isolation": "isolation",
    "primary compound": "primary_compound",
    "primary_compound": "primary_compound",
    "secondary compound": "secondary_compound",
    "secondary_compound": "secondary_compound",
    "weak point": "weak_point",
    "weak_point": "weak_point",
}


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "value"


def _safe_relative(path: Path, root: Path = REPO_ROOT) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


@dataclass(frozen=True)
class SourceEnvelope:
    source_id: str
    source_family_id: str
    source_path: str
    source_kind: str
    split_scope: tuple[str, ...]
    authority_weight: float
    classification_confidence: float
    program_id: str


@dataclass(frozen=True)
class NormalizedBlock:
    block_id: str
    section_ref: str
    content_type: str
    raw_text: str
    normalized_text: str
    structured_fields: dict[str, Any]
    parent_block_id: str | None = None


@dataclass(frozen=True)
class NormalizedDocument:
    source: SourceEnvelope
    document_type: str
    blocks: tuple[NormalizedBlock, ...]


@dataclass(frozen=True)
class ClaimCandidate:
    claim_key: str
    target_type: str
    target_id: str
    payload_path: str
    normalized_value: Any
    scope: dict[str, Any]
    normalization_method: str
    normalization_confidence: float
    evidence_fragment_id: str
    source_id: str
    source_family_id: str
    authority_weight: float
    classification_confidence: float
    excerpt_quality: float


@dataclass(frozen=True)
class CandidateBucket:
    fingerprint: str
    normalized_value: Any
    claims: tuple[ClaimCandidate, ...]


@dataclass(frozen=True)
class ClaimCluster:
    claim_key: str
    buckets: tuple[CandidateBucket, ...]


@dataclass(frozen=True)
class ResolvedClaim:
    claim_key: str
    chosen_value: Any
    confidence: float
    resolution_basis: str
    supporting_claims: tuple[ClaimCandidate, ...]

    @classmethod
    def from_manual_resolution(
        cls,
        cluster: ClaimCluster,
        resolution: "DoctrineResolutionEntry",
    ) -> "ResolvedClaim":
        matching_claims: list[ClaimCandidate] = []
        target_fingerprint = value_fingerprint(resolution.chosen_value)
        for bucket in cluster.buckets:
            if bucket.fingerprint == target_fingerprint:
                matching_claims.extend(bucket.claims)
        return cls(
            claim_key=cluster.claim_key,
            chosen_value=resolution.chosen_value,
            confidence=1.0,
            resolution_basis="manual_curation",
            supporting_claims=tuple(matching_claims),
        )


@dataclass(frozen=True)
class UnresolvedConflict:
    claim_key: str
    candidate_set_hash: str
    reason: str
    candidates: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class DoctrineResolutionEntry:
    claim_key: str
    candidate_set_hash: str
    action: str
    chosen_value: Any
    resolution_basis: str
    supporting_source_ids: tuple[str, ...]
    curation_status: str


def build_source_family_id(source_path: str) -> str:
    stem = Path(source_path).stem
    return _slugify(stem)


def resolve_source_envelope_from_program_json(
    *,
    program_path: Path,
    source_registry_bundle: SourceRegistryBundle,
) -> tuple[SourceEnvelope, dict[str, Any]]:
    payload = json.loads(program_path.read_text(encoding="utf-8"))
    program_id = str(payload.get("program_id") or program_path.stem)
    source_workbook = str(payload.get("source_workbook") or "").strip()
    relative_source_path = _safe_relative(Path(source_workbook), REPO_ROOT) if source_workbook else ""
    basename = Path(relative_source_path or source_workbook or program_path.name).name
    registry_entries = list(source_registry_bundle.entries)

    exact_match = next((entry for entry in registry_entries if entry.source_path == relative_source_path), None)
    basename_match = next(
        (entry for entry in registry_entries if Path(entry.source_path).name == basename and "full_body" in entry.split_scope),
        None,
    )
    program_family_match = None
    lowered_program_id = program_id.lower()
    if "phase_1" in lowered_program_id or "phase-1" in lowered_program_id:
        program_family_match = next(
            (
                entry
                for entry in registry_entries
                if entry.program_family == "pure_bodybuilding_phase_1"
                and entry.source_kind == "authored_program_workbook"
                and "full_body" in entry.split_scope
            ),
            None,
        )
    elif "phase_2" in lowered_program_id or "phase-2" in lowered_program_id:
        program_family_match = next(
            (
                entry
                for entry in registry_entries
                if entry.program_family == "pure_bodybuilding_phase_2"
                and entry.source_kind == "authored_program_workbook"
                and "full_body" in entry.split_scope
            ),
            None,
        )

    matched_entry = exact_match or basename_match or program_family_match
    resolved_source_path = relative_source_path or _safe_relative(program_path, REPO_ROOT)
    source_family_id = build_source_family_id(relative_source_path or basename or program_id)
    if matched_entry is not None and matched_entry.program_family:
        source_family_id = str(matched_entry.program_family)

    envelope = SourceEnvelope(
        source_id=str(matched_entry.source_id) if matched_entry is not None else program_id,
        source_family_id=source_family_id,
        source_path=str(matched_entry.source_path) if matched_entry is not None else resolved_source_path,
        source_kind=str(matched_entry.source_kind) if matched_entry is not None else "authored_program_workbook",
        split_scope=tuple(matched_entry.split_scope) if matched_entry is not None else ("full_body",),
        authority_weight=float(matched_entry.authority_weight) if matched_entry is not None else 1.0,
        classification_confidence=float(matched_entry.classification_confidence) if matched_entry is not None else 1.0,
        program_id=program_id,
    )
    return envelope, payload


def load_structured_program_document(
    *,
    program_path: Path,
    source_registry_bundle: SourceRegistryBundle,
) -> NormalizedDocument:
    source, payload = resolve_source_envelope_from_program_json(
        program_path=program_path,
        source_registry_bundle=source_registry_bundle,
    )

    blocks: list[NormalizedBlock] = []
    phases = list(payload.get("phases") or [])
    for phase_index, phase in enumerate(phases, start=1):
        phase_id = str(phase.get("phase_id") or f"phase_{phase_index}")
        phase_block_id = f"phase:{phase_id}"
        blocks.append(
            NormalizedBlock(
                block_id=phase_block_id,
                section_ref=f"program:{source.program_id}/phase:{phase_id}",
                content_type="heading",
                raw_text=str(phase.get("phase_name") or phase_id),
                normalized_text=_normalize_token(str(phase.get("phase_name") or phase_id)),
                structured_fields={
                    "program_id": source.program_id,
                    "phase_id": phase_id,
                    "phase_name": str(phase.get("phase_name") or phase_id),
                },
            )
        )
        for week in list(phase.get("weeks") or []):
            week_index = int(week.get("week_index") or 0)
            week_block_id = f"{phase_block_id}/week:{week_index}"
            blocks.append(
                NormalizedBlock(
                    block_id=week_block_id,
                    section_ref=f"program:{source.program_id}/phase:{phase_id}/week:{week_index}",
                    content_type="heading",
                    raw_text=str(week.get("week_role") or f"week_{week_index}"),
                    normalized_text=_normalize_token(str(week.get("week_role") or f"week_{week_index}")),
                    structured_fields={
                        "program_id": source.program_id,
                        "phase_id": phase_id,
                        "week_index": week_index,
                        "week_role": str(week.get("week_role") or ""),
                    },
                    parent_block_id=phase_block_id,
                )
            )
            for day in list(week.get("days") or []):
                day_id = str(day.get("day_id") or "")
                day_role = str(day.get("day_role") or "")
                day_block_id = f"{week_block_id}/day:{day_id}"
                blocks.append(
                    NormalizedBlock(
                        block_id=day_block_id,
                        section_ref=f"program:{source.program_id}/phase:{phase_id}/week:{week_index}/day:{day_id}",
                        content_type="heading",
                        raw_text=str(day.get("day_name") or day_id),
                        normalized_text=_normalize_token(str(day.get("day_name") or day_id)),
                        structured_fields={
                            "program_id": source.program_id,
                            "phase_id": phase_id,
                            "week_index": week_index,
                            "week_role": str(week.get("week_role") or ""),
                            "day_id": day_id,
                            "day_name": str(day.get("day_name") or day_id),
                            "day_role": day_role,
                        },
                        parent_block_id=week_block_id,
                    )
                )
                for slot in list(day.get("slots") or []):
                    slot_id = str(slot.get("slot_id") or "")
                    exercise_id = str(slot.get("exercise_id") or "")
                    slot_role = str(slot.get("slot_role") or "")
                    blocks.append(
                        NormalizedBlock(
                            block_id=f"{day_block_id}/slot:{slot_id}",
                            section_ref=f"program:{source.program_id}/phase:{phase_id}/week:{week_index}/day:{day_id}/slot:{slot_id}",
                            content_type="row_group",
                            raw_text=json.dumps(slot, sort_keys=True),
                            normalized_text=_normalize_token(
                                " ".join(
                                    item
                                    for item in [
                                        exercise_id,
                                        slot_role,
                                        day_role,
                                        str(slot.get("exercise_name") or ""),
                                    ]
                                    if item
                                )
                            ),
                            structured_fields={
                                "program_id": source.program_id,
                                "phase_id": phase_id,
                                "week_index": week_index,
                                "week_role": str(week.get("week_role") or ""),
                                "day_id": day_id,
                                "day_name": str(day.get("day_name") or day_id),
                                "day_role": day_role,
                                "slot_id": slot_id,
                                "exercise_id": exercise_id,
                                "order_index": int(slot.get("order_index") or 0),
                                "slot_role": slot_role,
                            },
                            parent_block_id=day_block_id,
                        )
                    )

    return NormalizedDocument(
        source=source,
        document_type="structured_program_json",
        blocks=tuple(blocks),
    )


def normalize_movement_pattern(
    *,
    raw_value: str | None = None,
    exercise_id: str | None = None,
    exercise_library_bundle: CanonicalExerciseLibraryBundle,
) -> tuple[str, float, str]:
    exercise_lookup = {record.exercise_id: record for record in exercise_library_bundle.records}
    if exercise_id:
        record = exercise_lookup.get(exercise_id)
        if record is None or not record.movement_pattern:
            raise ValueError(f"unable to normalize movement_pattern for unknown exercise_id={exercise_id}")
        return str(record.movement_pattern), 1.0, "exercise_library_lookup"

    normalized = _normalize_token(str(raw_value or ""))
    mapped = _MOVEMENT_PATTERN_MAP.get(normalized)
    if mapped:
        return mapped, 0.9, "lookup_table"
    raise ValueError(f"unable to normalize movement_pattern from raw_value={raw_value!r}")


def normalize_day_role(raw_value: str) -> tuple[str, float, str]:
    normalized = _normalize_token(raw_value)
    mapped = _DAY_ROLE_MAP.get(raw_value.strip().lower()) or _DAY_ROLE_MAP.get(normalized)
    if mapped:
        confidence = 1.0 if mapped == raw_value else 0.9
        method = "identity" if confidence == 1.0 else "lookup_table"
        return mapped, confidence, method
    raise ValueError(f"unable to normalize day_role={raw_value!r}")


def normalize_slot_role(raw_value: str) -> tuple[str, float, str]:
    normalized = _normalize_token(raw_value)
    mapped = _SLOT_ROLE_MAP.get(raw_value.strip().lower()) or _SLOT_ROLE_MAP.get(normalized)
    if mapped:
        confidence = 1.0 if mapped == raw_value else 0.9
        method = "identity" if confidence == 1.0 else "lookup_table"
        return mapped, confidence, method
    raise ValueError(f"unable to normalize slot_role={raw_value!r}")


def value_fingerprint(value: Any) -> str:
    return _sha256_text(json.dumps(value, sort_keys=True))


def cluster_claims(claims: list[ClaimCandidate]) -> dict[str, ClaimCluster]:
    grouped: dict[str, dict[str, list[ClaimCandidate]]] = {}
    for claim in claims:
        grouped.setdefault(claim.claim_key, {}).setdefault(value_fingerprint(claim.normalized_value), []).append(claim)

    clusters: dict[str, ClaimCluster] = {}
    for claim_key, bucket_map in grouped.items():
        buckets = tuple(
            CandidateBucket(
                fingerprint=fingerprint,
                normalized_value=claims_for_bucket[0].normalized_value,
                claims=tuple(
                    sorted(
                        claims_for_bucket,
                        key=lambda item: (
                            item.source_family_id,
                            item.source_id,
                            item.evidence_fragment_id,
                        ),
                    )
                ),
            )
            for fingerprint, claims_for_bucket in sorted(bucket_map.items())
        )
        clusters[claim_key] = ClaimCluster(claim_key=claim_key, buckets=buckets)
    return clusters


def evidence_confidence(claim: ClaimCandidate) -> float:
    return round(
        claim.authority_weight
        * claim.classification_confidence
        * claim.excerpt_quality
        * claim.normalization_confidence,
        2,
    )


def family_count(bucket: CandidateBucket) -> int:
    return len({claim.source_family_id for claim in bucket.claims})


def score_candidate_bucket(bucket: CandidateBucket) -> float:
    best_by_family: dict[str, float] = {}
    weight_by_family: dict[str, float] = {}
    for claim in bucket.claims:
        score = evidence_confidence(claim)
        family = claim.source_family_id
        if family not in best_by_family or score > best_by_family[family]:
            best_by_family[family] = score
            weight_by_family[family] = claim.authority_weight

    if not best_by_family:
        return 0.0

    weighted_sum = sum(best_by_family[family] * weight_by_family[family] for family in best_by_family)
    weight_total = sum(weight_by_family.values())
    base_score = weighted_sum / weight_total if weight_total else 0.0
    corroboration_bonus = 0.0
    family_total = len(best_by_family)
    if family_total == 2:
        corroboration_bonus = 0.05
    elif family_total >= 3:
        corroboration_bonus = 0.10
    return round(min(0.99, base_score + corroboration_bonus), 2)


def cluster_candidate_set_hash(cluster: ClaimCluster) -> str:
    payload = [
        {
            "fingerprint": bucket.fingerprint,
            "normalized_value": bucket.normalized_value,
            "source_family_ids": sorted({claim.source_family_id for claim in bucket.claims}),
        }
        for bucket in cluster.buckets
    ]
    return f"sha256:{_sha256_text(json.dumps(payload, sort_keys=True))}"


def load_resolutions(path: Path | None) -> dict[str, DoctrineResolutionEntry]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = list(payload.get("resolutions") or [])
    resolved: dict[str, DoctrineResolutionEntry] = {}
    for entry in entries:
        item = DoctrineResolutionEntry(
            claim_key=str(entry["claim_key"]),
            candidate_set_hash=str(entry["candidate_set_hash"]),
            action=str(entry["action"]),
            chosen_value=entry["chosen_value"],
            resolution_basis=str(entry["resolution_basis"]),
            supporting_source_ids=tuple(str(value) for value in entry.get("supporting_source_ids") or []),
            curation_status=str(entry.get("curation_status") or "curated"),
        )
        resolved[f"{item.claim_key}|{item.candidate_set_hash}"] = item
    return resolved


def write_unresolved_conflicts(
    *,
    path: Path,
    bundle_id: str,
    conflicts: Iterable[UnresolvedConflict],
) -> None:
    payload = {
        "bundle_id": bundle_id,
        "version": "0.1.0",
        "conflicts": [
            {
                "claim_key": conflict.claim_key,
                "candidate_set_hash": conflict.candidate_set_hash,
                "reason": conflict.reason,
                "candidates": list(conflict.candidates),
            }
            for conflict in sorted(conflicts, key=lambda item: item.claim_key)
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_stable_json(payload), encoding="utf-8")


def select_cluster_winner(
    *,
    cluster: ClaimCluster,
    threshold: float,
    resolutions: dict[str, DoctrineResolutionEntry],
    win_margin: float = 0.15,
) -> ResolvedClaim | UnresolvedConflict:
    candidate_set_hash = cluster_candidate_set_hash(cluster)
    resolution = resolutions.get(f"{cluster.claim_key}|{candidate_set_hash}")
    if resolution is not None:
        return ResolvedClaim.from_manual_resolution(cluster, resolution)

    scored_candidates: list[dict[str, Any]] = []
    for bucket in cluster.buckets:
        scored_candidates.append(
            {
                "fingerprint": bucket.fingerprint,
                "normalized_value": bucket.normalized_value,
                "score": score_candidate_bucket(bucket),
                "family_count": family_count(bucket),
                "claims": bucket.claims,
            }
        )
    scored_candidates.sort(key=lambda item: (-float(item["score"]), str(item["fingerprint"])))
    top = scored_candidates[0]
    second = scored_candidates[1] if len(scored_candidates) > 1 else None
    margin = round(float(top["score"]) - (float(second["score"]) if second is not None else 0.0), 2)

    if float(top["score"]) < threshold:
        return UnresolvedConflict(
            claim_key=cluster.claim_key,
            candidate_set_hash=candidate_set_hash,
            reason="below_threshold",
            candidates=tuple(
                {
                    "normalized_value": candidate["normalized_value"],
                    "score": candidate["score"],
                    "supporting_source_families": sorted(
                        {claim.source_family_id for claim in candidate["claims"]}
                    ),
                }
                for candidate in scored_candidates
            ),
        )

    if second is not None and margin < win_margin:
        return UnresolvedConflict(
            claim_key=cluster.claim_key,
            candidate_set_hash=candidate_set_hash,
            reason="insufficient_margin",
            candidates=tuple(
                {
                    "normalized_value": candidate["normalized_value"],
                    "score": candidate["score"],
                    "supporting_source_families": sorted(
                        {claim.source_family_id for claim in candidate["claims"]}
                    ),
                }
                for candidate in scored_candidates
            ),
        )

    return ResolvedClaim(
        claim_key=cluster.claim_key,
        chosen_value=top["normalized_value"],
        confidence=float(top["score"]),
        resolution_basis="auto",
        supporting_claims=tuple(top["claims"]),
    )
