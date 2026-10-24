import os,json,hashlib
from pathlib import Path
from sqlalchemy import create_engine,text,select
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL']);assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'integration_1024','m2a_test')
e=create_engine(u)
with e.connect() as c:assert tuple(c.execute(text('select current_database(),current_user')).one())==('integration_1024','m2a_test')
metadata=json.loads(Path('docs/evidence/today-performance-2026-10-23/environment.json').read_text())['source']['after']
for relative,expected in metadata['runtime_sha256'].items():assert hashlib.sha256(Path(relative).read_bytes()).hexdigest()==expected
from app.database import SessionLocal
from app.models import WorkoutSetLog,WorkoutLogCommand,WorkoutOccurrence,WorkoutPlan
from app.workout_identity import identified_sessions
account=json.loads(Path('.qualification/customized-journey-account.json').read_text());uid=account['user_id'];session=account['session']
with SessionLocal() as db:
 logs=list(db.scalars(select(WorkoutSetLog).where(WorkoutSetLog.user_id==uid)));commands=list(db.scalars(select(WorkoutLogCommand).where(WorkoutLogCommand.user_id==uid)))
 assert len(logs)==3 and len(commands)==4
 assert len([c for c in commands if not c.response.get('operation')])==2
 assert sorted(c.response['operation'] for c in commands if c.response.get('operation'))==['correct','undo']
 effective=[r for r in logs if r.voided_at is None];assert len(effective)==1 and effective[0].set_index==1 and effective[0].reps==9
 first=next(r for r in logs if r.set_index==1 and not r.supersedes_id);second=next(r for r in logs if r.set_index==2);replacement=next(r for r in logs if r.supersedes_id)
 assert first.reps==8 and second.reps==8 and replacement.reps==9
 assert replacement.supersedes_id==first.id and first.voided_at and second.voided_at
 assert all(abs(r.weight-13.6077711)<1e-10 for r in logs)
 occurrence=db.get(WorkoutOccurrence,session['workout_occurrence_id']);plan=db.get(WorkoutPlan,occurrence.plan_id)
 assert occurrence.payload==identified_sessions(plan)[occurrence.session_slot]
 report={'application_revision':metadata['revision'],'stored_receipts':3,'effective_receipts':1,'unique_log_commands':2,'unique_history_commands':2,'total_retained_commands':4,'original_set_actuals_retained':True,'correction_appended_once':True,'second_set_undo_retained_record':True,'canonical_weight_kg':13.6077711,'performed_snapshot_exactly_matches_identified_accepted_plan':True,'effective_first_set_repetitions':9,'command_ledger':[{'command_id':c.command_id,'operation':c.response.get('operation','log_set')} for c in commands],'retained_receipt_lineage':[{'id':r.id,'command_id':r.command_id,'set_index':r.set_index,'reps':r.reps,'weight_kg':r.weight,'voided':r.voided_at is not None,'void_source':r.void_source,'supersedes_id':r.supersedes_id} for r in logs]}
Path('.qualification/journeys/customized-db-preservation.json').write_text(json.dumps(report,indent=2));print('PASS Customized retained receipt lineage, canonical actuals and exact accepted snapshot')
