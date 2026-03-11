from datetime import UTC, datetime

import pytest

from core_engine.decision_program_recommendation import (
    build_program_recommendation_payload,
    build_program_switch_payload,
    humanize_program_reason,
    prepare_profile_program_recommendation_inputs,
    prepare_profile_program_recommendation_route_runtime,
    prepare_program_recommendation_runtime,
    prepare_program_switch_runtime,
    recommend_program_selection,
    resolve_program_recommendation_candidates,
)


def test_recommend_program_selection_returns_structured_trace_for_adaptation_upgrade() -> None:
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
    assert decision["decision_trace"]["interpreter"] == "recommend_program_selection"


def test_resolve_program_recommendation_candidates_orders_compatible_programs() -> None:
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

    assert runtime["recommendation_inputs"]["current_program_id"] == "ppl_v1"
    assert runtime["recommendation_runtime"]["decision"]["recommended_program_id"] == "upper_lower_v1"
    assert runtime["decision_trace"]["interpreter"] == "prepare_profile_program_recommendation_route_runtime"


def test_build_program_switch_payload_and_runtime_cover_confirmation_states() -> None:
    decision = {
        "recommended_program_id": "upper_lower_v1",
        "reason": "days_adaptation_upgrade",
        "rationale": humanize_program_reason("days_adaptation_upgrade"),
        "decision_trace": {"interpreter": "recommend_program_selection"},
    }
    candidate_resolution_trace = {"interpreter": "resolve_program_recommendation_candidates"}

    payload = build_program_switch_payload(
        current_program_id="ppl_v1",
        target_program_id="upper_lower_v1",
        confirm=False,
        decision=decision,
        candidate_resolution_trace=candidate_resolution_trace,
    )
    assert payload["status"] == "confirmation_required"

    runtime = prepare_program_switch_runtime(
        current_program_id="ppl_v1",
        target_program_id="upper_lower_v1",
        confirm=True,
        compatible_program_ids=["ppl_v1", "upper_lower_v1"],
        decision=decision,
        candidate_resolution_trace=candidate_resolution_trace,
    )
    assert runtime["should_apply"] is True
    assert runtime["response_payload"]["status"] == "switched"


def test_prepare_program_switch_runtime_rejects_incompatible_target() -> None:
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
    assert payload["decision_trace"]["candidate_resolution"]["interpreter"] == "resolve_program_recommendation_candidates"


def test_recommend_program_selection_rotates_when_authored_sequence_is_complete() -> None:
    decision = recommend_program_selection(
        current_program_id="adaptive_full_body_gold_v0_1",
        compatible_program_summaries=[
            {"id": "adaptive_full_body_gold_v0_1", "split": "full_body", "days_supported": [3], "session_count": 3},
            {"id": "full_body_v1", "split": "full_body", "days_supported": [3], "session_count": 3},
        ],
        days_available=3,
        latest_adherence_score=4,
        latest_plan_payload={
            "mesocycle": {
                "week_index": 10,
                "trigger_weeks_effective": 10,
                "authored_sequence_complete": True,
                "phase_transition_pending": True,
                "phase_transition_reason": "authored_sequence_complete",
                "post_authored_behavior": "hold_last_authored_week",
            }
        },
    )

    assert decision["recommended_program_id"] == "full_body_v1"
    assert decision["reason"] == "mesocycle_complete_rotate"
    assert decision["decision_trace"]["selected_program_id"] == "full_body_v1"
