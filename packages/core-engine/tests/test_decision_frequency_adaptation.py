from core_engine.decision_frequency_adaptation import (
    apply_active_frequency_adaptation_runtime,
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
