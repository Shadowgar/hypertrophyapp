"""Real API regression checks; runner must set an explicit disposable TEST_DATABASE_URL."""
from test_profile_training_state import _reset_db, _register_and_onboard
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, WorkoutSetLog


def seeded():
    _reset_db()
    client = TestClient(app)
    headers, email = _register_and_onboard(client)
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).one()
        user.onboarding_answers = {"keep": "consent and answers", "generated_onboarding": {"revision": 7}}
        db.add(WorkoutSetLog(user_id=user.id, workout_id="retained-history", primary_exercise_id="cross_body_lat_pull_around", exercise_id="cross_body_lat_pull_around", set_index=1, reps=12, weight=20))
        db.commit()
    return client, headers


def test_equipment_patch_preserves_every_unrelated_profile_field_and_history():
    client, headers = seeded()
    before = client.get('/profile', headers=headers).json()
    result = client.patch('/profile/equipment', headers=headers, json={"training_location": "home", "equipment_profile": ["cable"]})
    assert result.status_code == 200
    after = client.get('/profile', headers=headers).json()
    assert after == {**before, "training_location": "home", "equipment_profile": ["cable"]}
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).count() == 1
    assert client.patch('/profile/equipment', headers=headers, json={"equipment_profile": [], "days_available": 2}).status_code == 422
    assert client.patch('/profile/equipment', json={"equipment_profile": []}).status_code == 401


def test_legacy_profile_update_does_not_clear_omitted_constraints():
    client, headers = seeded()
    before = client.get('/profile', headers=headers).json()
    payload = {k: v for k, v in before.items() if k not in {'email','scheduling_timezone','effective_days_available','effective_program_id','session_time_budget_minutes','movement_restrictions','near_failure_tolerance'}}
    assert client.post('/profile', headers=headers, json=payload).status_code == 200
    after = client.get('/profile', headers=headers).json()
    for key in ('session_time_budget_minutes','movement_restrictions','near_failure_tolerance'):
        assert after[key] == before[key]


def test_appearance_default_revision_retry_and_account_isolation():
    client, headers = seeded()
    before = client.get('/profile', headers=headers).json()
    default = client.get('/profile/preferences', headers=headers)
    assert default.status_code == 200
    assert default.json() == {"theme_family": "classic", "appearance": "dark", "weight_unit": "lb", "revision": 0}
    update = {"theme_family": "graphite", "appearance": "system", "weight_unit": "kg", "expected_revision": 0}
    saved = client.put('/profile/preferences', headers=headers, json=update)
    assert saved.status_code == 200
    assert saved.json()['revision'] == 1
    assert client.put('/profile/preferences', headers=headers, json=update).json() == saved.json()
    conflict = client.put('/profile/preferences', headers=headers, json={**update, "theme_family": "charcoal"})
    assert conflict.status_code == 409
    second = client.post('/auth/register', json={"email":"second@example.com","password":"Synthetic-only-Q98z!","name":"Second"}).json()
    assert client.get('/profile/preferences', headers={"Authorization":f"Bearer {second['access_token']}"}).json() == default.json()
    assert client.get('/profile', headers=headers).json() == before
    assert client.put('/profile/preferences', headers=headers, json={**update, "theme_family":"forest"}).status_code == 422
