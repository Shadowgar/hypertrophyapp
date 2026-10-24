"""Fresh disposable replay only; refuses any existing account/manifest."""
import os,json,subprocess,sys
from pathlib import Path
from datetime import date
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL'])
assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'today_performance_1023','m2a_test')
e=create_engine(u)
with e.connect() as c:
 assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_performance_1023','m2a_test')
 assert c.execute(text('select count(*) from users')).scalar()==0,'Fresh disposable replay database required; no reset is permitted'
assert date.today().weekday()==4,'Recorded fixture is Friday; explicitly reconcile replay clocks before seeding another day'
q=Path('.qualification');assert not (q/'performance-accounts.json').exists(),'Do not overwrite an existing private manifest'
(q/'performance-accounts.json').write_text('{}')
for name in ['seed-authored-final.py','seed-customized.py','seed-customized-large.py']:
 subprocess.run([sys.executable,str(q/name)],check=True)
# Reuse the same individually exercised guarded account helper.
exec((q/'seed-authored-final.py').read_text().split('for size,count in')[0])
accounts=json.loads((q/'performance-accounts.json').read_text())
for n in range(6):accounts[f'authored-first-{n}']=newuser('first')
(q/'performance-accounts.json').write_text(json.dumps(accounts))
subprocess.run([sys.executable,str(q/'seed-first-browser.py')],check=True)
print('Fresh owned replay fixtures created; private tokens remain in ignored manifest')
