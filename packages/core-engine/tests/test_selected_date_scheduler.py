from copy import deepcopy
from datetime import UTC, date, datetime

import pytest

from core_engine.selected_date_scheduler import (
    SelectedDateError, place_on_selected_dates, validate_selected_week,
)


MONDAY = date(2026, 9, 28)
INSTANT = datetime(2026, 9, 28, 16, tzinfo=UTC)


def selected(*days, timezone="America/New_York", instant=INSTANT):
    return validate_selected_week(
        week_start=MONDAY, selected_dates=list(days), timezone=timezone,
        planning_instant=instant,
    )


def source_plan():
    pair = [{"kind": "superset", "group_id": "A", "hard": True,
             "source_slot_ids": ["slot-a", "slot-b"]}]
    return {"week_start": MONDAY.isoformat(), "sessions": [
        {"session_id": "repeat", "date": "2026-09-28", "exercises": [
            {"id": "repeat", "sets": 3, "source_lineage": {"source_slot_id": "slot-a"},
             "source_relationships": pair},
            {"id": "repeat", "sets": 2, "source_lineage": {"source_slot_id": "slot-b"},
             "source_relationships": pair},
        ]},
        {"session_id": "repeat", "date": "2026-09-29", "exercises": [
            {"id": "other", "sets": 4, "source_lineage": {"source_slot_id": "slot-c"}},
        ]},
        {"session_id": "repeat", "date": "2026-09-30", "exercises": [
            {"id": "third", "sets": 2, "source_lineage": {"source_slot_id": "slot-d"}},
        ]},
    ]}


def test_tue_fri_sun_exact_dates_preserve_source_and_are_deterministic():
    original = source_plan()
    dates = selected(date(2026, 9, 29), date(2026, 10, 2), date(2026, 10, 4))
    first = place_on_selected_dates(original, dates, placement_revision=1)
    second = place_on_selected_dates(original, dates, placement_revision=1)
    assert first == second
    assert original == source_plan()
    assert [session["scheduled_date"] for session in first["sessions"]] == [
        "2026-09-29", "2026-10-02", "2026-10-04"]
    assert [session["exercises"] for session in first["sessions"]] == [
        session["exercises"] for session in original["sessions"]]
    assert first["schedule"]["spacing"]["gap_days"] == [3, 2]
    assert any("Adjacent-week" in warning for warning in first["schedule"]["spacing"]["warnings"])
    assert not any("Consecutive" in warning for warning in first["schedule"]["spacing"]["warnings"])


def test_tue_wed_thu_keeps_dates_and_explains_back_to_back_spacing():
    dates = selected(date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 1))
    result = place_on_selected_dates(source_plan(), dates, placement_revision=1)
    assert [s["scheduled_date"] for s in result["sessions"]] == [
        "2026-09-29", "2026-09-30", "2026-10-01"]
    assert result["schedule"]["spacing"]["gap_days"] == [1, 1]
    assert any("Consecutive" in warning for warning in result["schedule"]["spacing"]["warnings"])


def test_reschedule_retains_old_dates_in_placement_history():
    first = place_on_selected_dates(source_plan(), selected(
        date(2026, 9, 29), date(2026, 10, 2), date(2026, 10, 4)), placement_revision=1)
    second = place_on_selected_dates(first, selected(
        date(2026, 9, 28), date(2026, 9, 30), date(2026, 10, 3)), placement_revision=2, preserve_grouping=True)
    assert second["schedule"]["placement_history"] == [{
        "placement_revision": 1, "selected_dates": ["2026-09-29", "2026-10-02", "2026-10-04"],
        "timezone": "America/New_York"}]
    assert [s["exercises"] for s in second["sessions"]] == [s["exercises"] for s in first["sessions"]]


@pytest.mark.parametrize("dates,timezone,week_start", [
    ([date(2026, 9, 29), date(2026, 9, 29)], "America/New_York", MONDAY),
    ([date(2026, 9, 27), date(2026, 9, 29)], "America/New_York", MONDAY),
    ([], "America/New_York", MONDAY),
    ([date(2026, 9, 29)], "America/New_York", MONDAY),
    ([date(2026, 9, 29), date(2026, 10, 2)], "Mars/Olympus", MONDAY),
    ([date(2026, 9, 29), date(2026, 10, 2)], "America/New_York", date(2026, 10, 5)),
])
def test_invalid_current_week_input_rejects(dates, timezone, week_start):
    with pytest.raises(SelectedDateError):
        validate_selected_week(week_start=week_start, selected_dates=dates,
            timezone=timezone, planning_instant=INSTANT)


def test_timezone_and_dst_change_local_week_without_shifting_date_only_values():
    # UTC has crossed Monday while New York is still Sunday.
    instant = datetime(2026, 11, 2, 2, 30, tzinfo=UTC)
    local = validate_selected_week(week_start=date(2026, 10, 26),
        selected_dates=[date(2026, 10, 27), date(2026, 11, 1)],
        timezone="America/New_York", planning_instant=instant)
    result = place_on_selected_dates({"sessions": deepcopy(source_plan()["sessions"][:2])},
        local, placement_revision=1)
    assert [s["scheduled_date"] for s in result["sessions"]] == ["2026-10-27", "2026-11-01"]
    with pytest.raises(SelectedDateError):
        validate_selected_week(week_start=date(2026, 11, 2),
            selected_dates=[date(2026, 11, 3), date(2026, 11, 6)],
            timezone="America/New_York", planning_instant=instant)


def test_preserved_grouping_mismatched_count_is_infeasible_without_pruning():
    dates = selected(date(2026, 9, 29), date(2026, 10, 2))
    with pytest.raises(SelectedDateError, match="cannot fit"):
        place_on_selected_dates(source_plan(), dates, placement_revision=1, preserve_grouping=True)


def test_selected_date_count_change_regroups_losslessly_and_traces_candidates():
    original = source_plan()
    result = place_on_selected_dates(original, selected(date(2026, 9, 29), date(2026, 10, 2)), placement_revision=1)
    assert len(result["sessions"]) == 2
    assert [e for s in result["sessions"] for e in s["exercises"]] == [e for s in original["sessions"] for e in s["exercises"]]
    trace = result["schedule"]["decision_trace"]
    assert trace["allocation"]["candidate_count"] == 2
    assert trace["allocation"]["context_completeness"] == {"previous": "unknown", "next": "unknown"}
    assert trace["source_digest"]
    assert trace["rule_digest"]


def test_same_count_reschedule_preserves_session_and_exercise_identity_even_when_gap_changes():
    from test_authored_redistribution import _date_sensitive_source
    original = _date_sensitive_source()
    plan = {"sessions": [{"session_id": f"session-{index}", "exercises": original[0]["exercises"][index * 2:index * 2 + 2]}
        for index in range(3)]}
    result = place_on_selected_dates(plan, selected(date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 1)),
        placement_revision=2, preserve_grouping=True)
    assert [s["session_id"] for s in result["sessions"]] == ["session-0", "session-1", "session-2"]
    assert [s["exercises"] for s in result["sessions"]] == [s["exercises"] for s in plan["sessions"]]
    assert result["schedule"]["decision_trace"]["allocation"]["objective"]["consecutive_overlapping_working_sets"] == 4


def test_all_source_slots_in_one_hard_group_cannot_fill_selected_dates():
    original = source_plan()
    slots = ["slot-a", "slot-b", "slot-c", "slot-d"]
    relation = {"kind": "superset", "group_id": "all", "hard": True, "source_slot_ids": slots}
    for session in original["sessions"]:
        for exercise in session["exercises"]:
            exercise["source_relationships"] = [relation]
    with pytest.raises(SelectedDateError, match="fewer units"):
        place_on_selected_dates(original, selected(date(2026, 9, 29), date(2026, 10, 2)), placement_revision=1)


def test_date_only_neighbors_disclose_missing_work_even_when_dates_are_known():
    result = place_on_selected_dates(source_plan(), selected(date(2026, 9, 29), date(2026, 10, 2)),
        placement_revision=1, previous_date=date(2026, 9, 27), next_date=date(2026, 10, 5))
    assert result["schedule"]["spacing"]["gap_days"] == [2, 3, 3]
    assert any("workload context is unknown" in value for value in result["schedule"]["spacing"]["warnings"])


def test_explicit_minimum_rest_also_blocks_fixed_grouping_reschedule():
    relation = {"kind": "minimum_rest", "group_id": "rest", "hard": True,
        "source_slot_ids": ["slot-a", "slot-c"], "minimum_rest_days": 1}
    plan = {"sessions": source_plan()["sessions"][:2]}
    for session in plan["sessions"]:
        for exercise in session["exercises"]:
            if exercise["source_lineage"]["source_slot_id"] in {"slot-a", "slot-c"}:
                exercise["source_relationships"] = [*(exercise.get("source_relationships") or []), relation]
    with pytest.raises(SelectedDateError, match="minimum rest"):
        place_on_selected_dates(plan, selected(date(2026, 9, 29), date(2026, 9, 30)),
            placement_revision=2, preserve_grouping=True)


@pytest.mark.parametrize("instant,dates", [
    (datetime(2026, 9, 28, 16), [date(2026, 9, 29), date(2026, 10, 2)]),
    (INSTANT, [datetime(2026, 9, 29, 16, tzinfo=UTC), date(2026, 10, 2)]),
    (INSTANT, [date(2026, 9, day) for day in (28, 29, 30)] + [date(2026, 10, day) for day in (1, 2, 3)]),
])
def test_naive_instant_datetime_workout_or_six_dates_rejects(instant, dates):
    with pytest.raises(SelectedDateError):
        selected(*dates, instant=instant)


def test_dst_spring_change_preserves_sunday_calendar_date():
    local = validate_selected_week(week_start=date(2026, 3, 2),
        selected_dates=[date(2026, 3, 3), date(2026, 3, 8)], timezone="America/New_York",
        planning_instant=datetime(2026, 3, 8, 7, 30, tzinfo=UTC))
    result = place_on_selected_dates(source_plan(), local, placement_revision=1)
    assert [s["scheduled_date"] for s in result["sessions"]] == ["2026-03-03", "2026-03-08"]
    assert local.local_today == date(2026, 3, 8)


def test_duration_is_visible_as_uncalibrated_workload_uncertainty():
    result = place_on_selected_dates(source_plan(), selected(date(2026, 9, 29), date(2026, 10, 2)), placement_revision=1)
    assert any("Session duration is uncalibrated" in warning for warning in result["schedule"]["spacing"]["warnings"])
    assert result["schedule"]["decision_trace"]["workload"]["working_sets"] == [5, 6]


def test_native_five_day_grouping_can_be_preserved_on_initial_placement():
    plan = {"sessions": [{"session_id": f"native-{index}", "exercises": [
        {"id": "repeat", "sets": index + 1, "source_lineage": {"source_slot_id": f"slot-{index}"}}]}
        for index in range(5)]}
    result = place_on_selected_dates(plan, selected(date(2026, 9, 28), date(2026, 9, 29), date(2026, 9, 30),
        date(2026, 10, 1), date(2026, 10, 2)), placement_revision=1, preserve_grouping=True)
    assert [s["exercises"] for s in result["sessions"]] == [s["exercises"] for s in plan["sessions"]]
    assert [s["session_id"] for s in result["sessions"]] == [f"native-{index}" for index in range(5)]
    assert result["schedule"]["decision_trace"]["allocation"]["candidate_count"] == 1


@pytest.mark.parametrize("date_count", [2, 3])
def test_regrouped_runtime_sessions_keep_headers_and_source_template_session_keys(date_count):
    plan = source_plan()
    for index, session in enumerate(plan["sessions"]):
        session.update({"session_id": f"source-template-{index + 1}", "title": f"Source header {index + 1}", "session_index": index})
    result = place_on_selected_dates(plan, selected(*[date(2026, 9, 29), date(2026, 10, 2), date(2026, 10, 4)][:date_count]), placement_revision=1)
    assert [s["session_id"] for s in result["sessions"]] == [f"source-template-{index + 1}" for index in range(date_count)]
    assert [s["title"] for s in result["sessions"]] == [f"Source header {index + 1}" for index in range(date_count)]
    assert [s["session_index"] for s in result["sessions"]] == list(range(date_count))
    assert [e for s in result["sessions"] for e in s["exercises"]] == [e for s in plan["sessions"] for e in s["exercises"]]


def test_regroup_increasing_count_has_stable_fallback_session_headers_and_keys():
    plan = source_plan()
    for session in plan["sessions"]:
        session["exercises"][0]["source_relationships"] = []
    plan["sessions"][0]["exercises"][1]["source_relationships"] = []
    result = place_on_selected_dates(plan, selected(date(2026, 9, 28), date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 1)), placement_revision=1)
    extra = result["sessions"][3]
    assert extra["session_id"] == "selected-date-4"
    assert extra["title"] == "Adapted Full Body #4"
    assert extra["session_index"] == 3
    assert result == place_on_selected_dates(plan, selected(date(2026, 9, 28), date(2026, 9, 29), date(2026, 9, 30), date(2026, 10, 1)), placement_revision=1)


def test_neighbor_trace_uses_relevant_workload_summary_without_duplicated_prescriptions():
    import json
    context = {"date": date(2026, 9, 27), "exercises": [{"sets": 6, "primary_muscles": ["chest"],
        "recommended_working_weight": 123.75, "private_notes": "sensitive-neighbor-note", "authored_prescription": {"sets": [{"source_set_id": "neighbor-set"}]}}]}
    result = place_on_selected_dates(source_plan(), selected(date(2026, 9, 29), date(2026, 10, 2)), placement_revision=1, previous_context=context)
    summary = result["schedule"]["decision_trace"]["inputs"]["previous_context"]
    assert summary["date"] == "2026-09-27"
    assert summary["working_sets"] == 6
    assert summary["primary_muscle_working_sets"] == {"chest": 6}
    assert summary["context_digest"]
    emitted = json.dumps(result["schedule"]["decision_trace"])
    assert "recommended_working_weight" not in emitted
    assert "sensitive-neighbor-note" not in emitted
    assert "neighbor-set" not in emitted
