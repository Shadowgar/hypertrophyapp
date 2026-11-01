import os,json,hashlib
from pathlib import Path
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL']);assert (u.port,u.database,u.username)==(55441,'gym_start_browser','gym_start_test')
from app.database import SessionLocal
from app.models import WorkoutOccurrence,WorkoutSetLog,AuthoredInitialCalibration,WorkoutPlan
from app.workout_identity import identified_sessions
from app.workout_history import effective_set_logs
browser=json.loads(Path('docs/evidence/simple-starting-weights-2026-11-01/browser-results.json').read_text());assert browser.get('passed')
expected={entry['scenario']:entry['canonicalKg'] for entry in browser['observations'] if 'canonicalKg' in entry}
accounts=json.loads(Path('.qualification/browser-accounts.json').read_text());result=[]
def source(ex):return {k:ex.get(k) for k in ('id','sets','rep_range','authored_prescription','source_lineage')}
with SessionLocal() as db:
 for mode,a in accounts.items():
  occurrence=db.get(WorkoutOccurrence,a['session']['workout_occurrence_id']);assert not occurrence or occurrence.user_id==a['user_id']
  original=[source(ex) for ex in a['session']['exercises']]
  persisted=occurrence.payload if occurrence else next(se for p in db.query(WorkoutPlan).filter_by(user_id=a['user_id']) for se in identified_sessions(p) if se['workout_occurrence_id']==a['session']['workout_occurrence_id'])
  current=[source(ex) for ex in persisted['exercises']]
  assert original==current,(mode,'source changed')
  logs=db.query(WorkoutSetLog).filter_by(user_id=a['user_id']).all()
  calibrations=db.query(AuthoredInitialCalibration).filter_by(user_id=a['user_id']).all()
  effective=effective_set_logs(db).filter_by(user_id=a['user_id']).count()
  assert effective==(0 if mode in ('phase1','unsupported') else 1),(mode,effective)
  assert len({row.command_id for row in calibrations})==len(calibrations)
  for row in logs:
   assert occurrence and row.workout_occurrence_id==occurrence.id
   assert abs(row.weight-expected[mode])<1e-9,(mode,'canonical weight changed')
   if mode=='flexible':assert row.performed_local_date.isoformat()==a['session']['execution_context']['local_day'],(mode,'actual date changed')
   else:assert row.performed_local_date is None and occurrence.scheduled_date.isoformat()==a['session']['date']
   if mode=='flexible':assert row.execution_context_id==a['session']['execution_context']['id'] and row.performed_local_date
  result.append({'scenario':mode,'source_preserved':True,'canonical_kg_preserved':True,'source_projection_sha256':hashlib.sha256(json.dumps(original,sort_keys=True).encode()).hexdigest(),'effective_working_sets':effective,'raw_set_rows':len(logs),'calibration_reports':len(calibrations),'distinct_calibration_commands':len({row.command_id for row in calibrations}),'actual_dates_present':all(row.performed_local_date is not None for row in logs)})
Path('docs/evidence/simple-starting-weights-2026-11-01/database-results.json').write_text(json.dumps(result,indent=2));print('PASS: all seven occurrence prescription projections preserved; owned receipts/date bindings and single calibration per command.')
