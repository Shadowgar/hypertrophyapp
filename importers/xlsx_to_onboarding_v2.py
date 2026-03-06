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
from importers.xlsx_to_program import (
    infer_equipment_tags_from_name,
    parse_sheet_to_sessions,
    read_xlsx_sheets,
    slugify,
)


def _is_structural_session(session_name: str) -> bool:
    lowered = session_name.strip().lower()
    return lowered.startswith("warm up") or lowered.startswith("weak point") or lowered.startswith("block ")


def _is_rest_session(session_name: str) -> bool:
    lowered = session_name.strip().lower()
    return "rest" in lowered


def _slot_role(exercise_name: str, session_name: str) -> str:
    lowered = exercise_name.lower()
    if "weak point" in lowered or "weak point" in session_name.lower():
        return "weak_point"
    if any(token in lowered for token in ("squat", "bench", "deadlift", "pull-up", "pulldown", "press", "row")):
        return "primary_compound"
    if any(token in lowered for token in ("split squat", "rdl", "leg press", "incline")):
        return "secondary_compound"
    if any(token in lowered for token in ("curl", "extension", "raise", "fly", "pushdown", "calf")):
        return "isolation"
    return "accessory"


def _coaching_cues(notes: str | None) -> list[str]:
    if not notes:
        return []
    parts = [part.strip() for part in notes.replace("!", ".").split(".")]
    return [part for part in parts if part][:3]


def _build_week_template(session_rows: list[dict[str, Any]]) -> dict[str, Any]:
    days: list[dict[str, Any]] = []
    day_counter = 0

    for session in session_rows:
        session_name = str(session.get("name") or "").strip()
        if not session_name or _is_structural_session(session_name) or _is_rest_session(session_name):
            continue

        day_counter += 1
        slots: list[dict[str, Any]] = []
        for order_index, exercise in enumerate(session.get("exercises") or [], start=1):
            exercise_name = str(exercise.get("name") or "").strip()
            if not exercise_name:
                continue

            rep_range = exercise.get("rep_range") or [8, 12]
            rep_min = int(rep_range[0]) if rep_range else 8
            rep_max = int(rep_range[1]) if len(rep_range) > 1 else rep_min
            rep_min, rep_max = sorted((rep_min, rep_max))

            video = exercise.get("video") if isinstance(exercise.get("video"), dict) else {}
            notes = exercise.get("notes") if isinstance(exercise.get("notes"), str) else None
            primary_muscles = [str(m) for m in (exercise.get("primary_muscles") or []) if str(m).strip()]

            slots.append(
                {
                    "slot_id": f"d{day_counter}_s{order_index}",
                    "order_index": order_index,
                    "exercise_id": str(exercise.get("primary_exercise_id") or exercise.get("id") or slugify(exercise_name)),
                    "slot_role": _slot_role(exercise_name, session_name),
                    "primary_muscles": primary_muscles,
                    "video_url": str(video.get("youtube_url") or "") or None,
                    "warmup_prescription": [
                        {"percent": 50, "reps": 8},
                        {"percent": 70, "reps": 5},
                    ],
                    "work_sets": [
                        {
                            "set_type": "work",
                            "sets": int(exercise.get("sets") or 3),
                            "rep_target": {"min": rep_min, "max": rep_max},
                            "rir_target": 2,
                        }
                    ],
                    "notes": notes,
                }
            )

        if not slots:
            continue

        days.append(
            {
                "day_id": f"d{day_counter}",
                "day_name": session_name,
                "slots": slots,
            }
        )

    return {"week_template_id": "week_base", "days": days}


def _build_exercise_library(session_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    entries: list[dict[str, Any]] = []

    for session in session_rows:
        session_name = str(session.get("name") or "")
        for exercise in session.get("exercises") or []:
            exercise_name = str(exercise.get("name") or "").strip()
            if not exercise_name:
                continue

            exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or slugify(exercise_name))
            if exercise_id in seen:
                continue
            seen.add(exercise_id)

            substitutions = [
                {
                    "exercise_id": slugify(str(candidate)),
                    "rationale": "Workbook substitution option",
                    "equipment_tags": infer_equipment_tags_from_name(str(candidate)),
                }
                for candidate in (exercise.get("substitution_candidates") or [])
                if str(candidate).strip()
            ]

            notes = exercise.get("notes") if isinstance(exercise.get("notes"), str) else ""
            movement_pattern = str(exercise.get("movement_pattern") or "accessory")
            video = exercise.get("video") if isinstance(exercise.get("video"), dict) else {}

            entries.append(
                {
                    "exercise_id": exercise_id,
                    "canonical_name": exercise_name,
                    "aliases": [exercise_name],
                    "execution": notes or "Execute with controlled tempo and full range of motion.",
                    "coaching_cues": _coaching_cues(notes),
                    "primary_muscles": [str(m) for m in (exercise.get("primary_muscles") or []) if str(m).strip()],
                    "secondary_muscles": [],
                    "equipment_tags": infer_equipment_tags_from_name(exercise_name),
                    "movement_pattern": movement_pattern,
                    "valid_substitutions": substitutions,
                    "default_video_url": str(video.get("youtube_url") or "") or None,
                    "slot_usage_rationale": f"Used in {session_name} to preserve session intent and progression continuity.",
                }
            )

    return entries


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

    selected = sheets
    if sheet_name:
        selected = [sheet for sheet in sheets if sheet.name == sheet_name]
        if not selected:
            raise ValueError(f"Sheet '{sheet_name}' not found in {input_file.name}")

    sessions: list[dict[str, Any]] = []
    for sheet in selected:
        sessions.extend(parse_sheet_to_sessions(sheet))

    if not sessions:
        raise ValueError("No sessions parsed from workbook")

    week_template = _build_week_template(sessions)
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
        "blueprint": {
            "program_id": program_id,
            "program_name": " ".join(part.capitalize() for part in program_id.split("_")),
            "source_workbook": str(input_file),
            "split": "full_body",
            "default_training_days": 5,
            "total_weeks": total_weeks,
            "week_sequence": ["week_base" for _ in range(total_weeks)],
            "week_templates": [week_template],
        },
        "exercise_library": _build_exercise_library(sessions),
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
