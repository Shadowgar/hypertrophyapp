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
base='06e910896203355c11815d3e586e1dec6d8e0c3e'
out=Path('docs/evidence/today-loading-resume-2026-11-01');out.mkdir(parents=True,exist_ok=True)
samples={label:json.loads(Path('.qualification/'+label+'-measurements.json').read_text()) for label in ('baseline','candidate')}
summary=[]
for mode,delay in [('phase1','none'),('phase2','none'),('flexible','none'),('customized','none'),('phase1','progress'),('phase1','health')]:
 row={'mode':mode,'controlled_delay':delay}
 for label,rs in samples.items():
  selected=[r for r in rs if r['mode']==mode and r['delay']==delay];assert len(selected)==3
  row[label]={k:{'median_ms':round(statistics.median(r[k] for r in selected)),'min_ms':round(min(r[k] for r in selected)),'max_ms':round(max(r[k] for r in selected))} for k in ['visible_ms','soreness_ms','usable_ms']}
  row[label]['request_counts']=[dict(Counter(r['path'] for r in sample['reads'])) for sample in selected]
 summary.append(row)
compact={label:[{k:r[k] for k in ['mode','delay','rep','visible_ms','soreness_ms','usable_ms']}|{'reads':[{'path':q['path'],'elapsed_ms':round(q['end']-q['start']),'status':q['status']} for q in r['reads']]} for r in rows] for label,rows in samples.items()}
(out/'measurements.json').write_text(json.dumps({'base':base,'samples_per_cell':3,'fixture_calendar':'2026-11-01T23:45:00Z for routing and initial-estimate date only; authentication clock actual. Baseline measured on same calendar day before midnight; response exercises and traces verified byte-equal after external fixture injection. Recovery journeys use actual clocks and new Monday fixtures.','method':'Sequential base/candidate production builds, Chromium390x844, real API/SQL, same synthetic occurrence payloads. No cache-reset/cold-process guarantee; no p95 or physical iPhone assertion. Controlled real GET responses held1500ms in browser after actual server response.','summary':summary,'samples':compact},indent=2))
# Compiler covered-file list is read from the unchanged algorithm; no source import/startup.
tree=ast.parse(Path('importers/authored_lineage.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='compiler_sha256');paths=ast.literal_eval(next(n.value for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='paths' for t in n.targets)))
def original(p):return subprocess.check_output(['git','show',base+':'+p])
def fingerprint(blobs):
 h=hashlib.sha256()
 for p,b in blobs:h.update(p.encode()+b'\0'+b+b'\0')
 return h.hexdigest()
assert len(paths)==8
for p in paths:assert Path(p).read_bytes()==original(p)
artifacts=json.loads(Path('docs/evidence/simple-starting-weights-2026-11-01/compiler-parity.json').read_text())['authored_artifacts'];assert len(artifacts)==9
for a in artifacts:assert Path(a['path']).read_bytes()==original(a['path']);assert hashlib.sha256(Path(a['path']).read_bytes()).hexdigest()==a['sha256']
preserved=['apps/web/components/atlas-runner.tsx','apps/web/components/authored-calibration.tsx','apps/web/components/use-atlas-set.ts']
for p in preserved:assert Path(p).read_bytes()==original(p)
(out/'source-parity.json').write_text(json.dumps({'base':base,'compiler_inputs_byte_identical':len(paths),'baseline_compiler_sha256':fingerprint([(p,original(p)) for p in paths]),'candidate_compiler_sha256':fingerprint([(p,Path(p).read_bytes()) for p in paths]),'authored_artifact_files_byte_identical':len(artifacts),'starting_weight_composer_files_byte_identical':[{'path':p,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in preserved]},indent=2))
from app.database import SessionLocal
from app.models import WorkoutOccurrence,WorkoutPlan,WorkoutSetLog
from app.workout_identity import identified_sessions
from app.workout_history import effective_set_logs
def projection(ex):return {k:ex.get(k) for k in ('id','sets','rep_range','authored_prescription','source_lineage')}
result=[]
with SessionLocal() as db:
 for group,file in [('measurements','browser-accounts.json'),('recovery','browser-recovery-accounts.json')]:
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
(out/'database-results.json').write_text(json.dumps(result,indent=2));print('PASS: compiler8/artifact9/composer3 byte parity; all10 synthetic source projections and owned audit receipts preserved.')
