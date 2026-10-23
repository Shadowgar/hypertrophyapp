import os,subprocess,signal
from pathlib import Path
exec(Path('.qualification/cold-performance.py').read_text().split('for scenario in ')[0])
label=os.environ.get('TODAY_RUN_LABEL','baseline');source=os.environ.get('TODAY_SOURCE_ROOT','/tmp/hypertrophy-starting-load');env={**os.environ,'TODAY_SOURCE_ROOT':source,'TODAY_RUN_LABEL':label,'TODAY_PROCESS_MARKER':uuid.uuid4().hex}
ports_free()
with (root/'.qualification'/f'{label}-warm-server.log').open('w') as log:
 api=subprocess.Popen([str(root/'.qualification/run-python'),'pg',str(root/'.qualification/serve-instrumented.py')],cwd=root,env=env,stdout=log,stderr=log,start_new_session=True);web=None
 try:
  ready(8020,api,env['TODAY_PROCESS_MARKER'],source);web=subprocess.Popen([source+'/apps/web/node_modules/.bin/next','start','-H','127.0.0.1','-p','3020'],cwd=source+'/apps/web',env=env,stdout=log,stderr=log,start_new_session=True);ready(3020,web,env['TODAY_PROCESS_MARKER'],source)
  subprocess.run([str(root/'.qualification/run-python'),'pg','.qualification/seed-customized-journey.py'],cwd=root,env=env,stdout=log,stderr=log,check=True)
  subprocess.run(['node','.qualification/customized-runtime.cjs'],cwd=root,env=env,stdout=log,stderr=log,check=True)
 finally:
  if web:stop(web)
  stop(api)
