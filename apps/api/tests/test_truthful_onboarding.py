"""New-account unknowns and ordinary preference writes must never invent or erase evidence."""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from test_profile_training_state import _reset_db, _register_and_onboard
from app.database import SessionLocal
from app.main import app
from app.models import User, WeeklyCheckin, WeeklyReviewCycle, WorkoutPlan, WorkoutSetLog

NUTRITION = ('nutrition_phase', 'calories', 'protein', 'fat', 'carbs')
PROFILE = dict(name='Synthetic newcomer', age=30, weight=80, gender='prefer_not_to_say',
               split_preference='full_body', days_available=3, training_location='gym',
               equipment_profile=['cable'], selected_program_id=None, program_selection_mode='auto')


def test_new_account_unknown_nutrition_is_not_zero_or_maintenance_and_creates_no_evidence():
    _reset_db()
    client = TestClient(app)
    registration = client.post('/auth/register', json={
        'email': 'truthful-new@example.com', 'password': 'Synthetic-only-Q98z!', 'name': 'Synthetic newcomer'})
    headers = {'Authorization': f"Bearer {registration.json()['access_token']}"}
    assert {key: client.get('/profile', headers=headers).json()[key] for key in NUTRITION} == dict.fromkeys(NUTRITION)
    saved = client.post('/profile', headers=headers, json=PROFILE)
    assert saved.status_code == 200
    assert {key: saved.json()[key] for key in NUTRITION} == dict.fromkeys(NUTRITION)
    assert saved.json()['program_selection_mode'] == 'auto'
    assert saved.json()['selected_program_id'] is None
    with SessionLocal() as db:
        user = db.query(User).one()
        assert all(getattr(user, key) is None for key in NUTRITION)
        assert all(db.query(model).count() == 0 for model in (WeeklyCheckin, WeeklyReviewCycle, WorkoutPlan, WorkoutSetLog))


def test_explicit_targets_are_preserved_when_compatibility_client_omits_them():
    _reset_db()
    client = TestClient(app)
    headers, _ = _register_and_onboard(client)
    targets = dict(nutrition_phase='maintenance', calories=2400, protein=140, fat=0, carbs=300)
    assert client.post('/profile', headers=headers, json={**PROFILE, **targets}).status_code == 200
    result = client.post('/profile', headers=headers, json={**PROFILE, 'name': 'Updated name'})
    assert result.status_code == 200
    assert {key: result.json()[key] for key in NUTRITION} == targets
    with SessionLocal() as db:
        assert db.query(WeeklyCheckin).count() == db.query(WeeklyReviewCycle).count() == 0


@pytest.mark.parametrize('action', ['profile_program', 'profile_answers_without_sets', 'confirmed_switch'])
def test_normal_profile_changes_preserve_plans_checkins_sets_and_generated_consent(action):
    _reset_db()
    client = TestClient(app)
    headers, email = _register_and_onboard(client)
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).one()
        user.onboarding_answers = {'generated_onboarding': {'revision': 7, 'sentinel': 'preserve consent'}}
        db.add(WorkoutPlan(user_id=user.id, week_start=date(2026, 10, 19), split='full_body', phase='accumulation',
                           payload={'program_template_id': 'pure_bodybuilding_phase_1_full_body', 'sessions': []}))
        db.add(WeeklyCheckin(user_id=user.id, week_start=date(2026, 10, 19), body_weight=81, adherence_score=3))
        if action != 'profile_answers_without_sets':
            db.add(WorkoutSetLog(user_id=user.id, workout_id='retained-original-source-slot',
                                primary_exercise_id='cross_body_lat_pull_around', exercise_id='cross_body_lat_pull_around',
                                set_index=1, reps=12, weight=20, rpe=8))
        db.commit()
        before = {model.__name__: [{column.name: getattr(row, column.name) for column in model.__table__.columns}
                                  for row in db.query(model).all()]
                  for model in (WorkoutPlan, WeeklyCheckin, WorkoutSetLog)}
    target = 'pure_bodybuilding_phase_2_full_body'
    if action == 'confirmed_switch':
        response = client.post('/profile/program-switch', headers=headers, json={'target_program_id': target, 'confirm': True})
        assert response.status_code == 200, response.text
        assert response.json()['applied'] is True
    else:
        profile = client.get('/profile', headers=headers).json()
        profile['onboarding_answers'] = {'new_explicit_answer': 'preserve history'}
        if action == 'profile_program':
            profile['selected_program_id'] = target
        response = client.post('/profile', headers=headers, json=profile)
        assert response.status_code == 200, response.text
    with SessionLocal() as db:
        after = {model.__name__: [{column.name: getattr(row, column.name) for column in model.__table__.columns}
                                 for row in db.query(model).all()]
                 for model in (WorkoutPlan, WeeklyCheckin, WorkoutSetLog)}
        assert after == before
        assert db.query(User).filter_by(email=email).one().onboarding_answers['generated_onboarding'] == {'revision': 7, 'sentinel': 'preserve consent'}


def test_initial_setup_is_account_bound_and_refuses_to_overwrite_after_lost_response():
    _reset_db()
    client = TestClient(app)
    registration = client.post('/auth/register', json={
        'email': 'initial-setup@example.com', 'password': 'Synthetic-only-Q98z!', 'name': 'Synthetic newcomer'})
    headers = {'Authorization': f"Bearer {registration.json()['access_token']}"}
    assert client.get('/profile', headers=headers).json()['initial_setup_available'] is True
    assert client.post('/profile/initial-setup', json=PROFILE).status_code == 401
    first = client.post('/profile/initial-setup', headers=headers, json=PROFILE)
    assert first.status_code == 200
    assert first.json()['initial_setup_available'] is False
    # The first response may be lost; a later command cannot replace a saved profile.
    retry = client.post('/profile/initial-setup', headers=headers, json={**PROFILE, 'weight': 99})
    assert retry.status_code == 409
    assert client.get('/profile', headers=headers).json() == first.json()
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).count() == db.query(WeeklyReviewCycle).count() == 0


def test_postgres_concurrent_initial_setup_has_one_winner():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.database import engine
    if engine.dialect.name != 'postgresql':
        pytest.skip('PostgreSQL row-lock qualification')
    _reset_db()
    client = TestClient(app)
    registration = client.post('/auth/register', json={
        'email': 'initial-race@example.com', 'password': 'Synthetic-only-Q98z!', 'name': 'Synthetic newcomer'})
    headers = {'Authorization': f"Bearer {registration.json()['access_token']}"}
    barrier = Barrier(2)
    def submit(weight):
        barrier.wait(timeout=10)
        return TestClient(app).post('/profile/initial-setup', headers=headers, json={**PROFILE, 'weight': weight})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, [80, 99]))
    assert sorted(result.status_code for result in results) == [200, 409]
    winner = next(result.json() for result in results if result.status_code == 200)
    assert client.get('/profile', headers=headers).json() == winner


@pytest.mark.parametrize('field,value', [('calories', 0), ('equipment_profile', []), ('program_selection_mode', 'auto')])
def test_initial_setup_does_not_treat_partial_or_auto_profiles_as_blank(field, value):
    _reset_db()
    client = TestClient(app)
    registration = client.post('/auth/register', json={
        'email': 'partial-profile@example.com', 'password': 'Synthetic-only-Q98z!', 'name': 'Synthetic newcomer'})
    headers = {'Authorization': f"Bearer {registration.json()['access_token']}"}
    with SessionLocal() as db:
        user = db.query(User).one()
        setattr(user, field, value)
        db.commit()
    before = client.get('/profile', headers=headers).json()
    assert before['initial_setup_available'] is False
    assert client.post('/profile/initial-setup', headers=headers, json=PROFILE).status_code == 409
    assert client.get('/profile', headers=headers).json() == before
