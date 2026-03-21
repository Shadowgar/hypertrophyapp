from datetime import UTC, date, datetime
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

from ..database import get_db
from ..deps import get_current_user
from ..generated_assessment_schema import ProfileAssessmentInput
from ..generated_full_body_runtime_adapter import (
    GENERATED_FULL_BODY_COMPATIBILITY_TEMPLATE_ID,
    prepare_generated_full_body_runtime_template,
)
from ..models import CoachingRecommendation, ExerciseState, SorenessEntry, User, WeeklyCheckin, WeeklyReviewCycle, WorkoutPlan, WorkoutSetLog
from ..program_loader import (
    list_program_templates,
    resolve_active_administered_program_id,
    load_program_onboarding_package,
    load_program_rule_set,
    load_program_template,
    resolve_administered_program_id,
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


def _list_active_program_templates() -> list[dict[str, Any]]:
    try:
        return list_program_templates(active_only=True)
    except TypeError:
        # Test monkeypatches may provide a no-arg lambda replacement.
        return cast(list[dict[str, Any]], list_program_templates())


def _prepare_plan_generation_runtime(
    *,
    db: Session,
    current_user: User,
    selected_template_id: str,
    active_frequency_adaptation: dict[str, Any] | None,
) -> dict[str, Any]:
    history_rows = (
        db.query(WorkoutSetLog)
        .filter(WorkoutSetLog.user_id == current_user.id)
        .order_by(WorkoutSetLog.created_at.desc())
        .limit(100)
        .all()
    )
    exercise_states = db.query(ExerciseState).filter(ExerciseState.user_id == current_user.id).all()
    prior_plans = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == current_user.id).all()
    latest_plan = max(prior_plans, key=lambda plan: plan.created_at) if prior_plans else None

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
        current_days_available=current_user.days_available,
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
    resolved_program_id = resolve_administered_program_id(program_id) or program_id
    try:
        summary = resolve_program_guide_summary(
            program_id=resolved_program_id,
            available_program_summaries=list_program_templates(active_only=False),
        )
        template = load_program_template(resolved_program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    return ProgramGuideResponse(**build_program_guide_payload(program_id=resolved_program_id, program_summary=summary, template=template))


@router.get("/plan/guides/programs/{program_id}/days/{day_index}", responses=GUIDE_RESPONSES)
def get_program_day_guide(program_id: str, day_index: int) -> ProgramDayGuideResponse:
    resolved_program_id = resolve_administered_program_id(program_id) or program_id
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
    resolved_program_id = resolve_administered_program_id(program_id) or program_id
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
    explicit_template_id = resolve_active_administered_program_id(payload.template_id) if payload.template_id else None
    profile_template_id = resolve_active_administered_program_id(current_user.selected_program_id)

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
        requested_program_id=resolve_active_administered_program_id(payload.program_id),
        selected_program_id=resolve_active_administered_program_id(current_user.selected_program_id),
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
        requested_program_id=resolve_active_administered_program_id(payload.program_id),
        selected_program_id=resolve_active_administered_program_id(current_user.selected_program_id),
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

    return FrequencyAdaptationApplyResponse(**cast(dict[str, Any], route_runtime["response_payload"]))


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
    explicit_template_id = resolve_administered_program_id(payload.template_id) if payload.template_id else None
    profile_template_id = resolve_active_administered_program_id(current_user.selected_program_id)
    program_recommendation_trace: dict[str, Any] | None = None

    auto_mode = (current_user.program_selection_mode or "manual") == "auto"
    if auto_mode and explicit_template_id is None:
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
            days_available=current_user.days_available,
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
            selected_program_id=resolve_active_administered_program_id(current_user.selected_program_id),
            days_available=current_user.days_available,
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

        if recommended_program_id:
            # Persist the recommendation so the current program matches reality.
            current_user.selected_program_id = recommended_program_id
            db.add(current_user)
            profile_template_id = resolve_active_administered_program_id(current_user.selected_program_id)
            explicit_template_id = recommended_program_id

    try:
        template_runtime = prepare_generation_template_runtime(
            explicit_template_id=explicit_template_id,
            profile_template_id=profile_template_id,
            split_preference=current_user.split_preference,
            days_available=current_user.days_available,
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
    template_selection_trace = cast(dict[str, Any], template_runtime["decision_trace"])
    if program_recommendation_trace is not None:
        template_selection_trace["program_recommendation_trace"] = program_recommendation_trace
    rule_set = resolve_optional_rule_set(
        template_id=selected_template_id,
        resolve_linked_program_id=resolve_rule_program_id,
        load_rule_set=load_program_rule_set,
    )

    active_state = dict(current_user.active_frequency_adaptation or {})
    if active_state:
        for key in ("template_id", "program_id"):
            normalized = resolve_active_administered_program_id(str(active_state.get(key) or "").strip())
            if normalized:
                active_state[key] = normalized
    active_frequency_adaptation = resolve_active_frequency_adaptation_runtime(
        active_state=active_state if active_state else None,
        selected_template_id=selected_template_id,
    )
    generation_context = _prepare_plan_generation_runtime(
        db=db,
        current_user=current_user,
        selected_template_id=selected_template_id,
        active_frequency_adaptation=active_frequency_adaptation,
    )
    generation_runtime = cast(dict[str, Any], generation_context["generation_runtime"])
    runtime_template = template
    generated_full_body_adaptive_loop_policy = None
    if selected_template_id == GENERATED_FULL_BODY_COMPATIBILITY_TEMPLATE_ID:
        generated_runtime = prepare_generated_full_body_runtime_template(
            selected_template_id=selected_template_id,
            selected_template=template,
            profile_input=ProfileAssessmentInput(
                days_available=int(current_user.days_available or 0),
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
        template_selection_trace["generated_full_body_runtime_trace"] = cast(
            dict[str, Any], generated_runtime["generated_full_body_runtime_trace"]
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
        }
        if generated_full_body_adaptive_loop_policy is not None
        else None,
        selected_template_id=selected_template_id,
        active_frequency_adaptation=active_frequency_adaptation,
        review_cycle=review_cycle,
    )
    plan = cast(dict[str, Any], finalize_runtime["response_payload"])
    adaptation_persistence_payload = cast(dict[str, Any], finalize_runtime["adaptation_persistence_payload"])
    if bool(adaptation_persistence_payload["state_updated"]):
        current_user.active_frequency_adaptation = cast(dict[str, Any] | None, adaptation_persistence_payload["next_state"])
        db.add(current_user)

    record = WorkoutPlan(**cast(dict[str, Any], finalize_runtime["record_values"]))
    db.add(record)
    db.commit()

    return plan


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
    latest_plan = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == current_user.id)
        .order_by(WorkoutPlan.created_at.desc())
        .first()
    )
    if latest_plan is None:
        raise HTTPException(status_code=404, detail="No plan generated")

    payload = latest_plan.payload or {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="Latest plan payload is invalid")
    return payload
