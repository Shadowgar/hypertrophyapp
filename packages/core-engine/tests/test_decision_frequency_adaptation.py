from core_engine.decision_frequency_adaptation import (
    apply_active_frequency_adaptation_runtime,
    prepare_frequency_adaptation_route_runtime,
    recommend_frequency_adaptation_preview,
    resolve_active_frequency_adaptation_runtime,
)


def test_frequency_adaptation_preview_module_emits_structured_trace() -> None:
    onboarding_package = {
        "frequency_adaptation_rules": {
            "default_training_days": 4,
            "minimum_temporary_days": 2,
            "max_temporary_weeks": 4,
            "weak_area_bonus_slots": 2,
            "preserve_slot_roles": ["anchor"],
            "reduce_slot_roles_first": ["optional"],
            "daily_slot_cap_when_compressed": 8,
            "coverage_targets": [{"muscle_group": "chest", "minimum_weekly_slots": 2}],
            "reintegration_policy": "stepwise_return_after_temporary_window",
        },
        "blueprint": {
            "program_id": "adaptive_full_body_v1",
            "week_templates": [
                {
                    "week_template_id": "wk1",
                    "days": [
                        {
                            "day_id": "d1",
                            "label": "Day 1",
                            "slots": [
                                {
                                    "slot_id": "s1",
                                    "movement_pattern": "horizontal_press",
                                    "primary_muscles": ["chest"],
                                    "role": "anchor",
                                }
                            ],
                        }
                    ],
                }
            ],
            "week_sequence": ["wk1"],
        },
    }

    preview = recommend_frequency_adaptation_preview(
        onboarding_package=onboarding_package,
        program_id="adaptive_full_body_v1",
        current_days=4,
        target_days=3,
        duration_weeks=2,
        explicit_weak_areas=["chest"],
        stored_weak_areas=None,
        equipment_profile=["dumbbell"],
        recovery_state="normal",
        current_week_index=1,
    )

    assert preview["decision_trace"]["interpreter"] == "recommend_frequency_adaptation_preview"
    assert preview["decision_trace"]["outcome"]["reason_code"] == "preview_generated"


def test_active_frequency_adaptation_runtime_apply_decrements_week_counter() -> None:
    active = resolve_active_frequency_adaptation_runtime(
        active_state={"template_id": "full_body_v1", "target_days": 3, "weeks_remaining": 2, "duration_weeks": 2},
        selected_template_id="full_body_v1",
    )
    assert active is not None

    runtime = apply_active_frequency_adaptation_runtime(
        plan={"week_start": "2026-03-16"},
        selected_template_id="full_body_v1",
        active_frequency_adaptation=active,
    )

    assert runtime["state_updated"] is True
    assert runtime["next_state"]["weeks_remaining"] == 1
    assert runtime["plan"]["applied_frequency_adaptation"]["decision_trace"]["interpreter"] == "apply_active_frequency_adaptation_runtime"


def test_prepare_frequency_adaptation_route_runtime_preview_shapes_payload_and_trace() -> None:
    adaptation_runtime = {
        "program_id": "adaptive_full_body_v1",
        "current_days": 4,
        "target_days": 3,
        "duration_weeks": 2,
        "explicit_weak_areas": ["chest"],
        "stored_weak_areas": [],
        "equipment_profile": ["dumbbell"],
        "recovery_state": "normal",
        "current_week_index": 1,
        "decision_trace": {"interpreter": "prepare_frequency_adaptation_runtime_inputs"},
    }
    onboarding_package = {
        "frequency_adaptation_rules": {
            "default_training_days": 4,
            "minimum_temporary_days": 2,
            "max_temporary_weeks": 4,
            "weak_area_bonus_slots": 2,
            "preserve_slot_roles": ["anchor"],
            "reduce_slot_roles_first": ["optional"],
            "daily_slot_cap_when_compressed": 8,
            "coverage_targets": [{"muscle_group": "chest", "minimum_weekly_slots": 2}],
            "reintegration_policy": "stepwise_return_after_temporary_window",
        },
        "blueprint": {
            "program_id": "adaptive_full_body_v1",
            "week_templates": [
                {
                    "week_template_id": "wk1",
                    "days": [
                        {
                            "day_id": "d1",
                            "label": "Day 1",
                            "slots": [{"slot_id": "s1", "movement_pattern": "horizontal_press", "primary_muscles": ["chest"], "role": "anchor"}],
                        }
                    ],
                }
            ],
            "week_sequence": ["wk1"],
        },
    }

    runtime = prepare_frequency_adaptation_route_runtime(
        adaptation_runtime=adaptation_runtime,
        onboarding_package=onboarding_package,
        decision_kind="preview",
    )

    assert runtime["decision_kind"] == "preview"
    assert runtime["preview_payload"]["decision_trace"]["interpreter"] == "recommend_frequency_adaptation_preview"
    assert runtime["preview_payload"]["decision_trace"]["request_runtime_trace"]["interpreter"] == "prepare_frequency_adaptation_runtime_inputs"
    assert runtime["decision_trace"]["interpreter"] == "prepare_frequency_adaptation_route_runtime"


def test_prepare_frequency_adaptation_route_runtime_apply_builds_response_and_persistence() -> None:
    adaptation_runtime = {
        "program_id": "adaptive_full_body_v1",
        "current_days": 4,
        "target_days": 3,
        "duration_weeks": 2,
        "explicit_weak_areas": [],
        "stored_weak_areas": ["chest"],
        "equipment_profile": ["dumbbell"],
        "recovery_state": "normal",
        "current_week_index": 1,
        "decision_trace": {"interpreter": "prepare_frequency_adaptation_runtime_inputs"},
    }
    onboarding_package = {
        "frequency_adaptation_rules": {
            "default_training_days": 4,
            "minimum_temporary_days": 2,
            "max_temporary_weeks": 4,
            "weak_area_bonus_slots": 2,
            "preserve_slot_roles": ["anchor"],
            "reduce_slot_roles_first": ["optional"],
            "daily_slot_cap_when_compressed": 8,
            "coverage_targets": [{"muscle_group": "chest", "minimum_weekly_slots": 2}],
            "reintegration_policy": "stepwise_return_after_temporary_window",
        },
        "blueprint": {
            "program_id": "adaptive_full_body_v1",
            "week_templates": [
                {
                    "week_template_id": "wk1",
                    "days": [
                        {
                            "day_id": "d1",
                            "label": "Day 1",
                            "slots": [{"slot_id": "s1", "movement_pattern": "horizontal_press", "primary_muscles": ["chest"], "role": "anchor"}],
                        }
                    ],
                }
            ],
            "week_sequence": ["wk1"],
        },
    }

    runtime = prepare_frequency_adaptation_route_runtime(
        adaptation_runtime=adaptation_runtime,
        onboarding_package=onboarding_package,
        decision_kind="apply",
        applied_at="2026-03-09T12:00:00",
    )

    assert runtime["decision_kind"] == "apply"
    assert runtime["response_payload"]["status"] == "applied"
    assert runtime["persistence_state"]["weeks_remaining"] == 2
    assert runtime["response_payload"]["decision_trace"]["interpreter"] == "interpret_frequency_adaptation_apply"


def test_phase1_full_body_preview_emits_program_specific_5_to_3_policy_trace() -> None:
    onboarding_package = {
        "program_id": "pure_bodybuilding_phase_1_full_body",
        "frequency_adaptation_rules": {
            "default_training_days": 5,
            "minimum_temporary_days": 3,
            "max_temporary_weeks": 2,
            "weak_area_bonus_slots": 1,
            "preserve_slot_roles": ["primary_compound", "secondary_compound", "weak_point"],
            "reduce_slot_roles_first": ["isolation", "accessory"],
            "daily_slot_cap_when_compressed": 8,
            "reintegration_policy": "Return to original 5-day template at next week boundary; keep progression state from compressed weeks.",
        },
        "blueprint": {
            "program_id": "pure_bodybuilding_phase_1_full_body",
            "default_training_days": 5,
            "week_sequence": ["week_1"],
            "week_templates": [
                {
                    "week_template_id": "week_1",
                    "week_label": "Week 1",
                    "block_label": "BLOCK 1: 5-WEEK BUILD PHASE",
                    "special_banners": ["Mandatory Rest Day", "Mandatory Rest Day"],
                    "days": [
                        {
                            "day_id": "d1",
                            "day_name": "Full Body #1",
                            "day_role": "full_body_1",
                            "slots": [
                                {"slot_id": "d1s1", "exercise_id": "press_a", "slot_role": "primary_compound", "primary_muscles": ["chest"]},
                            ],
                        },
                        {
                            "day_id": "d2",
                            "day_name": "Full Body #2",
                            "day_role": "full_body_2",
                            "slots": [
                                {"slot_id": "d2s1", "exercise_id": "hinge_a", "slot_role": "secondary_compound", "primary_muscles": ["hamstrings"]},
                            ],
                        },
                        {
                            "day_id": "d3",
                            "day_name": "Full Body #3",
                            "day_role": "full_body_3",
                            "slots": [
                                {"slot_id": "d3s1", "exercise_id": "pull_a", "slot_role": "primary_compound", "primary_muscles": ["back"]},
                            ],
                        },
                        {
                            "day_id": "d4",
                            "day_name": "Full Body #4",
                            "day_role": "full_body_4",
                            "slots": [
                                {"slot_id": "d4s1", "exercise_id": "squat_a", "slot_role": "primary_compound", "primary_muscles": ["quads"]},
                            ],
                        },
                        {
                            "day_id": "d5",
                            "day_name": "Arms & Weak Points",
                            "day_role": "weak_point_arms",
                            "slots": [
                                {"slot_id": "d5s1", "exercise_id": "weak_a", "slot_role": "weak_point", "primary_muscles": ["biceps"]},
                            ],
                        },
                    ],
                }
            ],
        },
    }

    preview = recommend_frequency_adaptation_preview(
        onboarding_package=onboarding_package,
        program_id="pure_bodybuilding_phase_1_full_body",
        current_days=5,
        target_days=3,
        duration_weeks=1,
        explicit_weak_areas=["biceps"],
        stored_weak_areas=[],
        equipment_profile=["cable", "machine"],
        recovery_state="normal",
        current_week_index=1,
    )

    week = preview["weeks"][0]
    assert week["program_policy"] == "pure_bodybuilding_phase_1_full_body_5_to_3"
    assert week["week_label"] == "Week 1"
    assert week["block_label"] == "BLOCK 1: 5-WEEK BUILD PHASE"
    assert week["special_banners"] == ["Mandatory Rest Day", "Mandatory Rest Day"]
    assert week["action_summary"] == {"combine": 2, "preserve": 3}
    assert week["adapted_days"][0]["day_name"] == "Full Body #1 + Full Body #2"
    assert week["adapted_days"][0]["source_day_names"] == ["Full Body #1", "Full Body #2"]
    assert week["adapted_days"][2]["day_name"] == "Arms & Weak Points"
    assert week["adapted_days"][2]["source_day_roles"] == ["weak_point_arms"]

    outcome = preview["decision_trace"]["outcome"]
    assert outcome["policy_mode"] == "program_specific"
    assert outcome["policy_id"] == "pure_bodybuilding_phase_1_full_body_5_to_3"
    assert outcome["preservation_focus"] == [
        "full_body_intent",
        "weak_point_intent",
        "progression_continuity",
    ]
