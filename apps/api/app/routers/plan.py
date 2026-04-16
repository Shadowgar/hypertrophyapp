from datetime import UTC, date, datetime, timedelta
from copy import deepcopy
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from core_engine import (
    apply_active_frequency_adaptation_runtime,
    build_coach_preview_context,
    finalize_coach_preview_commit_runtime,
    build_coaching_recommendation_timeline_payload,
    build_guide_programs_payload,
    build_program_day_guide_payload,
    build_program_exercise_guide_payload,
    build_program_guide_payload,
    build_plan_decision_training_state,
    prepare_coach_preview_decision_context,
    prepare_coach_preview_commit_runtime,
    prepare_coach_preview_route_runtime,
    prepare_coach_preview_runtime_inputs,
    prepare_coaching_apply_route_finalize_runtime,
    prepare_coaching_apply_route_runtime,
    prepare_coaching_apply_runtime_source,
    prepare_frequency_adaptation_route_runtime,
    prepare_frequency_adaptation_decision_runtime,
    prepare_generate_week_finalize_runtime,
    prepare_generate_week_review_lookup_runtime,
    prepare_generate_week_scheduler_runtime,
    prepare_generation_template_runtime,
    prepare_plan_generation_decision_runtime,
    prepare_profile_program_recommendation_route_runtime,
    recommend_frequency_adaptation_preview,
    resolve_program_display_name,
    resolve_optional_rule_set,
    resolve_onboarding_program_id,
    resolve_program_guide_summary,
    resolve_program_exercise_guide,
    generate_week_plan,
    recommend_coach_intelligence_preview,
    normalize_coaching_recommendation_timeline_limit,
    resolve_active_frequency_adaptation_runtime,
)
from core_engine.scheduler import AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY

from ..database import get_db
from ..deps import get_current_user
from ..generated_assessment_schema import ProfileAssessmentInput
from ..generated_full_body_runtime_adapter import (
    GENERATED_FULL_BODY_COMPATIBILITY_TEMPLATE_ID,
    prepare_generated_full_body_runtime_template,
)
from ..models import (
    CoachingRecommendation,
    ExerciseState,
    SorenessEntry,
    User,
    WeeklyCheckin,
    WeeklyReviewCycle,
    WorkoutPlan,
    WorkoutSessionState,
    WorkoutSetLog,
)
from ..observability import log_event
from ..program_loader import (
    is_authored_phase1_binding_id,
    is_authored_phase2_binding_id,
    is_generated_full_body_binding_id,
    list_program_templates,
    load_program_onboarding_package,
    load_program_rule_set,
    load_program_template,
    resolve_linked_program_id,
    resolve_selected_program_binding_id,
    resolve_onboarding_program_id as resolve_loader_onboarding_program_id,
    resolve_rule_program_id,
)
from ..adaptive_schema import FrequencyAdaptationResult
from ..schemas import GenerateWeekPlanRequest, ProgramTemplateSummary
from ..schemas import (
    FrequencyAdaptationApplyRequest,
    FrequencyAdaptationApplyResponse,
    ApplyPhaseDecisionRequest,
    ApplyPhaseDecisionResponse,
    ApplySpecializationDecisionRequest,
    ApplySpecializationDecisionResponse,
    CoachingRecommendationTimelineEntry,
    CoachingRecommendationTimelineResponse,
    GuideDaySummary,
    GuideExerciseSummary,
    GuideProgramSummary,
    FrequencyAdaptationPreviewRequest,
    IntelligenceCoachPreviewRequest,
    IntelligenceCoachPreviewResponse,
    NextWeekPlanRequest,
    ProgramDayGuideResponse,
    ProgramExerciseGuideResponse,
    ProgramGuideResponse,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
INVALID_TEMPLATE_DETAIL = "Invalid program template schema"
GUIDE_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"description": "Guide resource not found"},
    422: {"description": INVALID_TEMPLATE_DETAIL},
}
PROFILE_INCOMPLETE_DETAIL = "Complete profile first"
GenerationMode = Literal["current_week_regenerate", "next_week_advance"]


def _list_active_program_templates() -> list[dict[str, Any]]:
    try:
        return list_program_templates(active_only=True)
    except TypeError:
        # Test monkeypatches may provide a no-arg lambda replacement.
        return cast(list[dict[str, Any]], list_program_templates())


def _resolve_authored_week_index(program_template: dict[str, Any], *, prior_authored_family_weeks: int) -> int:
    authored_weeks = program_template.get("authored_weeks") or []
    if not isinstance(authored_weeks, list) or not authored_weeks:
        return 1
    bounded_index = min(max(0, int(prior_authored_family_weeks)), len(authored_weeks) - 1)
    selected_week = authored_weeks[bounded_index] if isinstance(authored_weeks[bounded_index], dict) else {}
    return max(1, int(selected_week.get("week_index", bounded_index + 1) or bounded_index + 1))


def _resolve_authored_prior_family_weeks(
    *,
    selected_template_id: str,
    training_state: dict[str, Any],
    fallback_prior_family_weeks: int,
) -> int:
    generation_state = cast(dict[str, Any], training_state.get("generation_state") or {})
    prior_weeks_by_program = generation_state.get("prior_generated_weeks_by_program")
    if not isinstance(prior_weeks_by_program, dict):
        return max(0, int(fallback_prior_family_weeks))

    matched_weeks = 0
    matched_any_family = False
    for program_id, prior_weeks in prior_weeks_by_program.items():
        if resolve_selected_program_binding_id(str(program_id).strip()) != selected_template_id:
            continue
        try:
            matched_weeks += max(0, int(prior_weeks or 0))
        except (TypeError, ValueError):
            continue
        matched_any_family = True

    if matched_any_family:
        return matched_weeks
    return max(0, int(fallback_prior_family_weeks))


def _resolve_onboarding_week(
    onboarding_package: dict[str, Any],
    *,
    week_index: int,
) -> dict[str, Any] | None:
    blueprint = cast(dict[str, Any], onboarding_package.get("blueprint") or {})
    week_sequence = [
        str(item).strip()
        for item in blueprint.get("week_sequence") or []
        if str(item).strip()
    ]
    if not week_sequence:
        return None
    template_key = week_sequence[(max(1, int(week_index)) - 1) % len(week_sequence)]
    for candidate in blueprint.get("week_templates") or []:
        if not isinstance(candidate, dict):
            continue
        if str(candidate.get("week_template_id") or "").strip() == template_key:
            return candidate
    return None


def _exercise_identity(exercise: dict[str, Any]) -> str:
    return str(exercise.get("primary_exercise_id") or exercise.get("id") or "").strip()


def _has_user_workout_activity(db: Session, *, user_id: str) -> bool:
    return any(
        (
            db.query(WorkoutSessionState).filter(WorkoutSessionState.user_id == user_id).first(),
            db.query(WorkoutSetLog).filter(WorkoutSetLog.user_id == user_id).first(),
            db.query(ExerciseState).filter(ExerciseState.user_id == user_id).first(),
        )
    )


def _list_user_workout_plans(db: Session, *, user_id: str) -> list[WorkoutPlan]:
    return (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.created_at.desc())
        .all()
    )


def _session_signature(session: dict[str, Any]) -> dict[str, Any]:
    exercises = [
        exercise
        for exercise in session.get("exercises") or []
        if isinstance(exercise, dict)
    ]
    ordered_exercises = [
        {
            "exercise_id": _exercise_identity(exercise),
            "sets": int(exercise.get("sets") or 0),
        }
        for exercise in exercises
        if _exercise_identity(exercise)
    ]
    return {
        "title": str(session.get("title") or session.get("name") or "").strip(),
        "day_role": str(session.get("day_role") or "").strip() or None,
        "exercise_order": [item["exercise_id"] for item in ordered_exercises],
        "exercise_sets": ordered_exercises,
        "planned_total": sum(item["sets"] for item in ordered_exercises),
    }


def _plan_payload_signature(payload: dict[str, Any]) -> dict[str, Any]:
    mesocycle = cast(dict[str, Any], payload.get("mesocycle") or {})
    return {
        "program_template_id": resolve_selected_program_binding_id(payload.get("program_template_id")),
        "week_index": int(mesocycle.get("week_index") or 0),
        "authored_week_index": int(mesocycle.get("authored_week_index") or 0),
        "sessions": [
            _session_signature(session)
            for session in payload.get("sessions") or []
            if isinstance(session, dict)
        ],
    }


def _delete_user_workout_plans_for_binding(
    db: Session,
    *,
    user_id: str,
    binding_id: str,
) -> None:
    for plan in _list_user_workout_plans(db, user_id=user_id):
        payload = plan.payload if isinstance(plan.payload, dict) else {}
        plan_binding_id = resolve_selected_program_binding_id(payload.get("program_template_id"))
        if plan_binding_id == binding_id:
            db.delete(plan)


def _resolve_effective_days_available(
    *,
    current_days_available: int,
    target_days_override: int | None,
) -> int:
    if target_days_override is not None:
        return int(target_days_override)
    return int(current_days_available)


def _resolve_choose_for_me_family_template(family: str | None) -> str | None:
    normalized = str(family or "").strip().lower()
    mapping = {
        "full_body": "full_body_v1",
        # Until authored upper/lower and PPL templates pass active contract gates,
        # route those family intents to the phase-2 canonical authored path.
        "upper_lower": "pure_bodybuilding_phase_2_full_body",
        "push_pull": "pure_bodybuilding_phase_2_full_body",
    }
    return mapping.get(normalized)


def _resolve_choose_for_me_family_target_days(family: str | None) -> int | None:
    normalized = str(family or "").strip().lower()
    mapping = {
        "full_body": 3,
        "upper_lower": 4,
        "push_pull": 3,
    }
    return mapping.get(normalized)


def _build_adaptive_signal_summary(
    *,
    db: Session,
    user_id: str,
) -> dict[str, Any]:
    latest_soreness = (
        db.query(SorenessEntry)
        .filter(SorenessEntry.user_id == user_id)
        .order_by(SorenessEntry.entry_date.desc(), SorenessEntry.created_at.desc())
        .first()
    )
    recent_checkins = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.user_id == user_id)
        .order_by(WeeklyCheckin.week_start.desc(), WeeklyCheckin.created_at.desc())
        .limit(4)
        .all()
    )
    recent_reviews = (
        db.query(WeeklyReviewCycle)
        .filter(WeeklyReviewCycle.user_id == user_id)
        .order_by(WeeklyReviewCycle.week_start.desc(), WeeklyReviewCycle.created_at.desc())
        .limit(4)
        .all()
    )
    adherence_scores = [int(item.adherence_score) for item in recent_checkins if item.adherence_score is not None]
    avg_adherence = round(sum(adherence_scores) / len(adherence_scores), 2) if adherence_scores else None
    recent_fault_counts: list[int] = []
    for review in recent_reviews:
        summary = review.summary if isinstance(review.summary, dict) else {}
        recent_fault_counts.append(int(summary.get("faulty_exercise_count") or 0))
    avg_faulty_exercises = (
        round(sum(recent_fault_counts) / len(recent_fault_counts), 2) if recent_fault_counts else None
    )
    severe_soreness_groups = 0
    if latest_soreness and isinstance(latest_soreness.severity_by_muscle, dict):
        severe_soreness_groups = sum(
            1
            for value in latest_soreness.severity_by_muscle.values()
            if str(value).strip().lower() == "severe"
        )
    checkin_count = len(recent_checkins)
    review_count = len(recent_reviews)
    evidence_points = checkin_count + review_count
    if evidence_points >= 6:
        policy_confidence = "high"
    elif evidence_points >= 3:
        policy_confidence = "medium"
    else:
        policy_confidence = "low"

    policy_reason = "stable_signals"
    policy_band = "progressive"
    downshift_guardrail_active = False
    if severe_soreness_groups >= 3:
        policy_band = "conservative"
        policy_reason = "high_severe_soreness"
        downshift_guardrail_active = True
    elif avg_adherence is not None and avg_adherence <= 2:
        policy_band = "conservative"
        policy_reason = "low_adherence"
        downshift_guardrail_active = True
    elif avg_faulty_exercises is not None and avg_faulty_exercises >= 2:
        policy_band = "conservative"
        policy_reason = "high_faulty_exercise_count"
        downshift_guardrail_active = True
    elif policy_confidence == "low":
        policy_band = "conservative"
        policy_reason = "sparse_adaptive_signals"

    return {
        "window_checkins": checkin_count,
        "window_reviews": review_count,
        "average_adherence_score": avg_adherence,
        "average_faulty_exercise_count": avg_faulty_exercises,
        "latest_severe_soreness_group_count": severe_soreness_groups,
        "policy_band": policy_band,
        "policy_reason": policy_reason,
        "policy_confidence": policy_confidence,
        "downshift_guardrail_active": downshift_guardrail_active,
    }


def _resolve_latest_binding_plan(
    prior_plans: list[WorkoutPlan],
    *,
    binding_id: str,
) -> WorkoutPlan | None:
    matching_plans = [
        plan
        for plan in prior_plans
        if resolve_selected_program_binding_id(
            (plan.payload if isinstance(plan.payload, dict) else {}).get("program_template_id")
        )
        == binding_id
    ]
    return matching_plans[0] if matching_plans else None


def _resolve_generation_week_context(
    prior_plans: list[WorkoutPlan],
    *,
    binding_id: str,
    generation_mode: GenerationMode,
) -> tuple[list[WorkoutPlan], date | None]:
    latest_binding_plan = _resolve_latest_binding_plan(prior_plans, binding_id=binding_id)
    monday = date.today() - timedelta(days=date.today().weekday())
    if generation_mode == "next_week_advance":
        if latest_binding_plan is not None:
            return prior_plans, latest_binding_plan.week_start + timedelta(days=7)
        return prior_plans, monday + timedelta(days=7)
    if latest_binding_plan is None:
        return prior_plans, monday
    current_week_start = monday
    has_current_week_plan = latest_binding_plan.week_start >= current_week_start
    if not has_current_week_plan:
        return prior_plans, current_week_start
    filtered_prior_plans = [
        plan
        for plan in prior_plans
        if not (
            resolve_selected_program_binding_id(
                (plan.payload if isinstance(plan.payload, dict) else {}).get("program_template_id")
            )
            == binding_id
            and plan.week_start == current_week_start
        )
    ]
    return filtered_prior_plans, current_week_start


def _apply_week_start_override_to_plan(
    *,
    base_plan: dict[str, Any],
    week_start_override: date | None,
) -> dict[str, Any]:
    if week_start_override is None:
        return base_plan
    current_week_start = date.fromisoformat(str(base_plan.get("week_start") or ""))
    if current_week_start == week_start_override:
        return base_plan
    shifted_plan = deepcopy(base_plan)
    delta_days = (week_start_override - current_week_start).days
    shifted_plan["week_start"] = week_start_override.isoformat()
    for session in shifted_plan.get("sessions") or []:
        if not isinstance(session, dict):
            continue
        session_date = str(session.get("date") or "").strip()
        if not session_date:
            continue
        session["date"] = (date.fromisoformat(session_date) + timedelta(days=delta_days)).isoformat()
    return shifted_plan


def _build_authored_adapted_sessions(
    *,
    preview_week: dict[str, Any],
    onboarding_week: dict[str, Any] | None,
    runtime_week_sessions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    onboarding_days = [
        day
        for day in (onboarding_week or {}).get("days") or []
        if isinstance(day, dict)
    ]
    indexed_sessions = runtime_week_sessions[: len(onboarding_days)] if onboarding_days else runtime_week_sessions
    source_day_lookup: dict[str, dict[str, Any]] = {}
    for index, runtime_session in enumerate(indexed_sessions):
        onboarding_day = onboarding_days[index] if index < len(onboarding_days) else {}
        day_id = str(onboarding_day.get("day_id") or f"d{index + 1}").strip()
        source_day_lookup[day_id] = {
            "day_name": str(
                onboarding_day.get("day_name")
                or onboarding_day.get("label")
                or runtime_session.get("name")
                or day_id
            ).strip(),
            "day_role": str(onboarding_day.get("day_role") or runtime_session.get("day_role") or "").strip() or None,
            "session": runtime_session,
        }

    adapted_sessions: list[dict[str, Any]] = []
    for adapted_index, adapted_day in enumerate(preview_week.get("adapted_days") or []):
        if not isinstance(adapted_day, dict):
            continue
        source_day_ids = [
            str(item).strip()
            for item in adapted_day.get("source_day_ids") or []
            if str(item).strip() and str(item).strip() in source_day_lookup
        ]
        anchor_id = str(adapted_day.get("day_id") or "").strip()
        anchor_source = source_day_lookup.get(anchor_id) or (source_day_lookup.get(source_day_ids[0]) if source_day_ids else None)
        if anchor_source is None:
            continue

        selected_exercises: list[dict[str, Any]] = []
        merge_source_day_ids = source_day_ids or ([anchor_id] if anchor_id in source_day_lookup else [])
        for source_day_id in merge_source_day_ids:
            source_session = cast(dict[str, Any], source_day_lookup[source_day_id]["session"])
            selected_exercises.extend(
                deepcopy(exercise)
                for exercise in source_session.get("exercises") or []
                if isinstance(exercise, dict)
            )
        if not selected_exercises:
            continue

        source_names = [str(source_day_lookup[day_id]["day_name"]).strip() for day_id in source_day_ids if day_id in source_day_lookup]
        day_name = str(adapted_day.get("day_name") or "").strip()
        if not day_name:
            day_name = " + ".join(source_names) if len(source_names) > 1 else (source_names[0] if source_names else str(anchor_source["day_name"]))

        day_role = str(adapted_day.get("day_role") or "").strip() or cast(str | None, anchor_source.get("day_role"))
        adapted_sessions.append(
            {
                "name": day_name,
                "day_role": day_role,
                "day_offset": min(6, int(cast(dict[str, Any], anchor_source["session"]).get("day_offset") or adapted_index)),
                "exercises": selected_exercises,
            }
        )

    return adapted_sessions


def _prepare_authored_frequency_adapted_template(
    *,
    selected_template_id: str,
    program_template: dict[str, Any],
    current_days_available: int,
    active_frequency_adaptation: dict[str, Any] | None,
    training_state: dict[str, Any],
    stored_weak_areas: list[str] | None,
    equipment_profile: list[str] | None,
    session_time_budget_minutes: int | None,
    movement_restrictions: list[str] | None,
    prior_generated_weeks: int,
    authored_week_index_override: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if not (is_authored_phase1_binding_id(selected_template_id) or is_authored_phase2_binding_id(selected_template_id)):
        return program_template, None

    onboarding_package = load_program_onboarding_package(selected_template_id)
    blueprint = cast(dict[str, Any], onboarding_package.get("blueprint") or {})
    default_training_days = int(
        blueprint.get("default_training_days")
        or len(cast(list[Any], (_resolve_onboarding_week(onboarding_package, week_index=1) or {}).get("days") or []))
        or current_days_available
    )
    target_days = int(active_frequency_adaptation.get("target_days") or current_days_available) if active_frequency_adaptation else int(current_days_available)

    trace: dict[str, Any] = {
        "interpreter": "prepare_authored_frequency_adapted_template",
        "selected_template_id": selected_template_id,
        "default_training_days": default_training_days,
        "target_days": target_days,
        "active_frequency_adaptation_present": bool(active_frequency_adaptation),
    }
    if target_days >= default_training_days:
        trace["status"] = "not_applied"
        trace["reason"] = "target_days_not_below_authored_default"
        return program_template, trace

    authored_weeks = program_template.get("authored_weeks") or []
    if not isinstance(authored_weeks, list) or not authored_weeks:
        trace["status"] = "not_applied"
        trace["reason"] = "authored_weeks_missing"
        return program_template, trace

    authored_prior_family_weeks = _resolve_authored_prior_family_weeks(
        selected_template_id=selected_template_id,
        training_state=training_state,
        fallback_prior_family_weeks=prior_generated_weeks,
    )
    authored_week_index = (
        int(authored_week_index_override)
        if authored_week_index_override is not None
        else _resolve_authored_week_index(
            program_template,
            prior_authored_family_weeks=authored_prior_family_weeks,
        )
    )
    authored_week_index = max(1, authored_week_index)
    authored_week_position = min(max(0, int(authored_prior_family_weeks)), len(authored_weeks) - 1)
    if authored_week_index_override is not None:
        authored_week_position = min(max(0, authored_week_index - 1), len(authored_weeks) - 1)
    selected_week = authored_weeks[authored_week_position] if isinstance(authored_weeks[authored_week_position], dict) else {}
    runtime_week_sessions = [
        session
        for session in selected_week.get("sessions") or []
        if isinstance(session, dict)
    ]
    onboarding_week = _resolve_onboarding_week(onboarding_package, week_index=authored_week_index)

    fatigue_state = cast(dict[str, Any], training_state.get("fatigue_state") or {})
    recovery_state = str(fatigue_state.get("recovery_state") or "normal").strip() or "normal"
    preview_payload = recommend_frequency_adaptation_preview(
        onboarding_package=onboarding_package,
        program_id=selected_template_id,
        template_id=selected_template_id,
        current_days=default_training_days,
        target_days=target_days,
        duration_weeks=1,
        explicit_weak_areas=list(active_frequency_adaptation.get("weak_areas") or []) if active_frequency_adaptation else None,
        stored_weak_areas=list(stored_weak_areas or []),
        equipment_profile=list(equipment_profile or []),
        recovery_state=recovery_state,
        current_week_index=authored_week_index,
        request_runtime_trace={
            "interpreter": "prepare_authored_frequency_adapted_template",
            "selected_template_id": selected_template_id,
            "authored_prior_family_weeks": authored_prior_family_weeks,
            "authored_week_index": authored_week_index,
        },
    )
    preview_week = cast(list[dict[str, Any]], preview_payload.get("weeks") or [])[:1]
    if not preview_week:
        trace["status"] = "not_applied"
        trace["reason"] = "preview_weeks_missing"
        trace["preview_trace"] = cast(dict[str, Any], preview_payload.get("decision_trace") or {})
        return program_template, trace

    adapted_sessions = _build_authored_adapted_sessions(
        preview_week=preview_week[0],
        onboarding_week=onboarding_week,
        runtime_week_sessions=runtime_week_sessions,
    )
    if not adapted_sessions:
        trace["status"] = "not_applied"
        trace["reason"] = "adapted_sessions_missing"
        trace["preview_trace"] = cast(dict[str, Any], preview_payload.get("decision_trace") or {})
        return program_template, trace

    adapted_template = deepcopy(program_template)
    adapted_template["sessions"] = deepcopy(adapted_sessions)
    passthrough_eligible = not list(movement_restrictions or [])
    if passthrough_eligible:
        adapted_template[AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY] = True
    adapted_weeks = cast(list[Any], adapted_template.get("authored_weeks") or [])
    if 0 <= authored_week_position < len(adapted_weeks) and isinstance(adapted_weeks[authored_week_position], dict):
        adapted_weeks[authored_week_position] = {
            **adapted_weeks[authored_week_position],
            "sessions": deepcopy(adapted_sessions),
        }
        adapted_template["authored_weeks"] = adapted_weeks

    trace["status"] = "applied"
    trace["authored_prior_family_weeks"] = authored_prior_family_weeks
    trace["authored_week_index"] = authored_week_index
    trace["authored_week_index_override"] = authored_week_index_override
    trace["session_count"] = len(adapted_sessions)
    trace["authoritative_passthrough_eligible"] = passthrough_eligible
    trace["preview_trace"] = cast(dict[str, Any], preview_payload.get("decision_trace") or {})
    return adapted_template, trace


def _prepare_plan_generation_runtime(
    *,
    db: Session,
    current_user: User,
    selected_template_id: str,
    effective_days_available: int,
    active_frequency_adaptation: dict[str, Any] | None,
    prior_plans_override: list[WorkoutPlan] | None = None,
    latest_plan_override: WorkoutPlan | None = None,
) -> dict[str, Any]:
    history_rows = (
        db.query(WorkoutSetLog)
        .filter(WorkoutSetLog.user_id == current_user.id)
        .order_by(WorkoutSetLog.created_at.desc())
        .limit(100)
        .all()
    )
    exercise_states = db.query(ExerciseState).filter(ExerciseState.user_id == current_user.id).all()
    prior_plans = list(prior_plans_override) if prior_plans_override is not None else _list_user_workout_plans(db, user_id=current_user.id)
    latest_plan = latest_plan_override
    if latest_plan is None and prior_plans:
        latest_plan = max(prior_plans, key=lambda plan: plan.created_at)

    latest_soreness = (
        db.query(SorenessEntry)
        .filter(SorenessEntry.user_id == current_user.id, SorenessEntry.entry_date <= date.today())
        .order_by(SorenessEntry.entry_date.desc(), SorenessEntry.created_at.desc())
        .first()
    )
    latest_checkin = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.user_id == current_user.id, WeeklyCheckin.week_start <= date.today())
        .order_by(WeeklyCheckin.week_start.desc(), WeeklyCheckin.created_at.desc())
        .first()
    )
    recent_review_cycles = (
        db.query(WeeklyReviewCycle)
        .filter(WeeklyReviewCycle.user_id == current_user.id)
        .order_by(WeeklyReviewCycle.reviewed_on.desc(), WeeklyReviewCycle.created_at.desc())
        .limit(3)
        .all()
    )
    runtime = prepare_plan_generation_decision_runtime(
        selected_template_id=selected_template_id,
        current_days_available=effective_days_available,
        active_frequency_adaptation=active_frequency_adaptation,
        selected_program_id=current_user.selected_program_id,
        split_preference=current_user.split_preference,
        training_location=current_user.training_location,
        equipment_profile=list(current_user.equipment_profile or []),
        weak_areas=list(current_user.weak_areas or []),
        nutrition_phase=current_user.nutrition_phase,
        session_time_budget_minutes=current_user.session_time_budget_minutes,
        movement_restrictions=list(current_user.movement_restrictions or []),
        near_failure_tolerance=current_user.near_failure_tolerance,
        latest_plan=latest_plan,
        latest_soreness_entry=latest_soreness,
        recent_workout_logs=history_rows,
        exercise_states=exercise_states,
        recent_checkins=[latest_checkin] if latest_checkin is not None else [],
        recent_review_cycles=recent_review_cycles,
        prior_plans=prior_plans,
        build_plan_decision_training_state=build_plan_decision_training_state,
    )
    return runtime


@router.get("/plan/programs", response_model=list[ProgramTemplateSummary])
def plan_list_programs() -> list[dict]:
    return _list_active_program_templates()


@router.get("/plan/guides/programs")
def list_guide_programs() -> list[GuideProgramSummary]:
    return [GuideProgramSummary(**payload) for payload in build_guide_programs_payload(_list_active_program_templates())]


@router.get("/plan/guides/programs/{program_id}", responses=GUIDE_RESPONSES)
def get_program_guide(program_id: str) -> ProgramGuideResponse:
    resolved_program_id = resolve_linked_program_id(program_id)
    try:
        summary = resolve_program_guide_summary(
            program_id=resolved_program_id,
            available_program_summaries=_list_active_program_templates(),
        )
        template = load_program_template(resolved_program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    return ProgramGuideResponse(**build_program_guide_payload(program_id=resolved_program_id, program_summary=summary, template=template))


@router.get("/plan/guides/programs/{program_id}/days/{day_index}", responses=GUIDE_RESPONSES)
def get_program_day_guide(program_id: str, day_index: int) -> ProgramDayGuideResponse:
    resolved_program_id = resolve_linked_program_id(program_id)
    try:
        template = load_program_template(resolved_program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    try:
        payload = build_program_day_guide_payload(program_id=resolved_program_id, template=template, day_index=day_index)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="Guide day not found")
    return ProgramDayGuideResponse(**payload)


@router.get("/plan/guides/programs/{program_id}/exercise/{exercise_id}", responses=GUIDE_RESPONSES)
def get_program_exercise_guide(program_id: str, exercise_id: str) -> ProgramExerciseGuideResponse:
    resolved_program_id = resolve_linked_program_id(program_id)
    try:
        template = load_program_template(resolved_program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    exercise = resolve_program_exercise_guide(template=template, exercise_id=exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Guide exercise not found")
    return ProgramExerciseGuideResponse(**build_program_exercise_guide_payload(program_id=resolved_program_id, exercise=exercise))


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _resolve_preview_recommendation(db: Session, *, user_id: str, recommendation_id: str) -> CoachingRecommendation:
    recommendation = (
        db.query(CoachingRecommendation)
        .filter(
            CoachingRecommendation.id == recommendation_id,
            CoachingRecommendation.user_id == user_id,
            CoachingRecommendation.recommendation_type == "coach_preview",
        )
        .first()
    )
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return recommendation


def _apply_coaching_decision_route(
    *,
    db: Session,
    current_user: User,
    recommendation_id: str,
    confirm: bool,
    decision_kind: Literal["phase", "specialization"],
) -> dict[str, Any]:
    source_recommendation = _resolve_preview_recommendation(
        db,
        user_id=current_user.id,
        recommendation_id=recommendation_id,
    )
    source_runtime = prepare_coaching_apply_runtime_source(source_recommendation)
    try:
        route_runtime = prepare_coaching_apply_route_runtime(
            decision_kind=decision_kind,
            source_runtime=source_runtime,
            confirm=confirm,
            user_id=current_user.id,
            applied_at=_utcnow_naive(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not confirm:
        finalized_runtime = prepare_coaching_apply_route_finalize_runtime(
            route_runtime=route_runtime,
        )
        return cast(dict[str, Any], finalized_runtime["response_payload"])

    commit_runtime = cast(dict[str, Any], route_runtime["commit_runtime"])
    applied_record = CoachingRecommendation(
        **cast(dict[str, Any], commit_runtime["record_values"])
    )
    db.add(applied_record)
    db.flush()

    finalized_runtime = prepare_coaching_apply_route_finalize_runtime(
        route_runtime=route_runtime,
        applied_recommendation_id=applied_record.id,
    )
    recommendation_payload = cast(dict[str, Any] | None, finalized_runtime["recommendation_payload"])
    if recommendation_payload is not None:
        applied_record.recommendation_payload = recommendation_payload

    db.commit()
    return cast(dict[str, Any], finalized_runtime["response_payload"])


@router.get(
    "/plan/intelligence/recommendations",
    response_model=CoachingRecommendationTimelineResponse,
)
def list_coaching_recommendations(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = 20,
) -> CoachingRecommendationTimelineResponse:
    capped_limit = normalize_coaching_recommendation_timeline_limit(limit)
    rows = (
        db.query(CoachingRecommendation)
        .filter(CoachingRecommendation.user_id == current_user.id)
        .order_by(CoachingRecommendation.created_at.desc())
        .limit(capped_limit)
        .all()
    )

    timeline_payload = build_coaching_recommendation_timeline_payload(rows)
    entries = [CoachingRecommendationTimelineEntry(**entry) for entry in cast(list[dict[str, Any]], timeline_payload["entries"])]
    return CoachingRecommendationTimelineResponse(entries=entries)


@router.post(
    "/plan/intelligence/apply-phase",
    response_model=ApplyPhaseDecisionResponse,
    responses={404: {"description": "Recommendation not found"}},
)
def apply_phase_decision(
    payload: ApplyPhaseDecisionRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ApplyPhaseDecisionResponse:
    response_payload = _apply_coaching_decision_route(
        db=db,
        current_user=current_user,
        recommendation_id=payload.recommendation_id,
        confirm=payload.confirm,
        decision_kind="phase",
    )
    return ApplyPhaseDecisionResponse(**response_payload)


@router.post(
    "/plan/intelligence/apply-specialization",
    response_model=ApplySpecializationDecisionResponse,
    responses={404: {"description": "Recommendation not found"}},
)
def apply_specialization_decision(
    payload: ApplySpecializationDecisionRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ApplySpecializationDecisionResponse:
    response_payload = _apply_coaching_decision_route(
        db=db,
        current_user=current_user,
        recommendation_id=payload.recommendation_id,
        confirm=payload.confirm,
        decision_kind="specialization",
    )
    return ApplySpecializationDecisionResponse(**response_payload)


@router.post(
    "/plan/intelligence/coach-preview",
    response_model=IntelligenceCoachPreviewResponse,
    responses={
        400: {"description": PROFILE_INCOMPLETE_DETAIL},
        404: {"description": "Program template not found"},
        422: {"description": "Program template schema is invalid"},
    },
)
def coach_intelligence_preview(
    payload: IntelligenceCoachPreviewRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> IntelligenceCoachPreviewResponse:
    if not current_user.split_preference:
        raise HTTPException(status_code=400, detail=PROFILE_INCOMPLETE_DETAIL)

    preview_runtime = prepare_coach_preview_runtime_inputs(
        preview_request=payload.model_dump(mode="json"),
        profile_days_available=current_user.days_available,
    )
    preview_request = cast(dict[str, Any], preview_runtime["preview_request"])
    explicit_template_id = resolve_selected_program_binding_id(payload.template_id) if payload.template_id else None
    profile_template_id = resolve_selected_program_binding_id(current_user.selected_program_id)

    try:
        template_runtime = prepare_generation_template_runtime(
            explicit_template_id=explicit_template_id,
            profile_template_id=profile_template_id,
            split_preference=current_user.split_preference,
            days_available=int(preview_runtime["max_requested_days"]),
            nutrition_phase=current_user.nutrition_phase or "maintenance",
            available_equipment=current_user.equipment_profile or [],
            candidate_summaries=_list_active_program_templates(),
            load_template=load_program_template,
            ignored_loader_exceptions=(FileNotFoundError, KeyError, ValidationError),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    selected_template_id = cast(str, template_runtime["selected_template_id"])
    template = cast(dict[str, Any], template_runtime["selected_template"])
    latest_plan = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == current_user.id)
        .order_by(WorkoutPlan.created_at.desc())
        .first()
    )

    history_rows = (
        db.query(WorkoutSetLog)
        .filter(WorkoutSetLog.user_id == current_user.id)
        .order_by(WorkoutSetLog.created_at.desc())
        .limit(100)
        .all()
    )
    latest_checkin = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.user_id == current_user.id, WeeklyCheckin.week_start <= date.today())
        .order_by(WeeklyCheckin.week_start.desc(), WeeklyCheckin.created_at.desc())
        .first()
    )
    preview_context_runtime = prepare_coach_preview_decision_context(
        user_name=current_user.name,
        split_preference=current_user.split_preference,
        template=template,
        latest_plan=latest_plan,
        recent_workout_logs=history_rows,
        recent_checkins=[latest_checkin] if latest_checkin is not None else [],
        selected_program_id=profile_template_id,
        nutrition_phase=current_user.nutrition_phase,
        available_equipment=current_user.equipment_profile,
        build_plan_decision_training_state=build_plan_decision_training_state,
        build_coach_preview_context=build_coach_preview_context,
    )

    rule_set = resolve_optional_rule_set(
        template_id=selected_template_id,
        resolve_linked_program_id=resolve_rule_program_id,
        load_rule_set=load_program_rule_set,
    )
    program_name = resolve_program_display_name(
        program_id=selected_template_id,
        available_program_summaries=list_program_templates(active_only=False),
    )
    route_runtime = prepare_coach_preview_route_runtime(
        user_id=current_user.id,
        template_id=selected_template_id,
        context=cast(dict[str, Any], preview_context_runtime["context"]),
        preview_request=preview_request,
        rule_set=rule_set,
        request_runtime_trace=cast(dict[str, Any], preview_runtime["decision_trace"]),
        template_runtime_trace=cast(dict[str, Any], template_runtime["decision_trace"]),
        program_name=program_name,
        recommend_coach_intelligence_preview=recommend_coach_intelligence_preview,
        prepare_coach_preview_commit_runtime=prepare_coach_preview_commit_runtime,
    )
    commit_runtime = cast(dict[str, Any], route_runtime["commit_runtime"])
    recommendation_record = CoachingRecommendation(
        **cast(dict[str, Any], commit_runtime["record_values"]),
    )
    db.add(recommendation_record)
    db.flush()

    payloads = finalize_coach_preview_commit_runtime(
        prepared_runtime=commit_runtime,
        recommendation_id=recommendation_record.id,
    )
    response_model = IntelligenceCoachPreviewResponse(**payloads["response_payload"])

    recommendation_record.recommendation_payload = response_model.model_dump(mode="json")
    db.commit()

    return response_model


@router.post(
    "/plan/adaptation/preview",
    response_model=FrequencyAdaptationResult,
    responses={
        400: {"description": PROFILE_INCOMPLETE_DETAIL},
        404: {"description": "Onboarding package not found"},
    },
)
def preview_frequency_adaptation(
    payload: FrequencyAdaptationPreviewRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> FrequencyAdaptationResult:
    if not current_user.days_available or not current_user.split_preference:
        raise HTTPException(status_code=400, detail=PROFILE_INCOMPLETE_DETAIL)
    log_event(
        "frequency_adaptation_preview_requested",
        route="/plan/adaptation/preview",
        action="preview_frequency_adaptation",
        user_id=current_user.id,
        selected_program_id=resolve_selected_program_binding_id(current_user.selected_program_id),
        template_id=resolve_selected_program_binding_id(payload.program_id),
        target_days=payload.target_days,
        days_available=current_user.days_available,
    )

    latest_plan = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == current_user.id)
        .order_by(WorkoutPlan.created_at.desc())
        .first()
    )
    latest_soreness = (
        db.query(SorenessEntry)
        .filter(SorenessEntry.user_id == current_user.id, SorenessEntry.entry_date <= date.today())
        .order_by(SorenessEntry.entry_date.desc(), SorenessEntry.created_at.desc())
        .first()
    )
    adaptation_decision_runtime = prepare_frequency_adaptation_decision_runtime(
        requested_program_id=resolve_selected_program_binding_id(payload.program_id),
        selected_program_id=resolve_selected_program_binding_id(current_user.selected_program_id),
        latest_plan=latest_plan,
        latest_soreness_entry=latest_soreness,
        current_days_available=current_user.days_available,
        target_days=payload.target_days,
        duration_weeks=payload.duration_weeks,
        explicit_weak_areas=payload.weak_areas,
        stored_weak_areas=current_user.weak_areas or [],
        equipment_profile=current_user.equipment_profile or [],
        build_plan_decision_training_state=build_plan_decision_training_state,
    )
    adaptation_runtime = cast(dict[str, Any], adaptation_decision_runtime["adaptation_runtime"])
    onboarding_program_id = resolve_onboarding_program_id(
        template_id=str(adaptation_runtime["program_id"]),
        resolve_linked_program_id=resolve_loader_onboarding_program_id,
    )
    try:
        onboarding_package = load_program_onboarding_package(onboarding_program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    route_runtime = prepare_frequency_adaptation_route_runtime(
        adaptation_runtime=adaptation_runtime,
        onboarding_package=onboarding_package,
        decision_kind="preview",
    )
    raw_result = cast(dict[str, Any], route_runtime["preview_payload"])
    log_event(
        "frequency_adaptation_preview_completed",
        route="/plan/adaptation/preview",
        action="preview_frequency_adaptation",
        user_id=current_user.id,
        selected_program_id=resolve_selected_program_binding_id(current_user.selected_program_id),
        template_id=str(adaptation_runtime["program_id"]),
        path_family="generated" if is_generated_full_body_binding_id(str(adaptation_runtime["program_id"])) else "authored",
        target_days=payload.target_days,
        days_available=current_user.days_available,
    )
    return FrequencyAdaptationResult.model_validate(raw_result)


@router.post(
    "/plan/adaptation/apply",
    response_model=FrequencyAdaptationApplyResponse,
    responses={
        400: {"description": PROFILE_INCOMPLETE_DETAIL},
        404: {"description": "Onboarding package not found"},
    },
)
def apply_frequency_adaptation(
    payload: FrequencyAdaptationApplyRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> FrequencyAdaptationApplyResponse:
    if not current_user.days_available or not current_user.split_preference:
        raise HTTPException(status_code=400, detail=PROFILE_INCOMPLETE_DETAIL)
    log_event(
        "frequency_adaptation_apply_requested",
        route="/plan/adaptation/apply",
        action="apply_frequency_adaptation",
        user_id=current_user.id,
        selected_program_id=resolve_selected_program_binding_id(current_user.selected_program_id),
        template_id=resolve_selected_program_binding_id(payload.program_id),
        target_days=payload.target_days,
        days_available=current_user.days_available,
    )

    latest_plan = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == current_user.id)
        .order_by(WorkoutPlan.created_at.desc())
        .first()
    )
    latest_soreness = (
        db.query(SorenessEntry)
        .filter(SorenessEntry.user_id == current_user.id, SorenessEntry.entry_date <= date.today())
        .order_by(SorenessEntry.entry_date.desc(), SorenessEntry.created_at.desc())
        .first()
    )
    adaptation_decision_runtime = prepare_frequency_adaptation_decision_runtime(
        requested_program_id=resolve_selected_program_binding_id(payload.program_id),
        selected_program_id=resolve_selected_program_binding_id(current_user.selected_program_id),
        latest_plan=latest_plan,
        latest_soreness_entry=latest_soreness,
        current_days_available=current_user.days_available,
        target_days=payload.target_days,
        duration_weeks=payload.duration_weeks,
        explicit_weak_areas=payload.weak_areas,
        stored_weak_areas=current_user.weak_areas or [],
        equipment_profile=current_user.equipment_profile or [],
        build_plan_decision_training_state=build_plan_decision_training_state,
    )
    adaptation_runtime = cast(dict[str, Any], adaptation_decision_runtime["adaptation_runtime"])
    selected_template_id = str(adaptation_runtime["program_id"])
    onboarding_program_id = resolve_onboarding_program_id(
        template_id=selected_template_id,
        resolve_linked_program_id=resolve_loader_onboarding_program_id,
    )
    try:
        onboarding_package = load_program_onboarding_package(onboarding_program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    route_runtime = prepare_frequency_adaptation_route_runtime(
        adaptation_runtime=adaptation_runtime,
        onboarding_package=onboarding_package,
        decision_kind="apply",
        applied_at=datetime.now().isoformat(),
    )

    current_user.active_frequency_adaptation = cast(dict[str, Any], route_runtime["persistence_state"])
    db.add(current_user)
    db.commit()

    response_model = FrequencyAdaptationApplyResponse(**cast(dict[str, Any], route_runtime["response_payload"]))
    log_event(
        "frequency_adaptation_apply_completed",
        route="/plan/adaptation/apply",
        action="apply_frequency_adaptation",
        user_id=current_user.id,
        selected_program_id=resolve_selected_program_binding_id(current_user.selected_program_id),
        template_id=response_model.program_id,
        path_family="generated" if is_generated_full_body_binding_id(response_model.program_id) else "authored",
        target_days=response_model.target_days,
        days_available=current_user.days_available,
    )
    return response_model


def _build_week_plan_runtime_for_user(
    *,
    db: Session,
    current_user: User,
    explicit_template_id: str | None,
    target_days_override: int | None = None,
    generation_mode: GenerationMode = "current_week_regenerate",
) -> dict[str, Any]:
    effective_days_available = _resolve_effective_days_available(
        current_days_available=current_user.days_available,
        target_days_override=target_days_override,
    )
    profile_template_id = resolve_selected_program_binding_id(current_user.selected_program_id)
    normalized_explicit_template_id = resolve_selected_program_binding_id(explicit_template_id) if explicit_template_id else None
    program_recommendation_trace: dict[str, Any] | None = None
    choose_for_me_trace: dict[str, Any] | None = None
    adaptive_signal_summary = _build_adaptive_signal_summary(db=db, user_id=current_user.id)

    auto_mode = (current_user.program_selection_mode or "manual") == "auto"
    if auto_mode and normalized_explicit_template_id is None:
        preferred_family = str(current_user.choose_for_me_family or "").strip().lower() or None
        preferred_family_template = _resolve_choose_for_me_family_template(preferred_family)
        preferred_family_target_days = _resolve_choose_for_me_family_target_days(preferred_family)
        effective_days_adjusted = False
        effective_days_adjustment_reason = ""
        if preferred_family_target_days is not None and effective_days_available >= preferred_family_target_days:
            effective_days_available = preferred_family_target_days
            effective_days_adjusted = True
            effective_days_adjustment_reason = "family_target_days"
        latest_plan = (
            db.query(WorkoutPlan)
            .filter(WorkoutPlan.user_id == current_user.id)
            .order_by(WorkoutPlan.created_at.desc())
            .first()
        )
        recent_checkins = (
            db.query(WeeklyCheckin)
            .filter(WeeklyCheckin.user_id == current_user.id)
            .order_by(WeeklyCheckin.week_start.desc(), WeeklyCheckin.created_at.desc())
            .limit(4)
            .all()
        )
        recent_reviews = (
            db.query(WeeklyReviewCycle)
            .filter(WeeklyReviewCycle.user_id == current_user.id)
            .order_by(WeeklyReviewCycle.week_start.desc(), WeeklyReviewCycle.created_at.desc())
            .limit(4)
            .all()
        )

        training_state = build_plan_decision_training_state(
            selected_program_id=current_user.selected_program_id,
            days_available=effective_days_available,
            split_preference=current_user.split_preference,
            training_location=current_user.training_location,
            equipment_profile=current_user.equipment_profile or [],
            weak_areas=current_user.weak_areas or [],
            nutrition_phase=current_user.nutrition_phase,
            session_time_budget_minutes=current_user.session_time_budget_minutes,
            movement_restrictions=list(current_user.movement_restrictions or []),
            near_failure_tolerance=current_user.near_failure_tolerance,
            latest_plan=latest_plan,
            latest_soreness_entry=None,
            recent_workout_logs=[],
            recent_checkins=recent_checkins,
            recent_review_cycles=recent_reviews,
            prior_plans=[],
        )

        route_runtime = prepare_profile_program_recommendation_route_runtime(
            selected_program_id=resolve_selected_program_binding_id(current_user.selected_program_id),
            days_available=effective_days_available,
            split_preference=current_user.split_preference,
            latest_plan=latest_plan,
            available_program_summaries=list_program_templates(),
            latest_adherence_score=None,
            user_training_state=training_state,
            generated_at=datetime.now(UTC),
        )

        recommendation_runtime = cast(dict[str, Any], route_runtime.get("recommendation_runtime") or {})
        response_payload = cast(dict[str, Any], recommendation_runtime.get("response_payload") or {})
        recommended_program_id = cast(str, response_payload.get("recommended_program_id") or "")
        program_recommendation_trace = cast(dict[str, Any], route_runtime.get("decision_trace") or {})

        choose_for_me_trace = {
            "preferred_family": preferred_family,
            "preferred_family_template": preferred_family_template,
            "preferred_family_target_days": preferred_family_target_days,
            "effective_days_adjusted": effective_days_adjusted,
            "effective_days_adjustment_reason": effective_days_adjustment_reason or None,
            "adaptive_signal_summary": adaptive_signal_summary,
            "engine_recommended_program_id": recommended_program_id,
        }

        if (
            adaptive_signal_summary.get("policy_band") == "conservative"
            and bool(adaptive_signal_summary.get("downshift_guardrail_active"))
            and effective_days_available > 2
        ):
            effective_days_available -= 1
            choose_for_me_trace["effective_days_adjusted"] = True
            choose_for_me_trace["effective_days_adjustment_reason"] = "conservative_policy_band_downshift"

        if preferred_family_template:
            active_ids = {str(item.get("id") or "") for item in _list_active_program_templates()}
            if preferred_family_template in active_ids:
                recommended_program_id = preferred_family_template
                choose_for_me_trace["family_preference_applied"] = True
            else:
                choose_for_me_trace["family_preference_applied"] = False
                choose_for_me_trace["family_preference_reason"] = "preferred_template_not_active"

        if recommended_program_id:
            current_user.selected_program_id = resolve_selected_program_binding_id(recommended_program_id) or recommended_program_id
            db.add(current_user)
            profile_template_id = resolve_selected_program_binding_id(current_user.selected_program_id)
            normalized_explicit_template_id = resolve_selected_program_binding_id(recommended_program_id) or recommended_program_id

        current_diagnostics = (
            dict(current_user.choose_for_me_diagnostics)
            if isinstance(current_user.choose_for_me_diagnostics, dict)
            else {}
        )
        current_diagnostics["adaptive_loop_v2"] = adaptive_signal_summary
        current_user.choose_for_me_diagnostics = current_diagnostics
        db.add(current_user)

    template_runtime = prepare_generation_template_runtime(
        explicit_template_id=normalized_explicit_template_id,
        profile_template_id=profile_template_id,
        split_preference=current_user.split_preference,
        days_available=effective_days_available,
        nutrition_phase=current_user.nutrition_phase or "maintenance",
        available_equipment=current_user.equipment_profile or [],
        candidate_summaries=_list_active_program_templates(),
        load_template=load_program_template,
        ignored_loader_exceptions=(FileNotFoundError, KeyError, ValidationError),
    )

    selected_template_id = cast(str, template_runtime["selected_template_id"])
    template = cast(dict[str, Any], template_runtime["selected_template"])
    template_selection_trace = cast(dict[str, Any], template_runtime["decision_trace"])
    if program_recommendation_trace is not None:
        template_selection_trace["program_recommendation_trace"] = program_recommendation_trace
    if choose_for_me_trace is not None:
        template_selection_trace["choose_for_me_trace"] = choose_for_me_trace
    weak_areas = [str(area).strip() for area in (current_user.weak_areas or []) if str(area).strip()]
    if weak_areas:
        template_selection_trace["weak_spot_focus_synthesis"] = {
            "focus_muscles": weak_areas[:3],
            "focus_day_priority": "high" if len(weak_areas) >= 2 else "moderate",
            "policy_band": adaptive_signal_summary.get("policy_band"),
            "reason": "weak_area_overlay_for_choose_for_me_generation",
        }
    rule_set = resolve_optional_rule_set(
        template_id=selected_template_id,
        resolve_linked_program_id=resolve_rule_program_id,
        load_rule_set=load_program_rule_set,
    )

    active_frequency_adaptation = None
    if target_days_override is None:
        active_state = dict(current_user.active_frequency_adaptation or {})
        if active_state:
            for key in ("template_id", "program_id"):
                normalized = resolve_selected_program_binding_id(str(active_state.get(key) or "").strip())
                if normalized:
                    active_state[key] = normalized
        active_frequency_adaptation = resolve_active_frequency_adaptation_runtime(
            active_state=active_state if active_state else None,
            selected_template_id=selected_template_id,
        )
    prior_plans = _list_user_workout_plans(db, user_id=current_user.id)
    authored_week_index_override: int | None = None
    if generation_mode == "current_week_regenerate":
        monday = date.today() - timedelta(days=date.today().weekday())
        current_week_binding_plans = [
            plan
            for plan in prior_plans
            if resolve_selected_program_binding_id(
                (plan.payload if isinstance(plan.payload, dict) else {}).get("program_template_id")
            )
            == selected_template_id
            and plan.week_start >= monday
        ]
        # Only pin authored week when there is a single unambiguous current-week row.
        if len(current_week_binding_plans) == 1:
            latest_payload = (
                current_week_binding_plans[0].payload
                if isinstance(current_week_binding_plans[0].payload, dict)
                else {}
            )
            latest_mesocycle = cast(dict[str, Any], latest_payload.get("mesocycle") or {})
            authored_candidate = latest_mesocycle.get("authored_week_index") or latest_mesocycle.get("week_index")
            try:
                authored_week_index_override = max(1, int(authored_candidate))
            except (TypeError, ValueError):
                authored_week_index_override = None

    filtered_prior_plans, week_start_override = _resolve_generation_week_context(
        prior_plans,
        binding_id=selected_template_id,
        generation_mode=generation_mode,
    )
    latest_plan = max(filtered_prior_plans, key=lambda plan: plan.created_at) if filtered_prior_plans else None
    generation_context = _prepare_plan_generation_runtime(
        db=db,
        current_user=current_user,
        selected_template_id=selected_template_id,
        effective_days_available=effective_days_available,
        active_frequency_adaptation=active_frequency_adaptation,
        prior_plans_override=filtered_prior_plans,
        latest_plan_override=latest_plan,
    )
    generation_runtime = cast(dict[str, Any], generation_context["generation_runtime"])
    runtime_template = template
    generated_full_body_adaptive_loop_policy = None
    generated_full_body_block_review_policy = None
    if is_generated_full_body_binding_id(selected_template_id):
        generated_runtime = prepare_generated_full_body_runtime_template(
            selected_template_id=selected_template_id,
            selected_template=template,
            profile_input=ProfileAssessmentInput(
                days_available=int(effective_days_available),
                split_preference=current_user.split_preference,
                training_location=current_user.training_location,
                equipment_profile=list(current_user.equipment_profile or []),
                weak_areas=list(current_user.weak_areas or []),
                session_time_budget_minutes=current_user.session_time_budget_minutes,
                movement_restrictions=list(current_user.movement_restrictions or []),
                near_failure_tolerance=current_user.near_failure_tolerance,
            ),
            training_state=cast(dict[str, Any], generation_context["training_state"]),
        )
        runtime_template = cast(dict[str, Any], generated_runtime["program_template"])
        generated_full_body_adaptive_loop_policy = generated_runtime.get("generated_full_body_adaptive_loop_policy")
        generated_full_body_block_review_policy = generated_runtime.get("generated_full_body_block_review_policy")
        template_selection_trace["generated_full_body_runtime_trace"] = cast(
            dict[str, Any], generated_runtime["generated_full_body_runtime_trace"]
        )
        log_event(
            "generation_path_selected",
            route="/plan/generate-week" if generation_mode == "current_week_regenerate" else "/plan/next-week",
            action="build_week_plan_runtime",
            user_id=current_user.id,
            selected_program_id=resolve_selected_program_binding_id(current_user.selected_program_id),
            template_id=selected_template_id,
            runtime_template_id=selected_template_id,
            path_family="generated",
            generation_mode=generation_mode,
            week_index=cast(dict[str, Any], generated_runtime["generated_full_body_runtime_trace"]).get("week_index"),
            authored_week_index=cast(dict[str, Any], generated_runtime["generated_full_body_runtime_trace"]).get("authored_week_index"),
            days_available=current_user.days_available,
            target_days=effective_days_available,
        )
    else:
        runtime_template, authored_adaptation_trace = _prepare_authored_frequency_adapted_template(
            selected_template_id=selected_template_id,
            program_template=template,
            current_days_available=effective_days_available,
            active_frequency_adaptation=active_frequency_adaptation,
            training_state=cast(dict[str, Any], generation_context["training_state"]),
            stored_weak_areas=list(current_user.weak_areas or []),
            equipment_profile=list(current_user.equipment_profile or []),
            session_time_budget_minutes=current_user.session_time_budget_minutes,
            movement_restrictions=list(current_user.movement_restrictions or []),
            prior_generated_weeks=int(generation_runtime.get("prior_generated_weeks") or 0),
            authored_week_index_override=authored_week_index_override,
        )
        if authored_adaptation_trace is not None:
            template_selection_trace["authored_frequency_adaptation_trace"] = authored_adaptation_trace
        log_event(
            "generation_path_selected",
            route="/plan/generate-week" if generation_mode == "current_week_regenerate" else "/plan/next-week",
            action="build_week_plan_runtime",
            user_id=current_user.id,
            selected_program_id=resolve_selected_program_binding_id(current_user.selected_program_id),
            template_id=selected_template_id,
            runtime_template_id=resolve_linked_program_id(selected_template_id),
            path_family="authored",
            generation_mode=generation_mode,
            days_available=current_user.days_available,
            target_days=effective_days_available,
            week_index=cast(dict[str, Any], template_selection_trace.get("authored_frequency_adaptation_trace") or {}).get("week_index"),
            authored_week_index=cast(dict[str, Any], template_selection_trace.get("authored_frequency_adaptation_trace") or {}).get("authored_week_index"),
        )
    scheduler_runtime = prepare_generate_week_scheduler_runtime(
        user_name=current_user.name,
        split_preference=current_user.split_preference,
        nutrition_phase=current_user.nutrition_phase,
        available_equipment=current_user.equipment_profile,
        generation_runtime=generation_runtime,
        program_template=runtime_template,
        rule_set=rule_set,
    )

    base_plan = generate_week_plan(**cast(dict[str, Any], scheduler_runtime["scheduler_kwargs"]))
    base_plan = _apply_week_start_override_to_plan(
        base_plan=base_plan,
        week_start_override=week_start_override,
    )
    review_lookup_runtime = prepare_generate_week_review_lookup_runtime(base_plan=base_plan)
    week_start = cast(date, review_lookup_runtime["week_start"])
    review_cycle = (
        db.query(WeeklyReviewCycle)
        .filter(WeeklyReviewCycle.user_id == current_user.id, WeeklyReviewCycle.week_start == week_start)
        .order_by(WeeklyReviewCycle.created_at.desc())
        .first()
    )
    finalize_runtime = prepare_generate_week_finalize_runtime(
        user_id=current_user.id,
        base_plan=base_plan,
        template_selection_trace=template_selection_trace,
        generation_runtime_trace=cast(dict[str, Any], generation_runtime["decision_trace"]),
        generated_adaptive_runtime={
            "training_state": cast(dict[str, Any], generation_context["training_state"]),
            "generation_runtime": generation_runtime,
            "adaptive_policy": cast(dict[str, Any] | None, generated_full_body_adaptive_loop_policy),
            "block_review_policy": cast(dict[str, Any] | None, generated_full_body_block_review_policy),
        }
        if generated_full_body_adaptive_loop_policy is not None
        else None,
        selected_template_id=selected_template_id,
        active_frequency_adaptation=active_frequency_adaptation,
        review_cycle=review_cycle,
    )
    return {
        "selected_template_id": selected_template_id,
        "response_payload": cast(dict[str, Any], finalize_runtime["response_payload"]),
        "record_values": cast(dict[str, Any], finalize_runtime["record_values"]),
        "adaptation_persistence_payload": cast(dict[str, Any], finalize_runtime["adaptation_persistence_payload"]),
        "replace_current_week": generation_mode == "current_week_regenerate",
    }


def _persist_week_plan_runtime(
    *,
    db: Session,
    current_user: User,
    plan_runtime: dict[str, Any],
) -> WorkoutPlan:
    adaptation_persistence_payload = cast(dict[str, Any], plan_runtime["adaptation_persistence_payload"])
    if bool(adaptation_persistence_payload["state_updated"]):
        current_user.active_frequency_adaptation = cast(dict[str, Any] | None, adaptation_persistence_payload["next_state"])
        db.add(current_user)

    record_values = cast(dict[str, Any], plan_runtime["record_values"])
    if bool(plan_runtime.get("replace_current_week")):
        record_payload = cast(dict[str, Any], record_values.get("payload") or {})
        replace_binding_id = resolve_selected_program_binding_id(record_payload.get("program_template_id"))
        replace_week_start = cast(date, record_values["week_start"])
        rows_to_replace = (
            db.query(WorkoutPlan)
            .filter(WorkoutPlan.user_id == current_user.id, WorkoutPlan.week_start == replace_week_start)
            .all()
        )
        for existing_row in rows_to_replace:
            existing_payload = existing_row.payload if isinstance(existing_row.payload, dict) else {}
            existing_binding_id = resolve_selected_program_binding_id(existing_payload.get("program_template_id"))
            if existing_binding_id == replace_binding_id:
                db.delete(existing_row)

    record = WorkoutPlan(**record_values)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _ensure_latest_authored_plan_current_if_needed(
    *,
    db: Session,
    current_user: User,
) -> WorkoutPlan | None:
    selected_template_id = resolve_selected_program_binding_id(current_user.selected_program_id)
    if not (is_authored_phase1_binding_id(selected_template_id) or is_authored_phase2_binding_id(selected_template_id)):
        plans = _list_user_workout_plans(db, user_id=current_user.id)
        return plans[0] if plans else None

    plans = _list_user_workout_plans(db, user_id=current_user.id)
    latest_plan = plans[0] if plans else None
    if latest_plan is None or _has_user_workout_activity(db, user_id=current_user.id):
        return latest_plan

    latest_payload = latest_plan.payload if isinstance(latest_plan.payload, dict) else {}
    latest_payload_binding_id = resolve_selected_program_binding_id(latest_payload.get("program_template_id"))
    if latest_payload_binding_id != selected_template_id:
        return latest_plan

    candidate_runtime = _build_week_plan_runtime_for_user(
        db=db,
        current_user=current_user,
        explicit_template_id=selected_template_id,
        generation_mode="current_week_regenerate",
    )
    if _plan_payload_signature(latest_payload) == _plan_payload_signature(cast(dict[str, Any], candidate_runtime["response_payload"])):
        return latest_plan

    _delete_user_workout_plans_for_binding(
        db,
        user_id=current_user.id,
        binding_id=selected_template_id,
    )
    return _persist_week_plan_runtime(
        db=db,
        current_user=current_user,
        plan_runtime=candidate_runtime,
    )


def ensure_current_workout_plans_for_user(
    *,
    db: Session,
    current_user: User,
) -> list[WorkoutPlan]:
    _ensure_latest_authored_plan_current_if_needed(db=db, current_user=current_user)
    return _list_user_workout_plans(db, user_id=current_user.id)


def _generate_week_for_user(
    *,
    db: Session,
    current_user: User,
    explicit_template_id: str | None,
    target_days: int | None,
    generation_mode: GenerationMode,
) -> dict[str, Any]:
    route = "/plan/generate-week" if generation_mode == "current_week_regenerate" else "/plan/next-week"
    user_id = str(current_user.id)
    normalized_explicit_template_id = resolve_selected_program_binding_id(explicit_template_id) if explicit_template_id else None
    if normalized_explicit_template_id and resolve_selected_program_binding_id(current_user.selected_program_id) != normalized_explicit_template_id:
        current_user.selected_program_id = normalized_explicit_template_id
        db.add(current_user)
        db.flush()

    selected_program_id = resolve_selected_program_binding_id(current_user.selected_program_id)
    days_available = current_user.days_available
    log_event(
        "week_generate_requested" if generation_mode == "current_week_regenerate" else "week_next_requested",
        route=route,
        action="plan_generation",
        user_id=user_id,
        selected_program_id=selected_program_id,
        template_id=normalized_explicit_template_id or explicit_template_id,
        generation_mode=generation_mode,
        days_available=days_available,
        target_days=target_days,
    )
    try:
        plan_runtime = _build_week_plan_runtime_for_user(
            db=db,
            current_user=current_user,
            explicit_template_id=normalized_explicit_template_id,
            target_days_override=target_days,
            generation_mode=generation_mode,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    record = _persist_week_plan_runtime(
        db=db,
        current_user=current_user,
        plan_runtime=plan_runtime,
    )
    payload = cast(dict[str, Any], record.payload)
    mesocycle = cast(dict[str, Any], payload.get("mesocycle") or {})
    log_event(
        "week_regenerated_current" if generation_mode == "current_week_regenerate" else "week_advanced_next",
        route=route,
        action="plan_generation",
        user_id=user_id,
        selected_program_id=selected_program_id,
        template_id=payload.get("program_template_id"),
        runtime_template_id=payload.get("program_template_id"),
        generation_mode=generation_mode,
        path_family="generated" if is_generated_full_body_binding_id(str(payload.get("program_template_id") or "")) else "authored",
        week_index=mesocycle.get("week_index"),
        displayed_week_index=mesocycle.get("week_index"),
        authored_week_index=mesocycle.get("authored_week_index"),
        week_start=payload.get("week_start"),
        days_available=days_available,
        target_days=target_days,
    )
    return payload


@router.post(
    "/plan/generate-week",
    responses={
        400: {"description": PROFILE_INCOMPLETE_DETAIL},
        404: {"description": "Program template not found"},
        422: {"description": "Program template schema is invalid"},
    },
)
def plan_generate_week(
    payload: GenerateWeekPlanRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    if not current_user.days_available or not current_user.split_preference:
        raise HTTPException(status_code=400, detail=PROFILE_INCOMPLETE_DETAIL)
    explicit_template_id = resolve_selected_program_binding_id(payload.template_id) if payload.template_id else None
    return _generate_week_for_user(
        db=db,
        current_user=current_user,
        explicit_template_id=explicit_template_id,
        target_days=payload.target_days,
        generation_mode="current_week_regenerate",
    )


@router.post(
    "/plan/next-week",
    responses={
        400: {"description": PROFILE_INCOMPLETE_DETAIL},
        404: {"description": "Program template not found"},
        422: {"description": "Program template schema is invalid"},
    },
)
def plan_generate_next_week(
    payload: NextWeekPlanRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    if not current_user.days_available or not current_user.split_preference:
        raise HTTPException(status_code=400, detail=PROFILE_INCOMPLETE_DETAIL)
    explicit_template_id = resolve_selected_program_binding_id(payload.template_id) if payload.template_id else None
    return _generate_week_for_user(
        db=db,
        current_user=current_user,
        explicit_template_id=explicit_template_id,
        target_days=payload.target_days,
        generation_mode="next_week_advance",
    )


@router.get("/plan/latest-week")
def plan_latest_week(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """
    Return the most recent generated week plan for the current user.

    This mirrors the shape of the /plan/generate-week response but does not
    trigger a new generation.
    """
    log_event(
        "latest_week_fetch_started",
        route="/plan/latest-week",
        action="latest_week_fetch",
        user_id=current_user.id,
        selected_program_id=resolve_selected_program_binding_id(current_user.selected_program_id),
    )
    plans = ensure_current_workout_plans_for_user(db=db, current_user=current_user)
    latest_plan = plans[0] if plans else None
    if latest_plan is None:
        raise HTTPException(status_code=404, detail="No plan generated")

    payload = latest_plan.payload or {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="Latest plan payload is invalid")
    mesocycle = cast(dict[str, Any], payload.get("mesocycle") or {})
    log_event(
        "latest_week_fetched",
        route="/plan/latest-week",
        action="latest_week_fetch",
        user_id=current_user.id,
        selected_program_id=resolve_selected_program_binding_id(current_user.selected_program_id),
        template_id=payload.get("program_template_id"),
        runtime_template_id=payload.get("program_template_id"),
        path_family="generated" if is_generated_full_body_binding_id(str(payload.get("program_template_id") or "")) else "authored",
        week_index=mesocycle.get("week_index"),
        displayed_week_index=mesocycle.get("week_index"),
        authored_week_index=mesocycle.get("authored_week_index"),
        week_start=payload.get("week_start"),
    )
    return payload
