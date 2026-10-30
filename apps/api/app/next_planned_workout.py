"""Read-only outstanding-session preview and existing-rule date amendment.

This is an adapter to selected_week_command, not a carry-forward scheduler.
Execution/consent snapshots keep the existing whole-week freeze boundary.
"""
from datetime import date, datetime
from copy import deepcopy

from fastapi import HTTPException
from .models import WorkoutPlan, WorkoutOccurrence, WorkoutSetLog, WorkoutLogCommand, WorkoutSessionState
from .selected_date_plans import AUTHORED, SELECTED_MODE, local_week, selected_week_command
from .workout_history import lock_history_user
from .workout_identity import identified_plans
from core_engine.selected_date_scheduler import validate_selected_week, SelectedDateError


def _review(db, user, planning_instant: datetime):
    plans = db.query(WorkoutPlan).filter_by(user_id=user.id).all()
    plans = [p for p in plans if (p.payload.get('schedule') or {}).get('mode') == SELECTED_MODE]
    if not plans:
        return None
    today, monday = local_week(user.scheduling_timezone, planning_instant)
    occupied = {r.id for r in db.query(WorkoutOccurrence).filter_by(user_id=user.id).all()}
    for model in (WorkoutSetLog, WorkoutLogCommand, WorkoutSessionState):
        occupied.update(r.workout_occurrence_id for r in db.query(model).filter_by(user_id=user.id).all()
            if r.workout_occurrence_id)
    candidates = []
    dated_sessions = []
    for row in plans:
        for session in identified_plans(db, [row])[0].payload.get('sessions') or []:
            original = session.get('scheduled_date')
            try:
                calendar_date = date.fromisoformat(original)
            except (ValueError, TypeError):
                raise HTTPException(409, 'A planned date requires reconciliation before moving workouts') from None
            dated_sessions.append((row, session, calendar_date))
            if session['workout_occurrence_id'] not in occupied and calendar_date != today:
                candidates.append((calendar_date, row.week_start, row.id, session['session_slot'], row, session))
    if not candidates:
        return None
    _, _, _, _, row, session = min(candidates, key=lambda v: v[:4])
    value = {'plan_id': row.id, 'workout_occurrence_id': session['workout_occurrence_id'],
        'original_date': session['scheduled_date'], 'local_today': today.isoformat(),
        'timezone': user.scheduling_timezone, 'program_template_id': row.payload.get('program_template_id'),
        'placement_revision': int(row.placement_revision or 0), 'session': deepcopy(session),
        'can_move': False, 'blocked_reason': None, 'preview_digest': None}
    try:
        if any(day == today for _, _, day in dated_sessions):
            raise HTTPException(409, 'A workout is already scheduled today; its placement cannot be overwritten')
        if row.payload.get('customized') or row.payload.get('program_template_id') not in AUTHORED:
            raise HTTPException(409, 'Customized dates require their existing consent-bound date amendment in Customize')
        if row.week_start != monday:
            raise HTTPException(409, 'Moving work across local weeks requires a carry-forward and source-week progression contract; keep the original date')
        if row.schedule_timezone != user.scheduling_timezone:
            raise HTTPException(409, 'The saved timezone requires reconciliation before changing dates')
        if db.query(WorkoutOccurrence).filter_by(user_id=user.id, week_start=row.week_start).first():
            raise HTTPException(409, 'This week has an execution or consent snapshot; its dates cannot be regenerated')
        dates = [date.fromisoformat(s.get('scheduled_date')) for s in row.payload.get('sessions') or []]
        if [d.isoformat() for d in dates] != (row.payload.get('schedule') or {}).get('selected_dates'):
            raise HTTPException(409, 'Saved session dates and selected dates require reconciliation')
        index = session['session_slot']
        dates[index] = today
        if dates != sorted(set(dates)):
            raise HTTPException(409, 'Moving this missed session would reorder or overlap other source sessions; a carry-forward policy is required')
        selected = validate_selected_week(week_start=monday, selected_dates=dates,
            timezone=user.scheduling_timezone, planning_instant=planning_instant)
        preview = selected_week_command(db=db, user=user, explicit_template_id=row.payload['program_template_id'],
            selected_week=selected, expected_revision=row.placement_revision, preview=True)
        value.update(can_move=True, preview_digest=preview['schedule']['preview_digest'])
    except HTTPException as exc:
        value['blocked_reason'] = str(exc.detail)
    except (SelectedDateError, ValueError, TypeError):
        value['blocked_reason'] = 'Saved dates cannot be safely moved; review the existing selected-date rules in Week'
    return value


def next_planned_workout(db, user, planning_instant: datetime):
    return _review(db, user, planning_instant)


def move_next_planned_workout(db, user, payload, planning_clock):
    lock_history_user(db, user.id)
    db.refresh(user)
    planning_instant = planning_clock()
    value = _review(db, user, planning_instant)
    expected = {'plan_id': payload.plan_id, 'workout_occurrence_id': payload.workout_occurrence_id,
        'original_date': payload.expected_original_date.isoformat(),
        'local_today': payload.expected_local_today.isoformat(),
        'placement_revision': payload.expected_placement_revision, 'preview_digest': payload.expected_preview_digest}
    if value is None or any(value[key] != item for key, item in expected.items()):
        raise HTTPException(409, 'The reviewed workout or local date changed; reload the preview before confirming')
    if not value['can_move']:
        raise HTTPException(409, value['blocked_reason'])
    row = db.query(WorkoutPlan).filter_by(id=value['plan_id'], user_id=user.id).one()
    dates = [date.fromisoformat(s['scheduled_date']) for s in row.payload['sessions']]
    dates[value['session']['session_slot']] = payload.expected_local_today
    selected = validate_selected_week(week_start=row.week_start, selected_dates=dates,
        timezone=user.scheduling_timezone, planning_instant=planning_instant)
    # Existing command reacquires the same User lock, rechecks snapshots,
    # prescription digest, source rest and adjacent schedules before its commit.
    return selected_week_command(db=db, user=user, explicit_template_id=row.payload['program_template_id'],
        selected_week=selected, expected_revision=payload.expected_placement_revision,
        expected_preview_digest=payload.expected_preview_digest)
