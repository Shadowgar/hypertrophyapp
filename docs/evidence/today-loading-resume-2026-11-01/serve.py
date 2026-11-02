import os,time,json,threading,functools,contextvars,sys
from pathlib import Path
from sqlalchemy import event,text,create_engine
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL']);assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55443,'today_loading_browser','today_loading_test')
probe=create_engine(u)
with probe.connect() as c:assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_loading_browser','today_loading_test')
probe.dispose()
from app.database import engine
from app.main import app
import app.workout_load_state as load
import app.workout_initial_calibration as calibration
import app.workout_customized as customized
import app.routers.workout as workout
import app.workout_authored as authored
process_marker=os.environ['TODAY_PROCESS_MARKER']
state=contextvars.ContextVar('perf',default=None)
@event.listens_for(engine,'before_cursor_execute')
def before(conn,cursor,statement,parameters,context,many):
 context._perf_start=time.perf_counter()
@event.listens_for(engine,'after_cursor_execute')
def after(conn,cursor,statement,parameters,context,many):
 s=state.get()
 if s is not None:
  s['sql_count']+=1;s['sql_ms']+=(time.perf_counter()-context._perf_start)*1000
  if 'authored_initial_calibrations' in statement:s['calibration_sql_count']+=1
# External wrappers preserve original arguments/results and do not cache behavior.
names={'_source_warmup_protocol','source_scope','setup_scope','find_calibration','_all_groups','load_authored_history_snapshot','project_authored_load_feedback','_warmup_guidance','typed_projection','authored_feedback_projection','_list_current_workout_plans','decision_for','feedback','today','calibration_for'}
for mod in [load,calibration,customized,workout,authored]:
 for name in names:
  fn=getattr(mod,name,None)
  if not callable(fn):continue
  def wrap(fn,label):
   @functools.wraps(fn)
   def call(*a,**k):
    s=state.get();start=time.perf_counter()
    try:return fn(*a,**k)
    finally:
     if s is not None:
      p=s['phases'].setdefault(label,{'calls':0,'ms':0});p['calls']+=1;p['ms']+=(time.perf_counter()-start)*1000
   return call
  setattr(mod,name,wrap(fn,mod.__name__+'.'+name))
output=Path('.qualification/api-timings-'+os.environ.get('TODAY_RUN_LABEL','baseline')+'.jsonl')
@app.middleware('http')
async def measurement(request,call_next):
 s={'path':request.url.path,'scenario':request.headers.get('x-perf-scenario'),'sql_count':0,'sql_ms':0,'calibration_sql_count':0,'phases':{}};token=state.set(s);start=time.perf_counter()
 try:
  response=await call_next(request);response.headers['X-Perf-Run']=process_marker;s['status']=response.status_code;return response
 finally:
  s['total_ms']=(time.perf_counter()-start)*1000
  with output.open('a') as f:f.write(json.dumps(s)+'\n')
  state.reset(token)
# Reuse the prior performance study's isolated routing-clock technique.
# Freeze only application calendar owners; authentication/JWT wall clock is untouched.
from datetime import datetime as RealDatetime,date as RealDate,timezone
import app.routers.plan as plan_route,app.routers.profile as profile_route,app.routers.history as history_route
import app.flexible_training as flexible
class FixtureDatetime(RealDatetime):
 @classmethod
 def now(cls,tz=None):
  value=RealDatetime(2026,11,1,23,45,tzinfo=timezone.utc)
  return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)
class FixtureDate(RealDate):
 @classmethod
 def today(cls):return cls(2026,11,1)
for module in ((workout,plan_route,profile_route,history_route,flexible,load) if os.environ.get("TODAY_FIXTURE_CLOCK") == "1" else ()):
 if hasattr(module,'datetime'):module.datetime=FixtureDatetime
 if hasattr(module,'date'):module.date=FixtureDate
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=8043,log_level='warning')
