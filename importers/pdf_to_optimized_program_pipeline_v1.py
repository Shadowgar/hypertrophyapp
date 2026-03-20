#!/usr/bin/env python3
"""
PDF -> canonical artifacts pipeline (optimized program, v1)

This pipeline is designed to produce the same kinds of canonical artifacts
you already use for Phase 1/2:
  - programs/gold/<program_id>.json (+ .import_report.json, .onboarding.json)
  - docs/rules/canonical/<program_id>.rules.json (+ .distillation_report.json)
  - evidence/validation parity matrix JSON

It reuses existing, schema-validating building blocks:
  - importers/xlsx_to_canonical_v2.py (template + onboarding from XLSX)
  - importers/pdf_doctrine_rules_v2.py (typed rules distillation from PDF)
  - apps/api/app/program_loader.py contract checks (metadata safety contract)

Loader activation is intentionally gated:
  - If --activate is passed AND contract validation succeeds, the script writes:
      programs/active_administered_program_ids.json
      programs/contract_enforced_template_ids.json
    These files are UNION'ed with existing defaults by program_loader at runtime.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from datetime import date


REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


from importers.pdf_doctrine_rules_v2 import distill_rule_set_v2
from importers.xlsx_to_canonical_v2 import run_canonical_import
from app.template_schema import CanonicalProgramTemplate
from app.program_loader import _validate_active_template_metadata_contract


def _read_json_list(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def _write_json_list(path: Path, values: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(set(values)), indent=2) + "\n", encoding="utf-8")


def _validate_template_contract(*, template_payload: dict[str, Any], program_id: str) -> tuple[bool, str | None]:
    try:
        _validate_active_template_metadata_contract(template_payload, template_id=program_id)
        return True, None
    except Exception as exc:  # pragma: no cover - error path
        return False, str(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF -> canonical optimized program pipeline (v1)")
    parser.add_argument("--source-pdf", type=Path, required=True, help="Source PDF for doctrine rules distillation")
    parser.add_argument("--input-xlsx", type=Path, required=True, help="Program workbook providing week/day exercise structure")
    parser.add_argument("--program-id", type=str, required=True, help="Canonical program scope identifier")
    parser.add_argument("--program-name", type=str, default=None, help="Optional human-readable program name")
    parser.add_argument("--weeks", type=int, default=10, help="Total weeks in authored program")
    parser.add_argument("--sheet", type=str, default=None, help="Optional workbook sheet filter")
    parser.add_argument("--phase-id", type=str, default="accumulation_1", help="Default phase id for template builder")
    parser.add_argument("--phase-name", type=str, default="Accumulation", help="Default phase display name")
    parser.add_argument("--output-dir", type=Path, default=None, help="Override programs/gold output dir")
    parser.add_argument("--activate", action="store_true", help="Enable loader activation after passing validation")
    parser.add_argument(
        "--provenance-index",
        type=Path,
        default=REPO_ROOT / "docs" / "guides" / "provenance_index.json",
        help="Provenance index for resolving the normalized guide doc from --source-pdf",
    )
    parser.add_argument(
        "--guide-doc",
        type=Path,
        default=None,
        help="Optional explicit normalized guide markdown path. If omitted, provenance index is used.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=None,
        help="Optional parity matrix output path (default: programs/gold/<program-id>.parity_matrix.json).",
    )
    args = parser.parse_args()

    template_dir = args.output_dir or (REPO_ROOT / "programs" / "gold")
    rules_dir = REPO_ROOT / "docs" / "rules" / "canonical"
    parity_out = args.report_output or (template_dir / f"{args.program_id}.parity_matrix.json")

    # 1) Canonical template + onboarding from XLSX.
    template_results = run_canonical_import(
        input_file=args.input_xlsx,
        program_id=args.program_id,
        total_weeks=max(1, args.weeks),
        source_pdf=str(args.source_pdf),
        sheet_name=args.sheet,
        program_name=args.program_name,
        phase_id=args.phase_id,
        phase_name=args.phase_name,
        output_dir=template_dir,
        template_only=False,
    )
    template_path = Path(template_results["template"])
    template_report_path = Path(template_results["template_report"])

    template_payload = json.loads(template_path.read_text(encoding="utf-8"))
    template_report = json.loads(template_report_path.read_text(encoding="utf-8"))

    # 2) Contract + schema validation for emitted template.
    template_schema_passed = True
    template_schema_error: str | None = None
    try:
        CanonicalProgramTemplate.model_validate(template_payload)
    except Exception as exc:
        template_schema_passed = False
        template_schema_error = str(exc)

    contract_passed, contract_error = (False, "template_schema_failed") if not template_schema_passed else (
        _validate_template_contract(template_payload=template_payload, program_id=args.program_id)
    )

    # 3) Typed canonical doctrine rules distillation from PDF.
    rules_path, distillation_report_path = distill_rule_set_v2(
        source_pdf=str(args.source_pdf),
        program_id=args.program_id,
        output_file=rules_dir / f"{args.program_id}.rules.json",
        guide_doc=args.guide_doc,
        provenance_index=args.provenance_index,
        report_output=None,
    )
    distillation_report = json.loads(distillation_report_path.read_text(encoding="utf-8"))

    # 4) Parity matrix (evidence/validation summary).
    activation_requested = bool(args.activate)
    activation_written = False

    if activation_requested and contract_passed:
        active_path = REPO_ROOT / "programs" / "active_administered_program_ids.json"
        contract_path = REPO_ROOT / "programs" / "contract_enforced_template_ids.json"

        current_active = _read_json_list(active_path)
        current_contract = _read_json_list(contract_path)

        _write_json_list(active_path, current_active + [args.program_id])
        _write_json_list(contract_path, current_contract + [args.program_id])
        activation_written = True

    parity_matrix = {
        "pipeline": "pdf_to_optimized_program_pipeline_v1",
        "date": date.today().isoformat(),
        "program_id": args.program_id,
        "input_xlsx": str(args.input_xlsx),
        "source_pdf": str(args.source_pdf),
        "artifacts": {
            "template": str(template_path),
            "template_report": str(template_report_path),
            "rules": str(rules_path),
            "distillation_report": str(distillation_report_path),
        },
        "template_validation": {
            "schema_passed": template_schema_passed,
            "schema_error": template_schema_error,
            "contract_passed": contract_passed,
            "contract_error": contract_error,
            "template_import_diagnostics_count": template_report.get("diagnostics_count"),
            "template_import_diagnostics": template_report.get("diagnostics"),
        },
        "rules_validation": {
            "distillation_sections_matched": distillation_report.get("sections_matched"),
            "distillation_sections_matched_count": distillation_report.get("sections_matched_count"),
            "distillation_diagnostics_count": distillation_report.get("diagnostics_count"),
            "distillation_diagnostics": distillation_report.get("diagnostics"),
        },
        "loader_activation": {
            "requested": activation_requested,
            "written": activation_written,
            "active_administered_program_ids_file": str(REPO_ROOT / "programs" / "active_administered_program_ids.json"),
            "contract_enforced_template_ids_file": str(REPO_ROOT / "programs" / "contract_enforced_template_ids.json"),
        },
    }

    parity_out.parent.mkdir(parents=True, exist_ok=True)
    parity_out.write_text(json.dumps(parity_matrix, indent=2), encoding="utf-8")

    print(f"[OK] Template: {template_path}")
    print(f"[OK] Rules: {rules_path}")
    print(f"[OK] Parity matrix: {parity_out}")
    if activation_requested and not contract_passed:
        print("[WARN] Activation requested but template contract validation failed; no activation files were written.")


if __name__ == "__main__":
    main()

