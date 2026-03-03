from datetime import UTC, date
from datetime import datetime
from typing import Annotated, Any, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import BodyMeasurementEntry, SorenessEntry, User, WeeklyCheckin
from ..models import WorkoutPlan
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
    WeeklyCheckinRequest,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _compatible_program_ids(days_available: int, split_preference: str) -> list[str]:
    summaries = list_program_templates()
    compatible = [
        item["id"]
        for item in summaries
        if days_available in (item.get("days_supported") or [])
    ]
    split_matched = [
        item["id"]
        for item in summaries
        if item.get("split") == split_preference and days_available in (item.get("days_supported") or [])
    ]
    ordered = split_matched + [item for item in compatible if item not in split_matched]
    return ordered or [item["id"] for item in summaries]


def _latest_plan_payload(db: Session, user_id: str) -> dict[str, Any]:
    latest_plan = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.created_at.desc())
        .first()
    )
    if latest_plan and isinstance(latest_plan.payload, dict):
        return latest_plan.payload
    return {}


def _deterministic_program_recommendation(
    *,
    current_program_id: str,
    compatible_program_ids: list[str],
    latest_adherence_score: int | None,
    latest_plan_payload: dict[str, Any],
) -> tuple[str, str]:
    if not compatible_program_ids:
        return current_program_id, "no_compatible_programs"
    if current_program_id not in compatible_program_ids:
        return compatible_program_ids[0], "current_not_compatible"
    if latest_adherence_score is not None and latest_adherence_score <= 2:
        return current_program_id, "low_adherence_keep_program"

    rotated = _rotate_for_coverage_gap(current_program_id, compatible_program_ids, latest_plan_payload)
    if rotated:
        return rotated, "coverage_gap_rotate"

    rotated = _rotate_for_mesocycle_completion(current_program_id, compatible_program_ids, latest_plan_payload)
    if rotated:
        return rotated, "mesocycle_complete_rotate"

    return current_program_id, "maintain_current_program"


def _rotate_for_coverage_gap(
    current_program_id: str,
    compatible_program_ids: list[str],
    latest_plan_payload: dict[str, Any],
) -> str | None:
    if len(compatible_program_ids) <= 1:
        return None
    under_target = (latest_plan_payload.get("muscle_coverage") or {}).get("under_target_muscles")
    if not isinstance(under_target, list) or len(under_target) < 4:
        return None
    return next((candidate for candidate in compatible_program_ids if candidate != current_program_id), None)


def _rotate_for_mesocycle_completion(
    current_program_id: str,
    compatible_program_ids: list[str],
    latest_plan_payload: dict[str, Any],
) -> str | None:
    if len(compatible_program_ids) <= 1:
        return None
    mesocycle = latest_plan_payload.get("mesocycle")
    if not isinstance(mesocycle, dict):
        return None

    week_index = int(mesocycle.get("week_index", 1) or 1)
    trigger_weeks = int(mesocycle.get("trigger_weeks_effective", 6) or 6)
    if week_index < trigger_weeks:
        return None

    index = compatible_program_ids.index(current_program_id)
    next_index = (index + 1) % len(compatible_program_ids)
    recommended = compatible_program_ids[next_index]
    return recommended if recommended != current_program_id else None


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
        days_available=current_user.days_available or 2,
        nutrition_phase=current_user.nutrition_phase or "maintenance",
        calories=current_user.calories or 0,
        protein=current_user.protein or 0,
        fat=current_user.fat or 0,
        carbs=current_user.carbs or 0,
    )


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
    current_user.selected_program_id = payload.selected_program_id
    current_user.training_location = payload.training_location
    current_user.equipment_profile = payload.equipment_profile
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
    compatible_program_ids = _compatible_program_ids(
        days_available=current_user.days_available or 2,
        split_preference=current_user.split_preference or "full_body",
    )

    latest_checkin = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.user_id == current_user.id)
        .order_by(WeeklyCheckin.week_start.desc(), WeeklyCheckin.created_at.desc())
        .first()
    )
    adherence_score = latest_checkin.adherence_score if latest_checkin else None
    latest_plan_payload = _latest_plan_payload(db, current_user.id)

    recommended_program_id, reason = _deterministic_program_recommendation(
        current_program_id=current_program_id,
        compatible_program_ids=compatible_program_ids,
        latest_adherence_score=adherence_score,
        latest_plan_payload=latest_plan_payload,
    )

    return ProgramRecommendationResponse(
        current_program_id=current_program_id,
        recommended_program_id=recommended_program_id,
        reason=reason,
        compatible_program_ids=compatible_program_ids,
        generated_at=datetime.now(UTC),
    )


@router.post("/profile/program-switch")
def switch_program(
    payload: ProgramSwitchRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ProgramSwitchResponse:
    compatible_program_ids = _compatible_program_ids(
        days_available=current_user.days_available or 2,
        split_preference=current_user.split_preference or "full_body",
    )

    if payload.target_program_id not in compatible_program_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target program is not compatible")

    current_program_id = current_user.selected_program_id or "full_body_v1"
    latest_checkin = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.user_id == current_user.id)
        .order_by(WeeklyCheckin.week_start.desc(), WeeklyCheckin.created_at.desc())
        .first()
    )
    adherence_score = latest_checkin.adherence_score if latest_checkin else None
    latest_plan_payload = _latest_plan_payload(db, current_user.id)
    recommended_program_id, reason = _deterministic_program_recommendation(
        current_program_id=current_program_id,
        compatible_program_ids=compatible_program_ids,
        latest_adherence_score=adherence_score,
        latest_plan_payload=latest_plan_payload,
    )

    if payload.target_program_id == current_program_id:
        return ProgramSwitchResponse(
            status="unchanged",
            current_program_id=current_program_id,
            target_program_id=payload.target_program_id,
            recommended_program_id=recommended_program_id,
            reason="target_matches_current",
            requires_confirmation=False,
            applied=False,
        )

    if not payload.confirm:
        return ProgramSwitchResponse(
            status="confirmation_required",
            current_program_id=current_program_id,
            target_program_id=payload.target_program_id,
            recommended_program_id=recommended_program_id,
            reason=reason,
            requires_confirmation=True,
            applied=False,
        )

    current_user.selected_program_id = payload.target_program_id
    db.add(current_user)
    db.commit()

    return ProgramSwitchResponse(
        status="switched",
        current_program_id=current_program_id,
        target_program_id=payload.target_program_id,
        recommended_program_id=recommended_program_id,
        reason=reason,
        requires_confirmation=False,
        applied=True,
    )


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
