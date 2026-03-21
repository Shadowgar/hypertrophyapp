from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.generated_assessment_builder import ASSESSMENT_SYSTEM_DEFAULTS, build_user_assessment
from app.generated_assessment_schema import ProfileAssessmentInput, UserAssessment
from app.knowledge_loader import load_doctrine_bundle, load_policy_bundle
from tests.fixtures.generated_full_body_archetypes import get_generated_full_body_archetypes


RULE_FALLBACK_DEFAULT_IDS = {
    "default_assessment_experience_thresholds_v1",
    "default_assessment_recovery_mapping_v1",
    "default_assessment_schedule_mapping_v1",
    "default_assessment_comeback_rule_v1",
    "default_assessment_weak_point_merge_rule_v1",
}


def _doctrine_rule_ids(bundle) -> set[str]:
    return {rule.rule_id for rules in bundle.rules_by_module.values() for rule in rules}


def test_generated_assessment_builder_is_deterministic_and_traceable() -> None:
    compiled_dir = REPO_ROOT / "knowledge" / "compiled"
    doctrine_bundle = load_doctrine_bundle("multi_source_hypertrophy_v1", compiled_dir)
    policy_bundle = load_policy_bundle("system_coaching_policy_v1", compiled_dir)
    valid_doctrine_rule_ids = _doctrine_rule_ids(doctrine_bundle)

    for archetype_name, fixture in get_generated_full_body_archetypes().items():
        profile_input = ProfileAssessmentInput.model_validate(fixture["profile_input"])
        assessment_first = build_user_assessment(
            profile_input=profile_input,
            training_state=fixture["training_state"],
            doctrine_bundle=doctrine_bundle,
            policy_bundle=policy_bundle,
        )
        assessment_second = build_user_assessment(
            profile_input=profile_input,
            training_state=fixture["training_state"],
            doctrine_bundle=doctrine_bundle,
            policy_bundle=policy_bundle,
        )

        assert assessment_first.model_dump(mode="json") == assessment_second.model_dump(mode="json"), archetype_name

        expected = fixture["expected_assessment"]
        assert assessment_first.experience_level == expected["experience_level"], archetype_name
        assert assessment_first.user_class_flags == expected["user_class_flags"], archetype_name
        assert assessment_first.recovery_profile == expected["recovery_profile"], archetype_name
        assert assessment_first.schedule_profile == expected["schedule_profile"], archetype_name
        assert assessment_first.equipment_context == expected["equipment_context"], archetype_name
        assert assessment_first.fatigue_tolerance_profile == expected["fatigue_tolerance_profile"], archetype_name
        assert assessment_first.comeback_flag == expected["comeback_flag"], archetype_name
        assert [item.muscle_group for item in assessment_first.weak_point_priorities] == expected["weak_point_order"], archetype_name

        assert set(assessment_first.field_trace) == set(UserAssessment.model_fields), archetype_name
        for field_name, trace in assessment_first.field_trace.items():
            assert trace.input_refs or trace.rule_sources, f"{archetype_name}: missing trace payload for {field_name}"

        traced_doctrine_ids = {
            source.source_id
            for trace in assessment_first.field_trace.values()
            for source in trace.rule_sources
            if source.source_type == "doctrine"
        }
        assert traced_doctrine_ids <= valid_doctrine_rule_ids, archetype_name

        traced_system_ids = {
            source.source_id
            for trace in assessment_first.field_trace.values()
            for source in trace.rule_sources
            if source.source_type == "system_default"
        }
        assert traced_system_ids <= set(ASSESSMENT_SYSTEM_DEFAULTS), archetype_name
        assert set(assessment_first.system_default_ids_used) <= set(ASSESSMENT_SYSTEM_DEFAULTS), archetype_name
        assert not (set(assessment_first.system_default_ids_used) & RULE_FALLBACK_DEFAULT_IDS), archetype_name
        assert assessment_first.system_default_ids_used == expected.get("default_ids", []), archetype_name
