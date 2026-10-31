"""Actual native Flexible execution on the verified disposable scenario target."""
from copy import deepcopy
from uuid import uuid4
import pytest

from test_flexible_lifecycle import scenario, small_source, enrollment, operation
from app.database import SessionLocal
from app.models import WorkoutOccurrence, WorkoutSetLog


@pytest.mark.parametrize('with_context', [False, True])
def test_native_flexible_unknown_baseline_remains_unknown_through_today_and_logging(scenario, monkeypatch, with_context):
    small_source(monkeypatch)
    user_id, headers, client = scenario
    enrolled, _ = enrollment(client, headers)
    response, _ = operation(client, headers, enrolled, 'start')
    assert response.status_code == 200, response.text
    state = response.json()
    with SessionLocal() as db:
        original = deepcopy(db.get(WorkoutOccurrence, state['occurrence_id']).payload)
    today = client.get('/workout/today', headers=headers)
    assert today.status_code == 200, today.text
    item = today.json()['exercises'][0]
    assert item['recommended_working_weight'] is None
    body = {'command_id':str(uuid4()), 'exercise_id':item['id'],
        'exercise_occurrence_id':item['exercise_occurrence_id'], 'set_index':1,
        'reps':8, 'weight':17.5, 'set_kind':'work',
        'execution_context_id':state['execution_context']['id']}
    if with_context:
        body.update(rpe=8, load_context={'unit':'kg', 'display_unit':'kg',
            'basis':'machine_stack', 'increment':0.5, 'increment_unit':'kg',
            'equipment_key':'synthetic-cable'})
    path = f'/workout/{state["occurrence_id"]}/log-set'
    logged = client.post(path, headers=headers, json=body)
    assert logged.status_code == 200, logged.text
    receipt = logged.json()
    assert receipt['planned_weight'] is None and receipt['weight_delta'] is None
    assert receipt['next_working_weight'] is None
    live = receipt['live_recommendation']
    assert live['decision_trace']['runtime_weight_adapter']['source_weight_available'] is False
    if with_context:
        # Actual declared evidence may qualify remaining-set guidance even
        # though the immutable source snapshot still has no load baseline.
        assert live['recommended_weight'] is not None
        assert live['decision_trace'].get('load_recommendation_available') is not False
    else:
        assert live['recommended_weight'] is None
    assert client.post(path, headers=headers, json=body).json() == receipt
    with SessionLocal() as db:
        assert db.get(WorkoutOccurrence, state['occurrence_id']).payload == original
        row = db.query(WorkoutSetLog).filter_by(user_id=user_id).one()
        assert row.weight == 17.5 and row.execution_context_id == state['execution_context']['id']
        assert row.replay_context['planned_exercise'].get('recommended_working_weight') is None
