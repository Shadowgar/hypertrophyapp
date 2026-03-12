from datetime import date

from core_engine.decision_weekly_review import (
    apply_weekly_review_adjustments_to_plan,
    build_weekly_review_performance_summary,
    prepare_weekly_review_summary_route_runtime,
    prepare_weekly_review_status_route_runtime,
    prepare_weekly_review_submit_route_runtime,
    prepare_weekly_review_submit_persistence_values,
    build_weekly_review_decision_payload,
    interpret_weekly_review_decision,
    summarize_weekly_review_performance,
    resolve_weekly_review_window,
)


def test_resolve_weekly_review_window_rolls_to_next_week_on_sunday() -> None:
    window = resolve_weekly_review_window(today=date(2026, 3, 8))

    assert window["today_is_sunday"] is True
    assert window["current_week_start"] == date(2026, 3, 2)
    assert window["week_start"] == date(2026, 3, 9)
    assert window["previous_week_start"] == date(2026, 3, 2)


def test_interpret_weekly_review_decision_emits_structured_decision_trace() -> None:
    decision = interpret_weekly_review_decision(
        summary={
            "completion_pct": 90,
            "faulty_exercise_count": 1,
            "exercise_faults": [
                {
                    "primary_exercise_id": "bench_press",
                    "fault_score": 1,
                    "fault_reasons": ["above_target_reps"],
                    "completion_pct": 100,
                }
            ],
        },
        body_weight=80.0,
        calories=2700,
        protein=170,
        adherence_score=4,
    )
    payload = build_weekly_review_decision_payload(
        summary={
            "completion_pct": 90,
            "faulty_exercise_count": 1,
            "exercise_faults": [
                {
                    "primary_exercise_id": "bench_press",
                    "fault_score": 1,
                    "fault_reasons": ["above_target_reps"],
                    "completion_pct": 100,
                }
            ],
        },
        body_weight=80.0,
        calories=2700,
        protein=170,
        adherence_score=4,
    )

    assert decision["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"
    assert payload["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"


def test_interpret_weekly_review_decision_consumes_readiness_state_with_trace_source() -> None:
    decision = interpret_weekly_review_decision(
        summary={
            "completion_pct": 100,
            "faulty_exercise_count": 0,
            "exercise_faults": [],
        },
        body_weight=80.0,
        calories=2800,
        protein=160,
        adherence_score=4,
        readiness_state={
            "sleep_quality": 2,
            "stress_level": 4,
            "pain_flags": ["elbow_flexion"],
        },
    )

    readiness_step = next(
        step for step in decision["decision_trace"]["steps"] if step["decision"] == "readiness_state_adjustments"
    )

    assert decision["readiness_score"] == 81
    assert readiness_step["result"]["source"] == "context_readiness_state"
    assert [rule["rule"] for rule in readiness_step["result"]["matched_rules"]] == [
        "low_sleep",
        "high_stress",
        "pain_flags_present",
    ]


def test_interpret_weekly_review_decision_uses_sfr_snapshot_for_recovery_limited_guidance() -> None:
    decision = interpret_weekly_review_decision(
        summary={
            "completion_pct": 92,
            "faulty_exercise_count": 1,
            "exercise_faults": [],
        },
        body_weight=80.0,
        calories=2800,
        protein=160,
        adherence_score=4,
        readiness_state={
            "sleep_quality": 2,
            "stress_level": 4,
            "pain_flags": ["elbow_flexion"],
        },
    )

    sfr_step = next(
        step for step in decision["decision_trace"]["steps"] if step["decision"] == "stimulus_fatigue_response"
    )

    assert decision["global_guidance"] == "recovery_limited_reduce_load_and_complete_quality_volume"
    assert sfr_step["result"]["source"] == "weekly_review_inputs"
    assert sfr_step["result"]["recoverability"] == "low"
    assert sfr_step["result"]["deload_pressure"] == "high"
    assert decision["decision_trace"]["outcome"]["stimulus_fatigue_response_source"] == "weekly_review_inputs"


def test_interpret_weekly_review_decision_prefers_canonical_coaching_state_sfr_with_trace_source() -> None:
    canonical_snapshot = {
        "stimulus_quality": "low",
        "fatigue_cost": "high",
        "recoverability": "low",
        "progression_eligibility": False,
        "deload_pressure": "high",
        "substitution_pressure": "moderate",
        "signals": {
            "stimulus": ["low_adherence"],
            "fatigue": ["high_stress"],
            "recoverability": ["stress_limited", "fatigue_limited"],
        },
    }

    decision = interpret_weekly_review_decision(
        summary={
            "completion_pct": 100,
            "faulty_exercise_count": 0,
            "exercise_faults": [],
        },
        body_weight=80.0,
        calories=2800,
        protein=160,
        adherence_score=5,
        coaching_state={
            "stimulus_fatigue_response": canonical_snapshot,
        },
    )

    sfr_step = next(
        step for step in decision["decision_trace"]["steps"] if step["decision"] == "stimulus_fatigue_response"
    )

    assert decision["global_guidance"] == "recovery_limited_reduce_load_and_complete_quality_volume"
    assert sfr_step["result"]["source"] == "coaching_state.stimulus_fatigue_response"
    assert sfr_step["result"]["deload_pressure"] == "high"
    assert decision["decision_trace"]["outcome"]["stimulus_fatigue_response_source"] == (
        "coaching_state.stimulus_fatigue_response"
    )
    assert decision["decision_trace"]["outcome"]["stimulus_fatigue_response"] == canonical_snapshot


def test_interpret_weekly_review_decision_uses_sfr_to_bound_adjustments_and_suppress_positive_overrides() -> None:
    decision = interpret_weekly_review_decision(
        summary={
            "completion_pct": 100,
            "faulty_exercise_count": 1,
            "exercise_faults": [
                {
                    "primary_exercise_id": "bench_press",
                    "fault_score": 1,
                    "fault_reasons": ["above_target_reps"],
                    "completion_pct": 100,
                }
            ],
        },
        body_weight=80.0,
        calories=2500,
        protein=150,
        adherence_score=5,
        readiness_state={
            "sleep_quality": 2,
            "stress_level": 4,
            "pain_flags": ["elbow_flexion"],
        },
    )

    sfr_adjustment_step = next(
        step for step in decision["decision_trace"]["steps"] if step["decision"] == "stimulus_fatigue_adjustments"
    )
    override = decision["adjustments"]["exercise_overrides"][0]

    assert decision["adjustments"]["global_set_delta"] == -1
    assert decision["adjustments"]["global_weight_scale"] == 0.95
    assert override["set_delta"] == 0
    assert override["weight_scale"] == 1.0
    assert override["rationale"] == "recovery_limited_hold_progression"
    assert sfr_adjustment_step["result"]["allow_positive_progression"] is False
    assert sfr_adjustment_step["result"]["allow_weak_point_boost"] is False


def test_apply_weekly_review_adjustments_to_plan_sets_adaptive_review() -> None:
    adjusted = apply_weekly_review_adjustments_to_plan(
        plan_payload={
            "sessions": [
                {
                    "exercises": [
                        {
                            "id": "bench_press",
                            "primary_exercise_id": "bench_press",
                            "sets": 3,
                            "recommended_working_weight": 100.0,
                        }
                    ]
                }
            ]
        },
        review_adjustments={
            "global": {"set_delta": 1, "weight_scale": 0.95},
            "exercise_overrides": {"bench_press": {"set_delta": 0, "weight_scale": 1.0, "rationale": "maintain"}},
            "weak_point_exercises": ["bench_press"],
            "decision_trace": {"interpreter": "interpret_weekly_review_decision"},
        },
        review_context={"week_start": "2026-03-09", "reviewed_on": "2026-03-16"},
    )

    assert adjusted["adaptive_review"]["global_set_delta"] == 1
    assert adjusted["adaptive_review"]["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"


def test_summarize_weekly_review_performance_builds_fault_summary_and_trace() -> None:
    summary = summarize_weekly_review_performance(
        previous_week_start=date(2026, 3, 2),
        week_start=date(2026, 3, 9),
        previous_plan_payload={
            "sessions": [
                {
                    "exercises": [
                        {
                            "id": "bench_press",
                            "name": "Bench Press",
                            "sets": 3,
                            "rep_range": [8, 10],
                            "recommended_working_weight": 100.0,
                        }
                    ]
                }
            ]
        },
        performed_logs=[
            {"exercise_id": "bench_press", "reps": 7, "weight": 95.0},
            {"exercise_id": "bench_press", "reps": 8, "weight": 95.0},
        ],
    )

    assert summary["planned_sets_total"] == 3
    assert summary["completed_sets_total"] == 2
    assert summary["faulty_exercise_count"] == 1
    assert summary["exercise_faults"][0]["fault_score"] >= 1
    assert summary["decision_trace"]["interpreter"] == "summarize_weekly_review_performance"


def test_build_weekly_review_performance_summary_normalizes_rows() -> None:
    class _Plan:
        payload = {
            "sessions": [
                {
                    "exercises": [
                        {
                            "id": "lat_pulldown",
                            "name": "Lat Pulldown",
                            "sets": 2,
                            "rep_range": [10, 12],
                            "recommended_working_weight": 120.0,
                        }
                    ]
                }
            ]
        }

    class _Row:
        primary_exercise_id = "lat_pulldown"
        exercise_id = "lat_pulldown"
        reps = 12
        weight = 120.0

    summary = build_weekly_review_performance_summary(
        previous_week_start=date(2026, 3, 2),
        week_start=date(2026, 3, 9),
        previous_plan=_Plan(),
        performed_logs=[_Row()],
    )

    assert summary["planned_sets_total"] == 2
    assert summary["completed_sets_total"] == 1
    assert summary["decision_trace"]["interpreter"] == "summarize_weekly_review_performance"


def test_prepare_weekly_review_submit_persistence_values_shapes_checkin_and_review_rows() -> None:
    persistence_values = prepare_weekly_review_submit_persistence_values(
        user_id="user_123",
        reviewed_on=date(2026, 3, 16),
        week_start=date(2026, 3, 9),
        previous_week_start=date(2026, 3, 2),
        body_weight=81.2,
        calories=2750,
        protein=180,
        fat=70,
        carbs=320,
        adherence_score=4,
        notes="solid week",
        summary_payload={"planned_sets_total": 16},
        review_persistence_payload={
            "faults": {"exercise_faults": [{"primary_exercise_id": "bench_press"}]},
            "adjustments": {"global": {"set_delta": 0, "weight_scale": 1.0}},
        },
    )

    assert persistence_values["checkin_values"]["user_id"] == "user_123"
    assert persistence_values["checkin_values"]["week_start"] == date(2026, 3, 9)
    assert persistence_values["review_values"]["reviewed_on"] == date(2026, 3, 16)
    assert persistence_values["review_values"]["faults"]["exercise_faults"][0]["primary_exercise_id"] == "bench_press"
    assert persistence_values["decision_trace"]["interpreter"] == "prepare_weekly_review_submit_persistence_values"


def test_prepare_weekly_review_submit_route_runtime_shapes_submit_flow_payloads() -> None:
    runtime = prepare_weekly_review_submit_route_runtime(
        user_id="user_123",
        reviewed_on=date(2026, 3, 16),
        week_start=date(2026, 3, 9),
        previous_week_start=date(2026, 3, 2),
        body_weight=81.2,
        calories=2750,
        protein=180,
        fat=70,
        carbs=320,
        adherence_score=4,
        notes="solid week",
        nutrition_phase="maintenance",
        summary_payload={
            "faulty_exercise_count": 1,
            "exercise_faults": [
                {
                    "primary_exercise_id": "bench_press",
                    "fault_score": 1,
                    "fault_reasons": ["low_completion"],
                    "completion_pct": 80,
                }
            ],
        },
    )

    assert runtime["user_update_payload"]["weight"] == 81.2
    assert runtime["submit_persistence_values"]["checkin_values"]["user_id"] == "user_123"
    assert runtime["response_payload"]["status"] == "review_logged"
    assert runtime["response_payload"]["fault_count"] == 1
    assert runtime["decision_trace"]["interpreter"] == "prepare_weekly_review_submit_route_runtime"


def test_prepare_weekly_review_summary_route_runtime_shapes_summary_payload_and_trace() -> None:
    runtime = prepare_weekly_review_summary_route_runtime(
        previous_week_start=date(2026, 3, 2),
        week_start=date(2026, 3, 9),
        previous_plan={
            "payload": {
                "sessions": [
                    {
                        "exercises": [
                            {
                                "id": "bench_press",
                                "name": "Bench Press",
                                "sets": 2,
                                "rep_range": [8, 10],
                                "recommended_working_weight": 100.0,
                            }
                        ]
                    }
                ]
            }
        },
        performed_logs=[{"exercise_id": "bench_press", "reps": 8, "weight": 100.0}],
    )

    assert runtime["summary_payload"]["planned_sets_total"] == 2
    assert runtime["summary_payload"]["completed_sets_total"] == 1
    assert runtime["decision_trace"]["interpreter"] == "prepare_weekly_review_summary_route_runtime"


def test_prepare_weekly_review_status_route_runtime_shapes_response_and_window_trace() -> None:
    runtime = prepare_weekly_review_status_route_runtime(
        today=date(2026, 3, 8),
        existing_review_submitted=False,
        previous_week_summary={"faulty_exercise_count": 1},
    )

    assert runtime["response_payload"]["today_is_sunday"] is True
    assert runtime["response_payload"]["review_required"] is True
    assert runtime["decision_trace"]["interpreter"] == "prepare_weekly_review_status_route_runtime"
