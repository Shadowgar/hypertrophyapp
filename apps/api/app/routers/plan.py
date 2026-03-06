from datetime import date
import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from core_engine import (
    evaluate_schedule_adaptation,
    generate_week_plan,
    recommend_phase_transition,
    recommend_progression_action,
    recommend_specialization_adjustments,
    summarize_program_media_and_warmups,
)

from ..database import get_db
from ..deps import get_current_user
from ..models import CoachingRecommendation, SorenessEntry, User, WeeklyCheckin, WeeklyReviewCycle, WorkoutPlan, WorkoutSetLog
from ..program_loader import list_program_templates, load_program_template
from ..schemas import GenerateWeekPlanRequest, ProgramTemplateSummary
from ..schemas import (
    GuideDaySummary,
    GuideExerciseSummary,
    GuideProgramSummary,
    IntelligenceCoachPreviewRequest,
    IntelligenceCoachPreviewResponse,
    ProgramDayGuideResponse,
    ProgramExerciseGuideResponse,
    ProgramGuideResponse,
    ProgramMediaWarmupSummaryResponse,
    ProgressionDecisionResponse,
    ReferenceWorkbookGuidePair,
    ScheduleAdaptationPreviewResponse,
    SpecializationPreviewResponse,
    PhaseTransitionResponse,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
INVALID_TEMPLATE_DETAIL = "Invalid program template schema"
GUIDE_RESPONSES = {
    404: {"description": "Guide resource not found"},
    422: {"description": INVALID_TEMPLATE_DETAIL},
}

REVIEW_SET_DELTA_MIN = -1
REVIEW_SET_DELTA_MAX = 1
REVIEW_ADDITIONAL_SET_CAP = 2
REVIEW_INTENSITY_MIN_SCALE = 0.93
REVIEW_INTENSITY_MAX_SCALE = 1.03


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


def _round_to_increment(weight: float, increment: float = 2.5) -> float:
    return round(max(5.0, weight) / increment) * increment


def _clamp_scale(value: float) -> float:
    return max(0.8, min(1.2, value))


def _clamp_review_set_delta(value: int) -> int:
    return max(REVIEW_SET_DELTA_MIN, min(REVIEW_SET_DELTA_MAX, value))


def _clamp_review_intensity_scale(value: float) -> float:
    return max(REVIEW_INTENSITY_MIN_SCALE, min(REVIEW_INTENSITY_MAX_SCALE, value))


def _resolve_review_adjustments(review_cycle: WeeklyReviewCycle) -> tuple[int, float, dict[str, Any], list[str]]:
    adjustments = review_cycle.adjustments if isinstance(review_cycle.adjustments, dict) else {}
    global_adjustments = adjustments.get("global") if isinstance(adjustments.get("global"), dict) else {}
    global_set_delta = _clamp_review_set_delta(int(global_adjustments.get("set_delta", 0) or 0))
    global_weight_scale = _clamp_review_intensity_scale(
        _clamp_scale(float(global_adjustments.get("weight_scale", 1.0) or 1.0))
    )
    exercise_overrides = adjustments.get("exercise_overrides") if isinstance(adjustments.get("exercise_overrides"), dict) else {}
    weak_points = adjustments.get("weak_point_exercises") if isinstance(adjustments.get("weak_point_exercises"), list) else []
    return global_set_delta, global_weight_scale, exercise_overrides, weak_points


def _apply_exercise_adjustments(
    exercise: dict[str, Any],
    *,
    global_set_delta: int,
    global_weight_scale: float,
    exercise_overrides: dict[str, Any],
) -> None:
    primary_exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or "")
    per_exercise = exercise_overrides.get(primary_exercise_id)
    if not isinstance(per_exercise, dict):
        per_exercise = {}

    exercise_set_delta = _clamp_review_set_delta(int(per_exercise.get("set_delta", 0) or 0))
    exercise_weight_scale = _clamp_review_intensity_scale(
        _clamp_scale(float(per_exercise.get("weight_scale", 1.0) or 1.0))
    )

    original_sets = int(exercise.get("sets", 1) or 1)
    adjusted_sets = original_sets + global_set_delta + exercise_set_delta
    max_sets = max(1, original_sets + REVIEW_ADDITIONAL_SET_CAP)
    exercise["sets"] = max(1, min(max_sets, adjusted_sets))

    original_weight = float(exercise.get("recommended_working_weight", 20) or 20)
    scaled_weight = original_weight * global_weight_scale * exercise_weight_scale
    exercise["recommended_working_weight"] = _round_to_increment(scaled_weight)

    rationale = per_exercise.get("rationale")
    if rationale:
        exercise["adaptive_rationale"] = str(rationale)


def _apply_review_adjustments(plan: dict[str, Any], review_cycle: WeeklyReviewCycle) -> dict[str, Any]:
    global_set_delta, global_weight_scale, exercise_overrides, weak_points = _resolve_review_adjustments(review_cycle)

    for session in plan.get("sessions") or []:
        for exercise in session.get("exercises") or []:
            _apply_exercise_adjustments(
                exercise,
                global_set_delta=global_set_delta,
                global_weight_scale=global_weight_scale,
                exercise_overrides=exercise_overrides,
            )

    plan["adaptive_review"] = {
        "week_start": review_cycle.week_start.isoformat(),
        "reviewed_on": review_cycle.reviewed_on.isoformat(),
        "global_set_delta": global_set_delta,
        "global_weight_scale": global_weight_scale,
        "weak_point_exercises": weak_points,
    }
    return plan


def _template_summary_rank(
    summary: dict[str, Any],
    *,
    split_preference: str,
    days_available: int,
) -> tuple[int, int, int, str]:
    split_rank = 0 if str(summary.get("split") or "") == split_preference else 1
    session_count = int(summary.get("session_count") or 0)
    adaptation_rank = 0 if 2 <= days_available <= 4 and session_count >= 5 else 1
    return (split_rank, adaptation_rank, -session_count, str(summary.get("id") or ""))


def _append_candidate_ids(
    ordered: list[str],
    summaries: list[dict[str, Any]],
    predicate,
) -> None:
    for summary in summaries:
        if not predicate(summary):
            continue
        template_id = str(summary.get("id") or "")
        if template_id and template_id not in ordered:
            ordered.append(template_id)


def _ordered_candidate_template_ids(
    *,
    preferred_template_id: str | None,
    split_preference: str,
    days_available: int,
) -> list[str]:
    summaries = list_program_templates()
    sorted_summaries = sorted(
        summaries,
        key=lambda summary: _template_summary_rank(
            summary,
            split_preference=split_preference,
            days_available=days_available,
        ),
    )
    ordered: list[str] = []

    preferred_id = str(preferred_template_id or "")
    if preferred_id:
        ordered.append(preferred_id)

    _append_candidate_ids(
        ordered,
        sorted_summaries,
        lambda summary: (
            summary.get("split") == split_preference
            and days_available in (summary.get("days_supported") or [])
        ),
    )
    _append_candidate_ids(
        ordered,
        sorted_summaries,
        lambda summary: days_available in (summary.get("days_supported") or []),
    )

    if "full_body_v1" not in ordered:
        ordered.append("full_body_v1")
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


def _resolve_program_name(program_id: str) -> str:
    summaries = list_program_templates()
    match = next((summary for summary in summaries if summary.get("id") == program_id), None)
    if isinstance(match, dict):
        name = str(match.get("name") or "").strip()
        if name:
            return name
    return _program_display_name(program_id)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_reference_workbook_pairs() -> list[dict[str, Any]]:
    provenance_path = _repo_root() / "docs" / "guides" / "provenance_index.json"
    if not provenance_path.exists():
        return []

    try:
        payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    pairs = payload.get("workbook_pdf_pairs")
    if not isinstance(pairs, list):
        return []

    normalized: list[dict[str, Any]] = []
    for row in pairs:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "workbook_asset_path": str(row.get("workbook_asset_path") or ""),
                "workbook_asset_sha256": str(row.get("workbook_asset_sha256") or ""),
                "guide_asset_path": str(row.get("guide_asset_path") or ""),
                "guide_asset_sha256": str(row.get("guide_asset_sha256") or ""),
                "match_score": int(row.get("match_score") or 0),
            }
        )

    return normalized


def _derive_readiness_score(
    *,
    completion_pct: int,
    adherence_score: int,
    soreness_level: str,
    progression_action: str,
) -> int:
    soreness_penalty_by_level = {
        "none": 0,
        "mild": 4,
        "moderate": 10,
        "severe": 18,
    }
    action_penalty = {
        "progress": 0,
        "hold": 5,
        "deload": 18,
    }
    soreness_penalty = soreness_penalty_by_level.get(soreness_level.lower(), 0)
    readiness = int((0.65 * completion_pct) + (8 * adherence_score))
    readiness -= soreness_penalty
    readiness -= action_penalty.get(progression_action, 0)
    return max(0, min(100, readiness))


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


@router.get("/plan/intelligence/reference-pairs", response_model=list[ReferenceWorkbookGuidePair])
def list_reference_workbook_guide_pairs() -> list[ReferenceWorkbookGuidePair]:
    pairs = _load_reference_workbook_pairs()
    return [ReferenceWorkbookGuidePair.model_validate(row) for row in pairs]


@router.post(
    "/plan/intelligence/coach-preview",
    response_model=IntelligenceCoachPreviewResponse,
    responses={
        400: {"description": "Complete profile first"},
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
        raise HTTPException(status_code=400, detail="Complete profile first")

    profile_days = current_user.days_available or payload.from_days
    max_requested_days = max(payload.from_days, payload.to_days, profile_days)

    try:
        selected_template_id, template = _resolve_template_for_generation(
            explicit_template_id=payload.template_id,
            profile_template_id=current_user.selected_program_id,
            split_preference=current_user.split_preference,
            days_available=max_requested_days,
            nutrition_phase=current_user.nutrition_phase or "maintenance",
            available_equipment=current_user.equipment_profile or [],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc

    history_rows = (
        db.query(WorkoutSetLog)
        .filter(WorkoutSetLog.user_id == current_user.id)
        .order_by(WorkoutSetLog.created_at.desc())
        .limit(100)
        .all()
    )
    history = [
        {
            "primary_exercise_id": row.primary_exercise_id,
            "exercise_id": row.exercise_id,
            "next_working_weight": row.weight,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in history_rows
    ]

    schedule = evaluate_schedule_adaptation(
        user_profile={"name": current_user.name},
        split_preference=current_user.split_preference,
        program_template=template,
        history=history,
        phase=current_user.nutrition_phase or "maintenance",
        from_days=payload.from_days,
        to_days=payload.to_days,
        available_equipment=current_user.equipment_profile or [],
    )
    progression = recommend_progression_action(
        completion_pct=payload.completion_pct,
        adherence_score=payload.adherence_score,
        soreness_level=payload.soreness_level,
        average_rpe=payload.average_rpe,
        consecutive_underperformance_weeks=payload.stagnation_weeks,
    )

    readiness_score = (
        payload.readiness_score
        if payload.readiness_score is not None
        else _derive_readiness_score(
            completion_pct=payload.completion_pct,
            adherence_score=payload.adherence_score,
            soreness_level=payload.soreness_level,
            progression_action=str(progression.get("action") or "hold"),
        )
    )
    phase_transition = recommend_phase_transition(
        current_phase=payload.current_phase,
        weeks_in_phase=payload.weeks_in_phase,
        readiness_score=readiness_score,
        progression_action=str(progression.get("action") or "hold"),
        stagnation_weeks=payload.stagnation_weeks,
    )
    specialization = recommend_specialization_adjustments(
        weekly_volume_by_muscle=(schedule.get("to_plan") or {}).get("weekly_volume_by_muscle", {}),
        lagging_muscles=payload.lagging_muscles,
        target_min_sets=payload.target_min_sets,
    )
    media_warmups = summarize_program_media_and_warmups(template)

    response_payload = IntelligenceCoachPreviewResponse(
        template_id=selected_template_id,
        program_name=_resolve_program_name(selected_template_id),
        schedule=ScheduleAdaptationPreviewResponse.model_validate(
            {
                "from_days": schedule.get("from_days"),
                "to_days": schedule.get("to_days"),
                "kept_sessions": schedule.get("kept_sessions"),
                "dropped_sessions": schedule.get("dropped_sessions"),
                "added_sessions": schedule.get("added_sessions"),
                "risk_level": schedule.get("risk_level"),
                "muscle_set_delta": schedule.get("muscle_set_delta"),
                "tradeoffs": schedule.get("tradeoffs"),
            }
        ),
        progression=ProgressionDecisionResponse.model_validate(progression),
        phase_transition=PhaseTransitionResponse.model_validate(phase_transition),
        specialization=SpecializationPreviewResponse.model_validate(specialization),
        media_warmups=ProgramMediaWarmupSummaryResponse.model_validate(media_warmups),
    )

    recommendation_record = CoachingRecommendation(
        user_id=current_user.id,
        template_id=selected_template_id,
        recommendation_type="coach_preview",
        current_phase=payload.current_phase,
        recommended_phase=response_payload.phase_transition.next_phase,
        progression_action=response_payload.progression.action,
        request_payload=payload.model_dump(mode="json"),
        recommendation_payload=response_payload.model_dump(mode="json"),
        status="previewed",
    )
    db.add(recommendation_record)
    db.commit()

    return response_payload


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
        raise HTTPException(status_code=422, detail=INVALID_TEMPLATE_DETAIL) from exc
    history_rows = (
        db.query(WorkoutSetLog)
        .filter(WorkoutSetLog.user_id == current_user.id)
        .order_by(WorkoutSetLog.created_at.desc())
        .limit(100)
        .all()
    )

    history = [
        {
            "primary_exercise_id": row.primary_exercise_id,
            "exercise_id": row.exercise_id,
            "next_working_weight": row.weight,
            "created_at": row.created_at.isoformat() if row.created_at else None,
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
    review_cycle = (
        db.query(WeeklyReviewCycle)
        .filter(WeeklyReviewCycle.user_id == current_user.id, WeeklyReviewCycle.week_start == week_start)
        .order_by(WeeklyReviewCycle.created_at.desc())
        .first()
    )
    if review_cycle is not None:
        plan = _apply_review_adjustments(plan, review_cycle)

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
