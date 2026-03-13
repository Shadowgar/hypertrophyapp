#!/usr/bin/env python3
"""Build-time importer v2 for one-program onboarding packages.

This script emits a structured onboarding package for a single program and validates
it against app-level adaptive schemas. Runtime services must never parse XLSX/PDF.
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

from app.adaptive_schema import ProgramOnboardingPackage
from importers.structured_program_builder import (
    build_exercise_library,
    build_program_blueprint,
    collect_structured_phases_from_workbook,
    collect_sessions_from_workbook,
    default_program_name,
)
from importers.xlsx_to_program import read_xlsx_sheets, slugify


def _normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def _first_non_empty_cell(row: list[str]) -> str:
    for value in row:
        if value.strip():
            return value.strip()
    return ""


def _row_text(row: list[str]) -> str:
    return " ".join(value.strip() for value in row if value.strip())


def _find_row_index(rows: list[list[str]], label: str) -> int | None:
    normalized_label = _normalize_label(label)
    for index, row in enumerate(rows):
        if any(
            _normalize_label(value) == normalized_label or _normalize_label(value).startswith(normalized_label)
            for value in row
            if value.strip()
        ):
            return index
    return None


def _parse_important_program_notes(rows: list[list[str]]) -> list[str]:
    section_index = _find_row_index(rows, "IMPORTANT PROGRAM NOTES (READ BEFORE STARTING)")
    if section_index is None:
        return []
    raw_text = _row_text(rows[section_index])
    if "•" not in raw_text:
        return []
    return [part.strip() for part in raw_text.split("•")[1:] if part.strip()]


def _collect_instruction_rows(rows: list[list[str]], start_index: int, end_index: int) -> list[dict[str, str]]:
    instructions: list[dict[str, str]] = []
    for row in rows[start_index:end_index]:
        values = [value.strip() for value in row if value.strip()]
        if len(values) < 2:
            continue
        instructions.append({"label": values[0], "instruction": values[1]})
    return instructions


def _parse_warm_up_protocol(rows: list[list[str]]) -> dict[str, Any] | None:
    general_index = _find_row_index(rows, "General Warm-Up")
    specific_index = _find_row_index(rows, "Exercise-Specific Warm-Up")
    weak_points_index = _find_row_index(rows, "WEAK POINTS TABLE")
    if general_index is None or specific_index is None or weak_points_index is None:
        return None
    return {
        "general_warm_up_intro": _row_text(rows[general_index + 1]) if general_index + 1 < len(rows) else None,
        "general_warm_up": _collect_instruction_rows(rows, general_index + 2, specific_index),
        "exercise_specific_warm_up_intro": _row_text(rows[specific_index + 1]) if specific_index + 1 < len(rows) else None,
        "exercise_specific_warm_up": _collect_instruction_rows(rows, specific_index + 2, weak_points_index),
    }


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value.strip()))


def _parse_weak_points_table(rows: list[list[str]]) -> list[dict[str, Any]]:
    section_index = _find_row_index(rows, "WEAK POINTS TABLE")
    if section_index is None:
        return []

    block_index = None
    for index in range(section_index + 1, len(rows)):
        first_value = _first_non_empty_cell(rows[index])
        if _normalize_label(first_value).startswith("block "):
            block_index = index
            break
    if block_index is None:
        block_index = len(rows)

    header_index = None
    for index in range(section_index + 1, block_index):
        normalized_values = [_normalize_label(value) for value in rows[index] if value.strip()]
        if "weak point" in normalized_values and any("exercise 1 options" in value for value in normalized_values):
            header_index = index
            break
    if header_index is None:
        return []

    entries: list[dict[str, Any]] = []
    current_entry: dict[str, Any] | None = None
    for row in rows[header_index + 1 : block_index]:
        weak_point = row[4].strip() if len(row) > 4 else ""
        exercise_1 = row[5].strip() if len(row) > 5 else ""
        exercise_2 = row[11].strip() if len(row) > 11 else ""
        if not any((weak_point, exercise_1, exercise_2)):
            continue

        if weak_point:
            current_entry = {
                "weak_point": weak_point,
                "exercise_1_options": [],
                "exercise_2_options": [],
                "guidance": [],
            }
            entries.append(current_entry)

        if current_entry is None:
            continue

        for value, key in ((exercise_1, "exercise_1_options"), (exercise_2, "exercise_2_options")):
            if not value:
                continue
            if re.match(r"^\d+\.\s", value):
                current_entry[key].append(value)
            else:
                current_entry["guidance"].append(value)

    for entry in entries:
        entry["exercise_1_options"] = _dedupe_preserve_order(entry["exercise_1_options"])
        entry["exercise_2_options"] = _dedupe_preserve_order(entry["exercise_2_options"])
        entry["guidance"] = _dedupe_preserve_order(entry["guidance"])
    return entries


def _parse_week_template_metadata(rows: list[list[str]]) -> dict[int, dict[str, Any]]:
    metadata: dict[int, dict[str, Any]] = {}
    current_block_label: str | None = None
    pending_banners: list[str] = []

    for row in rows:
        first_value = _first_non_empty_cell(row)
        normalized = _normalize_label(first_value)
        if not normalized:
            continue
        if normalized.startswith("block "):
            current_block_label = first_value
            continue
        if normalized.startswith("semi deload") or normalized.startswith("deload week"):
            pending_banners.append(first_value)
            continue

        week_match = re.match(r"week\s*(\d+)$", normalized)
        if not week_match:
            continue

        week_index = int(week_match.group(1))
        metadata[week_index] = {
            "block_label": current_block_label,
            "week_label": first_value,
            "special_banners": list(pending_banners),
        }
        pending_banners = []

    return metadata


def _apply_workbook_structure_to_blueprint(
    blueprint: dict[str, Any],
    *,
    rows: list[list[str]],
) -> dict[str, Any]:
    blueprint["important_program_notes"] = _parse_important_program_notes(rows)
    blueprint["warm_up_protocol"] = _parse_warm_up_protocol(rows)
    blueprint["weak_points_table"] = _parse_weak_points_table(rows)

    week_metadata = _parse_week_template_metadata(rows)
    for template_index, week_template in enumerate(blueprint.get("week_templates") or [], start=1):
        metadata = week_metadata.get(template_index, {})
        week_template["block_label"] = metadata.get("block_label")
        week_template["week_label"] = metadata.get("week_label")
        week_template["special_banners"] = metadata.get("special_banners", [])

    return blueprint


def _is_pure_bodybuilding_phase1_full_body_workbook(*, input_file: Path, rows: list[list[str]]) -> bool:
    workbook_title = _normalize_label(_first_non_empty_cell(rows[0])) if rows else ""
    return input_file.name == "Pure Bodybuilding Phase 1 - Full Body Sheet.xlsx" or (
        "the pure bodybuilding program full body" in workbook_title
    )


def _build_program_intent(*, program_id: str, input_file: Path, rows: list[list[str]]) -> dict[str, Any]:
    if _is_pure_bodybuilding_phase1_full_body_workbook(input_file=input_file, rows=rows):
        return {
            "program_id": program_id,
            "phase_goal": "Drive hypertrophy across four full-body days plus an Arms & Weak Points day.",
            "progression_philosophy": (
                "Progress through the authored rep ranges given in the program and use The Hypertrophy Handbook "
                "for the detailed progression and substitution rules."
            ),
            "fatigue_management": (
                "Use the first 2 weeks as the authored adaptation ramp with fewer intensity techniques before "
                "pushing harder after the first 2 weeks."
            ),
            "non_negotiables": [
                "Preserve the authored four full-body training days.",
                "Preserve the Arms & Weak Points day structure.",
                "Preserve the authored weak-point table as the source of optional weak-point exercise choices.",
            ],
            "flexible_elements": [
                "Weak Point Exercise 2 only when recovered enough to use the optional second weak-point slot.",
                "Exercise substitutions follow the authored substitution columns and handbook guidance.",
            ],
            "preserve_when_frequency_reduced": [],
        }

    return {
        "program_id": program_id,
        "phase_goal": "Drive hypertrophy across all major muscle groups with high-quality weekly full-body exposure.",
        "progression_philosophy": "Double progression with conservative load increases after top-end rep attainment.",
        "fatigue_management": "Use scheduled recovery and temporary volume reduction when readiness drops.",
        "non_negotiables": [
            "Preserve weekly full-body coverage.",
            "Preserve priority compounds before accessories.",
            "Preserve weak-point stimulus under compression.",
        ],
        "flexible_elements": [
            "Accessory isolation slot count.",
            "Session exercise ordering among non-priority slots.",
            "Temporary set reductions during fatigue spikes.",
        ],
        "preserve_when_frequency_reduced": [
            "Primary compound slots.",
            "Weak-point chest and hamstrings coverage.",
            "Progression continuity for carried lifts.",
        ],
    }


def build_onboarding_package(
    *,
    input_file: Path,
    source_pdf: str,
    program_id: str,
    total_weeks: int,
    output_file: Path | None,
    sheet_name: str | None,
) -> Path:
    sheets = read_xlsx_sheets(input_file)
    if not sheets:
        raise ValueError(f"No readable worksheets found in {input_file}")
    selected_sheets = sheets if sheet_name is None else [sheet for sheet in sheets if sheet.name == sheet_name]
    if sheet_name and not selected_sheets:
        raise ValueError(f"Sheet '{sheet_name}' not found in {input_file.name}")

    sessions, _diagnostics, _selected_sheet_names = collect_sessions_from_workbook(
        input_file,
        sheet_name=sheet_name,
    )
    structured_phases, _structured_diagnostics, _structured_sheet_names = collect_structured_phases_from_workbook(
        input_file,
        sheet_name=sheet_name,
    )

    if not sessions:
        raise ValueError("No sessions parsed from workbook")

    blueprint = build_program_blueprint(
        program_id=program_id,
        program_name=default_program_name(program_id),
        source_workbook=str(input_file),
        split="full_body",
        total_weeks=total_weeks,
        session_rows=sessions,
        structured_phases=structured_phases,
    )
    blueprint = _apply_workbook_structure_to_blueprint(
        blueprint,
        rows=selected_sheets[0].rows,
    )
    week_template = blueprint["week_templates"][0]
    if not week_template["days"]:
        raise ValueError("No valid training days parsed from workbook")
    if len(week_template["days"]) < 3:
        raise ValueError(
            "Workbook parsing produced too few training days for reliable onboarding package generation; "
            "manual curation is required for this program."
        )

    package = {
        "program_id": program_id,
        "version": "0.2.0",
        "source_pdf": source_pdf,
        "blueprint": blueprint,
        "exercise_library": build_exercise_library(sessions),
        "program_intent": _build_program_intent(program_id=program_id, input_file=input_file, rows=selected_sheets[0].rows),
        "frequency_adaptation_rules": {
            "default_training_days": 5,
            "minimum_temporary_days": 3,
            "max_temporary_weeks": 2,
            "preserve_slot_roles": ["primary_compound", "secondary_compound", "weak_point"],
            "reduce_slot_roles_first": ["isolation", "accessory"],
            "weak_area_bonus_slots": 1,
            "daily_slot_cap_when_compressed": 8,
            "coverage_targets": [
                {"muscle_group": "chest", "minimum_weekly_slots": 2},
                {"muscle_group": "back", "minimum_weekly_slots": 2},
                {"muscle_group": "quads", "minimum_weekly_slots": 2},
                {"muscle_group": "hamstrings", "minimum_weekly_slots": 2},
                {"muscle_group": "shoulders", "minimum_weekly_slots": 2},
            ],
            "reintegration_policy": "Return to original 5-day template at next week boundary; keep progression state from compressed weeks.",
        },
    }

    validated = ProgramOnboardingPackage.model_validate(package)

    destination = output_file or (REPO_ROOT / "programs" / "gold" / f"{program_id}.onboarding.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(validated.model_dump(mode="json"), indent=2), encoding="utf-8")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert one workbook into onboarding package v2")
    parser.add_argument("--input", type=Path, required=True, help="Path to source workbook")
    parser.add_argument("--source-pdf", type=str, required=True, help="Source PDF path used for doctrine rules")
    parser.add_argument("--program-id", type=str, required=False, help="Output program identifier")
    parser.add_argument("--weeks", type=int, default=10, help="Total weeks in authored program")
    parser.add_argument("--sheet", type=str, default=None, help="Optional workbook sheet filter")
    parser.add_argument("--output", type=Path, default=None, help="Output onboarding package JSON path")
    args = parser.parse_args()

    input_file = args.input.resolve()
    program_id = args.program_id or slugify(input_file.stem).replace("_sheet", "")

    destination = build_onboarding_package(
        input_file=input_file,
        source_pdf=args.source_pdf,
        program_id=program_id,
        total_weeks=max(1, args.weeks),
        output_file=args.output,
        sheet_name=args.sheet,
    )

    print(f"Onboarding package written to: {destination}")


if __name__ == "__main__":
    main()
