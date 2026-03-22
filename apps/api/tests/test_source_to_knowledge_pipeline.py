import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importers.source_to_knowledge_pipeline import build_compiled_knowledge


def test_source_to_knowledge_pipeline_writes_expected_artifacts(tmp_path: Path) -> None:
    guides_dir = tmp_path / "docs" / "guides"
    guides_dir.mkdir(parents=True)
    asset_catalog_path = guides_dir / "asset_catalog.json"
    provenance_index_path = guides_dir / "provenance_index.json"
    asset_catalog_path.write_text(
        json.dumps(
            {
                "aggregate_signature": "asset-signature",
                "assets": [
                    {
                        "asset_path": "reference/Program Sheet.xlsx",
                        "asset_sha256": "a" * 64,
                        "asset_type": "xlsx",
                        "derived_doc": "docs/guides/generated/program-sheet.md",
                    },
                    {
                        "asset_path": "reference/Program Manual.pdf",
                        "asset_sha256": "b" * 64,
                        "asset_type": "pdf",
                        "derived_doc": "docs/guides/generated/program-manual.md",
                    },
                ],
                "workbook_pdf_pairs": [
                    {
                        "workbook_asset_path": "reference/Program Sheet.xlsx",
                        "guide_asset_path": "reference/Program Manual.pdf",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    provenance_index_path.write_text(
        json.dumps(
            {
                "aggregate_signature": "provenance-signature",
                "provenance": [
                    {
                        "asset": "reference/Program Sheet.xlsx",
                        "derived_entities": [{"path": "docs/guides/generated/program-sheet.md"}],
                    },
                    {
                        "asset": "reference/Program Manual.pdf",
                        "derived_entities": [{"path": "docs/guides/generated/program-manual.md"}],
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "knowledge" / "compiled"
    doctrine_resolutions_path = tmp_path / "knowledge" / "curation" / "doctrine_bundles" / "multi_source_hypertrophy_v1.resolutions.json"
    doctrine_resolutions_path.parent.mkdir(parents=True, exist_ok=True)
    doctrine_resolutions_path.write_text(
        json.dumps({"bundle_id": "multi_source_hypertrophy_v1", "version": "0.1.0", "resolutions": []}, indent=2),
        encoding="utf-8",
    )
    doctrine_unresolved_path = tmp_path / "knowledge" / "curation" / "doctrine_bundles" / "multi_source_hypertrophy_v1.unresolved.json"
    exercise_resolutions_path = tmp_path / "knowledge" / "curation" / "exercise_library_extraction.resolutions.json"
    exercise_resolutions_path.parent.mkdir(parents=True, exist_ok=True)
    exercise_resolutions_path.write_text(
        json.dumps({"bundle_id": "exercise_library_extraction", "version": "0.1.0", "resolutions": []}, indent=2),
        encoding="utf-8",
    )
    exercise_unresolved_path = tmp_path / "knowledge" / "curation" / "exercise_library_extraction.unresolved.json"
    manifest = build_compiled_knowledge(
        asset_catalog_path=asset_catalog_path,
        provenance_index_path=provenance_index_path,
        overrides_path=REPO_ROOT / "knowledge" / "curation" / "source_registry_overrides.json",
        onboarding_dir=REPO_ROOT / "programs" / "gold",
        exercise_library_overrides_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_overrides.json",
        doctrine_seed_path=REPO_ROOT / "knowledge" / "curation" / "doctrine_bundles" / "multi_source_hypertrophy_v1.seed.json",
        policy_seed_path=REPO_ROOT / "knowledge" / "curation" / "policy_bundles" / "system_coaching_policy_v1.seed.json",
        output_dir=output_dir,
        exercise_library_extraction_resolutions_path=exercise_resolutions_path,
        exercise_library_extraction_unresolved_output_path=exercise_unresolved_path,
        doctrine_resolutions_path=doctrine_resolutions_path,
        doctrine_unresolved_output_path=doctrine_unresolved_path,
    )

    assert manifest.bundle_id == "build_manifest"
    assert manifest.artifacts
    assert (output_dir / "source_registry.v1.json").exists()
    assert (output_dir / "exercise_library.foundation.v1.json").exists()
    assert (output_dir / "doctrine_bundles" / "multi_source_hypertrophy_v1.bundle.json").exists()
    assert (output_dir / "policy_bundles" / "system_coaching_policy_v1.bundle.json").exists()
    assert (output_dir / "build_manifest.v1.json").exists()
    assert doctrine_unresolved_path.exists()
    assert exercise_unresolved_path.exists()

    policy_payload = json.loads(
        (output_dir / "policy_bundles" / "system_coaching_policy_v1.bundle.json").read_text(encoding="utf-8")
    )
    doctrine_payload = json.loads(
        (output_dir / "doctrine_bundles" / "multi_source_hypertrophy_v1.bundle.json").read_text(encoding="utf-8")
    )
    assert policy_payload["constraint_resolution_policy"]["resolution_order"] == [
        "safety",
        "recoverability",
        "day_and_time_feasibility",
        "adherence_and_skill_feasibility",
        "locked_user_constraints_when_feasible",
        "active_specialization_priority",
        "hypertrophy_ideality",
        "variety_and_preference_refinement",
    ]
    assert policy_payload["minimum_viable_program_policy"]["fallback_order"] == [
        "reduce_exercise_variety",
        "reduce_optional_work",
        "reduce_frequency_before_violating_hard_constraints",
    ]
    assert {
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
        "full_body_equipment_and_restriction_filtering_v1",
        "full_body_slot_role_sequence_v1",
        "full_body_exercise_reuse_limits_v1",
        "full_body_weak_point_slot_insertion_v1",
        "full_body_initial_rep_ranges_by_slot_role_and_pattern_v1",
        "full_body_rep_adjustments_by_exercise_demand_v1",
        "full_body_start_weight_initialization_v1",
    } <= {
        rule["rule_id"]
        for module_rules in doctrine_payload["rules_by_module"].values()
        for rule in module_rules
    }
    required_rule = next(
        rule
        for module_rules in doctrine_payload["rules_by_module"].values()
        for rule in module_rules
        if rule["rule_id"] == "full_body_required_movement_patterns_v1"
    )
    assert required_rule["status"] == "curated"
    assert required_rule["provenance"]
    assert {
        "respect_session_time_budget",
        "do_not_replay_single_authored_layout",
    } <= {item["constraint_id"] for item in policy_payload["hard_constraints"]}
    assert policy_payload["generated_full_body_adaptive_loop_policy"]["policy_id"] == "generated_full_body_adaptive_loop_v1"
    assert policy_payload["generated_full_body_adaptive_loop_policy"]["minimum_axis_persistence_weeks"] == 2
    assert policy_payload["generated_full_body_adaptive_loop_policy"]["max_primary_axes_per_week"] == 1
    assert policy_payload["generated_full_body_adaptive_loop_policy"]["max_volume_targets_per_week"] == 2
    assert policy_payload["generated_full_body_adaptive_loop_policy"]["max_load_targets_per_week"] == 2
    assert policy_payload["generated_full_body_block_review_policy"]["policy_id"] == "generated_full_body_block_review_v1"
    assert policy_payload["generated_full_body_block_review_policy"]["minimum_generated_weeks_for_block_review"] == 3
    assert policy_payload["generated_full_body_block_review_policy"]["minimum_review_window_weeks"] == 3
    assert policy_payload["generated_full_body_block_review_policy"]["block_reset_resets_adaptive_persistence"] is True
    assert {
        "prefer_full_body_when_generated_split_unspecified",
        "prefer_simple_options_for_novice_and_comeback",
        "prefer_recoverable_options_for_low_recovery",
        "prefer_adherence_first_for_inconsistent_schedule",
    } <= {item["preference_id"] for item in policy_payload["soft_preferences"]}
    required_patterns = [
        item["movement_pattern"]
        for item in next(
            rule
            for rule in doctrine_payload["rules_by_module"]["exercise_selection"]
            if rule["rule_id"] == "full_body_required_movement_patterns_v1"
        )["payload"]["requirements"]
    ]
    library_payload = json.loads((output_dir / "exercise_library.foundation.v1.json").read_text(encoding="utf-8"))
    available_patterns = {record["movement_pattern"] for record in library_payload["records"] if record.get("movement_pattern")}
    records_by_id = {record["exercise_id"]: record for record in library_payload["records"]}
    assert set(required_patterns) <= available_patterns
    barbell_rdl = records_by_id["barbell_rdl"]
    assert barbell_rdl["fatigue_cost"] == "high"
    assert any(ref["source_id"] == "curated-exercise-library-override-v1" for ref in barbell_rdl["provenance"])
    assert any(
        ref.get("section_ref") == "exercise_intelligence_extraction:barbell_rdl:fatigue_cost"
        for ref in barbell_rdl["provenance"]
    )
    assert records_by_id["belt_squat"]["skill_demand"] == "moderate"
    assert records_by_id["belt_squat"]["stability_demand"] == "moderate"
    assert records_by_id["bent_over_cable_pec_flye"]["skill_demand"] == "moderate"
    assert records_by_id["bent_over_cable_pec_flye"]["stability_demand"] == "moderate"
    assert records_by_id["bottom_half_ez_bar_preacher_curl"]["skill_demand"] == "low"
    assert records_by_id["bottom_half_ez_bar_preacher_curl"]["stability_demand"] == "low"
    distributed_patterns = [
        pattern
        for session_rules in next(
            rule
            for rule in doctrine_payload["rules_by_module"]["exercise_selection"]
            if rule["rule_id"] == "full_body_movement_pattern_distribution_v1"
        )["payload"]["distribution_by_session_count"].values()
        for session in session_rules
        for pattern in session["movement_patterns"]
    ]
    assert set(distributed_patterns) <= available_patterns
    optional_fill_patterns = [
        pattern
        for patterns in next(
            rule
            for rule in doctrine_payload["rules_by_module"]["exercise_selection"]
            if rule["rule_id"] == "full_body_optional_fill_pattern_priority_by_complexity_ceiling_v1"
        )["payload"]["optional_patterns_by_complexity_ceiling"].values()
        for pattern in patterns
    ]
    assert set(optional_fill_patterns) <= available_patterns
    weak_point_payload = next(
        rule
        for rule in doctrine_payload["rules_by_module"]["exercise_selection"]
        if rule["rule_id"] == "full_body_weak_point_slot_insertion_v1"
    )["payload"]
    assert "volume_tier_to_max_weekly_weak_point_slots" in weak_point_payload
    assert "minimum_remaining_capacity_inclusive" in weak_point_payload

    second = build_compiled_knowledge(
        asset_catalog_path=asset_catalog_path,
        provenance_index_path=provenance_index_path,
        overrides_path=REPO_ROOT / "knowledge" / "curation" / "source_registry_overrides.json",
        onboarding_dir=REPO_ROOT / "programs" / "gold",
        exercise_library_overrides_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_overrides.json",
        doctrine_seed_path=REPO_ROOT / "knowledge" / "curation" / "doctrine_bundles" / "multi_source_hypertrophy_v1.seed.json",
        policy_seed_path=REPO_ROOT / "knowledge" / "curation" / "policy_bundles" / "system_coaching_policy_v1.seed.json",
        output_dir=output_dir,
        exercise_library_extraction_resolutions_path=exercise_resolutions_path,
        exercise_library_extraction_unresolved_output_path=exercise_unresolved_path,
        doctrine_resolutions_path=doctrine_resolutions_path,
        doctrine_unresolved_output_path=doctrine_unresolved_path,
    )
    assert manifest.model_dump(mode="json") == second.model_dump(mode="json")
