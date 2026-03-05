from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import BodyMeasurementEntry, User, WeeklyCheckin, WorkoutSetLog

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _monday_of(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _round2(value: float) -> float:
    return round(float(value), 2)


def _build_volume_heatmap(log_rows: list[WorkoutSetLog], *, limit_weeks: int) -> dict[str, Any]:
    today = date.today()
    this_monday = _monday_of(today)
    ordered_weeks = [this_monday - timedelta(days=7 * offset) for offset in reversed(range(limit_weeks))]
    week_keys = [week.isoformat() for week in ordered_weeks]

    week_map: dict[str, list[dict[str, Any]]] = {
        week_key: [{"day_index": day_index, "sets": 0, "volume": 0.0} for day_index in range(7)]
        for week_key in week_keys
    }

    for row in log_rows:
        row_date = row.created_at.date()
        week_key = _monday_of(row_date).isoformat()
        if week_key not in week_map:
            continue
        day_index = row_date.weekday()
        cell = week_map[week_key][day_index]
        cell["sets"] += 1
        cell["volume"] += float(row.reps) * float(row.weight)

    max_volume = 0.0
    weeks: list[dict[str, Any]] = []
    for week_key in week_keys:
        cells = week_map[week_key]
        for cell in cells:
            cell["volume"] = _round2(cell["volume"])
            max_volume = max(max_volume, cell["volume"])
        weeks.append({"week_start": week_key, "days": cells})

    return {
        "max_volume": _round2(max_volume),
        "weeks": weeks,
    }


def _build_strength_trends(log_rows: list[WorkoutSetLog], *, limit: int = 4) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_exercise: dict[str, dict[str, Any]] = {}

    for row in log_rows:
        exercise_key = (row.primary_exercise_id or row.exercise_id or "").strip()
        if not exercise_key:
            continue

        entry = _get_or_create_strength_entry(by_exercise, exercise_key)
        _update_strength_entry(entry, row)

    ranked = sorted(
        by_exercise.values(),
        key=lambda item: (-int(item["total_sets"]), -float(item["total_volume"]), str(item["exercise_id"])),
    )
    selected = ranked[:limit]

    trends: list[dict[str, Any]] = []
    highlights: list[dict[str, Any]] = []

    for item in selected:
        trend_item = _build_strength_trend_item(item)
        trends.append(trend_item)
        if trend_item["pr_weight"] > 0:
            highlights.append(
                {
                    "exercise_id": trend_item["exercise_id"],
                    "pr_weight": trend_item["pr_weight"],
                    "previous_pr_weight": trend_item["previous_pr_weight"],
                    "pr_delta": trend_item["pr_delta"],
                }
            )

    highlights.sort(key=lambda item: (-float(item["pr_delta"]), -float(item["pr_weight"]), str(item["exercise_id"])))
    return trends, highlights[:3]


def _get_or_create_strength_entry(by_exercise: dict[str, dict[str, Any]], exercise_key: str) -> dict[str, Any]:
    return by_exercise.setdefault(
        exercise_key,
        {
            "exercise_id": exercise_key,
            "total_sets": 0,
            "total_volume": 0.0,
            "weekly": defaultdict(lambda: {"max_weight": 0.0, "avg_est_1rm": 0.0, "samples": 0}),
            "pr_weight": 0.0,
            "previous_pr_weight": 0.0,
        },
    )


def _update_strength_entry(entry: dict[str, Any], row: WorkoutSetLog) -> None:
    weight = float(row.weight)
    reps = int(row.reps)
    est_1rm = weight * (1 + (reps / 30.0))
    week_key = _monday_of(row.created_at.date()).isoformat()

    weekly = entry["weekly"][week_key]
    weekly["max_weight"] = max(float(weekly["max_weight"]), weight)
    weekly["avg_est_1rm"] += est_1rm
    weekly["samples"] += 1

    entry["total_sets"] += 1
    entry["total_volume"] += weight * reps

    pr_weight = float(entry["pr_weight"])
    previous_pr_weight = float(entry["previous_pr_weight"])
    if weight > pr_weight:
        entry["previous_pr_weight"] = pr_weight
        entry["pr_weight"] = weight
        return
    if previous_pr_weight < weight < pr_weight:
        entry["previous_pr_weight"] = weight


def _build_strength_points(weekly: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for week_key in sorted(weekly.keys()):
        week = weekly[week_key]
        samples = max(1, int(week["samples"]))
        points.append(
            {
                "week_start": week_key,
                "max_weight": _round2(float(week["max_weight"])),
                "avg_est_1rm": _round2(float(week["avg_est_1rm"]) / samples),
            }
        )
    return points


def _build_strength_trend_item(item: dict[str, Any]) -> dict[str, Any]:
    points = _build_strength_points(item["weekly"])
    latest_weight = points[-1]["max_weight"] if points else 0.0
    previous_pr_weight = _round2(float(item["previous_pr_weight"]))
    pr_weight = _round2(float(item["pr_weight"]))
    pr_delta = _round2(pr_weight - previous_pr_weight) if previous_pr_weight > 0 else pr_weight
    return {
        "exercise_id": item["exercise_id"],
        "total_sets": int(item["total_sets"]),
        "latest_weight": latest_weight,
        "pr_weight": pr_weight,
        "previous_pr_weight": previous_pr_weight,
        "pr_delta": pr_delta,
        "points": points,
    }


def _build_body_measurement_trends(entries: list[BodyMeasurementEntry], *, limit: int = 3) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[BodyMeasurementEntry]] = defaultdict(list)
    for row in entries:
        key = (str(row.name).strip().lower(), str(row.unit).strip().lower())
        grouped[key].append(row)

    ranked_groups = sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), item[0][0], item[0][1]),
    )

    trends: list[dict[str, Any]] = []
    for (name, unit), rows in ranked_groups[:limit]:
        sorted_rows = sorted(rows, key=lambda row: (row.measured_on, row.created_at))
        points = [{"measured_on": row.measured_on.isoformat(), "value": _round2(float(row.value))} for row in sorted_rows]
        first_value = points[0]["value"] if points else 0.0
        latest_value = points[-1]["value"] if points else 0.0
        trends.append(
            {
                "name": name,
                "unit": unit,
                "latest_value": latest_value,
                "delta": _round2(latest_value - first_value),
                "points": points,
            }
        )

    return trends


@router.get("/history/exercise/{exercise_id}")
def get_exercise_history(
    exercise_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    rows = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.exercise_id == exercise_id,
        )
        .order_by(WorkoutSetLog.created_at.desc())
        .limit(50)
        .all()
    )
    history = [
        {
            "id": row.id,
            "primary_exercise_id": row.primary_exercise_id,
            "reps": row.reps,
            "weight": row.weight,
            "set_index": row.set_index,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
    return {"exercise_id": exercise_id, "history": history}


@router.get("/history/weekly-checkins")
def get_weekly_checkin_history(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = 12,
) -> dict:
    capped_limit = max(1, min(52, int(limit)))
    rows = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.user_id == current_user.id)
        .order_by(WeeklyCheckin.week_start.desc())
        .limit(capped_limit)
        .all()
    )
    entries = [
        {
            "week_start": row.week_start.isoformat(),
            "body_weight": float(row.body_weight),
            "adherence_score": int(row.adherence_score),
            "notes": row.notes,
            "created_at": row.created_at.isoformat(),
        }
        for row in reversed(rows)
    ]
    return {"entries": entries}


@router.get("/history/analytics")
def get_history_analytics(
    db: DbSession,
    current_user: CurrentUser,
    limit_weeks: int = 8,
    checkin_limit: int = 24,
) -> dict[str, Any]:
    capped_weeks = max(2, min(26, int(limit_weeks)))
    capped_checkin_limit = max(4, min(52, int(checkin_limit)))
    start_date = _monday_of(date.today()) - timedelta(days=(capped_weeks - 1) * 7)
    start_datetime = datetime.combine(start_date, time.min)

    checkin_rows = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.user_id == current_user.id)
        .order_by(WeeklyCheckin.week_start.desc())
        .limit(capped_checkin_limit)
        .all()
    )
    checkins = [
        {
            "week_start": row.week_start.isoformat(),
            "body_weight": float(row.body_weight),
            "adherence_score": int(row.adherence_score),
            "notes": row.notes,
            "created_at": row.created_at.isoformat(),
        }
        for row in reversed(checkin_rows)
    ]

    adherence_scores = [int(entry["adherence_score"]) for entry in checkins]
    if adherence_scores:
        average_score = sum(adherence_scores) / len(adherence_scores)
        latest_score = adherence_scores[-1]
        trend_delta = latest_score - adherence_scores[0]
        high_readiness_streak = 0
        for score in reversed(adherence_scores):
            if score >= 4:
                high_readiness_streak += 1
            else:
                break
    else:
        average_score = 0.0
        latest_score = 0
        trend_delta = 0
        high_readiness_streak = 0

    log_rows = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == current_user.id,
            WorkoutSetLog.created_at >= start_datetime,
        )
        .order_by(WorkoutSetLog.created_at.asc())
        .all()
    )

    measurement_rows = (
        db.query(BodyMeasurementEntry)
        .filter(
            BodyMeasurementEntry.user_id == current_user.id,
            BodyMeasurementEntry.measured_on >= start_date,
        )
        .order_by(BodyMeasurementEntry.measured_on.asc(), BodyMeasurementEntry.created_at.asc())
        .all()
    )

    strength_trends, pr_highlights = _build_strength_trends(log_rows)
    measurement_trends = _build_body_measurement_trends(measurement_rows)
    volume_heatmap = _build_volume_heatmap(log_rows, limit_weeks=capped_weeks)

    return {
        "window": {
            "start_date": start_date.isoformat(),
            "end_date": date.today().isoformat(),
            "limit_weeks": capped_weeks,
            "checkin_limit": capped_checkin_limit,
        },
        "checkins": checkins,
        "adherence": {
            "average_score": _round2(average_score),
            "average_pct": int(round((average_score / 5) * 100)) if average_score > 0 else 0,
            "latest_score": int(latest_score),
            "trend_delta": int(trend_delta),
            "high_readiness_streak": int(high_readiness_streak),
        },
        "bodyweight_trend": [
            {
                "week_start": str(entry["week_start"]),
                "body_weight": float(entry["body_weight"]),
            }
            for entry in checkins
        ],
        "strength_trends": strength_trends,
        "pr_highlights": pr_highlights,
        "body_measurement_trends": measurement_trends,
        "volume_heatmap": volume_heatmap,
    }
