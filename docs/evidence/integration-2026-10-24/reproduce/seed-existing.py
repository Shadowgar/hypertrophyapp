import os,json,secrets
from pathlib import Path
from uuid import uuid4
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL'])
assert (u.host,u.port,u.database,u.username)==('127.0.0.1',55418,'integration_1024','m2a_test')
with create_engine(u).connect() as c:assert tuple(c.execute(text('select current_database(),current_user')).one())==('integration_1024','m2a_test')
from app.database import SessionLocal
from app.models import User,WorkoutSetLog
from app.security import hash_password,create_access_token
uid=str(uuid4());secret=secrets.token_urlsafe(24);email='existing-'+uid+'@example.com'
with SessionLocal() as db:
 db.add(User(id=uid,email=email,password_hash=hash_password(secret),name='Synthetic existing account',age=38,weight=83,days_available=4,selected_program_id='pure_bodybuilding_phase_2_full_body',equipment_profile=['cable'],training_location='gym',movement_restrictions=['overhead'],session_time_budget_minutes=55,near_failure_tolerance='low',scheduling_timezone='UTC',onboarding_answers={'preserve':'synthetic-consent-document'}));db.flush()
 db.add(WorkoutSetLog(user_id=uid,workout_id='synthetic-legacy-history',primary_exercise_id='cross_body_lat_pull_around',exercise_id='cross_body_lat_pull_around',set_index=1,reps=12,weight=20));db.commit()
a={'token':create_access_token(uid),'email':email,'password':secret,'user_id':uid}
Path('.qualification/existing-account.json').write_text(json.dumps(a))
print('Created synthetic existing account, unrelated settings and retained history; private credentials omitted')
