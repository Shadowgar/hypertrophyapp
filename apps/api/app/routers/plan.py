from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from core_engine import generate_week_plan

from ..database import get_db
from ..deps import get_current_user
from ..models import SorenessEntry, User, WeeklyCheckin, WorkoutPlan, WorkoutSetLog
from ..program_loader import list_program_templates, load_program_template
from ..schemas import GenerateWeekPlanRequest, ProgramTemplateSummary

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _collect_recovery_and_mesocycle_inputs(
    db: Session,
    *,
    user_id: str,
    selected_template_id: str,
) -> tuple[dict[str, str], int, int | None, int]:
    latest_soreness = (
        db.query(SorenessEntry)
        .filter(SorenessEntry.user_id == user_id, SorenessEntry.entry_date <= date.today())
        .order_by(SorenessEntry.entry_date.desc(), SorenessEntry.created_at.desc())
        .first()
    )
    soreness_by_muscle = latest_soreness.severity_by_muscle if latest_soreness else {}
    severe_soreness_count = sum(
        1 for severity in soreness_by_muscle.values() if str(severity).lower() == "severe"
    )

    latest_checkin = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.user_id == user_id, WeeklyCheckin.week_start <= date.today())
        .order_by(WeeklyCheckin.week_start.desc(), WeeklyCheckin.created_at.desc())
        .first()
    )
    latest_adherence_score = latest_checkin.adherence_score if latest_checkin else None

    prior_plans = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).all()
    prior_weeks_for_template: set[str] = set()
    for existing_plan in prior_plans:
        payload_data = existing_plan.payload if isinstance(existing_plan.payload, dict) else {}
        program_id = payload_data.get("program_template_id")
        if program_id == selected_template_id:
            prior_weeks_for_template.add(existing_plan.week_start.isoformat())
            continue

        sessions = payload_data.get("sessions") or []
        if any(
            str(session.get("session_id", "")).startswith(f"{selected_template_id}-")
            for session in sessions
        ):
            prior_weeks_for_template.add(existing_plan.week_start.isoformat())

    return (
        soreness_by_muscle,
        severe_soreness_count,
        latest_adherence_score,
        len(prior_weeks_for_template),
    )


@router.get("/plan/programs", response_model=list[ProgramTemplateSummary])
def plan_list_programs() -> list[dict]:
    return list_program_templates()


@router.post(
    "/plan/generate-week",
    responses={
        400: {"description": "Complete profile first"},
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
        raise HTTPException(status_code=400, detail="Complete profile first")

    selected_template_id = payload.template_id or current_user.selected_program_id or "full_body_v1"

    try:
        template = load_program_template(selected_template_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid program template schema") from exc
    history_rows = (
        db.query(WorkoutSetLog)
        .filter(WorkoutSetLog.user_id == current_user.id)
        .order_by(WorkoutSetLog.created_at.desc())
        .limit(100)
        .all()
    )

    history = [
        {
            "exercise_id": row.exercise_id,
            "next_working_weight": row.weight,
        }
        for row in history_rows
    ]

    soreness_by_muscle, severe_soreness_count, latest_adherence_score, prior_generated_weeks = (
        _collect_recovery_and_mesocycle_inputs(
            db,
            user_id=current_user.id,
            selected_template_id=selected_template_id,
        )
    )

    plan = generate_week_plan(
        user_profile={"name": current_user.name},
        days_available=current_user.days_available,
        split_preference=current_user.split_preference,
        program_template=template,
        history=history,
        phase=current_user.nutrition_phase or "maintenance",
        available_equipment=current_user.equipment_profile or [],
        soreness_by_muscle=soreness_by_muscle,
        prior_generated_weeks=prior_generated_weeks,
        latest_adherence_score=latest_adherence_score,
        severe_soreness_count=severe_soreness_count,
    )

    week_start = date.fromisoformat(plan["week_start"])
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
