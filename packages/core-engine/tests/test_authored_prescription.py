from datetime import date, timedelta
from core_engine.authored_prescription import preserve_prescription, uniform_rep_range
from core_engine.decision_weekly_review import summarize_weekly_review_performance


def test_distinct_targets_effort_ranges_and_explicit_top_backoff_roles():
    prescription = preserve_prescription({"reps": "top:6;backoff:10", "early_set_rpe": "~7-8",
        "last_set_rpe": "~9-10", "rest": "2-3 min", "last_set_intensity_technique": "Example technique"}, 2)
    first, last = prescription["sets"]
    assert (first["set_type"], last["set_type"]) == ("top", "backoff")
    assert first["rep_target"]["min"] == 6 and last["rep_target"]["min"] == 10
    assert first["effort_target"]["min"] == 7 and first["effort_target"]["max"] == 8
    assert last["effort_target"]["min"] == 9 and last["effort_target"]["max"] == 10
    assert first["intensity_technique"] is None and last["intensity_technique"] == "Example technique"
    assert all(item["rest"] == "2-3 min" for item in prescription["sets"])
    assert uniform_rep_range(prescription) is None


def test_missing_values_and_source_expressions_are_not_synthesized():
    prescription = preserve_prescription({"reps": "5,4,3+", "early_set_rpe": "2-3", "tracking_set_1": "Example tracking"}, 3, effort_kind="rir")
    assert [item["rep_target"]["raw"] for item in prescription["sets"]] == ["5", "4", "3+"]
    assert prescription["sets"][-1]["rep_target"] == {"kind": "text", "raw": "3+"}
    assert prescription["sets"][0]["effort_target"]["kind"] == "rir"
    assert prescription["sets"][-1]["effort_target"] == {"kind": "unknown", "raw": None}
    assert prescription["raw"]["tracking_set_1"] == "Example tracking"
    assert prescription["raw"]["warm_up_sets"] is None
    assert all(item["rest"] is None for item in prescription["sets"])
    assert uniform_rep_range(prescription) is None


def test_review_retains_counts_and_excludes_incompatible_numeric_faults():
    start = date(2026, 9, 21)
    amrap = {"id": "example", "sets": 2, "rep_range": None, "recommended_working_weight": 20,
        "authored_prescription": preserve_prescription({"reps": "AMRAP"}, 2)}
    amrap["exercise_occurrence_id"] = "typed-occurrence"
    numeric = {"id": "example", "exercise_occurrence_id": "numeric-occurrence", "sets": 1,
        "rep_range": [8, 12], "recommended_working_weight": 20}
    summary = summarize_weekly_review_performance(previous_week_start=start, week_start=start + timedelta(days=7),
        previous_plan_payload={"sessions": [{"exercises": [amrap, numeric]}]},
        performed_logs=[{"exercise_id": "example", "exercise_occurrence_id": "typed-occurrence", "reps": 30, "weight": 0},
            {"exercise_id": "example", "exercise_occurrence_id": "numeric-occurrence", "reps": 5, "weight": 20}])
    assert summary["planned_sets_total"] == 3 and summary["completed_sets_total"] == 2
    fault = summary["exercise_faults"][0]
    assert fault["planned_sets"] == 1 and fault["completed_sets"] == 1
    assert fault["average_performed_reps"] == 5 and "below_target_reps" in fault["fault_reasons"]
    assert summary["decision_trace"]["steps"][0]["numeric_fault_classification_excluded"]


def test_review_source_slot_fallback_retains_numeric_cohort_and_marks_legacy_ambiguity():
    start = date(2026, 9, 21)
    typed = {"id": "shared", "sets": 2, "rep_range": None,
        "source_lineage": {"source_sha256": "source", "source_slot_id": "typed-slot"},
        "authored_prescription": preserve_prescription({"reps": "AMRAP"}, 2)}
    numeric = {"id": "shared", "sets": 1, "rep_range": [8, 12], "recommended_working_weight": 20,
        "source_lineage": {"source_sha256": "source", "source_slot_id": "numeric-slot"}}
    summary = summarize_weekly_review_performance(previous_week_start=start, week_start=start + timedelta(days=7),
        previous_plan_payload={"sessions": [{"exercises": [typed, numeric]}]}, performed_logs=[
            {"exercise_id": "shared", "reps": 30, "weight": 0, "replay_context": {"planned_exercise": typed}},
            {"exercise_id": "shared", "reps": 5, "weight": 20, "replay_context": {"planned_exercise": numeric}},
            {"exercise_id": "shared", "reps": 99, "weight": 20}])
    assert summary["planned_sets_total"] == 3 and summary["completed_sets_total"] == 3
    fault = summary["exercise_faults"][0]
    assert fault["completed_sets"] == 1 and fault["average_performed_reps"] == 5
    assert "below_target_reps" in fault["fault_reasons"]
    assert summary["decision_trace"]["steps"][0]["ambiguous_legacy_log_count"] == 1
