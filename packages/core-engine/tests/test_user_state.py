from datetime import date, datetime
from types import SimpleNamespace

from core_engine import build_plan_decision_training_state, build_user_training_state


def test_build_user_training_state_assembles_canonical_runtime_payload() -> None:
    payload = build_user_training_state(
        selected_program_id="full_body_v1",
        latest_plan=SimpleNamespace(
            week_start=date(2026, 3, 2),
            payload={
                "program_template_id": "full_body_v1",
                "phase": "accumulation",
                "week_start": "2026-03-02",
                "mesocycle": {"week_index": 3, "trigger_weeks_effective": 5},
                "muscle_coverage": {"under_target_muscles": ["biceps", "rear_delts"]},
                "sessions": [
                    {
                        "session_id": "full_body_v1-day-1",
                        "date": "2026-03-02",
                        "exercises": [{"id": "incline_press", "sets": 3}],
                    },
                    {
                        "session_id": "full_body_v1-day-2",
                        "date": "2026-03-03",
                        "exercises": [{"id": "bench_press_barbell", "sets": 3}],
                    },
                ],
            },
        ),
        recent_workout_logs=[
            SimpleNamespace(
                workout_id="full_body_v1-day-2",
                primary_exercise_id="bench_press_barbell",
                exercise_id="bench_press_barbell",
                set_index=1,
                reps=8,
                weight=100.0,
                rpe=8.5,
                created_at=datetime(2026, 3, 3, 9, 0),
            )
        ],
        exercise_states=[
            SimpleNamespace(
                exercise_id="bench_press_barbell",
                current_working_weight=100.0,
                exposure_count=6,
                consecutive_under_target_exposures=3,
                last_progression_action="hold",
                last_updated_at=datetime(2026, 3, 3, 9, 30),
            )
        ],
        latest_soreness_entry=SimpleNamespace(
            severity_by_muscle={"chest": "severe", "back": "severe", "quads": "mild"}
        ),
        recent_checkins=[
            SimpleNamespace(adherence_score=4),
            SimpleNamespace(adherence_score=3),
        ],
        recent_review_cycles=[
            SimpleNamespace(
                adherence_score=4,
                summary={"faulty_exercise_count": 1},
                adjustments={"global": {"set_delta": -1, "weight_scale": 0.95}},
            ),
            SimpleNamespace(
                adherence_score=3,
                summary={"faulty_exercise_count": 2},
                adjustments={"global": {"set_delta": 0, "weight_scale": 0.98}},
            ),
            SimpleNamespace(
                adherence_score=5,
                summary={"faulty_exercise_count": 0},
                adjustments={"global": {"set_delta": 0, "weight_scale": 1.0}},
            ),
        ],
        prior_plans=[
            SimpleNamespace(
                week_start=date(2026, 2, 17),
                payload={"program_template_id": "full_body_v1", "sessions": []},
            ),
            SimpleNamespace(
                week_start=date(2026, 2, 24),
                payload={"program_template_id": "other_template", "sessions": [{"session_id": "full_body_v1-day-1"}]},
            ),
        ],
        today=date(2026, 3, 3),
    )

    assert payload["user_program_state"] == {
        "program_id": "full_body_v1",
        "phase_id": "accumulation",
        "week_index": 3,
        "day_id": "w3d2",
        "session_id": "full_body_v1-day-2",
        "last_generated_week_start": date(2026, 3, 2),
    }
    assert payload["exercise_performance_history"] == [
        {
            "exercise_id": "bench_press_barbell",
            "performed_at": datetime(2026, 3, 3, 9, 0),
            "set_index": 1,
            "reps": 8,
            "weight": 100.0,
            "rpe": 8.5,
        }
    ]
    assert payload["progression_state_per_exercise"] == [
        {
            "exercise_id": "bench_press_barbell",
            "current_working_weight": 100.0,
            "exposure_count": 6,
            "consecutive_under_target_exposures": 3,
            "last_progression_action": "hold",
            "last_updated_at": datetime(2026, 3, 3, 9, 30),
        }
    ]
    assert payload["fatigue_state"] == {
        "recovery_state": "high_fatigue",
        "severe_soreness_count": 2,
        "session_rpe_avg": 8.5,
        "soreness_by_muscle": {"chest": "severe", "back": "severe", "quads": "mild"},
        "flagged_muscles": ["back", "chest"],
    }
    assert payload["adherence_state"] == {
        "latest_adherence_score": 4,
        "rolling_average_score": 3.5,
        "missed_session_count": 1,
    }
    assert payload["stall_state"] == {
        "stalled_exercise_ids": ["bench_press_barbell"],
        "consecutive_underperformance_weeks": 2,
        "phase_stagnation_weeks": 2,
    }
    assert payload["generation_state"] == {
        "prior_generated_weeks_by_program": {"full_body_v1": 2, "other_template": 1},
        "under_target_muscles": ["biceps", "rear_delts"],
        "mesocycle_trigger_weeks_effective": 5,
    }


def test_build_plan_decision_training_state_uses_canonical_builder_defaults() -> None:
    payload = build_plan_decision_training_state(
        selected_program_id="full_body_v1",
        latest_plan=SimpleNamespace(
            week_start=date(2026, 3, 2),
            payload={
                "program_template_id": "full_body_v1",
                "phase": "accumulation",
                "mesocycle": {"week_index": 2},
                "sessions": [],
            },
        ),
        latest_soreness_entry=None,
    )

    assert payload["user_program_state"]["program_id"] == "full_body_v1"
    assert payload["user_program_state"]["week_index"] == 2
    assert payload["exercise_performance_history"] == []
    assert payload["progression_state_per_exercise"] == []
