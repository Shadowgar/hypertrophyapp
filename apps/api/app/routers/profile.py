from datetime import UTC, date, datetime
from typing import Annotated, Any, Sequence, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from core_engine import (
    build_weekly_review_performance_summary,
    build_user_training_state,
    build_weekly_review_decision_payload,
    build_weekly_review_status_payload,
    build_weekly_review_submit_payload,
    prepare_weekly_review_submit_window,
    interpret_weekly_review_decision,
    prepare_program_recommendation_runtime,
    prepare_program_switch_runtime,
    resolve_weekly_review_window,
)
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import BodyMeasurementEntry, SorenessEntry, User, WeeklyCheckin, WeeklyReviewCycle, WorkoutSetLog
from ..models import ExerciseState, PasswordResetToken, WorkoutPlan, WorkoutSessionState
from ..program_loader import list_program_templates
from ..schemas import (
    BodyMeasurementEntryCreateRequest,
    BodyMeasurementEntryResponse,
    BodyMeasurementEntryUpdateRequest,
    ProfileResponse,
    ProfileUpsert,
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


def _latest_plan(db: Session, user_id: str) -> WorkoutPlan | None:
    return (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.created_at.desc())
        .first()
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
    return build_user_training_state(
        selected_program_id=current_user.selected_program_id,
        latest_plan=latest_plan,
        recent_workout_logs=[],
        exercise_states=[],
        latest_soreness_entry=None,
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
            WorkoutSetLog.created_at >= datetime.combine(previous_week_start, datetime.min.time()),
            WorkoutSetLog.created_at < datetime.combine(week_start, datetime.min.time()),
        )
        .all()
    )
    return WeeklyPerformanceSummaryResponse(
        **build_weekly_review_performance_summary(
            previous_week_start=previous_week_start,
            week_start=week_start,
            previous_plan=previous_plan,
            performed_logs=logs,
        )
    )


@router.get("/profile")
def get_profile(current_user: CurrentUser) -> ProfileResponse:
    return ProfileResponse(
        email=current_user.email,
        name=current_user.name,
        age=current_user.age or 0,
        weight=current_user.weight or 0,
        gender=current_user.gender or "",
        split_preference=current_user.split_preference or "",
        selected_program_id=current_user.selected_program_id or "full_body_v1",
        training_location=current_user.training_location,
        equipment_profile=current_user.equipment_profile or [],
        weak_areas=current_user.weak_areas or [],
        onboarding_answers=current_user.onboarding_answers or {},
        days_available=current_user.days_available or 2,
        nutrition_phase=current_user.nutrition_phase or "maintenance",
        calories=current_user.calories or 0,
        protein=current_user.protein or 0,
        fat=current_user.fat or 0,
        carbs=current_user.carbs or 0,
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

    payload = build_user_training_state(
        selected_program_id=current_user.selected_program_id,
        latest_plan=latest_plan,
        recent_workout_logs=recent_logs,
        exercise_states=exercise_states,
        latest_soreness_entry=latest_soreness,
        recent_checkins=recent_checkins,
        recent_review_cycles=recent_reviews,
        prior_plans=prior_plans,
    )
    return UserTrainingStateResponse.model_validate(payload)


@router.post("/profile")
def upsert_profile(
    payload: ProfileUpsert,
    db: DbSession,
    current_user: CurrentUser,
) -> ProfileResponse:
    current_user.name = payload.name
    current_user.age = payload.age
    current_user.weight = payload.weight
    current_user.gender = payload.gender
    current_user.split_preference = payload.split_preference
    current_user.selected_program_id = payload.selected_program_id or "full_body_v1"
    current_user.training_location = payload.training_location
    current_user.equipment_profile = payload.equipment_profile
    current_user.weak_areas = payload.weak_areas
    current_user.onboarding_answers = payload.onboarding_answers
    current_user.days_available = payload.days_available
    current_user.nutrition_phase = payload.nutrition_phase
    current_user.calories = payload.calories
    current_user.protein = payload.protein
    current_user.fat = payload.fat
    current_user.carbs = payload.carbs

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return get_profile(current_user)


@router.get("/profile/program-recommendation")
def program_recommendation(
    db: DbSession,
    current_user: CurrentUser,
) -> ProgramRecommendationResponse:
    current_program_id = current_user.selected_program_id or "full_body_v1"
    days_available = current_user.days_available or 2
    split_preference = current_user.split_preference or "full_body"
    latest_plan = _latest_plan(db, current_user.id)
    latest_plan_payload = latest_plan.payload if latest_plan and isinstance(latest_plan.payload, dict) else {}
    training_state = _build_program_recommendation_training_state(
        db,
        current_user=current_user,
        latest_plan=latest_plan,
    )

    runtime = prepare_program_recommendation_runtime(
        current_program_id=current_program_id,
        available_program_summaries=list_program_templates(),
        days_available=days_available,
        split_preference=split_preference,
        latest_adherence_score=None,
        latest_plan_payload=latest_plan_payload,
        user_training_state=training_state,
        generated_at=datetime.now(UTC),
    )

    return ProgramRecommendationResponse(**runtime["response_payload"])


@router.post("/profile/program-switch")
def switch_program(
    payload: ProgramSwitchRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ProgramSwitchResponse:
    days_available = current_user.days_available or 2
    split_preference = current_user.split_preference or "full_body"
    current_program_id = current_user.selected_program_id or "full_body_v1"
    latest_plan = _latest_plan(db, current_user.id)
    latest_plan_payload = latest_plan.payload if latest_plan and isinstance(latest_plan.payload, dict) else {}
    training_state = _build_program_recommendation_training_state(
        db,
        current_user=current_user,
        latest_plan=latest_plan,
    )

    recommendation_runtime = prepare_program_recommendation_runtime(
        current_program_id=current_program_id,
        available_program_summaries=list_program_templates(),
        days_available=days_available,
        split_preference=split_preference,
        latest_adherence_score=None,
        latest_plan_payload=latest_plan_payload,
        user_training_state=training_state,
    )

    try:
        runtime = prepare_program_switch_runtime(
            current_program_id=current_program_id,
            target_program_id=payload.target_program_id,
            confirm=payload.confirm,
            compatible_program_ids=cast(list[str], recommendation_runtime["compatible_program_ids"]),
            decision=cast(dict[str, Any], recommendation_runtime["decision"]),
            candidate_resolution_trace=cast(dict[str, Any], recommendation_runtime["candidate_resolution_trace"]),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if runtime["should_apply"]:
        current_user.selected_program_id = payload.target_program_id
        db.add(current_user)
        db.commit()

    return ProgramSwitchResponse(**runtime["response_payload"])


@router.post("/weekly-checkin")
def weekly_checkin(
    payload: WeeklyCheckinRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    entry = WeeklyCheckin(
        user_id=current_user.id,
        week_start=payload.week_start,
        body_weight=payload.body_weight,
        adherence_score=payload.adherence_score,
        notes=payload.notes,
    )
    db.add(entry)
    db.commit()
    return {"status": "logged", "phase": current_user.nutrition_phase or "maintenance"}


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
    return WeeklyReviewStatusResponse(
        **build_weekly_review_status_payload(
            today=today,
            existing_review_submitted=existing_review is not None,
            previous_week_summary=summary.model_dump(mode="json"),
        )
    )


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
    decision_payload = build_weekly_review_decision_payload(
        summary=summary_payload,
        body_weight=payload.body_weight,
        calories=payload.calories,
        protein=payload.protein,
        adherence_score=payload.adherence_score,
    )

    current_user.weight = payload.body_weight
    current_user.calories = payload.calories
    current_user.protein = payload.protein
    current_user.fat = payload.fat
    current_user.carbs = payload.carbs
    if payload.nutrition_phase:
        current_user.nutrition_phase = payload.nutrition_phase
    db.add(current_user)

    checkin_entry = WeeklyCheckin(
        user_id=current_user.id,
        week_start=week_start,
        body_weight=payload.body_weight,
        adherence_score=payload.adherence_score,
        notes=payload.notes,
    )
    db.add(checkin_entry)

    review_entry = WeeklyReviewCycle(
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
        faults={"exercise_faults": [item.model_dump(mode="json") for item in summary.exercise_faults]},
        adjustments=dict(decision_payload["storage_adjustments"]),
        summary=summary_payload,
    )
    db.add(review_entry)
    db.commit()

    return WeeklyReviewSubmitResponse(
        **build_weekly_review_submit_payload(
            week_start=week_start,
            previous_week_start=previous_week_start,
            summary=summary_payload,
            decision_payload=decision_payload,
        )
    )


@router.get("/soreness", response_model=list[SorenessEntryResponse])
def list_soreness_entries(
    db: DbSession,
    current_user: CurrentUser,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> Sequence[SorenessEntry]:
    query = db.query(SorenessEntry).filter(SorenessEntry.user_id == current_user.id)
    if start_date is not None:
        query = query.filter(SorenessEntry.entry_date >= start_date)
    if end_date is not None:
        query = query.filter(SorenessEntry.entry_date <= end_date)
    return query.order_by(SorenessEntry.entry_date.desc(), SorenessEntry.created_at.desc()).all()


@router.post("/soreness", response_model=SorenessEntryResponse, status_code=status.HTTP_201_CREATED)
def create_soreness_entry(
    payload: SorenessEntryCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> SorenessEntry:
    entry = SorenessEntry(
        user_id=current_user.id,
        entry_date=payload.entry_date,
        severity_by_muscle=dict(payload.severity_by_muscle),
        notes=payload.notes,
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

    entry.entry_date = payload.entry_date
    entry.severity_by_muscle = dict(payload.severity_by_muscle)
    entry.notes = payload.notes
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
    query = db.query(BodyMeasurementEntry).filter(BodyMeasurementEntry.user_id == current_user.id)
    if start_date is not None:
        query = query.filter(BodyMeasurementEntry.measured_on >= start_date)
    if end_date is not None:
        query = query.filter(BodyMeasurementEntry.measured_on <= end_date)
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
    entry = BodyMeasurementEntry(
        user_id=current_user.id,
        measured_on=payload.measured_on,
        name=payload.name,
        value=payload.value,
        unit=payload.unit,
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

    if payload.measured_on is not None:
        entry.measured_on = payload.measured_on
    if payload.name is not None:
        entry.name = payload.name
    if payload.value is not None:
        entry.value = payload.value
    if payload.unit is not None:
        entry.unit = payload.unit

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
    user_id = current_user.id

    db.query(WorkoutSessionState).filter(WorkoutSessionState.user_id == user_id).delete(synchronize_session=False)
    db.query(WorkoutSetLog).filter(WorkoutSetLog.user_id == user_id).delete(synchronize_session=False)
    db.query(ExerciseState).filter(ExerciseState.user_id == user_id).delete(synchronize_session=False)
    db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).delete(synchronize_session=False)
    db.query(WeeklyReviewCycle).filter(WeeklyReviewCycle.user_id == user_id).delete(synchronize_session=False)
    db.query(WeeklyCheckin).filter(WeeklyCheckin.user_id == user_id).delete(synchronize_session=False)
    db.query(SorenessEntry).filter(SorenessEntry.user_id == user_id).delete(synchronize_session=False)
    db.query(BodyMeasurementEntry).filter(BodyMeasurementEntry.user_id == user_id).delete(synchronize_session=False)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete(synchronize_session=False)
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()

    return StatusResponse(status="wiped")
