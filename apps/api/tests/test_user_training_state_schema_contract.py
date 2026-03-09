from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.adaptive_schema import UserTrainingState


def test_user_training_state_validates_against_canonical_contract() -> None:
    state = UserTrainingState.model_validate(
        {
            "user_program_state": {
                "program_id": "full_body_v1",
                "phase_id": "accumulation",
                "week_index": 3,
                "day_id": "w3d2",
                "session_id": "full_body_v1-day-2",
                "last_generated_week_start": date(2026, 3, 2),
            },
            "exercise_performance_history": [
                {
                    "exercise_id": "bench_press_barbell",
                    "performed_at": datetime(2026, 3, 7, 9, 0),
                    "set_index": 1,
                    "reps": 8,
                    "weight": 100.0,
                    "rpe": 8.5,
                }
            ],
            "progression_state_per_exercise": [
                {
                    "exercise_id": "bench_press_barbell",
                    "current_working_weight": 100.0,
                    "exposure_count": 6,
                    "consecutive_under_target_exposures": 1,
                    "last_progression_action": "hold",
                    "last_updated_at": datetime(2026, 3, 7, 9, 30),
                }
            ],
            "fatigue_state": {
                "recovery_state": "normal",
                "severe_soreness_count": 0,
                "session_rpe_avg": 8.0,
                "soreness_by_muscle": {},
                "flagged_muscles": [],
            },
            "adherence_state": {
                "latest_adherence_score": 4,
                "rolling_average_score": 4.25,
                "missed_session_count": 1,
            },
            "stall_state": {
                "stalled_exercise_ids": ["bench_press_barbell"],
                "consecutive_underperformance_weeks": 1,
                "phase_stagnation_weeks": 0,
            },
            "generation_state": {
                "prior_generated_weeks_by_program": {"full_body_v1": 2},
                "under_target_muscles": ["biceps"],
                "mesocycle_trigger_weeks_effective": 5,
            },
        }
    )

    assert state.user_program_state.program_id == "full_body_v1"
    assert state.exercise_performance_history[0].exercise_id == "bench_press_barbell"
    assert state.progression_state_per_exercise[0].last_progression_action == "hold"


def test_user_training_state_rejects_duplicate_progression_entries() -> None:
    with pytest.raises(ValidationError, match="progression_state_per_exercise must have unique exercise_id values"):
        UserTrainingState.model_validate(
            {
                "user_program_state": {
                    "program_id": "full_body_v1",
                    "phase_id": "accumulation",
                    "week_index": 3,
                },
                "progression_state_per_exercise": [
                    {
                        "exercise_id": "bench_press_barbell",
                        "current_working_weight": 100.0,
                        "exposure_count": 6,
                        "consecutive_under_target_exposures": 1,
                        "last_progression_action": "hold",
                    },
                    {
                        "exercise_id": "bench_press_barbell",
                        "current_working_weight": 102.5,
                        "exposure_count": 7,
                        "consecutive_under_target_exposures": 0,
                        "last_progression_action": "increase_load",
                    },
                ],
                "fatigue_state": {
                    "recovery_state": "normal",
                    "severe_soreness_count": 0,
                    "soreness_by_muscle": {},
                    "flagged_muscles": [],
                },
                "adherence_state": {
                    "latest_adherence_score": 4,
                    "missed_session_count": 0,
                },
                "stall_state": {
                    "stalled_exercise_ids": [],
                    "consecutive_underperformance_weeks": 0,
                    "phase_stagnation_weeks": 0,
                },
                "generation_state": {
                    "prior_generated_weeks_by_program": {},
                },
            }
        )


def test_user_training_state_rejects_invalid_nested_ranges() -> None:
    with pytest.raises(ValidationError):
        UserTrainingState.model_validate(
            {
                "user_program_state": {
                    "program_id": "full_body_v1",
                    "phase_id": "accumulation",
                    "week_index": 0,
                },
                "exercise_performance_history": [
                    {
                        "exercise_id": "bench_press_barbell",
                        "performed_at": datetime(2026, 3, 7, 9, 0),
                        "set_index": 0,
                        "reps": 0,
                        "weight": -1,
                    }
                ],
                "progression_state_per_exercise": [],
                "fatigue_state": {
                    "recovery_state": "high_fatigue",
                    "severe_soreness_count": -1,
                    "soreness_by_muscle": {},
                    "flagged_muscles": [],
                },
                "adherence_state": {
                    "latest_adherence_score": 6,
                    "missed_session_count": -1,
                },
                "stall_state": {
                    "stalled_exercise_ids": [],
                    "consecutive_underperformance_weeks": -1,
                    "phase_stagnation_weeks": -1,
                },
                "generation_state": {
                    "prior_generated_weeks_by_program": {},
                },
            }
        )