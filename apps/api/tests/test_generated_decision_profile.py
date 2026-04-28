from __future__ import annotations

from app.generated_decision_profile import build_generated_decision_profile


def test_missing_optional_fields_use_safe_defaults() -> None:
    profile = build_generated_decision_profile(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=3,
        session_time_budget_minutes=None,
        temporary_duration_minutes=None,
        near_failure_tolerance=None,
        weak_areas=[],
        movement_restrictions=[],
        equipment_profile=[],
        onboarding_answers={},
        training_state={},
    )

    assert profile.generated_mode == "normal_full_body"
    assert profile.recovery_modifier == "standard"
    assert profile.session_time_band == "standard"
    assert "default_session_time_band_standard" in profile.decision_trace.defaults_applied
    assert profile.decision_trace.insufficient_data_avoided is True


def test_missing_days_defaults_to_three() -> None:
    profile = build_generated_decision_profile(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=None,
        session_time_budget_minutes=60,
        temporary_duration_minutes=None,
        near_failure_tolerance="moderate",
        weak_areas=[],
        movement_restrictions=[],
        equipment_profile=["dumbbell"],
        onboarding_answers={},
        training_state={},
    )
    assert profile.target_days == 3


def test_low_session_time_selects_low_time_mode() -> None:
    profile = build_generated_decision_profile(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=3,
        session_time_budget_minutes=40,
        temporary_duration_minutes=None,
        near_failure_tolerance="moderate",
        weak_areas=[],
        movement_restrictions=[],
        equipment_profile=["dumbbell"],
        onboarding_answers={},
        training_state={},
    )
    assert profile.generated_mode == "low_time_full_body"


def test_low_recovery_selects_low_recovery_mode() -> None:
    profile = build_generated_decision_profile(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=3,
        session_time_budget_minutes=60,
        temporary_duration_minutes=None,
        near_failure_tolerance="low",
        weak_areas=[],
        movement_restrictions=[],
        equipment_profile=["dumbbell"],
        onboarding_answers={},
        training_state={},
    )
    assert profile.generated_mode == "low_recovery_full_body"


def test_detrained_user_selects_comeback_reentry() -> None:
    profile = build_generated_decision_profile(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=3,
        session_time_budget_minutes=60,
        temporary_duration_minutes=None,
        near_failure_tolerance="moderate",
        weak_areas=[],
        movement_restrictions=[],
        equipment_profile=["dumbbell"],
        onboarding_answers={"trained_consistently_last_4_weeks": False},
        training_state={},
    )
    assert profile.generated_mode == "comeback_reentry"
    assert profile.reentry_required is True


def test_normal_user_selects_normal_mode() -> None:
    profile = build_generated_decision_profile(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=3,
        session_time_budget_minutes=60,
        temporary_duration_minutes=None,
        near_failure_tolerance="moderate",
        weak_areas=["chest"],
        movement_restrictions=["overhead_pressing"],
        equipment_profile=["barbell", "bench", "machine", "cable"],
        onboarding_answers={"trained_consistently_last_4_weeks": True, "goal_mode": "hypertrophy"},
        training_state={},
    )
    assert profile.generated_mode == "normal_full_body"


def test_weakpoints_are_normalized_deduped_and_capped() -> None:
    profile = build_generated_decision_profile(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=3,
        session_time_budget_minutes=60,
        temporary_duration_minutes=None,
        near_failure_tolerance="moderate",
        weak_areas=["biceps", "triceps", "shoulders", "side_delts"],
        movement_restrictions=[],
        equipment_profile=["dumbbell"],
        onboarding_answers={},
        training_state={},
    )
    assert profile.weakpoint_targets == ["arms", "delts"]


def test_gender_does_not_change_mode_or_family() -> None:
    base_kwargs = dict(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=3,
        session_time_budget_minutes=60,
        temporary_duration_minutes=None,
        near_failure_tolerance="moderate",
        weak_areas=["chest"],
        movement_restrictions=[],
        equipment_profile=["dumbbell", "bench"],
        training_state={},
    )
    male = build_generated_decision_profile(onboarding_answers={"gender": "male"}, **base_kwargs)
    female = build_generated_decision_profile(onboarding_answers={"gender": "female"}, **base_kwargs)
    assert male.generated_mode == female.generated_mode
    assert male.path_family == female.path_family


def test_height_weight_do_not_change_mode_or_family() -> None:
    base_kwargs = dict(
        selected_program_id="full_body_v1",
        program_selection_mode="generated",
        days_available=3,
        session_time_budget_minutes=60,
        temporary_duration_minutes=None,
        near_failure_tolerance="moderate",
        weak_areas=["chest"],
        movement_restrictions=[],
        equipment_profile=["dumbbell", "bench"],
        training_state={},
    )
    lighter = build_generated_decision_profile(onboarding_answers={"weight": 60, "height": 160}, **base_kwargs)
    heavier = build_generated_decision_profile(onboarding_answers={"weight": 110, "height": 195}, **base_kwargs)
    assert lighter.generated_mode == heavier.generated_mode
    assert lighter.path_family == heavier.path_family


def test_insufficient_data_default_only_for_truly_incomplete_inputs() -> None:
    profile = build_generated_decision_profile(
        selected_program_id=None,
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
    assert profile.generated_mode == "insufficient_data_default"
    assert profile.decision_trace.selected_mode_reason == "insufficient_or_contradictory_data"


def test_decision_trace_records_defaults_and_selected_mode() -> None:
    profile = build_generated_decision_profile(
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
    assert profile.decision_trace.selected_mode_reason
