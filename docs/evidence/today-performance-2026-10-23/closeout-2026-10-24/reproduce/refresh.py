import os,json,base64
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL'])
assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'today_performance_1023','m2a_test')
e=create_engine(u)
with e.connect() as c:assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_performance_1023','m2a_test')
e.dispose()
from app.database import SessionLocal
from app.models import User
from app.security import create_access_token
original=json.loads(Path('.qualification/performance-accounts.json').read_text());out={}
with SessionLocal() as db:
 for key,a in original.items():
  if key not in ('authored-large-unstarted','authored-large-inprogress','customized-small-unstarted','customized-small-inprogress'):continue
  user=db.get(User,a['user_id']);assert user is not None
  out[key]={**a,'token':create_access_token(user.id,user.password_hash)}
Path('.qualification/closeout/accounts.json').write_text(json.dumps(out));print('Verified disposable target; refreshed four private synthetic bearer tokens without database writes')
