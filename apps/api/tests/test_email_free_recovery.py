"""Focused recovery authority tests; explicit synthetic targets via conftest."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.database import Base, engine, SessionLocal
from app.main import app
from app.models import User, PasswordResetToken
from app.security import create_access_token, hash_password, hash_password_reset_token, verify_password

client = TestClient(app)
PASSWORD='Original-password-123'

@pytest.fixture
def account():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        u = User(email=f'{uuid4()}@example.test',name='Synthetic',password_hash=hash_password(PASSWORD),onboarding_answers={'preserved':True})
        db.add(u); db.commit()
        return u.id, {'Authorization':'Bearer '+create_access_token(u.id,u.password_hash)}

def generate(account, **changes):
    return client.post('/auth/recovery-codes',headers=account[1],json={'current_password':PASSWORD,'confirmed':True,'command_id':str(uuid4()),**changes})

def reset(code, password='New-password-123'):
    return client.post('/auth/password-reset/confirm',json={'token':code,'new_password':password})

def test_ten_codes_hash_only_idempotent_confirmation_and_history_preserved(account):
    command=str(uuid4())
    denied=generate(account,current_password='Incorrect-password-123')
    assert denied.status_code == 401
    assert generate(account,confirmed=False).status_code == 422
    result=generate(account,command_id=command)
    assert result.status_code == 200
    codes=result.json()['codes']
    assert len(codes)==len(set(codes))==10 and all(len(c)>=43 for c in codes)
    assert result.headers['cache-control']=='no-store'
    duplicate=generate(account,command_id=command)
    assert duplicate.status_code==200 and duplicate.json()=={'status':'already_processed','codes':[]}
    with SessionLocal() as db:
        from app.models import AccountRecoveryCode
        rows=db.query(AccountRecoveryCode).filter_by(user_id=account[0]).all()
        assert len(rows)==10 and not any(c in repr([r.__dict__ for r in rows]) for c in codes)
        assert db.get(User, account[0]).onboarding_answers=={'preserved':True}

def test_single_use_keeps_nine_and_rejects_old_sessions(account):
    codes=generate(account).json()['codes']
    assert reset(codes[0]).status_code==200
    assert reset(codes[0]).status_code==400
    assert client.get('/auth/recovery-codes',headers=account[1]).status_code==401
    with SessionLocal() as db:
        u=db.get(User,account[0]); assert verify_password('New-password-123',u.password_hash)
        headers={'Authorization':'Bearer '+create_access_token(u.id,u.password_hash)}
    data=client.get('/auth/recovery-codes',headers=headers).json()
    assert data['remaining']==9 and any(e['kind']=='password_recovered' for e in data['events'])
    assert not any(c in str(data) for c in codes)
    assert reset(codes[1]).status_code==200

def test_regeneration_and_short_lived_confirmation_revoke_old_codes(account):
    old=generate(account).json()['codes']
    fresh=generate(account).json()['codes']
    assert reset(old[0]).status_code==400
    legacy='operator-synthetic-'+uuid4().hex
    with SessionLocal() as db:
        db.add(PasswordResetToken(user_id=account[0],token_hash=hash_password_reset_token(legacy),expires_at=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(minutes=10))); db.commit()
    assert reset(legacy).status_code==200
    assert reset(fresh[0]).status_code==400

def test_events_are_owned_and_acknowledgment_preserves_audit(account):
    generate(account)
    data=client.get('/auth/recovery-codes',headers=account[1]).json()
    event=data['events'][0]['id']
    with SessionLocal() as db:
        other=User(email=f'{uuid4()}@example.test',name='Other',password_hash=hash_password(PASSWORD)); db.add(other); db.commit()
        headers={'Authorization':'Bearer '+create_access_token(other.id,other.password_hash)}
    assert client.post(f'/auth/recovery-events/{event}/acknowledge',headers=headers).status_code==404
    assert client.post(f'/auth/recovery-events/{event}/acknowledge',headers=account[1]).status_code==200
    assert client.get('/auth/recovery-codes',headers=account[1]).json()['events'][0]['acknowledged_at']

def test_stale_credential_after_lock_rejected_even_same_password(account):
    from app.account_recovery import generate_codes
    with SessionLocal() as db:
        user=db.get(User,account[0]); old=sha256(user.password_hash.encode()).hexdigest()
        user.password_hash=hash_password(PASSWORD); db.commit()
        with pytest.raises(HTTPException) as e:
            generate_codes(db,account[0],old,PASSWORD,str(uuid4()))
        assert e.value.status_code==401

def test_bad_codes_share_generic_error_and_generation_is_rate_limited(account):
    bad=reset('frc_'+('x'*43))
    assert bad.status_code==400 and bad.json()['detail']=='Invalid or expired reset token'
    for _ in range(3): assert generate(account,current_password='Wrong-password-123').status_code==401
    assert generate(account).status_code==429

def test_failure_before_commit_rolls_back_code_claim_and_password(account, monkeypatch):
    from app.account_recovery import confirm_recovery
    codes=generate(account).json()['codes']
    with SessionLocal() as db:
        original=db.get(User,account[0]).password_hash
        def fail(): raise RuntimeError('synthetic commit failure')
        monkeypatch.setattr(db,'commit',fail)
        with pytest.raises(RuntimeError): confirm_recovery(db,codes[0],'New-password-123')
        db.rollback()
        assert db.get(User,account[0]).password_hash==original
    assert reset(codes[0]).status_code==200

def test_postgres_same_code_race_has_one_winner(account):
    if engine.dialect.name!='postgresql': pytest.skip('real PostgreSQL locking qualification')
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.account_recovery import confirm_recovery
    code=generate(account).json()['codes'][0]
    gate=Barrier(2)
    def submit(index):
        with SessionLocal() as db:
            gate.wait(timeout=10)
            try:
                confirm_recovery(db,code,f'Winner-{index}-password'); return 200
            except HTTPException as e:
                db.rollback(); return e.status_code
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(submit,[0,1]))==[200,400]

def test_postgres_duplicate_generation_and_concurrent_reset(account):
    if engine.dialect.name!='postgresql': pytest.skip('real PostgreSQL locking qualification')
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.account_recovery import generate_codes, confirm_recovery
    with SessionLocal() as db: cv=sha256(db.get(User,account[0]).password_hash.encode()).hexdigest()
    command=str(uuid4()); gate=Barrier(2)
    def submit(_):
        with SessionLocal() as db:
            gate.wait(timeout=10)
            return generate_codes(db,account[0],cv,PASSWORD,command)
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(submit,[0,1]))
    assert sorted(len(r['codes']) for r in results)==[0,10]
    code=next(r['codes'][0] for r in results if r['codes'])
    # Hold User while a generation request with a previously valid CV waits.
    from threading import Event
    started=Event()
    with SessionLocal() as resetting:
        resetting.query(User).filter_by(id=account[0]).with_for_update().one()
        def stale_generate():
            with SessionLocal() as db:
                started.set()
                try: generate_codes(db,account[0],cv,PASSWORD,str(uuid4())); return 200
                except HTTPException as e: db.rollback(); return e.status_code
        with ThreadPoolExecutor(1) as pool:
            future=pool.submit(stale_generate); assert started.wait(5)
            confirm_recovery(resetting,code,PASSWORD)
            assert future.result(timeout=10)==401

def test_legacy_random_token_may_share_permanent_prefix(account):
    token='frc_'+uuid4().hex
    with SessionLocal() as db:
        db.add(PasswordResetToken(user_id=account[0],token_hash=hash_password_reset_token(token),expires_at=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(minutes=10))); db.commit()
    assert reset(token).status_code==200
