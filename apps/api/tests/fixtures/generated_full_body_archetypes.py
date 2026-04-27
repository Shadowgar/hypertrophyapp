from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta


def _build_progression_entries(entry_count: int, total_exposure_count: int) -> list[dict]:
    base_exposure = total_exposure_count // entry_count
    remainder = total_exposure_count % entry_count
    updated_at = datetime(2026, 3, 1, 10, 0, 0)
    entries = []
    for index in range(entry_count):
        entries.append(
            {
                "exercise_id": f"exercise_{index + 1}",
                "current_working_weight": 100 + index,
                "exposure_count": base_exposure + (1 if index < remainder else 0),
                "consecutive_under_target_exposures": 0,
                "last_progression_action": "hold",
                "fatigue_score": 0.25,
                "last_updated_at": (updated_at + timedelta(days=index)).isoformat(),
            }
        )
    return entries


def _build_progression_entries_from_specs(specs: list[dict]) -> list[dict]:
    updated_at = datetime(2026, 3, 1, 10, 0, 0)
    entries = []
    for index, spec in enumerate(specs):
        entries.append(
            {
                "exercise_id": spec["exercise_id"],
                "current_working_weight": spec["current_working_weight"],
                "exposure_count": spec["exposure_count"],
                "consecutive_under_target_exposures": spec.get("consecutive_under_target_exposures", 0),
                "last_progression_action": spec.get("last_progression_action", "hold"),
                "fatigue_score": spec.get("fatigue_score", 0.25),
                "last_updated_at": (updated_at + timedelta(days=index)).isoformat(),
            }
        )
    return entries


def _build_performance_history(entry_count: int) -> list[dict]:
    performed_at = datetime(2026, 3, 1, 7, 0, 0)
    return [
        {
            "exercise_id": f"exercise_{(index % 8) + 1}",
            "performed_at": (performed_at + timedelta(days=index)).isoformat(),
            "set_index": 1,
            "reps": 10,
            "weight": 135.0,
            "rpe": 8.0,
        }
        for index in range(entry_count)
    ]


def _build_training_state(
    *,
    profile_input: dict,
    total_exposure_count: int,
    progression_entry_count: int,
    performance_history_count: int,
    progression_state_per_exercise: list[dict] | None = None,
    recoverability: str = "moderate",
    recovery_state: str = "normal",
    adherence_score: int = 4,
    missed_sessions: int = 0,
    under_target_muscles: list[str] | None = None,
    prior_generated_weeks_by_program: dict[str, int] | None = None,
) -> dict:
    fatigue_state = {
        "recovery_state": recovery_state,
        "severe_soreness_count": 0,
        "session_rpe_avg": 7.5,
        "soreness_by_muscle": {},
        "flagged_muscles": [],
    }
    adherence_state = {
        "latest_adherence_score": adherence_score,
        "rolling_average_score": float(adherence_score),
        "missed_session_count": missed_sessions,
    }
    stimulus_fatigue_response = {
        "stimulus_quality": "moderate",
        "fatigue_cost": "moderate",
        "recoverability": recoverability,
        "progression_eligibility": True,
        "deload_pressure": "low",
        "substitution_pressure": "low",
        "signals": {
            "stimulus": [],
            "fatigue": [],
            "recoverability": [],
        },
    }
    return {
        "user_program_state": {
            "program_id": "generated_preview",
            "phase_id": "phase_1",
            "week_index": 1,
            "day_id": None,
            "session_id": None,
            "last_generated_week_start": "2026-03-01",
        },
        "exercise_performance_history": _build_performance_history(performance_history_count),
        "progression_state_per_exercise": progression_state_per_exercise
        or _build_progression_entries(progression_entry_count, total_exposure_count),
        "fatigue_state": fatigue_state,
        "adherence_state": adherence_state,
        "readiness_state": {
            "sleep_quality": 4,
            "stress_level": 2,
            "pain_flags": [],
            "recovery_risk_flags": [],
        },
        "stimulus_fatigue_response": stimulus_fatigue_response,
        "coaching_state": {
            "readiness": {
                "sleep_quality": 4,
                "stress_level": 2,
                "pain_flags": [],
                "recovery_risk_flags": [],
            },
            "fatigue": fatigue_state,
            "adherence": adherence_state,
            "stall": {
                "stalled_exercise_ids": [],
                "consecutive_underperformance_weeks": 0,
                "phase_stagnation_weeks": 0,
            },
            "stimulus_fatigue_response": stimulus_fatigue_response,
            "mesocycle": {
                "week_index": 1,
                "trigger_weeks_effective": 1,
                "authored_week_index": None,
                "authored_week_role": None,
                "authored_sequence_length": None,
                "authored_sequence_complete": False,
                "phase_transition_pending": False,
                "phase_transition_reason": None,
                "post_authored_behavior": None,
            },
        },
        "constraint_state": {
            "days_available": profile_input["days_available"],
            "split_preference": profile_input.get("split_preference"),
            "training_location": profile_input.get("training_location"),
            "equipment_profile": profile_input.get("equipment_profile", []),
            "weak_areas": profile_input.get("weak_areas", []),
            "nutrition_phase": None,
            "session_time_budget_minutes": profile_input.get("session_time_budget_minutes"),
            "movement_restrictions": profile_input.get("movement_restrictions", []),
            "near_failure_tolerance": profile_input.get("near_failure_tolerance"),
        },
        "stall_state": {
            "stalled_exercise_ids": [],
            "consecutive_underperformance_weeks": 0,
            "phase_stagnation_weeks": 0,
        },
        "generation_state": {
            "prior_generated_weeks_by_program": prior_generated_weeks_by_program or {},
            "under_target_muscles": under_target_muscles or [],
            "mesocycle_trigger_weeks_effective": 1,
            "latest_mesocycle": {
                "week_index": 1,
                "trigger_weeks_effective": 1,
                "authored_week_index": None,
                "authored_week_role": None,
                "authored_sequence_length": None,
                "authored_sequence_complete": False,
                "phase_transition_pending": False,
                "phase_transition_reason": None,
                "post_authored_behavior": None,
            },
        },
    }


ARCHETYPE_FIXTURES = {
    "novice_gym_full_body": {
        "profile_input": {
            "days_available": 3,
            "split_preference": None,
            "training_location": "gym",
            "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
            "weak_areas": ["chest", "lats"],
            "session_time_budget_minutes": 75,
            "movement_restrictions": [],
            "near_failure_tolerance": "high",
        },
        "training_state": _build_training_state(
            profile_input={
                "days_available": 3,
                "split_preference": None,
                "training_location": "gym",
                "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
                "weak_areas": ["chest", "lats"],
                "session_time_budget_minutes": 75,
                "movement_restrictions": [],
                "near_failure_tolerance": "high",
            },
            total_exposure_count=18,
            progression_entry_count=3,
            performance_history_count=8,
            progression_state_per_exercise=_build_progression_entries_from_specs(
                [
                    {
                        "exercise_id": "hack_squat",
                        "current_working_weight": 245.0,
                        "exposure_count": 6,
                    },
                    {
                        "exercise_id": "neutral_grip_lat_pulldown",
                        "current_working_weight": 150.0,
                        "exposure_count": 6,
                    },
                    {
                        "exercise_id": "machine_shoulder_press",
                        "current_working_weight": 110.0,
                        "exposure_count": 6,
                    },
                ]
            ),
            under_target_muscles=["rear_delts"],
        ),
        "expected_assessment": {
            "experience_level": "novice",
            "user_class_flags": ["novice"],
            "recovery_profile": "normal",
            "schedule_profile": "normal",
            "equipment_context": "full_gym",
            "fatigue_tolerance_profile": "high",
            "comeback_flag": False,
            "weak_point_order": ["chest", "lats", "rear_delts"],
        },
        "expected_blueprint": {
            "session_exercise_cap": 6,
            "complexity_ceiling": "simple",
            "non_empty_candidate_patterns": ["squat", "hinge", "horizontal_press", "horizontal_pull", "vertical_pull", "vertical_press"],
        },
        "expected_template": {
            "constructibility_status": "ready",
            "session_count": 3,
            "expects_insufficiency": False,
            "expected_session_exercise_counts": [10, 10, 10],
            "expected_selected_exercise_ids": [
                "hack_squat",
                "neutral_grip_lat_pulldown",
                "machine_shoulder_press",
            ],
            "expected_start_weight_matches": {
                "hack_squat": 245.0,
                "machine_shoulder_press": 110.0,
                "neutral_grip_lat_pulldown": 150.0
            }
        },
    },
    "low_time_full_body": {
        "profile_input": {
            "days_available": 3,
            "split_preference": "ppl",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
            "weak_areas": ["quads"],
            "session_time_budget_minutes": 45,
            "movement_restrictions": [],
            "near_failure_tolerance": None,
        },
        "training_state": _build_training_state(
            profile_input={
                "days_available": 3,
                "split_preference": "ppl",
                "training_location": "gym",
                "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
                "weak_areas": ["quads"],
                "session_time_budget_minutes": 45,
                "movement_restrictions": [],
                "near_failure_tolerance": None,
            },
            total_exposure_count=45,
            progression_entry_count=6,
            performance_history_count=12,
            under_target_muscles=["hamstrings"],
        ),
        "expected_assessment": {
            "experience_level": "early_intermediate",
            "user_class_flags": ["early_intermediate"],
            "recovery_profile": "normal",
            "schedule_profile": "low_time",
            "equipment_context": "full_gym",
            "fatigue_tolerance_profile": "moderate",
            "comeback_flag": False,
            "weak_point_order": ["quads", "hamstrings"],
            "default_ids": ["default_near_failure_tolerance_moderate_v1"],
        },
        "expected_blueprint": {
            "session_exercise_cap": 4,
            "complexity_ceiling": "standard",
        },
        "expected_template": {
            "constructibility_status": "ready",
            "session_count": 3,
            "expects_insufficiency": False,
            "expected_session_exercise_counts": [7, 7, 7],
            "expected_selected_exercise_ids": [
                "bottom_half_low_incline_db_press",
                "roman_chair_leg_raise",
            ],
        },
    },
    "restricted_equipment_full_body": {
        "profile_input": {
            "days_available": 3,
            "split_preference": None,
            "training_location": "home",
            "equipment_profile": [],
            "weak_areas": ["triceps"],
            "session_time_budget_minutes": 60,
            "movement_restrictions": [],
            "near_failure_tolerance": "low",
        },
        "training_state": _build_training_state(
            profile_input={
                "days_available": 3,
                "split_preference": None,
                "training_location": "home",
                "equipment_profile": [],
                "weak_areas": ["triceps"],
                "session_time_budget_minutes": 60,
                "movement_restrictions": [],
                "near_failure_tolerance": "low",
            },
            total_exposure_count=50,
            progression_entry_count=6,
            performance_history_count=12,
            under_target_muscles=["hamstrings"],
        ),
        "expected_assessment": {
            "experience_level": "early_intermediate",
            "user_class_flags": ["early_intermediate", "restricted_equipment"],
            "recovery_profile": "normal",
            "schedule_profile": "normal",
            "equipment_context": "restricted_equipment",
            "fatigue_tolerance_profile": "low",
            "comeback_flag": False,
            "weak_point_order": ["triceps", "hamstrings"],
        },
        "expected_blueprint": {
            "session_exercise_cap": 5,
            "complexity_ceiling": "standard",
            "expects_insufficiency": True,
        },
        "expected_template": {
            "constructibility_status": "insufficient",
            "session_count": 3,
            "expects_insufficiency": True,
            "expected_session_exercise_counts": [3, 5, 5],
        },
    },
    "low_recovery_full_body": {
        "profile_input": {
            "days_available": 3,
            "split_preference": None,
            "training_location": "gym",
            "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
            "weak_areas": ["delts"],
            "session_time_budget_minutes": 60,
            "movement_restrictions": [],
            "near_failure_tolerance": "low",
        },
        "training_state": _build_training_state(
            profile_input={
                "days_available": 3,
                "split_preference": None,
                "training_location": "gym",
                "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
                "weak_areas": ["delts"],
                "session_time_budget_minutes": 60,
                "movement_restrictions": [],
                "near_failure_tolerance": "low",
            },
            total_exposure_count=52,
            progression_entry_count=6,
            performance_history_count=12,
            recoverability="low",
            under_target_muscles=["hamstrings"],
        ),
        "expected_assessment": {
            "experience_level": "early_intermediate",
            "user_class_flags": ["early_intermediate", "low_recovery"],
            "recovery_profile": "low_recovery",
            "schedule_profile": "normal",
            "equipment_context": "full_gym",
            "fatigue_tolerance_profile": "low",
            "comeback_flag": False,
            "weak_point_order": ["delts", "hamstrings"],
        },
        "expected_blueprint": {
            "volume_tier": "conservative",
            "complexity_ceiling": "simple",
        },
        "expected_template": {
            "constructibility_status": "ready",
            "session_count": 3,
            "expects_insufficiency": False,
            "expected_session_exercise_counts": [7, 7, 7],
            "expected_selected_exercise_ids": [
                "decline_machine_chest_press",
                "neutral_grip_lat_pulldown",
            ],
        },
    },
    "inconsistent_schedule_full_body": {
        "profile_input": {
            "days_available": 3,
            "split_preference": None,
            "training_location": "gym",
            "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
            "weak_areas": ["back"],
            "session_time_budget_minutes": 60,
            "movement_restrictions": [],
            "near_failure_tolerance": "moderate",
        },
        "training_state": _build_training_state(
            profile_input={
                "days_available": 3,
                "split_preference": None,
                "training_location": "gym",
                "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
                "weak_areas": ["back"],
                "session_time_budget_minutes": 60,
                "movement_restrictions": [],
                "near_failure_tolerance": "moderate",
            },
            total_exposure_count=50,
            progression_entry_count=6,
            performance_history_count=12,
            adherence_score=2,
            missed_sessions=3,
            under_target_muscles=["lats"],
        ),
        "expected_assessment": {
            "experience_level": "early_intermediate",
            "user_class_flags": ["early_intermediate", "inconsistent_schedule"],
            "recovery_profile": "normal",
            "schedule_profile": "inconsistent_schedule",
            "equipment_context": "full_gym",
            "fatigue_tolerance_profile": "moderate",
            "comeback_flag": False,
            "weak_point_order": ["back", "lats"],
        },
        "expected_blueprint": {
            "volume_tier": "conservative",
            "complexity_ceiling": "simple",
            "required_policy_ids": ["prefer_adherence_first_for_inconsistent_schedule"],
        },
        "expected_template": {
            "constructibility_status": "ready",
            "session_count": 3,
            "expects_insufficiency": False,
            "expected_session_exercise_counts": [9, 9, 9],
        },
    },
    "comeback_full_body": {
        "profile_input": {
            "days_available": 3,
            "split_preference": "upper_lower",
            "training_location": "gym",
            "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
            "weak_areas": ["glutes"],
            "session_time_budget_minutes": 60,
            "movement_restrictions": [],
            "near_failure_tolerance": "moderate",
        },
        "training_state": _build_training_state(
            profile_input={
                "days_available": 3,
                "split_preference": "upper_lower",
                "training_location": "gym",
                "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
                "weak_areas": ["glutes"],
                "session_time_budget_minutes": 60,
                "movement_restrictions": [],
                "near_failure_tolerance": "moderate",
            },
            total_exposure_count=40,
            progression_entry_count=5,
            performance_history_count=2,
            under_target_muscles=["hamstrings"],
            prior_generated_weeks_by_program={"generated_full_body_preview": 4},
        ),
        "expected_assessment": {
            "experience_level": "early_intermediate",
            "user_class_flags": ["early_intermediate", "comeback"],
            "recovery_profile": "normal",
            "schedule_profile": "normal",
            "equipment_context": "full_gym",
            "fatigue_tolerance_profile": "moderate",
            "comeback_flag": True,
            "weak_point_order": ["glutes", "hamstrings"],
        },
        "expected_blueprint": {
            "volume_tier": "conservative",
            "complexity_ceiling": "simple",
        },
        "expected_template": {
            "constructibility_status": "ready",
            "session_count": 3,
            "expects_insufficiency": False,
            "expected_session_exercise_counts": [7, 7, 7],
        },
    },
    "two_day_full_body": {
        "profile_input": {
            "days_available": 2,
            "split_preference": None,
            "training_location": "gym",
            "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
            "weak_areas": ["biceps"],
            "session_time_budget_minutes": 60,
            "movement_restrictions": [],
            "near_failure_tolerance": "moderate",
        },
        "training_state": _build_training_state(
            profile_input={
                "days_available": 2,
                "split_preference": None,
                "training_location": "gym",
                "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
                "weak_areas": ["biceps"],
                "session_time_budget_minutes": 60,
                "movement_restrictions": [],
                "near_failure_tolerance": "moderate",
            },
            total_exposure_count=48,
            progression_entry_count=6,
            performance_history_count=12,
            under_target_muscles=["rear_delts"],
        ),
        "expected_assessment": {
            "experience_level": "early_intermediate",
            "user_class_flags": ["early_intermediate"],
            "recovery_profile": "normal",
            "schedule_profile": "normal",
            "equipment_context": "full_gym",
            "fatigue_tolerance_profile": "moderate",
            "comeback_flag": False,
            "weak_point_order": ["biceps", "rear_delts"],
        },
        "expected_blueprint": {
            "session_exercise_cap": 5,
            "volume_tier": "moderate",
            "complexity_ceiling": "standard",
        },
        "expected_template": {
            "constructibility_status": "ready",
            "session_count": 2,
            "expects_insufficiency": False,
            "expected_session_exercise_counts": [7, 7],
        },
    },
    "four_day_full_body": {
        "profile_input": {
            "days_available": 4,
            "split_preference": None,
            "training_location": "gym",
            "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
            "weak_areas": ["calves"],
            "session_time_budget_minutes": 60,
            "movement_restrictions": [],
            "near_failure_tolerance": "moderate",
        },
        "training_state": _build_training_state(
            profile_input={
                "days_available": 4,
                "split_preference": None,
                "training_location": "gym",
                "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
                "weak_areas": ["calves"],
                "session_time_budget_minutes": 60,
                "movement_restrictions": [],
                "near_failure_tolerance": "moderate",
            },
            total_exposure_count=56,
            progression_entry_count=6,
            performance_history_count=14,
            under_target_muscles=["triceps"],
        ),
        "expected_assessment": {
            "experience_level": "early_intermediate",
            "user_class_flags": ["early_intermediate"],
            "recovery_profile": "normal",
            "schedule_profile": "normal",
            "equipment_context": "full_gym",
            "fatigue_tolerance_profile": "moderate",
            "comeback_flag": False,
            "weak_point_order": ["calves", "triceps"],
        },
        "expected_blueprint": {
            "session_exercise_cap": 5,
            "volume_tier": "moderate",
            "complexity_ceiling": "standard",
        },
        "expected_template": {
            "constructibility_status": "ready",
            "session_count": 4,
            "expects_insufficiency": False,
            "expected_session_exercise_counts": [7, 7, 7, 7],
        },
    },
    "five_day_full_body": {
        "profile_input": {
            "days_available": 5,
            "split_preference": None,
            "training_location": "gym",
            "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
            "weak_areas": ["side_delts"],
            "session_time_budget_minutes": 60,
            "movement_restrictions": [],
            "near_failure_tolerance": "moderate",
        },
        "training_state": _build_training_state(
            profile_input={
                "days_available": 5,
                "split_preference": None,
                "training_location": "gym",
                "equipment_profile": ["barbell", "bodyweight", "cable", "dumbbell", "machine"],
                "weak_areas": ["side_delts"],
                "session_time_budget_minutes": 60,
                "movement_restrictions": [],
                "near_failure_tolerance": "moderate",
            },
            total_exposure_count=60,
            progression_entry_count=7,
            performance_history_count=16,
            under_target_muscles=["biceps"],
        ),
        "expected_assessment": {
            "experience_level": "early_intermediate",
            "user_class_flags": ["early_intermediate"],
            "recovery_profile": "normal",
            "schedule_profile": "normal",
            "equipment_context": "full_gym",
            "fatigue_tolerance_profile": "moderate",
            "comeback_flag": False,
            "weak_point_order": ["side_delts", "biceps"],
        },
        "expected_blueprint": {
            "session_exercise_cap": 5,
            "volume_tier": "moderate",
            "complexity_ceiling": "standard",
        },
        "expected_template": {
            "constructibility_status": "ready",
            "session_count": 5,
            "expects_insufficiency": False,
            "expected_session_exercise_counts": [7, 7, 7, 7, 7],
        },
    },
}


def get_generated_full_body_archetypes() -> dict[str, dict]:
    return deepcopy(ARCHETYPE_FIXTURES)
