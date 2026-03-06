from core_engine.intelligence import (
    evaluate_schedule_adaptation,
    recommend_phase_transition,
    recommend_progression_action,
    recommend_specialization_adjustments,
    summarize_program_media_and_warmups,
)


def _sample_template() -> dict:
    return {
        "id": "intelligence_test_template",
        "sessions": [
            {
                "name": "Upper Push",
                "exercises": [
                    {
                        "id": "bench",
                        "name": "Bench Press",
                        "sets": 3,
                        "start_weight": 100,
                        "primary_muscles": ["chest", "triceps"],
                        "video": {"youtube_url": "https://www.youtube.com/watch?v=abc"},
                    }
                ],
            },
            {
                "name": "Upper Pull",
                "exercises": [
                    {
                        "id": "row",
                        "name": "Barbell Row",
                        "sets": 3,
                        "start_weight": 90,
                        "primary_muscles": ["back", "biceps"],
                        "video": None,
                    }
                ],
            },
            {
                "name": "Lower Quad",
                "exercises": [
                    {
                        "id": "squat",
                        "name": "Back Squat",
                        "sets": 4,
                        "start_weight": 120,
                        "primary_muscles": ["quads", "glutes"],
                    }
                ],
            },
            {
                "name": "Lower Hinge",
                "exercises": [
                    {
                        "id": "rdl",
                        "name": "Romanian Deadlift",
                        "sets": 3,
                        "start_weight": 110,
                        "primary_muscles": ["hamstrings", "glutes"],
                    }
                ],
            },
            {
                "name": "Shoulders Arms",
                "exercises": [
                    {
                        "id": "lateral_raise",
                        "name": "Lateral Raise",
                        "sets": 3,
                        "start_weight": 20,
                        "primary_muscles": ["shoulders"],
                    },
                    {
                        "id": "calf_raise",
                        "name": "Calf Raise",
                        "sets": 3,
                        "start_weight": 80,
                        "primary_muscles": ["calves"],
                    },
                ],
            },
        ],
    }


def test_schedule_adaptation_reports_tradeoffs_and_muscle_delta() -> None:
    result = evaluate_schedule_adaptation(
        user_profile={"name": "Test"},
        split_preference="full_body",
        program_template=_sample_template(),
        history=[],
        phase="maintenance",
        from_days=5,
        to_days=3,
    )

    assert result["from_days"] == 5
    assert result["to_days"] == 3
    assert result["dropped_sessions"]
    assert any("density" in item.lower() for item in result["tradeoffs"])
    assert isinstance(result["muscle_set_delta"], dict)


def test_progression_action_recommends_deload_for_low_readiness() -> None:
    decision = recommend_progression_action(
        completion_pct=62,
        adherence_score=2,
        soreness_level="severe",
        average_rpe=9.5,
        consecutive_underperformance_weeks=2,
    )

    assert decision["action"] == "deload"
    assert decision["set_delta"] == -1
    assert decision["load_scale"] < 1.0


def test_progression_action_recommends_progress_when_metrics_are_strong() -> None:
    decision = recommend_progression_action(
        completion_pct=98,
        adherence_score=5,
        soreness_level="mild",
        average_rpe=8.5,
        consecutive_underperformance_weeks=0,
    )

    assert decision["action"] == "progress"
    assert decision["load_scale"] > 1.0


def test_phase_transition_moves_from_accumulation_to_intensification() -> None:
    transition = recommend_phase_transition(
        current_phase="accumulation",
        weeks_in_phase=6,
        readiness_score=72,
        progression_action="progress",
        stagnation_weeks=0,
    )

    assert transition["next_phase"] == "intensification"


def test_phase_transition_moves_to_deload_when_stalled() -> None:
    transition = recommend_phase_transition(
        current_phase="intensification",
        weeks_in_phase=3,
        readiness_score=58,
        progression_action="hold",
        stagnation_weeks=2,
    )

    assert transition["next_phase"] == "deload"


def test_specialization_adjustments_focus_on_lagging_muscles() -> None:
    adjustments = recommend_specialization_adjustments(
        weekly_volume_by_muscle={
            "chest": 12,
            "back": 13,
            "quads": 11,
            "hamstrings": 10,
            "glutes": 10,
            "shoulders": 6,
            "biceps": 5,
            "triceps": 9,
            "calves": 7,
        },
        lagging_muscles=["biceps", "shoulders", "calves"],
        max_focus_muscles=2,
        target_min_sets=8,
    )

    assert adjustments["focus_muscles"] == ["biceps", "shoulders"]
    assert adjustments["focus_adjustments"]["biceps"] >= 1
    assert adjustments["focus_adjustments"]["shoulders"] >= 1


def test_media_and_warmup_summary_reports_video_coverage() -> None:
    summary = summarize_program_media_and_warmups(_sample_template())

    assert summary["total_exercises"] == 6
    assert summary["video_linked_exercises"] == 1
    assert summary["video_coverage_pct"] > 0
    assert len(summary["sample_warmups"]) == 3
