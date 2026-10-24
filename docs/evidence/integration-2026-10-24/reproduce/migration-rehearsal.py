import os,json,hashlib
from pathlib import Path
from sqlalchemy import create_engine,text,inspect
from sqlalchemy.engine import make_url
from alembic.config import Config
from alembic import command
u=make_url(os.environ['DATABASE_URL'])
assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'integration_1024','m2a_test')
e=create_engine(u)
with e.connect() as c:
 assert tuple(c.execute(text('select current_database(),current_user')).one())==('integration_1024','m2a_test')
 existing=inspect(c).get_table_names()
 assert not existing or (c.execute(text('select version_num from alembic_version')).scalar()=='0024_merge_authored_customized' and c.execute(text('select count(*) from users')).scalar()==0)
cfg=Config('apps/api/alembic.ini');cfg.set_main_option('script_location',str(Path('apps/api/alembic').resolve()))
if not existing: command.upgrade(cfg,'0024_merge_authored_customized')
# Pre-preference existing account and retained historical rows, inserted only in this new DB.
with e.begin() as c:
 c.execute(text("INSERT INTO users (id,email,password_hash,name,days_available,equipment_profile,movement_restrictions,selected_program_id,onboarding_answers,created_at) VALUES ('integration-preserved','integration-preserved@example.com','unused','Synthetic preservation',3,'[\"cable\"]','[]','pure_bodybuilding_phase_1_full_body','{\"synthetic\": true}',CURRENT_TIMESTAMP)"))
 c.execute(text("INSERT INTO workout_set_logs (id,user_id,workout_id,exercise_id,primary_exercise_id,set_index,reps,weight,set_kind,created_at) VALUES ('integration-set','integration-preserved','synthetic-preserved','cross_body_lat_pull_around','cross_body_lat_pull_around',1,11,30,'work',CURRENT_TIMESTAMP)"))
def snap(tables=None):
 with e.connect() as c:
  tables=tables or sorted(t for t in inspect(c).get_table_names() if t!='alembic_version')
  result={}
  for t in tables:
   rows=sorted(json.dumps(x[0],sort_keys=True,default=str) for x in c.execute(text('SELECT row_to_json(t) FROM "'+t+'" t')))
   # Encode as explicit record with algorithm; no checksum masquerades as a token field.
   result[t]={'rows':len(rows),'content_digest':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
  return result
before24=snap();command.upgrade(cfg,'0025_interface_preferences');after25=snap(list(before24));assert before24==after25
with e.begin() as c:
 assert c.execute(text('select count(*) from user_interface_preferences')).scalar()==0
 c.execute(text("INSERT INTO user_interface_preferences VALUES ('integration-preserved','classic','dark','lb',1)"))
before25=snap();command.upgrade(cfg,'head');after26=snap(list(before25));assert before25==after26
with e.connect() as c:
 assert c.execute(text('select version_num from alembic_version')).scalar()=='0026_initial_calibration'
 assert c.execute(text('select count(*) from authored_initial_calibrations')).scalar()==0
result={'target':'integration_1024 / m2a_test on loopback 55418, tmpfs','0024_to_0025_preserved':before24==after25,'0025_to_0026_preserved':before25==after26,'before_0025':before24,'before_0026':before25,'after_0026':snap(),'new_preferences_backfilled':False,'new_calibrations_backfilled':False}
Path('.qualification/migration-preservation.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: additive full chain, existing synthetic account/history retained, no preference/calibration backfill')
