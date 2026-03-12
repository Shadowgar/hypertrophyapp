from __future__ import annotations

from typing import Any, Literal, cast

from .rules_runtime import evaluate_deload_signal, resolve_adaptive_rule_runtime
from .scheduler import generate_week_plan


ProgressionAction = Literal["progress", "hold", "deload"]
ProgramPhase = Literal["accumulation", "intensification", "deload"]


class TracedReadinessScore(int):
    decision_trace: dict[str, Any]

    def __new__(cls, value: int, decision_trace: dict[str, Any]) -> "TracedReadinessScore":
        instance = int.__new__(cls, value)
        instance.decision_trace = decision_trace
        return instance

    def __reduce__(self) -> tuple[Any, tuple[int, dict[str, Any]]]:
        return (self.__class__, (int(self), self.decision_trace))


_PROGRESSION_REASON_CLAUSES = {
    "low_completion": "session completion has been too low",
    "low_adherence": "adherence has dropped below the target threshold",
    "high_soreness": "fatigue and soreness are elevated",
}

_PHASE_TRANSITION_REASON_MESSAGES = {
    "resume_accumulation": "Deload work appears sufficient. Resume accumulation and rebuild workload.",
    "deload_complete": "Deload work appears sufficient. Resume accumulation and rebuild workload.",
    "extend_deload_low_readiness": "Stay in deload because readiness is still too low to resume hard training.",
    "intro_phase_protection": "Stay in accumulation. Early underperformance is still within the intro phase and should not be treated as a true stall.",
    "accumulation_stall": "Accumulation has stalled. Transition into deload to recover before rebuilding momentum.",
    "accumulation_complete": "Accumulation has run its course and readiness is high enough to move into intensification.",
    "continue_accumulation": "Stay in accumulation. Current readiness and momentum do not justify a phase change yet.",
    "intensification_fatigue_cap": "End intensification and deload before fatigue outpaces recovery.",
    "continue_intensification": "Stay in intensification. Current performance still supports heavier work in this phase.",
    "authored_sequence_complete": "The authored mesocycle is complete. Hold the final authored week only as a temporary fallback and rotate into the next planned template or phase.",
    "phase_apply": "Apply the recommended phase transition.",
}

_SORENESS_LEVEL = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3,
}


def _normalized_soreness_level(value: str | None) -> int:
    key = (value or "none").strip().lower()
    return _SORENESS_LEVEL.get(key, 0)


def _normalized_optional_scale(value: int | None) -> int | None:
    if value is None:
        return None
    return max(1, min(5, int(value)))


def _clamp_days(value: int) -> int:
    return max(2, min(7, int(value)))


def _looks_like_human_rationale(value: str) -> bool:
    text = value.strip()
    return bool(text) and "_" not in text and "+" not in text


def _humanize_reason_code(reason: str, *, empty_message: str = "No rationale recorded.") -> str:
    normalized = reason.strip()
    if not normalized:
        return empty_message
    if _looks_like_human_rationale(normalized):
        return normalized

    text = normalized.replace("_", " ").replace("+", " and ").strip()
    if not text:
        return empty_message
    return text[:1].upper() + text[1:] + "."


def _joined_clauses(clauses: list[str]) -> str:
    if not clauses:
        return "training stress and recovery signals are not aligned"
    if len(clauses) == 1:
        return clauses[0]
    if len(clauses) == 2:
        return f"{clauses[0]} and {clauses[1]}"
    return ", ".join(clauses[:-1]) + f", and {clauses[-1]}"


def _rule_dict(rule_set: dict[str, Any] | None, key: str) -> dict[str, Any]:
    if not isinstance(rule_set, dict):
        return {}
    value = rule_set.get(key)
    return value if isinstance(value, dict) else {}


def _rule_rationale(rule_set: dict[str, Any] | None, key: str, fallback: str) -> str:
    templates = _rule_dict(rule_set, "rationale_templates")
    value = templates.get(key)
    return value if isinstance(value, str) and value.strip() else fallback


def _deload_response(config: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "action": "deload",
        "load_scale": config["deload_load_scale"],
        "set_delta": config["deload_set_delta"],
        "reason": reason,
    }


def _hold_response(reason: str) -> dict[str, Any]:
    return {
        "action": "hold",
        "load_scale": 1.0,
        "set_delta": 0,
        "reason": reason,
    }


def _progress_response(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": "progress",
        "load_scale": config["progress_load_scale"],
        "set_delta": 0,
        "reason": config["progress_reason"],
    }


def _accumulation_phase_transition(
    *,
    weeks_in_phase: int,
    readiness_score: int,
    progression_action: ProgressionAction,
    stagnation_weeks: int,
    intro_weeks: int,
) -> dict[str, Any]:
    if intro_weeks and weeks_in_phase <= intro_weeks and stagnation_weeks >= 1:
        return {"next_phase": "accumulation", "reason": "intro_phase_protection"}
    if stagnation_weeks >= 2 or readiness_score < 55:
        return {"next_phase": "deload", "reason": "accumulation_stall"}
    if weeks_in_phase >= 6 and progression_action == "progress" and readiness_score >= 65:
        return {"next_phase": "intensification", "reason": "accumulation_complete"}
    return {"next_phase": "accumulation", "reason": "continue_accumulation"}


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
    changed_muscles = {muscle: delta for muscle, delta in volume_delta.items() if delta != 0}

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


def humanize_progression_reason(
    progression: dict[str, Any],
    *,
    rule_set: dict[str, Any] | None = None,
) -> str:
    reason = str(progression.get("reason") or "").strip()
    if _looks_like_human_rationale(reason):
        return reason

    if "+" in reason:
        clauses = [_PROGRESSION_REASON_CLAUSES.get(token, token.replace("_", " ")) for token in reason.split("+") if token]
        return f"Deload because {_joined_clauses(clauses)}."

    if reason == "under_target_without_high_fatigue":
        return "Performance is below target without clear high-fatigue signals. Hold load and accumulate cleaner exposures before changing phase or deloading."
    if reason == "sfr_high_deload_pressure":
        return "Recovery capacity looks too limited to keep pushing productively. Deload before fatigue compounds further."

    action = str(progression.get("action") or "hold")
    if action == "progress":
        return _rule_rationale(
            rule_set,
            "increase_load",
            "Readiness and performance support progressing load on the next exposure.",
        )
    if action == "deload":
        return _rule_rationale(
            rule_set,
            "deload",
            "Current fatigue and performance signals support a short deload before pushing harder again.",
        )
    if action == "hold":
        return _rule_rationale(
            rule_set,
            "hold_load",
            "Current performance supports holding load while accumulating more stable work.",
        )
    return _humanize_reason_code(reason)


def humanize_phase_transition_reason(phase_transition: dict[str, Any]) -> str:
    reason = str(phase_transition.get("reason") or "").strip()
    if _looks_like_human_rationale(reason):
        return reason
    return _PHASE_TRANSITION_REASON_MESSAGES.get(reason, _humanize_reason_code(reason))


def derive_readiness_score(
    *,
    completion_pct: int,
    adherence_score: int,
    soreness_level: str,
    progression_action: str,
    sleep_quality: int | None = None,
    stress_level: int | None = None,
    pain_flags: list[str] | None = None,
) -> TracedReadinessScore:
    soreness_penalty_by_level = {
        "none": 0,
        "mild": 4,
        "moderate": 10,
        "severe": 18,
    }
    action_penalty = {
        "progress": 0,
        "hold": 5,
        "deload": 18,
    }
    normalized_completion_pct = max(0, min(100, int(completion_pct)))
    normalized_adherence = max(1, min(5, int(adherence_score)))
    normalized_soreness = str(soreness_level or "none").strip().lower()
    normalized_progression_action = str(progression_action or "hold").strip()
    soreness_penalty = soreness_penalty_by_level.get(normalized_soreness, 0)
    readiness = int((0.65 * normalized_completion_pct) + (8 * normalized_adherence))
    readiness -= soreness_penalty
    readiness -= action_penalty.get(normalized_progression_action, 0)
    sleep_penalty = 0
    if sleep_quality is not None:
        normalized_sleep = max(1, min(5, int(sleep_quality)))
        if normalized_sleep <= 2:
            sleep_penalty = 8
        elif normalized_sleep == 3:
            sleep_penalty = 3
        readiness -= sleep_penalty
    else:
        normalized_sleep = None
    stress_penalty = 0
    if stress_level is not None:
        normalized_stress = max(1, min(5, int(stress_level)))
        if normalized_stress >= 4:
            stress_penalty = 8
        elif normalized_stress == 3:
            stress_penalty = 3
        readiness -= stress_penalty
    else:
        normalized_stress = None
    pain_penalty = 0
    if pain_flags:
        pain_penalty = 6
        readiness -= pain_penalty
    normalized_readiness = max(0, min(100, readiness))
    decision_trace = {
        "interpreter": "derive_readiness_score",
        "version": "v1",
        "inputs": {
            "completion_pct": normalized_completion_pct,
            "adherence_score": normalized_adherence,
            "soreness_level": normalized_soreness,
            "progression_action": normalized_progression_action,
            "sleep_quality": normalized_sleep,
            "stress_level": normalized_stress,
            "pain_flags": [str(flag).strip() for flag in (pain_flags or []) if str(flag).strip()],
        },
        "steps": [
            {
                "decision": "apply_penalties",
                "result": {
                    "soreness_penalty": soreness_penalty,
                    "action_penalty": action_penalty.get(normalized_progression_action, 0),
                    "sleep_penalty": sleep_penalty,
                    "stress_penalty": stress_penalty,
                    "pain_penalty": pain_penalty,
                },
            }
        ],
        "outcome": {
            "readiness_score": normalized_readiness,
        },
    }
    return TracedReadinessScore(normalized_readiness, decision_trace)


def evaluate_stimulus_fatigue_response(
    *,
    completion_pct: int,
    adherence_score: int,
    soreness_level: str,
    average_rpe: float | None = None,
    consecutive_underperformance_weeks: int = 0,
    sleep_quality: int | None = None,
    stress_level: int | None = None,
    pain_flags: list[str] | None = None,
) -> dict[str, Any]:
    completion_pct = max(0, min(100, int(completion_pct)))
    adherence_score = max(1, min(5, int(adherence_score)))
    soreness_rank = _normalized_soreness_level(soreness_level)
    underperf = max(0, int(consecutive_underperformance_weeks))
    normalized_sleep = _normalized_optional_scale(sleep_quality)
    normalized_stress = _normalized_optional_scale(stress_level)
    normalized_pain_flags = [str(item).strip() for item in (pain_flags or []) if str(item).strip()]
    normalized_rpe = float(average_rpe) if isinstance(average_rpe, (int, float)) else None

    stimulus_signals: list[str] = []
    if completion_pct >= 90:
        stimulus_signals.append("high_completion")
    elif completion_pct < 75:
        stimulus_signals.append("low_completion")
    if adherence_score >= 4:
        stimulus_signals.append("high_adherence")
    elif adherence_score <= 2:
        stimulus_signals.append("low_adherence")
    if underperf >= 2:
        stimulus_signals.append("underperformance_streak")

    if completion_pct >= 90 and adherence_score >= 4 and underperf == 0:
        stimulus_quality = "high"
    elif completion_pct < 75 or adherence_score <= 2 or underperf >= 2:
        stimulus_quality = "low"
    else:
        stimulus_quality = "moderate"

    fatigue_signals: list[str] = []
    if soreness_rank >= 2:
        fatigue_signals.append("elevated_soreness")
    if normalized_rpe is not None and normalized_rpe >= 9.0:
        fatigue_signals.append("high_rpe")
    if normalized_sleep is not None and normalized_sleep <= 2:
        fatigue_signals.append("low_sleep")
    if normalized_stress is not None and normalized_stress >= 4:
        fatigue_signals.append("high_stress")
    if normalized_pain_flags:
        fatigue_signals.append("pain_flags_present")

    if soreness_rank >= 3 or (normalized_rpe is not None and normalized_rpe >= 9.5) or len(fatigue_signals) >= 2:
        fatigue_cost = "high"
    elif soreness_rank <= 1 and (normalized_rpe is None or normalized_rpe <= 8.0) and not fatigue_signals:
        fatigue_cost = "low"
    else:
        fatigue_cost = "moderate"

    recoverability_signals: list[str] = []
    if normalized_sleep is not None and normalized_sleep <= 2:
        recoverability_signals.append("sleep_limited")
    if normalized_stress is not None and normalized_stress >= 4:
        recoverability_signals.append("stress_limited")
    if normalized_pain_flags:
        recoverability_signals.append("pain_limited")
    if fatigue_cost == "high":
        recoverability_signals.append("fatigue_limited")

    if recoverability_signals:
        recoverability = "low" if fatigue_cost == "high" or len(recoverability_signals) >= 2 else "moderate"
    elif fatigue_cost == "low" and adherence_score >= 4 and completion_pct >= 85:
        recoverability = "high"
    else:
        recoverability = "moderate"

    progression_eligibility = (
        stimulus_quality == "high"
        and fatigue_cost != "high"
        and recoverability != "low"
    )

    if underperf >= 2 or (fatigue_cost == "high" and recoverability == "low"):
        deload_pressure = "high"
    elif underperf >= 1 or fatigue_cost == "high" or recoverability == "low":
        deload_pressure = "moderate"
    else:
        deload_pressure = "low"

    if normalized_pain_flags and fatigue_cost == "high":
        substitution_pressure = "high"
    elif normalized_pain_flags:
        substitution_pressure = "moderate"
    else:
        substitution_pressure = "low"

    decision_trace = {
        "interpreter": "evaluate_stimulus_fatigue_response",
        "version": "v1",
        "inputs": {
            "completion_pct": completion_pct,
            "adherence_score": adherence_score,
            "soreness_level": str(soreness_level or "").strip().lower(),
            "average_rpe": normalized_rpe,
            "consecutive_underperformance_weeks": underperf,
            "sleep_quality": normalized_sleep,
            "stress_level": normalized_stress,
            "pain_flags": normalized_pain_flags,
        },
        "steps": [
            {
                "decision": "classify_stimulus_fatigue_recovery",
                "result": {
                    "stimulus_signals": list(stimulus_signals),
                    "fatigue_signals": list(fatigue_signals),
                    "recoverability_signals": list(recoverability_signals),
                },
            }
        ],
        "outcome": {
            "stimulus_quality": stimulus_quality,
            "fatigue_cost": fatigue_cost,
            "recoverability": recoverability,
            "progression_eligibility": progression_eligibility,
            "deload_pressure": deload_pressure,
            "substitution_pressure": substitution_pressure,
        },
    }
    return {
        "stimulus_quality": stimulus_quality,
        "fatigue_cost": fatigue_cost,
        "recoverability": recoverability,
        "progression_eligibility": progression_eligibility,
        "deload_pressure": deload_pressure,
        "substitution_pressure": substitution_pressure,
        "signals": {
            "stimulus": stimulus_signals,
            "fatigue": fatigue_signals,
            "recoverability": recoverability_signals,
        },
        "decision_trace": decision_trace,
    }


def recommend_progression_action(
    *,
    completion_pct: int,
    adherence_score: int,
    soreness_level: str,
    average_rpe: float | None = None,
    consecutive_underperformance_weeks: int = 0,
    rule_set: dict[str, Any] | None = None,
    sleep_quality: int | None = None,
    stress_level: int | None = None,
    pain_flags: list[str] | None = None,
) -> dict[str, Any]:
    completion_pct = max(0, min(100, int(completion_pct)))
    adherence_score = max(1, min(5, int(adherence_score)))
    soreness_rank = _normalized_soreness_level(soreness_level)
    underperf = max(0, int(consecutive_underperformance_weeks))
    config = resolve_adaptive_rule_runtime(rule_set)
    stimulus_fatigue_response = evaluate_stimulus_fatigue_response(
        completion_pct=completion_pct,
        adherence_score=adherence_score,
        soreness_level=soreness_level,
        average_rpe=average_rpe,
        consecutive_underperformance_weeks=underperf,
        sleep_quality=sleep_quality,
        stress_level=stress_level,
        pain_flags=pain_flags,
    )
    deload_signal = evaluate_deload_signal(
        completion_pct=completion_pct,
        adherence_score=adherence_score,
        soreness_rank=soreness_rank,
        average_rpe=average_rpe,
        consecutive_underperformance_weeks=underperf,
        rule_set=rule_set,
    )

    decision: dict[str, Any]
    if deload_signal["forced_deload_reasons"]:
        decision = {
            **_deload_response(
                config,
                "+".join(cast(list[str], deload_signal["forced_deload_reasons"])) or str(config["deload_reason"]),
            ),
            "stimulus_fatigue_response": stimulus_fatigue_response,
        }
    elif (
        stimulus_fatigue_response["deload_pressure"] == "high"
        and stimulus_fatigue_response["recoverability"] == "low"
    ):
        decision = {
            **_deload_response(config, "sfr_high_deload_pressure"),
            "stimulus_fatigue_response": stimulus_fatigue_response,
        }
    elif underperf >= int(config["underperf_threshold"]):
        if bool(deload_signal["underperformance_deload_matched"]):
            decision = {
                **_deload_response(config, str(config["deload_reason"])),
                "stimulus_fatigue_response": stimulus_fatigue_response,
            }
        else:
            decision = {
                **_hold_response("under_target_without_high_fatigue"),
                "stimulus_fatigue_response": stimulus_fatigue_response,
            }
    elif (
        completion_pct >= 95
        and adherence_score >= 4
        and soreness_rank <= 1
        and (average_rpe is None or float(average_rpe) <= 9.0)
    ):
        decision = {
            **_progress_response(config),
            "stimulus_fatigue_response": stimulus_fatigue_response,
        }
    else:
        decision = {
            **_hold_response(config["hold_reason"]),
            "stimulus_fatigue_response": stimulus_fatigue_response,
        }

    decision["decision_trace"] = {
        "interpreter": "recommend_progression_action",
        "version": "v1",
        "inputs": {
            "completion_pct": completion_pct,
            "adherence_score": adherence_score,
            "soreness_level": str(soreness_level or "").strip().lower(),
            "average_rpe": float(average_rpe) if isinstance(average_rpe, (int, float)) else None,
            "consecutive_underperformance_weeks": underperf,
            "sleep_quality": sleep_quality,
            "stress_level": stress_level,
            "pain_flags": [str(item).strip() for item in (pain_flags or []) if str(item).strip()],
        },
        "steps": [
            {
                "decision": "evaluate_stimulus_fatigue_response",
                "result": cast(dict[str, Any], stimulus_fatigue_response["decision_trace"]).get("outcome", {}),
            },
            {
                "decision": "evaluate_deload_signal",
                "result": {
                    "forced_deload_reasons": list(cast(list[str], deload_signal["forced_deload_reasons"])),
                    "underperformance_deload_matched": bool(deload_signal["underperformance_deload_matched"]),
                },
            },
        ],
        "outcome": {
            "action": str(decision.get("action") or ""),
            "reason": str(decision.get("reason") or ""),
            "load_scale": float(decision.get("load_scale") or 0),
            "set_delta": int(decision.get("set_delta") or 0),
        },
    }
    return decision


def recommend_phase_transition(
    *,
    current_phase: ProgramPhase,
    weeks_in_phase: int,
    readiness_score: int,
    progression_action: ProgressionAction,
    stagnation_weeks: int = 0,
    rule_set: dict[str, Any] | None = None,
    authored_sequence_complete: bool = False,
    phase_transition_pending: bool = False,
    phase_transition_reason: str | None = None,
    post_authored_behavior: str | None = None,
) -> dict[str, Any]:
    weeks_in_phase = max(1, int(weeks_in_phase))
    readiness_score = max(0, min(100, int(readiness_score)))
    stagnation_weeks = max(0, int(stagnation_weeks))
    adaptive_runtime = resolve_adaptive_rule_runtime(rule_set)
    intro_weeks = int(adaptive_runtime["intro_weeks"])
    scheduled_deload_weeks = int(adaptive_runtime["scheduled_deload_weeks"])

    transition: dict[str, Any]
    if (
        bool(authored_sequence_complete)
        or bool(phase_transition_pending)
        or str(phase_transition_reason or "").strip() == "authored_sequence_complete"
    ):
        transition = {
            "next_phase": current_phase,
            "reason": "authored_sequence_complete",
            "authored_sequence_complete": True,
            "transition_pending": True,
            "recommended_action": "rotate_program",
            "post_authored_behavior": str(post_authored_behavior or "hold_last_authored_week"),
        }
    elif current_phase == "deload":
        if readiness_score >= 70:
            transition = {"next_phase": "accumulation", "reason": "deload_complete"}
        else:
            transition = {"next_phase": "deload", "reason": "extend_deload_low_readiness"}
    elif current_phase == "accumulation":
        transition = _accumulation_phase_transition(
            weeks_in_phase=weeks_in_phase,
            readiness_score=readiness_score,
            progression_action=progression_action,
            stagnation_weeks=stagnation_weeks,
            intro_weeks=intro_weeks,
        )
    elif progression_action == "deload" or weeks_in_phase >= min(4, scheduled_deload_weeks) or stagnation_weeks >= 2:
        transition = {"next_phase": "deload", "reason": "intensification_fatigue_cap"}
    else:
        transition = {"next_phase": "intensification", "reason": "continue_intensification"}

    transition["decision_trace"] = {
        "interpreter": "recommend_phase_transition",
        "version": "v1",
        "inputs": {
            "current_phase": current_phase,
            "weeks_in_phase": weeks_in_phase,
            "readiness_score": readiness_score,
            "progression_action": progression_action,
            "stagnation_weeks": stagnation_weeks,
            "authored_sequence_complete": bool(authored_sequence_complete),
            "phase_transition_pending": bool(phase_transition_pending),
            "phase_transition_reason": str(phase_transition_reason or ""),
            "post_authored_behavior": str(post_authored_behavior or ""),
        },
        "steps": [
            {
                "decision": "phase_transition_policy",
                "result": {
                    "intro_weeks": intro_weeks,
                    "scheduled_deload_weeks": scheduled_deload_weeks,
                },
            }
        ],
        "outcome": {
            "next_phase": str(transition.get("next_phase") or ""),
            "reason": str(transition.get("reason") or ""),
            "transition_pending": bool(transition.get("transition_pending")),
            "recommended_action": str(transition.get("recommended_action") or ""),
        },
    }
    return transition
