"""Retain active history and credential boundaries during feature containment."""
from uuid import uuid4
from datetime import UTC, datetime, timedelta

import jwt

from sqlalchemy import text

from test_customized_application import application, accepted, post


def test_feature_disabled_retains_active_logging_correction_retry_and_history(application, monkeypatch):
    c, h, Session, account = application
    proposal = accepted(application)
    activation_path = f"/customized/proposals/{proposal['proposal_id']}/activate"
    activation = dict(expected_revision=proposal['revision'], snapshot_hash=proposal['snapshot_hash'])
    assert post(c, h, activation_path, activation).status_code == 200
    today = c.get('/workout/today', headers=h).json()
    occurrence = today['workout_occurrence_id']
    exercise = today['exercises'][0]
    payload = dict(command_id=uuid4().hex, exercise_id=exercise['id'],
        exercise_occurrence_id=exercise['exercise_occurrence_id'], set_index=1, reps=8, weight=10)
    receipt = post(c, h, f'/workout/{occurrence}/log-set', payload)
    assert receipt.status_code == 200, receipt.text
    from app.config import settings
    with Session() as db:
        from app.models import User
        subject = db.query(User).filter_by(email=account['email']).one().id
        # Exact deployed-source 27231cf claim shape: no cv and no jti.
        legacy_headers = {'Authorization': 'Bearer ' + jwt.encode(
            {'sub': subject, 'exp': datetime.now(UTC) + timedelta(minutes=10)},
            settings.jwt_secret, algorithm=settings.jwt_algorithm)}
        lifecycle_before = tuple(db.execute(text(
            'SELECT (SELECT count(*) FROM customized_candidate_events), '
            '(SELECT count(*) FROM customized_candidate_commands), '
            '(SELECT count(*) FROM customized_candidate_sessions)')).one())
    assert c.get('/workout/today', headers=legacy_headers).status_code == 200
    assert c.get('/customized/options', headers=legacy_headers).status_code == 401
    monkeypatch.setattr(settings, 'customized_enabled', False)
    assert c.get('/customized/options', headers=h).status_code == 404
    assert post(c, h, '/customized/proposals', {}).status_code == 404
    assert post(c, h, activation_path, activation).status_code == 404
    assert c.get(f"/customized/proposals/{proposal['proposal_id']}/history", headers=h).status_code == 404
    assert c.get('/workout/today', headers=h).json()['workout_occurrence_id'] == occurrence
    assert post(c, h, f'/workout/{occurrence}/log-set', payload).json() == receipt.json()
    correction = dict(command_id=uuid4().hex, reps=9, weight=12, reason='Synthetic containment correction')
    corrected = post(c, h, f"/workout/set/{receipt.json()['id']}/correct", correction)
    assert corrected.status_code == 200, corrected.text
    assert post(c, h, f"/workout/set/{receipt.json()['id']}/correct", correction).json() == corrected.json()
    second = dict(payload, command_id=uuid4().hex, set_index=2)
    assert post(c, h, f'/workout/{occurrence}/log-set', second).status_code == 200
    progress = c.get(f'/workout/{occurrence}/progress', headers=h)
    assert progress.status_code == 200 and progress.json()['completed_total'] == 2
    assert c.get(f"/workout/set/{receipt.json()['id']}/audit", headers=h).status_code == 200
    assert c.get('/history/calendar?start_date=2026-10-19&end_date=2026-10-25', headers=h).status_code == 200
    with Session() as db:
        assert tuple(db.execute(text(
            'SELECT (SELECT count(*) FROM customized_candidate_events), '
            '(SELECT count(*) FROM customized_candidate_commands), '
            '(SELECT count(*) FROM customized_candidate_sessions)')).one()) == lifecycle_before
        # Simulate a credential change on this synthetic account only. The
        # containment flag must not disable the existing cv verifier.
        from app.security import hash_password
        user = db.query(User).filter_by(email=account['email']).one()
        user.password_hash = hash_password('Synthetic-changed-credential-only-123!')
        db.commit()
    assert c.get('/workout/today', headers=h).status_code == 401
    fresh = c.post('/auth/login', json={'email': account['email'], 'password': 'Synthetic-changed-credential-only-123!'})
    assert fresh.status_code == 200
    fresh_headers = {'Authorization': 'Bearer ' + fresh.json()['access_token']}
    assert c.get('/workout/today', headers=fresh_headers).status_code == 200
    # Compatibility is intentional, not full legacy-session revocation.
    assert c.get('/workout/today', headers=legacy_headers).status_code == 200
