import json
import hashlib
from pathlib import Path
import re
from typing import Any
from pydantic import ValidationError

from .config import settings
from .adaptive_schema import AdaptiveGoldProgramTemplate, AdaptiveGoldRuleSet, ProgramOnboardingPackage
from .template_schema import CanonicalProgramTemplate

PHASE1_CANONICAL_PROGRAM_ID = "pure_bodybuilding_phase_1_full_body"
ACTIVE_ADMINISTERED_PROGRAM_IDS: set[str] = {
    PHASE1_CANONICAL_PROGRAM_ID,
    "upper_lower_v1",
}
PHASE1_CANONICAL_RUNTIME_TEMPLATE_ID = PHASE1_CANONICAL_PROGRAM_ID
PHASE1_LEGACY_RUNTIME_TEMPLATE_ID = "adaptive_full_body_gold_v0_1"
PHASE1_LEGACY_RULE_OVERLAY_SOURCE_ID = PHASE1_LEGACY_RUNTIME_TEMPLATE_ID
PHASE1_COMPATIBILITY_ALIASES: set[str] = {
    "full_body_v1",
    "adaptive_full_body_gold_v0_1",
    "pure_bodybuilding_full_body",
    PHASE1_CANONICAL_PROGRAM_ID,
}

ADMINISTERED_PROGRAM_ID_ALIASES: dict[str, str] = {
    alias: PHASE1_CANONICAL_PROGRAM_ID for alias in PHASE1_COMPATIBILITY_ALIASES
}

RUNTIME_TEMPLATE_SOURCE_IDS: dict[str, str] = {
    "full_body_v1": PHASE1_CANONICAL_RUNTIME_TEMPLATE_ID,
    "adaptive_full_body_gold_v0_1": PHASE1_CANONICAL_RUNTIME_TEMPLATE_ID,
    PHASE1_CANONICAL_PROGRAM_ID: PHASE1_CANONICAL_RUNTIME_TEMPLATE_ID,
}

RUNTIME_TEMPLATE_SOURCE_FALLBACK_IDS: dict[str, str] = {
    PHASE1_CANONICAL_RUNTIME_TEMPLATE_ID: PHASE1_LEGACY_RUNTIME_TEMPLATE_ID,
}

ONBOARDING_SOURCE_IDS: dict[str, str] = {
    "full_body_v1": PHASE1_CANONICAL_PROGRAM_ID,
    "adaptive_full_body_gold_v0_1": PHASE1_CANONICAL_PROGRAM_ID,
    "pure_bodybuilding_full_body": PHASE1_CANONICAL_PROGRAM_ID,
    PHASE1_CANONICAL_PROGRAM_ID: PHASE1_CANONICAL_PROGRAM_ID,
}

RULE_SOURCE_IDS: dict[str, str] = {
    "full_body_v1": PHASE1_CANONICAL_PROGRAM_ID,
    "adaptive_full_body_gold_v0_1": PHASE1_CANONICAL_PROGRAM_ID,
    "pure_bodybuilding_full_body": PHASE1_CANONICAL_PROGRAM_ID,
    PHASE1_CANONICAL_PROGRAM_ID: PHASE1_CANONICAL_PROGRAM_ID,
}


PROGRAM_DESCRIPTIONS: dict[str, str] = {
    PHASE1_CANONICAL_PROGRAM_ID: "Pure Bodybuilding Phase 1 Full Body administered baseline with authored workbook execution detail.",
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
    PHASE1_CANONICAL_PROGRAM_ID: "Pure Bodybuilding - Phase 1 Full Body",
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
    "adaptive_full_body_gold_v0_1": "pure_bodybuilding_phase_1_full_body",
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
    PHASE1_CANONICAL_PROGRAM_ID: PHASE1_CANONICAL_PROGRAM_ID,
    "full_body_v1": PHASE1_CANONICAL_PROGRAM_ID,
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


def resolve_administered_program_id(program_id: str | None) -> str | None:
    if program_id is None:
        return None
    normalized = str(program_id).strip()
    if not normalized:
        return None
    return ADMINISTERED_PROGRAM_ID_ALIASES.get(normalized, normalized)


def resolve_active_administered_program_id(program_id: str | None) -> str:
    normalized = resolve_administered_program_id(program_id)
    if normalized in ACTIVE_ADMINISTERED_PROGRAM_IDS:
        return str(normalized)
    return PHASE1_CANONICAL_PROGRAM_ID


def resolve_runtime_template_id(template_id: str) -> str:
    normalized = str(template_id).strip()
    if not normalized:
        return normalized
    return RUNTIME_TEMPLATE_SOURCE_IDS.get(normalized, normalized)


def _resolve_runtime_template_source_candidates(template_id: str) -> list[str]:
    normalized = str(template_id).strip()
    canonical_source_id = resolve_runtime_template_id(normalized)
    candidates: list[str] = [canonical_source_id]

    fallback_source_id = RUNTIME_TEMPLATE_SOURCE_FALLBACK_IDS.get(canonical_source_id)
    if fallback_source_id and fallback_source_id not in candidates:
        candidates.append(fallback_source_id)

    if normalized and normalized not in candidates:
        candidates.append(normalized)

    return candidates


def resolve_onboarding_program_id(program_id: str) -> str:
    normalized = str(program_id).strip()
    return ONBOARDING_SOURCE_IDS.get(normalized, resolve_linked_program_id(normalized))


def resolve_rule_program_id(program_id: str) -> str:
    normalized = str(program_id).strip()
    return RULE_SOURCE_IDS.get(normalized, resolve_linked_program_id(normalized))


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
        PHASE1_CANONICAL_PROGRAM_ID: 0,
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
    package = _load_adaptive_gold_onboarding_package(program_id)
    if package is None:
        return {}

    knowledge: dict[str, dict[str, Any]] = {}
    for entry in package.exercise_library:
        payload = entry.model_dump(mode="json")
        knowledge[str(entry.exercise_id)] = payload
    return knowledge


def _load_adaptive_gold_onboarding_package(program_id: str) -> ProgramOnboardingPackage | None:
    onboarding_program_id = ADAPTIVE_GOLD_ONBOARDING_PROGRAM_IDS.get(program_id)
    if not onboarding_program_id:
        return None

    candidate = _resolve_onboarding_path() / f"{onboarding_program_id}.onboarding.json"
    if not candidate.exists():
        return None

    raw = json.loads(candidate.read_text(encoding="utf-8"))
    return ProgramOnboardingPackage.model_validate(raw)


def _adaptive_slot_to_runtime_exercise(
    slot: dict[str, Any],
    exercise_library: dict[str, dict[str, Any]],
    authored_slot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    slot_source = dict(slot)
    if authored_slot:
        slot_source.update(authored_slot)

    exercise_id = str(slot_source.get("exercise_id") or slot.get("exercise_id") or "").strip()
    library_exercise_id = ADAPTIVE_GOLD_EXERCISE_ID_ALIASES.get(exercise_id, exercise_id)
    exercise_knowledge = exercise_library.get(library_exercise_id) or {}
    work_sets = slot_source.get("work_sets") or []
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
    resolved_video_url = (
        slot_source.get("video_url")
        or slot_source.get("demo_url")
        or exercise_knowledge.get("default_video_url")
    )
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
        "last_set_intensity_technique": slot_source.get("last_set_intensity_technique"),
        "warm_up_sets": slot_source.get("warm_up_sets"),
        "working_sets": slot_source.get("working_sets"),
        "reps": slot_source.get("reps"),
        "early_set_rpe": slot_source.get("early_set_rpe"),
        "last_set_rpe": slot_source.get("last_set_rpe"),
        "rest": slot_source.get("rest"),
        "tracking_set_1": slot_source.get("tracking_set_1"),
        "tracking_set_2": slot_source.get("tracking_set_2"),
        "tracking_set_3": slot_source.get("tracking_set_3"),
        "tracking_set_4": slot_source.get("tracking_set_4"),
        "substitution_option_1": slot_source.get("substitution_option_1"),
        "substitution_option_2": slot_source.get("substitution_option_2"),
        "demo_url": slot_source.get("demo_url"),
        "video_url": slot_source.get("video_url"),
        "notes": slot_source.get("notes"),
        "video": {"youtube_url": resolved_video_url},
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
    onboarding_package = _load_adaptive_gold_onboarding_package(validated.program_id)
    onboarding_templates_by_id = (
        {template.week_template_id: template for template in onboarding_package.blueprint.week_templates}
        if onboarding_package is not None
        else {}
    )
    authored_phase_weeks = [
        week
        for phase in validated.phases
        for week in phase.weeks
        if week.days
    ]
    if not authored_phase_weeks:
        raise ValueError("adaptive gold template must contain at least one phase with weeks")

    def _resolve_onboarding_week(sequence_index: int) -> Any | None:
        if onboarding_package is None:
            return None
        if sequence_index < 1 or sequence_index > len(onboarding_package.blueprint.week_sequence):
            return None
        template_id = onboarding_package.blueprint.week_sequence[sequence_index - 1]
        return onboarding_templates_by_id.get(template_id)

    def _resolve_authored_slot(day: Any | None, slot: Any, slot_index: int) -> dict[str, Any] | None:
        if day is None:
            return None
        authored_slots = list(getattr(day, "slots", []) or [])
        if slot_index < len(authored_slots):
            candidate = authored_slots[slot_index]
            if str(getattr(candidate, "exercise_id", "") or "") == str(getattr(slot, "exercise_id", "") or ""):
                return candidate.model_dump(mode="json")
        slot_order_index = int(getattr(slot, "order_index", slot_index + 1) or slot_index + 1)
        slot_exercise_id = str(getattr(slot, "exercise_id", "") or "")
        for candidate in authored_slots:
            if (
                str(getattr(candidate, "exercise_id", "") or "") == slot_exercise_id
                and int(getattr(candidate, "order_index", 0) or 0) == slot_order_index
            ):
                return candidate.model_dump(mode="json")
        return None

    def _week_sessions(week: Any, sequence_index: int) -> list[dict[str, Any]]:
        onboarding_week = _resolve_onboarding_week(sequence_index)
        sessions: list[dict[str, Any]] = []
        for index, day in enumerate(week.days):
            onboarding_day = None
            if onboarding_week is not None and index < len(onboarding_week.days):
                onboarding_day = onboarding_week.days[index]
            sessions.append(
                {
                    "name": day.day_name,
                    "day_role": _infer_adaptive_day_role(day, index),
                    "day_offset": min(6, index),
                    "exercises": [
                        _adaptive_slot_to_runtime_exercise(
                            slot.model_dump(mode="json"),
                            exercise_library,
                            authored_slot=_resolve_authored_slot(onboarding_day, slot, slot_index),
                        )
                        for slot_index, slot in enumerate(day.slots)
                    ],
                }
            )
        return sessions

    first_week_sessions = _week_sessions(authored_phase_weeks[0], 1)
    runtime_authored_weeks = [
        {
            "week_index": sequence_index,
            "week_role": str(week.week_role).strip() if week.week_role else None,
            "sessions": _week_sessions(week, sequence_index),
        }
        for sequence_index, week in enumerate(authored_phase_weeks, start=1)
    ]
    max_days_supported = max(len(week.days) for week in authored_phase_weeks)

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


def list_program_templates(*, active_only: bool = True) -> list[dict]:
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

        canonical_id = resolve_administered_program_id(runtime_id) or runtime_id
        if canonical_id != runtime_id:
            data = dict(data)
            data["id"] = canonical_id

        templates_by_id[canonical_id] = data
        summaries_by_id[canonical_id] = {
            "id": canonical_id,
            "name": PROGRAM_NAMES.get(canonical_id, _fallback_program_name(canonical_id)),
            "version": data["version"],
            "split": data["split"],
            "days_supported": data["days_supported"],
            "session_count": len(data["sessions"]),
            "description": PROGRAM_DESCRIPTIONS.get(
                canonical_id,
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
    summaries = [summaries_by_id[key] for key in selected_ids]
    if not active_only:
        return summaries

    active_summaries = [summary for summary in summaries if summary.get("id") in ACTIVE_ADMINISTERED_PROGRAM_IDS]
    if active_summaries:
        return active_summaries
    return summaries


def load_program_template(template_id: str) -> dict:
    canonical_template_id = resolve_administered_program_id(template_id)

    for source_template_id in _resolve_runtime_template_source_candidates(template_id):
        for candidate in _iter_runtime_template_files():
            if _normalized_stem(candidate) != source_template_id:
                continue

            raw = json.loads(candidate.read_text(encoding="utf-8"))
            if "program_id" in raw and "phases" in raw:
                payload = _adaptive_gold_to_runtime_template(raw)
            else:
                validated = CanonicalProgramTemplate.model_validate(raw)
                payload = validated.model_dump()
            if str(payload.get("id") or "") != source_template_id:
                continue
            if canonical_template_id and canonical_template_id != payload.get("id"):
                payload = dict(payload)
                payload["id"] = canonical_template_id
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
    candidate = _resolve_onboarding_path() / f"{resolve_onboarding_program_id(program_id)}.onboarding.json"
    if not candidate.exists():
        raise FileNotFoundError(f"Program onboarding package not found: {program_id}")

    raw = json.loads(candidate.read_text(encoding="utf-8"))
    validated = ProgramOnboardingPackage.model_validate(raw)
    return validated.model_dump(mode="json")


def _merge_phase1_scheduler_overlay(rule_set_payload: dict[str, Any]) -> dict[str, Any]:
    if rule_set_payload.get("generated_week_scheduler_rules"):
        return rule_set_payload

    if PHASE1_CANONICAL_PROGRAM_ID not in set(rule_set_payload.get("program_scope") or []):
        return rule_set_payload

    fallback_candidate = _resolve_gold_rules_path() / f"{PHASE1_LEGACY_RULE_OVERLAY_SOURCE_ID}.rules.json"
    if not fallback_candidate.exists():
        return rule_set_payload

    fallback_raw = json.loads(fallback_candidate.read_text(encoding="utf-8"))
    fallback_validated = AdaptiveGoldRuleSet.model_validate(fallback_raw)
    fallback_payload = fallback_validated.model_dump(mode="json")
    scheduler_rules = fallback_payload.get("generated_week_scheduler_rules")
    if not scheduler_rules:
        return rule_set_payload

    merged = dict(rule_set_payload)
    merged["generated_week_scheduler_rules"] = scheduler_rules
    return merged


def load_program_rule_set(program_id: str) -> dict[str, Any]:
    resolved_program_id = resolve_rule_program_id(program_id)
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
                return _merge_phase1_scheduler_overlay(payload)

    raise FileNotFoundError(f"Program rule set not found: {program_id}")
