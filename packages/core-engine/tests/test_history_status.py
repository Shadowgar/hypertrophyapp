from datetime import date, datetime
from types import SimpleNamespace

from core_engine import build_history_calendar

DAY = date(2026, 10, 21)


def session(identity="occ", sets=2):
    return {"workout_occurrence_id": identity, "session_id": "same-template", "title": "Workout A", "date": str(DAY),
            "exercises": [{"id": "press", "exercise_occurrence_id": f"{identity}-{slot}", "sets": sets} for slot in ("left", "right")]}


def plan(sessions=None):
    return SimpleNamespace(payload={"program_template_id": "authored-phase-1", "schedule": {
        "mode": "selected_dates_v1", "week_start": "2026-10-19", "selected_dates": [str(DAY)], "timezone": "UTC"},
        "sessions": [session()] if sessions is None else sessions})


def receipt(slot="left", index=1, kind="work", **extra):
    return {"id": f"{slot}-{index}-{kind}", "workout_id": "same-template", "workout_occurrence_id": "occ",
            "exercise_occurrence_id": f"occ-{slot}", "exercise_id": "press", "set_index": index, "set_kind": kind,
            "parent_set_index": None, "weight": 10, "reps": 8, "created_at": datetime(2026, 10, 21, 12), **extra}


def calendar(rows, plans=None, start=DAY, end=DAY):
    return build_history_calendar(log_rows=rows, all_log_rows_until_end=rows, plans=[plan()] if plans is None else plans,
                                  start_date=start, end_date=end, today=DAY)["days"]


def test_completion_requires_every_unique_work_set_in_every_distinct_slot():
    rows = [receipt("left", 1), receipt("left", 2), receipt("right", 1)]
    partial = calendar(rows + [receipt("left", 1), receipt("right", 2, "warmup"), receipt("right", 2, parent_set_index=1)])[0]
    assert (partial["status"], partial["working_sets_completed"], partial["working_sets_planned"]) == ("partial", 3, 4)
    complete = calendar(rows + [receipt("right", 2)])[0]
    assert complete["status"] == "complete"
    assert complete["occurrences"][0]["workout_occurrence_id"] == "occ"
    assert calendar(rows)[0]["status"] == "partial"  # Effective undo removes its completion effect.


def test_known_schedule_rest_and_unknown_are_distinct_from_incomplete_work():
    days = calendar([], start=date(2026, 10, 20), end=date(2026, 10, 22))
    assert [day["status"] for day in days] == ["rest", "scheduled", "rest"]
    assert calendar([], plans=[])[0]["status"] == "unknown"
    assert calendar([receipt(kind="warmup")])[0]["status"] == "partial"
    assert calendar([receipt(workout_occurrence_id=None, exercise_occurrence_id=None)])[0]["status"] == "unknown"


def test_ambiguous_or_missing_slot_evidence_cannot_claim_completion():
    ambiguous = session()
    ambiguous["exercises"][1]["exercise_occurrence_id"] = "occ-left"
    assert calendar([receipt("left", 1), receipt("left", 2)], plans=[plan([ambiguous])])[0]["status"] == "unknown"
    assert calendar([receipt("foreign", 1)])[0]["status"] == "unknown"


def test_voids_and_technique_children_do_not_fill_required_work():
    rows = [receipt("left", 1), receipt("left", 2), receipt("right", 1), receipt("right", 2, voided_at=datetime(2026, 10, 22))]
    assert calendar(rows)[0]["working_sets_completed"] == 3
    assert calendar(rows)[0]["status"] == "partial"


def test_day_detail_keeps_repeated_catalog_slots_and_workout_occurrences_separate():
    from core_engine import build_history_day_detail
    first, second = session("occ"), session("occ-two")
    rows = [receipt("left", 1), receipt("right", 1), receipt("left", 1, workout_occurrence_id="occ-two", exercise_occurrence_id="occ-two-left")]
    detail = build_history_day_detail(day=DAY, log_rows=rows, plans=[plan([first, second])])
    assert len(detail["workouts"]) == 2
    one = next(item for item in detail["workouts"] if item["workout_occurrence_id"] == "occ")
    assert len(one["exercises"]) == 2
    assert {item["exercise_occurrence_id"] for item in one["exercises"]} == {"occ-left", "occ-right"}
    assert all(len(item["sets"]) == 1 for item in one["exercises"])


def test_analytics_separates_known_equipment_and_does_not_turn_warmups_into_working_loads():
    from core_engine import build_history_analytics
    def row(machine, weight, **extra):
        return receipt(weight=weight, replay_context={"planned_exercise": {"name": "Cable press"},
            "load_intelligence": {"load_context": {"unit": "kg", "basis": "machine_stack", "equipment_key": machine}}}, **extra)
    rows = [row("cable-a", 20), row("cable-b", 35), row("cable-a", 99, kind="warmup"), receipt(weight=80)]
    result = build_history_analytics(checkin_rows=[], log_rows=rows, measurement_rows=[], limit_weeks=4, checkin_limit=4, today=DAY)
    series = result["load_series"]
    assert len(series) == 2
    assert {item["equipment_key"]: item["points"][0]["max_weight"] for item in series} == {"cable-a": 20, "cable-b": 35}
    assert all(item["exercise_name"] == "Cable press" for item in series)
    assert result["load_series_unknown_sets"] == 1


def test_partial_detail_retains_unperformed_slots_without_inflating_catalog_count():
    from core_engine import build_history_day_detail
    detail = build_history_day_detail(day=DAY, log_rows=[receipt()], plans=[plan()])
    assert len(detail["workouts"][0]["exercises"]) == 2
    assert detail["totals"]["exercise_count"] == 1
    empty = next(item for item in detail["workouts"][0]["exercises"] if item["exercise_occurrence_id"] == "occ-right")
    assert empty["sets"] == []
    assert empty["planned_sets"] == 2


def test_rest_requires_consistent_schedule_and_completion_requires_every_occurrence():
    from copy import deepcopy
    source = plan()
    before = deepcopy(source.payload)
    broken = plan()
    broken.payload["schedule"]["selected_dates"] = ["2026-10-20"]
    assert calendar([], [broken], start=date(2026, 10, 20), end=date(2026, 10, 20))[0]["status"] == "unknown"
    other = session("second")
    rows = [receipt(slot, index, kind="top" if index == 1 else "backoff") for slot in ("left", "right") for index in (1, 2)]
    assert calendar(rows, [plan([session(), other])])[0]["status"] == "partial"
    assert calendar(rows, [source])[0]["status"] == "complete"
    assert source.payload == before


def test_legacy_occurrence_date_disagreement_cannot_move_completion_to_planned_day():
    from datetime import timedelta
    actual_day = DAY + timedelta(days=1)
    rows = [receipt(slot, index, performed_date=actual_day) for slot in ("left", "right") for index in (1, 2)]
    days = calendar(rows, start=DAY, end=actual_day)
    assert [item["status"] for item in days] == ["unknown", "unknown"]
    assert days[0]["occurrences"][0]["status"] == "unknown"
