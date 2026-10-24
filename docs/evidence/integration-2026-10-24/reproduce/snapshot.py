import os,json,hashlib,sys
from pathlib import Path
from sqlalchemy import create_engine,text,inspect
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL'])
assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'integration_1024','m2a_test')
name=sys.argv[1]
assert name in ('integration_1024','integration_1024_restore')
e=create_engine(u.set(database=name))
with e.connect() as c:
 assert tuple(c.execute(text('select current_database(),current_user')).one())==(name,'m2a_test')
 result={}
 for table in sorted(inspect(c).get_table_names()):
  rows=sorted(json.dumps(x[0],sort_keys=True,default=str) for x in c.execute(text('SELECT row_to_json(t) FROM "'+table+'" t')))
  result[table]={'rows':len(rows),'content_digest':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
 if name=='integration_1024':
  before=json.loads(Path('.qualification/migration-preservation.json').read_text())['before_0026']
  for table,key,value in [('users','id','integration-preserved'),('workout_set_logs','id','integration-set'),('user_interface_preferences','user_id','integration-preserved')]:
   rows=sorted(json.dumps(x[0],sort_keys=True,default=str) for x in c.execute(text('SELECT row_to_json(t) FROM "'+table+'" t WHERE '+key+'=:v'),{'v':value}))
   assert len(rows)==before[table]['rows'] and hashlib.sha256('\n'.join(rows).encode()).hexdigest()==before[table]['content_digest']
  print('Original migration-seeded account, preference and history rows still byte-equivalent')
Path('.qualification/'+name+'-snapshot.json').write_text(json.dumps(result,indent=2)+'\n')
print(name,'tables',len(result),'rows',sum(x['rows'] for x in result.values()))
