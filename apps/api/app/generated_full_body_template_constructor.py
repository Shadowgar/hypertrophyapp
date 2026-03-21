from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .generated_assessment_schema import UserAssessment
from .generated_full_body_blueprint_schema import GeneratedFullBodyBlueprintInput, PatternInsufficiencyRecord
from .generated_full_body_template_draft_schema import (
    ConstructibilityIssue,
    ConstructorTraceRef,
    GeneratedExerciseDraft,
    GeneratedFullBodyTemplateDraft,
    GeneratedSessionDraft,
)
from .knowledge_schema import CanonicalExerciseLibraryBundle, DoctrineBundle, DoctrineRuleStub, PolicyBundle


CONSTRUCTOR_SYSTEM_DEFAULTS: dict[str, str] = {
    "template_draft_id_hash_v1": "Deterministic generated Full Body template-draft hashing scheme.",
    "generated_session_id_v1": "Generic deterministic generated session-id scheme.",
    "generated_session_title_v1": "Generic deterministic generated session-title scheme.",
    "default_generated_sets_v1": "Temporary scheduler-compatibility default sets value for generated constructor outputs.",
    "default_generated_rep_range_v1": "Temporary scheduler-compatibility default rep-range value for generated constructor outputs.",
    "default_generated_start_weight_v1": "Temporary scheduler-compatibility default starting weight for generated constructor outputs.",
    "default_generated_substitution_candidates_empty_v1": "Temporary scheduler-compatibility default empty substitution-candidate list.",
    "constructor_assessment_reference_passthrough_v1": "Assessment id passthrough trace marker for constructor outputs.",
    "constructor_blueprint_reference_passthrough_v1": "Blueprint id passthrough trace marker for constructor outputs.",
    "constructor_bundle_reference_passthrough_v1": "Bundle id passthrough trace marker for constructor outputs.",
    "constructor_field_trace_v1": "Constructor field-trace generation marker.",
    "constructibility_issue_id_hash_v1": "Deterministic constructibility-issue hashing scheme.",
    "constructor_system_default_ids_used_v1": "Constructor system-default collection marker.",
}


DEFAULT_GENERATED_PRESCRIPTIONS = {
    "sets": 3,
    "rep_range": [8, 12],
    "start_weight": 20.0,
    "substitution_candidates": [],
}


@dataclass(frozen=True)
class _ResolvedRule:
    rule_id: str
    payload: dict[str, Any]


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


def _resolve_minimal_prescription_defaults() -> dict[str, Any]:
    return {
        "sets": DEFAULT_GENERATED_PRESCRIPTIONS["sets"],
        "rep_range": list(DEFAULT_GENERATED_PRESCRIPTIONS["rep_range"]),
        "start_weight": DEFAULT_GENERATED_PRESCRIPTIONS["start_weight"],
        "substitution_candidates": list(DEFAULT_GENERATED_PRESCRIPTIONS["substitution_candidates"]),
    }


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
    slot_role: str,
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
        "sets": _trace(system_default_ids=["default_generated_sets_v1"]),
        "rep_range": _trace(system_default_ids=["default_generated_rep_range_v1"]),
        "start_weight": _trace(system_default_ids=["default_generated_start_weight_v1"]),
        "substitution_candidates": _trace(system_default_ids=["default_generated_substitution_candidates_empty_v1"]),
        "field_trace": _trace(system_default_ids=["constructor_field_trace_v1"]),
    }


def _build_exercise_draft(
    *,
    record: dict[str, Any],
    slot_role: str,
    doctrine_rule_ids: list[str],
    policy_ids: list[str],
) -> GeneratedExerciseDraft:
    prescription_defaults = _resolve_minimal_prescription_defaults()
    field_trace = _selected_exercise_trace(
        doctrine_rule_ids=doctrine_rule_ids,
        policy_ids=policy_ids,
        exercise_id=record["exercise_id"],
        slot_role=slot_role,
    )
    return GeneratedExerciseDraft(
        id=record["exercise_id"],
        name=record["canonical_name"],
        movement_pattern=str(record.get("movement_pattern") or ""),
        slot_role=slot_role,
        primary_muscles=list(record.get("primary_muscles") or []),
        equipment_tags=list(record.get("equipment_tags") or []),
        sets=int(prescription_defaults["sets"]),
        rep_range=list(prescription_defaults["rep_range"]),
        start_weight=float(prescription_defaults["start_weight"]),
        substitution_candidates=list(prescription_defaults["substitution_candidates"]),
        field_trace=field_trace,
    )


def _select_candidate_exercise_id(
    *,
    candidate_ids: list[str],
    assigned_counts: dict[str, int],
    max_assignments_per_week: int,
    allow_reuse_after_unique_candidates_exhausted: bool,
    session_exercise_ids: set[str],
) -> tuple[str | None, bool]:
    for exercise_id in candidate_ids:
        if exercise_id in session_exercise_ids:
            continue
        if assigned_counts.get(exercise_id, 0) < max_assignments_per_week:
            return exercise_id, False

    if not allow_reuse_after_unique_candidates_exhausted:
        return None, False

    for exercise_id in candidate_ids:
        if exercise_id not in session_exercise_ids:
            return exercise_id, True
    return None, False


def _collect_selected_exercise_ids(sessions: list[GeneratedSessionDraft]) -> list[str]:
    return _unique_preserve_order([exercise.id for session in sessions for exercise in session.exercises])


def _collect_default_ids(
    sessions: list[GeneratedSessionDraft],
    insufficiencies: list[ConstructibilityIssue],
) -> list[str]:
    ids: list[str] = [
        "generated_session_id_v1",
        "generated_session_title_v1",
        "default_generated_sets_v1",
        "default_generated_rep_range_v1",
        "default_generated_start_weight_v1",
        "default_generated_substitution_candidates_empty_v1",
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
        "optional_fill": "full_body_optional_fill_pattern_priority_by_complexity_ceiling_v1",
        "slot_roles": "full_body_slot_role_sequence_v1",
        "reuse": "full_body_exercise_reuse_limits_v1",
        "weak_point": "full_body_weak_point_slot_insertion_v1",
    }
    topology_rule = _require_rule_payload(doctrine_bundle, rule_ids["topology"])
    day_role_rule = _require_rule_payload(doctrine_bundle, rule_ids["day_roles"])
    pattern_distribution_rule = _require_rule_payload(doctrine_bundle, rule_ids["pattern_distribution"])
    fill_target_rule = _require_rule_payload(doctrine_bundle, rule_ids["fill_target"])
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
    target_exercises_per_session = max(
        minimum_exercises_per_session,
        min(blueprint_input.session_exercise_cap, doctrine_session_target),
    )
    optional_fill_patterns = [
        str(item)
        for item in optional_fill_rule.payload["optional_patterns_by_complexity_ceiling"].get(
            blueprint_input.complexity_ceiling, []
        )
    ]
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
                    optional_fill_rule.rule_id,
                    slot_role_rule.rule_id,
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

            selected_id, _ = _select_candidate_exercise_id(
                candidate_ids=candidate_ids,
                assigned_counts=assigned_counts,
                max_assignments_per_week=max_assignments_per_week,
                allow_reuse_after_unique_candidates_exhausted=allow_reuse_after_exhaustion,
                session_exercise_ids=session_exercise_ids,
            )
            if selected_id is None:
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

            record = record_by_id.get(selected_id)
            if record is None:
                raise ValueError(f"exercise library missing selected exercise id: {selected_id}")

            exercise = _build_exercise_draft(
                record=record,
                slot_role=slot_role,
                doctrine_rule_ids=[
                    pattern_distribution_rule.rule_id,
                    slot_role_rule.rule_id,
                    reuse_rule.rule_id,
                ],
                policy_ids=anti_copy_policy_ids,
            )
            session.exercises.append(exercise)
            session_exercise_ids.add(selected_id)
            assigned_counts[selected_id] = assigned_counts.get(selected_id, 0) + 1

    weak_point_slot_role = str(weak_point_rule.payload.get("slot_role") or "weak_point")
    if weak_point_slots_used < weak_point_slot_limit:
        for preferred_session_index in _preferred_weak_point_sessions(weak_point_rule, blueprint_input.session_count):
            if weak_point_slots_used >= weak_point_slot_limit:
                break
            session = session_lookup.get(preferred_session_index)
            if session is None:
                continue
            remaining_capacity = target_exercises_per_session - len(session.exercises)
            if remaining_capacity < minimum_remaining_capacity or len(session.exercises) >= blueprint_input.session_exercise_cap:
                continue
            session_exercise_ids = {exercise.id for exercise in session.exercises}
            inserted = False
            for weak_point in assessment.weak_point_priorities:
                candidate_ids = list(
                    blueprint_input.weak_point_candidate_exercise_ids_by_muscle.get(weak_point.muscle_group, [])
                )
                selected_id, _ = _select_candidate_exercise_id(
                    candidate_ids=candidate_ids,
                    assigned_counts=assigned_counts,
                    max_assignments_per_week=max_assignments_per_week,
                    allow_reuse_after_unique_candidates_exhausted=allow_reuse_after_exhaustion,
                    session_exercise_ids=session_exercise_ids,
                )
                if selected_id is None:
                    continue
                record = record_by_id.get(selected_id)
                if record is None:
                    continue
                exercise = _build_exercise_draft(
                    record=record,
                    slot_role=weak_point_slot_role,
                    doctrine_rule_ids=[
                        fill_target_rule.rule_id,
                        weak_point_rule.rule_id,
                        slot_role_rule.rule_id,
                        reuse_rule.rule_id,
                    ],
                    policy_ids=density_policy_ids,
                )
                session.exercises.append(exercise)
                session_exercise_ids.add(selected_id)
                assigned_counts[selected_id] = assigned_counts.get(selected_id, 0) + 1
                weak_point_slots_used += 1
                inserted = True
                break
            if inserted:
                continue

    fill_progress = True
    while fill_progress:
        fill_progress = False
        for session in sessions:
            if len(session.exercises) >= target_exercises_per_session:
                continue
            if len(session.exercises) >= blueprint_input.session_exercise_cap:
                continue
            session_exercise_ids = {exercise.id for exercise in session.exercises}
            next_slot_role = _next_slot_role(
                session=session,
                slot_roles_by_position=slot_roles_by_position,
                fallback_slot_role="accessory",
            )
            for movement_pattern in optional_fill_patterns:
                candidate_ids = list(blueprint_input.candidate_exercise_ids_by_pattern.get(movement_pattern, []))
                if not candidate_ids:
                    continue
                selected_id, _ = _select_candidate_exercise_id(
                    candidate_ids=candidate_ids,
                    assigned_counts=assigned_counts,
                    max_assignments_per_week=max_assignments_per_week,
                    allow_reuse_after_unique_candidates_exhausted=allow_reuse_after_exhaustion,
                    session_exercise_ids=session_exercise_ids,
                )
                if selected_id is None:
                    continue
                record = record_by_id.get(selected_id)
                if record is None:
                    continue
                exercise = _build_exercise_draft(
                    record=record,
                    slot_role=next_slot_role,
                    doctrine_rule_ids=[
                        fill_target_rule.rule_id,
                        optional_fill_rule.rule_id,
                        slot_role_rule.rule_id,
                        reuse_rule.rule_id,
                    ],
                    policy_ids=density_policy_ids,
                )
                session.exercises.append(exercise)
                session_exercise_ids.add(selected_id)
                assigned_counts[selected_id] = assigned_counts.get(selected_id, 0) + 1
                fill_progress = True
                break

    if any(len(session.exercises) < target_exercises_per_session for session in sessions):
        _append_issue(
            insufficiencies,
            issue_keys,
            _pattern_issue(
                issue_type="session_fill_target_unmet",
                reason="one_or_more_sessions_below_target_after_optional_fill_exhausted",
                movement_pattern=None,
                slot_role=None,
                base_trace=_trace(
                    doctrine_rule_ids=[
                        fill_target_rule.rule_id,
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
