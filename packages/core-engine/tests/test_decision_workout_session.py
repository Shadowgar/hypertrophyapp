from types import SimpleNamespace

from core_engine.decision_workout_session import (
    build_workout_performance_summary,
    build_workout_today_plan_runtime,
    prepare_workout_exercise_state_runtime,
    prepare_workout_log_set_context_route_runtime,
    prepare_workout_log_set_decision_route_runtime,
    prepare_workout_log_set_response_runtime,
    prepare_workout_progress_route_runtime,
    prepare_workout_session_state_route_runtime,
    prepare_workout_summary_response_runtime,
    prepare_workout_summary_route_runtime,
    prepare_workout_today_plan_route_runtime,
    prepare_workout_today_progression_route_runtime,
    prepare_workout_today_response_runtime,
    prepare_workout_today_selection_route_runtime,
)


def _sample_rule_set() -> dict:
    return {
        "progression_rules": {
            "on_success": {"percent": 2.5},
            "on_under_target": {"reduce_percent": 2.0, "after_exposures": 2},
        },
        "deload_rules": {
            "scheduled_every_n_weeks": 4,
            "early_deload_trigger": "three_consecutive_under_target_exposures",
            "on_deload": {"load_reduction_percent": 10},
        },
        "fatigue_rules": {
            "high_fatigue_trigger": {
                "conditions": ["session_rpe_avg >= 9", "intro phase lasts 2 weeks"],
            },
            "on_high_fatigue": {"set_delta": -1},
        },
        "rationale_templates": {
            "increase_load": "Increase the load next time.",
            "hold_load": "Hold the load until reps stabilize.",
            "deload": "Take a short deload.",
            "below_target_reps_reduce_or_hold_load": "Reps fell short, so reduce or hold the load next time.",
            "within_target_reps_hold_or_microload": "Reps were on target, so hold steady or microload next time.",
            "above_target_reps_increase_load_next_exposure": "Reps were above target, so increase load next time.",
        },
    }


def test_prepare_workout_today_plan_route_runtime_builds_queryable_plan_context() -> None:
    runtime = prepare_workout_today_plan_route_runtime(
        plan_rows=[
            SimpleNamespace(
                payload={
                    "program_template_id": "full_body_v1",
                    "mesocycle": {"week_index": 2},
                    "deload": {"active": False},
                    "sessions": [
                        {"session_id": "day-1", "date": "2026-03-05"},
                        {"session_id": "day-2", "date": "2026-03-07"},
                    ],
                }
            )
        ]
    )

    assert runtime["has_plan"] is True
    assert runtime["session_ids"] == ["day-1", "day-2"]
    assert runtime["selected_program_id"] == "full_body_v1"
    assert runtime["mesocycle"] == {"week_index": 2}
    assert runtime["deload"] == {"active": False}
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_today_plan_route_runtime"


def test_build_workout_today_plan_runtime_normalizes_sessions_and_program_context() -> None:
    runtime = build_workout_today_plan_runtime(
        latest_plan_payload={
            "program_template_id": "full_body_v1",
            "mesocycle": {"week_index": 2},
            "deload": {"active": False},
            "sessions": [
                {"session_id": "full_body_v1-day-1", "name": "Day 1"},
                {"session_id": "full_body_v1-day-2", "name": "Day 2"},
            ],
        }
    )

    assert runtime["selected_program_id"] == "full_body_v1"
    assert runtime["session_ids"] == ["full_body_v1-day-1", "full_body_v1-day-2"]
    assert runtime["mesocycle"] == {"week_index": 2}
    assert runtime["deload"] == {"active": False}
    assert runtime["decision_trace"]["interpreter"] == "build_workout_today_plan_runtime"


def test_prepare_workout_exercise_state_runtime_builds_initial_and_updated_state_payloads() -> None:
    runtime = prepare_workout_exercise_state_runtime(
        existing_state=None,
        primary_exercise_id="bench_press",
        planned_exercise={
            "id": "bench_press",
            "name": "Bench Press",
            "start_weight": 100.0,
            "substitution_candidates": ["Machine Press"],
        },
        planned_weight=100.0,
        planned_sets=3,
        planned_reps_min=8,
        planned_reps_max=10,
        completed_set_index=1,
        completed_reps=10,
        nutrition_phase="maintenance",
        equipment_profile=["machine"],
        rule_set=_sample_rule_set(),
    )

    assert runtime["initial_state_values"]["current_working_weight"] >= 5.0
    assert runtime["state_values"]["exposure_count"] == 1
    assert runtime["state_values"]["last_progression_action"] in {"progress", "hold", "deload"}
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_exercise_state_runtime"


def test_build_workout_performance_summary_normalizes_rows_and_progression_state() -> None:
    payload = build_workout_performance_summary(
        workout_id="session-1",
        planned_session={
            "exercises": [
                {
                    "id": "bench",
                    "name": "Bench Press",
                    "sets": 3,
                    "rep_range": [8, 10],
                    "recommended_working_weight": 100.0,
                }
            ]
        },
        performed_logs=[
            SimpleNamespace(exercise_id="bench", set_index=1, reps=8, weight=100.0),
            SimpleNamespace(exercise_id="bench", set_index=2, reps=9, weight=100.0),
        ],
        progression_states=[SimpleNamespace(exercise_id="bench", current_working_weight=102.5)],
        rule_set=_sample_rule_set(),
    )

    assert payload["workout_id"] == "session-1"
    assert payload["completed_total"] == 2
    assert payload["planned_total"] == 3
    assert payload["exercises"][0]["next_working_weight"] == 102.5
    assert payload["decision_trace"]["interpreter"] == "summarize_workout_session_guidance"


def test_prepare_workout_today_selection_route_runtime_prefers_incomplete_resume_session() -> None:
    runtime = prepare_workout_today_selection_route_runtime(
        sessions=[
            {"session_id": "day-1", "date": "2026-03-05", "exercises": [{"id": "bench", "sets": 3}]},
            {"session_id": "day-2", "date": "2026-03-07", "exercises": [{"id": "row", "sets": 3}]},
        ],
        recent_logs=[
            SimpleNamespace(workout_id="day-1"),
        ],
        today_iso="2026-03-07",
    )

    assert runtime["selected_session"]["session_id"] == "day-1"
    assert runtime["selected_session_id"] == "day-1"
    assert runtime["resume_selected"] is True
    assert runtime["selection_reason"] == "resume_incomplete_session"
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_today_selection_route_runtime"


def test_prepare_workout_today_response_runtime_builds_final_today_payload() -> None:
    runtime = prepare_workout_today_response_runtime(
        selected_session={
            "session_id": "day-1",
            "name": "Day 1",
            "exercises": [
                {
                    "id": "bench",
                    "primary_exercise_id": "bench",
                    "name": "Bench Press",
                    "sets": 3,
                    "rep_range": [8, 10],
                    "recommended_working_weight": 100,
                }
            ],
        },
        selected_session_logs=[SimpleNamespace(exercise_id="bench", set_index=1)],
        session_states=[
            SimpleNamespace(
                exercise_id="bench",
                primary_exercise_id="bench",
                completed_sets=1,
                remaining_sets=2,
                recommended_reps_min=8,
                recommended_reps_max=10,
                recommended_weight=97.5,
                last_guidance="remaining_sets_reduce_load_focus_target_reps",
                substitution_recommendation=None,
            )
        ],
        progression_states=[],
        equipment_profile=["dumbbell"],
        rule_set=None,
        mesocycle={"week_index": 2},
        deload={"active": False},
        resume_selected=True,
        daily_quote={"text": "Discipline.", "author": "Marcus Aurelius", "source": "Meditations"},
    )

    payload = runtime["response_payload"]
    assert payload["session_id"] == "day-1"
    assert payload["resume"] is True
    assert payload["mesocycle"] == {"week_index": 2}
    assert payload["exercises"][0]["completed_sets"] == 1
    assert payload["exercises"][0]["live_recommendation"]["guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_today_response_runtime"


def test_prepare_workout_today_progression_route_runtime_builds_primary_ids_and_rule_set() -> None:
    runtime = prepare_workout_today_progression_route_runtime(
        session_states=[
            SimpleNamespace(primary_exercise_id="bench"),
            SimpleNamespace(primary_exercise_id="row"),
            SimpleNamespace(primary_exercise_id="bench"),
        ],
        selected_program_id="full_body_v1",
        resolve_linked_program_id=lambda template_id: template_id,
        load_rule_set=lambda template_id: {"program_id": template_id},
    )

    assert runtime["primary_exercise_ids"] == ["bench", "row"]
    assert runtime["rule_set"] == {"program_id": "full_body_v1"}
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_today_progression_route_runtime"


def test_prepare_workout_log_set_context_route_runtime_builds_request_plan_and_rule_context() -> None:
    runtime = prepare_workout_log_set_context_route_runtime(
        workout_id="day-1",
        plan_rows=[
            SimpleNamespace(
                payload={
                    "program_template_id": "full_body_v1",
                    "sessions": [
                        {
                            "session_id": "day-1",
                            "exercises": [
                                {
                                    "id": "bench-alt",
                                    "primary_exercise_id": "bench",
                                    "sets": 3,
                                    "rep_range": [8, 10],
                                    "recommended_working_weight": 100,
                                }
                            ],
                        }
                    ],
                }
            )
        ],
        primary_exercise_id=None,
        exercise_id="bench-alt",
        set_index=1,
        reps=8,
        weight=100.0,
        rpe=8.5,
        resolve_linked_program_id=lambda template_id: template_id,
        load_rule_set=lambda template_id: {"program_id": template_id},
    )

    assert runtime["primary_exercise_id"] == "bench-alt"
    assert runtime["program_id"] == "full_body_v1"
    assert runtime["planned_exercise"]["id"] == "bench-alt"
    assert runtime["rule_set"] == {"program_id": "full_body_v1"}
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_log_set_context_route_runtime"


def test_prepare_workout_log_set_decision_route_runtime_wraps_log_set_runtime() -> None:
    runtime = prepare_workout_log_set_decision_route_runtime(
        user_id="user_123",
        workout_id="day-1",
        existing_exercise_state=None,
        request_runtime={
            "primary_exercise_id": "bench",
            "exercise_id": "bench",
            "set_index": 1,
            "reps": 6,
            "weight": 100.0,
            "rpe": None,
        },
        planned_exercise={
            "id": "bench",
            "sets": 3,
            "rep_range": [8, 10],
            "recommended_working_weight": 100.0,
        },
        nutrition_phase="maintenance",
        equipment_profile=["dumbbell"],
        rule_set=None,
    )

    assert runtime["record_values"]["user_id"] == "user_123"
    assert runtime["exercise_state_create_values"]["exercise_id"] == "bench"
    assert runtime["session_state_inputs"]["planned_sets"] == 3
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_log_set_decision_route_runtime"


def test_prepare_workout_session_state_route_runtime_shapes_state_create_and_live_payload() -> None:
    runtime = prepare_workout_session_state_route_runtime(
        existing_state=None,
        user_id="user_123",
        workout_id="day-1",
        exercise_id="bench",
        primary_exercise_id="bench",
        planned_sets=3,
        planned_rep_range=(8, 10),
        planned_weight=100.0,
        set_index=1,
        reps=6,
        weight=100.0,
        substitution_recommendation=None,
        rule_set=None,
    )

    assert runtime["create_values"]["user_id"] == "user_123"
    assert runtime["create_values"]["workout_id"] == "day-1"
    assert runtime["create_values"]["exercise_id"] == "bench"
    assert runtime["live_recommendation"]["completed_sets"] == 1
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_session_state_route_runtime"


def test_prepare_workout_log_set_response_runtime_builds_final_response_payload() -> None:
    runtime = prepare_workout_log_set_response_runtime(
        record=SimpleNamespace(
            id="log_123",
            primary_exercise_id="bench",
            exercise_id="bench",
            set_index=1,
            reps=6,
            weight=100.0,
            created_at="2026-03-10T10:00:00",
        ),
        decision_runtime={
            "planned_reps_min": 8,
            "planned_reps_max": 10,
            "planned_weight": 100.0,
            "feedback": {
                "rep_delta": -2,
                "weight_delta": 0.0,
                "next_working_weight": 100.0,
                "guidance": "below_target_reps_reduce_or_hold_load",
                "guidance_rationale": "Below target.",
                "decision_trace": {"interpreter": "interpret_workout_set_feedback"},
            },
            "starting_load_runtime": {"decision_trace": {"interpreter": "resolve_starting_load"}},
        },
        live_recommendation={
            "completed_sets": 1,
            "remaining_sets": 2,
            "recommended_reps_min": 8,
            "recommended_reps_max": 10,
            "recommended_weight": 97.5,
            "guidance": "remaining_sets_reduce_load_focus_target_reps",
            "guidance_rationale": "Trim load.",
            "decision_trace": {"interpreter": "recommend_live_workout_adjustment"},
        },
    )

    payload = runtime["response_payload"]
    assert payload["id"] == "log_123"
    assert payload["planned_reps_min"] == 8
    assert payload["decision_trace"]["interpreter"] == "interpret_workout_set_feedback"
    assert payload["live_recommendation"]["guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_log_set_response_runtime"


def test_prepare_workout_progress_route_runtime_builds_payload_from_logs_and_plan_context() -> None:
    runtime = prepare_workout_progress_route_runtime(
        workout_id="day-1",
        plan_rows=[
            SimpleNamespace(
                payload={
                    "sessions": [
                        {
                            "session_id": "day-1",
                            "exercises": [
                                {"id": "bench", "sets": 3},
                                {"id": "row", "sets": 2},
                            ],
                        }
                    ]
                }
            )
        ],
        selected_session_logs=[SimpleNamespace(exercise_id="bench", set_index=1)],
    )

    payload = runtime["response_payload"]
    assert payload["workout_id"] == "day-1"
    assert payload["completed_total"] == 1
    assert payload["planned_total"] == 5
    assert payload["exercises"][0]["exercise_id"] == "bench"
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_progress_route_runtime"


def test_prepare_workout_summary_route_runtime_builds_progression_query_context() -> None:
    runtime = prepare_workout_summary_route_runtime(
        workout_id="day-1",
        plan_rows=[
            SimpleNamespace(
                payload={
                    "program_template_id": "full_body_v1",
                    "sessions": [
                        {
                            "session_id": "day-1",
                            "exercises": [
                                {"id": "bench-alt", "primary_exercise_id": "bench"},
                                {"id": "row"},
                                {"id": "bench-alt-2", "primary_exercise_id": "bench"},
                            ],
                        }
                    ],
                }
            )
        ],
        resolve_linked_program_id=lambda template_id: template_id,
        load_rule_set=lambda template_id: {"program_id": template_id},
    )

    assert runtime["has_session"] is True
    assert runtime["program_id"] == "full_body_v1"
    assert runtime["rule_set"] == {"program_id": "full_body_v1"}
    assert runtime["session"]["session_id"] == "day-1"
    assert runtime["primary_exercise_ids"] == ["bench", "row"]
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_summary_route_runtime"


def test_prepare_workout_summary_response_runtime_builds_summary_payload() -> None:
    runtime = prepare_workout_summary_response_runtime(
        workout_id="day-1",
        planned_session={
            "session_id": "day-1",
            "exercises": [
                {
                    "id": "bench",
                    "primary_exercise_id": "bench",
                    "sets": 3,
                    "rep_range": [8, 10],
                    "recommended_working_weight": 100.0,
                }
            ],
        },
        performed_logs=[SimpleNamespace(exercise_id="bench", set_index=1, reps=6, weight=100.0)],
        progression_states=[SimpleNamespace(exercise_id="bench", current_working_weight=100.0)],
        rule_set=None,
    )

    assert runtime["response_payload"]["workout_id"] == "day-1"
    assert runtime["response_payload"]["exercises"][0]["exercise_id"] == "bench"
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_summary_response_runtime"


def test_prepare_workout_summary_route_runtime_handles_missing_session() -> None:
    runtime = prepare_workout_summary_route_runtime(
        workout_id="missing-day",
        plan_rows=[SimpleNamespace(payload={"sessions": [{"session_id": "day-1", "exercises": []}]})],
    )

    assert runtime["has_session"] is False
    assert runtime["session"] is None
    assert runtime["primary_exercise_ids"] == []
    assert runtime["decision_trace"]["outcome"]["has_session"] is False
