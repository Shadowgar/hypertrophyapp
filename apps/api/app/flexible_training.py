"""Account-serialized, date-independent Authored lifecycle; existing logger owns sets."""
from collections import defaultdict
from copy import deepcopy
from datetime import UTC, date, datetime
from hashlib import sha256
import json
from uuid import UUID, uuid4, uuid5
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from core_engine.history_status import occurrence_coverage, working

from .models import (User, TrainingSequence, TrainingSequenceCommand, WorkoutOccurrence,
    WorkoutPlan, WorkoutSetLog, WorkoutLogCommand, WorkoutSessionState, AuthoredInitialCalibration)
from .flexible_source import native_source, evaluate_rest
from .workout_history import effective_set_logs
from .workout_identity import identified_sessions, NAMESPACE


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str, allow_nan=False).encode()).hexdigest()


def lock_user(db, user_id):
    db.execute(select(User.id).where(User.id == user_id).with_for_update()).scalar_one()


def current_sequence(db, user_id):
    return db.query(TrainingSequence).filter(TrainingSequence.user_id == user_id,
        TrainingSequence.state.in_(['active', 'attention_required'])).one_or_none()


def guard_calendar(db, user_id):
    user = db.get(User, user_id)
    if current_sequence(db, user_id) or (user and user.schedule_mode == "flexible"):
        raise HTTPException(409, 'A Flexible program owns the current training sequence; calendar generation cannot replace it')


def _day(sequence):
    return datetime.now(UTC).astimezone(ZoneInfo(sequence.timezone)).date()


def _profile(user):
    return {key: getattr(user, key) for key in ('selected_program_id', 'equipment_profile',
        'movement_restrictions', 'schedule_mode', 'session_time_budget_minutes')}


def _dose(session):
    value = deepcopy(session)
    for key in ('workout_occurrence_id', 'plan_id', 'week_start', 'session_slot', 'execution_context'):
        value.pop(key, None)
    for exercise in value.get('exercises', []):
        for key in ('exercise_occurrence_id', 'execution_slot', 'authored_constraint',
                'performed_variant', 'substitution_consent', 'substitution_decisions'):
            exercise.pop(key, None)
    return value


def _rows(db, user_id, occurrence_id=None):
    query = effective_set_logs(db).filter(WorkoutSetLog.user_id == user_id)
    if occurrence_id:
        query = query.filter(WorkoutSetLog.workout_occurrence_id == occurrence_id)
    return query.all()


def _coverage(session, rows):
    raw = occurrence_coverage(session, rows)
    names = {item.get('exercise_occurrence_id'): item.get('name', '') for item in session.get('exercises', [])}
    return {'known': raw['known'], 'required': raw['working_sets_planned'],
        'completed': raw['working_sets_completed'], 'complete': raw['complete'],
        'missing': [{'exercise_occurrence_id': slot, 'set_index': index, 'name': names.get(slot, '')}
            for slot, index in raw['missing']]}


def _catalog(db, sequence):
    occurrences = db.query(WorkoutOccurrence).filter_by(user_id=sequence.user_id, sequence_id=sequence.id).order_by(WorkoutOccurrence.source_position).all()
    for row in occurrences:
        if (row.payload.get('workout_occurrence_id') != row.id or row.payload.get('session_id') != row.workout_id
                or any(exercise.get('exercise_occurrence_id') != str(uuid5(UUID(row.id), f'exercise-slot/{index}'))
                    for index, exercise in enumerate(row.payload.get('exercises', [])))):
            raise ValueError('Frozen source occurrence or exercise identity changed')
    manifest = sequence.source_catalog.get('manifest')
    actual = [{'position': row.source_position, 'source_week': row.source_week, 'source_session': row.source_session,
        'occurrence_id': row.id, 'prescription_digest': digest(_dose(row.payload))} for row in occurrences]
    if manifest != actual:
        raise ValueError('Frozen source occurrence manifest is missing or changed')
    return {**deepcopy(sequence.source_catalog), 'items': [
        {'position': row.source_position, 'source_week': row.source_week,
         'source_session': row.source_session, 'session': deepcopy(row.payload)} for row in occurrences]}


def _actual_days(db, sequence):
    snapshots = {row.id: row for row in db.query(WorkoutOccurrence).filter_by(user_id=sequence.user_id, sequence_id=sequence.id).all()}
    result = defaultdict(list)
    for row in _rows(db, sequence.user_id):
        snapshot = snapshots.get(row.workout_occurrence_id)
        if not snapshot or not working(row):
            continue
        exercise = next((item for item in snapshot.payload.get('exercises', [])
            if item.get('exercise_occurrence_id') == row.exercise_occurrence_id), None)
        if not exercise:
            continue
        slot = (exercise.get('source_lineage') or {}).get('source_slot_id')
        # A legacy placement is not reliable actual-date evidence for hard rest.
        if slot and row.performed_local_date is not None:
            result[slot].append(row.performed_local_date)
    return dict(result)


def _rest(db, sequence, occurrence, day):
    try:
        return evaluate_rest(_catalog(db, sequence), occurrence.source_position, _actual_days(db, sequence), day)
    except ValueError as exc:
        return {'blockers': [{'code': 'source_admission_conflict', 'message': str(exc)}], 'earliest_day': None}


def next_training(db, user, sequence=None):
    sequence = sequence or current_sequence(db, user.id)
    if sequence is None and user.schedule_mode == 'flexible':
        sequence = db.query(TrainingSequence).filter_by(user_id=user.id).order_by(TrainingSequence.created_at.desc()).first()
    if sequence is None:
        return {'mode': 'calendar', 'action': 'none'}
    day = _day(sequence)
    result = {'mode': 'flexible', 'sequence_id': sequence.id, 'revision': sequence.revision,
        'source_position': sequence.cursor, 'state': sequence.state, 'local_day': str(day), 'timezone': sequence.timezone,
        'expected_sessions_per_week': sequence.expected_sessions_per_week,
        'source_notice': sequence.source_catalog.get('coverage_notice'), 'blockers': [],
        'resolution_options': [], 'action': 'none', 'occurrence_id': None}
    occurrence = db.query(WorkoutOccurrence).filter_by(user_id=user.id, sequence_id=sequence.id, source_position=sequence.cursor).one_or_none()
    if occurrence is None or sequence.state in ('finished', 'retired'):
        if sequence.state not in ('finished', 'retired'):
            result.update(action='blocked', blockers=[{'code': 'source_admission_conflict',
                'message': 'Current frozen source occurrence is missing'}], resolution_options=['reconcile', 'retire'])
        result['digest'] = digest(result)
        return result
    session = deepcopy(occurrence.payload)
    session['execution_context'] = deepcopy(occurrence.execution_context)
    coverage = _coverage(session, _rows(db, user.id, occurrence.id))
    rest = _rest(db, sequence, occurrence, day)
    blockers = rest['blockers']
    if digest(_dose(session)) != occurrence.prescription_digest:
        blockers.append({'code': 'source_admission_conflict', 'message': 'Frozen prescription identity changed'})
    if not coverage['known']:
        blockers.append({'code': 'coverage_unknown', 'message': 'Required working-set coverage is ambiguous'})
    context = occurrence.execution_context or {}
    state = occurrence.execution_state
    action = 'start' if state == 'planned' else 'resume' if state == 'paused' or context.get('local_day') != str(day) else 'finish' if coverage['complete'] else 'active'
    if blockers or sequence.state == 'attention_required':
        action = 'blocked'
    result.update(action=action, session=session, occurrence_id=occurrence.id,
        execution_context=deepcopy(occurrence.execution_context), coverage=coverage,
        advancement=deepcopy(occurrence.advancement), blockers=blockers,
        resolution_options=['reconcile', 'retire'] if action == 'blocked' else [],
        workload={'exercise_count': len(session.get('exercises', [])), 'working_sets': coverage['required'],
            'time_goal_minutes': user.session_time_budget_minutes, 'duration_estimate_minutes': None})
    result['digest'] = digest({**result, 'profile': _profile(user),
        'receipts': [(r.id, r.set_index, r.performed_local_date) for r in _rows(db, user.id, occurrence.id)]})
    return result


def _legacy_pending(db, user):
    snapshots = {r.id: r for r in db.query(WorkoutOccurrence).filter_by(user_id=user.id).all()}
    rows = _rows(db, user.id)
    pending = []
    for plan in db.query(WorkoutPlan).filter_by(user_id=user.id).all():
        if (plan.payload.get('schedule') or {}).get('mode') == 'selected_dates_superseded_v1':
            continue
        sessions = identified_sessions(plan, snapshots)
        if sessions and all(occurrence_coverage(session, [r for r in rows if r.workout_occurrence_id == session['workout_occurrence_id']])['complete'] for session in sessions):
            continue
        pending.append(plan)
    return pending


def enrollment_preview(db, user, payload):
    try:
        ZoneInfo(payload.timezone)
        source = native_source(payload.program_id)
    except (ValueError, KeyError) as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        if type(exc).__name__ == 'ZoneInfoNotFoundError':
            raise HTTPException(422, 'Unknown timezone') from exc
        raise
    blockers = []
    if not user.split_preference or user.equipment_profile is None:
        blockers.append({'code': 'profile_incomplete', 'message': 'Save your training setup and equipment before reviewing Flexible enrollment'})
    if current_sequence(db, user.id):
        blockers.append({'code': 'current_sequence_exists', 'message': 'A current Flexible program already exists'})
    pending = _legacy_pending(db, user)
    legacy = pending[0] if len(pending) == 1 else None
    if pending:
        if len(pending) != 1 or payload.switch_plan_id != legacy.id:
            blockers.append({'code': 'legacy_reservation_conflict', 'message': 'Review one entirely unstarted plan with Switch to Flexible; multiple outstanding reservations require reconciliation'})
        else:
            ids = [s['workout_occurrence_id'] for s in identified_sessions(legacy)]
            activity = any(db.query(model).filter(model.user_id == user.id, model.workout_occurrence_id.in_(ids)).first()
                for model in (WorkoutSetLog, WorkoutLogCommand, WorkoutSessionState, AuthoredInitialCalibration))
            snapshots = db.query(WorkoutOccurrence).filter_by(user_id=user.id, plan_id=legacy.id).first()
            old = legacy.payload
            ordinal = (old.get('mesocycle') or {}).get('authored_week_index')
            if old.get('program_template_id') != source['program_id'] or ordinal != 1:
                blockers.append({'code': 'legacy_source_mapping_required', 'message': 'V1 conversion requires the first native source block; later blocks need an audited completed-source mapping'})
            native_slots = {e['source_lineage']['source_slot_id']: e for i in source['items'] if i['source_week'] == 1 for e in i['session']['exercises']}
            old_slots = [e for s in old.get('sessions', []) for e in s.get('exercises', [])]
            keys = [(e.get('source_lineage') or {}).get('source_slot_id') for e in old_slots]
            source_fields = ('id', 'primary_exercise_id', 'rep_range', 'load_semantics',
                'execution_modifiers', 'source_lineage', 'authored_prescription', 'sets',
                'source_relationships', 'source_approved_alternatives')
            if keys != list(native_slots) or any(
                digest({k: e.get(k) for k in source_fields}) !=
                digest({k: native_slots.get(slot, {}).get(k) for k in source_fields}) for slot, e in zip(keys, old_slots)):
                blockers.append({'code': 'legacy_source_mismatch', 'message': 'Saved source identities or prescriptions differ from the admitted native source'})
            if snapshots or activity:
                blockers.append({'code': 'legacy_started', 'message': 'Consent snapshots or recorded activity prevent conversion'})
    elif payload.switch_plan_id:
        blockers.append({'code': 'legacy_reservation_changed', 'message': 'The reviewed unstarted reservation is no longer available'})
    binding = {'input': payload.model_dump(mode='json'), 'source': source['source_digest'], 'profile': _profile(user),
        'legacy': [(p.id, p.placement_revision, p.payload) for p in pending], 'blockers': blockers}
    return {'digest': digest(binding), 'program_id': source['program_id'], 'session_count': len(source['items']),
        'total_working_sets': sum(e['sets'] for i in source['items'] for e in i['session']['exercises']),
        'first_session': source['items'][0]['session'], 'legacy_plan_id': legacy.id if legacy else None,
        'available': not blockers, 'blockers': blockers, 'source_notice': source['coverage_notice']}, source


def _replay(db, user_id, command_id, request_digest):
    saved = db.query(TrainingSequenceCommand).filter_by(user_id=user_id, command_id=command_id).first()
    if saved:
        if saved.request_digest != request_digest:
            raise HTTPException(409, 'Command identifier already binds a different request')
        return deepcopy(saved.response)
    return None


def _receipt(db, user, sequence, command_id, request_digest, operation, result):
    db.add(TrainingSequenceCommand(user_id=user.id, command_id=command_id, request_digest=request_digest,
        sequence_id=sequence.id, operation=operation, response=deepcopy(result)))
    db.commit()
    return result


def enroll(db, user, payload):
    if payload.command_id.startswith('server/'):
        raise HTTPException(422, 'Reserved lifecycle command namespace')
    lock_user(db, user.id)
    db.refresh(user)
    request_digest = digest({'operation': 'enroll', 'payload': payload.model_dump(mode='json')})
    replay = _replay(db, user.id, payload.command_id, request_digest)
    if replay is not None:
        return replay
    from .routers.training import EnrollmentPreview
    reviewed = EnrollmentPreview(**payload.model_dump(include=set(EnrollmentPreview.model_fields)))
    preview, source = enrollment_preview(db, user, reviewed)
    if not payload.confirmed or preview['digest'] != payload.preview_digest or not preview['available']:
        raise HTTPException(409, {'message': 'Enrollment changed or needs explicit consent', 'preview': preview})
    sequence = TrainingSequence(id=str(uuid4()), user_id=user.id, program_id=source['program_id'],
        source_digest=source['source_digest'], source_catalog={k: deepcopy(v) for k, v in source.items() if k != 'items'},
        timezone=payload.timezone, expected_sessions_per_week=payload.expected_sessions_per_week,
        revision=1, cursor=0, state='active', consent={'confirmed': True, 'preview_digest': preview['digest'],
            'switch_plan_id': payload.switch_plan_id, 'timestamp': datetime.now(UTC).isoformat()})
    db.add(sequence)
    db.flush()
    manifest = []
    for item in source['items']:
        identity = str(uuid5(NAMESPACE, f'{user.id}/{sequence.id}/source/{item["source_week"]}/{item["source_session"]}'))
        session = deepcopy(item['session'])
        session.update(workout_occurrence_id=identity, session_slot=item['position'],
            session_id=f'flexible/{identity}', title=session.get('name') or 'Authored workout')
        for index, exercise in enumerate(session['exercises']):
            exercise['exercise_occurrence_id'] = str(uuid5(UUID(identity), f'exercise-slot/{index}'))
            exercise['execution_slot'] = index
        manifest.append({'position': item['position'], 'source_week': item['source_week'],
            'source_session': item['source_session'], 'occurrence_id': identity, 'prescription_digest': digest(_dose(session))})
        db.add(WorkoutOccurrence(id=identity, user_id=user.id, sequence_id=sequence.id,
            source_position=item['position'], source_week=item['source_week'], source_session=item['source_session'],
            plan_id=None, week_start=None, session_slot=item['position'], workout_id=session['session_id'],
            program_id=source['program_id'], payload=session, prescription_digest=digest(_dose(session)), execution_state='planned'))
    sequence.source_catalog = {**sequence.source_catalog, 'manifest': manifest}
    if payload.switch_plan_id:
        plan = db.query(WorkoutPlan).filter_by(id=payload.switch_plan_id, user_id=user.id).one()
        old = deepcopy(plan.payload)
        old['flexible_supersession'] = {'sequence_id': sequence.id, 'command_id': payload.command_id,
            'original_schedule': deepcopy(old.get('schedule')), 'prescription_retained': True}
        old['schedule'] = {**(old.get('schedule') or {}), 'mode': 'selected_dates_superseded_v1'}
        plan.payload = old
    user.schedule_mode = 'flexible'
    user.expected_sessions_per_week = payload.expected_sessions_per_week
    user.scheduling_timezone = payload.timezone
    user.days_available = None
    db.flush()
    return _receipt(db, user, sequence, payload.command_id, request_digest, 'enroll', next_training(db, user, sequence))


def command(db, user, sequence_id, operation, payload):
    if payload.command_id.startswith('server/'):
        raise HTTPException(422, 'Reserved lifecycle command namespace')
    lock_user(db, user.id)
    db.refresh(user)
    request_digest = digest({'sequence_id': sequence_id, 'operation': operation, 'payload': payload.model_dump(mode='json')})
    replay = _replay(db, user.id, payload.command_id, request_digest)
    if replay is not None:
        return replay
    sequence = db.query(TrainingSequence).filter_by(id=sequence_id, user_id=user.id).one_or_none()
    if sequence is None:
        raise HTTPException(404, 'Training sequence not found')
    state = next_training(db, user, sequence)
    if (not payload.confirmed or state['revision'] != payload.expected_revision or state['digest'] != payload.expected_digest
            or state['local_day'] != str(payload.expected_local_day) or state['occurrence_id'] != payload.occurrence_id):
        raise HTTPException(409, 'Training decision changed; refresh and confirm again')
    if sequence.state not in ('active', 'attention_required'):
        raise HTTPException(409, 'This sequence is no longer current')
    occurrence = db.query(WorkoutOccurrence).filter_by(id=payload.occurrence_id, user_id=user.id, sequence_id=sequence.id).one_or_none()
    if occurrence is None and operation != 'retire':
        raise HTTPException(409, 'No current source occurrence; retire this conflicted program')
    day = state['local_day']
    if operation in ('start', 'resume'):
        if state['action'] != operation or state['blockers']:
            raise HTTPException(409, 'This source occurrence is not eligible for the requested start/resume')
        occurrence.execution_state = 'active'
        occurrence.execution_context = {'id': str(uuid4()), 'local_day': day, 'timezone': sequence.timezone}
    elif operation == 'pause':
        if occurrence.execution_state != 'active':
            raise HTTPException(409, 'Only active work can be paused')
        occurrence.execution_state = 'paused'
        occurrence.execution_context = None
    elif operation in ('finish', 'end-early'):
        if state['blockers']:
            raise HTTPException(409, 'Resolve mandatory source/dependency conflicts before source advancement')
        if occurrence.execution_state not in ('active', 'paused'):
            raise HTTPException(409, 'Start the source occurrence before closing it')
        if not state['coverage']['known'] or (operation == 'finish' and not state['coverage']['complete']):
            raise HTTPException(409, 'Full Finish requires every required working set; use confirmed End Early for missing work')
        if operation == 'end-early' and state['coverage']['complete']:
            raise HTTPException(409, 'All required work is covered; use Finish')
        occurrence.execution_state = 'finished' if operation == 'finish' else 'ended_early'
        occurrence.advancement = {'operation': operation, 'coverage': deepcopy(state['coverage']),
            'missing': deepcopy(state['coverage']['missing']), 'reason': payload.reason,
            'command_id': payload.command_id, 'as_of': datetime.now(UTC).isoformat(), 'local_day': day,
            'prescription_digest': occurrence.prescription_digest, 'source_position': occurrence.source_position}
        occurrence.execution_context = None
        sequence.cursor += 1
        if sequence.cursor == len(sequence.source_catalog['manifest']):
            sequence.state = 'finished'
    elif operation == 'reconcile':
        if state['blockers']:
            raise HTTPException(409, {'message': 'Mandatory conflict remains; use the stated evidence/date resolution or retire this program', 'blockers': state['blockers']})
        sequence.state = 'active'
    elif operation == 'retire':
        if state['action'] != 'blocked':
            raise HTTPException(409, 'Retirement is available for an explicit reconciliation conflict')
        if occurrence is not None:
            if occurrence.execution_state == 'active':
                occurrence.execution_state = 'paused'
            occurrence.execution_context = None
        sequence.state = 'retired'
        # Preserve the mandatory conflict and its terminal outcome in the receipt.
    else:
        raise HTTPException(404, 'Unknown training operation')
    sequence.revision += 1
    db.flush()
    result = next_training(db, user, sequence)
    result['command_receipt'] = {'operation': operation, 'occurrence_id': occurrence.id if occurrence else None,
        'advancement': deepcopy(occurrence.advancement) if occurrence else None, 'reconciliation': deepcopy(state['blockers']) if operation in ('reconcile', 'retire') else None}
    return _receipt(db, user, sequence, payload.command_id, request_digest, operation, result)


def validate_performance(db, user, occurrence, context_id):
    if not occurrence.sequence_id:
        guard_calendar(db, user.id)
        return
    sequence = current_sequence(db, user.id)
    context = occurrence.execution_context or {}
    if (not sequence or sequence.id != occurrence.sequence_id or sequence.cursor != occurrence.source_position
            or occurrence.execution_state != 'active' or not context_id or context_id != context.get('id')
            or context.get('local_day') != str(_day(sequence)) or context.get('timezone') != sequence.timezone):
        # Called only after exact retained-command replay under the User lock.
        # This rejected context cannot be reused by a later Resume (new UUID).
        raise HTTPException(409, {'code': 'performance_context_not_current',
            'message': 'Original set was not recorded: its execution context is no longer current. Confirm Start or Resume before recording new work.'})
    state = next_training(db, user, sequence)
    if state['action'] == 'blocked':
        raise HTTPException(409, {'message': 'A mandatory training dependency needs reconciliation', 'blockers': state['blockers']})


def performance_fields(occurrence):
    if not occurrence.sequence_id:
        return {}
    context = occurrence.execution_context or {}
    return {'performed_local_date': date.fromisoformat(context['local_day']),
        'performed_timezone': context['timezone'], 'execution_context_id': context['id']}


def reconcile_amendment(db, user, history_command_id):
    """History keeps advancement; only actual mandatory conflicts gate current work."""
    sequence = current_sequence(db, user.id)
    if not sequence:
        return
    db.flush()
    state = next_training(db, user, sequence)
    if state['blockers'] and sequence.state != 'attention_required':
        sequence.state = 'attention_required'
        sequence.revision += 1
        db.add(TrainingSequenceCommand(user_id=user.id, sequence_id=sequence.id,
            command_id='server/amendment/' + digest(history_command_id), request_digest=digest(state['blockers']),
            operation='amendment_gate', response={'blockers': state['blockers'], 'cause_command_id': history_command_id,
                'resolution_options': ['reconcile', 'retire']}))
