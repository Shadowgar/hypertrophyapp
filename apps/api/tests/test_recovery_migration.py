"""Additive rehearsal on a fresh synthetic database in the disposable cluster."""
from pathlib import Path
from uuid import uuid4
import hashlib

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from app.config import settings
from app.database import engine


def test_populated_0027_to_0028_preserves_original_rows(monkeypatch):
    if engine.dialect.name!='postgresql': pytest.skip('isolated PostgreSQL migration qualification')
    # conftest already required loopback non-default port + explicit disposable
    # name/user markers; never derive an address from production defaults.
    name='recovery_migration_'+uuid4().hex
    with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
        conn.execute(text('CREATE DATABASE '+name))
    target=engine.url.set(database=name)
    monkeypatch.setattr(settings,'database_url',target.render_as_string(hide_password=False))
    cfg=Config()
    cfg.set_main_option('script_location',str(Path(__file__).resolve().parents[1]/'alembic'))
    command.upgrade(cfg,'0027_flexible_training')
    isolated=create_engine(target)
    with isolated.begin() as conn:
        conn.execute(text("INSERT INTO users(id,email,password_hash,name,created_at) VALUES ('synthetic-owner','synthetic@example.test','synthetic-not-a-credential','Synthetic',CURRENT_TIMESTAMP)"))
        conn.exec_driver_sql("INSERT INTO workout_plans(id,user_id,week_start,split,phase,payload,created_at) VALUES ('synthetic-plan','synthetic-owner','2026-10-26','full_body','phase1','{\"preserve\":true}',CURRENT_TIMESTAMP)")
    tables=inspect(isolated).get_table_names()
    assert len(tables)==25 and 'customized_candidate_schema' in tables
    def inventory():
        with isolated.connect() as conn:
            return {t:hashlib.sha256('\n'.join(sorted(conn.execute(text('SELECT row_to_json(t)::text FROM "'+t+'" t')).scalars())).encode()).hexdigest() for t in tables if t!='alembic_version'}
    before=inventory()
    columns={t:[(c['name'],str(c['type']),c['nullable'],c.get('default')) for c in inspect(isolated).get_columns(t)] for t in tables}
    command.upgrade(cfg,'0028_account_recovery_codes')
    assert inventory()==before
    assert {t:[(c['name'],str(c['type']),c['nullable'],c.get('default')) for c in inspect(isolated).get_columns(t)] for t in tables}==columns
    assert set(inspect(isolated).get_table_names())-set(tables)=={'account_recovery_codes','account_security_events'}
    with isolated.connect() as conn:
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar()=='0028_account_recovery_codes'
        assert conn.execute(text('SELECT count(*) FROM account_recovery_codes')).scalar()==0
        assert conn.execute(text('SELECT count(*) FROM account_security_events')).scalar()==0
    isolated.dispose()
