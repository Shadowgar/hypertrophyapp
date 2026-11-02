import ast,hashlib,json,os,statistics,subprocess
from pathlib import Path
from collections import Counter
from sqlalchemy.engine import make_url
from sqlalchemy import create_engine,text
u=make_url(os.environ['DATABASE_URL'])
assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55443,'today_loading_browser','today_loading_test')
e=create_engine(u)
with e.connect() as c:assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_loading_browser','today_loading_test')
e.dispose()
out=Path('docs/evidence/today-loading-resume-2026-11-01')
from app.database import SessionLocal
from app.models import WorkoutOccurrence,WorkoutPlan,WorkoutSetLog
from app.workout_identity import identified_sessions
from app.workout_history import effective_set_logs
def projection(ex):return {k:ex.get(k) for k in ('id','sets','rep_range','authored_prescription','source_lineage')}
result=[]
with SessionLocal() as db:
 for group,file in [('recovery','browser-recovery-accounts.json')]:
  accounts=json.loads(Path('.qualification/'+file).read_text())
  for mode,a in accounts.items():
   occurrence=db.get(WorkoutOccurrence,a['session']['workout_occurrence_id']);assert not occurrence or occurrence.user_id==a['user_id']
   persisted=occurrence.payload if occurrence else next(s for p in db.query(WorkoutPlan).filter_by(user_id=a['user_id']) for s in identified_sessions(p) if s['workout_occurrence_id']==a['session']['workout_occurrence_id'])
   expected=[projection(ex) for ex in a['session']['exercises']];assert expected==[projection(ex) for ex in persisted['exercises']]
   logs=db.query(WorkoutSetLog).filter_by(user_id=a['user_id']).all();count=effective_set_logs(db).filter_by(user_id=a['user_id']).count()
   assert count==(1 if (group=='recovery' and mode=='recent') or (group=='measurements' and mode=='manual' and os.environ.get('TODAY_EXPECT_OLD_MANUAL_RECEIPT')=='1') else 0) # earlier isolated failed-harness committed receipt is preserved
   for row in logs:
    assert row.workout_occurrence_id==a['session']['workout_occurrence_id'];assert row.performed_local_date is None
    assert abs(row.weight-(42 if mode=='recent' else 25)*0.45359237)<1e-9
   result.append({'group':group,'scenario':mode,'source_projection_sha256':hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest(),'source_preserved':True,'effective_sets':count,'audit_rows':len(logs),'canonical_kg_preserved':True,'calendar_dates_not_backfilled':True})
(out/'database-final-recovery-results.json').write_text(json.dumps(result,indent=2));print('PASS: four final synthetic source projections, owned audit receipts, canonical kg and dates preserved.')
