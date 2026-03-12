from datetime import UTC, date, datetime
import math
from types import SimpleNamespace

import pytest
import core_engine.intelligence as intelligence_module

from core_engine.intelligence import (
    apply_active_frequency_adaptation_runtime,
    apply_weekly_review_adjustments_to_plan,
    build_coach_preview_payloads,
    build_coach_preview_recommendation_record_fields,
    build_coaching_recommendation_timeline_entry,
    build_coaching_recommendation_timeline_payload,
    build_frequency_adaptation_apply_payload,
    build_generated_week_plan_payload,
    build_phase_applied_recommendation_record,
    build_repeat_failure_substitution_payload,
    build_workout_log_set_payload,
    prepare_workout_exercise_state_runtime,
    prepare_workout_log_set_decision_runtime,
    prepare_workout_log_set_request_runtime,
    build_workout_session_state_defaults,
    prepare_workout_session_state_upsert_runtime,
    resolve_workout_log_set_plan_context,
    build_program_recommendation_payload,
    prepare_workout_session_state_persistence_payload,
    prepare_program_recommendation_runtime,
    prepare_profile_program_recommendation_inputs,
    prepare_profile_program_recommendation_route_runtime,
    build_program_switch_payload,
    prepare_program_switch_runtime,
    build_specialization_applied_recommendation_record,
    build_weekly_review_decision_payload,
    build_weekly_review_performance_summary,
    prepare_weekly_review_submit_window,
    build_weekly_review_cycle_persistence_payload,
    build_soreness_entry_persistence_payload,
    build_body_measurement_create_payload,
    build_body_measurement_update_payload,
    prepare_profile_date_window_runtime,
    build_profile_upsert_persistence_payload,
    build_profile_response_payload,
    build_frequency_adaptation_persistence_state,
    build_generated_week_adaptation_persistence_payload,
    build_weekly_checkin_persistence_payload,
    build_weekly_checkin_response_payload,
    build_weekly_review_user_update_payload,
    prepare_weekly_review_log_window_runtime,
    build_weekly_review_submit_payload,
    build_workout_performance_summary,
    build_workout_summary_payload,
    build_workout_today_session_state_payloads,
    build_workout_today_state_payloads,
    build_workout_today_payload,
    resolve_workout_today_plan_payload,
    build_workout_today_plan_runtime,
    build_workout_today_log_runtime,
    build_workout_summary_progression_lookup_runtime,
    build_workout_today_progression_lookup_runtime,
    hydrate_live_workout_recommendation,
    finalize_applied_coaching_recommendation,
    group_workout_logs_by_exercise,
    interpret_coach_phase_apply_decision,
    interpret_coach_specialization_apply_decision,
    prepare_phase_apply_runtime,
    prepare_coaching_apply_runtime_source,
    prepare_specialization_apply_runtime,
    interpret_frequency_adaptation_apply,
    interpret_workout_set_feedback,
    interpret_weekly_review_decision,
    recommend_live_workout_adjustment,
    recommend_coach_intelligence_preview,
    recommend_frequency_adaptation_preview,
    build_workout_progress_payload,
    evaluate_schedule_adaptation,
    extract_coaching_recommendation_focus_muscles,
    derive_readiness_score,
    humanize_program_reason,
    recommend_phase_transition,
    recommend_program_selection,
    recommend_progression_action,
    recommend_specialization_adjustments,
    resolve_active_frequency_adaptation_runtime,
    resolve_latest_logged_workout_resume_state,
    resolve_program_recommendation_candidates,
    resolve_workout_completion_per_exercise,
    resolve_workout_plan_context,
    resolve_weekly_review_window,
    resolve_workout_plan_reference,
    resolve_workout_today_session_selection,
    summarize_workout_exercise_performance,
    summarize_workout_session_guidance,
    summarize_weekly_review_performance,
    summarize_program_media_and_warmups,
    resolve_workout_session_state_update,
    build_weekly_review_status_payload,
    normalize_coaching_recommendation_timeline_limit,
    prepare_generated_week_review_overlay,
)
from core_engine.decision_generated_week import (
    order_generation_template_candidates,
    recommend_generation_template_selection,
)


def _sample_rule_set() -> dict:
    return {
        "progression_rules": {
            "on_success": {"percent": 2.5},
            "on_under_target": {"reduce_percent": 2.5, "after_exposures": 2},
        },
        "fatigue_rules": {
            "high_fatigue_trigger": {
                "conditions": [
                    "intro phase lasts 2 weeks; avoid interpreting early underperformance as stall",
                    "session_rpe_avg >= 9 for two exposures",
                ]
            },
            "on_high_fatigue": {"action": "reduce_volume", "set_delta": -1},
        },
        "deload_rules": {
            "scheduled_every_n_weeks": 6,
            "early_deload_trigger": "repeated_under_target_plus_high_fatigue",
            "on_deload": {"set_reduction_percent": 35, "load_reduction_percent": 10},
        },
        "rationale_templates": {
            "increase_load": "Performance exceeded target range. Increase load next exposure.",
            "hold_load": "Performance stayed in range. Hold load and chase the rep ceiling.",
            "deload": "Fatigue and underperformance indicate that a short deload is warranted.",
        },
    }


def _sample_template() -> dict:
    return {
        "id": "intelligence_test_template",
        "sessions": [
            {
                "name": "Upper Push",
                "exercises": [
                    {
                        "id": "bench",
                        "name": "Bench Press",
                        "sets": 3,
                        "start_weight": 100,
                        "primary_muscles": ["chest", "triceps"],
                        "video": {"youtube_url": "https://www.youtube.com/watch?v=abc"},
                    }
                ],
            },
            {
                "name": "Upper Pull",
                "exercises": [
                    {
                        "id": "row",
                        "name": "Barbell Row",
                        "sets": 3,
                        "start_weight": 90,
                        "primary_muscles": ["back", "biceps"],
                        "video": None,
                    }
                ],
            },
            {
                "name": "Lower Quad",
                "exercises": [
                    {
                        "id": "squat",
                        "name": "Back Squat",
                        "sets": 4,
                        "start_weight": 120,
                        "primary_muscles": ["quads", "glutes"],
                    }
                ],
            },
            {
                "name": "Lower Hinge",
                "exercises": [
                    {
                        "id": "rdl",
                        "name": "Romanian Deadlift",
                        "sets": 3,
                        "start_weight": 110,
                        "primary_muscles": ["hamstrings", "glutes"],
                    }
                ],
            },
            {
                "name": "Shoulders Arms",
                "exercises": [
                    {
                        "id": "lateral_raise",
                        "name": "Lateral Raise",
                        "sets": 3,
                        "start_weight": 20,
                        "primary_muscles": ["shoulders"],
                    },
                    {
                        "id": "calf_raise",
                        "name": "Calf Raise",
                        "sets": 3,
                        "start_weight": 80,
                        "primary_muscles": ["calves"],
                    },
                ],
            },
        ],
    }


def _sample_onboarding_package() -> dict:
    return {
        "program_id": "pure_bodybuilding_phase_1_full_body",
        "frequency_adaptation_rules": {
            "default_training_days": 5,
            "minimum_temporary_days": 2,
            "max_temporary_weeks": 4,
            "weak_area_bonus_slots": 2,
            "preserve_slot_roles": ["primary_compound", "secondary_compound", "weak_point"],
            "reduce_slot_roles_first": ["isolation", "accessory"],
            "daily_slot_cap_when_compressed": 10,
            "reintegration_policy": "Rejoin authored week order after temporary constraint period.",
        },
        "blueprint": {
            "default_training_days": 5,
            "week_sequence": ["week_base"] * 10,
            "week_templates": [
                {
                    "week_template_id": "week_base",
                    "days": [
                        {"day_id": "d1", "slots": [{"exercise_id": "bench_press", "slot_role": "primary_compound", "primary_muscles": ["chest"]}]},
                        {"day_id": "d2", "slots": [{"exercise_id": "hack_squat", "slot_role": "primary_compound", "primary_muscles": ["quads"]}]},
                        {"day_id": "d3", "slots": [{"exercise_id": "row", "slot_role": "secondary_compound", "primary_muscles": ["back"]}]},
                        {"day_id": "d4", "slots": [{"exercise_id": "rdl", "slot_role": "primary_compound", "primary_muscles": ["hamstrings"]}]},
                        {"day_id": "d5", "slots": [{"exercise_id": "weak_chest_fly", "slot_role": "weak_point", "primary_muscles": ["chest"]}]},
                    ],
                }
            ],
        },
    }


def test_schedule_adaptation_reports_tradeoffs_and_muscle_delta() -> None:
    result = evaluate_schedule_adaptation(
        user_profile={"name": "Test"},
        split_preference="full_body",
        program_template=_sample_template(),
        history=[],
        phase="maintenance",
        from_days=5,
        to_days=3,
    )

    assert result["from_days"] == 5
    assert result["to_days"] == 3
    assert result["dropped_sessions"]
    assert any("density" in item.lower() for item in result["tradeoffs"])
    assert isinstance(result["muscle_set_delta"], dict)


def test_progression_action_recommends_deload_for_low_readiness() -> None:
    decision = recommend_progression_action(
        completion_pct=62,
        adherence_score=2,
        soreness_level="severe",
        average_rpe=9.5,
        consecutive_underperformance_weeks=2,
    )

    assert decision["action"] == "deload"
    assert decision["set_delta"] == -1
    assert decision["load_scale"] < 1.0


def test_progression_action_recommends_progress_when_metrics_are_strong() -> None:
    decision = recommend_progression_action(
        completion_pct=98,
        adherence_score=5,
        soreness_level="mild",
        average_rpe=8.5,
        consecutive_underperformance_weeks=0,
    )

    assert decision["action"] == "progress"
    assert decision["load_scale"] > 1.0


def test_progression_action_holds_underperformance_without_high_fatigue_when_rules_loaded() -> None:
    decision = recommend_progression_action(
        completion_pct=90,
        adherence_score=4,
        soreness_level="mild",
        average_rpe=8.0,
        consecutive_underperformance_weeks=2,
        rule_set=_sample_rule_set(),
    )

    assert decision["action"] == "hold"
    assert decision["reason"] == "under_target_without_high_fatigue"


def test_progression_action_deloads_for_underperformance_with_high_fatigue_when_rules_loaded() -> None:
    decision = recommend_progression_action(
        completion_pct=90,
        adherence_score=4,
        soreness_level="moderate",
        average_rpe=9.2,
        consecutive_underperformance_weeks=2,
        rule_set=_sample_rule_set(),
    )

    assert decision["action"] == "deload"
    assert decision["reason"] == "Fatigue and underperformance indicate that a short deload is warranted."


def test_phase_transition_respects_intro_phase_protection_from_rules() -> None:
    transition = recommend_phase_transition(
        current_phase="accumulation",
        weeks_in_phase=2,
        readiness_score=50,
        progression_action="hold",
        stagnation_weeks=1,
        rule_set=_sample_rule_set(),
    )

    assert transition["next_phase"] == "accumulation"
    assert transition["reason"] == "intro_phase_protection"


def test_phase_transition_moves_from_accumulation_to_intensification() -> None:
    transition = recommend_phase_transition(
        current_phase="accumulation",
        weeks_in_phase=6,
        readiness_score=72,
        progression_action="progress",
        stagnation_weeks=0,
    )

    assert transition["next_phase"] == "intensification"


def test_phase_transition_moves_to_deload_when_stalled() -> None:
    transition = recommend_phase_transition(
        current_phase="intensification",
        weeks_in_phase=3,
        readiness_score=58,
        progression_action="hold",
        stagnation_weeks=2,
    )

    assert transition["next_phase"] == "deload"


def test_specialization_adjustments_focus_on_lagging_muscles() -> None:
    adjustments = recommend_specialization_adjustments(
        weekly_volume_by_muscle={
            "chest": 12,
            "back": 13,
            "quads": 11,
            "hamstrings": 10,
            "glutes": 10,
            "shoulders": 6,
            "biceps": 5,
            "triceps": 9,
            "calves": 7,
        },
        lagging_muscles=["biceps", "shoulders", "calves"],
        max_focus_muscles=2,
        target_min_sets=8,
    )

    assert adjustments["focus_muscles"] == ["biceps", "shoulders"]
    assert adjustments["focus_adjustments"]["biceps"] >= 1
    assert adjustments["focus_adjustments"]["shoulders"] >= 1


def test_media_and_warmup_summary_reports_video_coverage() -> None:
    summary = summarize_program_media_and_warmups(_sample_template())

    assert summary["total_exercises"] == 6
    assert summary["video_linked_exercises"] == 1
    assert summary["video_coverage_pct"] > 0
    assert len(summary["sample_warmups"]) == 3


def test_program_recommendation_returns_structured_trace_for_adaptation_upgrade() -> None:
    decision = recommend_program_selection(
        current_program_id="ppl_v1",
        compatible_program_summaries=[
            {"id": "upper_lower_v1", "session_count": 5},
            {"id": "ppl_v1", "session_count": 3},
        ],
        days_available=3,
        latest_adherence_score=4,
        latest_plan_payload={},
    )

    assert decision["recommended_program_id"] == "upper_lower_v1"
    assert decision["reason"] == "days_adaptation_upgrade"
    trace = decision["decision_trace"]
    assert trace["interpreter"] == "recommend_program_selection"
    assert trace["selected_program_id"] == "upper_lower_v1"
    assert any(step["rule"] == "days_adaptation_upgrade" and step["matched"] for step in trace["steps"])


def test_program_recommendation_candidate_resolution_orders_compatible_programs() -> None:
    resolution = resolve_program_recommendation_candidates(
        available_program_summaries=[
            {"id": "upper_lower_v1", "split": "ppl", "days_supported": [3], "session_count": 5},
            {"id": "ppl_v1", "split": "ppl", "days_supported": [3], "session_count": 3},
            {"id": "full_body_v1", "split": "full_body", "days_supported": [3, 4], "session_count": 3},
        ],
        days_available=3,
        split_preference="ppl",
    )

    assert resolution["compatible_program_ids"] == ["upper_lower_v1", "ppl_v1", "full_body_v1"]
    assert resolution["decision_trace"]["interpreter"] == "resolve_program_recommendation_candidates"
    assert resolution["decision_trace"]["compatibility_mode"] == "days_supported_match"


def test_build_program_recommendation_payload_merges_candidate_resolution_trace() -> None:
    generated_at = datetime(2026, 3, 7, tzinfo=UTC)
    payload = build_program_recommendation_payload(
        decision={
            "current_program_id": "ppl_v1",
            "recommended_program_id": "upper_lower_v1",
            "reason": "days_adaptation_upgrade",
            "rationale": humanize_program_reason("days_adaptation_upgrade"),
            "compatible_program_ids": ["upper_lower_v1", "ppl_v1"],
            "decision_trace": {"interpreter": "recommend_program_selection", "selected_program_id": "upper_lower_v1"},
        },
        candidate_resolution_trace={
            "interpreter": "resolve_program_recommendation_candidates",
            "compatible_program_ids": ["upper_lower_v1", "ppl_v1"],
        },
        generated_at=generated_at,
    )

    assert payload["generated_at"] == generated_at
    assert payload["recommended_program_id"] == "upper_lower_v1"
    assert payload["decision_trace"]["candidate_resolution"]["interpreter"] == "resolve_program_recommendation_candidates"


def test_prepare_program_recommendation_runtime_returns_decision_and_response_payload() -> None:
    generated_at = datetime(2026, 3, 7, tzinfo=UTC)

    runtime = prepare_program_recommendation_runtime(
        current_program_id="ppl_v1",
        available_program_summaries=[
            {"id": "upper_lower_v1", "split": "ppl", "days_supported": [3], "session_count": 5},
            {"id": "ppl_v1", "split": "ppl", "days_supported": [3], "session_count": 3},
            {"id": "full_body_v1", "split": "full_body", "days_supported": [3, 4], "session_count": 3},
        ],
        days_available=3,
        split_preference="ppl",
        latest_adherence_score=4,
        latest_plan_payload={},
        generated_at=generated_at,
    )

    assert runtime["compatible_program_ids"] == ["upper_lower_v1", "ppl_v1", "full_body_v1"]
    assert runtime["decision"]["recommended_program_id"] == "upper_lower_v1"
    assert runtime["candidate_resolution_trace"]["interpreter"] == "resolve_program_recommendation_candidates"
    assert runtime["response_payload"]["generated_at"] == generated_at
    assert runtime["response_payload"]["decision_trace"]["candidate_resolution"]["interpreter"] == (
        "resolve_program_recommendation_candidates"
    )


def test_prepare_program_recommendation_runtime_prefers_canonical_training_state_context() -> None:
    runtime = prepare_program_recommendation_runtime(
        current_program_id="ppl_v1",
        available_program_summaries=[
            {"id": "upper_lower_v1", "split": "ppl", "days_supported": [3], "session_count": 5},
            {"id": "ppl_v1", "split": "ppl", "days_supported": [3], "session_count": 3},
        ],
        days_available=3,
        split_preference="ppl",
        latest_adherence_score=None,
        latest_plan_payload={},
        user_training_state={
            "user_program_state": {"program_id": "ppl_v1", "week_index": 6},
            "adherence_state": {"latest_adherence_score": 4},
            "generation_state": {
                "under_target_muscles": ["biceps", "rear_delts", "side_delts", "lats"],
                "mesocycle_trigger_weeks_effective": 5,
            },
        },
    )

    trace_inputs = runtime["decision"]["decision_trace"]["inputs"]
    assert trace_inputs["latest_adherence_score_source"] == "training_state"
    assert trace_inputs["under_target_muscles_source"] == "training_state"
    assert trace_inputs["mesocycle_context_source"] == "training_state"


def test_prepare_profile_program_recommendation_inputs_applies_router_fallbacks() -> None:
    runtime = prepare_profile_program_recommendation_inputs(
        selected_program_id=None,
        days_available=None,
        split_preference=None,
        latest_plan=None,
    )
    assert runtime["current_program_id"] == "full_body_v1"
    assert runtime["days_available"] == 2
    assert runtime["split_preference"] == "full_body"
    assert runtime["latest_plan_payload"] == {}


def test_prepare_profile_program_recommendation_route_runtime_combines_inputs_and_runtime() -> None:
    runtime = prepare_profile_program_recommendation_route_runtime(
        selected_program_id="ppl_v1",
        days_available=3,
        split_preference="ppl",
        latest_plan={"payload": {"mesocycle": {"week_index": 3}}},
        available_program_summaries=[
            {"id": "upper_lower_v1", "split": "ppl", "days_supported": [3], "session_count": 5},
            {"id": "ppl_v1", "split": "ppl", "days_supported": [3], "session_count": 3},
        ],
        latest_adherence_score=4,
        user_training_state=None,
        generated_at=datetime(2026, 3, 9, tzinfo=UTC),
    )

    inputs = runtime["recommendation_inputs"]
    recommendation_runtime = runtime["recommendation_runtime"]
    assert inputs["current_program_id"] == "ppl_v1"
    assert recommendation_runtime["decision"]["recommended_program_id"] == "upper_lower_v1"
    assert recommendation_runtime["response_payload"]["recommended_program_id"] == "upper_lower_v1"
    assert runtime["decision_trace"]["interpreter"] == "prepare_profile_program_recommendation_route_runtime"


def test_build_program_switch_payload_resolves_confirmation_and_unchanged_variants() -> None:
    confirmation_payload = build_program_switch_payload(
        current_program_id="ppl_v1",
        target_program_id="upper_lower_v1",
        confirm=False,
        decision={
            "recommended_program_id": "upper_lower_v1",
            "reason": "days_adaptation_upgrade",
            "rationale": humanize_program_reason("days_adaptation_upgrade"),
            "decision_trace": {"interpreter": "recommend_program_selection"},
        },
        candidate_resolution_trace={"interpreter": "resolve_program_recommendation_candidates"},
    )

    assert confirmation_payload["status"] == "confirmation_required"
    assert confirmation_payload["requires_confirmation"] is True
    assert confirmation_payload["applied"] is False
    assert confirmation_payload["decision_trace"]["switch_outcome"]["reason"] == "days_adaptation_upgrade"

    unchanged_payload = build_program_switch_payload(
        current_program_id="ppl_v1",
        target_program_id="ppl_v1",
        confirm=True,
        decision={
            "recommended_program_id": "upper_lower_v1",
            "reason": "days_adaptation_upgrade",
            "rationale": humanize_program_reason("days_adaptation_upgrade"),
            "decision_trace": {"interpreter": "recommend_program_selection"},
        },
        candidate_resolution_trace={"interpreter": "resolve_program_recommendation_candidates"},
    )

    assert unchanged_payload["status"] == "unchanged"
    assert unchanged_payload["reason"] == "target_matches_current"
    assert unchanged_payload["rationale"] == humanize_program_reason("target_matches_current")
    assert unchanged_payload["decision_trace"]["switch_outcome"] == {"status": "unchanged", "reason": "target_matches_current"}


def test_prepare_program_switch_runtime_requires_compatible_target() -> None:
    with pytest.raises(ValueError, match="Target program is not compatible"):
        prepare_program_switch_runtime(
            current_program_id="ppl_v1",
            target_program_id="bro_split_v1",
            confirm=False,
            compatible_program_ids=["ppl_v1", "upper_lower_v1"],
            decision={
                "recommended_program_id": "upper_lower_v1",
                "reason": "days_adaptation_upgrade",
                "rationale": humanize_program_reason("days_adaptation_upgrade"),
                "decision_trace": {"interpreter": "recommend_program_selection"},
            },
            candidate_resolution_trace={"interpreter": "resolve_program_recommendation_candidates"},
        )


def test_prepare_program_switch_runtime_only_marks_confirmed_change_as_applicable() -> None:
    preflight_runtime = prepare_program_switch_runtime(
        current_program_id="ppl_v1",
        target_program_id="upper_lower_v1",
        confirm=False,
        compatible_program_ids=["ppl_v1", "upper_lower_v1"],
        decision={
            "recommended_program_id": "upper_lower_v1",
            "reason": "days_adaptation_upgrade",
            "rationale": humanize_program_reason("days_adaptation_upgrade"),
            "decision_trace": {"interpreter": "recommend_program_selection"},
        },
        candidate_resolution_trace={"interpreter": "resolve_program_recommendation_candidates"},
    )

    unchanged_runtime = prepare_program_switch_runtime(
        current_program_id="ppl_v1",
        target_program_id="ppl_v1",
        confirm=True,
        compatible_program_ids=["ppl_v1", "upper_lower_v1"],
        decision={
            "recommended_program_id": "upper_lower_v1",
            "reason": "days_adaptation_upgrade",
            "rationale": humanize_program_reason("days_adaptation_upgrade"),
            "decision_trace": {"interpreter": "recommend_program_selection"},
        },
        candidate_resolution_trace={"interpreter": "resolve_program_recommendation_candidates"},
    )

    apply_runtime = prepare_program_switch_runtime(
        current_program_id="ppl_v1",
        target_program_id="upper_lower_v1",
        confirm=True,
        compatible_program_ids=["ppl_v1", "upper_lower_v1"],
        decision={
            "recommended_program_id": "upper_lower_v1",
            "reason": "days_adaptation_upgrade",
            "rationale": humanize_program_reason("days_adaptation_upgrade"),
            "decision_trace": {"interpreter": "recommend_program_selection"},
        },
        candidate_resolution_trace={"interpreter": "resolve_program_recommendation_candidates"},
    )

    assert preflight_runtime["should_apply"] is False
    assert preflight_runtime["response_payload"]["status"] == "confirmation_required"
    assert unchanged_runtime["should_apply"] is False
    assert unchanged_runtime["response_payload"]["status"] == "unchanged"
    assert apply_runtime["should_apply"] is True
    assert apply_runtime["response_payload"]["status"] == "switched"


def test_build_weekly_review_decision_payload_wraps_interpreter_output() -> None:
    decision_payload = build_weekly_review_decision_payload(
        summary={
            "completion_pct": 100,
            "faulty_exercise_count": 0,
            "exercise_faults": [],
        },
        body_weight=82.0,
        calories=2600,
        protein=180,
        adherence_score=4,
    )

    assert isinstance(decision_payload["readiness_score"], int)
    assert decision_payload["global_guidance"]
    assert decision_payload["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"
    assert "storage_adjustments" in decision_payload


def test_derive_readiness_score_supports_readiness_state_inputs() -> None:
    readiness = derive_readiness_score(
        completion_pct=70,
        adherence_score=4,
        soreness_level="none",
        progression_action="hold",
        sleep_quality=2,
        stress_level=4,
        pain_flags=["elbow_flexion"],
    )

    assert readiness == 50


def test_build_weekly_review_decision_payload_does_not_alias_response_and_storage_data() -> None:
    decision_payload = build_weekly_review_decision_payload(
        summary={
            "completion_pct": 100,
            "faulty_exercise_count": 0,
            "exercise_faults": [],
        },
        body_weight=82.0,
        calories=2600,
        protein=180,
        adherence_score=4,
    )

    decision_payload["storage_adjustments"]["weak_point_exercises"].append("injected")

    assert decision_payload["adjustments"]["weak_point_exercises"] == []


def test_build_weekly_review_submit_payload_uses_summary_fault_count() -> None:
    payload = build_weekly_review_submit_payload(
        week_start=date(2026, 3, 2),
        previous_week_start=date(2026, 2, 23),
        summary={
            "faulty_exercise_count": 2,
            "exercise_faults": [],
            "completion_pct": 87,
        },
        decision_payload={
            "readiness_score": 72,
            "global_guidance": "progressive_overload_ready",
            "adjustments": {
                "global_set_delta": 0,
                "global_weight_scale": 1.0,
                "weak_point_exercises": [],
                "exercise_overrides": [],
            },
            "decision_trace": {"interpreter": "interpret_weekly_review_decision"},
        },
    )

    assert payload["status"] == "review_logged"
    assert payload["fault_count"] == 2
    assert math.isclose(payload["adjustments"]["global_weight_scale"], 1.0, rel_tol=1e-9, abs_tol=1e-9)
    assert payload["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"


def test_build_weekly_review_cycle_persistence_payload_shapes_faults_and_adjustments() -> None:
    payload = build_weekly_review_cycle_persistence_payload(
        summary={
            "exercise_faults": [
                {"exercise_id": "bench", "guidance": "hold"},
                {"exercise_id": "row", "guidance": "reduce"},
            ]
        },
        decision_payload={
            "storage_adjustments": {
                "load_adjustments": {"bench": -2.5},
                "decision_trace": {"interpreter": "interpret_weekly_review_decision"},
            }
        },
    )

    assert payload["faults"] == {
        "exercise_faults": [
            {"exercise_id": "bench", "guidance": "hold"},
            {"exercise_id": "row", "guidance": "reduce"},
        ]
    }
    assert payload["adjustments"]["load_adjustments"]["bench"] == -2.5
    assert payload["decision_trace"]["interpreter"] == "build_weekly_review_cycle_persistence_payload"


def test_build_soreness_entry_persistence_payload_copies_severity_map() -> None:
    severity_by_muscle = {"quads": "moderate", "hamstrings": "mild"}
    payload = build_soreness_entry_persistence_payload(
        entry_date=date(2026, 3, 2),
        severity_by_muscle=severity_by_muscle,
        notes="Leg day residual fatigue",
    )

    severity_by_muscle["quads"] = "severe"

    assert payload["entry_date"] == date(2026, 3, 2)
    assert payload["severity_by_muscle"] == {"quads": "moderate", "hamstrings": "mild"}
    assert payload["notes"] == "Leg day residual fatigue"


def test_build_body_measurement_create_payload_shapes_fields() -> None:
    payload = build_body_measurement_create_payload(
        measured_on=date(2026, 3, 2),
        name="waist",
        value=82.5,
        unit="cm",
    )
    assert payload == {
        "measured_on": date(2026, 3, 2),
        "name": "waist",
        "value": 82.5,
        "unit": "cm",
    }


def test_build_body_measurement_update_payload_includes_only_provided_fields() -> None:
    payload = build_body_measurement_update_payload(
        measured_on=None,
        name=None,
        value=82.0,
        unit=None,
    )
    assert payload == {"value": 82.0}


def test_prepare_profile_date_window_runtime_preserves_optional_bounds() -> None:
    runtime = prepare_profile_date_window_runtime(
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 7),
    )
    assert runtime["start_date"] == date(2026, 3, 1)
    assert runtime["end_date"] == date(2026, 3, 7)
    assert runtime["decision_trace"]["interpreter"] == "prepare_profile_date_window_runtime"


def test_build_profile_upsert_persistence_payload_defaults_selected_program() -> None:
    payload = build_profile_upsert_persistence_payload(
        name="Test User",
        age=30,
        weight=80.0,
        gender="male",
        split_preference="full_body",
        selected_program_id=None,
        training_location="home",
        equipment_profile=["dumbbell"],
        weak_areas=["chest"],
        onboarding_answers={"primary_goal": "build_muscle"},
        days_available=3,
        nutrition_phase="maintenance",
        calories=2500,
        protein=180,
        fat=70,
        carbs=260,
        session_time_budget_minutes=75,
        movement_restrictions=["deep_knee_flexion"],
        near_failure_tolerance="moderate",
    )
    assert payload["selected_program_id"] == "full_body_v1"
    assert payload["onboarding_answers"] == {"primary_goal": "build_muscle"}
    assert payload["session_time_budget_minutes"] == 75
    assert payload["movement_restrictions"] == ["deep_knee_flexion"]
    assert payload["near_failure_tolerance"] == "moderate"


def test_build_profile_response_payload_applies_profile_defaults() -> None:
    payload = build_profile_response_payload(
        email="coach@example.com",
        name="Coach",
        age=None,
        weight=None,
        gender=None,
        split_preference=None,
        selected_program_id=None,
        training_location="home",
        equipment_profile=None,
        weak_areas=None,
        onboarding_answers=None,
        days_available=None,
        nutrition_phase=None,
        calories=None,
        protein=None,
        fat=None,
        carbs=None,
        session_time_budget_minutes=None,
        movement_restrictions=None,
        near_failure_tolerance=None,
    )
    assert payload["email"] == "coach@example.com"
    assert payload["selected_program_id"] == "full_body_v1"
    assert payload["days_available"] == 2
    assert payload["nutrition_phase"] == "maintenance"
    assert payload["equipment_profile"] == []
    assert payload["onboarding_answers"] == {}
    assert payload["movement_restrictions"] == []
    assert payload["session_time_budget_minutes"] is None
    assert payload["near_failure_tolerance"] is None


def test_build_frequency_adaptation_persistence_state_copies_dict() -> None:
    decision = {"persistence_state": {"program_id": "full_body_v1", "weeks_remaining": 2}}
    payload = build_frequency_adaptation_persistence_state(decision_payload=decision)
    decision["persistence_state"]["weeks_remaining"] = 1
    assert payload == {"program_id": "full_body_v1", "weeks_remaining": 2}


def test_build_generated_week_adaptation_persistence_payload_emits_state_update() -> None:
    payload = build_generated_week_adaptation_persistence_payload(
        adaptation_runtime={"state_updated": True, "next_state": {"program_id": "full_body_v1", "weeks_remaining": 1}}
    )
    assert payload["state_updated"] is True
    assert payload["next_state"] == {"program_id": "full_body_v1", "weeks_remaining": 1}


def test_build_weekly_checkin_persistence_payload_shapes_entry_fields() -> None:
    payload = build_weekly_checkin_persistence_payload(
        week_start=date(2026, 3, 9),
        body_weight=81.2,
        adherence_score=4,
        notes="solid week",
    )
    assert payload == {
        "week_start": date(2026, 3, 9),
        "body_weight": 81.2,
        "adherence_score": 4,
        "notes": "solid week",
    }


def test_build_weekly_checkin_response_payload_defaults_phase() -> None:
    payload = build_weekly_checkin_response_payload(nutrition_phase=None)
    assert payload == {"status": "logged", "phase": "maintenance"}


def test_build_weekly_review_user_update_payload_includes_optional_nutrition_phase() -> None:
    payload = build_weekly_review_user_update_payload(
        body_weight=81.0,
        calories=2550,
        protein=185,
        fat=72,
        carbs=260,
        nutrition_phase="cut",
    )
    assert payload["weight"] == 81.0
    assert payload["nutrition_phase"] == "cut"

    without_phase = build_weekly_review_user_update_payload(
        body_weight=81.0,
        calories=2550,
        protein=185,
        fat=72,
        carbs=260,
        nutrition_phase=None,
    )
    assert "nutrition_phase" not in without_phase


def test_prepare_weekly_review_log_window_runtime_builds_half_open_bounds() -> None:
    runtime = prepare_weekly_review_log_window_runtime(
        previous_week_start=date(2026, 3, 2),
        week_start=date(2026, 3, 9),
    )
    assert runtime["window_start"].isoformat() == "2026-03-02T00:00:00"
    assert runtime["window_end"].isoformat() == "2026-03-09T00:00:00"
    assert runtime["decision_trace"]["interpreter"] == "prepare_weekly_review_log_window_runtime"


def test_resolve_workout_completion_per_exercise_keeps_highest_logged_set() -> None:
    completed = resolve_workout_completion_per_exercise(
        performed_logs=[
            {"exercise_id": "bench_press", "set_index": 1},
            {"exercise_id": "bench_press", "set_index": 3},
            {"exercise_id": "bench_press", "set_index": 2},
            {"exercise_id": "row", "set_index": 1},
            {"exercise_id": "", "set_index": 4},
        ]
    )

    assert completed == {"bench_press": 3, "row": 1}


def test_group_workout_logs_by_exercise_sorts_each_bucket() -> None:
    grouped = group_workout_logs_by_exercise(
        performed_logs=[
            {"exercise_id": "bench", "set_index": 3, "reps": 6, "weight": 100},
            {"exercise_id": "bench", "set_index": 1, "reps": 8, "weight": 100},
            {"exercise_id": "row", "set_index": 2, "reps": 10, "weight": 80},
            {"exercise_id": "row", "set_index": 1, "reps": 12, "weight": 80},
        ]
    )

    assert [row["set_index"] for row in grouped["bench"]] == [1, 3]
    assert [row["set_index"] for row in grouped["row"]] == [1, 2]


def test_build_workout_summary_payload_wraps_session_guidance_output() -> None:
    exercise_summary = summarize_workout_exercise_performance(
        exercise={
            "id": "bench",
            "primary_exercise_id": "bench",
            "name": "Bench Press",
            "sets": 3,
            "rep_range": [8, 12],
            "recommended_working_weight": 100,
        },
        performed_logs=[
            {"set_index": 1, "reps": 6, "weight": 97.5},
            {"set_index": 2, "reps": 6, "weight": 97.5},
            {"set_index": 3, "reps": 6, "weight": 97.5},
        ],
        next_working_weight=100,
        rule_set=_sample_rule_set(),
    )

    payload = build_workout_summary_payload(
        workout_id="workout_a",
        completed_total=3,
        planned_total=3,
        exercise_summaries=[exercise_summary],
        rule_set=_sample_rule_set(),
    )

    assert payload["workout_id"] == "workout_a"
    assert payload["percent_complete"] == 100
    assert payload["overall_guidance"] == "performance_below_target_adjust_load_and_recover"
    assert payload["decision_trace"]["interpreter"] == "summarize_workout_session_guidance"


def test_build_workout_performance_summary_normalizes_rows_and_progression_state() -> None:
    payload = build_workout_performance_summary(
        workout_id="workout_a",
        planned_session={
            "session_id": "workout_a",
            "exercises": [
                {
                    "id": "bench_variant",
                    "primary_exercise_id": "bench",
                    "name": "Bench Press",
                    "sets": 3,
                    "rep_range": [8, 12],
                    "recommended_working_weight": 100,
                }
            ],
        },
        performed_logs=[
            SimpleNamespace(exercise_id="bench_variant", set_index=2, reps=6, weight=97.5),
            SimpleNamespace(exercise_id="bench_variant", set_index=1, reps=6, weight=97.5),
        ],
        progression_states=[SimpleNamespace(exercise_id="bench", current_working_weight=102.5)],
        rule_set=_sample_rule_set(),
    )

    assert payload["workout_id"] == "workout_a"
    assert payload["completed_total"] == 2
    assert payload["planned_total"] == 3
    assert payload["decision_trace"]["interpreter"] == "summarize_workout_session_guidance"

    exercise = payload["exercises"][0]
    assert exercise["exercise_id"] == "bench_variant"
    assert math.isclose(exercise["next_working_weight"], 102.5, rel_tol=1e-9, abs_tol=1e-9)
    assert exercise["decision_trace"]["interpreter"] == "summarize_workout_exercise_performance"


def test_build_workout_log_set_payload_copies_feedback_and_live_recommendation() -> None:
    payload = build_workout_log_set_payload(
        record_id="log_123",
        primary_exercise_id="bench",
        exercise_id="bench",
        set_index=1,
        reps=6,
        weight=95.0,
        planned_reps_min=8,
        planned_reps_max=12,
        planned_weight=100.0,
        feedback={
            "rep_delta": -2,
            "weight_delta": -5.0,
            "next_working_weight": 100.0,
            "guidance": "below_target_reps_reduce_or_hold_load",
            "guidance_rationale": "Hold load on the first miss.",
            "decision_trace": {"interpreter": "interpret_workout_set_feedback", "outcome": {"guidance": "below_target_reps_reduce_or_hold_load"}},
        },
        starting_load_decision_trace=None,
        live_recommendation={
            "completed_sets": 1,
            "remaining_sets": 2,
            "recommended_reps_min": 8,
            "recommended_reps_max": 12,
            "recommended_weight": 97.5,
            "guidance": "remaining_sets_reduce_load_focus_target_reps",
            "guidance_rationale": "Trim load slightly within the session.",
            "decision_trace": {"interpreter": "recommend_live_workout_adjustment"},
            "substitution_recommendation": {
                "recommended_name": "Chest Supported Row",
                "compatible_substitutions": ["Chest Supported Row", "1-Arm Cable Row"],
                "failed_exposure_count": 3,
                "trigger_threshold": 3,
                "reason": "repeat_failure_threshold_reached",
                "decision_trace": {"interpreter": "resolve_repeat_failure_substitution"},
            },
        },
        created_at=datetime(2026, 3, 7, 10, 0),
    )

    payload["decision_trace"]["outcome"]["guidance"] = "mutated"
    payload["live_recommendation"]["decision_trace"]["interpreter"] = "mutated"

    rebuilt = build_workout_log_set_payload(
        record_id="log_123",
        primary_exercise_id="bench",
        exercise_id="bench",
        set_index=1,
        reps=6,
        weight=95.0,
        planned_reps_min=8,
        planned_reps_max=12,
        planned_weight=100.0,
        feedback={
            "rep_delta": -2,
            "weight_delta": -5.0,
            "next_working_weight": 100.0,
            "guidance": "below_target_reps_reduce_or_hold_load",
            "guidance_rationale": "Hold load on the first miss.",
            "decision_trace": {"interpreter": "interpret_workout_set_feedback", "outcome": {"guidance": "below_target_reps_reduce_or_hold_load"}},
        },
        starting_load_decision_trace=None,
        live_recommendation={
            "completed_sets": 1,
            "remaining_sets": 2,
            "recommended_reps_min": 8,
            "recommended_reps_max": 12,
            "recommended_weight": 97.5,
            "guidance": "remaining_sets_reduce_load_focus_target_reps",
            "guidance_rationale": "Trim load slightly within the session.",
            "decision_trace": {"interpreter": "recommend_live_workout_adjustment"},
            "substitution_recommendation": {
                "recommended_name": "Chest Supported Row",
                "compatible_substitutions": ["Chest Supported Row", "1-Arm Cable Row"],
                "failed_exposure_count": 3,
                "trigger_threshold": 3,
                "reason": "repeat_failure_threshold_reached",
                "decision_trace": {"interpreter": "resolve_repeat_failure_substitution"},
            },
        },
        created_at=datetime(2026, 3, 7, 10, 0),
    )

    assert rebuilt["id"] == "log_123"
    assert rebuilt["decision_trace"]["outcome"]["guidance"] == "below_target_reps_reduce_or_hold_load"
    assert rebuilt["live_recommendation"]["decision_trace"]["interpreter"] == "recommend_live_workout_adjustment"
    assert rebuilt["live_recommendation"]["substitution_recommendation"]["recommended_name"] == "Chest Supported Row"


def test_resolve_workout_log_set_plan_context_normalizes_rep_range_sets_and_weight() -> None:
    payload = resolve_workout_log_set_plan_context(
        planned_exercise={
            "rep_range": [12, 8],
            "sets": 0,
            "recommended_working_weight": None,
        },
        fallback_weight=87.5,
    )

    assert payload == {
        "planned_reps_min": 8,
        "planned_reps_max": 12,
        "planned_sets": 3,
        "planned_weight": 87.5,
    }


def test_prepare_workout_log_set_request_runtime_falls_back_primary_exercise_id() -> None:
    runtime = prepare_workout_log_set_request_runtime(
        primary_exercise_id=None,
        exercise_id="bench",
        set_index=2,
        reps=8,
        weight=82.5,
        rpe=8.0,
    )
    assert runtime["primary_exercise_id"] == "bench"
    assert runtime["exercise_id"] == "bench"
    assert runtime["set_index"] == 2
    assert runtime["reps"] == 8
    assert runtime["weight"] == 82.5


def test_build_workout_session_state_defaults_seeds_expected_values() -> None:
    payload = build_workout_session_state_defaults(
        primary_exercise_id="bench",
        planned_sets=3,
        planned_reps_min=8,
        planned_reps_max=12,
        planned_weight=100.0,
    )

    assert payload["primary_exercise_id"] == "bench"
    assert payload["completed_sets"] == 0
    assert payload["remaining_sets"] == 3
    assert math.isclose(payload["recommended_weight"], 100.0, rel_tol=1e-9, abs_tol=1e-9)
    assert payload["last_guidance"] == "remaining_sets_hold_load_and_match_target_reps"


def test_prepare_workout_session_state_persistence_payload_wraps_reducer_output() -> None:
    payload = prepare_workout_session_state_persistence_payload(
        existing_state=SimpleNamespace(set_history=[{"set_index": 1, "reps": 8, "weight": 100.0}]),
        primary_exercise_id="bench",
        planned_sets=3,
        planned_reps_min=8,
        planned_reps_max=12,
        planned_weight=100.0,
        set_index=2,
        reps=6,
        weight=100.0,
        substitution_recommendation=None,
        rule_set=_sample_rule_set(),
    )

    state = payload["state"]
    live = payload["live_recommendation"]

    assert state["completed_sets"] == 2
    assert state["last_guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert live["guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert live["decision_trace"]["interpreter"] == "recommend_live_workout_adjustment"


def test_prepare_workout_session_state_upsert_runtime_shapes_create_update_and_live_payloads() -> None:
    runtime = prepare_workout_session_state_upsert_runtime(
        existing_state=None,
        primary_exercise_id="bench",
        planned_sets=3,
        planned_reps_min=8,
        planned_reps_max=12,
        planned_weight=100.0,
        set_index=1,
        reps=7,
        weight=100.0,
        substitution_recommendation=None,
        rule_set=_sample_rule_set(),
    )

    assert runtime["create_values"]["primary_exercise_id"] == "bench"
    assert runtime["update_values"]["completed_sets"] == 1
    assert runtime["live_recommendation"]["guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_session_state_upsert_runtime"


def test_prepare_workout_exercise_state_runtime_builds_initial_and_updated_state_payloads() -> None:
    runtime = prepare_workout_exercise_state_runtime(
        existing_state=None,
        primary_exercise_id="bench_press",
        planned_exercise={
            "id": "bench_press",
            "name": "Bench Press",
            "start_weight": 100.0,
            "substitution_candidates": [{"exercise_id": "machine_press", "name": "Machine Press"}],
        },
        planned_weight=100.0,
        planned_sets=3,
        planned_reps_min=8,
        planned_reps_max=10,
        completed_set_index=1,
        completed_reps=10,
        nutrition_phase="maintenance",
        equipment_profile=["barbell"],
        rule_set=_sample_rule_set(),
    )

    assert runtime["initial_state_values"]["current_working_weight"] >= 5.0
    assert runtime["state_values"]["exposure_count"] == 1
    assert runtime["state_values"]["last_progression_action"] in {"progress", "hold", "deload"}
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_exercise_state_runtime"


def test_prepare_workout_log_set_decision_runtime_prepares_exercise_state_persistence_payloads() -> None:
    request_runtime = prepare_workout_log_set_request_runtime(
        primary_exercise_id=None,
        exercise_id="bench_press",
        set_index=1,
        reps=9,
        weight=100.0,
        rpe=8.0,
    )
    runtime = prepare_workout_log_set_decision_runtime(
        user_id="user_1",
        workout_id="workout_1",
        request_runtime=request_runtime,
        planned_exercise={
            "id": "bench_press",
            "name": "Bench Press",
            "sets": 3,
            "rep_range": [8, 10],
            "recommended_working_weight": 100.0,
            "estimated_1rm": 150.0,
            "substitution_candidates": ["machine_press"],
        },
        existing_exercise_state=None,
        nutrition_phase="maintenance",
        equipment_profile=["machine"],
        rule_set=_sample_rule_set(),
    )

    create_values = runtime["exercise_state_create_values"]
    update_values = runtime["exercise_state_update_values"]
    assert create_values["user_id"] == "user_1"
    assert create_values["exercise_id"] == "bench_press"
    assert create_values["current_working_weight"] >= 5.0
    assert update_values["exposure_count"] == 1
    assert runtime["session_state_inputs"]["substitution_recommendation"] == runtime["substitution_recommendation"]
    assert runtime["decision_trace"]["interpreter"] == "prepare_workout_log_set_decision_runtime"
    assert runtime["decision_trace"]["outcome"]["has_starting_load_runtime"] is True


def test_build_workout_today_state_payloads_merges_state_counts_and_hydrates_live_guidance() -> None:
    payload = build_workout_today_state_payloads(
        session_states=[
            {
                "exercise_id": "bench",
                "completed_sets": 2,
                "remaining_sets": 1,
                "recommended_reps_min": 8,
                "recommended_reps_max": 12,
                "recommended_weight": 97.5,
                "last_guidance": "remaining_sets_reduce_load_focus_target_reps",
                "substitution_recommendation": {
                    "recommended_name": "Chest Supported Row",
                    "compatible_substitutions": ["Chest Supported Row", "1-Arm Cable Row"],
                    "failed_exposure_count": 3,
                    "trigger_threshold": 3,
                    "reason": "repeat_failure_threshold_reached",
                    "decision_trace": {"interpreter": "resolve_repeat_failure_substitution"},
                },
            }
        ],
        completed_sets_by_exercise={"bench": 1, "row": 2},
        rule_set=_sample_rule_set(),
    )

    assert payload["completed_sets_by_exercise"] == {"bench": 2, "row": 2}
    assert payload["live_recommendations_by_exercise"]["bench"]["guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert payload["live_recommendations_by_exercise"]["bench"]["remaining_sets"] == 1
    assert payload["live_recommendations_by_exercise"]["bench"]["substitution_recommendation"]["recommended_name"] == "Chest Supported Row"


def test_build_repeat_failure_substitution_payload_returns_structured_result() -> None:
    payload = build_repeat_failure_substitution_payload(
        planned_exercise={
            "id": "bench_variant",
            "primary_exercise_id": "bench",
            "name": "Bench Press",
            "substitution_candidates": ["Chest Supported Row", "1-Arm Cable Row"],
        },
        exercise_state=SimpleNamespace(exercise_id="bench", consecutive_under_target_exposures=3),
        equipment_profile=["cable", "machine", "dumbbell"],
        rule_set={
            **_sample_rule_set(),
            "substitution_rules": {"repeat_failure_trigger": "switch_after_3_failed_exposures"},
        },
    )

    assert payload is not None
    assert payload["recommended_name"] == "Chest Supported Row"
    assert payload["failed_exposure_count"] == 3
    assert payload["decision_trace"]["interpreter"] == "resolve_repeat_failure_substitution"


def test_build_workout_today_session_state_payloads_adds_substitution_runtime() -> None:
    payloads = build_workout_today_session_state_payloads(
        session_states=[
            SimpleNamespace(
                exercise_id="bench_variant",
                primary_exercise_id="bench",
                completed_sets=2,
                remaining_sets=1,
                recommended_reps_min=8,
                recommended_reps_max=12,
                recommended_weight=97.5,
                last_guidance="remaining_sets_reduce_load_focus_target_reps",
            )
        ],
        planned_session={
            "exercises": [
                {
                    "id": "bench_variant",
                    "primary_exercise_id": "bench",
                    "name": "Bench Press",
                    "substitution_candidates": ["Chest Supported Row", "1-Arm Cable Row"],
                }
            ]
        },
        progression_states=[SimpleNamespace(exercise_id="bench", consecutive_under_target_exposures=3)],
        equipment_profile=["cable", "machine", "dumbbell"],
        rule_set={
            **_sample_rule_set(),
            "substitution_rules": {"repeat_failure_trigger": "switch_after_3_failed_exposures"},
        },
    )

    assert len(payloads) == 1
    assert payloads[0]["exercise_id"] == "bench_variant"
    assert payloads[0]["substitution_recommendation"] is not None
    assert payloads[0]["substitution_recommendation"]["recommended_name"] == "Chest Supported Row"


def test_humanize_program_reason_returns_expected_text() -> None:
    assert humanize_program_reason("low_adherence_keep_program") == (
        "Recent adherence is low. Keep the current program stable before rotating templates."
    )


def test_coach_preview_returns_structured_trace() -> None:
    request_runtime_trace = {
        "interpreter": "prepare_coach_preview_runtime_inputs",
        "outcome": {"max_requested_days": 5},
    }
    template_runtime_trace = {
        "interpreter": "recommend_generation_template_selection",
        "selected_template_id": "intelligence_test_template",
    }
    decision = recommend_coach_intelligence_preview(
        template_id="intelligence_test_template",
        context={
            "user_profile": {"name": "Test"},
            "split_preference": "full_body",
            "program_template": _sample_template(),
            "history": [],
            "phase": "maintenance",
            "available_equipment": ["barbell", "bench"],
        },
        preview_request={
            "from_days": 5,
            "to_days": 3,
            "completion_pct": 96,
            "adherence_score": 4,
            "soreness_level": "mild",
            "average_rpe": 8.5,
            "current_phase": "accumulation",
            "weeks_in_phase": 6,
            "stagnation_weeks": 0,
            "lagging_muscles": ["biceps", "shoulders"],
            "target_min_sets": 8,
        },
        rule_set=_sample_rule_set(),
        request_runtime_trace=request_runtime_trace,
        template_runtime_trace=template_runtime_trace,
    )

    assert decision["progression"]["rationale"]
    assert decision["phase_transition"]["rationale"]
    trace = decision["decision_trace"]
    assert trace["interpreter"] == "recommend_coach_intelligence_preview"
    assert trace["request_runtime_trace"]["interpreter"] == "prepare_coach_preview_runtime_inputs"
    assert trace["template_runtime_trace"]["interpreter"] == "recommend_generation_template_selection"
    assert trace["outputs"]["next_phase"] == decision["phase_transition"]["next_phase"]
    assert any(step["decision"] == "progression" for step in trace["steps"])


def test_build_coach_preview_payloads_keeps_response_and_persistence_isolated() -> None:
    preview_payload = recommend_coach_intelligence_preview(
        template_id="intelligence_test_template",
        context={
            "user_profile": {"name": "Test"},
            "split_preference": "full_body",
            "program_template": _sample_template(),
            "history": [],
            "phase": "maintenance",
            "available_equipment": ["barbell", "bench"],
        },
        preview_request={
            "from_days": 5,
            "to_days": 3,
            "completion_pct": 96,
            "adherence_score": 4,
            "soreness_level": "mild",
            "average_rpe": 8.5,
            "current_phase": "accumulation",
            "weeks_in_phase": 6,
            "stagnation_weeks": 0,
            "lagging_muscles": ["biceps", "shoulders"],
            "target_min_sets": 8,
        },
        rule_set=_sample_rule_set(),
    )

    payloads = build_coach_preview_payloads(
        recommendation_id="rec_123",
        preview_payload=preview_payload,
        program_name="Full Body V1",
    )

    payloads["response_payload"]["specialization"]["focus_muscles"].append("triceps")

    assert payloads["response_payload"]["recommendation_id"] == "rec_123"
    assert payloads["response_payload"]["program_name"] == "Full Body V1"
    assert payloads["recommendation_payload"]["specialization"]["focus_muscles"] == ["biceps", "shoulders"]


def test_build_coach_preview_recommendation_record_fields_shapes_persistable_payload() -> None:
    fields = build_coach_preview_recommendation_record_fields(
        template_id="full_body_v1",
        preview_request={"current_phase": "accumulation", "from_days": 5, "to_days": 3},
        preview_payload={
            "phase_transition": {"next_phase": "intensification"},
            "progression": {"action": "hold"},
        },
    )

    assert fields["template_id"] == "full_body_v1"
    assert fields["recommendation_type"] == "coach_preview"
    assert fields["current_phase"] == "accumulation"
    assert fields["recommended_phase"] == "intensification"
    assert fields["progression_action"] == "hold"
    assert fields["status"] == "previewed"
    assert fields["request_payload"]["from_days"] == 5


def test_phase_apply_interpreter_returns_trace_and_confirmation_status() -> None:
    decision = interpret_coach_phase_apply_decision(
        recommendation_id="rec_123",
        phase_transition={
            "next_phase": "accumulation",
            "reason": "continue_accumulation",
            "rationale": "Stay in accumulation. Current readiness and momentum do not justify a phase change yet.",
        },
        confirm=False,
    )

    assert decision["status"] == "confirmation_required"
    assert decision["requires_confirmation"] is True
    assert decision["decision_trace"]["interpreter"] == "interpret_coach_phase_apply_decision"
    assert decision["decision_trace"]["outcome"]["status"] == "confirmation_required"


def test_prepare_coaching_apply_runtime_source_normalizes_recommendation_payload() -> None:
    source = prepare_coaching_apply_runtime_source(
        SimpleNamespace(
            id="rec_123",
            recommendation_payload=None,
            template_id="full_body_v1",
            current_phase="accumulation",
            recommended_phase="intensification",
            progression_action="hold",
        )
    )

    assert source["recommendation_id"] == "rec_123"
    assert source["recommendation_payload"] == {}
    assert source["template_id"] == "full_body_v1"
    assert source["current_phase"] == "accumulation"
    assert source["recommended_phase"] == "intensification"
    assert source["progression_action"] == "hold"
    assert source["decision_trace"]["interpreter"] == "prepare_coaching_apply_runtime_source"


def test_prepare_phase_apply_runtime_uses_fallback_phase_and_builds_record_fields() -> None:
    runtime = prepare_phase_apply_runtime(
        recommendation_id="rec_123",
        recommendation_payload={
            "phase_transition": {
                "reason": "continue_accumulation",
                "rationale": "Stay in accumulation.",
            }
        },
        fallback_next_phase="accumulation",
        confirm=True,
        template_id="full_body_v1",
        current_phase="accumulation",
        progression_action="hold",
    )

    assert runtime["payload_value"]["next_phase"] == "accumulation"
    assert runtime["decision_payload"]["next_phase"] == "accumulation"
    assert runtime["record_fields"]["recommended_phase"] == "accumulation"


def test_prepare_phase_apply_runtime_rejects_missing_phase_transition() -> None:
    with pytest.raises(ValueError, match="Recommendation is missing phase transition details"):
        prepare_phase_apply_runtime(
            recommendation_id="rec_123",
            recommendation_payload={},
            fallback_next_phase="accumulation",
            confirm=False,
            template_id="full_body_v1",
            current_phase="accumulation",
            progression_action="hold",
        )


def test_specialization_apply_interpreter_returns_trace_and_focus_payload() -> None:
    decision = interpret_coach_specialization_apply_decision(
        recommendation_id="rec_123",
        specialization={
            "focus_muscles": ["biceps", "shoulders"],
            "focus_adjustments": {"biceps": 2},
            "donor_adjustments": {"quads": -1},
            "uncompensated_added_sets": 1,
        },
        confirm=True,
    )

    assert decision["status"] == "applied"
    assert decision["focus_muscles"] == ["biceps", "shoulders"]
    assert decision["decision_trace"]["interpreter"] == "interpret_coach_specialization_apply_decision"
    assert decision["decision_trace"]["outcome"]["applied"] is True


def test_prepare_specialization_apply_runtime_returns_record_fields() -> None:
    runtime = prepare_specialization_apply_runtime(
        recommendation_id="rec_123",
        recommendation_payload={
            "specialization": {
                "focus_muscles": ["biceps", "shoulders"],
                "focus_adjustments": {"biceps": 2},
                "donor_adjustments": {"quads": -1},
                "uncompensated_added_sets": 1,
            }
        },
        confirm=True,
        template_id="full_body_v1",
        current_phase="accumulation",
        recommended_phase="intensification",
        progression_action="progress",
    )

    assert runtime["decision_payload"]["focus_muscles"] == ["biceps", "shoulders"]
    assert runtime["record_fields"]["recommendation_type"] == "specialization_decision"


def test_prepare_specialization_apply_runtime_rejects_missing_payload() -> None:
    with pytest.raises(ValueError, match="Recommendation is missing specialization details"):
        prepare_specialization_apply_runtime(
            recommendation_id="rec_123",
            recommendation_payload={},
            confirm=False,
            template_id="full_body_v1",
            current_phase="accumulation",
            recommended_phase="accumulation",
            progression_action="hold",
        )


def test_build_frequency_adaptation_apply_payload_copies_decision_data() -> None:
    decision = interpret_frequency_adaptation_apply(
        onboarding_package=_sample_onboarding_package(),
        program_id="full_body_v1",
        current_days=5,
        target_days=3,
        duration_weeks=2,
        explicit_weak_areas=["chest"],
        stored_weak_areas=["hamstrings"],
        equipment_profile=["barbell", "bench"],
        recovery_state="recovered",
        current_week_index=4,
        applied_at="2026-03-07T00:00:00",
    )

    payload = build_frequency_adaptation_apply_payload(decision)
    decision["weak_areas"].append("back")
    decision["decision_trace"]["outcome"]["status"] = "mutated"

    assert payload["status"] == "applied"
    assert payload["program_id"] == "full_body_v1"
    assert payload["weak_areas"] == ["chest"]
    assert payload["decision_trace"]["outcome"]["status"] == "applied"


def test_build_generated_week_plan_payload_applies_review_and_adaptation_runtime() -> None:
    finalized = build_generated_week_plan_payload(
        base_plan={
            "week_start": "2026-03-09",
            "split": "full_body",
            "phase": "maintenance",
            "sessions": [
                {
                    "exercises": [
                        {
                            "id": "bench",
                            "primary_exercise_id": "bench",
                            "sets": 3,
                            "recommended_working_weight": 100,
                        }
                    ]
                }
            ],
        },
        template_selection_trace={"interpreter": "recommend_generation_template_selection", "selected_template_id": "full_body_v1"},
        generation_runtime_trace={"interpreter": "resolve_week_generation_runtime_inputs", "outcome": {"effective_days_available": 3}},
        selected_template_id="full_body_v1",
        active_frequency_adaptation={
            "template_id": "full_body_v1",
            "program_id": "full_body_v1",
            "target_days": 3,
            "duration_weeks": 2,
            "weeks_remaining": 2,
            "weak_areas": ["chest"],
            "last_applied_week_start": None,
            "decision_trace": {"interpreter": "interpret_frequency_adaptation_apply"},
        },
        review_adjustments={
            "global": {"set_delta": 1, "weight_scale": 0.95},
            "weak_point_exercises": ["bench"],
            "exercise_overrides": {},
            "decision_trace": {"interpreter": "interpret_weekly_review_decision"},
        },
        review_context={"week_start": "2026-03-09", "reviewed_on": "2026-03-08"},
    )

    plan = finalized["plan"]
    exercise = plan["sessions"][0]["exercises"][0]

    assert plan["template_selection_trace"]["selected_template_id"] == "full_body_v1"
    assert plan["generation_runtime_trace"]["interpreter"] == "resolve_week_generation_runtime_inputs"
    assert exercise["sets"] == 4
    assert math.isclose(exercise["recommended_working_weight"], 95.0, rel_tol=1e-9, abs_tol=1e-9)
    assert plan["adaptive_review"]["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"
    assert plan["applied_frequency_adaptation"]["decision_trace"]["interpreter"] == "apply_active_frequency_adaptation_runtime"
    assert finalized["adaptation_runtime"]["state_updated"] is True


def test_prepare_generated_week_review_overlay_normalizes_context_and_adjustments() -> None:
    review_cycle = SimpleNamespace(
        week_start=date(2026, 3, 9),
        reviewed_on=date(2026, 3, 10),
        adjustments={
            "global": {"set_delta": 1, "weight_scale": 0.95},
            "exercise_overrides": {},
        },
    )

    overlay = prepare_generated_week_review_overlay(review_cycle)

    assert overlay["review_adjustments"]["global"]["set_delta"] == 1
    assert overlay["review_context"] == {"week_start": "2026-03-09", "reviewed_on": "2026-03-10"}
    assert overlay["decision_trace"]["interpreter"] == "prepare_generated_week_review_overlay"
    assert overlay["decision_trace"]["outcome"]["review_available"] is True


def test_build_coaching_recommendation_timeline_entry_humanizes_legacy_reasons_and_focus() -> None:
    entry = build_coaching_recommendation_timeline_entry(
        recommendation_id="rec_123",
        recommendation_type="coach_preview",
        status="previewed",
        template_id="full_body_v1",
        current_phase="accumulation",
        recommended_phase="accumulation",
        progression_action="hold",
        recommendation_payload={
            "progression": {
                "action": "hold",
                "reason": "under_target_without_high_fatigue",
            },
            "phase_transition": {
                "next_phase": "accumulation",
                "reason": "continue_accumulation",
            },
            "specialization": {
                "focus_muscles": ["biceps", "", "shoulders"],
            },
        },
        created_at=date(2026, 3, 5),
        applied_at=None,
    )

    assert entry["rationale"] == (
        "Stay in accumulation. Current readiness and momentum do not justify a phase change yet."
    )
    assert entry["focus_muscles"] == ["biceps", "shoulders"]


def test_normalize_coaching_recommendation_timeline_limit_clamps_to_bounds() -> None:
    assert normalize_coaching_recommendation_timeline_limit(-3) == 1
    assert normalize_coaching_recommendation_timeline_limit(20) == 20
    assert normalize_coaching_recommendation_timeline_limit(500) == 100


def test_build_coaching_recommendation_timeline_payload_normalizes_non_dict_payloads() -> None:
    rows = [
        SimpleNamespace(
            id="rec_1",
            recommendation_type="coach_preview",
            status="previewed",
            template_id="full_body_v1",
            current_phase="accumulation",
            recommended_phase="accumulation",
            progression_action="hold",
            recommendation_payload=None,
            created_at=datetime(2026, 3, 9, 8, 0),
            applied_at=None,
        ),
        SimpleNamespace(
            id="rec_2",
            recommendation_type="specialization_decision",
            status="applied",
            template_id="full_body_v1",
            current_phase="accumulation",
            recommended_phase="accumulation",
            progression_action="hold",
            recommendation_payload={
                "specialization": {"focus_muscles": ["biceps", "shoulders"]},
            },
            created_at=datetime(2026, 3, 9, 9, 0),
            applied_at=datetime(2026, 3, 9, 9, 5),
        ),
    ]

    payload = build_coaching_recommendation_timeline_payload(rows)

    assert len(payload["entries"]) == 2
    assert payload["entries"][0]["rationale"] == "No rationale recorded"
    assert payload["entries"][0]["focus_muscles"] == []
    assert payload["entries"][1]["focus_muscles"] == ["biceps", "shoulders"]


def test_extract_coaching_recommendation_focus_muscles_returns_filtered_list() -> None:
    focus_muscles = extract_coaching_recommendation_focus_muscles(
        {
            "specialization": {
                "focus_muscles": ["biceps", " ", "shoulders", 7],
            }
        }
    )

    assert focus_muscles == ["biceps", "shoulders", "7"]


def test_finalize_phase_application_adds_applied_recommendation_id() -> None:
    decision_payload = interpret_coach_phase_apply_decision(
        recommendation_id="rec_123",
        phase_transition={
            "next_phase": "intensification",
            "reason": "advance_to_intensification",
            "rationale": "Readiness supports a transition into intensification.",
        },
        confirm=True,
    )

    record_fields = build_phase_applied_recommendation_record(
        template_id="full_body_v1",
        current_phase="accumulation",
        progression_action="progress",
        source_recommendation_id="rec_123",
        next_phase="intensification",
    )
    finalized = finalize_applied_coaching_recommendation(
        payload_key="phase_transition",
        payload_value={
            "next_phase": "intensification",
            "reason": "advance_to_intensification",
        },
        decision_payload=decision_payload,
        applied_recommendation_id="applied_456",
    )

    assert record_fields["recommendation_type"] == "phase_decision"
    assert record_fields["recommended_phase"] == "intensification"
    assert record_fields["request_payload"]["source_recommendation_id"] == "rec_123"
    assert finalized["response_payload"]["applied_recommendation_id"] == "applied_456"
    assert finalized["response_payload"]["decision_trace"]["outcome"]["applied_recommendation_id"] == "applied_456"
    assert finalized["recommendation_payload"]["phase_transition"]["next_phase"] == "intensification"


def test_finalize_specialization_application_preserves_specialization_payload() -> None:
    decision_payload = interpret_coach_specialization_apply_decision(
        recommendation_id="rec_123",
        specialization={
            "focus_muscles": ["biceps", "shoulders"],
            "focus_adjustments": {"biceps": 2},
            "donor_adjustments": {"chest": -1},
            "uncompensated_added_sets": 1,
        },
        confirm=True,
    )

    record_fields = build_specialization_applied_recommendation_record(
        template_id="full_body_v1",
        current_phase="accumulation",
        recommended_phase="accumulation",
        progression_action="hold",
        source_recommendation_id="rec_123",
    )
    finalized = finalize_applied_coaching_recommendation(
        payload_key="specialization",
        payload_value={
            "focus_muscles": ["biceps", "shoulders"],
            "focus_adjustments": {"biceps": 2},
            "donor_adjustments": {"chest": -1},
            "uncompensated_added_sets": 1,
        },
        decision_payload=decision_payload,
        applied_recommendation_id="applied_789",
    )

    assert record_fields["recommendation_type"] == "specialization_decision"
    assert record_fields["request_payload"]["confirm"] is True
    assert finalized["recommendation_payload"]["specialization"]["focus_muscles"] == ["biceps", "shoulders"]
    assert finalized["response_payload"]["decision_trace"]["outcome"]["applied_recommendation_id"] == "applied_789"


def test_weekly_review_interpreter_returns_structured_trace_and_storage_payload() -> None:
    summary = summarize_weekly_review_performance(
        previous_week_start=date(2024, 1, 1),
        week_start=date(2024, 1, 8),
        previous_plan_payload={
            "sessions": [
                {
                    "exercises": [
                        {
                            "id": "bench",
                            "primary_exercise_id": "bench",
                            "name": "Bench Press",
                            "sets": 3,
                            "rep_range": [8, 12],
                            "recommended_working_weight": 100,
                        }
                    ]
                }
            ]
        },
        performed_logs=[
            {"primary_exercise_id": "bench", "exercise_id": "bench", "reps": 13, "weight": 100},
            {"primary_exercise_id": "bench", "exercise_id": "bench", "reps": 13, "weight": 100},
            {"primary_exercise_id": "bench", "exercise_id": "bench", "reps": 13, "weight": 100},
        ],
    )

    decision = interpret_weekly_review_decision(
        summary=summary,
        body_weight=80.0,
        calories=3000,
        protein=190,
        adherence_score=5,
    )

    assert decision["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"
    assert decision["decision_trace"]["outcome"]["readiness_score"] == decision["readiness_score"]
    assert decision["storage_adjustments"]["decision_trace"] == decision["decision_trace"]


def test_build_weekly_review_performance_summary_normalizes_plan_and_log_rows() -> None:
    summary = build_weekly_review_performance_summary(
        previous_week_start=date(2024, 1, 1),
        week_start=date(2024, 1, 8),
        previous_plan=SimpleNamespace(
            payload={
                "sessions": [
                    {
                        "exercises": [
                            {
                                "id": "bench",
                                "primary_exercise_id": "bench",
                                "name": "Bench Press",
                                "sets": 3,
                                "rep_range": [8, 12],
                                "recommended_working_weight": 100,
                            }
                        ]
                    }
                ]
            }
        ),
        performed_logs=[
            SimpleNamespace(primary_exercise_id="bench", exercise_id="bench", reps=13, weight=100),
            SimpleNamespace(primary_exercise_id="bench", exercise_id="bench", reps=13, weight=100),
            SimpleNamespace(primary_exercise_id="bench", exercise_id="bench", reps=13, weight=100),
        ],
    )

    assert summary["completion_pct"] == 100
    assert summary["planned_sets_total"] == 3
    assert summary["completed_sets_total"] == 3
    assert summary["decision_trace"]["interpreter"] == "summarize_weekly_review_performance"


def test_apply_weekly_review_adjustments_to_plan_exposes_persisted_trace() -> None:
    plan = {
        "sessions": [
            {
                "exercises": [
                    {
                        "id": "bench",
                        "primary_exercise_id": "bench",
                        "sets": 3,
                        "recommended_working_weight": 100,
                    }
                ]
            }
        ]
    }

    adjusted = apply_weekly_review_adjustments_to_plan(
        plan=plan,
        review_adjustments={
            "global": {"set_delta": 1, "weight_scale": 0.95},
            "weak_point_exercises": ["bench"],
            "exercise_overrides": {
                "bench": {"set_delta": 1, "weight_scale": 1.02, "rationale": "weak_point_bounded_extra_practice"}
            },
            "decision_trace": {"interpreter": "interpret_weekly_review_decision"},
        },
        review_context={"week_start": "2024-01-08", "reviewed_on": "2024-01-07"},
    )

    exercise = adjusted["sessions"][0]["exercises"][0]
    assert exercise["sets"] == 5
    assert math.isclose(exercise["recommended_working_weight"], 97.5, rel_tol=1e-9, abs_tol=1e-9)
    assert adjusted["adaptive_review"]["decision_trace"]["interpreter"] == "interpret_weekly_review_decision"


def test_interpret_workout_set_feedback_returns_trace_and_rationale() -> None:
    decision = interpret_workout_set_feedback(
        reps=6,
        weight=100,
        planned_reps_min=8,
        planned_reps_max=12,
        planned_weight=100,
        next_working_weight=100,
        rule_set=_sample_rule_set(),
    )

    assert decision["guidance"] == "below_target_reps_reduce_or_hold_load"
    assert decision["guidance_rationale"].startswith("Performance fell below the target range.")
    assert decision["decision_trace"]["interpreter"] == "interpret_workout_set_feedback"


def test_live_workout_adjustment_and_hydration_return_traces() -> None:
    live = recommend_live_workout_adjustment(
        planned_reps_min=8,
        planned_reps_max=12,
        planned_sets=3,
        completed_sets=1,
        last_reps=6,
        last_weight=100,
        average_reps=6.0,
        rule_set=_sample_rule_set(),
    )

    assert live["guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert live["decision_trace"]["interpreter"] == "recommend_live_workout_adjustment"

    hydrated = hydrate_live_workout_recommendation(
        completed_sets=1,
        remaining_sets=2,
        recommended_reps_min=8,
        recommended_reps_max=10,
        recommended_weight=97.5,
        guidance="remaining_sets_reduce_load_focus_target_reps",
        substitution_recommendation={
            "recommended_name": "Chest Supported Row",
            "compatible_substitutions": ["Chest Supported Row", "1-Arm Cable Row"],
            "failed_exposure_count": 3,
            "trigger_threshold": 3,
            "reason": "repeat_failure_threshold_reached",
            "decision_trace": {"interpreter": "resolve_repeat_failure_substitution"},
        },
        rule_set=_sample_rule_set(),
    )

    assert hydrated["decision_trace"]["interpreter"] == "hydrate_live_workout_recommendation"
    assert hydrated["guidance_rationale"].startswith("Reps dropped below target.")
    assert hydrated["substitution_recommendation"]["recommended_name"] == "Chest Supported Row"


def test_resolve_workout_session_state_update_returns_persistable_state_and_live_payload() -> None:
    resolved = resolve_workout_session_state_update(
        existing_set_history=[{"set_index": 1, "reps": 8, "weight": 100.0}],
        primary_exercise_id="bench",
        planned_sets=3,
        planned_reps_min=8,
        planned_reps_max=12,
        planned_weight=100.0,
        set_index=2,
        reps=6,
        weight=100.0,
        rule_set=_sample_rule_set(),
    )

    state = resolved["state"]
    live = resolved["live_recommendation"]

    assert state["primary_exercise_id"] == "bench"
    assert state["completed_sets"] == 2
    assert state["total_logged_reps"] == 14
    assert math.isclose(state["total_logged_weight"], 200.0)
    assert state["remaining_sets"] == 1
    assert state["last_guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert live["guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert live["decision_trace"]["interpreter"] == "recommend_live_workout_adjustment"


def test_resolve_workout_session_state_update_replaces_existing_set_index() -> None:
    resolved = resolve_workout_session_state_update(
        existing_set_history=[
            {"set_index": 1, "reps": 8, "weight": 100.0},
            {"set_index": 2, "reps": 7, "weight": 97.5},
        ],
        primary_exercise_id="bench",
        planned_sets=3,
        planned_reps_min=8,
        planned_reps_max=12,
        planned_weight=100.0,
        set_index=2,
        reps=9,
        weight=100.0,
        rule_set=_sample_rule_set(),
    )

    state = resolved["state"]

    assert len(state["set_history"]) == 2
    assert state["set_history"][1] == {"set_index": 2, "reps": 9, "weight": 100.0}
    assert state["total_logged_reps"] == 17
    assert state["completed_sets"] == 2


def test_build_workout_progress_payload_summarizes_completed_and_planned_sets() -> None:
    payload = build_workout_progress_payload(
        workout_id="session-1",
        completed_sets_by_exercise={"bench": 1, "row": 2},
        planned_session={
            "session_id": "session-1",
            "exercises": [
                {"id": "bench", "sets": 3},
                {"id": "row", "sets": 2},
            ],
        },
    )

    assert payload["workout_id"] == "session-1"
    assert payload["completed_total"] == 3
    assert payload["planned_total"] == 5
    assert payload["percent_complete"] == 60
    assert payload["exercises"] == [
        {"exercise_id": "bench", "planned_sets": 3, "completed_sets": 1},
        {"exercise_id": "row", "planned_sets": 2, "completed_sets": 2},
    ]


def test_build_workout_today_payload_hydrates_warmups_and_live_recommendations() -> None:
    live = hydrate_live_workout_recommendation(
        completed_sets=1,
        remaining_sets=2,
        recommended_reps_min=8,
        recommended_reps_max=10,
        recommended_weight=97.5,
        guidance="remaining_sets_reduce_load_focus_target_reps",
        rule_set=_sample_rule_set(),
    )

    payload = build_workout_today_payload(
        selected_session={
            "session_id": "session-1",
            "name": "Day 1",
            "exercises": [{"id": "bench", "recommended_working_weight": 100}],
        },
        mesocycle={"week_index": 2},
        deload={"active": False},
        completed_sets_by_exercise={"bench": 1},
        live_recommendations_by_exercise={"bench": live},
        resume_selected=True,
        daily_quote={"text": "Discipline.", "author": "Marcus Aurelius", "source": "Meditations"},
    )

    assert payload["resume"] is True
    assert payload["mesocycle"] == {"week_index": 2}
    assert payload["deload"] == {"active": False}
    assert payload["daily_quote"]["author"] == "Marcus Aurelius"
    assert payload["exercises"][0]["completed_sets"] == 1
    assert payload["exercises"][0]["live_recommendation"]["guidance"] == "remaining_sets_reduce_load_focus_target_reps"
    assert isinstance(payload["exercises"][0]["warmups"], list)
    assert payload["exercises"][0]["warmups"]


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


def test_resolve_workout_today_plan_payload_selects_latest_dict_payload() -> None:
    runtime = resolve_workout_today_plan_payload(
        plan_rows=[
            SimpleNamespace(payload={"program_template_id": "full_body_v1", "sessions": []}),
            SimpleNamespace(payload=None),
        ]
    )

    assert runtime["has_plan"] is True
    assert runtime["latest_plan_payload"]["program_template_id"] == "full_body_v1"
    assert runtime["decision_trace"]["interpreter"] == "resolve_workout_today_plan_payload"


def test_resolve_workout_today_plan_payload_handles_missing_plans() -> None:
    runtime = resolve_workout_today_plan_payload(plan_rows=[])

    assert runtime["has_plan"] is False
    assert runtime["latest_plan_payload"] == {}


def test_build_workout_today_log_runtime_projects_resume_and_completion_rows() -> None:
    runtime = build_workout_today_log_runtime(
        recent_logs=[
            SimpleNamespace(workout_id="day-1"),
            SimpleNamespace(workout_id="day-1"),
            SimpleNamespace(workout_id="day-2"),
        ],
        selected_session_logs=[
            SimpleNamespace(exercise_id="bench", set_index=1),
            SimpleNamespace(exercise_id="bench", set_index=2),
        ],
    )

    assert runtime["resume_logs"] == [
        {"workout_id": "day-1"},
        {"workout_id": "day-1"},
        {"workout_id": "day-2"},
    ]
    assert runtime["completion_logs"] == [
        {"exercise_id": "bench", "set_index": 1},
        {"exercise_id": "bench", "set_index": 2},
    ]
    assert runtime["decision_trace"]["interpreter"] == "build_workout_today_log_runtime"


def test_build_workout_summary_progression_lookup_runtime_normalizes_primary_ids() -> None:
    runtime = build_workout_summary_progression_lookup_runtime(
        planned_session={
            "exercises": [
                {"id": "bench-alt", "primary_exercise_id": "bench"},
                {"id": "row"},
                {"id": "bench-alt-2", "primary_exercise_id": "bench"},
                "invalid",
            ]
        }
    )

    assert runtime["primary_exercise_ids"] == ["bench", "row"]
    assert runtime["decision_trace"]["interpreter"] == "build_workout_summary_progression_lookup_runtime"
    assert runtime["decision_trace"]["outcome"]["primary_exercise_id_count"] == 2


def test_build_workout_today_progression_lookup_runtime_normalizes_primary_ids() -> None:
    runtime = build_workout_today_progression_lookup_runtime(
        session_states=[
            SimpleNamespace(primary_exercise_id="bench"),
            SimpleNamespace(primary_exercise_id="row"),
            SimpleNamespace(primary_exercise_id="bench"),
            SimpleNamespace(primary_exercise_id=None),
        ]
    )

    assert runtime["primary_exercise_ids"] == ["bench", "row"]
    assert runtime["decision_trace"]["interpreter"] == "build_workout_today_progression_lookup_runtime"
    assert runtime["decision_trace"]["outcome"]["primary_exercise_id_count"] == 2


def test_resolve_workout_today_session_selection_prefers_latest_incomplete_session() -> None:
    selection = resolve_workout_today_session_selection(
        sessions=[
            {"session_id": "a", "date": "2026-03-05"},
            {"session_id": "b", "date": "2026-03-07"},
        ],
        latest_logged_workout_id="a",
        latest_logged_session_incomplete=True,
        today_iso="2026-03-07",
    )

    assert selection["selected_session"]["session_id"] == "a"
    assert selection["resume_selected"] is True
    assert selection["selection_reason"] == "resume_incomplete_session"


def test_resolve_workout_today_session_selection_falls_back_to_today_match_then_first() -> None:
    today_selection = resolve_workout_today_session_selection(
        sessions=[
            {"session_id": "a", "date": "2026-03-05"},
            {"session_id": "b", "date": "2026-03-07"},
        ],
        latest_logged_workout_id="a",
        latest_logged_session_incomplete=False,
        today_iso="2026-03-07",
    )
    fallback_selection = resolve_workout_today_session_selection(
        sessions=[
            {"session_id": "a", "date": "2026-03-05"},
            {"session_id": "b", "date": "2026-03-06"},
        ],
        latest_logged_workout_id=None,
        latest_logged_session_incomplete=False,
        today_iso="2026-03-07",
    )

    assert today_selection["selected_session"]["session_id"] == "b"
    assert today_selection["resume_selected"] is False
    assert today_selection["selection_reason"] == "today_match"
    assert fallback_selection["selected_session"]["session_id"] == "a"
    assert fallback_selection["selection_reason"] == "first_session_fallback"


def test_resolve_latest_logged_workout_resume_state_returns_latest_session_and_incomplete_flag() -> None:
    runtime = resolve_latest_logged_workout_resume_state(
        sessions=[
            {"session_id": "a", "exercises": [{"sets": 2}, {"sets": 1}]},
            {"session_id": "b", "exercises": [{"sets": 3}]},
        ],
        performed_logs=[
            {"workout_id": "a"},
            {"workout_id": "a"},
        ],
    )

    assert runtime["latest_logged_workout_id"] == "a"
    assert runtime["latest_logged_session_incomplete"] is True


def test_resolve_latest_logged_workout_resume_state_handles_complete_and_missing_sessions() -> None:
    complete_runtime = resolve_latest_logged_workout_resume_state(
        sessions=[{"session_id": "a", "exercises": [{"sets": 2}]}],
        performed_logs=[
            {"workout_id": "a"},
            {"workout_id": "a"},
        ],
    )
    missing_runtime = resolve_latest_logged_workout_resume_state(
        sessions=[{"session_id": "a", "exercises": [{"sets": 2}]}],
        performed_logs=[{"workout_id": "z"}],
    )

    assert complete_runtime["latest_logged_workout_id"] == "a"
    assert complete_runtime["latest_logged_session_incomplete"] is False
    assert missing_runtime["latest_logged_workout_id"] == "z"
    assert missing_runtime["latest_logged_session_incomplete"] is False


def test_resolve_workout_plan_reference_returns_session_exercise_and_program() -> None:
    reference = resolve_workout_plan_reference(
        plan_payloads=[
            {
                "program_template_id": "full_body_v1",
                "sessions": [
                    {
                        "session_id": "session-1",
                        "exercises": [
                            {"id": "bench", "sets": 3},
                            {"id": "row", "sets": 3},
                        ],
                    }
                ],
            }
        ],
        workout_id="session-1",
        exercise_id="row",
    )

    assert reference["program_id"] == "full_body_v1"
    assert reference["session"]["session_id"] == "session-1"
    assert reference["exercise"]["id"] == "row"


def test_resolve_workout_plan_reference_returns_none_when_unmatched() -> None:
    reference = resolve_workout_plan_reference(
        plan_payloads=[{"program_template_id": "full_body_v1", "sessions": []}],
        workout_id="missing-session",
        exercise_id="missing-exercise",
    )

    assert reference == {
        "session": None,
        "exercise": None,
        "program_id": None,
    }


def test_resolve_workout_plan_context_normalizes_plan_rows() -> None:
    rows = [
        SimpleNamespace(
            payload={
                "program_template_id": "full_body_v1",
                "sessions": [
                    {
                        "session_id": "session-1",
                        "exercises": [{"id": "bench"}, {"id": "row"}],
                    }
                ],
            }
        ),
        SimpleNamespace(payload=None),
    ]
    context = resolve_workout_plan_context(
        plan_rows=rows,
        workout_id="session-1",
        exercise_id="row",
    )

    assert context["program_id"] == "full_body_v1"
    assert context["session"]["session_id"] == "session-1"
    assert context["exercise"]["id"] == "row"
    assert context["decision_trace"]["interpreter"] == "resolve_workout_plan_context"


def test_resolve_workout_plan_context_returns_none_for_unmatched_workout() -> None:
    context = resolve_workout_plan_context(
        plan_rows=[SimpleNamespace(payload={"program_template_id": "full_body_v1", "sessions": []})],
        workout_id="missing-workout",
        exercise_id=None,
    )

    assert context["session"] is None
    assert context["exercise"] is None
    assert context["program_id"] is None
    assert context["decision_trace"]["outcome"]["matched_session"] is False


def test_resolve_weekly_review_window_rolls_sunday_into_next_review_week() -> None:
    sunday_window = resolve_weekly_review_window(today=date(2026, 3, 8))
    wednesday_window = resolve_weekly_review_window(today=date(2026, 3, 4))

    assert sunday_window["today_is_sunday"] is True
    assert sunday_window["current_week_start"] == date(2026, 3, 2)
    assert sunday_window["week_start"] == date(2026, 3, 9)
    assert sunday_window["previous_week_start"] == date(2026, 3, 2)
    assert sunday_window["previous_week_end"] == date(2026, 3, 8)

    assert wednesday_window["today_is_sunday"] is False
    assert wednesday_window["week_start"] == date(2026, 3, 2)
    assert wednesday_window["previous_week_start"] == date(2026, 2, 23)


def test_build_weekly_review_status_payload_marks_review_required_only_on_sunday_without_existing_review() -> None:
    payload = build_weekly_review_status_payload(
        today=date(2026, 3, 8),
        existing_review_submitted=False,
        previous_week_summary={"planned_sets_total": 9},
    )
    existing_payload = build_weekly_review_status_payload(
        today=date(2026, 3, 8),
        existing_review_submitted=True,
        previous_week_summary={"planned_sets_total": 9},
    )

    assert payload["today_is_sunday"] is True
    assert payload["review_required"] is True
    assert payload["previous_week_summary"] == {"planned_sets_total": 9}
    assert existing_payload["review_required"] is False


def test_prepare_weekly_review_submit_window_defaults_to_window_week_start() -> None:
    runtime = prepare_weekly_review_submit_window(
        today=date(2026, 3, 8),
        requested_week_start=None,
    )

    assert runtime["week_start"] == date(2026, 3, 9)
    assert runtime["previous_week_start"] == date(2026, 3, 2)
    assert runtime["decision_trace"]["interpreter"] == "prepare_weekly_review_submit_window"
    assert runtime["decision_trace"]["outcome"]["source"] == "window_default"


def test_workout_summary_interpreters_return_structured_trace() -> None:
    exercise_summary = summarize_workout_exercise_performance(
        exercise={
            "id": "bench",
            "primary_exercise_id": "bench",
            "name": "Bench Press",
            "sets": 3,
            "rep_range": [8, 12],
            "recommended_working_weight": 100,
        },
        performed_logs=[
            {"set_index": 1, "reps": 6, "weight": 97.5},
            {"set_index": 2, "reps": 6, "weight": 97.5},
            {"set_index": 3, "reps": 6, "weight": 97.5},
        ],
        next_working_weight=100,
        rule_set=_sample_rule_set(),
    )

    summary = summarize_workout_session_guidance(
        workout_id="workout_a",
        completed_total=3,
        planned_total=3,
        exercise_summaries=[exercise_summary],
        rule_set=_sample_rule_set(),
    )

    assert exercise_summary["decision_trace"]["interpreter"] == "summarize_workout_exercise_performance"
    assert summary["decision_trace"]["interpreter"] == "summarize_workout_session_guidance"
    assert summary["overall_guidance"] == "performance_below_target_adjust_load_and_recover"


def test_frequency_adaptation_interpreters_emit_trace_and_runtime_state() -> None:
    request_runtime_trace = {
        "interpreter": "prepare_frequency_adaptation_runtime_inputs",
        "outcome": {"program_id": "full_body_v1"},
    }
    preview = recommend_frequency_adaptation_preview(
        onboarding_package=_sample_onboarding_package(),
        program_id="full_body_v1",
        current_days=5,
        target_days=3,
        duration_weeks=2,
        explicit_weak_areas=[],
        stored_weak_areas=["Chest", "hamstrings"],
        equipment_profile=["barbell", "bench"],
        recovery_state="normal",
        current_week_index=2,
        request_runtime_trace=request_runtime_trace,
    )

    assert preview["decision_trace"]["interpreter"] == "recommend_frequency_adaptation_preview"
    assert preview["decision_trace"]["version"] == "v1"
    assert isinstance(preview["decision_trace"]["steps"], list)
    assert preview["decision_trace"]["outcome"]["reason_code"] == "preview_generated"
    assert preview["decision_trace"]["outcome"]["weak_area_bonus_slots"] == 2
    assert preview["decision_trace"]["resolved_context"]["weak_area_source"] == "profile"
    assert preview["decision_trace"]["request_runtime_trace"]["interpreter"] == "prepare_frequency_adaptation_runtime_inputs"

    applied = interpret_frequency_adaptation_apply(
        onboarding_package=_sample_onboarding_package(),
        program_id="full_body_v1",
        current_days=5,
        target_days=3,
        duration_weeks=2,
        explicit_weak_areas=["chest"],
        stored_weak_areas=["hamstrings"],
        equipment_profile=["barbell", "bench"],
        recovery_state="normal",
        current_week_index=2,
        applied_at="2026-03-07T00:00:00",
        request_runtime_trace=request_runtime_trace,
    )

    assert applied["decision_trace"]["interpreter"] == "interpret_frequency_adaptation_apply"
    assert applied["decision_trace"]["version"] == "v1"
    assert isinstance(applied["decision_trace"]["steps"], list)
    assert applied["decision_trace"]["outcome"]["reason_code"] == "adaptation_applied"
    assert applied["decision_trace"]["resolved_context"]["weak_areas"] == ["chest"]
    assert applied["decision_trace"]["request_runtime_trace"]["interpreter"] == "prepare_frequency_adaptation_runtime_inputs"

    active = resolve_active_frequency_adaptation_runtime(
        active_state=applied["persistence_state"],
        selected_template_id="full_body_v1",
    )

    runtime = apply_active_frequency_adaptation_runtime(
        plan={"week_start": "2026-03-09", "sessions": []},
        selected_template_id="full_body_v1",
        active_frequency_adaptation=active,
    )

    summary = runtime["plan"]["applied_frequency_adaptation"]
    assert summary["decision_trace"]["interpreter"] == "apply_active_frequency_adaptation_runtime"
    assert summary["weeks_remaining_after_apply"] == 1


def test_generation_template_selection_orders_candidates_for_adaptation_and_split() -> None:
    ordered = order_generation_template_candidates(
        preferred_template_id="ppl_v1",
        split_preference="ppl",
        days_available=3,
        candidate_summaries=[
            {"id": "upper_lower_v1", "split": "ppl", "days_supported": [3], "session_count": 5},
            {"id": "ppl_v1", "split": "ppl", "days_supported": [3], "session_count": 3},
            {"id": "full_body_v1", "split": "full_body", "days_supported": [3], "session_count": 3},
        ],
    )

    assert ordered[:3] == ["ppl_v1", "upper_lower_v1", "full_body_v1"]


def test_intelligence_module_no_longer_defines_generation_template_selection_helpers() -> None:
    assert "order_generation_template_candidates" not in intelligence_module.__dict__
    assert "recommend_generation_template_selection" not in intelligence_module.__dict__


def test_generation_template_selection_returns_trace_for_viable_candidate() -> None:
    decision = recommend_generation_template_selection(
        explicit_template_id=None,
        profile_template_id="ppl_v1",
        split_preference="ppl",
        days_available=3,
        candidate_summaries=[
            {"id": "upper_lower_v1", "split": "ppl", "days_supported": [3], "session_count": 5},
            {"id": "ppl_v1", "split": "ppl", "days_supported": [3], "session_count": 3},
        ],
        candidate_evaluations=[
            {"template_id": "ppl_v1", "status": "loaded", "session_count": 0, "exercise_count": 0},
            {"template_id": "upper_lower_v1", "status": "loaded", "session_count": 1, "exercise_count": 1},
        ],
    )

    assert decision["selected_template_id"] == "upper_lower_v1"
    assert decision["decision_trace"]["interpreter"] == "recommend_generation_template_selection"
    assert decision["decision_trace"]["reason"] == "first_viable_candidate"


def test_generation_template_selection_returns_trace_for_explicit_override() -> None:
    decision = recommend_generation_template_selection(
        explicit_template_id="explicit_template",
        profile_template_id="full_body_v1",
        split_preference="full_body",
        days_available=3,
        candidate_summaries=[],
        candidate_evaluations=[],
    )

    assert decision["selected_template_id"] == "explicit_template"
    assert decision["decision_trace"]["reason"] == "explicit_template_override"
