"""Next-week qualification on explicit disposable SQLite; PG covers serialization separately."""
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4
import pytest
from app.database import SessionLocal
from app.models import User, WorkoutPlan, WorkoutOccurrence
from test_selected_date_scheduling import scenario, request_dates, fixed_clock

MONDAY = date(2026, 10, 5)

@pytest.fixture
def week(scenario, monkeypatch):
    fixed_clock(monkeypatch, datetime(2026,10,7,16,tzinfo=UTC))
    return scenario

def activate(client, headers, request):
    preview = client.post('/plan/selected-dates/preview', headers=headers, json=request)
    assert preview.status_code == 200, preview.text
    return client.post('/plan/generate-week', headers=headers,
        json={**request, 'expected_preview_digest': preview.json()['schedule']['preview_digest']})

@pytest.mark.parametrize('phase', ['pure_bodybuilding_phase_1_full_body', 'pure_bodybuilding_phase_2_full_body'])
def test_preview_activate_and_revisit_correct_successor_without_consuming_twice(week, phase):
    user_id, headers, client = week
    current = activate(client, headers, request_dates(MONDAY, phase=phase))
    assert current.status_code == 200, current.text
    future_request = request_dates(MONDAY+timedelta(days=7), (0,3,5), phase=phase)
    with SessionLocal() as db:
        before = deepcopy(db.query(WorkoutPlan).filter_by(user_id=user_id).one().payload)
    preview = client.post('/plan/selected-dates/preview', headers=headers, json=future_request)
    assert preview.status_code == 200, preview.text
    assert preview.json()['schedule']['spacing']['previous_date'] == '2026-10-11'
    assert preview.json()['schedule']['spacing']['gap_days'][0] == 1
    assert preview.json()['mesocycle']['authored_week_index'] == 2
    assert {e['source_lineage']['source_week'] for s in preview.json()['sessions'] for e in s['exercises']} == {2}
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 1
        assert db.query(WorkoutOccurrence).filter_by(user_id=user_id).count() == 0
    future = activate(client, headers, future_request)
    assert future.status_code == 200, future.text
    assert {s['workout_occurrence_id'] for s in future.json()['sessions']}.isdisjoint(s['workout_occurrence_id'] for s in current.json()['sessions'])
    for monday, dates in [(MONDAY, current.json()['schedule']['selected_dates']), (MONDAY+timedelta(days=7), future_request['selected_dates'])]:
        context = client.get(f'/plan/scheduling-context?timezone=America/New_York&week_start={monday}', headers=headers)
        assert context.status_code == 200, context.text
        assert context.json()['selected_dates'] == dates
        assert context.json()['week_start'] == monday.isoformat()
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=user_id, week_start=MONDAY).one().payload == before
    revised = activate(client, headers, request_dates(MONDAY+timedelta(days=7), (1,4,6), revision=1, phase=phase))
    assert revised.status_code == 200, revised.text
    assert revised.json()['mesocycle']['authored_week_index'] == 2
    assert [s['exercises'] for s in revised.json()['sessions']] == [s['exercises'] for s in future.json()['sessions']]
    today = client.get('/workout/today', headers=headers)
    assert today.status_code == 404 and today.json()['detail'] == 'No workout scheduled today'


def test_next_week_without_predecessor_conflicts_and_does_not_persist(week):
    user_id, headers, client = week
    result = client.post('/plan/selected-dates/preview', headers=headers, json=request_dates(MONDAY+timedelta(days=7)))
    assert result.status_code == 409, result.text
    assert 'reconcil' in result.json()['detail'].lower()
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 0


def test_predecessor_revision_invalidates_future_preview_but_not_activated_plan(week):
    user_id, headers, client = week
    assert activate(client, headers, request_dates(MONDAY)).status_code == 200
    request = request_dates(MONDAY+timedelta(days=7), (0,3,5))
    preview = client.post('/plan/selected-dates/preview', headers=headers, json=request)
    assert preview.status_code == 200, preview.text
    assert activate(client, headers, request_dates(MONDAY, (0,3,5), revision=1)).status_code == 200
    stale = client.post('/plan/generate-week', headers=headers, json={**request, 'expected_preview_digest':preview.json()['schedule']['preview_digest']})
    assert stale.status_code == 409, stale.text
    future = activate(client, headers, request)
    assert future.status_code == 200, future.text
    frozen = deepcopy(future.json())
    assert activate(client, headers, request_dates(MONDAY, revision=2)).status_code == 200
    context = client.get(f'/plan/scheduling-context?timezone=America/New_York&week_start={request["week_start"]}', headers=headers)
    assert context.json()['plan'] == frozen

@pytest.mark.parametrize('count', [2,4,5])
def test_next_week_uses_source_successor_for_every_date_count(week, count):
    _, headers, client = week
    assert activate(client, headers, request_dates(MONDAY)).status_code == 200
    request = request_dates(MONDAY+timedelta(days=7), tuple(range(count)))
    result = activate(client, headers, request)
    assert result.status_code == 200, result.text
    assert result.json()['mesocycle']['authored_week_index'] == 2
    assert {e['source_lineage']['source_week'] for s in result.json()['sessions'] for e in s['exercises']} == {2}

@pytest.mark.parametrize('problem', ['missing_ordinal','exhausted','duplicate','program'])
def test_ambiguous_or_conflicting_progression_requires_reconciliation(week, problem):
    user_id, headers, client = week
    assert activate(client, headers, request_dates(MONDAY)).status_code == 200
    with SessionLocal() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=user_id).one()
        payload = deepcopy(row.payload)
        if problem == 'missing_ordinal':
            payload['mesocycle'].pop('authored_week_index')
        elif problem == 'exhausted':
            payload['mesocycle']['authored_week_index'] = 100
        elif problem == 'program':
            payload['program_template_id'] = 'pure_bodybuilding_phase_2_full_body'
        else:
            db.add(WorkoutPlan(user_id=user_id, week_start=MONDAY, split=row.split, phase=row.phase, payload=payload))
        row.payload = payload
        db.commit()
        before = {r.id:deepcopy(r.payload) for r in db.query(WorkoutPlan).filter_by(user_id=user_id)}
    result = client.post('/plan/selected-dates/preview', headers=headers, json=request_dates(MONDAY+timedelta(days=7)))
    assert result.status_code == 409, result.text
    with SessionLocal() as db:
        assert {r.id:r.payload for r in db.query(WorkoutPlan).filter_by(user_id=user_id)} == before


def test_future_snapshot_is_immutable_and_current_logging_keeps_future_plan(week):
    from app.models import WorkoutSetLog
    user_id, headers, client = week
    current = activate(client, headers, request_dates(MONDAY)).json()
    future = activate(client, headers, request_dates(MONDAY+timedelta(days=7))).json()
    for saved in (current, future):
        session = saved['sessions'][0]
        exercise = session['exercises'][0]
        logged = client.post(f"/workout/{session['workout_occurrence_id']}/log-set", headers=headers, json={
            'command_id': uuid4().hex, 'exercise_id':exercise['id'],
            'exercise_occurrence_id':exercise['exercise_occurrence_id'], 'set_index':1,'reps':8,'weight':25})
        assert logged.status_code == 200, logged.text
    with SessionLocal() as db:
        snapshots = {r.id:deepcopy(r.payload) for r in db.query(WorkoutOccurrence).filter_by(user_id=user_id)}
        logs = [(r.id,r.workout_occurrence_id,r.created_at,r.weight) for r in db.query(WorkoutSetLog).filter_by(user_id=user_id)]
    blocked = client.post('/plan/generate-week', headers=headers, json={
        **request_dates(MONDAY+timedelta(days=7), (0,3,5), revision=1),
        'expected_preview_digest':future['schedule']['preview_digest']})
    assert blocked.status_code == 409
    assert 'snapshot' in blocked.json()['detail']
    with SessionLocal() as db:
        assert {r.id:r.payload for r in db.query(WorkoutOccurrence).filter_by(user_id=user_id)} == snapshots
        assert [(r.id,r.workout_occurrence_id,r.created_at,r.weight) for r in db.query(WorkoutSetLog).filter_by(user_id=user_id)] == logs
        assert db.query(WorkoutPlan).filter_by(user_id=user_id,week_start=MONDAY+timedelta(days=7)).one().payload['schedule'] == future['schedule']


def test_future_activation_cannot_hide_current_legacy_work(week):
    user_id, headers, client = week
    assert activate(client, headers, request_dates(MONDAY)).status_code == 200
    with SessionLocal() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=user_id).one()
        payload=deepcopy(row.payload)
        payload.pop('schedule')
        row.payload, row.schedule_timezone, row.placement_revision = payload, None, None
        db.get(User,user_id).scheduling_timezone=None
        db.commit()
    result=client.post('/plan/selected-dates/preview',headers=headers,json=request_dates(MONDAY+timedelta(days=7)))
    assert result.status_code==409, result.text
    assert 'reconcil' in result.json()['detail'].lower()
    with SessionLocal() as db:
        assert db.get(User,user_id).scheduling_timezone is None
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count()==1


def test_saved_ordinal_disagreeing_with_source_lineage_requires_reconciliation(week):
    user_id, headers, client = week
    assert activate(client, headers, request_dates(MONDAY)).status_code == 200
    with SessionLocal() as db:
        row=db.query(WorkoutPlan).filter_by(user_id=user_id).one()
        payload=deepcopy(row.payload)
        payload['mesocycle']['authored_week_index']=4
        row.payload=payload
        db.commit()
    result=client.post('/plan/selected-dates/preview',headers=headers,json=request_dates(MONDAY+timedelta(days=7)))
    assert result.status_code==409,result.text


def test_current_history_dependency_is_recorded_and_stale_future_activation_rejected(week):
    user_id, headers, client=week
    current=activate(client,headers,request_dates(MONDAY)).json()
    request=request_dates(MONDAY+timedelta(days=7))
    preview=client.post('/plan/selected-dates/preview',headers=headers,json=request)
    assert preview.status_code==200,preview.text
    dependencies=preview.json()['schedule']['activation_dependencies']
    assert len(dependencies['generation_input_digest'])==64
    session=current['sessions'][0]
    exercise=session['exercises'][0]
    logged=client.post(f"/workout/{session['workout_occurrence_id']}/log-set",headers=headers,json={
        'command_id':uuid4().hex,'exercise_id':exercise['id'],'exercise_occurrence_id':exercise['exercise_occurrence_id'],
        'set_index':1,'reps':8,'weight':20})
    assert logged.status_code==200,logged.text
    stale=client.post('/plan/generate-week',headers=headers,json={**request,'expected_preview_digest':preview.json()['schedule']['preview_digest']})
    assert stale.status_code==409,stale.text
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count()==1


def test_activated_future_becomes_current_on_local_monday_without_regeneration(week, monkeypatch):
    user_id, headers, client = week
    fixed_clock(monkeypatch, datetime(2026,10,11,16,tzinfo=UTC))
    assert activate(client, headers, request_dates(MONDAY)).status_code == 200
    next_monday = MONDAY + timedelta(days=7)
    future = activate(client, headers, request_dates(next_monday, (0,3,5)))
    assert future.status_code == 200, future.text
    saved = future.json()
    fixed_clock(monkeypatch, datetime(2026,10,12,4,1,tzinfo=UTC))
    context = client.get('/plan/scheduling-context?timezone=America/New_York', headers=headers)
    assert context.status_code == 200, context.text
    assert context.json()['plan'] == saved
    assert context.json()['week_start'] == next_monday.isoformat()
    today = client.get('/workout/today', headers=headers)
    assert today.status_code == 200, today.text
    assert today.json()['workout_occurrence_id'] == saved['sessions'][0]['workout_occurrence_id']
    assert today.json()['scheduled_date'] == next_monday.isoformat()
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 2


def test_preview_digest_for_current_week_cannot_activate_next_week(week):
    user_id, headers, client = week
    current = activate(client, headers, request_dates(MONDAY))
    assert current.status_code == 200, current.text
    result = client.post('/plan/generate-week', headers=headers, json={
        **request_dates(MONDAY+timedelta(days=7)),
        'expected_preview_digest': current.json()['schedule']['preview_digest']})
    assert result.status_code == 409, result.text
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 1


def test_unbound_auto_future_retains_the_saved_predecessor_program(week):
    user_id, headers, client = week
    assert activate(client, headers, request_dates(MONDAY)).status_code == 200
    with SessionLocal() as db:
        user = db.get(User, user_id)
        user.selected_program_id = None
        user.program_selection_mode = 'auto'
        db.commit()
    request = request_dates(MONDAY + timedelta(days=7))
    request['template_id'] = None
    future = activate(client, headers, request)
    assert future.status_code == 200, future.text
    assert future.json()['program_template_id'] == 'pure_bodybuilding_phase_1_full_body'
    assert future.json()['mesocycle']['authored_week_index'] == 2
    with SessionLocal() as db:
        assert db.get(User, user_id).selected_program_id is None
        assert db.get(User, user_id).program_selection_mode == 'auto'


def test_changed_profile_input_invalidates_the_recorded_generation_dependency(week):
    user_id, headers, client = week
    assert activate(client, headers, request_dates(MONDAY)).status_code == 200
    request = request_dates(MONDAY + timedelta(days=7))
    preview = client.post('/plan/selected-dates/preview', headers=headers, json=request)
    assert preview.status_code == 200, preview.text
    with SessionLocal() as db:
        db.get(User, user_id).session_time_budget_minutes = 45
        db.commit()
    fresh = client.post('/plan/selected-dates/preview', headers=headers, json=request)
    assert fresh.status_code == 200, fresh.text
    assert fresh.json()['schedule']['activation_dependencies']['generation_input_digest'] != (
        preview.json()['schedule']['activation_dependencies']['generation_input_digest'])
    stale = client.post('/plan/generate-week', headers=headers, json={
        **request, 'expected_preview_digest': preview.json()['schedule']['preview_digest']})
    assert stale.status_code == 409, stale.text


def test_next_week_activation_requires_a_preview_digest(week):
    user_id, headers, client = week
    assert activate(client, headers, request_dates(MONDAY)).status_code == 200
    request = request_dates(MONDAY + timedelta(days=7))
    direct = client.post('/plan/generate-week', headers=headers, json=request)
    assert direct.status_code == 409, direct.text
    assert 'preview' in direct.json()['detail'].lower()
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 1
    assert activate(client, headers, request).status_code == 200


def test_rollover_derives_current_day_count_without_mutating_preferences_or_plans(week, monkeypatch):
    from app import selected_date_plans
    from app.routers import plan, profile
    user_id, headers, client = week
    assert activate(client, headers, request_dates(MONDAY)).status_code == 200
    future = activate(client, headers, request_dates(MONDAY + timedelta(days=7), (0,3)))
    assert future.status_code == 200, future.text
    monkeypatch.setattr(profile, 'datetime', selected_date_plans.datetime)
    assert client.get('/profile', headers=headers).json()['days_available'] == 3
    with SessionLocal() as db:
        saved_plans = {p.id: deepcopy(p.payload) for p in db.query(WorkoutPlan).filter_by(user_id=user_id)}
    # At 00:01 Monday UTC it is still Sunday in New York.
    fixed_clock(monkeypatch, datetime(2026,10,12,0,1,tzinfo=UTC))
    monkeypatch.setattr(profile, 'datetime', selected_date_plans.datetime)
    assert client.get('/profile', headers=headers).json()['days_available'] == 3
    fixed_clock(monkeypatch, datetime(2026,10,12,4,1,tzinfo=UTC))
    monkeypatch.setattr(profile, 'datetime', selected_date_plans.datetime)
    response = client.get('/profile', headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()['effective_days_available'] == 2
    assert response.json()['days_available'] == 3
    # Settings round-trips writable preferences when changing unrelated setup.
    updated = client.post('/profile', headers=headers, json={**response.json(), 'training_location':'home',
        'effective_days_available':5,'effective_program_id':'unqualified','scheduling_timezone':'Pacific/Honolulu'})
    assert updated.status_code == 200, updated.text
    assert updated.json()['days_available'] == 3
    assert updated.json()['effective_days_available'] == 2
    assert updated.json()['effective_program_id'] == 'pure_bodybuilding_phase_1_full_body'
    assert updated.json()['scheduling_timezone'] == 'America/New_York'
    observed = []
    owner = plan.prepare_frequency_adaptation_decision_runtime
    def capture(**kwargs):
        observed.append(kwargs['current_days_available'])
        return owner(**kwargs)
    monkeypatch.setattr(plan, 'prepare_frequency_adaptation_decision_runtime', capture)
    preview = client.post('/plan/adaptation/preview', headers=headers, json={'target_days':3})
    assert preview.status_code == 200, preview.text
    assert observed == [2]
    coach_days = []
    coach_owner = plan.prepare_coach_preview_runtime_inputs
    def capture_coach(**kwargs):
        coach_days.append(kwargs['profile_days_available'])
        return coach_owner(**kwargs)
    monkeypatch.setattr(plan, 'prepare_coach_preview_runtime_inputs', capture_coach)
    coach = client.post('/plan/intelligence/coach-preview', headers=headers, json={'from_days':2,'to_days':2})
    assert coach.status_code == 200, coach.text
    assert coach_days == [2]
    with SessionLocal() as db:
        assert db.get(User, user_id).days_available == 3
        assert {p.id:p.payload for p in db.query(WorkoutPlan).filter_by(user_id=user_id)} == saved_plans


def test_auto_phase_two_rollover_uses_active_binding_without_overwriting_preference(week, monkeypatch):
    from app import selected_date_plans
    from app.routers import profile
    user_id, headers, client = week
    phase = 'pure_bodybuilding_phase_2_full_body'
    assert activate(client, headers, request_dates(MONDAY, phase=phase)).status_code == 200
    with SessionLocal() as db:
        user = db.get(User, user_id)
        user.selected_program_id, user.program_selection_mode = None, 'auto'
        db.commit()
    request = request_dates(MONDAY + timedelta(days=7), phase=phase)
    request.pop('template_id')
    assert activate(client, headers, request).status_code == 200
    fixed_clock(monkeypatch, datetime(2026,10,12,4,1,tzinfo=UTC))
    monkeypatch.setattr(profile, 'datetime', selected_date_plans.datetime)
    response = client.get('/profile', headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()['selected_program_id'] is None
    assert response.json()['effective_program_id'] == phase
    saved = client.post('/profile', headers=headers, json={**response.json(), 'training_location':'home'})
    assert saved.status_code == 200, saved.text
    assert saved.json()['selected_program_id'] is None
    assert saved.json()['effective_program_id'] == phase
    recommendation = client.get('/profile/program-recommendation', headers=headers)
    assert recommendation.status_code == 200, recommendation.text
    assert recommendation.json()['current_program_id'] == phase
    switch = client.post('/profile/program-switch', headers=headers, json={'target_program_id':phase})
    assert switch.status_code == 200, switch.text
    assert switch.json()['current_program_id'] == phase
    assert switch.json()['applied'] is False
    with SessionLocal() as db:
        assert db.get(User,user_id).selected_program_id is None
        assert db.get(User,user_id).program_selection_mode == 'auto'
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 2


def test_current_intelligence_excludes_future_plan_until_local_rollover(week, monkeypatch):
    from app import selected_date_plans
    from app.routers import plan, profile
    user_id, headers, client = week
    phase = 'pure_bodybuilding_phase_2_full_body'
    assert activate(client, headers, request_dates(MONDAY, phase=phase)).status_code == 200
    assert activate(client, headers, request_dates(MONDAY+timedelta(days=7), (0,3), phase=phase)).status_code == 200
    with SessionLocal() as db:
        saved = {p.id:deepcopy(p.payload) for p in db.query(WorkoutPlan).filter_by(user_id=user_id)}
    fixed_clock(monkeypatch, datetime(2026,10,12,0,1,tzinfo=UTC))
    monkeypatch.setattr(profile, 'datetime', selected_date_plans.datetime)
    state = client.get('/profile/training-state', headers=headers)
    assert state.status_code == 200, state.text
    assert state.json()['user_program_state']['last_generated_week_start'] == MONDAY.isoformat()
    assert state.json()['generation_state']['latest_mesocycle']['authored_week_index'] == 1
    assert state.json()['generation_state']['prior_generated_weeks_by_program'][phase] == 1
    observed = []
    def capture(owner):
        def wrapper(**kwargs):
            observed.append(kwargs['latest_plan'].week_start)
            return owner(**kwargs)
        return wrapper
    monkeypatch.setattr(profile,'prepare_profile_program_recommendation_route_runtime',capture(profile.prepare_profile_program_recommendation_route_runtime))
    monkeypatch.setattr(plan,'prepare_frequency_adaptation_decision_runtime',capture(plan.prepare_frequency_adaptation_decision_runtime))
    monkeypatch.setattr(plan,'prepare_coach_preview_decision_context',capture(plan.prepare_coach_preview_decision_context))
    requests = [
        client.get('/profile/program-recommendation',headers=headers),
        client.post('/profile/program-switch',headers=headers,json={'target_program_id':phase}),
        client.post('/plan/adaptation/preview',headers=headers,json={'target_days':2}),
        client.post('/plan/intelligence/coach-preview',headers=headers,json={'from_days':3,'to_days':2}),
    ]
    assert all(r.status_code==200 for r in requests), [r.status_code for r in requests]
    assert observed == [MONDAY]*4
    fixed_clock(monkeypatch, datetime(2026,10,12,4,1,tzinfo=UTC))
    monkeypatch.setattr(profile, 'datetime', selected_date_plans.datetime)
    state = client.get('/profile/training-state',headers=headers)
    assert state.status_code == 200, state.text
    assert state.json()['user_program_state']['last_generated_week_start'] == (MONDAY+timedelta(days=7)).isoformat()
    assert state.json()['generation_state']['latest_mesocycle']['authored_week_index'] == 2
    assert state.json()['generation_state']['prior_generated_weeks_by_program'][phase] == 2
    with SessionLocal() as db:
        assert {p.id:p.payload for p in db.query(WorkoutPlan).filter_by(user_id=user_id)} == saved


def test_legacy_next_week_cannot_bypass_dated_reservations_or_change_preferences(week):
    user_id, headers, client = week
    assert activate(client, headers, request_dates(MONDAY)).status_code == 200
    assert activate(client, headers, request_dates(MONDAY+timedelta(days=7))).status_code == 200
    with SessionLocal() as db:
        saved = {p.id:deepcopy(p.payload) for p in db.query(WorkoutPlan).filter_by(user_id=user_id)}
        user = db.get(User,user_id)
        preferences = (user.selected_program_id,user.days_available,user.scheduling_timezone)
    response = client.post('/plan/next-week',headers=headers,json={'target_days':2})
    assert response.status_code == 409, response.text
    assert 'Week' in response.json()['detail']
    with SessionLocal() as db:
        user = db.get(User,user_id)
        assert (user.selected_program_id,user.days_available,user.scheduling_timezone) == preferences
        assert {p.id:p.payload for p in db.query(WorkoutPlan).filter_by(user_id=user_id)} == saved


@pytest.mark.parametrize('problem',['valid','missing','repeated','lineage'])
def test_legacy_future_conversion_requires_the_real_source_successor(week, problem):
    user_id, headers, client = week
    assert activate(client,headers,request_dates(MONDAY)).status_code == 200
    request = request_dates(MONDAY+timedelta(days=7))
    original = activate(client,headers,request)
    assert original.status_code == 200
    with SessionLocal() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=user_id,week_start=MONDAY+timedelta(days=7)).one()
        payload = deepcopy(row.payload)
        payload.pop('schedule')
        if problem == 'missing': payload['mesocycle'].pop('authored_week_index')
        if problem == 'repeated': payload['mesocycle']['authored_week_index'] = 1
        if problem == 'lineage': payload['sessions'][0]['exercises'][0]['source_lineage']['source_sha256'] = 'unqualified'
        row.payload, row.schedule_timezone, row.placement_revision = payload, None, None
        db.commit()
        saved = {p.id:deepcopy(p.payload) for p in db.query(WorkoutPlan).filter_by(user_id=user_id)}
    preview = client.post('/plan/selected-dates/preview',headers=headers,json=request)
    if problem == 'valid':
        assert preview.status_code == 200
        placed = client.post('/plan/generate-week',headers=headers,json={**request,'expected_preview_digest':preview.json()['schedule']['preview_digest']})
        assert placed.status_code == 200
        assert placed.json()['schedule']['source_progression']['authored_week_index'] == 2
        assert [s['exercises'] for s in placed.json()['sessions']] == [s['exercises'] for s in original.json()['sessions']]
    else:
        assert preview.status_code == 409, preview.status_code
        assert 'reconcil' in preview.json()['detail'].lower()
        with SessionLocal() as db:
            assert {p.id:p.payload for p in db.query(WorkoutPlan).filter_by(user_id=user_id)} == saved


def test_later_legacy_reservation_invalidates_new_current_preview_without_consuming_twice(week):
    user_id, headers, client = week
    request = request_dates(MONDAY)
    preview = client.post('/plan/selected-dates/preview',headers=headers,json=request)
    assert preview.status_code == 200
    legacy = client.post('/plan/next-week',headers=headers,json={})
    assert legacy.status_code == 200
    # The legacy route uses its own server-date clock; any later reservation
    # must invalidate this explicitly dated current-week preview.
    assert date.fromisoformat(legacy.json()['week_start']) > MONDAY
    assert legacy.json()['mesocycle']['authored_week_index'] == 1
    response = client.post('/plan/generate-week',headers=headers,json={**request,'expected_preview_digest':preview.json()['schedule']['preview_digest']})
    assert response.status_code == 409, response.status_code
    assert 'reconcil' in response.json()['detail'].lower()
    with SessionLocal() as db:
        assert db.get(User,user_id).scheduling_timezone is None
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 1
