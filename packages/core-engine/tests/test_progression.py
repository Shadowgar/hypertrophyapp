from core_engine.progression import ExerciseState, LastPerformance, recommend_working_weight


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
