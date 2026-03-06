from core_engine import adapt_onboarding_frequency


def _sample_onboarding_package() -> dict:
    return {
        "program_id": "pure_bodybuilding_phase_1_full_body",
        "frequency_adaptation_rules": {
            "default_training_days": 5,
            "minimum_temporary_days": 2,
            "max_temporary_weeks": 4,
            "preserve_slot_roles": ["primary_compound", "secondary_compound", "weak_point"],
            "reduce_slot_roles_first": ["isolation", "accessory"],
            "daily_slot_cap_when_compressed": 10,
            "reintegration_policy": "Rejoin authored week order after temporary constraint period.",
        },
        "blueprint": {
            "default_training_days": 5,
            "week_sequence": ["week_base"] * 10,
            "week_templates": [
                {
                    "week_template_id": "week_base",
                    "days": [
                        {
                            "day_id": "d1",
                            "slots": [
                                {"exercise_id": "bench_press", "slot_role": "primary_compound", "primary_muscles": ["chest", "triceps"]},
                                {"exercise_id": "lat_pulldown", "slot_role": "secondary_compound", "primary_muscles": ["back", "biceps"]},
                            ],
                        },
                        {
                            "day_id": "d2",
                            "slots": [
                                {"exercise_id": "hack_squat", "slot_role": "primary_compound", "primary_muscles": ["quads", "glutes"]},
                                {"exercise_id": "lying_leg_curl", "slot_role": "secondary_compound", "primary_muscles": ["hamstrings"]},
                            ],
                        },
                        {
                            "day_id": "d3",
                            "slots": [
                                {"exercise_id": "incline_press", "slot_role": "primary_compound", "primary_muscles": ["chest", "shoulders"]},
                                {"exercise_id": "seated_row", "slot_role": "secondary_compound", "primary_muscles": ["back"]},
                            ],
                        },
                        {
                            "day_id": "d4",
                            "slots": [
                                {"exercise_id": "romanian_deadlift", "slot_role": "primary_compound", "primary_muscles": ["hamstrings", "glutes"]},
                                {"exercise_id": "split_squat", "slot_role": "secondary_compound", "primary_muscles": ["quads"]},
                            ],
                        },
                        {
                            "day_id": "d5",
                            "slots": [
                                {"exercise_id": "weak_chest_fly", "slot_role": "weak_point", "primary_muscles": ["chest"]},
                                {"exercise_id": "weak_ham_curl", "slot_role": "weak_point", "primary_muscles": ["hamstrings"]},
                                {"exercise_id": "lateral_raise", "slot_role": "isolation", "primary_muscles": ["shoulders"]},
                            ],
                        },
                    ],
                }
            ],
        },
    }


def _overlay(days: int) -> dict:
    return {
        "available_training_days": days,
        "temporary_duration_weeks": 2,
        "current_week_index": 3,
        "weak_areas": [
            {"muscle_group": "chest", "priority": 5, "desired_extra_slots_per_week": 1},
            {"muscle_group": "hamstrings", "priority": 5, "desired_extra_slots_per_week": 1},
        ],
    }


def test_adaptation_supports_two_to_five_days() -> None:
    package = _sample_onboarding_package()

    for days in (2, 3, 4, 5):
        result = adapt_onboarding_frequency(onboarding_package=package, overlay=_overlay(days))
        assert result["from_days"] == 5
        assert result["to_days"] == days
        assert len(result["weeks"]) == 2
        for week in result["weeks"]:
            assert week["adapted_training_days"] == days
            assert len(week["adapted_days"]) == days


def test_adaptation_preserves_weak_area_stimulus_when_compressed() -> None:
    package = _sample_onboarding_package()
    result = adapt_onboarding_frequency(onboarding_package=package, overlay=_overlay(3))

    for week in result["weeks"]:
        chest_slots = week["coverage_after"].get("chest", 0)
        hamstring_slots = week["coverage_after"].get("hamstrings", 0)
        assert chest_slots >= 1
        assert hamstring_slots >= 1

        weak_area_exercises = {"weak_chest_fly", "weak_ham_curl"}
        weak_decisions = [
            decision
            for decision in week["decisions"]
            if decision["exercise_id"] in weak_area_exercises
        ]
        assert weak_decisions
        assert all(decision["action"] != "reduce" for decision in weak_decisions)
