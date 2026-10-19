"""Original, isolated three-date Full Body draft construction owner.

Select knee extension, hip extension, push and pull actions independently of any
source-program template. Repeat exact variants across the three dates, changing
priority order and using injected emphasis dose. This is a candidate qualitative
structure for expert review, not a physiological optimum or approved ontology.
"""
from dataclasses import replace
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .calibration import calibrate_working_load, calibration_policy_reasons
from .audit import content_hash, policy_content_hash, policy_is_approved
from .models import (
    SCHEMA_VERSION, SKILLS, CustomizedProfile, ExerciseCatalog, SciencePolicy,
    PlanningContext, ExposureTarget, CompletedExposure, StrengthReport, DecisionTrace, DurationRange, RejectedCandidate, Selection,
    PlannedExercise, TimeBudget, DraftSession, ExposureLedgerRow, PlanPreview, finite,
)

VERSION = "customized-full-body-c1-v1"
GROUP_ACTIONS = (
    ("knee_extension", ("knee_extension",)),
    ("hip_extension", ("hip_extension",)),
    ("push", ("horizontal_press", "vertical_press")),
    ("pull", ("horizontal_pull", "vertical_pull")),
)
EMPHASES = ("knee_extension", "hip_extension", "push")
RULES_HASH = content_hash({"version": VERSION, "groups": GROUP_ACTIONS, "emphases": EMPHASES,
    "tie_break": ("user_preferred_variant", "user_preferred_stability", "variant_id"),
    "timing": "warmup+work+between_work_sets_rest+setup+between_exercise_transition+margin",
    "policy_gate": "bound_approval_or_explicit_nonprescriptive_simulation"})


def _validation(profile, catalog, policy, context, *, allowed_actions=None):
    reasons = []
    allowed_actions = {a for _, actions in GROUP_ACTIONS for a in actions} if allowed_actions is None else allowed_actions
    if (profile.version != "c1-profile-v1" or context.version != "c1-context-v1"
            or not catalog.version):
        reasons.append("unsupported_input_version")
    if (not finite(profile.session_cap_minutes) or profile.session_cap_minutes <= 0
            or profile.cap_kind not in {"hard", "flexible"} or profile.max_skill not in SKILLS):
        reasons.append("invalid_profile_constraints")
    try:
        zone = ZoneInfo(profile.timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        reasons.append("invalid_iana_timezone")
        zone = None
    if (not isinstance(context.planning_instant, datetime) or context.planning_instant.tzinfo is None
            or context.planning_instant.utcoffset() is None):
        reasons.append("explicit_aware_planning_instant_required")
    if type(context.week_start) is not date or context.week_start.weekday() != 0:
        reasons.append("monday_week_start_required")
    dates = profile.selected_dates
    if len(dates) != 3 or any(type(d) is not date for d in dates) or len(set(dates)) != 3:
        reasons.append("selected_dates_must_be_three_distinct_dates")
    elif type(context.week_start) is date:
        if any(not context.week_start <= d < context.week_start + timedelta(days=7) for d in dates):
            reasons.append("selected_date_outside_week")
        if zone and "explicit_aware_planning_instant_required" not in reasons:
            if min(dates) < context.planning_instant.astimezone(zone).date():
                reasons.append("past_selected_date_unsupported")
        if context.previous_training_date is not None and (type(context.previous_training_date) is not date or context.previous_training_date >= min(dates)):
            reasons.append("invalid_previous_date_context")
        if context.next_training_date is not None and (type(context.next_training_date) is not date or context.next_training_date <= max(dates)):
            reasons.append("invalid_next_date_context")
    known_restrictions = {tag for e in catalog.exercises for tag in e.restriction_tags}
    if not set(profile.restrictions) <= known_restrictions:
        reasons.append("restriction_not_mapped")
    if profile.unsupported_controls:
        reasons.append("unsupported_profile_controls")
    ids = [e.variant_id for e in catalog.exercises]
    if len(ids) != len(set(ids)):
        reasons.append("duplicate_variant_identity")
    if not catalog.sources or any(not e.sources for e in catalog.exercises):
        reasons.append("catalog_provenance_missing")
    for e in catalog.exercises:
        regions = (*e.primary_regions, *e.secondary_regions, *e.unknown_regions)
        if (not e.variant_id or e.variant_id != e.load_identity.variant_id
                or e.skill not in SKILLS or not e.required_equipment
                or e.load_identity.implement not in e.required_equipment
                or len(regions) != len(set(regions)) or not regions):
            reasons.append("invalid_exercise_metadata")
        if any(not finite(w) or w <= 0 for w in e.attainable_loads) or len(set(e.attainable_loads)) != len(e.attainable_loads):
            reasons.append("invalid_attainable_inventory")
    if policy:
        reasons.extend(calibration_policy_reasons(policy))
        if policy.status not in {"provisional", "approved", "disabled"} or not policy.version or not policy.sources:
            reasons.append("invalid_science_policy")
        if policy.goal != profile.goal or policy.training_status != profile.training_status:
            reasons.append("policy_profile_not_supported")
        if type(policy.minimum_gap_days) is not int or policy.minimum_gap_days < 0:
            reasons.append("invalid_science_policy")
        actions = [d.action for d in policy.doses]
        if len(actions) != len(set(actions)):
            reasons.append("invalid_science_policy")
        for d in policy.doses:
            if (d.action not in allowed_actions
                    or any(type(v) is not int or v < 1 for v in (d.sets, d.emphasis_sets, d.reps_min, d.reps_max))
                    or d.reps_min > d.reps_max or d.effort_kind not in {"rir", "rpe10"}
                    or not finite(d.effort_min) or not finite(d.effort_max)
                    or not 0 <= d.effort_min <= d.effort_max
                    or (d.effort_kind == "rpe10" and d.effort_max > 10)):
                reasons.append("invalid_science_policy")
    return tuple(dict.fromkeys(reasons))


def _select(group, actions, profile, catalog, doses):
    eligible, rejected = [], []
    for e in sorted(catalog.exercises, key=lambda e: e.variant_id):
        reasons = []
        if e.action not in actions:
            reasons.append("different_action_group")
        if e.action not in doses:
            reasons.append("action_dose_missing")
        if not set(e.required_equipment) <= set(profile.confirmed_equipment):
            reasons.append("equipment_unavailable")
        if set(e.restriction_tags) & set(profile.restrictions):
            reasons.append("declared_restriction")
        if e.variant_id in profile.excluded_variants:
            reasons.append("user_excluded_variant")
        if SKILLS.index(e.skill) > SKILLS.index(profile.max_skill):
            reasons.append("skill_not_confirmed")
        if reasons:
            rejected.append(RejectedCandidate(e.variant_id, tuple(reasons)))
        else:
            eligible.append(e)
    def rank(e):
        preferences = profile.preferred_variants
        return (preferences.index(e.variant_id) if e.variant_id in preferences else len(preferences),
                bool(profile.preferred_stability and e.stability != profile.preferred_stability), e.variant_id)
    eligible.sort(key=rank)
    winner = eligible[0] if eligible else None
    return winner, Selection(group, winner.variant_id if winner else None,
        tuple(e.variant_id for e in eligible), tuple(rejected),
        ("equipment_restriction_skill_filtered", "user_preference_then_stable_identity") if winner else ("required_action_unavailable",))


def _sum_ranges(ranges):
    return DurationRange(sum(r.low for r in ranges), sum(r.high for r in ranges))


def _scale(r, n):
    return DurationRange(r.low * n, r.high * n)


def _time_budget(exercises, policy, profile):
    work = _sum_ranges(tuple(_scale(e.exercise.work_seconds_per_set, e.sets) for e in exercises))
    rest = _sum_ranges(tuple(_scale(e.rest_seconds, e.sets - 1) for e in exercises))
    setup = _sum_ranges(tuple(e.exercise.setup_seconds for e in exercises))
    transition = _scale(policy.transition_seconds, len(exercises) - 1)
    total = _sum_ranges((policy.warmup_seconds, work, rest, setup, transition, policy.margin_seconds))
    cap = profile.session_cap_minutes * 60
    if total.high <= cap:
        status = "within_estimated_cap"
    elif profile.cap_kind == "flexible":
        status = "over_flexible_target"
    else:
        status = "over_cap" if total.low > cap else "uncertain_over_cap"
    return TimeBudget(policy.warmup_seconds, work, rest, setup, transition, policy.margin_seconds, total, status)


def plan_full_body(*, profile: CustomizedProfile, catalog: ExerciseCatalog,
                   policy: SciencePolicy | None, context: PlanningContext,
                   allow_provisional_preview: bool = False,
                   exposures: tuple[CompletedExposure, ...] = (),
                   strength_reports: tuple[StrengthReport, ...] = ()) -> PlanPreview:
    """Return an unwired draft; simulation is opt-in and never prescriptive.

    Inputs must be immutable normalized domain objects, not raw onboarding/API
    dictionaries. Raises TypeError for the wrong boundary; invalid domain values
    abstain with an auditable invalid-input result.
    """
    if not isinstance(profile, CustomizedProfile) or not isinstance(catalog, ExerciseCatalog) or not isinstance(context, PlanningContext) or (policy is not None and not isinstance(policy, SciencePolicy)):
        raise TypeError("C1 requires typed normalized inputs")
    reasons = list(_validation(profile, catalog, policy, context))
    approved = policy is not None and policy_is_approved(policy)
    trace = DecisionTrace(SCHEMA_VERSION, VERSION, RULES_HASH,
        content_hash((profile, catalog, policy, context, allow_provisional_preview, exposures, strength_reports)), content_hash(profile), content_hash(catalog),
        policy_content_hash(policy), content_hash(context), content_hash((exposures, strength_reports)),
        tuple(sorted(set((*catalog.sources, *(s for e in catalog.exercises for s in e.sources), *(policy.sources if policy else ()))), key=lambda s: (s.reference, s.version, s.sha256))),
        ("no_persistence_or_activation", "metadata_v2_scoring_unused", "original_action_groups_no_source_layout",
         "policy_approved" if approved else "policy_not_approved", "origins_are_provenance_only"))
    def result(status, sessions=(), selections=(), ledger=(), tradeoffs=()):
        return PlanPreview(VERSION, status, "approved" if approved else "not_approved", tuple(sessions),
            tuple(selections), tuple(ledger), tuple(dict.fromkeys(reasons)), tuple(tradeoffs), trace)
    if profile.mode != "customized" or not profile.consent_reference:
        reasons.append("explicit_customized_consent_required")
        return result("consent_required")
    if reasons:
        return result("unsupported_profile" if any(r in reasons for r in ("unsupported_profile_controls", "policy_profile_not_supported", "restriction_not_mapped")) else "invalid_input")
    if policy is None or policy.status == "disabled" or (not approved and not allow_provisional_preview):
        reasons.append("policy_not_approved")
        return result("policy_not_approved")
    if not approved:
        reasons.append("provisional_nonprescriptive_simulation")
    if context.previous_training_date is None or context.next_training_date is None:
        reasons.append("adjacent_week_context_unknown")
    doses = {d.action: d for d in policy.doses}
    selected, selections = {}, []
    for group, actions in GROUP_ACTIONS:
        e, selection = _select(group, actions, profile, catalog, doses)
        selections.append(selection)
        if e:
            selected[group] = e
    if len(selected) != len(GROUP_ACTIONS):
        reasons.append("required_action_unavailable")
        return result("infeasible", selections=selections, tradeoffs=("Confirm equipment/skill, revise the restriction or review alternative action coverage; no work was silently removed.",))
    if any(not e.metadata_qualified for e in selected.values()):
        reasons.append("exercise_ontology_unqualified")
    dates = sorted(profile.selected_dates)
    neighbors = [d for d in (context.previous_training_date, *dates, context.next_training_date) if d is not None]
    spacing_conflict = any((b - a).days < policy.minimum_gap_days for a, b in zip(neighbors, neighbors[1:]))
    if spacing_conflict:
        reasons.append("schedule_spacing_conflict")
    sessions, ledger, tradeoffs = [], [], []
    for local_date, emphasis in zip(dates, EMPHASES):
        groups = sorted(selected, key=lambda group: (group != emphasis, list(selected).index(group)))
        exercises = []
        for group in groups:
            e = selected[group]
            dose = doses[e.action]
            exercises.append(PlannedExercise(e, dose.emphasis_sets if group == emphasis else dose.sets,
                dose.reps_min, dose.reps_max, dose.effort_kind, dose.effort_min, dose.effort_max, dose.rest_seconds,
                ("original_action_coverage", "repeatable_variant", "emphasis_dose" if group == emphasis else "anchor_dose")))
        # Date context belongs to the planning instant, never a future session.
        as_of = context.planning_instant.astimezone(ZoneInfo(profile.timezone)).date()
        calibrated = []
        for e in exercises:
            target = ExposureTarget(e.reps_min, e.reps_max, e.effort_kind, e.effort_min, e.effort_max)
            calibrated.append(replace(e, calibration=calibrate_working_load(exercise=e.exercise, target=target,
                policy=policy, as_of=as_of, exposures=exposures, strength_reports=strength_reports,
                allow_provisional_preview=allow_provisional_preview,required_set_indices=tuple(range(1,e.sets+1)))))
        budget = _time_budget(tuple(exercises), policy, profile)
        session_id = "c1-" + content_hash((VERSION, local_date, emphasis, exercises, profile.timezone, policy_content_hash(policy)))[:24]
        sessions.append(DraftSession(session_id, local_date, emphasis, tuple(calibrated), budget))
        for e in exercises:
            for involvement, regions in (("primary", e.exercise.primary_regions), ("secondary", e.exercise.secondary_regions), ("unknown", e.exercise.unknown_regions)):
                for region in sorted(regions):
                    ledger.append(ExposureLedgerRow(session_id, e.exercise.variant_id, region, involvement, e.sets))
        if budget.status in {"over_cap", "uncertain_over_cap"}:
            reasons.append("hard_session_cap_exceeded")
            tradeoffs.append(f"{local_date}: estimated {budget.total_seconds.low / 60:g}-{budget.total_seconds.high / 60:g} minutes exceeds the hard {profile.session_cap_minutes:g}-minute cap. Review dose, equipped alternatives or cap; the draft retains all work.")
        elif budget.status == "over_flexible_target":
            tradeoffs.append(f"{local_date}: estimated duration exceeds your flexible target; review the complete draft before choosing a tradeoff.")
    if spacing_conflict:
        tradeoffs.append("Review selected dates or the provisional spacing policy; dates were retained and no session was skipped.")
    status = "infeasible" if spacing_conflict or "hard_session_cap_exceeded" in reasons else "draft" if approved else "policy_not_approved"
    return result(status, sessions, selections, ledger, tradeoffs)
