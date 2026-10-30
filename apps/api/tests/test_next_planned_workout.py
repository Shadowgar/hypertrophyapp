"""Read-only previews and commands using existing Authored week-freeze rules."""
from copy import deepcopy
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.models import User, WorkoutOccurrence, WorkoutPlan
from app import selected_date_plans
from app.routers import plan, workout
from test_selected_date_scheduling import scenario  # explicit disposable SQLite fixture

MONDAY = date(2026, 10, 26)


@pytest.fixture
def planned(scenario, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = datetime(2026, 10, 26, 16, tzinfo=UTC)
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)
    for module in (selected_date_plans, plan, workout):
        monkeypatch.setattr(module, 'datetime', Clock)
    uid, headers, client = scenario
    with SessionLocal() as db:
        user = db.get(User, uid)
        user.scheduling_timezone = 'America/New_York'
        row = WorkoutPlan(user_id=uid, week_start=MONDAY, split='full_body', phase='maintenance',
            placement_revision=1, schedule_timezone=user.scheduling_timezone,
            payload={'program_template_id': 'pure_bodybuilding_phase_1_full_body',
                'mesocycle': {'authored_week_index': 1},
                'schedule': {'mode': 'selected_dates_v1', 'week_start': str(MONDAY), 'timezone': user.scheduling_timezone,
                    'selected_dates': ['2026-10-27', '2026-10-29', '2026-10-31'], 'placement_revision': 1},
                'sessions': [{'session_id': f'day-{i}', 'title': f'Source session {i}', 'date': day, 'scheduled_date': day,
                    'placement_revision': 1, 'exercises': [{'id': f'slot-{i}', 'name': f'Source lift {i}', 'sets': i+2,
                        'source_lineage': {'source_slot_id': f'source-{i}'}, 'rep_range': [8, 10]}]}
                    for i, day in enumerate(['2026-10-27', '2026-10-29', '2026-10-31'])]})
        db.add(row); db.commit(); pid = row.id
    return uid, headers, client, pid


def preview(client, headers):
    response = client.get('/workout/next-planned', headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def move_body(value):
    return {'plan_id': value['plan_id'], 'workout_occurrence_id': value['workout_occurrence_id'],
        'expected_original_date': value['original_date'], 'expected_local_today': value['local_today'],
        'expected_placement_revision': value['placement_revision'],
        'expected_preview_digest': value['preview_digest'], 'confirmed': True}


def stored(pid):
    with SessionLocal() as db:
        return deepcopy(db.get(WorkoutPlan, pid).payload)


def test_next_preview_on_rest_day_is_read_only_and_complete(planned):
    uid, headers, client, pid = planned
    before = stored(pid)
    assert client.get('/workout/today', headers=headers).status_code == 404
    value = preview(client, headers)
    assert value['original_date'] == '2026-10-27'
    assert value['local_today'] == '2026-10-26'
    assert value['session']['title'] == 'Source session 0'
    assert value['session']['exercises'][0]['sets'] == 2
    assert value['can_move'] and value['preview_digest']
    assert stored(pid) == before
    with SessionLocal() as db:
        assert db.query(WorkoutOccurrence).filter_by(user_id=uid).count() == 0


def test_confirmed_move_preserves_occurrences_prescription_and_history(planned):
    uid, headers, client, pid = planned
    value = preview(client, headers); before = stored(pid)
    moved = client.post('/workout/next-planned/move', headers=headers, json=move_body(value))
    assert moved.status_code == 200, moved.text
    body = moved.json()
    assert body['schedule']['selected_dates'] == ['2026-10-26','2026-10-29','2026-10-31']
    assert body['schedule']['placement_revision'] == 2
    assert body['schedule']['placement_history'][0]['selected_dates'] == before['schedule']['selected_dates']
    assert body['sessions'][0]['workout_occurrence_id'] == value['workout_occurrence_id']
    assert [s['exercises'] for s in stored(pid)['sessions']] == [s['exercises'] for s in before['sessions']]
    assert body['program_template_id'] == before['program_template_id']
    assert client.get('/workout/today', headers=headers).json()['workout_occurrence_id'] == value['workout_occurrence_id']
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=uid).count() == 1
        assert db.query(WorkoutOccurrence).filter_by(user_id=uid).count() == 0
    assert client.post('/workout/next-planned/move', headers=headers, json=move_body(value)).status_code == 409


@pytest.mark.parametrize('change', [
    {'confirmed': False}, {'expected_placement_revision': 9}, {'expected_original_date': '2026-10-28'},
    {'expected_local_today': '2026-10-27'}, {'expected_preview_digest': 'f'*64},
    {'workout_occurrence_id': str(uuid4())}, {'plan_id': str(uuid4())},
])
def test_missing_consent_or_stale_review_never_mutates(planned, change):
    _, headers, client, pid = planned; value = preview(client, headers); before = stored(pid)
    request = {**move_body(value), **change}
    response = client.post('/workout/next-planned/move', headers=headers, json=request)
    assert response.status_code in (409, 422), response.text
    assert stored(pid) == before


def test_snapshot_freezes_week_and_blocks_inflight_move(planned):
    uid, headers, client, pid = planned; value = preview(client, headers); before = stored(pid)
    with SessionLocal() as db:
        session = value['session']
        db.add(WorkoutOccurrence(id=value['workout_occurrence_id'],user_id=uid,plan_id=pid,week_start=MONDAY,
            session_slot=0,workout_id=session['session_id'],payload=session,scheduled_date=date(2026,10,27)))
        db.commit()
    assert client.post('/workout/next-planned/move', headers=headers, json=move_body(value)).status_code == 409
    remaining = preview(client, headers)
    assert not remaining['can_move']
    assert 'snapshot' in remaining['blocked_reason']
    assert stored(pid) == before


def test_previous_week_is_preview_only(planned):
    _, headers, client, pid = planned
    with SessionLocal() as db:
        row = db.get(WorkoutPlan,pid); row.week_start=date(2026,10,19)
        p=deepcopy(row.payload);p['sessions'][0]['scheduled_date']=p['sessions'][0]['date']='2026-10-20';row.payload=p;db.commit()
    value=preview(client,headers)
    assert not value['can_move'] and 'week' in value['blocked_reason'].lower()


def test_customized_consent_not_bypassed(planned):
    _, headers, client, pid=planned
    with SessionLocal() as db:
        row=db.get(WorkoutPlan,pid);p=deepcopy(row.payload);p['customized']={'consent_id':'retained'};row.payload=p;db.commit()
    value=preview(client,headers)
    assert not value['can_move'] and 'Customized' in value['blocked_reason']


def test_current_date_collision_is_not_overwritten(planned):
    _, headers, client, pid=planned
    with SessionLocal() as db:
        row=db.get(WorkoutPlan,pid);p=deepcopy(row.payload);p['sessions'][-1]['date']=p['sessions'][-1]['scheduled_date']='2026-10-26';row.payload=p;db.commit()
    value=preview(client,headers)
    assert not value['can_move'] and 'today' in value['blocked_reason'].lower()


def test_authentication_required():
    assert TestClient(__import__('app.main',fromlist=['app']).app).get('/workout/next-planned').status_code==401


def test_same_week_missed_session_checks_explicit_source_rest(planned, monkeypatch):
    _, headers, client, pid = planned
    class Wednesday(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026,10,28,16,tzinfo=UTC)
    monkeypatch.setattr(workout, 'datetime', Wednesday)
    monkeypatch.setattr(selected_date_plans, 'datetime', Wednesday)
    with SessionLocal() as db:
        row=db.get(WorkoutPlan,pid);p=deepcopy(row.payload)
        rest={'kind':'minimum_rest','hard':True,'group_id':'source-rest','source_slot_ids':['source-0','source-1'],'minimum_rest_days':1}
        for session in p['sessions'][:2]:session['exercises'][0]['source_relationships']=[rest]
        row.payload=p;db.commit()
    value=preview(client,headers)
    assert value['original_date']=='2026-10-27'
    assert not value['can_move'] and 'minimum rest' in value['blocked_reason']


def test_missed_session_cannot_be_reordered_past_other_source_work(planned, monkeypatch):
    _, headers, client, pid=planned
    class Friday(datetime):
        @classmethod
        def now(cls,tz=None):return datetime(2026,10,30,16,tzinfo=UTC)
    monkeypatch.setattr(workout,'datetime',Friday)
    value=preview(client,headers)
    assert not value['can_move'] and 'reorder' in value['blocked_reason']


def test_foreign_account_plan_is_not_movable(planned):
    _,headers,client,pid=planned;value=preview(client,headers)
    with SessionLocal() as db:
        user=User(id=str(uuid4()),email=str(uuid4())+'@example.invalid',name='Synthetic foreign account',password_hash='unused')
        db.add(user);db.flush()
        foreign=WorkoutPlan(user_id=user.id,week_start=MONDAY,split='full_body',phase='maintenance',payload=deepcopy(stored(pid)))
        db.add(foreign);db.commit();foreign_id=foreign.id
    request=move_body(value);request['plan_id']=foreign_id
    assert client.post('/workout/next-planned/move',headers=headers,json=request).status_code==409
    assert stored(foreign_id)==stored(pid)


def test_local_today_rechecked_after_waiting_for_user_lock(planned, monkeypatch):
    _,headers,client,pid=planned;value=preview(client,headers);before=stored(pid)
    from app import next_planned_workout as commands
    original=commands.lock_history_user
    class Tuesday(datetime):
        @classmethod
        def now(cls,tz=None):return datetime(2026,10,27,16,tzinfo=UTC)
    def crossed_midnight(db,user_id):
        original(db,user_id)
        monkeypatch.setattr(workout,'datetime',Tuesday)
        monkeypatch.setattr(selected_date_plans,'datetime',Tuesday)
    monkeypatch.setattr(commands,'lock_history_user',crossed_midnight)
    response=client.post('/workout/next-planned/move',headers=headers,json=move_body(value))
    assert response.status_code==409
    assert stored(pid)==before
