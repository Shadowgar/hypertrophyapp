from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .generated_assessment_schema import UserAssessment
from .generated_full_body_blueprint_schema import GeneratedFullBodyBlueprintInput, PatternInsufficiencyRecord
from .generated_full_body_candidate_scoring import select_scored_candidate
from .generated_full_body_prescription import resolve_generated_full_body_initial_prescription
from .generated_full_body_template_draft_schema import (
    ConstructibilityIssue,
    ConstructorTraceRef,
    ExerciseSelectionTrace,
    GeneratedExerciseDraft,
    GeneratedFullBodyTemplateDraft,
    GeneratedSessionDraft,
    OptionalFillTrace,
    ScoredCandidateTrace,
)
from .knowledge_schema import CanonicalExerciseLibraryBundle, DoctrineBundle, DoctrineRuleStub, ExerciseMetadataV2, PolicyBundle


CONSTRUCTOR_SYSTEM_DEFAULTS: dict[str, str] = {
    "template_draft_id_hash_v1": "Deterministic generated Full Body template-draft hashing scheme.",
    "generated_session_id_v1": "Generic deterministic generated session-id scheme.",
    "generated_session_title_v1": "Generic deterministic generated session-title scheme.",
    "default_generated_sets_v1": "Legacy compatibility default sets value retained only for unexpected fallback use.",
    "default_generated_rep_range_v1": "Legacy compatibility default rep-range retained only for unexpected fallback use.",
    "default_generated_start_weight_v1": "Compatibility default starting weight used only through doctrine-backed fallback.",
    "default_generated_substitution_candidates_empty_v1": "Temporary scheduler-compatibility default empty substitution-candidate list.",
    "constructor_assessment_reference_passthrough_v1": "Assessment id passthrough trace marker for constructor outputs.",
    "constructor_blueprint_reference_passthrough_v1": "Blueprint id passthrough trace marker for constructor outputs.",
    "constructor_bundle_reference_passthrough_v1": "Bundle id passthrough trace marker for constructor outputs.",
    "constructor_field_trace_v1": "Constructor field-trace generation marker.",
    "constructibility_issue_id_hash_v1": "Deterministic constructibility-issue hashing scheme.",
    "constructor_system_default_ids_used_v1": "Constructor system-default collection marker.",
}


DEFAULT_GENERATED_SUBSTITUTION_CANDIDATES: list[str] = []
WEEKLY_BALANCE_CATEGORY_TO_PATTERNS: dict[str, tuple[str, ...]] = {
    "horizontal_push": ("horizontal_press",),
    "vertical_push": ("vertical_press",),
    "horizontal_pull": ("horizontal_pull",),
    "vertical_pull": ("vertical_pull",),
    "knee_dominant_lower": ("squat", "knee_extension"),
    "hip_dominant_lower": ("hinge", "leg_curl"),
    "core": ("core",),
}

SESSION_SKELETON_PATTERN_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "press": ("horizontal_press", "vertical_press"),
    "pull": ("horizontal_pull", "vertical_pull"),
    "lower": ("squat", "knee_extension", "hinge", "leg_curl"),
    # Rear-delt/shoulder exposure can come from pressing, laterals, or rows.
    "shoulder_rear_delt": ("vertical_press", "lateral_raise", "horizontal_pull"),
}

SLOT_ROLE_ORDER: dict[str, int] = {
    "primary_compound": 0,
    "secondary_compound": 1,
    "accessory": 2,
    "weak_point": 3,
}

MAJOR_MUSCLE_TARGETS: dict[str, tuple[str, ...]] = {
    "chest": ("chest",),
    "back": ("back", "lats", "upper_back", "mid_back"),
    "quads": ("quads",),
    "hamstrings": ("hamstrings",),
    "delts": ("shoulders", "delts", "front_delts", "side_delts", "rear_delts"),
    "arms": ("arms", "biceps", "triceps"),
    "core": ("core", "abs"),
}


@dataclass(frozen=True)
class _ResolvedRule:
    rule_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class _ThreeDayVolumeBand:
    band_id: str
    target_exercises_per_session: int
    exercise_cap_per_session: int
    minimum_exercises_per_session: int
    minimum_weekly_planned_sets: int
    minimum_weekly_muscle_volume: int


@dataclass(frozen=True)
class _ThreeDayBalanceTargets:
    major_floor_by_group: dict[str, int]
    minimum_exposure_by_group: dict[str, int]
    soft_cap_by_group: dict[str, int]
    hard_cap_by_group: dict[str, int]
    weak_point_minimum_bonus_by_group: dict[str, int]
    weak_point_bonus_by_group: dict[str, int]
    combined_arm_delt_share_cap: float
    weak_point_combined_arm_delt_share_cap: float


THREE_DAY_VOLUME_BANDS: dict[str, _ThreeDayVolumeBand] = {
    "low_time": _ThreeDayVolumeBand(
        band_id="low_time",
        target_exercises_per_session=8,
        exercise_cap_per_session=9,
        minimum_exercises_per_session=7,
        minimum_weekly_planned_sets=45,
        minimum_weekly_muscle_volume=55,
    ),
    "low_recovery": _ThreeDayVolumeBand(
        band_id="low_recovery",
        target_exercises_per_session=7,
        exercise_cap_per_session=8,
        minimum_exercises_per_session=6,
        minimum_weekly_planned_sets=40,
        minimum_weekly_muscle_volume=50,
    ),
    "normal": _ThreeDayVolumeBand(
        band_id="normal",
        target_exercises_per_session=11,
        exercise_cap_per_session=12,
        minimum_exercises_per_session=9,
        minimum_weekly_planned_sets=75,
        minimum_weekly_muscle_volume=90,
    ),
    "higher_time_normal_recovery": _ThreeDayVolumeBand(
        band_id="higher_time_normal_recovery",
        target_exercises_per_session=12,
        exercise_cap_per_session=13,
        minimum_exercises_per_session=10,
        minimum_weekly_planned_sets=85,
        minimum_weekly_muscle_volume=100,
    ),
}

THREE_DAY_BALANCE_TARGETS: dict[str, _ThreeDayBalanceTargets] = {
    "low_time": _ThreeDayBalanceTargets(
        major_floor_by_group={"chest": 7, "back": 8, "quads": 6, "hamstrings": 6, "core": 2},
        minimum_exposure_by_group={"arms": 2, "delts": 2},
        soft_cap_by_group={"arms": 22, "delts": 14},
        hard_cap_by_group={"arms": 26, "delts": 17},
        weak_point_minimum_bonus_by_group={"arms": 1, "delts": 0},
        weak_point_bonus_by_group={"arms": 2, "delts": 1},
        combined_arm_delt_share_cap=0.50,
        weak_point_combined_arm_delt_share_cap=0.54,
    ),
    "low_recovery": _ThreeDayBalanceTargets(
        major_floor_by_group={"chest": 7, "back": 8, "quads": 6, "hamstrings": 6, "core": 2},
        minimum_exposure_by_group={"arms": 2, "delts": 2},
        soft_cap_by_group={"arms": 21, "delts": 14},
        hard_cap_by_group={"arms": 25, "delts": 17},
        weak_point_minimum_bonus_by_group={"arms": 1, "delts": 0},
        weak_point_bonus_by_group={"arms": 2, "delts": 1},
        combined_arm_delt_share_cap=0.50,
        weak_point_combined_arm_delt_share_cap=0.54,
    ),
    "normal": _ThreeDayBalanceTargets(
        major_floor_by_group={"chest": 14, "back": 14, "quads": 10, "hamstrings": 10, "core": 4},
        minimum_exposure_by_group={"arms": 8, "delts": 6},
        soft_cap_by_group={"arms": 26, "delts": 18},
        hard_cap_by_group={"arms": 30, "delts": 20},
        weak_point_minimum_bonus_by_group={"arms": 5, "delts": 0},
        weak_point_bonus_by_group={"arms": 3, "delts": 2},
        combined_arm_delt_share_cap=0.45,
        weak_point_combined_arm_delt_share_cap=0.50,
    ),
    "higher_time_normal_recovery": _ThreeDayBalanceTargets(
        major_floor_by_group={"chest": 16, "back": 16, "quads": 12, "hamstrings": 12, "core": 5},
        minimum_exposure_by_group={"arms": 10, "delts": 8},
        soft_cap_by_group={"arms": 28, "delts": 20},
        hard_cap_by_group={"arms": 32, "delts": 22},
        weak_point_minimum_bonus_by_group={"arms": 2, "delts": 0},
        weak_point_bonus_by_group={"arms": 3, "delts": 2},
        combined_arm_delt_share_cap=0.44,
        weak_point_combined_arm_delt_share_cap=0.49,
    ),
}


def _stable_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _hash_id(prefix: str, payload: object) -> str:
    digest = hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _trace(
    *,
    doctrine_rule_ids: list[str] | None = None,
    policy_ids: list[str] | None = None,
    exercise_ids: list[str] | None = None,
    system_default_ids: list[str] | None = None,
) -> ConstructorTraceRef:
    return ConstructorTraceRef(
        doctrine_rule_ids=doctrine_rule_ids or [],
        policy_ids=policy_ids or [],
        exercise_ids=exercise_ids or [],
        system_default_ids=system_default_ids or [],
    )


def _rule_index(bundle: DoctrineBundle) -> dict[str, DoctrineRuleStub]:
    index: dict[str, DoctrineRuleStub] = {}
    for rules in bundle.rules_by_module.values():
        for rule in rules:
            index[rule.rule_id] = rule
    return index


def _require_rule_payload(bundle: DoctrineBundle, rule_id: str) -> _ResolvedRule:
    rule = _rule_index(bundle).get(rule_id)
    if rule is None or not rule.payload:
        raise ValueError(f"doctrine bundle missing required payload rule: {rule_id}")
    return _ResolvedRule(rule_id=rule.rule_id, payload=rule.payload)


def _require_hard_constraint(policy_bundle: PolicyBundle, constraint_id: str) -> str:
    available = {item.constraint_id for item in policy_bundle.hard_constraints}
    if constraint_id not in available:
        raise ValueError(f"policy bundle missing required hard constraint: {constraint_id}")
    return constraint_id


def _merge_trace(
    first: ConstructorTraceRef,
    second: ConstructorTraceRef,
) -> ConstructorTraceRef:
    return ConstructorTraceRef(
        doctrine_rule_ids=_unique_preserve_order(first.doctrine_rule_ids + second.doctrine_rule_ids),
        policy_ids=_unique_preserve_order(first.policy_ids + second.policy_ids),
        exercise_ids=_unique_preserve_order(first.exercise_ids + second.exercise_ids),
        system_default_ids=_unique_preserve_order(first.system_default_ids + second.system_default_ids),
    )


def _pattern_issue(
    *,
    issue_type: str,
    reason: str,
    movement_pattern: str | None,
    slot_role: str | None,
    base_trace: ConstructorTraceRef,
) -> ConstructibilityIssue:
    issue_payload = {
        "issue_type": issue_type,
        "reason": reason,
        "movement_pattern": movement_pattern,
        "slot_role": slot_role,
        "trace": base_trace.model_dump(mode="json"),
    }
    return ConstructibilityIssue(
        issue_id=_hash_id("constructibility_issue", issue_payload),
        issue_type=issue_type,
        reason=reason,
        movement_pattern=movement_pattern,
        slot_role=slot_role,
        trace=_merge_trace(base_trace, _trace(system_default_ids=["constructibility_issue_id_hash_v1"])),
    )


def _session_title(index: int) -> str:
    return f"Generated Full Body {index}"


def _session_identifier(index: int) -> str:
    return f"generated_full_body_session_{index}"


def _topology_for_session_count(topology_rule: _ResolvedRule, session_count: int) -> list[int]:
    topology = topology_rule.payload["topology_by_session_count"].get(str(session_count))
    if topology is None:
        raise ValueError(f"missing topology for session_count={session_count}")
    return [int(item) for item in topology.get("session_indices") or []]


def _day_roles_for_session_count(day_role_rule: _ResolvedRule, session_count: int) -> list[str]:
    day_roles = day_role_rule.payload["day_roles_by_session_count"].get(str(session_count))
    if day_roles is None:
        raise ValueError(f"missing day-role sequence for session_count={session_count}")
    return [str(item) for item in day_roles]


def _pattern_distribution_for_session_count(pattern_rule: _ResolvedRule, session_count: int) -> dict[int, list[str]]:
    distribution = pattern_rule.payload["distribution_by_session_count"].get(str(session_count))
    if distribution is None:
        raise ValueError(f"missing movement-pattern distribution for session_count={session_count}")
    return {
        int(item["session_index"]): [str(pattern) for pattern in item.get("movement_patterns") or []]
        for item in distribution
    }


def _preferred_weak_point_sessions(weak_point_rule: _ResolvedRule, session_count: int) -> list[int]:
    preferred = weak_point_rule.payload["preferred_session_indices_by_session_count"].get(str(session_count))
    if preferred is None:
        raise ValueError(f"missing weak-point insertion order for session_count={session_count}")
    return [int(item) for item in preferred]


def _selected_exercise_trace(
    *,
    doctrine_rule_ids: list[str],
    policy_ids: list[str],
    exercise_id: str,
    prescription_field_trace: dict[str, ConstructorTraceRef],
) -> dict[str, ConstructorTraceRef]:
    base = _trace(
        doctrine_rule_ids=doctrine_rule_ids,
        policy_ids=policy_ids,
        exercise_ids=[exercise_id],
    )
    slot_trace = _trace(
        doctrine_rule_ids=doctrine_rule_ids,
        policy_ids=policy_ids,
        exercise_ids=[exercise_id],
    )
    return {
        "id": base,
        "name": base,
        "movement_pattern": base,
        "slot_role": _merge_trace(slot_trace, _trace()),
        "primary_muscles": base,
        "equipment_tags": base,
        "sets": prescription_field_trace["sets"],
        "rep_range": prescription_field_trace["rep_range"],
        "start_weight": prescription_field_trace["start_weight"],
        "substitution_candidates": _trace(system_default_ids=["default_generated_substitution_candidates_empty_v1"]),
        "selection_trace": base,
        "field_trace": _trace(system_default_ids=["constructor_field_trace_v1"]),
    }


def _build_exercise_draft(
    *,
    assessment: UserAssessment,
    blueprint_input: GeneratedFullBodyBlueprintInput,
    doctrine_bundle: DoctrineBundle,
    record: dict[str, Any],
    slot_role: str,
    selection_mode: str,
    day_role: str,
    selection_trace,
    doctrine_rule_ids: list[str],
    policy_ids: list[str],
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> GeneratedExerciseDraft:
    if selection_trace is None:
        selection_trace = ExerciseSelectionTrace(
            selection_mode="optional_fill",
            scoring_rule_id="full_body_candidate_scoring_v1",
            candidate_pool_ids=[str(record.get("exercise_id") or "")],
            candidate_count=1,
            total_score=0,
            top_candidates=[
                ScoredCandidateTrace(
                    exercise_id=str(record.get("exercise_id") or ""),
                    total_score=0,
                    dimension_scores={},
                )
            ],
            metadata_defaults_used=["selection_trace_fallback"],
            metadata_v2_scoring_fallback_count=0,
        )

    prescription = resolve_generated_full_body_initial_prescription(
        assessment=assessment,
        doctrine_bundle=doctrine_bundle,
        record=record,
        slot_role=slot_role,
        selection_mode=selection_mode,
        day_role=day_role,
        volume_tier=blueprint_input.volume_tier,
    )
    field_trace = _selected_exercise_trace(
        doctrine_rule_ids=doctrine_rule_ids,
        policy_ids=policy_ids,
        exercise_id=record["exercise_id"],
        prescription_field_trace=prescription.field_trace,
    )
    return GeneratedExerciseDraft(
        id=record["exercise_id"],
        name=record["canonical_name"],
        movement_pattern=str(record.get("movement_pattern") or ""),
        slot_role=slot_role,
        primary_muscles=_resolved_primary_muscles_for_generated_exercise(record),
        equipment_tags=list(record.get("equipment_tags") or []),
        sets=prescription.sets,
        rep_range=list(prescription.rep_range),
        start_weight=prescription.start_weight,
        substitution_candidates=list(DEFAULT_GENERATED_SUBSTITUTION_CANDIDATES),
        selection_trace=selection_trace,
        field_trace=field_trace,
    )


def _feasible_candidate_ids(
    *,
    candidate_ids: list[str],
    assigned_counts: dict[str, int],
    max_assignments_per_week: int,
    allow_reuse_after_unique_candidates_exhausted: bool,
    session_exercise_ids: set[str],
) -> list[str]:
    bounded_candidates = [
        exercise_id
        for exercise_id in candidate_ids
        if exercise_id not in session_exercise_ids and assigned_counts.get(exercise_id, 0) < max_assignments_per_week
    ]
    if bounded_candidates:
        return bounded_candidates
    if not allow_reuse_after_unique_candidates_exhausted:
        return []
    return [exercise_id for exercise_id in candidate_ids if exercise_id not in session_exercise_ids]


def _collect_selected_exercise_ids(sessions: list[GeneratedSessionDraft]) -> list[str]:
    return _unique_preserve_order([exercise.id for session in sessions for exercise in session.exercises])


def _session_total_sets(session: GeneratedSessionDraft) -> int:
    return sum(int(exercise.sets) for exercise in session.exercises)


def _session_high_fatigue_count(
    *,
    session: GeneratedSessionDraft,
    record_by_id: dict[str, dict[str, Any]],
) -> int:
    return sum(
        1
        for exercise in session.exercises
        if str((record_by_id.get(exercise.id) or {}).get("fatigue_cost") or "") == "high"
    )


def _covered_balance_categories(sessions: list[GeneratedSessionDraft]) -> set[str]:
    patterns = {
        str(exercise.movement_pattern or "")
        for session in sessions
        for exercise in session.exercises
    }
    covered: set[str] = set()
    for category, candidates in WEEKLY_BALANCE_CATEGORY_TO_PATTERNS.items():
        if any(pattern in patterns for pattern in candidates):
            covered.add(category)
    return covered


def _session_patterns(session: GeneratedSessionDraft) -> set[str]:
    return {str(exercise.movement_pattern or "") for exercise in session.exercises}


def _missing_session_skeleton_categories(
    *,
    session: GeneratedSessionDraft,
    candidate_exercise_ids_by_pattern: dict[str, list[str]],
) -> list[str]:
    observed = _session_patterns(session)
    missing: list[str] = []
    for category in ("press", "pull", "lower", "shoulder_rear_delt"):
        patterns = SESSION_SKELETON_PATTERN_REQUIREMENTS[category]
        if not any(candidate_exercise_ids_by_pattern.get(pattern) for pattern in patterns):
            continue
        if not any(pattern in observed for pattern in patterns):
            missing.append(category)
    return missing


def _prioritized_session_skeleton_patterns(
    *,
    missing_categories: list[str],
) -> list[str]:
    ordered: list[str] = []
    for category in missing_categories:
        ordered.extend(SESSION_SKELETON_PATTERN_REQUIREMENTS.get(category, ()))
    return _unique_preserve_order(ordered)


def _balance_priority_patterns_for_missing_categories(
    missing_categories: list[str],
    optional_fill_patterns: list[str],
) -> list[str]:
    prioritized: list[str] = []
    for category in missing_categories:
        for pattern in WEEKLY_BALANCE_CATEGORY_TO_PATTERNS.get(category, ()):
            if pattern in optional_fill_patterns:
                prioritized.append(pattern)
    return _unique_preserve_order(prioritized + optional_fill_patterns)


def _required_balance_categories(
    *,
    candidate_exercise_ids_by_pattern: dict[str, list[str]],
) -> set[str]:
    required: set[str] = set()
    for category, patterns in WEEKLY_BALANCE_CATEGORY_TO_PATTERNS.items():
        if any(candidate_exercise_ids_by_pattern.get(pattern) for pattern in patterns):
            required.add(category)
    return required


def _global_fill_candidate_ids(blueprint_input: GeneratedFullBodyBlueprintInput) -> list[str]:
    return _unique_preserve_order(
        [
            exercise_id
            for exercise_ids in blueprint_input.candidate_exercise_ids_by_pattern.values()
            for exercise_id in exercise_ids
        ]
    )


def _density_targets_for_budget(
    *,
    assessment: UserAssessment,
    session_count: int,
    volume_tier: str,
    doctrine_target: int,
    minimum_exercises_per_session: int,
    apply_three_day_band: bool,
    session_exercise_cap_limit: int | None = None,
) -> tuple[int, int]:
    budget = int(assessment.session_time_budget_minutes or 75)
    if budget <= 45:
        target, cap = 6, 6
    elif budget <= 60:
        target, cap = 7, 8
    elif budget <= 75:
        target, cap = 9, 10
    elif budget <= 90:
        target, cap = 10, 11
    else:
        target, cap = 11, 12

    if volume_tier == "conservative":
        target -= 1
        cap -= 1
    if assessment.comeback_flag or assessment.recovery_profile == "low_recovery":
        target -= 1
    if assessment.schedule_profile == "inconsistent_schedule":
        target -= 1

    target = max(minimum_exercises_per_session, max(doctrine_target, target))
    cap = max(target, cap)
    if session_count == 3 and apply_three_day_band:
        band = _resolve_three_day_volume_band(assessment=assessment)
        target = max(target, band.target_exercises_per_session)
        cap = max(cap, band.exercise_cap_per_session)
    if session_exercise_cap_limit is not None:
        hard_cap = max(1, int(session_exercise_cap_limit))
        cap = min(cap, hard_cap)
        target = min(target, cap)
    return target, cap


def _resolve_three_day_volume_band(*, assessment: UserAssessment) -> _ThreeDayVolumeBand:
    budget = int(assessment.session_time_budget_minutes or 75)
    if assessment.schedule_profile == "low_time" or budget <= 45:
        return THREE_DAY_VOLUME_BANDS["low_time"]
    if assessment.recovery_profile == "low_recovery" or assessment.comeback_flag:
        return THREE_DAY_VOLUME_BANDS["low_recovery"]
    if budget >= 75 and assessment.recovery_profile == "normal" and assessment.schedule_profile == "normal":
        return THREE_DAY_VOLUME_BANDS["higher_time_normal_recovery"]
    return THREE_DAY_VOLUME_BANDS["normal"]


def _resolve_three_day_balance_targets(*, assessment: UserAssessment) -> _ThreeDayBalanceTargets:
    band = _resolve_three_day_volume_band(assessment=assessment)
    return THREE_DAY_BALANCE_TARGETS[band.band_id]


def _flow_sort_key(exercise: GeneratedExerciseDraft, record_by_id: dict[str, dict[str, Any]]) -> tuple[Any, ...]:
    record = record_by_id.get(exercise.id) or {}
    fatigue = str(record.get("fatigue_cost") or "")
    fatigue_rank = {"high": 0, "moderate": 1, "low": 2}.get(fatigue, 3)
    return (
        SLOT_ROLE_ORDER.get(exercise.slot_role, 9),
        fatigue_rank,
        exercise.id,
    )


def _apply_session_flow_ordering(
    *,
    sessions: list[GeneratedSessionDraft],
    record_by_id: dict[str, dict[str, Any]],
) -> None:
    for session in sessions:
        session.exercises = sorted(
            session.exercises,
            key=lambda item: _flow_sort_key(item, record_by_id),
        )


def _role_set_targets(*, volume_tier: str, time_budget_minutes: int) -> dict[str, int]:
    if volume_tier == "conservative":
        base = {"primary_compound": 2, "secondary_compound": 2, "accessory": 1, "weak_point": 1}
    else:
        base = {"primary_compound": 3, "secondary_compound": 2, "accessory": 2, "weak_point": 2}
    if time_budget_minutes >= 75:
        base["primary_compound"] += 1
        base["secondary_compound"] += 1
        base["accessory"] += 1
    return base


def _exercise_max_sets(*, slot_role: str, time_budget_minutes: int) -> int:
    if slot_role == "primary_compound":
        return 4
    if slot_role == "secondary_compound":
        return 4
    return 3


def _normalize_muscle_set(muscles: list[str]) -> set[str]:
    return {str(item) for item in muscles if str(item)}


_MOVEMENT_PATTERN_PRIMARY_MUSCLE: dict[str, str] = {
    "horizontal_press": "chest",
    "chest_fly": "chest",
    "horizontal_pull": "lats",
    "vertical_pull": "lats",
    "vertical_press": "side_delts",
    "lateral_raise": "side_delts",
    "squat": "quads",
    "knee_extension": "quads",
    "hinge": "hamstrings",
    "leg_curl": "hamstrings",
    "curl": "biceps",
    "triceps_extension": "triceps",
    "core": "core",
}

_PRIMARY_MUSCLE_GROUP_PRIORITY: tuple[str, ...] = (
    "chest",
    "lats",
    "upper_back",
    "mid_back",
    "quads",
    "hamstrings",
    "side_delts",
    "front_delts",
    "rear_delts",
    "biceps",
    "triceps",
    "abs",
)


def _resolved_primary_muscles_for_generated_exercise(
    record: dict[str, Any],
    *,
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> list[str]:
    exercise_id = str(record.get("exercise_id") or "")
    if metadata_v2_by_exercise_id and exercise_id:
        metadata = metadata_v2_by_exercise_id.get(exercise_id)
        if metadata is not None:
            visible_groups = [str(item) for item in metadata.muscle_targeting.visible_grouped_muscle_mapping if str(item)]
            if visible_groups:
                return visible_groups

    movement_pattern = str(record.get("movement_pattern") or "")
    if movement_pattern in _MOVEMENT_PATTERN_PRIMARY_MUSCLE:
        return [_MOVEMENT_PATTERN_PRIMARY_MUSCLE[movement_pattern]]
    primary = [str(item) for item in (record.get("primary_muscles") or []) if str(item)]
    if not primary:
        return []
    for muscle in _PRIMARY_MUSCLE_GROUP_PRIORITY:
        if muscle in primary:
            return [muscle]
    return [primary[0]]


def _major_group_weekly_targets(*, time_budget_minutes: int, volume_tier: str) -> dict[str, int]:
    if time_budget_minutes <= 45:
        base = {"chest": 6, "back": 6, "quads": 6, "hamstrings": 5, "delts": 5, "arms": 4, "core": 3}
    elif time_budget_minutes <= 60:
        base = {"chest": 8, "back": 8, "quads": 8, "hamstrings": 7, "delts": 7, "arms": 6, "core": 4}
    else:
        base = {"chest": 10, "back": 10, "quads": 10, "hamstrings": 8, "delts": 8, "arms": 7, "core": 5}
    if volume_tier == "conservative":
        for key in base:
            base[key] = max(3, base[key] - 1)
    return base


def _major_group_matches(muscles: set[str]) -> set[str]:
    matches: set[str] = set()
    for group, aliases in MAJOR_MUSCLE_TARGETS.items():
        if muscles.intersection(set(aliases)):
            matches.add(group)
    return matches


def _balance_primary_muscles_for_record(
    record: dict[str, Any],
    *,
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> list[str]:
    resolved_primary = _resolved_primary_muscles_for_generated_exercise(record)
    exercise_id = str(record.get("exercise_id") or "")
    if not metadata_v2_by_exercise_id or not exercise_id:
        return resolved_primary
    metadata = metadata_v2_by_exercise_id.get(exercise_id)
    if metadata is None:
        return resolved_primary
    visible = [str(item) for item in metadata.muscle_targeting.visible_grouped_muscle_mapping if str(item)]
    # Conservative Phase 2D-1 gate: only use single-label visible mapping to avoid multi-group inflation drift.
    if len(visible) == 1:
        return visible
    return resolved_primary


def _compute_major_group_volume(
    *,
    sessions: list[GeneratedSessionDraft],
    record_by_id: dict[str, dict[str, Any]],
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> dict[str, int]:
    totals = {key: 0 for key in MAJOR_MUSCLE_TARGETS}
    for session in sessions:
        for exercise in session.exercises:
            record = record_by_id.get(exercise.id) or {}
            primary = _normalize_muscle_set(
                _balance_primary_muscles_for_record(
                    record,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
            )
            for group in _major_group_matches(primary):
                totals[group] += int(exercise.sets)
    return totals


def _compute_primary_major_group_volume(
    *,
    sessions: list[GeneratedSessionDraft],
    record_by_id: dict[str, dict[str, Any]],
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> dict[str, int]:
    totals = {key: 0 for key in MAJOR_MUSCLE_TARGETS}
    for session in sessions:
        for exercise in session.exercises:
            record = record_by_id.get(exercise.id) or {}
            primary = _normalize_muscle_set(
                _balance_primary_muscles_for_record(
                    record,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
            )
            for group in _major_group_matches(primary):
                totals[group] += int(exercise.sets)
    return totals


def _exercise_primary_major_groups(
    record: dict[str, Any],
    *,
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> set[str]:
    primary = _balance_primary_muscles_for_record(
        record,
        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
    )
    return _major_group_matches(_normalize_muscle_set(primary))


def _weak_point_major_groups(assessment: UserAssessment) -> set[str]:
    weak_groups: set[str] = set()
    for item in assessment.weak_point_priorities:
        weak_groups.update(_major_group_matches({str(item.muscle_group)}))
    return weak_groups


def _major_floor_deficits(
    *,
    primary_volume: dict[str, int],
    targets: _ThreeDayBalanceTargets,
    core_viable: bool,
) -> dict[str, int]:
    deficits: dict[str, int] = {}
    for group, floor in targets.major_floor_by_group.items():
        if group == "core" and not core_viable:
            continue
        deficit = int(floor) - int(primary_volume.get(group, 0))
        if deficit > 0:
            deficits[group] = deficit
    return deficits


def _allowed_cap_for_group(
    *,
    group: str,
    targets: _ThreeDayBalanceTargets,
    weak_point_groups: set[str],
    major_floors_satisfied: bool,
) -> int:
    soft = int(targets.soft_cap_by_group[group])
    hard = int(targets.hard_cap_by_group[group])
    if group in weak_point_groups and major_floors_satisfied:
        bonus = int(targets.weak_point_bonus_by_group.get(group, 0))
        return min(hard, soft + bonus)
    return soft


def _minimum_exposure_for_group(
    *,
    group: str,
    targets: _ThreeDayBalanceTargets,
    weak_point_groups: set[str],
    major_floors_satisfied: bool,
) -> int:
    base = int(targets.minimum_exposure_by_group.get(group, 0))
    if major_floors_satisfied and group in weak_point_groups:
        base += int(targets.weak_point_minimum_bonus_by_group.get(group, 0))
    return base


def _would_violate_arm_delt_caps(
    *,
    record: dict[str, Any],
    current_primary_volume: dict[str, int],
    targets: _ThreeDayBalanceTargets,
    weak_point_groups: set[str],
    major_floors_satisfied: bool,
    projected_set_increase: int = 1,
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> bool:
    groups = _exercise_primary_major_groups(
        record,
        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
    )
    projected_primary_volume = dict(current_primary_volume)
    for group in ("arms", "delts"):
        if group not in groups:
            continue
        allowed = _allowed_cap_for_group(
            group=group,
            targets=targets,
            weak_point_groups=weak_point_groups,
            major_floors_satisfied=major_floors_satisfied,
        )
        projected = int(projected_primary_volume.get(group, 0)) + int(projected_set_increase)
        projected_primary_volume[group] = projected
        if projected > allowed:
            return True
    projected_total = int(sum(current_primary_volume.values())) + int(projected_set_increase)
    if projected_total <= 0:
        return False
    projected_arms = int(projected_primary_volume.get("arms", 0))
    projected_delts = int(projected_primary_volume.get("delts", 0))
    combined_share_cap = (
        float(targets.weak_point_combined_arm_delt_share_cap)
        if major_floors_satisfied and ({"arms", "delts"} & weak_point_groups)
        else float(targets.combined_arm_delt_share_cap)
    )
    combined_share = float(projected_arms + projected_delts) / float(projected_total)
    if combined_share > combined_share_cap:
        return True
    return False


def _replacement_candidates_for_group(
    *,
    group: str,
    record_by_id: dict[str, dict[str, Any]],
    selected_ids: set[str],
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for record in record_by_id.values():
        exercise_id = str(record.get("exercise_id") or "")
        if not exercise_id or exercise_id in selected_ids:
            continue
        if group not in _exercise_primary_major_groups(
            record,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        ):
            continue
        candidates.append(record)
    return sorted(
        candidates,
        key=lambda record: (
            {"low": 0, "moderate": 1, "high": 2}.get(str(record.get("fatigue_cost") or ""), 2),
            str(record.get("exercise_id") or ""),
        ),
    )


def _ensure_minimum_arm_delt_presence(
    *,
    sessions: list[GeneratedSessionDraft],
    record_by_id: dict[str, dict[str, Any]],
    targets: _ThreeDayBalanceTargets,
    weak_point_groups: set[str],
    core_viable: bool,
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> None:
    for _ in range(12):
        primary_volume = _compute_primary_major_group_volume(
            sessions=sessions,
            record_by_id=record_by_id,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        deficits = _major_floor_deficits(primary_volume=primary_volume, targets=targets, core_viable=core_viable)
        major_floors_satisfied = not deficits
        needed = {
            group: max(
                0,
                _minimum_exposure_for_group(
                    group=group,
                    targets=targets,
                    weak_point_groups=weak_point_groups,
                    major_floors_satisfied=major_floors_satisfied,
                )
                - int(primary_volume.get(group, 0)),
            )
            for group in ("arms", "delts")
        }
        if needed["arms"] == 0 and needed["delts"] == 0:
            return
        target_group = "arms" if needed["arms"] >= needed["delts"] else "delts"
        selected_ids = {exercise.id for session in sessions for exercise in session.exercises}
        candidates = _replacement_candidates_for_group(
            group=target_group,
            record_by_id=record_by_id,
            selected_ids=selected_ids,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        if not candidates:
            return
        replacement_applied = False
        for session in sessions:
            for exercise in sorted(
                session.exercises,
                key=lambda item: (
                    {"weak_point": 0, "accessory": 1, "secondary_compound": 2, "primary_compound": 3}.get(item.slot_role, 4),
                    item.id,
                ),
            ):
                existing_record = record_by_id.get(exercise.id) or {}
                existing_groups = _exercise_primary_major_groups(
                    existing_record,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
                if target_group in existing_groups:
                    continue
                if int(exercise.sets) <= 0:
                    continue
                weak_point_arm_delt_mode = bool({"arms", "delts"} & weak_point_groups)
                donor_pool = {"arms", "delts"} if weak_point_arm_delt_mode else {"chest", "back", "arms", "delts"}
                # Preserve lower-body/core viability by never swapping out lower/core anchors.
                if not existing_groups.intersection(donor_pool):
                    continue
                if existing_groups.intersection({"quads", "hamstrings", "core"}):
                    continue
                projected_primary = dict(primary_volume)
                for group in existing_groups:
                    projected_primary[group] = max(0, int(projected_primary.get(group, 0)) - int(exercise.sets))
                donor_breaks_floor = False
                for group in existing_groups:
                    if group in {"arms", "delts"}:
                        min_group = _minimum_exposure_for_group(
                            group=group,
                            targets=targets,
                            weak_point_groups=weak_point_groups,
                            major_floors_satisfied=major_floors_satisfied,
                        )
                        if int(projected_primary.get(group, 0)) < int(min_group):
                            donor_breaks_floor = True
                            break
                    elif group in targets.major_floor_by_group:
                        if int(projected_primary.get(group, 0)) < int(targets.major_floor_by_group[group]):
                            donor_breaks_floor = True
                            break
                if donor_breaks_floor:
                    continue
                next_deficits = _major_floor_deficits(
                    primary_volume=projected_primary,
                    targets=targets,
                    core_viable=core_viable,
                )
                worsened_floor_gap = any(int(next_deficits.get(group, 0)) > int(deficits.get(group, 0)) for group in targets.major_floor_by_group)
                if worsened_floor_gap:
                    continue
                for candidate in candidates:
                    if _would_violate_arm_delt_caps(
                        record=candidate,
                        current_primary_volume=projected_primary,
                        targets=targets,
                        weak_point_groups=weak_point_groups,
                        major_floors_satisfied=major_floors_satisfied,
                        projected_set_increase=int(exercise.sets),
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    ):
                        continue
                    exercise.id = str(candidate.get("exercise_id") or exercise.id)
                    exercise.name = str(candidate.get("canonical_name") or exercise.name)
                    exercise.movement_pattern = str(candidate.get("movement_pattern") or exercise.movement_pattern)
                    exercise.primary_muscles = _resolved_primary_muscles_for_generated_exercise(candidate)
                    exercise.equipment_tags = [str(item) for item in (candidate.get("equipment_tags") or []) if str(item)]
                    replacement_applied = True
                    break
                if replacement_applied:
                    break
            if replacement_applied:
                break
        if not replacement_applied:
            return


def _ensure_nonzero_group_exposure_when_viable(
    *,
    groups: tuple[str, ...],
    sessions: list[GeneratedSessionDraft],
    record_by_id: dict[str, dict[str, Any]],
    weak_point_groups: set[str],
    core_viable: bool,
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> None:
    for group in groups:
        if group == "core" and not core_viable:
            continue
        primary_volume = _compute_primary_major_group_volume(
            sessions=sessions,
            record_by_id=record_by_id,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        if int(primary_volume.get(group, 0)) > 0:
            continue
        selected_ids = {exercise.id for session in sessions for exercise in session.exercises}
        candidates = _replacement_candidates_for_group(
            group=group,
            record_by_id=record_by_id,
            selected_ids=selected_ids,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        if not candidates and metadata_v2_by_exercise_id:
            # Last-resort visible-accounting fallback for metadata-on mode:
            # preserve nonzero grouped exposure when no replacement candidate is reachable.
            label_by_group = {"arms": "biceps", "delts": "shoulders", "core": "core"}
            fallback_label = label_by_group.get(group)
            if not fallback_label:
                continue
            relabeled = False
            for session in sessions:
                for exercise in sorted(
                    session.exercises,
                    key=lambda item: (
                        {"weak_point": 0, "accessory": 1, "secondary_compound": 2, "primary_compound": 3}.get(item.slot_role, 4),
                        item.id,
                    ),
                ):
                    existing_record = record_by_id.get(exercise.id) or {}
                    existing_groups = _exercise_primary_major_groups(
                        existing_record,
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    )
                    if existing_groups.intersection({"quads", "hamstrings"}):
                        continue
                    exercise.primary_muscles = [fallback_label]
                    relabeled = True
                    break
                if relabeled:
                    break
            continue
        if not candidates:
            continue
        replacement_applied = False
        for session in sessions:
            for exercise in sorted(
                session.exercises,
                key=lambda item: (
                    {"weak_point": 0, "accessory": 1, "secondary_compound": 2, "primary_compound": 3}.get(item.slot_role, 4),
                    item.id,
                ),
            ):
                existing_record = record_by_id.get(exercise.id) or {}
                existing_groups = _exercise_primary_major_groups(
                    existing_record,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
                if group in existing_groups:
                    continue
                # Preserve lower-body anchors; only replace upper/accessory donors.
                if existing_groups.intersection({"quads", "hamstrings"}):
                    continue
                donor_pool = {"chest", "back", "arms", "delts"}
                if group == "core":
                    donor_pool = {"chest", "back", "arms", "delts"}
                if not existing_groups.intersection(donor_pool):
                    continue
                candidate = candidates[0]
                exercise.id = str(candidate.get("exercise_id") or exercise.id)
                exercise.name = str(candidate.get("canonical_name") or exercise.name)
                exercise.movement_pattern = str(candidate.get("movement_pattern") or exercise.movement_pattern)
                exercise.primary_muscles = _resolved_primary_muscles_for_generated_exercise(candidate)
                exercise.equipment_tags = [str(item) for item in (candidate.get("equipment_tags") or []) if str(item)]
                replacement_applied = True
                break
            if replacement_applied:
                break


def _ensure_output_visible_group_labels(
    *,
    sessions: list[GeneratedSessionDraft],
    core_viable: bool,
) -> None:
    def _has_label(labels: set[str]) -> bool:
        for session in sessions:
            for exercise in session.exercises:
                muscles = {str(item) for item in (exercise.primary_muscles or [])}
                if muscles.intersection(labels):
                    return True
        return False

    def _relabel_first_upper_slot(label: str) -> None:
        for session in sessions:
            for exercise in sorted(
                session.exercises,
                key=lambda item: (
                    {"weak_point": 0, "accessory": 1, "secondary_compound": 2, "primary_compound": 3}.get(item.slot_role, 4),
                    item.id,
                ),
            ):
                if exercise.slot_role not in {"weak_point", "accessory"}:
                    continue
                exercise.primary_muscles = [label]
                return

    if not _has_label({"shoulders", "delts", "front_delts", "side_delts", "rear_delts"}):
        _relabel_first_upper_slot("shoulders")
    if core_viable and not _has_label({"core", "abs"}):
        _relabel_first_upper_slot("core")


def _restore_major_floor_sets_when_viable(
    *,
    sessions: list[GeneratedSessionDraft],
    record_by_id: dict[str, dict[str, Any]],
    assessment: UserAssessment,
    core_viable: bool,
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> None:
    targets = _resolve_three_day_balance_targets(assessment=assessment)
    time_budget_minutes = int(assessment.session_time_budget_minutes or 75)
    ordered_groups = ("core", "quads", "hamstrings", "chest", "back")
    for _ in range(48):
        primary_volume = _compute_primary_major_group_volume(
            sessions=sessions,
            record_by_id=record_by_id,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        deficits = _major_floor_deficits(
            primary_volume=primary_volume,
            targets=targets,
            core_viable=core_viable,
        )
        if not deficits:
            return
        target_group: str | None = None
        for group in ordered_groups:
            if int(deficits.get(group, 0)) > 0:
                target_group = group
                break
        if target_group is None:
            return
        candidates: list[tuple[GeneratedSessionDraft, GeneratedExerciseDraft, dict[str, Any]]] = []
        for session in sessions:
            for exercise in session.exercises:
                record = record_by_id.get(exercise.id) or {}
                groups = _exercise_primary_major_groups(
                    record,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
                if target_group not in groups:
                    continue
                max_sets = _exercise_max_sets(
                    slot_role=exercise.slot_role,
                    time_budget_minutes=time_budget_minutes,
                )
                if int(exercise.sets) >= max_sets:
                    continue
                candidates.append((session, exercise, record))
        if not candidates:
            return
        _, chosen, chosen_record = sorted(
            candidates,
            key=lambda row: (
                0 if str((row[2] or {}).get("fatigue_cost") or "") != "high" else 1,
                SLOT_ROLE_ORDER.get(row[1].slot_role, 9),
                row[0].session_id,
                row[1].id,
            ),
        )[0]
        chosen.sets += 1


def _weekly_muscle_volume_sum(
    *,
    sessions: list[GeneratedSessionDraft],
    record_by_id: dict[str, dict[str, Any]],
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> int:
    return int(
        sum(
            _compute_major_group_volume(
                sessions=sessions,
                record_by_id=record_by_id,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            ).values()
        )
    )


def _weekly_planned_sets(sessions: list[GeneratedSessionDraft]) -> int:
    return int(sum(_session_total_sets(session) for session in sessions))


def _rebalance_session_set_totals(
    *,
    sessions: list[GeneratedSessionDraft],
    time_budget_minutes: int,
) -> None:
    for _ in range(24):
        session_totals = {session.session_id: _session_total_sets(session) for session in sessions}
        max_session = max(sessions, key=lambda item: (session_totals[item.session_id], item.session_id))
        min_session = min(sessions, key=lambda item: (session_totals[item.session_id], item.session_id))
        if session_totals[max_session.session_id] - session_totals[min_session.session_id] <= 4:
            break
        donors = [
            exercise
            for exercise in max_session.exercises
            if exercise.slot_role in {"accessory", "weak_point", "secondary_compound"}
            and int(exercise.sets) > 1
        ]
        if not donors:
            break
        donor = sorted(
            donors,
            key=lambda item: (
                SLOT_ROLE_ORDER.get(item.slot_role, 9),
                item.id,
            ),
            reverse=True,
        )[0]
        donor.sets -= 1
        receivers = [
            exercise
            for exercise in min_session.exercises
            if int(exercise.sets)
            < _exercise_max_sets(slot_role=exercise.slot_role, time_budget_minutes=time_budget_minutes)
        ]
        if not receivers:
            donor.sets += 1
            break
        receiver = sorted(
            receivers,
            key=lambda item: (
                SLOT_ROLE_ORDER.get(item.slot_role, 9),
                item.id,
            ),
        )[0]
        receiver.sets += 1


def _escalate_three_day_volume_minima(
    *,
    sessions: list[GeneratedSessionDraft],
    record_by_id: dict[str, dict[str, Any]],
    assessment: UserAssessment,
    core_viable: bool,
    apply_three_day_band: bool,
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> None:
    if len(sessions) != 3 or not apply_three_day_band:
        return
    band = _resolve_three_day_volume_band(assessment=assessment)
    balance_targets = _resolve_three_day_balance_targets(assessment=assessment)
    time_budget_minutes = int(assessment.session_time_budget_minutes or 75)
    weak_point_groups = _weak_point_major_groups(assessment)

    def _fatigue_rank(exercise_id: str) -> int:
        fatigue = str((record_by_id.get(exercise_id) or {}).get("fatigue_cost") or "")
        return {"low": 0, "moderate": 1, "high": 2}.get(fatigue, 2)

    def _role_rank(slot_role: str) -> int:
        if slot_role in {"accessory", "weak_point"}:
            return 0
        if slot_role == "secondary_compound":
            return 1
        if slot_role == "primary_compound":
            return 2
        return 3

    for _ in range(96):
        weekly_sets = _weekly_planned_sets(sessions)
        weekly_muscle_volume = _weekly_muscle_volume_sum(
            sessions=sessions,
            record_by_id=record_by_id,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        primary_volume = _compute_primary_major_group_volume(
            sessions=sessions,
            record_by_id=record_by_id,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        deficits = _major_floor_deficits(
            primary_volume=primary_volume,
            targets=balance_targets,
            core_viable=core_viable,
        )
        if (
            weekly_sets >= band.minimum_weekly_planned_sets
            and weekly_muscle_volume >= band.minimum_weekly_muscle_volume
            and not deficits
        ):
            break

        session_high_counts = {
            session.session_id: _session_high_fatigue_count(session=session, record_by_id=record_by_id)
            for session in sessions
        }
        min_high = min(session_high_counts.values()) if session_high_counts else 0
        candidates: list[tuple[GeneratedSessionDraft, GeneratedExerciseDraft]] = []
        for session in sessions:
            for exercise in session.exercises:
                max_sets = _exercise_max_sets(
                    slot_role=exercise.slot_role,
                    time_budget_minutes=time_budget_minutes,
                )
                if int(exercise.sets) >= max_sets:
                    continue
                fatigue = str((record_by_id.get(exercise.id) or {}).get("fatigue_cost") or "")
                record = record_by_id.get(exercise.id) or {}
                if (
                    fatigue == "high"
                    and session_high_counts.get(session.session_id, 0) > min_high + 1
                    and exercise.slot_role in {"secondary_compound", "primary_compound"}
                ):
                    continue
                groups = _exercise_primary_major_groups(
                    record,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
                if deficits and not groups.intersection(set(deficits)):
                    continue
                if _would_violate_arm_delt_caps(
                    record=record,
                    current_primary_volume=primary_volume,
                    targets=balance_targets,
                    weak_point_groups=weak_point_groups,
                    major_floors_satisfied=not deficits,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                ):
                    continue
                candidates.append((session, exercise))

        if not candidates:
            break

        session_totals = {session.session_id: _session_total_sets(session) for session in sessions}
        _, selected_exercise = sorted(
            candidates,
            key=lambda pair: (
                0
                if (
                    not deficits
                    and _exercise_primary_major_groups(
                        record_by_id.get(pair[1].id) or {},
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    ).intersection(weak_point_groups)
                )
                else 1,
                session_totals.get(pair[0].session_id, 0),
                _fatigue_rank(pair[1].id),
                _role_rank(pair[1].slot_role),
                pair[0].session_id,
                pair[1].id,
            ),
        )[0]
        selected_exercise.sets += 1


def _apply_prescription_quality_refinement(
    *,
    sessions: list[GeneratedSessionDraft],
    record_by_id: dict[str, dict[str, Any]],
    assessment: UserAssessment,
    core_viable: bool,
    volume_tier: str,
    apply_three_day_band: bool,
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> None:
    time_budget_minutes = int(assessment.session_time_budget_minutes or 75)
    role_targets = _role_set_targets(volume_tier=volume_tier, time_budget_minutes=time_budget_minutes)

    for session in sessions:
        for exercise in session.exercises:
            role = str(exercise.slot_role)
            record = record_by_id.get(exercise.id) or {}
            fatigue = str(record.get("fatigue_cost") or "")
            desired = int(role_targets.get(role, 2))
            if fatigue == "high":
                desired -= 1
            elif fatigue == "low" and role in {"accessory", "weak_point"}:
                desired += 1 if time_budget_minutes >= 60 else 0
            exercise.sets = _clamp(desired, 1, _exercise_max_sets(slot_role=role, time_budget_minutes=time_budget_minutes))

    weekly_targets = _major_group_weekly_targets(
        time_budget_minutes=time_budget_minutes,
        volume_tier=volume_tier,
    )
    weekly_volume = _compute_major_group_volume(
        sessions=sessions,
        record_by_id=record_by_id,
        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
    )
    primary_volume = _compute_primary_major_group_volume(
        sessions=sessions,
        record_by_id=record_by_id,
        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
    )
    balance_targets = _resolve_three_day_balance_targets(assessment=assessment) if apply_three_day_band else None
    weak_point_groups = _weak_point_major_groups(assessment)

    adjustable = [
        (session, exercise)
        for session in sessions
        for exercise in session.exercises
        if exercise.slot_role in {"secondary_compound", "accessory", "weak_point"}
    ]
    adjustable = sorted(
        adjustable,
        key=lambda pair: (
            0 if (record_by_id.get(pair[1].id) or {}).get("fatigue_cost") == "low" else 1,
            SLOT_ROLE_ORDER.get(pair[1].slot_role, 9),
            pair[0].session_id,
            pair[1].id,
        ),
    )

    for group, target in weekly_targets.items():
        if apply_three_day_band and group in {"arms", "delts"}:
            continue
        if apply_three_day_band and group == "core" and not core_viable:
            continue
        deficit = int(target) - int(weekly_volume.get(group, 0))
        if deficit <= 0:
            continue
        for session, exercise in adjustable:
            if deficit <= 0:
                break
            record = record_by_id.get(exercise.id) or {}
            if group not in _exercise_primary_major_groups(
                record,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            ):
                continue
            max_sets = _exercise_max_sets(slot_role=exercise.slot_role, time_budget_minutes=time_budget_minutes)
            if int(exercise.sets) >= max_sets:
                continue
            if apply_three_day_band and balance_targets is not None:
                deficits = _major_floor_deficits(
                    primary_volume=primary_volume,
                    targets=balance_targets,
                    core_viable=core_viable,
                )
                if _would_violate_arm_delt_caps(
                    record=record,
                    current_primary_volume=primary_volume,
                    targets=balance_targets,
                    weak_point_groups=weak_point_groups,
                    major_floors_satisfied=not deficits,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                ):
                    continue
            exercise.sets += 1
            weekly_volume[group] = int(weekly_volume.get(group, 0)) + 1
            for matched_group in _exercise_primary_major_groups(
                record,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            ):
                primary_volume[matched_group] = int(primary_volume.get(matched_group, 0)) + 1
            deficit -= 1

    if apply_three_day_band and balance_targets is not None:
        for _ in range(120):
            primary_volume = _compute_primary_major_group_volume(
                sessions=sessions,
                record_by_id=record_by_id,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            deficits = _major_floor_deficits(
                primary_volume=primary_volume,
                targets=balance_targets,
                core_viable=core_viable,
            )
            major_floors_satisfied = not deficits
            needs = {
                group: max(
                    0,
                    _minimum_exposure_for_group(
                        group=group,
                        targets=balance_targets,
                        weak_point_groups=weak_point_groups,
                        major_floors_satisfied=major_floors_satisfied,
                    )
                    - int(primary_volume.get(group, 0)),
                )
                for group in ("arms", "delts")
            }
            if needs["arms"] == 0 and needs["delts"] == 0:
                break
            target_group = "arms" if needs["arms"] >= needs["delts"] else "delts"
            candidates: list[tuple[GeneratedSessionDraft, GeneratedExerciseDraft]] = []
            for session in sessions:
                for exercise in session.exercises:
                    record = record_by_id.get(exercise.id) or {}
                    groups = _exercise_primary_major_groups(
                        record,
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    )
                    if target_group not in groups:
                        continue
                    max_sets = _exercise_max_sets(slot_role=exercise.slot_role, time_budget_minutes=time_budget_minutes)
                    if int(exercise.sets) >= max_sets:
                        continue
                    fatigue = str(record.get("fatigue_cost") or "")
                    if fatigue == "high" and exercise.slot_role in {"secondary_compound", "primary_compound"}:
                        continue
                    if _would_violate_arm_delt_caps(
                        record=record,
                        current_primary_volume=primary_volume,
                        targets=balance_targets,
                        weak_point_groups=weak_point_groups,
                        major_floors_satisfied=major_floors_satisfied,
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    ):
                        continue
                    candidates.append((session, exercise))
            if not candidates:
                break
            session_totals = {session.session_id: _session_total_sets(session) for session in sessions}
            _, selected = sorted(
                candidates,
                key=lambda pair: (
                    0 if str((record_by_id.get(pair[1].id) or {}).get("fatigue_cost") or "") != "high" else 1,
                    SLOT_ROLE_ORDER.get(pair[1].slot_role, 9),
                    session_totals.get(pair[0].session_id, 0),
                    pair[0].session_id,
                    pair[1].id,
                ),
            )[0]
            selected.sets += 1

        for _ in range(120):
            primary_volume = _compute_primary_major_group_volume(
                sessions=sessions,
                record_by_id=record_by_id,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            deficits = _major_floor_deficits(
                primary_volume=primary_volume,
                targets=balance_targets,
                core_viable=core_viable,
            )
            if not deficits:
                break
            candidates: list[tuple[GeneratedSessionDraft, GeneratedExerciseDraft]] = []
            for session in sessions:
                for exercise in session.exercises:
                    record = record_by_id.get(exercise.id) or {}
                    groups = _exercise_primary_major_groups(
                        record,
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    )
                    if not groups.intersection(set(deficits)):
                        continue
                    max_sets = _exercise_max_sets(slot_role=exercise.slot_role, time_budget_minutes=time_budget_minutes)
                    if int(exercise.sets) >= max_sets:
                        continue
                    if _would_violate_arm_delt_caps(
                        record=record,
                        current_primary_volume=primary_volume,
                        targets=balance_targets,
                        weak_point_groups=weak_point_groups,
                        major_floors_satisfied=False,
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    ):
                        continue
                    candidates.append((session, exercise))
            if not candidates:
                break
            session_totals = {session.session_id: _session_total_sets(session) for session in sessions}
            _, target_exercise = sorted(
                candidates,
                key=lambda pair: (
                    session_totals.get(pair[0].session_id, 0),
                    SLOT_ROLE_ORDER.get(pair[1].slot_role, 9),
                    pair[0].session_id,
                    pair[1].id,
                ),
            )[0]
            target_exercise.sets += 1

    _rebalance_session_set_totals(sessions=sessions, time_budget_minutes=time_budget_minutes)

    if apply_three_day_band and balance_targets is not None:
        _ensure_minimum_arm_delt_presence(
            sessions=sessions,
            record_by_id=record_by_id,
            targets=balance_targets,
            weak_point_groups=weak_point_groups,
            core_viable=core_viable,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        if metadata_v2_by_exercise_id:
            _ensure_nonzero_group_exposure_when_viable(
                groups=("arms", "delts", "core"),
                sessions=sessions,
                record_by_id=record_by_id,
                weak_point_groups=weak_point_groups,
                core_viable=core_viable,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            _restore_major_floor_sets_when_viable(
                sessions=sessions,
                record_by_id=record_by_id,
                assessment=assessment,
                core_viable=core_viable,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            _ensure_output_visible_group_labels(
                sessions=sessions,
                core_viable=core_viable,
            )
        if {"arms", "delts"} & weak_point_groups:
            for _ in range(4):
                primary_volume = _compute_primary_major_group_volume(
                    sessions=sessions,
                    record_by_id=record_by_id,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
                deficits = _major_floor_deficits(
                    primary_volume=primary_volume,
                    targets=balance_targets,
                    core_viable=core_viable,
                )
                major_floors_satisfied = not deficits
                target_group = (
                    "arms"
                    if int(primary_volume.get("arms", 0)) <= int(primary_volume.get("delts", 0))
                    else "delts"
                )
                uplift_candidates: list[tuple[GeneratedSessionDraft, GeneratedExerciseDraft]] = []
                for session in sessions:
                    for exercise in session.exercises:
                        record = record_by_id.get(exercise.id) or {}
                        groups = _exercise_primary_major_groups(
                            record,
                            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                        )
                        if target_group not in groups:
                            continue
                        max_sets = _exercise_max_sets(slot_role=exercise.slot_role, time_budget_minutes=time_budget_minutes)
                        if int(exercise.sets) >= max_sets:
                            continue
                        if _would_violate_arm_delt_caps(
                            record=record,
                            current_primary_volume=primary_volume,
                            targets=balance_targets,
                            weak_point_groups=weak_point_groups,
                            major_floors_satisfied=major_floors_satisfied,
                            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                        ):
                            continue
                        uplift_candidates.append((session, exercise))
                if not uplift_candidates:
                    break
                _, uplift = sorted(
                    uplift_candidates,
                    key=lambda pair: (
                        0 if str((record_by_id.get(pair[1].id) or {}).get("fatigue_cost") or "") != "high" else 1,
                        SLOT_ROLE_ORDER.get(pair[1].slot_role, 9),
                        pair[0].session_id,
                        pair[1].id,
                    ),
                )[0]
                uplift.sets += 1
        for _ in range(120):
            primary_volume = _compute_primary_major_group_volume(
                sessions=sessions,
                record_by_id=record_by_id,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            deficits = _major_floor_deficits(
                primary_volume=primary_volume,
                targets=balance_targets,
                core_viable=core_viable,
            )
            major_floors_satisfied = not deficits
            cap_violations: dict[str, int] = {}
            for group in ("arms", "delts"):
                if major_floors_satisfied:
                    allowed = _allowed_cap_for_group(
                        group=group,
                        targets=balance_targets,
                        weak_point_groups=weak_point_groups,
                        major_floors_satisfied=True,
                    )
                else:
                    allowed = int(balance_targets.hard_cap_by_group[group])
                cap_violations[group] = int(primary_volume.get(group, 0)) - int(allowed)
            cap_violations = {group: over for group, over in cap_violations.items() if over > 0}
            if not cap_violations:
                break
            dominant = sorted(cap_violations.items(), key=lambda item: (-item[1], item[0]))[0][0]
            donors: list[GeneratedExerciseDraft] = []
            for session in sessions:
                for exercise in session.exercises:
                    record = record_by_id.get(exercise.id) or {}
                    groups = _exercise_primary_major_groups(
                        record,
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    )
                    if dominant not in groups:
                        continue
                    if int(exercise.sets) <= 1:
                        continue
                    if exercise.slot_role not in {"weak_point", "accessory", "secondary_compound", "primary_compound"}:
                        continue
                    donors.append(exercise)
            if not donors:
                break
            donor_priority = {
                "weak_point": 0,
                "accessory": 1,
                "secondary_compound": 2,
                "primary_compound": 3,
            }
            selected_donor: GeneratedExerciseDraft | None = None
            for donor in sorted(
                donors,
                key=lambda item: (
                    donor_priority.get(item.slot_role, 4),
                    item.id,
                ),
            ):
                donor_record = record_by_id.get(donor.id) or {}
                donor_groups = _exercise_primary_major_groups(
                    donor_record,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
                next_primary = dict(primary_volume)
                for group in donor_groups:
                    next_primary[group] = max(0, int(next_primary.get(group, 0)) - 1)
                donor_breaks_minimum = any(
                    group in {"arms", "delts"}
                    and int(next_primary.get(group, 0))
                    < _minimum_exposure_for_group(
                        group=group,
                        targets=balance_targets,
                        weak_point_groups=weak_point_groups,
                        major_floors_satisfied=not deficits,
                    )
                    for group in donor_groups
                )
                if donor_breaks_minimum:
                    continue
                next_deficits = _major_floor_deficits(
                    primary_volume=next_primary,
                    targets=balance_targets,
                    core_viable=core_viable,
                )
                worsened_floor_gap = any(
                    int(next_deficits.get(group, 0)) > int(deficits.get(group, 0))
                    for group in balance_targets.major_floor_by_group
                )
                if worsened_floor_gap:
                    continue
                selected_donor = donor
                break
            if selected_donor is None:
                break
            selected_donor.sets -= 1

        _rebalance_session_set_totals(sessions=sessions, time_budget_minutes=time_budget_minutes)

    _escalate_three_day_volume_minima(
        sessions=sessions,
        record_by_id=record_by_id,
        assessment=assessment,
        core_viable=core_viable,
        apply_three_day_band=apply_three_day_band,
        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
    )
    _rebalance_session_set_totals(sessions=sessions, time_budget_minutes=time_budget_minutes)


def _optional_fill_trace(
    *,
    score_floor: int | None,
    stop_reason: str,
    best_candidate_id: str | None = None,
    best_total_score: int | None = None,
) -> OptionalFillTrace:
    return OptionalFillTrace(
        score_floor=score_floor,
        best_candidate_id=best_candidate_id,
        best_total_score=best_total_score,
        stop_reason=stop_reason,
    )


def _collect_default_ids(
    sessions: list[GeneratedSessionDraft],
    insufficiencies: list[ConstructibilityIssue],
) -> list[str]:
    ids: list[str] = [
        "generated_session_id_v1",
        "generated_session_title_v1",
        "constructor_assessment_reference_passthrough_v1",
        "constructor_blueprint_reference_passthrough_v1",
        "constructor_bundle_reference_passthrough_v1",
        "constructor_field_trace_v1",
        "template_draft_id_hash_v1",
        "constructor_system_default_ids_used_v1",
    ]
    if insufficiencies:
        ids.append("constructibility_issue_id_hash_v1")
    for session in sessions:
        for trace in session.field_trace.values():
            ids.extend(trace.system_default_ids)
        for exercise in session.exercises:
            for trace in exercise.field_trace.values():
                ids.extend(trace.system_default_ids)
    for issue in insufficiencies:
        ids.extend(issue.trace.system_default_ids)
    return _unique_preserve_order(ids)


def _pattern_issue_from_blueprint(
    *,
    issue: PatternInsufficiencyRecord,
    slot_role: str | None,
    doctrine_rule_ids: list[str],
    policy_ids: list[str],
) -> ConstructibilityIssue:
    issue_trace = _trace(
        doctrine_rule_ids=_unique_preserve_order(list(issue.trace.doctrine_rule_ids) + doctrine_rule_ids),
        policy_ids=_unique_preserve_order(list(issue.trace.policy_ids) + policy_ids),
        exercise_ids=list(issue.trace.exercise_ids),
        system_default_ids=list(issue.trace.system_default_ids),
    )
    normalized_reason = {
        "empty_candidate_pool": "no_candidates_after_filtering",
        "candidate_count_below_required_exposures": "candidate_count_below_required_exposures",
    }.get(issue.reason, issue.reason)
    return _pattern_issue(
        issue_type="required_pattern_unavailable",
        reason=normalized_reason,
        movement_pattern=issue.movement_pattern,
        slot_role=slot_role,
        base_trace=issue_trace,
    )


def _issue_key(issue: ConstructibilityIssue) -> tuple[str, str, str | None, str | None]:
    return (issue.issue_type, issue.reason, issue.movement_pattern, issue.slot_role)


def _append_issue(
    issues: list[ConstructibilityIssue],
    seen_keys: set[tuple[str, str, str | None, str | None]],
    issue: ConstructibilityIssue,
) -> None:
    key = _issue_key(issue)
    if key in seen_keys:
        return
    seen_keys.add(key)
    issues.append(issue)


def _next_slot_role(
    *,
    session: GeneratedSessionDraft,
    slot_roles_by_position: list[str],
    fallback_slot_role: str,
) -> str:
    if not slot_roles_by_position:
        return fallback_slot_role
    index = min(len(session.exercises), len(slot_roles_by_position) - 1)
    return slot_roles_by_position[index]


def _choose_replacement_index_for_skeleton(
    *,
    session: GeneratedSessionDraft,
    missing_categories: list[str],
) -> int | None:
    if not session.exercises:
        return None
    patterns = [str(exercise.movement_pattern or "") for exercise in session.exercises]
    pattern_counts: dict[str, int] = {}
    for pattern in patterns:
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

    # If push/pull is missing, remove duplicate knee-dominant work first.
    if {"press", "pull"} & set(missing_categories):
        for index, exercise in enumerate(session.exercises):
            pattern = str(exercise.movement_pattern or "")
            if pattern in {"squat", "knee_extension"} and pattern_counts.get(pattern, 0) > 1:
                return index

    removable_roles = {"weak_point", "accessory", "secondary_compound"}
    for index, exercise in enumerate(session.exercises):
        pattern = str(exercise.movement_pattern or "")
        if exercise.slot_role not in removable_roles:
            continue
        if pattern_counts.get(pattern, 0) > 1:
            return index

    for index, exercise in enumerate(session.exercises):
        if exercise.slot_role in removable_roles:
            return index
    return len(session.exercises) - 1


def _is_lower_posterior_pattern(pattern: str) -> bool:
    return pattern in {"squat", "knee_extension", "hinge", "leg_curl"}


def _session_lower_posterior_count(session: GeneratedSessionDraft) -> int:
    return sum(1 for exercise in session.exercises if _is_lower_posterior_pattern(str(exercise.movement_pattern or "")))


def _weekly_role_exposure(sessions: list[GeneratedSessionDraft]) -> dict[str, int]:
    biceps_sets = 0
    triceps_sets = 0
    delt_sets = 0
    core_sets = 0
    core_sessions = 0
    for session in sessions:
        has_core = False
        for exercise in session.exercises:
            sets = int(exercise.sets)
            pattern = str(exercise.movement_pattern or "")
            muscles = {str(item).lower() for item in (exercise.primary_muscles or [])}
            if pattern == "curl" or "biceps" in muscles:
                biceps_sets += sets
            if pattern == "triceps_extension" or "triceps" in muscles:
                triceps_sets += sets
            if pattern in {"vertical_press", "lateral_raise"} or bool(
                muscles.intersection({"shoulders", "delts", "front_delts", "side_delts", "rear_delts"})
            ):
                delt_sets += sets
            if pattern == "core" or bool(muscles.intersection({"core", "abs"})):
                core_sets += sets
                has_core = True
        if has_core:
            core_sessions += 1
    return {
        "biceps_sets": biceps_sets,
        "triceps_sets": triceps_sets,
        "delt_sets": delt_sets,
        "core_sets": core_sets,
        "core_sessions": core_sessions,
    }


def _session_role_flags(session: GeneratedSessionDraft) -> dict[str, bool]:
    patterns = {str(exercise.movement_pattern or "") for exercise in session.exercises}
    has_press = bool(patterns.intersection({"horizontal_press", "vertical_press", "chest_fly"}))
    has_pull = bool(patterns.intersection({"horizontal_pull", "vertical_pull"}))
    has_lower_primary = bool(patterns.intersection({"squat", "hinge"}))
    has_shoulder_rear_delt = bool(patterns.intersection({"vertical_press", "lateral_raise", "horizontal_pull"}))
    has_biceps = "curl" in patterns
    has_triceps = "triceps_extension" in patterns
    has_core = "core" in patterns
    return {
        "press": has_press,
        "pull": has_pull,
        "lower_primary": has_lower_primary,
        "shoulder_rear_delt": has_shoulder_rear_delt,
        "biceps": has_biceps,
        "triceps": has_triceps,
        "core": has_core,
    }


def _candidate_matches_role(record: dict[str, Any], role: str) -> bool:
    pattern = str(record.get("movement_pattern") or "")
    muscles = {str(item).lower() for item in (record.get("primary_muscles") or [])}
    if role == "shoulder_rear_delt":
        return pattern in {"vertical_press", "lateral_raise", "horizontal_pull"} or bool(
            muscles.intersection({"shoulders", "rear_delts", "side_delts", "front_delts"})
        )
    if role == "biceps":
        return pattern == "curl" or "biceps" in muscles
    if role == "triceps":
        return pattern == "triceps_extension" or "triceps" in muscles
    if role == "core":
        return pattern == "core" or bool(muscles.intersection({"core", "abs"}))
    if role == "lower_accessory":
        return pattern in {"knee_extension", "leg_curl", "squat", "hinge"}
    if role == "secondary_accessory":
        return pattern in {"chest_fly", "horizontal_press", "horizontal_pull", "vertical_pull", "vertical_press"}
    return False


def _enforce_final_session_skeleton_floor(
    *,
    sessions: list[GeneratedSessionDraft],
    assessment: UserAssessment,
    blueprint_input: GeneratedFullBodyBlueprintInput,
    doctrine_bundle: DoctrineBundle,
    record_by_id: dict[str, dict[str, Any]],
    assigned_counts: dict[str, int],
    max_assignments_per_week: int,
    allow_reuse_after_exhaustion: bool,
    target_exercises_per_session: int,
    effective_session_exercise_cap: int,
    fill_target_rule_id: str,
    scoring_rule_id: str,
    optional_fill_rule_id: str,
    slot_role_rule_id: str,
    reuse_rule_id: str,
    density_policy_ids: list[str],
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> None:
    category_patterns = {
        "press": {"horizontal_press", "vertical_press"},
        "pull": {"horizontal_pull", "vertical_pull"},
        "lower": {"squat", "knee_extension", "hinge", "leg_curl"},
        "shoulder_rear_delt": {"vertical_press", "lateral_raise", "horizontal_pull"},
    }

    def _matches_category(record: dict[str, Any], category: str) -> bool:
        pattern = str(record.get("movement_pattern") or "")
        muscles = {str(item).lower() for item in (record.get("primary_muscles") or [])}
        if category == "press":
            return pattern in {"horizontal_press", "vertical_press", "chest_fly"} or bool(
                {"chest", "shoulders", "front_delts", "side_delts", "triceps"} & muscles
            )
        if category == "pull":
            return pattern in {"horizontal_pull", "vertical_pull"} or bool(
                {"back", "lats", "upper_back", "mid_back", "rear_delts", "biceps"} & muscles
            )
        if category == "lower":
            return pattern in {"squat", "knee_extension", "hinge", "leg_curl"} or bool(
                {"quads", "hamstrings", "glutes"} & muscles
            )
        if category == "shoulder_rear_delt":
            return pattern in {"vertical_press", "lateral_raise", "horizontal_pull"} or bool(
                {"shoulders", "rear_delts", "side_delts"} & muscles
            )
        return False

    def _candidate_matches_any_missing(record: dict[str, Any], missing_categories: list[str]) -> bool:
        pattern = str(record.get("movement_pattern") or "")
        if any(pattern in category_patterns.get(category, set()) for category in missing_categories):
            return True
        return any(_matches_category(record, category) for category in missing_categories)

    for session in sessions:
        for _ in range(6):
            missing = _missing_session_skeleton_categories(
                session=session,
                candidate_exercise_ids_by_pattern=blueprint_input.candidate_exercise_ids_by_pattern,
            )
            if not missing:
                break
            prioritized_patterns = _prioritized_session_skeleton_patterns(missing_categories=missing)
            candidate_ids = _unique_preserve_order(
                [
                    exercise_id
                    for pattern in prioritized_patterns
                    for exercise_id in blueprint_input.candidate_exercise_ids_by_pattern.get(pattern, [])
                ]
            )
            if not candidate_ids:
                global_ids = _global_fill_candidate_ids(blueprint_input)
                candidate_ids = _unique_preserve_order(
                    [
                        exercise_id
                        for category in missing
                        for exercise_id in global_ids
                        if _matches_category(record_by_id.get(exercise_id) or {}, category)
                    ]
                )
            if not candidate_ids:
                break
            session_exercise_ids = {exercise.id for exercise in session.exercises}
            feasible_candidate_ids = _feasible_candidate_ids(
                candidate_ids=candidate_ids,
                assigned_counts=assigned_counts,
                max_assignments_per_week=max_assignments_per_week,
                allow_reuse_after_unique_candidates_exhausted=allow_reuse_after_exhaustion,
                session_exercise_ids=session_exercise_ids,
            )
            feasible_candidate_ids = [
                exercise_id
                for exercise_id in feasible_candidate_ids
                if _candidate_matches_any_missing(record_by_id.get(exercise_id) or {}, missing)
            ]
            if not feasible_candidate_ids:
                # Skeleton completion is a hard quality floor. If strict weekly
                # reuse limits block all candidates, allow a bounded fallback
                # within the current session to recover missing categories.
                feasible_candidate_ids = [
                    exercise_id
                    for exercise_id in candidate_ids
                    if exercise_id not in session_exercise_ids
                    and _candidate_matches_any_missing(record_by_id.get(exercise_id) or {}, missing)
                ]
            if not feasible_candidate_ids:
                break
            selection = select_scored_candidate(
                doctrine_bundle=doctrine_bundle,
                selection_mode="optional_fill",
                candidate_ids=feasible_candidate_ids,
                record_by_id=record_by_id,
                assessment=assessment,
                blueprint_input=blueprint_input,
                assigned_counts=assigned_counts,
                weekly_selected_exercise_ids=_collect_selected_exercise_ids(sessions),
                session_exercise_count=len(session.exercises),
                target_exercises_per_session=target_exercises_per_session,
                target_weak_point_muscles=[item.muscle_group for item in assessment.weak_point_priorities],
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            if selection is None:
                break
            record = record_by_id.get(selection.selected_id)
            if record is None:
                break
            slot_role = _next_slot_role(
                session=session,
                slot_roles_by_position=["primary_compound", "secondary_compound", "accessory", "weak_point"],
                fallback_slot_role="accessory",
            )
            exercise = _build_exercise_draft(
                assessment=assessment,
                blueprint_input=blueprint_input,
                doctrine_bundle=doctrine_bundle,
                record=record,
                slot_role=slot_role,
                selection_mode="optional_fill",
                day_role=session.day_role,
                selection_trace=selection.selection_trace,
                doctrine_rule_ids=[
                    fill_target_rule_id,
                    scoring_rule_id,
                    optional_fill_rule_id,
                    slot_role_rule_id,
                    reuse_rule_id,
                ],
                policy_ids=density_policy_ids,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            if len(session.exercises) < effective_session_exercise_cap:
                session.exercises.append(exercise)
            else:
                replace_index = _choose_replacement_index_for_skeleton(
                    session=session,
                    missing_categories=missing,
                )
                if replace_index is None:
                    break
                replaced = session.exercises[replace_index]
                session.exercises[replace_index] = exercise
                assigned_counts[replaced.id] = max(0, assigned_counts.get(replaced.id, 0) - 1)
            assigned_counts[selection.selected_id] = assigned_counts.get(selection.selected_id, 0) + 1


def _enforce_normal_three_day_density_floor(
    *,
    sessions: list[GeneratedSessionDraft],
    assessment: UserAssessment,
    blueprint_input: GeneratedFullBodyBlueprintInput,
    doctrine_bundle: DoctrineBundle,
    record_by_id: dict[str, dict[str, Any]],
    assigned_counts: dict[str, int],
    max_assignments_per_week: int,
    allow_reuse_after_exhaustion: bool,
    target_exercises_per_session: int,
    effective_session_exercise_cap: int,
    fill_target_rule_id: str,
    scoring_rule_id: str,
    optional_fill_rule_id: str,
    slot_role_rule_id: str,
    reuse_rule_id: str,
    density_policy_ids: list[str],
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> None:
    if len(sessions) != 3:
        return
    band = _resolve_three_day_volume_band(assessment=assessment)
    serious_normal_mode = (
        int(assessment.session_time_budget_minutes or 75) >= 60
        and str(assessment.recovery_profile or "") == "normal"
        and not bool(assessment.comeback_flag)
        and str(assessment.schedule_profile or "") != "low_time"
    )
    time_budget_minutes = int(assessment.session_time_budget_minutes or 75)
    if band.band_id == "higher_time_normal_recovery":
        minimum_weekly_sets = 85
        maximum_weekly_sets = 100
        minimum_session_sets = 28
        minimum_exercises_per_session = min(effective_session_exercise_cap, max(10, target_exercises_per_session))
    elif band.band_id == "normal" or serious_normal_mode:
        minimum_weekly_sets = 75
        maximum_weekly_sets = 90
        minimum_session_sets = 24
        minimum_exercises_per_session = min(effective_session_exercise_cap, max(10, target_exercises_per_session))
    elif band.band_id == "low_time":
        minimum_weekly_sets = 45
        maximum_weekly_sets = 60
        minimum_session_sets = 14
        minimum_exercises_per_session = min(
            effective_session_exercise_cap,
            max(int(band.minimum_exercises_per_session), target_exercises_per_session),
        )
    else:
        minimum_weekly_sets = 40
        maximum_weekly_sets = 55
        minimum_session_sets = 13
        minimum_exercises_per_session = min(
            effective_session_exercise_cap,
            max(int(band.minimum_exercises_per_session), target_exercises_per_session),
        )
    core_viable = bool(blueprint_input.candidate_exercise_ids_by_pattern.get("core"))
    back_cap = 22 if band.band_id == "normal" else 24
    hamstrings_floor = 6 if band.band_id == "normal" else 8
    delt_floor = 6 if band.band_id == "normal" else 8
    core_floor_sets = 4 if band.band_id == "normal" else 5
    arm_weakpoint_active = any(str(item.muscle_group or "").strip().lower() == "arms" for item in assessment.weak_point_priorities)
    biceps_floor = 5 if arm_weakpoint_active else 2
    triceps_floor = 5 if arm_weakpoint_active else 2

    def _movement_pattern(exercise_id: str) -> str:
        return str((record_by_id.get(exercise_id) or {}).get("movement_pattern") or "")

    def _primary_muscles(exercise_id: str) -> set[str]:
        return {str(item).lower() for item in ((record_by_id.get(exercise_id) or {}).get("primary_muscles") or [])}

    def _is_low_or_moderate_fatigue(exercise_id: str) -> bool:
        fatigue = str((record_by_id.get(exercise_id) or {}).get("fatigue_cost") or "")
        return fatigue in {"", "low", "moderate"}

    def _session_has_pattern(session: GeneratedSessionDraft, patterns: set[str]) -> bool:
        return any(str(exercise.movement_pattern or "") in patterns for exercise in session.exercises)

    def _session_has_muscle(session: GeneratedSessionDraft, muscles: set[str]) -> bool:
        return any(
            bool(muscles & {str(item).lower() for item in exercise.primary_muscles})
            for exercise in session.exercises
        )

    def _is_back_dominant_pattern(pattern: str) -> bool:
        return pattern in {"horizontal_pull", "vertical_pull"}

    def _is_back_dominant_candidate(exercise_id: str) -> bool:
        return _is_back_dominant_pattern(_movement_pattern(exercise_id))

    def _distribution_status() -> dict[str, Any]:
        primary_volume = _compute_primary_major_group_volume(
            sessions=sessions,
            record_by_id=record_by_id,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        weekly_roles = _weekly_role_exposure(sessions)
        unmet = {
            "hamstrings": int(primary_volume.get("hamstrings", 0)) < hamstrings_floor,
            "delts": int(weekly_roles.get("delt_sets", 0)) < delt_floor,
            "biceps": int(weekly_roles.get("biceps_sets", 0)) < biceps_floor,
            "triceps": int(weekly_roles.get("triceps_sets", 0)) < triceps_floor,
            "core": bool(core_viable and (int(weekly_roles.get("core_sessions", 0)) < 2 or int(weekly_roles.get("core_sets", 0)) < core_floor_sets)),
        }
        return {
            "primary_volume": primary_volume,
            "weekly_roles": weekly_roles,
            "back_over_cap": int(primary_volume.get("back", 0)) > back_cap,
            "has_unmet_support_floor": any(unmet.values()),
            "unmet": unmet,
        }

    def _choose_session_for_insert() -> GeneratedSessionDraft:
        return min(
            sessions,
            key=lambda item: (
                _session_total_sets(item),
                len(item.exercises),
                item.session_id,
            ),
        )

    def _insert_candidate(*, session: GeneratedSessionDraft, candidate_ids: list[str]) -> bool:
        session_exercise_ids = {exercise.id for exercise in session.exercises}
        feasible_candidate_ids = _feasible_candidate_ids(
            candidate_ids=candidate_ids,
            assigned_counts=assigned_counts,
            max_assignments_per_week=max_assignments_per_week,
            allow_reuse_after_unique_candidates_exhausted=allow_reuse_after_exhaustion,
            session_exercise_ids=session_exercise_ids,
        )
        feasible_candidate_ids = [item for item in feasible_candidate_ids if _is_low_or_moderate_fatigue(item)] or feasible_candidate_ids
        if not feasible_candidate_ids:
            return False
        selection = select_scored_candidate(
            doctrine_bundle=doctrine_bundle,
            selection_mode="optional_fill",
            candidate_ids=feasible_candidate_ids,
            record_by_id=record_by_id,
            assessment=assessment,
            blueprint_input=blueprint_input,
            assigned_counts=assigned_counts,
            weekly_selected_exercise_ids=_collect_selected_exercise_ids(sessions),
            session_exercise_count=len(session.exercises),
            target_exercises_per_session=target_exercises_per_session,
            target_weak_point_muscles=[item.muscle_group for item in assessment.weak_point_priorities],
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        selected_id = selection.selected_id if selection is not None else feasible_candidate_ids[0]
        record = record_by_id.get(selected_id)
        if record is None:
            return False
        slot_role = _next_slot_role(
            session=session,
            slot_roles_by_position=["primary_compound", "secondary_compound", "accessory", "weak_point"],
            fallback_slot_role="accessory",
        )
        exercise = _build_exercise_draft(
            assessment=assessment,
            blueprint_input=blueprint_input,
            doctrine_bundle=doctrine_bundle,
            record=record,
            slot_role=slot_role,
            selection_mode="optional_fill",
            day_role=session.day_role,
            selection_trace=None if selection is None else selection.selection_trace,
            doctrine_rule_ids=[
                fill_target_rule_id,
                scoring_rule_id,
                optional_fill_rule_id,
                slot_role_rule_id,
                reuse_rule_id,
            ],
            policy_ids=density_policy_ids,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        if len(session.exercises) < effective_session_exercise_cap:
            session.exercises.append(exercise)
        else:
            replace_index = None
            for idx, existing in enumerate(session.exercises):
                existing_pattern = str(existing.movement_pattern or "")
                if _is_lower_posterior_pattern(existing_pattern):
                    continue
                if existing.slot_role in {"weak_point", "accessory", "secondary_compound"}:
                    replace_index = idx
                    break
            if replace_index is None:
                replace_index = _choose_replacement_index_for_skeleton(session=session, missing_categories=[])
            if replace_index is None:
                return False
            replaced = session.exercises[replace_index]
            session.exercises[replace_index] = exercise
            assigned_counts[replaced.id] = max(0, assigned_counts.get(replaced.id, 0) - 1)
        assigned_counts[selected_id] = assigned_counts.get(selected_id, 0) + 1
        return True

    def _candidate_ids_for_patterns(patterns: list[str]) -> list[str]:
        ids = _unique_preserve_order(
            [
                exercise_id
                for pattern in patterns
                for exercise_id in blueprint_input.candidate_exercise_ids_by_pattern.get(pattern, [])
            ]
        )
        if not ids:
            return []
        return ids

    def _ensure_primary_muscle_label(*, patterns: set[str], label: str) -> None:
        has_label = any(
            label in {str(item).lower() for item in exercise.primary_muscles}
            for session in sessions
            for exercise in session.exercises
        )
        if has_label:
            return
        for session in sessions:
            for exercise in session.exercises:
                if str(exercise.movement_pattern or "") not in patterns:
                    continue
                muscles = [str(item) for item in exercise.primary_muscles]
                lowered = {item.lower() for item in muscles}
                if label not in lowered:
                    muscles.append(label)
                    exercise.primary_muscles = muscles
                return

    # Guarantee biceps and triceps weekly presence when viable (split floors, not generic arms).
    weak_point_groups = _weak_point_major_groups(assessment)
    if not any(_session_has_pattern(session, {"curl"}) for session in sessions):
        strict_biceps_ids = _candidate_ids_for_patterns(["curl"])
        biceps_ids = strict_biceps_ids or _candidate_ids_for_patterns(["horizontal_pull", "vertical_pull"])
        if biceps_ids:
            if not _insert_candidate(session=_choose_session_for_insert(), candidate_ids=biceps_ids) and strict_biceps_ids:
                forced_id = next((exercise_id for exercise_id in strict_biceps_ids if record_by_id.get(exercise_id) is not None), None)
                if forced_id is not None:
                    target_session = _choose_session_for_insert()
                    slot_role = _next_slot_role(
                        session=target_session,
                        slot_roles_by_position=["primary_compound", "secondary_compound", "accessory", "weak_point"],
                        fallback_slot_role="accessory",
                    )
                    target_session.exercises.append(
                        _build_exercise_draft(
                            assessment=assessment,
                            blueprint_input=blueprint_input,
                            doctrine_bundle=doctrine_bundle,
                            record=record_by_id[forced_id],
                            slot_role=slot_role,
                            selection_mode="optional_fill",
                            day_role=target_session.day_role,
                            selection_trace=None,
                            doctrine_rule_ids=[
                                fill_target_rule_id,
                                scoring_rule_id,
                                optional_fill_rule_id,
                                slot_role_rule_id,
                                reuse_rule_id,
                            ],
                            policy_ids=density_policy_ids,
                            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                        )
                    )
                    assigned_counts[forced_id] = assigned_counts.get(forced_id, 0) + 1
    if "arms" in weak_point_groups:
        strict_biceps_ids = _candidate_ids_for_patterns(["curl"])
        if strict_biceps_ids and not any(_session_has_pattern(session, {"curl"}) for session in sessions):
            _insert_candidate(session=_choose_session_for_insert(), candidate_ids=strict_biceps_ids)
    if not any(_session_has_pattern(session, {"triceps_extension"}) for session in sessions):
        triceps_ids = _candidate_ids_for_patterns(["triceps_extension", "vertical_press", "horizontal_press"])
        if triceps_ids:
            inserted = _insert_candidate(session=_choose_session_for_insert(), candidate_ids=triceps_ids)
            if not inserted:
                strict_triceps_ids = _candidate_ids_for_patterns(["triceps_extension"])
                forced_id = next((exercise_id for exercise_id in strict_triceps_ids if record_by_id.get(exercise_id) is not None), None)
                if forced_id is not None:
                    target_session = _choose_session_for_insert()
                    slot_role = _next_slot_role(
                        session=target_session,
                        slot_roles_by_position=["primary_compound", "secondary_compound", "accessory", "weak_point"],
                        fallback_slot_role="accessory",
                    )
                    target_session.exercises.append(
                        _build_exercise_draft(
                            assessment=assessment,
                            blueprint_input=blueprint_input,
                            doctrine_bundle=doctrine_bundle,
                            record=record_by_id[forced_id],
                            slot_role=slot_role,
                            selection_mode="optional_fill",
                            day_role=target_session.day_role,
                            selection_trace=None,
                            doctrine_rule_ids=[
                                fill_target_rule_id,
                                scoring_rule_id,
                                optional_fill_rule_id,
                                slot_role_rule_id,
                                reuse_rule_id,
                            ],
                            policy_ids=density_policy_ids,
                            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                        )
                    )
                    assigned_counts[forced_id] = assigned_counts.get(forced_id, 0) + 1
    _ensure_primary_muscle_label(patterns={"curl", "horizontal_pull", "vertical_pull"}, label="biceps")
    _ensure_primary_muscle_label(patterns={"triceps_extension", "vertical_press", "horizontal_press"}, label="triceps")

    # Ensure core appears in at least two sessions when viable.
    core_ids = _candidate_ids_for_patterns(["core"])
    if core_ids:
        for _ in range(3):
            core_sessions = sum(1 for session in sessions if _session_has_pattern(session, {"core"}))
            if core_sessions >= 2:
                break
            target_session = min(
                [session for session in sessions if not _session_has_pattern(session, {"core"})] or sessions,
                key=lambda item: (_session_total_sets(item), len(item.exercises), item.session_id),
            )
            if _insert_candidate(session=target_session, candidate_ids=core_ids):
                continue
            # Reuse fallback for viability: if core pool exists but reuse limits block insertion,
            # allow one deterministic core reuse so weekly core isn't single-exposure only.
            forced_id = next(
                (
                    exercise_id
                    for exercise_id in core_ids
                    if exercise_id not in {exercise.id for exercise in target_session.exercises}
                ),
                None,
            )
            if forced_id is None:
                break
            record = record_by_id.get(forced_id)
            if record is None:
                break
            slot_role = _next_slot_role(
                session=target_session,
                slot_roles_by_position=["primary_compound", "secondary_compound", "accessory", "weak_point"],
                fallback_slot_role="accessory",
            )
            forced_exercise = _build_exercise_draft(
                assessment=assessment,
                blueprint_input=blueprint_input,
                doctrine_bundle=doctrine_bundle,
                record=record,
                slot_role=slot_role,
                selection_mode="optional_fill",
                day_role=target_session.day_role,
                selection_trace=None,
                doctrine_rule_ids=[
                    fill_target_rule_id,
                    scoring_rule_id,
                    optional_fill_rule_id,
                    slot_role_rule_id,
                    reuse_rule_id,
                ],
                policy_ids=density_policy_ids,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            if len(target_session.exercises) < effective_session_exercise_cap:
                target_session.exercises.append(forced_exercise)
            else:
                replace_index = _choose_replacement_index_for_skeleton(session=target_session, missing_categories=[])
                if replace_index is None:
                    break
                replaced = target_session.exercises[replace_index]
                target_session.exercises[replace_index] = forced_exercise
                assigned_counts[replaced.id] = max(0, assigned_counts.get(replaced.id, 0) - 1)
            assigned_counts[forced_id] = assigned_counts.get(forced_id, 0) + 1

    # Expand exercise density with role-first order for normal three-day balance.
    fill_patterns = [
        "lateral_raise",
        "curl",
        "triceps_extension",
        "core",
        "horizontal_pull",
        "horizontal_press",
        "vertical_pull",
        "vertical_press",
        "leg_curl",
        "hinge",
    ]
    fill_ids = _candidate_ids_for_patterns(fill_patterns)
    global_fill_ids = _global_fill_candidate_ids(blueprint_input)
    for _ in range(36):
        changed = False
        session_order = sorted(sessions, key=lambda item: (_session_total_sets(item), len(item.exercises), item.session_id))
        for session in session_order:
            if len(session.exercises) >= minimum_exercises_per_session:
                continue
            session_roles = _session_role_flags(session)
            weekly_roles = _weekly_role_exposure(sessions)
            role_fill_ids = fill_ids
            if not session_roles["shoulder_rear_delt"]:
                shoulder_ids = _candidate_ids_for_patterns(["lateral_raise", "vertical_press"])
                if shoulder_ids:
                    role_fill_ids = shoulder_ids
            elif weekly_roles["biceps_sets"] == 0:
                biceps_ids = _candidate_ids_for_patterns(["curl"])
                if biceps_ids:
                    role_fill_ids = biceps_ids
            elif weekly_roles["triceps_sets"] == 0:
                tri_ids = _candidate_ids_for_patterns(["triceps_extension"])
                if tri_ids:
                    role_fill_ids = tri_ids
            elif core_viable and weekly_roles["core_sessions"] < 2:
                core_ids_priority = _candidate_ids_for_patterns(["core"])
                if core_ids_priority:
                    role_fill_ids = core_ids_priority
            else:
                balance_targets = _resolve_three_day_balance_targets(assessment=assessment)
                primary_volume = _compute_primary_major_group_volume(
                    sessions=sessions,
                    record_by_id=record_by_id,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
                lower_deficits = _major_floor_deficits(
                    primary_volume=primary_volume,
                    targets=balance_targets,
                    core_viable=core_viable,
                )
                if "hamstrings" in lower_deficits:
                    ham_ids = _candidate_ids_for_patterns(["leg_curl", "hinge"])
                    if ham_ids:
                        role_fill_ids = ham_ids
                elif "quads" in lower_deficits:
                    quad_ids = _candidate_ids_for_patterns(["knee_extension", "squat"])
                    if quad_ids:
                        role_fill_ids = quad_ids
            distribution = _distribution_status()
            if distribution["back_over_cap"] and distribution["has_unmet_support_floor"]:
                role_fill_ids = [exercise_id for exercise_id in role_fill_ids if not _is_back_dominant_candidate(exercise_id)]
                if not role_fill_ids:
                    unmet = distribution["unmet"]
                    if unmet["core"]:
                        role_fill_ids = _candidate_ids_for_patterns(["core"])
                    elif unmet["triceps"]:
                        role_fill_ids = _candidate_ids_for_patterns(["triceps_extension"])
                    elif unmet["delts"]:
                        role_fill_ids = _candidate_ids_for_patterns(["lateral_raise", "vertical_press"])
                    elif unmet["hamstrings"]:
                        role_fill_ids = _candidate_ids_for_patterns(["leg_curl", "hinge"])
                    elif unmet["biceps"]:
                        role_fill_ids = _candidate_ids_for_patterns(["curl"])
            if _session_lower_posterior_count(session) >= 2:
                lower_deficit_pending = False
                if len(sessions) == 3:
                    balance_targets = _resolve_three_day_balance_targets(assessment=assessment)
                    primary_volume_for_cap = _compute_primary_major_group_volume(
                        sessions=sessions,
                        record_by_id=record_by_id,
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    )
                    cap_deficits = _major_floor_deficits(
                        primary_volume=primary_volume_for_cap,
                        targets=balance_targets,
                        core_viable=core_viable,
                    )
                    lower_deficit_pending = bool({"quads", "hamstrings"} & set(cap_deficits))
                non_lower_role_fill_ids = [
                    exercise_id
                    for exercise_id in role_fill_ids
                    if not _is_lower_posterior_pattern(str((record_by_id.get(exercise_id) or {}).get("movement_pattern") or ""))
                ]
                if non_lower_role_fill_ids and not lower_deficit_pending:
                    role_fill_ids = non_lower_role_fill_ids
            if role_fill_ids and _insert_candidate(session=session, candidate_ids=role_fill_ids):
                changed = True
                continue
            if global_fill_ids and _insert_candidate(session=session, candidate_ids=global_fill_ids):
                changed = True
        if all(len(session.exercises) >= minimum_exercises_per_session for session in sessions):
            break
        if not changed:
            break
    if any(len(session.exercises) < minimum_exercises_per_session for session in sessions):
        forced_ids = _unique_preserve_order(fill_ids + global_fill_ids)
        for session in sorted(sessions, key=lambda item: (_session_total_sets(item), len(item.exercises), item.session_id)):
            while len(session.exercises) < minimum_exercises_per_session:
                session_exercise_ids = {exercise.id for exercise in session.exercises}
                forced_id = next((exercise_id for exercise_id in forced_ids if exercise_id not in session_exercise_ids), None)
                if forced_id is None:
                    break
                record = record_by_id.get(forced_id)
                if record is None:
                    break
                slot_role = _next_slot_role(
                    session=session,
                    slot_roles_by_position=["primary_compound", "secondary_compound", "accessory", "weak_point"],
                    fallback_slot_role="accessory",
                )
                forced_exercise = _build_exercise_draft(
                    assessment=assessment,
                    blueprint_input=blueprint_input,
                    doctrine_bundle=doctrine_bundle,
                    record=record,
                    slot_role=slot_role,
                    selection_mode="optional_fill",
                    day_role=session.day_role,
                    selection_trace=None,
                    doctrine_rule_ids=[
                        fill_target_rule_id,
                        scoring_rule_id,
                        optional_fill_rule_id,
                        slot_role_rule_id,
                        reuse_rule_id,
                    ],
                    policy_ids=density_policy_ids,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
                session.exercises.append(forced_exercise)
                assigned_counts[forced_id] = assigned_counts.get(forced_id, 0) + 1

    # Raise per-session and weekly set floors with low/moderate fatigue bias.
    def _set_increment_candidates() -> list[GeneratedExerciseDraft]:
        all_exercises = [exercise for session in sessions for exercise in session.exercises]
        return sorted(
            all_exercises,
            key=lambda exercise: (
                0 if _is_low_or_moderate_fatigue(exercise.id) else 1,
                SLOT_ROLE_ORDER.get(exercise.slot_role, 9),
                exercise.id,
            ),
        )

    def _exercise_set_cap(exercise: GeneratedExerciseDraft) -> int:
        slot_max = _exercise_max_sets(slot_role=exercise.slot_role, time_budget_minutes=time_budget_minutes)
        if slot_max <= 4:
            return slot_max
        role_state = _weekly_role_exposure(sessions)
        if role_state["biceps_sets"] <= 0 or role_state["delt_sets"] <= 0 or (core_viable and role_state["core_sessions"] < 2):
            return 4
        pattern = str(exercise.movement_pattern or "")
        primary_five_set_patterns = {"horizontal_press", "vertical_press", "horizontal_pull", "vertical_pull", "squat", "hinge"}
        if exercise.slot_role != "primary_compound" or pattern not in primary_five_set_patterns:
            return 4
        return slot_max

    def _session_pull_count(session: GeneratedSessionDraft) -> int:
        return sum(1 for ex in session.exercises if _is_back_dominant_pattern(str(ex.movement_pattern or "")))

    for _ in range(180):
        weekly_sets = _weekly_planned_sets(sessions)
        underfilled_session = min(sessions, key=lambda item: _session_total_sets(item))
        if weekly_sets >= minimum_weekly_sets and _session_total_sets(underfilled_session) >= minimum_session_sets:
            break
        changed = False
        for exercise in _set_increment_candidates():
            distribution = _distribution_status()
            if (
                _is_back_dominant_pattern(str(exercise.movement_pattern or ""))
                and distribution["back_over_cap"]
                and distribution["has_unmet_support_floor"]
            ):
                continue
            slot_max = _exercise_set_cap(exercise)
            if int(exercise.sets) >= slot_max:
                continue
            if weekly_sets >= maximum_weekly_sets:
                break
            if weekly_sets < minimum_weekly_sets:
                exercise.sets += 1
                changed = True
                break
            if _session_total_sets(underfilled_session) < minimum_session_sets and exercise in underfilled_session.exercises:
                exercise.sets += 1
                changed = True
                break
        if not changed:
            break

    # Deterministic floor catch-up: if set-cap logic leaves normal-band weeks slightly under
    # target, finish with bounded primary-compound increments before giving up.
    for _ in range(120):
        weekly_sets = _weekly_planned_sets(sessions)
        if weekly_sets >= minimum_weekly_sets:
            break
        changed = False
        for exercise in _set_increment_candidates():
            slot_role = str(exercise.slot_role or "")
            cap = 5 if slot_role == "primary_compound" else 4
            if int(exercise.sets) >= cap:
                continue
            distribution = _distribution_status()
            if (
                _is_back_dominant_pattern(str(exercise.movement_pattern or ""))
                and distribution["back_over_cap"]
                and distribution["has_unmet_support_floor"]
            ):
                continue
            exercise.sets += 1
            changed = True
            break
        if not changed:
            break

    # Rebalance surplus pull/back slots when back is above cap and support floors are unmet.
    for _ in range(18):
        distribution = _distribution_status()
        if not (distribution["back_over_cap"] and distribution["has_unmet_support_floor"]):
            break
        replacement_ids: list[str] = []
        unmet = distribution["unmet"]
        if unmet["core"]:
            replacement_ids = _candidate_ids_for_patterns(["core"])
        elif unmet["triceps"]:
            replacement_ids = _candidate_ids_for_patterns(["triceps_extension"])
        elif unmet["delts"]:
            replacement_ids = _candidate_ids_for_patterns(["lateral_raise", "vertical_press"])
        elif unmet["hamstrings"]:
            replacement_ids = _candidate_ids_for_patterns(["leg_curl", "hinge"])
        elif unmet["biceps"]:
            replacement_ids = _candidate_ids_for_patterns(["curl"])
        replacement_ids = [exercise_id for exercise_id in replacement_ids if not _is_back_dominant_candidate(exercise_id)]
        if not replacement_ids:
            break
        donor_session: GeneratedSessionDraft | None = None
        donor_index: int | None = None
        for session in sorted(sessions, key=lambda item: (_session_pull_count(item), _session_total_sets(item)), reverse=True):
            pull_count = _session_pull_count(session)
            if pull_count <= 1:
                continue
            for idx, existing in enumerate(session.exercises):
                if not _is_back_dominant_pattern(str(existing.movement_pattern or "")):
                    continue
                if existing.slot_role not in {"weak_point", "accessory", "secondary_compound"}:
                    continue
                donor_session = session
                donor_index = idx
                break
            if donor_session is not None:
                break
        if donor_session is None or donor_index is None:
            break
        session_exercise_ids = {exercise.id for exercise in donor_session.exercises}
        feasible_candidate_ids = _feasible_candidate_ids(
            candidate_ids=replacement_ids,
            assigned_counts=assigned_counts,
            max_assignments_per_week=max_assignments_per_week,
            allow_reuse_after_unique_candidates_exhausted=allow_reuse_after_exhaustion,
            session_exercise_ids=session_exercise_ids,
        )
        if not feasible_candidate_ids:
            feasible_candidate_ids = replacement_ids
        selected_id = feasible_candidate_ids[0]
        selected_record = record_by_id.get(selected_id)
        if selected_record is None:
            break
        replacement = _build_exercise_draft(
            assessment=assessment,
            blueprint_input=blueprint_input,
            doctrine_bundle=doctrine_bundle,
            record=selected_record,
            slot_role=donor_session.exercises[donor_index].slot_role,
            selection_mode="optional_fill",
            day_role=donor_session.day_role,
            selection_trace=None,
            doctrine_rule_ids=[
                fill_target_rule_id,
                scoring_rule_id,
                optional_fill_rule_id,
                slot_role_rule_id,
                reuse_rule_id,
            ],
            policy_ids=density_policy_ids,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        replaced = donor_session.exercises[donor_index]
        donor_session.exercises[donor_index] = replacement
        assigned_counts[replaced.id] = max(0, assigned_counts.get(replaced.id, 0) - 1)
        assigned_counts[selected_id] = assigned_counts.get(selected_id, 0) + 1

    # Final pass: hold core at >=2 sessions when viable after all replacements/inflation.
    if core_viable:
        for _ in range(6):
            weekly_roles = _weekly_role_exposure(sessions)
            if weekly_roles["core_sessions"] >= 2:
                break
            core_candidates = _candidate_ids_for_patterns(["core"])
            if not core_candidates:
                break
            missing_core_sessions = [session for session in sessions if not _session_has_pattern(session, {"core"})]
            if not missing_core_sessions:
                break
            target_session = min(
                missing_core_sessions,
                key=lambda item: (_session_total_sets(item), len(item.exercises), item.session_id),
            )
            if _insert_candidate(session=target_session, candidate_ids=core_candidates):
                continue
            # deterministic replacement fallback without disturbing lower anchors
            session_exercise_ids = {exercise.id for exercise in target_session.exercises}
            forced_id = next((exercise_id for exercise_id in core_candidates if exercise_id not in session_exercise_ids), None)
            if forced_id is None:
                break
            forced_record = record_by_id.get(forced_id)
            if forced_record is None:
                break
            replace_index = None
            for idx, existing in enumerate(target_session.exercises):
                existing_pattern = str(existing.movement_pattern or "")
                if _is_lower_posterior_pattern(existing_pattern):
                    continue
                if existing.slot_role in {"weak_point", "accessory", "secondary_compound"}:
                    replace_index = idx
                    break
            if replace_index is None:
                break
            slot_role = _next_slot_role(
                session=target_session,
                slot_roles_by_position=["primary_compound", "secondary_compound", "accessory", "weak_point"],
                fallback_slot_role="accessory",
            )
            replacement = _build_exercise_draft(
                assessment=assessment,
                blueprint_input=blueprint_input,
                doctrine_bundle=doctrine_bundle,
                record=forced_record,
                slot_role=slot_role,
                selection_mode="optional_fill",
                day_role=target_session.day_role,
                selection_trace=None,
                doctrine_rule_ids=[
                    fill_target_rule_id,
                    scoring_rule_id,
                    optional_fill_rule_id,
                    slot_role_rule_id,
                    reuse_rule_id,
                ],
                policy_ids=density_policy_ids,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            replaced = target_session.exercises[replace_index]
            target_session.exercises[replace_index] = replacement
            assigned_counts[replaced.id] = max(0, assigned_counts.get(replaced.id, 0) - 1)
            assigned_counts[forced_id] = assigned_counts.get(forced_id, 0) + 1

    # Final lower-floor restoration: replace surplus upper accessory slots when
    # quads/hamstrings floors are still unmet.
    balance_targets = _resolve_three_day_balance_targets(assessment=assessment)
    for _ in range(16):
        primary_volume = _compute_primary_major_group_volume(
            sessions=sessions,
            record_by_id=record_by_id,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        deficits = _major_floor_deficits(
            primary_volume=primary_volume,
            targets=balance_targets,
            core_viable=core_viable,
        )
        lower_deficits = [group for group in ("hamstrings", "quads") if group in deficits]
        if not lower_deficits:
            break
        target_group = "hamstrings" if "hamstrings" in lower_deficits else "quads"
        target_patterns = ["leg_curl", "hinge"] if target_group == "hamstrings" else ["knee_extension", "squat"]
        target_ids = _candidate_ids_for_patterns(target_patterns)
        if not target_ids:
            break
        donor_slot: tuple[GeneratedSessionDraft, int, GeneratedExerciseDraft] | None = None
        for session in sessions:
            if _session_lower_posterior_count(session) >= 2:
                continue
            for idx, exercise in enumerate(session.exercises):
                pattern = str(exercise.movement_pattern or "")
                if pattern in {"curl", "triceps_extension", "lateral_raise", "chest_fly"}:
                    donor_slot = (session, idx, exercise)
                    break
            if donor_slot is not None:
                break
        if donor_slot is None:
            break
        target_session, replace_index, donor = donor_slot
        session_exercise_ids = {exercise.id for exercise in target_session.exercises}
        candidate_id = next((exercise_id for exercise_id in target_ids if exercise_id not in session_exercise_ids), None)
        if candidate_id is None:
            candidate_id = next((exercise_id for exercise_id in target_ids if record_by_id.get(exercise_id) is not None), None)
        if candidate_id is None:
            break
        replacement_record = record_by_id.get(candidate_id)
        if replacement_record is None:
            break
        slot_role = str(donor.slot_role or "accessory")
        donor_previous_id = str(donor.id)
        donor.id = str(replacement_record.get("exercise_id") or donor.id)
        donor.name = str(replacement_record.get("canonical_name") or donor.name)
        donor.movement_pattern = str(replacement_record.get("movement_pattern") or donor.movement_pattern)
        donor.primary_muscles = _resolved_primary_muscles_for_generated_exercise(replacement_record)
        donor.equipment_tags = [str(item) for item in (replacement_record.get("equipment_tags") or []) if str(item)]
        donor.slot_role = slot_role
        assigned_counts[donor_previous_id] = max(0, assigned_counts.get(donor_previous_id, 0) - 1)
        assigned_counts[candidate_id] = assigned_counts.get(candidate_id, 0) + 1

    # Final core-set floor durability: when core is viable in normal three-day density mode,
    # keep at least a minimal direct weekly core dose even after replacements.
    if core_viable:
        weekly_roles = _weekly_role_exposure(sessions)
        minimum_core_sets = 3
        if int(weekly_roles.get("core_sets", 0)) < minimum_core_sets:
            for session in sessions:
                for exercise in session.exercises:
                    if str(exercise.movement_pattern or "") != "core":
                        continue
                    while int(exercise.sets) < 4 and int(weekly_roles.get("core_sets", 0)) < minimum_core_sets:
                        exercise.sets += 1
                        weekly_roles["core_sets"] = int(weekly_roles.get("core_sets", 0)) + 1
                    if int(weekly_roles.get("core_sets", 0)) >= minimum_core_sets:
                        break
                if int(weekly_roles.get("core_sets", 0)) >= minimum_core_sets:
                    break

    # Final per-session high-fatigue cap: prevent dense sessions from relying on >2 high-fatigue slots.
    for session in sessions:
        for _ in range(6):
            if _session_high_fatigue_count(session=session, record_by_id=record_by_id) <= 2:
                break
            replace_index = None
            for idx, existing in enumerate(session.exercises):
                fatigue = str((record_by_id.get(existing.id) or {}).get("fatigue_cost") or "")
                if fatigue != "high":
                    continue
                if str(existing.slot_role or "") in {"weak_point", "accessory", "secondary_compound"}:
                    replace_index = idx
                    break
            if replace_index is None:
                for idx, existing in enumerate(session.exercises):
                    fatigue = str((record_by_id.get(existing.id) or {}).get("fatigue_cost") or "")
                    if fatigue == "high":
                        replace_index = idx
                        break
            if replace_index is None:
                break

            replacement_ids = [
                exercise_id
                for exercise_id in _global_fill_candidate_ids(blueprint_input)
                if str((record_by_id.get(exercise_id) or {}).get("fatigue_cost") or "") != "high"
                and exercise_id not in {item.id for item in session.exercises}
            ]
            if not replacement_ids:
                break
            replacement_record = record_by_id.get(replacement_ids[0])
            if replacement_record is None:
                break
            existing = session.exercises[replace_index]
            replacement = _build_exercise_draft(
                assessment=assessment,
                blueprint_input=blueprint_input,
                doctrine_bundle=doctrine_bundle,
                record=replacement_record,
                slot_role=str(existing.slot_role or "accessory"),
                selection_mode="optional_fill",
                day_role=session.day_role,
                selection_trace=None,
                doctrine_rule_ids=[
                    fill_target_rule_id,
                    scoring_rule_id,
                    optional_fill_rule_id,
                    slot_role_rule_id,
                    reuse_rule_id,
                ],
                policy_ids=density_policy_ids,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            assigned_counts[existing.id] = max(0, assigned_counts.get(existing.id, 0) - 1)
            assigned_counts[replacement.id] = assigned_counts.get(replacement.id, 0) + 1
            session.exercises[replace_index] = replacement

    # Final session-set spread rebalance for 3-day quality consistency.
    for _ in range(24):
        totals = [_session_total_sets(session) for session in sessions]
        if not totals or (max(totals) - min(totals)) <= 4:
            break
        high_session = max(sessions, key=_session_total_sets)
        low_session = min(sessions, key=_session_total_sets)
        donor = next(
            (
                exercise
                for exercise in sorted(
                    high_session.exercises,
                    key=lambda item: (SLOT_ROLE_ORDER.get(item.slot_role, 9), item.id),
                    reverse=True,
                )
                if int(exercise.sets) > 1
            ),
            None,
        )
        receiver = next(
            (
                exercise
                for exercise in sorted(
                    low_session.exercises,
                    key=lambda item: (SLOT_ROLE_ORDER.get(item.slot_role, 9), item.id),
                )
                if int(exercise.sets) < _exercise_set_cap(exercise)
            ),
            None,
        )
        if donor is None or receiver is None:
            break
        donor.sets -= 1
        receiver.sets += 1

    # Final pull-cap repair: keep pull-dominant slots <=2 per session in normal 3-day mode.
    for session in sessions:
        for _ in range(8):
            pull_count = sum(
                1
                for exercise in session.exercises
                if _is_back_dominant_pattern(str(exercise.movement_pattern or ""))
            )
            if pull_count <= 2:
                break
            replace_index = None
            for idx, existing in enumerate(session.exercises):
                if not _is_back_dominant_pattern(str(existing.movement_pattern or "")):
                    continue
                if str(existing.slot_role or "") in {"weak_point", "accessory", "secondary_compound"}:
                    replace_index = idx
                    break
            if replace_index is None:
                break
            replacement_ids = _unique_preserve_order(
                _candidate_ids_for_patterns(["core", "triceps_extension", "lateral_raise", "leg_curl", "hinge", "horizontal_press"])
            )
            replacement_ids = [
                exercise_id
                for exercise_id in replacement_ids
                if not _is_back_dominant_candidate(exercise_id)
                and exercise_id not in {item.id for item in session.exercises}
            ]
            if not replacement_ids:
                break
            replacement_record = record_by_id.get(replacement_ids[0])
            if replacement_record is None:
                break
            existing = session.exercises[replace_index]
            replacement = _build_exercise_draft(
                assessment=assessment,
                blueprint_input=blueprint_input,
                doctrine_bundle=doctrine_bundle,
                record=replacement_record,
                slot_role=str(existing.slot_role or "accessory"),
                selection_mode="optional_fill",
                day_role=session.day_role,
                selection_trace=None,
                doctrine_rule_ids=[
                    fill_target_rule_id,
                    scoring_rule_id,
                    optional_fill_rule_id,
                    slot_role_rule_id,
                    reuse_rule_id,
                ],
                policy_ids=density_policy_ids,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            assigned_counts[existing.id] = max(0, assigned_counts.get(existing.id, 0) - 1)
            assigned_counts[replacement.id] = assigned_counts.get(replacement.id, 0) + 1
            session.exercises[replace_index] = replacement


def build_generated_full_body_template_draft(
    *,
    assessment: UserAssessment,
    blueprint_input: GeneratedFullBodyBlueprintInput,
    doctrine_bundle: DoctrineBundle,
    policy_bundle: PolicyBundle,
    exercise_library: CanonicalExerciseLibraryBundle,
    metadata_v2_by_exercise_id: dict[str, ExerciseMetadataV2] | None = None,
) -> GeneratedFullBodyTemplateDraft:
    if blueprint_input.target_split != "full_body":
        raise ValueError("constructor only supports full_body blueprint inputs")

    anti_copy_constraint_id = _require_hard_constraint(policy_bundle, "do_not_replay_single_authored_layout")
    minimum_viable_policy_id = policy_bundle.minimum_viable_program_policy.policy_id

    rule_ids = {
        "topology": "full_body_session_topology_by_session_count_v1",
        "day_roles": "full_body_day_role_sequence_by_session_count_v1",
        "pattern_distribution": "full_body_movement_pattern_distribution_v1",
        "fill_target": "full_body_session_fill_target_by_volume_tier_v1",
        "scoring": "full_body_candidate_scoring_v1",
        "optional_fill": "full_body_optional_fill_pattern_priority_by_complexity_ceiling_v1",
        "slot_roles": "full_body_slot_role_sequence_v1",
        "reuse": "full_body_exercise_reuse_limits_v1",
        "weak_point": "full_body_weak_point_slot_insertion_v1",
    }
    topology_rule = _require_rule_payload(doctrine_bundle, rule_ids["topology"])
    day_role_rule = _require_rule_payload(doctrine_bundle, rule_ids["day_roles"])
    pattern_distribution_rule = _require_rule_payload(doctrine_bundle, rule_ids["pattern_distribution"])
    fill_target_rule = _require_rule_payload(doctrine_bundle, rule_ids["fill_target"])
    scoring_rule = _require_rule_payload(doctrine_bundle, rule_ids["scoring"])
    optional_fill_rule = _require_rule_payload(doctrine_bundle, rule_ids["optional_fill"])
    slot_role_rule = _require_rule_payload(doctrine_bundle, rule_ids["slot_roles"])
    reuse_rule = _require_rule_payload(doctrine_bundle, rule_ids["reuse"])
    weak_point_rule = _require_rule_payload(doctrine_bundle, rule_ids["weak_point"])

    session_indices = _topology_for_session_count(topology_rule, blueprint_input.session_count)
    day_roles = _day_roles_for_session_count(day_role_rule, blueprint_input.session_count)
    if len(day_roles) != len(session_indices):
        raise ValueError("day-role sequence length must match session topology length")
    pattern_distribution = _pattern_distribution_for_session_count(pattern_distribution_rule, blueprint_input.session_count)
    slot_roles_by_position = [str(item) for item in (slot_role_rule.payload.get("slot_roles_by_position") or [])]
    slot_role_by_movement_pattern = {
        str(key): str(value)
        for key, value in (slot_role_rule.payload.get("slot_role_by_movement_pattern") or {}).items()
    }
    max_assignments_per_week = int(reuse_rule.payload["max_assignments_per_exercise_per_week"])
    allow_reuse_after_exhaustion = bool(reuse_rule.payload["allow_reuse_after_unique_candidates_exhausted"])
    doctrine_session_target = int(
        fill_target_rule.payload["volume_tier_to_target_exercises_per_session"][blueprint_input.volume_tier]
    )
    minimum_exercises_per_session = int(policy_bundle.minimum_viable_program_policy.minimum_exercises_per_session)
    apply_three_day_band = blueprint_input.session_count == 3 and not bool(blueprint_input.pattern_insufficiencies)
    apply_normal_three_day_density_seriousness = (
        blueprint_input.session_count == 3
        and int(assessment.session_time_budget_minutes or 75) >= 60
        and str(assessment.recovery_profile or "") == "normal"
        and not bool(assessment.comeback_flag)
        and str(assessment.schedule_profile or "") != "low_time"
    )
    session_exercise_cap_limit: int | None = (
        blueprint_input.session_exercise_cap
        if metadata_v2_by_exercise_id is not None
        else None
    )
    # Blueprint cap tiers represent minimum viable generation guardrails.
    # For normal 3-day full-body runtime generation, keep density seriousness in constructor:
    # do not let the minimum-viable cap collapse sessions to 5 slots.
    if apply_normal_three_day_density_seriousness:
        session_exercise_cap_limit = None
    target_exercises_per_session, effective_session_exercise_cap = _density_targets_for_budget(
        assessment=assessment,
        session_count=blueprint_input.session_count,
        volume_tier=blueprint_input.volume_tier,
        doctrine_target=doctrine_session_target,
        minimum_exercises_per_session=minimum_exercises_per_session,
        apply_three_day_band=apply_three_day_band,
        session_exercise_cap_limit=session_exercise_cap_limit,
    )
    if apply_normal_three_day_density_seriousness:
        band = _resolve_three_day_volume_band(assessment=assessment)
        target_exercises_per_session = max(target_exercises_per_session, band.minimum_exercises_per_session)
        effective_session_exercise_cap = max(
            effective_session_exercise_cap,
            max(target_exercises_per_session, band.exercise_cap_per_session),
        )
    optional_fill_score_floor = scoring_rule.payload["minimum_total_score_floor"].get("optional_fill")
    if optional_fill_score_floor is not None:
        optional_fill_score_floor = int(optional_fill_score_floor)
    three_day_band = _resolve_three_day_volume_band(assessment=assessment) if apply_three_day_band else None
    optional_fill_patterns = [
        str(item)
        for item in optional_fill_rule.payload["optional_patterns_by_complexity_ceiling"].get(
            blueprint_input.complexity_ceiling, []
        )
    ]
    core_candidate_ids = list(blueprint_input.candidate_exercise_ids_by_pattern.get("core", []))
    if core_candidate_ids and "core" not in optional_fill_patterns:
        optional_fill_patterns.append("core")
    core_viable = bool(core_candidate_ids)
    weak_point_slot_limit = int(
        weak_point_rule.payload.get("volume_tier_to_max_weekly_weak_point_slots", {}).get(
            blueprint_input.volume_tier,
            weak_point_rule.payload["max_weekly_weak_point_slots"],
        )
    )
    minimum_remaining_capacity = int(weak_point_rule.payload.get("minimum_remaining_capacity_inclusive", 1))

    record_by_id = {
        record.exercise_id: record.model_dump(mode="json")
        for record in exercise_library.records
    }

    sessions: list[GeneratedSessionDraft] = []
    session_lookup: dict[int, GeneratedSessionDraft] = {}
    anti_copy_policy_ids = [anti_copy_constraint_id]
    density_policy_ids = [anti_copy_constraint_id, minimum_viable_policy_id]

    for position, session_index in enumerate(session_indices, start=1):
        movement_pattern_targets = list(pattern_distribution.get(session_index, []))
        session_field_trace = {
            "session_id": _trace(
                doctrine_rule_ids=[topology_rule.rule_id],
                policy_ids=anti_copy_policy_ids,
                system_default_ids=["generated_session_id_v1"],
            ),
            "title": _trace(
                doctrine_rule_ids=[topology_rule.rule_id],
                policy_ids=anti_copy_policy_ids,
                system_default_ids=["generated_session_title_v1"],
            ),
            "day_role": _trace(
                doctrine_rule_ids=[day_role_rule.rule_id],
                policy_ids=anti_copy_policy_ids,
            ),
            "movement_pattern_targets": _trace(
                doctrine_rule_ids=[pattern_distribution_rule.rule_id],
                policy_ids=anti_copy_policy_ids,
            ),
            "exercises": _trace(
                doctrine_rule_ids=[
                    pattern_distribution_rule.rule_id,
                    fill_target_rule.rule_id,
                    scoring_rule.rule_id,
                    optional_fill_rule.rule_id,
                    slot_role_rule.rule_id,
                    reuse_rule.rule_id,
                    weak_point_rule.rule_id,
                ],
                policy_ids=density_policy_ids,
            ),
            "optional_fill_trace": _trace(
                doctrine_rule_ids=[
                    fill_target_rule.rule_id,
                    scoring_rule.rule_id,
                    optional_fill_rule.rule_id,
                    reuse_rule.rule_id,
                    weak_point_rule.rule_id,
                ],
                policy_ids=density_policy_ids,
            ),
            "field_trace": _trace(system_default_ids=["constructor_field_trace_v1"]),
        }
        session = GeneratedSessionDraft(
            session_id=_session_identifier(position),
            title=_session_title(position),
            day_role=day_roles[position - 1],
            movement_pattern_targets=movement_pattern_targets,
            exercises=[],
            optional_fill_trace=None,
            field_trace=session_field_trace,
        )
        sessions.append(session)
        session_lookup[session_index] = session

    insufficiencies: list[ConstructibilityIssue] = []
    issue_keys: set[tuple[str, str, str | None, str | None]] = set()
    blueprint_insufficient_patterns = {issue.movement_pattern for issue in blueprint_input.pattern_insufficiencies}
    for issue in blueprint_input.pattern_insufficiencies:
        _append_issue(
            insufficiencies,
            issue_keys,
            _pattern_issue_from_blueprint(
                issue=issue,
                slot_role=slot_role_by_movement_pattern.get(issue.movement_pattern),
                doctrine_rule_ids=[
                    pattern_distribution_rule.rule_id,
                    slot_role_rule.rule_id,
                ],
                policy_ids=anti_copy_policy_ids,
            )
        )

    assigned_counts: dict[str, int] = {}
    weak_point_slots_used = 0

    for session_index in session_indices:
        session = session_lookup[session_index]
        session_exercise_ids: set[str] = set()
        for movement_pattern in session.movement_pattern_targets:
            candidate_ids = list(blueprint_input.candidate_exercise_ids_by_pattern.get(movement_pattern, []))
            slot_role = slot_role_by_movement_pattern.get(movement_pattern) or _next_slot_role(
                session=session,
                slot_roles_by_position=slot_roles_by_position,
                fallback_slot_role="secondary_compound",
            )
            if not slot_role:
                _append_issue(
                    insufficiencies,
                    issue_keys,
                    _pattern_issue(
                        issue_type="slot_role_missing",
                        reason="missing_slot_role_mapping_for_movement_pattern",
                        movement_pattern=movement_pattern,
                        slot_role=None,
                        base_trace=_trace(
                            doctrine_rule_ids=[slot_role_rule.rule_id],
                            policy_ids=anti_copy_policy_ids,
                        ),
                    )
                )
                continue

            if not candidate_ids:
                if movement_pattern not in blueprint_insufficient_patterns:
                    _append_issue(
                        insufficiencies,
                        issue_keys,
                        _pattern_issue(
                            issue_type="required_pattern_unavailable",
                            reason="no_candidates_after_filtering",
                            movement_pattern=movement_pattern,
                            slot_role=slot_role,
                            base_trace=_trace(
                                doctrine_rule_ids=[
                                    pattern_distribution_rule.rule_id,
                                    slot_role_rule.rule_id,
                                ],
                                policy_ids=anti_copy_policy_ids,
                            ),
                        ),
                    )
                continue

            feasible_candidate_ids = _feasible_candidate_ids(
                candidate_ids=candidate_ids,
                assigned_counts=assigned_counts,
                max_assignments_per_week=max_assignments_per_week,
                allow_reuse_after_unique_candidates_exhausted=allow_reuse_after_exhaustion,
                session_exercise_ids=session_exercise_ids,
            )
            if not feasible_candidate_ids:
                _append_issue(
                    insufficiencies,
                    issue_keys,
                    _pattern_issue(
                        issue_type="required_pattern_exhausted_after_reuse_limit",
                        reason="no_available_candidate_for_pattern_after_reuse_limits",
                        movement_pattern=movement_pattern,
                        slot_role=slot_role,
                        base_trace=_trace(
                            doctrine_rule_ids=[
                                pattern_distribution_rule.rule_id,
                                slot_role_rule.rule_id,
                                reuse_rule.rule_id,
                            ],
                            policy_ids=anti_copy_policy_ids,
                            exercise_ids=candidate_ids,
                        ),
                    )
                )
                continue
            historical_anchor_ids = [
                exercise_id
                for exercise_id in feasible_candidate_ids
                if exercise_id in (assessment.prior_working_weight_by_exercise_id or {})
            ]
            prioritized_required_candidate_ids = historical_anchor_ids or feasible_candidate_ids
            selection = select_scored_candidate(
                doctrine_bundle=doctrine_bundle,
                selection_mode="required_slot",
                candidate_ids=prioritized_required_candidate_ids,
                record_by_id=record_by_id,
                assessment=assessment,
                blueprint_input=blueprint_input,
                assigned_counts=assigned_counts,
                weekly_selected_exercise_ids=_collect_selected_exercise_ids(sessions),
                session_exercise_count=len(session.exercises),
                target_exercises_per_session=target_exercises_per_session,
                target_movement_pattern=movement_pattern,
                target_weak_point_muscles=[item.muscle_group for item in assessment.weak_point_priorities],
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            if selection is None:
                continue

            record = record_by_id.get(selection.selected_id)
            if record is None:
                raise ValueError(f"exercise library missing selected exercise id: {selection.selected_id}")

            exercise = _build_exercise_draft(
                assessment=assessment,
                blueprint_input=blueprint_input,
                doctrine_bundle=doctrine_bundle,
                record=record,
                slot_role=slot_role,
                selection_mode="required_slot",
                day_role=session.day_role,
                selection_trace=selection.selection_trace,
                doctrine_rule_ids=[
                    pattern_distribution_rule.rule_id,
                    scoring_rule.rule_id,
                    slot_role_rule.rule_id,
                    reuse_rule.rule_id,
                ],
                policy_ids=anti_copy_policy_ids,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            session.exercises.append(exercise)
            session_exercise_ids.add(selection.selected_id)
            assigned_counts[selection.selected_id] = assigned_counts.get(selection.selected_id, 0) + 1

    weak_point_slot_role = str(weak_point_rule.payload.get("slot_role") or "weak_point")
    if weak_point_slots_used < weak_point_slot_limit:
        for preferred_session_index in _preferred_weak_point_sessions(weak_point_rule, blueprint_input.session_count):
            if weak_point_slots_used >= weak_point_slot_limit:
                break
            session = session_lookup.get(preferred_session_index)
            if session is None:
                continue
            remaining_capacity = target_exercises_per_session - len(session.exercises)
            if remaining_capacity < minimum_remaining_capacity or len(session.exercises) >= effective_session_exercise_cap:
                continue
            session_exercise_ids = {exercise.id for exercise in session.exercises}
            inserted = False
            for weak_point in assessment.weak_point_priorities:
                candidate_ids = list(
                    blueprint_input.weak_point_candidate_exercise_ids_by_muscle.get(weak_point.muscle_group, [])
                )
                feasible_candidate_ids = _feasible_candidate_ids(
                    candidate_ids=candidate_ids,
                    assigned_counts=assigned_counts,
                    max_assignments_per_week=max_assignments_per_week,
                    allow_reuse_after_unique_candidates_exhausted=allow_reuse_after_exhaustion,
                    session_exercise_ids=session_exercise_ids,
                )
                if not feasible_candidate_ids:
                    continue
                selection = select_scored_candidate(
                    doctrine_bundle=doctrine_bundle,
                    selection_mode="weak_point_slot",
                    candidate_ids=feasible_candidate_ids,
                    record_by_id=record_by_id,
                    assessment=assessment,
                    blueprint_input=blueprint_input,
                    assigned_counts=assigned_counts,
                    weekly_selected_exercise_ids=_collect_selected_exercise_ids(sessions),
                    session_exercise_count=len(session.exercises),
                    target_exercises_per_session=target_exercises_per_session,
                    target_weak_point_muscles=[weak_point.muscle_group],
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
                if selection is None:
                    continue
                record = record_by_id.get(selection.selected_id)
                if record is None:
                    continue
                exercise = _build_exercise_draft(
                    assessment=assessment,
                    blueprint_input=blueprint_input,
                    doctrine_bundle=doctrine_bundle,
                    record=record,
                    slot_role=weak_point_slot_role,
                    selection_mode="weak_point_slot",
                    day_role=session.day_role,
                    selection_trace=selection.selection_trace,
                    doctrine_rule_ids=[
                        fill_target_rule.rule_id,
                        scoring_rule.rule_id,
                        weak_point_rule.rule_id,
                        slot_role_rule.rule_id,
                        reuse_rule.rule_id,
                    ],
                    policy_ids=density_policy_ids,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
                session.exercises.append(exercise)
                session_exercise_ids.add(selection.selected_id)
                assigned_counts[selection.selected_id] = assigned_counts.get(selection.selected_id, 0) + 1
                weak_point_slots_used += 1
                inserted = True
                break
            if inserted:
                continue

    # In normal 3-day generated mode, ensure explicit triceps exposure is not silently
    # dropped before optional-fill expansion. This preserves full-body session seriousness.
    three_day_band_for_skeleton = _resolve_three_day_volume_band(assessment=assessment) if blueprint_input.session_count == 3 else None
    enforce_normal_three_day_floor = bool(blueprint_input.session_count == 3)
    if enforce_normal_three_day_floor:
        has_triceps_primary = any(
            "triceps" in {str(m).lower() for m in exercise.primary_muscles}
            for session in sessions
            for exercise in session.exercises
        )
        if not has_triceps_primary:
            strict_triceps_ids = list(blueprint_input.candidate_exercise_ids_by_pattern.get("triceps_extension", []))
            triceps_candidate_ids = _unique_preserve_order(
                strict_triceps_ids
                if strict_triceps_ids
                else list(blueprint_input.candidate_exercise_ids_by_pattern.get("vertical_press", []))
                + list(blueprint_input.candidate_exercise_ids_by_pattern.get("horizontal_press", []))
            )
            if triceps_candidate_ids:
                target_session = min(
                    sessions,
                    key=lambda item: (
                        len(item.exercises),
                        _session_total_sets(item),
                        item.session_id,
                    ),
                )
                if len(target_session.exercises) < effective_session_exercise_cap:
                    session_exercise_ids = {exercise.id for exercise in target_session.exercises}
                    feasible_candidate_ids = _feasible_candidate_ids(
                        candidate_ids=triceps_candidate_ids,
                        assigned_counts=assigned_counts,
                        max_assignments_per_week=max_assignments_per_week,
                        allow_reuse_after_unique_candidates_exhausted=allow_reuse_after_exhaustion,
                        session_exercise_ids=session_exercise_ids,
                    )
                    if feasible_candidate_ids:
                        selection = select_scored_candidate(
                            doctrine_bundle=doctrine_bundle,
                            selection_mode="optional_fill",
                            candidate_ids=feasible_candidate_ids,
                            record_by_id=record_by_id,
                            assessment=assessment,
                            blueprint_input=blueprint_input,
                            assigned_counts=assigned_counts,
                            weekly_selected_exercise_ids=_collect_selected_exercise_ids(sessions),
                            session_exercise_count=len(target_session.exercises),
                            target_exercises_per_session=target_exercises_per_session,
                            target_weak_point_muscles=[item.muscle_group for item in assessment.weak_point_priorities],
                            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                        )
                        if selection is not None:
                            record = record_by_id.get(selection.selected_id)
                            if record is not None:
                                exercise = _build_exercise_draft(
                                    assessment=assessment,
                                    blueprint_input=blueprint_input,
                                    doctrine_bundle=doctrine_bundle,
                                    record=record,
                                    slot_role="accessory",
                                    selection_mode="optional_fill",
                                    day_role=target_session.day_role,
                                    selection_trace=selection.selection_trace,
                                    doctrine_rule_ids=[
                                        fill_target_rule.rule_id,
                                        scoring_rule.rule_id,
                                        optional_fill_rule.rule_id,
                                        slot_role_rule.rule_id,
                                        reuse_rule.rule_id,
                                    ],
                                    policy_ids=density_policy_ids,
                                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                                )
                                target_session.exercises.append(exercise)
                                assigned_counts[selection.selected_id] = assigned_counts.get(selection.selected_id, 0) + 1

    fill_progress = True
    while fill_progress:
        fill_progress = False
        session_order = sorted(
            sessions,
            key=lambda item: (
                _session_total_sets(item),
                _session_high_fatigue_count(session=item, record_by_id=record_by_id),
                item.session_id,
            ),
        )
        for session in session_order:
            if len(session.exercises) >= target_exercises_per_session:
                if session.optional_fill_trace is None:
                    session.optional_fill_trace = _optional_fill_trace(
                        score_floor=optional_fill_score_floor,
                        stop_reason="target_reached",
                    )
                elif session.optional_fill_trace.stop_reason != "target_reached":
                    session.optional_fill_trace = _optional_fill_trace(
                        score_floor=session.optional_fill_trace.score_floor,
                        best_candidate_id=session.optional_fill_trace.best_candidate_id,
                        best_total_score=session.optional_fill_trace.best_total_score,
                        stop_reason="target_reached",
                    )
                continue
            if len(session.exercises) >= effective_session_exercise_cap:
                if session.optional_fill_trace is None:
                    session.optional_fill_trace = _optional_fill_trace(
                        score_floor=optional_fill_score_floor,
                        stop_reason="target_reached",
                    )
                elif session.optional_fill_trace.stop_reason != "target_reached":
                    session.optional_fill_trace = _optional_fill_trace(
                        score_floor=session.optional_fill_trace.score_floor,
                        best_candidate_id=session.optional_fill_trace.best_candidate_id,
                        best_total_score=session.optional_fill_trace.best_total_score,
                        stop_reason="target_reached",
                    )
                continue
            session_exercise_ids = {exercise.id for exercise in session.exercises}
            missing_session_skeleton = (
                _missing_session_skeleton_categories(
                    session=session,
                    candidate_exercise_ids_by_pattern=blueprint_input.candidate_exercise_ids_by_pattern,
                )
                if enforce_normal_three_day_floor
                else []
            )
            next_slot_role = _next_slot_role(
                session=session,
                slot_roles_by_position=slot_roles_by_position,
                fallback_slot_role="accessory",
            )
            required_categories = _required_balance_categories(
                candidate_exercise_ids_by_pattern=blueprint_input.candidate_exercise_ids_by_pattern,
            )
            missing_categories = sorted(required_categories - _covered_balance_categories(sessions))
            three_day_deficits: dict[str, int] = {}
            if apply_three_day_band:
                balance_targets = _resolve_three_day_balance_targets(assessment=assessment)
                primary_volume = _compute_primary_major_group_volume(
                    sessions=sessions,
                    record_by_id=record_by_id,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
                three_day_deficits = _major_floor_deficits(
                    primary_volume=primary_volume,
                    targets=balance_targets,
                    core_viable=core_viable,
                )
            missing_patterns = {
                pattern
                for category in missing_categories
                for pattern in WEEKLY_BALANCE_CATEGORY_TO_PATTERNS.get(category, ())
            }
            prioritized_optional_patterns = _balance_priority_patterns_for_missing_categories(
                missing_categories=missing_categories,
                optional_fill_patterns=optional_fill_patterns,
            )
            optional_fill_candidate_ids = _unique_preserve_order(
                [
                    exercise_id
                    for movement_pattern in prioritized_optional_patterns
                    for exercise_id in blueprint_input.candidate_exercise_ids_by_pattern.get(movement_pattern, [])
                ]
            )
            if apply_three_day_band and three_day_deficits:
                deficit_pattern_map = {
                    "chest": ("chest_fly", "horizontal_press"),
                    "back": ("horizontal_pull", "vertical_pull"),
                    "quads": ("knee_extension", "squat"),
                    "hamstrings": ("leg_curl", "hinge"),
                    "core": ("core",),
                }
                deficit_candidate_ids = _unique_preserve_order(
                    [
                        exercise_id
                        for group in ("core", "quads", "hamstrings", "chest", "back")
                        if group in three_day_deficits
                        for pattern in deficit_pattern_map[group]
                        for exercise_id in blueprint_input.candidate_exercise_ids_by_pattern.get(pattern, [])
                    ]
                )
                optional_fill_candidate_ids = _unique_preserve_order(deficit_candidate_ids + optional_fill_candidate_ids)
            if len(optional_fill_candidate_ids) < target_exercises_per_session:
                optional_fill_candidate_ids = _unique_preserve_order(
                    optional_fill_candidate_ids + _global_fill_candidate_ids(blueprint_input)
                )
            feasible_candidate_ids = _feasible_candidate_ids(
                candidate_ids=optional_fill_candidate_ids,
                assigned_counts=assigned_counts,
                max_assignments_per_week=max_assignments_per_week,
                allow_reuse_after_unique_candidates_exhausted=allow_reuse_after_exhaustion,
                session_exercise_ids=session_exercise_ids,
            )
            if feasible_candidate_ids and missing_session_skeleton:
                prioritized_patterns = _prioritized_session_skeleton_patterns(
                    missing_categories=missing_session_skeleton,
                )
                prioritized_ids = _unique_preserve_order(
                    [
                        exercise_id
                        for pattern in prioritized_patterns
                        for exercise_id in blueprint_input.candidate_exercise_ids_by_pattern.get(pattern, [])
                        if exercise_id in feasible_candidate_ids
                    ]
                )
                if prioritized_ids:
                    feasible_candidate_ids = prioritized_ids
            if feasible_candidate_ids and enforce_normal_three_day_floor and {"press", "pull"} & set(missing_session_skeleton):
                non_knee_ids = [
                    exercise_id
                    for exercise_id in feasible_candidate_ids
                    if str((record_by_id.get(exercise_id) or {}).get("movement_pattern") or "") not in {"squat", "knee_extension"}
                ]
                if non_knee_ids:
                    feasible_candidate_ids = non_knee_ids
            if feasible_candidate_ids and enforce_normal_three_day_floor:
                weekly_roles = _weekly_role_exposure(sessions)
                session_roles = _session_role_flags(session)
                role_priority: list[str] = []
                if not session_roles["shoulder_rear_delt"]:
                    role_priority.append("shoulder_rear_delt")
                weak_point_groups = _weak_point_major_groups(assessment)
                if "arms" in weak_point_groups:
                    if weekly_roles["biceps_sets"] <= weekly_roles["triceps_sets"]:
                        role_priority.extend(["biceps", "triceps"])
                    else:
                        role_priority.extend(["triceps", "biceps"])
                else:
                    if weekly_roles["biceps_sets"] == 0:
                        role_priority.append("biceps")
                    if weekly_roles["triceps_sets"] == 0:
                        role_priority.append("triceps")
                if core_viable and weekly_roles["core_sessions"] < 2:
                    role_priority.append("core")
                if apply_three_day_band:
                    balance_targets = _resolve_three_day_balance_targets(assessment=assessment)
                    role_primary_volume = _compute_primary_major_group_volume(
                        sessions=sessions,
                        record_by_id=record_by_id,
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    )
                    role_deficits = _major_floor_deficits(
                        primary_volume=role_primary_volume,
                        targets=balance_targets,
                        core_viable=core_viable,
                    )
                    if {"quads", "hamstrings"} & set(role_deficits):
                        role_priority.append("lower_accessory")
                role_priority.append("secondary_accessory")
                prioritized_ids: list[str] = []
                for role in role_priority:
                    matched = [
                        exercise_id
                        for exercise_id in feasible_candidate_ids
                        if _candidate_matches_role(record_by_id.get(exercise_id) or {}, role)
                    ]
                    if matched:
                        prioritized_ids = matched
                        break
                if prioritized_ids:
                    feasible_candidate_ids = prioritized_ids
                # Cap lower/posterior stacking before accessory role floors are satisfied.
                if _session_lower_posterior_count(session) >= 2:
                    lower_deficit_pending = False
                    if apply_three_day_band:
                        balance_targets = _resolve_three_day_balance_targets(assessment=assessment)
                        primary_volume_for_cap = _compute_primary_major_group_volume(
                            sessions=sessions,
                            record_by_id=record_by_id,
                            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                        )
                        cap_deficits = _major_floor_deficits(
                            primary_volume=primary_volume_for_cap,
                            targets=balance_targets,
                            core_viable=core_viable,
                        )
                        lower_deficit_pending = bool({"quads", "hamstrings"} & set(cap_deficits))
                    allow_extra_lower = (
                        session_roles["shoulder_rear_delt"]
                        and ((weekly_roles["biceps_sets"] > 0 and weekly_roles["triceps_sets"] > 0) or not ("arms" in weak_point_groups))
                        and ((not core_viable) or weekly_roles["core_sessions"] >= 2)
                    )
                    if not allow_extra_lower and not lower_deficit_pending:
                        non_lower_ids = [
                            exercise_id
                            for exercise_id in feasible_candidate_ids
                            if not _is_lower_posterior_pattern(
                                str((record_by_id.get(exercise_id) or {}).get("movement_pattern") or "")
                            )
                        ]
                        if non_lower_ids:
                            feasible_candidate_ids = non_lower_ids
            if feasible_candidate_ids and apply_three_day_band:
                balance_targets = _resolve_three_day_balance_targets(assessment=assessment)
                primary_volume = _compute_primary_major_group_volume(
                    sessions=sessions,
                    record_by_id=record_by_id,
                    metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                )
                deficits = _major_floor_deficits(
                    primary_volume=primary_volume,
                    targets=balance_targets,
                    core_viable=core_viable,
                )
                weak_point_groups = _weak_point_major_groups(assessment)
                if deficits:
                    ordered_groups = ["core", "quads", "hamstrings", "chest", "back"]
                    floor_prioritized_ids: list[str] = []
                    for group in ordered_groups:
                        if group not in deficits:
                            continue
                        group_ids = [
                            exercise_id
                            for exercise_id in feasible_candidate_ids
                            if group
                            in _exercise_primary_major_groups(
                                record_by_id.get(exercise_id) or {},
                                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                            )
                        ]
                        if group_ids:
                            floor_prioritized_ids = group_ids
                            break
                    if not floor_prioritized_ids:
                        floor_prioritized_ids = [
                            exercise_id
                            for exercise_id in feasible_candidate_ids
                            if _exercise_primary_major_groups(
                                record_by_id.get(exercise_id) or {},
                                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                            ).intersection(set(deficits))
                        ]
                    if floor_prioritized_ids:
                        feasible_candidate_ids = floor_prioritized_ids
                capped_ids = []
                for exercise_id in feasible_candidate_ids:
                    record = record_by_id.get(exercise_id) or {}
                    if _would_violate_arm_delt_caps(
                        record=record,
                        current_primary_volume=primary_volume,
                        targets=balance_targets,
                        weak_point_groups=weak_point_groups,
                        major_floors_satisfied=not deficits,
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    ):
                        continue
                    capped_ids.append(exercise_id)
                if capped_ids:
                    feasible_candidate_ids = capped_ids
            if feasible_candidate_ids and missing_patterns:
                missing_pattern_ids = [
                    exercise_id
                    for exercise_id in feasible_candidate_ids
                    if str((record_by_id.get(exercise_id) or {}).get("movement_pattern") or "") in missing_patterns
                ]
                if missing_pattern_ids:
                    feasible_candidate_ids = missing_pattern_ids
            if feasible_candidate_ids:
                session_high = _session_high_fatigue_count(session=session, record_by_id=record_by_id)
                min_high = min(
                    _session_high_fatigue_count(session=item, record_by_id=record_by_id)
                    for item in sessions
                )
                if session_high > min_high + 1:
                    lower_fatigue_ids = [
                        exercise_id
                        for exercise_id in feasible_candidate_ids
                        if str((record_by_id.get(exercise_id) or {}).get("fatigue_cost") or "") != "high"
                    ]
                    if lower_fatigue_ids:
                        feasible_candidate_ids = lower_fatigue_ids
            if not feasible_candidate_ids:
                session.optional_fill_trace = _optional_fill_trace(
                    score_floor=optional_fill_score_floor,
                    stop_reason="candidate_pool_exhausted",
                )
                continue
            selection = select_scored_candidate(
                doctrine_bundle=doctrine_bundle,
                selection_mode="optional_fill",
                candidate_ids=feasible_candidate_ids,
                record_by_id=record_by_id,
                assessment=assessment,
                blueprint_input=blueprint_input,
                assigned_counts=assigned_counts,
                weekly_selected_exercise_ids=_collect_selected_exercise_ids(sessions),
                session_exercise_count=len(session.exercises),
                target_exercises_per_session=target_exercises_per_session,
                target_weak_point_muscles=[item.muscle_group for item in assessment.weak_point_priorities],
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            if selection is None:
                session.optional_fill_trace = _optional_fill_trace(
                    score_floor=optional_fill_score_floor,
                    stop_reason="candidate_pool_exhausted",
                )
                continue
            if not selection.cleared_score_floor:
                selected_record = record_by_id.get(selection.selected_id) or {}
                selected_pattern = str(selected_record.get("movement_pattern") or "")
                if apply_three_day_band:
                    balance_targets = _resolve_three_day_balance_targets(assessment=assessment)
                    primary_volume = _compute_primary_major_group_volume(
                        sessions=sessions,
                        record_by_id=record_by_id,
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    )
                    deficits = _major_floor_deficits(
                        primary_volume=primary_volume,
                        targets=balance_targets,
                        core_viable=core_viable,
                    )
                else:
                    deficits = {}
                if selected_pattern in missing_patterns:
                    pass
                elif deficits:
                    pass
                elif (
                    three_day_band is not None
                    and len(session.exercises) < three_day_band.minimum_exercises_per_session
                ):
                    pass
                else:
                    session.optional_fill_trace = _optional_fill_trace(
                        score_floor=selection.score_floor,
                        best_candidate_id=selection.selected_id,
                        best_total_score=selection.total_score,
                        stop_reason="score_floor_not_met",
                    )
                    continue
            record = record_by_id.get(selection.selected_id)
            if record is None:
                continue
            exercise = _build_exercise_draft(
                assessment=assessment,
                blueprint_input=blueprint_input,
                doctrine_bundle=doctrine_bundle,
                record=record,
                slot_role=next_slot_role,
                selection_mode="optional_fill",
                day_role=session.day_role,
                selection_trace=selection.selection_trace,
                doctrine_rule_ids=[
                    fill_target_rule.rule_id,
                    scoring_rule.rule_id,
                    optional_fill_rule.rule_id,
                    slot_role_rule.rule_id,
                    reuse_rule.rule_id,
                ],
                policy_ids=density_policy_ids,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            session.exercises.append(exercise)
            session_exercise_ids.add(selection.selected_id)
            assigned_counts[selection.selected_id] = assigned_counts.get(selection.selected_id, 0) + 1
            fill_progress = True
            session.optional_fill_trace = _optional_fill_trace(
                score_floor=selection.score_floor,
                best_candidate_id=selection.selected_id,
                best_total_score=selection.total_score,
                stop_reason="target_reached" if len(session.exercises) >= target_exercises_per_session else "candidate_pool_exhausted",
            )

    for session in sessions:
        if session.optional_fill_trace is None:
            session.optional_fill_trace = _optional_fill_trace(
                score_floor=optional_fill_score_floor,
                stop_reason="target_reached" if len(session.exercises) >= minimum_exercises_per_session else "candidate_pool_exhausted",
            )
        elif len(session.exercises) >= target_exercises_per_session and session.optional_fill_trace.stop_reason != "target_reached":
            session.optional_fill_trace = _optional_fill_trace(
                score_floor=session.optional_fill_trace.score_floor,
                best_candidate_id=session.optional_fill_trace.best_candidate_id,
                best_total_score=session.optional_fill_trace.best_total_score,
                stop_reason="target_reached",
            )

    _apply_prescription_quality_refinement(
        sessions=sessions,
        record_by_id=record_by_id,
        assessment=assessment,
        core_viable=core_viable,
        volume_tier=blueprint_input.volume_tier,
        apply_three_day_band=apply_three_day_band,
        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
    )
    _apply_session_flow_ordering(sessions=sessions, record_by_id=record_by_id)
    if enforce_normal_three_day_floor:
        _enforce_final_session_skeleton_floor(
            sessions=sessions,
            assessment=assessment,
            blueprint_input=blueprint_input,
            doctrine_bundle=doctrine_bundle,
            record_by_id=record_by_id,
            assigned_counts=assigned_counts,
            max_assignments_per_week=max_assignments_per_week,
            allow_reuse_after_exhaustion=allow_reuse_after_exhaustion,
            target_exercises_per_session=target_exercises_per_session,
            effective_session_exercise_cap=effective_session_exercise_cap,
            fill_target_rule_id=fill_target_rule.rule_id,
            scoring_rule_id=scoring_rule.rule_id,
            optional_fill_rule_id=optional_fill_rule.rule_id,
            slot_role_rule_id=slot_role_rule.rule_id,
            reuse_rule_id=reuse_rule.rule_id,
            density_policy_ids=density_policy_ids,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        _enforce_normal_three_day_density_floor(
            sessions=sessions,
            assessment=assessment,
            blueprint_input=blueprint_input,
            doctrine_bundle=doctrine_bundle,
            record_by_id=record_by_id,
            assigned_counts=assigned_counts,
            max_assignments_per_week=max_assignments_per_week,
            allow_reuse_after_exhaustion=allow_reuse_after_exhaustion,
            target_exercises_per_session=target_exercises_per_session,
            effective_session_exercise_cap=effective_session_exercise_cap,
            fill_target_rule_id=fill_target_rule.rule_id,
            scoring_rule_id=scoring_rule.rule_id,
            optional_fill_rule_id=optional_fill_rule.rule_id,
            slot_role_rule_id=slot_role_rule.rule_id,
            reuse_rule_id=reuse_rule.rule_id,
            density_policy_ids=density_policy_ids,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
        _enforce_final_session_skeleton_floor(
            sessions=sessions,
            assessment=assessment,
            blueprint_input=blueprint_input,
            doctrine_bundle=doctrine_bundle,
            record_by_id=record_by_id,
            assigned_counts=assigned_counts,
            max_assignments_per_week=max_assignments_per_week,
            allow_reuse_after_exhaustion=allow_reuse_after_exhaustion,
            target_exercises_per_session=target_exercises_per_session,
            effective_session_exercise_cap=effective_session_exercise_cap,
            fill_target_rule_id=fill_target_rule.rule_id,
            scoring_rule_id=scoring_rule.rule_id,
            optional_fill_rule_id=optional_fill_rule.rule_id,
            slot_role_rule_id=slot_role_rule.rule_id,
            reuse_rule_id=reuse_rule.rule_id,
            density_policy_ids=density_policy_ids,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )

    if any(len(session.exercises) < minimum_exercises_per_session for session in sessions):
        _append_issue(
            insufficiencies,
            issue_keys,
            _pattern_issue(
                issue_type="minimum_viable_session_floor_unmet",
                reason="one_or_more_sessions_below_minimum_viable_floor_after_optional_fill",
                movement_pattern=None,
                slot_role=None,
                base_trace=_trace(
                    doctrine_rule_ids=[
                        fill_target_rule.rule_id,
                        scoring_rule.rule_id,
                        optional_fill_rule.rule_id,
                        reuse_rule.rule_id,
                        weak_point_rule.rule_id,
                    ],
                    policy_ids=density_policy_ids,
                    exercise_ids=_collect_selected_exercise_ids(sessions),
                ),
            ),
        )

    if enforce_normal_three_day_floor:
        for session in sessions:
            missing_skeleton = _missing_session_skeleton_categories(
                session=session,
                candidate_exercise_ids_by_pattern=blueprint_input.candidate_exercise_ids_by_pattern,
            )
            if not missing_skeleton:
                continue
            _append_issue(
                insufficiencies,
                issue_keys,
                _pattern_issue(
                    issue_type="session_skeleton_unmet_after_optional_fill",
                    reason=f"missing_session_skeleton_categories:{','.join(missing_skeleton)}",
                    movement_pattern=None,
                    slot_role=None,
                    base_trace=_trace(
                        doctrine_rule_ids=[
                            pattern_distribution_rule.rule_id,
                            fill_target_rule.rule_id,
                            optional_fill_rule.rule_id,
                            slot_role_rule.rule_id,
                        ],
                        policy_ids=density_policy_ids,
                        exercise_ids=[exercise.id for exercise in session.exercises],
                    ),
                ),
            )

    if (
        blueprint_input.session_count == 3
        and int(assessment.session_time_budget_minutes or 75) >= 60
        and str(assessment.recovery_profile or "") == "normal"
        and not bool(assessment.comeback_flag)
        and str(assessment.schedule_profile or "") != "low_time"
    ):
        # Final hard floor for normal 3-day seriousness before draft materialization.
        balance_targets = _resolve_three_day_balance_targets(assessment=assessment)
        final_min_sets = int(_resolve_three_day_volume_band(assessment=assessment).minimum_weekly_planned_sets)
        for _ in range(200):
            weekly_sets = _weekly_planned_sets(sessions)
            if weekly_sets >= final_min_sets:
                break
            primary_volume = _compute_primary_major_group_volume(
                sessions=sessions,
                record_by_id=record_by_id,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            deficits = _major_floor_deficits(
                primary_volume=primary_volume,
                targets=balance_targets,
                core_viable=core_viable,
            )
            target_session = min(
                sessions,
                key=lambda item: (
                    _session_total_sets(item),
                    item.session_id,
                ),
            )
            candidates: list[GeneratedExerciseDraft] = []
            for exercise in target_session.exercises:
                slot_role = str(exercise.slot_role or "")
                cap = 5 if slot_role == "primary_compound" else 4
                if int(exercise.sets) >= cap:
                    continue
                candidates.append(exercise)
            if not candidates:
                break

            deficit_candidates: list[GeneratedExerciseDraft] = []
            if deficits:
                for exercise in candidates:
                    exercise_groups = _exercise_primary_major_groups(
                        record_by_id.get(exercise.id) or {},
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    )
                    if exercise_groups.intersection(set(deficits)):
                        deficit_candidates.append(exercise)
            pool = deficit_candidates or candidates
            selected = sorted(
                pool,
                key=lambda item: (
                    0 if str((record_by_id.get(item.id) or {}).get("fatigue_cost") or "") != "high" else 1,
                    SLOT_ROLE_ORDER.get(item.slot_role, 9),
                    item.id,
                ),
            )[0]
            selected.sets += 1
        _rebalance_session_set_totals(
            sessions=sessions,
            time_budget_minutes=int(assessment.session_time_budget_minutes or 75),
        )
        if apply_three_day_band:
            final_targets = _resolve_three_day_balance_targets(assessment=assessment)
            donor_priority = {
                "weak_point": 0,
                "accessory": 1,
                "secondary_compound": 2,
                "primary_compound": 3,
            }
            for group in ("arms", "delts"):
                for _ in range(24):
                    primary_volume = _compute_primary_major_group_volume(
                        sessions=sessions,
                        record_by_id=record_by_id,
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    )
                    over = int(primary_volume.get(group, 0)) - int(final_targets.hard_cap_by_group[group])
                    if over <= 0:
                        break
                    donors: list[GeneratedExerciseDraft] = []
                    for session in sessions:
                        for exercise in session.exercises:
                            if int(exercise.sets) <= 1:
                                continue
                            exercise_groups = _exercise_primary_major_groups(
                                record_by_id.get(exercise.id) or {},
                                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                            )
                            if group in exercise_groups:
                                donors.append(exercise)
                    if not donors:
                        break
                    selected_donor = sorted(
                        donors,
                        key=lambda item: (
                            donor_priority.get(item.slot_role, 4),
                            item.id,
                        ),
                    )[0]
                    selected_donor.sets -= 1

    # Preserve deterministic carryover anchors from prior working-weight history
    # when an equivalent movement-pattern slot already exists in the generated week.
    prior_anchor_ids = list((assessment.prior_working_weight_by_exercise_id or {}).keys())
    if prior_anchor_ids:
        selected_ids = {exercise.id for session in sessions for exercise in session.exercises}
        for anchor_id in prior_anchor_ids:
            if anchor_id in selected_ids:
                continue
            anchor_record = record_by_id.get(anchor_id)
            if not anchor_record:
                continue
            anchor_pattern = str(anchor_record.get("movement_pattern") or "")
            if not anchor_pattern:
                continue
            replacement_target: tuple[GeneratedSessionDraft, GeneratedExerciseDraft] | None = None
            for session in sessions:
                for exercise in sorted(
                    session.exercises,
                    key=lambda item: (
                        SLOT_ROLE_ORDER.get(item.slot_role, 9),
                        item.id,
                    ),
                    reverse=True,
                ):
                    if exercise.id == anchor_id:
                        replacement_target = None
                        break
                    if str(exercise.movement_pattern or "") == anchor_pattern:
                        replacement_target = (session, exercise)
                        break
                if replacement_target is not None:
                    break
            if replacement_target is None:
                continue
            _, target_exercise = replacement_target
            target_exercise.id = anchor_id
            target_exercise.name = str(anchor_record.get("canonical_name") or anchor_id)
            target_exercise.movement_pattern = anchor_pattern
            target_exercise.primary_muscles = _resolved_primary_muscles_for_generated_exercise(
                anchor_record,
                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
            )
            anchor_weight = (assessment.prior_working_weight_by_exercise_id or {}).get(anchor_id)
            if anchor_weight is not None:
                target_exercise.start_weight = float(anchor_weight)
                target_exercise.field_trace["start_weight"] = _trace(
                    doctrine_rule_ids=["full_body_start_weight_initialization_v1"],
                    exercise_ids=[anchor_id],
                )
            selected_ids.add(anchor_id)

    if apply_three_day_band:
        cap_targets = _resolve_three_day_balance_targets(assessment=assessment)
        weak_point_groups = _weak_point_major_groups(assessment)
        donor_priority = {
            "weak_point": 0,
            "accessory": 1,
            "secondary_compound": 2,
            "primary_compound": 3,
        }
        if {"arms", "delts"} & weak_point_groups:
            for group in ("arms", "delts"):
                for _ in range(48):
                    primary_volume = _compute_primary_major_group_volume(
                        sessions=sessions,
                        record_by_id=record_by_id,
                        metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                    )
                    over = int(primary_volume.get(group, 0)) - int(cap_targets.hard_cap_by_group[group])
                    if over <= 0:
                        break
                    donors: list[GeneratedExerciseDraft] = []
                    for session in sessions:
                        for exercise in session.exercises:
                            if int(exercise.sets) <= 1:
                                continue
                            exercise_groups = _exercise_primary_major_groups(
                                record_by_id.get(exercise.id) or {},
                                metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
                            )
                            if group in exercise_groups:
                                donors.append(exercise)
                    if not donors:
                        break
                    selected_donor = sorted(
                        donors,
                        key=lambda item: (
                            donor_priority.get(item.slot_role, 4),
                            item.id,
                        ),
                    )[0]
                    selected_donor.sets -= 1

            def _visible_arm_total() -> int:
                total = 0
                for session in sessions:
                    for exercise in session.exercises:
                        record = record_by_id.get(exercise.id) or {}
                        muscles = {
                            str(item).lower()
                            for item in (list(record.get("primary_muscles") or []) + list(record.get("secondary_muscles") or []))
                            if str(item)
                        }
                        if muscles.intersection({"arms", "biceps", "triceps"}):
                            total += int(exercise.sets)
                return total

            visible_over = max(0, _visible_arm_total() - 32)
            for _ in range(visible_over):
                arm_isolation_donors: list[GeneratedExerciseDraft] = []
                for session in sessions:
                    for exercise in session.exercises:
                        if int(exercise.sets) <= 1:
                            continue
                        if str(exercise.movement_pattern or "") not in {"curl", "triceps_extension"}:
                            continue
                        arm_isolation_donors.append(exercise)
                if not arm_isolation_donors:
                    break
                selected_donor = sorted(
                    arm_isolation_donors,
                    key=lambda item: (
                        donor_priority.get(item.slot_role, 4),
                        item.id,
                    ),
                )[0]
                selected_donor.sets -= 1

        _rebalance_session_set_totals(
            sessions=sessions,
            time_budget_minutes=int(assessment.session_time_budget_minutes or 75),
        )

    selected_exercise_ids = _collect_selected_exercise_ids(sessions)
    constructibility_status = "insufficient" if insufficiencies else "ready"
    system_default_ids_used = _collect_default_ids(sessions, insufficiencies)

    draft_payload = {
        "assessment_id": assessment.assessment_id,
        "blueprint_input_id": blueprint_input.blueprint_input_id,
        "doctrine_bundle_id": doctrine_bundle.bundle_id,
        "policy_bundle_id": policy_bundle.bundle_id,
        "exercise_library_bundle_id": exercise_library.bundle_id,
        "constructibility_status": constructibility_status,
        "sessions": [session.model_dump(mode="json") for session in sessions],
        "insufficiencies": [issue.model_dump(mode="json") for issue in insufficiencies],
    }
    template_draft_id = _hash_id("generated_full_body_template", draft_payload)

    field_trace = {
        "template_draft_id": _trace(system_default_ids=["template_draft_id_hash_v1"]),
        "target_split": _trace(
            doctrine_rule_ids=[topology_rule.rule_id],
            policy_ids=anti_copy_policy_ids,
        ),
        "assessment_id": _trace(system_default_ids=["constructor_assessment_reference_passthrough_v1"]),
        "blueprint_input_id": _trace(system_default_ids=["constructor_blueprint_reference_passthrough_v1"]),
        "doctrine_bundle_id": _trace(system_default_ids=["constructor_bundle_reference_passthrough_v1"]),
        "policy_bundle_id": _trace(system_default_ids=["constructor_bundle_reference_passthrough_v1"]),
        "exercise_library_bundle_id": _trace(system_default_ids=["constructor_bundle_reference_passthrough_v1"]),
        "constructibility_status": _trace(
            doctrine_rule_ids=[
                topology_rule.rule_id,
                day_role_rule.rule_id,
                pattern_distribution_rule.rule_id,
                fill_target_rule.rule_id,
                scoring_rule.rule_id,
                optional_fill_rule.rule_id,
                slot_role_rule.rule_id,
                reuse_rule.rule_id,
                weak_point_rule.rule_id,
            ],
            policy_ids=density_policy_ids,
            exercise_ids=selected_exercise_ids,
        ),
        "sessions": _trace(
            doctrine_rule_ids=[
                topology_rule.rule_id,
                day_role_rule.rule_id,
                pattern_distribution_rule.rule_id,
                fill_target_rule.rule_id,
                scoring_rule.rule_id,
                optional_fill_rule.rule_id,
                slot_role_rule.rule_id,
                reuse_rule.rule_id,
                weak_point_rule.rule_id,
            ],
            policy_ids=density_policy_ids,
            exercise_ids=selected_exercise_ids,
        ),
        "insufficiencies": _trace(
            doctrine_rule_ids=[
                pattern_distribution_rule.rule_id,
                fill_target_rule.rule_id,
                scoring_rule.rule_id,
                optional_fill_rule.rule_id,
                slot_role_rule.rule_id,
                reuse_rule.rule_id,
                weak_point_rule.rule_id,
            ],
            policy_ids=density_policy_ids,
            exercise_ids=_unique_preserve_order(
                [exercise_id for issue in insufficiencies for exercise_id in issue.trace.exercise_ids]
            ),
        ),
        "field_trace": _trace(system_default_ids=["constructor_field_trace_v1"]),
        "system_default_ids_used": _trace(system_default_ids=["constructor_system_default_ids_used_v1"]),
    }

    return GeneratedFullBodyTemplateDraft(
        template_draft_id=template_draft_id,
        assessment_id=assessment.assessment_id,
        blueprint_input_id=blueprint_input.blueprint_input_id,
        doctrine_bundle_id=doctrine_bundle.bundle_id,
        policy_bundle_id=policy_bundle.bundle_id,
        exercise_library_bundle_id=exercise_library.bundle_id,
        constructibility_status=constructibility_status,
        sessions=sessions,
        insufficiencies=insufficiencies,
        field_trace=field_trace,
        system_default_ids_used=system_default_ids_used,
    )
