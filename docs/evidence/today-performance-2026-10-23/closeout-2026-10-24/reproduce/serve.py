import os,json,hashlib
from pathlib import Path
from datetime import datetime as RealDatetime,date as RealDate,timezone
# Reuse guarded real-API SQL/phase instrumentation, not application policy.
code=Path('/tmp/hypertrophy-today-perf/.qualification/serve-instrumented.py').read_text()
code=code.split('import uvicorn')[0]
exec(compile(code,'existing-measurement-server','exec'))
import app.routers.workout as workout_route,app.routers.plan as plan_route,app.routers.profile as profile_route,app.routers.history as history_route
class FixtureDatetime(RealDatetime):
 @classmethod
 def now(cls,tz=None):
  value=RealDatetime(2026,10,23,17,tzinfo=timezone.utc)
  return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)
class FixtureDate(RealDate):
 @classmethod
 def today(cls):return cls(2026,10,23)
for module in (workout_route,plan_route,profile_route,history_route):
 if hasattr(module,'datetime'):module.datetime=FixtureDatetime
 if hasattr(module,'date'):module.date=FixtureDate
# JWT/auth time intentionally remains actual wall time.
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=8020,log_level='warning')
