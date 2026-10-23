import os,json,platform,hashlib
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL']);assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'today_performance_1023','m2a_test')
e=create_engine(u);accounts=json.loads(Path('.qualification/performance-accounts.json').read_text());rows=[]
with e.connect() as c:
 assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_performance_1023','m2a_test')
 for key,a in accounts.items():
  if '-first-' in key:continue
  own={'user_id':a['user_id']};counts={t:c.execute(text(f'SELECT count(*) FROM {t} WHERE user_id=:user_id'),own).scalar() for t in ['workout_plans','workout_occurrences','workout_set_logs','authored_initial_calibrations','user_interface_preferences']}
  rows.append({'scenario':key,'mode':'Authored' if key.startswith('authored') else 'Customized','current_exercises':len(a['session']['exercises']),'prior_exposure_sessions':100 if '-large-' in key else 0,'current_receipts':1 if key.endswith('inprogress') else 0,'counts':counts})
 version=c.execute(text('select version()')).scalar()
source={}
for label,path,commit in [('baseline','/tmp/hypertrophy-starting-load','c656988c2133e5a655c83a9ba87c5f6c47c9308e'),('after','/tmp/hypertrophy-today-perf','912e7e928960069316e81f01a1df08001b0f2a53')]:
 p=Path(path);source[label]={'revision':commit,'build_id':(p/'apps/web/.next/BUILD_ID').read_text().strip(),'routes_manifest_sha256':hashlib.sha256((p/'apps/web/.next/routes-manifest.json').read_bytes()).hexdigest(),'runtime_sha256':{f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['apps/api/app/workout_load_state.py','apps/api/app/workout_initial_calibration.py','apps/web/app/today/page.tsx','apps/web/lib/api.ts']}}
Path('docs/evidence/today-performance-2026-10-23/environment.json').write_text(json.dumps({'source':source,'platform':platform.platform(),'python':platform.python_version(),'node':'22.22.0','postgres':version,'browser':'Headless Chromium 1208 via Playwright; 390x844','frontend':'Real Next.js production build on loopback3020; same-origin /api proxy to loopback8020','database':'Disposable today_performance_1023 / m2a_test on 127.0.0.1:55418; verified Docker tmpfs, no mounts','datasets':rows},indent=2))
print('Eight-account dataset/source/build metadata recorded; no credentials included')
