import os,json
from pathlib import Path
from copy import deepcopy
from uuid import uuid4
from datetime import date,timedelta,datetime,time
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL']);assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'today_performance_1023','m2a_test')
with create_engine(u).connect() as c:assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_performance_1023','m2a_test')
from app.database import SessionLocal
from app.models import User,WorkoutPlan,WorkoutOccurrence,WorkoutSetLog,UserInterfacePreference
from app.program_loader import load_program_template
from app.security import create_access_token
from app.workout_identity import identified_sessions,resolve_occurrence
from fastapi.testclient import TestClient
from app.main import app
PROGRAM='pure_bodybuilding_phase_1_full_body';today=date.today();monday=today-timedelta(days=today.weekday())
original=load_program_template(PROGRAM)['sessions'][2];original['session_id']='performance-source-session'

for ex in original['exercises']:ex.setdefault('recommended_working_weight',0)
accounts=json.loads(Path('.qualification/performance-accounts.json').read_text());client=TestClient(app)
def newuser(mode):
 uid=str(uuid4())
 with SessionLocal() as db:
  db.add(User(id=uid,email=f'perf-{uid}@example.com',password_hash='unused',name='Synthetic performance '+mode,selected_program_id=PROGRAM,equipment_profile=['cable','machine','dumbbell','barbell','bench','bodyweight','floor'],movement_restrictions=[],days_available=3,training_location='gym',onboarding_answers={},scheduling_timezone='UTC'));db.flush()
  db.add(UserInterfacePreference(user_id=uid,theme_family='classic',appearance='dark',weight_unit='lb',revision=1));db.commit()
 return {'user_id':uid,'token':create_access_token(uid,'unused'),'mode':mode}
def addplan(db,uid,day,session):
 session=deepcopy(session);session.update(date=day.isoformat(),scheduled_date=day.isoformat(),schedule_timezone='UTC',placement_revision=1)
 row=WorkoutPlan(user_id=uid,week_start=day-timedelta(days=day.weekday()),split='full_body',phase='maintenance',schedule_timezone='UTC',placement_revision=1,payload={'program_template_id':PROGRAM,'schedule':{'mode':'selected_dates_v1','selected_dates':[day.isoformat()],'timezone':'UTC','placement_revision':1},'sessions':[session]});db.add(row);db.flush()
 if day==today:
  payload=deepcopy(row.payload);payload['sessions']=[];dates=[monday,monday+timedelta(days=2),today]
  for index,raw in enumerate(load_program_template(PROGRAM)['sessions'][:3]):
   raw=deepcopy(raw);raw.update(session_id=f'performance-source-session-{index}',date=dates[index].isoformat(),scheduled_date=dates[index].isoformat(),schedule_timezone='UTC',placement_revision=1)
   for ex in raw['exercises']:ex.setdefault('recommended_working_weight',0)
   payload['sessions'].append(raw)
  payload['schedule']['selected_dates']=[d.isoformat() for d in dates];row.payload=payload;db.flush()
 return row
for size,count in [('small',0),('large',100)]:
 for state in ['unstarted','inprogress']:
  key=f'authored-{size}-{state}';a=newuser(key);accounts[key]=a
  with SessionLocal() as db:
   for n in range(count):
    day=today-timedelta(days=7*(n+1));p=addplan(db,a['user_id'],day,original);occ,session=resolve_occurrence(db,a['user_id'],identified_sessions(p)[0]['workout_occurrence_id'],[p]);db.add(occ);db.flush()
    for ex in session['exercises']:
     for index in range(1,4):
      db.add(WorkoutSetLog(user_id=a['user_id'],workout_id=session['session_id'],workout_occurrence_id=occ.id,exercise_occurrence_id=ex['exercise_occurrence_id'],primary_exercise_id=ex['id'],exercise_id=ex['id'],set_index=index,reps=11,weight=30,rpe=8,set_kind='work',created_at=datetime.combine(day,time(12)),replay_context={'version':2,'load_intelligence':{'load_context':{'unit':'kg','basis':'total_external','equipment_key':None,'increment':None,'increment_unit':'kg','equipment_tags':['cable'],'equipment_provenance':'profile_tags_not_inventory'}},'planned_exercise':deepcopy(ex)}))
   p=addplan(db,a['user_id'],today,original);db.commit();a['session']=identified_sessions(p)[2]
  if state=='inprogress':
   s=a['session'];ex=s['exercises'][0]
   r=client.post('/workout/'+s['workout_occurrence_id']+'/log-set',headers={'Authorization':'Bearer '+a['token']},json={'command_id':str(uuid4()),'exercise_occurrence_id':ex['exercise_occurrence_id'],'exercise_id':ex['id'],'set_index':1,'weight':30,'reps':11,'rpe':8});assert r.status_code==200,(key,r.text)
  print(key,count,len(original['exercises']))

Path('.qualification/performance-accounts.json').write_text(json.dumps(accounts))
print('Fresh coherent Mon/Wed/Fri Authored fixture accounts saved; current Friday uses third source session')
