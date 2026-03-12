from core_engine.decision_coach_preview import (
    build_applied_coaching_recommendation_record_values,
    build_applied_coaching_recommendation_response,
    finalize_applied_coaching_recommendation_commit_runtime,
    prepare_coaching_apply_commit_runtime,
    build_phase_applied_recommendation_record,
    build_coaching_recommendation_timeline_entry,
    build_coaching_recommendation_timeline_payload,
    build_coach_preview_payloads,
    build_coach_preview_recommendation_record_fields,
    finalize_coach_preview_commit_runtime,
    build_specialization_applied_recommendation_record,
    extract_coaching_recommendation_focus_muscles,
    finalize_applied_coaching_recommendation,
    interpret_coach_phase_apply_decision,
    interpret_coach_specialization_apply_decision,
    normalize_coaching_recommendation_timeline_limit,
    resolve_coaching_recommendation_rationale,
    prepare_coaching_apply_runtime_source,
    prepare_applied_coaching_recommendation_commit_runtime,
    prepare_coach_preview_commit_runtime,
    prepare_coach_preview_route_runtime,
    prepare_coaching_apply_decision_runtime,
    prepare_coaching_apply_route_finalize_runtime,
    prepare_coaching_apply_route_runtime,
    prepare_coach_preview_decision_context,
    prepare_phase_apply_runtime,
    prepare_specialization_apply_runtime,
    recommend_specialization_adjustments,
    recommend_coach_intelligence_preview,
    summarize_program_media_and_warmups,
)


def test_build_coach_preview_payloads_keeps_response_and_persistence_isolated() -> None:
    payloads = build_coach_preview_payloads(
        recommendation_id="rec_123",
        preview_payload={"specialization": {"focus_muscles": ["biceps", "shoulders"]}},
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


def test_prepare_and_finalize_coach_preview_commit_runtime_shape_record_and_payloads() -> None:
    prepared = prepare_coach_preview_commit_runtime(
        user_id="user_123",
        template_id="full_body_v1",
        preview_request={"current_phase": "accumulation"},
        preview_payload={
            "phase_transition": {"next_phase": "intensification"},
            "progression": {"action": "hold"},
            "specialization": {"focus_muscles": ["lats"]},
        },
        program_name="Full Body V1",
    )

    assert prepared["record_values"]["user_id"] == "user_123"
    assert prepared["record_values"]["recommendation_type"] == "coach_preview"
    assert prepared["decision_trace"]["interpreter"] == "prepare_coach_preview_commit_runtime"

    finalized = finalize_coach_preview_commit_runtime(
        prepared_runtime=prepared,
        recommendation_id="rec_123",
    )
    assert finalized["response_payload"]["recommendation_id"] == "rec_123"
    assert finalized["response_payload"]["program_name"] == "Full Body V1"
    assert finalized["recommendation_payload"]["specialization"]["focus_muscles"] == ["lats"]


def test_prepare_coach_preview_route_runtime_builds_preview_and_commit_runtime() -> None:
    route_runtime = prepare_coach_preview_route_runtime(
        user_id="user_123",
        template_id="full_body_v1",
        context={"split_preference": "full_body"},
        preview_request={"current_phase": "accumulation"},
        rule_set={"rationale_templates": {}},
        request_runtime_trace={"interpreter": "prepare_coach_preview_runtime_inputs"},
        template_runtime_trace={"interpreter": "prepare_generation_template_runtime"},
        program_name="Full Body V1",
        recommend_coach_intelligence_preview=lambda **kwargs: {
            "template_id": kwargs["template_id"],
            "phase_transition": {"next_phase": "intensification"},
            "progression": {"action": "hold"},
            "specialization": {"focus_muscles": ["chest"]},
        },
        prepare_coach_preview_commit_runtime=lambda **kwargs: {
            "record_values": {"user_id": kwargs["user_id"], "template_id": kwargs["template_id"]},
            "payload_runtime": {
                "preview_payload": kwargs["preview_payload"],
                "program_name": kwargs["program_name"],
            },
        },
    )

    assert route_runtime["preview_payload"]["phase_transition"]["next_phase"] == "intensification"
    assert route_runtime["commit_runtime"]["record_values"]["user_id"] == "user_123"
    assert route_runtime["commit_runtime"]["payload_runtime"]["program_name"] == "Full Body V1"
    assert route_runtime["decision_trace"]["interpreter"] == "prepare_coach_preview_route_runtime"


def test_prepare_coaching_apply_runtime_source_normalizes_recommendation_payload() -> None:
    class _Rec:
        id = "rec_123"
        recommendation_payload = None
        template_id = "full_body_v1"
        current_phase = "accumulation"
        recommended_phase = "intensification"
        progression_action = "hold"

    source = prepare_coaching_apply_runtime_source(_Rec())

    assert source["recommendation_id"] == "rec_123"
    assert source["recommendation_payload"] == {}
    assert source["decision_trace"]["interpreter"] == "prepare_coaching_apply_runtime_source"


def test_prepare_phase_apply_runtime_uses_fallback_phase_and_builds_record_fields() -> None:
    runtime = prepare_phase_apply_runtime(
        recommendation_id="rec_123",
        recommendation_payload={
            "phase_transition": {"reason": "continue_accumulation", "rationale": "Stay in accumulation."}
        },
        fallback_next_phase="accumulation",
        confirm=True,
        template_id="full_body_v1",
        current_phase="accumulation",
        progression_action="hold",
        interpret_phase_apply_decision=lambda **kwargs: {"next_phase": kwargs["phase_transition"]["next_phase"]},
        build_phase_applied_record=lambda **kwargs: {"recommended_phase": kwargs["next_phase"]},
    )

    assert runtime["payload_value"]["next_phase"] == "accumulation"
    assert runtime["record_fields"]["recommended_phase"] == "accumulation"


def test_prepare_specialization_apply_runtime_rejects_missing_payload() -> None:
    try:
        prepare_specialization_apply_runtime(
            recommendation_id="rec_123",
            recommendation_payload={},
            confirm=False,
            template_id="full_body_v1",
            current_phase="accumulation",
            recommended_phase="intensification",
            progression_action="hold",
            interpret_specialization_apply_decision=lambda **kwargs: kwargs,
            build_specialization_applied_record=lambda **kwargs: kwargs,
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "missing specialization details" in str(exc)


def test_interpret_coach_phase_apply_decision_requires_supported_phase() -> None:
    try:
        interpret_coach_phase_apply_decision(
            recommendation_id="rec_123",
            phase_transition={"next_phase": "unsupported"},
            confirm=False,
            humanize_phase_transition_reason=lambda _: "fallback",
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "unsupported next phase" in str(exc)


def test_interpret_coach_phase_apply_decision_builds_trace_with_fallback_rationale() -> None:
    decision = interpret_coach_phase_apply_decision(
        recommendation_id="rec_123",
        phase_transition={"next_phase": "deload", "reason": "phase_apply"},
        confirm=True,
        humanize_phase_transition_reason=lambda _: "Apply the recommendation.",
    )

    assert decision["status"] == "applied"
    assert decision["applied"] is True
    assert decision["requires_confirmation"] is False
    assert decision["rationale"] == "Apply the recommendation."
    assert decision["decision_trace"]["interpreter"] == "interpret_coach_phase_apply_decision"


def test_interpret_coach_specialization_apply_decision_normalizes_payload_and_trace() -> None:
    decision = interpret_coach_specialization_apply_decision(
        recommendation_id="rec_123",
        specialization={
            "focus_muscles": ["chest"],
            "focus_adjustments": {"chest": "1"},
            "donor_adjustments": {"arms": -1},
            "uncompensated_added_sets": "2",
        },
        confirm=False,
    )

    assert decision["status"] == "confirmation_required"
    assert decision["focus_adjustments"] == {"chest": 1}
    assert decision["donor_adjustments"] == {"arms": -1}
    assert decision["uncompensated_added_sets"] == 2
    assert decision["decision_trace"]["interpreter"] == "interpret_coach_specialization_apply_decision"


def test_build_phase_applied_recommendation_record_shapes_apply_metadata() -> None:
    record = build_phase_applied_recommendation_record(
        template_id="full_body_v1",
        current_phase="accumulation",
        progression_action="hold",
        source_recommendation_id="rec_123",
        next_phase="deload",
    )

    assert record["recommendation_type"] == "phase_decision"
    assert record["recommended_phase"] == "deload"
    assert record["request_payload"]["source_recommendation_id"] == "rec_123"


def test_build_specialization_applied_recommendation_record_shapes_apply_metadata() -> None:
    record = build_specialization_applied_recommendation_record(
        template_id="full_body_v1",
        current_phase="accumulation",
        recommended_phase="intensification",
        progression_action="hold",
        source_recommendation_id="rec_123",
    )

    assert record["recommendation_type"] == "specialization_decision"
    assert record["recommended_phase"] == "intensification"
    assert record["request_payload"]["confirm"] is True


def test_recommend_specialization_adjustments_prioritizes_low_volume_lagging_muscles() -> None:
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


def test_summarize_program_media_and_warmups_reports_video_coverage() -> None:
    summary = summarize_program_media_and_warmups(
        {
            "sessions": [
                {
                    "exercises": [
                        {
                            "id": "bench",
                            "start_weight": 100,
                            "video": {"youtube_url": "https://example.com/bench"},
                        },
                        {"id": "row", "start_weight": 90},
                        {"id": "squat", "start_weight": 140},
                        {"id": "curl", "start_weight": 25},
                    ]
                },
                {"exercises": [{"id": "dip"}, {"id": "lateral_raise"}]},
            ]
        }
    )

    assert summary["total_exercises"] == 6
    assert summary["video_linked_exercises"] == 1
    assert summary["video_coverage_pct"] > 0
    assert len(summary["sample_warmups"]) == 3


def test_finalize_applied_coaching_recommendation_appends_applied_recommendation_id() -> None:
    finalized = finalize_applied_coaching_recommendation(
        payload_key="phase_transition",
        payload_value={"next_phase": "deload"},
        decision_payload={
            "status": "applied",
            "decision_trace": {
                "interpreter": "interpret_coach_phase_apply_decision",
                "outcome": {"status": "applied"},
            },
        },
        applied_recommendation_id="rec_applied_123",
    )

    trace_outcome = finalized["recommendation_payload"]["decision_trace"]["outcome"]
    assert trace_outcome["status"] == "applied"
    assert trace_outcome["applied_recommendation_id"] == "rec_applied_123"
    assert finalized["response_payload"]["applied_recommendation_id"] == "rec_applied_123"


def test_recommend_coach_intelligence_preview_builds_payload_and_trace() -> None:
    preview = recommend_coach_intelligence_preview(
        template_id="full_body_v1",
        context={
            "split_preference": "full_body",
            "program_template": {"sessions": [{"exercises": [{"id": "bench"}]}]},
            "phase": "maintenance",
            "user_profile": {"days_available": 4},
            "history": [{"exercise_id": "bench"}],
            "available_equipment": ["dumbbell"],
        },
        preview_request={
            "from_days": 4,
            "to_days": 3,
            "completion_pct": 90,
            "adherence_score": 4,
            "soreness_level": "mild",
            "current_phase": "accumulation",
            "weeks_in_phase": 2,
            "stagnation_weeks": 0,
            "lagging_muscles": ["chest"],
            "target_min_sets": 10,
        },
        rule_set={"rationale_templates": {}},
        request_runtime_trace={"interpreter": "prepare_coach_preview_runtime_inputs"},
        template_runtime_trace={"interpreter": "prepare_generation_template_runtime"},
        evaluate_schedule_adaptation=lambda **_: {
            "from_days": 4,
            "to_days": 3,
            "kept_sessions": ["A", "B"],
            "dropped_sessions": ["C"],
            "added_sessions": [],
            "risk_level": "low",
            "muscle_set_delta": {"chest": -1},
            "to_plan": {"weekly_volume_by_muscle": {"chest": 9}},
        },
        recommend_progression_action=lambda **_: {"action": "hold", "reason": "maintain"},
        humanize_progression_reason=lambda *_args, **_kwargs: "Hold load.",
        derive_readiness_score=lambda **_: 78,
        recommend_phase_transition=lambda **_: {"next_phase": "accumulation", "reason": "continue"},
        humanize_phase_transition_reason=lambda *_args, **_kwargs: "Stay in accumulation.",
        recommend_specialization_adjustments=lambda **_: {
            "focus_muscles": ["chest"],
            "focus_adjustments": {"chest": 1},
            "donor_adjustments": {"arms": -1},
            "uncompensated_added_sets": 0,
        },
        summarize_program_media_and_warmups=lambda *_args, **_kwargs: {
            "total_exercises": 1,
            "video_linked_exercises": 1,
            "video_coverage_pct": 100.0,
            "sample_warmups": [{"exercise_id": "bench"}],
        },
    )

    assert preview["schedule"]["risk_level"] == "low"
    assert preview["progression"]["rationale"] == "Hold load."
    assert preview["phase_transition"]["rationale"] == "Stay in accumulation."
    assert preview["decision_trace"]["interpreter"] == "recommend_coach_intelligence_preview"
    assert preview["decision_trace"]["request_runtime_trace"]["interpreter"] == "prepare_coach_preview_runtime_inputs"


def test_recommend_coach_intelligence_preview_uses_provided_readiness_score() -> None:
    preview = recommend_coach_intelligence_preview(
        template_id="full_body_v1",
        context={"program_template": {}, "user_profile": {}},
        preview_request={
            "from_days": 3,
            "to_days": 3,
            "readiness_score": 61,
            "completion_pct": 80,
            "adherence_score": 3,
            "soreness_level": "none",
            "current_phase": "accumulation",
            "weeks_in_phase": 1,
            "stagnation_weeks": 0,
        },
        rule_set=None,
        evaluate_schedule_adaptation=lambda **_: {
            "from_days": 3,
            "to_days": 3,
            "kept_sessions": [],
            "dropped_sessions": [],
            "added_sessions": [],
            "risk_level": "low",
            "muscle_set_delta": {},
            "to_plan": {"weekly_volume_by_muscle": {}},
        },
        recommend_progression_action=lambda **_: {"action": "hold", "reason": "maintain"},
        humanize_progression_reason=lambda *_args, **_kwargs: "Hold",
        derive_readiness_score=lambda **_: 12,
        recommend_phase_transition=lambda **kwargs: {"next_phase": kwargs["current_phase"], "reason": "continue"},
        humanize_phase_transition_reason=lambda *_args, **_kwargs: "Continue",
        recommend_specialization_adjustments=lambda **_: {
            "focus_muscles": [],
            "focus_adjustments": {},
            "donor_adjustments": {},
            "uncompensated_added_sets": 0,
        },
        summarize_program_media_and_warmups=lambda *_args, **_kwargs: {
            "total_exercises": 0,
            "video_linked_exercises": 0,
            "video_coverage_pct": 0.0,
            "sample_warmups": [],
        },
    )

    readiness_step = next(
        step for step in preview["decision_trace"]["steps"] if step.get("decision") == "readiness_score"
    )
    assert readiness_step["result"]["provided"] is True
    assert readiness_step["result"]["value"] == 61


def test_recommend_coach_intelligence_preview_prefers_context_coaching_state_when_score_not_provided() -> None:
    captured: dict[str, object] = {}

    def _derive_readiness_score(**kwargs: object) -> int:
        captured.update(kwargs)
        return 50

    preview = recommend_coach_intelligence_preview(
        template_id="full_body_v1",
        context={
            "program_template": {},
            "user_profile": {},
            "coaching_state": {
                "readiness": {
                    "sleep_quality": 2,
                    "stress_level": 4,
                    "pain_flags": ["elbow_flexion"],
                    "recovery_risk_flags": ["high_stress", "low_sleep", "pain_flags_present"],
                },
                "stall": {
                    "stalled_exercise_ids": [],
                    "consecutive_underperformance_weeks": 2,
                    "phase_stagnation_weeks": 1,
                },
                "mesocycle": {},
            },
        },
        preview_request={
            "from_days": 3,
            "to_days": 3,
            "completion_pct": 95,
            "adherence_score": 4,
            "soreness_level": "mild",
            "current_phase": "deload",
            "weeks_in_phase": 1,
        },
        rule_set=None,
        evaluate_schedule_adaptation=lambda **_: {
            "from_days": 3,
            "to_days": 3,
            "kept_sessions": [],
            "dropped_sessions": [],
            "added_sessions": [],
            "risk_level": "low",
            "muscle_set_delta": {},
            "to_plan": {"weekly_volume_by_muscle": {}},
        },
        recommend_progression_action=lambda **_: {"action": "progress", "reason": "maintain"},
        humanize_progression_reason=lambda *_args, **_kwargs: "Progress",
        derive_readiness_score=_derive_readiness_score,
        recommend_phase_transition=lambda **kwargs: {"next_phase": kwargs["current_phase"], "reason": "continue"},
        humanize_phase_transition_reason=lambda *_args, **_kwargs: "Continue",
        recommend_specialization_adjustments=lambda **_: {
            "focus_muscles": [],
            "focus_adjustments": {},
            "donor_adjustments": {},
            "uncompensated_added_sets": 0,
        },
        summarize_program_media_and_warmups=lambda *_args, **_kwargs: {
            "total_exercises": 0,
            "video_linked_exercises": 0,
            "video_coverage_pct": 0.0,
            "sample_warmups": [],
        },
    )

    readiness_step = next(
        step for step in preview["decision_trace"]["steps"] if step.get("decision") == "readiness_score"
    )
    coaching_state_step = next(
        step for step in preview["decision_trace"]["steps"] if step.get("decision") == "canonical_coaching_state"
    )
    assert captured["sleep_quality"] == 2
    assert captured["stress_level"] == 4
    assert captured["pain_flags"] == ["elbow_flexion"]
    assert readiness_step["result"]["provided"] is False
    assert readiness_step["result"]["source"] == "context_coaching_state"
    assert readiness_step["result"]["value"] == 50
    assert coaching_state_step["result"]["readiness_source"] == "coaching_state.readiness"
    assert coaching_state_step["result"]["stall_source"] == "coaching_state.stall"
    assert coaching_state_step["result"]["stagnation_weeks"] == 2


def test_recommend_coach_intelligence_preview_traces_canonical_sfr_context_without_overwriting_progression_snapshot() -> None:
    canonical_snapshot = {
        "stimulus_quality": "moderate",
        "fatigue_cost": "low",
        "recoverability": "high",
        "progression_eligibility": True,
        "deload_pressure": "low",
        "substitution_pressure": "low",
        "signals": {
            "stimulus": ["recent_completion_strong"],
            "fatigue": [],
            "recoverability": ["sleep_supportive"],
        },
    }
    progression_snapshot = {
        "stimulus_quality": "low",
        "fatigue_cost": "high",
        "recoverability": "low",
        "progression_eligibility": False,
        "deload_pressure": "high",
        "substitution_pressure": "moderate",
    }

    preview = recommend_coach_intelligence_preview(
        template_id="full_body_v1",
        context={
            "program_template": {},
            "user_profile": {},
            "coaching_state": {
                "readiness": {},
                "stall": {},
                "mesocycle": {},
                "stimulus_fatigue_response": canonical_snapshot,
            },
        },
        preview_request={
            "from_days": 3,
            "to_days": 3,
            "completion_pct": 82,
            "adherence_score": 3,
            "soreness_level": "moderate",
            "average_rpe": 9.0,
            "current_phase": "accumulation",
            "weeks_in_phase": 2,
            "stagnation_weeks": 0,
        },
        rule_set=None,
        evaluate_schedule_adaptation=lambda **_: {
            "from_days": 3,
            "to_days": 3,
            "kept_sessions": [],
            "dropped_sessions": [],
            "added_sessions": [],
            "risk_level": "low",
            "muscle_set_delta": {},
            "to_plan": {"weekly_volume_by_muscle": {}},
        },
        recommend_progression_action=lambda **_: {
            "action": "hold",
            "reason": "under_target_without_high_fatigue",
            "stimulus_fatigue_response": progression_snapshot,
        },
        humanize_progression_reason=lambda *_args, **_kwargs: "Hold",
        derive_readiness_score=lambda **_: 63,
        recommend_phase_transition=lambda **kwargs: {"next_phase": kwargs["current_phase"], "reason": "continue"},
        humanize_phase_transition_reason=lambda *_args, **_kwargs: "Continue",
        recommend_specialization_adjustments=lambda **_: {
            "focus_muscles": [],
            "focus_adjustments": {},
            "donor_adjustments": {},
            "uncompensated_added_sets": 0,
        },
        summarize_program_media_and_warmups=lambda *_args, **_kwargs: {
            "total_exercises": 0,
            "video_linked_exercises": 0,
            "video_coverage_pct": 0.0,
            "sample_warmups": [],
        },
    )

    coaching_state_step = next(
        step for step in preview["decision_trace"]["steps"] if step.get("decision") == "canonical_coaching_state"
    )
    progression_step = next(
        step for step in preview["decision_trace"]["steps"] if step.get("decision") == "progression"
    )

    assert coaching_state_step["result"]["stimulus_fatigue_response_source"] == "coaching_state.stimulus_fatigue_response"
    assert coaching_state_step["result"]["stimulus_fatigue_response"] == canonical_snapshot
    assert preview["progression"]["stimulus_fatigue_response"] == progression_snapshot
    assert progression_step["result"]["stimulus_fatigue_response"] == progression_snapshot
    assert progression_step["result"]["stimulus_fatigue_response"] != canonical_snapshot


def test_recommend_coach_intelligence_preview_ignores_legacy_preview_context_fields_without_canonical_state() -> None:
    captured: dict[str, object] = {}
    captured_phase_kwargs: dict[str, object] = {}

    def _derive_readiness_score(**kwargs: object) -> int:
        captured.update(kwargs)
        return 48

    def _recommend_phase_transition(**kwargs: object) -> dict[str, object]:
        captured_phase_kwargs.update(kwargs)
        return {"next_phase": kwargs["current_phase"], "reason": "continue"}

    preview = recommend_coach_intelligence_preview(
        template_id="full_body_v1",
        context={
            "program_template": {},
            "user_profile": {},
            "readiness_state": {
                "sleep_quality": 1,
                "stress_level": 5,
                "pain_flags": ["legacy_flag"],
            },
            "latest_mesocycle": {
                "authored_sequence_complete": True,
                "phase_transition_pending": True,
                "phase_transition_reason": "legacy_transition",
                "post_authored_behavior": "legacy_hold",
            },
        },
        preview_request={
            "from_days": 3,
            "to_days": 3,
            "completion_pct": 90,
            "adherence_score": 4,
            "soreness_level": "mild",
            "current_phase": "accumulation",
            "weeks_in_phase": 2,
        },
        rule_set=None,
        evaluate_schedule_adaptation=lambda **_: {
            "from_days": 3,
            "to_days": 3,
            "kept_sessions": [],
            "dropped_sessions": [],
            "added_sessions": [],
            "risk_level": "low",
            "muscle_set_delta": {},
            "to_plan": {"weekly_volume_by_muscle": {}},
        },
        recommend_progression_action=lambda **_: {"action": "hold", "reason": "maintain"},
        humanize_progression_reason=lambda *_args, **_kwargs: "Hold",
        derive_readiness_score=_derive_readiness_score,
        recommend_phase_transition=_recommend_phase_transition,
        humanize_phase_transition_reason=lambda *_args, **_kwargs: "Continue",
        recommend_specialization_adjustments=lambda **_: {
            "focus_muscles": [],
            "focus_adjustments": {},
            "donor_adjustments": {},
            "uncompensated_added_sets": 0,
        },
        summarize_program_media_and_warmups=lambda *_args, **_kwargs: {
            "total_exercises": 0,
            "video_linked_exercises": 0,
            "video_coverage_pct": 0.0,
            "sample_warmups": [],
        },
    )

    coaching_state_step = next(
        step for step in preview["decision_trace"]["steps"] if step.get("decision") == "canonical_coaching_state"
    )
    assert captured["sleep_quality"] is None
    assert captured["stress_level"] is None
    assert captured["pain_flags"] == []
    assert captured_phase_kwargs["authored_sequence_complete"] is False
    assert captured_phase_kwargs["phase_transition_pending"] is False
    assert captured_phase_kwargs["phase_transition_reason"] is None
    assert captured_phase_kwargs["post_authored_behavior"] is None
    assert coaching_state_step["result"]["readiness_source"] == "unavailable"
    assert coaching_state_step["result"]["mesocycle_source"] == "unavailable"


def test_recommend_coach_intelligence_preview_traces_stimulus_fatigue_response_snapshot() -> None:
    preview = recommend_coach_intelligence_preview(
        template_id="full_body_v1",
        context={"program_template": {}, "user_profile": {}},
        preview_request={
            "from_days": 5,
            "to_days": 3,
            "completion_pct": 90,
            "adherence_score": 4,
            "soreness_level": "mild",
            "average_rpe": 8.0,
            "current_phase": "accumulation",
            "weeks_in_phase": 3,
            "stagnation_weeks": 2,
        },
        rule_set=None,
        evaluate_schedule_adaptation=lambda **_: {
            "from_days": 5,
            "to_days": 3,
            "kept_sessions": [],
            "dropped_sessions": [],
            "added_sessions": [],
            "risk_level": "low",
            "muscle_set_delta": {},
            "to_plan": {"weekly_volume_by_muscle": {}},
        },
        recommend_progression_action=lambda **_: {
            "action": "hold",
            "reason": "under_target_without_high_fatigue",
            "load_scale": 1.0,
            "set_delta": 0,
            "stimulus_fatigue_response": {
                "stimulus_quality": "moderate",
                "fatigue_cost": "moderate",
                "recoverability": "moderate",
                "progression_eligibility": False,
                "deload_pressure": "moderate",
                "substitution_pressure": "low",
            },
        },
        humanize_progression_reason=lambda *_args, **_kwargs: "Hold",
        derive_readiness_score=lambda **_: 63,
        recommend_phase_transition=lambda **kwargs: {"next_phase": kwargs["current_phase"], "reason": "continue"},
        humanize_phase_transition_reason=lambda *_args, **_kwargs: "Continue",
        recommend_specialization_adjustments=lambda **_: {
            "focus_muscles": [],
            "focus_adjustments": {},
            "donor_adjustments": {},
            "uncompensated_added_sets": 0,
        },
        summarize_program_media_and_warmups=lambda *_args, **_kwargs: {
            "total_exercises": 0,
            "video_linked_exercises": 0,
            "video_coverage_pct": 0.0,
            "sample_warmups": [],
        },
    )

    progression_step = next(
        step for step in preview["decision_trace"]["steps"] if step.get("decision") == "progression"
    )

    assert progression_step["result"]["stimulus_fatigue_response"]["deload_pressure"] == "moderate"
    assert progression_step["result"]["stimulus_fatigue_response"]["progression_eligibility"] is False


def test_timeline_helpers_build_entries_and_clamp_limits() -> None:
    class _Row:
        id = "rec_1"
        recommendation_type = "coach_preview"
        status = "previewed"
        template_id = "full_body_v1"
        current_phase = "accumulation"
        recommended_phase = "intensification"
        progression_action = "hold"
        recommendation_payload = {
            "phase_transition": {"reason": "continue_accumulation"},
            "specialization": {"focus_muscles": ["chest", ""]},
        }
        created_at = "2026-03-09T10:00:00"
        applied_at = None

    payload = build_coaching_recommendation_timeline_payload(
        [_Row()],
        humanize_phase_transition_reason=lambda *_args, **_kwargs: "Stay in accumulation.",
        humanize_progression_reason=lambda *_args, **_kwargs: "Hold load.",
        humanize_specialization_reason=lambda *_args, **_kwargs: "Focus chest.",
    )

    assert normalize_coaching_recommendation_timeline_limit(-5) == 1
    assert normalize_coaching_recommendation_timeline_limit(500) == 100
    assert payload["entries"][0]["rationale"] == "Stay in accumulation."
    assert payload["entries"][0]["focus_muscles"] == ["chest"]


def test_resolve_coaching_recommendation_rationale_prefers_existing_rationale() -> None:
    rationale = resolve_coaching_recommendation_rationale(
        {
            "progression": {"rationale": "Hold load."},
            "specialization": {"reason": "focus_chest"},
        },
        humanize_phase_transition_reason=lambda *_args, **_kwargs: "phase",
        humanize_progression_reason=lambda *_args, **_kwargs: "progression",
        humanize_specialization_reason=lambda *_args, **_kwargs: "specialization",
    )
    focus = extract_coaching_recommendation_focus_muscles(
        {"specialization": {"focus_muscles": ["lats", "", "rear_delts"]}}
    )

    assert rationale == "Hold load."
    assert focus == ["lats", "rear_delts"]


def test_build_applied_coaching_recommendation_response_finalizes_payload_and_response() -> None:
    result = build_applied_coaching_recommendation_response(
        payload_key="specialization",
        payload_value={"focus_muscles": ["lats"]},
        decision_payload={
            "status": "applied",
            "decision_trace": {
                "interpreter": "interpret_coach_specialization_apply_decision",
                "outcome": {"status": "applied"},
            },
        },
        applied_recommendation_id="applied_123",
    )

    assert result["recommendation_payload"]["specialization"]["focus_muscles"] == ["lats"]
    assert result["recommendation_payload"]["decision_trace"]["outcome"]["applied_recommendation_id"] == "applied_123"
    assert result["response_payload"]["applied_recommendation_id"] == "applied_123"


def test_build_applied_coaching_recommendation_record_values_shapes_insert_payload() -> None:
    values = build_applied_coaching_recommendation_record_values(
        user_id="user_123",
        applied_at="2026-03-09T12:00:00",
        record_fields={"template_id": "full_body_v1", "recommendation_type": "phase_decision"},
    )

    assert values["user_id"] == "user_123"
    assert values["recommendation_payload"] == {}
    assert values["template_id"] == "full_body_v1"


def test_prepare_applied_coaching_recommendation_commit_runtime_shapes_record_and_payload_runtime() -> None:
    runtime = prepare_applied_coaching_recommendation_commit_runtime(
        user_id="user_123",
        applied_at="2026-03-09T12:00:00",
        record_fields={"template_id": "full_body_v1", "recommendation_type": "phase_decision"},
        payload_key="phase_transition",
        payload_value={"next_phase": "deload"},
        decision_payload={"status": "applied", "decision_trace": {"outcome": {"status": "applied"}}},
    )

    assert runtime["record_values"]["user_id"] == "user_123"
    assert runtime["record_values"]["template_id"] == "full_body_v1"
    assert runtime["payload_runtime"]["payload_key"] == "phase_transition"
    assert runtime["payload_runtime"]["payload_value"]["next_phase"] == "deload"
    assert runtime["decision_trace"]["interpreter"] == "prepare_applied_coaching_recommendation_commit_runtime"


def test_finalize_applied_coaching_recommendation_commit_runtime_builds_response_and_recommendation_payload() -> None:
    prepared_runtime = {
        "record_values": {
            "user_id": "user_123",
            "recommendation_payload": {},
            "applied_at": "2026-03-09T12:00:00",
            "template_id": "full_body_v1",
            "recommendation_type": "specialization_decision",
        },
        "payload_runtime": {
            "payload_key": "specialization",
            "payload_value": {"focus_muscles": ["lats"]},
            "decision_payload": {
                "status": "applied",
                "decision_trace": {"outcome": {"status": "applied"}},
            },
        },
    }

    finalized = finalize_applied_coaching_recommendation_commit_runtime(
        prepared_runtime=prepared_runtime,
        applied_recommendation_id="applied_123",
    )

    assert finalized["recommendation_payload"]["specialization"]["focus_muscles"] == ["lats"]
    assert finalized["response_payload"]["applied_recommendation_id"] == "applied_123"


def test_prepare_coaching_apply_decision_runtime_routes_phase_inputs() -> None:
    runtime = prepare_coaching_apply_decision_runtime(
        decision_kind="phase",
        source_runtime={
            "recommendation_id": "rec_1",
            "recommendation_payload": {"phase_transition": {"next_phase": "deload"}},
            "recommended_phase": "intensification",
            "template_id": "full_body_v1",
            "current_phase": "accumulation",
            "progression_action": "hold",
        },
        confirm=True,
        prepare_phase_runtime=lambda **kwargs: {
            "kind": "phase",
            "confirm": kwargs["confirm"],
            "fallback_next_phase": kwargs["fallback_next_phase"],
        },
        prepare_specialization_runtime=lambda **kwargs: {"kind": "specialization", "confirm": kwargs["confirm"]},
    )

    assert runtime["decision_kind"] == "phase"
    assert runtime["runtime"]["kind"] == "phase"
    assert runtime["runtime"]["fallback_next_phase"] == "intensification"
    assert runtime["decision_trace"]["interpreter"] == "prepare_coaching_apply_decision_runtime"


def test_prepare_coaching_apply_decision_runtime_routes_specialization_inputs() -> None:
    runtime = prepare_coaching_apply_decision_runtime(
        decision_kind="specialization",
        source_runtime={
            "recommendation_id": "rec_2",
            "recommendation_payload": {"specialization": {"focus_muscles": ["lats"]}},
            "recommended_phase": "intensification",
            "template_id": "full_body_v1",
            "current_phase": "accumulation",
            "progression_action": "progress",
        },
        confirm=False,
        prepare_phase_runtime=lambda **kwargs: {"kind": "phase", "confirm": kwargs["confirm"]},
        prepare_specialization_runtime=lambda **kwargs: {
            "kind": "specialization",
            "confirm": kwargs["confirm"],
            "recommended_phase": kwargs["recommended_phase"],
        },
    )

    assert runtime["decision_kind"] == "specialization"
    assert runtime["runtime"]["kind"] == "specialization"
    assert runtime["runtime"]["recommended_phase"] == "intensification"


def test_prepare_coaching_apply_commit_runtime_uses_decision_kind_payload_mapping() -> None:
    commit_runtime = prepare_coaching_apply_commit_runtime(
        decision_kind="phase",
        user_id="user_123",
        applied_at="2026-03-09T12:00:00",
        apply_runtime={
            "record_fields": {"template_id": "full_body_v1", "recommendation_type": "phase_decision"},
            "payload_value": {"next_phase": "deload"},
            "decision_payload": {"status": "applied"},
        },
    )

    assert commit_runtime["record_values"]["user_id"] == "user_123"
    assert commit_runtime["payload_runtime"]["payload_key"] == "phase_transition"
    assert commit_runtime["payload_runtime"]["payload_value"]["next_phase"] == "deload"


def test_prepare_coaching_apply_commit_runtime_rejects_unsupported_kind() -> None:
    try:
        prepare_coaching_apply_commit_runtime(
            decision_kind="unsupported",
            user_id="user_123",
            applied_at="2026-03-09T12:00:00",
            apply_runtime={
                "record_fields": {"template_id": "full_body_v1"},
                "payload_value": {},
                "decision_payload": {},
            },
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Unsupported coaching apply decision kind" in str(exc)


def test_prepare_coaching_apply_route_runtime_returns_preflight_response_payload() -> None:
    route_runtime = prepare_coaching_apply_route_runtime(
        decision_kind="phase",
        source_runtime={"recommendation_id": "rec_1", "recommendation_payload": {"phase_transition": {"next_phase": "deload"}}},
        confirm=False,
        user_id="user_123",
        applied_at="2026-03-09T12:00:00",
        prepare_apply_decision_runtime=lambda **kwargs: {
            "decision_kind": kwargs["decision_kind"],
            "runtime": {"decision_payload": {"status": "confirmation_required"}},
        },
        prepare_apply_commit_runtime=lambda **kwargs: {"record_values": {"user_id": kwargs["user_id"]}},
    )

    assert route_runtime["response_payload"]["status"] == "confirmation_required"
    assert "commit_runtime" not in route_runtime


def test_prepare_coaching_apply_route_runtime_returns_commit_runtime_on_confirm() -> None:
    route_runtime = prepare_coaching_apply_route_runtime(
        decision_kind="specialization",
        source_runtime={"recommendation_id": "rec_2", "recommendation_payload": {"specialization": {"focus_muscles": ["lats"]}}},
        confirm=True,
        user_id="user_123",
        applied_at="2026-03-09T12:00:00",
        prepare_apply_decision_runtime=lambda **kwargs: {
            "decision_kind": kwargs["decision_kind"],
            "runtime": {
                "decision_payload": {"status": "applied"},
                "record_fields": {"template_id": "full_body_v1"},
                "payload_value": {"focus_muscles": ["lats"]},
            },
        },
        prepare_apply_commit_runtime=lambda **kwargs: {
            "record_values": {"user_id": kwargs["user_id"], "recommendation_payload": {}},
            "payload_runtime": {"payload_key": "specialization"},
        },
    )

    assert route_runtime["response_payload"]["status"] == "applied"
    assert route_runtime["commit_runtime"]["record_values"]["user_id"] == "user_123"


def test_prepare_coaching_apply_route_finalize_runtime_returns_preflight_payload_without_recommendation_payload() -> None:
    finalized = prepare_coaching_apply_route_finalize_runtime(
        route_runtime={"response_payload": {"status": "confirmation_required"}},
    )

    assert finalized["response_payload"]["status"] == "confirmation_required"
    assert finalized["recommendation_payload"] is None
    assert finalized["decision_trace"]["interpreter"] == "prepare_coaching_apply_route_finalize_runtime"


def test_prepare_coaching_apply_route_finalize_runtime_finalizes_commit_payloads() -> None:
    finalized = prepare_coaching_apply_route_finalize_runtime(
        route_runtime={
            "response_payload": {"status": "applied"},
            "commit_runtime": {
                "payload_runtime": {
                    "payload_key": "phase_transition",
                    "payload_value": {"next_phase": "deload"},
                    "decision_payload": {
                        "status": "applied",
                        "decision_trace": {"outcome": {"status": "applied"}},
                    },
                }
            },
        },
        applied_recommendation_id="applied_123",
    )

    assert finalized["response_payload"]["status"] == "applied"
    assert finalized["response_payload"]["applied_recommendation_id"] == "applied_123"
    assert finalized["recommendation_payload"]["phase_transition"]["next_phase"] == "deload"


def test_prepare_coach_preview_decision_context_builds_training_state_and_context() -> None:
    result = prepare_coach_preview_decision_context(
        user_name="Coach User",
        split_preference="full_body",
        template={"sessions": []},
        latest_plan={"id": "plan_1"},
        recent_workout_logs=[{"workout_id": "w1"}],
        selected_program_id="full_body_v1",
        nutrition_phase=None,
        available_equipment=None,
        build_plan_decision_training_state=lambda **kwargs: {
            "program_id": kwargs["selected_program_id"],
            "log_count": len(kwargs["recent_workout_logs"]),
        },
        build_coach_preview_context=lambda **kwargs: {
            "split_preference": kwargs["split_preference"],
            "nutrition_phase": kwargs["nutrition_phase"],
            "equipment": kwargs["available_equipment"],
            "state_program": kwargs["user_training_state"]["program_id"],
        },
    )

    assert result["training_state"]["program_id"] == "full_body_v1"
    assert result["training_state"]["log_count"] == 1
    assert result["context"]["nutrition_phase"] == "maintenance"
    assert result["context"]["equipment"] == []
    assert result["context"]["state_program"] == "full_body_v1"
    assert result["decision_trace"]["interpreter"] == "prepare_coach_preview_decision_context"


def test_recommend_coach_intelligence_preview_surfaces_authored_sequence_completion() -> None:
    captured_phase_kwargs: dict[str, object] = {}

    def _recommend_phase_transition(**kwargs: object) -> dict[str, object]:
        captured_phase_kwargs.update(kwargs)
        return {
            "next_phase": kwargs["current_phase"],
            "reason": "authored_sequence_complete",
            "transition_pending": kwargs["phase_transition_pending"],
            "recommended_action": "rotate_program",
            "post_authored_behavior": kwargs["post_authored_behavior"],
        }

    preview = recommend_coach_intelligence_preview(
        template_id="adaptive_full_body_gold_v0_1",
        context={
            "program_template": {},
            "user_profile": {},
            "coaching_state": {
                "mesocycle": {
                    "authored_sequence_complete": True,
                    "phase_transition_pending": True,
                    "phase_transition_reason": "authored_sequence_complete",
                    "post_authored_behavior": "hold_last_authored_week",
                }
            },
        },
        preview_request={
            "from_days": 3,
            "to_days": 3,
            "completion_pct": 92,
            "adherence_score": 4,
            "soreness_level": "mild",
            "current_phase": "intensification",
            "weeks_in_phase": 4,
            "stagnation_weeks": 0,
        },
        rule_set=None,
        evaluate_schedule_adaptation=lambda **_: {
            "from_days": 3,
            "to_days": 3,
            "kept_sessions": [],
            "dropped_sessions": [],
            "added_sessions": [],
            "risk_level": "low",
            "muscle_set_delta": {},
            "to_plan": {"weekly_volume_by_muscle": {}},
        },
        recommend_progression_action=lambda **_: {"action": "hold", "reason": "maintain"},
        humanize_progression_reason=lambda *_args, **_kwargs: "Hold",
        derive_readiness_score=lambda **_: 70,
        recommend_phase_transition=_recommend_phase_transition,
        humanize_phase_transition_reason=lambda *_args, **_kwargs: "The authored mesocycle is complete. Rotate to a fresh next step.",
        recommend_specialization_adjustments=lambda **_: {
            "focus_muscles": [],
            "focus_adjustments": {},
            "donor_adjustments": {},
            "uncompensated_added_sets": 0,
        },
        summarize_program_media_and_warmups=lambda *_args, **_kwargs: {
            "total_exercises": 0,
            "video_linked_exercises": 0,
            "video_coverage_pct": 0.0,
            "sample_warmups": [],
        },
    )

    assert captured_phase_kwargs["authored_sequence_complete"] is True
    assert captured_phase_kwargs["phase_transition_pending"] is True
    assert captured_phase_kwargs["post_authored_behavior"] == "hold_last_authored_week"
    assert preview["phase_transition"]["reason"] == "authored_sequence_complete"
    assert preview["phase_transition"]["transition_pending"] is True
    assert preview["phase_transition"]["recommended_action"] == "rotate_program"
