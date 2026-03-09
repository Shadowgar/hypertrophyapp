from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Any, cast


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def resolve_weekly_review_window(*, today: date) -> dict[str, date | bool]:
    current_week_start = today - timedelta(days=today.weekday())
    today_is_sunday = today.weekday() == 6
    week_start = current_week_start + timedelta(days=7) if today_is_sunday else current_week_start
    previous_week_start = week_start - timedelta(days=7)
    return {
        "today_is_sunday": today_is_sunday,
        "current_week_start": current_week_start,
        "week_start": week_start,
        "previous_week_start": previous_week_start,
        "previous_week_end": week_start - timedelta(days=1),
    }


def prepare_weekly_review_submit_window(
    *,
    today: date,
    requested_week_start: date | None,
) -> dict[str, Any]:
    window = resolve_weekly_review_window(today=today)
    source = "request" if requested_week_start is not None else "window_default"
    week_start = requested_week_start or cast(date, window["week_start"])
    previous_week_start = week_start - timedelta(days=7)
    return {
        "week_start": week_start,
        "previous_week_start": previous_week_start,
        "decision_trace": {
            "interpreter": "prepare_weekly_review_submit_window",
            "version": "v1",
            "inputs": {
                "today": today.isoformat(),
                "requested_week_start": requested_week_start.isoformat() if requested_week_start else None,
            },
            "outcome": {
                "source": source,
                "week_start": week_start.isoformat(),
                "previous_week_start": previous_week_start.isoformat(),
            },
        },
    }


def build_weekly_review_status_payload(
    *,
    today: date,
    existing_review_submitted: bool,
    previous_week_summary: dict[str, Any],
) -> dict[str, Any]:
    window = resolve_weekly_review_window(today=today)
    today_is_sunday = bool(window["today_is_sunday"])
    return {
        "today_is_sunday": today_is_sunday,
        "review_required": today_is_sunday and not existing_review_submitted,
        "current_week_start": window["current_week_start"],
        "week_start": window["week_start"],
        "previous_week_start": window["previous_week_start"],
        "previous_week_end": window["previous_week_end"],
        "existing_review_submitted": existing_review_submitted,
        "previous_week_summary": previous_week_summary,
    }


def build_weekly_review_submit_payload(
    *,
    week_start: date,
    previous_week_start: date,
    summary: dict[str, Any],
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "review_logged",
        "week_start": week_start,
        "previous_week_start": previous_week_start,
        "readiness_score": int(decision_payload.get("readiness_score") or 0),
        "global_guidance": str(decision_payload.get("global_guidance") or ""),
        "fault_count": int(summary.get("faulty_exercise_count", 0) or 0),
        "summary": deepcopy(summary),
        "adjustments": deepcopy(_coerce_dict(decision_payload.get("adjustments"))),
        "decision_trace": deepcopy(_coerce_dict(decision_payload.get("decision_trace"))),
    }


def build_weekly_review_cycle_persistence_payload(
    *,
    summary: dict[str, Any],
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    exercise_faults = [
        deepcopy(_coerce_dict(item))
        for item in (summary.get("exercise_faults") or [])
        if isinstance(item, dict)
    ]
    storage_adjustments = deepcopy(_coerce_dict(decision_payload.get("storage_adjustments")))
    return {
        "faults": {"exercise_faults": exercise_faults},
        "adjustments": storage_adjustments,
        "decision_trace": {
            "interpreter": "build_weekly_review_cycle_persistence_payload",
            "version": "v1",
            "inputs": {
                "fault_count": len(exercise_faults),
                "has_storage_adjustments": bool(storage_adjustments),
            },
            "outcome": {
                "fault_count": len(exercise_faults),
                "adjustment_keys": sorted(storage_adjustments.keys()),
            },
        },
    }


def build_weekly_review_user_update_payload(
    *,
    body_weight: float,
    calories: int,
    protein: int,
    fat: int,
    carbs: int,
    nutrition_phase: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "weight": body_weight,
        "calories": calories,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
    }
    if nutrition_phase:
        payload["nutrition_phase"] = nutrition_phase
    return payload


def prepare_weekly_review_log_window_runtime(
    *,
    previous_week_start: date,
    week_start: date,
) -> dict[str, Any]:
    window_start = datetime.combine(previous_week_start, datetime.min.time())
    window_end = datetime.combine(week_start, datetime.min.time())
    return {
        "window_start": window_start,
        "window_end": window_end,
        "decision_trace": {
            "interpreter": "prepare_weekly_review_log_window_runtime",
            "version": "v1",
            "inputs": {
                "previous_week_start": previous_week_start.isoformat(),
                "week_start": week_start.isoformat(),
            },
        },
    }
