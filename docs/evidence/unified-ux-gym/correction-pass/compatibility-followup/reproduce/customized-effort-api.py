import sys,os
from pathlib import Path
for candidate in (Path.cwd()/'apps/api/tests',Path.cwd()/'tests'):
    if candidate.is_dir():sys.path.insert(0,str(candidate))
from test_customized_application import application,accepted,post

def test_actual_effort_scale_switch_preserves_consent_and_history(application):
    c,h,Session,_=application
    a=accepted(application)
    active=post(c,h,f"/customized/proposals/{a['proposal_id']}/activate",dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash']))
    assert active.status_code==200,active.text
    t=c.get('/workout/today',headers=h).json();e=t['exercises'][0];wid=t['workout_occurrence_id']
    logged=post(c,h,f'/workout/{wid}/log-set',dict(command_id='effort-original',exercise_id=e['id'],exercise_occurrence_id=e['exercise_occurrence_id'],set_index=1,reps=8,weight=10,rpe=8))
    assert logged.status_code==200,logged.text
    from app.models import WorkoutSetLog,WorkoutPlan
    from copy import deepcopy
    with Session() as db:
        original=db.query(WorkoutSetLog).filter_by(workout_occurrence_id=wid).one();oid=original.id
        consent=deepcopy(db.get(WorkoutPlan,active.json()['active_plan_id']).payload['customized']['consent_receipt'])
    url=f'/workout/set/{oid}/correct'
    rejected=post(c,h,url,dict(command_id='effort-rir-invalid',reps=8,weight=10,actual_rir=2,reason='Synthetic scale switch'))
    assert rejected.status_code==422 and rejected.json()['detail']=='Record one actual effort scale'
    rir=post(c,h,url,dict(command_id='effort-rir',reps=8,weight=10,actual_rir=2,rpe=None,reason='Synthetic RIR instead of RPE'))
    assert rir.status_code==200,rir.text
    replacement=rir.json()['effective_set_id'];url=f'/workout/set/{replacement}/correct'
    rejected=post(c,h,url,dict(command_id='effort-rpe-invalid',reps=8,weight=10,rpe=8,reason='Synthetic scale switch'))
    assert rejected.status_code==422 and rejected.json()['detail']=='Record one actual effort scale'
    values=dict(command_id='effort-rpe',reps=8,weight=10,rpe=8,actual_rir=None,reason='Synthetic RPE instead of RIR')
    rpe=post(c,h,url,values);assert rpe.status_code==200,rpe.text
    assert post(c,h,url,values).json()==rpe.json()
    with Session() as db:
        rows=db.query(WorkoutSetLog).filter_by(workout_occurrence_id=wid).all();assert len(rows)==3
        current=db.get(WorkoutSetLog,rpe.json()['effective_set_id']);assert current.rpe==8 and current.replay_context['actual_rir'] is None
        assert db.get(WorkoutSetLog,replacement).rpe is None and db.get(WorkoutSetLog,replacement).replay_context['actual_rir']==2
        assert db.get(WorkoutSetLog,oid).rpe==8
        assert db.get(WorkoutPlan,active.json()['active_plan_id']).payload['customized']['consent_receipt']==consent
