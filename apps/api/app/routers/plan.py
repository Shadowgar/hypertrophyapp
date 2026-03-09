from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from core_engine import (
    apply_active_frequency_adaptation_runtime,
    build_coach_preview_context,
    build_coach_preview_payloads,
    build_coach_preview_recommendation_record_fields,
    build_coaching_recommendation_timeline_entry,
    build_frequency_adaptation_apply_payload,
    build_generated_week_plan_payload,
    build_guide_programs_payload,
    build_program_day_guide_payload,
    build_program_exercise_guide_payload,
    build_program_guide_payload,
    build_user_training_state,
    format_program_display_name,
    prepare_coach_preview_runtime_inputs,
    prepare_coaching_apply_runtime_source,
    prepare_frequency_adaptation_runtime_inputs,
    finalize_applied_coaching_recommendation,
    prepare_generation_template_runtime,
    prepare_generated_week_review_overlay,
    resolve_program_guide_summary,
    prepare_phase_apply_runtime,
    prepare_specialization_apply_runtime,
    resolve_program_exercise_guide,
    resolve_week_generation_runtime_inputs,
    generate_week_plan,
    interpret_frequency_adaptation_apply,
    recommend_coach_intelligence_preview,
    recommend_frequency_adaptation_preview,
    resolve_active_frequency_adaptation_runtime,
)

from ..database import get_db
from ..deps import get_current_user
from ..models import CoachingRecommendation, ExerciseState, SorenessEntry, User, WeeklyCheckin, WeeklyReviewCycle, WorkoutPlan, WorkoutSetLog
from ..program_loader import list_program_templates, load_program_onboarding_package, load_program_rule_set, load_program_template, resolve_linked_program_id
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

def _resolve_program_name(program_id: str) -> str:
    summaries = list_program_templates()
    match = next((summary for summary in summaries if summary.get("id") == program_id), None)
    if isinstance(match, dict):
        name = str(match.get("name") or "").strip()
        if name:
            return name
    return format_program_display_name(program_id)


def _load_template_rule_set(template_id: str) -> dict[str, Any] | None:
    try:
        return load_program_rule_set(resolve_linked_program_id(template_id))
    except FileNotFoundError:
        return None


def _build_plan_decision_training_state(
    *,
    current_user: User,
    latest_plan: WorkoutPlan | None,
    latest_soreness: SorenessEntry | None,
    recent_logs: list[WorkoutSetLog] | None = None,
    recent_checkins: list[WeeklyCheckin] | None = None,
    recent_review_cycles: list[WeeklyReviewCycle] | None = None,
    prior_plans: list[WorkoutPlan] | None = None,
) -> dict[str, Any]:
    return build_user_training_state(
        selected_program_id=current_user.selected_program_id,
        latest_plan=latest_plan,
        recent_workout_logs=list(recent_logs or []),
        exercise_states=[],
        latest_soreness_entry=latest_soreness,
        recent_checkins=list(recent_checkins or []),
        recent_review_cycles=list(recent_review_cycles or []),
        prior_plans=list(prior_plans or []),
    )


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
    training_state = _build_plan_decision_training_state(
        current_user=current_user,
        latest_plan=latest_plan,
        latest_soreness=latest_soreness,
        recent_logs=history_rows,
        recent_checkins=[latest_checkin] if latest_checkin is not None else [],
        recent_review_cycles=recent_review_cycles,
        prior_plans=prior_plans,
    )
    generation_runtime = resolve_week_generation_runtime_inputs(
        selected_template_id=selected_template_id,
        current_days_available=current_user.days_available,
        active_frequency_adaptation=active_frequency_adaptation,
        user_training_state=training_state,
        history_rows=[],
        latest_soreness_entry=None,
        latest_checkin=None,
        prior_plans=[],
    )
    return {
        "training_state": training_state,
        "generation_runtime": generation_runtime,
    }


@router.get("/plan/programs", response_model=list[ProgramTemplateSummary])
def plan_list_programs() -> list[dict]:
    return list_program_templates()


@router.get("/plan/guides/programs")
def list_guide_programs() -> list[GuideProgramSummary]:
    return [GuideProgramSummary(**payload) for payload in build_guide_programs_payload(list_program_templates())]


@router.get("/plan/guides/programs/{program_id}", responses=GUIDE_RESPONSES)
def get_program_guide(program_id: str) -> ProgramGuideResponse:
    try:
        summary = resolve_program_guide_summary(
            program_id=program_id,
            available_program_summaries=list_program_templates(),
        )
        template = load_program_template(program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    return ProgramGuideResponse(**build_program_guide_payload(program_id=program_id, program_summary=summary, template=template))


@router.get("/plan/guides/programs/{program_id}/days/{day_index}", responses=GUIDE_RESPONSES)
def get_program_day_guide(program_id: str, day_index: int) -> ProgramDayGuideResponse:
    try:
        template = load_program_template(program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    try:
        payload = build_program_day_guide_payload(program_id=program_id, template=template, day_index=day_index)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="Guide day not found")
    return ProgramDayGuideResponse(**payload)


@router.get("/plan/guides/programs/{program_id}/exercise/{exercise_id}", responses=GUIDE_RESPONSES)
def get_program_exercise_guide(program_id: str, exercise_id: str) -> ProgramExerciseGuideResponse:
    try:
        template = load_program_template(program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    exercise = resolve_program_exercise_guide(template=template, exercise_id=exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Guide exercise not found")
    return ProgramExerciseGuideResponse(**build_program_exercise_guide_payload(program_id=program_id, exercise=exercise))


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


@router.get(
    "/plan/intelligence/recommendations",
    response_model=CoachingRecommendationTimelineResponse,
)
def list_coaching_recommendations(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = 20,
) -> CoachingRecommendationTimelineResponse:
    capped_limit = max(1, min(100, int(limit)))
    rows = (
        db.query(CoachingRecommendation)
        .filter(CoachingRecommendation.user_id == current_user.id)
        .order_by(CoachingRecommendation.created_at.desc())
        .limit(capped_limit)
        .all()
    )

    entries = [
        CoachingRecommendationTimelineEntry(
            **build_coaching_recommendation_timeline_entry(
                recommendation_id=row.id,
                recommendation_type=row.recommendation_type,
                status=row.status,
                template_id=row.template_id,
                current_phase=row.current_phase,
                recommended_phase=row.recommended_phase,
                progression_action=row.progression_action,
                recommendation_payload=row.recommendation_payload if isinstance(row.recommendation_payload, dict) else {},
                created_at=row.created_at,
                applied_at=row.applied_at,
            )
        )
        for row in rows
    ]
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
    source_recommendation = _resolve_preview_recommendation(
        db,
        user_id=current_user.id,
        recommendation_id=payload.recommendation_id,
    )
    source_runtime = prepare_coaching_apply_runtime_source(source_recommendation)

    try:
        runtime = prepare_phase_apply_runtime(
            recommendation_id=cast(str, source_runtime["recommendation_id"]),
            recommendation_payload=cast(dict[str, Any], source_runtime["recommendation_payload"]),
            fallback_next_phase=cast(str, source_runtime["recommended_phase"]),
            confirm=payload.confirm,
            template_id=cast(str, source_runtime["template_id"]),
            current_phase=cast(str, source_runtime["current_phase"]),
            progression_action=cast(str, source_runtime["progression_action"]),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not payload.confirm:
        return ApplyPhaseDecisionResponse(**runtime["decision_payload"])

    applied_record = CoachingRecommendation(
        user_id=current_user.id,
        recommendation_payload={},
        applied_at=_utcnow_naive(),
        **cast(dict[str, Any], runtime["record_fields"]),
    )
    db.add(applied_record)
    db.flush()

    finalized = finalize_applied_coaching_recommendation(
        payload_key="phase_transition",
        payload_value=cast(dict[str, Any], runtime["payload_value"]),
        decision_payload=cast(dict[str, Any], runtime["decision_payload"]),
        applied_recommendation_id=applied_record.id,
    )
    applied_record.recommendation_payload = finalized["recommendation_payload"]

    db.commit()

    return ApplyPhaseDecisionResponse(**finalized["response_payload"])


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
    source_recommendation = _resolve_preview_recommendation(
        db,
        user_id=current_user.id,
        recommendation_id=payload.recommendation_id,
    )
    source_runtime = prepare_coaching_apply_runtime_source(source_recommendation)
    try:
        runtime = prepare_specialization_apply_runtime(
            recommendation_id=cast(str, source_runtime["recommendation_id"]),
            recommendation_payload=cast(dict[str, Any], source_runtime["recommendation_payload"]),
            confirm=payload.confirm,
            template_id=cast(str, source_runtime["template_id"]),
            current_phase=cast(str, source_runtime["current_phase"]),
            recommended_phase=cast(str, source_runtime["recommended_phase"]),
            progression_action=cast(str, source_runtime["progression_action"]),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not payload.confirm:
        return ApplySpecializationDecisionResponse(**runtime["decision_payload"])

    applied_record = CoachingRecommendation(
        user_id=current_user.id,
        recommendation_payload={},
        applied_at=_utcnow_naive(),
        **cast(dict[str, Any], runtime["record_fields"]),
    )
    db.add(applied_record)
    db.flush()

    finalized = finalize_applied_coaching_recommendation(
        payload_key="specialization",
        payload_value=cast(dict[str, Any], runtime["payload_value"]),
        decision_payload=cast(dict[str, Any], runtime["decision_payload"]),
        applied_recommendation_id=applied_record.id,
    )
    applied_record.recommendation_payload = finalized["recommendation_payload"]

    db.commit()

    return ApplySpecializationDecisionResponse(**finalized["response_payload"])


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

    try:
        template_runtime = prepare_generation_template_runtime(
            explicit_template_id=payload.template_id,
            profile_template_id=current_user.selected_program_id,
            split_preference=current_user.split_preference,
            days_available=int(preview_runtime["max_requested_days"]),
            nutrition_phase=current_user.nutrition_phase or "maintenance",
            available_equipment=current_user.equipment_profile or [],
            candidate_summaries=list_program_templates(),
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
    training_state = _build_plan_decision_training_state(
        current_user=current_user,
        latest_plan=latest_plan,
        latest_soreness=None,
        recent_logs=history_rows,
    )

    rule_set = _load_template_rule_set(selected_template_id)
    preview_payload = recommend_coach_intelligence_preview(
        template_id=selected_template_id,
        context=build_coach_preview_context(
            user_name=current_user.name,
            split_preference=current_user.split_preference,
            template=template,
            history_rows=[],
            user_training_state=training_state,
            nutrition_phase=current_user.nutrition_phase or "maintenance",
            available_equipment=current_user.equipment_profile or [],
        ),
        preview_request=preview_request,
        rule_set=rule_set,
        request_runtime_trace=cast(dict[str, Any], preview_runtime["decision_trace"]),
        template_runtime_trace=cast(dict[str, Any], template_runtime["decision_trace"]),
    )

    recommendation_record = CoachingRecommendation(
        user_id=current_user.id,
        **build_coach_preview_recommendation_record_fields(
            template_id=selected_template_id,
            preview_request=preview_request,
            preview_payload=preview_payload,
        ),
    )
    db.add(recommendation_record)
    db.flush()

    payloads = build_coach_preview_payloads(
        recommendation_id=recommendation_record.id,
        preview_payload=preview_payload,
        program_name=_resolve_program_name(selected_template_id),
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
    training_state = _build_plan_decision_training_state(
        current_user=current_user,
        latest_plan=latest_plan,
        latest_soreness=latest_soreness,
    )
    adaptation_runtime = prepare_frequency_adaptation_runtime_inputs(
        requested_program_id=payload.program_id,
        selected_program_id=current_user.selected_program_id,
        user_training_state=training_state,
        current_days_available=current_user.days_available,
        target_days=payload.target_days,
        duration_weeks=payload.duration_weeks,
        explicit_weak_areas=payload.weak_areas,
        stored_weak_areas=current_user.weak_areas or [],
        equipment_profile=current_user.equipment_profile or [],
    )
    onboarding_program_id = resolve_linked_program_id(str(adaptation_runtime["program_id"]))
    try:
        onboarding_package = load_program_onboarding_package(onboarding_program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    raw_result = recommend_frequency_adaptation_preview(
        onboarding_package=onboarding_package,
        program_id=onboarding_program_id,
        current_days=int(adaptation_runtime["current_days"]),
        target_days=int(adaptation_runtime["target_days"]),
        duration_weeks=int(adaptation_runtime["duration_weeks"]),
        explicit_weak_areas=cast(list[str], adaptation_runtime["explicit_weak_areas"]),
        stored_weak_areas=cast(list[str], adaptation_runtime["stored_weak_areas"]),
        equipment_profile=cast(list[str], adaptation_runtime["equipment_profile"]),
        recovery_state=str(adaptation_runtime["recovery_state"]),
        current_week_index=int(adaptation_runtime["current_week_index"]),
        request_runtime_trace=cast(dict[str, Any], adaptation_runtime["decision_trace"]),
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
    training_state = _build_plan_decision_training_state(
        current_user=current_user,
        latest_plan=latest_plan,
        latest_soreness=latest_soreness,
    )
    adaptation_runtime = prepare_frequency_adaptation_runtime_inputs(
        requested_program_id=payload.program_id,
        selected_program_id=current_user.selected_program_id,
        user_training_state=training_state,
        current_days_available=current_user.days_available,
        target_days=payload.target_days,
        duration_weeks=payload.duration_weeks,
        explicit_weak_areas=payload.weak_areas,
        stored_weak_areas=current_user.weak_areas or [],
        equipment_profile=current_user.equipment_profile or [],
    )
    selected_template_id = str(adaptation_runtime["program_id"])
    onboarding_program_id = resolve_linked_program_id(selected_template_id)
    try:
        onboarding_package = load_program_onboarding_package(onboarding_program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    decision = interpret_frequency_adaptation_apply(
        onboarding_package=onboarding_package,
        program_id=selected_template_id,
        current_days=int(adaptation_runtime["current_days"]),
        target_days=int(adaptation_runtime["target_days"]),
        duration_weeks=int(adaptation_runtime["duration_weeks"]),
        explicit_weak_areas=cast(list[str], adaptation_runtime["explicit_weak_areas"]),
        stored_weak_areas=cast(list[str], adaptation_runtime["stored_weak_areas"]),
        equipment_profile=cast(list[str], adaptation_runtime["equipment_profile"]),
        recovery_state=str(adaptation_runtime["recovery_state"]),
        current_week_index=int(adaptation_runtime["current_week_index"]),
        applied_at=datetime.now().isoformat(),
        request_runtime_trace=cast(dict[str, Any], adaptation_runtime["decision_trace"]),
    )

    current_user.active_frequency_adaptation = dict(decision["persistence_state"])
    db.add(current_user)
    db.commit()

    return FrequencyAdaptationApplyResponse(**build_frequency_adaptation_apply_payload(decision))


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

    try:
        template_runtime = prepare_generation_template_runtime(
            explicit_template_id=payload.template_id,
            profile_template_id=current_user.selected_program_id,
            split_preference=current_user.split_preference,
            days_available=current_user.days_available,
            nutrition_phase=current_user.nutrition_phase or "maintenance",
            available_equipment=current_user.equipment_profile or [],
            candidate_summaries=list_program_templates(),
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
    rule_set = _load_template_rule_set(selected_template_id)

    active_frequency_adaptation = resolve_active_frequency_adaptation_runtime(
        active_state=current_user.active_frequency_adaptation,
        selected_template_id=selected_template_id,
    )
    generation_context = _prepare_plan_generation_runtime(
        db=db,
        current_user=current_user,
        selected_template_id=selected_template_id,
        active_frequency_adaptation=active_frequency_adaptation,
    )
    generation_runtime = cast(dict[str, Any], generation_context["generation_runtime"])

    base_plan = generate_week_plan(
        user_profile={"name": current_user.name},
        days_available=cast(int, generation_runtime["effective_days_available"]),
        split_preference=current_user.split_preference,
        program_template=template,
        history=cast(list[dict[str, Any]], generation_runtime["history"]),
        phase=current_user.nutrition_phase or "maintenance",
        available_equipment=current_user.equipment_profile or [],
        soreness_by_muscle=cast(dict[str, str], generation_runtime["soreness_by_muscle"]),
        prior_generated_weeks=cast(int, generation_runtime["prior_generated_weeks"]),
        latest_adherence_score=cast(int | None, generation_runtime["latest_adherence_score"]),
        severe_soreness_count=cast(int, generation_runtime["severe_soreness_count"]),
        rule_set=rule_set,
    )
    week_start = date.fromisoformat(base_plan["week_start"])
    review_cycle = (
        db.query(WeeklyReviewCycle)
        .filter(WeeklyReviewCycle.user_id == current_user.id, WeeklyReviewCycle.week_start == week_start)
        .order_by(WeeklyReviewCycle.created_at.desc())
        .first()
    )
    review_overlay = prepare_generated_week_review_overlay(review_cycle)

    finalized_plan = build_generated_week_plan_payload(
        base_plan=base_plan,
        template_selection_trace=template_selection_trace,
        generation_runtime_trace=cast(dict[str, Any], generation_runtime["decision_trace"]),
        selected_template_id=selected_template_id,
        active_frequency_adaptation=active_frequency_adaptation,
        review_adjustments=cast(dict[str, Any] | None, review_overlay["review_adjustments"]),
        review_context=cast(dict[str, Any] | None, review_overlay["review_context"]),
    )
    plan = cast(dict[str, Any], finalized_plan["plan"])
    adaptation_runtime = finalized_plan["adaptation_runtime"]
    if bool(adaptation_runtime["state_updated"]):
        current_user.active_frequency_adaptation = cast(dict[str, Any] | None, adaptation_runtime["next_state"])
        db.add(current_user)

    record = WorkoutPlan(
        user_id=current_user.id,
        week_start=week_start,
        split=plan["split"],
        phase=plan["phase"],
        payload=plan,
    )
    db.add(record)
    db.commit()

    return plan
