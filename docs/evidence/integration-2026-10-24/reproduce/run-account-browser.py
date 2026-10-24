import os,subprocess,signal,socket,time,json,urllib.request
from pathlib import Path
root=Path.cwd();log=(root/'.qualification/browser-server.log').open('w');api=web=None
for port in (8020,3020):
 with socket.socket() as s: assert s.connect_ex(('127.0.0.1',port))!=0, 'qualification port occupied'
env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/home/rocco','NEXT_TELEMETRY_DISABLED':'1'}
def ready(port,proc):
 for _ in range(240):
  assert proc.poll() is None, 'owned service exited'
  try:
   with urllib.request.urlopen('http://127.0.0.1:'+str(port)+('/health' if port==8020 else '/')) as r:
    if port==8020: assert r.headers['X-Integration-Qualification']=='integration-1024'
    return
  except OSError:time.sleep(.25)
 raise AssertionError('server readiness deadline')
try:
 api=subprocess.Popen([str(root/'.qualification/run-browser-python'),'pg','.qualification/serve.py'],cwd=root,env=env,stdout=log,stderr=log,start_new_session=True);ready(8020,api)
 web=subprocess.Popen([str(root/'apps/web/node_modules/.bin/next'),'start','-H','127.0.0.1','-p','3020'],cwd=root/'apps/web',env=env,stdout=log,stderr=log,start_new_session=True);ready(3020,web)
 info={'build':(root/'apps/web/.next/BUILD_ID').read_text().strip(),'api':'127.0.0.1:8020','web':'127.0.0.1:3020','database':'integration_1024','dev_cleanup_enabled':False}
 Path('.qualification/journeys/build.json').write_text(json.dumps(info,indent=2))
 for script in ['account-journey.cjs']:
  print('Running '+script,flush=True);subprocess.run(['node','.qualification/'+script],cwd=root,env=env,check=True)
 for script in []:
  subprocess.run([str(root/'.qualification/run-browser-python'),'pg','.qualification/'+script],cwd=root,env=env,check=True)
finally:
 for p in [web,api]:
  if p and p.poll() is None:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
 log.close()
