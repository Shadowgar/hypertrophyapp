from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .generated_assessment_builder import build_user_assessment
from .generated_assessment_schema import ProfileAssessmentInput
from .generated_full_body_blueprint_builder import build_generated_full_body_blueprint_input
from .generated_full_body_template_constructor import build_generated_full_body_template_draft
from .knowledge_loader import load_doctrine_bundle, load_exercise_library, load_exercise_metadata_v2, load_policy_bundle
from .template_schema import CanonicalProgramTemplate


GENERATED_FULL_BODY_COMPATIBILITY_TEMPLATE_ID = "full_body_v1"

FALLBACK_REASON_BUNDLE_LOAD_FAILED = "bundle_load_failed"
FALLBACK_REASON_ASSESSMENT_VALIDATION_FAILED = "assessment_validation_failed"
FALLBACK_REASON_BLUEPRINT_VALIDATION_FAILED = "blueprint_validation_failed"
FALLBACK_REASON_CONSTRUCTOR_INSUFFICIENT = "constructor_insufficient"
FALLBACK_REASON_DRAFT_ADAPTATION_FAILED = "draft_adaptation_failed"
FALLBACK_REASON_UNEXPECTED_EXCEPTION = "unexpected_exception"

RUNTIME_ADAPTER_FALLBACK_REASONS = {
    FALLBACK_REASON_BUNDLE_LOAD_FAILED,
    FALLBACK_REASON_ASSESSMENT_VALIDATION_FAILED,
    FALLBACK_REASON_BLUEPRINT_VALIDATION_FAILED,
    FALLBACK_REASON_CONSTRUCTOR_INSUFFICIENT,
    FALLBACK_REASON_DRAFT_ADAPTATION_FAILED,
    FALLBACK_REASON_UNEXPECTED_EXCEPTION,
}


def _base_trace(*, selected_template_id: str, activation_guard_matched: bool) -> dict[str, Any]:
    return {
        "selected_template_id": selected_template_id,
        "compatibility_selected_template_id": selected_template_id,
        "compatibility_program_template_id": selected_template_id,
        "compatibility_mode": "canonical_template_id_preserved",
        "activation_guard_matched": activation_guard_matched,
        "anti_copy_guard_mode": "doctrine_blueprint_constructor_only",
    }


def _not_applicable_result(*, selected_template_id: str, selected_template: dict[str, Any]) -> dict[str, Any]:
    trace = _base_trace(selected_template_id=selected_template_id, activation_guard_matched=False)
    trace.update(
        {
            "status": "not_applicable",
            "content_origin": "fallback_to_selected_template",
            "generated_constructor_applied": False,
        }
    )
    return {
        "status": "not_applicable",
        "program_template": dict(selected_template),
        "generated_full_body_runtime_trace": trace,
        "generated_full_body_adaptive_loop_policy": None,
        "generated_full_body_block_review_policy": None,
    }


def _fallback_result(
    *,
    selected_template_id: str,
    selected_template: dict[str, Any],
    fallback_reason: str,
    assessment_id: str | None = None,
    blueprint_input_id: str | None = None,
    generated_template_draft_id: str | None = None,
    constructibility_status: str | None = None,
) -> dict[str, Any]:
    trace = _base_trace(selected_template_id=selected_template_id, activation_guard_matched=True)
    trace.update(
        {
            "status": "fallback_to_selected_template",
            "content_origin": "fallback_to_selected_template",
            "generated_constructor_applied": False,
            "fallback_reason": fallback_reason,
        }
    )
    if assessment_id:
        trace["generated_assessment_id"] = assessment_id
    if blueprint_input_id:
        trace["generated_blueprint_input_id"] = blueprint_input_id
    if generated_template_draft_id:
        trace["generated_template_draft_id"] = generated_template_draft_id
    if constructibility_status:
        trace["constructibility_status"] = constructibility_status
    return {
        "status": "fallback_to_selected_template",
        "program_template": dict(selected_template),
        "generated_full_body_runtime_trace": trace,
        "generated_full_body_adaptive_loop_policy": None,
        "generated_full_body_block_review_policy": None,
    }


def _session_name_overrides(raw_sessions: Any, expected_count: int) -> list[str] | None:
    if not isinstance(raw_sessions, list) or len(raw_sessions) != expected_count:
        return None
    overrides: list[str] = []
    for session in raw_sessions:
        if not isinstance(session, dict):
            return None
        name = str(session.get("name") or "").strip()
        if not name:
            return None
        overrides.append(name)
    return overrides


def _draft_sessions_to_template_sessions(
    draft_sessions: list[Any],
    *,
    session_name_overrides: list[str] | None = None,
) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    for index, session in enumerate(draft_sessions):
        session_payload = {
            "name": (
                session_name_overrides[index]
                if session_name_overrides is not None and index < len(session_name_overrides)
                else session.title
            ),
            "day_role": session.day_role,
            "exercises": [
                {
                    "id": exercise.id,
                    "primary_exercise_id": exercise.id,
                    "name": exercise.name,
                    "sets": exercise.sets,
                    "rep_range": list(exercise.rep_range),
                    "start_weight": exercise.start_weight,
                    "slot_role": exercise.slot_role,
                    "movement_pattern": exercise.movement_pattern,
                    "primary_muscles": list(exercise.primary_muscles),
                    "equipment_tags": list(exercise.equipment_tags),
                    "substitution_candidates": list(exercise.substitution_candidates),
                }
                for exercise in session.exercises
            ],
        }
        sessions.append(session_payload)
    return sessions


def _adapt_draft_to_program_template(
    *,
    selected_template_id: str,
    selected_template: dict[str, Any],
    draft: Any,
) -> dict[str, Any]:
    generated_sessions = _draft_sessions_to_template_sessions(
        draft.sessions,
        session_name_overrides=_session_name_overrides(selected_template.get("sessions"), len(draft.sessions)),
    )
    adapted_template = deepcopy(selected_template)
    adapted_template["id"] = selected_template_id
    adapted_template["split"] = str(adapted_template.get("split") or draft.target_split or "full_body")
    adapted_template["sessions"] = generated_sessions

    authored_weeks = adapted_template.get("authored_weeks")
    if isinstance(authored_weeks, list) and authored_weeks:
        adapted_authored_weeks: list[dict[str, Any]] = []
        for raw_week in authored_weeks:
            week = deepcopy(raw_week) if isinstance(raw_week, dict) else {}
            week["sessions"] = _draft_sessions_to_template_sessions(
                draft.sessions,
                session_name_overrides=_session_name_overrides(week.get("sessions"), len(draft.sessions)),
            )
            adapted_authored_weeks.append(week)
        adapted_template["authored_weeks"] = adapted_authored_weeks
    else:
        adapted_template["authored_weeks"] = []

    validated = CanonicalProgramTemplate.model_validate(adapted_template)
    return validated.model_dump(mode="json")


def prepare_generated_full_body_runtime_template(
    *,
    selected_template_id: str,
    selected_template: dict[str, Any],
    profile_input: ProfileAssessmentInput,
    training_state: dict[str, Any],
    compiled_base_dir: Path | None = None,
) -> dict[str, Any]:
    if selected_template_id != GENERATED_FULL_BODY_COMPATIBILITY_TEMPLATE_ID:
        return _not_applicable_result(
            selected_template_id=selected_template_id,
            selected_template=selected_template,
        )

    try:
        doctrine_bundle = load_doctrine_bundle("multi_source_hypertrophy_v1", compiled_base_dir)
        policy_bundle = load_policy_bundle("system_coaching_policy_v1", compiled_base_dir)
        exercise_library = load_exercise_library(compiled_base_dir)
    except Exception:
        return _fallback_result(
            selected_template_id=selected_template_id,
            selected_template=selected_template,
            fallback_reason=FALLBACK_REASON_BUNDLE_LOAD_FAILED,
        )

    metadata_v2_loaded = False
    metadata_v2_record_count = 0
    metadata_v2_by_exercise_id: dict[str, Any] | None = None
    try:
        metadata_bundle = load_exercise_metadata_v2(compiled_base_dir)
    except Exception:
        metadata_bundle = None
    if metadata_bundle is not None:
        metadata_v2_by_exercise_id = {record.exercise_id: record.metadata_v2 for record in metadata_bundle.records}
        metadata_v2_loaded = True
        metadata_v2_record_count = len(metadata_bundle.records)

    try:
        assessment = build_user_assessment(
            profile_input=profile_input,
            training_state=training_state,
            doctrine_bundle=doctrine_bundle,
            policy_bundle=policy_bundle,
        )
    except (ValidationError, ValueError):
        return _fallback_result(
            selected_template_id=selected_template_id,
            selected_template=selected_template,
            fallback_reason=FALLBACK_REASON_ASSESSMENT_VALIDATION_FAILED,
        )

    try:
        blueprint_input = build_generated_full_body_blueprint_input(
            assessment=assessment,
            doctrine_bundle=doctrine_bundle,
            policy_bundle=policy_bundle,
            exercise_library=exercise_library,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
    except (ValidationError, ValueError):
        return _fallback_result(
            selected_template_id=selected_template_id,
            selected_template=selected_template,
            fallback_reason=FALLBACK_REASON_BLUEPRINT_VALIDATION_FAILED,
            assessment_id=assessment.assessment_id,
        )

    try:
        draft = build_generated_full_body_template_draft(
            assessment=assessment,
            blueprint_input=blueprint_input,
            doctrine_bundle=doctrine_bundle,
            policy_bundle=policy_bundle,
            exercise_library=exercise_library,
            metadata_v2_by_exercise_id=metadata_v2_by_exercise_id,
        )
    except Exception:
        return _fallback_result(
            selected_template_id=selected_template_id,
            selected_template=selected_template,
            fallback_reason=FALLBACK_REASON_UNEXPECTED_EXCEPTION,
            assessment_id=assessment.assessment_id,
            blueprint_input_id=blueprint_input.blueprint_input_id,
        )

    if draft.constructibility_status != "ready":
        return _fallback_result(
            selected_template_id=selected_template_id,
            selected_template=selected_template,
            fallback_reason=FALLBACK_REASON_CONSTRUCTOR_INSUFFICIENT,
            assessment_id=assessment.assessment_id,
            blueprint_input_id=blueprint_input.blueprint_input_id,
            generated_template_draft_id=draft.template_draft_id,
            constructibility_status=draft.constructibility_status,
        )

    try:
        program_template = _adapt_draft_to_program_template(
            selected_template_id=selected_template_id,
            selected_template=selected_template,
            draft=draft,
        )
    except (ValidationError, ValueError):
        return _fallback_result(
            selected_template_id=selected_template_id,
            selected_template=selected_template,
            fallback_reason=FALLBACK_REASON_DRAFT_ADAPTATION_FAILED,
            assessment_id=assessment.assessment_id,
            blueprint_input_id=blueprint_input.blueprint_input_id,
            generated_template_draft_id=draft.template_draft_id,
            constructibility_status=draft.constructibility_status,
        )

    trace = _base_trace(selected_template_id=selected_template_id, activation_guard_matched=True)
    candidate_ids = {
        exercise_id
        for exercise_ids in blueprint_input.candidate_exercise_ids_by_pattern.values()
        for exercise_id in exercise_ids
    }
    candidate_coverage = (
        float(
            len(
                [
                    exercise_id
                    for exercise_id in candidate_ids
                    if metadata_v2_by_exercise_id is not None and exercise_id in metadata_v2_by_exercise_id
                ]
            )
        )
        / float(len(candidate_ids))
        if candidate_ids
        else 0.0
    )
    selected_exercises = [exercise for session in draft.sessions for exercise in session.exercises]
    fallback_count = 0
    metadata_visible_count = 0
    metadata_scoring_used = False
    metadata_scoring_time = False
    metadata_scoring_recovery = False
    metadata_scoring_role = False
    metadata_scoring_overlap = False
    metadata_scoring_fallback_count = 0
    for exercise in selected_exercises:
        metadata = None if metadata_v2_by_exercise_id is None else metadata_v2_by_exercise_id.get(exercise.id)
        visible = [] if metadata is None else list(metadata.muscle_targeting.visible_grouped_muscle_mapping)
        if visible:
            metadata_visible_count += 1
        else:
            fallback_count += 1
        selection_trace = exercise.selection_trace
        metadata_scoring_used = metadata_scoring_used or bool(selection_trace.metadata_v2_used_for_scoring)
        metadata_scoring_time = metadata_scoring_time or bool(selection_trace.metadata_v2_used_for_time_efficiency)
        metadata_scoring_recovery = metadata_scoring_recovery or bool(selection_trace.metadata_v2_used_for_recovery)
        metadata_scoring_role = metadata_scoring_role or bool(selection_trace.metadata_v2_used_for_role_fit)
        metadata_scoring_overlap = metadata_scoring_overlap or bool(selection_trace.metadata_v2_used_for_overlap)
        metadata_scoring_fallback_count += int(selection_trace.metadata_v2_scoring_fallback_count)

    trace.update(
        {
            "status": "generated_constructor_applied",
            "content_origin": "generated_constructor_applied",
            "generated_constructor_applied": True,
            "generated_assessment_id": assessment.assessment_id,
            "generated_blueprint_input_id": blueprint_input.blueprint_input_id,
            "generated_template_draft_id": draft.template_draft_id,
            "constructibility_status": draft.constructibility_status,
            "metadata_v2_loaded": metadata_v2_loaded,
            "metadata_v2_record_count": metadata_v2_record_count,
            "metadata_v2_candidate_coverage_ratio": candidate_coverage,
            "metadata_v2_used_for_visible_balance": bool(metadata_v2_loaded and metadata_visible_count > 0),
            "metadata_v2_fallback_count": fallback_count,
            "metadata_v2_used_for_scoring": metadata_scoring_used,
            "metadata_v2_used_for_time_efficiency": metadata_scoring_time,
            "metadata_v2_used_for_recovery": metadata_scoring_recovery,
            "metadata_v2_used_for_role_fit": metadata_scoring_role,
            "metadata_v2_used_for_overlap": metadata_scoring_overlap,
            "metadata_v2_scoring_fallback_count": metadata_scoring_fallback_count,
        }
    )
    return {
        "status": "generated_constructor_applied",
        "program_template": program_template,
        "generated_full_body_runtime_trace": trace,
        "generated_full_body_adaptive_loop_policy": (
            policy_bundle.generated_full_body_adaptive_loop_policy.model_dump(mode="json")
            if policy_bundle.generated_full_body_adaptive_loop_policy is not None
            else None
        ),
        "generated_full_body_block_review_policy": (
            policy_bundle.generated_full_body_block_review_policy.model_dump(mode="json")
            if policy_bundle.generated_full_body_block_review_policy is not None
            else None
        ),
    }
