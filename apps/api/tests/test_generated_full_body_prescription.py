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
from app.generated_full_body_prescription import resolve_generated_full_body_initial_prescription
from app.knowledge_loader import load_doctrine_bundle, load_exercise_library, load_policy_bundle
from tests.fixtures.generated_full_body_archetypes import get_generated_full_body_archetypes


def _load_context(archetype_name: str):
    compiled_dir = REPO_ROOT / "knowledge" / "compiled"
    doctrine_bundle = load_doctrine_bundle("multi_source_hypertrophy_v1", compiled_dir)
    policy_bundle = load_policy_bundle("system_coaching_policy_v1", compiled_dir)
    exercise_library = load_exercise_library(compiled_dir)
    fixture = get_generated_full_body_archetypes()[archetype_name]
    assessment = build_user_assessment(
        profile_input=ProfileAssessmentInput.model_validate(fixture["profile_input"]),
        training_state=fixture["training_state"],
        doctrine_bundle=doctrine_bundle,
        policy_bundle=policy_bundle,
    )
    record_by_id = {record.exercise_id: record.model_dump(mode="json") for record in exercise_library.records}
    return fixture, assessment, doctrine_bundle, record_by_id


def test_generated_full_body_prescription_reuses_start_weight_only_for_exact_exercise_matches() -> None:
    _, assessment, doctrine_bundle, record_by_id = _load_context("novice_gym_full_body")

    exact_match = resolve_generated_full_body_initial_prescription(
        assessment=assessment,
        doctrine_bundle=doctrine_bundle,
        record=record_by_id["hack_squat"],
        slot_role="primary_compound",
        selection_mode="required_slot",
        day_role="generated_full_body_1",
        volume_tier="moderate",
    )
    fallback = resolve_generated_full_body_initial_prescription(
        assessment=assessment,
        doctrine_bundle=doctrine_bundle,
        record=record_by_id["decline_machine_chest_press"],
        slot_role="secondary_compound",
        selection_mode="required_slot",
        day_role="generated_full_body_1",
        volume_tier="moderate",
    )

    assert exact_match.start_weight == 245.0
    assert exact_match.field_trace["start_weight"].system_default_ids == []
    assert fallback.start_weight == 20.0
    assert fallback.field_trace["start_weight"].system_default_ids == ["default_generated_start_weight_v1"]


def test_generated_full_body_prescription_keeps_optional_fill_subordinate_to_required_work() -> None:
    _, assessment, doctrine_bundle, record_by_id = _load_context("low_time_full_body")

    required_compound = resolve_generated_full_body_initial_prescription(
        assessment=assessment,
        doctrine_bundle=doctrine_bundle,
        record=record_by_id["hack_squat"],
        slot_role="primary_compound",
        selection_mode="required_slot",
        day_role="generated_full_body_1",
        volume_tier="moderate",
    )
    optional_fill = resolve_generated_full_body_initial_prescription(
        assessment=assessment,
        doctrine_bundle=doctrine_bundle,
        record=record_by_id["standing_calf_raise"],
        slot_role="secondary_compound",
        selection_mode="optional_fill",
        day_role="generated_full_body_3",
        volume_tier="moderate",
    )

    assert required_compound.sets > optional_fill.sets
    assert required_compound.rep_range[0] < optional_fill.rep_range[0]


def test_generated_full_body_prescription_downshifts_low_recovery_relative_to_standard_cases() -> None:
    _, novice_assessment, doctrine_bundle, record_by_id = _load_context("novice_gym_full_body")
    _, low_recovery_assessment, _, _ = _load_context("low_recovery_full_body")

    standard = resolve_generated_full_body_initial_prescription(
        assessment=novice_assessment,
        doctrine_bundle=doctrine_bundle,
        record=record_by_id["hack_squat"],
        slot_role="primary_compound",
        selection_mode="required_slot",
        day_role="generated_full_body_1",
        volume_tier="moderate",
    )
    reduced = resolve_generated_full_body_initial_prescription(
        assessment=low_recovery_assessment,
        doctrine_bundle=doctrine_bundle,
        record=record_by_id["hack_squat"],
        slot_role="primary_compound",
        selection_mode="required_slot",
        day_role="generated_full_body_1",
        volume_tier="conservative",
    )

    assert reduced.sets < standard.sets
    assert reduced.rep_range[0] > standard.rep_range[0]


def test_generated_full_body_prescription_applies_day_role_emphasis_to_character_only() -> None:
    _, assessment, doctrine_bundle, record_by_id = _load_context("novice_gym_full_body")
    record = record_by_id["hack_squat"]

    day_one = resolve_generated_full_body_initial_prescription(
        assessment=assessment,
        doctrine_bundle=doctrine_bundle,
        record=record,
        slot_role="primary_compound",
        selection_mode="required_slot",
        day_role="generated_full_body_1",
        volume_tier="moderate",
    )
    day_two = resolve_generated_full_body_initial_prescription(
        assessment=assessment,
        doctrine_bundle=doctrine_bundle,
        record=record,
        slot_role="primary_compound",
        selection_mode="required_slot",
        day_role="generated_full_body_2",
        volume_tier="moderate",
    )

    assert day_one.sets != day_two.sets or day_one.rep_range != day_two.rep_range
    assert day_one.field_trace["sets"].doctrine_rule_ids[-1] == "full_body_day_role_prescription_emphasis_v1"
    assert day_two.field_trace["rep_range"].doctrine_rule_ids[1] == "full_body_day_role_prescription_emphasis_v1"
