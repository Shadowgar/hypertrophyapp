from datetime import UTC, date, datetime
from typing import Annotated, Any, Sequence, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from core_engine import (
    build_user_training_state,
    prepare_weekly_review_status_route_runtime,
    prepare_weekly_review_summary_route_runtime,
    prepare_weekly_review_submit_route_runtime,
    build_soreness_entry_persistence_payload,
    build_body_measurement_create_payload,
    build_body_measurement_update_payload,
    prepare_profile_date_window_runtime,
    build_profile_upsert_persistence_payload,
    build_profile_response_payload,
    build_weekly_checkin_persistence_payload,
    build_weekly_checkin_response_payload,
    build_plan_decision_training_state,
    prepare_weekly_review_log_window_runtime,
    prepare_weekly_review_submit_window,
    prepare_profile_program_recommendation_route_runtime,
    prepare_program_switch_runtime,
    resolve_weekly_review_window,
)
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import BodyMeasurementEntry, SorenessEntry, User, WeeklyCheckin, WeeklyReviewCycle, WorkoutSetLog
from ..models import CoachingRecommendation, ExerciseState, PasswordResetToken, WorkoutPlan, WorkoutSessionState
from ..observability import log_event
from ..program_loader import (
    PHASE1_CANONICAL_PROGRAM_ID,
    list_program_templates,
    resolve_selected_program_binding_id,
)
from ..schemas import (
    BodyMeasurementEntryCreateRequest,
    BodyMeasurementEntryResponse,
    BodyMeasurementEntryUpdateRequest,
    ProfileResponse,
    ProfileUpsert,
    ProgramSelectionUpdateRequest,
    ProgramRecommendationResponse,
    ProgramSwitchRequest,
    ProgramSwitchResponse,
    SorenessEntryCreateRequest,
    SorenessEntryResponse,
    StatusResponse,
    WeeklyExerciseAdjustmentResponse,
    WeeklyExerciseFaultResponse,
    WeeklyCheckinRequest,
    WeeklyPerformanceSummaryResponse,
    WeeklyPlanAdjustmentResponse,
    WeeklyReviewStatusResponse,
    WeeklyReviewSubmitRequest,
    WeeklyReviewSubmitResponse,
    UserTrainingStateResponse,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _clear_user_training_state(db: Session, *, user_id: str) -> None:
    db.query(WorkoutSessionState).filter(WorkoutSessionState.user_id == user_id).delete(synchronize_session=False)
    db.query(WorkoutSetLog).filter(WorkoutSetLog.user_id == user_id).delete(synchronize_session=False)
    db.query(ExerciseState).filter(ExerciseState.user_id == user_id).delete(synchronize_session=False)
    db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).delete(synchronize_session=False)
    db.query(WeeklyReviewCycle).filter(WeeklyReviewCycle.user_id == user_id).delete(synchronize_session=False)
    db.query(WeeklyCheckin).filter(WeeklyCheckin.user_id == user_id).delete(synchronize_session=False)
    db.query(SorenessEntry).filter(SorenessEntry.user_id == user_id).delete(synchronize_session=False)
    db.query(BodyMeasurementEntry).filter(BodyMeasurementEntry.user_id == user_id).delete(synchronize_session=False)
    db.query(CoachingRecommendation).filter(CoachingRecommendation.user_id == user_id).delete(synchronize_session=False)


def _has_user_workout_activity(db: Session, *, user_id: str) -> bool:
    return any(
        (
            db.query(WorkoutSessionState).filter(WorkoutSessionState.user_id == user_id).first(),
            db.query(WorkoutSetLog).filter(WorkoutSetLog.user_id == user_id).first(),
            db.query(ExerciseState).filter(ExerciseState.user_id == user_id).first(),
        )
    )


def _latest_plan(db: Session, user_id: str) -> WorkoutPlan | None:
    return (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.created_at.desc())
        .first()
    )


def _is_profile_complete(
    *,
    selected_program_id: str | None,
    split_preference: str | None,
    days_available: int | None,
) -> bool:
    return bool(
        resolve_selected_program_binding_id(selected_program_id)
        and str(split_preference or "").strip()
        and days_available is not None
    )


def _build_program_recommendation_training_state(
    db: Session,
    *,
    current_user: User,
    latest_plan: WorkoutPlan | None,
) -> dict[str, Any]:
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
    return build_plan_decision_training_state(
        selected_program_id=current_user.selected_program_id,
        days_available=current_user.days_available,
        split_preference=current_user.split_preference,
        training_location=current_user.training_location,
        equipment_profile=current_user.equipment_profile,
        weak_areas=current_user.weak_areas,
        nutrition_phase=current_user.nutrition_phase,
        session_time_budget_minutes=current_user.session_time_budget_minutes,
        movement_restrictions=current_user.movement_restrictions,
        near_failure_tolerance=current_user.near_failure_tolerance,
        latest_plan=latest_plan,
        latest_soreness_entry=None,
        recent_workout_logs=[],
        recent_checkins=recent_checkins,
        recent_review_cycles=recent_reviews,
        prior_plans=[],
    )


def _collect_previous_week_performance_summary(
    db: Session,
    *,
    user_id: str,
    previous_week_start: date,
    week_start: date,
) -> WeeklyPerformanceSummaryResponse:
    log_window_runtime = prepare_weekly_review_log_window_runtime(
        previous_week_start=previous_week_start,
        week_start=week_start,
    )
    previous_plan = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id, WorkoutPlan.week_start == previous_week_start)
        .order_by(WorkoutPlan.created_at.desc())
        .first()
    )
    logs = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == user_id,
            WorkoutSetLog.created_at >= cast(datetime, log_window_runtime["window_start"]),
            WorkoutSetLog.created_at < cast(datetime, log_window_runtime["window_end"]),
        )
        .all()
    )
    summary_runtime = prepare_weekly_review_summary_route_runtime(
        previous_week_start=previous_week_start,
        week_start=week_start,
        previous_plan=previous_plan,
        performed_logs=logs,
    )
    return WeeklyPerformanceSummaryResponse(
        **cast(dict[str, Any], summary_runtime["summary_payload"])
    )


@router.get("/profile")
def get_profile(current_user: CurrentUser) -> ProfileResponse:
    selected_program_id = resolve_selected_program_binding_id(current_user.selected_program_id)
    return ProfileResponse(
        **build_profile_response_payload(
            email=current_user.email,
            name=current_user.name,
            age=current_user.age,
            weight=current_user.weight,
            gender=current_user.gender,
            split_preference=current_user.split_preference,
            selected_program_id=selected_program_id,
            program_selection_mode=current_user.program_selection_mode,
            choose_for_me_family=current_user.choose_for_me_family,
            choose_for_me_diagnostics=current_user.choose_for_me_diagnostics,
            training_location=current_user.training_location,
            equipment_profile=current_user.equipment_profile,
            weak_areas=current_user.weak_areas,
            onboarding_answers=current_user.onboarding_answers,
            days_available=current_user.days_available,
            session_time_budget_minutes=current_user.session_time_budget_minutes,
            movement_restrictions=current_user.movement_restrictions,
            near_failure_tolerance=current_user.near_failure_tolerance,
            nutrition_phase=current_user.nutrition_phase,
            calories=current_user.calories,
            protein=current_user.protein,
            fat=current_user.fat,
            carbs=current_user.carbs,
        )
    )


@router.get("/profile/training-state")
def get_training_state(
    db: DbSession,
    current_user: CurrentUser,
) -> UserTrainingStateResponse:
    latest_plan = _latest_plan(db, current_user.id)
    prior_plans = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == current_user.id).all()
    latest_soreness = (
        db.query(SorenessEntry)
        .filter(SorenessEntry.user_id == current_user.id)
        .order_by(SorenessEntry.entry_date.desc(), SorenessEntry.created_at.desc())
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
    recent_logs = (
        db.query(WorkoutSetLog)
        .filter(WorkoutSetLog.user_id == current_user.id)
        .order_by(WorkoutSetLog.created_at.desc())
        .limit(200)
        .all()
    )
    exercise_states = (
        db.query(ExerciseState)
        .filter(ExerciseState.user_id == current_user.id)
        .order_by(ExerciseState.last_updated_at.desc(), ExerciseState.exercise_id.asc())
        .all()
    )

    selected_program_id = resolve_selected_program_binding_id(current_user.selected_program_id)
    payload = build_user_training_state(
        selected_program_id=selected_program_id,
        days_available=current_user.days_available,
        split_preference=current_user.split_preference,
        training_location=current_user.training_location,
        equipment_profile=current_user.equipment_profile,
        weak_areas=current_user.weak_areas,
        nutrition_phase=current_user.nutrition_phase,
        session_time_budget_minutes=current_user.session_time_budget_minutes,
        movement_restrictions=current_user.movement_restrictions,
        near_failure_tolerance=current_user.near_failure_tolerance,
        latest_plan=latest_plan,
        recent_workout_logs=recent_logs,
        exercise_states=exercise_states,
        latest_soreness_entry=latest_soreness,
        recent_checkins=recent_checkins,
        recent_review_cycles=recent_reviews,
        prior_plans=prior_plans,
    )
    user_program_state = cast(dict[str, Any], payload.get("user_program_state") or {})
    normalized_program_id = resolve_selected_program_binding_id(user_program_state.get("program_id"))
    if normalized_program_id:
        user_program_state["program_id"] = normalized_program_id
        payload["user_program_state"] = user_program_state

    generation_state = cast(dict[str, Any], payload.get("generation_state") or {})
    prior_by_program = cast(dict[str, Any], generation_state.get("prior_generated_weeks_by_program") or {})
    if prior_by_program:
        normalized_counts: dict[str, int] = {}
        for raw_program_id, raw_count in prior_by_program.items():
            normalized = resolve_selected_program_binding_id(str(raw_program_id))
            if not normalized:
                continue
            normalized_counts[normalized] = normalized_counts.get(normalized, 0) + int(raw_count or 0)
        generation_state["prior_generated_weeks_by_program"] = normalized_counts
        payload["generation_state"] = generation_state

    return UserTrainingStateResponse.model_validate(payload)


@router.post("/profile")
def upsert_profile(
    payload: ProfileUpsert,
    db: DbSession,
    current_user: CurrentUser,
) -> ProfileResponse:
    previous_binding_id = resolve_selected_program_binding_id(current_user.selected_program_id)
    next_binding_id = resolve_selected_program_binding_id(payload.selected_program_id)
    was_complete = _is_profile_complete(
        selected_program_id=current_user.selected_program_id,
        split_preference=current_user.split_preference,
        days_available=current_user.days_available,
    )
    will_be_complete = _is_profile_complete(
        selected_program_id=payload.selected_program_id,
        split_preference=payload.split_preference,
        days_available=payload.days_available,
    )
    persistence_payload = build_profile_upsert_persistence_payload(
        name=payload.name,
        age=payload.age,
        weight=payload.weight,
        gender=payload.gender,
        split_preference=payload.split_preference,
        selected_program_id=next_binding_id,
        program_selection_mode=payload.program_selection_mode,
        choose_for_me_family=payload.choose_for_me_family,
        choose_for_me_diagnostics=payload.choose_for_me_diagnostics,
        training_location=payload.training_location,
        equipment_profile=payload.equipment_profile,
        weak_areas=payload.weak_areas,
        onboarding_answers=payload.onboarding_answers,
        days_available=payload.days_available,
        session_time_budget_minutes=payload.session_time_budget_minutes,
        movement_restrictions=payload.movement_restrictions,
        near_failure_tolerance=payload.near_failure_tolerance,
        nutrition_phase=payload.nutrition_phase,
        calories=payload.calories,
        protein=payload.protein,
        fat=payload.fat,
        carbs=payload.carbs,
    )
    onboarding_answers_changed = bool(payload.onboarding_answers) and payload.onboarding_answers != (current_user.onboarding_answers or {})
    same_binding_onboarding_reset = (
        was_complete
        and will_be_complete
        and previous_binding_id == next_binding_id
        and onboarding_answers_changed
        and not _has_user_workout_activity(db, user_id=current_user.id)
    )
    should_reset_training_state = (
        (not was_complete and will_be_complete)
        or previous_binding_id != next_binding_id
        or same_binding_onboarding_reset
    )
    profile_action = "onboarding_submit" if (not was_complete and will_be_complete) else "profile_update"
    if should_reset_training_state:
        _clear_user_training_state(db, user_id=current_user.id)
        current_user.active_frequency_adaptation = None
    for key, value in persistence_payload.items():
        setattr(current_user, key, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    log_event(
        "onboarding_submitted" if profile_action == "onboarding_submit" else "profile_updated",
        route="/profile",
        action=profile_action,
        user_id=current_user.id,
        selected_program_id=next_binding_id,
        days_available=current_user.days_available,
        target_days=current_user.days_available,
    )

    return get_profile(current_user)


@router.get("/profile/program-recommendation")
def program_recommendation(
    db: DbSession,
    current_user: CurrentUser,
) -> ProgramRecommendationResponse:
    selected_program_id = resolve_selected_program_binding_id(current_user.selected_program_id)
    latest_plan = _latest_plan(db, current_user.id)
    training_state = _build_program_recommendation_training_state(
        db,
        current_user=current_user,
        latest_plan=latest_plan,
    )
    route_runtime = prepare_profile_program_recommendation_route_runtime(
        selected_program_id=selected_program_id,
        days_available=current_user.days_available,
        split_preference=current_user.split_preference,
        latest_plan=latest_plan,
        available_program_summaries=list_program_templates(),
        latest_adherence_score=None,
        user_training_state=training_state,
        generated_at=datetime.now(UTC),
    )
    runtime = cast(dict[str, Any], route_runtime["recommendation_runtime"])

    return ProgramRecommendationResponse(**runtime["response_payload"])


@router.post("/profile/program-switch")
def switch_program(
    payload: ProgramSwitchRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ProgramSwitchResponse:
    selected_program_id = resolve_selected_program_binding_id(current_user.selected_program_id)
    target_program_id = resolve_selected_program_binding_id(payload.target_program_id) or payload.target_program_id
    latest_plan = _latest_plan(db, current_user.id)
    training_state = _build_program_recommendation_training_state(
        db,
        current_user=current_user,
        latest_plan=latest_plan,
    )
    route_runtime = prepare_profile_program_recommendation_route_runtime(
        selected_program_id=selected_program_id,
        days_available=current_user.days_available,
        split_preference=current_user.split_preference,
        latest_plan=latest_plan,
        available_program_summaries=list_program_templates(),
        latest_adherence_score=None,
        user_training_state=training_state,
    )
    recommendation_inputs = cast(dict[str, Any], route_runtime["recommendation_inputs"])
    recommendation_runtime = cast(dict[str, Any], route_runtime["recommendation_runtime"])

    try:
        runtime = prepare_program_switch_runtime(
            current_program_id=cast(str, recommendation_inputs["current_program_id"]),
            target_program_id=target_program_id,
            confirm=payload.confirm,
            compatible_program_ids=cast(list[str], recommendation_runtime["compatible_program_ids"]),
            decision=cast(dict[str, Any], recommendation_runtime["decision"]),
            candidate_resolution_trace=cast(dict[str, Any], recommendation_runtime["candidate_resolution_trace"]),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if runtime["should_apply"]:
        if resolve_selected_program_binding_id(current_user.selected_program_id) != target_program_id:
            _clear_user_training_state(db, user_id=current_user.id)
            current_user.active_frequency_adaptation = None
        current_user.selected_program_id = target_program_id
        db.add(current_user)
        db.commit()

    return ProgramSwitchResponse(**runtime["response_payload"])


@router.post("/profile/program-selection")
def update_program_selection(
    payload: ProgramSelectionUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ProfileResponse:
    next_binding_id = resolve_selected_program_binding_id(payload.selected_program_id)
    if payload.program_selection_mode == "manual" and not next_binding_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="selected_program_id is required in manual mode")

    current_user.selected_program_id = next_binding_id
    current_user.program_selection_mode = payload.program_selection_mode
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    log_event(
        "profile_program_selection_updated",
        route="/profile/program-selection",
        action="program_selection_update",
        user_id=current_user.id,
        selected_program_id=next_binding_id,
    )
    return get_profile(current_user)


@router.post("/weekly-checkin")
def weekly_checkin(
    payload: WeeklyCheckinRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    persistence_payload = build_weekly_checkin_persistence_payload(
        week_start=payload.week_start,
        body_weight=payload.body_weight,
        adherence_score=payload.adherence_score,
        sleep_quality=payload.sleep_quality,
        stress_level=payload.stress_level,
        pain_flags=payload.pain_flags,
        notes=payload.notes,
    )
    entry = WeeklyCheckin(
        user_id=current_user.id,
        week_start=cast(date, persistence_payload["week_start"]),
        body_weight=cast(float, persistence_payload["body_weight"]),
        adherence_score=cast(int, persistence_payload["adherence_score"]),
        sleep_quality=cast(int | None, persistence_payload["sleep_quality"]),
        stress_level=cast(int | None, persistence_payload["stress_level"]),
        pain_flags=cast(list[str], persistence_payload["pain_flags"]),
        notes=cast(str | None, persistence_payload["notes"]),
    )
    db.add(entry)
    db.commit()
    return build_weekly_checkin_response_payload(nutrition_phase=current_user.nutrition_phase)


@router.get("/weekly-review/status")
def weekly_review_status(
    db: DbSession,
    current_user: CurrentUser,
) -> WeeklyReviewStatusResponse:
    today = date.today()
    window = resolve_weekly_review_window(today=today)
    week_start = window["week_start"]
    previous_week_start = window["previous_week_start"]
    existing_review = (
        db.query(WeeklyReviewCycle)
        .filter(WeeklyReviewCycle.user_id == current_user.id, WeeklyReviewCycle.week_start == week_start)
        .order_by(WeeklyReviewCycle.created_at.desc())
        .first()
    )
    summary = _collect_previous_week_performance_summary(
        db,
        user_id=current_user.id,
        previous_week_start=previous_week_start,
        week_start=week_start,
    )
    status_runtime = prepare_weekly_review_status_route_runtime(
        today=today,
        existing_review_submitted=existing_review is not None,
        previous_week_summary=summary.model_dump(mode="json"),
    )
    return WeeklyReviewStatusResponse(**cast(dict[str, Any], status_runtime["response_payload"]))


@router.post("/weekly-review")
def submit_weekly_review(
    payload: WeeklyReviewSubmitRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> WeeklyReviewSubmitResponse:
    today = date.today()
    submit_window = prepare_weekly_review_submit_window(
        today=today,
        requested_week_start=payload.week_start,
    )
    week_start = cast(date, submit_window["week_start"])
    previous_week_start = cast(date, submit_window["previous_week_start"])

    summary = _collect_previous_week_performance_summary(
        db,
        user_id=current_user.id,
        previous_week_start=previous_week_start,
        week_start=week_start,
    )
    summary_payload = summary.model_dump(mode="json")
    training_state = _build_program_recommendation_training_state(
        db,
        current_user=current_user,
        latest_plan=_latest_plan(db, current_user.id),
    )
    route_runtime = prepare_weekly_review_submit_route_runtime(
        user_id=current_user.id,
        reviewed_on=today,
        week_start=week_start,
        previous_week_start=previous_week_start,
        body_weight=payload.body_weight,
        calories=payload.calories,
        protein=payload.protein,
        fat=payload.fat,
        carbs=payload.carbs,
        adherence_score=payload.adherence_score,
        notes=payload.notes,
        nutrition_phase=payload.nutrition_phase,
        summary_payload=summary_payload,
        readiness_state=cast(dict[str, Any], training_state.get("readiness_state") or {}),
        coaching_state=cast(dict[str, Any], training_state.get("coaching_state") or {}),
        near_failure_tolerance=current_user.near_failure_tolerance,
    )
    user_update_payload = cast(dict[str, Any], route_runtime["user_update_payload"])
    for key, value in user_update_payload.items():
        setattr(current_user, key, value)
    if payload.sessions_next_week is not None:
        current_user.days_available = int(payload.sessions_next_week)
    db.add(current_user)

    submit_persistence_values = cast(dict[str, Any], route_runtime["submit_persistence_values"])

    checkin_entry = WeeklyCheckin(
        **cast(dict[str, Any], submit_persistence_values["checkin_values"])
    )
    db.add(checkin_entry)

    review_entry = WeeklyReviewCycle(
        **cast(dict[str, Any], submit_persistence_values["review_values"])
    )
    db.add(review_entry)
    db.commit()
    log_event(
        "weekly_review_submitted",
        route="/weekly-review",
        action="weekly_review_submit",
        user_id=current_user.id,
        selected_program_id=resolve_selected_program_binding_id(current_user.selected_program_id),
        days_available=current_user.days_available,
        target_days=payload.sessions_next_week,
        week_start=week_start,
    )

    return WeeklyReviewSubmitResponse(**cast(dict[str, Any], route_runtime["response_payload"]))


@router.get("/soreness", response_model=list[SorenessEntryResponse])
def list_soreness_entries(
    db: DbSession,
    current_user: CurrentUser,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> Sequence[SorenessEntry]:
    date_window_runtime = prepare_profile_date_window_runtime(
        start_date=start_date,
        end_date=end_date,
    )
    query = db.query(SorenessEntry).filter(SorenessEntry.user_id == current_user.id)
    if date_window_runtime["start_date"] is not None:
        query = query.filter(SorenessEntry.entry_date >= cast(date, date_window_runtime["start_date"]))
    if date_window_runtime["end_date"] is not None:
        query = query.filter(SorenessEntry.entry_date <= cast(date, date_window_runtime["end_date"]))
    return query.order_by(SorenessEntry.entry_date.desc(), SorenessEntry.created_at.desc()).all()


@router.post("/soreness", response_model=SorenessEntryResponse, status_code=status.HTTP_201_CREATED)
def create_soreness_entry(
    payload: SorenessEntryCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> SorenessEntry:
    persistence_payload = build_soreness_entry_persistence_payload(
        entry_date=payload.entry_date,
        severity_by_muscle=payload.severity_by_muscle,
        notes=payload.notes,
    )
    entry = SorenessEntry(
        user_id=current_user.id,
        entry_date=cast(date, persistence_payload["entry_date"]),
        severity_by_muscle=cast(dict[str, str], persistence_payload["severity_by_muscle"]),
        notes=cast(str | None, persistence_payload["notes"]),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.put("/soreness/{entry_id}", response_model=SorenessEntryResponse)
def update_soreness_entry(
    entry_id: str,
    payload: SorenessEntryCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> SorenessEntry:
    entry = (
        db.query(SorenessEntry)
        .filter(SorenessEntry.id == entry_id, SorenessEntry.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soreness entry not found")

    persistence_payload = build_soreness_entry_persistence_payload(
        entry_date=payload.entry_date,
        severity_by_muscle=payload.severity_by_muscle,
        notes=payload.notes,
    )
    entry.entry_date = cast(date, persistence_payload["entry_date"])
    entry.severity_by_muscle = cast(dict[str, str], persistence_payload["severity_by_muscle"])
    entry.notes = cast(str | None, persistence_payload["notes"])
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/soreness/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_soreness_entry(
    entry_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    entry = (
        db.query(SorenessEntry)
        .filter(SorenessEntry.id == entry_id, SorenessEntry.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soreness entry not found")
    db.delete(entry)
    db.commit()


@router.get("/body-measurements", response_model=list[BodyMeasurementEntryResponse])
def list_body_measurements(
    db: DbSession,
    current_user: CurrentUser,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> Sequence[BodyMeasurementEntry]:
    date_window_runtime = prepare_profile_date_window_runtime(
        start_date=start_date,
        end_date=end_date,
    )
    query = db.query(BodyMeasurementEntry).filter(BodyMeasurementEntry.user_id == current_user.id)
    if date_window_runtime["start_date"] is not None:
        query = query.filter(BodyMeasurementEntry.measured_on >= cast(date, date_window_runtime["start_date"]))
    if date_window_runtime["end_date"] is not None:
        query = query.filter(BodyMeasurementEntry.measured_on <= cast(date, date_window_runtime["end_date"]))
    return query.order_by(BodyMeasurementEntry.measured_on.desc(), BodyMeasurementEntry.created_at.desc()).all()


@router.post(
    "/body-measurements",
    response_model=BodyMeasurementEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_body_measurement(
    payload: BodyMeasurementEntryCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> BodyMeasurementEntry:
    persistence_payload = build_body_measurement_create_payload(
        measured_on=payload.measured_on,
        name=payload.name,
        value=payload.value,
        unit=payload.unit,
    )
    entry = BodyMeasurementEntry(
        user_id=current_user.id,
        measured_on=cast(date, persistence_payload["measured_on"]),
        name=cast(str, persistence_payload["name"]),
        value=cast(float, persistence_payload["value"]),
        unit=cast(str, persistence_payload["unit"]),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.put("/body-measurements/{entry_id}", response_model=BodyMeasurementEntryResponse)
def update_body_measurement(
    entry_id: str,
    payload: BodyMeasurementEntryUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> BodyMeasurementEntry:
    entry = (
        db.query(BodyMeasurementEntry)
        .filter(BodyMeasurementEntry.id == entry_id, BodyMeasurementEntry.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measurement entry not found")

    persistence_payload = build_body_measurement_update_payload(
        measured_on=payload.measured_on,
        name=payload.name,
        value=payload.value,
        unit=payload.unit,
    )
    for key, value in persistence_payload.items():
        setattr(entry, key, value)

    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/body-measurements/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_body_measurement(
    entry_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    entry = (
        db.query(BodyMeasurementEntry)
        .filter(BodyMeasurementEntry.id == entry_id, BodyMeasurementEntry.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measurement entry not found")
    db.delete(entry)
    db.commit()


@router.post("/profile/dev/wipe", response_model=StatusResponse)
def wipe_current_user_data(
    db: DbSession,
    current_user: CurrentUser,
) -> StatusResponse:
    if not settings.allow_dev_wipe_endpoints:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev wipe endpoints disabled")

    user_id = current_user.id

    _clear_user_training_state(db, user_id=user_id)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete(synchronize_session=False)
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()

    return StatusResponse(status="wiped")


@router.post("/profile/dev/reset-phase1", response_model=StatusResponse)
def reset_current_user_to_phase1(
    db: DbSession,
    current_user: CurrentUser,
) -> StatusResponse:
    if not settings.allow_dev_wipe_endpoints:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev wipe endpoints disabled")

    _clear_user_training_state(db, user_id=current_user.id)

    current_user.selected_program_id = PHASE1_CANONICAL_PROGRAM_ID
    current_user.split_preference = "full_body"
    current_user.days_available = 5
    current_user.active_frequency_adaptation = None

    db.add(current_user)
    db.commit()
    return StatusResponse(status="reset_to_phase1")
