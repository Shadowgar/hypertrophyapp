import json
import hashlib
from pathlib import Path
import re
from typing import Any
from pydantic import ValidationError

from .config import settings
from .adaptive_schema import AdaptiveGoldProgramTemplate, AdaptiveGoldRuleSet, ProgramOnboardingPackage
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
    "adaptive_full_body_gold_v0_1": "Adaptive Full Body Gold v0.1",
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
    "adaptive_full_body_gold_v0_1": "adaptive_full_body_gold_v0_1",
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

ADAPTIVE_GOLD_ONBOARDING_PROGRAM_IDS: dict[str, str] = {
    "adaptive_full_body_gold_v0_1": "pure_bodybuilding_phase_1_full_body",
}

ADAPTIVE_GOLD_EXERCISE_ID_ALIASES: dict[str, str] = {
    "row_chest_supported": "chest_supported_row",
}

_ADAPTIVE_DAY_ROLE_ALIASES: dict[str, str] = {
    "fb1": "full_body_1",
    "fb2": "full_body_2",
    "fb3": "full_body_3",
    "fb4": "full_body_4",
    "fb5": "weak_point_arms",
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
        "authored_weeks": program.get("authored_weeks"),
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


def _resolve_gold_rules_path() -> Path:
    return Path(__file__).resolve().parents[3] / "docs" / "rules" / "gold"


def _iter_runtime_template_files() -> list[Path]:
    programs_path = _resolve_programs_path()
    candidates = [candidate for candidate in sorted(programs_path.glob("*.json")) if _is_runtime_template_file(candidate)]

    gold_path = programs_path / "gold"
    if gold_path.exists():
        candidates.extend(
            candidate
            for candidate in sorted(gold_path.glob("*.json"))
            if _is_runtime_template_file(candidate)
        )
    return candidates


def _fallback_exercise_name(exercise_id: str) -> str:
    return " ".join(part.capitalize() for part in exercise_id.split("_") if part)


def _infer_equipment_tags(exercise_id: str) -> list[str]:
    lowered = exercise_id.lower()
    tags: list[str] = []
    if "barbell" in lowered:
        tags.append("barbell")
    if "dumbbell" in lowered or lowered.startswith("db_") or "_db_" in lowered:
        tags.append("dumbbell")
    if "cable" in lowered:
        tags.append("cable")
    if "machine" in lowered:
        tags.append("machine")
    if "bodyweight" in lowered:
        tags.append("bodyweight")
    if "bench" in lowered:
        tags.append("bench")
    if "row" in lowered:
        tags.append("machine" if "supported" in lowered else "cable")
    return sorted(set(tags))


def _load_adaptive_gold_exercise_library(program_id: str) -> dict[str, dict[str, Any]]:
    onboarding_program_id = ADAPTIVE_GOLD_ONBOARDING_PROGRAM_IDS.get(program_id)
    if not onboarding_program_id:
        return {}

    candidate = _resolve_onboarding_path() / f"{onboarding_program_id}.onboarding.json"
    if not candidate.exists():
        return {}

    raw = json.loads(candidate.read_text(encoding="utf-8"))
    package = ProgramOnboardingPackage.model_validate(raw)
    knowledge: dict[str, dict[str, Any]] = {}
    for entry in package.exercise_library:
        payload = entry.model_dump(mode="json")
        knowledge[str(entry.exercise_id)] = payload
    return knowledge


def _adaptive_slot_to_runtime_exercise(
    slot: dict[str, Any],
    exercise_library: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    exercise_id = str(slot.get("exercise_id") or "").strip()
    library_exercise_id = ADAPTIVE_GOLD_EXERCISE_ID_ALIASES.get(exercise_id, exercise_id)
    exercise_knowledge = exercise_library.get(library_exercise_id) or {}
    work_sets = slot.get("work_sets") or []
    first_work_set = work_sets[0] if isinstance(work_sets, list) and work_sets else {}
    rep_target = first_work_set.get("rep_target") if isinstance(first_work_set, dict) else {}
    total_sets = sum(
        int(item.get("sets") or 0)
        for item in work_sets
        if isinstance(item, dict)
    )
    substitution_candidates: list[str] = []
    substitution_metadata: dict[str, dict[str, Any]] = {}
    for candidate in exercise_knowledge.get("valid_substitutions") or []:
        candidate_id = str(candidate.get("exercise_id") or "").strip()
        if not candidate_id:
            continue
        candidate_knowledge = exercise_library.get(candidate_id) or {}
        candidate_name = str(candidate_knowledge.get("canonical_name") or _fallback_exercise_name(candidate_id))
        substitution_candidates.append(candidate_name)
        substitution_metadata[candidate_name] = {
            "id": candidate_id,
            "name": candidate_name,
            "movement_pattern": candidate_knowledge.get("movement_pattern"),
            "primary_muscles": list(candidate_knowledge.get("primary_muscles") or []),
            "equipment_tags": list(candidate_knowledge.get("equipment_tags") or _infer_equipment_tags(candidate_id)),
            "video": {
                "youtube_url": candidate_knowledge.get("default_video_url"),
            },
        }
    return {
        "id": exercise_id,
        "primary_exercise_id": exercise_id,
        "name": str(exercise_knowledge.get("canonical_name") or _fallback_exercise_name(exercise_id)),
        "sets": max(1, total_sets or 3),
        "rep_range": [
            int((rep_target or {}).get("min") or 8),
            int((rep_target or {}).get("max") or (rep_target or {}).get("min") or 12),
        ],
        "start_weight": 20.0,
        "priority": "standard",
        "slot_role": slot.get("slot_role"),
        "movement_pattern": exercise_knowledge.get("movement_pattern"),
        "primary_muscles": list(exercise_knowledge.get("primary_muscles") or []),
        "equipment_tags": list(exercise_knowledge.get("equipment_tags") or _infer_equipment_tags(exercise_id)),
        "substitution_candidates": substitution_candidates,
        "substitution_metadata": substitution_metadata,
        "notes": slot.get("notes"),
        "video": {"youtube_url": slot.get("video_url") or exercise_knowledge.get("default_video_url")},
    }


def _infer_adaptive_day_role(day: Any, fallback_index: int) -> str:
    explicit = str(getattr(day, "day_role", None) or "").strip()
    if explicit:
        return explicit

    day_id = str(getattr(day, "day_id", "") or "").strip().lower()
    if day_id in _ADAPTIVE_DAY_ROLE_ALIASES:
        return _ADAPTIVE_DAY_ROLE_ALIASES[day_id]

    day_name = str(getattr(day, "day_name", "") or "").strip().lower()
    if "weak" in day_name or "arms" in day_name:
        return "weak_point_arms"
    return f"full_body_{fallback_index + 1}"


def _adaptive_gold_to_runtime_template(payload: dict[str, Any]) -> dict[str, Any]:
    validated = AdaptiveGoldProgramTemplate.model_validate(payload)
    exercise_library = _load_adaptive_gold_exercise_library(validated.program_id)
    first_phase = next((phase for phase in validated.phases if phase.weeks), None)
    if first_phase is None:
        raise ValueError("adaptive gold template must contain at least one phase with weeks")
    authored_weeks = [week for week in first_phase.weeks if week.days]
    if not authored_weeks:
        raise ValueError("adaptive gold template must contain at least one week with days")

    def _week_sessions(week: Any) -> list[dict[str, Any]]:
        sessions: list[dict[str, Any]] = []
        for index, day in enumerate(week.days):
            sessions.append(
                {
                    "name": day.day_name,
                    "day_role": _infer_adaptive_day_role(day, index),
                    "day_offset": min(6, index),
                    "exercises": [
                        _adaptive_slot_to_runtime_exercise(slot.model_dump(mode="json"), exercise_library)
                        for slot in day.slots
                    ],
                }
            )
        return sessions

    first_week_sessions = _week_sessions(authored_weeks[0])
    runtime_authored_weeks = [
        {
            "week_index": int(week.week_index),
            "week_role": str(week.week_role).strip() if week.week_role else None,
            "sessions": _week_sessions(week),
        }
        for week in authored_weeks
    ]
    max_days_supported = max(len(week.days) for week in authored_weeks)

    return CanonicalProgramTemplate.model_validate(
        {
            "id": validated.program_id,
            "version": validated.version,
            "split": validated.split,
            "days_supported": list(range(2, max(2, max_days_supported) + 1)),
            "deload": {
                "trigger_weeks": 6,
                "set_reduction_pct": 35,
                "load_reduction_pct": 10,
            },
            "progression": {
                "mode": "double_progression",
                "increment_kg": 2.5,
            },
            "sessions": first_week_sessions,
            "authored_weeks": runtime_authored_weeks,
        }
    ).model_dump()


def list_program_templates() -> list[dict]:
    summaries_by_id: dict[str, dict] = {}
    templates_by_id: dict[str, dict[str, Any]] = {}
    for candidate in _iter_runtime_template_files():
        raw = json.loads(candidate.read_text(encoding="utf-8"))
        try:
            if "program_id" in raw and "phases" in raw:
                data = _adaptive_gold_to_runtime_template(raw)
            else:
                validated = CanonicalProgramTemplate.model_validate(raw)
                data = validated.model_dump()
        except ValidationError:
            continue

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
    for candidate in _iter_runtime_template_files():
        if _normalized_stem(candidate) != template_id:
            continue

        raw = json.loads(candidate.read_text(encoding="utf-8"))
        if "program_id" in raw and "phases" in raw:
            payload = _adaptive_gold_to_runtime_template(raw)
        else:
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
    rules_paths = [_resolve_rules_path(), _resolve_gold_rules_path()]

    for rules_path in rules_paths:
        if not rules_path.exists():
            continue

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
