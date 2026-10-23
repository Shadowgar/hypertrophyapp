import os,subprocess,signal,time,json,urllib.request
from pathlib import Path
exec(Path('.qualification/cold-performance.py').read_text().split('for scenario in ')[0])
accounts=json.loads(Path('.qualification/performance-accounts.json').read_text());rows=[]
for block,(label,source) in enumerate([('base','/tmp/hypertrophy-starting-load'),('candidate','/tmp/hypertrophy-today-perf'),('candidate','/tmp/hypertrophy-today-perf'),('base','/tmp/hypertrophy-starting-load')],1):
 run=f'abba-{block}-{label}';env={**os.environ,'TODAY_RUN_LABEL':run,'TODAY_SOURCE_ROOT':source,'TODAY_PROCESS_MARKER':uuid.uuid4().hex};ports_free()
 with (root/'.qualification'/f'{run}-server.log').open('w') as log:
  api=subprocess.Popen([str(root/'.qualification/run-python'),'pg',str(root/'.qualification/serve-instrumented.py')],cwd=root,env=env,stdout=log,stderr=log,start_new_session=True)
  try:
   ready(8020,api,env['TODAY_PROCESS_MARKER'],source)
   for key in ['customized-large-unstarted','customized-large-inprogress']:
    a=accounts[key]
    for trial in range(6):
     start=time.perf_counter();req=urllib.request.Request('http://127.0.0.1:8020/workout/today',headers={'Authorization':'Bearer '+a['token'],'X-Perf-Scenario':key})
     with urllib.request.urlopen(req,timeout=60) as r:
      assert r.headers.get('X-Perf-Run')==env['TODAY_PROCESS_MARKER'];payload=json.load(r);status=r.status
     rows.append({'block':block,'source':label,'scenario':key,'trial':trial,'warmup_excluded':trial==0,'ms':(time.perf_counter()-start)*1000,'status':status,'exercises':len(payload['exercises'])})
  finally:stop(api)
 (root/'docs/evidence/today-performance-2026-10-23/customized-abba-api.json').write_text(json.dumps(rows,indent=2));print(run,'finished',flush=True)
