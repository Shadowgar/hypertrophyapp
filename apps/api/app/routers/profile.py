from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Any, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

WEAK_POINT_MAX_BOOSTED_EXERCISES = 2
WEAK_POINT_SET_DELTA_CAP = 1
WEAK_POINT_TOTAL_SET_BUDGET = 2
WEAK_POINT_MIN_COMPLETION_FOR_BOOST = 90
WEAK_POINT_MIN_READINESS_FOR_BOOST = 65
WEAK_POINT_INTENSITY_MIN_SCALE = 0.93
WEAK_POINT_INTENSITY_MAX_SCALE = 1.03


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


def _monday_of(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _week_window_for(value: date) -> tuple[date, date, date]:
    current_week_start = _monday_of(value)
    target_week_start = current_week_start + timedelta(days=7) if value.weekday() == 6 else current_week_start
    previous_week_start = target_week_start - timedelta(days=7)
    return current_week_start, target_week_start, previous_week_start


def _resolve_rep_range(rep_range: Any) -> tuple[int, int]:
    if not isinstance(rep_range, list):
        return 8, 12
    minimum = int(rep_range[0]) if len(rep_range) > 0 else 8
    maximum = int(rep_range[1]) if len(rep_range) > 1 else minimum
    if minimum > maximum:
        minimum, maximum = maximum, minimum
    return minimum, maximum


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _clamp_scale(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _empty_performance_bucket() -> dict[str, float]:
    return {"sets": 0.0, "reps_sum": 0.0, "weight_sum": 0.0}


def _accumulate_single_planned_exercise(planned_index: dict[str, dict[str, Any]], exercise: dict[str, Any]) -> None:
    primary_exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or "")
    if not primary_exercise_id:
        return

    planned_sets = int(exercise.get("sets", 0) or 0)
    target_min, target_max = _resolve_rep_range(exercise.get("rep_range"))
    target_weight = float(exercise.get("recommended_working_weight", 0) or 0)
    bucket = planned_index.setdefault(
        primary_exercise_id,
        {
            "exercise_id": str(exercise.get("id") or primary_exercise_id),
            "name": str(exercise.get("name") or primary_exercise_id),
            "planned_sets": 0,
            "target_min_sum": 0,
            "target_max_sum": 0,
            "target_count": 0,
            "target_weight_sum": 0.0,
            "target_weight_count": 0,
        },
    )
    bucket["planned_sets"] += max(0, planned_sets)
    bucket["target_min_sum"] += target_min
    bucket["target_max_sum"] += target_max
    bucket["target_count"] += 1
    if target_weight > 0:
        bucket["target_weight_sum"] += target_weight
        bucket["target_weight_count"] += 1


def _accumulate_planned_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    planned_index: dict[str, dict[str, Any]] = {}
    for session in payload.get("sessions") or []:
        for exercise in session.get("exercises") or []:
            _accumulate_single_planned_exercise(planned_index, exercise)
    return planned_index


def _collect_performed_index(logs: list[WorkoutSetLog], planned_index: dict[str, dict[str, Any]]) -> dict[str, dict[str, float]]:
    performed_index: dict[str, dict[str, float]] = {}
    for row in logs:
        key = row.primary_exercise_id or row.exercise_id
        if key not in planned_index:
            continue
        bucket = performed_index.setdefault(key, _empty_performance_bucket())
        bucket["sets"] += 1
        bucket["reps_sum"] += float(row.reps)
        bucket["weight_sum"] += float(row.weight)
    return performed_index


def _resolve_fault_reasons(completed_sets: int, completion_pct: int, average_reps: float, target_min: int, target_max: int) -> tuple[int, list[str]]:
    fault_score = 0
    fault_reasons: list[str] = []

    if completed_sets == 0:
        return 3, ["missed_exercise"]

    if completion_pct < 85:
        fault_score += 2
        fault_reasons.append("low_completion")
    if average_reps < target_min:
        fault_score += 2
        fault_reasons.append("below_target_reps")
    if average_reps > target_max:
        fault_score += 1
        fault_reasons.append("above_target_reps")
    return fault_score, fault_reasons


def _resolve_fault_guidance(completed_sets: int, completion_pct: int, average_reps: float, target_min: int, target_max: int) -> str:
    if completed_sets == 0:
        return "rebuild_exposure_with_conservative_load"
    if completion_pct < 85:
        return "complete_all_planned_sets_before_progression"
    if average_reps < target_min:
        return "reduce_or_hold_load_and_recover"
    if average_reps > target_max:
        return "increase_load_next_exposure"
    return "maintain_or_microload"


def _resolve_fault_level(fault_score: int) -> str:
    if fault_score >= 3:
        return "high"
    if fault_score == 2:
        return "medium"
    if fault_score == 1:
        return "low"
    return "none"


def _build_exercise_fault(
    primary_exercise_id: str,
    planned: dict[str, Any],
    performed: dict[str, float],
) -> tuple[WeeklyExerciseFaultResponse, int, int]:
    planned_sets = int(planned["planned_sets"])
    target_count = max(1, int(planned["target_count"]))
    target_min = int(round(planned["target_min_sum"] / target_count))
    target_max = int(round(planned["target_max_sum"] / target_count))

    target_weight_count = int(planned["target_weight_count"])
    target_weight = (
        float(planned["target_weight_sum"]) / max(1, target_weight_count)
        if target_weight_count > 0
        else 0.0
    )
    completed_sets = int(performed["sets"])
    average_reps = float(performed["reps_sum"]) / completed_sets if completed_sets > 0 else 0.0
    average_weight = float(performed["weight_sum"]) / completed_sets if completed_sets > 0 else 0.0
    completion_pct = int((completed_sets / max(1, planned_sets)) * 100)

    fault_score, fault_reasons = _resolve_fault_reasons(completed_sets, completion_pct, average_reps, target_min, target_max)
    return (
        WeeklyExerciseFaultResponse(
            primary_exercise_id=primary_exercise_id,
            exercise_id=str(planned["exercise_id"]),
            name=str(planned["name"]),
            planned_sets=planned_sets,
            completed_sets=completed_sets,
            completion_pct=completion_pct,
            target_reps_min=target_min,
            target_reps_max=target_max,
            average_performed_reps=round(average_reps, 2),
            target_weight=round(target_weight, 2),
            average_performed_weight=round(average_weight, 2),
            guidance=_resolve_fault_guidance(completed_sets, completion_pct, average_reps, target_min, target_max),
            fault_score=fault_score,
            fault_level=_resolve_fault_level(fault_score),
            fault_reasons=fault_reasons,
        ),
        planned_sets,
        completed_sets,
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
    payload = previous_plan.payload if previous_plan and isinstance(previous_plan.payload, dict) else {}

    planned_index = _accumulate_planned_index(payload)

    logs = (
        db.query(WorkoutSetLog)
        .filter(
            WorkoutSetLog.user_id == user_id,
            WorkoutSetLog.created_at >= datetime.combine(previous_week_start, time.min),
            WorkoutSetLog.created_at < datetime.combine(week_start, time.min),
        )
        .all()
    )
    performed_index = _collect_performed_index(logs, planned_index)

    exercise_faults: list[WeeklyExerciseFaultResponse] = []
    planned_sets_total = 0
    completed_sets_total = 0

    for primary_exercise_id, planned in planned_index.items():
        fault, planned_sets, completed_sets = _build_exercise_fault(
            primary_exercise_id,
            planned,
            performed_index.get(primary_exercise_id, _empty_performance_bucket()),
        )
        planned_sets_total += planned_sets
        completed_sets_total += completed_sets
        exercise_faults.append(fault)

    exercise_faults.sort(key=lambda row: (-row.fault_score, row.completion_pct, row.name))
    completion_pct = int((completed_sets_total / max(1, planned_sets_total)) * 100)
    faulty_exercise_count = sum(1 for row in exercise_faults if row.fault_score > 0)

    return WeeklyPerformanceSummaryResponse(
        previous_week_start=previous_week_start,
        previous_week_end=week_start - timedelta(days=1),
        planned_sets_total=planned_sets_total,
        completed_sets_total=completed_sets_total,
        completion_pct=completion_pct,
        faulty_exercise_count=faulty_exercise_count,
        exercise_faults=exercise_faults,
    )


def _build_weekly_plan_adjustments(
    summary: WeeklyPerformanceSummaryResponse,
    *,
    body_weight: float,
    calories: int,
    protein: int,
    adherence_score: int,
) -> tuple[int, str, WeeklyPlanAdjustmentResponse, dict[str, Any]]:
    calories_per_kg = float(calories) / max(1.0, body_weight)
    protein_per_kg = float(protein) / max(1.0, body_weight)

    global_set_delta = 0
    global_weight_scale = 1.0
    readiness_score = 100

    global_set_delta, global_weight_scale, readiness_score = _resolve_global_adjustments(
        calories_per_kg=calories_per_kg,
        protein_per_kg=protein_per_kg,
        adherence_score=adherence_score,
        base_set_delta=global_set_delta,
        base_weight_scale=global_weight_scale,
        base_readiness=readiness_score,
    )

    weak_point_exercises = [row.primary_exercise_id for row in summary.exercise_faults if row.fault_score > 0][:3]
    overrides: list[WeeklyExerciseAdjustmentResponse] = []
    boosted_exercise_ids: list[str] = []
    remaining_set_budget = WEAK_POINT_TOTAL_SET_BUDGET

    for row in summary.exercise_faults:
        allow_weak_point_boost = (
            row.primary_exercise_id in weak_point_exercises
            and len(boosted_exercise_ids) < WEAK_POINT_MAX_BOOSTED_EXERCISES
            and remaining_set_budget > 0
        )
        override = _resolve_exercise_override(
            row,
            readiness_score=readiness_score,
            allow_weak_point_boost=allow_weak_point_boost,
        )
        if override is not None:
            overrides.append(override)
            if override.set_delta > 0:
                boosted_exercise_ids.append(override.primary_exercise_id)
                remaining_set_budget = max(0, remaining_set_budget - override.set_delta)

    readiness_score = _clamp_int(readiness_score, 1, 100)
    global_guidance = _resolve_global_guidance(readiness_score, summary.faulty_exercise_count)

    response_adjustments = WeeklyPlanAdjustmentResponse(
        global_set_delta=global_set_delta,
        global_weight_scale=round(global_weight_scale, 3),
        weak_point_exercises=weak_point_exercises,
        exercise_overrides=overrides,
    )
    storage_adjustments = {
        "global": {
            "set_delta": response_adjustments.global_set_delta,
            "weight_scale": response_adjustments.global_weight_scale,
        },
        "weak_point_exercises": response_adjustments.weak_point_exercises,
        "exercise_overrides": {
            item.primary_exercise_id: {
                "set_delta": item.set_delta,
                "weight_scale": item.weight_scale,
                "rationale": item.rationale,
            }
            for item in response_adjustments.exercise_overrides
        },
        "weak_point_boosted_exercises": boosted_exercise_ids,
        "weak_point_caps": {
            "max_boosted_exercises": WEAK_POINT_MAX_BOOSTED_EXERCISES,
            "max_set_delta_per_exercise": WEAK_POINT_SET_DELTA_CAP,
            "max_total_weak_point_set_delta": WEAK_POINT_TOTAL_SET_BUDGET,
            "intensity_min_scale": WEAK_POINT_INTENSITY_MIN_SCALE,
            "intensity_max_scale": WEAK_POINT_INTENSITY_MAX_SCALE,
        },
    }
    return readiness_score, global_guidance, response_adjustments, storage_adjustments


def _resolve_global_adjustments(
    *,
    calories_per_kg: float,
    protein_per_kg: float,
    adherence_score: int,
    base_set_delta: int,
    base_weight_scale: float,
    base_readiness: int,
) -> tuple[int, float, int]:
    global_set_delta = base_set_delta
    global_weight_scale = base_weight_scale
    readiness_score = base_readiness

    if calories_per_kg < 24:
        global_set_delta -= 1
        global_weight_scale *= 0.95
        readiness_score -= 20
    elif calories_per_kg < 28:
        global_weight_scale *= 0.975
        readiness_score -= 10
    elif calories_per_kg > 35 and adherence_score >= 4:
        global_weight_scale *= 1.01
        readiness_score += 5

    if protein_per_kg < 1.6:
        global_weight_scale *= 0.98
        readiness_score -= 15
    elif protein_per_kg >= 2.0:
        readiness_score += 3

    if adherence_score <= 2:
        global_weight_scale *= 0.98
        readiness_score -= 15

    return global_set_delta, global_weight_scale, readiness_score


def _resolve_exercise_override(
    row: WeeklyExerciseFaultResponse,
    *,
    readiness_score: int,
    allow_weak_point_boost: bool,
) -> WeeklyExerciseAdjustmentResponse | None:
    if row.fault_score <= 0:
        return None

    set_delta = 0
    weight_scale = 1.0
    rationale = "maintain"

    if "missed_exercise" in row.fault_reasons:
        weight_scale *= 0.95
        rationale = "missed_exercise_restart_conservative"
    elif "low_completion" in row.fault_reasons:
        weight_scale *= 0.975
        rationale = "low_completion_secure_volume"

    if "below_target_reps" in row.fault_reasons:
        weight_scale *= 0.975
        rationale = "below_target_reps_reduce_or_hold"

    if "above_target_reps" in row.fault_reasons and readiness_score >= 70:
        weight_scale *= 1.025
        rationale = "above_target_reps_progress_load"

    weak_point_boost_blocked = any(
        reason in row.fault_reasons
        for reason in ("missed_exercise", "low_completion", "below_target_reps")
    )
    if (
        allow_weak_point_boost
        and not weak_point_boost_blocked
        and row.completion_pct >= WEAK_POINT_MIN_COMPLETION_FOR_BOOST
        and readiness_score >= WEAK_POINT_MIN_READINESS_FOR_BOOST
    ):
        set_delta = min(WEAK_POINT_SET_DELTA_CAP, set_delta + 1)
        rationale = "weak_point_bounded_extra_practice"

    set_delta = _clamp_int(set_delta, -1, WEAK_POINT_SET_DELTA_CAP)
    weight_scale = _clamp_scale(weight_scale, WEAK_POINT_INTENSITY_MIN_SCALE, WEAK_POINT_INTENSITY_MAX_SCALE)

    return WeeklyExerciseAdjustmentResponse(
        primary_exercise_id=row.primary_exercise_id,
        set_delta=set_delta,
        weight_scale=round(weight_scale, 3),
        rationale=rationale,
    )


def _resolve_global_guidance(readiness_score: int, faulty_exercise_count: int) -> str:
    if readiness_score < 55:
        return "recovery_limited_reduce_load_and_complete_quality_volume"
    if faulty_exercise_count > 0:
        return "target_fault_exercises_with_controlled_progression"
    return "progressive_overload_ready"


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
    current_user.selected_program_id = payload.selected_program_id or "full_body_v1"
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


@router.get("/weekly-review/status")
def weekly_review_status(
    db: DbSession,
    current_user: CurrentUser,
) -> WeeklyReviewStatusResponse:
    today = date.today()
    current_week_start, week_start, previous_week_start = _week_window_for(today)
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

    today_is_sunday = today.weekday() == 6
    review_required = today_is_sunday and existing_review is None
    return WeeklyReviewStatusResponse(
        today_is_sunday=today_is_sunday,
        review_required=review_required,
        current_week_start=current_week_start,
        week_start=week_start,
        previous_week_start=previous_week_start,
        previous_week_end=week_start - timedelta(days=1),
        existing_review_submitted=existing_review is not None,
        previous_week_summary=summary,
    )


@router.post("/weekly-review")
def submit_weekly_review(
    payload: WeeklyReviewSubmitRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> WeeklyReviewSubmitResponse:
    today = date.today()
    _current_week_start, default_week_start, _default_previous_week_start = _week_window_for(today)
    week_start = payload.week_start or default_week_start
    previous_week_start = week_start - timedelta(days=7)

    summary = _collect_previous_week_performance_summary(
        db,
        user_id=current_user.id,
        previous_week_start=previous_week_start,
        week_start=week_start,
    )
    readiness_score, global_guidance, adjustment_response, adjustment_storage = _build_weekly_plan_adjustments(
        summary,
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
        adjustments=adjustment_storage,
        summary=summary.model_dump(mode="json"),
    )
    db.add(review_entry)
    db.commit()

    return WeeklyReviewSubmitResponse(
        status="review_logged",
        week_start=week_start,
        previous_week_start=previous_week_start,
        readiness_score=readiness_score,
        global_guidance=global_guidance,
        fault_count=summary.faulty_exercise_count,
        summary=summary,
        adjustments=adjustment_response,
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
