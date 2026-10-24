import os,json,hashlib,urllib.request
from pathlib import Path
from sqlalchemy import create_engine,text,inspect
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL']);assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'today_performance_1023','m2a_test')
e=create_engine(u)
with e.connect() as c:assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_performance_1023','m2a_test')
accounts=json.loads(Path('.qualification/performance-accounts.json').read_text());label=os.environ.get('TODAY_RUN_LABEL','baseline');payloads={};database={}
for key,a in accounts.items():
 if '-first-' in key:continue
 payloads[key]={}
 for endpoint in ['/workout/today','/workout/'+a['session']['workout_occurrence_id']+'/progress','/workout/'+a['session']['workout_occurrence_id']+'/summary']:
  req=urllib.request.Request('http://127.0.0.1:8020'+endpoint,headers={'Authorization':'Bearer '+a['token']})
  with urllib.request.urlopen(req,timeout=120) as r:payloads[key][endpoint]=json.load(r)
ids=[a['user_id'] for key,a in accounts.items() if '-first-' not in key]
with e.connect() as c:
 for table in ['workout_plans', 'workout_occurrences', 'workout_set_logs', 'workout_log_commands', 'workout_session_states', 'authored_initial_calibrations', 'user_interface_preferences', 'authored_load_states', 'exercise_states', 'customized_equipment_profiles']:
  cols={x['name'] for x in inspect(e).get_columns(table)};field='user_id' if 'user_id' in cols else 'subject' if 'subject' in cols else 'id' if table=='users' else None
  if not field:continue
  rows=[r[0] for r in c.execute(text(f'SELECT row_to_json(t) FROM "{table}" t WHERE "{field}" = ANY(:ids)'),{'ids':ids})]
  database[table]={'rows':len(rows),'sha256':hashlib.sha256(json.dumps(sorted(rows,key=lambda r:json.dumps(r,sort_keys=True)),sort_keys=True,default=str).encode()).hexdigest()}
Path('.qualification/'+label+'-payloads.json').write_text(json.dumps(payloads,sort_keys=True))
Path('docs/evidence/today-performance-2026-10-23/'+label+'-database.json').write_text(json.dumps({'scope':{'account_count':len(ids),'accounts':[k for k in accounts if '-first-' not in k],'selection':'Only rows owned by the eight ordinary benchmark accounts; fresh first-use accounts excluded','tables':'Training plans, occurrences, receipts, commands, state, calibration, inventory and presentation preferences; no auth/reset-token tables'},'tables':database},indent=2))
print('Captured synthetic endpoint payloads privately; scoped database hashes publicly')
