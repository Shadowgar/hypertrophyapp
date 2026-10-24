"""Owner-approved initial estimates: source fidelity and exact-setup abstention."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json

import pytest

from core_engine import load_intelligence

PROGRAM = 'pure_bodybuilding_phase_1_full_body'
TODAY = date(2026, 10, 23)


def exercise():
    return {'id': 'cross_body_lat_pull_around', 'equipment_tags': ['cable'],
        'load_semantics': 'external_load',
        'source_lineage': {'source_program_id': PROGRAM, 'source_slot': 1},
        'authored_constraint': {'status': 'ready'},
        'authored_prescription': {'raw': {'warm_up_sets': '1.0'}, 'sets': [
            {'set_index': 1, 'set_type': 'work', 'rep_target': {'kind': 'reps', 'min': 10, 'max': 12},
             'effort_target': {'kind': 'rpe', 'min': 7, 'max': 8}, 'intensity_technique': None},
            {'set_index': 2, 'set_type': 'work', 'rep_target': {'kind': 'reps', 'min': 10, 'max': 12},
             'effort_target': {'kind': 'rpe', 'min': 8, 'max': 9}, 'intensity_technique': 'Long-length partials'}]}}


def calibration(**fields):
    return {'method': 'known_1rm', 'load': 100, 'unit': 'lb', 'observed_date': '2026-10-20',
        'confirmed': True, 'variant_id': 'cross_body_lat_pull_around',
        'setup_details': 'Right side, full ROM, same cable/grip/settings',
        'attainable': {'unit': 'lb', 'min': 5, 'step': 2.5, 'max': 100}, **fields}


def context(**fields):
    return {'unit': 'kg', 'basis': 'machine_stack', 'equipment_key': 'cable-1',
        'display_unit': 'lb', 'equipment_tags': ['cable'], **fields}


def decide(*, ex=None, cal=None, load=None, **fields):
    owner = getattr(load_intelligence, 'decide_initial_working_load', None)
    assert callable(owner), 'Initial-load decision must belong to the existing load owner'
    return owner(exercise=exercise() if ex is None else ex, program_id=PROGRAM,
        calibration=calibration() if cal is None else cal, load_context=context() if load is None else load,
        today=TODAY, **fields)


def unavailable(result, reason):
    assert result['status'] == 'unavailable'
    assert result['recommended_working_weight'] is None
    assert reason in result['reason_codes']
    assert result['explanation']
    json.dumps(result, allow_nan=False)


def test_known_benchmark_is_rep_aware_provisional_and_never_a_performed_record():
    result = decide()
    assert result['status'] == 'provisional'
    assert result['recommended_working_weight'] == 29.48350405  # 65 lb
    assert result['reported_1rm'] == 45.359237
    assert result['estimated_1rm'] is None
    assert result['decision_trace']['calculations']['target_reps'] == '12'
    assert result['decision_trace']['calculations']['provisional_target_rir'] == '3'
    ex = exercise()
    ex['authored_prescription']['sets'][0]['rep_target'] = {'kind': 'reps', 'min': 8, 'max': 10}
    assert decide(ex=ex)['recommended_working_weight'] == 30.617484975  # 67.5 lb


def test_recent_set_rir_estimate_is_distinct_from_reported_1rm():
    result = decide(cal=calibration(method='recent_set', load=40, reps=8, rir=2))
    assert result['recommended_working_weight'] == 15.87573295  # 35 lb
    assert result['reported_1rm'] is None
    assert result['estimated_1rm'] == pytest.approx(24.191593066666666)
    assert decide(cal=calibration(method='recent_set', reps=1, rir=0))['estimated_1rm'] == 45.359237


def test_equivalent_units_replay_deterministically_without_source_or_input_mutation():
    ex, cal, load = exercise(), calibration(), context()
    before = deepcopy((ex, cal, load))
    result = decide(ex=ex, cal=cal, load=load)
    assert result == decide(ex=ex, cal=cal, load=load)
    assert (ex, cal, load) == before
    equivalent = decide(cal=calibration(load=45.359237, unit='kg'))
    assert equivalent['recommended_working_weight'] == result['recommended_working_weight']
    assert equivalent['decision_trace']['calculations'] == result['decision_trace']['calculations']
    result['decision_trace']['source_prescription']['sets'].clear()
    assert ex == before[0]


@pytest.mark.parametrize('flags,reason', [({'has_current_work': True}, 'current_working_sets_take_precedence'),
    ({'has_effective_history': True}, 'effective_history_takes_precedence')])
def test_any_effective_work_wins_even_when_incomplete_or_missing_effort(flags, reason):
    unavailable(decide(**flags), reason)


@pytest.mark.parametrize('field,value,reason', [
    ('load', True, 'calibration_load_invalid'), ('load', 0, 'calibration_load_invalid'),
    ('load', -1, 'calibration_load_invalid'), ('load', float('nan'), 'calibration_load_invalid'),
    ('load', float('inf'), 'calibration_load_invalid'), ('load', '100', 'calibration_load_invalid'),
    ('unit', None, 'calibration_unit_unknown'), ('unit', 'lbs', 'calibration_unit_unknown'),
    ('observed_date', '2026-10-24', 'calibration_date_invalid'),
    ('observed_date', '2026-02-30', 'calibration_date_invalid'), ('observed_date', None, 'calibration_date_invalid'),
    ('confirmed', False, 'exact_setup_confirmation_required'), ('confirmed', 1, 'exact_setup_confirmation_required'),
    ('variant_id', 'other', 'performed_variant_mismatch'),
    ('setup_details', ' ', 'setup_details_required'), ('method', 'legacy_rpe', 'calibration_method_unsupported'),
    ('attainable', None, 'attainable_loads_invalid'),
])
def test_invalid_calibration_never_infers_a_weight(field, value, reason):
    unavailable(decide(cal=calibration(**{field: value})), reason)


@pytest.mark.parametrize('reps,rir', [(0, 1), (11, 0), (True, 1), (1.5, 1), (8, None),
    (8, True), (8, -1), (8, 4), (8, 3), (8, float('nan')), (8, float('inf'))])
def test_recent_set_requires_explicit_bounded_reps_and_rir(reps, rir):
    unavailable(decide(cal=calibration(method='recent_set', reps=reps, rir=rir)), 'recent_set_evidence_invalid')


@pytest.mark.parametrize('basis', ['bodyweight', 'assistance', 'added_bodyweight', None])
def test_unsupported_basis_never_becomes_external_load(basis):
    unavailable(decide(load=context(basis=basis)), 'load_basis_unknown_or_unsupported')


@pytest.mark.parametrize('field,value,reason', [('equipment_key', '', 'equipment_identity_required'),
    ('equipment_tags', [], 'equipment_unavailable'), ('equipment_tags', ['barbell'], 'equipment_unavailable'),
    ('unit', 'lb', 'recorded_load_unit_unknown'), ('load_semantics', 'bodyweight', 'load_semantics_unsupported_or_contradictory')])
def test_missing_or_incompatible_load_context_abstains(field, value, reason):
    unavailable(decide(load=context(**{field: value})), reason)


@pytest.mark.parametrize('first_change,reason', [
    ({'set_type': 'drop'}, 'first_working_set_not_ordinary'),
    ({'intensity_technique': 'partials'}, 'first_working_set_not_ordinary'),
    ({'rep_target': {'kind': 'amrap'}}, 'initial_rep_target_unsupported'),
    ({'rep_target': {'kind': 'reps', 'min': 4, 'max': 5}}, 'initial_rep_target_unsupported'),
    ({'rep_target': {'kind': 'reps', 'min': 12, 'max': 13}}, 'initial_rep_target_unsupported'),
    ({'effort_target': {'kind': 'rpe', 'min': 6, 'max': 8}}, 'initial_effort_target_unsupported'),
    ({'effort_target': {'kind': 'rir', 'min': 2, 'max': 3}}, 'initial_effort_target_unsupported'),
    ({'effort_target': {'kind': 'rpe', 'min': 7, 'max': 11}}, 'initial_effort_target_unsupported'),
    ({'hard_load_instruction': 'use 50 kg'}, 'source_hard_load_instruction')])
def test_first_source_set_remains_authoritative(first_change, reason):
    ex = exercise()
    ex['authored_prescription']['sets'][0].update(first_change)
    unavailable(decide(ex=ex), reason)


@pytest.mark.parametrize('change,reason', [
    ({'authored_constraint': {'status': 'unresolved'}}, 'authored_constraint_unresolved'),
    ({'authored_constraint': {'status': 'confirmed', 'execution_status': 'infeasible'}}, 'authored_constraint_unresolved'),
    ({'pain': True}, 'pain_or_unsafe_report'), ({'unsafe': True}, 'pain_or_unsafe_report'),
    ({'load_semantics': 'added_bodyweight'}, 'load_semantics_unsupported_or_contradictory'),
    ({'load_semantics': 'per_hand'}, 'load_semantics_unsupported_or_contradictory'),
    ({'performed_variant': {'id': 'other'}}, 'performed_variant_mismatch')])
def test_source_context_never_grants_unrelated_authority(change, reason):
    unavailable(decide(ex={**exercise(), **change}), reason)


@pytest.mark.parametrize('attainable,expected', [
    ({'unit': 'lb', 'values': [70, 5, 65, 60]}, 29.48350405),
    ({'unit': 'lb', 'min': 62, 'step': 3, 'max': 99}, 29.48350405),
    ({'unit': 'lb', 'min': 5, 'step': 2.5, 'max': 40}, 18.1436948),
    ({'unit': 'kg', 'values': [29.48350405, 31]}, 29.48350405),
])
def test_attainable_selection_floors_respecting_declared_origin_and_maximum(attainable, expected):
    assert decide(cal=calibration(attainable=attainable))['recommended_working_weight'] == expected


@pytest.mark.parametrize('attainable', [
    {}, {'unit': 'lb', 'values': []}, {'unit': 'lb', 'values': [0, 65]},
    {'unit': 'lb', 'values': [True, 65]}, {'unit': 'lb', 'values': [float('inf')]},
    {'unit': 'lb', 'values': [5] * 1001}, {'unit': 'lb', 'min': 0, 'step': 2.5, 'max': 100},
    {'unit': 'lb', 'min': 5, 'step': 0, 'max': 100}, {'unit': 'lb', 'min': 50, 'step': 5, 'max': 20},
    {'unit': 'lb', 'values': [65], 'min': 5, 'step': 2.5, 'max': 100}])
def test_invalid_attainable_declarations_do_not_fall_back_to_compatibility_grid(attainable):
    unavailable(decide(cal=calibration(attainable=attainable)), 'attainable_loads_invalid')


def test_below_smallest_attainable_load_never_rounds_up():
    unavailable(decide(cal=calibration(attainable={'unit': 'lb', 'values': [70, 80]})), 'no_attainable_load_at_or_below_estimate')


def test_only_authored_phase_one_and_two_admit_initial_estimates():
    owner = getattr(load_intelligence, 'decide_initial_working_load', None)
    assert callable(owner)
    for program in (PROGRAM, 'pure_bodybuilding_phase_2_full_body'):
        ex = exercise()
        ex['source_lineage']['source_program_id'] = program
        assert owner(exercise=ex, program_id=program, calibration=calibration(), load_context=context(), today=TODAY)['status'] == 'provisional'
    unavailable(owner(exercise=exercise(), program_id='customized', calibration=calibration(), load_context=context(), today=TODAY), 'authored_program_unqualified')


def test_source_warmup_can_explicitly_use_provisional_load_and_same_attainable_floor():
    from core_engine.authored_warmups import build_authored_warmup_guidance
    from test_authored_warmups import protocol
    ex, initial = exercise(), decide()
    result = build_authored_warmup_guidance(exercise=ex, working_decision={}, load_context=context(),
        program_id=PROGRAM, source_protocol=protocol(), provisional_decision=initial)
    assert result['status'] == 'suggested'
    assert result['count'] == 1
    assert result['sets'] == [{'set_index': 1, 'suggested_weight': 17.009713875,
        'reps_min': 6, 'reps_max': 10, 'percent': 60}]  # 60% of 65 lb => floor 37.5 lb
    assert result['decision_trace']['provisional_working_weight'] == 29.48350405
    assert result['decision_trace']['qualified_working_weight'] is None
    assert 'provisional' in result['explanation'].lower()


def test_stale_or_tampered_provisional_warmup_input_cannot_supply_a_number():
    from core_engine.authored_warmups import build_authored_warmup_guidance
    from test_authored_warmups import protocol
    initial = decide()
    initial['recommended_working_weight'] = 500
    result = build_authored_warmup_guidance(exercise=exercise(), working_decision={}, load_context=context(),
        program_id=PROGRAM, source_protocol=protocol(), provisional_decision=initial)
    assert result['status'] == 'manual'
    assert all(row['suggested_weight'] is None for row in result['sets'])


def test_qualified_history_warmup_load_wins_over_optional_provisional_input():
    from core_engine.authored_warmups import build_authored_warmup_guidance
    from test_authored_warmups import protocol
    result = build_authored_warmup_guidance(exercise=exercise(),
        working_decision={'scope': 'next_exposure', 'prefill_available': True, 'recommended_weight': 100},
        load_context=context(increment=2.5, increment_unit='kg'), program_id=PROGRAM,
        source_protocol=protocol(), provisional_decision=decide())
    assert result['sets'][0]['suggested_weight'] == 60
    assert result['decision_trace']['qualified_working_weight'] == 100
    assert result['decision_trace']['provisional_working_weight'] is None


def test_wrapped_provisional_result_retains_warmup_eligibility():
    from core_engine.authored_warmups import build_authored_warmup_guidance
    from test_authored_warmups import protocol
    initial = {**decide(), 'id': 'recommendation-1', 'scope': 'initial', 'evidence_revision': 'revision-1'}
    initial['decision_trace'].update(history_scope={'cutoff': 'today'}, calibration_id='cal-1', calibration_revision=1)
    result = build_authored_warmup_guidance(exercise=exercise(), working_decision={}, load_context=context(),
        program_id=PROGRAM, source_protocol=protocol(), provisional_decision=initial)
    assert result['status'] == 'suggested'
    assert result['sets'][0]['suggested_weight'] == 17.009713875


def test_boolean_source_set_identity_cannot_be_first_work_set():
    ex = exercise()
    ex['authored_prescription']['sets'][0]['set_index'] = True
    unavailable(decide(ex=ex), 'first_working_set_not_ordinary')


@pytest.mark.parametrize('upper,rpe', [(6, 7), (12, 10)])
def test_inclusive_source_target_bounds_are_supported(upper, rpe):
    ex = exercise()
    first = ex['authored_prescription']['sets'][0]
    first['rep_target'] = {'kind': 'reps', 'min': upper, 'max': upper}
    first['effort_target'] = {'kind': 'rpe', 'min': rpe, 'max': rpe}
    assert decide(ex=ex)['status'] == 'provisional'


def test_recent_report_exact_grid_tie_never_loses_an_increment_to_intermediate_rounding():
    ex = exercise()
    ex['authored_prescription']['sets'][0]['rep_target'] = {'kind': 'reps', 'min': 8, 'max': 8}
    ex['authored_prescription']['sets'][0]['effort_target'] = {'kind': 'rpe', 'min': 8, 'max': 8}
    result = decide(ex=ex, cal=calibration(method='recent_set', load=40, reps=8, rir=2))
    assert result['recommended_working_weight'] == 18.1436948  # Exactly the reported 40 lb


@pytest.mark.parametrize('load', [1e308, 1e-300, 10 ** 400])
def test_extreme_numbers_never_crash_or_emit_nonfinite_canonical_weights(load):
    result = decide(cal=calibration(method='recent_set', load=load, unit='kg', reps=10, rir=0))
    json.dumps(result, allow_nan=False)
    assert result['status'] in {'provisional', 'unavailable'}


def test_confirmed_variant_uses_its_equipment_and_exercise_identity():
    ex = exercise()
    ex['performed_variant'] = {'exercise_id': 'lat_variant', 'id': 'option-1', 'equipment_tags': ['cable'], 'load_semantics': 'external_load'}
    ex['authored_constraint'] = {'status': 'confirmed', 'execution_status': 'ready'}
    assert decide(ex=ex, cal=calibration(variant_id='lat_variant'))['status'] == 'provisional'


def test_alternative_equipment_tags_do_not_require_every_catalog_alternative():
    ex = exercise()
    ex['equipment_tags'] = ['cable', 'machine']
    assert decide(ex=ex)['status'] == 'provisional'


def test_provisional_result_has_an_explicit_nonempty_reason_for_consumers():
    result = decide()
    assert result['reason_codes'] == ['provisional_initial_load_estimate']
    assert result['decision_trace']['reason_codes'] == result['reason_codes']


def test_initial_arithmetic_is_independent_of_the_callers_decimal_context():
    from decimal import localcontext, ROUND_UP
    expected = decide()
    with localcontext() as caller:
        caller.prec = 6
        caller.rounding = ROUND_UP
        assert decide() == expected
