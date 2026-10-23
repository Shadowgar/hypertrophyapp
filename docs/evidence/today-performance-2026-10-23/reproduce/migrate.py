import os
from pathlib import Path
from sqlalchemy import create_engine,text,inspect
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL']);assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'today_performance_1023','m2a_test')
e=create_engine(u)
with e.connect() as c:assert tuple(c.execute(text('select current_database(),current_user')).one())==('today_performance_1023','m2a_test')
assert inspect(e).get_table_names()==[]
from alembic.config import Config
from alembic import command
cfg=Config('/tmp/hypertrophy-starting-load/apps/api/alembic.ini');cfg.set_main_option('script_location','/tmp/hypertrophy-starting-load/apps/api/alembic');command.upgrade(cfg,'head')
print('Migrated verified empty disposable today_performance_1023 to head')
