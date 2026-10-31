"""Runtime absence and receipt targets cannot invent a working-load baseline."""
from copy import deepcopy

import pytest

from core_engine.authored_constraints import typed_tracking_feedback
from core_engine.authored_prescription import preserve_prescription


def exercise(raw='AMRAP', **changes):
    return {'id':'synthetic', 'sets':2, 'load_semantics':'external_load',
        'authored_prescription':preserve_prescription({'reps':raw, 'rest':'Synthetic rest'}, 2),
        'source_lineage':{'source_slot_id':'synthetic-slot'}, **changes}


@pytest.mark.parametrize('raw', ['8-12', 'AMRAP', '5,3+'])
@pytest.mark.parametrize('missing_key', [False, True])
def test_missing_external_weight_remains_unknown_without_mutating_prescription(raw, missing_key):
    item = exercise(raw)
    if not missing_key:
        item['recommended_working_weight'] = None
    original = deepcopy(item)
    result = typed_tracking_feedback(item, completed_sets=1, set_index=2)
    assert result['recommended_weight'] is None
    assert result['decision_trace']['runtime_weight_adapter'] == {
        'owner':'core_engine.authored_constraints', 'source_weight_available':False}
    assert result['decision_trace']['numeric_progression'] == 'not_applicable'
    assert result['decision_trace']['set_prescription'] == original['authored_prescription']['sets'][1]
    assert result['completed_sets'] == 1 and result['remaining_sets'] == 1
    assert (result['recommended_reps_min'], result['recommended_reps_max']) == ((8, 12) if raw == '8-12' else (None, None))
    assert item == original


@pytest.mark.parametrize('weight', [0, 27.5, '32.5'])
def test_available_explicit_weight_is_retained(weight):
    result = typed_tracking_feedback(exercise(recommended_working_weight=weight), completed_sets=0)
    assert result['recommended_weight'] == float(weight)


@pytest.mark.parametrize('raw', ['8-12', 'AMRAP'])
def test_bodyweight_target_retains_zero_external_load_and_source_target(raw):
    item = exercise(raw, load_semantics='bodyweight', recommended_working_weight=None)
    original = deepcopy(item)
    result = typed_tracking_feedback(item, completed_sets=0)
    assert result['recommended_weight'] == 0
    assert result['decision_trace']['set_prescription'] == item['authored_prescription']['sets'][0]
    assert item == original


def test_variant_compatibility_weight_does_not_become_a_load_recommendation():
    item = exercise(recommended_working_weight=40,
        performed_variant={'id':'confirmed-variant', 'load_semantics':'external_load'})
    original = deepcopy(item)
    result = typed_tracking_feedback(item, completed_sets=1)
    assert result['recommended_weight'] is None
    assert result['decision_trace']['load_recommendation_available'] is False
    assert result['guidance_rationale'] == 'confirmed_variant_receipt_only'
    assert item == original
