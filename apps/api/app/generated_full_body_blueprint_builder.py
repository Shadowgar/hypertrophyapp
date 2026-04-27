from __future__ import annotations

import hashlib
import json

from .generated_assessment_schema import UserAssessment
from .generated_full_body_blueprint_schema import (
    BlueprintTraceRef,
    GeneratedFullBodyBlueprintInput,
    MovementPatternCoverage,
    MovementPatternRequirement,
    PatternInsufficiencyRecord,
)
from .knowledge_schema import CanonicalExerciseLibraryBundle, DoctrineBundle, PolicyBundle


BLUEPRINT_SYSTEM_DEFAULTS: dict[str, str] = {
    "blueprint_input_id_hash_v1": "Deterministic blueprint input hashing scheme.",
    "blueprint_scope_full_body_only_v1": "This milestone only prepares Full Body blueprint inputs.",
    "default_session_exercise_cap_max_tier_v1": "Fallback to the highest exercise-cap tier when no time budget is provided.",
    "pattern_coverage_candidate_threshold_v1": "Candidate sufficiency equals minimum_weekly_exposures in this input-preparation milestone.",
    "soft_preference_activation_v1": "Soft preference activation is computed from policy defaults plus assessment state.",
    "blueprint_field_trace_v1": "Blueprint field-trace generation marker.",
    "blueprint_system_default_ids_used_v1": "Blueprint system-default collection marker.",
    "bundle_reference_passthrough_v1": "Bundle id passthrough trace marker.",
    "assessment_reference_passthrough_v1": "Assessment id passthrough trace marker.",
}


def _stable_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _hash_id(prefix: str, payload: object) -> str:
    digest = hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _rule_index(bundle: DoctrineBundle) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for rules in bundle.rules_by_module.values():
        for rule in rules:
            index[rule.rule_id] = rule.model_dump(mode="json")
    return index


def _require_rule_payload(bundle: DoctrineBundle, rule_id: str) -> dict:
    rule = _rule_index(bundle).get(rule_id)
    if rule is None or not rule.get("payload"):
        raise ValueError(f"doctrine bundle missing required payload rule: {rule_id}")
    return rule["payload"]


def _hard_constraint_ids(policy_bundle: PolicyBundle) -> list[str]:
    return [item.constraint_id for item in policy_bundle.hard_constraints]


def _soft_preference_lookup(policy_bundle: PolicyBundle) -> dict[str, float]:
    return {item.preference_id: item.default_weight for item in policy_bundle.soft_preferences}


def _trace(
    *,
    doctrine_rule_ids: list[str] | None = None,
    policy_ids: list[str] | None = None,
    exercise_ids: list[str] | None = None,
    system_default_ids: list[str] | None = None,
) -> BlueprintTraceRef:
    return BlueprintTraceRef(
        doctrine_rule_ids=doctrine_rule_ids or [],
        policy_ids=policy_ids or [],
        exercise_ids=exercise_ids or [],
        system_default_ids=system_default_ids or [],
    )


def _stable_candidate_order_key(record: dict) -> tuple[str]:
    return (record["exercise_id"],)


def _candidate_pool_for_pattern(
    *,
    pattern: str,
    records: list[dict],
    available_equipment_tags: set[str],
    movement_restrictions: set[str],
) -> tuple[list[str], list[str], list[dict]]:
    pattern_records = [record for record in records if record.get("movement_pattern") == pattern]
    candidates: list[dict] = []
    excluded_ids: list[str] = []
    for record in pattern_records:
        requires_unavailable_equipment = bool(record.get("equipment_tags")) and not set(record["equipment_tags"]).issubset(
            available_equipment_tags
        )
        violates_restrictions = bool(record.get("contraindications")) and bool(
            set(record["contraindications"]).intersection(movement_restrictions)
        )
        if requires_unavailable_equipment or violates_restrictions:
            excluded_ids.append(record["exercise_id"])
            continue
        candidates.append(record)

    sorted_candidates = sorted(candidates, key=_stable_candidate_order_key)
    candidate_ids = [record["exercise_id"] for record in sorted_candidates]
    return candidate_ids, excluded_ids, sorted_candidates


def build_generated_full_body_blueprint_input(
    *,
    assessment: UserAssessment,
    doctrine_bundle: DoctrineBundle,
    policy_bundle: PolicyBundle,
    exercise_library: CanonicalExerciseLibraryBundle,
) -> GeneratedFullBodyBlueprintInput:
    defaults_used: list[str] = []
    doctrine_rule_ids = {
        "split": "split_full_body_supported_days_v1",
        "cap": "full_body_session_cap_by_time_budget_v1",
        "volume": "full_body_volume_tier_by_user_class_v1",
        "patterns": "full_body_required_movement_patterns_v1",
        "optional_fill": "full_body_optional_fill_pattern_priority_by_complexity_ceiling_v1",
        "filtering": "full_body_equipment_and_restriction_filtering_v1",
    }
    split_rule = _require_rule_payload(doctrine_bundle, doctrine_rule_ids["split"])
    cap_rule = _require_rule_payload(doctrine_bundle, doctrine_rule_ids["cap"])
    volume_rule = _require_rule_payload(doctrine_bundle, doctrine_rule_ids["volume"])
    pattern_rule = _require_rule_payload(doctrine_bundle, doctrine_rule_ids["patterns"])
    optional_fill_rule = _require_rule_payload(doctrine_bundle, doctrine_rule_ids["optional_fill"])
    _ = _require_rule_payload(doctrine_bundle, doctrine_rule_ids["filtering"])

    hard_constraint_ids = _hard_constraint_ids(policy_bundle)
    policy_weights = _soft_preference_lookup(policy_bundle)
    active_soft_preferences: dict[str, float] = {}
    active_preference_ids: list[str] = []

    split_preference = assessment.split_preference
    if split_preference is None:
        weight = policy_weights.get("prefer_full_body_when_generated_split_unspecified")
        if weight is not None:
            active_soft_preferences["prefer_full_body_when_generated_split_unspecified"] = weight
            active_preference_ids.append("prefer_full_body_when_generated_split_unspecified")
    if "novice" in assessment.user_class_flags or "comeback" in assessment.user_class_flags:
        weight = policy_weights.get("prefer_simple_options_for_novice_and_comeback")
        if weight is not None:
            active_soft_preferences["prefer_simple_options_for_novice_and_comeback"] = weight
            active_preference_ids.append("prefer_simple_options_for_novice_and_comeback")
    if "low_recovery" in assessment.user_class_flags:
        weight = policy_weights.get("prefer_recoverable_options_for_low_recovery")
        if weight is not None:
            active_soft_preferences["prefer_recoverable_options_for_low_recovery"] = weight
            active_preference_ids.append("prefer_recoverable_options_for_low_recovery")
    if "inconsistent_schedule" in assessment.user_class_flags:
        weight = policy_weights.get("prefer_adherence_first_for_inconsistent_schedule")
        if weight is not None:
            active_soft_preferences["prefer_adherence_first_for_inconsistent_schedule"] = weight
            active_preference_ids.append("prefer_adherence_first_for_inconsistent_schedule")

    session_count = min(assessment.days_available, max(split_rule["supported_days"]))

    time_budget = assessment.session_time_budget_minutes
    time_budget_tiers = cap_rule["tiers"]
    if time_budget is None:
        session_exercise_cap = time_budget_tiers[-1]["exercise_cap"]
        defaults_used.append("default_session_exercise_cap_max_tier_v1")
    else:
        session_exercise_cap = time_budget_tiers[-1]["exercise_cap"]
        for tier in time_budget_tiers:
            if time_budget <= tier["max_minutes_inclusive"]:
                session_exercise_cap = tier["exercise_cap"]
                break

    volume_mapping = volume_rule["user_class_to_volume_tier"]
    volume_tier = "moderate"
    for flag in assessment.user_class_flags:
        tier = volume_mapping.get(flag)
        if tier == "conservative":
            volume_tier = "conservative"
            break
        if tier == "moderate":
            volume_tier = "moderate"

    complexity_ceiling = (
        "simple"
        if any(flag in assessment.user_class_flags for flag in ["novice", "comeback", "low_recovery", "inconsistent_schedule"])
        else "standard"
    )

    records = [record.model_dump(mode="json") for record in exercise_library.records]
    available_patterns = {record["movement_pattern"] for record in records if record.get("movement_pattern")}
    requirements = [
        item
        for item in sorted(pattern_rule["requirements"], key=lambda item: (item["priority_rank"], item["movement_pattern"]))
        if item["movement_pattern"] in available_patterns
    ]
    required_pattern_names = {item["movement_pattern"] for item in requirements}
    required_movement_patterns = [
        MovementPatternRequirement(
            movement_pattern=item["movement_pattern"],
            minimum_weekly_exposures=item["minimum_weekly_exposures"],
            priority_rank=item["priority_rank"],
            trace=_trace(doctrine_rule_ids=[doctrine_rule_ids["patterns"]]),
        )
        for item in requirements
    ]

    available_equipment_tags = set(assessment.baseline_signal_summary.available_equipment_tags)
    movement_restrictions = set(assessment.movement_restrictions)
    excluded_exercise_ids: list[str] = []
    candidate_exercise_ids_by_pattern: dict[str, list[str]] = {}
    pattern_coverage: list[MovementPatternCoverage] = []
    pattern_insufficiencies: list[PatternInsufficiencyRecord] = []

    filtered_records: list[dict] = []
    seen_filtered_ids: set[str] = set()

    for requirement in required_movement_patterns:
        candidate_ids, excluded_for_pattern, included_records = _candidate_pool_for_pattern(
            pattern=requirement.movement_pattern,
            records=records,
            available_equipment_tags=available_equipment_tags,
            movement_restrictions=movement_restrictions,
        )
        excluded_exercise_ids.extend(excluded_for_pattern)
        for record in included_records:
            if record["exercise_id"] not in seen_filtered_ids:
                filtered_records.append(record)
                seen_filtered_ids.add(record["exercise_id"])
        candidate_exercise_ids_by_pattern[requirement.movement_pattern] = candidate_ids

        if len(candidate_ids) == 0:
            coverage_status = "empty"
            insufficiency_reason = "empty_candidate_pool"
        elif len(candidate_ids) < requirement.minimum_weekly_exposures:
            coverage_status = "insufficient"
            insufficiency_reason = "candidate_count_below_required_exposures"
        else:
            coverage_status = "covered"
            insufficiency_reason = None

        coverage_trace = _trace(
            doctrine_rule_ids=[
                doctrine_rule_ids["patterns"],
                doctrine_rule_ids["filtering"],
            ],
            policy_ids=hard_constraint_ids,
            exercise_ids=candidate_ids,
            system_default_ids=["pattern_coverage_candidate_threshold_v1"],
        )
        pattern_coverage.append(
            MovementPatternCoverage(
                movement_pattern=requirement.movement_pattern,
                minimum_weekly_exposures=requirement.minimum_weekly_exposures,
                candidate_count=len(candidate_ids),
                candidate_exercise_ids=candidate_ids,
                status=coverage_status,
                trace=coverage_trace,
            )
        )
        if insufficiency_reason is not None:
            pattern_insufficiencies.append(
                PatternInsufficiencyRecord(
                    movement_pattern=requirement.movement_pattern,
                    reason=insufficiency_reason,
                    minimum_weekly_exposures=requirement.minimum_weekly_exposures,
                    candidate_count=len(candidate_ids),
                    candidate_exercise_ids=candidate_ids,
                    trace=coverage_trace,
                )
            )

    optional_fill_patterns = [
        pattern
        for pattern in optional_fill_rule["optional_patterns_by_complexity_ceiling"].get(complexity_ceiling, [])
        if pattern in available_patterns and pattern not in required_pattern_names
    ]
    if "core" in available_patterns and "core" not in required_pattern_names and "core" not in optional_fill_patterns:
        optional_fill_patterns.append("core")
    for movement_pattern in optional_fill_patterns:
        candidate_ids, excluded_for_pattern, included_records = _candidate_pool_for_pattern(
            pattern=movement_pattern,
            records=records,
            available_equipment_tags=available_equipment_tags,
            movement_restrictions=movement_restrictions,
        )
        excluded_exercise_ids.extend(excluded_for_pattern)
        for record in included_records:
            if record["exercise_id"] not in seen_filtered_ids:
                filtered_records.append(record)
                seen_filtered_ids.add(record["exercise_id"])
        candidate_exercise_ids_by_pattern[movement_pattern] = candidate_ids

    global_sorted_candidates = sorted(filtered_records, key=_stable_candidate_order_key)
    weak_point_candidate_exercise_ids_by_muscle: dict[str, list[str]] = {}
    for item in assessment.weak_point_priorities:
        primary = [record["exercise_id"] for record in global_sorted_candidates if item.muscle_group in record.get("primary_muscles", [])]
        secondary = [
            record["exercise_id"]
            for record in global_sorted_candidates
            if item.muscle_group in record.get("secondary_muscles", []) and record["exercise_id"] not in primary
        ]
        weak_point_candidate_exercise_ids_by_muscle[item.muscle_group] = primary + secondary

    excluded_exercise_ids = _unique_preserve_order(excluded_exercise_ids)
    active_preference_ids = _unique_preserve_order(active_preference_ids)

    field_trace = {
        "blueprint_input_id": _trace(system_default_ids=["blueprint_input_id_hash_v1"]),
        "target_split": _trace(
            doctrine_rule_ids=[doctrine_rule_ids["split"]],
            policy_ids=active_preference_ids,
            system_default_ids=["blueprint_scope_full_body_only_v1"],
        ),
        "assessment_id": _trace(system_default_ids=["assessment_reference_passthrough_v1"]),
        "doctrine_bundle_id": _trace(system_default_ids=["bundle_reference_passthrough_v1"]),
        "policy_bundle_id": _trace(system_default_ids=["bundle_reference_passthrough_v1"]),
        "exercise_library_bundle_id": _trace(system_default_ids=["bundle_reference_passthrough_v1"]),
        "hard_constraint_ids": _trace(policy_ids=hard_constraint_ids),
        "soft_preference_weights": _trace(
            policy_ids=active_preference_ids,
            system_default_ids=["soft_preference_activation_v1"] if not active_preference_ids else [],
        ),
        "session_count": _trace(doctrine_rule_ids=[doctrine_rule_ids["split"]]),
        "session_exercise_cap": _trace(
            doctrine_rule_ids=[doctrine_rule_ids["cap"]],
            policy_ids=["respect_session_time_budget"],
            system_default_ids=(["default_session_exercise_cap_max_tier_v1"] if time_budget is None else []),
        ),
        "volume_tier": _trace(doctrine_rule_ids=[doctrine_rule_ids["volume"]]),
        "complexity_ceiling": _trace(
            policy_ids=active_preference_ids,
            system_default_ids=["blueprint_scope_full_body_only_v1"],
        ),
        "required_movement_patterns": _trace(doctrine_rule_ids=[doctrine_rule_ids["patterns"]]),
        "candidate_exercise_ids_by_pattern": _trace(
            doctrine_rule_ids=[
                doctrine_rule_ids["patterns"],
                doctrine_rule_ids["optional_fill"],
                doctrine_rule_ids["filtering"],
            ],
            policy_ids=hard_constraint_ids,
            exercise_ids=_unique_preserve_order(
                [exercise_id for exercise_ids in candidate_exercise_ids_by_pattern.values() for exercise_id in exercise_ids]
            ),
        ),
        "weak_point_candidate_exercise_ids_by_muscle": _trace(
            doctrine_rule_ids=[
                doctrine_rule_ids["optional_fill"],
                doctrine_rule_ids["filtering"],
            ],
            exercise_ids=_unique_preserve_order(
                [exercise_id for exercise_ids in weak_point_candidate_exercise_ids_by_muscle.values() for exercise_id in exercise_ids]
            ),
        ),
        "excluded_exercise_ids": _trace(
            doctrine_rule_ids=[doctrine_rule_ids["filtering"]],
            policy_ids=hard_constraint_ids,
            exercise_ids=excluded_exercise_ids,
        ),
        "pattern_coverage": _trace(
            doctrine_rule_ids=[
                doctrine_rule_ids["patterns"],
                doctrine_rule_ids["filtering"],
            ],
            policy_ids=hard_constraint_ids,
            exercise_ids=_unique_preserve_order(
                [exercise_id for coverage in pattern_coverage for exercise_id in coverage.candidate_exercise_ids]
            ),
            system_default_ids=["pattern_coverage_candidate_threshold_v1"],
        ),
        "pattern_insufficiencies": _trace(
            doctrine_rule_ids=[
                doctrine_rule_ids["patterns"],
                doctrine_rule_ids["filtering"],
            ],
            policy_ids=hard_constraint_ids,
            exercise_ids=_unique_preserve_order(
                [exercise_id for record in pattern_insufficiencies for exercise_id in record.candidate_exercise_ids]
            ),
            system_default_ids=["pattern_coverage_candidate_threshold_v1"],
        ),
        "field_trace": _trace(system_default_ids=["blueprint_field_trace_v1"]),
        "system_default_ids_used": _trace(system_default_ids=["blueprint_system_default_ids_used_v1"]),
    }

    blueprint_payload = {
        "assessment_id": assessment.assessment_id,
        "session_count": session_count,
        "session_exercise_cap": session_exercise_cap,
        "volume_tier": volume_tier,
        "complexity_ceiling": complexity_ceiling,
        "required_movement_patterns": [item.model_dump(mode="json") for item in required_movement_patterns],
        "candidate_exercise_ids_by_pattern": candidate_exercise_ids_by_pattern,
        "weak_point_candidate_exercise_ids_by_muscle": weak_point_candidate_exercise_ids_by_muscle,
        "excluded_exercise_ids": excluded_exercise_ids,
        "pattern_insufficiencies": [item.model_dump(mode="json") for item in pattern_insufficiencies],
    }
    blueprint_input_id = _hash_id("full_body_blueprint_input", blueprint_payload)

    return GeneratedFullBodyBlueprintInput(
        blueprint_input_id=blueprint_input_id,
        target_split="full_body",
        assessment_id=assessment.assessment_id,
        doctrine_bundle_id=doctrine_bundle.bundle_id,
        policy_bundle_id=policy_bundle.bundle_id,
        exercise_library_bundle_id=exercise_library.bundle_id,
        hard_constraint_ids=hard_constraint_ids,
        soft_preference_weights=active_soft_preferences,
        session_count=session_count,
        session_exercise_cap=session_exercise_cap,
        volume_tier=volume_tier,
        complexity_ceiling=complexity_ceiling,
        required_movement_patterns=required_movement_patterns,
        candidate_exercise_ids_by_pattern=candidate_exercise_ids_by_pattern,
        weak_point_candidate_exercise_ids_by_muscle=weak_point_candidate_exercise_ids_by_muscle,
        excluded_exercise_ids=excluded_exercise_ids,
        pattern_coverage=pattern_coverage,
        pattern_insufficiencies=pattern_insufficiencies,
        field_trace=field_trace,
        system_default_ids_used=_unique_preserve_order(defaults_used),
    )
