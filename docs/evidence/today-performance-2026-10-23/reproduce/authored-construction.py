import os,json,time
from pathlib import Path
from datetime import datetime,date,timedelta,UTC
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL']);assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'today_performance_1023','m2a_test')
probe=create_engine(u)
with probe.connect() as c:assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_performance_1023','m2a_test')
probe.dispose()
from app.database import SessionLocal
from app.models import User,WorkoutPlan
from app.main import app
import app.routers.plan as plan
from fastapi.testclient import TestClient
real=plan.datetime;today=date.today();monday=today-timedelta(days=today.weekday())
class FixedDatetime(datetime):
 @classmethod
 def now(cls,tz=None):
  instant=datetime.combine(monday,datetime.min.time(),tzinfo=UTC)+timedelta(hours=12)
  return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
plan.datetime=FixedDatetime
accounts=json.loads(Path('.qualification/performance-accounts.json').read_text());label=os.environ.get('TODAY_RUN_LABEL','baseline');rows=[];client=TestClient(app)
try:
 for n in range(3):
  key=f'authored-first-browser-{label}-{n}';a=accounts[key]
  with SessionLocal() as db:
   user=db.get(User,a['user_id']);assert db.query(WorkoutPlan).filter_by(user_id=user.id).count()==0;user.split_preference='full_body';user.days_available=3;db.commit()
  payload={'template_id':'pure_bodybuilding_phase_1_full_body','selected_dates':[monday.isoformat(),(monday+timedelta(days=2)).isoformat(),today.isoformat()],'week_start':monday.isoformat(),'timezone':'UTC','expected_placement_revision':0}
  h={'Authorization':'Bearer '+a['token']}
  for path in ['/plan/selected-dates/preview','/plan/generate-week']:
   start=time.perf_counter();r=client.post(path,headers=h,json=payload);row={'trial':n+1,'phase':path,'ms':(time.perf_counter()-start)*1000,'status':r.status_code};rows.append(row)
   if r.status_code!=200:row['failure']=r.json();break
   if path.endswith('preview'):payload['expected_preview_digest']=r.json()['schedule']['preview_digest']
finally:plan.datetime=real
Path(f'docs/evidence/today-performance-2026-10-23/{label}-authored-construction.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
