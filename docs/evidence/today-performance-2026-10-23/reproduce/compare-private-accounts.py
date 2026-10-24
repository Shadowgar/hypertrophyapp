import os,json,hashlib
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL']);assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'today_performance_1023','m2a_test')
e=create_engine(u);accounts=json.loads(Path('.qualification/performance-accounts.json').read_text());ids=[a['user_id'] for k,a in accounts.items() if '-first-' not in k]
with e.connect() as c:
 assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_performance_1023','m2a_test')
 rows=[r[0] for r in c.execute(text('SELECT row_to_json(t) FROM users t WHERE id = ANY(:ids)'),{'ids':ids})]
after={'rows':len(rows),'sha256':hashlib.sha256(json.dumps(sorted(rows,key=lambda r:json.dumps(r,sort_keys=True)),sort_keys=True,default=str).encode()).hexdigest()}
before=json.loads(Path('.qualification/baseline-scoped-all-tables-private.json').read_text())['users'];same=after==before
p=Path('docs/evidence/today-performance-2026-10-23/preservation.json');d=json.loads(p.read_text());d['ordinary_accounts_unchanged_private_comparison']=same;p.write_text(json.dumps(d,indent=2));print('Eight ordinary account rows privately unchanged:',same);assert same
