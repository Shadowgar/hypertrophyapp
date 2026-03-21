from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
CORE_ENGINE_ROOT = REPO_ROOT / "packages" / "core-engine"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
if str(CORE_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ENGINE_ROOT))

from app.generated_assessment_builder import build_user_assessment
from app.generated_assessment_schema import ProfileAssessmentInput
from app.generated_full_body_blueprint_builder import build_generated_full_body_blueprint_input
from app.generated_full_body_template_constructor import build_generated_full_body_template_draft
from app.knowledge_loader import load_doctrine_bundle, load_exercise_library, load_policy_bundle
from core_engine.scheduler import generate_week_plan
from tests.fixtures.generated_full_body_archetypes import get_generated_full_body_archetypes


def _build_draft(archetype_fixture: dict):
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
    return assessment, draft, policy_bundle


def _to_program_template(draft) -> dict:
    return {
        "id": draft.template_draft_id,
        "sessions": [
            {
                "name": session.title,
                "day_role": session.day_role,
                "exercises": [
                    {
                        "id": exercise.id,
                        "name": exercise.name,
                        "movement_pattern": exercise.movement_pattern,
                        "slot_role": exercise.slot_role,
                        "primary_muscles": list(exercise.primary_muscles),
                        "equipment_tags": list(exercise.equipment_tags),
                        "sets": exercise.sets,
                        "rep_range": list(exercise.rep_range),
                        "start_weight": exercise.start_weight,
                        "substitution_candidates": list(exercise.substitution_candidates),
                    }
                    for exercise in session.exercises
                ],
            }
            for session in draft.sessions
        ],
    }


def test_generated_full_body_template_drafts_are_scheduler_compatible_for_constructible_archetypes() -> None:
    for archetype_name, fixture in get_generated_full_body_archetypes().items():
        assessment, draft, policy_bundle = _build_draft(fixture)
        if fixture["expected_template"]["constructibility_status"] != "ready":
            assert draft.constructibility_status == "insufficient", archetype_name
            continue

        plan = generate_week_plan(
            user_profile={"name": "Generated Constructor Test"},
            days_available=assessment.days_available,
            split_preference="full_body",
            program_template=_to_program_template(draft),
            history=[],
            phase="gain",
            available_equipment=list(assessment.baseline_signal_summary.available_equipment_tags),
            session_time_budget_minutes=assessment.session_time_budget_minutes,
            movement_restrictions=list(assessment.movement_restrictions),
            progression_state_per_exercise=fixture["training_state"]["progression_state_per_exercise"],
            stimulus_fatigue_response=fixture["training_state"]["stimulus_fatigue_response"],
            weak_areas=[item.muscle_group for item in assessment.weak_point_priorities],
        )

        assert len(plan["sessions"]) == fixture["expected_template"]["session_count"], archetype_name
        assert plan["program_template_id"] == draft.template_draft_id, archetype_name
        assert plan["split"] == "full_body", archetype_name
        minimum_exercises_per_session = policy_bundle.minimum_viable_program_policy.minimum_exercises_per_session
        for session in plan["sessions"]:
            assert session["exercises"], archetype_name
            assert len(session["exercises"]) >= minimum_exercises_per_session, archetype_name
