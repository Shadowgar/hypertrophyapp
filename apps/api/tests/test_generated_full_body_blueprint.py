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
from app.generated_full_body_blueprint_schema import GeneratedFullBodyBlueprintInput
from app.knowledge_loader import load_doctrine_bundle, load_exercise_library, load_policy_bundle
from tests.fixtures.generated_full_body_archetypes import get_generated_full_body_archetypes


def _doctrine_rule_ids(bundle) -> set[str]:
    return {rule.rule_id for rules in bundle.rules_by_module.values() for rule in rules}


def _policy_ids(bundle) -> set[str]:
    return {item.constraint_id for item in bundle.hard_constraints} | {item.preference_id for item in bundle.soft_preferences}


def _collect_system_default_ids(blueprint) -> set[str]:
    ids = set()
    for trace in blueprint.field_trace.values():
        ids.update(trace.system_default_ids)
    for item in blueprint.required_movement_patterns:
        ids.update(item.trace.system_default_ids)
    for item in blueprint.pattern_coverage:
        ids.update(item.trace.system_default_ids)
    for item in blueprint.pattern_insufficiencies:
        ids.update(item.trace.system_default_ids)
    return ids


def _collect_doctrine_ids(blueprint) -> set[str]:
    ids = set()
    for trace in blueprint.field_trace.values():
        ids.update(trace.doctrine_rule_ids)
    for item in blueprint.required_movement_patterns:
        ids.update(item.trace.doctrine_rule_ids)
    for item in blueprint.pattern_coverage:
        ids.update(item.trace.doctrine_rule_ids)
    for item in blueprint.pattern_insufficiencies:
        ids.update(item.trace.doctrine_rule_ids)
    return ids


def _collect_policy_ids(blueprint) -> set[str]:
    ids = set()
    for trace in blueprint.field_trace.values():
        ids.update(trace.policy_ids)
    for item in blueprint.required_movement_patterns:
        ids.update(item.trace.policy_ids)
    for item in blueprint.pattern_coverage:
        ids.update(item.trace.policy_ids)
    for item in blueprint.pattern_insufficiencies:
        ids.update(item.trace.policy_ids)
    return ids


def test_generated_full_body_blueprint_is_deterministic_and_traceable() -> None:
    compiled_dir = REPO_ROOT / "knowledge" / "compiled"
    doctrine_bundle = load_doctrine_bundle("multi_source_hypertrophy_v1", compiled_dir)
    policy_bundle = load_policy_bundle("system_coaching_policy_v1", compiled_dir)
    exercise_library = load_exercise_library(compiled_dir)

    valid_doctrine_rule_ids = _doctrine_rule_ids(doctrine_bundle)
    valid_policy_ids = _policy_ids(policy_bundle)
    valid_exercise_ids = {record.exercise_id for record in exercise_library.records}
    exercise_by_id = {record.exercise_id: record for record in exercise_library.records}
    doctrine_rules = {rule.rule_id: rule for rules in doctrine_bundle.rules_by_module.values() for rule in rules}

    for archetype_name, fixture in get_generated_full_body_archetypes().items():
        assessment = build_user_assessment(
            profile_input=ProfileAssessmentInput.model_validate(fixture["profile_input"]),
            training_state=fixture["training_state"],
            doctrine_bundle=doctrine_bundle,
            policy_bundle=policy_bundle,
        )
        blueprint_first = build_generated_full_body_blueprint_input(
            assessment=assessment,
            doctrine_bundle=doctrine_bundle,
            policy_bundle=policy_bundle,
            exercise_library=exercise_library,
        )
        blueprint_second = build_generated_full_body_blueprint_input(
            assessment=assessment,
            doctrine_bundle=doctrine_bundle,
            policy_bundle=policy_bundle,
            exercise_library=exercise_library,
        )

        assert blueprint_first.model_dump(mode="json") == blueprint_second.model_dump(mode="json"), archetype_name
        assert blueprint_first.target_split == "full_body", archetype_name
        assert set(blueprint_first.field_trace) == set(GeneratedFullBodyBlueprintInput.model_fields), archetype_name

        for exercise_ids in blueprint_first.candidate_exercise_ids_by_pattern.values():
            assert set(exercise_ids) <= valid_exercise_ids, archetype_name
            assert exercise_ids == sorted(exercise_ids), archetype_name
        assert set(blueprint_first.excluded_exercise_ids) <= valid_exercise_ids, archetype_name

        assert _collect_doctrine_ids(blueprint_first) <= valid_doctrine_rule_ids, archetype_name
        assert _collect_policy_ids(blueprint_first) <= valid_policy_ids, archetype_name
        assert _collect_system_default_ids(blueprint_first) <= set(BLUEPRINT_SYSTEM_DEFAULTS), archetype_name
        assert set(blueprint_first.system_default_ids_used) <= set(BLUEPRINT_SYSTEM_DEFAULTS), archetype_name

        expected = fixture["expected_blueprint"]
        if "session_exercise_cap" in expected:
            assert blueprint_first.session_exercise_cap == expected["session_exercise_cap"], archetype_name
        if "volume_tier" in expected:
            assert blueprint_first.volume_tier == expected["volume_tier"], archetype_name
        if "complexity_ceiling" in expected:
            assert blueprint_first.complexity_ceiling == expected["complexity_ceiling"], archetype_name
        if "non_empty_candidate_patterns" in expected:
            for pattern in expected["non_empty_candidate_patterns"]:
                assert blueprint_first.candidate_exercise_ids_by_pattern.get(pattern), f"{archetype_name}: empty pool for {pattern}"
        optional_fill_patterns = doctrine_rules["full_body_optional_fill_pattern_priority_by_complexity_ceiling_v1"].payload[
            "optional_patterns_by_complexity_ceiling"
        ][blueprint_first.complexity_ceiling]
        for pattern in optional_fill_patterns:
            assert pattern in blueprint_first.candidate_exercise_ids_by_pattern, f"{archetype_name}: missing optional pool for {pattern}"
        if expected.get("expects_insufficiency"):
            assert blueprint_first.pattern_insufficiencies, archetype_name
            for insufficiency in blueprint_first.pattern_insufficiencies:
                assert insufficiency.reason in {"empty_candidate_pool", "candidate_count_below_required_exposures"}, archetype_name
                assert insufficiency.trace.system_default_ids == ["pattern_coverage_candidate_threshold_v1"], archetype_name
        if "required_policy_ids" in expected:
            traced_policy_ids = _collect_policy_ids(blueprint_first)
            for policy_id in expected["required_policy_ids"]:
                assert policy_id in traced_policy_ids, archetype_name

        if archetype_name == "restricted_equipment_full_body":
            available_equipment = set(assessment.baseline_signal_summary.available_equipment_tags)
            assert blueprint_first.excluded_exercise_ids, archetype_name
            for exercise_id in blueprint_first.excluded_exercise_ids:
                record = exercise_by_id[exercise_id]
                assert record.equipment_tags
                assert not set(record.equipment_tags).issubset(available_equipment)

        for coverage in blueprint_first.pattern_coverage:
            candidate_pool = blueprint_first.candidate_exercise_ids_by_pattern[coverage.movement_pattern]
            assert coverage.candidate_exercise_ids == candidate_pool, archetype_name
            if not candidate_pool:
                assert coverage.status == "empty", archetype_name
                assert any(item.movement_pattern == coverage.movement_pattern for item in blueprint_first.pattern_insufficiencies), archetype_name
