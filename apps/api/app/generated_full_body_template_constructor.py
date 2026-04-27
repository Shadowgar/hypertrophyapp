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
    GeneratedExerciseDraft,
    GeneratedFullBodyTemplateDraft,
    GeneratedSessionDraft,
    OptionalFillTrace,
)
from .knowledge_schema import CanonicalExerciseLibraryBundle, DoctrineBundle, DoctrineRuleStub, PolicyBundle


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

SLOT_ROLE_ORDER: dict[str, int] = {
    "primary_compound": 0,
    "secondary_compound": 1,
    "accessory": 2,
    "weak_point": 3,
}

MAJOR_MUSCLE_TARGETS: dict[str, tuple[str, ...]] = {
    "chest": ("chest",),
    "back": ("lats", "upper_back", "mid_back"),
    "quads": ("quads",),
    "hamstrings": ("hamstrings",),
    "delts": ("front_delts", "side_delts", "rear_delts"),
    "arms": ("biceps", "triceps"),
    "core": ("abs",),
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
    soft_cap_by_group: dict[str, int]
    hard_cap_by_group: dict[str, int]
    weak_point_bonus_by_group: dict[str, int]
    combined_arm_delt_share_cap: float
    weak_point_combined_arm_delt_share_cap: float


THREE_DAY_VOLUME_BANDS: dict[str, _ThreeDayVolumeBand] = {
    "low_time": _ThreeDayVolumeBand(
        band_id="low_time",
        target_exercises_per_session=8,
        exercise_cap_per_session=9,
        minimum_exercises_per_session=7,
        minimum_weekly_planned_sets=42,
        minimum_weekly_muscle_volume=42,
    ),
    "low_recovery": _ThreeDayVolumeBand(
        band_id="low_recovery",
        target_exercises_per_session=7,
        exercise_cap_per_session=8,
        minimum_exercises_per_session=6,
        minimum_weekly_planned_sets=42,
        minimum_weekly_muscle_volume=42,
    ),
    "normal": _ThreeDayVolumeBand(
        band_id="normal",
        target_exercises_per_session=9,
        exercise_cap_per_session=10,
        minimum_exercises_per_session=8,
        minimum_weekly_planned_sets=55,
        minimum_weekly_muscle_volume=55,
    ),
    "higher_time_normal_recovery": _ThreeDayVolumeBand(
        band_id="higher_time_normal_recovery",
        target_exercises_per_session=10,
        exercise_cap_per_session=11,
        minimum_exercises_per_session=9,
        minimum_weekly_planned_sets=62,
        minimum_weekly_muscle_volume=62,
    ),
}

THREE_DAY_BALANCE_TARGETS: dict[str, _ThreeDayBalanceTargets] = {
    "low_time": _ThreeDayBalanceTargets(
        major_floor_by_group={"chest": 7, "back": 8, "quads": 6, "hamstrings": 6, "core": 2},
        soft_cap_by_group={"arms": 22, "delts": 14},
        hard_cap_by_group={"arms": 26, "delts": 17},
        weak_point_bonus_by_group={"arms": 2, "delts": 1},
        combined_arm_delt_share_cap=0.50,
        weak_point_combined_arm_delt_share_cap=0.54,
    ),
    "low_recovery": _ThreeDayBalanceTargets(
        major_floor_by_group={"chest": 7, "back": 8, "quads": 6, "hamstrings": 6, "core": 2},
        soft_cap_by_group={"arms": 21, "delts": 14},
        hard_cap_by_group={"arms": 25, "delts": 17},
        weak_point_bonus_by_group={"arms": 2, "delts": 1},
        combined_arm_delt_share_cap=0.50,
        weak_point_combined_arm_delt_share_cap=0.54,
    ),
    "normal": _ThreeDayBalanceTargets(
        major_floor_by_group={"chest": 10, "back": 12, "quads": 8, "hamstrings": 8, "core": 3},
        soft_cap_by_group={"arms": 24, "delts": 16},
        hard_cap_by_group={"arms": 28, "delts": 18},
        weak_point_bonus_by_group={"arms": 3, "delts": 2},
        combined_arm_delt_share_cap=0.48,
        weak_point_combined_arm_delt_share_cap=0.52,
    ),
    "higher_time_normal_recovery": _ThreeDayBalanceTargets(
        major_floor_by_group={"chest": 12, "back": 14, "quads": 9, "hamstrings": 9, "core": 4},
        soft_cap_by_group={"arms": 26, "delts": 17},
        hard_cap_by_group={"arms": 30, "delts": 19},
        weak_point_bonus_by_group={"arms": 3, "delts": 2},
        combined_arm_delt_share_cap=0.47,
        weak_point_combined_arm_delt_share_cap=0.51,
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
) -> GeneratedExerciseDraft:
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
        return 5 if time_budget_minutes >= 75 else 4
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
    "core": "abs",
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


def _resolved_primary_muscles_for_generated_exercise(record: dict[str, Any]) -> list[str]:
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


def _compute_major_group_volume(
    *,
    sessions: list[GeneratedSessionDraft],
    record_by_id: dict[str, dict[str, Any]],
) -> dict[str, int]:
    totals = {key: 0 for key in MAJOR_MUSCLE_TARGETS}
    for session in sessions:
        for exercise in session.exercises:
            primary = _normalize_muscle_set(list(exercise.primary_muscles or []))
            for group in _major_group_matches(primary):
                totals[group] += int(exercise.sets)
    return totals


def _compute_primary_major_group_volume(
    *,
    sessions: list[GeneratedSessionDraft],
    record_by_id: dict[str, dict[str, Any]],
) -> dict[str, int]:
    del record_by_id
    totals = {key: 0 for key in MAJOR_MUSCLE_TARGETS}
    for session in sessions:
        for exercise in session.exercises:
            primary = _normalize_muscle_set(list(exercise.primary_muscles or []))
            for group in _major_group_matches(primary):
                totals[group] += int(exercise.sets)
    return totals


def _exercise_primary_major_groups(record: dict[str, Any]) -> set[str]:
    return _major_group_matches(_normalize_muscle_set(_resolved_primary_muscles_for_generated_exercise(record)))


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


def _would_violate_arm_delt_caps(
    *,
    record: dict[str, Any],
    current_primary_volume: dict[str, int],
    targets: _ThreeDayBalanceTargets,
    weak_point_groups: set[str],
    major_floors_satisfied: bool,
    projected_set_increase: int = 1,
) -> bool:
    groups = _exercise_primary_major_groups(record)
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


def _weekly_muscle_volume_sum(
    *,
    sessions: list[GeneratedSessionDraft],
    record_by_id: dict[str, dict[str, Any]],
) -> int:
    return int(sum(_compute_major_group_volume(sessions=sessions, record_by_id=record_by_id).values()))


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
        weekly_muscle_volume = _weekly_muscle_volume_sum(sessions=sessions, record_by_id=record_by_id)
        primary_volume = _compute_primary_major_group_volume(sessions=sessions, record_by_id=record_by_id)
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
                groups = _exercise_primary_major_groups(record)
                if deficits and not groups.intersection(set(deficits)):
                    continue
                if _would_violate_arm_delt_caps(
                    record=record,
                    current_primary_volume=primary_volume,
                    targets=balance_targets,
                    weak_point_groups=weak_point_groups,
                    major_floors_satisfied=not deficits,
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
                    and _exercise_primary_major_groups(record_by_id.get(pair[1].id) or {}).intersection(weak_point_groups)
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
    weekly_volume = _compute_major_group_volume(sessions=sessions, record_by_id=record_by_id)
    primary_volume = _compute_primary_major_group_volume(sessions=sessions, record_by_id=record_by_id)
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
            muscles = _normalize_muscle_set(list(record.get("primary_muscles") or []))
            if group not in _major_group_matches(muscles):
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
                ):
                    continue
            exercise.sets += 1
            weekly_volume[group] = int(weekly_volume.get(group, 0)) + 1
            for matched_group in _exercise_primary_major_groups(record):
                primary_volume[matched_group] = int(primary_volume.get(matched_group, 0)) + 1
            deficit -= 1

    if apply_three_day_band and balance_targets is not None:
        for _ in range(120):
            primary_volume = _compute_primary_major_group_volume(sessions=sessions, record_by_id=record_by_id)
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
                    groups = _exercise_primary_major_groups(record)
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
        for _ in range(120):
            primary_volume = _compute_primary_major_group_volume(sessions=sessions, record_by_id=record_by_id)
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
                    groups = _exercise_primary_major_groups(record)
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
            donor = sorted(
                donors,
                key=lambda item: (
                    donor_priority.get(item.slot_role, 4),
                    item.id,
                ),
            )[0]
            donor_record = record_by_id.get(donor.id) or {}
            donor_groups = _exercise_primary_major_groups(donor_record)
            next_primary = dict(primary_volume)
            for group in donor_groups:
                next_primary[group] = max(0, int(next_primary.get(group, 0)) - 1)
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
                break
            donor.sets -= 1

        _rebalance_session_set_totals(sessions=sessions, time_budget_minutes=time_budget_minutes)

    _escalate_three_day_volume_minima(
        sessions=sessions,
        record_by_id=record_by_id,
        assessment=assessment,
        core_viable=core_viable,
        apply_three_day_band=apply_three_day_band,
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


def build_generated_full_body_template_draft(
    *,
    assessment: UserAssessment,
    blueprint_input: GeneratedFullBodyBlueprintInput,
    doctrine_bundle: DoctrineBundle,
    policy_bundle: PolicyBundle,
    exercise_library: CanonicalExerciseLibraryBundle,
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
    target_exercises_per_session, effective_session_exercise_cap = _density_targets_for_budget(
        assessment=assessment,
        session_count=blueprint_input.session_count,
        volume_tier=blueprint_input.volume_tier,
        doctrine_target=doctrine_session_target,
        minimum_exercises_per_session=minimum_exercises_per_session,
        apply_three_day_band=apply_three_day_band,
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
            selection = select_scored_candidate(
                doctrine_bundle=doctrine_bundle,
                selection_mode="required_slot",
                candidate_ids=feasible_candidate_ids,
                record_by_id=record_by_id,
                assessment=assessment,
                blueprint_input=blueprint_input,
                assigned_counts=assigned_counts,
                weekly_selected_exercise_ids=_collect_selected_exercise_ids(sessions),
                session_exercise_count=len(session.exercises),
                target_exercises_per_session=target_exercises_per_session,
                target_movement_pattern=movement_pattern,
                target_weak_point_muscles=[item.muscle_group for item in assessment.weak_point_priorities],
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
                )
                session.exercises.append(exercise)
                session_exercise_ids.add(selection.selected_id)
                assigned_counts[selection.selected_id] = assigned_counts.get(selection.selected_id, 0) + 1
                weak_point_slots_used += 1
                inserted = True
                break
            if inserted:
                continue

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
                primary_volume = _compute_primary_major_group_volume(sessions=sessions, record_by_id=record_by_id)
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
            if feasible_candidate_ids and apply_three_day_band:
                balance_targets = _resolve_three_day_balance_targets(assessment=assessment)
                primary_volume = _compute_primary_major_group_volume(sessions=sessions, record_by_id=record_by_id)
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
                            if group in _exercise_primary_major_groups(record_by_id.get(exercise_id) or {})
                        ]
                        if group_ids:
                            floor_prioritized_ids = group_ids
                            break
                    if not floor_prioritized_ids:
                        floor_prioritized_ids = [
                            exercise_id
                            for exercise_id in feasible_candidate_ids
                            if _exercise_primary_major_groups(record_by_id.get(exercise_id) or {}).intersection(set(deficits))
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
                    primary_volume = _compute_primary_major_group_volume(sessions=sessions, record_by_id=record_by_id)
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
    )
    _apply_session_flow_ordering(sessions=sessions, record_by_id=record_by_id)

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
