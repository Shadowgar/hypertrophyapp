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

from app.knowledge_schema import SourceRegistryBundle, SourceRegistryEntry


DEFAULT_SCHEMA_VERSION = "knowledge-1"
DEFAULT_BUNDLE_ID = "source_registry"
DEFAULT_BUNDLE_VERSION = "0.1.0"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_stable_json(payload), encoding="utf-8")


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "source"


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _title_from_path(source_path: str) -> str:
    stem = Path(source_path).stem
    words = re.sub(r"[_\-]+", " ", stem).strip()
    return words or source_path


def _infer_split_scope(source_path: str) -> list[str]:
    lowered = source_path.lower()
    scopes: list[str] = []
    if "full body" in lowered or "full_body" in lowered:
        scopes.append("full_body")
    if "upper lower" in lowered or "upper_lower" in lowered:
        scopes.append("upper_lower")
    if "push pull legs" in lowered or "push_pull_legs" in lowered or "ppl" in lowered:
        scopes.append("ppl")
    return sorted(set(scopes))


def _infer_program_family(source_path: str) -> str | None:
    lowered = source_path.lower()
    if "full body" in lowered or "full_body" in lowered:
        return "full_body"
    if "upper lower" in lowered or "upper_lower" in lowered:
        return "upper_lower"
    if "push pull legs" in lowered or "push_pull_legs" in lowered or "ppl" in lowered:
        return "ppl"
    if "specialization" in lowered or "arm hypertrophy" in lowered or "glute" in lowered or "bench" in lowered:
        return "specialization"
    if "comeback" in lowered or "fundamentals" in lowered or "get-ready" in lowered:
        return "rebuild_foundation"
    return None


def _infer_bodypart_scope(source_path: str) -> list[str]:
    lowered = source_path.lower()
    keyword_map = {
        "arm": "arms",
        "bicep": "biceps",
        "tricep": "triceps",
        "chest": "chest",
        "bench": "chest",
        "glute": "glutes",
        "squat": "quads",
        "hamstring": "hamstrings",
        "back": "back",
        "lat": "lats",
        "shoulder": "shoulders",
        "delt": "delts",
        "calf": "calves",
    }
    scopes = {label for token, label in keyword_map.items() if token in lowered}
    return sorted(scopes)


def _infer_source_kind(source_path: str, source_type: str, paired_source_ids: list[str]) -> str:
    lowered = source_path.lower()
    if source_type == "xlsx":
        return "authored_program_workbook"
    if source_type == "epub":
        return "general_hypertrophy_guide"
    if "technique" in lowered or "bench press" in lowered:
        return "technique_guide"
    if "specialization" in lowered or "arm hypertrophy" in lowered or "glute" in lowered:
        return "specialization_manual"
    if source_type == "pdf" and paired_source_ids:
        return "program_manual"
    if source_type == "pdf":
        return "general_hypertrophy_guide"
    return "other"


def _default_authority_weight(source_kind: str) -> float:
    if source_kind in {"authored_program_workbook", "program_manual"}:
        return 1.0
    if source_kind == "technique_guide":
        return 0.95
    if source_kind == "specialization_manual":
        return 0.9
    if source_kind == "general_hypertrophy_guide":
        return 0.75
    return 0.5


def _infer_extraction_capabilities(source_type: str, source_kind: str) -> list[str]:
    capabilities: list[str] = []
    if source_type == "xlsx":
        capabilities.extend(["exercise_table", "week_structure", "session_layout"])
    if source_type == "pdf":
        capabilities.extend(["doctrine_text", "progression_guidance"])
    if source_kind == "technique_guide":
        capabilities.append("technique_cues")
    if source_kind == "specialization_manual":
        capabilities.append("specialization_signal")
    if source_kind in {"program_manual", "authored_program_workbook"}:
        capabilities.append("program_intent")
    return sorted(set(capabilities))


def _infer_doctrine_modules(source_kind: str, split_scope: list[str], bodypart_scope: list[str]) -> list[str]:
    modules: set[str] = {"exercise_selection"}
    if source_kind in {"program_manual", "authored_program_workbook"}:
        modules.update({"progression", "volume_allocation", "mesocycle_management"})
    if source_kind in {"technique_guide", "specialization_manual"}:
        modules.add("exercise_execution")
    if split_scope:
        modules.add("split_selection")
    if bodypart_scope:
        modules.add("weak_spot_prioritization")
    return sorted(modules)


def _load_overrides(overrides_path: Path | None) -> dict[str, dict[str, Any]]:
    if overrides_path is None or not overrides_path.exists():
        return {}

    payload = json.loads(overrides_path.read_text(encoding="utf-8"))
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return {}

    overrides: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        match_path = str(entry.get("match_path") or "").strip()
        if not match_path:
            continue
        overrides[match_path] = dict(entry)
    return overrides


def _build_pair_map(workbook_pdf_pairs: list[dict[str, Any]]) -> dict[str, list[str]]:
    pair_map: dict[str, set[str]] = {}
    for pair in workbook_pdf_pairs:
        workbook_path = str(pair.get("workbook_asset_path") or "").strip()
        guide_path = str(pair.get("guide_asset_path") or "").strip()
        if not workbook_path or not guide_path:
            continue
        pair_map.setdefault(workbook_path, set()).add(guide_path)
        pair_map.setdefault(guide_path, set()).add(workbook_path)
    return {key: sorted(value) for key, value in pair_map.items()}


def _build_derived_doc_map(
    asset_catalog_assets: list[dict[str, Any]],
    provenance_entries: list[dict[str, Any]],
) -> dict[str, list[str]]:
    derived_doc_map: dict[str, set[str]] = {}

    for asset in asset_catalog_assets:
        asset_path = str(asset.get("asset_path") or "").strip()
        derived_doc = str(asset.get("derived_doc") or "").strip()
        if asset_path and derived_doc:
            derived_doc_map.setdefault(asset_path, set()).add(derived_doc)

    for provenance in provenance_entries:
        asset_path = str(provenance.get("asset") or "").strip()
        if not asset_path:
            continue
        for entity in provenance.get("derived_entities") or []:
            entity_path = str((entity or {}).get("path") or "").strip()
            if entity_path:
                derived_doc_map.setdefault(asset_path, set()).add(entity_path)

    return {key: sorted(value) for key, value in derived_doc_map.items()}


def _source_id(source_path: str, source_sha256: str) -> str:
    return f"{_slugify(Path(source_path).stem)}-{source_sha256[:8]}"


def _finalize_bundle_payload(payload: dict[str, Any]) -> dict[str, Any]:
    base_payload = dict(payload)
    base_payload.pop("output_signature", None)
    base_payload.pop("aggregate_signature", None)
    output_signature = _sha256_text(_stable_json(base_payload))
    final_payload = dict(base_payload)
    final_payload["output_signature"] = output_signature
    final_payload["aggregate_signature"] = _sha256_text(_stable_json(final_payload))
    return final_payload


def build_source_registry(
    *,
    asset_catalog_path: Path,
    provenance_index_path: Path,
    overrides_path: Path | None = None,
    schema_version: str = DEFAULT_SCHEMA_VERSION,
    bundle_version: str = DEFAULT_BUNDLE_VERSION,
) -> SourceRegistryBundle:
    asset_catalog_payload = json.loads(asset_catalog_path.read_text(encoding="utf-8"))
    provenance_payload = json.loads(provenance_index_path.read_text(encoding="utf-8"))
    overrides = _load_overrides(overrides_path)

    asset_catalog_assets = list(asset_catalog_payload.get("assets") or [])
    provenance_entries = list(provenance_payload.get("provenance") or [])
    pair_map = _build_pair_map(list(asset_catalog_payload.get("workbook_pdf_pairs") or []))
    derived_doc_map = _build_derived_doc_map(asset_catalog_assets, provenance_entries)

    entries: list[SourceRegistryEntry] = []
    for asset in sorted(asset_catalog_assets, key=lambda item: str(item.get("asset_path") or "")):
        source_path = str(asset.get("asset_path") or "").strip()
        source_sha256 = str(asset.get("asset_sha256") or "").strip()
        source_type = str(asset.get("asset_type") or "").strip()
        if not source_path or not source_sha256 or not source_type:
            continue

        override = overrides.get(source_path, {})
        paired_source_ids = [
            _source_id(pair_path, str(next_asset.get("asset_sha256") or ""))
            for pair_path in pair_map.get(source_path, [])
            for next_asset in asset_catalog_assets
            if str(next_asset.get("asset_path") or "") == pair_path
        ]
        source_kind = str(
            override.get("source_kind")
            or _infer_source_kind(source_path, source_type, paired_source_ids)
        )
        title = str(override.get("title") or _title_from_path(source_path))
        split_scope = list(override.get("split_scope") or _infer_split_scope(source_path))
        bodypart_scope = list(override.get("bodypart_scope") or _infer_bodypart_scope(source_path))
        source_family_id = str(
            override.get("source_family_id")
            or _infer_program_family(source_path)
            or source_kind
        )
        doctrine_modules = list(
            override.get("doctrine_modules")
            or _infer_doctrine_modules(source_kind, split_scope, bodypart_scope)
        )
        extraction_capabilities = list(
            override.get("extraction_capabilities")
            or _infer_extraction_capabilities(source_type, source_kind)
        )
        entry = SourceRegistryEntry(
            source_id=_source_id(source_path, source_sha256),
            source_path=source_path,
            source_sha256=source_sha256,
            source_type=source_type,
            source_kind=source_kind,
            title=title,
            paired_source_ids=paired_source_ids,
            program_family=override.get("program_family"),
            source_family_id=source_family_id,
            split_scope=split_scope,
            bodypart_scope=bodypart_scope,
            doctrine_modules=doctrine_modules,
            extraction_capabilities=extraction_capabilities,
            authority_weight=float(override.get("authority_weight") or _default_authority_weight(source_kind)),
            classification_confidence=float(override.get("classification_confidence") or 0.6),
            curation_status=str(override.get("curation_status") or "seeded"),
            derived_doc_paths=list(override.get("derived_doc_paths") or derived_doc_map.get(source_path, [])),
            provenance_refs=list(override.get("provenance_refs") or []),
        )
        entries.append(entry)

    input_signature_parts = [
        str(asset_catalog_payload.get("aggregate_signature") or ""),
        str(provenance_payload.get("aggregate_signature") or ""),
    ]
    if overrides_path is not None and overrides_path.exists():
        input_signature_parts.append(_sha256_text(overrides_path.read_text(encoding="utf-8")))
    input_signature = _sha256_text("\n".join(input_signature_parts))

    payload = {
        "schema_version": schema_version,
        "bundle_id": DEFAULT_BUNDLE_ID,
        "bundle_version": bundle_version,
        "input_signature": input_signature,
        "output_signature": "pending",
        "aggregate_signature": "pending",
        "entries": [entry.model_dump(mode="json") for entry in entries],
    }
    return SourceRegistryBundle.model_validate(_finalize_bundle_payload(payload))


def write_source_registry(bundle: SourceRegistryBundle, output_path: Path) -> None:
    _write_json(output_path, bundle.model_dump(mode="json"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile the deterministic source registry bundle.")
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
        "--output",
        type=Path,
        default=REPO_ROOT / "knowledge" / "compiled" / "source_registry.v1.json",
    )
    args = parser.parse_args()

    bundle = build_source_registry(
        asset_catalog_path=args.asset_catalog,
        provenance_index_path=args.provenance_index,
        overrides_path=args.overrides,
    )
    write_source_registry(bundle, args.output)
    print(_safe_relative(args.output, REPO_ROOT))


if __name__ == "__main__":
    main()
