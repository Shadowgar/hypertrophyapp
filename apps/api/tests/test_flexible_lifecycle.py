"""Flexible commands use disposable accounts and the existing logger."""
from test_selected_date_scheduling import scenario


def test_enrollment_preview_does_not_require_weekdays(scenario):
    _, headers, client = scenario
    response = client.post('/training/enroll/preview', headers=headers, json={
        'program_id': 'pure_bodybuilding_phase_1_full_body',
        'timezone': 'America/New_York', 'expected_sessions_per_week': 3,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['available']
    assert body['session_count'] == 50
    assert body['digest']
    assert client.get('/training/next', headers=headers).json()['mode'] == 'calendar'

from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4
import pytest
from app import flexible_training as training
from app.database import SessionLocal
from app.models import TrainingSequence, WorkoutOccurrence, WorkoutSetLog


def small_source(monkeypatch):
    source = deepcopy(training.native_source('pure_bodybuilding_phase_1_full_body'))
    chosen = [deepcopy(source['items'][i]) for i in (0, 5, 10)]
    for index, item in enumerate(chosen):
        item['position'] = index
        item['session']['exercises'] = [item['session']['exercises'][0]]
        item['session']['exercises'][0]['source_relationships'] = []
    source.update(items=chosen, rest_rules=[])
    monkeypatch.setattr(training, 'native_source', lambda _: deepcopy(source))
    return source


def enrollment(client, headers):
    body = {'program_id': 'pure_bodybuilding_phase_1_full_body', 'timezone': 'America/New_York', 'expected_sessions_per_week': 3}
    preview = client.post('/training/enroll/preview', headers=headers, json=body)
    assert preview.status_code == 200, preview.text
    request = {**body, 'preview_digest': preview.json()['digest'], 'confirmed': True, 'command_id': str(uuid4())}
    response = client.post('/training/enroll', headers=headers, json=request)
    assert response.status_code == 200, response.text
    return response.json(), request


def operation(client, headers, state, name, **changes):
    body = {'command_id': str(uuid4()), 'expected_revision': state['revision'],
        'occurrence_id': state['occurrence_id'], 'expected_digest': state['digest'],
        'expected_local_day': state['local_day'], 'confirmed': True, **changes}
    return client.post(f'/training/{state["sequence_id"]}/{name}', headers=headers, json=body), body


def next_state(client, headers):
    response = client.get('/training/next', headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def clock(monkeypatch, value):
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)
    monkeypatch.setattr(training, 'datetime', Frozen)


def test_enroll_start_pause_resume_and_replay_preserve_identity(scenario, monkeypatch):
    small_source(monkeypatch)
    uid, headers, client = scenario
    state, request = enrollment(client, headers)
    assert state['action'] == 'start'
    assert client.post('/training/enroll', headers=headers, json=request).json() == state
    started, command = operation(client, headers, state, 'start')
    assert started.status_code == 200, started.text
    active = started.json()
    identity = active['occurrence_id']
    assert active['action'] == 'active'
    paused, _ = operation(client, headers, active, 'pause')
    assert paused.status_code == 200, paused.text
    assert paused.json()['action'] == 'resume'
    clock(monkeypatch, datetime(2026, 12, 1, 16, tzinfo=UTC))
    resumed, _ = operation(client, headers, next_state(client, headers), 'resume')
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()['occurrence_id'] == identity
    assert resumed.json()['execution_context']['local_day'] == '2026-12-01'
    assert client.post(f'/training/{state["sequence_id"]}/start', headers=headers, json=command).json() == active
    with SessionLocal() as db:
        assert db.query(TrainingSequence).filter_by(user_id=uid).count() == 1
        assert db.query(WorkoutOccurrence).filter_by(user_id=uid).count() == 3
        assert db.query(WorkoutSetLog).filter_by(user_id=uid).count() == 0


def test_explicit_end_early_advances_without_complete_coverage(scenario, monkeypatch):
    small_source(monkeypatch)
    uid, headers, client = scenario
    state, _ = enrollment(client, headers)
    started, _ = operation(client, headers, state, 'start')
    active = started.json()
    finish, _ = operation(client, headers, active, 'finish')
    assert finish.status_code == 409
    denied, _ = operation(client, headers, active, 'end-early', confirmed=False)
    assert denied.status_code == 409
    ended, request = operation(client, headers, active, 'end-early', reason='Shift changed')
    assert ended.status_code == 200, ended.text
    assert ended.json()['source_position'] == 1
    assert ended.json()['action'] == 'start'
    assert ended.json()['command_receipt']['advancement']['coverage']['complete'] is False
    assert ended.json()['command_receipt']['advancement']['missing']
    assert client.post(f'/training/{state["sequence_id"]}/end-early', headers=headers, json=request).json() == ended.json()
    with SessionLocal() as db:
        old = db.get(WorkoutOccurrence, active['occurrence_id'])
        assert old.execution_state == 'ended_early'
        assert old.payload == state['session'] or {**old.payload, 'execution_context': None} == state['session']
        assert db.query(WorkoutSetLog).filter_by(user_id=uid).count() == 0


def test_direct_logging_requires_confirmed_current_execution_context(scenario, monkeypatch):
    small_source(monkeypatch)
    _, headers, client = scenario
    state, _ = enrollment(client, headers)
    exercise = state['session']['exercises'][0]
    body = {'command_id': str(uuid4()), 'exercise_id': exercise['id'],
        'exercise_occurrence_id': exercise['exercise_occurrence_id'], 'set_index': 1,
        'reps': 8, 'weight': 20, 'set_kind': 'work'}
    path = f'/workout/{state["occurrence_id"]}/log-set'
    assert client.post(path, headers=headers, json=body).status_code == 409
    started, _ = operation(client, headers, state, 'start')
    context = started.json()['execution_context']
    body['execution_context_id'] = context['id']
    response = client.post(path, headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert response.json()['performed_local_date'] == context['local_day']
    paused, _ = operation(client, headers, next_state(client, headers), 'pause')
    assert paused.status_code == 200
    assert client.post(path, headers=headers, json=body).json() == response.json()
    assert client.post(path, headers=headers, json={**body, 'command_id': str(uuid4()), 'set_index': 2}).status_code == 409


def test_flexible_profile_has_advisory_frequency_without_calendar_count(scenario):
    uid, headers, client = scenario
    payload = {'name': 'Synthetic Flexible', 'age': 30, 'weight': 80, 'gender': 'unspecified',
        'split_preference': 'full_body', 'selected_program_id': 'pure_bodybuilding_phase_1_full_body',
        'equipment_profile': ['barbell', 'dumbbell', 'machine', 'cable', 'bench'],
        'schedule_mode': 'flexible', 'days_available': None, 'expected_sessions_per_week': 3}
    saved = client.post('/profile', headers=headers, json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()['days_available'] is None
    assert saved.json()['expected_sessions_per_week'] == 3
    assert saved.json()['schedule_mode'] == 'flexible'
    assert not saved.json()['initial_setup_available']
    with SessionLocal() as db:
        from app.models import User, WorkoutPlan
        assert db.get(User, uid).days_available is None
        assert db.query(WorkoutPlan).filter_by(user_id=uid).count() == 0
    invalid = client.post('/profile', headers=headers, json={**payload, 'schedule_mode': 'calendar'})
    assert invalid.status_code == 422


def test_today_requires_start_and_reuses_active_native_occurrence(scenario, monkeypatch):
    small_source(monkeypatch)
    _, headers, client = scenario
    state, _ = enrollment(client, headers)
    assert client.get('/workout/today', headers=headers).status_code == 409
    started, _ = operation(client, headers, state, 'start')
    assert started.status_code == 200
    today = client.get('/workout/today', headers=headers)
    assert today.status_code == 200, today.text
    assert today.json()['workout_occurrence_id'] == state['occurrence_id']
    assert today.json()['execution_context'] == started.json()['execution_context']
    assert today.json()['exercises'][0]['authored_prescription'] == state['session']['exercises'][0]['authored_prescription']
    assert today.json()['exercises'][0]['recommended_working_weight'] is None


@pytest.mark.parametrize('path,body', [
    ('/plan/generate-week', {'template_id': 'pure_bodybuilding_phase_1_full_body', 'target_days': 3}),
    ('/profile/program-selection', {'selected_program_id': 'pure_bodybuilding_phase_2_full_body', 'program_selection_mode': 'manual'}),
])
def test_legacy_writers_cannot_create_competing_cursor(scenario, monkeypatch, path, body):
    small_source(monkeypatch)
    uid, headers, client = scenario
    state, _ = enrollment(client, headers)
    response = client.post(path, headers=headers, json=body)
    assert response.status_code == 409, response.text
    assert next_state(client, headers)['sequence_id'] == state['sequence_id']
    with SessionLocal() as db:
        from app.models import User, WorkoutPlan
        assert db.get(User, uid).selected_program_id == 'pure_bodybuilding_phase_1_full_body'
        assert db.query(WorkoutPlan).filter_by(user_id=uid).count() == 0


def test_enrollment_requires_saved_setup_and_invalidates_changed_constraints(scenario, monkeypatch):
    small_source(monkeypatch)
    uid, headers, client = scenario
    body = {'program_id': 'pure_bodybuilding_phase_1_full_body', 'timezone': 'America/New_York'}
    with SessionLocal() as db:
        from app.models import User
        user = db.get(User, uid)
        user.split_preference = None
        user.equipment_profile = None
        db.commit()
    preview = client.post('/training/enroll/preview', headers=headers, json=body).json()
    assert not preview['available']
    assert any(b['code'] == 'profile_incomplete' for b in preview['blockers'])
    with SessionLocal() as db:
        user = db.get(User, uid)
        user.split_preference = 'full_body'
        user.equipment_profile = []  # An explicit empty inventory is not a missing answer.
        db.commit()
    preview = client.post('/training/enroll/preview', headers=headers, json=body).json()
    assert preview['available']
    with SessionLocal() as db:
        user = db.get(User, uid)
        user.movement_restrictions = ['pain_report']
        db.commit()
    result = client.post('/training/enroll', headers=headers, json={**body,
        'preview_digest': preview['digest'], 'confirmed': True, 'command_id': str(uuid4())})
    assert result.status_code == 409
    with SessionLocal() as db:
        assert db.query(TrainingSequence).filter_by(user_id=uid).count() == 0


@pytest.mark.parametrize('frequency', [None, 1, 7])
def test_frequency_is_optional_advisory_and_never_regroups_native_source(scenario, frequency):
    _, headers, client = scenario
    preview = client.post('/training/enroll/preview', headers=headers, json={
        'program_id': 'pure_bodybuilding_phase_1_full_body', 'timezone': 'America/New_York',
        'expected_sessions_per_week': frequency})
    assert preview.status_code == 200, preview.text
    body = preview.json()
    source = training.native_source(body['program_id'])
    assert body['session_count'] == 50
    assert body['first_session'] == source['items'][0]['session']
    assert body['total_working_sets'] == sum(e['sets'] for i in source['items'] for e in i['session']['exercises'])


def test_calendar_review_cannot_invent_flexible_dose_or_adaptation(scenario, monkeypatch):
    small_source(monkeypatch)
    uid, headers, client = scenario
    enrollment(client, headers)
    response = client.get('/weekly-review/status', headers=headers)
    assert response.status_code == 409, response.text
    response = client.post('/weekly-review', headers=headers, json={
        'body_weight': 80, 'calories': 2000, 'protein': 120, 'fat': 50, 'carbs': 200,
        'adherence_score': 3, 'sessions_next_week': 3})
    assert response.status_code == 409, response.text
    with SessionLocal() as db:
        from app.models import User, WeeklyReviewCycle
        assert db.get(User, uid).days_available is None
        assert db.query(WeeklyReviewCycle).filter_by(user_id=uid).count() == 0


def test_next_day_unreceived_command_has_definitive_rejection_but_committed_command_replays(scenario, monkeypatch):
    small_source(monkeypatch)
    clock(monkeypatch, datetime(2026, 10, 30, 16, tzinfo=UTC))
    _, headers, client = scenario
    state, _ = enrollment(client, headers)
    started, _ = operation(client, headers, state, 'start')
    exercise = state['session']['exercises'][0]
    body = {'command_id': str(uuid4()), 'exercise_id': exercise['id'],
        'exercise_occurrence_id': exercise['exercise_occurrence_id'], 'set_index': 1,
        'reps': 8, 'weight': 20, 'set_kind': 'work', 'execution_context_id': started.json()['execution_context']['id']}
    path = f'/workout/{state["occurrence_id"]}/log-set'
    accepted = client.post(path, headers=headers, json=body)
    assert accepted.status_code == 200, accepted.text
    clock(monkeypatch, datetime(2026, 11, 2, 16, tzinfo=UTC))
    assert next_state(client, headers)['action'] == 'resume'
    assert client.post(path, headers=headers, json=body).json() == accepted.json()
    rejected = client.post(path, headers=headers, json={**body, 'command_id': str(uuid4()), 'set_index': 2})
    assert rejected.status_code == 409
    assert rejected.json()['detail']['code'] == 'performance_context_not_current'


def test_legacy_read_repair_rechecks_mode_after_waiting_for_account_lock(scenario, monkeypatch):
    uid, _, _ = scenario
    from app.routers import plan
    from app.models import User, WorkoutPlan
    from sqlalchemy import update
    from datetime import date
    with SessionLocal() as db:
        user = db.get(User, uid)
        original = {'program_template_id': user.selected_program_id, 'sessions': []}
        row = WorkoutPlan(user_id=uid, week_start=date(2026, 10, 26), split='full_body', phase='accumulation', payload=deepcopy(original))
        db.add(row)
        db.commit()
        db.refresh(user)
        locks=[]
        def grant_after_mode_change(session, user_id):
            locks.append(user_id)
            # Models a stale authenticated User while the preceding lock holder
            # saves Flexible mode. The identity map must be refreshed after lock.
            session.execute(update(User).where(User.id == user_id).values(schedule_mode='flexible'),
                execution_options={'synchronize_session': False})
        monkeypatch.setattr(plan, 'lock_history_user', grant_after_mode_change)
        def forbidden_builder(**kwargs):
            pytest.fail('Legacy GET reached regeneration using stale calendar ownership')
        monkeypatch.setattr(plan, '_build_week_plan_runtime_for_user', forbidden_builder)
        assert plan._ensure_latest_authored_plan_current_if_needed(db=db, current_user=user) is None
        assert locks == [uid]
        assert db.get(WorkoutPlan, row.id).payload == original
