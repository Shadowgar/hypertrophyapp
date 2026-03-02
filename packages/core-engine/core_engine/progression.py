from dataclasses import dataclass


PHASE_MULTIPLIER = {
    "cut": 0.85,
    "maintenance": 1.0,
    "bulk": 1.15,
}


@dataclass(slots=True)
class ExerciseState:
    exercise_id: str
    current_working_weight: float
    exposure_count: int
    fatigue_score: float = 0.0


@dataclass(slots=True)
class LastPerformance:
    completed_reps: int
    target_reps_min: int
    target_reps_max: int
    completed_sets: int
    planned_sets: int


def recommend_working_weight(
    exercise_state: ExerciseState,
    last_performance: LastPerformance,
    rep_range: tuple[int, int],
    phase_modifier: str,
) -> float:
    current = exercise_state.current_working_weight
    phase_factor = PHASE_MULTIPLIER.get(phase_modifier, 1.0)

    min_rep, max_rep = rep_range
    at_top = last_performance.completed_reps >= max_rep
    below_min = last_performance.completed_reps < min_rep
    sets_completed_ratio = (
        last_performance.completed_sets / max(last_performance.planned_sets, 1)
    )

    if below_min or sets_completed_ratio < 0.75:
        delta = -0.02 * current
    elif at_top and sets_completed_ratio >= 1.0:
        delta = 0.025 * current * phase_factor
    else:
        delta = 0.0

    next_weight = max(5.0, current + delta)
    return round(next_weight / 2.5) * 2.5


def update_exercise_state_after_workout(
    exercise_state: ExerciseState,
    completed_reps: int,
    target_rep_range: tuple[int, int],
    completed_sets: int,
    planned_sets: int,
    phase_modifier: str,
) -> ExerciseState:
    perf = LastPerformance(
        completed_reps=completed_reps,
        target_reps_min=target_rep_range[0],
        target_reps_max=target_rep_range[1],
        completed_sets=completed_sets,
        planned_sets=planned_sets,
    )

    next_weight = recommend_working_weight(
        exercise_state=exercise_state,
        last_performance=perf,
        rep_range=target_rep_range,
        phase_modifier=phase_modifier,
    )

    fatigue_delta = 0.2 if completed_sets >= planned_sets else 0.35
    if phase_modifier == "cut":
        fatigue_delta += 0.1

    return ExerciseState(
        exercise_id=exercise_state.exercise_id,
        current_working_weight=next_weight,
        exposure_count=exercise_state.exposure_count + 1,
        fatigue_score=max(0.0, min(1.0, exercise_state.fatigue_score + fatigue_delta - 0.15)),
    )
