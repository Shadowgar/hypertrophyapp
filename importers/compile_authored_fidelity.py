"""Compile the two authorized Full Body sources into explicit review outputs.

Source workbooks stay read-only. Existing onboarding guidance and exercise
metadata are retained; source-derived slots and structure are rebuilt.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
for directory in (REPO_ROOT, REPO_ROOT / "apps/api", REPO_ROOT / "packages/core-engine"):
    sys.path.insert(0, str(directory))

from app.adaptive_schema import ProgramOnboardingPackage
from importers.authored_lineage import artifact_json, artifact_sha256
from importers.structured_program_builder import (
    build_exercise_library, build_program_blueprint,
    collect_sessions_from_workbook, collect_structured_phases_from_workbook,
)
from importers.xlsx_to_program import read_xlsx_sheets
from importers.xlsx_to_program_v2 import build_program_template
from importers.xlsx_to_onboarding_v2 import _apply_workbook_structure_to_blueprint


def compile_sources(source_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for phase in (1, 2):
        program_id = f"pure_bodybuilding_phase_{phase}_full_body"
        source = source_dir / f"Pure Bodybuilding Phase {phase} - Full Body Sheet.xlsx"
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        # Read the companion before emitting, including when output_dir is the gold directory.
        companion = json.loads((REPO_ROOT / "programs/gold" / f"{program_id}.onboarding.json").read_text())
        template_path, _ = build_program_template(
            input_file=source, program_id=program_id, total_weeks=10,
            output_file=output_dir / f"{program_id}.json", sheet_name="Full Body",
            program_name=f"Hypertrophy Phase {phase}",
            report_output=output_dir / f"{program_id}.import_report.json",
        )
        template = json.loads(template_path.read_text())
        template["source_workbook"] = "reference/" + source.name
        template["source_provenance"]["artifact_sha256"] = artifact_sha256(template)
        template_path.write_text(artifact_json(template))
        phases, _, _ = collect_structured_phases_from_workbook(source, sheet_name="Full Body")
        sessions, _, _ = collect_sessions_from_workbook(source, sheet_name="Full Body")
        blueprint = build_program_blueprint(
            program_id=program_id, program_name=template["program_name"],
            source_workbook=template["source_workbook"], split="full_body", total_weeks=10,
            session_rows=sessions, structured_phases=phases,
        )
        sheet = next(sheet for sheet in read_xlsx_sheets(source) if sheet.name == "Full Body")
        blueprint = _apply_workbook_structure_to_blueprint(blueprint, rows=sheet.rows)
        for field in ("week_templates", "week_sequence", "total_weeks", "source_workbook"):
            companion["blueprint"][field] = blueprint[field]
        weeks = [week for phase in template["phases"] for week in phase["weeks"]]
        for week, canonical_week in zip(companion["blueprint"]["week_templates"], weeks, strict=True):
            for day, canonical_day in zip(week["days"], canonical_week["days"], strict=True):
                for slot, canonical_slot in zip(day["slots"], canonical_day["slots"], strict=True):
                    slot["source_lineage"] = canonical_slot["source_lineage"]
                    slot["authored_prescription"] = canonical_slot["authored_prescription"]
        existing_ids = {entry["exercise_id"] for entry in companion["exercise_library"]}
        for entry in build_exercise_library(sessions):
            if entry["exercise_id"] not in existing_ids:
                companion["exercise_library"].append(entry)
                if "exercise_catalog" in companion:
                    companion["exercise_catalog"].append(entry)
        companion["version"] = "0.3.0"
        companion["source_provenance"] = {
            **template["source_provenance"],
            "canonical_artifact_sha256": template["source_provenance"]["artifact_sha256"],
        }
        companion["source_provenance"]["artifact_sha256"] = artifact_sha256(companion)
        ProgramOnboardingPackage.model_validate(companion)
        (output_dir / f"{program_id}.onboarding.json").write_text(artifact_json(companion))
        if source_hash != hashlib.sha256(source.read_bytes()).hexdigest():
            raise ValueError("Source changed during compilation")
        count = sum(len(day["slots"]) for week in weeks for day in week["days"])
        print(f"Phase {phase}: compiled {count} rows; source unchanged")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    compile_sources(args.source_dir, args.output_dir)


if __name__ == "__main__":
    main()
