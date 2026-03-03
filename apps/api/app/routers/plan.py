from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from core_engine import generate_week_plan

from ..database import get_db
from ..deps import get_current_user
from ..models import SorenessEntry, User, WeeklyCheckin, WorkoutPlan, WorkoutSetLog
from ..program_loader import list_program_templates, load_program_template
from ..schemas import GenerateWeekPlanRequest, ProgramTemplateSummary
from ..schemas import (
    GuideDaySummary,
    GuideExerciseSummary,
    GuideProgramSummary,
    ProgramDayGuideResponse,
    ProgramExerciseGuideResponse,
    ProgramGuideResponse,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
INVALID_TEMPLATE_DETAIL = "Invalid program template schema"
GUIDE_RESPONSES = {
    404: {"description": "Guide resource not found"},
    422: {"description": INVALID_TEMPLATE_DETAIL},
}


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


def _preview_template_viability(
    *,
    template: dict[str, Any],
    days_available: int,
    split_preference: str,
    nutrition_phase: str,
    available_equipment: list[str],
) -> tuple[int, int]:
    preview = generate_week_plan(
        user_profile={"name": "preview"},
        days_available=days_available,
        split_preference=split_preference,
        program_template=template,
        history=[],
        phase=nutrition_phase,
        available_equipment=available_equipment,
    )
    sessions = preview.get("sessions") or []
    session_count = len(sessions)
    exercise_count = sum(len(session.get("exercises") or []) for session in sessions)
    return session_count, exercise_count


def _ordered_candidate_template_ids(
    *,
    preferred_template_id: str | None,
    split_preference: str,
    days_available: int,
) -> list[str]:
    summaries = list_program_templates()
    ordered: list[str] = []

    def add_template(template_id: str | None) -> None:
        if not template_id or template_id in ordered:
            return
        ordered.append(template_id)

    add_template(preferred_template_id)

    for summary in summaries:
        if summary.get("split") == split_preference and days_available in (summary.get("days_supported") or []):
            add_template(summary.get("id"))

    for summary in summaries:
        if days_available in (summary.get("days_supported") or []):
            add_template(summary.get("id"))

    add_template("full_body_v1")
    return ordered


def _resolve_template_for_generation(
    *,
    explicit_template_id: str | None,
    profile_template_id: str | None,
    split_preference: str,
    days_available: int,
    nutrition_phase: str,
    available_equipment: list[str],
) -> tuple[str, dict[str, Any]]:
    if explicit_template_id:
        return explicit_template_id, load_program_template(explicit_template_id)

    ordered_candidates = _ordered_candidate_template_ids(
        preferred_template_id=profile_template_id,
        split_preference=split_preference,
        days_available=days_available,
    )

    fallback_template_id = profile_template_id or "full_body_v1"
    fallback_template: dict[str, Any] | None = None

    for candidate_id in ordered_candidates:
        try:
            candidate_template = load_program_template(candidate_id)
        except (FileNotFoundError, ValidationError):
            continue

        if fallback_template is None:
            fallback_template = candidate_template
            fallback_template_id = candidate_id

        session_count, exercise_count = _preview_template_viability(
            template=candidate_template,
            days_available=days_available,
            split_preference=split_preference,
            nutrition_phase=nutrition_phase,
            available_equipment=available_equipment,
        )
        if session_count > 0 and exercise_count > 0:
            return candidate_id, candidate_template

    if fallback_template is not None:
        return fallback_template_id, fallback_template

    raise FileNotFoundError("No valid program templates available for generation")


def _program_display_name(program_id: str) -> str:
    normalized = program_id.replace("_v", " v").replace("_", " ").strip()
    return " ".join(part.capitalize() for part in normalized.split())


def _guide_program_summary(program_id: str) -> dict[str, Any]:
    summaries = list_program_templates()
    summary = next((item for item in summaries if item.get("id") == program_id), None)
    if summary is None:
        raise FileNotFoundError(f"Program template not found: {program_id}")
    return summary


def _guide_day_exercises(template: dict[str, Any], *, day_index: int) -> list[GuideExerciseSummary]:
    sessions = template.get("sessions") or []
    if day_index < 1 or day_index > len(sessions):
        raise IndexError("day index out of range")

    session = sessions[day_index - 1]
    exercises = session.get("exercises") or []
    result: list[GuideExerciseSummary] = []
    for exercise in exercises:
        video = exercise.get("video") if isinstance(exercise.get("video"), dict) else {}
        result.append(
            GuideExerciseSummary(
                id=str(exercise.get("id", "")),
                primary_exercise_id=exercise.get("primary_exercise_id"),
                name=str(exercise.get("name", "")),
                notes=exercise.get("notes"),
                video_youtube_url=video.get("youtube_url"),
            )
        )
    return result


def _resolve_exercise_guide(template: dict[str, Any], *, exercise_id: str) -> GuideExerciseSummary | None:
    sessions = template.get("sessions") or []
    for session in sessions:
        for exercise in session.get("exercises") or []:
            if exercise.get("id") == exercise_id or exercise.get("primary_exercise_id") == exercise_id:
                video = exercise.get("video") if isinstance(exercise.get("video"), dict) else {}
                return GuideExerciseSummary(
                    id=str(exercise.get("id", "")),
                    primary_exercise_id=exercise.get("primary_exercise_id"),
                    name=str(exercise.get("name", "")),
                    notes=exercise.get("notes"),
                    video_youtube_url=video.get("youtube_url"),
                )
    return None


@router.get("/plan/programs", response_model=list[ProgramTemplateSummary])
def plan_list_programs() -> list[dict]:
    return list_program_templates()


@router.get("/plan/guides/programs")
def list_guide_programs() -> list[GuideProgramSummary]:
    summaries = list_program_templates()
    return [
        GuideProgramSummary(
            id=str(item["id"]),
            name=_program_display_name(str(item["id"])),
            split=str(item["split"]),
            days_supported=list(item.get("days_supported") or []),
            description=str(item.get("description") or ""),
        )
        for item in summaries
    ]


@router.get("/plan/guides/programs/{program_id}", responses=GUIDE_RESPONSES)
def get_program_guide(program_id: str) -> ProgramGuideResponse:
    try:
        summary = _guide_program_summary(program_id)
        template = load_program_template(program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    sessions = template.get("sessions") or []
    days = [
        GuideDaySummary(
            day_index=index,
            day_name=str(session.get("name") or f"Day {index}"),
            exercise_count=len(session.get("exercises") or []),
            first_exercise_id=(session.get("exercises") or [{}])[0].get("id") if (session.get("exercises") or []) else None,
        )
        for index, session in enumerate(sessions, start=1)
    ]

    return ProgramGuideResponse(
        id=program_id,
        name=_program_display_name(program_id),
        description=str(summary.get("description") or ""),
        split=str(summary.get("split") or ""),
        days_supported=list(summary.get("days_supported") or []),
        days=days,
    )


@router.get("/plan/guides/programs/{program_id}/days/{day_index}", responses=GUIDE_RESPONSES)
def get_program_day_guide(program_id: str, day_index: int) -> ProgramDayGuideResponse:
    try:
        template = load_program_template(program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    sessions = template.get("sessions") or []
    if day_index < 1 or day_index > len(sessions):
        raise HTTPException(status_code=404, detail="Guide day not found")

    day_name = str((sessions[day_index - 1] or {}).get("name") or f"Day {day_index}")
    exercises = _guide_day_exercises(template, day_index=day_index)
    return ProgramDayGuideResponse(
        program_id=program_id,
        day_index=day_index,
        day_name=day_name,
        exercises=exercises,
    )


@router.get("/plan/guides/programs/{program_id}/exercise/{exercise_id}", responses=GUIDE_RESPONSES)
def get_program_exercise_guide(program_id: str, exercise_id: str) -> ProgramExerciseGuideResponse:
    try:
        template = load_program_template(program_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    exercise = _resolve_exercise_guide(template, exercise_id=exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Guide exercise not found")
    return ProgramExerciseGuideResponse(program_id=program_id, exercise=exercise)


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

    try:
        selected_template_id, template = _resolve_template_for_generation(
            explicit_template_id=payload.template_id,
            profile_template_id=current_user.selected_program_id,
            split_preference=current_user.split_preference,
            days_available=current_user.days_available,
            nutrition_phase=current_user.nutrition_phase or "maintenance",
            available_equipment=current_user.equipment_profile or [],
        )
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
