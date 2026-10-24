import os,subprocess,json
from pathlib import Path
root=Path('/tmp/hypertrophy-today-perf');rows=[]
for block,(label,source) in enumerate([('base','/tmp/hypertrophy-starting-load'),('candidate','/tmp/hypertrophy-today-perf'),('candidate','/tmp/hypertrophy-today-perf'),('base','/tmp/hypertrophy-starting-load')],1):
 run=f'cold-abba-{block}-{label}';env={**os.environ,'TODAY_RUN_LABEL':run,'TODAY_SOURCE_ROOT':source,'TODAY_COLD_SCENARIOS':'customized-small-inprogress','TODAY_COLD_TRIALS':'1'}
 subprocess.run(['python3','.qualification/cold-performance.py'],cwd=root,env=env,check=True)
 data=json.loads((root/f'docs/evidence/today-performance-2026-10-23/{run}-cold-browser.json').read_text());rows.extend(dict(r,block=block,source=label) for r in data)
 (root/'docs/evidence/today-performance-2026-10-23/customized-cold-abba.json').write_text(json.dumps(rows,indent=2))
