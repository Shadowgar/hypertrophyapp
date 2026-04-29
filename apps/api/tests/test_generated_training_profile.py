from __future__ import annotations

from app.generated_training_profile import build_generated_training_profile


def test_generated_training_profile_sparse_defaults_still_valid() -> None:
    profile = build_generated_training_profile(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=None,
        session_time_budget_minutes=None,
        temporary_duration_minutes=None,
        near_failure_tolerance=None,
        weak_areas=None,
        movement_restrictions=None,
        equipment_profile=None,
        onboarding_answers={},
        training_state={},
    )
    assert profile.path_family == "generated"
    assert profile.runtime_active.target_days == 3
    assert profile.runtime_active.session_time_band == "standard"
    assert profile.runtime_active.recovery_modifier == "standard"
    assert "default_target_days_3" in profile.decision_trace.defaults_applied
    assert "phase3a.generated_training_profile_bridge_v1" in profile.decision_trace.rule_hits


def test_generated_training_profile_deterministic_for_same_inputs() -> None:
    kwargs = dict(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=3,
        session_time_budget_minutes=60,
        temporary_duration_minutes=None,
        near_failure_tolerance="moderate",
        weak_areas=["biceps", "side_delts", "biceps"],
        movement_restrictions=["overhead_pressing"],
        equipment_profile=["barbell", "bench", "dumbbell", "machine"],
        onboarding_answers={"goal_mode": "hypertrophy", "trained_consistently_last_4_weeks": True},
        training_state={"fatigue_state": {"recovery_state": "normal"}},
    )
    first = build_generated_training_profile(**kwargs)
    second = build_generated_training_profile(**kwargs)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_generated_training_profile_trace_includes_defaults_missing_rule_hits_trace_only_fields() -> None:
    profile = build_generated_training_profile(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=None,
        session_time_budget_minutes=None,
        temporary_duration_minutes=None,
        near_failure_tolerance=None,
        weak_areas=[],
        movement_restrictions=[],
        equipment_profile=[],
        onboarding_answers={},
        training_state={},
    )
    assert profile.decision_trace.defaults_applied
    assert profile.decision_trace.missing_fields
    assert profile.decision_trace.rule_hits
    assert "starting_rir" in profile.decision_trace.trace_only_fields
    assert "progression_mode" in profile.decision_trace.trace_only_fields


def test_trace_only_controls_not_runtime_wired_in_phase3a() -> None:
    profile = build_generated_training_profile(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=3,
        session_time_budget_minutes=60,
        temporary_duration_minutes=None,
        near_failure_tolerance="moderate",
        weak_areas=["chest"],
        movement_restrictions=["overhead_pressing"],
        equipment_profile=["barbell", "bench", "dumbbell", "machine"],
        onboarding_answers={"goal_mode": "hypertrophy"},
        training_state={},
    )
    assert profile.runtime_active.model_fields_set == {
        "target_days",
        "session_time_band",
        "recovery_modifier",
        "weakpoint_targets",
        "movement_restriction_flags",
        "generated_mode",
    }
    assert profile.trace_only_controls.starting_rir >= 1
    assert profile.trace_only_controls.high_fatigue_cap >= 1
