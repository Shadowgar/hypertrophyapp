#!/usr/bin/env python3
"""PDF doctrine distillation v2 — typed rules with provenance and distillation report.

Enhances v1 with:
  - Generated-week scheduler rules block (mesocycle, exercise adjustment, session selection,
    exercise cap, muscle coverage) matching the schema used by rules_runtime.
  - Per-rule provenance: each rule block carries source_asset, section, and excerpt.
  - Distillation report: rules emitted, sections matched, sections with no match.

Usage:
  python importers/pdf_doctrine_rules_v2.py \
    --source-pdf "reference/The Hypertrophy Handbook.pdf" \
    --program-id pure_bodybuilding_phase_1_full_body \
    --guide-doc docs/guides/generated/<guide>.md

  # Or auto-resolve guide doc via provenance_index:
  python importers/pdf_doctrine_rules_v2.py \
    --source-pdf "reference/The Hypertrophy Handbook.pdf" \
    --program-id pure_bodybuilding_phase_1_full_body
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.adaptive_schema import AdaptiveGoldRuleSet
from importers.pdf_doctrine_rules_v1 import (
    build_rule_set_payload as build_v1_payload,
    resolve_guide_doc,
    _compress_whitespace,
    _find_excerpt,
)
from importers.xlsx_to_program import slugify


_DEFAULT_SCHEDULER_RULES: dict[str, Any] = {
    "mesocycle": {
        "sequence_completion_phase_transition_reason": "Authored mesocycle complete; recommend program rotation or phase transition.",
        "post_authored_sequence_behavior": "hold_last_authored_week",
        "soreness_deload_trigger": {
            "minimum_severe_count": 3,
            "reason": "3+ severe-soreness muscle groups; deload recommended.",
        },
        "adherence_deload_trigger": {
            "maximum_score": 2,
            "reason": "Adherence critically low; deload recommended.",
        },
        "stimulus_fatigue_deload_trigger": {
            "deload_pressure": "high",
            "recoverability": "low",
            "reason": "High deload pressure with low recoverability; deload recommended.",
        },
    },
    "exercise_adjustment": {
        "policies": [
            {
                "policy_id": "high_fatigue_stalled",
                "match_policy": "all",
                "conditions": {
                    "minimum_fatigue_score": 0.7,
                    "minimum_consecutive_under_target_exposures": 2,
                    "last_progression_actions": ["hold_or_reduce", "reduce"],
                },
                "adjustment": {
                    "load_scale": 0.9,
                    "set_delta": -1,
                    "substitution_pressure": "high",
                    "substitution_guidance": "Consider substituting this exercise if the pattern continues.",
                },
            },
            {
                "policy_id": "moderate_fatigue",
                "match_policy": "all",
                "conditions": {
                    "minimum_fatigue_score": 0.5,
                    "minimum_consecutive_under_target_exposures": 1,
                    "last_progression_actions": [],
                },
                "adjustment": {
                    "load_scale": 0.95,
                    "set_delta": 0,
                    "substitution_pressure": "moderate",
                },
            },
        ],
        "default_adjustment": {
            "load_scale": 1.0,
            "set_delta": 0,
            "substitution_pressure": "low",
        },
        "substitution_pressure_guidance": {
            "low": None,
            "moderate": "This exercise has moderate substitution pressure; monitor next exposure.",
            "high": "This exercise has high substitution pressure; a swap may improve stimulus quality.",
        },
    },
    "session_selection": {
        "recent_history_exercise_limit": 6,
        "anchor_first_session_when_day_roles_present": True,
        "required_day_roles_when_compressed": ["weak_point_arms"],
        "structural_slot_role_priority": {
            "primary_compound": 1,
            "secondary_compound": 2,
            "weak_point": 3,
            "accessory": 4,
            "isolation": 5,
        },
        "day_role_priority": {
            "full_body_1": 1,
            "full_body_2": 2,
            "full_body_3": 3,
            "full_body_4": 4,
            "weak_point_arms": 5,
        },
        "missed_day_policy": "skip_and_continue",
    },
    "session_exercise_cap": {
        "time_budget_thresholds": [
            {"maximum_minutes": 45, "exercise_limit": 6},
            {"maximum_minutes": 60, "exercise_limit": 8},
            {"maximum_minutes": 90, "exercise_limit": 10},
        ],
        "default_slot_role_priority": {
            "primary_compound": 1,
            "secondary_compound": 2,
            "weak_point": 3,
            "accessory": 4,
            "isolation": 5,
        },
        "day_role_slot_role_priority_overrides": {
            "weak_point_arms": {
                "weak_point": 1,
                "isolation": 2,
                "accessory": 3,
                "primary_compound": 4,
                "secondary_compound": 5,
            },
        },
    },
    "muscle_coverage": {
        "tracked_muscles": [
            "chest", "back", "quads", "hamstrings", "glutes",
            "shoulders", "biceps", "triceps", "calves", "abs", "forearms",
        ],
        "minimum_sets_per_muscle": 4,
        "authored_label_normalization": {
            "rear delts": "shoulders",
            "side delts": "shoulders",
            "front delts": "shoulders",
            "lats": "back",
            "traps": "back",
            "hip adductors": "glutes",
        },
    },
}


def _extract_sections_matched(text: str) -> list[dict[str, str]]:
    """Scan for recognizable section headings and return which were found."""
    sections = [
        ("starting_load", r"starting\s+load|warm.?up|reps?\s+in\s+(?:the\s+)?tank"),
        ("progression", r"progress(?:ion)?\s+through\s+the\s+rep\s+ranges?|double\s+progression"),
        ("fatigue_management", r"fatigue\s+management|intensity\s+will\s+increase|rpe"),
        ("deload", r"deload|recovery\s+week"),
        ("substitution", r"substitut(?:ion|e)\s+(?:column|option)"),
        ("warm_up", r"general\s+warm.?up|exercise.specific\s+warm.?up"),
        ("weak_points", r"weak\s+point"),
        ("frequency", r"training\s+days?\s+per\s+week|frequency"),
    ]
    results = []
    for name, pattern in sections:
        import re
        if re.search(pattern, text, re.IGNORECASE):
            results.append({"section": name, "status": "matched"})
        else:
            results.append({"section": name, "status": "not_found"})
    return results


def build_v2_rule_set_payload(
    *,
    program_id: str,
    source_pdf: str,
    guide_doc: Path,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Build the v2 rule set payload with scheduler rules and provenance.

    Returns (payload, diagnostics).
    """
    v1_payload = build_v1_payload(
        program_id=program_id,
        source_pdf=source_pdf,
        guide_doc=guide_doc,
    )

    v1_payload["version"] = "0.2.0"

    if not v1_payload.get("generated_week_scheduler_rules"):
        v1_payload["generated_week_scheduler_rules"] = _DEFAULT_SCHEDULER_RULES

    text = guide_doc.read_text(encoding="utf-8")
    normalized = _compress_whitespace(text)
    sections = _extract_sections_matched(normalized)

    diagnostics: list[dict[str, str]] = []
    for section in sections:
        if section["status"] == "not_found":
            diagnostics.append({
                "source": "pdf_distillation",
                "code": f"section_not_found_{section['section']}",
                "message": f"No match found for section '{section['section']}' in {source_pdf}; rules for this area use defaults.",
            })

    if not v1_payload.get("source_sections"):
        diagnostics.append({
            "source": "pdf_distillation",
            "code": "no_source_sections",
            "message": "No source excerpts could be extracted; rules are based on defaults.",
        })

    return v1_payload, diagnostics


def _build_distillation_report(
    *,
    source_pdf: str,
    program_id: str,
    guide_doc: Path,
    output_path: Path,
    diagnostics: list[dict[str, str]],
    sections_matched: list[dict[str, str]],
    rules_emitted: list[str],
) -> dict[str, Any]:
    return {
        "distiller": "pdf_doctrine_rules_v2",
        "version": "2.0.0",
        "date": date.today().isoformat(),
        "source_pdf": source_pdf,
        "program_id": program_id,
        "guide_doc": str(guide_doc),
        "output": str(output_path),
        "rules_emitted": rules_emitted,
        "rules_emitted_count": len(rules_emitted),
        "sections": sections_matched,
        "sections_matched_count": sum(1 for s in sections_matched if s["status"] == "matched"),
        "sections_not_found_count": sum(1 for s in sections_matched if s["status"] == "not_found"),
        "diagnostics": diagnostics,
        "diagnostics_count": len(diagnostics),
    }


def distill_rule_set_v2(
    *,
    source_pdf: str,
    program_id: str,
    output_file: Path | None = None,
    guide_doc: Path | None = None,
    provenance_index: Path | None = None,
    report_output: Path | None = None,
) -> tuple[Path, Path]:
    """Run the v2 distillation pipeline. Returns (rules_path, report_path)."""
    resolved_guide = guide_doc or resolve_guide_doc(source_pdf=source_pdf, provenance_index=provenance_index)
    payload, diagnostics = build_v2_rule_set_payload(
        program_id=program_id,
        source_pdf=source_pdf,
        guide_doc=resolved_guide,
    )
    validated = AdaptiveGoldRuleSet.model_validate(payload)

    destination = output_file or (REPO_ROOT / "docs" / "rules" / "canonical" / f"{program_id}.rules.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(validated.model_dump(mode="json"), indent=2), encoding="utf-8")

    text = resolved_guide.read_text(encoding="utf-8")
    normalized = _compress_whitespace(text)
    sections_matched = _extract_sections_matched(normalized)

    rules_emitted = [
        "starting_load_rules",
        "progression_rules",
        "fatigue_rules",
        "deload_rules",
        "substitution_rules",
        "generated_week_scheduler_rules",
        "rationale_templates",
    ]

    report_path = report_output or destination.with_suffix(".distillation_report.json")
    report = _build_distillation_report(
        source_pdf=source_pdf,
        program_id=program_id,
        guide_doc=resolved_guide,
        output_path=destination,
        diagnostics=diagnostics,
        sections_matched=sections_matched,
        rules_emitted=rules_emitted,
    )
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return destination, report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF doctrine distillation v2 — typed rules with provenance")
    parser.add_argument("--source-pdf", type=str, required=True, help="Reference PDF path")
    parser.add_argument("--program-id", type=str, required=False, help="Rule-set program scope identifier")
    parser.add_argument("--guide-doc", type=Path, default=None, help="Normalized guide markdown path")
    parser.add_argument("--output", type=Path, default=None, help="Output rules JSON path")
    parser.add_argument("--report-output", type=Path, default=None, help="Output distillation report JSON path")
    args = parser.parse_args()

    program_id = args.program_id or slugify(Path(args.source_pdf).stem)
    destination, report_path = distill_rule_set_v2(
        source_pdf=args.source_pdf,
        program_id=program_id,
        output_file=args.output,
        guide_doc=args.guide_doc,
        report_output=args.report_output,
    )
    print(f"Rule set written to: {destination}")
    print(f"Distillation report written to: {report_path}")


if __name__ == "__main__":
    main()
