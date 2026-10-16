"""Synthetic engineering scenarios, never approved training prescriptions."""
from dataclasses import replace
from datetime import date, datetime, UTC
from hashlib import sha256

import pytest

from core_engine.customized.models import (
    ActionDose, CustomizedProfile, DurationRange, Exercise, ExerciseCatalog,
    LoadIdentity, PlanningContext, SciencePolicy, CalibrationPolicy, SourceRef,
)
from core_engine.customized.planner import plan_full_body


SOURCE = SourceRef("synthetic-engineering-fixture", "fixture-v1", sha256(b"synthetic").hexdigest())


def context(**overrides):
    return replace(PlanningContext(
        version="c1-context-v1", planning_instant=datetime(2026, 10, 26, 12, tzinfo=UTC),
        week_start=date(2026, 10, 26), previous_training_date=None, next_training_date=None,
    ), **overrides)


def profile(**overrides):
    return replace(CustomizedProfile(
        version="c1-profile-v1", mode="customized", consent_reference="synthetic-consent",
        goal="hypertrophy", training_status="current", selected_dates=(date(2026, 10, 27), date(2026, 10, 29), date(2026, 11, 1)),
        timezone="America/New_York", session_cap_minutes=60, cap_kind="hard",
        confirmed_equipment=("dumbbell", "floor"), max_skill="basic", restrictions=(),
        excluded_variants=(), preferred_variants=(), preferred_stability=None,
        origins=(("equipment", "synthetic-user-confirmed"),), unsupported_controls=(),
    ), **overrides)


def exercise(action, variant=None, *, implement="dumbbell", **overrides):
    variant = variant or f"db-{action}"
    return replace(Exercise(
        variant_id=variant, name=f"Synthetic {action}", action=action,
        required_equipment=(implement, "floor"), restriction_tags=(), stability="unsupported", skill="basic",
        load_identity=LoadIdentity(variant, implement, f"synthetic-{implement}-1", "declared-full", "fixture-setup", "kg", "per_hand"),
        attainable_loads=(5.0, 7.0, 9.0, 11.0),
        primary_regions=(f"{action}-primary",), secondary_regions=("shared-secondary",), unknown_regions=("unclassified-region",),
        setup_seconds=DurationRange(30, 60), work_seconds_per_set=DurationRange(30, 45),
        sources=(SOURCE,), metadata_qualified=False,
    ), **overrides)


def catalog(*extra, **overrides):
    return replace(ExerciseCatalog("c1-catalog-v1", tuple(exercise(a) for a in ("knee_extension", "hip_extension", "horizontal_press", "horizontal_pull")) + extra, (SOURCE,)), **overrides)


def policy(**overrides):
    return replace(SciencePolicy(
        version="synthetic-policy-v1", status="provisional", goal="hypertrophy", training_status="current",
        doses=tuple(ActionDose(a, sets=2, emphasis_sets=3, reps_min=7, reps_max=11,
            effort_kind="rir", effort_min=2, effort_max=3, rest_seconds=DurationRange(60, 90))
            for a in ("knee_extension", "hip_extension", "horizontal_press", "horizontal_pull")),
        warmup_seconds=DurationRange(240, 360), transition_seconds=DurationRange(30, 60),
        margin_seconds=DurationRange(120, 180), minimum_gap_days=1,
        calibration=CalibrationPolicy(history_max_age_days=21, self_report_max_age_days=14,
            minimum_completed_sets=2, underchallenge_rir=5, underchallenge_rpe=5),
        sources=(SOURCE,), approval=None,
    ), **overrides)


def preview(**kwargs):
    args = dict(profile=profile(), catalog=catalog(), policy=policy(), context=context(), allow_provisional_preview=True)
    args.update(kwargs)
    return plan_full_body(**args)


def test_replay_preserves_selected_dates_and_distinct_original_emphases():
    result = preview()
    assert result == preview()
    assert tuple(s.local_date for s in result.sessions) == (date(2026, 10, 27), date(2026, 10, 29), date(2026, 11, 1))
    assert [s.emphasis for s in result.sessions] == ["knee_extension", "hip_extension", "push"]
    assert all(len(s.exercises) == 4 for s in result.sessions)
    assert [s.exercises[0].exercise.action for s in result.sessions] == ["knee_extension", "hip_extension", "horizontal_press"]
    assert result.can_activate is False and result.prescriptive is False
    assert result.status == "policy_not_approved"
    assert "adjacent_week_context_unknown" in result.reasons
    assert len(result.trace.policy_hash) == len(result.trace.catalog_hash) == 64
    assert result.trace.owner == "customized-full-body-c1-v1"


def test_missing_disabled_and_unapproved_policy_cannot_silently_prescribe():
    for args in (dict(policy=None), dict(policy=policy(status="disabled")), dict(allow_provisional_preview=False)):
        result = preview(**args)
        assert result.status == "policy_not_approved" and result.sessions == ()
        assert not result.can_activate


@pytest.mark.parametrize("p", [profile(mode="authored"), profile(mode="auto"), profile(consent_reference="")])
def test_manual_auto_and_authored_never_confer_customization_consent(p):
    result = preview(profile=p)
    assert result.status == "consent_required" and not result.sessions


@pytest.mark.parametrize("p,reason", [
    (profile(selected_dates=(date(2026, 10, 27),) * 3), "selected_dates_must_be_three_distinct_dates"),
    (profile(selected_dates=(date(2026, 10, 27), date(2026, 10, 29), date(2026, 11, 2))), "selected_date_outside_week"),
    (profile(timezone="bad/timezone"), "invalid_iana_timezone"),
    (profile(goal="strength"), "policy_profile_not_supported"),
    (profile(training_status="returning"), "policy_profile_not_supported"),
    (profile(unsupported_controls=("pain-diagnosis",)), "unsupported_profile_controls"),
])
def test_invalid_or_unsupported_profile_abstains(p, reason):
    result = preview(profile=p)
    assert reason in result.reasons and not result.sessions


def test_dumbbell_only_filters_all_unavailable_implements_and_explains_rejections():
    c = catalog(*(exercise("horizontal_press", f"a-{i}", implement=i) for i in ("barbell", "cable", "machine")))
    result = preview(catalog=c)
    assert all(e.exercise.load_identity.implement == "dumbbell" for s in result.sessions for e in s.exercises)
    assert {r.variant_id for r in result.selections[0].rejected if "equipment_unavailable" in r.reasons} == {"a-barbell", "a-cable", "a-machine"}


def test_preferences_change_feasible_selection_but_never_override_hard_constraints():
    alternate = exercise("horizontal_press", "alternate")
    result = preview(catalog=catalog(alternate), profile=profile(preferred_variants=("alternate",)))
    assert all(next(e for e in s.exercises if e.exercise.action == "horizontal_press").exercise.variant_id == "alternate" for s in result.sessions)
    blocked = preview(catalog=catalog(alternate), profile=profile(preferred_variants=("alternate",), excluded_variants=("alternate",)))
    assert all(e.exercise.variant_id != "alternate" for s in blocked.sessions for e in s.exercises)
    assert result.trace.profile_hash != blocked.trace.profile_hash


def test_missing_equipment_restriction_and_skill_do_not_drop_required_actions():
    for p, c in [
        (profile(confirmed_equipment=()), catalog()),
        (profile(restrictions=("no-hinge",)), catalog(exercises=tuple(replace(e, restriction_tags=("no-hinge",)) if e.action == "hip_extension" else e for e in catalog().exercises))),
        (profile(), catalog(exercises=tuple(replace(e, skill="advanced") if e.action == "hip_extension" else e for e in catalog().exercises))),
    ]:
        result = preview(profile=p, catalog=c)
        assert result.status == "infeasible"
        assert "required_action_unavailable" in result.reasons
        assert result.sessions == ()
        assert result.tradeoffs


def test_planned_primary_secondary_and_unknown_ledger_do_not_invent_fractional_equivalence():
    result = preview()
    assert sum(row.sets for row in result.exposure_ledger if row.involvement == "primary") == 27
    assert sum(row.sets for row in result.exposure_ledger if row.involvement == "secondary") == 27
    assert sum(row.sets for row in result.exposure_ledger if row.involvement == "unknown") == 27
    assert all(row.evidence_kind == "planned" for row in result.exposure_ledger)
    assert all(not e.exercise.metadata_qualified for s in result.sessions for e in s.exercises)
    assert "exercise_ontology_unqualified" in result.reasons


def test_full_time_budget_52_minutes_fails_hard_45_without_truncating():
    # Four slots: nine work sets. 8 warmup + 12 work + 20 rest + 8 setup/transition + 4 margin = 52.
    c = catalog(exercises=tuple(replace(e, setup_seconds=DurationRange(75, 75), work_seconds_per_set=DurationRange(80, 80)) for e in catalog().exercises))
    p = policy(doses=tuple(replace(d, rest_seconds=DurationRange(240, 240)) for d in policy().doses),
        warmup_seconds=DurationRange(480, 480), transition_seconds=DurationRange(60, 60), margin_seconds=DurationRange(240, 240))
    result = preview(profile=profile(session_cap_minutes=45), catalog=c, policy=p)
    assert result.status == "infeasible"
    assert result.sessions[0].duration.total_seconds == DurationRange(3120, 3120)
    assert sum(e.sets for e in result.sessions[0].exercises) == 9
    assert result.sessions[0].duration.status == "over_cap"
    assert "hard_session_cap_exceeded" in result.reasons and result.tradeoffs
    flexible = preview(profile=profile(session_cap_minutes=45, cap_kind="flexible"), catalog=c, policy=p)
    assert flexible.sessions[0].duration.status == "over_flexible_target"
    assert flexible.status == "policy_not_approved"


def test_uncertain_time_range_cannot_claim_hard_cap_feasibility():
    p = policy(warmup_seconds=DurationRange(0, 3600))
    result = preview(profile=profile(session_cap_minutes=45), policy=p)
    assert result.status == "infeasible"
    assert result.sessions[0].duration.status == "uncertain_over_cap"


def test_neighbor_spacing_never_moves_or_skips_dates():
    result = preview(policy=policy(minimum_gap_days=2), context=context(previous_training_date=date(2026, 10, 26)))
    assert result.status == "infeasible" and "schedule_spacing_conflict" in result.reasons
    assert tuple(s.local_date for s in result.sessions) == profile().selected_dates


def test_policy_content_changes_hash_and_actual_dose():
    changed = policy(doses=tuple(replace(d, sets=4, emphasis_sets=5) for d in policy().doses))
    first, second = preview(), preview(policy=changed)
    assert first.trace.policy_hash != second.trace.policy_hash
    assert sum(e.sets for s in second.sessions for e in s.exercises) == 51


def test_duplicate_catalog_identity_fails_closed():
    result = preview(catalog=catalog(exercise("knee_extension")))
    assert result.status == "invalid_input" and "duplicate_variant_identity" in result.reasons


def test_unrecognized_restriction_is_explicitly_unsupported_not_silently_ignored():
    result = preview(profile=profile(restrictions=("unmapped-medical-restriction",)))
    assert result.status == "unsupported_profile" and not result.sessions
    assert "restriction_not_mapped" in result.reasons


def test_stability_preference_changes_selection_without_scoring_activation():
    supported = replace(exercise("horizontal_pull", "zz-supported"), stability="supported")
    result = preview(catalog=catalog(supported), profile=profile(preferred_stability="supported"))
    pulls = [e for s in result.sessions for e in s.exercises if e.exercise.action == "horizontal_pull"]
    assert all(e.exercise.variant_id == "zz-supported" for e in pulls)
    assert "metadata_v2_scoring_unused" in result.trace.facts


def test_invalid_numeric_policy_and_cap_abstain_with_trace():
    for kwargs in (dict(profile=profile(session_cap_minutes=float("nan"))),
                   dict(policy=policy(doses=(replace(policy().doses[0], reps_min=0),))),
                   dict(policy=policy(calibration=replace(policy().calibration, minimum_completed_sets=0)))):
        result = preview(**kwargs)
        assert result.status == "invalid_input" and not result.sessions
        assert len(result.trace.input_hash) == 64


def test_local_today_uses_explicit_instant_and_rejects_past_dates_without_moving_them():
    ctx = context(planning_instant=datetime(2026, 10, 28, 2, tzinfo=UTC))
    # Still Tuesday in New York, already Wednesday in Tokyo.
    assert preview(context=ctx).sessions
    assert "past_selected_date_unsupported" in preview(context=ctx, profile=profile(timezone="Asia/Tokyo")).reasons


def test_bound_policy_approval_changes_draft_status_but_never_grants_activation():
    from core_engine.customized.models import PolicyApproval
    from core_engine.customized.audit import policy_content_hash
    p = policy()
    approved = replace(p, status="approved", approval=PolicyApproval(policy_content_hash(p), "synthetic-reviewer", "synthetic-decision"))
    assert preview(policy=approved, allow_provisional_preview=False).status == "draft"
    assert not preview(policy=approved).can_activate
    changed = replace(approved, minimum_gap_days=3)
    assert not preview(policy=changed, allow_provisional_preview=False).sessions


def test_planner_has_no_source_or_history_access_and_no_runtime_writes():
    """Exercise decisions with writes/network denied; permit only IANA tzdata reads."""
    import os
    from pathlib import Path
    import subprocess
    import sys
    test_root = str(Path(__file__).parent)
    code = r'''
import sys
from test_customized_planner import preview, profile, catalog, policy, context
args = dict(profile=profile(), catalog=catalog(), policy=policy(), context=context())
before = repr(args)
def deny_io(event, arguments):
    if event == "open":
        path, mode, flags = arguments
        assert str(path).startswith("/usr/share/zoneinfo/"), f"Unexpected read: {path}"
        assert mode == "r" and flags & 3 == 0, "Unexpected file write"
    if event.startswith(("socket.", "sqlite3.", "subprocess.")) or event in {
        "os.remove", "os.rename", "os.mkdir", "os.rmdir", "os.system", "os.truncate"}:
        raise AssertionError(f"Unexpected runtime I/O: {event}")
sys.addaudithook(deny_io)
result = preview(**args)
assert len(result.sessions) == 3 and result == preview(**args)
assert not result.can_activate and repr(args) == before
'''
    env = {**os.environ, "PYTHONPATH": os.pathsep.join((test_root, os.environ.get("PYTHONPATH", ""))), "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run([sys.executable, "-c", code], env=env, text=True, capture_output=True, timeout=15)
    assert completed.returncode == 0, completed.stderr
