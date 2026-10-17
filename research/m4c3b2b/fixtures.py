"""Disposable rows only; no production fixtures, migrations or activation."""
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
import json,time
from types import SimpleNamespace
from uuid import uuid4
from sqlalchemy import text
from app.models import User
from app.customized_postgres import PostgresUnit,PostgresProposalStore,PostgresSessionGate
from app.customized_source_calendar import SourceCalendarPort
from app.customized_staging_schedule import ReadOnlyCalendarAdapter
from app.customized_lifecycle import LifecycleService
from research.m4c3a.fixtures import demo_server,demo_context


def build_system(engine):
    now=demo_context().planning_instant;unit=PostgresUnit(engine);gate=PostgresSessionGate(unit,clock=lambda:now)
    users={key:uuid4().hex for key in ('a','b')};credentials={key:'Bearer synthetic-'+uuid4().hex for key in users}
    for key,subject in users.items():
        with engine.begin() as conn:
            conn.execute(User.__table__.insert().values(id=subject,email=subject+'@synthetic.invalid',
                name=subject,password_hash='synthetic-credential'))
            conn.execute(text("""INSERT INTO customized_candidate_sessions(session_id,subject,credential_fingerprint,
                credential_digest,revision,entitlement_reference,scopes,valid_from,expires_at,revoked)
                VALUES (:id,:s,:f,:d,1,'explicit-disposable-grant',CAST(:scopes AS jsonb),:start,:end,false)"""),
                dict(id=str(uuid4()),s=subject,f=sha256(credentials[key].encode()).hexdigest(),
                    d=sha256(b'synthetic-credential').hexdigest(),scopes=json.dumps(['customized:preview','customized:proposal']),
                    start=now-timedelta(days=1),end=now+timedelta(days=1)))
    actors={key:gate.bind(SimpleNamespace(id=subject),credentials[key]) for key,subject in users.items()}
    source=SourceCalendarPort(unit);schedule=ReadOnlyCalendarAdapter(source,context=demo_context())
    store=PostgresProposalStore(unit,gate)
    service=LifecycleService(server=replace(demo_server(),allowed_subjects=tuple(users.values())),store=store,
        schedule=schedule,clock=lambda:now,comparison_pairs=(('shorter-current','longer-current'),('longer-current','shorter-current')),
        authorize_actor=gate.authorize)
    def change(kind,subject):
        # Exactly the same User-first ordering as #83. Separate physical connection.
        with engine.begin() as conn:
            conn.execute(text("SET LOCAL application_name='c3b2b_competing_writer'"))
            conn.execute(text('SELECT id FROM users WHERE id=:s FOR UPDATE'),dict(s=subject)).one()
            if kind=='reset':
                conn.execute(text('UPDATE users SET password_hash=:p WHERE id=:s'),dict(s=subject,p='reset-'+uuid4().hex))
                conn.execute(text('UPDATE customized_candidate_sessions SET revoked=true,revision=revision+1 WHERE subject=:s'),dict(s=subject))
            elif kind=='revoke':conn.execute(text('UPDATE customized_candidate_sessions SET revoked=true,revision=revision+1 WHERE subject=:s'),dict(s=subject))
            elif kind=='rotate':conn.execute(text('UPDATE customized_candidate_sessions SET credential_fingerprint=:f,revision=revision+1 WHERE subject=:s'),dict(s=subject,f=uuid4().hex+uuid4().hex))
            elif kind=='calendar':
                # A dated plan change, not a custom synthetic envelope revision.
                from app.models import WorkoutPlan
                conn.execute(WorkoutPlan.__table__.insert().values(id=uuid4().hex,user_id=subject,
                    week_start=now.date(),placement_revision=1,schedule_timezone='America/New_York',split='full_body',phase='synthetic',
                    payload={'program_template_id':'pure_bodybuilding_phase_1_full_body','schedule':{'mode':'selected_dates_v1'},'sessions':[]}))
            else:raise ValueError(kind)
    def wait_for_lock(subject):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            with engine.connect() as conn:
                waiting=conn.execute(text("""SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()
                    AND application_name='c3b2b_competing_writer' AND wait_event_type='Lock'""")).scalar()
                if waiting:return True
            time.sleep(.01)
        return False
    return SimpleNamespace(engine=engine,unit=unit,gate=gate,store=store,service=service,source=source,actors=actors,
        users=users,credentials=credentials,change=change,wait_for_lock=wait_for_lock)
