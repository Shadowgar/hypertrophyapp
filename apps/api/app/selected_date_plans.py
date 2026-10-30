"""Selected-date commands: explicit local clock, no prescription policy.

Execution/consent snapshots freeze the whole week's placement in this slice.
Preview uses a transient profile and never flushes or commits a planning change.
"""
from copy import deepcopy
from dataclasses import dataclass
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
PREVIEW_DIGEST_VERSION = 'selected-date-preview-v2'
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
        'dependencies': schedule.get('activation_dependencies'),
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


@dataclass(frozen=True)
class CurrentSchedulingProfile:
    days_available: int | None
    program_id: str | None
    plan: WorkoutPlan | None = None
    week_start: date | None = None


def current_scheduling_profile(db: Session, user: User, planning_instant: datetime) -> CurrentSchedulingProfile:
    """Read effective count/binding without rewriting editable preferences.

    A future activation takes effect here only on its local Monday. Legacy
    profiles and weeks without a dated plan keep the stored availability.
    """
    from .flexible_training import current_sequence
    sequence = current_sequence(db, user.id)
    if sequence:
        return CurrentSchedulingProfile(None, sequence.program_id)
    fallback = CurrentSchedulingProfile(user.days_available, resolve_selected_program_binding_id(user.selected_program_id))
    if not user.scheduling_timezone:
        return fallback
    _, monday = local_week(user.scheduling_timezone, planning_instant)
    rows = active_selected_plans(db.query(WorkoutPlan).filter_by(user_id=user.id, week_start=monday).all(), monday)
    if not rows:
        return CurrentSchedulingProfile(fallback.days_available, fallback.program_id, week_start=monday)
    if len(rows) != 1 or rows[0].schedule_timezone != user.scheduling_timezone:
        raise HTTPException(409, 'Current dated schedule requires reconciliation')
    dates = (rows[0].payload.get('schedule') or {}).get('selected_dates') or []
    if not 2 <= len(dates) <= 5 or len(set(dates)) != len(dates):
        raise HTTPException(409, 'Current dated schedule count requires reconciliation')
    binding = resolve_selected_program_binding_id(rows[0].payload.get('program_template_id'))
    if not binding:
        raise HTTPException(409, 'Current dated program requires reconciliation')
    return CurrentSchedulingProfile(len(dates), binding, plan=rows[0], week_start=monday)


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


def scheduling_context(db: Session, user: User, timezone: str | None, planning_instant: datetime, *, week_start: date | None = None, week_offset: int = 0) -> dict:
    from .routers.plan import _list_user_workout_plans
    zone = user.scheduling_timezone or timezone
    today, monday = local_week(zone, planning_instant)
    current_monday = monday
    if week_offset not in (0, 1):
        raise HTTPException(422, 'Week offset must be current (0) or next (1)')
    if week_start is None:
        week_start = monday + timedelta(days=7 * week_offset)
    if week_start is not None:
        if week_start not in (monday, monday + timedelta(days=7)):
            raise HTTPException(422, 'Select the current or next local Monday–Sunday week')
        monday = week_start
    plans = _list_user_workout_plans(db, user_id=user.id)
    active = active_selected_plans(plans, monday)
    if len(active) > 1:
        raise HTTPException(409, 'Multiple active dated plans require reconciliation')
    row = active[0] if active else None
    # A legacy plan is shown only in its own selected calendar week.
    legacy = next((p for p in plans if p.week_start == monday and not p.payload.get('schedule')
        and resolve_selected_program_binding_id(p.payload.get('program_template_id')) == user.selected_program_id), None)
    plan = identified_plans(db, [row or legacy])[0].payload if row or legacy else None
    if plan is not None:
        plan = {**plan, 'plan_id': (row or legacy).id}
    return {'timezone': zone, 'timezone_persisted': bool(user.scheduling_timezone),
        'local_today': today.isoformat(), 'week_start': monday.isoformat(),
        'current_week_start': current_monday.isoformat(),
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


def live_week_plans(plans: list[WorkoutPlan], monday: date) -> list[WorkoutPlan]:
    return [p for p in plans if p.week_start == monday
        and not (p.payload.get('schedule') or {}).get('mode', '').startswith('selected_dates_superseded')]


def authored_source_slots(payload: dict) -> list[tuple[str, ...]]:
    keys = ('source_slot_id', 'source_sha256', 'artifact_sha256')
    return sorted(tuple(str((exercise.get('source_lineage') or {}).get(key) or '') for key in keys)
        for session in payload.get('sessions') or [] for exercise in session.get('exercises') or [])


def resolve_source_successor(plans: list[WorkoutPlan], week: SelectedWeek, selected_id: str | None):
    """Reserve the next authored ordinal from saved source identity, without writes.

    A future reservation requires a current saved program. Gaps, multiple
    programs, unknown source ordinals and sequence exhaustion require review.
    """
    from .program_loader import load_program_template
    if any(p.week_start > week.week_start
        and not (p.payload.get('schedule') or {}).get('mode', '').startswith('selected_dates_superseded') for p in plans):
        raise HTTPException(409, 'Later saved program reservations require progression reconciliation')
    current_monday = week.local_today - timedelta(days=week.local_today.weekday())
    previous = live_week_plans(plans, week.week_start - timedelta(days=7))
    if week.week_start > current_monday and len(previous) != 1:
        raise HTTPException(409, 'Current-week program is missing or ambiguous; reconcile it before planning next week')
    if week.week_start > current_monday and ((previous[0].payload.get('schedule') or {}).get('mode') != SELECTED_MODE
        or previous[0].schedule_timezone != week.timezone):
        raise HTTPException(409, 'Reconcile current-week selected dates before planning next week')
    if previous and (len(previous) != 1 or resolve_selected_program_binding_id(previous[0].payload.get('program_template_id')) != selected_id):
        raise HTTPException(409, 'Adjacent program identity conflicts; reconcile program progression')
    if selected_id not in AUTHORED:
        if week.week_start > current_monday:
            raise HTTPException(409, 'Next-week source progression is not established for this program; reconciliation required')
        return None, None
    earlier = [p for p in plans if p.week_start < week.week_start
        and resolve_selected_program_binding_id(p.payload.get('program_template_id')) == selected_id
        and not (p.payload.get('schedule') or {}).get('mode', '').startswith('selected_dates_superseded')]
    if not previous:
        if earlier:
            raise HTTPException(409, 'Authored progression has a calendar gap; reconciliation required')
        return None, None
    predecessor = previous[0]
    ordinal = (predecessor.payload.get('mesocycle') or {}).get('authored_week_index')
    template = load_program_template(selected_id)
    source_weeks = template.get('authored_weeks') or []
    if type(ordinal) is not int or not 1 <= ordinal < len(source_weeks):
        raise HTTPException(409, 'Authored source week is unknown or exhausted; reconciliation required')
    expected = authored_source_slots(source_weeks[ordinal-1])
    saved = authored_source_slots(predecessor.payload)
    if not expected or expected != saved:
        raise HTTPException(409, 'Saved authored week lineage does not match the admitted source; reconciliation required')
    # Reject inconsistent or duplicate reservations, rather than counting rows.
    ordinals = [(p.payload.get('mesocycle') or {}).get('authored_week_index') for p in earlier]
    if any(type(value) is not int or value < 1 or value > ordinal for value in ordinals) or len(set(ordinals)) != len(ordinals):
        raise HTTPException(409, 'Authored source week reservations conflict; reconciliation required')
    target = ordinal + 1
    if source_weeks[target-1].get('week_index') != target:
        raise HTTPException(409, 'Authored source sequence is ambiguous; reconciliation required')
    dependency = {'owner': 'app.selected_date_plans.resolve_source_successor',
        'policy': 'saved-predecessor-source-successor-v1', 'program_template_id': selected_id,
        'predecessor_plan_id': predecessor.id, 'predecessor_week_start': predecessor.week_start.isoformat(),
        'predecessor_authored_week_index': ordinal, 'authored_week_index': target}
    return target, dependency


def activation_dependencies(plans, week, progression, generation_input_digest):
    """Digest relevant reservations and advisory context under the command lock."""
    def summary(row):
        return {'plan_id': row.id, 'week_start': row.week_start.isoformat(),
            'placement_revision': int(row.placement_revision or 0),
            'program_template_id': row.payload.get('program_template_id'),
            'content_digest': preview_content_digest(row.payload)}
    predecessor = [p for p in plans if progression and p.id == progression['predecessor_plan_id']]
    neighbors = [p for p in plans if p.week_start in (week.week_start-timedelta(days=7), week.week_start+timedelta(days=7))
        and (p.payload.get('schedule') or {}).get('mode') == SELECTED_MODE]
    return {'version': 'selected-date-dependencies-v2', 'source_progression': progression,
        'generation_input_digest': generation_input_digest,
        'predecessor': [summary(p) for p in predecessor],
        'neighbors': [summary(p) for p in sorted(neighbors, key=lambda p: (p.week_start, p.id))]}


def selected_week_command(*, db: Session, user: User, explicit_template_id: str | None,
    selected_week: SelectedWeek, expected_revision: int | None, preview: bool = False,
    expected_preview_digest: str | None = None) -> dict:
    from .routers.plan import _build_week_plan_runtime_for_user, _current_regenerate_would_replace_with_existing_progress, _list_user_workout_plans
    if not preview:
        lock_history_user(db, user.id)
        db.refresh(user)
    from .flexible_training import guard_calendar
    guard_calendar(db, user.id)
    if user.scheduling_timezone and user.scheduling_timezone != selected_week.timezone:
        raise HTTPException(409, 'Use your configured scheduling timezone; timezone changes need a separate history policy')
    if not preview:
        try:
            selected_week = validate_selected_week(week_start=selected_week.week_start,
                selected_dates=list(selected_week.dates), timezone=selected_week.timezone,
                planning_instant=datetime.now(UTC))
        except SelectedDateError as exc:
            raise HTTPException(409, 'The current local week changed; review this week again before activating') from exc
        current_monday = selected_week.local_today - timedelta(days=selected_week.local_today.weekday())
        if selected_week.week_start > current_monday and not expected_preview_digest:
            raise HTTPException(409, 'Preview next week and supply its content digest before activating')
    selected_id = resolve_selected_program_binding_id(explicit_template_id or user.selected_program_id)
    plans = _list_user_workout_plans(db, user_id=user.id)
    current_plans = [p for p in plans if p.week_start == selected_week.week_start
        and not (p.payload.get('schedule') or {}).get('mode', '').startswith('selected_dates_superseded')]
    if not selected_id and not current_plans and selected_week.week_start > selected_week.local_today:
        # Auto retains the sole saved predecessor; it must not select a new
        # program while placing the next week of that existing program.
        predecessors = live_week_plans(plans, selected_week.week_start - timedelta(days=7))
        if len(predecessors) == 1:
            selected_id = resolve_selected_program_binding_id(predecessors[0].payload.get('program_template_id'))
    if not selected_id and current_plans:
        if len(current_plans) != 1:
            raise HTTPException(409, 'Multiple current-week plans require manual reconciliation')
        # Auto places retained current-week work instead of choosing a new
        # program or regenerating its source prescriptions.
        selected_id = resolve_selected_program_binding_id(current_plans[0].payload.get('program_template_id'))
        if not selected_id:
            raise HTTPException(409, 'Current-week program identity requires manual reconciliation')

    def reject_displaced_program(binding_id):
        if binding_id and any(resolve_selected_program_binding_id(p.payload.get('program_template_id')) != binding_id
            for p in current_plans):
            raise HTTPException(409, 'This week already has another program; an explicit program transition is required')

    reject_displaced_program(selected_id)
    active = active_selected_plans(plans, selected_week.week_start)
    if not selected_id and len(active) == 1:
        selected_id = resolve_selected_program_binding_id(active[0].payload.get('program_template_id'))
    if len(active) > 1 or (active and resolve_selected_program_binding_id(active[0].payload.get('program_template_id')) != selected_id):
        raise HTTPException(409, 'This week already has a dated program; a mode/program transition requires separate confirmation')
    matching = [p for p in current_plans
        if resolve_selected_program_binding_id(p.payload.get('program_template_id')) == selected_id]
    if len(matching) > 1:
        raise HTTPException(409, 'Multiple current-week plans require manual reconciliation')
    existing = matching[0] if matching else None
    if existing and existing.payload.get("customized"):
        raise HTTPException(409,"Customized dates are consent-bound; review a new Customized revision instead of changing them here")
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
    generation_input_digest = None
    progression_dependency = None
    if existing:
        if selected_week.week_start > selected_week.local_today and (existing.payload.get('schedule') or {}).get('mode') != SELECTED_MODE:
            from .program_loader import load_program_template
            source_week_index, progression_dependency = resolve_source_successor(plans, selected_week, selected_id)
            saved_ordinal = (existing.payload.get('mesocycle') or {}).get('authored_week_index')
            source_weeks = load_program_template(selected_id).get('authored_weeks') or []
            if (type(saved_ordinal) is not int or saved_ordinal != source_week_index
                or authored_source_slots(existing.payload) != authored_source_slots(source_weeks[source_week_index-1])):
                raise HTTPException(409, 'Legacy future plan does not match the source successor; reconciliation required')
        # Adding dates to legacy work is also placement-only. Preserve its
        # authored source week, working loads and source-scoped variants.
        base = deepcopy(existing.payload)
        values = {'split': existing.split, 'phase': existing.phase}
    else:
        source_week_index, progression_dependency = resolve_source_successor(
            plans, selected_week, selected_id)
        profile_values = {column.key: deepcopy(getattr(user, column.key)) for column in User.__table__.columns}
        profile_values.update(days_available=len(selected_week.dates), selected_program_id=selected_id,
            program_selection_mode=('manual' if selected_id else user.program_selection_mode), active_frequency_adaptation=None)
        transient_profile = User(**profile_values)
        try:
            with db.no_autoflush:
                runtime = _build_week_plan_runtime_for_user(db=db, current_user=transient_profile,
                    explicit_template_id=selected_id, target_days_override=len(selected_week.dates),
                    generation_mode='selected_date_current', reference_date=max(selected_week.week_start, selected_week.local_today),
                    persist_profile_changes=False, selected_authored_week_index=source_week_index)
        except (FileNotFoundError, KeyError) as exc:
            raise HTTPException(404, 'Selected program template is unavailable') from exc
        except ValidationError as exc:
            raise HTTPException(422, 'Selected program template is invalid') from exc
        except AuthoredAllocationInfeasible as exc:
            raise HTTPException(409, f'Authored schedule is infeasible: {exc}') from exc
        base, values = runtime['response_payload'], runtime['record_values']
        generation_input_digest = runtime.get('generation_input_digest')
        selected_id = resolve_selected_program_binding_id(runtime['selected_template_id'])
    reject_displaced_program(selected_id)
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
    placed['schedule']['activation_dependencies'] = activation_dependencies(
        plans, selected_week, progression_dependency, generation_input_digest)
    if progression_dependency:
        placed['schedule']['source_progression'] = progression_dependency
    elif existing and existing.payload.get('schedule', {}).get('source_progression'):
        placed['schedule']['source_progression'] = deepcopy(existing.payload['schedule']['source_progression'])
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
    if selected_week.week_start == selected_week.local_today - timedelta(days=selected_week.local_today.weekday()):
        user.days_available = len(selected_week.dates)
        user.selected_program_id = selected_id
    db.commit()
    db.refresh(record)
    return identified_plans(db, [record])[0].payload
