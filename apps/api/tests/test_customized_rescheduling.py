"""Active date changes on verified disposable PostgreSQL, retaining execution identity."""
from copy import deepcopy
from datetime import UTC, datetime, date, timedelta
from uuid import uuid4

import pytest
from test_customized_application import application, accepted, post


def activated(application, body=None):
    c,h,_,_=application
    document=accepted(application,body)
    response=post(c,h,f"/customized/proposals/{document['proposal_id']}/activate",
        dict(expected_revision=document['revision'],snapshot_hash=document['snapshot_hash']))
    assert response.status_code==200,response.text
    return response.json()


def bound(application):
    from app.customized_application import build_service
    import app.main as main
    from app.models import User
    c,h,Session,account=application
    with Session() as db:
        user=db.query(User).filter_by(email=account['email']).one()
        service,gate=build_service(db.get_bind(),user.id,main.customized_clock,enabled=True)
        return service,gate.bind(user,h['Authorization'])


def preview(service,actor,active,dates,revision=1,key=None):
    return service.preview_reschedule(actor,active['proposal_id'],dict(selected_dates=dates,timezone='America/New_York'),
        expected_revision=active['revision'],expected_placement_revision=revision,idempotency_key=key or uuid4().hex)


def confirm(service,actor,pending,revision=1,key=None,**changes):
    data=dict(expected_revision=pending['revision'],expected_placement_revision=revision,
        digest=pending['pending_reschedule']['digest'],agree=True,idempotency_key=key or uuid4().hex)
    data.update(changes)
    return service.confirm_reschedule(actor,pending['proposal_id'],**data)


def test_reschedule_preserves_same_plan_prescription_ids_history_and_retry(application):
    from app.models import WorkoutPlan
    from app.workout_identity import identified_sessions
    active=activated(application);service,actor=bound(application)
    with application[2]() as db:
        plan=db.get(WorkoutPlan,active['active_plan_id']);before=deepcopy(plan.payload)
        identities=identified_sessions(plan)
    pending=preview(service,actor,active,['2026-10-20','2026-10-22','2026-10-24'])
    assert pending['state']=='active'
    assert pending['pending_reschedule']['source_verified'] is False
    with application[2]() as db:
        assert db.get(WorkoutPlan,active['active_plan_id']).payload==before
    result=confirm(service,actor,pending,key='same-reschedule')
    assert confirm(service,actor,pending,key='same-reschedule')==result
    with application[2]() as db:
        plan=db.get(WorkoutPlan,active['active_plan_id'])
        assert plan.placement_revision==2
        assert db.query(WorkoutPlan).filter_by(user_id=actor.subject,week_start=plan.week_start).count()==1
        sessions=identified_sessions(plan)
        assert [s['workout_occurrence_id'] for s in sessions]==[s['workout_occurrence_id'] for s in identities]
        assert [s['exercises'] for s in sessions]==[s['exercises'] for s in identities]
        assert [s['scheduled_date'] for s in sessions]==['2026-10-20','2026-10-22','2026-10-24']
        assert plan.payload['schedule']['placement_history'][0]['selected_dates']==before['schedule']['selected_dates']
    assert result['reschedule_receipt']['placement_revision']==2


def test_frozen_date_survives_undo_and_other_session_moves(application,monkeypatch):
    from app.models import WorkoutPlan,WorkoutOccurrence
    from app.customized_lifecycle_models import LifecycleError
    c,h,Session,_=application
    from app.routers import workout
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):
            instant=datetime(2026,10,19,12,tzinfo=UTC)
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(workout,'datetime',Clock)
    active=activated(application)
    today_response=c.get('/workout/today',headers=h)
    assert today_response.status_code==200,today_response.text
    today=c.get('/workout/today',headers=h).json();exercise=today['exercises'][0];wid=today['workout_occurrence_id']
    response=post(c,h,f'/workout/{wid}/log-set',dict(command_id='freeze',exercise_id=exercise['id'],
        exercise_occurrence_id=exercise['exercise_occurrence_id'],set_index=1,reps=9,weight=10))
    assert response.status_code==200,response.text
    response=post(c,h,f'/workout/{wid}/undo-last-set',dict(command_id='undo-freeze',exercise_id=exercise['id'],exercise_occurrence_id=exercise['exercise_occurrence_id']))
    assert response.status_code==200,response.text
    service,actor=bound(application)
    with Session() as db:
        frozen=deepcopy(db.get(WorkoutOccurrence,wid).payload)
    with pytest.raises(LifecycleError,match='frozen_occurrence_requires_future_replacement'):
        preview(service,actor,active,['2026-10-20','2026-10-22','2026-10-24'])
    pending=preview(service,actor,active,['2026-10-19','2026-10-21','2026-10-24'])
    result=confirm(service,actor,pending)
    with Session() as db:
        assert db.get(WorkoutOccurrence,wid).payload==frozen
        assert db.get(WorkoutPlan,active['active_plan_id']).placement_revision==2
    # Source integrity accepts the frozen occurrence's old placement only because
    # recorded history proves its unchanged date and prescription.
    with service.store.unit.account(actor.subject):
        service.schedule.week=date(2026,10,19)
        resolved=service.schedule.resolve(actor.subject,'America/New_York')
        assert next(o for o in resolved.occurrences if o.occurrence_id==wid).local_date==date(2026,10,19)
    assert result['state']=='active'
    # Historical dates alone cannot authorize a changed frozen prescription.
    with Session() as db:
        plan=db.get(WorkoutPlan,active['active_plan_id']);original=deepcopy(plan.payload)
        altered=deepcopy(original);altered['sessions'][0]['exercises'][0]['sets']+=1
        plan.payload=altered;db.commit()
    with pytest.raises(LifecycleError,match='frozen_occurrence_changed'):
        with service.store.unit.account(actor.subject):service.schedule.resolve(actor.subject,'America/New_York')
    with Session() as db:
        plan=db.get(WorkoutPlan,active['active_plan_id']);altered=deepcopy(original)
        altered['schedule']['placement_history'][0]['selected_dates'][0]='2026-10-20'
        plan.payload=altered;db.commit()
    with pytest.raises(LifecycleError,match='frozen_occurrence_changed'):
        with service.store.unit.account(actor.subject):service.schedule.resolve(actor.subject,'America/New_York')


@pytest.mark.parametrize(('dates','timezone','code'),[
    (['2026-10-20','2026-10-20','2026-10-24'],'America/New_York','Duplicate workout dates'),
    (['2026-10-20','2026-10-21','2026-10-24'],'America/New_York','schedule_spacing_conflict'),
    (['2026-10-26','2026-10-28','2026-10-30'],'America/New_York','cross_week_move_requires_future_replacement'),
    (['2026-10-20','2026-10-22','2026-10-24'],'UTC','schedule_timezone_change_requires_resolution'),
    (['2026-10-20','2026-10-22'],'America/New_York','three_actual_dates_required'),
])
def test_invalid_dates_leave_active_plan_unchanged(application,dates,timezone,code):
    from app.customized_lifecycle_models import LifecycleError
    from app.models import WorkoutPlan
    active=activated(application);service,actor=bound(application)
    with application[2]() as db:before=deepcopy(db.get(WorkoutPlan,active['active_plan_id']).payload)
    with pytest.raises(LifecycleError,match=code):
        service.preview_reschedule(actor,active['proposal_id'],dict(selected_dates=dates,timezone=timezone),
            expected_revision=active['revision'],expected_placement_revision=1,idempotency_key=uuid4().hex)
    with application[2]() as db:
        plan=db.get(WorkoutPlan,active['active_plan_id'])
        assert plan.payload==before and plan.placement_revision==1
    assert service.get(actor,active['proposal_id'])['revision']==active['revision']


def test_confirm_requires_explicit_exact_session_bound_preview(application):
    from app.customized_lifecycle_models import LifecycleError
    active=activated(application);service,actor=bound(application)
    pending=preview(service,actor,active,['2026-10-20','2026-10-22','2026-10-24'])
    for changes,code in [({'agree':False},'explicit_date_change_agreement_required'),
                         ({'agree':1},'explicit_date_change_agreement_required'),
                         ({'digest':'0'*64},'stale_reschedule_preview'),
                         ({'expected_revision':active['revision']},'stale_revision'),
                         ({'expected_placement_revision':2},'stale_placement_revision')]:
        with pytest.raises(LifecycleError,match=code):confirm(service,actor,pending,**changes)
    from app.models import User
    from app.customized_application import build_service
    token='Bearer '+uuid4().hex
    gate=service.store.gate
    gate.issue(actor.subject,token,entitlement_reference='synthetic second authenticated session',scopes=actor.scopes,
        valid_from=service.clock(),expires_at=service.clock()+timedelta(hours=1))
    with application[2]() as db:second=gate.bind(db.get(User,actor.subject),token)
    with pytest.raises(LifecycleError,match='reschedule_session_mismatch'):confirm(service,second,pending)
    confirm(service,actor,pending)


def test_changed_receipt_invalidates_preview_and_rollback_keeps_dates(application):
    from app.models import WorkoutPlan
    from app.customized_lifecycle_models import LifecycleError
    c,h,Session,_=application
    active=activated(application);service,actor=bound(application)
    pending=preview(service,actor,active,['2026-10-19','2026-10-21','2026-10-24'])
    today=c.get('/workout/today',headers=h).json();e=today['exercises'][0];wid=today['workout_occurrence_id']
    response=post(c,h,f'/workout/{wid}/log-set',dict(command_id='concurrent-start',exercise_id=e['id'],
        exercise_occurrence_id=e['exercise_occurrence_id'],set_index=1,reps=8,weight=10))
    assert response.status_code==200,response.text
    with pytest.raises(LifecycleError,match='stale_reschedule_preview'):confirm(service,actor,pending)
    with Session() as db:
        plan=db.get(WorkoutPlan,active['active_plan_id'])
        assert plan.placement_revision==1 and plan.payload['schedule']['selected_dates'][-1]=='2026-10-23'
    assert service.get(actor,active['proposal_id'])['revision']==pending['revision']


def test_api_reschedule_updates_week_and_today_without_duplicate_occurrence(application,monkeypatch):
    from app.models import WorkoutPlan,WorkoutOccurrence
    import app.main as main
    c,h,Session,_=application
    active=activated(application);base=f"/customized/proposals/{active['proposal_id']}"
    before=c.get('/workout/today',headers=h).json();wid=before['workout_occurrence_id']
    response=post(c,h,base+'/reschedule/preview',dict(expected_revision=active['revision'],expected_placement_revision=1,
        selected_dates=['2026-10-20','2026-10-22','2026-10-24'],timezone='America/New_York'))
    assert response.status_code==200,response.text
    pending=response.json()
    response=post(c,h,base+'/reschedule/confirm',dict(expected_revision=pending['revision'],expected_placement_revision=1,
        digest=pending['pending_reschedule']['digest'],agree=True),'api-date-confirm')
    assert response.status_code==200,response.text
    assert c.get('/workout/today',headers=h).status_code==404
    monkeypatch.setattr(main,'customized_clock',lambda:datetime(2026,10,20,12,tzinfo=UTC))
    today=c.get('/workout/today',headers=h)
    assert today.status_code==200,today.text
    assert today.json()['workout_occurrence_id']==wid
    fields=('id','exercise_occurrence_id','sets','rep_range','recommended_working_weight','load_semantics')
    assert [{k:e[k] for k in fields} for e in today.json()['exercises']]==[{k:e[k] for k in fields} for e in before['exercises']]
    week=c.get('/plan/scheduling-context',headers=h)
    assert week.status_code==200,week.text
    assert week.json()['selected_dates']==['2026-10-20','2026-10-22','2026-10-24']
    with Session() as db:
        assert db.query(WorkoutPlan).filter_by(id=active['active_plan_id']).count()==1
        assert db.query(WorkoutOccurrence).filter_by(plan_id=active['active_plan_id']).count()==0


def seed_neighbor(application,active,day,*,malformed=False):
    from app.models import WorkoutPlan
    with application[2]() as db:
        existing=db.get(WorkoutPlan,active['active_plan_id']);week=day-timedelta(days=day.weekday())
        payload=dict(program_template_id='pure_bodybuilding_phase_1_full_body',sessions=[dict(session_id='synthetic-neighbor',
            scheduled_date=day.isoformat(),schedule_timezone='America/New_York',placement_revision=1,
            exercises=[dict(id='synthetic-authored-slot',sets=1,rep_range=[8,12])])],
            schedule=dict(mode='selected_dates_v1',week_start=week.isoformat(),timezone='America/New_York',selected_dates=[day.isoformat()]))
        if malformed:payload['schedule']['selected_dates']=[]
        row=WorkoutPlan(user_id=existing.user_id,week_start=week,schedule_timezone='America/New_York',placement_revision=1,
            split='full_body',phase='authored',payload=payload)
        db.add(row);db.commit()
        return row.id,deepcopy(row.payload)


@pytest.mark.parametrize('neighbor,dates',[
    (date(2026,10,18),['2026-10-19','2026-10-21','2026-10-24']),
    (date(2026,10,26),['2026-10-20','2026-10-22','2026-10-25']),
])
def test_adjacent_authored_week_enforces_existing_c1_hard_gap_and_is_preserved(application,neighbor,dates):
    from app.models import WorkoutPlan
    from app.customized_lifecycle_models import LifecycleError
    active=activated(application);pid,payload=seed_neighbor(application,active,neighbor)
    service,actor=bound(application)
    with pytest.raises(LifecycleError,match='schedule_spacing_conflict'):preview(service,actor,active,dates)
    with application[2]() as db:assert db.get(WorkoutPlan,pid).payload==payload


def test_malformed_adjacent_coverage_fails_closed(application):
    from app.customized_lifecycle_models import LifecycleError
    active=activated(application);seed_neighbor(application,active,date(2026,10,12),malformed=True)
    service,actor=bound(application)
    with pytest.raises(LifecycleError,match='ambiguous_source_coverage_requires_resolution'):
        preview(service,actor,active,['2026-10-20','2026-10-22','2026-10-24'])


def test_reschedule_retains_local_dates_through_dst_change(application,monkeypatch):
    from test_customized_application import request
    from app.models import WorkoutPlan,User
    from app.config import settings
    from app.security import create_access_token
    import app.main as main
    monkeypatch.setattr(settings,'jwt_expire_minutes',14*24*60)
    with application[2]() as db:
        user=db.query(User).filter_by(email=application[3]['email']).one()
        application[1]['Authorization']='Bearer '+create_access_token(user.id,user.password_hash)
    monkeypatch.setattr(main,'customized_clock',lambda:datetime(2026,10,26,12,tzinfo=UTC))
    body=request();body['selected_dates']=['2026-10-26','2026-10-28','2026-10-30']
    active=activated(application,body);service,actor=bound(application)
    service.clock=main.customized_clock;service.schedule.clock=main.customized_clock
    pending=preview(service,actor,active,['2026-10-27','2026-10-29','2026-11-01'])
    confirm(service,actor,pending)
    with application[2]() as db:
        plan=db.get(WorkoutPlan,active['active_plan_id'])
        assert plan.payload['schedule']['selected_dates']==['2026-10-27','2026-10-29','2026-11-01']
        assert plan.schedule_timezone=='America/New_York'


def test_two_competing_confirms_commit_one_placement_revision(application):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.models import WorkoutPlan
    from app.customized_lifecycle_models import LifecycleError
    active=activated(application);service,actor=bound(application)
    pending=preview(service,actor,active,['2026-10-20','2026-10-22','2026-10-24'])
    barrier=Barrier(2)
    def race():
        barrier.wait(timeout=5)
        try:return confirm(service,actor,pending)['reschedule_receipt']['placement_revision']
        except LifecycleError as exc:return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:race(),range(2)))
    assert sorted(results,key=str)==[2,'stale_revision']
    with application[2]() as db:
        plan=db.get(WorkoutPlan,active['active_plan_id'])
        assert plan.placement_revision==2 and len(plan.payload['schedule']['placement_history'])==1


def test_persistence_failure_rolls_back_placement_and_retry_receipt(application,monkeypatch):
    from app.models import WorkoutPlan
    from app.customized_lifecycle_models import LifecycleError
    active=activated(application);service,actor=bound(application)
    pending=preview(service,actor,active,['2026-10-20','2026-10-22','2026-10-24'])
    original=service._append
    def fail_after_flush(*args,**kwargs):raise LifecycleError('synthetic_append_failure')
    monkeypatch.setattr(service,'_append',fail_after_flush)
    with pytest.raises(LifecycleError,match='synthetic_append_failure'):confirm(service,actor,pending,key='rollback-retry')
    with application[2]() as db:
        plan=db.get(WorkoutPlan,active['active_plan_id'])
        assert plan.placement_revision==1 and plan.payload['schedule']['placement_history']==[]
    assert service.get(actor,active['proposal_id'])['revision']==pending['revision']
    monkeypatch.setattr(service,'_append',original)
    assert confirm(service,actor,pending,key='rollback-retry')['reschedule_receipt']['placement_revision']==2


def test_retry_payload_conflict_and_revoked_session_cannot_confirm(application):
    from app.customized_lifecycle_models import LifecycleError
    active=activated(application);service,actor=bound(application)
    dates=['2026-10-20','2026-10-22','2026-10-24']
    pending=preview(service,actor,active,dates,key='preview-once')
    assert preview(service,actor,active,dates,key='preview-once')==pending
    with pytest.raises(LifecycleError,match='idempotency_conflict'):
        preview(service,actor,active,['2026-10-19','2026-10-21','2026-10-24'],key='preview-once')
    service.store.gate.revoke(actor.subject,actor.session_id)
    with pytest.raises(LifecycleError,match='session_unavailable'):confirm(service,actor,pending)


def test_foreign_account_and_authored_payload_cannot_reschedule(application):
    from app.models import WorkoutPlan
    from app.customized_lifecycle_models import LifecycleError
    c,h,Session,account=application
    active=activated(application)
    response=c.post('/auth/register',json={**account,'email':uuid4().hex+'@example.com'})
    assert response.status_code==200,response.text
    other={'Authorization':'Bearer '+response.json()['access_token']}
    response=post(c,other,f"/customized/proposals/{active['proposal_id']}/reschedule/preview",
        dict(expected_revision=active['revision'],expected_placement_revision=1,
            selected_dates=['2026-10-20','2026-10-22','2026-10-24'],timezone='America/New_York'))
    assert response.status_code==404,response.text
    # A stored Authored payload, even if referenced by a lifecycle record, never
    # obtains Customized write authority from choosing the Customize page.
    with Session() as db:
        plan=db.get(WorkoutPlan,active['active_plan_id']);payload=deepcopy(plan.payload)
        payload['mode']='authored';payload['program_template_id']='pure_bodybuilding_phase_1_full_body'
        plan.payload=payload;db.commit()
    service,actor=bound(application)
    with pytest.raises(LifecycleError,match='active_customized_identity_conflict'):
        preview(service,actor,active,['2026-10-20','2026-10-22','2026-10-24'])
    with Session() as db:assert db.get(WorkoutPlan,active['active_plan_id']).payload==payload
