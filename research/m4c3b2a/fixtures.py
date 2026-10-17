"""Disposable account/session/calendar fixtures, never a production adapter.

Only an exclusively created SQLite file under an explicit /tmp root receives a
create-only copy of the existing User table. No metadata-wide DDL, reset, delete,
ordinary app database connection, migration or network is used.
"""
from dataclasses import dataclass,replace
from datetime import timedelta
import hashlib
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine,text,select,func
from sqlalchemy.orm import Session

from app.models import User
from app.security import create_access_token
from app.customized_lifecycle import LifecycleService
from app.customized_staging_auth import SessionGrant,StagingAccessGate
from app.customized_staging_schedule import CalendarWindow,ReadOnlyCalendarAdapter,SOURCE_CONTRACT
from app.customized_staging_http import create_staging_app
from app.deps import get_db
from research.m4c3a.fixtures import demo_server,demo_context
from research.m4c3b1.demo import proposed_request
from research.m4c3b1.store import DisposableProposalStore


class DisposableAccounts:
    def __init__(self,root):
        root=Path(root).resolve();path=root/'accounts.sqlite'
        if not root.is_relative_to(Path('/tmp')) or root==Path('/tmp') or path.is_symlink():
            raise ValueError('Explicit disposable account root required')
        # Never infer an existing file to be disposable or overwrite it.
        with path.open('xb'):pass
        path.chmod(0o600)
        self.engine=create_engine('sqlite:///'+str(path),connect_args={'check_same_thread':False})
        with self.engine.begin() as connection:
            connection.execute(text('CREATE TABLE c3b2a_account_marker (version TEXT NOT NULL)'))
            connection.execute(text("INSERT INTO c3b2a_account_marker VALUES ('synthetic-only-v1')"))
            User.__table__.create(connection)
        with Session(self.engine) as db:
            db.add_all([User(id=name,email=name+'@synthetic.invalid',name=name,password_hash='synthetic-credential-'+name) for name in ('alice','bob')])
            db.commit()

    def dependency(self):
        with Session(self.engine) as db:yield db

    def user(self,subject):
        with Session(self.engine) as db:return db.get(User,subject)

    def credential_revision(self,subject):
        user=self.user(subject)  # Fresh Session, never a stale request cache.
        return hashlib.sha256(user.password_hash.encode()).hexdigest() if user else None

    def change_credential(self,subject,value):
        with Session(self.engine) as db:
            user=db.get(User,subject);user.password_hash=value;db.commit()

    def private_row_count(self):
        with Session(self.engine) as db:return db.scalar(select(func.count()).select_from(User))

    def close(self):self.engine.dispose()


class SyntheticSessionAccess:
    def __init__(self):self.grants={}
    def resolve(self,subject,session_id):return self.grants.get((subject,session_id))
    def revoke(self,subject):
        for key,grant in tuple(self.grants.items()):
            if key[0]==subject:self.grants[key]=replace(grant,enabled=False,revision=grant.revision+1)


class SyntheticCalendar:
    def __init__(self):self.rows=();self.revision='synthetic-calendar-1'
    def read(self,subject,timezone,start,end):
        return CalendarWindow(subject,timezone,start,end,self.revision,SOURCE_CONTRACT,
            tuple(row for row in self.rows if row.subject==subject),False)


def build_staging_demo(root,*,origin):
    context=demo_context();accounts=DisposableAccounts(root);access=SyntheticSessionAccess();calendar=SyntheticCalendar()
    tokens={subject:create_access_token(subject) for subject in ('alice','bob')}
    for subject,token in tokens.items():
        binding=hashlib.sha256(('Bearer '+token).encode()).hexdigest()
        user=accounts.user(subject)
        access.grants[subject,binding]=SessionGrant(subject,binding,hashlib.sha256(user.password_hash.encode()).hexdigest(),
            'synthetic-explicit-entitlement-'+subject,1,('customized:preview','customized:proposal'),
            context.planning_instant-timedelta(days=1),context.planning_instant+timedelta(days=1),True)
    gate=StagingAccessGate(access,clock=lambda:context.planning_instant,current_credential_revision=accounts.credential_revision)
    server=replace(demo_server(),allowed_subjects=('alice','bob'))
    service=LifecycleService(server=server,store=DisposableProposalStore.create(Path(root)/'proposals.sqlite',disposable_root=root),
        schedule=ReadOnlyCalendarAdapter(calendar,context=context),clock=lambda:context.planning_instant,
        comparison_pairs=(('shorter-current','longer-current'),('longer-current','shorter-current')),authorize_actor=gate.authorize)
    app=create_staging_app(service=service,access_gate=gate,trusted_origin=origin,initial_request=proposed_request())
    # Keep signature/expiry/account checks and actual ORM queries; only the database
    # dependency points at the marked two-user disposable file.
    app.dependency_overrides[get_db]=accounts.dependency
    return SimpleNamespace(app=app,service=service,accounts=accounts,access=access,calendar=calendar,tokens=tokens)
