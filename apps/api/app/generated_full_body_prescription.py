from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .generated_assessment_schema import UserAssessment
from .generated_full_body_blueprint_schema import VolumeTier
from .generated_full_body_template_draft_schema import ConstructorTraceRef, SelectionMode
from .knowledge_schema import DoctrineBundle, DoctrineRuleStub


SETS_RULE_ID = "full_body_initial_sets_by_slot_role_and_volume_tier_v1"
USER_STATE_SET_RULE_ID = "full_body_set_adjustments_by_user_state_v1"
DAY_ROLE_RULE_ID = "full_body_day_role_prescription_emphasis_v1"
REP_RANGE_RULE_ID = "full_body_initial_rep_ranges_by_slot_role_and_pattern_v1"
EXERCISE_DEMAND_RULE_ID = "full_body_rep_adjustments_by_exercise_demand_v1"
START_WEIGHT_RULE_ID = "full_body_start_weight_initialization_v1"
SLOT_ROLES = ("primary_compound", "secondary_compound", "accessory", "weak_point")


@dataclass(frozen=True)
class PrescriptionResolution:
    sets: int
    rep_range: list[int]
    start_weight: float
    field_trace: dict[str, ConstructorTraceRef]


def _trace(
    *,
    doctrine_rule_ids: list[str] | None = None,
    exercise_ids: list[str] | None = None,
    system_default_ids: list[str] | None = None,
) -> ConstructorTraceRef:
    return ConstructorTraceRef(
        doctrine_rule_ids=doctrine_rule_ids or [],
        exercise_ids=exercise_ids or [],
        system_default_ids=system_default_ids or [],
    )


def _rule_index(bundle: DoctrineBundle) -> dict[str, DoctrineRuleStub]:
    index: dict[str, DoctrineRuleStub] = {}
    for rules in bundle.rules_by_module.values():
        for rule in rules:
            index[rule.rule_id] = rule
    return index


def _require_rule_payload(bundle: DoctrineBundle, rule_id: str) -> dict[str, Any]:
    rule = _rule_index(bundle).get(rule_id)
    if rule is None or not rule.payload:
        raise ValueError(f"doctrine bundle missing required payload rule: {rule_id}")
    return dict(rule.payload)


def _first_progression_level(record: dict[str, Any]) -> str | None:
    levels = list(record.get("progression_compatibility") or [])
    if not levels:
        return None
    return str(levels[0])


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _slot_role_map(rule_payload: dict[str, Any], key: str) -> dict[str, int]:
    values = rule_payload.get(key) or {}
    if not isinstance(values, dict):
        raise ValueError(f"prescription doctrine payload missing mapping for {key}")
    return {str(slot_role): int(delta) for slot_role, delta in values.items()}


def _selection_mode_map(rule_payload: dict[str, Any], selection_mode: SelectionMode) -> dict[str, Any]:
    payload = rule_payload.get("base_sets_by_selection_mode") or rule_payload.get("base_rep_ranges_by_selection_mode")
    if not isinstance(payload, dict):
        raise ValueError("prescription doctrine payload missing selection mode map")
    mode_payload = payload.get(selection_mode)
    if not isinstance(mode_payload, dict):
        raise ValueError(f"prescription doctrine payload missing selection mode contract for {selection_mode}")
    return mode_payload


def _resolve_sets(
    *,
    doctrine_bundle: DoctrineBundle,
    assessment: UserAssessment,
    slot_role: str,
    selection_mode: SelectionMode,
    day_role: str,
    volume_tier: VolumeTier,
    exercise_id: str,
) -> tuple[int, ConstructorTraceRef]:
    if slot_role not in SLOT_ROLES:
        raise ValueError(f"unsupported slot role for prescription: {slot_role}")

    sets_rule = _require_rule_payload(doctrine_bundle, SETS_RULE_ID)
    user_state_rule = _require_rule_payload(doctrine_bundle, USER_STATE_SET_RULE_ID)
    day_role_rule = _require_rule_payload(doctrine_bundle, DAY_ROLE_RULE_ID)

    base_sets = _selection_mode_map(sets_rule, selection_mode)
    volume_tier_sets = base_sets.get(volume_tier)
    if not isinstance(volume_tier_sets, dict):
        raise ValueError(f"prescription doctrine payload missing set contract for volume_tier={volume_tier}")

    resolved_sets = int(volume_tier_sets[slot_role])

    user_flag_deltas = user_state_rule.get("user_flag_set_deltas") or {}
    for flag in assessment.user_class_flags:
        slot_adjustments = user_flag_deltas.get(flag)
        if isinstance(slot_adjustments, dict):
            resolved_sets += int(slot_adjustments.get(slot_role, 0))

    schedule_deltas = user_state_rule.get("schedule_profile_set_deltas") or {}
    schedule_adjustments = schedule_deltas.get(assessment.schedule_profile)
    if isinstance(schedule_adjustments, dict):
        resolved_sets += int(schedule_adjustments.get(slot_role, 0))

    day_role_emphasis = (day_role_rule.get("emphasis_by_day_role") or {}).get(day_role, {})
    if not isinstance(day_role_emphasis, dict):
        day_role_emphasis = {}
    day_role_deltas = day_role_emphasis.get("set_deltas_by_slot_role") or {}
    if isinstance(day_role_deltas, dict):
        resolved_sets += int(day_role_deltas.get(slot_role, 0))

    minimum_sets = _slot_role_map(user_state_rule, "minimum_sets_by_slot_role")[slot_role]
    maximum_sets = _slot_role_map(user_state_rule, "maximum_sets_by_slot_role")[slot_role]

    return (
        _clamp(resolved_sets, minimum_sets, maximum_sets),
        _trace(
            doctrine_rule_ids=[SETS_RULE_ID, USER_STATE_SET_RULE_ID, DAY_ROLE_RULE_ID],
            exercise_ids=[exercise_id],
        ),
    )


def _resolve_base_rep_range(
    *,
    doctrine_bundle: DoctrineBundle,
    assessment: UserAssessment,
    slot_role: str,
    selection_mode: SelectionMode,
    day_role: str,
    volume_tier: VolumeTier,
    movement_pattern: str,
) -> tuple[list[int], dict[str, Any], dict[str, Any]]:
    rep_rule = _require_rule_payload(doctrine_bundle, REP_RANGE_RULE_ID)
    day_role_rule = _require_rule_payload(doctrine_bundle, DAY_ROLE_RULE_ID)

    base_ranges = _selection_mode_map(rep_rule, selection_mode)
    slot_payload = base_ranges.get(slot_role)
    if not isinstance(slot_payload, dict):
        raise ValueError(f"prescription doctrine payload missing rep-range slot contract for {slot_role}")

    pattern_overrides = slot_payload.get("pattern_overrides") or {}
    default_range = slot_payload.get("default")
    if movement_pattern in pattern_overrides:
        base_range = list(pattern_overrides[movement_pattern])
    else:
        base_range = list(default_range or [])
    if len(base_range) != 2:
        raise ValueError("rep-range contract must contain [min, max]")

    total_shift = 0
    total_shift += int((rep_rule.get("volume_tier_rep_shift") or {}).get(volume_tier, 0))
    total_shift += int((rep_rule.get("schedule_profile_rep_shift") or {}).get(assessment.schedule_profile, 0))
    for flag in assessment.user_class_flags:
        total_shift += int((rep_rule.get("user_flag_rep_shift") or {}).get(flag, 0))

    day_role_emphasis = (day_role_rule.get("emphasis_by_day_role") or {}).get(day_role, {})
    if not isinstance(day_role_emphasis, dict):
        day_role_emphasis = {}
    rep_shifts = day_role_emphasis.get("rep_range_shift_by_slot_role") or {}
    if isinstance(rep_shifts, dict):
        total_shift += int(rep_shifts.get(slot_role, 0))

    min_rep = int(rep_rule["minimum_rep"])
    max_rep = int(rep_rule["maximum_rep"])
    adjusted_range = [
        _clamp(int(base_range[0]) + total_shift, min_rep, max_rep),
        _clamp(int(base_range[1]) + total_shift, min_rep, max_rep),
    ]
    if adjusted_range[0] > adjusted_range[1]:
        adjusted_range[0] = adjusted_range[1]

    return adjusted_range, rep_rule, day_role_rule


def _resolve_rep_range(
    *,
    doctrine_bundle: DoctrineBundle,
    assessment: UserAssessment,
    record: dict[str, Any],
    slot_role: str,
    selection_mode: SelectionMode,
    day_role: str,
    volume_tier: VolumeTier,
) -> tuple[list[int], ConstructorTraceRef]:
    base_range, rep_rule, _ = _resolve_base_rep_range(
        doctrine_bundle=doctrine_bundle,
        assessment=assessment,
        slot_role=slot_role,
        selection_mode=selection_mode,
        day_role=day_role,
        volume_tier=volume_tier,
        movement_pattern=str(record.get("movement_pattern") or ""),
    )
    demand_rule = _require_rule_payload(doctrine_bundle, EXERCISE_DEMAND_RULE_ID)

    demand_shift = 0
    demand_shift += int((demand_rule.get("fatigue_cost_rep_shift") or {}).get(record.get("fatigue_cost"), 0))
    demand_shift += int((demand_rule.get("skill_demand_rep_shift") or {}).get(record.get("skill_demand"), 0))
    demand_shift += int((demand_rule.get("stability_demand_rep_shift") or {}).get(record.get("stability_demand"), 0))
    demand_shift += int(
        (demand_rule.get("progression_compatibility_rep_shift") or {}).get(_first_progression_level(record), 0)
    )
    demand_shift = min(demand_shift, int(demand_rule["maximum_total_positive_shift"]))

    min_rep = int(rep_rule["minimum_rep"])
    max_rep = int(rep_rule["maximum_rep"])
    adjusted_range = [
        _clamp(int(base_range[0]) + demand_shift, min_rep, max_rep),
        _clamp(int(base_range[1]) + demand_shift, min_rep, max_rep),
    ]
    if adjusted_range[0] > adjusted_range[1]:
        adjusted_range[0] = adjusted_range[1]

    return (
        adjusted_range,
        _trace(
            doctrine_rule_ids=[REP_RANGE_RULE_ID, DAY_ROLE_RULE_ID, EXERCISE_DEMAND_RULE_ID],
            exercise_ids=[record["exercise_id"]],
        ),
    )


def _resolve_start_weight(
    *,
    doctrine_bundle: DoctrineBundle,
    assessment: UserAssessment,
    record: dict[str, Any],
) -> tuple[float, ConstructorTraceRef]:
    start_weight_rule = _require_rule_payload(doctrine_bundle, START_WEIGHT_RULE_ID)
    if start_weight_rule.get("history_source") != "exact_exercise_id_match":
        raise ValueError("start-weight doctrine must require exact exercise id matching")
    if not bool(start_weight_rule.get("prohibit_cross_exercise_inference", False)):
        raise ValueError("start-weight doctrine must prohibit cross-exercise inference")

    exercise_id = str(record["exercise_id"])
    exact_match_weight = assessment.prior_working_weight_by_exercise_id.get(exercise_id)
    if exact_match_weight is not None:
        return (
            float(exact_match_weight),
            _trace(doctrine_rule_ids=[START_WEIGHT_RULE_ID], exercise_ids=[exercise_id]),
        )

    fallback_method = start_weight_rule.get("fallback_method") or {}
    fallback_default_id = fallback_method.get("system_default_id")
    fallback_value = fallback_method.get("value")
    if fallback_method.get("type") != "system_default" or not fallback_default_id or fallback_value is None:
        raise ValueError("start-weight doctrine fallback contract is malformed")
    return (
        float(fallback_value),
        _trace(
            doctrine_rule_ids=[START_WEIGHT_RULE_ID],
            exercise_ids=[exercise_id],
            system_default_ids=[str(fallback_default_id)],
        ),
    )


def resolve_generated_full_body_initial_prescription(
    *,
    assessment: UserAssessment,
    doctrine_bundle: DoctrineBundle,
    record: dict[str, Any],
    slot_role: str,
    selection_mode: SelectionMode,
    day_role: str,
    volume_tier: VolumeTier,
) -> PrescriptionResolution:
    sets, sets_trace = _resolve_sets(
        doctrine_bundle=doctrine_bundle,
        assessment=assessment,
        slot_role=slot_role,
        selection_mode=selection_mode,
        day_role=day_role,
        volume_tier=volume_tier,
        exercise_id=str(record["exercise_id"]),
    )
    rep_range, rep_range_trace = _resolve_rep_range(
        doctrine_bundle=doctrine_bundle,
        assessment=assessment,
        record=record,
        slot_role=slot_role,
        selection_mode=selection_mode,
        day_role=day_role,
        volume_tier=volume_tier,
    )
    start_weight, start_weight_trace = _resolve_start_weight(
        doctrine_bundle=doctrine_bundle,
        assessment=assessment,
        record=record,
    )

    return PrescriptionResolution(
        sets=sets,
        rep_range=rep_range,
        start_weight=start_weight,
        field_trace={
            "sets": sets_trace,
            "rep_range": rep_range_trace,
            "start_weight": start_weight_trace,
        },
    )
