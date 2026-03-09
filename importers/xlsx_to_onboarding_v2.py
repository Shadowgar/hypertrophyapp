#!/usr/bin/env python3
"""Build-time importer v2 for one-program onboarding packages.

This script emits a structured onboarding package for a single program and validates
it against app-level adaptive schemas. Runtime services must never parse XLSX/PDF.
"""

from __future__ import annotations

import argparse
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

from app.adaptive_schema import ProgramOnboardingPackage
from importers.structured_program_builder import (
    build_exercise_library,
    build_program_blueprint,
    collect_structured_phases_from_workbook,
    collect_sessions_from_workbook,
    default_program_name,
)
from importers.xlsx_to_program import slugify


def build_onboarding_package(
    *,
    input_file: Path,
    source_pdf: str,
    program_id: str,
    total_weeks: int,
    output_file: Path | None,
    sheet_name: str | None,
) -> Path:
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
        "program_intent": {
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
        },
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
