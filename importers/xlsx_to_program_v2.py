#!/usr/bin/env python3
"""Build-time structured exporter for adaptive gold program templates.

This script emits a schema-validated adaptive gold program template plus a
sidecar import report with explicit diagnostics.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.adaptive_schema import AdaptiveGoldProgramTemplate
from importers.structured_program_builder import (
    build_adaptive_gold_program_template,
    build_blueprint_week_template,
    build_import_report,
    collect_structured_phases_from_workbook,
    collect_sessions_from_workbook,
    default_program_name,
)
from importers.xlsx_to_program import slugify, split_from_filename


def build_program_template(
    *,
    input_file: Path,
    program_id: str,
    total_weeks: int,
    output_file: Path | None,
    sheet_name: str | None,
    program_name: str | None = None,
    phase_id: str = "accumulation_1",
    phase_name: str = "Accumulation",
    report_output: Path | None = None,
) -> tuple[Path, Path]:
    sessions, diagnostics, selected_sheet_names = collect_sessions_from_workbook(
        input_file,
        sheet_name=sheet_name,
    )
    structured_phases, structured_diagnostics, _selected_structured_sheet_names = collect_structured_phases_from_workbook(
        input_file,
        sheet_name=sheet_name,
    )
    diagnostics.extend(structured_diagnostics)

    resolved_program_name = program_name or default_program_name(program_id)
    split = split_from_filename(input_file)
    payload = build_adaptive_gold_program_template(
        program_id=program_id,
        program_name=resolved_program_name,
        source_workbook=str(input_file),
        split=split,
        total_weeks=total_weeks,
        session_rows=sessions,
        structured_phases=structured_phases,
        phase_id=phase_id,
        phase_name=phase_name,
    )
    validated = AdaptiveGoldProgramTemplate.model_validate(payload)

    destination = output_file or (REPO_ROOT / "programs" / "gold" / f"{program_id}.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(validated.model_dump(mode="json"), indent=2), encoding="utf-8")

    week_template = build_blueprint_week_template(sessions)
    emitted_week_count = sum(len(phase.weeks) for phase in validated.phases)
    report_destination = report_output or destination.with_name(f"{destination.stem}.import_report.json")
    report_destination.parent.mkdir(parents=True, exist_ok=True)
    report_payload = build_import_report(
        input_file=input_file,
        selected_sheet_names=selected_sheet_names,
        session_rows=sessions,
        diagnostics=diagnostics,
        export_type="adaptive_gold_program_template",
        output_path=destination,
        total_weeks=emitted_week_count,
        phase_count=len(validated.phases),
        day_count=len(week_template["days"]),
    )
    report_destination.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    return destination, report_destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert workbook into adaptive gold program template")
    parser.add_argument("--input", type=Path, required=True, help="Path to source workbook")
    parser.add_argument("--program-id", type=str, required=False, help="Output program identifier")
    parser.add_argument("--program-name", type=str, required=False, help="Human-readable program name")
    parser.add_argument("--weeks", type=int, default=6, help="Number of weeks to emit in the structured template")
    parser.add_argument("--sheet", type=str, default=None, help="Optional workbook sheet filter")
    parser.add_argument("--output", type=Path, default=None, help="Output JSON path")
    parser.add_argument("--report-output", type=Path, default=None, help="Optional diagnostics report path")
    parser.add_argument("--phase-id", type=str, default="accumulation_1", help="Phase identifier")
    parser.add_argument("--phase-name", type=str, default="Accumulation", help="Phase display name")
    args = parser.parse_args()

    input_file = args.input.resolve()
    program_id = args.program_id or slugify(input_file.stem).replace("_sheet", "")
    destination, report_destination = build_program_template(
        input_file=input_file,
        program_id=program_id,
        total_weeks=max(1, args.weeks),
        output_file=args.output,
        sheet_name=args.sheet,
        program_name=args.program_name,
        phase_id=args.phase_id,
        phase_name=args.phase_name,
        report_output=args.report_output,
    )

    print(f"Adaptive gold template written to: {destination}")
    print(f"Import diagnostics written to: {report_destination}")
    print("No runtime dependency on reference files is allowed.")


if __name__ == "__main__":
    main()