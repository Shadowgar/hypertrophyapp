import os,time,subprocess,urllib.request,json,signal,socket,uuid
from pathlib import Path
root=Path('/tmp/hypertrophy-today-perf');label=os.environ.get('TODAY_RUN_LABEL','baseline');source=os.environ.get('TODAY_SOURCE_ROOT','/tmp/hypertrophy-starting-load');results=[]
def ports_free():
 for port in [8020,3020]:
  with socket.socket() as sock:
   if sock.connect_ex(('127.0.0.1',port))==0:raise RuntimeError(f'Benchmark port {port} already owned; refuse to reuse')
def listener(port,process,source):
 inodes=set()
 for line in Path('/proc/net/tcp').read_text().splitlines()[1:]:
  fields=line.split()
  if fields[1].split(':')[-1]==f'{port:04X}' and fields[3]=='0A':inodes.add(fields[9])
 owners=[]
 for entry in Path('/proc').iterdir():
  if not entry.name.isdigit():continue
  try:
   if os.getpgid(int(entry.name))!=process.pid:continue
   for fd in (entry/'fd').iterdir():
    target=os.readlink(fd)
    if target.startswith('socket:[') and target[8:-1] in inodes:
     cwd=os.readlink(entry/'cwd');assert cwd==source+'/apps/web',(entry.name,cwd,source)
     owners.append(int(entry.name));break
  except (ProcessLookupError,FileNotFoundError,PermissionError):continue
 assert owners,'No owned frontend process group member holds listening socket'
 return owners
def ready(port,process,marker,source):
 for n in range(100):
  if process.poll() is not None:raise RuntimeError(f'Owned process exited before port {port} ready')
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}'+('/health' if port==8020 else '/api/health'),timeout=1) as r:
    if r.status==200:
     assert r.headers.get('X-Perf-Run')==marker,'Response is not from owned API process'
     time.sleep(.15)
     if process.poll() is not None:raise RuntimeError('Owned process exited after ready response')
     if port==3020:
      owners=listener(port,process,source);build=(Path(source)/'apps/web/.next/BUILD_ID').read_text().strip()
      with urllib.request.urlopen(f'http://127.0.0.1:{port}/',timeout=2) as page:
       html=page.read().decode();assert build in html,'Build ID absent from live frontend response'
      row={'run':env['TODAY_RUN_LABEL'],'api_process':api.pid,'marker':marker,'api_proxy_confirmed':True,'web_process_group':process.pid,'listening_pids':owners,'web_cwd':source+'/apps/web','build_id':build}
      with (root/'.qualification/process-ownership.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
     return
  except (urllib.error.URLError,TimeoutError):time.sleep(.1)
 raise RuntimeError('Owned qualification process failed to start')
def stop(p):
 if p.poll() is None:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
for scenario in os.environ.get('TODAY_COLD_SCENARIOS','authored-small-unstarted,authored-large-inprogress,customized-small-inprogress,customized-large-inprogress').split(','):
 for trial in range(1,int(os.environ.get('TODAY_COLD_TRIALS','3'))+1):
  unique=f'{label}-cold-{scenario}-{trial}';env={**os.environ,'TODAY_SOURCE_ROOT':source,'TODAY_RUN_LABEL':unique,'TODAY_SCENARIOS':scenario,'TODAY_TRIALS':'1','TODAY_SERVER_STATE':'process/browser-cold','TODAY_PROCESS_MARKER':uuid.uuid4().hex}
  ports_free()
  with (root/'.qualification'/f'{unique}-server.log').open('w') as log:
   api=subprocess.Popen([str(root/'.qualification/run-python'),'pg',str(root/'.qualification/serve-instrumented.py')],cwd=root,env=env,stdout=log,stderr=log,start_new_session=True)
   web=None
   try:
    ready(8020,api,env['TODAY_PROCESS_MARKER'],source);web=subprocess.Popen([source+'/apps/web/node_modules/.bin/next','start','-H','127.0.0.1','-p','3020'],cwd=source+'/apps/web',env=env,stdout=log,stderr=log,start_new_session=True);ready(3020,web,env['TODAY_PROCESS_MARKER'],source)
    subprocess.run(['node',str(root/'.qualification/browser-performance.cjs')],cwd=root,env=env,stdout=log,stderr=log,check=True)
    data=json.loads((root/f'docs/evidence/today-performance-2026-10-23/{unique}-browser.json').read_text());results.extend(data)
   finally:
    if web:stop(web)
    stop(api)
  (root/f'docs/evidence/today-performance-2026-10-23/{label}-cold-browser.json').write_text(json.dumps(results,indent=2));print(unique,round(results[-1].get('usable_ms') or 0),flush=True)
