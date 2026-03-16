#!/usr/bin/env python3
"""Unified canonical importer v2 — single entrypoint for program template + onboarding.

Reads one XLSX workbook and produces:
  1. Adaptive gold program template JSON (programs/gold/<program_id>.json)
  2. Onboarding package JSON (programs/gold/<program_id>.onboarding.json)
  3. Import diagnostics report JSON (programs/gold/<program_id>.import_report.json)

All outputs are schema-validated against AdaptiveGoldProgramTemplate and
ProgramOnboardingPackage. Runtime must never parse raw XLSX.

Usage:
  python importers/xlsx_to_canonical_v2.py \
    --input reference/<workbook>.xlsx \
    --source-pdf reference/<manual>.pdf \
    --program-id pure_bodybuilding_phase_1_full_body \
    --weeks 10

  # Template-only mode (skip onboarding):
  python importers/xlsx_to_canonical_v2.py --input ... --template-only
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.adaptive_schema import AdaptiveGoldProgramTemplate, ProgramOnboardingPackage
from importers.xlsx_to_program import slugify, split_from_filename
from importers.xlsx_to_program_v2 import build_program_template
from importers.xlsx_to_onboarding_v2 import build_onboarding_package


def _build_unified_report(
    *,
    input_file: Path,
    program_id: str,
    template_path: Path,
    template_report_path: Path,
    onboarding_path: Path | None,
    diagnostics: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "importer": "xlsx_to_canonical_v2",
        "version": "2.0.0",
        "date": date.today().isoformat(),
        "input_file": str(input_file),
        "program_id": program_id,
        "outputs": {
            "template": str(template_path),
            "template_report": str(template_report_path),
            "onboarding": str(onboarding_path) if onboarding_path else None,
        },
        "diagnostics": diagnostics,
        "diagnostics_count": len(diagnostics),
    }


def run_canonical_import(
    *,
    input_file: Path,
    program_id: str,
    total_weeks: int,
    source_pdf: str = "",
    sheet_name: str | None = None,
    program_name: str | None = None,
    phase_id: str = "accumulation_1",
    phase_name: str = "Accumulation",
    output_dir: Path | None = None,
    template_only: bool = False,
) -> dict[str, Path]:
    """Run the canonical v2 import pipeline.

    Returns dict with keys: template, template_report, onboarding (if not template_only),
    and unified_report.
    """
    dest_dir = output_dir or (REPO_ROOT / "programs" / "gold")
    dest_dir.mkdir(parents=True, exist_ok=True)

    diagnostics: list[dict[str, str]] = []

    template_path, template_report_path = build_program_template(
        input_file=input_file,
        program_id=program_id,
        total_weeks=total_weeks,
        output_file=dest_dir / f"{program_id}.json",
        sheet_name=sheet_name,
        program_name=program_name,
        phase_id=phase_id,
        phase_name=phase_name,
        report_output=dest_dir / f"{program_id}.import_report.json",
    )

    report_data = json.loads(template_report_path.read_text(encoding="utf-8"))
    if report_data.get("diagnostics"):
        for diag in report_data["diagnostics"]:
            diagnostics.append({
                "source": "template_builder",
                "code": diag.get("code", "unknown"),
                "message": diag.get("message", str(diag)),
            })

    results: dict[str, Path] = {
        "template": template_path,
        "template_report": template_report_path,
    }

    onboarding_path: Path | None = None
    if not template_only:
        if not source_pdf:
            diagnostics.append({
                "source": "canonical_pipeline",
                "code": "missing_source_pdf",
                "message": "No --source-pdf provided; onboarding package requires a source_pdf reference.",
            })
        else:
            try:
                onboarding_path = build_onboarding_package(
                    input_file=input_file,
                    source_pdf=source_pdf,
                    program_id=program_id,
                    total_weeks=total_weeks,
                    output_file=dest_dir / f"{program_id}.onboarding.json",
                    sheet_name=sheet_name,
                )
                results["onboarding"] = onboarding_path
            except Exception as exc:
                diagnostics.append({
                    "source": "onboarding_builder",
                    "code": "onboarding_build_error",
                    "message": str(exc),
                })

    unified_report = _build_unified_report(
        input_file=input_file,
        program_id=program_id,
        template_path=template_path,
        template_report_path=template_report_path,
        onboarding_path=onboarding_path,
        diagnostics=diagnostics,
    )

    unified_report_path = dest_dir / f"{program_id}.canonical_import_report.json"
    unified_report_path.write_text(json.dumps(unified_report, indent=2), encoding="utf-8")
    results["unified_report"] = unified_report_path

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Canonical v2 importer: XLSX → program template + onboarding package"
    )
    parser.add_argument("--input", type=Path, required=True, help="Path to source XLSX workbook")
    parser.add_argument("--program-id", type=str, required=False, help="Output program identifier")
    parser.add_argument("--program-name", type=str, required=False, help="Human-readable program name")
    parser.add_argument("--source-pdf", type=str, default="", help="Source PDF path for doctrine rules reference")
    parser.add_argument("--weeks", type=int, default=10, help="Total weeks in authored program")
    parser.add_argument("--sheet", type=str, default=None, help="Optional workbook sheet filter")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory (default: programs/gold/)")
    parser.add_argument("--phase-id", type=str, default="accumulation_1", help="Phase identifier")
    parser.add_argument("--phase-name", type=str, default="Accumulation", help="Phase display name")
    parser.add_argument("--template-only", action="store_true", help="Only produce template (skip onboarding)")
    args = parser.parse_args()

    input_file = args.input.resolve()
    program_id = args.program_id or slugify(input_file.stem).replace("_sheet", "")

    results = run_canonical_import(
        input_file=input_file,
        program_id=program_id,
        total_weeks=max(1, args.weeks),
        source_pdf=args.source_pdf,
        sheet_name=args.sheet,
        program_name=args.program_name,
        phase_id=args.phase_id,
        phase_name=args.phase_name,
        output_dir=args.output_dir,
        template_only=args.template_only,
    )

    print(f"Canonical importer v2 results for {program_id}:")
    for key, path in results.items():
        print(f"  {key}: {path}")
    print("Runtime must never parse raw XLSX/PDF files.")


if __name__ == "__main__":
    main()
