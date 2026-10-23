import os,json,hashlib
from pathlib import Path
from sqlalchemy import create_engine,text,select
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL'])
assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'initial_load_migration_1023','m2a_test')
e=create_engine(u)
with e.connect() as c:assert tuple(c.execute(text('select current_database(),current_user')).one())==('initial_load_migration_1023','m2a_test')
from app.database import SessionLocal
from app.models import AuthoredInitialCalibration,WorkoutSetLog,WorkoutOccurrence,WorkoutLogCommand,WorkoutPlan
accounts=json.loads(Path('.qualification/browser-accounts.json').read_text())
result={'application_revision':'96ef19d43c88440b987d290844e4da7775a70912','target':'verified disposable initial_load_migration_1023','accounts':{}}
with SessionLocal() as db:
 for name,account in accounts.items():
  uid=account['user_id'];session=account['session'];ex=session['exercises'][0]
  calibrations=list(db.scalars(select(AuthoredInitialCalibration).where(AuthoredInitialCalibration.user_id==uid)))
  logs=list(db.scalars(select(WorkoutSetLog).where(WorkoutSetLog.user_id==uid)))
  commands=list(db.scalars(select(WorkoutLogCommand).where(WorkoutLogCommand.user_id==uid)))
  occurrence=db.get(WorkoutOccurrence,session['workout_occurrence_id'])
  if occurrence is not None: stored=occurrence.payload['exercises'][0]
  else:
   plan=db.scalars(select(WorkoutPlan).where(WorkoutPlan.user_id==uid).order_by(WorkoutPlan.week_start.desc())).first()
   stored=plan.payload['sessions'][0]['exercises'][0]
  for key in ('id','sets','authored_prescription','last_set_intensity_technique','warmup_sets'):
   assert stored.get(key)==ex.get(key),(name,key)
  assert len(calibrations)==1,(name,len(calibrations))
  assert calibrations[0].data['load']==100 and calibrations[0].data['unit']=='lb'
  assert len({x.command_id for x in commands})==len(commands)
  record={'calibration_rows':len(calibrations),'original_benchmark':{'load':100,'unit':'lb','method':calibrations[0].data['method']},'unique_command_receipts':len(commands),'source_fields_unchanged':True,
   'workout_rows':[{'set':x.set_index,'kind':x.set_kind,'reps':x.reps,'weight_kg':x.weight,'rpe':x.rpe,'supersedes_prior_receipt':x.supersedes_id is not None,'voided':x.voided_at is not None,'void_source':x.void_source} for x in logs]}
  if name=='eligible':
   assert len(logs)==4
   assert len([x for x in logs if x.set_kind=='warmup'])==1
   assert len([x for x in logs if x.supersedes_id])==1
   assert len([x for x in logs if x.voided_at])==2
   effective=[x for x in logs if x.voided_at is None and x.set_kind!='warmup']
   assert len(effective)==1 and effective[0].reps==12 and abs(effective[0].weight-29.48350405)<1e-10
  elif name=='unsupported':assert len(logs)==0
  else:assert len(logs)==3 and all(x.weight==40 and x.voided_at is None for x in logs)
  result['accounts'][name]=record
Path('docs/evidence/starting-load-2026-10-23/implementation/browser-db-preservation.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: each benchmark stored once; source fields unchanged; exact set/correction retries append once; undo retains rows; historical exposure unchanged; unsupported benchmark never becomes work.')
