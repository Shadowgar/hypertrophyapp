import os,json
from pathlib import Path
from copy import deepcopy
from datetime import date,timedelta
from uuid import uuid4
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL']);assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'today_performance_1023','m2a_test')
e=create_engine(u)
with e.connect() as c:assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_performance_1023','m2a_test')
from app.database import SessionLocal
from app.models import WorkoutPlan
from app.workout_identity import identified_sessions
from fastapi.testclient import TestClient
from app.main import app
accounts=json.loads(Path('.qualification/browser-accounts.json').read_text());account=accounts['history'];today=date.today();prior=today-timedelta(days=7)
with SessionLocal() as db:
 ex=deepcopy(account['session']['exercises'][0]);ex.pop('exercise_occurrence_id',None)
 row=WorkoutPlan(user_id=account['user_id'],week_start=prior-timedelta(days=prior.weekday()),split='full_body',phase='maintenance',payload={'program_template_id':'pure_bodybuilding_phase_1_full_body','sessions':[{'session_id':'initial-prior','title':'Synthetic prior exposure','scheduled_date':prior.isoformat(),'date':prior.isoformat(),'schedule_timezone':'UTC','placement_revision':1,'exercises':[ex]}]})
 db.add(row);db.commit();session=identified_sessions(row)[0]
headers={'Authorization':'Bearer '+account['token']};client=TestClient(app)
context={'unit':'kg','display_unit':'lb','basis':'machine_stack','equipment_key':'synthetic-cable-A-left-full-ROM','increment':2.5,'increment_unit':'lb'}
for index in (1,2,3):
 result=client.post('/workout/'+session['workout_occurrence_id']+'/log-set',headers=headers,json={'command_id':str(uuid4()),'exercise_occurrence_id':session['exercises'][0]['exercise_occurrence_id'],'exercise_id':ex['id'],'set_index':index,'weight':40,'reps':11,'rpe':7.5 if index<3 else 8.5,'load_context':context})
 assert result.status_code==200,result.text
current=account['session'];response=client.post('/workout/'+current['workout_occurrence_id']+'/initial-calibration',headers=headers,json={'command_id':str(uuid4()),'exercise_occurrence_id':current['exercises'][0]['exercise_occurrence_id'],'load_context':context,'calibration':{'method':'known_1rm','load':100,'unit':'lb','observed_date':today.isoformat(),'confirmed':True,'variant_id':ex['id'],'setup_details':'Left side full ROM, single handle, pulley 8','attainable':{'unit':'lb','min':5,'step':2.5,'max':100}}})
assert response.status_code==200,response.text
r=response.json();assert r['next_exposure']['recommended_weight']==40 and r['initial_estimate']['status']=='unavailable'
print('Qualified history scenario: 3 synthetic source-target sets; history-backed hold40kg supersedes reported100lb calibration. No old records modified.')
