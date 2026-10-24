import json,time,urllib.request,os
from pathlib import Path
accounts=json.loads(Path('.qualification/performance-accounts.json').read_text());rows=[]
for key,a in accounts.items():
 if '-first-' in key:continue
 for i in range(int(os.environ.get('TODAY_TRIALS','5'))):
  t=time.perf_counter();req=urllib.request.Request('http://127.0.0.1:8020/workout/today',headers={'Authorization':'Bearer '+a['token'],'X-Perf-Scenario':key})
  try:
   with urllib.request.urlopen(req,timeout=120) as r:payload=json.load(r);status=r.status
   row={'scenario':key,'trial':i+1,'ms':(time.perf_counter()-t)*1000,'status':status,'exercise_count':len(payload.get('exercises',[])),'resume':payload.get('resume')}
  except Exception as e:row={'scenario':key,'trial':i+1,'error':str(e)}
  rows.append(row);print(json.dumps(row),flush=True)
Path('docs/evidence/today-performance-2026-10-23/'+os.environ.get('TODAY_RUN_LABEL','baseline')+'-api.json').write_text(json.dumps(rows,indent=2))
