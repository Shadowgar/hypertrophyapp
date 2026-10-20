"""Declared inventory and bounded admission; synthetic engineering evidence only."""
from dataclasses import replace
from datetime import date
import math

import pytest

from core_engine.customized import inventory
from core_engine.customized import calibration
from test_customized_calibration import exposure, row, target, report
from test_customized_planner import exercise, policy


def weights(*items, kind="dumbbell", unit="kg", **extra):
    return dict(kind=kind, unit=unit, weights=[dict(weight=w, count=c) for w, c in items], **extra)


def test_dumbbell_requires_declared_count_without_inventing_steps():
    setup = weights((10, 1), (11, 2), (15, 2))
    assert inventory.attainable_loads(setup) == (10., 11., 15.)
    assert inventory.attainable_loads(setup, required_count=2) == (11., 15.)
    assert inventory.attainable_loads(weights((10, 1), (10, 1)), required_count=2) == (10.,)


def test_lb_conversion_and_declared_limits_use_exact_decimal_factor():
    setup = weights((10, 2), (20, 2), (30, 2), unit="lb", min_load=20, max_load=20)
    assert inventory.attainable_loads(setup) == (9.0718474,)


def test_barbell_uses_balanced_available_pairs_and_bar_weight():
    setup = dict(kind="barbell", unit="kg", bar_weight=20,
                 plates=[dict(weight=5, count=3), dict(weight=2.5, count=2)])
    assert inventory.attainable_loads(setup) == (20., 25., 30., 35.)
    setup["plates"] = [dict(weight=5, count=1), dict(weight=5, count=1)]
    assert inventory.attainable_loads(setup) == (20., 30.)


def test_stack_only_uses_actual_labels_or_explicit_complete_ladder():
    assert inventory.attainable_loads(weights((7, 1), (13, 1), kind="machine_stack")) == (7., 13.)
    setup = dict(kind="machine_stack", unit="lb", stack=dict(minimum=10, maximum=15, increment=2))
    assert inventory.attainable_loads(setup) == (4.5359237, 5.44310844, 6.35029318)
    assert inventory.attainable_loads(dict(kind="bodyweight", unit="kg")) == ()


@pytest.mark.parametrize("setup", [
    weights((math.nan, 1)), weights((math.inf, 1)), weights((-1, 1)), weights((True, 1)),
    weights((10, 0)), weights((10, 1.5)), weights((10, True)), weights(("10", 1)),
    weights((10**1000, 1)), weights((10, 10**10)), weights((10, 1), unit="stone"),
    weights((10, 1), min_load=11, max_load=10), weights((10, 1), min_load="5"),
    dict(kind="barbell", unit="kg", bar_weight=20, plates=[dict(weight=1, count=129)]),
    dict(kind="machine_stack", unit="kg", stack=dict(minimum=1, maximum=2000, increment=1)),
    dict(kind="machine_stack", unit="kg", stack=dict(minimum=1, maximum=10)),
    dict(kind="machine_stack", unit="kg", stack=dict(minimum=1, maximum=10, increment=0)),
    dict(kind="unrecognized", unit="kg"),
])
def test_invalid_or_unbounded_inventory_fails_closed(setup):
    with pytest.raises(ValueError):
        inventory.attainable_loads(setup)


@pytest.mark.parametrize("count", [0, -1, True, 1.5, 10**10])
def test_invalid_required_count_fails_closed(count):
    with pytest.raises(ValueError):
        inventory.attainable_loads(weights((10, 2)), required_count=count)


def test_exponential_plate_combinations_are_bounded():
    setup = dict(kind="barbell", unit="kg", bar_weight=20,
        plates=[dict(weight=2**i, count=2) for i in range(11)])
    with pytest.raises(ValueError):
        inventory.attainable_loads(setup)


def recommendation(*, next_load=11, effort=6, **kwargs):
    e = replace(exercise("horizontal_press"), attainable_loads=(10., next_load))
    exp = exposure(records=(row(1, actual_load=10, actual_effort=effort),
                            row(2, actual_load=10, actual_effort=effort)))
    args = dict(exercise=e, target=target(), policy=policy(), as_of=date(2026, 10, 26), exposures=(exp,))
    args.update(kwargs)
    return calibration.recommend_calibrated_load(**args)


def test_complete_easy_history_admits_only_real_next_load_within_provisional_bound():
    result = recommendation()
    assert result["action"] == "increase" and result["recommended_weight"] == 11
    assert result["policy_status"] == "provisional"
    assert result["version"] == calibration.BOUNDED_CALIBRATION_VERSION
    assert result["calibration"]["known_baseline"] == 10
    assert result["calibration"]["completed_sets"] == 2
    assert result["calibration"]["evidence_ids"] == ["receipt-1", "receipt-2"]
    assert "bounded_attainable_increase" in result["reason_codes"]


def test_large_inventory_gap_monitors_without_fabricating_smaller_weight():
    result = recommendation(next_load=15)
    assert result["action"] == "monitor" and result["recommended_weight"] is None
    assert "higher_attainable_outside_bound" in result["reason_codes"]
    result = recommendation(next_load=10)
    assert result["action"] == "monitor" and result["recommended_weight"] is None


def test_qualified_known_working_weight_is_held():
    result = recommendation(effort=3)
    assert result["action"] == "hold" and result["recommended_weight"] == 10


@pytest.mark.parametrize("change,reason", [
    ({"actual_effort": None}, "actual_effort_unknown_or_invalid"),
    ({"technique": "unknown"}, "technique_not_qualified"),
    ({"pain": None}, "pain_status_unknown"),
    ({"pain": True}, "pain_reported"),
    ({"performed_reps": 6}, "performed_reps_below_target"),
    ({"load_identity": None}, "recorded_load_identity_incomparable"),
])
def test_missing_or_unqualified_actual_evidence_cannot_increase(change, reason):
    exp = exposure(records=(row(1, **dict(actual_load=10, actual_effort=6) | change),
                            row(2, actual_load=10, actual_effort=6)))
    result = recommendation(exposures=(exp,))
    assert result["action"] == "monitor" and result["recommended_weight"] is None
    assert reason in result["reason_codes"]


def test_stale_or_incomplete_history_monitors():
    for exp, reason in [(exposure(performed_on=date(2025, 1, 1)), "exposure_stale_or_future"),
                        (exposure(finalized=False), "exposure_not_finalized")]:
        result = recommendation(exposures=(exp,))
        assert result["action"] == "monitor" and reason in result["reason_codes"]


def test_self_report_never_converts_strength_to_working_weight():
    result = recommendation(exposures=(), strength_reports=(report(load=100),))
    assert result["action"] == "monitor" and result["recommended_weight"] is None
    assert result["calibration"]["strength_information"][0]["load"] == 100
    assert "self_report_information_only_no_working_load_conversion" in result["reason_codes"]


def test_changed_required_workload_is_not_the_same_calibration_exposure():
    result = recommendation(required_set_indices=(1,2,3))
    assert result['action']=='monitor'
    assert 'prescribed_workload_incomparable' in result['reason_codes']


@pytest.mark.parametrize('field',['kind','unit'])
def test_unhashable_inventory_labels_are_validation_errors(field):
    setup = weights((10,2))
    setup[field]=[]
    with pytest.raises(ValueError):inventory.attainable_loads(setup)
