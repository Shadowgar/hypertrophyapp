import os,json
from pathlib import Path
from copy import deepcopy
from uuid import uuid4
from datetime import date,timedelta
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL'])
assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'today_performance_1023','m2a_test')
e=create_engine(u)
with e.connect() as c:
 assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_performance_1023','m2a_test')
 assert c.execute(text('select version_num from alembic_version')).scalar()=='0026_initial_calibration'
from app.database import SessionLocal
from app.models import User,WorkoutPlan,UserInterfacePreference
from app.program_loader import load_program_template
from app.security import create_access_token
from app.workout_identity import identified_sessions
PROGRAM='pure_bodybuilding_phase_1_full_body'
original=load_program_template(PROGRAM)['sessions'][0]['exercises'][0]
assert original['id']=='cross_body_lat_pull_around'
original['recommended_working_weight']=0
accounts={}
for mode in ('eligible','unsupported','history'):
 uid=str(uuid4());today=date.today();monday=today-timedelta(days=today.weekday())
 with SessionLocal() as db:
  user=User(id=uid,email=f'initial-{mode}-{uid}@example.com',password_hash='unused',name='Synthetic '+mode,
   selected_program_id=PROGRAM,equipment_profile=['cable'],movement_restrictions=[],days_available=3,
   training_location='gym',onboarding_answers={},scheduling_timezone='UTC')
  db.add(user);db.flush()
  db.add(UserInterfacePreference(user_id=uid,theme_family='classic',appearance='dark',weight_unit='lb',revision=1))
  exercise=deepcopy(original)
  if mode=='unsupported':
   # An owned synthetic source-shaped fixture with an unsupported target; no compiled artifact altered.
   exercise['authored_prescription']['sets'][0]['rep_target']={'kind':'amrap','raw':'AMRAP','min':None,'max':None}
  row=WorkoutPlan(user_id=uid,week_start=monday,split='full_body',phase='maintenance',schedule_timezone='UTC',placement_revision=1,payload={'program_template_id':PROGRAM,'schedule':{'mode':'selected_dates_v1','selected_dates':[monday.isoformat(),(monday+timedelta(days=2)).isoformat(),today.isoformat()],'timezone':'UTC','placement_revision':1},
   'sessions':[{'session_id':'initial-browser','title':'Synthetic Cross-Body qualification','date':today.isoformat(),'scheduled_date':today.isoformat(),
    'schedule_timezone':'UTC','placement_revision':1,'exercises':[exercise]}]})
  db.add(row);db.commit();session=identified_sessions(row)[0]
  accounts[mode]={'user_id':uid,'token':create_access_token(uid),'session':session}
Path('.qualification/browser-accounts.json').write_text(json.dumps(accounts,indent=2))
print('Three synthetic owned accounts/plans created; credentials retained only in ignored private evidence.')
