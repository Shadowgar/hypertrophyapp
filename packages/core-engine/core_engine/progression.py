from dataclasses import dataclass
from typing import Any

from .rules_runtime import resolve_progression_rule_runtime


PHASE_MULTIPLIER = {
    "cut": 0.85,
    "maintenance": 1.0,
    "bulk": 1.15,
}


def _underperformance_delta(
    *,
    current: float,
    exposure_count: int,
    reduce_percent: float,
    reduce_after_exposures: int,
) -> float:
    if reduce_after_exposures and exposure_count < reduce_after_exposures:
        return 0.0
    return -(reduce_percent / 100.0) * current


def _resolve_progression_outcome(
    *,
    exercise_state: "ExerciseState",
    last_performance: "LastPerformance",
    rep_range: tuple[int, int],
    phase_modifier: str,
    load_semantics: str | None = None,
    rule_set: dict[str, Any] | None,
) -> tuple[float, str, bool]:
    current = exercise_state.current_working_weight
    phase_factor = PHASE_MULTIPLIER.get(phase_modifier, 1.0)
    progression_runtime = resolve_progression_rule_runtime(rule_set)
    increase_percent = float(progression_runtime["increase_percent"])
    reduce_percent = float(progression_runtime["reduce_percent"])
    reduce_after_exposures = int(progression_runtime["reduce_after_exposures"])

    min_rep, max_rep = rep_range
    at_top = last_performance.completed_reps >= max_rep
    below_min = last_performance.completed_reps < min_rep
    sets_completed_ratio = (
        last_performance.completed_sets / max(last_performance.planned_sets, 1)
    )

    if below_min or sets_completed_ratio < 0.75:
        delta = _underperformance_delta(
            current=current,
            exposure_count=exercise_state.exposure_count,
            reduce_percent=reduce_percent,
            reduce_after_exposures=reduce_after_exposures,
        )
        progression_action = "reduce_load" if delta < 0 else "hold"
        under_target = True
    elif at_top and sets_completed_ratio >= 1.0:
        delta = (increase_percent / 100.0) * current * phase_factor
        progression_action = "increase_load"
        under_target = False
    else:
        delta = 0.0
        progression_action = "hold"
        under_target = False

    # Assisted-machine semantics: higher stack weight = more assistance (easier).
    # So making it "harder" means decreasing the recorded weight.
    if (load_semantics or "").strip().lower() == "assistance":
        if progression_action == "increase_load":
            delta = -abs(delta)
        elif progression_action == "reduce_load":
            delta = abs(delta)

    next_weight = max(2.0, current + delta)
    rounded_weight = round(next_weight / 0.5) * 0.5
    return rounded_weight, progression_action, under_target


@dataclass(slots=True)
class ExerciseState:
    exercise_id: str
    current_working_weight: float
    exposure_count: int
    consecutive_under_target_exposures: int = 0
    last_progression_action: str = "hold"
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
    load_semantics: str | None = None,
    rule_set: dict[str, Any] | None = None,
) -> float:
    next_weight, _progression_action, _under_target = _resolve_progression_outcome(
        exercise_state=exercise_state,
        last_performance=last_performance,
        rep_range=rep_range,
        phase_modifier=phase_modifier,
        load_semantics=load_semantics,
        rule_set=rule_set,
    )
    return next_weight


def update_exercise_state_after_workout(
    exercise_state: ExerciseState,
    completed_reps: int,
    target_rep_range: tuple[int, int],
    completed_sets: int,
    planned_sets: int,
    phase_modifier: str,
    load_semantics: str | None = None,
    rule_set: dict[str, Any] | None = None,
) -> ExerciseState:
    perf = LastPerformance(
        completed_reps=completed_reps,
        target_reps_min=target_rep_range[0],
        target_reps_max=target_rep_range[1],
        completed_sets=completed_sets,
        planned_sets=planned_sets,
    )

    next_weight, progression_action, under_target = _resolve_progression_outcome(
        exercise_state=exercise_state,
        last_performance=perf,
        rep_range=target_rep_range,
        phase_modifier=phase_modifier,
        load_semantics=load_semantics,
        rule_set=rule_set,
    )

    fatigue_delta = 0.2 if completed_sets >= planned_sets else 0.35
    if phase_modifier == "cut":
        fatigue_delta += 0.1

    return ExerciseState(
        exercise_id=exercise_state.exercise_id,
        current_working_weight=next_weight,
        exposure_count=exercise_state.exposure_count + 1,
        consecutive_under_target_exposures=(
            exercise_state.consecutive_under_target_exposures + 1 if under_target else 0
        ),
        last_progression_action=progression_action,
        fatigue_score=max(0.0, min(1.0, exercise_state.fatigue_score + fatigue_delta - 0.15)),
    )
