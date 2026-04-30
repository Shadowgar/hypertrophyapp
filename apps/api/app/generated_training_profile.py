from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .generated_decision_profile import GeneratedDecisionProfile, build_generated_decision_profile


ProgressionMode = Literal["reps_first", "load_first", "hybrid"]
SexRelatedPhysiologyFlag = Literal["off", "female", "male", "intersex", "self_describe", "prefer_not"]


class RuntimeActiveControls(BaseModel):
    target_days: int = Field(ge=2, le=5)
    session_time_band: str
    recovery_modifier: str
    weakpoint_targets: list[str] = Field(default_factory=list)
    movement_restriction_flags: list[str] = Field(default_factory=list)
    generated_mode: str


class WeeklyVolumeBand(BaseModel):
    planned_sets_min: int = Field(ge=0)
    planned_sets_max: int = Field(ge=0)


class RepBands(BaseModel):
    main_lift: str
    accessory: str


class TraceOnlyControls(BaseModel):
    starting_rir: int = Field(ge=1, le=4)
    high_fatigue_cap: int = Field(ge=1, le=3)
    weekly_volume_band: WeeklyVolumeBand
    major_muscle_floors: dict[str, int]
    arm_delt_caps: dict[str, int]
    core_floor: int = Field(ge=0)
    rep_bands: RepBands
    progression_mode: ProgressionMode
    sex_related_physiology_flag: SexRelatedPhysiologyFlag
    anthropometry_flags: dict[str, bool]
    bodyweight_regression_flag: bool


class GeneratedTrainingProfileTrace(BaseModel):
    selected_mode_reason: str
    defaults_applied: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    generated_onboarding_complete: bool = False
    profile_completeness: Literal["low", "medium", "high"] = "low"
    rule_hits: list[str] = Field(default_factory=list)
    trace_only_fields: list[str] = Field(default_factory=list)
    insufficient_data_avoided: bool = False


class GeneratedTrainingProfile(BaseModel):
    selected_program_id: str
    path_family: Literal["authored", "generated"]
    decision_profile: GeneratedDecisionProfile
    runtime_active: RuntimeActiveControls
    trace_only_controls: TraceOnlyControls
    decision_trace: GeneratedTrainingProfileTrace


_TRACE_ONLY_FIELDS: list[str] = [
    "starting_rir",
    "high_fatigue_cap",
    "weekly_volume_band",
    "major_muscle_floors",
    "arm_delt_caps",
    "core_floor",
    "rep_bands",
    "progression_mode",
    "sex_related_physiology_flag",
    "anthropometry_flags",
    "bodyweight_regression_flag",
]


def _as_clean_str(value: Any) -> str:
    return str(value or "").strip()


def _normalize_sex_related_physiology_flag(onboarding_answers: dict[str, Any]) -> SexRelatedPhysiologyFlag:
    enabled_raw = onboarding_answers.get("use_sex_related_physiology")
    enabled = str(enabled_raw).strip().lower() in {"true", "1", "yes", "y"} if enabled_raw is not None else False
    if not enabled:
        return "off"

    raw = _as_clean_str(
        onboarding_answers.get("sex_related_physiology")
        or onboarding_answers.get("sex")
        or onboarding_answers.get("gender")
    ).lower()
    if raw in {"female", "woman"}:
        return "female"
    if raw in {"male", "man"}:
        return "male"
    if raw == "intersex":
        return "intersex"
    if raw in {"self_describe", "self-describe"}:
        return "self_describe"
    return "prefer_not"


def _normalize_anthropometry_flags(onboarding_answers: dict[str, Any]) -> dict[str, bool]:
    raw = _as_clean_str(onboarding_answers.get("limb_proportions") or onboarding_answers.get("anthropometry")).lower()
    return {
        "long_femurs": raw in {"long_thighs", "long_thighs_vs_torso", "both"},
        "long_arms": raw in {"long_arms", "long_arms_vs_height", "both"},
    }


def _normalize_bodyweight_regression_flag(
    *,
    onboarding_answers: dict[str, Any],
    movement_restriction_flags: list[str],
) -> bool:
    value = onboarding_answers.get("bodyweight_regression_flag")
    if isinstance(value, bool):
        return value
    return "unsupported_bent_over_rowing" in movement_restriction_flags


def _derive_progression_mode(goal_mode: str) -> ProgressionMode:
    if goal_mode == "strength_focus":
        return "load_first"
    if goal_mode == "recomposition":
        return "hybrid"
    return "reps_first"


def _derive_rep_bands(goal_mode: str) -> RepBands:
    if goal_mode == "strength_focus":
        return RepBands(main_lift="4-8", accessory="8-12")
    if goal_mode == "recomposition":
        return RepBands(main_lift="6-10", accessory="10-15")
    return RepBands(main_lift="6-10", accessory="8-15")


def _derive_starting_rir(training_status: str, recovery_modifier: str, generated_mode: str) -> int:
    if generated_mode == "comeback_reentry":
        return 4
    if recovery_modifier == "low":
        return 3
    if training_status == "advanced":
        return 2
    return 3


def _derive_high_fatigue_cap(recovery_modifier: str, session_time_band: str) -> int:
    if recovery_modifier == "low":
        return 1
    if session_time_band == "extended":
        return 2
    return 1


def _derive_weekly_volume_band(training_status: str, session_time_band: str) -> WeeklyVolumeBand:
    lookup = {
        ("novice", "low"): (36, 42),
        ("novice", "standard"): (42, 50),
        ("novice", "extended"): (50, 58),
        ("intermediate", "low"): (40, 48),
        ("intermediate", "standard"): (50, 60),
        ("intermediate", "extended"): (60, 72),
        ("advanced", "low"): (44, 54),
        ("advanced", "standard"): (58, 70),
        ("advanced", "extended"): (70, 84),
    }
    planned_sets_min, planned_sets_max = lookup.get((training_status, session_time_band), (42, 50))
    return WeeklyVolumeBand(planned_sets_min=planned_sets_min, planned_sets_max=planned_sets_max)


def _derive_major_muscle_floors(training_status: str, session_time_band: str) -> dict[str, int]:
    if training_status == "advanced" and session_time_band == "extended":
        return {"chest": 12, "back": 14, "quads": 12, "hamstrings": 12}
    if session_time_band == "low":
        return {"chest": 8, "back": 10, "quads": 8, "hamstrings": 8}
    return {"chest": 10, "back": 12, "quads": 10, "hamstrings": 10}


def _derive_arm_delt_caps(training_status: str, session_time_band: str) -> dict[str, int]:
    if training_status == "advanced" and session_time_band == "extended":
        return {"arm_soft_cap": 16, "delt_soft_cap": 16}
    if session_time_band == "low":
        return {"arm_soft_cap": 10, "delt_soft_cap": 10}
    return {"arm_soft_cap": 12, "delt_soft_cap": 12}


def _derive_core_floor(training_status: str, session_time_band: str) -> int:
    if training_status == "advanced" and session_time_band == "extended":
        return 6
    if session_time_band == "low":
        return 2
    return 4


def build_generated_training_profile(
    *,
    selected_program_id: str | None,
    program_selection_mode: str | None,
    days_available: int | None,
    session_time_budget_minutes: int | None,
    temporary_duration_minutes: int | None,
    near_failure_tolerance: str | None,
    weak_areas: list[str] | None,
    movement_restrictions: list[str] | None,
    equipment_profile: list[str] | None,
    onboarding_answers: dict[str, Any] | None,
    training_state: dict[str, Any] | None,
) -> GeneratedTrainingProfile:
    decision_profile = build_generated_decision_profile(
        selected_program_id=selected_program_id,
        program_selection_mode=program_selection_mode,
        days_available=days_available,
        session_time_budget_minutes=session_time_budget_minutes,
        temporary_duration_minutes=temporary_duration_minutes,
        near_failure_tolerance=near_failure_tolerance,
        weak_areas=weak_areas,
        movement_restrictions=movement_restrictions,
        equipment_profile=equipment_profile,
        onboarding_answers=onboarding_answers,
        training_state=training_state,
    )
    answers = dict(onboarding_answers or {})

    progression_mode = _derive_progression_mode(decision_profile.goal_mode)
    rep_bands = _derive_rep_bands(decision_profile.goal_mode)
    starting_rir = _derive_starting_rir(
        decision_profile.training_status,
        decision_profile.recovery_modifier,
        decision_profile.generated_mode,
    )
    high_fatigue_cap = _derive_high_fatigue_cap(decision_profile.recovery_modifier, decision_profile.session_time_band)
    weekly_volume_band = _derive_weekly_volume_band(decision_profile.training_status, decision_profile.session_time_band)
    major_muscle_floors = _derive_major_muscle_floors(decision_profile.training_status, decision_profile.session_time_band)
    arm_delt_caps = _derive_arm_delt_caps(decision_profile.training_status, decision_profile.session_time_band)
    core_floor = _derive_core_floor(decision_profile.training_status, decision_profile.session_time_band)
    sex_related_physiology_flag = _normalize_sex_related_physiology_flag(answers)
    anthropometry_flags = _normalize_anthropometry_flags(answers)
    bodyweight_regression_flag = _normalize_bodyweight_regression_flag(
        onboarding_answers=answers,
        movement_restriction_flags=decision_profile.movement_restriction_flags,
    )

    runtime_active = RuntimeActiveControls(
        target_days=decision_profile.target_days,
        session_time_band=decision_profile.session_time_band,
        recovery_modifier=decision_profile.recovery_modifier,
        weakpoint_targets=list(decision_profile.weakpoint_targets),
        movement_restriction_flags=list(decision_profile.movement_restriction_flags),
        generated_mode=decision_profile.generated_mode,
    )
    trace_only_controls = TraceOnlyControls(
        starting_rir=starting_rir,
        high_fatigue_cap=high_fatigue_cap,
        weekly_volume_band=weekly_volume_band,
        major_muscle_floors=major_muscle_floors,
        arm_delt_caps=arm_delt_caps,
        core_floor=core_floor,
        rep_bands=rep_bands,
        progression_mode=progression_mode,
        sex_related_physiology_flag=sex_related_physiology_flag,
        anthropometry_flags=anthropometry_flags,
        bodyweight_regression_flag=bodyweight_regression_flag,
    )
    profile_trace = GeneratedTrainingProfileTrace(
        selected_mode_reason=decision_profile.decision_trace.selected_mode_reason,
        defaults_applied=list(decision_profile.decision_trace.defaults_applied),
        missing_fields=list(decision_profile.decision_trace.missing_fields),
        generated_onboarding_complete=decision_profile.decision_trace.generated_onboarding_complete,
        profile_completeness=decision_profile.decision_trace.profile_completeness,
        rule_hits=list(decision_profile.decision_trace.rule_hits) + ["phase3a.generated_training_profile_bridge_v1"],
        trace_only_fields=list(_TRACE_ONLY_FIELDS),
        insufficient_data_avoided=decision_profile.decision_trace.insufficient_data_avoided,
    )

    return GeneratedTrainingProfile(
        selected_program_id=decision_profile.selected_program_id,
        path_family=decision_profile.path_family,
        decision_profile=decision_profile,
        runtime_active=runtime_active,
        trace_only_controls=trace_only_controls,
        decision_trace=profile_trace,
    )
