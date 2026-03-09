from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any


def _read_attr(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _monday_of(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _round2(value: float) -> float:
    return round(float(value), 2)


def _build_volume_heatmap(log_rows: list[Any], *, limit_weeks: int, today: date) -> dict[str, Any]:
    this_monday = _monday_of(today)
    ordered_weeks = [this_monday - timedelta(days=7 * offset) for offset in reversed(range(limit_weeks))]
    week_keys = [week.isoformat() for week in ordered_weeks]

    week_map: dict[str, list[dict[str, Any]]] = {
        week_key: [{"day_index": day_index, "sets": 0, "volume": 0.0} for day_index in range(7)]
        for week_key in week_keys
    }

    for row in log_rows:
        created_at = _read_attr(row, "created_at")
        row_date = created_at.date()
        week_key = _monday_of(row_date).isoformat()
        if week_key not in week_map:
            continue
        day_index = row_date.weekday()
        cell = week_map[week_key][day_index]
        cell["sets"] += 1
        cell["volume"] += float(_read_attr(row, "reps", 0)) * float(_read_attr(row, "weight", 0.0))

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


def _update_strength_entry(entry: dict[str, Any], row: Any) -> None:
    weight = float(_read_attr(row, "weight", 0.0))
    reps = int(_read_attr(row, "reps", 0))
    created_at = _read_attr(row, "created_at")
    est_1rm = weight * (1 + (reps / 30.0))
    week_key = _monday_of(created_at.date()).isoformat()

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


def _build_strength_trends(log_rows: list[Any], *, limit: int = 4) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_exercise: dict[str, dict[str, Any]] = {}

    for row in log_rows:
        exercise_key = str(_read_attr(row, "primary_exercise_id") or _read_attr(row, "exercise_id") or "").strip()
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


def _build_body_measurement_trends(entries: list[Any], *, limit: int = 3) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for row in entries:
        key = (str(_read_attr(row, "name", "")).strip().lower(), str(_read_attr(row, "unit", "")).strip().lower())
        grouped[key].append(row)

    ranked_groups = sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), item[0][0], item[0][1]),
    )

    trends: list[dict[str, Any]] = []
    for (name, unit), rows in ranked_groups[:limit]:
        sorted_rows = sorted(rows, key=lambda row: (_read_attr(row, "measured_on"), _read_attr(row, "created_at")))
        points = [
            {"measured_on": _read_attr(row, "measured_on").isoformat(), "value": _round2(float(_read_attr(row, "value", 0.0)))}
            for row in sorted_rows
        ]
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


def _normalize_muscles(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    values = [str(item).strip().lower() for item in raw if str(item).strip()]
    return list(dict.fromkeys(values))


def _build_planned_exercise_map(exercises: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], int]:
    planned_by_exercise: dict[str, dict[str, Any]] = {}
    total_planned_sets = 0
    for exercise in exercises:
        exercise_key = str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()
        if not exercise_key:
            continue
        planned_sets = max(0, int(exercise.get("sets", 0) or 0))
        planned_by_exercise[exercise_key] = {
            "planned_sets": planned_sets,
            "planned_name": str(exercise.get("name") or exercise_key),
            "primary_muscles": _normalize_muscles(exercise.get("primary_muscles")),
        }
        total_planned_sets += planned_sets
    return planned_by_exercise, total_planned_sets


def _iter_plan_sessions_for_day(plans: list[Any], target_day: str):
    for plan in plans:
        payload = _read_attr(plan, "payload")
        payload = payload if isinstance(payload, dict) else {}
        program_id = str(payload.get("program_template_id") or "").strip()
        sessions = payload.get("sessions") or []
        for session in sessions:
            if str(session.get("date") or "") == target_day:
                yield session, program_id


def _date_key_in_window(day_key: str, start_key: str, end_key: str) -> bool:
    return bool(day_key) and start_key <= day_key <= end_key


def _calendar_bucket(metadata: dict[str, dict[str, set[str]]], day_key: str) -> dict[str, set[str]]:
    return metadata.setdefault(day_key, {"program_ids": set(), "muscles": set()})


def _add_session_muscles(bucket: dict[str, set[str]], session: dict[str, Any]) -> None:
    for exercise in session.get("exercises") or []:
        for muscle in _normalize_muscles(exercise.get("primary_muscles")):
            bucket["muscles"].add(muscle)


def _extract_planned_calendar_metadata(
    plans: list[Any],
    start_date: date,
    end_date: date,
) -> dict[str, dict[str, set[str]]]:
    metadata: dict[str, dict[str, set[str]]] = {}
    start_key = start_date.isoformat()
    end_key = end_date.isoformat()

    for plan in plans:
        payload = _read_attr(plan, "payload")
        payload = payload if isinstance(payload, dict) else {}
        program_id = str(payload.get("program_template_id") or "").strip()
        sessions = payload.get("sessions") or []
        for session in sessions:
            day_key = str(session.get("date") or "").strip()
            if not _date_key_in_window(day_key, start_key, end_key):
                continue

            bucket = _calendar_bucket(metadata, day_key)
            if program_id:
                bucket["program_ids"].add(program_id)
            _add_session_muscles(bucket, session)

    return metadata


def _build_calendar_pr_metadata(
    ordered_log_rows: list[Any],
    *,
    start_date: date,
    end_date: date,
) -> dict[str, dict[str, Any]]:
    start_key = start_date.isoformat()
    end_key = end_date.isoformat()
    best_by_exercise: dict[str, float] = {}
    by_day: dict[str, dict[str, Any]] = {}

    for row in ordered_log_rows:
        created_at = _read_attr(row, "created_at")
        day_key = created_at.date().isoformat()
        exercise_id = str(_read_attr(row, "primary_exercise_id") or _read_attr(row, "exercise_id") or "").strip()
        if not exercise_id:
            continue

        weight = float(_read_attr(row, "weight", 0.0))
        previous_best = best_by_exercise.get(exercise_id)
        is_new_pr = previous_best is None or weight > previous_best
        if is_new_pr:
            best_by_exercise[exercise_id] = weight

        if not is_new_pr or day_key < start_key or day_key > end_key:
            continue

        bucket = by_day.setdefault(day_key, {"pr_exercises": set()})
        bucket["pr_exercises"].add(exercise_id)

    normalized: dict[str, dict[str, Any]] = {}
    for day_key, payload in by_day.items():
        pr_exercises = sorted(str(item) for item in payload["pr_exercises"])
        normalized[day_key] = {
            "pr_count": len(pr_exercises),
            "pr_exercises": pr_exercises,
        }
    return normalized


def _build_calendar_days(
    log_rows: list[Any],
    start_date: date,
    end_date: date,
    planned_day_metadata: dict[str, dict[str, set[str]]] | None = None,
    pr_day_metadata: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    planned_day_metadata = planned_day_metadata or {}
    pr_day_metadata = pr_day_metadata or {}
    by_date: dict[str, dict[str, Any]] = {}
    for row in log_rows:
        created_at = _read_attr(row, "created_at")
        day_key = created_at.date().isoformat()
        entry = by_date.setdefault(
            day_key,
            {
                "date": day_key,
                "set_count": 0,
                "total_volume": 0.0,
                "exercise_ids": set(),
            },
        )
        entry["set_count"] += 1
        entry["total_volume"] += float(_read_attr(row, "reps", 0)) * float(_read_attr(row, "weight", 0.0))
        entry["exercise_ids"].add(_read_attr(row, "primary_exercise_id") or _read_attr(row, "exercise_id"))

    days: list[dict[str, Any]] = []
    cursor = start_date
    while cursor <= end_date:
        day_key = cursor.isoformat()
        source = by_date.get(day_key)
        planned = planned_day_metadata.get(day_key, {"program_ids": set(), "muscles": set()})
        pr_meta = pr_day_metadata.get(day_key, {"pr_count": 0, "pr_exercises": []})
        program_ids = sorted(str(item) for item in planned.get("program_ids", set()) if str(item).strip())
        muscles = sorted(str(item) for item in planned.get("muscles", set()) if str(item).strip())
        pr_count = int(pr_meta.get("pr_count", 0) or 0)
        pr_exercises = [str(item) for item in pr_meta.get("pr_exercises", []) if str(item).strip()]
        if source is None:
            days.append(
                {
                    "date": day_key,
                    "weekday": cursor.weekday(),
                    "set_count": 0,
                    "exercise_count": 0,
                    "total_volume": 0.0,
                    "completed": False,
                    "program_ids": program_ids,
                    "muscles": muscles,
                    "pr_count": pr_count,
                    "pr_exercises": pr_exercises,
                }
            )
        else:
            days.append(
                {
                    "date": day_key,
                    "weekday": cursor.weekday(),
                    "set_count": int(source["set_count"]),
                    "exercise_count": len(source["exercise_ids"]),
                    "total_volume": _round2(float(source["total_volume"])),
                    "completed": int(source["set_count"]) > 0,
                    "program_ids": program_ids,
                    "muscles": muscles,
                    "pr_count": pr_count,
                    "pr_exercises": pr_exercises,
                }
            )
        cursor += timedelta(days=1)

    return days


def _build_streaks(completed_dates: list[date], *, today: date) -> tuple[int, int]:
    if not completed_dates:
        return 0, 0

    ordered = sorted(set(completed_dates))
    longest = 1
    running = 1
    for idx in range(1, len(ordered)):
        if ordered[idx] == ordered[idx - 1] + timedelta(days=1):
            running += 1
            longest = max(longest, running)
        else:
            running = 1

    current = 0
    cursor = today
    completed_set = set(ordered)
    while cursor in completed_set:
        current += 1
        cursor -= timedelta(days=1)

    return current, longest


def _extract_planned_sessions_for_day(plans: list[Any], day: date) -> dict[str, dict[str, Any]]:
    target_day = day.isoformat()
    planned_sessions: dict[str, dict[str, Any]] = {}

    for session, program_id in _iter_plan_sessions_for_day(plans, target_day):
        workout_id = str(session.get("session_id") or "").strip()
        if not workout_id or workout_id in planned_sessions:
            continue

        planned_by_exercise, total_planned_sets = _build_planned_exercise_map(session.get("exercises") or [])
        planned_sessions[workout_id] = {
            "program_id": program_id,
            "planned_sets_total": total_planned_sets,
            "planned_by_exercise": planned_by_exercise,
        }

    return planned_sessions


def _accumulate_logged_day_rows(
    log_rows: list[Any],
    planned_sessions: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in log_rows:
        workout_id = str(_read_attr(row, "workout_id") or "")
        planned_for_workout = planned_sessions.get(workout_id, {})
        planned_by_exercise = planned_for_workout.get("planned_by_exercise", {})
        exercise_lookup_key = str(_read_attr(row, "primary_exercise_id") or _read_attr(row, "exercise_id") or "")
        planned_info = planned_by_exercise.get(exercise_lookup_key, {})
        planned_sets_for_exercise = planned_info.get("planned_sets")

        workout = grouped.setdefault(
            workout_id,
            {
                "workout_id": workout_id,
                "program_id": planned_for_workout.get("program_id"),
                "total_sets": 0,
                "total_volume": 0.0,
                "planned_sets_total": int(planned_for_workout.get("planned_sets_total", 0) or 0),
                "exercise_map": {},
            },
        )
        primary_exercise_id = _read_attr(row, "primary_exercise_id")
        exercise_id = _read_attr(row, "exercise_id")
        exercise_key = f"{primary_exercise_id or exercise_id}::{exercise_id}"
        exercise_map: dict[str, Any] = workout["exercise_map"]
        exercise_entry = exercise_map.setdefault(
            exercise_key,
            {
                "exercise_id": exercise_id,
                "primary_exercise_id": primary_exercise_id,
                "sets": [],
                "total_sets": 0,
                "total_volume": 0.0,
                "planned_sets": int(planned_sets_for_exercise) if planned_sets_for_exercise is not None else None,
                "planned_name": planned_info.get("planned_name"),
                "primary_muscles": list(planned_info.get("primary_muscles") or []),
            },
        )

        reps = int(_read_attr(row, "reps", 0))
        weight = float(_read_attr(row, "weight", 0.0))
        created_at = _read_attr(row, "created_at")
        set_volume = weight * reps
        exercise_entry["sets"].append(
            {
                "set_index": int(_read_attr(row, "set_index", 0)),
                "reps": reps,
                "weight": weight,
                "rpe": float(_read_attr(row, "rpe")) if _read_attr(row, "rpe") is not None else None,
                "created_at": created_at.isoformat(),
            }
        )
        exercise_entry["total_sets"] += 1
        exercise_entry["total_volume"] += set_volume

        workout["total_sets"] += 1
        workout["total_volume"] += set_volume

    return grouped


def _serialize_grouped_workouts(grouped: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], int, float, set[str], int]:
    workouts: list[dict[str, Any]] = []
    total_sets = 0
    total_volume = 0.0
    unique_exercise_ids: set[str] = set()
    planned_set_count_total = 0

    for workout_id in sorted(grouped.keys()):
        workout = grouped[workout_id]
        exercise_entries = []
        for exercise in workout["exercise_map"].values():
            planned_sets = exercise["planned_sets"]
            exercise_entries.append(
                {
                    "exercise_id": exercise["exercise_id"],
                    "primary_exercise_id": exercise["primary_exercise_id"],
                    "planned_name": exercise.get("planned_name"),
                    "primary_muscles": list(exercise.get("primary_muscles") or []),
                    "sets": sorted(exercise["sets"], key=lambda item: (item["set_index"], item["created_at"])),
                    "total_sets": int(exercise["total_sets"]),
                    "total_volume": _round2(float(exercise["total_volume"])),
                    "planned_sets": planned_sets,
                    "set_delta": int(exercise["total_sets"] - planned_sets) if planned_sets is not None else None,
                }
            )
            unique_exercise_ids.add(str(exercise["primary_exercise_id"] or exercise["exercise_id"]))

        exercise_entries.sort(key=lambda item: (str(item["primary_exercise_id"] or item["exercise_id"]), str(item["exercise_id"])))
        planned_sets_total = int(workout.get("planned_sets_total", 0) or 0)
        planned_set_count_total += planned_sets_total
        workouts.append(
            {
                "workout_id": workout_id,
                "program_id": workout.get("program_id"),
                "total_sets": int(workout["total_sets"]),
                "total_volume": _round2(float(workout["total_volume"])),
                "planned_sets_total": planned_sets_total,
                "set_delta": int(workout["total_sets"] - planned_sets_total),
                "exercises": exercise_entries,
            }
        )
        total_sets += int(workout["total_sets"])
        total_volume += float(workout["total_volume"])

    return workouts, total_sets, total_volume, unique_exercise_ids, planned_set_count_total


def _build_planned_only_workouts(
    planned_sessions: dict[str, dict[str, Any]],
    existing_workout_ids: set[str],
) -> tuple[list[dict[str, Any]], set[str], int]:
    workouts: list[dict[str, Any]] = []
    unique_exercise_ids: set[str] = set()
    planned_set_count_total = 0

    for workout_id in sorted(planned_sessions.keys()):
        if workout_id in existing_workout_ids:
            continue
        planned_entry = planned_sessions[workout_id]
        planned_by_exercise = planned_entry.get("planned_by_exercise", {})
        planned_exercises = [
            {
                "exercise_id": exercise_id,
                "primary_exercise_id": exercise_id,
                "planned_name": str(exercise_info.get("planned_name") or exercise_id),
                "primary_muscles": list(exercise_info.get("primary_muscles") or []),
                "sets": [],
                "total_sets": 0,
                "total_volume": 0.0,
                "planned_sets": int(exercise_info.get("planned_sets") or 0),
                "set_delta": int(0 - int(exercise_info.get("planned_sets") or 0)),
            }
            for exercise_id, exercise_info in sorted(planned_by_exercise.items())
        ]
        planned_sets_total = int(planned_entry.get("planned_sets_total", 0) or 0)
        planned_set_count_total += planned_sets_total
        unique_exercise_ids.update(str(exercise_id) for exercise_id in planned_by_exercise.keys())
        workouts.append(
            {
                "workout_id": workout_id,
                "program_id": planned_entry.get("program_id"),
                "total_sets": 0,
                "total_volume": 0.0,
                "planned_sets_total": planned_sets_total,
                "set_delta": int(0 - planned_sets_total),
                "exercises": planned_exercises,
            }
        )

    return workouts, unique_exercise_ids, planned_set_count_total


def build_history_analytics(
    *,
    checkin_rows: list[Any],
    log_rows: list[Any],
    measurement_rows: list[Any],
    limit_weeks: int,
    checkin_limit: int,
    today: date | None = None,
) -> dict[str, Any]:
    resolved_today = today or date.today()
    capped_weeks = max(2, min(26, int(limit_weeks)))
    capped_checkin_limit = max(4, min(52, int(checkin_limit)))
    start_date = _monday_of(resolved_today) - timedelta(days=(capped_weeks - 1) * 7)

    ordered_checkins = sorted(checkin_rows, key=lambda row: _read_attr(row, "week_start"))[-capped_checkin_limit:]
    checkins = [
        {
            "week_start": _read_attr(row, "week_start").isoformat(),
            "body_weight": float(_read_attr(row, "body_weight", 0.0)),
            "adherence_score": int(_read_attr(row, "adherence_score", 0)),
            "notes": _read_attr(row, "notes"),
            "created_at": _read_attr(row, "created_at").isoformat(),
        }
        for row in ordered_checkins
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

    ordered_logs = sorted(log_rows, key=lambda row: _read_attr(row, "created_at"))
    filtered_measurements = [row for row in measurement_rows if _read_attr(row, "measured_on") >= start_date]
    ordered_measurements = sorted(
        filtered_measurements,
        key=lambda row: (_read_attr(row, "measured_on"), _read_attr(row, "created_at")),
    )

    strength_trends, pr_highlights = _build_strength_trends(ordered_logs)
    measurement_trends = _build_body_measurement_trends(ordered_measurements)
    volume_heatmap = _build_volume_heatmap(ordered_logs, limit_weeks=capped_weeks, today=resolved_today)

    return {
        "window": {
            "start_date": start_date.isoformat(),
            "end_date": resolved_today.isoformat(),
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


def build_history_calendar(
    *,
    log_rows: list[Any],
    all_log_rows_until_end: list[Any],
    plans: list[Any],
    start_date: date,
    end_date: date,
    today: date | None = None,
) -> dict[str, Any]:
    resolved_today = today or date.today()
    ordered_logs = sorted(log_rows, key=lambda row: _read_attr(row, "created_at"))
    ordered_logs_until_end = sorted(all_log_rows_until_end, key=lambda row: _read_attr(row, "created_at"))
    planned_day_metadata = _extract_planned_calendar_metadata(plans, start_date, end_date)
    pr_day_metadata = _build_calendar_pr_metadata(
        ordered_logs_until_end,
        start_date=start_date,
        end_date=end_date,
    )
    days = _build_calendar_days(ordered_logs, start_date, end_date, planned_day_metadata, pr_day_metadata)
    completed_dates = [date.fromisoformat(day["date"]) for day in days if day["completed"]]
    current_streak_days, longest_streak_days = _build_streaks(completed_dates, today=resolved_today)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "active_days": len(completed_dates),
        "current_streak_days": current_streak_days,
        "longest_streak_days": longest_streak_days,
        "days": days,
    }


def build_history_day_detail(
    *,
    day: date,
    log_rows: list[Any],
    plans: list[Any],
) -> dict[str, Any]:
    planned_sessions = _extract_planned_sessions_for_day(plans, day)
    grouped = _accumulate_logged_day_rows(sorted(log_rows, key=lambda row: (_read_attr(row, "created_at"), _read_attr(row, "set_index", 0))), planned_sessions)
    (
        workouts,
        total_sets,
        total_volume,
        unique_exercise_ids,
        planned_set_count_total,
    ) = _serialize_grouped_workouts(grouped)

    planned_only_workouts, planned_only_ids, planned_only_set_total = _build_planned_only_workouts(
        planned_sessions,
        existing_workout_ids={item["workout_id"] for item in workouts},
    )
    workouts.extend(planned_only_workouts)
    unique_exercise_ids.update(planned_only_ids)
    planned_set_count_total += planned_only_set_total

    return {
        "date": day.isoformat(),
        "workouts": workouts,
        "totals": {
            "set_count": int(total_sets),
            "exercise_count": len(unique_exercise_ids),
            "total_volume": _round2(total_volume),
            "planned_set_count": int(planned_set_count_total),
            "set_delta": int(total_sets - planned_set_count_total),
        },
    }