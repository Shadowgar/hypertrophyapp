from copy import deepcopy
from core_engine.authored_constraints import annotate_constraints
from core_engine.authored_prescription import preserve_prescription
from core_engine.scheduler import generate_week_plan, AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY


def source_exercise(id, pattern):
    return {"id": id, "name": id, "sets": 2, "rep_range": [8, 12], "start_weight": 20,
        "movement_pattern": pattern, "primary_muscles": ["quads" if pattern == "squat" else "shoulders"],
        "equipment_tags": ["bodyweight"], "authored_prescription": preserve_prescription(
            {"reps": "8-12", "early_set_rpe": "8", "last_set_rpe": "9", "rest": "2 min"}, 2),
        "source_lineage": {"source_slot_id": id, "source_sha256": "source"}}


def test_authored_restrictions_never_unlock_dose_or_weak_point_overlays():
    squat, shoulder, arm = source_exercise("squat-slot", "squat"), source_exercise("shoulder-slot", "vertical_press"), source_exercise("arm-slot", "isolation")
    squat["source_approved_alternatives"] = [{"option_id": "source-option", "id": "hinge", "name": "Hinge",
        "movement_pattern": "hinge", "equipment_tags": ["bodyweight"], "permission": {"source_slot_id": "squat-slot"}}]
    template = {"id": "example", "version": "1", "split": "full_body", "days_supported": [2],
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 50, "load_reduction_pct": 20},
        "progression": {"mode": "double_progression", "increment_kg": 2.5},
        "sessions": [{"name": "Source", "exercises": [squat, shoulder, arm]}], AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY: True}
    plans = [generate_week_plan({"name": "Synthetic"}, 2, "full_body", deepcopy(template), [], "maintenance",
        weak_areas=["shoulders", "biceps"], session_time_budget_minutes=15, movement_restrictions=r)
        for r in [[], ["unmatched"], ["deep_knee_flexion"]]]
    keys = ["id", "name", "sets", "rep_range", "authored_prescription", "source_lineage", "slot_role"]
    baseline = [{k: e.get(k) for k in keys} for e in plans[0]["sessions"][0]["exercises"]]
    for plan in plans:
        exercises = plan["sessions"][0]["exercises"]
        assert [{k: e.get(k) for k in keys} for e in exercises] == baseline
        assert len(exercises) == 3 and sum(e["sets"] for e in exercises) == 6
        assert all(not e.get("performed_variant") for e in exercises)
    conflicts = plans[2]["sessions"][0]["exercises"]
    assert conflicts[0]["authored_constraint"]["status"] == "unresolved"
    assert conflicts[0]["authored_constraint"]["allowed_alternatives"][0]["id"] == "hinge"
    assert all(e["authored_constraint"]["status"] == "ready" for e in conflicts[1:])


def test_missing_permission_and_incompatible_alternatives_remain_visible():
    source = source_exercise("slot", "squat")
    source["substitution_candidates"] = ["Generic option"]
    result = annotate_constraints(source, restrictions=["deep_knee_flexion"])
    assert result["id"] == source["id"] and result["authored_prescription"] == source["authored_prescription"]
    assert result["authored_constraint"]["status"] == "infeasible"
    assert result["substitution_candidates"] == []
    source["source_approved_alternatives"] = [{"id": "other-squat", "movement_pattern": "squat", "equipment_tags": ["barbell"]}]
    assert annotate_constraints(source, equipment=["dumbbell"], restrictions=["deep_knee_flexion"])["authored_constraint"]["allowed_alternatives"] == []


def test_generated_path_retains_existing_restriction_behavior():
    source = source_exercise("squat", "squat")
    source.pop("authored_prescription");source.pop("source_lineage")
    template = {"id": "generated", "sessions": [{"name": "Day", "exercises": [source, source_exercise("arm", "isolation")]}],
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 50, "load_reduction_pct": 20}}
    plan = generate_week_plan({"name": "Synthetic"}, 2, "full_body", template, [], "maintenance", movement_restrictions=["deep_knee_flexion"])
    assert all(e["id"] != "squat" and not e.get("authored_constraint") for s in plan["sessions"] for e in s["exercises"])


def test_variant_receipts_exclude_the_frozen_source_slot_from_raw_plan_load_advice():
    from datetime import date, timedelta
    from core_engine.decision_weekly_review import summarize_weekly_review_performance
    original = source_exercise("shared", "squat")
    original.update(sets=1, recommended_working_weight=20)
    original['source_lineage']['source_slot_id']='substituted-slot'
    numeric=deepcopy(original);numeric['source_lineage']['source_slot_id']='numeric-slot'
    frozen=deepcopy(original);frozen['exercise_occurrence_id']='substituted-occurrence'
    frozen['performed_variant']={'id':'variant','name':'Variant','load_semantics':'external_load'}
    start=date(2026,9,21)
    summary=summarize_weekly_review_performance(previous_week_start=start,week_start=start+timedelta(days=7),
        previous_plan_payload={'sessions':[{'exercises':[original,numeric]}]},performed_logs=[
            {'exercise_id':'shared','exercise_occurrence_id':'substituted-occurrence','reps':30,'weight':50,
             'replay_context':{'planned_exercise':frozen}},
            {'exercise_id':'shared','reps':5,'weight':20,'replay_context':{'planned_exercise':numeric}}])
    assert summary['planned_sets_total']==summary['completed_sets_total']==2
    assert len(summary['exercise_faults'])==1
    fault=summary['exercise_faults'][0]
    assert fault['planned_sets']==fault['completed_sets']==1
    assert fault['average_performed_reps']==5 and 'missed_sets' not in fault['fault_reasons']
    assert 'below_target_reps' in fault['fault_reasons']
