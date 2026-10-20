"""Original candidate program scenarios: expert review required, no prescription."""
from dataclasses import replace
from datetime import date, datetime, UTC

import pytest

from core_engine.customized.audit import content_hash, policy_content_hash
from core_engine.customized.models import DurationRange, PolicyApproval
from core_engine.customized.pilot import plan_pilot
from core_engine.customized.pilot_models import CoverageOmission
from research.m4c2.catalog import review_catalog, catalog_records
from research.m4c2.science import candidate_standard, gym_design, dumbbell_design
from research.m4c2.examples import synthetic_profile, explicit_context


def plan(**overrides):
    args = dict(profile=synthetic_profile(), catalog=review_catalog(), standard=candidate_standard("current"),
        design=gym_design(), context=explicit_context(), simulate=True)
    args.update(overrides)
    return plan_pilot(**args)


def test_complete_original_gym_week_has_actual_exercises_and_full_coverage():
    result = plan()
    assert result == plan()
    assert result.coverage_status == "complete_candidate"
    assert [len(s.exercises) for s in result.plan.sessions] == [7, 7, 7]
    assert [sum(e.sets for e in s.exercises) for s in result.plan.sessions] == [15, 15, 15]
    assert [s.local_date for s in result.plan.sessions] == [date(2026, 10, 27), date(2026, 10, 29), date(2026, 11, 1)]
    assert result.plan.sessions[0].exercises[0].exercise.name == "Seated leg press"
    assert result.plan.sessions[1].exercises[0].exercise.name == "Dumbbell Romanian deadlift"
    assert result.plan.sessions[2].exercises[0].exercise.name == "Seated chest press"
    assert result.missing_actions == () and result.missing_regions == ()
    counts = {r.region: r.primary_sets for r in result.region_totals}
    assert counts == {"quadriceps": 7, "glutes": 10, "hamstrings": 7, "chest": 5, "upper_back": 4,
        "lats": 2, "anterior_deltoid": 2, "lateral_deltoid": 4, "posterior_deltoid": 2,
        "elbow_flexors": 2, "triceps": 2, "calves": 4, "trunk": 4, "regional_distribution_unquantified": 0}
    assert result.dose_conflicts == ()
    assert result.plan.policy_status == "review_required"
    assert not result.plan.can_activate and not result.plan.prescriptive


def test_policy_and_simulation_are_explicit_even_with_local_approval_hash():
    assert not plan(standard=None).plan.sessions
    assert not plan(simulate=False).plan.sessions
    p = candidate_standard("current")
    for bound in ("forged", policy_content_hash(p.science)):
        approved = replace(p.science, status="approved", approval=PolicyApproval(bound, "claimed-reviewer", "claimed-owner"))
        result = plan(standard=replace(p, science=approved))
        assert result.plan.policy_status == "review_required"
        assert not result.plan.can_activate and not result.plan.prescriptive
    assert not plan(standard=replace(p, science=replace(p.science, status="disabled"))).plan.sessions


def test_no_silent_45_or_60_minute_guarantee():
    result = plan(profile=synthetic_profile(cap=45, cap_kind="hard"))
    assert result.plan.status == "infeasible"
    assert all(s.duration.total_seconds.high > 45 * 60 for s in result.plan.sessions)
    assert [sum(e.sets for e in s.exercises) for s in result.plan.sessions] == [15, 15, 15]
    hard60 = plan(profile=synthetic_profile(cap=60, cap_kind="hard"))
    assert hard60.plan.status == "infeasible" and hard60.plan.tradeoffs
    flexible = plan(profile=synthetic_profile(cap=60, cap_kind="flexible"))
    assert flexible.plan.status == "policy_not_approved" and flexible.plan.tradeoffs


def test_new_and_returning_policies_change_dose_and_effort_with_explicit_scope():
    for status, sets, effort in (("new", 21, (3, 4)), ("returning", 24, (3, 4))):
        result = plan(profile=synthetic_profile(status=status), standard=candidate_standard(status))
        assert sum(e.sets for s in result.plan.sessions for e in s.exercises) == sets
        assert all((e.effort_min, e.effort_max) == effort for s in result.plan.sessions for e in s.exercises)
        assert not result.plan.can_activate
    assert plan(profile=synthetic_profile(status="unknown")).plan.status == "unsupported_profile"


def test_missing_equipment_or_primary_region_never_claims_complete():
    assert plan(profile=synthetic_profile(equipment=())).plan.status == "infeasible"
    c = review_catalog()
    changed = tuple(replace(e, primary_regions=()) if e.action == "knee_flexion" else e for e in c.exercises)
    result = plan(catalog=replace(c, exercises=changed))
    assert result.coverage_status != "complete_candidate"
    assert "hamstrings" in result.missing_regions or result.plan.status == "invalid_input"


def test_dumbbell_case_reports_absent_vertical_pull_and_knee_flexion_until_accepted():
    p = synthetic_profile(gym=False, cap=45, cap_kind="hard", status="returning")
    result = plan(profile=p, standard=candidate_standard("returning"), design=dumbbell_design())
    assert result.coverage_status == "incomplete"
    assert {"knee_flexion", "vertical_pull"} <= set(result.missing_actions)
    assert result.plan.status == "infeasible"
    omissions = tuple(CoverageOmission("action", action, "No equipped variant; no equivalent growth claimed", "synthetic-review-consent") for action in result.missing_actions)
    # The hinge supplies two hamstring-primary sets, below the returning
    # candidate band of three. Approving missing actions cannot waive that dose.
    omissions += tuple(CoverageOmission("dose", r, "Reduced direct work acknowledged", "synthetic-review-consent") for r in result.dose_conflicts)
    accepted = plan(profile=replace(p, session_cap_minutes=60), standard=candidate_standard("returning"),
        design=dumbbell_design(), accepted_omissions=omissions)
    assert accepted.coverage_status == "accepted_limited_candidate"
    assert all(set(e.exercise.required_equipment) <= set(p.confirmed_equipment) for s in accepted.plan.sessions for e in s.exercises)
    assert all(e.exercise.load_identity.implement in {"dumbbell", "bodyweight"} for s in accepted.plan.sessions for e in s.exercises)
    assert accepted.plan.tradeoffs and not accepted.plan.can_activate


def test_unknown_rir_pain_and_exercise_substitution_do_not_inherit_load():
    from research.m4c2.examples import synthetic_exposure
    exp = synthetic_exposure()
    good = plan(exposures=(exp,))
    chosen = next(e for s in good.plan.sessions for e in s.exercises if e.exercise.variant_id == exp.identity.variant_id)
    assert chosen.calibration.working_load == 20
    easy = replace(exp, records=tuple(replace(r, actual_effort=6) for r in exp.records))
    result = plan(exposures=(easy,))
    assert any(e.calibration.possibly_underchallenging for s in result.plan.sessions for e in s.exercises)
    for fields in (dict(pain=True), dict(technique="poor"), dict(actual_effort=None)):
        bad = replace(exp, records=tuple(replace(r, **fields) for r in exp.records))
        result = plan(exposures=(bad,))
        assert all(e.calibration.working_load is None for s in result.plan.sessions for e in s.exercises)
    db = plan(profile=synthetic_profile(gym=False), design=dumbbell_design(), exposures=(exp,))
    assert all(e.calibration.working_load is None for s in db.plan.sessions for e in s.exercises)


def test_optional_1rm_is_information_and_no_available_increment_is_invented():
    from research.m4c2.examples import synthetic_exposure
    from core_engine.customized.models import StrengthReport
    exp = synthetic_exposure()
    report = StrengthReport("optional", "1rm", exp.identity, date(2026, 10, 25), 30, True, "synthetic-report", None)
    result = plan(strength_reports=(report,))
    assert all(e.calibration.working_load is None for s in result.plan.sessions for e in s.exercises)
    assert any(e.calibration.strength_information for s in result.plan.sessions for e in s.exercises)
    c = review_catalog()
    c = replace(c, exercises=tuple(replace(e, attainable_loads=(20,)) if e.variant_id == exp.identity.variant_id else e for e in c.exercises))
    easy = replace(exp, records=tuple(replace(r, actual_effort=6) for r in exp.records))
    result = plan(catalog=c, exposures=(easy,))
    matched = [e for s in result.plan.sessions for e in s.exercises if e.exercise.variant_id == exp.identity.variant_id]
    assert all(e.calibration.attainable_next_load is None for e in matched)


def test_returning_with_lower_confirmed_skill_requires_skill_review():
    result = plan(profile=replace(synthetic_profile(status="returning"), max_skill="basic"), standard=candidate_standard("returning"))
    assert result.plan.status == "infeasible"
    assert any("skill_not_confirmed" in r.reasons for selection in result.plan.selections for r in selection.rejected)


def test_missing_date_does_not_carry_or_skip_and_dst_retains_local_sunday():
    p = synthetic_profile()
    assert not plan(profile=replace(p, selected_dates=p.selected_dates[:2])).plan.sessions
    assert plan().plan.sessions[-1].local_date == date(2026, 11, 1)
    past = replace(explicit_context(), planning_instant=datetime(2026, 10, 28, 12, tzinfo=UTC))
    assert "past_selected_date_unsupported" in plan(context=past).plan.reasons


def test_falsified_or_incompatible_catalog_provenance_fails_closed():
    records = catalog_records()
    wrong = replace(records[0], checked_description="changed without requalification")
    with pytest.raises(ValueError, match="content|provenance"):
        review_catalog(records=(wrong, *records[1:]))
    mismatched = replace(records[0], source_action="elbow_flexion")
    with pytest.raises(ValueError, match="action|provenance"):
        review_catalog(records=(mismatched, *records[1:]))


def test_dose_band_violation_and_unknown_source_never_turn_into_silent_repairs():
    p = candidate_standard("current")
    science = replace(p.science, doses=tuple(replace(d, sets=6, emphasis_sets=7) for d in p.science.doses))
    result = plan(standard=replace(p, science=science))
    assert result.dose_conflicts and result.plan.status == "infeasible"
    assert any(e.sets >= 6 for s in result.plan.sessions for e in s.exercises)


def test_unknown_exposure_is_reported_and_secondary_work_is_not_added_to_direct():
    result = plan()
    unknown = next(r for r in result.region_totals if r.region == "regional_distribution_unquantified")
    assert unknown.unknown_sets == 45 and unknown.primary_sets == 0
    rows = {r.region:r for r in result.region_totals}
    assert rows["triceps"].primary_sets == 2 and rows["triceps"].secondary_sets == 7


def test_catalog_variants_are_not_ranked_as_universal_best_and_preference_changes_real_selection():
    preferred = replace(synthetic_profile(), preferred_variants=("db_bench_press",))
    result = plan(profile=preferred)
    assert all(e.exercise.variant_id == "db_bench_press" for s in result.plan.sessions for e in s.exercises if e.exercise.action == "horizontal_press")
    assert result.plan.trace.profile_hash != plan().plan.trace.profile_hash
    assert all(not e.metadata_qualified for e in review_catalog().exercises)


def test_single_set_calibration_does_not_qualify_a_larger_prescribed_workload():
    from research.m4c2.examples import synthetic_exposure
    exp = synthetic_exposure()
    one = replace(exp, exercise_occurrence_id="explicit-completed-calibration", required_set_indices=(1,),
        records=(replace(exp.records[0], actual_effort=6),))
    result = plan(exposures=(one,))
    press = next(e for s in result.plan.sessions for e in s.exercises if e.exercise.variant_id == exp.identity.variant_id)
    assert not press.calibration.possibly_underchallenging
    assert press.calibration.working_load is None
    assert "prescribed_workload_incomparable" in press.calibration.reasons


def test_blank_or_irrelevant_tradeoff_confirmation_cannot_authorize_omission():
    bad = CoverageOmission("action", "vertical_pull", "", "")
    assert plan(accepted_omissions=(bad,)).plan.status == "invalid_input"
    bad = replace(bad, reason="claimed", confirmation_reference="synthetic")
    assert plan(accepted_omissions=(bad,)).plan.status == "invalid_input"


def test_unilateral_both_side_execution_time_is_not_halved():
    original = plan()
    c = review_catalog()
    c = replace(c, exercises=tuple(e for e in c.exercises if e.variant_id != "gym_high_row"))
    p = replace(synthetic_profile(), preferred_variants=("db_supported_row",))
    unilateral = plan(profile=p,catalog=c)
    assert unilateral.plan.sessions[0].duration.work_seconds.low == original.plan.sessions[0].duration.work_seconds.low + 90
    assert unilateral.plan.sessions[0].duration.work_seconds.high == original.plan.sessions[0].duration.work_seconds.high + 140


def test_missing_standard_and_authored_profile_cannot_generate_and_c1_stays_separate():
    from core_engine.customized.planner import plan_full_body
    assert plan(profile=replace(synthetic_profile(),mode="authored")).plan.status == "consent_required"
    result = plan_full_body(profile=synthetic_profile(), catalog=review_catalog(), policy=candidate_standard("current").science,
        context=explicit_context(), allow_provisional_preview=True)
    assert result.status == "invalid_input" and not result.sessions


def test_shorter_gym_candidate_fits_60_only_as_explicit_limited_dose_tradeoff():
    from research.m4c2.science import shorter_gym_standard
    standard = shorter_gym_standard()
    p = synthetic_profile(cap=60, cap_kind="hard")
    result = plan(profile=p, standard=standard)
    assert result.plan.status == "infeasible"
    assert result.missing_actions == result.missing_regions == ()
    assert set(result.dose_conflicts) == {"lateral_deltoid", "posterior_deltoid", "elbow_flexors", "triceps", "calves", "trunk"}
    assert [sum(e.sets for e in s.exercises) for s in result.plan.sessions] == [11, 11, 11]
    assert [s.duration.total_seconds.high / 60 for s in result.plan.sessions] == [57.5, 59, 57.5]
    assert all(e.effort_min == 1 and e.effort_max == 3 for s in result.plan.sessions for e in s.exercises)
    acceptance = tuple(CoverageOmission("dose", r, "Explicit synthetic time/dose tradeoff", "test-short-review") for r in result.dose_conflicts)
    limited = plan(profile=p, standard=standard, accepted_omissions=acceptance)
    assert limited.coverage_status == "accepted_limited_candidate" and limited.plan.status == "policy_not_approved"
    assert not limited.plan.can_activate and not limited.plan.prescriptive
    hard45 = plan(profile=replace(p, session_cap_minutes=45), standard=standard, accepted_omissions=acceptance)
    assert hard45.plan.status == "infeasible"
    assert "hard_session_cap_exceeded" in hard45.plan.reasons
    assert [sum(e.sets for e in s.exercises) for s in plan().plan.sessions] == [15, 15, 15]


def test_shorter_candidate_preserves_rest_and_time_inputs_and_exposes_actual_primary_loss():
    from research.m4c2.science import shorter_gym_standard
    original, short = candidate_standard("current"), shorter_gym_standard()
    assert short.science.warmup_seconds == original.science.warmup_seconds
    assert short.science.transition_seconds == original.science.transition_seconds
    assert short.science.margin_seconds == original.science.margin_seconds
    assert short.direct_region_bands == original.direct_region_bands
    assert [(d.action,d.rest_seconds) for d in short.science.doses] == [(d.action,d.rest_seconds) for d in original.science.doses]
    result = plan(standard=short)
    counts = {r.region:r.primary_sets for r in result.region_totals}
    assert counts == {"quadriceps":6,"glutes":8,"hamstrings":6,"chest":4,"upper_back":4,"lats":2,
        "anterior_deltoid":2,"lateral_deltoid":2,"posterior_deltoid":1,"elbow_flexors":1,"triceps":1,
        "calves":2,"trunk":2,"regional_distribution_unquantified":0}
