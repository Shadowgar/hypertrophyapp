import os,json
from pathlib import Path
from copy import deepcopy
from uuid import uuid4
from datetime import date,datetime,timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL'])
assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55443,'today_loading_browser','today_loading_test')
e=create_engine(u)
with e.connect() as c:
 assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_loading_browser','today_loading_test')
from app.database import SessionLocal
from app.models import User,WorkoutPlan,UserInterfacePreference
from app.program_loader import load_program_template
from app.security import create_access_token
from app.workout_identity import identified_sessions
import httpx
c=httpx.Client(base_url='http://127.0.0.1:8043',timeout=120)
accounts={}
for mode,phase in [('phase1',1),('recent',1),('manual',1),('unsupported',1),('phase2',2),('flexible',1),('customized',1)]:
 uid=str(uuid4()); today=date.fromisoformat(os.environ["TODAY_FIXTURE_DAY"]); monday=today-timedelta(days=today.weekday())
 program=f'pure_bodybuilding_phase_{phase}_full_body'
 with SessionLocal() as db:
  user=User(id=uid,email=f'gym-{mode}-{uid}@example.com',password_hash='unused',name='Synthetic '+mode,age=34,weight=80,gender='prefer_not_to_say',nutrition_phase='maintenance',weak_areas=[],
   selected_program_id=program,split_preference='full_body',equipment_profile=sorted({tag for week in load_program_template(program).get('authored_weeks',[]) for se in week['sessions'] for ex in se['exercises'] for tag in ex.get('equipment_tags',[])}),movement_restrictions=[],days_available=3,
   training_location='gym',onboarding_answers={},scheduling_timezone='UTC')
  db.add(user);db.flush();db.add(UserInterfacePreference(user_id=uid,theme_family='classic',appearance='dark',weight_unit='lb',revision=1))
  db.commit()
 token=create_access_token(uid, "unused"); headers={'Authorization':'Bearer '+token}; accounts[mode]={'user_id':uid,'token':token}
 def post(path,body):
  r=c.post(path,headers={**headers,'Idempotency-Key':uuid4().hex},json=body)
  assert r.status_code==200,(path,r.status_code)
  return r.json()
 if mode not in ('flexible','customized'):
  post('/plan/generate-week',{'template_id':program,'week_start':monday.isoformat(),'selected_dates':[(monday+timedelta(days=i)).isoformat() for i in (1,4,6)],'timezone':'UTC','target_days':3,'expected_placement_revision':0})
 if mode=='flexible':
  body={'program_id':program,'timezone':'UTC','expected_sessions_per_week':3}
  preview=post('/training/enroll/preview',body);assert preview['available']
  state=post('/training/enroll',{**body,'preview_digest':preview['digest'],'confirmed':True,'command_id':str(uuid4())})
  state=post('/training/'+state['sequence_id']+'/start',{'command_id':str(uuid4()),'expected_revision':state['revision'],'occurrence_id':state['occurrence_id'],'expected_digest':state['digest'],'expected_local_day':state['local_day'],'confirmed':True})
 if mode=='customized':
  tz='Pacific/Kiritimati';local=datetime.fromisoformat(os.environ["TODAY_FIXTURE_INSTANT"]).astimezone(ZoneInfo(tz)).date();assert local.weekday()<=4
  dates=[(local+timedelta(days=i)).isoformat() for i in (0,2,4)]
  with SessionLocal() as db:db.get(User,uid).scheduling_timezone=tz;db.commit()
  body=dict(mode='customized',bundle_id='shorter-current',goal='hypertrophy',training_context='current',population='broadly_healthy_adult',selected_dates=dates,timezone=tz,cap_minutes=60,cap_kind='hard',equipment=['machine','floor','dumbbell','bench','bodyweight','leg_press_station','chest_press_station','row_station','leg_curl_station','pulldown_station','calf_station'],skill='intermediate',restrictions=[])
  p=post('/customized/proposals',body)
  ch=post('/customized/proposals/'+p['proposal_id']+'/challenge',dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']))
  a=post('/customized/proposals/'+p['proposal_id']+'/accept',dict(protocol='compact-candidate-consent-v2',expected_revision=ch['revision'],snapshot_hash=ch['snapshot_hash'],challenge=ch['challenge'],terms_hash=ch['terms_hash'],summary_hash=ch['summary_hash'],mode='customized',agree=True))
  post('/customized/proposals/'+a['proposal_id']+'/activate',dict(expected_revision=a['revision'],snapshot_hash=a['snapshot_hash']))
 r=c.get('/workout/today',headers=headers);assert r.status_code==200,(mode,r.status_code)
 accounts[mode]['session']=r.json()
 profile=c.get('/profile',headers=headers);assert profile.status_code==200,(mode,profile.status_code)

p=Path('.qualification/browser-accounts.json');p.write_text(json.dumps(accounts));p.chmod(0o600)
print('Seven synthetic accounts ready; real API-owned Flexible enrollment and Customized consent/activation. No production target used.')
