#!/usr/bin/env python3
"""Build-time PDF doctrine distillation into typed adaptive rules.

This is a deterministic first pass over normalized guide documents. It emits a
schema-validated adaptive rule set and attaches source excerpts for the rules it
was able to ground directly in the source text.
"""

from __future__ import annotations

import argparse
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

from app.adaptive_schema import AdaptiveGoldRuleSet
from importers.xlsx_to_program import slugify


def _compress_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def resolve_guide_doc(*, source_pdf: str, provenance_index: Path | None = None) -> Path:
    provenance_path = provenance_index or (REPO_ROOT / "docs" / "guides" / "provenance_index.json")
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    for item in payload.get("provenance", []):
        source_assets = item.get("source_assets") or []
        if source_pdf not in source_assets:
            continue
        for entity in item.get("derived_entities", []):
            if entity.get("type") == "normalized_guide_doc":
                return REPO_ROOT / str(entity["path"])
    raise ValueError(f"No normalized guide doc found for {source_pdf}")


def _find_excerpt(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    start = max(0, match.start() - 80)
    end = min(len(text), match.end() + 160)
    return _compress_whitespace(text[start:end])


def _extract_default_rir_target(text: str) -> int:
    match = re.search(r"leaving\s*(\d+)\s*-\s*(\d+)\s*reps?\s+in\s+the\s+tank", text, re.IGNORECASE)
    if match:
        lower = int(match.group(1))
        upper = int(match.group(2))
        return max(0, round((lower + upper) / 2))

    match = re.search(r"(\d+)\s*-\s*(\d+)\s*reps?\s+shy\s+of\s+failure", text, re.IGNORECASE)
    if match:
        lower = int(match.group(1))
        upper = int(match.group(2))
        return max(0, round((lower + upper) / 2))

    return 2


def _extract_intro_weeks(text: str) -> int:
    match = re.search(r"first\s+(\d+)\s+weeks?", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    if re.search(r"first\s+week", text, re.IGNORECASE):
        return 1
    return 1


def _extract_scheduled_deload_weeks(text: str) -> int | None:
    match = re.search(r"deload\s+every\s+(\d+)\s+weeks?", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"every\s+(\d+)\s+weeks?.{0,40}?deload", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _extract_repeat_failure_trigger(text: str) -> str | None:
    match = re.search(r"after\s+(\d+)\s+failed\s+exposures?", text, re.IGNORECASE)
    if match:
        return f"switch_after_{int(match.group(1))}_failed_exposures"
    return None


def _extract_early_deload_trigger(text: str) -> str | None:
    if re.search(r"three\s+consecutive\s+under\s+target\s+sessions?", text, re.IGNORECASE):
        return "three_consecutive_under_target_sessions"
    if re.search(r"repeated\s+under\s+target.{0,80}high\s+fatigue", text, re.IGNORECASE):
        return "repeated_under_target_plus_high_fatigue"
    return None


def _extract_fatigue_rpe_threshold_condition(text: str) -> str | None:
    match = re.search(
        r"session\s+rpe\s+avg\s*>=\s*(\d+(?:\.\d+)?)\s+for\s+(two|\d+)\s+exposures?",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    threshold = float(match.group(1))
    exposure_token = match.group(2).strip().lower()
    exposure_count = 2 if exposure_token == "two" else int(exposure_token)
    if exposure_count <= 1:
        exposure_phrase = "one exposure"
    elif exposure_count == 2:
        exposure_phrase = "two exposures"
    else:
        exposure_phrase = f"{exposure_count} exposures"
    return f"session_rpe_avg >= {threshold:g} for {exposure_phrase}"


def _starting_load_method(text: str) -> str:
    if re.search(r"1\s*rep\s*max|%1RM|percent\s*1RM", text, re.IGNORECASE):
        return "percent_1rm_reference"
    return "rep_range_rir_start"


def _fallback_percent_estimated_1rm(method: str) -> int:
    return 75 if method == "percent_1rm_reference" else 72


def _source_section(field: str, source_doc: Path, source_pdf: str, excerpt: str | None) -> dict[str, str] | None:
    if not excerpt:
        return None
    try:
        source_doc_value = str(source_doc.relative_to(REPO_ROOT))
    except ValueError:
        source_doc_value = str(source_doc)
    return {
        "field": field,
        "source_doc": source_doc_value,
        "source_pdf": source_pdf,
        "heading": "Excerpt",
        "excerpt": excerpt,
    }


def build_rule_set_payload(
    *,
    program_id: str,
    source_pdf: str,
    guide_doc: Path,
) -> dict[str, Any]:
    text = guide_doc.read_text(encoding="utf-8")
    normalized_text = _compress_whitespace(text)

    starting_method = _starting_load_method(normalized_text)
    default_rir_target = _extract_default_rir_target(normalized_text)
    intro_weeks = _extract_intro_weeks(normalized_text)
    scheduled_deload_weeks = _extract_scheduled_deload_weeks(normalized_text)
    repeat_failure_trigger = _extract_repeat_failure_trigger(normalized_text)
    early_deload_trigger = _extract_early_deload_trigger(normalized_text)
    fatigue_rpe_condition = _extract_fatigue_rpe_threshold_condition(normalized_text)

    intro_excerpt = _find_excerpt(normalized_text, r"first\s+\d+\s+weeks?.{0,120}?reps?\s+in\s+the\s+tank|first\s+week.{0,120}?reps?\s+in\s+the\s+tank")
    intensity_excerpt = _find_excerpt(normalized_text, r"after\s+the\s+first.{0,160}?intensity\s+will\s+increase")
    fatigue_excerpt = _find_excerpt(
        normalized_text,
        r"session\s+rpe\s+avg\s*>=\s*\d+(?:\.\d+)?\s+for\s+(?:two|\d+)\s+exposures?",
    )
    deload_excerpt = _find_excerpt(normalized_text, r"deload\s+every\s+\d+\s+weeks?|every\s+\d+\s+weeks?.{0,40}?deload")
    substitution_excerpt = _find_excerpt(normalized_text, r"exercise\s+substitutions?\s+column")
    progression_excerpt = _find_excerpt(normalized_text, r"progress\s+through\s+the\s+rep\s+ranges?")
    warmup_excerpt = _find_excerpt(normalized_text, r"general\s+warm-?up|exercise-specific\s+warm-?up")

    source_sections = [
        item
        for item in [
            _source_section("starting_load_rules.default_rir_target", guide_doc, source_pdf, intro_excerpt),
            _source_section("starting_load_rules.method", guide_doc, source_pdf, warmup_excerpt or intro_excerpt),
            _source_section("progression_rules.on_success", guide_doc, source_pdf, progression_excerpt),
            _source_section("fatigue_rules.high_fatigue_trigger", guide_doc, source_pdf, fatigue_excerpt or intensity_excerpt),
            _source_section("deload_rules.scheduled_every_n_weeks", guide_doc, source_pdf, deload_excerpt or intro_excerpt),
            _source_section("substitution_rules.equipment_mismatch", guide_doc, source_pdf, substitution_excerpt),
        ]
        if item is not None
    ]

    intro_phrase = f"intro week lasts {intro_weeks} week" if intro_weeks == 1 else f"intro phase lasts {intro_weeks} weeks"
    return {
        "rule_set_id": f"{program_id}_rules",
        "version": "0.1.0",
        "program_scope": [program_id],
        "source_pdf": source_pdf,
        "starting_load_rules": {
            "method": starting_method,
            "default_rir_target": default_rir_target,
            "fallback_percent_estimated_1rm": _fallback_percent_estimated_1rm(starting_method),
        },
        "progression_rules": {
            "success_condition": "reach_top_of_rep_range_then_add_load",
            "on_success": {"action": "increase_load", "percent": 2.5},
            "on_in_range": {"action": "hold_load_chase_reps"},
            "on_under_target": {"action": "hold_or_reduce", "reduce_percent": 2.5, "after_exposures": 2},
        },
        "fatigue_rules": {
            "high_fatigue_trigger": {
                "conditions": [
                    f"{intro_phrase}; avoid interpreting early underperformance as stall",
                    fatigue_rpe_condition or "session_rpe_avg >= 9 for two exposures",
                ]
            },
            "on_high_fatigue": {"action": "reduce_volume", "set_delta": -1},
        },
        "deload_rules": {
            "scheduled_every_n_weeks": max(4, int(scheduled_deload_weeks or (intro_weeks * 3))),
            "early_deload_trigger": early_deload_trigger or "repeated_under_target_plus_high_fatigue",
            "on_deload": {"set_reduction_percent": 35, "load_reduction_percent": 10},
        },
        "substitution_rules": {
            "equipment_mismatch": "use_first_compatible_substitution",
            "repeat_failure_trigger": repeat_failure_trigger or "switch_after_three_failed_exposures",
        },
        "rationale_templates": {
            "increase_load": "Performance exceeded target range. Increase load next exposure.",
            "hold_load": "Performance stayed in range. Hold load and chase the rep ceiling.",
            "reduce_load": "Performance repeatedly fell below target. Reduce load to restore quality.",
            "deload": "Fatigue and underperformance indicate that a short deload is warranted.",
        },
        "source_sections": source_sections,
    }


def distill_rule_set(
    *,
    source_pdf: str,
    program_id: str,
    output_file: Path | None = None,
    guide_doc: Path | None = None,
    provenance_index: Path | None = None,
) -> Path:
    resolved_guide_doc = guide_doc or resolve_guide_doc(source_pdf=source_pdf, provenance_index=provenance_index)
    payload = build_rule_set_payload(program_id=program_id, source_pdf=source_pdf, guide_doc=resolved_guide_doc)
    validated = AdaptiveGoldRuleSet.model_validate(payload)

    destination = output_file or (REPO_ROOT / "docs" / "rules" / "canonical" / f"{program_id}.rules.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(validated.model_dump(mode="json"), indent=2), encoding="utf-8")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Distill normalized guide doctrine into typed adaptive rules")
    parser.add_argument("--source-pdf", type=str, required=True, help="Reference PDF path used as doctrine source")
    parser.add_argument("--program-id", type=str, required=False, help="Rule-set program scope identifier")
    parser.add_argument("--guide-doc", type=Path, default=None, help="Optional normalized guide markdown path")
    parser.add_argument("--output", type=Path, default=None, help="Output JSON path")
    args = parser.parse_args()

    program_id = args.program_id or slugify(Path(args.source_pdf).stem)
    destination = distill_rule_set(
        source_pdf=args.source_pdf,
        program_id=program_id,
        output_file=args.output,
        guide_doc=args.guide_doc,
    )
    print(f"Adaptive rule set written to: {destination}")


if __name__ == "__main__":
    main()
