#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PROGRAMS_DIR = REPO_ROOT / "programs"
WEB_ONBOARDING = REPO_ROOT / "apps" / "web" / "app" / "onboarding" / "page.tsx"
WEB_SETTINGS = REPO_ROOT / "apps" / "web" / "app" / "settings" / "page.tsx"


CANONICAL_EQUIPMENT = {
    "barbell",
    "bench",
    "bodyweight",
    "cable",
    "dumbbell",
    "machine",
    "bands",
    "smith_machine",
    "rack",
}

EQUIPMENT_SYNONYMS = {
    "bar": "barbell",
    "bb": "barbell",
    "db": "dumbbell",
    "bw": "bodyweight",
    "cables": "cable",
    "smith": "smith_machine",
}

RESTRICTED_PATTERN_KEYS = {"vertical_press", "squat", "lunge"}
MOVEMENT_NORMALIZE_RE = re.compile(r"[^a-z]+")


@dataclass
class ExerciseRecord:
    template_id: str
    source_file: str
    session_name: str
    exercise_id: str
    name: str
    movement_pattern: str | None
    slot_role: str | None
    primary_muscles: list[str]
    equipment_tags: list[str]
    substitution_candidates: list[str]
    substitution_metadata: dict[str, Any]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_pattern(value: Any) -> str:
    return MOVEMENT_NORMALIZE_RE.sub("_", str(value or "").strip().lower()).strip("_")


def _extract_exercises(template: dict[str, Any], source_file: str) -> list[ExerciseRecord]:
    sessions = template.get("sessions") or []
    if not isinstance(sessions, list):
        return []
    records: list[ExerciseRecord] = []
    template_id = str(template.get("id") or source_file.replace(".json", ""))
    for session in sessions:
        if not isinstance(session, dict):
            continue
        session_name = str(session.get("name") or session.get("title") or "unknown")
        for ex in session.get("exercises") or []:
            if not isinstance(ex, dict):
                continue
            records.append(
                ExerciseRecord(
                    template_id=template_id,
                    source_file=source_file,
                    session_name=session_name,
                    exercise_id=str(ex.get("id") or ""),
                    name=str(ex.get("name") or ""),
                    movement_pattern=ex.get("movement_pattern"),
                    slot_role=ex.get("slot_role"),
                    primary_muscles=[str(m) for m in (ex.get("primary_muscles") or []) if str(m).strip()],
                    equipment_tags=[str(t) for t in (ex.get("equipment_tags") or []) if str(t).strip()],
                    substitution_candidates=[
                        str(c) for c in (ex.get("substitution_candidates") or ex.get("substitutions") or []) if str(c).strip()
                    ],
                    substitution_metadata=ex.get("substitution_metadata") if isinstance(ex.get("substitution_metadata"), dict) else {},
                )
            )
    return records


def _iter_program_templates(programs_dir: Path) -> list[ExerciseRecord]:
    records: list[ExerciseRecord] = []
    for path in sorted(programs_dir.rglob("*.json")):
        payload = _load_json(path)
        records.extend(_extract_exercises(payload, str(path.relative_to(REPO_ROOT))))
    return records


def _collect_keyed_values(payload: Any, target_key: str) -> list[tuple[str, Any]]:
    results: list[tuple[str, Any]] = []

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                child_path = f"{path}.{key}" if path else key
                if key == target_key:
                    results.append((child_path, value))
                _walk(value, child_path)
        elif isinstance(node, list):
            for idx, value in enumerate(node):
                _walk(value, f"{path}[{idx}]")

    _walk(payload, "")
    return results


def _extract_ui_equipment_tokens(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    # Capture simple string literals inside equipment option arrays/chips.
    return sorted(set(re.findall(r'"(barbell|bench|dumbbell|cable|machine|bands|bodyweight|rack|smith_machine|bar|db|bb|bw|cables|smith)"', text)))


def build_audit(programs_dir: Path = PROGRAMS_DIR) -> dict[str, Any]:
    records = _iter_program_templates(programs_dir)
    total = len(records)
    movement_present = 0
    movement_null = 0
    movement_missing_key = 0
    missing_movement_examples: list[dict[str, str]] = []

    equipment_token_counter: Counter[str] = Counter()
    non_canonical_equipment_tokens: Counter[str] = Counter()
    empty_equipment_examples: list[dict[str, str]] = []

    substitutions_total = 0
    substitutions_empty = 0
    substitution_metadata_present = 0
    substitution_metadata_missing = 0
    substitution_metadata_field_missing: Counter[str] = Counter()
    high_risk_empty_subs: list[dict[str, str]] = []
    placeholder_sub_candidates: list[dict[str, str]] = []
    sparse_candidate_metadata_examples: list[dict[str, str]] = []
    global_equipment_tokens: Counter[str] = Counter()
    global_non_canonical_tokens: Counter[str] = Counter()
    global_equipment_token_examples: list[dict[str, str]] = []
    global_placeholder_valid_substitutions: list[dict[str, str]] = []
    source_files = sorted(programs_dir.rglob("*.json"))

    movement_coverage_by_file: dict[str, Counter[str]] = defaultdict(Counter)
    primary_muscles_present = 0
    primary_muscles_missing = 0
    slot_role_present = 0
    slot_role_missing = 0
    equipment_tags_present = 0
    equipment_tags_missing = 0
    equipment_drift_examples: list[dict[str, Any]] = []

    for rec in records:
        # movement_pattern coverage
        movement_key_status = "present"
        mp = rec.movement_pattern
        if mp is None:
            movement_key_status = "null_or_missing"
            movement_null += 1
            if len(missing_movement_examples) < 40:
                missing_movement_examples.append(
                    {
                        "source_file": rec.source_file,
                        "template_id": rec.template_id,
                        "session": rec.session_name,
                        "exercise_id": rec.exercise_id,
                        "exercise_name": rec.name,
                    }
                )
        elif not str(mp).strip():
            movement_key_status = "null_or_missing"
            movement_null += 1
        else:
            movement_present += 1
        movement_coverage_by_file[rec.source_file][movement_key_status] += 1
        if rec.primary_muscles:
            primary_muscles_present += 1
        else:
            primary_muscles_missing += 1
        if str(rec.slot_role or "").strip():
            slot_role_present += 1
        else:
            slot_role_missing += 1
        if rec.equipment_tags:
            equipment_tags_present += 1
        else:
            equipment_tags_missing += 1

        # equipment tags
        if not rec.equipment_tags and len(empty_equipment_examples) < 40:
            empty_equipment_examples.append(
                {
                    "source_file": rec.source_file,
                    "exercise_id": rec.exercise_id,
                    "exercise_name": rec.name,
                }
            )
        for tag in rec.equipment_tags:
            token = tag.strip().lower()
            equipment_token_counter[token] += 1
            canonical = EQUIPMENT_SYNONYMS.get(token, token)
            if canonical not in CANONICAL_EQUIPMENT:
                non_canonical_equipment_tokens[token] += 1
            elif canonical != token:
                non_canonical_equipment_tokens[token] += 1
                if len(equipment_drift_examples) < 30:
                    equipment_drift_examples.append(
                        {
                            "source_file": rec.source_file,
                            "exercise_id": rec.exercise_id,
                            "token": token,
                            "canonical": canonical,
                        }
                    )

        # substitutions
        substitutions_total += 1
        if not rec.substitution_candidates:
            substitutions_empty += 1
            if _normalize_pattern(rec.movement_pattern) in RESTRICTED_PATTERN_KEYS and len(high_risk_empty_subs) < 50:
                high_risk_empty_subs.append(
                    {
                        "source_file": rec.source_file,
                        "exercise_id": rec.exercise_id,
                        "exercise_name": rec.name,
                        "movement_pattern": str(rec.movement_pattern),
                    }
                )

        if rec.substitution_metadata:
            substitution_metadata_present += 1
        else:
            substitution_metadata_missing += 1

        for candidate in rec.substitution_candidates:
            if "see_the_weak_point_table_for_sub_options" in candidate.lower() and len(placeholder_sub_candidates) < 30:
                placeholder_sub_candidates.append(
                    {
                        "source_file": rec.source_file,
                        "exercise_id": rec.exercise_id,
                        "candidate": candidate,
                    }
                )
            meta = rec.substitution_metadata.get(candidate) if isinstance(rec.substitution_metadata, dict) else None
            if not isinstance(meta, dict):
                substitution_metadata_field_missing["candidate_metadata_missing"] += 1
                if len(sparse_candidate_metadata_examples) < 40:
                    sparse_candidate_metadata_examples.append(
                        {
                            "source_file": rec.source_file,
                            "exercise_id": rec.exercise_id,
                            "candidate": candidate,
                            "issue": "candidate_metadata_missing",
                        }
                    )
                continue
            for field in ("id", "movement_pattern", "equipment_tags", "primary_muscles"):
                value = meta.get(field)
                missing = value is None or (isinstance(value, list) and not value) or (isinstance(value, str) and not value.strip())
                if missing:
                    substitution_metadata_field_missing[field] += 1
                    if len(sparse_candidate_metadata_examples) < 40:
                        sparse_candidate_metadata_examples.append(
                            {
                                "source_file": rec.source_file,
                                "exercise_id": rec.exercise_id,
                                "candidate": candidate,
                                "issue": f"missing_{field}",
                            }
                        )

    # recursive scans for metadata outside session/exercise blocks
    for path in source_files:
        payload = _load_json(path)
        rel_path = str(path.relative_to(REPO_ROOT))
        for key_path, value in _collect_keyed_values(payload, "equipment_tags"):
            if not isinstance(value, list):
                continue
            for tag in value:
                token = str(tag).strip().lower()
                if not token:
                    continue
                global_equipment_tokens[token] += 1
                canonical = EQUIPMENT_SYNONYMS.get(token, token)
                if canonical not in CANONICAL_EQUIPMENT or canonical != token:
                    global_non_canonical_tokens[token] += 1
                    if len(global_equipment_token_examples) < 60:
                        global_equipment_token_examples.append(
                            {
                                "source_file": rel_path,
                                "path": key_path,
                                "token": token,
                                "canonical": canonical,
                            }
                        )
        for key_path, value in _collect_keyed_values(payload, "valid_substitutions"):
            if not isinstance(value, list):
                continue
            for item in value:
                exercise_id = str(_load_json(path).get("id", ""))  # keep deterministic and cheap enough at this scale
                # item can be dict {exercise_id: ...} or str
                candidate = ""
                if isinstance(item, dict):
                    candidate = str(item.get("exercise_id") or "")
                else:
                    candidate = str(item or "")
                if "see_the_weak_point_table_for_sub_options" in candidate.lower() and len(global_placeholder_valid_substitutions) < 60:
                    global_placeholder_valid_substitutions.append(
                        {
                            "source_file": rel_path,
                            "path": key_path,
                            "candidate": candidate,
                            "template_id": exercise_id,
                        }
                    )

    # missing key estimation for movement_pattern via direct file scan
    for path in sorted(programs_dir.rglob("*.json")):
        payload = _load_json(path)
        sessions = payload.get("sessions") or []
        for session in sessions:
            if not isinstance(session, dict):
                continue
            for ex in session.get("exercises") or []:
                if not isinstance(ex, dict):
                    continue
                if "movement_pattern" not in ex:
                    movement_missing_key += 1

    movement_null = max(0, movement_null - movement_missing_key)

    onboarding_tokens = _extract_ui_equipment_tokens(WEB_ONBOARDING) if WEB_ONBOARDING.exists() else []
    settings_tokens = _extract_ui_equipment_tokens(WEB_SETTINGS) if WEB_SETTINGS.exists() else []

    return {
        "totals": {
            "exercise_count": total,
            "template_count": len({r.template_id for r in records}),
        },
        "coverage_summary": {
            "movement_pattern": {
                "present_count": movement_present,
                "present_pct": round((movement_present / total) * 100, 2) if total else 0.0,
                "null_count": movement_null,
                "null_pct": round((movement_null / total) * 100, 2) if total else 0.0,
                "missing_key_count": movement_missing_key,
                "missing_key_pct": round((movement_missing_key / total) * 100, 2) if total else 0.0,
            },
            "substitution_metadata": {
                "exercise_with_candidates_count": substitutions_total,
                "exercise_with_candidates_pct": round((substitutions_total / total) * 100, 2) if total else 0.0,
                "authored_substitution_metadata_present_count": substitution_metadata_present,
                "authored_substitution_metadata_present_pct": round((substitution_metadata_present / total) * 100, 2) if total else 0.0,
                "authored_substitution_metadata_missing_count": substitution_metadata_missing,
            },
            "runtime_dependent_fields": {
                "primary_muscles_present_count": primary_muscles_present,
                "primary_muscles_missing_count": primary_muscles_missing,
                "equipment_tags_present_count": equipment_tags_present,
                "equipment_tags_missing_count": equipment_tags_missing,
                "slot_role_present_count": slot_role_present,
                "slot_role_missing_count": slot_role_missing,
            },
            "equipment_tags": {
                "distinct_tokens": sorted(equipment_token_counter.keys()),
                "non_canonical_or_synonym_tokens": dict(non_canonical_equipment_tokens),
                "global_distinct_tokens": sorted(global_equipment_tokens.keys()),
                "global_non_canonical_or_synonym_tokens": dict(global_non_canonical_tokens),
                "ui_onboarding_tokens": onboarding_tokens,
                "ui_settings_tokens": settings_tokens,
            },
        },
        "gaps": {
            "movement_pattern_missing_examples": missing_movement_examples,
            "movement_pattern_coverage_by_file": {
                path: dict(counter) for path, counter in movement_coverage_by_file.items()
            },
            "empty_equipment_examples": empty_equipment_examples,
            "equipment_drift_examples": equipment_drift_examples,
            "global_equipment_drift_examples": global_equipment_token_examples,
            "high_risk_empty_substitution_candidates": high_risk_empty_subs,
            "placeholder_substitution_candidates": placeholder_sub_candidates,
            "global_placeholder_valid_substitutions": global_placeholder_valid_substitutions,
            "sparse_candidate_metadata_examples": sparse_candidate_metadata_examples,
            "substitution_metadata_field_missing_counts": dict(substitution_metadata_field_missing),
        },
        "severity": {
            "blocks_safe_runtime_decisions": [
                "Missing candidate movement_pattern metadata can bypass restriction filtering.",
                "High-risk movement patterns with empty substitution_candidates can cause unsafe drops/no fallback.",
                "Placeholder/stale substitution identifiers degrade to low-confidence fallback behavior.",
            ],
            "weakens_decision_quality": [
                "Equipment synonym drift and sparse equipment tags increase inference dependence.",
                "Missing candidate primary_muscles weakens weak-area routing and tie-break confidence.",
            ],
            "mostly_cosmetic": [
                "Missing candidate video metadata lowers coaching payload quality but not safety in most paths.",
            ],
        },
        "phase_recommendation": {
            "keep_metadata_hardening_phase": True,
            "reason": "Current runtime safety and quality now directly depend on metadata coverage and consistency.",
            "recommended_next_phase": "exercise metadata hardening for safe program expansion",
            "ordered_tasks": [
                "Define canonical movement_pattern and equipment tag vocabularies.",
                "Create metadata validator and fail-on-regression CI checks for active templates.",
                "Backfill substitution metadata for active templates (id, movement_pattern, equipment_tags, primary_muscles).",
                "Add sparse-metadata restriction policy (allow/deny/warn) with trace confidence flags.",
                "Normalize template-side equipment tokens and remove synonym drift at source.",
                "Remediate high-risk imported templates with empty substitution candidates for restricted patterns.",
                "Add regression tests for restriction leaks, substitution quality, and weak-area classification confidence.",
            ],
        },
    }


def markdown_summary(report: dict[str, Any]) -> str:
    cov = report["coverage_summary"]
    gaps = report["gaps"]
    phase = report["phase_recommendation"]
    lines = [
        "# Exercise Metadata Quality Audit",
        "",
        "## A. Coverage Summary by Metadata Type",
        f"- movement_pattern: {cov['movement_pattern']['present_count']}/{report['totals']['exercise_count']} present "
        f"({cov['movement_pattern']['present_pct']}%), {cov['movement_pattern']['null_count']} null "
        f"({cov['movement_pattern']['null_pct']}%), {cov['movement_pattern']['missing_key_count']} missing key "
        f"({cov['movement_pattern']['missing_key_pct']}%).",
        f"- substitution_metadata: {cov['substitution_metadata']['authored_substitution_metadata_present_count']}/"
        f"{cov['substitution_metadata']['exercise_with_candidates_count']} exercises with authored substitution metadata.",
        f"- equipment token drift: {len(cov['equipment_tags']['non_canonical_or_synonym_tokens'])} non-canonical/synonym tokens detected.",
        "",
        "## B. Exact Files/Locations with Missing or Inconsistent Metadata",
        "- movement pattern gaps: see `gaps.movement_pattern_missing_examples` and `gaps.movement_pattern_coverage_by_file` in JSON output.",
        "- equipment drift: see `gaps.equipment_drift_examples` and `coverage_summary.equipment_tags.non_canonical_or_synonym_tokens`.",
        "- substitution completeness/fallback gaps: see `gaps.high_risk_empty_substitution_candidates`, "
        "`gaps.placeholder_substitution_candidates`, and `gaps.sparse_candidate_metadata_examples`.",
        "",
        "## C. Severity Ranking",
        "- blocks safe runtime decisions:",
    ]
    lines.extend([f"  - {item}" for item in report["severity"]["blocks_safe_runtime_decisions"]])
    lines.append("- weakens decision quality:")
    lines.extend([f"  - {item}" for item in report["severity"]["weakens_decision_quality"]])
    lines.append("- mostly cosmetic:")
    lines.extend([f"  - {item}" for item in report["severity"]["mostly_cosmetic"]])
    lines.extend(
        [
            "",
            "## D. Recommended Next Implementation Plan",
            *[f"{idx}. {task}" for idx, task in enumerate(phase["ordered_tasks"], start=1)],
            "",
            "## E. Next Phase Decision",
            f"- keep phase: {phase['keep_metadata_hardening_phase']}",
            f"- recommended phase: {phase['recommended_next_phase']}",
            f"- reason: {phase['reason']}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate exercise metadata quality audit report.")
    parser.add_argument(
        "--programs-dir",
        type=Path,
        default=PROGRAMS_DIR,
        help="Directory containing program templates",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=REPO_ROOT / "docs" / "validation" / "exercise_metadata_quality_audit.json",
        help="Output path for JSON audit report",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=REPO_ROOT / "docs" / "validation" / "exercise_metadata_quality_audit.md",
        help="Output path for markdown summary",
    )
    args = parser.parse_args()

    report = build_audit(args.programs_dir)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)

    args.json_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    args.markdown_output.write_text(markdown_summary(report), encoding="utf-8")

    print(f"Wrote JSON report: {args.json_output}")
    print(f"Wrote markdown summary: {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
