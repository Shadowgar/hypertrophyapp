from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.knowledge_loader import load_doctrine_bundle, load_exercise_library, load_policy_bundle


REQUIRED_DOCTRINE_RULE_IDS = {
    "assessment_experience_thresholds_v1",
    "assessment_recovery_profile_mapping_v1",
    "assessment_schedule_profile_mapping_v1",
    "assessment_comeback_detection_v1",
    "assessment_weak_point_merge_v1",
    "split_full_body_supported_days_v1",
    "full_body_session_topology_by_session_count_v1",
    "full_body_day_role_sequence_by_session_count_v1",
    "full_body_session_cap_by_time_budget_v1",
    "full_body_volume_tier_by_user_class_v1",
    "full_body_session_fill_target_by_volume_tier_v1",
    "full_body_initial_sets_by_slot_role_and_volume_tier_v1",
    "full_body_set_adjustments_by_user_state_v1",
    "full_body_day_role_prescription_emphasis_v1",
    "full_body_required_movement_patterns_v1",
    "full_body_movement_pattern_distribution_v1",
    "full_body_candidate_sorting_v1",
    "full_body_candidate_scoring_v1",
    "full_body_optional_fill_pattern_priority_by_complexity_ceiling_v1",
    "full_body_slot_role_sequence_v1",
    "full_body_equipment_and_restriction_filtering_v1",
    "full_body_exercise_reuse_limits_v1",
    "full_body_weak_point_slot_insertion_v1",
    "full_body_initial_rep_ranges_by_slot_role_and_pattern_v1",
    "full_body_rep_adjustments_by_exercise_demand_v1",
    "full_body_start_weight_initialization_v1",
}

REQUIRED_POLICY_HARD_IDS = {
    "respect_session_time_budget",
    "do_not_replay_single_authored_layout",
}

REQUIRED_POLICY_SOFT_IDS = {
    "prefer_full_body_when_generated_split_unspecified",
    "prefer_simple_options_for_novice_and_comeback",
    "prefer_recoverable_options_for_low_recovery",
    "prefer_adherence_first_for_inconsistent_schedule",
}


def test_generated_full_body_doctrine_contract_is_present_and_library_compatible() -> None:
    compiled_dir = REPO_ROOT / "knowledge" / "compiled"
    doctrine_bundle = load_doctrine_bundle("multi_source_hypertrophy_v1", compiled_dir)
    policy_bundle = load_policy_bundle("system_coaching_policy_v1", compiled_dir)
    exercise_library = load_exercise_library(compiled_dir)

    rules = {rule.rule_id: rule for module_rules in doctrine_bundle.rules_by_module.values() for rule in module_rules}
    assert REQUIRED_DOCTRINE_RULE_IDS <= set(rules)

    assert {"novice", "advanced", "fallback"} <= set(rules["assessment_experience_thresholds_v1"].payload)
    assert {"low_recovery_when", "fallback"} <= set(rules["assessment_recovery_profile_mapping_v1"].payload)
    assert {"low_time", "inconsistent_schedule", "fallback"} <= set(rules["assessment_schedule_profile_mapping_v1"].payload)
    assert {"requires_prior_generated_weeks", "minimum_performance_history_entries_for_non_comeback"} <= set(
        rules["assessment_comeback_detection_v1"].payload
    )
    assert {"source_priority", "maximum_priorities"} <= set(rules["assessment_weak_point_merge_v1"].payload)
    assert {"supported_days", "default_when_split_unspecified"} <= set(rules["split_full_body_supported_days_v1"].payload)
    assert "topology_by_session_count" in rules["full_body_session_topology_by_session_count_v1"].payload
    assert "day_roles_by_session_count" in rules["full_body_day_role_sequence_by_session_count_v1"].payload
    assert "tiers" in rules["full_body_session_cap_by_time_budget_v1"].payload
    assert "user_class_to_volume_tier" in rules["full_body_volume_tier_by_user_class_v1"].payload
    assert "volume_tier_to_target_exercises_per_session" in rules["full_body_session_fill_target_by_volume_tier_v1"].payload
    assert "base_sets_by_selection_mode" in rules["full_body_initial_sets_by_slot_role_and_volume_tier_v1"].payload
    assert {"user_flag_set_deltas", "schedule_profile_set_deltas", "minimum_sets_by_slot_role", "maximum_sets_by_slot_role"} <= set(
        rules["full_body_set_adjustments_by_user_state_v1"].payload
    )
    assert "emphasis_by_day_role" in rules["full_body_day_role_prescription_emphasis_v1"].payload
    assert "requirements" in rules["full_body_required_movement_patterns_v1"].payload
    assert "distribution_by_session_count" in rules["full_body_movement_pattern_distribution_v1"].payload
    assert "sort_order" in rules["full_body_candidate_sorting_v1"].payload
    assert {"dimension_bands", "dimension_weights", "minimum_total_score_floor", "tie_break_order"} <= set(
        rules["full_body_candidate_scoring_v1"].payload
    )
    assert set(rules["full_body_candidate_scoring_v1"].payload["dimension_weights"]) == {
        "required_slot",
        "weak_point_slot",
        "optional_fill",
    }
    assert rules["full_body_candidate_scoring_v1"].payload["minimum_total_score_floor"]["optional_fill"] == 6
    assert rules["full_body_candidate_scoring_v1"].payload["tie_break_order"] == [
        "total_score_desc",
        "stimulus_fit_desc",
        "weak_point_alignment_desc",
        "recoverability_fit_desc",
        "progression_fit_desc",
        "weekly_assignment_count_asc",
        "exercise_id_asc",
    ]
    assert "optional_patterns_by_complexity_ceiling" in rules["full_body_optional_fill_pattern_priority_by_complexity_ceiling_v1"].payload
    assert {"slot_roles_by_position", "slot_role_by_movement_pattern"} <= set(rules["full_body_slot_role_sequence_v1"].payload)
    assert {"equipment_filter_mode", "restriction_filter_mode", "ignore_missing_contraindications"} <= set(
        rules["full_body_equipment_and_restriction_filtering_v1"].payload
    )
    assert {"max_assignments_per_exercise_per_week", "allow_reuse_after_unique_candidates_exhausted"} <= set(
        rules["full_body_exercise_reuse_limits_v1"].payload
    )
    assert {
        "max_weekly_weak_point_slots",
        "volume_tier_to_max_weekly_weak_point_slots",
        "minimum_remaining_capacity_inclusive",
        "preferred_session_indices_by_session_count",
        "slot_role",
    } <= set(
        rules["full_body_weak_point_slot_insertion_v1"].payload
    )
    assert {
        "base_rep_ranges_by_selection_mode",
        "volume_tier_rep_shift",
        "schedule_profile_rep_shift",
        "user_flag_rep_shift",
        "minimum_rep",
        "maximum_rep",
    } <= set(
        rules["full_body_initial_rep_ranges_by_slot_role_and_pattern_v1"].payload
    )
    assert {
        "fatigue_cost_rep_shift",
        "skill_demand_rep_shift",
        "stability_demand_rep_shift",
        "progression_compatibility_rep_shift",
        "maximum_total_positive_shift",
    } <= set(
        rules["full_body_rep_adjustments_by_exercise_demand_v1"].payload
    )
    assert {
        "history_source",
        "exact_match_field",
        "prohibit_cross_exercise_inference",
        "fallback_method",
    } <= set(
        rules["full_body_start_weight_initialization_v1"].payload
    )
    assert rules["full_body_start_weight_initialization_v1"].payload["history_source"] == "exact_exercise_id_match"
    assert rules["full_body_start_weight_initialization_v1"].payload["prohibit_cross_exercise_inference"] is True

    available_patterns = {record.movement_pattern for record in exercise_library.records if record.movement_pattern}
    required_patterns = {
        item["movement_pattern"] for item in rules["full_body_required_movement_patterns_v1"].payload["requirements"]
    }
    assert required_patterns <= available_patterns
    distributed_patterns = {
        pattern
        for item in rules["full_body_movement_pattern_distribution_v1"].payload["distribution_by_session_count"].values()
        for session in item
        for pattern in session["movement_patterns"]
    }
    assert distributed_patterns <= available_patterns
    optional_fill_patterns = {
        pattern
        for patterns in rules["full_body_optional_fill_pattern_priority_by_complexity_ceiling_v1"].payload[
            "optional_patterns_by_complexity_ceiling"
        ].values()
        for pattern in patterns
    }
    assert optional_fill_patterns <= available_patterns

    hard_constraint_ids = {item.constraint_id for item in policy_bundle.hard_constraints}
    soft_preference_ids = {item.preference_id for item in policy_bundle.soft_preferences}
    assert REQUIRED_POLICY_HARD_IDS <= hard_constraint_ids
    assert REQUIRED_POLICY_SOFT_IDS <= soft_preference_ids
