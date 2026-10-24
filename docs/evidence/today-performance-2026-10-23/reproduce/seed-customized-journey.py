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
import app.main as main
from datetime import UTC
main.customized_clock=lambda: datetime.combine(monday,time(12),tzinfo=UTC)
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
# Real Customized lifecycle: original deterministic proposal, reviewed consent and activation.
for state in ['journey']:
 key=f'customized-small-{state}';a=newuser(key);accounts[key]=a
 h={'Authorization':'Bearer '+a['token']}
 def post(path,data):
  r=client.post(path,headers={**h,'Idempotency-Key':uuid4().hex},json=data);assert r.status_code==200,(path,r.text[:700]);return r.json()
 dates=[today.isoformat()]+[(today+timedelta(days=n)).isoformat() for n in range(1,7-today.weekday())][:2]
 # Three selected days from current local week, with today retained.
 dates=[monday.isoformat(),(monday+timedelta(days=2)).isoformat(),today.isoformat()]
 p=post('/customized/proposals',dict(mode='customized',bundle_id='shorter-current',goal='hypertrophy',training_context='current',population='broadly_healthy_adult',selected_dates=dates,timezone='UTC',cap_minutes=60,cap_kind='hard',equipment=['machine','floor','dumbbell','bench','bodyweight','leg_press_station','chest_press_station','row_station','leg_curl_station','pulldown_station','calf_station'],skill='intermediate',restrictions=[]))
 ch=post(f"/customized/proposals/{p['proposal_id']}/challenge",dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']))
 ac=post(f"/customized/proposals/{p['proposal_id']}/accept",dict(protocol='compact-candidate-consent-v2',expected_revision=ch['revision'],snapshot_hash=ch['snapshot_hash'],challenge=ch['challenge'],terms_hash=ch['terms_hash'],summary_hash=ch['summary_hash'],mode='customized',agree=True))
 post(f"/customized/proposals/{p['proposal_id']}/activate",dict(expected_revision=ac['revision'],snapshot_hash=ac['snapshot_hash']))
 r=client.get('/workout/today',headers=h);assert r.status_code==200,r.text;s=r.json();a['session']=s
 if state=='inprogress':
  ex=s['exercises'][0];post('/workout/'+s['workout_occurrence_id']+'/log-set',dict(command_id=str(uuid4()),exercise_occurrence_id=ex['exercise_occurrence_id'],exercise_id=ex['id'],set_index=1,reps=8,weight=10))
 print(key,len(s['exercises']))
Path('.qualification/customized-journey-account.json').write_text(json.dumps(accounts[key]))
print('Synthetic accounts retained in private file only')
