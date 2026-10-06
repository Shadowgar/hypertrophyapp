"""Selected-date commands: explicit local clock, no prescription policy.

Execution/consent snapshots freeze the whole week's placement in this slice.
Preview uses a transient profile and never flushes or commits a planning change.
"""
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from core_engine.authored_redistribution import AuthoredAllocationInfeasible
from core_engine.selected_date_scheduler import SelectedDateError, SelectedWeek, place_on_selected_dates, validate_selected_week
from .models import User, WorkoutOccurrence, WorkoutPlan
from .program_loader import resolve_selected_program_binding_id
from .workout_history import lock_history_user
from .workout_identity import identified_plans

SELECTED_MODE = 'selected_dates_v1'
AUTHORED = {'pure_bodybuilding_phase_1_full_body', 'pure_bodybuilding_phase_2_full_body'}
PREVIEW_DIGEST_VERSION = 'selected-date-preview-v1'
_PREVIEW_PROJECTION_FIELDS = frozenset({
    'workout_occurrence_id', 'exercise_occurrence_id', 'plan_id',
    'session_slot', 'execution_slot', 'workout_slot', 'placement_revision',
    'created_at', 'generated_at', 'updated_at',
})


def preview_content_digest(plan: dict) -> str:
    """Bind reviewed content, with stable list order and explicit placement input.

    Preserve program/block headers and every session/exercise prescription field,
    including raw/typed source semantics, lineage, permissions, constraints,
    working loads and variants. Trace narratives, occurrence projection, volatile
    timestamps and placement-history metadata do not prescribe reviewed work.
    """
    def content(value):
        if isinstance(value, dict):
            return {key: content(item) for key, item in value.items()
                if key not in _PREVIEW_PROJECTION_FIELDS
                and key != 'decision_trace' and not key.endswith('_trace')}
        if isinstance(value, list):
            return [content(item) for item in value]
        return value

    schedule = plan.get('schedule') or {}
    prescription = content({key: value for key, value in plan.items() if key not in ('schedule', 'user')})
    for session in prescription.get('sessions') or []:
        # identified_sessions adds this duplicate plan-identity projection.
        # The actual selected week stays bound explicitly below.
        session.pop('week_start', None)
    canonical = {
        'version': PREVIEW_DIGEST_VERSION,
        'placement': {key: schedule.get(key) for key in ('week_start', 'timezone', 'selected_dates')},
        'prescription': prescription,
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    return sha256(encoded.encode('utf-8')).hexdigest()


def local_week(timezone: str | None, planning_instant: datetime) -> tuple[date, date]:
    if not timezone or len(timezone) > 64:
        raise HTTPException(422, 'Select an explicit IANA timezone')
    try:
        today = planning_instant.astimezone(ZoneInfo(timezone)).date()
    except (ZoneInfoNotFoundError, ValueError, KeyError) as exc:
        raise HTTPException(422, 'Select a valid IANA timezone') from exc
    return today, today - timedelta(days=today.weekday())


def active_selected_plans(plans: list[WorkoutPlan], week_start: date) -> list[WorkoutPlan]:
    return [p for p in plans if p.week_start == week_start and (p.payload.get('schedule') or {}).get('mode') == SELECTED_MODE]


def validate_request(payload, planning_instant: datetime) -> SelectedWeek:
    if payload.selected_dates is None or payload.week_start is None or payload.timezone is None:
        raise HTTPException(422, 'Selected dates require a week start and IANA timezone')
    if payload.target_days is not None and payload.target_days != len(payload.selected_dates):
        raise HTTPException(422, 'Target day count must equal the selected date count')
    try:
        return validate_selected_week(week_start=payload.week_start, selected_dates=payload.selected_dates,
            timezone=payload.timezone, planning_instant=planning_instant)
    except SelectedDateError as exc:
        raise HTTPException(422, str(exc)) from exc


def scheduling_context(db: Session, user: User, timezone: str | None, planning_instant: datetime) -> dict:
    from .routers.plan import _list_user_workout_plans
    zone = user.scheduling_timezone or timezone
    today, monday = local_week(zone, planning_instant)
    plans = _list_user_workout_plans(db, user_id=user.id)
    active = active_selected_plans(plans, monday)
    if len(active) > 1:
        raise HTTPException(409, 'Multiple active dated plans require reconciliation')
    row = active[0] if active else None
    # Show a current legacy plan only; a previous/future week cannot seed dates.
    legacy = next((p for p in plans if p.week_start == monday and not p.payload.get('schedule')
        and resolve_selected_program_binding_id(p.payload.get('program_template_id')) == user.selected_program_id), None)
    plan = identified_plans(db, [row or legacy])[0].payload if row or legacy else None
    return {'timezone': zone, 'timezone_persisted': bool(user.scheduling_timezone),
        'local_today': today.isoformat(), 'week_start': monday.isoformat(),
        'selected_dates': (row.payload['schedule']['selected_dates'] if row else []),
        'placement_revision': (int(row.placement_revision or 0) if row else 0), 'plan': plan}


def neighbor_context(plans: list[WorkoutPlan], week: SelectedWeek) -> tuple[dict | None, dict | None]:
    contexts = []
    for side, offset in (('previous', -7), ('next', 7)):
        rows = active_selected_plans(plans, week.week_start + timedelta(days=offset))
        if len(rows) != 1 or rows[0].schedule_timezone != week.timezone:
            contexts.append(None)
            continue
        sessions = rows[0].payload.get('sessions') or []
        if not sessions:
            contexts.append(None)
            continue
        session = sessions[-1] if side == 'previous' else sessions[0]
        try:
            day = date.fromisoformat(session['scheduled_date'])
        except (ValueError, KeyError, TypeError):
            contexts.append(None)
            continue
        contexts.append({'date': day, 'exercises': deepcopy(session.get('exercises') or [])})
    return tuple(contexts)


def selected_week_command(*, db: Session, user: User, explicit_template_id: str | None,
    selected_week: SelectedWeek, expected_revision: int | None, preview: bool = False,
    expected_preview_digest: str | None = None) -> dict:
    from .routers.plan import _build_week_plan_runtime_for_user, _current_regenerate_would_replace_with_existing_progress, _list_user_workout_plans
    if not preview:
        lock_history_user(db, user.id)
        db.refresh(user)
    if user.scheduling_timezone and user.scheduling_timezone != selected_week.timezone:
        raise HTTPException(409, 'Use your configured scheduling timezone; timezone changes need a separate history policy')
    if not preview:
        try:
            selected_week = validate_selected_week(week_start=selected_week.week_start,
                selected_dates=list(selected_week.dates), timezone=selected_week.timezone,
                planning_instant=datetime.now(UTC))
        except SelectedDateError as exc:
            raise HTTPException(409, 'The current local week changed; review this week again before activating') from exc
    selected_id = resolve_selected_program_binding_id(explicit_template_id or user.selected_program_id)
    plans = _list_user_workout_plans(db, user_id=user.id)
    active = active_selected_plans(plans, selected_week.week_start)
    if not selected_id and len(active) == 1:
        selected_id = resolve_selected_program_binding_id(active[0].payload.get('program_template_id'))
    if len(active) > 1 or (active and resolve_selected_program_binding_id(active[0].payload.get('program_template_id')) != selected_id):
        raise HTTPException(409, 'This week already has a dated program; a mode/program transition requires separate confirmation')
    matching = [p for p in plans if p.week_start == selected_week.week_start
        and not (p.payload.get('schedule') or {}).get('mode', '').startswith('selected_dates_superseded')
        and resolve_selected_program_binding_id(p.payload.get('program_template_id')) == selected_id]
    if len(matching) > 1:
        raise HTTPException(409, 'Multiple current-week plans require manual reconciliation')
    existing = matching[0] if matching else None
    prior_revision = int(existing.placement_revision or 0) if existing else 0
    if (prior_revision and expected_revision is None) or (expected_revision is not None and expected_revision != prior_revision):
        raise HTTPException(409, 'Schedule changed; reload the current placement revision')
    # Includes consent snapshots and undone/completed work. Never infer unstarted
    # from the absence of effective sets alone.
    if db.query(WorkoutOccurrence).filter_by(user_id=user.id, week_start=selected_week.week_start).first():
        raise HTTPException(409, 'This week has an execution or consent snapshot; its dates cannot be regenerated')
    if existing and _current_regenerate_would_replace_with_existing_progress(db=db, current_user=user,
        plan_runtime={'record_values': {'week_start': selected_week.week_start, 'payload': existing.payload}}):
        raise HTTPException(409, 'This week has workout progress; its dates cannot be regenerated')

    same_count = bool(existing and len(existing.payload.get('sessions') or []) == len(selected_week.dates))
    if existing:
        # Adding dates to legacy work is also placement-only. Preserve its
        # authored source week, working loads and source-scoped variants.
        base = deepcopy(existing.payload)
        values = {'split': existing.split, 'phase': existing.phase}
    else:
        profile_values = {column.key: deepcopy(getattr(user, column.key)) for column in User.__table__.columns}
        profile_values.update(days_available=len(selected_week.dates), selected_program_id=selected_id,
            program_selection_mode=('manual' if selected_id else user.program_selection_mode), active_frequency_adaptation=None)
        transient_profile = User(**profile_values)
        try:
            with db.no_autoflush:
                runtime = _build_week_plan_runtime_for_user(db=db, current_user=transient_profile,
                    explicit_template_id=selected_id, target_days_override=len(selected_week.dates),
                    generation_mode='selected_date_current', reference_date=selected_week.local_today,
                    persist_profile_changes=False)
        except (FileNotFoundError, KeyError) as exc:
            raise HTTPException(404, 'Selected program template is unavailable') from exc
        except ValidationError as exc:
            raise HTTPException(422, 'Selected program template is invalid') from exc
        except AuthoredAllocationInfeasible as exc:
            raise HTTPException(409, f'Authored schedule is infeasible: {exc}') from exc
        base, values = runtime['response_payload'], runtime['record_values']
        selected_id = resolve_selected_program_binding_id(runtime['selected_template_id'])
    if selected_id not in AUTHORED and len(base.get('sessions') or []) != len(selected_week.dates):
        raise HTTPException(409, 'Generated program cannot fit the exact selected date count')
    previous, following = neighbor_context(plans, selected_week)
    revision = prior_revision + 1
    try:
        placed = place_on_selected_dates(base, selected_week, placement_revision=revision,
            previous_context=previous, next_context=following,
            preserve_grouping=same_count or selected_id not in AUTHORED or (existing is None and len(selected_week.dates) == 5))
    except SelectedDateError as exc:
        raise HTTPException(409, str(exc)) from exc
    if selected_week.dates[0] < selected_week.local_today:
        placed['schedule']['spacing']['warnings'].append('Elapsed selected dates are placements only; no performed history is created.')
    placed['schedule']['revision_policy'] = 'unstarted-placement-v1; execution/consent freezes the week'
    if existing and not same_count:
        placed['schedule']['replaces_plan_id'] = existing.id
    digest = preview_content_digest(placed)
    placed['schedule']['preview_digest'] = digest
    placed['schedule']['preview_digest_version'] = PREVIEW_DIGEST_VERSION
    if not preview and expected_preview_digest is not None and expected_preview_digest.lower() != digest:
        raise HTTPException(409, 'Preview content changed; review the schedule again before activating')
    if preview:
        return placed
    if existing and same_count:
        record = existing
        record.payload = placed
    else:
        record = WorkoutPlan(user_id=user.id, week_start=selected_week.week_start,
            split=values['split'], phase=values['phase'], payload=placed)
        db.add(record)
        if existing:
            old = deepcopy(existing.payload)
            old.setdefault('schedule', {})['mode'] = 'selected_dates_superseded_v1'
            old['schedule']['superseded_by_placement_revision'] = revision
            existing.payload = old
    record.placement_revision = revision
    record.schedule_timezone = selected_week.timezone
    user.scheduling_timezone = selected_week.timezone
    user.days_available = len(selected_week.dates)
    user.selected_program_id = selected_id
    db.commit()
    db.refresh(record)
    return identified_plans(db, [record])[0].payload
