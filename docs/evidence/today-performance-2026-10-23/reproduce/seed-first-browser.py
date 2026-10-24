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
original=load_program_template(PROGRAM)['sessions'][0];original['session_id']='performance-source-session'

for ex in original['exercises']:ex.setdefault('recommended_working_weight',0)
accounts={};client=TestClient(app)
def newuser(mode):
 uid=str(uuid4())
 with SessionLocal() as db:
  db.add(User(id=uid,email=f'perf-{uid}@example.com',password_hash='unused',name='Synthetic performance '+mode,selected_program_id=PROGRAM,equipment_profile=['cable','machine','dumbbell','barbell','bench','bodyweight','floor'],movement_restrictions=[],days_available=3,training_location='gym',onboarding_answers={},scheduling_timezone='UTC'));db.flush()
  db.add(UserInterfacePreference(user_id=uid,theme_family='classic',appearance='dark',weight_unit='lb',revision=1));db.commit()
 return {'user_id':uid,'token':create_access_token(uid,'unused'),'mode':mode}
def addplan(db,uid,day,session):
 session=deepcopy(session);session.update(date=day.isoformat(),scheduled_date=day.isoformat(),schedule_timezone='UTC',placement_revision=1)
 row=WorkoutPlan(user_id=uid,week_start=day-timedelta(days=day.weekday()),split='full_body',phase='maintenance',schedule_timezone='UTC',placement_revision=1,payload={'program_template_id':PROGRAM,'schedule':{'mode':'selected_dates_v1','selected_dates':[day.isoformat()],'timezone':'UTC','placement_revision':1},'sessions':[session]});db.add(row);db.flush();return row

accounts=json.loads(Path('.qualification/performance-accounts.json').read_text())
for label in ['baseline','after']:
 for n in range(3):
  key=f'authored-first-browser-{label}-{n}';a=newuser(key)
  with SessionLocal() as db:
   u=db.get(User,a['user_id']);u.scheduling_timezone=None;db.commit()
  accounts[key]=a
Path('.qualification/performance-accounts.json').write_text(json.dumps(accounts))
print('Six fresh synthetic first-use browser accounts created')
