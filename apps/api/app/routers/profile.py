from datetime import date
from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import BodyMeasurementEntry, SorenessEntry, User, WeeklyCheckin
from ..schemas import (
    BodyMeasurementEntryCreateRequest,
    BodyMeasurementEntryResponse,
    BodyMeasurementEntryUpdateRequest,
    ProfileResponse,
    ProfileUpsert,
    SorenessEntryCreateRequest,
    SorenessEntryResponse,
    WeeklyCheckinRequest,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/profile")
def get_profile(current_user: CurrentUser) -> ProfileResponse:
    return ProfileResponse(
        email=current_user.email,
        name=current_user.name,
        age=current_user.age or 0,
        weight=current_user.weight or 0,
        gender=current_user.gender or "",
        split_preference=current_user.split_preference or "",
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
