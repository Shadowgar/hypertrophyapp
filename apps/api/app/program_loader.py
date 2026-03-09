import json
import hashlib
from pathlib import Path
import re
from typing import Any
from pydantic import ValidationError

from .config import settings
from .adaptive_schema import AdaptiveGoldRuleSet, ProgramOnboardingPackage
from .template_schema import CanonicalProgramTemplate


PROGRAM_DESCRIPTIONS: dict[str, str] = {
    "full_body_v1": "Pure Bodybuilding-inspired full body structure with deterministic day templates.",
    "ppl_v1": "Push/Pull/Legs baseline template for balanced hypertrophy progression.",
    "upper_lower_v1": "Upper/Lower split with clear weekly distribution and recovery spacing.",
    "edited_ppl_5x": "Imported higher-frequency PPL variant derived from reference spreadsheet data.",
    "my_new_program": "Reference-derived full body progression variant (Phase 1 extension).",
    "powerbuilding_3_0": "Powerbuilding 3.0 progression template from reference workbook.",
    "pure_bodybuilding_full_body": "Pure Bodybuilding Phase 1 full body template from reference workbook.",
    "pure_bodybuilding_phase_2_full_body_sheet": "Pure Bodybuilding Phase 2 full body variant from reference workbook.",
    "pure_bodybuilding_phase_2_full_body_sheet_1": "Pure Bodybuilding Phase 2 full body alternate sheet variant.",
    "pure_bodybuilding_phase_2_ppl_sheet": "Pure Bodybuilding Phase 2 Push/Pull/Legs variant from reference workbook.",
    "pure_bodybuilding_phase_2_upper_lower_sheet": "Pure Bodybuilding Phase 2 upper/lower split variant.",
    "the_ultimate_push_pull_legs_system_4x": "Ultimate Push Pull Legs System — 4 day frequency variant.",
    "the_ultimate_push_pull_legs_system_5x": "Ultimate Push Pull Legs System — 5 day frequency variant.",
    "the_ultimate_push_pull_legs_system_6x": "Ultimate Push Pull Legs System — 6 day frequency variant.",
    "the_bodybuilding_transformation_system_beginner": "Bodybuilding Transformation System — beginner track from reference workbook.",
    "the_bodybuilding_transformation_system_intermediate_advanced": "Bodybuilding Transformation System — intermediate/advanced track.",
}

PROGRAM_NAMES: dict[str, str] = {
    "full_body_v1": "Full Body v1",
    "ppl_v1": "Push Pull Legs v1",
    "upper_lower_v1": "Upper Lower v1",
    "edited_ppl_5x": "Edited PPL 5x",
    "my_new_program": "Full Body Phase 1 — Extended",
    "powerbuilding_3_0": "Powerbuilding 3.0",
    "pure_bodybuilding_full_body": "Pure Bodybuilding Phase 1 — Full Body",
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

LINKED_PROGRAM_IDS: dict[str, str] = {
    "full_body_v1": "pure_bodybuilding_phase_1_full_body",
    "ppl_v1": "pure_bodybuilding_phase_2_ppl_sheet",
    "upper_lower_v1": "pure_bodybuilding_phase_2_upper_lower_sheet",
    "pure_bodybuilding_full_body": "pure_bodybuilding_phase_1_full_body",
    "pure_bodybuilding_phase_1_full_body": "pure_bodybuilding_phase_1_full_body",
    "pure_bodybuilding_phase_2_full_body_sheet": "pure_bodybuilding_phase_2_full_body_sheet",
    "pure_bodybuilding_phase_2_full_body_sheet_1": "pure_bodybuilding_phase_2_full_body_sheet",
    "pure_bodybuilding_phase_2_ppl_sheet": "pure_bodybuilding_phase_2_ppl_sheet",
    "pure_bodybuilding_phase_2_upper_lower_sheet": "pure_bodybuilding_phase_2_upper_lower_sheet",
}


def _normalized_stem(path: Path) -> str:
    return path.stem.replace(".", "_")


def _is_runtime_template_file(path: Path) -> bool:
    name = path.name.lower()
    if name.endswith(".onboarding.json"):
        return False
    if name.endswith("_imported.json"):
        return False
    return True


def _fallback_program_name(program_id: str) -> str:
    return " ".join(part.capitalize() for part in program_id.replace("-", "_").split("_") if part)


def resolve_linked_program_id(program_id: str) -> str:
    return LINKED_PROGRAM_IDS.get(program_id, program_id)


def _program_signature(program: dict[str, Any]) -> str:
    # Signature intentionally excludes `id` so semantic duplicates collapse.
    payload = {
        "version": program.get("version"),
        "split": program.get("split"),
        "days_supported": program.get("days_supported"),
        "deload": program.get("deload"),
        "progression": program.get("progression"),
        "sessions": program.get("sessions"),
    }
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _catalog_id_rank(program_id: str) -> tuple[int, int, int, int, str]:
    curated_priority = {
        "full_body_v1": 0,
        "ppl_v1": 0,
        "upper_lower_v1": 0,
        "pure_bodybuilding_full_body": 1,
        "pure_bodybuilding_phase_2_full_body_sheet": 1,
        "pure_bodybuilding_phase_2_ppl_sheet": 1,
        "pure_bodybuilding_phase_2_upper_lower_sheet": 1,
    }
    ad_hoc_penalty = 1 if program_id.startswith("my_new_program") else 0
    alt_suffix_penalty = 1 if re.search(r"_\d+$", program_id) else 0
    return (
        curated_priority.get(program_id, 20),
        ad_hoc_penalty,
        alt_suffix_penalty,
        len(program_id),
        program_id,
    )


def _resolve_programs_path() -> Path:
    configured = Path(settings.programs_dir)
    if configured.exists():
        return configured

    repo_programs = Path(__file__).resolve().parents[3] / "programs"
    if repo_programs.exists():
        return repo_programs

    return configured


def _resolve_onboarding_path() -> Path:
    return _resolve_programs_path() / "gold"


def _resolve_rules_path() -> Path:
    return Path(__file__).resolve().parents[3] / "docs" / "rules" / "canonical"


def list_program_templates() -> list[dict]:
    programs_path = _resolve_programs_path()
    candidates = [candidate for candidate in sorted(programs_path.glob("*.json")) if _is_runtime_template_file(candidate)]

    summaries_by_id: dict[str, dict] = {}
    templates_by_id: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        raw = json.loads(candidate.read_text(encoding="utf-8"))
        try:
            validated = CanonicalProgramTemplate.model_validate(raw)
        except ValidationError:
            continue

        data = validated.model_dump()
        runtime_id = _normalized_stem(candidate)
        if str(data.get("id") or "") != runtime_id:
            # Runtime templates must have stable ID<->filename mapping.
            continue

        templates_by_id[data["id"]] = data
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

    winner_by_signature: dict[str, str] = {}
    for template_id in sorted(templates_by_id):
        signature = _program_signature(templates_by_id[template_id])
        incumbent = winner_by_signature.get(signature)
        if incumbent is None or _catalog_id_rank(template_id) < _catalog_id_rank(incumbent):
            winner_by_signature[signature] = template_id

    selected_ids = sorted(winner_by_signature.values())
    return [summaries_by_id[key] for key in selected_ids]


def load_program_template(template_id: str) -> dict:
    programs_path = _resolve_programs_path()
    for candidate in sorted(programs_path.glob("*.json")):
        if not _is_runtime_template_file(candidate):
            continue
        if _normalized_stem(candidate) != template_id:
            continue

        raw = json.loads(candidate.read_text(encoding="utf-8"))
        validated = CanonicalProgramTemplate.model_validate(raw)
        payload = validated.model_dump()
        if str(payload.get("id") or "") != template_id:
            continue
        return payload

    raise FileNotFoundError(f"Program template not found: {template_id}")


def list_program_onboarding_packages() -> list[dict[str, Any]]:
    onboarding_path = _resolve_onboarding_path()
    if not onboarding_path.exists():
        return []

    summaries: list[dict[str, Any]] = []
    for candidate in sorted(onboarding_path.glob("*.onboarding.json")):
        try:
            raw = json.loads(candidate.read_text(encoding="utf-8"))
            package = ProgramOnboardingPackage.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError):
            continue

        summaries.append(
            {
                "program_id": package.program_id,
                "program_name": package.blueprint.program_name,
                "split": package.blueprint.split,
                "default_training_days": package.blueprint.default_training_days,
                "total_weeks": package.blueprint.total_weeks,
                "source_workbook": package.blueprint.source_workbook,
                "source_pdf": package.source_pdf,
                "version": package.version,
            }
        )

    return summaries


def load_program_onboarding_package(program_id: str) -> dict[str, Any]:
    candidate = _resolve_onboarding_path() / f"{resolve_linked_program_id(program_id)}.onboarding.json"
    if not candidate.exists():
        raise FileNotFoundError(f"Program onboarding package not found: {program_id}")

    raw = json.loads(candidate.read_text(encoding="utf-8"))
    validated = ProgramOnboardingPackage.model_validate(raw)
    return validated.model_dump(mode="json")


def load_program_rule_set(program_id: str) -> dict[str, Any]:
    resolved_program_id = resolve_linked_program_id(program_id)
    rules_path = _resolve_rules_path()
    if not rules_path.exists():
        raise FileNotFoundError(f"Program rule set not found: {program_id}")

    direct_candidate = rules_path / f"{resolved_program_id}.rules.json"
    candidates = [direct_candidate]
    if not direct_candidate.exists():
        candidates = sorted(rules_path.glob("*.rules.json"))

    for candidate in candidates:
        if not candidate.exists():
            continue

        raw = json.loads(candidate.read_text(encoding="utf-8"))
        validated = AdaptiveGoldRuleSet.model_validate(raw)
        payload = validated.model_dump(mode="json")
        if resolved_program_id in payload.get("program_scope", []):
            return payload

    raise FileNotFoundError(f"Program rule set not found: {program_id}")
