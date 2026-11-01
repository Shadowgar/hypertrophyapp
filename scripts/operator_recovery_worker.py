"""Reviewed stdin worker for the existing API image; never installed as an API route.

Only main() emits a transient credential to the private parent pipe. Importing this
file performs no database operation. No tracebacks or raw database errors escape.
"""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone


class RecoveryRefused(RuntimeError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(',', ':')).encode()).hexdigest()


def inspect_account(db, user_id):
    from app.models import User, PasswordResetToken
    user = db.query(User).filter(User.id == user_id).populate_existing().first()
    if user is None:
        raise RecoveryRefused('Account not found')
    account = {c.name: getattr(user, c.name) for c in User.__table__.columns}
    tokens = db.query(PasswordResetToken).filter_by(user_id=user_id).order_by(PasswordResetToken.id).all()
    state = [{c.name: getattr(t, c.name) for c in PasswordResetToken.__table__.columns} for t in tokens]
    return {'account_id': user.id, 'account_sha256': digest(account), 'reset_state_sha256': digest(state),
            'normalized_email_sha256': hashlib.sha256(user.email.strip().lower().encode()).hexdigest()}


def issue(db, user_id, expected):
    from app.models import User, PasswordResetToken
    from app.security import create_password_reset_token, hash_password_reset_token
    user = db.query(User).filter(User.id == user_id).populate_existing().with_for_update().first()
    if user is None or inspect_account(db, user_id) != expected:
        raise RecoveryRefused('Account or recovery state changed; renewed authorization required')
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None)).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    code = create_password_reset_token()
    db.add(PasswordResetToken(user_id=user_id, token_hash=hash_password_reset_token(code), expires_at=now+timedelta(minutes=10)))
    db.commit()
    return code


def verify_database(db, target):
    from sqlalchemy import text
    from app.config import settings
    from sqlalchemy.engine import make_url
    url = make_url(settings.resolved_database_url)
    if url.get_backend_name() != 'postgresql' or url.query or url.database != target['database'] or url.username != target['role']:
        raise RecoveryRefused('Database coordinates differ')
    result = db.execute(text("SELECT current_database(), current_user, (SELECT system_identifier::text FROM pg_control_system()), inet_server_addr()::text, inet_server_port()")).one()
    schema = db.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all()
    if (list(result[:3]) != [target['database'], target['role'], target['cluster']]
            or result[3] not in target['server_addresses'] or result[4] != 5432
            or schema != [target['schema']] or os.environ.get('APP_VERSION') != target['revision']):
        raise RecoveryRefused('Database/schema/revision identity differs')


def main():
    try:
        data = json.loads(__import__('sys').stdin.read())
        from app.database import SessionLocal
        with SessionLocal() as db:
            verify_database(db, data['target'])
            if data['operation'] == 'inspect':
                result = {'state': inspect_account(db, data['target']['account_id'])}
            elif data['operation'] == 'issue':
                result = {'code': issue(db, data['target']['account_id'], data['state'])}
            else:
                raise RecoveryRefused('Unknown operation')
        print(json.dumps(result))
    except Exception:
        # Commit may already have succeeded. Never print exception/credential data.
        print('{"error":"operation_unconfirmed"}')
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
