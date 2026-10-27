"""Read-only classification using synthetic accounts; no destructive reset helpers."""
from datetime import date
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, WorkoutPlan, WorkoutSetLog

@pytest.fixture(scope='module')
def client():
    with TestClient(app) as client:
        yield client

def register(client):
    email = f'iphone-{uuid4().hex}@example.com'
    response = client.post('/auth/register', json={'email': email, 'password': 'Synthetic-only-password!', 'name': 'Synthetic'})
    assert response.status_code == 200
    return email, {'Authorization': f"Bearer {response.json()['access_token']}"}

def test_initial_saved_unscheduled_and_historical_accounts_have_distinct_states(client):
    email, headers = register(client)
    response = client.get('/profile', headers=headers).json()
    assert response['setup_status'] == 'initial'
    assert response['initial_setup_available'] is True
    payload = dict(name='Synthetic', age=32, weight=80, gender='', split_preference='full_body', days_available=3,
                   program_selection_mode='manual', selected_program_id='pure_bodybuilding_phase_1_full_body')
    assert client.post('/profile/initial-setup', headers=headers, json=payload).status_code == 200
    assert client.get('/profile', headers=headers).json()['setup_status'] == 'planning'
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).one()
        user.onboarding_answers = {'generated_onboarding': {'consent_sentinel': 'preserve'}}
        db.add(WorkoutPlan(user_id=user.id, week_start=date(2025, 1, 6), split='full_body', phase='accumulation', payload={'sessions': []}))
        db.commit()
    for _ in range(2):
        response = client.get('/profile', headers=headers).json()
        assert response['setup_status'] == 'established'
        assert response['initial_setup_available'] is False
        assert response['onboarding_answers']['generated_onboarding']['consent_sentinel'] == 'preserve'
    assert client.post('/profile/initial-setup', headers=headers, json=payload).status_code == 409

def test_history_alone_prevents_reinitialization_and_is_account_scoped(client):
    email, headers = register(client)
    _, other = register(client)
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).one()
        db.add(WorkoutSetLog(user_id=user.id, workout_id='retained-history', exercise_id='press', primary_exercise_id='press', set_index=1, reps=8, weight=20))
        db.commit()
    response = client.get('/profile', headers=headers).json()
    assert response['setup_status'] == 'established'
    assert response['initial_setup_available'] is False
    assert client.post('/profile/initial-setup', headers=headers, json=dict(name='Synthetic', age=32, weight=80, gender='', split_preference='full_body', days_available=3)).status_code == 409
    assert client.get('/profile', headers=other).json()['setup_status'] == 'initial'
