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
    blocked = client.post('/plan/generate-week', headers=headers, json=request_dates(MONDAY+timedelta(days=7), (0,3,5), revision=1))
    assert blocked.status_code == 409
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
