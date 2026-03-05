import json
from pathlib import Path
from pydantic import ValidationError

from .config import settings
from .template_schema import CanonicalProgramTemplate


PROGRAM_DESCRIPTIONS: dict[str, str] = {
    "full_body_v1": "Pure Bodybuilding-inspired full body structure with deterministic day templates.",
    "ppl_v1": "Push/Pull/Legs baseline template for balanced hypertrophy progression.",
    "upper_lower_v1": "Upper/Lower split with clear weekly distribution and recovery spacing.",
    "edited_ppl_5x": "Imported higher-frequency PPL variant derived from reference spreadsheet data.",
    "powerbuilding_3_0": "Powerbuilding 3.0 progression template from reference workbook.",
    "pure_bodybuilding_full_body": "Pure Bodybuilding full body template from reference workbook.",
    "pure_bodybuilding_phase_2_full_body_sheet": "Pure Bodybuilding Phase 2 full body variant from reference workbook.",
    "pure_bodybuilding_phase_2_full_body_sheet_1": "Pure Bodybuilding Phase 2 full body alternate sheet variant.",
    "pure_bodybuilding_phase_2_ppl_sheet": "Pure Bodybuilding Phase 2 Push/Pull/Legs variant from reference workbook.",
    "pure_bodybuilding_phase_2_upper_lower_sheet": "Pure Bodybuilding Phase 2 upper/lower split variant.",
    "the_ultimate_push_pull_legs_system_4x": "Ultimate Push Pull Legs System — 4 day frequency variant.",
    "the_ultimate_push_pull_legs_system_5x": "Ultimate Push Pull Legs System — 5 day frequency variant.",
    "the_ultimate_push_pull_legs_system_6x": "Ultimate Push Pull Legs System — 6 day frequency variant.",
    "the_bodybuilding_transformation_system_beginner": "Bodybuilding Transformation System — beginner track.",
    "the_bodybuilding_transformation_system_intermediate_advanced": "Bodybuilding Transformation System — intermediate/advanced track.",
}

PROGRAM_NAMES: dict[str, str] = {
    "full_body_v1": "Full Body v1",
    "ppl_v1": "Push Pull Legs v1",
    "upper_lower_v1": "Upper Lower v1",
    "edited_ppl_5x": "Edited PPL 5x",
    "powerbuilding_3_0": "Powerbuilding 3.0",
    "pure_bodybuilding_full_body": "Pure Bodybuilding — Full Body",
    "pure_bodybuilding_phase_2_full_body_sheet": "Pure Bodybuilding Phase 2 — Full Body",
    "pure_bodybuilding_phase_2_full_body_sheet_1": "Pure Bodybuilding Phase 2 — Full Body (Alt)",
    "pure_bodybuilding_phase_2_ppl_sheet": "Pure Bodybuilding Phase 2 — PPL",
    "pure_bodybuilding_phase_2_upper_lower_sheet": "Pure Bodybuilding Phase 2 — Upper Lower",
    "the_ultimate_push_pull_legs_system_4x": "Ultimate Push Pull Legs System — 4x",
    "the_ultimate_push_pull_legs_system_5x": "Ultimate Push Pull Legs System — 5x",
    "the_ultimate_push_pull_legs_system_6x": "Ultimate Push Pull Legs System — 6x",
    "the_bodybuilding_transformation_system_beginner": "Bodybuilding Transformation System — Beginner",
    "the_bodybuilding_transformation_system_intermediate_advanced": "Bodybuilding Transformation System — Intermediate/Advanced",
}


def _fallback_program_name(program_id: str) -> str:
    return " ".join(part.capitalize() for part in program_id.replace("-", "_").split("_") if part)


def _resolve_programs_path() -> Path:
    configured = Path(settings.programs_dir)
    if configured.exists():
        return configured

    repo_programs = Path(__file__).resolve().parents[3] / "programs"
    if repo_programs.exists():
        return repo_programs

    return configured


def list_program_templates() -> list[dict]:
    programs_path = _resolve_programs_path()
    candidates = sorted(programs_path.glob("*.json"))

    summaries_by_id: dict[str, dict] = {}
    for candidate in candidates:
        raw = json.loads(candidate.read_text(encoding="utf-8"))
        try:
            validated = CanonicalProgramTemplate.model_validate(raw)
        except ValidationError:
            continue

        data = validated.model_dump()
        summaries_by_id[data["id"]] = {
            "id": data["id"],
            "name": PROGRAM_NAMES.get(data["id"], _fallback_program_name(data["id"])),
            "version": data["version"],
            "split": data["split"],
            "days_supported": data["days_supported"],
            "session_count": len(data["sessions"]),
            "description": PROGRAM_DESCRIPTIONS.get(
                data["id"],
                f"Deterministic {data['split']} program template.",
            ),
        }

    return [summaries_by_id[key] for key in sorted(summaries_by_id)]


def load_program_template(template_id: str) -> dict:
    candidate = _resolve_programs_path() / f"{template_id}.json"
    if not candidate.exists():
        raise FileNotFoundError(f"Program template not found: {template_id}")

    raw = json.loads(candidate.read_text(encoding="utf-8"))
    validated = CanonicalProgramTemplate.model_validate(raw)
    return validated.model_dump()
