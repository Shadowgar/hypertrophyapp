from __future__ import annotations

from typing import Any, Literal

from .scheduler import generate_week_plan
from .warmups import compute_warmups


ProgressionAction = Literal["progress", "hold", "deload"]
ProgramPhase = Literal["accumulation", "intensification", "deload"]


_SORENESS_LEVEL = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3,
}


def _normalized_soreness_level(value: str | None) -> int:
    key = (value or "none").strip().lower()
    return _SORENESS_LEVEL.get(key, 0)


def _clamp_days(value: int) -> int:
    return max(2, min(7, int(value)))


def _muscle_set_delta(
    from_volume: dict[str, int],
    to_volume: dict[str, int],
) -> dict[str, int]:
    muscles = sorted(set(from_volume).union(to_volume))
    return {muscle: int(to_volume.get(muscle, 0)) - int(from_volume.get(muscle, 0)) for muscle in muscles}


def _tradeoff_risk_level(delta_by_muscle: dict[str, int]) -> str:
    steep_losses = [delta for delta in delta_by_muscle.values() if delta <= -3]
    moderate_losses = [delta for delta in delta_by_muscle.values() if -3 < delta <= -1]
    if steep_losses:
        return "high"
    if moderate_losses:
        return "medium"
    return "low"


def _sorted_session_titles(plan: dict[str, Any]) -> list[str]:
    return [str(session.get("title") or session.get("session_id") or "") for session in plan.get("sessions", [])]


def evaluate_schedule_adaptation(
    *,
    user_profile: dict[str, Any],
    split_preference: str,
    program_template: dict[str, Any],
    history: list[dict[str, Any]],
    phase: str,
    from_days: int,
    to_days: int,
    available_equipment: list[str] | None = None,
    soreness_by_muscle: dict[str, str] | None = None,
) -> dict[str, Any]:
    from_days = _clamp_days(from_days)
    to_days = _clamp_days(to_days)

    base_plan = generate_week_plan(
        user_profile=user_profile,
        days_available=from_days,
        split_preference=split_preference,
        program_template=program_template,
        history=history,
        phase=phase,
        available_equipment=available_equipment,
        soreness_by_muscle=soreness_by_muscle,
    )
    adapted_plan = generate_week_plan(
        user_profile=user_profile,
        days_available=to_days,
        split_preference=split_preference,
        program_template=program_template,
        history=history,
        phase=phase,
        available_equipment=available_equipment,
        soreness_by_muscle=soreness_by_muscle,
    )

    base_titles = _sorted_session_titles(base_plan)
    adapted_titles = _sorted_session_titles(adapted_plan)
    kept_titles = sorted(set(base_titles).intersection(adapted_titles))
    dropped_titles = [title for title in base_titles if title not in kept_titles]
    added_titles = [title for title in adapted_titles if title not in kept_titles]

    volume_delta = _muscle_set_delta(
        from_volume=base_plan.get("weekly_volume_by_muscle", {}),
        to_volume=adapted_plan.get("weekly_volume_by_muscle", {}),
    )
    changed_muscles = {
        muscle: delta for muscle, delta in volume_delta.items() if delta != 0
    }

    tradeoffs: list[str] = []
    if to_days < from_days:
        tradeoffs.append("Higher per-session density due to fewer training days.")
    if to_days > from_days:
        tradeoffs.append("Lower per-session density with more distributed weekly stress.")
    if dropped_titles:
        tradeoffs.append("Some original sessions are dropped to preserve priority lift continuity.")
    if changed_muscles:
        tradeoffs.append("Weekly set distribution shifts across muscle groups.")

    return {
        "from_days": from_days,
        "to_days": to_days,
        "kept_sessions": kept_titles,
        "dropped_sessions": dropped_titles,
        "added_sessions": added_titles,
        "muscle_set_delta": changed_muscles,
        "risk_level": _tradeoff_risk_level(changed_muscles),
        "tradeoffs": tradeoffs,
        "from_plan": base_plan,
        "to_plan": adapted_plan,
    }


def recommend_progression_action(
    *,
    completion_pct: int,
    adherence_score: int,
    soreness_level: str,
    average_rpe: float | None = None,
    consecutive_underperformance_weeks: int = 0,
) -> dict[str, Any]:
    completion_pct = max(0, min(100, int(completion_pct)))
    adherence_score = max(1, min(5, int(adherence_score)))
    soreness_rank = _normalized_soreness_level(soreness_level)
    underperf = max(0, int(consecutive_underperformance_weeks))

    if completion_pct < 70 or adherence_score <= 2 or soreness_rank >= 3 or underperf >= 2:
        reasons = []
        if completion_pct < 70:
            reasons.append("low_completion")
        if adherence_score <= 2:
            reasons.append("low_adherence")
        if soreness_rank >= 3:
            reasons.append("high_soreness")
        if underperf >= 2:
            reasons.append("multi_week_underperformance")
        return {
            "action": "deload",
            "load_scale": 0.9,
            "set_delta": -1,
            "reason": "+".join(reasons),
        }

    if (
        completion_pct >= 95
        and adherence_score >= 4
        and soreness_rank <= 1
        and (average_rpe is None or float(average_rpe) <= 9.0)
    ):
        return {
            "action": "progress",
            "load_scale": 1.025,
            "set_delta": 0,
            "reason": "high_readiness_progression",
        }

    return {
        "action": "hold",
        "load_scale": 1.0,
        "set_delta": 0,
        "reason": "maintain_until_stable",
    }


def recommend_phase_transition(
    *,
    current_phase: ProgramPhase,
    weeks_in_phase: int,
    readiness_score: int,
    progression_action: ProgressionAction,
    stagnation_weeks: int = 0,
) -> dict[str, Any]:
    weeks_in_phase = max(1, int(weeks_in_phase))
    readiness_score = max(0, min(100, int(readiness_score)))
    stagnation_weeks = max(0, int(stagnation_weeks))

    if current_phase == "deload":
        if readiness_score >= 70:
            return {"next_phase": "accumulation", "reason": "deload_complete"}
        return {"next_phase": "deload", "reason": "extend_deload_low_readiness"}

    if current_phase == "accumulation":
        if stagnation_weeks >= 2 or readiness_score < 55:
            return {"next_phase": "deload", "reason": "accumulation_stall"}
        if weeks_in_phase >= 6 and progression_action == "progress" and readiness_score >= 65:
            return {"next_phase": "intensification", "reason": "accumulation_complete"}
        return {"next_phase": "accumulation", "reason": "continue_accumulation"}

    # intensification
    if progression_action == "deload" or weeks_in_phase >= 4 or stagnation_weeks >= 2:
        return {"next_phase": "deload", "reason": "intensification_fatigue_cap"}
    return {"next_phase": "intensification", "reason": "continue_intensification"}


def recommend_specialization_adjustments(
    *,
    weekly_volume_by_muscle: dict[str, int],
    lagging_muscles: list[str],
    max_focus_muscles: int = 2,
    target_min_sets: int = 8,
) -> dict[str, Any]:
    normalized_lagging = {
        muscle.strip().lower()
        for muscle in lagging_muscles
        if muscle and muscle.strip().lower() in weekly_volume_by_muscle
    }
    ranked_focus = sorted(
        normalized_lagging,
        key=lambda muscle: (int(weekly_volume_by_muscle.get(muscle, 0)), muscle),
    )[: max(1, int(max_focus_muscles))]

    focus_adjustments: dict[str, int] = {}
    for muscle in ranked_focus:
        current_sets = int(weekly_volume_by_muscle.get(muscle, 0))
        focus_adjustments[muscle] = 2 if current_sets < target_min_sets else 1

    total_added_sets = sum(focus_adjustments.values())
    donor_candidates = sorted(
        [
            (muscle, int(sets))
            for muscle, sets in weekly_volume_by_muscle.items()
            if muscle not in ranked_focus and int(sets) > target_min_sets
        ],
        key=lambda row: (-row[1], row[0]),
    )

    donor_adjustments: dict[str, int] = {}
    remaining = total_added_sets
    for donor, sets in donor_candidates:
        if remaining <= 0:
            break
        allowed_drop = min(1, sets - target_min_sets)
        if allowed_drop <= 0:
            continue
        donor_adjustments[donor] = -allowed_drop
        remaining -= allowed_drop

    return {
        "focus_muscles": ranked_focus,
        "focus_adjustments": focus_adjustments,
        "donor_adjustments": donor_adjustments,
        "uncompensated_added_sets": max(0, remaining),
    }


def summarize_program_media_and_warmups(program_template: dict[str, Any]) -> dict[str, Any]:
    exercises: list[dict[str, Any]] = []
    for session in program_template.get("sessions", []):
        exercises.extend(session.get("exercises", []))

    total_exercises = len(exercises)
    with_video = 0
    sample_warmups: list[dict[str, Any]] = []

    for exercise in exercises:
        video = exercise.get("video") if isinstance(exercise.get("video"), dict) else {}
        if isinstance(video, dict) and str(video.get("youtube_url") or "").strip():
            with_video += 1

        start_weight = float(exercise.get("start_weight") or 0)
        if start_weight > 0 and len(sample_warmups) < 3:
            sample_warmups.append(
                {
                    "exercise_id": str(exercise.get("id") or ""),
                    "warmups": compute_warmups(start_weight),
                }
            )

    coverage_pct = round((with_video / total_exercises) * 100, 1) if total_exercises else 0.0
    return {
        "total_exercises": total_exercises,
        "video_linked_exercises": with_video,
        "video_coverage_pct": coverage_pct,
        "sample_warmups": sample_warmups,
    }
