from core_engine.progression import (
    ExerciseState,
    LastPerformance,
    recommend_working_weight,
    update_exercise_state_after_workout,
)


def _sample_rule_set() -> dict:
    return {
        "progression_rules": {
            "on_success": {"percent": 2.5},
            "on_under_target": {"reduce_percent": 2.5, "after_exposures": 2},
        }
    }


def test_recommend_working_weight_increases_on_top_range_completion() -> None:
    state = ExerciseState(exercise_id="bench", current_working_weight=100, exposure_count=3)
    perf = LastPerformance(
        completed_reps=12,
        target_reps_min=8,
        target_reps_max=12,
        completed_sets=3,
        planned_sets=3,
    )

    next_weight = recommend_working_weight(state, perf, (8, 12), "bulk")
    assert next_weight > state.current_working_weight


def test_recommend_working_weight_decreases_assistance_on_top_range_completion() -> None:
    """For assisted movements, lower stack weight is harder → progress reduces assistance."""
    state = ExerciseState(exercise_id="assisted_pull_up", current_working_weight=100, exposure_count=3)
    perf = LastPerformance(
        completed_reps=10,
        target_reps_min=8,
        target_reps_max=10,
        completed_sets=4,
        planned_sets=4,
    )

    next_weight = recommend_working_weight(state, perf, (8, 10), "maintenance", load_semantics="assistance")
    assert next_weight < state.current_working_weight


def test_recommend_working_weight_decreases_on_underperformance() -> None:
    state = ExerciseState(exercise_id="squat", current_working_weight=100, exposure_count=3)
    perf = LastPerformance(
        completed_reps=6,
        target_reps_min=8,
        target_reps_max=12,
        completed_sets=2,
        planned_sets=3,
    )

    next_weight = recommend_working_weight(state, perf, (8, 12), "cut")
    assert next_weight < state.current_working_weight


def test_recommend_working_weight_holds_early_underperformance_when_rules_require_more_exposures() -> None:
    state = ExerciseState(exercise_id="squat", current_working_weight=100, exposure_count=1)
    perf = LastPerformance(
        completed_reps=6,
        target_reps_min=8,
        target_reps_max=12,
        completed_sets=2,
        planned_sets=3,
    )

    next_weight = recommend_working_weight(state, perf, (8, 12), "maintenance", rule_set=_sample_rule_set())
    assert next_weight == state.current_working_weight


def test_update_exercise_state_tracks_under_target_streak_and_progression_action() -> None:
    state = ExerciseState(
        exercise_id="squat",
        current_working_weight=100,
        exposure_count=1,
        consecutive_under_target_exposures=1,
    )

    updated = update_exercise_state_after_workout(
        exercise_state=state,
        completed_reps=6,
        target_rep_range=(8, 12),
        completed_sets=2,
        planned_sets=3,
        phase_modifier="maintenance",
        rule_set=_sample_rule_set(),
    )

    assert updated.exposure_count == 2
    assert updated.consecutive_under_target_exposures == 2
    assert updated.last_progression_action == "hold"
