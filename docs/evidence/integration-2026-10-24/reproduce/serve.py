import os
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL'])
assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'integration_1024','m2a_test')
with create_engine(u).connect() as c:
 assert tuple(c.execute(text('select current_database(),current_user')).one())==('integration_1024','m2a_test')
 assert c.execute(text('select version_num from alembic_version')).scalar()=='0026_initial_calibration'
from app.main import app
@app.middleware('http')
async def qualification_marker(request,call_next):
 response=await call_next(request)
 response.headers['X-Integration-Qualification']='integration-1024'
 return response
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=8020,log_level='warning')
