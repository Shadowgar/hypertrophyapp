from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .decision_progression import evaluate_stimulus_fatigue_response
from .intelligence import resolve_latest_logged_workout_resume_state, resolve_workout_today_session_selection


def _read_attr(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _normalize_logs(recent_workout_logs: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in recent_workout_logs:
        created_at = _coerce_datetime(_read_attr(row, "created_at"))
        normalized.append(
            {
                "workout_id": str(_read_attr(row, "workout_id", "") or ""),
                "primary_exercise_id": str(_read_attr(row, "primary_exercise_id", "") or ""),
                "exercise_id": str(_read_attr(row, "exercise_id", "") or ""),
                "set_index": int(_read_attr(row, "set_index", 1) or 1),
                "reps": int(_read_attr(row, "reps", 0) or 0),
                "weight": float(_read_attr(row, "weight", 0) or 0),
                "rpe": _read_attr(row, "rpe"),
                "created_at": created_at,
            }
        )
    return normalized


def _derive_day_id(
    *,
    selected_session: dict[str, Any] | None,
    sessions: list[dict[str, Any]],
    week_start: date | None,
    week_index: int,
) -> str | None:
    if selected_session is None:
        return None

    explicit_day_id = str(selected_session.get("day_id") or "").strip()
    if explicit_day_id:
        return explicit_day_id

    session_date = _coerce_date(selected_session.get("date"))
    if week_start is not None and session_date is not None:
        day_number = (session_date - week_start).days + 1
        if 1 <= day_number <= 7:
            return f"w{week_index}d{day_number}"

    session_id = str(selected_session.get("session_id") or "")
    ordered_session_ids = [str(session.get("session_id") or "") for session in sessions]
    if session_id and session_id in ordered_session_ids:
        return f"w{week_index}d{ordered_session_ids.index(session_id) + 1}"

    return None


def _resolve_session_selection(
    *,
    sessions: list[dict[str, Any]],
    normalized_logs: list[dict[str, Any]],
    today: date,
) -> dict[str, Any] | None:
    if not sessions:
        return None

    logs_desc = sorted(
        normalized_logs,
        key=lambda row: row["created_at"] or datetime.min,
        reverse=True,
    )
    resume_state = resolve_latest_logged_workout_resume_state(
        sessions=sessions,
        performed_logs=logs_desc,
    )
    selection = resolve_workout_today_session_selection(
        sessions=sessions,
        latest_logged_workout_id=resume_state["latest_logged_workout_id"],
        latest_logged_session_incomplete=bool(resume_state["latest_logged_session_incomplete"]),
        today_iso=today.isoformat(),
    )
    selected_session = selection.get("selected_session")
    return _coerce_dict(selected_session) if isinstance(selected_session, dict) else None


def _derive_recovery_state(*, severe_soreness_count: int, session_rpe_avg: float | None) -> str:
    if severe_soreness_count >= 2:
        return "high_fatigue"
    if session_rpe_avg is not None and session_rpe_avg >= 9:
        return "high_fatigue"
    if severe_soreness_count == 1:
        return "low"
    if session_rpe_avg is not None and session_rpe_avg >= 8.5:
        return "low"
    return "normal"


def _count_missed_sessions(
    *,
    sessions: list[dict[str, Any]],
    normalized_logs: list[dict[str, Any]],
    today: date,
) -> int:
    logged_workout_ids = {str(row["workout_id"] or "") for row in normalized_logs if str(row["workout_id"] or "")}
    missed = 0
    for session in sessions:
        session_id = str(session.get("session_id") or "")
        session_date = _coerce_date(session.get("date"))
        if not session_id or session_date is None:
            continue
        if session_date < today and session_id not in logged_workout_ids:
            missed += 1
    return missed


def _review_indicates_underperformance(review: Any) -> bool:
    summary = _coerce_dict(_read_attr(review, "summary", {}))
    adjustments = _coerce_dict(_read_attr(review, "adjustments", {}))
    global_adjustment = _coerce_dict(adjustments.get("global"))

    faulty_exercise_count = int(
        summary.get("faulty_exercise_count")
        or len(summary.get("exercise_faults") or [])
        or 0
    )
    set_delta = int(global_adjustment.get("set_delta") or 0)
    weight_scale = float(global_adjustment.get("weight_scale") or 1)
    return faulty_exercise_count > 0 or set_delta < 0 or weight_scale < 1


def _count_consecutive_underperformance_weeks(recent_review_cycles: list[Any]) -> int:
    count = 0
    for review in recent_review_cycles:
        if not _review_indicates_underperformance(review):
            break
        count += 1
    return count


def _derive_program_id_from_session_id(session_id: str) -> str | None:
    day_delimiter = "-day-"
    if day_delimiter in session_id:
        prefix, _, suffix = session_id.partition(day_delimiter)
        if prefix and suffix.isdigit():
            return prefix

    prefix, separator, suffix = session_id.rpartition("-")
    if separator and suffix.isdigit() and prefix:
        return prefix
    return None


def _collect_plan_program_ids(payload: dict[str, Any]) -> set[str]:
    program_ids: set[str] = set()
    payload_program_id = str(payload.get("program_template_id") or "").strip()
    if payload_program_id:
        program_ids.add(payload_program_id)

    for session in payload.get("sessions") or []:
        if not isinstance(session, dict):
            continue
        session_program_id = _derive_program_id_from_session_id(str(session.get("session_id") or ""))
        if session_program_id:
            program_ids.add(session_program_id)

    return program_ids


def _count_prior_generated_weeks_by_program(prior_plans: list[Any]) -> dict[str, int]:
    weeks_by_program: dict[str, set[str]] = {}

    for plan in prior_plans:
        payload = _coerce_dict(_read_attr(plan, "payload", {}))
        week_start = _coerce_date(_read_attr(plan, "week_start")) or _coerce_date(payload.get("week_start"))
        if week_start is None:
            continue

        for program_id in _collect_plan_program_ids(payload):
            weeks_by_program.setdefault(program_id, set()).add(week_start.isoformat())

    return {
        program_id: len(week_keys)
        for program_id, week_keys in sorted(weeks_by_program.items())
    }


def _resolve_plan_context(latest_plan: Any | None) -> tuple[dict[str, Any], list[dict[str, Any]], date | None, int]:
    latest_plan_payload = _coerce_dict(_read_attr(latest_plan, "payload", {}))
    sessions = [
        _coerce_dict(session)
        for session in (latest_plan_payload.get("sessions") or [])
        if isinstance(session, dict)
    ]
    week_start = _coerce_date(latest_plan_payload.get("week_start")) or _coerce_date(
        _read_attr(latest_plan, "week_start")
    )
    mesocycle = _coerce_dict(latest_plan_payload.get("mesocycle"))
    week_index = max(1, int(mesocycle.get("week_index", 1) or 1))
    return latest_plan_payload, sessions, week_start, week_index


def _resolve_session_rpe_average(normalized_logs: list[dict[str, Any]]) -> float | None:
    rpe_values = [
        float(row["rpe"])
        for row in normalized_logs
        if isinstance(row.get("rpe"), (int, float))
    ]
    return round(sum(rpe_values) / len(rpe_values), 2) if rpe_values else None


def _resolve_soreness_by_muscle(latest_soreness_entry: Any | None) -> dict[str, str]:
    return {
        str(muscle): str(severity).lower()
        for muscle, severity in _coerce_dict(_read_attr(latest_soreness_entry, "severity_by_muscle", {})).items()
        if str(muscle).strip() and str(severity).strip()
    }


def _build_fatigue_state(
    *,
    latest_soreness_entry: Any | None,
    normalized_logs: list[dict[str, Any]],
) -> dict[str, Any]:
    session_rpe_avg = _resolve_session_rpe_average(normalized_logs)
    severity_by_muscle = _resolve_soreness_by_muscle(latest_soreness_entry)
    severe_soreness_count = sum(
        1 for severity in severity_by_muscle.values() if str(severity).lower() == "severe"
    )
    flagged_muscles = sorted(
        muscle
        for muscle, severity in severity_by_muscle.items()
        if str(severity).lower() in {"moderate", "severe"}
    )
    return {
        "recovery_state": _derive_recovery_state(
            severe_soreness_count=severe_soreness_count,
            session_rpe_avg=session_rpe_avg,
        ),
        "severe_soreness_count": severe_soreness_count,
        "session_rpe_avg": session_rpe_avg,
        "soreness_by_muscle": severity_by_muscle,
        "flagged_muscles": flagged_muscles,
    }


def _resolve_adherence_scores(recent_checkins: list[Any], recent_review_cycles: list[Any]) -> list[int]:
    checkin_scores = [
        int(_read_attr(entry, "adherence_score", 0) or 0)
        for entry in recent_checkins
        if int(_read_attr(entry, "adherence_score", 0) or 0) >= 1
    ]
    if checkin_scores:
        return checkin_scores
    return [
        int(_read_attr(entry, "adherence_score", 0) or 0)
        for entry in recent_review_cycles
        if int(_read_attr(entry, "adherence_score", 0) or 0) >= 1
    ]


def _build_adherence_state(
    *,
    recent_checkins: list[Any],
    recent_review_cycles: list[Any],
    sessions: list[dict[str, Any]],
    normalized_logs: list[dict[str, Any]],
    today: date,
    default_adherence_score: int,
) -> dict[str, Any]:
    adherence_scores = _resolve_adherence_scores(recent_checkins, recent_review_cycles)
    latest_adherence_score = adherence_scores[0] if adherence_scores else default_adherence_score
    rolling_average_score = round(sum(adherence_scores) / len(adherence_scores), 2) if adherence_scores else None
    return {
        "latest_adherence_score": latest_adherence_score,
        "rolling_average_score": rolling_average_score,
        "missed_session_count": _count_missed_sessions(
            sessions=sessions,
            normalized_logs=normalized_logs,
            today=today,
        ),
    }


def _completion_pct_proxy_from_adherence(latest_adherence_score: int | None) -> int:
    if latest_adherence_score is None:
        return 85

    normalized_adherence = max(1, min(5, int(latest_adherence_score)))
    return {
        1: 55,
        2: 68,
        3: 80,
        4: 90,
        5: 96,
    }[normalized_adherence]


def _resolve_soreness_level_for_sfr(fatigue_state: dict[str, Any]) -> str:
    severe_soreness_count = int(fatigue_state.get("severe_soreness_count") or 0)
    if severe_soreness_count >= 2:
        return "severe"
    if severe_soreness_count == 1:
        return "moderate"

    flagged_muscles = _normalize_string_list(fatigue_state.get("flagged_muscles"))
    if len(flagged_muscles) >= 2:
        return "moderate"
    if flagged_muscles:
        return "mild"
    return "none"


def _build_readiness_state(*, recent_checkins: list[Any]) -> dict[str, Any]:
    latest_checkin = recent_checkins[0] if recent_checkins else None
    sleep_quality_raw = _read_attr(latest_checkin, "sleep_quality") if latest_checkin is not None else None
    stress_level_raw = _read_attr(latest_checkin, "stress_level") if latest_checkin is not None else None
    pain_flags = _normalize_string_list(
        _read_attr(latest_checkin, "pain_flags", []) if latest_checkin is not None else []
    )

    sleep_quality = int(sleep_quality_raw) if sleep_quality_raw is not None else None
    stress_level = int(stress_level_raw) if stress_level_raw is not None else None

    recovery_risk_flags: list[str] = []
    if sleep_quality is not None and sleep_quality <= 2:
        recovery_risk_flags.append("low_sleep")
    if stress_level is not None and stress_level >= 4:
        recovery_risk_flags.append("high_stress")
    if pain_flags:
        recovery_risk_flags.append("pain_flags_present")

    return {
        "sleep_quality": sleep_quality,
        "stress_level": stress_level,
        "pain_flags": pain_flags,
        "recovery_risk_flags": sorted(recovery_risk_flags),
    }


def _normalize_string_list(values: list[str] | None) -> list[str]:
    return [str(item).strip() for item in (values or []) if str(item).strip()]


def _build_constraint_state(
    *,
    days_available: int | None,
    split_preference: str | None,
    training_location: str | None,
    equipment_profile: list[str] | None,
    weak_areas: list[str] | None,
    nutrition_phase: str | None,
    session_time_budget_minutes: int | None,
    movement_restrictions: list[str] | None,
    near_failure_tolerance: str | None,
) -> dict[str, Any]:
    return {
        "days_available": int(days_available) if days_available is not None else None,
        "split_preference": split_preference,
        "training_location": training_location,
        "equipment_profile": _normalize_string_list(equipment_profile),
        "weak_areas": _normalize_string_list(weak_areas),
        "nutrition_phase": nutrition_phase,
        "session_time_budget_minutes": (
            int(session_time_budget_minutes) if session_time_budget_minutes is not None else None
        ),
        "movement_restrictions": _normalize_string_list(movement_restrictions),
        "near_failure_tolerance": near_failure_tolerance,
    }


def _build_progression_state(exercise_states: list[Any]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "exercise_id": str(_read_attr(state, "exercise_id", "") or ""),
                "current_working_weight": float(_read_attr(state, "current_working_weight", 0) or 0),
                "exposure_count": int(_read_attr(state, "exposure_count", 0) or 0),
                "consecutive_under_target_exposures": int(
                    _read_attr(state, "consecutive_under_target_exposures", 0) or 0
                ),
                "last_progression_action": str(_read_attr(state, "last_progression_action", "hold") or "hold"),
                "fatigue_score": max(0.0, min(1.0, float(_read_attr(state, "fatigue_score", 0.0) or 0.0))),
                "last_updated_at": _read_attr(state, "last_updated_at"),
            }
            for state in exercise_states
            if str(_read_attr(state, "exercise_id", "") or "")
        ],
        key=lambda entry: str(entry["exercise_id"]),
    )


def _build_stall_state(
    progression_state: list[dict[str, Any]],
    recent_review_cycles: list[Any],
) -> dict[str, Any]:
    stalled_exercise_ids = sorted(
        {
            str(entry["exercise_id"])
            for entry in progression_state
            if int(entry["consecutive_under_target_exposures"]) >= 2
            or str(entry["last_progression_action"]) == "deload"
        }
    )
    review_stagnation_weeks = _count_consecutive_underperformance_weeks(recent_review_cycles)
    state_stagnation_weeks = 1 if any(
        int(entry["consecutive_under_target_exposures"]) >= 3 for entry in progression_state
    ) else 0
    return {
        "stalled_exercise_ids": stalled_exercise_ids,
        "consecutive_underperformance_weeks": max(review_stagnation_weeks, state_stagnation_weeks),
        "phase_stagnation_weeks": review_stagnation_weeks,
    }


def _build_stimulus_fatigue_response(
    *,
    readiness_state: dict[str, Any],
    fatigue_state: dict[str, Any],
    adherence_state: dict[str, Any],
    stall_state: dict[str, Any],
) -> dict[str, Any]:
    latest_adherence_score = adherence_state.get("latest_adherence_score")
    sleep_quality = readiness_state.get("sleep_quality")
    stress_level = readiness_state.get("stress_level")
    average_rpe = fatigue_state.get("session_rpe_avg")
    pain_flags = _normalize_string_list(readiness_state.get("pain_flags"))
    snapshot = evaluate_stimulus_fatigue_response(
        completion_pct=_completion_pct_proxy_from_adherence(
            int(latest_adherence_score) if latest_adherence_score is not None else None
        ),
        adherence_score=max(1, min(5, int(latest_adherence_score or 3))),
        soreness_level=_resolve_soreness_level_for_sfr(fatigue_state),
        average_rpe=float(average_rpe) if isinstance(average_rpe, (int, float)) else None,
        consecutive_underperformance_weeks=max(
            int(stall_state.get("consecutive_underperformance_weeks") or 0),
            int(stall_state.get("phase_stagnation_weeks") or 0),
        ),
        sleep_quality=int(sleep_quality) if sleep_quality is not None else None,
        stress_level=int(stress_level) if stress_level is not None else None,
        pain_flags=pain_flags,
    )
    return {
        "stimulus_quality": str(snapshot.get("stimulus_quality") or ""),
        "fatigue_cost": str(snapshot.get("fatigue_cost") or ""),
        "recoverability": str(snapshot.get("recoverability") or ""),
        "progression_eligibility": bool(snapshot.get("progression_eligibility")),
        "deload_pressure": str(snapshot.get("deload_pressure") or ""),
        "substitution_pressure": str(snapshot.get("substitution_pressure") or ""),
        "signals": {
            "stimulus": _normalize_string_list(_coerce_dict(snapshot.get("signals")).get("stimulus")),
            "fatigue": _normalize_string_list(_coerce_dict(snapshot.get("signals")).get("fatigue")),
            "recoverability": _normalize_string_list(_coerce_dict(snapshot.get("signals")).get("recoverability")),
        },
    }


def _build_performance_history(normalized_logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "exercise_id": str(row["primary_exercise_id"] or row["exercise_id"] or ""),
            "performed_at": row["created_at"],
            "set_index": int(row["set_index"] or 1),
            "reps": int(row["reps"] or 0),
            "weight": float(row["weight"] or 0),
            "rpe": row["rpe"],
        }
        for row in sorted(
            normalized_logs,
            key=lambda entry: (entry["created_at"] or datetime.min, int(entry["set_index"] or 1)),
        )
        if str(row["primary_exercise_id"] or row["exercise_id"] or "") and row["created_at"] is not None
    ]


def _build_user_program_state(
    *,
    latest_plan_payload: dict[str, Any],
    selected_program_id: str | None,
    default_program_id: str,
    week_index: int,
    selected_session: dict[str, Any] | None,
    sessions: list[dict[str, Any]],
    week_start: date | None,
) -> dict[str, Any]:
    return {
        "program_id": str(
            latest_plan_payload.get("program_template_id")
            or selected_program_id
            or default_program_id
        ),
        "phase_id": str(latest_plan_payload.get("phase") or "maintenance"),
        "week_index": week_index,
        "day_id": _derive_day_id(
            selected_session=selected_session,
            sessions=sessions,
            week_start=week_start,
            week_index=week_index,
        ),
        "session_id": str(selected_session.get("session_id") or "") if selected_session is not None else None,
        "last_generated_week_start": week_start,
    }


def _build_generation_state(
    *,
    prior_plans: list[Any],
    latest_plan_payload: dict[str, Any],
) -> dict[str, Any]:
    muscle_coverage = _coerce_dict(latest_plan_payload.get("muscle_coverage"))
    under_target_muscles = [
        str(muscle)
        for muscle in muscle_coverage.get("under_target_muscles") or []
        if str(muscle).strip()
    ]
    mesocycle = _coerce_dict(latest_plan_payload.get("mesocycle"))
    trigger_weeks_effective = mesocycle.get("trigger_weeks_effective")

    return {
        "prior_generated_weeks_by_program": _count_prior_generated_weeks_by_program(prior_plans),
        "under_target_muscles": under_target_muscles,
        "mesocycle_trigger_weeks_effective": (
            max(1, int(trigger_weeks_effective))
            if isinstance(trigger_weeks_effective, (int, float)) or str(trigger_weeks_effective).isdigit()
            else None
        ),
        "latest_mesocycle": {
            "week_index": (
                max(1, int(mesocycle["week_index"]))
                if isinstance(mesocycle.get("week_index"), (int, float)) or str(mesocycle.get("week_index")).isdigit()
                else None
            ),
            "trigger_weeks_effective": (
                max(1, int(trigger_weeks_effective))
                if isinstance(trigger_weeks_effective, (int, float)) or str(trigger_weeks_effective).isdigit()
                else None
            ),
            "authored_week_index": (
                max(1, int(mesocycle["authored_week_index"]))
                if isinstance(mesocycle.get("authored_week_index"), (int, float))
                or str(mesocycle.get("authored_week_index")).isdigit()
                else None
            ),
            "authored_week_role": (
                str(mesocycle.get("authored_week_role"))
                if str(mesocycle.get("authored_week_role") or "").strip()
                else None
            ),
            "authored_sequence_length": (
                max(1, int(mesocycle["authored_sequence_length"]))
                if isinstance(mesocycle.get("authored_sequence_length"), (int, float))
                or str(mesocycle.get("authored_sequence_length")).isdigit()
                else None
            ),
            "authored_sequence_complete": bool(mesocycle.get("authored_sequence_complete")),
            "phase_transition_pending": bool(mesocycle.get("phase_transition_pending")),
            "phase_transition_reason": (
                str(mesocycle.get("phase_transition_reason"))
                if str(mesocycle.get("phase_transition_reason") or "").strip()
                else None
            ),
            "post_authored_behavior": (
                str(mesocycle.get("post_authored_behavior"))
                if str(mesocycle.get("post_authored_behavior") or "").strip()
                else None
            ),
        },
    }


def _build_coaching_state(
    *,
    readiness_state: dict[str, Any],
    fatigue_state: dict[str, Any],
    adherence_state: dict[str, Any],
    stall_state: dict[str, Any],
    stimulus_fatigue_response: dict[str, Any],
    generation_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "readiness": dict(readiness_state),
        "fatigue": dict(fatigue_state),
        "adherence": dict(adherence_state),
        "stall": dict(stall_state),
        "stimulus_fatigue_response": dict(stimulus_fatigue_response),
        "mesocycle": dict(_coerce_dict(generation_state.get("latest_mesocycle"))),
    }


def build_user_training_state(
    *,
    selected_program_id: str | None,
    days_available: int | None = None,
    split_preference: str | None = None,
    training_location: str | None = None,
    equipment_profile: list[str] | None = None,
    weak_areas: list[str] | None = None,
    nutrition_phase: str | None = None,
    session_time_budget_minutes: int | None = None,
    movement_restrictions: list[str] | None = None,
    near_failure_tolerance: str | None = None,
    latest_plan: Any | None,
    recent_workout_logs: list[Any],
    exercise_states: list[Any],
    latest_soreness_entry: Any | None,
    recent_checkins: list[Any] | None = None,
    recent_review_cycles: list[Any] | None = None,
    prior_plans: list[Any] | None = None,
    today: date | None = None,
    default_program_id: str = "full_body_v1",
    default_adherence_score: int = 3,
) -> dict[str, Any]:
    resolved_today = today or date.today()
    latest_plan_payload, sessions, week_start, week_index = _resolve_plan_context(latest_plan)
    normalized_logs = _normalize_logs(recent_workout_logs)
    recent_checkins = recent_checkins or []
    recent_review_cycles = recent_review_cycles or []
    prior_plans = prior_plans or []
    selected_session = _resolve_session_selection(
        sessions=sessions,
        normalized_logs=normalized_logs,
        today=resolved_today,
    )
    fatigue_state = _build_fatigue_state(
        latest_soreness_entry=latest_soreness_entry,
        normalized_logs=normalized_logs,
    )
    adherence_state = _build_adherence_state(
        recent_checkins=recent_checkins,
        recent_review_cycles=recent_review_cycles,
        sessions=sessions,
        normalized_logs=normalized_logs,
        today=resolved_today,
        default_adherence_score=default_adherence_score,
    )
    progression_state = _build_progression_state(exercise_states)
    stall_state = _build_stall_state(progression_state, recent_review_cycles)
    performance_history = _build_performance_history(normalized_logs)
    readiness_state = _build_readiness_state(recent_checkins=recent_checkins)
    stimulus_fatigue_response = _build_stimulus_fatigue_response(
        readiness_state=readiness_state,
        fatigue_state=fatigue_state,
        adherence_state=adherence_state,
        stall_state=stall_state,
    )
    generation_state = _build_generation_state(
        prior_plans=prior_plans,
        latest_plan_payload=latest_plan_payload,
    )

    return {
        "user_program_state": _build_user_program_state(
            latest_plan_payload=latest_plan_payload,
            selected_program_id=selected_program_id,
            default_program_id=default_program_id,
            week_index=week_index,
            selected_session=selected_session,
            sessions=sessions,
            week_start=week_start,
        ),
        "exercise_performance_history": performance_history,
        "progression_state_per_exercise": progression_state,
        "fatigue_state": fatigue_state,
        "adherence_state": adherence_state,
        "readiness_state": readiness_state,
        "stimulus_fatigue_response": stimulus_fatigue_response,
        "coaching_state": _build_coaching_state(
            readiness_state=readiness_state,
            fatigue_state=fatigue_state,
            adherence_state=adherence_state,
            stall_state=stall_state,
            stimulus_fatigue_response=stimulus_fatigue_response,
            generation_state=generation_state,
        ),
        "constraint_state": _build_constraint_state(
            days_available=days_available,
            split_preference=split_preference,
            training_location=training_location,
            equipment_profile=equipment_profile,
            weak_areas=weak_areas,
            nutrition_phase=nutrition_phase,
            session_time_budget_minutes=session_time_budget_minutes,
            movement_restrictions=movement_restrictions,
            near_failure_tolerance=near_failure_tolerance,
        ),
        "stall_state": stall_state,
        "generation_state": generation_state,
    }


def build_plan_decision_training_state(
    *,
    selected_program_id: str | None,
    days_available: int | None = None,
    split_preference: str | None = None,
    training_location: str | None = None,
    equipment_profile: list[str] | None = None,
    weak_areas: list[str] | None = None,
    nutrition_phase: str | None = None,
    session_time_budget_minutes: int | None = None,
    movement_restrictions: list[str] | None = None,
    near_failure_tolerance: str | None = None,
    latest_plan: Any | None,
    latest_soreness_entry: Any | None,
    recent_workout_logs: list[Any] | None = None,
    exercise_states: list[Any] | None = None,
    recent_checkins: list[Any] | None = None,
    recent_review_cycles: list[Any] | None = None,
    prior_plans: list[Any] | None = None,
) -> dict[str, Any]:
    return build_user_training_state(
        selected_program_id=selected_program_id,
        days_available=days_available,
        split_preference=split_preference,
        training_location=training_location,
        equipment_profile=equipment_profile,
        weak_areas=weak_areas,
        nutrition_phase=nutrition_phase,
        session_time_budget_minutes=session_time_budget_minutes,
        movement_restrictions=movement_restrictions,
        near_failure_tolerance=near_failure_tolerance,
        latest_plan=latest_plan,
        recent_workout_logs=list(recent_workout_logs or []),
        exercise_states=list(exercise_states or []),
        latest_soreness_entry=latest_soreness_entry,
        recent_checkins=list(recent_checkins or []),
        recent_review_cycles=list(recent_review_cycles or []),
        prior_plans=list(prior_plans or []),
    )
