"""Synthetic persistence only; issuer never invokes Docker from these tests."""
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from app.database import Base, engine, SessionLocal
from app.models import User, PasswordResetToken
from app.security import hash_password, hash_password_reset_token

spec = importlib.util.spec_from_file_location('operator_worker', Path(__file__).resolve().parents[3] / 'scripts/operator_recovery_worker.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

@pytest.fixture
def account():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        u = User(email=f'{uuid4()}@example.test', name='Synthetic', password_hash=hash_password('Original-password-123'), onboarding_answers={'preserve': True})
        db.add(u); db.commit()
        return u.id

def test_issuer_preserves_account_invalidates_old_and_expires_in_ten_minutes(account):
    with SessionLocal() as db:
        db.add(PasswordResetToken(user_id=account, token_hash=hash_password_reset_token('old-synthetic-code-'+uuid4().hex), expires_at=datetime.now()+timedelta(days=1)))
        db.commit()
        before = worker.inspect_account(db, account)
        credential = db.get(User, account).password_hash
        code = worker.issue(db, account, before)
        rows = db.query(PasswordResetToken).filter_by(user_id=account).all()
        active = [r for r in rows if r.used_at is None]
        assert len(active) == 1 and active[0].token_hash == hash_password_reset_token(code)
        assert 590 < (active[0].expires_at-datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds() <= 600
        assert code not in repr(before) and len(code) >= 43
        assert db.get(User, account).password_hash == credential
        assert db.get(User, account).onboarding_answers == {'preserve': True}
        with pytest.raises(worker.RecoveryRefused):
            worker.issue(db, account, before)

def test_changed_account_and_unknown_account_refused(account):
    with SessionLocal() as db:
        before = worker.inspect_account(db, account)
        db.get(User, account).password_hash = hash_password('Changed-password-123'); db.commit()
        with pytest.raises(worker.RecoveryRefused): worker.issue(db, account, before)
        with pytest.raises(worker.RecoveryRefused): worker.inspect_account(db, str(uuid4()))

def test_operator_code_uses_existing_confirm_once_and_revokes_sessions(account):
    from app.routers.auth import password_reset_confirm
    from app.schemas import PasswordResetConfirmRequest
    from app.security import create_access_token
    from app.deps import get_current_user
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials
    from starlette.requests import Request
    with SessionLocal() as db:
        old = create_access_token(account, db.get(User, account).password_hash)
        code = worker.issue(db, account, worker.inspect_account(db, account))
        payload = PasswordResetConfirmRequest(token=code, new_password='New-password-123')
        assert password_reset_confirm(payload, db).status == 'password_updated'
        with pytest.raises(HTTPException): password_reset_confirm(payload, db)
        with pytest.raises(HTTPException): get_current_user(Request({'type':'http','headers':[]}), HTTPAuthorizationCredentials(scheme='Bearer', credentials=old), db)

def test_refuses_non_terminal_and_unprotected_manifest(tmp_path, monkeypatch):
    host_spec = importlib.util.spec_from_file_location('operator_host', Path(__file__).resolve().parents[3] / 'scripts/operator_recovery.py')
    host = importlib.util.module_from_spec(host_spec); host_spec.loader.exec_module(host)
    monkeypatch.setattr(host.os, 'isatty', lambda _: False)
    with pytest.raises(host.RecoveryRefused): host.private_terminal()
    p = tmp_path/'unsafe.json'; p.write_text('{}'); p.chmod(0o644)
    with pytest.raises(host.RecoveryRefused): host.private_read(p)
    p.chmod(0o600)
    assert host.private_read(p) == {}
    with pytest.raises(FileExistsError): host.private_write(p, {})

def _host():
    host_spec = importlib.util.spec_from_file_location('operator_host', Path(__file__).resolve().parents[3] / 'scripts/operator_recovery.py')
    host = importlib.util.module_from_spec(host_spec); host_spec.loader.exec_module(host)
    return host

def test_display_once_only_to_private_terminal_and_no_retry(tmp_path, monkeypatch, capsys):
    import io
    host=_host()
    class Terminal(io.StringIO):
        def close(self): pass
    terminal=Terminal()
    manifest={'target':{},'state':{'fingerprint':'synthetic'}}
    path=tmp_path/'manifest.json'; host.private_write(path,manifest)
    code='a'*43
    calls=[]
    def worker(operation, _):
        calls.append(operation)
        return {'state':manifest['state']} if operation=='inspect' else {'code':code}
    monkeypatch.setattr(host,'private_terminal',lambda:terminal)
    monkeypatch.setattr(host,'verify_host',lambda _:None)
    monkeypatch.setattr(host,'worker',worker)
    monkeypatch.setattr(host.getpass,'getpass',lambda _: 'ISSUE ONE FERRAVIS RECOVERY CODE '+host.fingerprint(manifest))
    assert host.main(['issue','--manifest',str(path)])==0
    assert terminal.getvalue().count(code)==1
    assert code not in ''.join(p.read_text() for p in tmp_path.iterdir())
    assert code not in str(capsys.readouterr())
    assert host.main(['issue','--manifest',str(path)])==1
    assert calls.count('issue')==1

def test_post_commit_display_failure_keeps_attempt_marker(tmp_path, monkeypatch):
    host=_host()
    class BrokenTerminal:
        def __enter__(self): return self
        def __exit__(self,*_): pass
        def write(self,_): raise OSError('private output unavailable')
    manifest={'target':{},'state':{'fingerprint':'synthetic'}}
    path=tmp_path/'manifest.json'; host.private_write(path,manifest)
    monkeypatch.setattr(host,'private_terminal',BrokenTerminal)
    monkeypatch.setattr(host,'verify_host',lambda _:None)
    monkeypatch.setattr(host,'worker',lambda operation,_: {'state':manifest['state']} if operation=='inspect' else {'code':'a'*43})
    monkeypatch.setattr(host.getpass,'getpass',lambda _: 'ISSUE ONE FERRAVIS RECOVERY CODE '+host.fingerprint(manifest))
    assert host.main(['issue','--manifest',str(path)])==1
    assert Path(str(path)+'.issuance.json').exists()
    assert not Path(str(path)+'.issuance.json.displayed').exists()

def test_postgres_two_issuers_one_winner(account):
    if engine.dialect.name!='postgresql': pytest.skip('real PostgreSQL locking qualification')
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    with SessionLocal() as db: binding=worker.inspect_account(db,account)
    gate=Barrier(2)
    def invoke(_):
        with SessionLocal() as db:
            gate.wait(timeout=10)
            try: worker.issue(db,account,binding); return 'issued'
            except worker.RecoveryRefused: db.rollback(); return 'refused'
    with ThreadPoolExecutor(2) as pool: assert sorted(pool.map(invoke,[0,1]))==['issued','refused']
