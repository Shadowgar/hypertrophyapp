import os,subprocess,signal
from pathlib import Path
exec(Path('.qualification/cold-performance.py').read_text().split('for scenario in ')[0])
label=os.environ.get('TODAY_RUN_LABEL','baseline');source=os.environ.get('TODAY_SOURCE_ROOT','/tmp/hypertrophy-starting-load');env={**os.environ,'TODAY_SOURCE_ROOT':source,'TODAY_RUN_LABEL':label,'TODAY_PROCESS_MARKER':uuid.uuid4().hex}
ports_free()
with (root/'.qualification'/f'{label}-warm-server.log').open('w') as log:
 api=subprocess.Popen([str(root/'.qualification/run-python'),'pg',str(root/'.qualification/serve-instrumented.py')],cwd=root,env=env,stdout=log,stderr=log,start_new_session=True);web=None
 try:
  ready(8020,api,env['TODAY_PROCESS_MARKER'],source);web=subprocess.Popen([source+'/apps/web/node_modules/.bin/next','start','-H','127.0.0.1','-p','3020'],cwd=source+'/apps/web',env=env,stdout=log,stderr=log,start_new_session=True);ready(3020,web,env['TODAY_PROCESS_MARKER'],source)
  first=[]
  for n in range(3):
   unique=f'{label}-first-browser-{n}'
   subprocess.run(['node','.qualification/browser-performance.cjs'],cwd=root,env={**env,'TODAY_RUN_LABEL':unique,'TODAY_SCENARIOS':f'authored-first-browser-{label}-{n}','TODAY_TRIALS':'1'},stdout=log,stderr=log,check=True)
   first.extend(json.loads((root/f'docs/evidence/today-performance-2026-10-23/{unique}-browser.json').read_text()))
  (root/f'docs/evidence/today-performance-2026-10-23/{label}-first-browser.json').write_text(json.dumps(first,indent=2))
 finally:
  if web:stop(web)
  stop(api)
print(label,'warm matrix finished',flush=True)
