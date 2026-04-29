from pathlib import Path
import sys
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.generated_assessment_builder import build_user_assessment
from app.generated_assessment_schema import ProfileAssessmentInput
from app.generated_full_body_blueprint_builder import build_generated_full_body_blueprint_input
from app.generated_full_body_candidate_scoring import select_scored_candidate
from app.knowledge_loader import load_doctrine_bundle, load_exercise_library, load_policy_bundle
from tests.fixtures.generated_full_body_archetypes import get_generated_full_body_archetypes


def _metadata_stub(
    *,
    systemic: str = "moderate",
    local: str = "moderate",
    setup: str = "moderate",
    rest: str = "moderate",
    role: str = "primary",
    tags: list[str] | None = None,
    skill: str = "intermediate",
    stability: str = "intermediate",
    overlap: dict[str, bool] | None = None,
):
    overlap_payload = {
        "pressing_overlap": False,
        "front_delt_overlap": False,
        "triceps_overlap": False,
        "biceps_overlap": False,
        "grip_overlap": False,
        "trap_overlap": False,
        "lower_back_overlap": False,
        "knee_stress": False,
        "hip_hinge_overlap": False,
    }
    if overlap:
        overlap_payload.update(overlap)
    return SimpleNamespace(
        fatigue=SimpleNamespace(systemic_fatigue=systemic, local_fatigue=local),
        time_efficiency=SimpleNamespace(setup_time=setup, rest_need=rest),
        role=SimpleNamespace(primary_role=role, tags=list(tags or [])),
        skill_stability_safety=SimpleNamespace(skill_requirement=skill, stability_requirement=stability),
        overlap=SimpleNamespace(**overlap_payload),
    )


def _assessment_and_blueprint(archetype_name: str):
    fixture = get_generated_full_body_archetypes()[archetype_name]
    compiled_dir = REPO_ROOT / "knowledge" / "compiled"
    doctrine_bundle = load_doctrine_bundle("multi_source_hypertrophy_v1", compiled_dir)
    policy_bundle = load_policy_bundle("system_coaching_policy_v1", compiled_dir)
    exercise_library = load_exercise_library(compiled_dir)
    assessment = build_user_assessment(
        profile_input=ProfileAssessmentInput.model_validate(fixture["profile_input"]),
        training_state=fixture["training_state"],
        doctrine_bundle=doctrine_bundle,
        policy_bundle=policy_bundle,
    )
    blueprint = build_generated_full_body_blueprint_input(
        assessment=assessment,
        doctrine_bundle=doctrine_bundle,
        policy_bundle=policy_bundle,
        exercise_library=exercise_library,
    )
    return doctrine_bundle, assessment, blueprint


def test_required_slot_scoring_prefers_more_recoverable_and_less_complex_candidate() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("low_recovery_full_body")
    record_by_id = {
        "press_machine": {
            "exercise_id": "press_machine",
            "family_id": "press_machine",
            "movement_pattern": "horizontal_press",
            "primary_muscles": ["chest", "triceps"],
            "secondary_muscles": ["front_delts"],
            "equipment_tags": ["machine"],
            "fatigue_cost": "moderate",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["high"],
        },
        "press_unstable": {
            "exercise_id": "press_unstable",
            "family_id": "press_unstable",
            "movement_pattern": "horizontal_press",
            "primary_muscles": ["chest", "triceps"],
            "secondary_muscles": ["front_delts"],
            "equipment_tags": ["dumbbell"],
            "fatigue_cost": "high",
            "skill_demand": "high",
            "stability_demand": "high",
            "progression_compatibility": ["moderate"],
        },
    }

    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="required_slot",
        candidate_ids=["press_machine", "press_unstable"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=0,
        target_exercises_per_session=4,
        target_movement_pattern="horizontal_press",
        target_weak_point_muscles=[item.muscle_group for item in assessment.weak_point_priorities],
    )

    assert result is not None
    assert result.selected_id == "press_machine"
    assert result.selection_trace.total_score == result.total_score


def test_weak_point_slot_scoring_prefers_direct_primary_weak_point_hit() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("novice_gym_full_body")
    record_by_id = {
        "direct_chest": {
            "exercise_id": "direct_chest",
            "family_id": "direct_chest",
            "movement_pattern": "horizontal_press",
            "primary_muscles": ["chest"],
            "secondary_muscles": ["triceps"],
            "equipment_tags": ["machine"],
            "fatigue_cost": "low",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["high"],
        },
        "secondary_chest": {
            "exercise_id": "secondary_chest",
            "family_id": "secondary_chest",
            "movement_pattern": "vertical_press",
            "primary_muscles": ["triceps"],
            "secondary_muscles": ["chest"],
            "equipment_tags": ["cable"],
            "fatigue_cost": "low",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["moderate"],
        },
    }

    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="weak_point_slot",
        candidate_ids=["secondary_chest", "direct_chest"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=2,
        target_exercises_per_session=4,
        target_weak_point_muscles=["chest"],
    )

    assert result is not None
    assert result.selected_id == "direct_chest"
    assert result.selection_trace.dimension_scores["weak_point_alignment"] > result.selection_trace.top_candidates[1].dimension_scores["weak_point_alignment"]


def test_optional_fill_scoring_stops_when_best_candidate_fails_score_floor() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("novice_gym_full_body")
    record_by_id = {
        "bad_fill_a": {
            "exercise_id": "bad_fill_a",
            "family_id": "bad_fill_a",
            "movement_pattern": "accessory",
            "primary_muscles": [],
            "secondary_muscles": [],
            "equipment_tags": ["barbell", "cable", "machine"],
            "fatigue_cost": "high",
            "skill_demand": "high",
            "stability_demand": "high",
            "progression_compatibility": ["low"],
        },
        "bad_fill_b": {
            "exercise_id": "bad_fill_b",
            "family_id": "bad_fill_b",
            "movement_pattern": "core",
            "primary_muscles": [],
            "secondary_muscles": [],
            "equipment_tags": ["barbell", "cable", "machine"],
            "fatigue_cost": "high",
            "skill_demand": "high",
            "stability_demand": "high",
            "progression_compatibility": ["low"],
        },
    }

    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["bad_fill_a", "bad_fill_b"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=3,
        target_exercises_per_session=4,
        target_weak_point_muscles=[item.muscle_group for item in assessment.weak_point_priorities],
    )

    assert result is not None
    assert result.score_floor == 6
    assert result.cleared_score_floor is False
    assert result.total_score < result.score_floor


def test_scoring_tie_break_prefers_lower_weekly_assignment_count_then_lexical_id() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("low_time_full_body")
    base_record = {
        "movement_pattern": "curl",
        "primary_muscles": ["biceps"],
        "secondary_muscles": [],
        "equipment_tags": ["cable"],
        "fatigue_cost": "low",
        "skill_demand": "low",
        "stability_demand": "low",
        "progression_compatibility": ["moderate"],
    }
    record_by_id = {
        "alpha_curl": {"exercise_id": "alpha_curl", "family_id": "alpha_curl", **base_record},
        "beta_curl": {"exercise_id": "beta_curl", "family_id": "beta_curl", **base_record},
    }

    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["beta_curl", "alpha_curl"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={"beta_curl": 1, "alpha_curl": 0},
        weekly_selected_exercise_ids=[],
        session_exercise_count=2,
        target_exercises_per_session=4,
        target_weak_point_muscles=[],
    )

    assert result is not None
    assert result.selected_id == "alpha_curl"


def test_missing_scoring_metadata_resolves_to_neutral_defaults_and_is_traced() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("novice_gym_full_body")
    record_by_id = {
        "neutral_fill": {
            "exercise_id": "neutral_fill",
            "family_id": "neutral_fill",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": None,
            "skill_demand": None,
            "stability_demand": None,
            "progression_compatibility": [],
        },
    }

    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["neutral_fill"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=2,
        target_exercises_per_session=4,
        target_weak_point_muscles=[],
    )

    assert result is not None
    assert result.selection_trace.dimension_scores["recoverability_fit"] == 0
    assert result.selection_trace.dimension_scores["complexity_fit"] == 0
    assert result.selection_trace.dimension_scores["progression_fit"] == 0
    assert set(result.selection_trace.metadata_defaults_used) == {
        "fatigue_cost",
        "skill_demand",
        "stability_demand",
        "progression_compatibility",
    }


def test_optional_fill_scoring_prefers_weak_point_primary_alignment_when_available() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("novice_gym_full_body")
    record_by_id = {
        "direct_chest_fill": {
            "exercise_id": "direct_chest_fill",
            "family_id": "direct_chest_fill",
            "movement_pattern": "horizontal_press",
            "primary_muscles": ["chest"],
            "secondary_muscles": ["triceps"],
            "equipment_tags": ["machine"],
            "fatigue_cost": "low",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["moderate"],
        },
        "non_target_fill": {
            "exercise_id": "non_target_fill",
            "family_id": "non_target_fill",
            "movement_pattern": "core",
            "primary_muscles": ["abs"],
            "secondary_muscles": [],
            "equipment_tags": ["machine"],
            "fatigue_cost": "low",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["moderate"],
        },
    }

    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["non_target_fill", "direct_chest_fill"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=2,
        target_exercises_per_session=4,
        target_weak_point_muscles=["chest"],
    )

    assert result is not None
    assert result.selected_id == "direct_chest_fill"


def test_optional_fill_scoring_shifts_toward_lower_fatigue_when_week_is_already_high_fatigue() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("novice_gym_full_body")
    record_by_id = {
        "low_fatigue_fill": {
            "exercise_id": "low_fatigue_fill",
            "family_id": "low_fatigue_fill",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "low",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["moderate"],
        },
        "high_fatigue_fill": {
            "exercise_id": "high_fatigue_fill",
            "family_id": "high_fatigue_fill",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "high",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["moderate"],
        },
        "week_hi_1": {
            "exercise_id": "week_hi_1",
            "family_id": "week_hi_1",
            "movement_pattern": "squat",
            "primary_muscles": ["quads"],
            "secondary_muscles": [],
            "equipment_tags": ["barbell"],
            "fatigue_cost": "high",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
        "week_hi_2": {
            "exercise_id": "week_hi_2",
            "family_id": "week_hi_2",
            "movement_pattern": "hinge",
            "primary_muscles": ["hamstrings"],
            "secondary_muscles": [],
            "equipment_tags": ["barbell"],
            "fatigue_cost": "high",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
    }

    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["high_fatigue_fill", "low_fatigue_fill"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=["week_hi_1", "week_hi_2"],
        session_exercise_count=2,
        target_exercises_per_session=4,
        target_weak_point_muscles=[],
    )

    assert result is not None
    assert result.selected_id == "low_fatigue_fill"


def test_optional_fill_scoring_late_session_prefers_lower_complexity_candidate() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("novice_gym_full_body")
    record_by_id = {
        "simple_fill": {
            "exercise_id": "simple_fill",
            "family_id": "simple_fill",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "low",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["moderate"],
        },
        "complex_fill": {
            "exercise_id": "complex_fill",
            "family_id": "complex_fill",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "low",
            "skill_demand": "high",
            "stability_demand": "high",
            "progression_compatibility": ["moderate"],
        },
    }

    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["complex_fill", "simple_fill"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=3,
        target_exercises_per_session=4,
        target_weak_point_muscles=[],
    )

    assert result is not None
    assert result.selected_id == "simple_fill"


def test_optional_fill_penalizes_overused_weekly_movement_pattern_for_variety() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("novice_gym_full_body")
    record_by_id = {
        "curl_fill": {
            "exercise_id": "curl_fill",
            "family_id": "curl_fill",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "low",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["moderate"],
        },
        "triceps_fill": {
            "exercise_id": "triceps_fill",
            "family_id": "triceps_fill",
            "movement_pattern": "triceps_extension",
            "primary_muscles": ["triceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "low",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["moderate"],
        },
        "week_curl_1": {
            "exercise_id": "week_curl_1",
            "family_id": "week_curl_1",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "low",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["moderate"],
        },
        "week_curl_2": {
            "exercise_id": "week_curl_2",
            "family_id": "week_curl_2",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "low",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["moderate"],
        },
    }

    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["curl_fill", "triceps_fill"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=["week_curl_1", "week_curl_2"],
        session_exercise_count=2,
        target_exercises_per_session=4,
        target_weak_point_muscles=[],
    )

    assert result is not None
    assert result.selected_id == "triceps_fill"

def test_metadata_off_preserves_prior_winner_behavior() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("low_recovery_full_body")
    record_by_id = {
        "press_machine": {
            "exercise_id": "press_machine",
            "family_id": "press_machine",
            "movement_pattern": "horizontal_press",
            "primary_muscles": ["chest", "triceps"],
            "secondary_muscles": ["front_delts"],
            "equipment_tags": ["machine"],
            "fatigue_cost": "moderate",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["high"],
        },
        "press_unstable": {
            "exercise_id": "press_unstable",
            "family_id": "press_unstable",
            "movement_pattern": "horizontal_press",
            "primary_muscles": ["chest", "triceps"],
            "secondary_muscles": ["front_delts"],
            "equipment_tags": ["dumbbell"],
            "fatigue_cost": "high",
            "skill_demand": "high",
            "stability_demand": "high",
            "progression_compatibility": ["moderate"],
        },
    }
    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="required_slot",
        candidate_ids=["press_machine", "press_unstable"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=0,
        target_exercises_per_session=4,
        target_movement_pattern="horizontal_press",
        target_weak_point_muscles=[],
        metadata_v2_by_exercise_id=None,
    )
    assert result is not None
    assert result.selected_id == "press_machine"
    assert result.selection_trace.metadata_v2_used_for_scoring is False


def test_metadata_on_scoring_is_deterministic() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("low_time_full_body")
    record_by_id = {
        "a": {
            "exercise_id": "a",
            "family_id": "fa",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "moderate",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
        "b": {
            "exercise_id": "b",
            "family_id": "fb",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "moderate",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
    }
    metadata = {
        "a": _metadata_stub(setup="low", rest="short", systemic="low", local="low"),
        "b": _metadata_stub(setup="high", rest="long", systemic="high", local="high"),
    }
    first = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["a", "b"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=3,
        target_exercises_per_session=4,
        target_weak_point_muscles=[],
        metadata_v2_by_exercise_id=metadata,
    )
    second = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["a", "b"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=3,
        target_exercises_per_session=4,
        target_weak_point_muscles=[],
        metadata_v2_by_exercise_id=metadata,
    )
    assert first is not None and second is not None
    assert first.selected_id == second.selected_id
    assert first.selection_trace.total_score == second.selection_trace.total_score


def test_low_time_prefers_lower_setup_and_rest_when_candidates_are_comparable() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("low_time_full_body")
    record_by_id = {
        "fast": {
            "exercise_id": "fast",
            "family_id": "f_fast",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "moderate",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
        "slow": {
            "exercise_id": "slow",
            "family_id": "f_slow",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "moderate",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
    }
    metadata = {
        "fast": _metadata_stub(setup="low", rest="short"),
        "slow": _metadata_stub(setup="high", rest="long"),
    }
    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["slow", "fast"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=3,
        target_exercises_per_session=4,
        target_weak_point_muscles=[],
        metadata_v2_by_exercise_id=metadata,
    )
    assert result is not None
    assert result.selected_id == "fast"
    assert result.selection_trace.metadata_v2_used_for_time_efficiency is True


def test_low_recovery_prefers_lower_systemic_fatigue_when_candidates_are_comparable() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("low_recovery_full_body")
    record_by_id = {
        "recovery_easy": {
            "exercise_id": "recovery_easy",
            "family_id": "r_easy",
            "movement_pattern": "horizontal_press",
            "primary_muscles": ["chest"],
            "secondary_muscles": ["triceps"],
            "equipment_tags": ["machine"],
            "fatigue_cost": "moderate",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
        "recovery_hard": {
            "exercise_id": "recovery_hard",
            "family_id": "r_hard",
            "movement_pattern": "horizontal_press",
            "primary_muscles": ["chest"],
            "secondary_muscles": ["triceps"],
            "equipment_tags": ["machine"],
            "fatigue_cost": "moderate",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
    }
    metadata = {
        "recovery_easy": _metadata_stub(systemic="low", local="low"),
        "recovery_hard": _metadata_stub(systemic="high", local="high"),
    }
    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="required_slot",
        candidate_ids=["recovery_hard", "recovery_easy"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=0,
        target_exercises_per_session=4,
        target_movement_pattern="horizontal_press",
        target_weak_point_muscles=[],
        metadata_v2_by_exercise_id=metadata,
    )
    assert result is not None
    assert result.selected_id == "recovery_easy"
    assert result.selection_trace.metadata_v2_used_for_recovery is True


def test_required_slot_prefers_primary_secondary_role_over_tertiary_when_comparable() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("novice_gym_full_body")
    record_by_id = {
        "slot_primary": {
            "exercise_id": "slot_primary",
            "family_id": "sp",
            "movement_pattern": "horizontal_press",
            "primary_muscles": ["chest"],
            "secondary_muscles": ["triceps"],
            "equipment_tags": ["machine"],
            "fatigue_cost": "moderate",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
        "slot_tertiary": {
            "exercise_id": "slot_tertiary",
            "family_id": "st",
            "movement_pattern": "horizontal_press",
            "primary_muscles": ["chest"],
            "secondary_muscles": ["triceps"],
            "equipment_tags": ["machine"],
            "fatigue_cost": "moderate",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
    }
    metadata = {
        "slot_primary": _metadata_stub(role="primary", tags=["primary"]),
        "slot_tertiary": _metadata_stub(role="tertiary", tags=["tertiary"]),
    }
    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="required_slot",
        candidate_ids=["slot_tertiary", "slot_primary"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=0,
        target_exercises_per_session=4,
        target_movement_pattern="horizontal_press",
        target_weak_point_muscles=[],
        metadata_v2_by_exercise_id=metadata,
    )
    assert result is not None
    assert result.selected_id == "slot_primary"
    assert result.selection_trace.metadata_v2_used_for_role_fit is True


def test_late_optional_fill_prefers_tertiary_pump_role_when_comparable() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("low_time_full_body")
    record_by_id = {
        "late_tertiary": {
            "exercise_id": "late_tertiary",
            "family_id": "lt",
            "movement_pattern": "lateral_raise",
            "primary_muscles": ["side_delts"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "low",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["moderate"],
        },
        "late_primary": {
            "exercise_id": "late_primary",
            "family_id": "lp",
            "movement_pattern": "lateral_raise",
            "primary_muscles": ["side_delts"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "low",
            "skill_demand": "low",
            "stability_demand": "low",
            "progression_compatibility": ["moderate"],
        },
    }
    metadata = {
        "late_tertiary": _metadata_stub(role="tertiary", tags=["pump_metabolic"]),
        "late_primary": _metadata_stub(role="primary", tags=["primary"]),
    }
    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["late_primary", "late_tertiary"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=3,
        target_exercises_per_session=4,
        target_weak_point_muscles=[],
        metadata_v2_by_exercise_id=metadata,
    )
    assert result is not None
    assert result.selected_id == "late_tertiary"


def test_optional_fill_avoids_repeated_overlap_bottleneck_when_comparable() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("novice_gym_full_body")
    record_by_id = {
        "candidate_press": {
            "exercise_id": "candidate_press",
            "family_id": "cp",
            "movement_pattern": "horizontal_press",
            "primary_muscles": ["chest"],
            "secondary_muscles": ["triceps"],
            "equipment_tags": ["machine"],
            "fatigue_cost": "moderate",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
        "candidate_neutral": {
            "exercise_id": "candidate_neutral",
            "family_id": "cn",
            "movement_pattern": "chest_fly",
            "primary_muscles": ["chest"],
            "secondary_muscles": [],
            "equipment_tags": ["machine"],
            "fatigue_cost": "moderate",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
        "week_press": {
            "exercise_id": "week_press",
            "family_id": "wp",
            "movement_pattern": "horizontal_press",
            "primary_muscles": ["chest"],
            "secondary_muscles": ["triceps"],
            "equipment_tags": ["machine"],
            "fatigue_cost": "moderate",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        },
    }
    metadata = {
        "candidate_press": _metadata_stub(overlap={"pressing_overlap": True, "triceps_overlap": True}),
        "candidate_neutral": _metadata_stub(overlap={"pressing_overlap": False, "triceps_overlap": False}),
        "week_press": _metadata_stub(overlap={"pressing_overlap": True, "triceps_overlap": True}),
    }
    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["candidate_press", "candidate_neutral"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=["week_press"],
        session_exercise_count=2,
        target_exercises_per_session=4,
        target_weak_point_muscles=[],
        metadata_v2_by_exercise_id=metadata,
    )
    assert result is not None
    assert result.selected_id == "candidate_neutral"
    assert result.selection_trace.metadata_v2_used_for_overlap is True


def test_metadata_scoring_fallback_count_increments_when_fields_missing() -> None:
    doctrine_bundle, assessment, blueprint = _assessment_and_blueprint("low_time_full_body")
    record_by_id = {
        "fallback_test": {
            "exercise_id": "fallback_test",
            "family_id": "ft",
            "movement_pattern": "curl",
            "primary_muscles": ["biceps"],
            "secondary_muscles": [],
            "equipment_tags": ["cable"],
            "fatigue_cost": "moderate",
            "skill_demand": "moderate",
            "stability_demand": "moderate",
            "progression_compatibility": ["moderate"],
        }
    }
    partial_metadata = {
        "fallback_test": SimpleNamespace(
            fatigue=None,
            time_efficiency=None,
            role=None,
            skill_stability_safety=None,
            overlap=None,
        )
    }
    result = select_scored_candidate(
        doctrine_bundle=doctrine_bundle,
        selection_mode="optional_fill",
        candidate_ids=["fallback_test"],
        record_by_id=record_by_id,
        assessment=assessment,
        blueprint_input=blueprint,
        assigned_counts={},
        weekly_selected_exercise_ids=[],
        session_exercise_count=3,
        target_exercises_per_session=4,
        target_weak_point_muscles=[],
        metadata_v2_by_exercise_id=partial_metadata,
    )
    assert result is not None
    assert result.selection_trace.metadata_v2_used_for_scoring is True
    assert result.selection_trace.metadata_v2_scoring_fallback_count >= 4
