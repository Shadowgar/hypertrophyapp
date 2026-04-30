from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, Field

from .program_loader import is_generated_full_body_binding_id, resolve_selected_program_binding_id


GeneratedMode = Literal[
    "normal_full_body",
    "low_time_full_body",
    "low_recovery_full_body",
    "comeback_reentry",
    "insufficient_data_default",
]
SessionTimeBand = Literal["low", "standard", "extended", "unknown"]
RecoveryModifier = Literal["low", "standard", "high", "unknown"]
TrainingStatus = Literal["novice", "intermediate", "advanced", "unknown"]
DetrainingStatus = Literal["active", "partial_layoff", "complete_layoff", "unknown"]
GoalMode = Literal["fat_loss", "recomposition", "lean_gain", "strength_focus", "general_fitness", "unknown"]
EquipmentScope = Literal["minimal", "dumbbell", "garage", "full_gym", "unknown"]
PathFamily = Literal["authored", "generated"]


class GeneratedDecisionTrace(BaseModel):
    selected_mode_reason: str
    defaults_applied: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    generated_onboarding_complete: bool = False
    profile_completeness: Literal["low", "medium", "high"] = "low"
    ignored_future_fields: list[str] = Field(default_factory=list)
    rule_hits: list[str] = Field(default_factory=list)
    insufficient_data_avoided: bool = False


class GeneratedDecisionProfile(BaseModel):
    selected_program_id: str
    path_family: PathFamily
    target_days: int = Field(ge=2, le=5)
    session_time_band: SessionTimeBand
    recovery_modifier: RecoveryModifier
    training_status: TrainingStatus
    detraining_status: DetrainingStatus
    goal_mode: GoalMode
    equipment_scope: EquipmentScope
    weakpoint_targets: list[str] = Field(default_factory=list)
    movement_restriction_flags: list[str] = Field(default_factory=list)
    generated_mode: GeneratedMode
    reentry_required: bool
    decision_trace: GeneratedDecisionTrace


def _as_clean_str(value: Any) -> str:
    return str(value or "").strip()


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "y", "1"}:
            return True
        if lowered in {"false", "no", "n", "0"}:
            return False
    if isinstance(value, (int, float)):
        if int(value) == 1:
            return True
        if int(value) == 0:
            return False
    return None


def _find_value(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _extract_generated_onboarding_answers(onboarding_answers: dict[str, Any]) -> tuple[dict[str, Any], bool, str]:
    generated_onboarding_state = dict(onboarding_answers.get("generated_onboarding") or {})
    generated_onboarding_answers = dict(generated_onboarding_state.get("generated_onboarding") or {})
    generated_onboarding_complete = bool(generated_onboarding_state.get("generated_onboarding_complete"))
    required_field_presence = dict(generated_onboarding_state.get("required_field_presence") or {})
    missing_required_count = sum(1 for present in required_field_presence.values() if present is not True)
    if missing_required_count == 0 and required_field_presence:
        profile_completeness: Literal["low", "medium", "high"] = "high"
    elif missing_required_count <= 3 and required_field_presence:
        profile_completeness = "medium"
    else:
        profile_completeness = "low"
    return generated_onboarding_answers, generated_onboarding_complete, profile_completeness


def _normalize_target_days(days_available: int | None, *, defaults: list[str], missing: list[str]) -> int:
    if days_available is None:
        defaults.append("default_target_days_3")
        missing.append("days_available")
        return 3
    return max(2, min(5, int(days_available)))


def _normalize_session_time_band(
    *,
    temporary_duration_minutes: int | None,
    session_time_budget_minutes: int | None,
    defaults: list[str],
    missing: list[str],
) -> SessionTimeBand:
    minutes = temporary_duration_minutes if temporary_duration_minutes is not None else session_time_budget_minutes
    if minutes is None:
        defaults.append("default_session_time_band_standard")
        missing.append("session_time_budget_minutes")
        return "standard"
    if int(minutes) <= 45:
        return "low"
    if int(minutes) >= 75:
        return "extended"
    return "standard"


def _normalize_recovery_modifier(
    *,
    near_failure_tolerance: str | None,
    training_state: dict[str, Any] | None,
    onboarding_answers: dict[str, Any],
    defaults: list[str],
) -> RecoveryModifier:
    tolerance = _as_clean_str(near_failure_tolerance).lower()
    if tolerance == "low":
        return "low"
    if tolerance == "high":
        return "high"

    recovery_answer = _as_clean_str(
        _find_value(
            onboarding_answers,
            "recovery",
            "recovery_capacity",
            "recovery_modifier",
            "recovery_status",
        )
    ).lower()
    if recovery_answer in {"low", "poor"}:
        return "low"
    if recovery_answer in {"high", "good"}:
        return "high"

    fatigue_state = dict((training_state or {}).get("fatigue_state") or {})
    if _as_clean_str(fatigue_state.get("recovery_state")).lower() == "high_fatigue":
        return "low"

    defaults.append("default_recovery_modifier_standard")
    return "standard"


def _normalize_training_status(onboarding_answers: dict[str, Any]) -> TrainingStatus:
    raw = _as_clean_str(
        _find_value(
            onboarding_answers,
            "training_status",
            "experience_level_generated",
            "experience_level",
            "lifting_experience",
        )
    ).lower()
    if raw in {"new", "novice", "beginner"}:
        return "novice"
    if raw in {"advanced", "expert"}:
        return "advanced"
    if raw in {"intermediate", "normal", "consistent", "returning"}:
        return "intermediate"
    return "unknown"


def _normalize_detraining_status(
    onboarding_answers: dict[str, Any],
    *,
    defaults: list[str],
) -> DetrainingStatus:
    trained_last_4_weeks = _as_bool(
        _find_value(
            onboarding_answers,
            "trained_consistently_last_4_weeks",
            "trained_in_last_4_weeks",
            "trained_last_4_weeks",
        )
    )
    if trained_last_4_weeks is True:
        return "active"
    if trained_last_4_weeks is False:
        return "complete_layoff"

    layoff = _as_clean_str(_find_value(onboarding_answers, "layoff_status", "detraining_status", "training_status")).lower()
    if "complete" in layoff:
        return "complete_layoff"
    if "partial" in layoff or "returning" in layoff:
        return "partial_layoff"
    if "active" in layoff or "consistent" in layoff:
        return "active"

    defaults.append("default_detraining_status_active")
    return "active"


def _normalize_goal_mode(onboarding_answers: dict[str, Any]) -> GoalMode:
    raw = _as_clean_str(_find_value(onboarding_answers, "goal_mode", "primary_goal", "goal")).lower()
    if raw in {"fat_loss", "cut", "lose_fat"}:
        return "fat_loss"
    if raw in {"recomposition", "recomp"}:
        return "recomposition"
    if raw in {"lean_gain", "gain", "build_muscle", "hypertrophy"}:
        return "lean_gain"
    if raw in {"strength", "strength_focus"}:
        return "strength_focus"
    if raw == "size_strength":
        return "strength_focus"
    if raw:
        return "general_fitness"
    return "unknown"


def _normalize_equipment_scope(equipment_profile: list[str] | None) -> EquipmentScope:
    tags = {_as_clean_str(item).lower() for item in (equipment_profile or []) if _as_clean_str(item)}
    if not tags:
        return "unknown"
    if any(item in tags for item in ("machine", "cable", "barbell")) and any(item in tags for item in ("bench", "dumbbell")):
        return "full_gym"
    if "barbell" in tags and "rack" in tags:
        return "garage"
    if "dumbbell" in tags:
        return "dumbbell"
    return "minimal"


def _normalize_weakpoints(weak_areas: list[str] | None) -> list[str]:
    alias: dict[str, str] = {
        "shoulders": "delts",
        "rear_delts": "delts",
        "side_delts": "delts",
        "front_delts": "delts",
        "triceps": "arms",
        "biceps": "arms",
        "lats": "back",
    }
    normalized: list[str] = []
    for raw in weak_areas or []:
        tag = _as_clean_str(raw).lower()
        if not tag:
            continue
        canonical = alias.get(tag, tag)
        if canonical not in normalized:
            normalized.append(canonical)
    return normalized[:2]


def _normalize_movement_restrictions(movement_restrictions: list[str] | None) -> list[str]:
    allowed: set[str] = {
        "deep_knee_flexion",
        "overhead_pressing",
        "barbell_from_floor",
        "long_length_hamstrings",
        "unsupported_bent_over_rowing",
        "none",
        "other",
    }
    normalized: list[str] = []
    for item in (movement_restrictions or []):
        candidate = _as_clean_str(item).lower().replace(" ", "_").replace("-", "_")
        if not candidate:
            continue
        canonical = candidate if candidate in allowed else "other"
        if canonical == "none":
            continue
        if canonical not in normalized:
            normalized.append(canonical)
    return normalized[:8]


def _resolve_path_family(selected_program_id: str, program_selection_mode: str | None) -> PathFamily:
    if _as_clean_str(program_selection_mode).lower() == "generated":
        return "generated"
    if is_generated_full_body_binding_id(selected_program_id):
        return "generated"
    return "authored"


def build_generated_decision_profile(
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
) -> GeneratedDecisionProfile:
    defaults_applied: list[str] = []
    missing_fields: list[str] = []
    rule_hits: list[str] = []

    resolved_program_id = resolve_selected_program_binding_id(_as_clean_str(selected_program_id)) or "full_body_v1"
    if not _as_clean_str(selected_program_id):
        defaults_applied.append("default_selected_program_id_full_body_v1")
        missing_fields.append("selected_program_id")

    answers = dict(onboarding_answers or {})
    generated_onboarding_answers, generated_onboarding_complete, profile_completeness = _extract_generated_onboarding_answers(answers)
    merged_answers = {**answers, **generated_onboarding_answers}
    path_family = _resolve_path_family(resolved_program_id, program_selection_mode)
    generated_target_days = generated_onboarding_answers.get("target_days")
    if generated_target_days is not None:
        try:
            target_days = _normalize_target_days(int(generated_target_days), defaults=defaults_applied, missing=missing_fields)
        except (TypeError, ValueError):
            target_days = _normalize_target_days(days_available, defaults=defaults_applied, missing=missing_fields)
    else:
        target_days = _normalize_target_days(days_available, defaults=defaults_applied, missing=missing_fields)
    generated_time_band = _as_clean_str(generated_onboarding_answers.get("session_time_band_source")).lower()
    source_session_time_budget_minutes = session_time_budget_minutes
    if generated_time_band == "30_45":
        source_session_time_budget_minutes = 45
    elif generated_time_band == "50_70":
        source_session_time_budget_minutes = 60
    elif generated_time_band == "75_100":
        source_session_time_budget_minutes = 90
    session_time_band = _normalize_session_time_band(
        temporary_duration_minutes=temporary_duration_minutes,
        session_time_budget_minutes=source_session_time_budget_minutes,
        defaults=defaults_applied,
        missing=missing_fields,
    )
    source_near_failure_tolerance = near_failure_tolerance
    generated_recovery = _as_clean_str(generated_onboarding_answers.get("recovery_modifier")).lower()
    if generated_recovery == "low":
        source_near_failure_tolerance = "low"
    elif generated_recovery == "high":
        source_near_failure_tolerance = "high"
    recovery_modifier = _normalize_recovery_modifier(
        near_failure_tolerance=source_near_failure_tolerance,
        training_state=training_state,
        onboarding_answers=merged_answers,
        defaults=defaults_applied,
    )
    training_status = _normalize_training_status(merged_answers)
    detraining_status = _normalize_detraining_status(merged_answers, defaults=defaults_applied)
    goal_mode = _normalize_goal_mode(merged_answers)
    source_equipment_profile = (
        cast(list[str], generated_onboarding_answers.get("equipment_pool"))
        if isinstance(generated_onboarding_answers.get("equipment_pool"), list) and generated_onboarding_answers.get("equipment_pool")
        else equipment_profile
    )
    equipment_scope = _normalize_equipment_scope(source_equipment_profile)
    source_weak_areas = (
        cast(list[str], generated_onboarding_answers.get("weakpoint_targets"))
        if isinstance(generated_onboarding_answers.get("weakpoint_targets"), list) and generated_onboarding_answers.get("weakpoint_targets")
        else weak_areas
    )
    weakpoint_targets = _normalize_weakpoints(source_weak_areas)
    source_movement_restrictions = (
        cast(list[str], generated_onboarding_answers.get("movement_restrictions"))
        if isinstance(generated_onboarding_answers.get("movement_restrictions"), list) and generated_onboarding_answers.get("movement_restrictions")
        else movement_restrictions
    )
    movement_restriction_flags = _normalize_movement_restrictions(source_movement_restrictions)

    reentry_required = detraining_status == "complete_layoff"
    contradictory_core = target_days < 2 or target_days > 5
    core_missing = {"selected_program_id", "days_available"} <= set(missing_fields)

    if path_family != "generated":
        generated_mode: GeneratedMode = "normal_full_body"
        reason = "non_generated_path_bypass"
        rule_hits.append("phase1a.path_family.authored")
    elif reentry_required:
        generated_mode = "comeback_reentry"
        reason = "detraining_complete_layoff"
        rule_hits.append("phase1a.mode.comeback_reentry")
    elif recovery_modifier == "low":
        generated_mode = "low_recovery_full_body"
        reason = "recovery_modifier_low"
        rule_hits.append("phase1a.mode.low_recovery")
    elif session_time_band == "low":
        generated_mode = "low_time_full_body"
        reason = "session_time_low"
        rule_hits.append("phase1a.mode.low_time")
    elif contradictory_core or core_missing:
        generated_mode = "insufficient_data_default"
        reason = "insufficient_or_contradictory_data"
        rule_hits.append("phase1a.mode.insufficient_data")
    else:
        generated_mode = "normal_full_body"
        reason = "safe_defaults_or_complete_inputs"
        rule_hits.append("phase1a.mode.normal")

    ignored_future_fields = ["gender", "sex", "height", "weight"]
    insufficient_data_avoided = generated_mode != "insufficient_data_default" and bool(defaults_applied or missing_fields)
    if insufficient_data_avoided:
        rule_hits.append("phase1a.insufficient_data_avoided_by_defaults")

    return GeneratedDecisionProfile(
        selected_program_id=resolved_program_id,
        path_family=path_family,
        target_days=target_days,
        session_time_band=session_time_band,
        recovery_modifier=recovery_modifier,
        training_status=training_status,
        detraining_status=detraining_status,
        goal_mode=goal_mode,
        equipment_scope=equipment_scope,
        weakpoint_targets=weakpoint_targets,
        movement_restriction_flags=movement_restriction_flags,
        generated_mode=generated_mode,
        reentry_required=reentry_required,
        decision_trace=GeneratedDecisionTrace(
            selected_mode_reason=reason,
            defaults_applied=defaults_applied,
            missing_fields=missing_fields,
            generated_onboarding_complete=generated_onboarding_complete,
            profile_completeness=profile_completeness,
            ignored_future_fields=ignored_future_fields,
            rule_hits=rule_hits,
            insufficient_data_avoided=insufficient_data_avoided,
        ),
    )
