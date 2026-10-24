import os
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL']);assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'today_performance_1023','m2a_test')
probe=create_engine(u)
with probe.connect() as c:assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_performance_1023','m2a_test')
probe.dispose()
import json,time,urllib.request
from pathlib import Path
from app.database import SessionLocal
from app.models import User,WorkoutPlan
accounts=json.loads(Path('.qualification/performance-accounts.json').read_text());rows=[]
for n in range(3):
 a=accounts[f'authored-first-{n+int(os.environ.get("TODAY_FIRST_OFFSET","0"))}']
 with SessionLocal() as db:
  u=db.get(User,a['user_id']);assert db.query(WorkoutPlan).filter_by(user_id=u.id).count()==0;u.scheduling_timezone=None;db.commit()
 t=time.perf_counter();req=urllib.request.Request('http://127.0.0.1:8020/workout/today',headers={'Authorization':'Bearer '+a['token']})
 try:
  with urllib.request.urlopen(req,timeout=120) as r:p=json.load(r);status=r.status
  row={'trial':n+1,'status':status,'ms':(time.perf_counter()-t)*1000,'exercise_count':len(p.get('exercises',[]))}
 except Exception as e:row={'trial':n+1,'error':str(e),'ms':(time.perf_counter()-t)*1000}
 rows.append(row)
Path('docs/evidence/today-performance-2026-10-23/'+os.environ.get('TODAY_RUN_LABEL','baseline')+'-first-use.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
