from inspect import signature
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.generated_assessment_builder import build_user_assessment
from app.generated_assessment_schema import ProfileAssessmentInput
from app.generated_full_body_blueprint_builder import BLUEPRINT_SYSTEM_DEFAULTS, build_generated_full_body_blueprint_input
from app.generated_full_body_template_constructor import CONSTRUCTOR_SYSTEM_DEFAULTS, build_generated_full_body_template_draft
from app.generated_full_body_template_draft_schema import (
    GeneratedExerciseDraft,
    GeneratedFullBodyTemplateDraft,
    GeneratedSessionDraft,
)
from app.knowledge_loader import load_doctrine_bundle, load_exercise_library, load_policy_bundle
from tests.fixtures.generated_full_body_archetypes import get_generated_full_body_archetypes


REQUIRED_CONSTRUCTOR_RULE_IDS = {
    "full_body_session_topology_by_session_count_v1",
    "full_body_day_role_sequence_by_session_count_v1",
    "full_body_movement_pattern_distribution_v1",
    "full_body_session_fill_target_by_volume_tier_v1",
    "full_body_optional_fill_pattern_priority_by_complexity_ceiling_v1",
    "full_body_slot_role_sequence_v1",
    "full_body_exercise_reuse_limits_v1",
    "full_body_weak_point_slot_insertion_v1",
}


def _collect_doctrine_ids(draft) -> set[str]:
    ids = set()
    for trace in draft.field_trace.values():
        ids.update(trace.doctrine_rule_ids)
    for issue in draft.insufficiencies:
        ids.update(issue.trace.doctrine_rule_ids)
    for session in draft.sessions:
        for trace in session.field_trace.values():
            ids.update(trace.doctrine_rule_ids)
        for exercise in session.exercises:
            for trace in exercise.field_trace.values():
                ids.update(trace.doctrine_rule_ids)
    return ids


def _collect_policy_ids(draft) -> set[str]:
    ids = set()
    for trace in draft.field_trace.values():
        ids.update(trace.policy_ids)
    for issue in draft.insufficiencies:
        ids.update(issue.trace.policy_ids)
    for session in draft.sessions:
        for trace in session.field_trace.values():
            ids.update(trace.policy_ids)
        for exercise in session.exercises:
            for trace in exercise.field_trace.values():
                ids.update(trace.policy_ids)
    return ids


def _policy_ids(bundle) -> set[str]:
    return (
        {item.constraint_id for item in bundle.hard_constraints}
        | {item.preference_id for item in bundle.soft_preferences}
        | {
            bundle.constraint_resolution_policy.policy_id,
            bundle.minimum_viable_program_policy.policy_id,
            bundle.anti_overadaptation_policy.policy_id,
            bundle.data_sufficiency_policy.policy_id,
        }
    )


def _collect_system_default_ids(draft) -> set[str]:
    ids = set()
    for trace in draft.field_trace.values():
        ids.update(trace.system_default_ids)
    for issue in draft.insufficiencies:
        ids.update(issue.trace.system_default_ids)
    for session in draft.sessions:
        for trace in session.field_trace.values():
            ids.update(trace.system_default_ids)
        for exercise in session.exercises:
            for trace in exercise.field_trace.values():
                ids.update(trace.system_default_ids)
    return ids


def _assert_trace_map(trace_map, expected_fields: set[str], label: str) -> None:
    assert set(trace_map) == expected_fields, label
    for field_name, trace in trace_map.items():
        assert (
            trace.doctrine_rule_ids
            or trace.policy_ids
            or trace.exercise_ids
            or trace.system_default_ids
        ), f"{label}: missing trace payload for {field_name}"


def _build_layers(archetype_fixture: dict):
    compiled_dir = REPO_ROOT / "knowledge" / "compiled"
    doctrine_bundle = load_doctrine_bundle("multi_source_hypertrophy_v1", compiled_dir)
    policy_bundle = load_policy_bundle("system_coaching_policy_v1", compiled_dir)
    exercise_library = load_exercise_library(compiled_dir)
    assessment = build_user_assessment(
        profile_input=ProfileAssessmentInput.model_validate(archetype_fixture["profile_input"]),
        training_state=archetype_fixture["training_state"],
        doctrine_bundle=doctrine_bundle,
        policy_bundle=policy_bundle,
    )
    blueprint = build_generated_full_body_blueprint_input(
        assessment=assessment,
        doctrine_bundle=doctrine_bundle,
        policy_bundle=policy_bundle,
        exercise_library=exercise_library,
    )
    draft = build_generated_full_body_template_draft(
        assessment=assessment,
        blueprint_input=blueprint,
        doctrine_bundle=doctrine_bundle,
        policy_bundle=policy_bundle,
        exercise_library=exercise_library,
    )
    return doctrine_bundle, policy_bundle, exercise_library, assessment, blueprint, draft


def test_generated_full_body_template_constructor_is_deterministic_traceable_and_original() -> None:
    compiled_dir = REPO_ROOT / "knowledge" / "compiled"
    doctrine_bundle = load_doctrine_bundle("multi_source_hypertrophy_v1", compiled_dir)
    policy_bundle = load_policy_bundle("system_coaching_policy_v1", compiled_dir)
    exercise_library = load_exercise_library(compiled_dir)

    valid_doctrine_rule_ids = {rule.rule_id for rules in doctrine_bundle.rules_by_module.values() for rule in rules}
    valid_policy_ids = _policy_ids(policy_bundle)
    valid_exercise_ids = {record.exercise_id for record in exercise_library.records}
    rules = {rule.rule_id: rule for rules in doctrine_bundle.rules_by_module.values() for rule in rules}

    sig = signature(build_generated_full_body_template_draft)
    assert list(sig.parameters) == [
        "assessment",
        "blueprint_input",
        "doctrine_bundle",
        "policy_bundle",
        "exercise_library",
    ]

    for archetype_name, fixture in get_generated_full_body_archetypes().items():
        _, _, _, assessment, blueprint, first = _build_layers(fixture)
        _, _, _, _, _, second = _build_layers(fixture)

        assert first.model_dump(mode="json") == second.model_dump(mode="json"), archetype_name
        assert first.constructibility_status == fixture["expected_template"]["constructibility_status"], archetype_name
        assert len(first.sessions) == fixture["expected_template"]["session_count"], archetype_name
        assert [len(session.exercises) for session in first.sessions] == fixture["expected_template"]["expected_session_exercise_counts"], archetype_name

        _assert_trace_map(first.field_trace, set(GeneratedFullBodyTemplateDraft.model_fields), archetype_name)

        expected_day_roles = rules["full_body_day_role_sequence_by_session_count_v1"].payload["day_roles_by_session_count"][
            str(blueprint.session_count)
        ]
        expected_distribution = rules["full_body_movement_pattern_distribution_v1"].payload["distribution_by_session_count"][
            str(blueprint.session_count)
        ]
        assert [session.day_role for session in first.sessions] == expected_day_roles, archetype_name
        assert [session.movement_pattern_targets for session in first.sessions] == [
            item["movement_patterns"] for item in expected_distribution
        ], archetype_name

        for index, session in enumerate(first.sessions, start=1):
            assert session.session_id == f"generated_full_body_session_{index}", archetype_name
            assert session.title == f"Generated Full Body {index}", archetype_name
            assert session.day_role == f"generated_full_body_{index}", archetype_name
            _assert_trace_map(session.field_trace, set(GeneratedSessionDraft.model_fields), f"{archetype_name}:session:{index}")
            assert len({exercise.id for exercise in session.exercises}) == len(session.exercises), archetype_name
            for exercise in session.exercises:
                assert exercise.id in valid_exercise_ids, archetype_name
                assert exercise.sets == 3, archetype_name
                assert exercise.rep_range == [8, 12], archetype_name
                assert exercise.start_weight == 20.0, archetype_name
                assert exercise.substitution_candidates == [], archetype_name
                _assert_trace_map(
                    exercise.field_trace,
                    set(GeneratedExerciseDraft.model_fields),
                    f"{archetype_name}:exercise:{exercise.id}",
                )

        assert _collect_doctrine_ids(first) <= valid_doctrine_rule_ids, archetype_name
        assert REQUIRED_CONSTRUCTOR_RULE_IDS <= _collect_doctrine_ids(first), archetype_name
        assert _collect_policy_ids(first) <= valid_policy_ids, archetype_name
        assert _collect_system_default_ids(first) <= (set(CONSTRUCTOR_SYSTEM_DEFAULTS) | set(BLUEPRINT_SYSTEM_DEFAULTS)), archetype_name
        assert set(first.system_default_ids_used) <= (set(CONSTRUCTOR_SYSTEM_DEFAULTS) | set(BLUEPRINT_SYSTEM_DEFAULTS)), archetype_name

        assert "do_not_replay_single_authored_layout" in _collect_policy_ids(first), archetype_name
        assert "do_not_replay_single_authored_layout" in first.field_trace["sessions"].policy_ids, archetype_name
        assert "minimum_viable_program_v1" in _collect_policy_ids(first), archetype_name

        serialized = json.dumps(first.model_dump(mode="json"), sort_keys=True)
        assert "week_template_id" not in serialized, archetype_name
        assert "program_id" not in serialized, archetype_name

        if fixture["expected_template"]["expects_insufficiency"]:
            assert first.insufficiencies, archetype_name
            assert first.constructibility_status == "insufficient", archetype_name
            assert any(issue.movement_pattern for issue in first.insufficiencies), archetype_name
            assert len({
                (issue.issue_type, issue.reason, issue.movement_pattern, issue.slot_role)
                for issue in first.insufficiencies
            }) == len(first.insufficiencies), archetype_name
        else:
            assert not first.insufficiencies, archetype_name
            assert all(session.exercises for session in first.sessions), archetype_name

        if archetype_name == "restricted_equipment_full_body":
            expected_patterns = {item.movement_pattern for item in blueprint.pattern_insufficiencies}
            actual_patterns = {item.movement_pattern for item in first.insufficiencies if item.movement_pattern}
            assert expected_patterns <= actual_patterns, archetype_name
