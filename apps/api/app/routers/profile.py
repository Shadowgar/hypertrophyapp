from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, WeeklyCheckin
from ..schemas import ProfileResponse, ProfileUpsert, WeeklyCheckinRequest

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
