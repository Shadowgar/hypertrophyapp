from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from core_engine import (
    build_coach_preview_context,
    build_guide_programs_payload,
    build_program_day_guide_payload,
    build_program_exercise_guide_payload,
    build_program_guide_payload,
    format_program_display_name,
    prepare_coach_preview_runtime_inputs,
    prepare_generation_template_runtime,
    prepare_generate_week_plan_runtime_inputs,
    prepare_generate_week_review_lookup_runtime,
    prepare_generate_week_scheduler_runtime,
    prepare_generate_week_finalize_runtime,
    prepare_frequency_adaptation_runtime_inputs,
    prepare_frequency_adaptation_decision_runtime,
    prepare_plan_generation_decision_runtime,
    resolve_program_display_name,
    resolve_program_guide_summary,
    resolve_optional_rule_set,
    resolve_onboarding_program_id,
    resolve_frequency_adaptation_request_context,
    resolve_generation_template_choice,
    resolve_program_exercise_guide,
    resolve_week_generation_runtime_inputs,
    serialize_recent_training_history,
)


def test_generation_template_runtime_exports_come_from_generated_week_owner() -> None:
    assert prepare_generation_template_runtime.__module__ == "core_engine.decision_generated_week"
    assert resolve_generation_template_choice.__module__ == "core_engine.decision_generated_week"


def test_resolve_generation_template_choice_falls_back_to_first_viable_candidate() -> None:
    unusable_template = {
        "id": "ppl_v1",
        "sessions": [
            {
                "name": "Push",
                "exercises": [
                    {
                        "id": "bench",
                        "name": "Bench Press",
                        "sets": 3,
                        "rep_range": [8, 10],
                        "start_weight": 60,
                        "equipment_tags": ["barbell"],
                        "substitution_candidates": [],
                    }
                ],
            }
        ],
    }
    fallback_template = {
        "id": "upper_lower_v1",
        "sessions": [
            {
                "name": "Upper",
                "exercises": [
                    {
                        "id": "db_press",
                        "name": "DB Press",
                        "sets": 3,
                        "rep_range": [8, 10],
                        "start_weight": 25,
                        "equipment_tags": ["dumbbell"],
                        "substitution_candidates": [],
                    }
                ],
            }
        ],
    }

    selection = resolve_generation_template_choice(
        explicit_template_id=None,
        explicit_template=None,
        profile_template_id="ppl_v1",
        split_preference="ppl",
        days_available=3,
        nutrition_phase="maintenance",
        available_equipment=["dumbbell"],
        candidate_summaries=[
            {"id": "ppl_v1", "split": "ppl", "days_supported": [3]},
            {"id": "upper_lower_v1", "split": "ppl", "days_supported": [3]},
        ],
        loaded_candidate_templates={
            "ppl_v1": unusable_template,
            "upper_lower_v1": fallback_template,
        },
    )

    assert selection["selected_template_id"] == "upper_lower_v1"
    assert selection["selected_template"]["id"] == "upper_lower_v1"
    assert selection["decision_trace"]["reason"] == "first_viable_candidate"


def test_prepare_generation_template_runtime_loads_explicit_template() -> None:
    template = {"id": "full_body_v1", "sessions": []}

    runtime = prepare_generation_template_runtime(
        explicit_template_id="full_body_v1",
        profile_template_id="ppl_v1",
        split_preference="full_body",
        days_available=3,
        nutrition_phase="maintenance",
        available_equipment=["barbell"],
        candidate_summaries=[],
        load_template=lambda template_id: template if template_id == "full_body_v1" else {},
    )

    assert runtime["selected_template_id"] == "full_body_v1"
    assert runtime["selected_template"] == template
    assert runtime["decision_trace"]["selected_template_id"] == "full_body_v1"


def test_prepare_generation_template_runtime_skips_unloadable_candidates() -> None:
    templates = {
        "upper_lower_v1": {
            "id": "upper_lower_v1",
            "sessions": [
                {
                    "name": "Upper",
                    "exercises": [
                        {
                            "id": "db_press",
                            "name": "DB Press",
                            "sets": 3,
                            "rep_range": [8, 10],
                            "start_weight": 25,
                            "equipment_tags": ["dumbbell"],
                            "substitution_candidates": [],
                        }
                    ],
                }
            ],
        }
    }

    def load_template(template_id: str) -> dict[str, Any]:
        if template_id == "broken_template":
            raise FileNotFoundError(template_id)
        return templates[template_id]

    runtime = prepare_generation_template_runtime(
        explicit_template_id=None,
        profile_template_id="broken_template",
        split_preference="ppl",
        days_available=3,
        nutrition_phase="maintenance",
        available_equipment=["dumbbell"],
        candidate_summaries=[
            {"id": "broken_template", "split": "ppl", "days_supported": [3]},
            {"id": "upper_lower_v1", "split": "ppl", "days_supported": [3]},
        ],
        load_template=load_template,
    )

    assert runtime["selected_template_id"] == "upper_lower_v1"
    assert runtime["selected_template"]["id"] == "upper_lower_v1"
    assert runtime["decision_trace"]["reason"] == "first_viable_candidate"


def test_resolve_program_guide_summary_returns_matching_summary() -> None:
    summary = resolve_program_guide_summary(
        program_id="full_body_v1",
        available_program_summaries=[
            {"id": "ppl_v1", "name": "PPL"},
            {"id": "full_body_v1", "name": "Full Body"},
        ],
    )
    assert summary["id"] == "full_body_v1"


def test_resolve_program_guide_summary_raises_when_missing() -> None:
    with pytest.raises(FileNotFoundError):
        resolve_program_guide_summary(
            program_id="missing_v1",
            available_program_summaries=[{"id": "full_body_v1"}],
        )


def test_resolve_program_display_name_prefers_summary_name_then_fallback() -> None:
    assert (
        resolve_program_display_name(
            program_id="full_body_v1",
            available_program_summaries=[{"id": "full_body_v1", "name": "Full Body Gold"}],
        )
        == "Full Body Gold"
    )
    assert (
        resolve_program_display_name(
            program_id="upper_lower_v2",
            available_program_summaries=[{"id": "full_body_v1", "name": "Full Body Gold"}],
        )
        == "Upper Lower V2"
    )


def test_resolve_optional_rule_set_returns_none_for_missing_or_invalid_template() -> None:
    assert (
        resolve_optional_rule_set(
            template_id=None,
            resolve_linked_program_id=lambda template_id: template_id,
            load_rule_set=lambda linked_id: {"id": linked_id},
        )
        is None
    )
    assert (
        resolve_optional_rule_set(
            template_id="missing_template",
            resolve_linked_program_id=lambda template_id: template_id,
            load_rule_set=lambda linked_id: (_ for _ in ()).throw(FileNotFoundError(linked_id)),
        )
        is None
    )


def test_resolve_optional_rule_set_loads_linked_rule_set() -> None:
    loaded = resolve_optional_rule_set(
        template_id="full_body_v1",
        resolve_linked_program_id=lambda template_id: f"{template_id}_linked",
        load_rule_set=lambda linked_id: {"rule_set_id": linked_id},
    )
    assert loaded == {"rule_set_id": "full_body_v1_linked"}


def test_resolve_onboarding_program_id_uses_linked_program_resolver() -> None:
    onboarding_program_id = resolve_onboarding_program_id(
        template_id="full_body_v1",
        resolve_linked_program_id=lambda template_id: f"{template_id}_linked",
    )
    assert onboarding_program_id == "full_body_v1_linked"


def test_resolve_week_generation_runtime_inputs_prefers_canonical_training_state() -> None:
    today = date(2026, 3, 5)
    user_training_state = {
        "exercise_performance_history": [
            {
                "exercise_id": "bench",
                "performed_at": datetime.combine(today - timedelta(days=2), time(9, 0)),
                "set_index": 1,
                "reps": 8,
                "weight": 82.5,
                "rpe": 8.0,
            },
            {
                "exercise_id": "row",
                "performed_at": datetime.combine(today - timedelta(days=1), time(9, 0)),
                "set_index": 1,
                "reps": 10,
                "weight": 70.0,
                "rpe": 7.5,
            },
        ],
        "fatigue_state": {
            "soreness_by_muscle": {"chest": "severe", "back": "severe", "quads": "mild"},
        },
        "adherence_state": {
            "latest_adherence_score": 2,
        },
        "generation_state": {
            "prior_generated_weeks_by_program": {"full_body_v1": 2},
        },
    }

    runtime = resolve_week_generation_runtime_inputs(
        selected_template_id="full_body_v1",
        current_days_available=4,
        active_frequency_adaptation={"target_days": 3},
        user_training_state=user_training_state,
        history_rows=[],
        latest_soreness_entry=None,
        latest_checkin=None,
        prior_plans=[],
    )

    assert runtime["effective_days_available"] == 3
    assert len(runtime["history"]) == 2
    assert runtime["history"][0]["primary_exercise_id"] == "bench"
    assert runtime["soreness_by_muscle"] == {"chest": "severe", "back": "severe", "quads": "mild"}
    assert runtime["severe_soreness_count"] == 2
    assert runtime["latest_adherence_score"] == 2
    assert runtime["prior_generated_weeks"] == 2
    assert runtime["decision_trace"]["interpreter"] == "resolve_week_generation_runtime_inputs"
    assert runtime["decision_trace"]["outcome"]["effective_days_available"] == 3
    assert runtime["decision_trace"]["outcome"]["prior_generated_weeks"] == 2
    assert runtime["decision_trace"]["steps"][1]["result"]["soreness_source"] == "training_state"
    assert runtime["decision_trace"]["steps"][3]["result"]["source"] == "training_state"


def test_resolve_week_generation_runtime_inputs_derives_sfr_from_readiness_state() -> None:
    user_training_state = {
        "fatigue_state": {
            "soreness_by_muscle": {"chest": "severe", "back": "mild"},
            "session_rpe_avg": 9.1,
        },
        "adherence_state": {
            "latest_adherence_score": 3,
        },
        "readiness_state": {
            "sleep_quality": 2,
            "stress_level": 4,
            "pain_flags": ["shoulder_irritation"],
        },
    }

    runtime = resolve_week_generation_runtime_inputs(
        selected_template_id="full_body_v1",
        current_days_available=4,
        active_frequency_adaptation=None,
        user_training_state=user_training_state,
        history_rows=[],
        latest_soreness_entry=None,
        latest_checkin=None,
        prior_plans=[],
    )

    snapshot = runtime["stimulus_fatigue_response"]
    assert snapshot["fatigue_cost"] == "high"
    assert snapshot["recoverability"] == "low"
    assert snapshot["deload_pressure"] == "high"
    assert snapshot["substitution_pressure"] == "high"
    sfr_step = next(
        step for step in runtime["decision_trace"]["steps"] if step["decision"] == "stimulus_fatigue_response"
    )
    assert sfr_step["result"]["completion_pct_proxy"] == 80
    assert runtime["decision_trace"]["outcome"]["stimulus_fatigue_response"]["deload_pressure"] == "high"


def test_prepare_generate_week_plan_runtime_inputs_normalizes_plan_inputs() -> None:
    runtime = prepare_generate_week_plan_runtime_inputs(
        user_name="Coach User",
        split_preference="full_body",
        nutrition_phase="maintenance",
        available_equipment=["barbell", "dumbbell"],
        generation_runtime={
            "effective_days_available": 4,
            "history": [{"exercise_id": "bench"}],
            "soreness_by_muscle": {"chest": "mild"},
            "prior_generated_weeks": 2,
            "latest_adherence_score": 3,
            "severe_soreness_count": 1,
            "session_time_budget_minutes": 45,
            "movement_restrictions": ["overhead_pressing"],
        },
    )

    assert runtime["user_profile"] == {
        "name": "Coach User",
        "session_time_budget_minutes": 45,
        "movement_restrictions": ["overhead_pressing"],
    }
    assert runtime["days_available"] == 4
    assert runtime["split_preference"] == "full_body"
    assert runtime["phase"] == "maintenance"
    assert runtime["available_equipment"] == ["barbell", "dumbbell"]
    assert runtime["history"] == [{"exercise_id": "bench"}]
    assert runtime["decision_trace"]["interpreter"] == "prepare_generate_week_plan_runtime_inputs"


def test_prepare_generate_week_plan_runtime_inputs_applies_defaults() -> None:
    runtime = prepare_generate_week_plan_runtime_inputs(
        user_name=None,
        split_preference="upper_lower",
        nutrition_phase=None,
        available_equipment=None,
        generation_runtime={},
    )

    assert runtime["user_profile"] == {
        "name": None,
        "session_time_budget_minutes": None,
        "movement_restrictions": [],
    }
    assert runtime["phase"] == "maintenance"
    assert runtime["available_equipment"] == []
    assert runtime["days_available"] == 0
    assert runtime["history"] == []
    assert runtime["soreness_by_muscle"] == {}


def test_prepare_generate_week_scheduler_runtime_shapes_generate_week_call_args() -> None:
    runtime = prepare_generate_week_scheduler_runtime(
        user_name="Coach User",
        split_preference="full_body",
        nutrition_phase="maintenance",
        available_equipment=["barbell", "dumbbell"],
        generation_runtime={
            "effective_days_available": 4,
            "history": [{"exercise_id": "bench"}],
            "soreness_by_muscle": {"chest": "mild"},
            "prior_generated_weeks": 2,
            "latest_adherence_score": 3,
            "severe_soreness_count": 1,
            "session_time_budget_minutes": 45,
            "movement_restrictions": ["overhead_pressing"],
        },
        program_template={"id": "full_body_v1", "sessions": []},
        rule_set={"progression_rules": {"on_success": {"percent": 2.5}}},
    )

    scheduler_kwargs = runtime["scheduler_kwargs"]
    assert scheduler_kwargs["user_profile"] == {
        "name": "Coach User",
        "session_time_budget_minutes": 45,
        "movement_restrictions": ["overhead_pressing"],
    }
    assert scheduler_kwargs["days_available"] == 4
    assert scheduler_kwargs["split_preference"] == "full_body"
    assert scheduler_kwargs["phase"] == "maintenance"
    assert scheduler_kwargs["available_equipment"] == ["barbell", "dumbbell"]
    assert scheduler_kwargs["program_template"]["id"] == "full_body_v1"
    assert scheduler_kwargs["rule_set"]["progression_rules"]["on_success"]["percent"] == 2.5
    assert runtime["decision_trace"]["interpreter"] == "prepare_generate_week_scheduler_runtime"
    assert runtime["decision_trace"]["plan_input_trace"]["interpreter"] == "prepare_generate_week_plan_runtime_inputs"


def test_prepare_generate_week_review_lookup_runtime_parses_week_start() -> None:
    runtime = prepare_generate_week_review_lookup_runtime(
        base_plan={"week_start": "2026-03-09"}
    )

    assert runtime["week_start"] == date(2026, 3, 9)
    assert runtime["decision_trace"]["interpreter"] == "prepare_generate_week_review_lookup_runtime"
    assert runtime["decision_trace"]["outcome"]["week_start"] == "2026-03-09"


def test_prepare_generate_week_finalize_runtime_shapes_response_and_record_values() -> None:
    runtime = prepare_generate_week_finalize_runtime(
        user_id="user_123",
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
        review_cycle=SimpleNamespace(
            week_start=date(2026, 3, 9),
            reviewed_on=date(2026, 3, 10),
            adjustments={
                "global": {"set_delta": 1, "weight_scale": 0.95},
                "exercise_overrides": {},
            },
        ),
    )

    assert runtime["week_start"] == date(2026, 3, 9)
    assert runtime["response_payload"]["sessions"][0]["exercises"][0]["sets"] == 4
    assert runtime["record_values"]["user_id"] == "user_123"
    assert runtime["record_values"]["split"] == "full_body"
    assert runtime["record_values"]["phase"] == "maintenance"
    assert runtime["adaptation_persistence_payload"]["state_updated"] is True
    assert runtime["response_payload"]["decision_trace"]["owner_family"] == "generated_week"
    assert runtime["response_payload"]["decision_trace"]["canonical_inputs"]["selected_template_id"] == "full_body_v1"
    assert runtime["response_payload"]["decision_trace"]["policy_basis"]["template_selection"]["reason"] == (
        "recommend_generation_template_selection"
    )
    assert runtime["response_payload"]["decision_trace"]["execution_steps"][0]["step"] == "template_selection"
    assert runtime["response_payload"]["decision_trace"]["reason_summary"]
    assert runtime["response_payload"]["decision_trace"]["alternative_resolution"]["status"] == "candidates_considered"
    assert runtime["decision_trace"]["interpreter"] == "prepare_generate_week_finalize_runtime"
    assert runtime["decision_trace"]["review_overlay_trace"]["interpreter"] == "prepare_generated_week_review_overlay"


def test_build_coach_preview_context_reuses_serialized_recent_training_history() -> None:
    history_rows = [
        SimpleNamespace(
            primary_exercise_id="bench",
            exercise_id="bench",
            weight=82.5,
            created_at=datetime(2026, 3, 5, 9, 0),
        )
    ]
    template = {"id": "full_body_v1", "sessions": []}

    serialized_history = serialize_recent_training_history(history_rows)
    context = build_coach_preview_context(
        user_name="Coach User",
        split_preference="full_body",
        template=template,
        history_rows=history_rows,
        nutrition_phase="maintenance",
        available_equipment=["barbell", "bench"],
    )

    assert serialized_history == [
        {
            "primary_exercise_id": "bench",
            "exercise_id": "bench",
            "next_working_weight": 82.5,
            "created_at": "2026-03-05T09:00:00",
        }
    ]
    assert context == {
        "user_profile": {"name": "Coach User"},
        "split_preference": "full_body",
        "program_template": template,
        "history": serialized_history,
        "readiness_state": {},
        "phase": "maintenance",
        "available_equipment": ["barbell", "bench"],
    }


def test_build_coach_preview_context_prefers_canonical_training_state_history() -> None:
    template = {"id": "full_body_v1", "sessions": []}

    context = build_coach_preview_context(
        user_name="Coach User",
        split_preference="full_body",
        template=template,
        history_rows=[
            SimpleNamespace(
                primary_exercise_id="bench",
                exercise_id="bench",
                weight=82.5,
                created_at=datetime(2026, 3, 5, 9, 0),
            )
        ],
        user_training_state={
            "exercise_performance_history": [
                {
                    "exercise_id": "row",
                    "performed_at": datetime(2026, 3, 6, 9, 0),
                    "set_index": 1,
                    "reps": 10,
                    "weight": 70.0,
                    "rpe": 8.0,
                }
            ]
        },
        nutrition_phase="maintenance",
        available_equipment=["barbell", "bench"],
    )

    assert context["history"] == [
        {
            "primary_exercise_id": "row",
            "exercise_id": "row",
            "next_working_weight": 70.0,
            "created_at": "2026-03-06T09:00:00",
        }
    ]


def test_prepare_coach_preview_runtime_inputs_normalizes_days_and_trace() -> None:
    runtime = prepare_coach_preview_runtime_inputs(
        preview_request={"from_days": 3, "to_days": 5, "current_phase": "accumulation"},
        profile_days_available=4,
    )

    assert runtime["max_requested_days"] == 5
    assert runtime["preview_request"]["from_days"] == 3
    assert runtime["preview_request"]["to_days"] == 5
    assert runtime["decision_trace"]["interpreter"] == "prepare_coach_preview_runtime_inputs"
    assert runtime["decision_trace"]["outcome"]["profile_days"] == 4


def test_resolve_frequency_adaptation_request_context_derives_program_week_and_recovery_state() -> None:
    latest_plan = SimpleNamespace(payload={"mesocycle": {"week_index": 4}})
    latest_soreness = SimpleNamespace(severity_by_muscle={"chest": "severe", "back": "severe", "quads": "mild"})

    context = resolve_frequency_adaptation_request_context(
        requested_program_id=None,
        selected_program_id="full_body_v1",
        latest_plan=latest_plan,
        latest_soreness_entry=latest_soreness,
    )

    assert context["program_id"] == "full_body_v1"
    assert context["current_week_index"] == 4
    assert context["recovery_state"] == "high_fatigue"
    assert context["decision_trace"]["interpreter"] == "resolve_frequency_adaptation_request_context"
    assert context["decision_trace"]["outcome"]["current_week_index"] == 4
    assert context["decision_trace"]["outcome"]["recovery_state"] == "high_fatigue"


def test_resolve_frequency_adaptation_request_context_prefers_canonical_training_state() -> None:
    context = resolve_frequency_adaptation_request_context(
        requested_program_id=None,
        selected_program_id=None,
        user_training_state={
            "user_program_state": {
                "program_id": "upper_lower_v1",
                "week_index": 5,
            },
            "fatigue_state": {
                "recovery_state": "high_fatigue",
                "severe_soreness_count": 2,
            },
        },
        latest_plan=None,
        latest_soreness_entry=None,
    )

    assert context["program_id"] == "upper_lower_v1"
    assert context["current_week_index"] == 5
    assert context["recovery_state"] == "high_fatigue"
    assert context["decision_trace"]["steps"][1]["result"]["source"] == "training_state"
    assert context["decision_trace"]["steps"][2]["result"]["source"] == "training_state"


def test_prepare_frequency_adaptation_runtime_inputs_reuses_context_and_shapes_engine_args() -> None:
    runtime = prepare_frequency_adaptation_runtime_inputs(
        requested_program_id=None,
        selected_program_id="full_body_v1",
        user_training_state={
            "user_program_state": {
                "program_id": "upper_lower_v1",
                "week_index": 5,
            },
            "fatigue_state": {
                "recovery_state": "high_fatigue",
                "severe_soreness_count": 2,
            },
        },
        current_days_available=5,
        target_days=3,
        duration_weeks=2,
        explicit_weak_areas=["chest"],
        stored_weak_areas=["hamstrings"],
        equipment_profile=["barbell", "bench"],
    )

    assert runtime["program_id"] == "full_body_v1"
    assert runtime["current_days"] == 5
    assert runtime["target_days"] == 3
    assert runtime["duration_weeks"] == 2
    assert runtime["recovery_state"] == "high_fatigue"
    assert runtime["current_week_index"] == 5
    assert runtime["explicit_weak_areas"] == ["chest"]
    assert runtime["stored_weak_areas"] == ["hamstrings"]
    assert runtime["equipment_profile"] == ["barbell", "bench"]
    assert runtime["decision_trace"]["interpreter"] == "prepare_frequency_adaptation_runtime_inputs"


def test_prepare_frequency_adaptation_decision_runtime_builds_training_state_then_runtime() -> None:
    runtime = prepare_frequency_adaptation_decision_runtime(
        requested_program_id="full_body_v1",
        selected_program_id="full_body_v1",
        latest_plan={"id": "plan_1"},
        latest_soreness_entry={"entry_date": "2026-03-09"},
        current_days_available=5,
        target_days=3,
        duration_weeks=2,
        explicit_weak_areas=["chest"],
        stored_weak_areas=["back"],
        equipment_profile=["barbell"],
        build_plan_decision_training_state=lambda **kwargs: {
            "program_id": kwargs["selected_program_id"],
            "has_plan": kwargs["latest_plan"] is not None,
        },
    )

    assert runtime["training_state"]["program_id"] == "full_body_v1"
    assert runtime["adaptation_runtime"]["target_days"] == 3
    assert runtime["decision_trace"]["interpreter"] == "prepare_frequency_adaptation_decision_runtime"
    assert runtime["decision_trace"]["outcome"]["program_id"] == "full_body_v1"
    assert runtime["context_trace"]["interpreter"] == "resolve_frequency_adaptation_request_context"


def test_prepare_plan_generation_decision_runtime_builds_canonical_training_state_and_generation_runtime() -> None:
    runtime = prepare_plan_generation_decision_runtime(
        selected_template_id="upper_lower_v1",
        current_days_available=5,
        active_frequency_adaptation={"target_days": 4},
        selected_program_id="upper_lower_v1",
        latest_plan=SimpleNamespace(payload={"program_template_id": "upper_lower_v1"}),
        latest_soreness_entry=SimpleNamespace(severity_by_muscle={"chest": "mild"}),
        recent_workout_logs=[
            SimpleNamespace(
                exercise_id="bench_press",
                primary_exercise_id="bench_press",
                weight=82.5,
                reps=8,
                rir=2,
                completed=True,
                created_at=datetime(2026, 3, 9, 9, 0),
            )
        ],
        recent_checkins=[SimpleNamespace(adherence_score=4)],
        recent_review_cycles=[SimpleNamespace(reviewed_on=date(2026, 3, 8))],
        prior_plans=[],
        build_plan_decision_training_state=lambda **kwargs: {
            "user_program_state": {
                "program_id": kwargs["selected_program_id"],
                "week_index": 3,
            },
            "adherence_state": {"latest_adherence_score": 4},
            "fatigue_state": {"soreness_by_muscle": {"chest": "mild"}},
            "exercise_performance_history": [{"exercise_id": "bench_press"}],
            "generation_state": {"prior_generated_weeks_by_program": {"upper_lower_v1": 2}},
            "source_flags": {
                "has_latest_plan": kwargs["latest_plan"] is not None,
                "checkin_count": len(kwargs["recent_checkins"]),
                "review_cycle_count": len(kwargs["recent_review_cycles"]),
            },
        },
    )

    assert runtime["training_state"]["source_flags"]["has_latest_plan"] is True
    assert runtime["training_state"]["source_flags"]["checkin_count"] == 1
    assert runtime["generation_runtime"]["effective_days_available"] == 4
    assert runtime["generation_runtime"]["latest_adherence_score"] == 4
    assert runtime["generation_runtime"]["prior_generated_weeks"] == 2
    assert runtime["generation_runtime"]["decision_trace"]["interpreter"] == "resolve_week_generation_runtime_inputs"
    assert runtime["decision_trace"]["interpreter"] == "prepare_plan_generation_decision_runtime"


def test_resolve_week_generation_runtime_inputs_prefers_canonical_training_state_history_and_adherence() -> None:
    today = date(2026, 3, 5)
    prior_plans = [
        SimpleNamespace(
            week_start=today - timedelta(days=14),
            payload={"program_template_id": "full_body_v1", "sessions": []},
        )
    ]

    runtime = resolve_week_generation_runtime_inputs(
        selected_template_id="full_body_v1",
        current_days_available=4,
        active_frequency_adaptation=None,
        user_training_state={
            "exercise_performance_history": [
                {
                    "exercise_id": "bench",
                    "performed_at": datetime(2026, 3, 3, 9, 0),
                    "weight": 82.5,
                }
            ],
            "adherence_state": {
                "latest_adherence_score": 4,
            },
        },
        history_rows=[],
        latest_soreness_entry=SimpleNamespace(severity_by_muscle={"chest": "severe", "back": "severe"}),
        latest_checkin=None,
        prior_plans=prior_plans,
    )

    assert runtime["history"] == [
        {
            "primary_exercise_id": "bench",
            "exercise_id": "bench",
            "next_working_weight": 82.5,
            "created_at": "2026-03-03T09:00:00",
        }
    ]
    assert runtime["latest_adherence_score"] == 4
    assert runtime["decision_trace"]["steps"][1]["result"]["latest_adherence_score_source"] == "training_state"
    assert runtime["decision_trace"]["steps"][2]["result"]["history_source"] == "training_state"


def test_guide_payload_builders_shape_program_day_and_exercise_views() -> None:
    summary_payloads = build_guide_programs_payload(
        [
            {
                "id": "full_body_v1",
                "split": "full_body",
                "days_supported": [3],
                "description": "Full body template",
            }
        ]
    )
    template = {
        "sessions": [
            {
                "name": "Day 1",
                "exercises": [
                    {
                        "id": "bench",
                        "primary_exercise_id": "bench",
                        "name": "Bench Press",
                        "notes": "Pause on chest.",
                        "video": {"youtube_url": "https://example.com/bench"},
                    }
                ],
            }
        ]
    }

    guide_payload = build_program_guide_payload(
        program_id="full_body_v1",
        program_summary=summary_payloads[0],
        template=template,
    )
    day_payload = build_program_day_guide_payload(program_id="full_body_v1", template=template, day_index=1)
    exercise = resolve_program_exercise_guide(template=template, exercise_id="bench")

    assert format_program_display_name("full_body_v1") == "Full Body V1"
    assert guide_payload["days"][0]["first_exercise_id"] == "bench"
    assert day_payload["exercises"][0]["video_youtube_url"] == "https://example.com/bench"
    assert exercise is not None
    assert build_program_exercise_guide_payload(program_id="full_body_v1", exercise=exercise)["exercise"]["id"] == "bench"
