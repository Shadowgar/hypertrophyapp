import pytest

import core_engine
from core_engine.rules_runtime import (
    evaluate_deload_signal,
    extract_fatigue_rpe_threshold,
    extract_intro_weeks,
    resolve_equipment_substitution,
    resolve_repeat_failure_substitution,
    resolve_adaptive_rule_runtime,
    resolve_scheduler_deload_runtime,
    resolve_scheduler_exercise_adjustment_runtime,
    resolve_scheduler_exercise_muscles_runtime,
    resolve_scheduler_mesocycle_runtime,
    resolve_scheduler_muscle_coverage_runtime,
    resolve_progression_rule_runtime,
    resolve_scheduler_session_exercise_cap,
    resolve_scheduler_session_selection,
    resolve_starting_load,
    resolve_substitution_rule_runtime,
)


def _scheduler_rule_set() -> dict[str, object]:
    return {
        "progression_rules": {
            "on_success": {"percent": 2.5},
            "on_under_target": {"reduce_percent": 2.5, "after_exposures": 2},
        },
        "fatigue_rules": {
            "high_fatigue_trigger": {
                "conditions": ["session_rpe_avg >= 9", "under_target_exposures >= 2"]
            },
            "on_high_fatigue": {"action": "reduce_volume", "set_delta": -1},
        },
        "deload_rules": {
            "scheduled_every_n_weeks": 6,
            "early_deload_trigger": "three_consecutive_under_target_sessions",
            "on_deload": {"set_reduction_percent": 35, "load_reduction_percent": 10},
        },
        "substitution_rules": {
            "equipment_mismatch": "use_first_compatible_substitution",
            "repeat_failure_trigger": "switch_after_three_failed_exposures",
        },
        "generated_week_scheduler_rules": {
            "mesocycle": {
                "sequence_completion_phase_transition_reason": "authored_sequence_complete",
                "post_authored_sequence_behavior": "hold_last_authored_week",
                "soreness_deload_trigger": {
                    "minimum_severe_count": 2,
                    "reason": "early_soreness",
                },
                "adherence_deload_trigger": {
                    "maximum_score": 2,
                    "reason": "early_adherence",
                },
                "stimulus_fatigue_deload_trigger": {
                    "deload_pressure": "high",
                    "recoverability": "low",
                    "reason": "early_sfr_recovery",
                },
            },
            "exercise_adjustment": {
                "policies": [
                    {
                        "policy_id": "high_fatigue_reduce_load_and_sets",
                        "match_policy": "all",
                        "conditions": {
                            "minimum_fatigue_score": 0.8,
                            "last_progression_actions": ["reduce_load"],
                        },
                        "adjustment": {
                            "load_scale": 0.95,
                            "set_delta": -1,
                            "substitution_pressure": "high",
                            "substitution_guidance": (
                                "prefer_compatible_variants_if_recovery_constraints_persist"
                            ),
                        },
                    },
                    {
                        "policy_id": "moderate_recovery_pressure",
                        "match_policy": "any",
                        "conditions": {
                            "minimum_fatigue_score": 0.7,
                            "minimum_consecutive_under_target_exposures": 2,
                            "last_progression_actions": ["reduce_load"],
                        },
                        "adjustment": {
                            "load_scale": 0.95,
                            "set_delta": 0,
                            "substitution_pressure": "moderate",
                            "substitution_guidance": (
                                "compatible_variants_available_if_recovery_constraints_persist"
                            ),
                        },
                    },
                ],
                "default_adjustment": {
                    "load_scale": 1.0,
                    "set_delta": 0,
                    "substitution_pressure": "low",
                    "substitution_guidance": None,
                },
                "substitution_pressure_guidance": {
                    "moderate": "compatible_variants_available_if_recovery_constraints_persist",
                    "high": "prefer_compatible_variants_if_recovery_constraints_persist",
                },
            },
            "session_selection": {
                "recent_history_exercise_limit": 6,
                "anchor_first_session_when_day_roles_present": True,
                "required_day_roles_when_compressed": ["weak_point_arms"],
                "structural_slot_role_priority": {
                    "weak_point": 120,
                    "primary_compound": 110,
                    "secondary_compound": 80,
                },
                "day_role_priority": {
                    "weak_point_arms": 100,
                    "full_body_1": 80,
                    "full_body_2": 80,
                    "full_body_3": 80,
                    "full_body_4": 80,
                },
                "missed_day_policy": "roll-forward-priority-lifts",
            },
            "session_exercise_cap": {
                "time_budget_thresholds": [
                    {"maximum_minutes": 30, "exercise_limit": 3},
                    {"maximum_minutes": 45, "exercise_limit": 4},
                    {"maximum_minutes": 60, "exercise_limit": 5},
                ],
                "default_slot_role_priority": {
                    "primary_compound": 100,
                    "weak_point": 90,
                    "secondary_compound": 80,
                    "accessory": 50,
                    "isolation": 40,
                },
                "day_role_slot_role_priority_overrides": {
                    "weak_point_arms": {
                        "weak_point": 120,
                        "primary_compound": 30,
                        "secondary_compound": 20,
                    }
                },
            },
            "muscle_coverage": {
                "tracked_muscles": [
                    "chest",
                    "back",
                    "quads",
                    "hamstrings",
                    "glutes",
                    "shoulders",
                    "biceps",
                    "triceps",
                    "calves",
                ],
                "minimum_sets_per_muscle": 2,
                "authored_label_normalization": {
                    "chest": "chest",
                    "pec": "chest",
                    "pecs": "chest",
                    "back": "back",
                    "lats": "back",
                    "lat": "back",
                    "mid_back": "back",
                    "upper_back": "back",
                    "erectors": "back",
                    "quads": "quads",
                    "quadriceps": "quads",
                    "hamstrings": "hamstrings",
                    "glutes": "glutes",
                    "shoulders": "shoulders",
                    "delts": "shoulders",
                    "front_delts": "shoulders",
                    "rear_delts": "shoulders",
                    "side_delts": "shoulders",
                    "biceps": "biceps",
                    "triceps": "triceps",
                    "calves": "calves",
                },
            },
        },
    }


def test_resolve_progression_rule_runtime_uses_rule_overrides() -> None:
    runtime = resolve_progression_rule_runtime(
        {
            "progression_rules": {
                "on_success": {"percent": 5},
                "on_under_target": {"reduce_percent": 3, "after_exposures": 2},
            }
        }
    )

    assert runtime == {
        "increase_percent": 5.0,
        "reduce_percent": 3.0,
        "reduce_after_exposures": 2,
    }


def test_resolve_starting_load_uses_estimated_1rm_fallback_when_available() -> None:
    runtime = resolve_starting_load(
        planned_exercise={"estimated_1rm": 155.0},
        fallback_weight=90.0,
        rule_set={
            "starting_load_rules": {
                "method": "rep_range_rir_start",
                "default_rir_target": 2,
                "fallback_percent_estimated_1rm": 72,
            }
        },
    )

    assert runtime["working_weight"] == pytest.approx(111.5)
    assert runtime["decision_trace"]["interpreter"] == "resolve_starting_load"
    assert runtime["decision_trace"]["outcome"] == {
        "working_weight": 111.5,
        "source": "estimated_1rm_fallback_percent",
    }


def test_resolve_starting_load_falls_back_to_planned_weight_without_estimated_1rm() -> None:
    runtime = resolve_starting_load(
        planned_exercise={"recommended_working_weight": 95.0},
        fallback_weight=95.0,
        rule_set={
            "starting_load_rules": {
                "method": "rep_range_rir_start",
                "default_rir_target": 2,
                "fallback_percent_estimated_1rm": 72,
            }
        },
    )

    assert runtime["working_weight"] == pytest.approx(95.0)
    assert runtime["decision_trace"]["outcome"] == {
        "working_weight": 95.0,
        "source": "planned_weight",
    }


def test_resolve_adaptive_rule_runtime_extracts_fatigue_and_deload_config() -> None:
    runtime = resolve_adaptive_rule_runtime(
        {
            "progression_rules": {
                "on_success": {"percent": 5},
                "on_under_target": {"reduce_percent": 3, "after_exposures": 2},
            },
            "fatigue_rules": {
                "high_fatigue_trigger": {
                    "conditions": [
                        "intro phase lasts 2 weeks; avoid interpreting early underperformance as stall",
                        "session_rpe_avg >= 9 for two exposures",
                    ]
                },
                "on_high_fatigue": {"action": "reduce_volume", "set_delta": -1},
            },
            "deload_rules": {
                "scheduled_every_n_weeks": 6,
                "early_deload_trigger": "repeated_under_target_plus_high_fatigue",
                "on_deload": {"set_reduction_percent": 35, "load_reduction_percent": 10},
            },
            "rationale_templates": {
                "increase_load": "increase",
                "hold_load": "hold",
                "deload": "deload",
            },
        }
    )

    assert runtime["fatigue_rpe_threshold"] == pytest.approx(9.0)
    assert runtime["intro_weeks"] == 2
    assert runtime["scheduled_deload_weeks"] == 6
    assert runtime["early_deload_trigger"] == "repeated_under_target_plus_high_fatigue"
    assert runtime["deload_load_scale"] == pytest.approx(0.9)


def test_resolve_scheduler_mesocycle_runtime_does_not_invent_cut_deload_cadence() -> None:
    runtime = resolve_scheduler_mesocycle_runtime(
        template_deload={"trigger_weeks": 6},
        prior_generated_weeks=4,
        latest_adherence_score=None,
        severe_soreness_count=0,
        authored_week_index=None,
        authored_week_role=None,
        authored_sequence_length=None,
        authored_sequence_complete=False,
        stimulus_fatigue_response=None,
        phase="cut",
        rule_set=None,
    )

    assert runtime["trigger_weeks_effective"] == 6
    assert runtime["week_index"] == 5
    assert runtime["decision_trace"]["interpreter"] == "resolve_scheduler_mesocycle_runtime"
    assert runtime["decision_trace"]["outcome"]["trigger_weeks_source"] == "template.deload.trigger_weeks"


def test_extract_rule_threshold_helpers_parse_conditions() -> None:
    rule_set = {
        "fatigue_rules": {
            "high_fatigue_trigger": {
                "conditions": [
                    "intro phase lasts 3 weeks; avoid interpreting early underperformance as stall",
                    "session_rpe_avg >= 8.5 for two exposures",
                ]
            }
        }
    }

    assert extract_intro_weeks(rule_set) == 3
    assert extract_fatigue_rpe_threshold(rule_set) == pytest.approx(8.5)


def test_evaluate_deload_signal_matches_rule_based_underperformance_and_high_fatigue() -> None:
    signal = evaluate_deload_signal(
        completion_pct=92,
        adherence_score=4,
        soreness_rank=2,
        average_rpe=9.1,
        consecutive_underperformance_weeks=2,
        rule_set={
            "progression_rules": {
                "on_under_target": {"after_exposures": 2},
            },
            "fatigue_rules": {
                "high_fatigue_trigger": {
                    "conditions": ["session_rpe_avg >= 9 for two exposures"]
                }
            },
            "deload_rules": {
                "early_deload_trigger": "repeated_under_target_plus_high_fatigue"
            },
        },
    )

    assert signal["high_fatigue"] is True
    assert signal["underperformance_deload_matched"] is True
    assert signal["forced_deload_reasons"] == []


def test_evaluate_deload_signal_matches_three_consecutive_under_target_trigger_without_high_fatigue() -> None:
    signal = evaluate_deload_signal(
        completion_pct=92,
        adherence_score=4,
        soreness_rank=1,
        average_rpe=7.0,
        consecutive_underperformance_weeks=3,
        rule_set={
            "progression_rules": {
                "on_under_target": {"after_exposures": 2},
            },
            "fatigue_rules": {
                "high_fatigue_trigger": {
                    "conditions": ["session_rpe_avg >= 9 for two exposures"]
                }
            },
            "deload_rules": {
                "early_deload_trigger": "three_consecutive_under_target_sessions"
            },
        },
    )

    assert signal["high_fatigue"] is False
    assert signal["underperformance_deload_matched"] is True


def test_evaluate_deload_signal_collects_forced_deload_reasons() -> None:
    signal = evaluate_deload_signal(
        completion_pct=65,
        adherence_score=2,
        soreness_rank=3,
        rule_set=None,
    )

    assert signal["forced_deload_reasons"] == ["low_completion", "low_adherence", "high_soreness"]


def test_resolve_substitution_rule_runtime_extracts_repeat_failure_threshold() -> None:
    runtime = resolve_substitution_rule_runtime(
        {
            "substitution_rules": {
                "equipment_mismatch": "use_first_compatible_substitution",
                "repeat_failure_trigger": "switch_after_three_failed_exposures",
            }
        }
    )

    assert runtime["equipment_mismatch_strategy"] == "use_first_compatible_substitution"
    assert runtime["repeat_failure_threshold"] == 3


def test_resolve_substitution_rule_runtime_extracts_numeric_repeat_failure_threshold() -> None:
    runtime = resolve_substitution_rule_runtime(
        {
            "substitution_rules": {
                "equipment_mismatch": "use_first_compatible_substitution",
                "repeat_failure_trigger": "switch_after_2_failed_exposures",
            }
        }
    )

    assert runtime["repeat_failure_threshold"] == 2


def test_resolve_substitution_rule_runtime_defaults_repeat_failure_threshold() -> None:
    runtime = resolve_substitution_rule_runtime(None)

    assert runtime["equipment_mismatch_strategy"] == "use_first_compatible_substitution"
    assert runtime["repeat_failure_threshold"] == 3


def test_resolve_scheduler_exercise_adjustment_runtime_carries_named_owner_trace() -> None:
    runtime = resolve_scheduler_exercise_adjustment_runtime(
        progression_state={
            "exercise_id": "incline_press",
            "consecutive_under_target_exposures": 2,
            "last_progression_action": "reduce_load",
            "fatigue_score": 0.85,
        },
        stimulus_substitution_pressure="moderate",
        rule_set=_scheduler_rule_set(),
    )

    assert runtime["set_delta"] == -1
    assert runtime["load_scale"] == pytest.approx(0.95)
    assert runtime["substitution_pressure"] == "high"
    assert runtime["substitution_guidance"] == "prefer_compatible_variants_if_recovery_constraints_persist"
    assert runtime["decision_trace"]["interpreter"] == "resolve_scheduler_exercise_adjustment_runtime"
    assert runtime["decision_trace"]["outcome"]["merged_substitution_pressure"] == "high"


def test_resolve_scheduler_session_selection_returns_named_missed_day_policy_trace() -> None:
    selection = resolve_scheduler_session_selection(
        session_profiles=[
            {
                "index": 0,
                "day_role": "full_body_1",
                "primary_exercise_ids": ["lat"],
                "muscles": ["back"],
                "slot_roles": ["primary_compound"],
            },
            {
                "index": 1,
                "day_role": "full_body_2",
                "primary_exercise_ids": ["rdl"],
                "muscles": ["hamstrings"],
                "slot_roles": ["primary_compound"],
            },
            {
                "index": 2,
                "day_role": "weak_point_arms",
                "primary_exercise_ids": ["weak_chest"],
                "muscles": ["chest"],
                "slot_roles": ["weak_point"],
            },
        ],
        history=[],
        days_available=2,
        rule_set=_scheduler_rule_set(),
    )

    assert selection["selected_indices"] == [0, 2]
    assert selection["missed_day_policy"] == "roll-forward-priority-lifts"
    assert selection["decision_trace"]["interpreter"] == "resolve_scheduler_session_selection"
    assert selection["decision_trace"]["outcome"]["required_session_indices"] == [0, 2]


def test_resolve_scheduler_mesocycle_runtime_uses_canonical_early_deload_triggers() -> None:
    runtime = resolve_scheduler_mesocycle_runtime(
        template_deload={"trigger_weeks": 6},
        prior_generated_weeks=1,
        latest_adherence_score=2,
        severe_soreness_count=2,
        authored_week_index=10,
        authored_week_role="intensification",
        authored_sequence_length=10,
        authored_sequence_complete=True,
        stimulus_fatigue_response={
            "deload_pressure": "high",
            "recoverability": "low",
        },
        stimulus_fatigue_response_source="derived_from_training_state_inputs",
        phase="maintenance",
        rule_set=_scheduler_rule_set(),
    )

    assert runtime["is_deload_week"] is True
    assert runtime["deload_reason"] == "early_soreness+early_adherence+early_sfr_recovery"
    assert runtime["phase_transition_reason"] == "authored_sequence_complete"
    assert runtime["post_authored_behavior"] == "hold_last_authored_week"
    assert runtime["decision_trace"]["inputs"]["stimulus_fatigue_response_source"] == "derived_from_training_state_inputs"
    assert runtime["decision_trace"]["outcome"]["stimulus_fatigue_response_source"] == (
        "derived_from_training_state_inputs"
    )


def test_resolve_scheduler_session_exercise_cap_uses_canonical_time_budget_rules() -> None:
    runtime = resolve_scheduler_session_exercise_cap(
        session_time_budget_minutes=30,
        day_role="weak_point_arms",
        slot_roles=["primary_compound", "weak_point", "isolation", "weak_point"],
        rule_set=_scheduler_rule_set(),
    )

    assert runtime["exercise_limit"] == 3
    assert runtime["kept_indices"] == [1, 2, 3]
    assert runtime["selected_threshold"] == {"maximum_minutes": 30, "exercise_limit": 3}
    assert runtime["decision_trace"]["steps"][0]["decision"] == "resolve_time_budget_threshold"
    assert runtime["decision_trace"]["outcome"]["selected_threshold"] == {
        "maximum_minutes": 30,
        "exercise_limit": 3,
    }


def test_resolve_scheduler_muscle_coverage_runtime_uses_canonical_contract() -> None:
    runtime = resolve_scheduler_muscle_coverage_runtime(rule_set=_scheduler_rule_set())

    assert runtime["tracked_muscles"] == [
        "chest",
        "back",
        "quads",
        "hamstrings",
        "glutes",
        "shoulders",
        "biceps",
        "triceps",
        "calves",
    ]
    assert runtime["minimum_sets_per_muscle"] == 2
    assert runtime["decision_trace"]["interpreter"] == "resolve_scheduler_muscle_coverage_runtime"


def test_resolve_scheduler_muscle_coverage_runtime_falls_back_to_canonical_contract_when_missing() -> None:
    runtime = resolve_scheduler_muscle_coverage_runtime(
        rule_set={
            "generated_week_scheduler_rules": {
                "mesocycle": _scheduler_rule_set()["generated_week_scheduler_rules"]["mesocycle"],
            }
        }
    )

    assert runtime["tracked_muscles"] == [
        "chest",
        "back",
        "quads",
        "hamstrings",
        "glutes",
        "shoulders",
        "biceps",
        "triceps",
        "calves",
    ]
    assert runtime["minimum_sets_per_muscle"] == 2
    assert runtime["authored_label_normalization"]["lats"] == "back"
    assert runtime["decision_trace"]["inputs"]["has_scheduler_rule_contract"] is False
    assert runtime["decision_trace"]["inputs"]["fallback_applied"] is True


def test_resolve_scheduler_exercise_muscles_runtime_normalizes_only_explicit_authored_metadata() -> None:
    muscle_coverage_runtime = resolve_scheduler_muscle_coverage_runtime(rule_set=_scheduler_rule_set())
    runtime = resolve_scheduler_exercise_muscles_runtime(
        exercise={
            "name": "Lat Raise Pec Deck",
            "primary_muscles": ["lats", "mid_back"],
            "secondary_muscles": ["rear_delts", "biceps"],
        },
        muscle_coverage_runtime=muscle_coverage_runtime,
    )

    assert runtime["normalized_muscles"] == ["back", "biceps", "shoulders"]
    assert runtime["decision_trace"]["outcome"]["input_source"] == "explicit_authored_muscle_metadata"


def test_resolve_scheduler_exercise_muscles_runtime_does_not_infer_from_tokens_without_authored_metadata() -> None:
    muscle_coverage_runtime = resolve_scheduler_muscle_coverage_runtime(rule_set=_scheduler_rule_set())
    runtime = resolve_scheduler_exercise_muscles_runtime(
        exercise={
            "name": "Lat Raise Pec Deck",
        },
        muscle_coverage_runtime=muscle_coverage_runtime,
    )

    assert runtime["normalized_muscles"] == []
    assert runtime["decision_trace"]["outcome"]["input_source"] == "no_explicit_authored_muscle_metadata"


def test_resolve_scheduler_exercise_muscles_runtime_can_consume_pre_resolved_coverage_runtime() -> None:
    muscle_coverage_runtime = resolve_scheduler_muscle_coverage_runtime(rule_set=_scheduler_rule_set())

    runtime = resolve_scheduler_exercise_muscles_runtime(
        exercise={
            "id": "row",
            "primary_muscles": ["lats"],
            "secondary_muscles": ["biceps"],
        },
        muscle_coverage_runtime=muscle_coverage_runtime,
    )

    assert runtime["normalized_muscles"] == ["back", "biceps"]


def test_resolve_scheduler_deload_runtime_returns_bounded_noop_without_authoritative_policy() -> None:
    runtime = resolve_scheduler_deload_runtime(
        template_deload={"trigger_weeks": 6},
        is_deload_week=True,
        mesocycle_decision_trace={"interpreter": "resolve_scheduler_mesocycle_runtime"},
        rule_set={
            "generated_week_scheduler_rules": _scheduler_rule_set()["generated_week_scheduler_rules"],
        },
    )

    assert runtime["active"] is True
    assert runtime["set_reduction_pct"] == 0
    assert runtime["load_reduction_pct"] == 0
    assert runtime["decision_trace"]["outcome"]["source"] == "bounded_non_authoritative_noop"


def test_core_engine_exports_scheduler_runtime_ownership_helpers() -> None:
    assert hasattr(core_engine, "resolve_scheduler_deload_runtime")
    assert hasattr(core_engine, "resolve_scheduler_exercise_muscles_runtime")
    assert hasattr(core_engine, "resolve_scheduler_muscle_coverage_runtime")


def test_resolve_equipment_substitution_chooses_first_compatible_candidate() -> None:
    result = resolve_equipment_substitution(
        exercise_id="barbell_row",
        exercise_name="Barbell Row",
        exercise_equipment_tags=["barbell"],
        substitution_candidates=["Cable Row", "DB Row"],
        equipment_set={"dumbbell"},
        rule_set={
            "substitution_rules": {
                "equipment_mismatch": "use_first_compatible_substitution",
                "repeat_failure_trigger": "switch_after_three_failed_exposures",
            }
        },
    )

    assert result["compatible_substitutions"] == ["DB Row"]
    assert result["selected_name"] == "DB Row"
    assert result["auto_substituted"] is True
    assert result["decision_trace"]["interpreter"] == "resolve_equipment_substitution"


def test_resolve_repeat_failure_substitution_recommends_compatible_alternative_after_threshold() -> None:
    result = resolve_repeat_failure_substitution(
        exercise_id="lat_cable_row",
        exercise_name="Lat-Focused Cable Row",
        substitution_candidates=["Chest Supported Row", "1-Arm Cable Row"],
        consecutive_under_target_exposures=3,
        equipment_set={"cable", "dumbbell", "machine"},
        rule_set={
            "substitution_rules": {
                "equipment_mismatch": "use_first_compatible_substitution",
                "repeat_failure_trigger": "switch_after_three_failed_exposures",
            }
        },
    )

    assert result["recommend_substitution"] is True
    assert result["recommended_name"] == "Chest Supported Row"
    assert result["decision_trace"]["interpreter"] == "resolve_repeat_failure_substitution"


def test_resolve_equipment_substitution_filters_restricted_candidates() -> None:
    result = resolve_equipment_substitution(
        exercise_id="press",
        exercise_name="Overhead Press",
        exercise_equipment_tags=["dumbbell"],
        substitution_candidates=["Landmine Press", "Lateral Raise"],
        equipment_set={"dumbbell"},
        rule_set={"substitution_rules": {"equipment_mismatch": "use_first_compatible_substitution"}},
        movement_restrictions={"overhead_pressing"},
        candidate_movement_patterns={
            "Landmine Press": "vertical_press",
            "Lateral Raise": "lateral_raise",
        },
    )

    assert result["compatible_substitutions"] == ["Lateral Raise"]
    assert "Landmine Press" in result["decision_trace"]["outcome"]["restricted_substitutions"]
    assert result["decision_trace"]["outcome"]["metadata_confidence"]["confidence"] == "high"


def test_resolve_repeat_failure_substitution_skips_restricted_candidates() -> None:
    result = resolve_repeat_failure_substitution(
        exercise_id="press",
        exercise_name="Overhead Press",
        substitution_candidates=["Landmine Press", "Lateral Raise"],
        consecutive_under_target_exposures=3,
        equipment_set={"dumbbell"},
        rule_set={"substitution_rules": {"repeat_failure_trigger": "switch_after_three_failed_exposures"}},
        movement_restrictions={"overhead_pressing"},
        candidate_movement_patterns={
            "Landmine Press": "vertical_press",
            "Lateral Raise": "lateral_raise",
        },
    )

    assert result["recommended_name"] == "Lateral Raise"
    assert "Landmine Press" in result["decision_trace"]["outcome"]["restricted_substitutions"]


def test_resolve_repeat_failure_substitution_allows_sparse_metadata_candidates() -> None:
    result = resolve_repeat_failure_substitution(
        exercise_id="press",
        exercise_name="Press",
        substitution_candidates=["Unknown Press"],
        consecutive_under_target_exposures=3,
        equipment_set={"machine"},
        rule_set={"substitution_rules": {"repeat_failure_trigger": "switch_after_three_failed_exposures"}},
        movement_restrictions=set(),
        candidate_movement_patterns={},
    )

    assert result["recommended_name"] == "Unknown Press"
    assert result["decision_trace"]["outcome"]["restricted_substitutions"] == []
    assert result["decision_trace"]["outcome"]["metadata_confidence"]["confidence"] == "low"
    assert result["decision_trace"]["outcome"]["metadata_confidence"]["policy"] == "allow_with_warning"


def test_resolve_equipment_substitution_marks_partial_metadata_confidence() -> None:
    result = resolve_equipment_substitution(
        exercise_id="row",
        exercise_name="Row",
        exercise_equipment_tags=["machine"],
        substitution_candidates=["Machine Row", "Unknown Option"],
        equipment_set={"machine"},
        rule_set={"substitution_rules": {"equipment_mismatch": "use_first_compatible_substitution"}},
        movement_restrictions={"deep_knee_flexion"},
        candidate_movement_patterns={
            "Machine Row": "horizontal_pull",
        },
    )

    confidence = result["decision_trace"]["outcome"]["metadata_confidence"]
    assert confidence["confidence"] == "partial"
    assert confidence["missing_movement_pattern_candidates"] == ["Unknown Option"]


def test_resolve_equipment_substitution_denies_missing_restriction_metadata_when_restrictions_active() -> None:
    result = resolve_equipment_substitution(
        exercise_id="press",
        exercise_name="Overhead Press",
        exercise_equipment_tags=["barbell"],
        substitution_candidates=["Unknown Press"],
        equipment_set={"machine"},
        rule_set={"substitution_rules": {"equipment_mismatch": "use_first_compatible_substitution"}},
        movement_restrictions={"overhead_pressing"},
        candidate_movement_patterns={},
    )

    assert result["compatible_substitutions"] == []
    outcome = result["decision_trace"]["outcome"]
    assert outcome["denied_due_to_missing_restriction_metadata"] == ["Unknown Press"]
    assert outcome["safe_drop_due_to_no_restriction_safe_candidate"] is True


def test_resolve_repeat_failure_substitution_safe_drop_when_all_candidates_not_restriction_safe() -> None:
    result = resolve_repeat_failure_substitution(
        exercise_id="press",
        exercise_name="Overhead Press",
        substitution_candidates=["Landmine Press", "Unknown Press"],
        consecutive_under_target_exposures=3,
        equipment_set={"dumbbell", "machine"},
        rule_set={"substitution_rules": {"repeat_failure_trigger": "switch_after_three_failed_exposures"}},
        movement_restrictions={"overhead_pressing"},
        candidate_movement_patterns={"Landmine Press": "vertical_press"},
    )

    outcome = result["decision_trace"]["outcome"]
    assert result["recommended_name"] is None
    assert "Landmine Press" in outcome["restricted_substitutions"]
    assert "Unknown Press" in outcome["denied_due_to_missing_restriction_metadata"]
    assert outcome["safe_drop_due_to_no_restriction_safe_candidate"] is True


def test_resolve_equipment_substitution_keeps_sparse_permissive_behavior_without_restrictions() -> None:
    result = resolve_equipment_substitution(
        exercise_id="press",
        exercise_name="Barbell Press",
        exercise_equipment_tags=["barbell"],
        substitution_candidates=["Unknown Press"],
        equipment_set={"machine"},
        rule_set={"substitution_rules": {"equipment_mismatch": "use_first_compatible_substitution"}},
        movement_restrictions=set(),
        candidate_movement_patterns={},
    )

    assert result["selected_name"] == "Unknown Press"
    assert result["auto_substituted"] is True
    outcome = result["decision_trace"]["outcome"]
    assert outcome["denied_due_to_missing_restriction_metadata"] == []
    assert outcome["safe_drop_due_to_no_restriction_safe_candidate"] is False
