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


def saved_account(client, program='pure_bodybuilding_phase_1_full_body'):
    email, headers = register(client)
    payload = dict(name='Synthetic', age=32, weight=80, gender='', split_preference='full_body', days_available=3,
                   program_selection_mode='manual', selected_program_id=program)
    assert client.post('/profile/initial-setup', headers=headers, json=payload).status_code == 200
    return email, headers


def snapshot(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


@pytest.mark.parametrize('program', ['pure_bodybuilding_phase_1_full_body', 'pure_bodybuilding_phase_2_full_body', 'full_body_v1'])
def test_basics_edit_preserves_setup_consent_preferences_schedule_and_history(client, program):
    from app.models import UserInterfacePreference
    email, headers = saved_account(client, program)
    other_email, other_headers = register(client)
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).one()
        user.onboarding_answers = {'birthday': '1994-01-01', 'generated_onboarding': {'consent_sentinel': 'preserve'}}
        user.nutrition_phase, user.calories, user.protein = 'maintenance', 2200, 150
        user.equipment_profile, user.scheduling_timezone = ['dumbbell'], 'UTC'
        user.active_frequency_adaptation = {'preserve': True}
        plan = WorkoutPlan(user_id=user.id, week_start=date(2025, 1, 6), split='full_body', phase='accumulation', payload={'sessions': [], 'selected_dates': ['2025-01-07', '2025-01-10']})
        log = WorkoutSetLog(user_id=user.id, workout_id='saved-basics-history', exercise_id='press', primary_exercise_id='press', set_index=1, reps=8, weight=20)
        prefs = UserInterfacePreference(user_id=user.id, theme_family='classic', appearance='dark', weight_unit='lb', revision=1)
        db.add_all([plan, log, prefs]); db.commit()
        before = {key: value for key, value in snapshot(user).items() if key not in {'name', 'age', 'weight'}}
        plan_before, log_before, prefs_before = snapshot(plan), snapshot(log), snapshot(prefs)
        other_before = snapshot(db.query(User).filter_by(email=other_email).one())
    response = client.patch('/profile/setup-basics', headers=headers, json={'name': '  Revised Name  ', 'age': 36, 'weight': 82.25})
    assert response.status_code == 200
    assert (response.json()['name'], response.json()['age'], response.json()['weight']) == ('Revised Name', 36, 82.25)
    assert response.json()['initial_setup_available'] is False
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).one()
        assert {key: value for key, value in snapshot(user).items() if key not in {'name', 'age', 'weight'}} == before
        assert snapshot(db.get(WorkoutPlan, plan_before['id'])) == plan_before
        assert snapshot(db.get(WorkoutSetLog, log_before['id'])) == log_before
        assert snapshot(db.get(UserInterfacePreference, prefs_before['user_id'])) == prefs_before
        assert snapshot(db.query(User).filter_by(email=other_email).one()) == other_before
    assert client.get('/profile', headers=other_headers).json()['setup_status'] == 'initial'


@pytest.mark.parametrize('changes', [{'name': '  '}, {'age': 13}, {'age': 91}, {'weight': 0}, {'weight': 'NaN'}, {'onboarding_answers': {}}, {'selected_program_id': 'full_body_v1'}])
def test_basics_edit_rejects_invalid_values_and_unrelated_fields_without_writes(client, changes):
    email, headers = saved_account(client)
    with SessionLocal() as db:
        before = snapshot(db.query(User).filter_by(email=email).one())
    response = client.patch('/profile/setup-basics', headers=headers, json={'name': 'Revised', 'age': 32, 'weight': 80, **changes})
    assert response.status_code == 422
    with SessionLocal() as db:
        assert snapshot(db.query(User).filter_by(email=email).one()) == before


def test_basics_edit_requires_authentication_and_never_initializes_blank_account(client):
    email, headers = register(client)
    payload = {'name': 'Revised', 'age': 32, 'weight': 80}
    assert client.patch('/profile/setup-basics', json=payload).status_code == 401
    assert client.patch('/profile/setup-basics', headers=headers, json=payload).status_code == 409
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).one()
        assert user.age is None and user.weight is None and user.name == 'Synthetic'
