from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .adaptive_schema import UserTrainingState
from .generated_assessment_schema import (
    AssessmentFieldTrace,
    AssessmentRuleSource,
    AssessmentTraceRef,
    BaselineSignalSummary,
    ProfileAssessmentInput,
    UserAssessment,
    WeakPointPriority,
)
from .knowledge_schema import DoctrineBundle, DoctrineRuleStub, PolicyBundle


ASSESSMENT_SYSTEM_DEFAULTS: dict[str, str] = {
    "default_assessment_experience_thresholds_v1": "Fallback experience thresholds used when doctrine coverage is absent.",
    "default_assessment_recovery_mapping_v1": "Fallback recovery mapping used when doctrine coverage is absent.",
    "default_assessment_schedule_mapping_v1": "Fallback schedule mapping used when doctrine coverage is absent.",
    "default_assessment_comeback_rule_v1": "Fallback comeback detection rule used when doctrine coverage is absent.",
    "default_assessment_weak_point_merge_rule_v1": "Fallback weak-point merge rule used when doctrine coverage is absent.",
    "default_near_failure_tolerance_moderate_v1": "Fallback fatigue tolerance profile when no explicit profile value is provided.",
    "assessment_id_hash_v1": "Deterministic assessment id hashing scheme.",
    "assessment_field_trace_v1": "Assessment field-trace generation marker.",
    "assessment_system_default_ids_used_v1": "Assessment system-default collection marker.",
}

DEFAULT_EXPERIENCE_THRESHOLDS = {
    "novice": {
        "max_total_exposures_exclusive": 30,
        "max_tracked_progression_entries_exclusive": 5,
    },
    "advanced": {
        "min_total_exposures_inclusive": 90,
        "min_tracked_progression_entries_inclusive": 8,
        "min_performance_history_entries_inclusive": 24,
    },
    "fallback": "early_intermediate",
}
DEFAULT_RECOVERY_MAPPING = {
    "low_recovery_when": {
        "recoverability_values": ["low"],
        "recovery_state_values": ["high_fatigue"],
    },
    "fallback": "normal",
}
DEFAULT_SCHEDULE_MAPPING = {
    "low_time": {"max_minutes_inclusive": 45},
    "inconsistent_schedule": {
        "max_latest_adherence_score_inclusive": 2,
        "min_missed_session_count_inclusive": 2,
    },
    "fallback": "normal",
}
DEFAULT_COMEBACK_RULE = {
    "requires_prior_generated_weeks": True,
    "minimum_performance_history_entries_for_non_comeback": 3,
}
DEFAULT_WEAK_POINT_MERGE_RULE = {
    "source_priority": ["explicit", "inferred"],
    "maximum_priorities": 3,
}


@dataclass(frozen=True)
class _ResolvedRule:
    payload: dict[str, Any]
    rule_sources: list[AssessmentRuleSource]
    default_ids: list[str]


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


def _ensure_training_state(training_state: UserTrainingState | dict) -> UserTrainingState:
    if isinstance(training_state, UserTrainingState):
        return training_state
    return UserTrainingState.model_validate(training_state)


def _rule_index(bundle: DoctrineBundle | None) -> dict[str, DoctrineRuleStub]:
    if bundle is None:
        return {}

    index: dict[str, DoctrineRuleStub] = {}
    for rules in bundle.rules_by_module.values():
        for rule in rules:
            index[rule.rule_id] = rule
    return index


def _resolve_doctrine_rule(
    bundle: DoctrineBundle | None,
    *,
    rule_id: str,
    default_payload: dict[str, Any],
    default_id: str,
) -> _ResolvedRule:
    rule = _rule_index(bundle).get(rule_id)
    if rule and rule.payload:
        return _ResolvedRule(
            payload=rule.payload,
            rule_sources=[AssessmentRuleSource(source_type="doctrine", source_id=rule.rule_id)],
            default_ids=[],
        )

    return _ResolvedRule(
        payload=default_payload,
        rule_sources=[AssessmentRuleSource(source_type="system_default", source_id=default_id)],
        default_ids=[default_id],
    )


def _resolve_experience_thresholds(doctrine_bundle: DoctrineBundle | None, policy_bundle: PolicyBundle | None) -> _ResolvedRule:
    del policy_bundle
    return _resolve_doctrine_rule(
        doctrine_bundle,
        rule_id="assessment_experience_thresholds_v1",
        default_payload=DEFAULT_EXPERIENCE_THRESHOLDS,
        default_id="default_assessment_experience_thresholds_v1",
    )


def _resolve_recovery_mapping(doctrine_bundle: DoctrineBundle | None, policy_bundle: PolicyBundle | None) -> _ResolvedRule:
    del policy_bundle
    return _resolve_doctrine_rule(
        doctrine_bundle,
        rule_id="assessment_recovery_profile_mapping_v1",
        default_payload=DEFAULT_RECOVERY_MAPPING,
        default_id="default_assessment_recovery_mapping_v1",
    )


def _resolve_schedule_mapping(doctrine_bundle: DoctrineBundle | None, policy_bundle: PolicyBundle | None) -> _ResolvedRule:
    del policy_bundle
    return _resolve_doctrine_rule(
        doctrine_bundle,
        rule_id="assessment_schedule_profile_mapping_v1",
        default_payload=DEFAULT_SCHEDULE_MAPPING,
        default_id="default_assessment_schedule_mapping_v1",
    )


def _resolve_comeback_rule(doctrine_bundle: DoctrineBundle | None, policy_bundle: PolicyBundle | None) -> _ResolvedRule:
    del policy_bundle
    return _resolve_doctrine_rule(
        doctrine_bundle,
        rule_id="assessment_comeback_detection_v1",
        default_payload=DEFAULT_COMEBACK_RULE,
        default_id="default_assessment_comeback_rule_v1",
    )


def _resolve_weak_point_merge_rule(doctrine_bundle: DoctrineBundle | None, policy_bundle: PolicyBundle | None) -> _ResolvedRule:
    del policy_bundle
    return _resolve_doctrine_rule(
        doctrine_bundle,
        rule_id="assessment_weak_point_merge_v1",
        default_payload=DEFAULT_WEAK_POINT_MERGE_RULE,
        default_id="default_assessment_weak_point_merge_rule_v1",
    )


def _profile_trace(source_path: str, source_id: str) -> AssessmentTraceRef:
    return AssessmentTraceRef(source_type="profile", source_path=source_path, source_id=source_id)


def _training_state_trace(source_path: str, source_id: str) -> AssessmentTraceRef:
    return AssessmentTraceRef(source_type="training_state", source_path=source_path, source_id=source_id)


def _system_trace(default_id: str, source_path: str) -> AssessmentTraceRef:
    return AssessmentTraceRef(source_type="system_default", source_path=source_path, source_id=default_id)


def _field_trace(
    *,
    input_refs: list[AssessmentTraceRef] | None = None,
    rule_sources: list[AssessmentRuleSource] | None = None,
) -> AssessmentFieldTrace:
    return AssessmentFieldTrace(input_refs=input_refs or [], rule_sources=rule_sources or [])


def _profile_or_state_scalar(
    profile_value: Any,
    state_value: Any,
    *,
    profile_path: str,
    state_path: str,
    source_id: str,
) -> tuple[Any, list[AssessmentTraceRef]]:
    if profile_value is not None:
        return profile_value, [_profile_trace(profile_path, source_id)]
    if state_value is not None:
        return state_value, [_training_state_trace(state_path, source_id)]
    return None, [_profile_trace(profile_path, source_id)]


def _profile_or_state_list(
    profile_values: list[str],
    state_values: list[str],
    *,
    profile_path: str,
    state_path: str,
    source_id: str,
) -> tuple[list[str], list[AssessmentTraceRef]]:
    if profile_values:
        return list(profile_values), [_profile_trace(profile_path, source_id)]
    if state_values:
        return list(state_values), [_training_state_trace(state_path, source_id)]
    return [], [_profile_trace(profile_path, source_id)]


def build_user_assessment(
    *,
    profile_input: ProfileAssessmentInput,
    training_state: UserTrainingState | dict,
    doctrine_bundle: DoctrineBundle | None = None,
    policy_bundle: PolicyBundle | None = None,
) -> UserAssessment:
    state = _ensure_training_state(training_state)
    defaults_used: list[str] = []

    experience_rule = _resolve_experience_thresholds(doctrine_bundle, policy_bundle)
    recovery_rule = _resolve_recovery_mapping(doctrine_bundle, policy_bundle)
    schedule_rule = _resolve_schedule_mapping(doctrine_bundle, policy_bundle)
    comeback_rule = _resolve_comeback_rule(doctrine_bundle, policy_bundle)
    weak_point_rule = _resolve_weak_point_merge_rule(doctrine_bundle, policy_bundle)

    defaults_used.extend(experience_rule.default_ids)
    defaults_used.extend(recovery_rule.default_ids)
    defaults_used.extend(schedule_rule.default_ids)
    defaults_used.extend(comeback_rule.default_ids)
    defaults_used.extend(weak_point_rule.default_ids)

    split_preference, split_refs = _profile_or_state_scalar(
        profile_input.split_preference,
        state.constraint_state.split_preference,
        profile_path="profile_input.split_preference",
        state_path="training_state.constraint_state.split_preference",
        source_id="split_preference",
    )
    training_location, training_location_refs = _profile_or_state_scalar(
        profile_input.training_location,
        state.constraint_state.training_location,
        profile_path="profile_input.training_location",
        state_path="training_state.constraint_state.training_location",
        source_id="training_location",
    )
    equipment_profile, equipment_refs = _profile_or_state_list(
        profile_input.equipment_profile,
        state.constraint_state.equipment_profile,
        profile_path="profile_input.equipment_profile",
        state_path="training_state.constraint_state.equipment_profile",
        source_id="equipment_profile",
    )
    weak_areas, weak_area_refs = _profile_or_state_list(
        profile_input.weak_areas,
        state.constraint_state.weak_areas,
        profile_path="profile_input.weak_areas",
        state_path="training_state.constraint_state.weak_areas",
        source_id="weak_areas",
    )
    time_budget, time_budget_refs = _profile_or_state_scalar(
        profile_input.session_time_budget_minutes,
        state.constraint_state.session_time_budget_minutes,
        profile_path="profile_input.session_time_budget_minutes",
        state_path="training_state.constraint_state.session_time_budget_minutes",
        source_id="session_time_budget_minutes",
    )
    movement_restrictions, movement_restriction_refs = _profile_or_state_list(
        profile_input.movement_restrictions,
        state.constraint_state.movement_restrictions,
        profile_path="profile_input.movement_restrictions",
        state_path="training_state.constraint_state.movement_restrictions",
        source_id="movement_restrictions",
    )
    near_failure_tolerance, fatigue_tolerance_refs = _profile_or_state_scalar(
        profile_input.near_failure_tolerance,
        state.constraint_state.near_failure_tolerance,
        profile_path="profile_input.near_failure_tolerance",
        state_path="training_state.constraint_state.near_failure_tolerance",
        source_id="near_failure_tolerance",
    )

    if near_failure_tolerance is None:
        near_failure_tolerance = "moderate"
        defaults_used.append("default_near_failure_tolerance_moderate_v1")
        fatigue_tolerance_refs = [
            _system_trace(
                "default_near_failure_tolerance_moderate_v1",
                "generated_assessment_builder.default_near_failure_tolerance",
            )
        ]

    progression_exposure_total = sum(entry.exposure_count for entry in state.progression_state_per_exercise)
    tracked_progression_entries = len(state.progression_state_per_exercise)
    performance_history_entries = len(state.exercise_performance_history)
    prior_generated_week_total = sum(state.generation_state.prior_generated_weeks_by_program.values())
    under_target_muscles = list(state.generation_state.under_target_muscles)
    prior_working_weight_by_exercise_id = {
        entry.exercise_id: float(entry.current_working_weight)
        for entry in state.progression_state_per_exercise
    }

    novice_thresholds = experience_rule.payload["novice"]
    advanced_thresholds = experience_rule.payload["advanced"]
    if (
        progression_exposure_total < novice_thresholds["max_total_exposures_exclusive"]
        or tracked_progression_entries < novice_thresholds["max_tracked_progression_entries_exclusive"]
    ):
        experience_level = "novice"
    elif (
        progression_exposure_total >= advanced_thresholds["min_total_exposures_inclusive"]
        and tracked_progression_entries >= advanced_thresholds["min_tracked_progression_entries_inclusive"]
        and performance_history_entries >= advanced_thresholds["min_performance_history_entries_inclusive"]
    ):
        experience_level = "advanced"
    else:
        experience_level = experience_rule.payload.get("fallback", "early_intermediate")

    recoverability_values = set(recovery_rule.payload["low_recovery_when"]["recoverability_values"])
    recovery_state_values = set(recovery_rule.payload["low_recovery_when"]["recovery_state_values"])
    coaching_recoverability = state.coaching_state.stimulus_fatigue_response.recoverability if state.coaching_state.stimulus_fatigue_response else None
    direct_recoverability = state.stimulus_fatigue_response.recoverability if state.stimulus_fatigue_response else None
    recovery_profile = (
        "low_recovery"
        if coaching_recoverability in recoverability_values
        or direct_recoverability in recoverability_values
        or state.fatigue_state.recovery_state in recovery_state_values
        else recovery_rule.payload.get("fallback", "normal")
    )

    low_time_max = schedule_rule.payload["low_time"]["max_minutes_inclusive"]
    inconsistent_max_score = schedule_rule.payload["inconsistent_schedule"]["max_latest_adherence_score_inclusive"]
    inconsistent_min_missed = schedule_rule.payload["inconsistent_schedule"]["min_missed_session_count_inclusive"]
    is_low_time = time_budget is not None and time_budget <= low_time_max
    is_inconsistent_schedule = (
        state.adherence_state.latest_adherence_score <= inconsistent_max_score
        or state.adherence_state.missed_session_count >= inconsistent_min_missed
    )
    if is_inconsistent_schedule:
        schedule_profile = "inconsistent_schedule"
    elif is_low_time:
        schedule_profile = "low_time"
    else:
        schedule_profile = schedule_rule.payload.get("fallback", "normal")

    equipment_context = "restricted_equipment" if training_location != "gym" or len(equipment_profile) < 4 else "full_gym"
    fatigue_tolerance_profile = near_failure_tolerance

    comeback_minimum_history = comeback_rule.payload["minimum_performance_history_entries_for_non_comeback"]
    comeback_flag = (
        bool(state.generation_state.prior_generated_weeks_by_program)
        and performance_history_entries < comeback_minimum_history
    )

    user_class_flags = [experience_level]
    if recovery_profile == "low_recovery":
        user_class_flags.append("low_recovery")
    if schedule_profile == "inconsistent_schedule":
        user_class_flags.append("inconsistent_schedule")
    if equipment_context == "restricted_equipment":
        user_class_flags.append("restricted_equipment")
    if comeback_flag:
        user_class_flags.append("comeback")
    user_class_flags = _unique_preserve_order(user_class_flags)

    max_priorities = weak_point_rule.payload["maximum_priorities"]
    merged_weak_points: list[str] = []
    weak_point_priorities: list[WeakPointPriority] = []
    for source_name, values, input_ref in [
        ("explicit", weak_areas, weak_area_refs or [_profile_trace("profile_input.weak_areas", "weak_areas")]),
        (
            "inferred",
            under_target_muscles,
            [_training_state_trace("training_state.generation_state.under_target_muscles", "under_target_muscles")],
        ),
    ]:
        for value in values:
            normalized = value.strip()
            if not normalized or normalized in merged_weak_points:
                continue
            merged_weak_points.append(normalized)
            weak_point_priorities.append(
                WeakPointPriority(
                    muscle_group=normalized,
                    priority_rank=len(weak_point_priorities) + 1,
                    source=source_name,
                    trace=_field_trace(input_refs=input_ref, rule_sources=weak_point_rule.rule_sources),
                )
            )
            if len(weak_point_priorities) >= max_priorities:
                break
        if len(weak_point_priorities) >= max_priorities:
            break

    baseline_signal_summary = BaselineSignalSummary(
        progression_exposure_total=progression_exposure_total,
        tracked_progression_entries=tracked_progression_entries,
        performance_history_entries=performance_history_entries,
        under_target_muscle_count=len(under_target_muscles),
        prior_generated_week_total=prior_generated_week_total,
        available_equipment_tags=sorted(set(equipment_profile)),
    )

    field_trace = {
        "assessment_id": _field_trace(
            input_refs=[
                _profile_trace("profile_input.days_available", "days_available"),
                _training_state_trace("training_state.progression_state_per_exercise", "progression_state_per_exercise"),
                _training_state_trace("training_state.exercise_performance_history", "exercise_performance_history"),
            ],
            rule_sources=[AssessmentRuleSource(source_type="system_default", source_id="assessment_id_hash_v1")],
        ),
        "experience_level": _field_trace(
            input_refs=[
                _training_state_trace("training_state.progression_state_per_exercise", "progression_state_per_exercise"),
                _training_state_trace("training_state.exercise_performance_history", "exercise_performance_history"),
            ],
            rule_sources=experience_rule.rule_sources,
        ),
        "user_class_flags": _field_trace(
            input_refs=[
                _training_state_trace("training_state.adherence_state", "adherence_state"),
                _training_state_trace("training_state.fatigue_state", "fatigue_state"),
                _training_state_trace("training_state.generation_state", "generation_state"),
            ]
            + training_location_refs
            + equipment_refs,
            rule_sources=experience_rule.rule_sources + recovery_rule.rule_sources + schedule_rule.rule_sources + comeback_rule.rule_sources,
        ),
        "days_available": _field_trace(
            input_refs=[_profile_trace("profile_input.days_available", "days_available")],
        ),
        "split_preference": _field_trace(input_refs=split_refs),
        "session_time_budget_minutes": _field_trace(input_refs=time_budget_refs),
        "recovery_profile": _field_trace(
            input_refs=[
                _training_state_trace("training_state.fatigue_state.recovery_state", "recovery_state"),
                _training_state_trace(
                    "training_state.coaching_state.stimulus_fatigue_response.recoverability",
                    "coaching_recoverability",
                ),
            ],
            rule_sources=recovery_rule.rule_sources,
        ),
        "schedule_profile": _field_trace(
            input_refs=[
                _training_state_trace("training_state.adherence_state.latest_adherence_score", "latest_adherence_score"),
                _training_state_trace("training_state.adherence_state.missed_session_count", "missed_session_count"),
            ]
            + time_budget_refs,
            rule_sources=schedule_rule.rule_sources,
        ),
        "equipment_context": _field_trace(
            input_refs=training_location_refs + equipment_refs,
        ),
        "fatigue_tolerance_profile": _field_trace(
            input_refs=fatigue_tolerance_refs,
        ),
        "movement_restrictions": _field_trace(input_refs=movement_restriction_refs),
        "weak_point_priorities": _field_trace(
            input_refs=weak_area_refs
            + [_training_state_trace("training_state.generation_state.under_target_muscles", "under_target_muscles")],
            rule_sources=weak_point_rule.rule_sources,
        ),
        "comeback_flag": _field_trace(
            input_refs=[
                _training_state_trace("training_state.generation_state.prior_generated_weeks_by_program", "prior_generated_weeks_by_program"),
                _training_state_trace("training_state.exercise_performance_history", "exercise_performance_history"),
            ],
            rule_sources=comeback_rule.rule_sources,
        ),
        "prior_working_weight_by_exercise_id": _field_trace(
            input_refs=[
                _training_state_trace(
                    "training_state.progression_state_per_exercise.current_working_weight",
                    "progression_state_per_exercise",
                )
            ],
        ),
        "baseline_signal_summary": _field_trace(
            input_refs=[
                _training_state_trace("training_state.progression_state_per_exercise", "progression_state_per_exercise"),
                _training_state_trace("training_state.exercise_performance_history", "exercise_performance_history"),
                _training_state_trace("training_state.generation_state", "generation_state"),
            ]
            + equipment_refs,
        ),
        "field_trace": _field_trace(
            rule_sources=[AssessmentRuleSource(source_type="system_default", source_id="assessment_field_trace_v1")]
        ),
        "system_default_ids_used": _field_trace(
            rule_sources=[AssessmentRuleSource(source_type="system_default", source_id="assessment_system_default_ids_used_v1")]
        ),
    }

    assessment_payload = {
        "experience_level": experience_level,
        "user_class_flags": user_class_flags,
        "days_available": profile_input.days_available,
        "split_preference": split_preference,
        "session_time_budget_minutes": time_budget,
        "recovery_profile": recovery_profile,
        "schedule_profile": schedule_profile,
        "equipment_context": equipment_context,
        "fatigue_tolerance_profile": fatigue_tolerance_profile,
        "movement_restrictions": movement_restrictions,
        "weak_point_priorities": [item.model_dump(mode="json") for item in weak_point_priorities],
        "comeback_flag": comeback_flag,
        "prior_working_weight_by_exercise_id": prior_working_weight_by_exercise_id,
        "baseline_signal_summary": baseline_signal_summary.model_dump(mode="json"),
    }
    assessment_id = _hash_id("assessment", assessment_payload)

    return UserAssessment(
        assessment_id=assessment_id,
        experience_level=experience_level,
        user_class_flags=user_class_flags,
        days_available=profile_input.days_available,
        split_preference=split_preference,
        session_time_budget_minutes=time_budget,
        recovery_profile=recovery_profile,
        schedule_profile=schedule_profile,
        equipment_context=equipment_context,
        fatigue_tolerance_profile=fatigue_tolerance_profile,
        movement_restrictions=movement_restrictions,
        weak_point_priorities=weak_point_priorities,
        comeback_flag=comeback_flag,
        prior_working_weight_by_exercise_id=prior_working_weight_by_exercise_id,
        baseline_signal_summary=baseline_signal_summary,
        field_trace=field_trace,
        system_default_ids_used=_unique_preserve_order(defaults_used),
    )
