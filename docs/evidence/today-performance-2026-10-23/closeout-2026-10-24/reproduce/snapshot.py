import os,json,hashlib,sys
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL']);assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'today_performance_1023','m2a_test')
e=create_engine(u)
with e.connect() as c:
 assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_performance_1023','m2a_test')
 assert c.execute(text('select version_num from alembic_version')).scalar()=='0026_initial_calibration'
 accounts=json.loads(Path('.qualification/performance-accounts.json').read_text());ids=[a['user_id'] for k,a in accounts.items() if '-first-' not in k];assert len(ids)==8
 output={}
 for table in ['users','workout_plans','workout_occurrences','workout_set_logs','workout_log_commands','workout_session_states','authored_initial_calibrations','user_interface_preferences','authored_load_states','exercise_states','customized_equipment_profiles']:
  field='id' if table=='users' else 'user_id'
  rows=[r[0] for r in c.execute(text(f'SELECT row_to_json(t) FROM "{table}" t WHERE "{field}" = ANY(:ids)'),{'ids':ids})]
  output[table]={'rows':len(rows),'sha256':hashlib.sha256(json.dumps(sorted(rows,key=lambda r:json.dumps(r,sort_keys=True)),sort_keys=True,default=str).encode()).hexdigest()}
Path('.qualification/closeout/db-'+sys.argv[1]+'.json').write_text(json.dumps(output))
print('Verified disposable schema0026 and privately fingerprinted eight synthetic accounts / eleven tables')
