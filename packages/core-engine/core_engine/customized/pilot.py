"""Complete-program C2 offline modeling, reusing C1's pure decision owners.

The qualitative action vocabulary is explicit. Program order and numerical
science policy are independently injected review artifacts, never source-program
layouts or runtime defaults. C2 is non-prescriptive regardless of local approval.
"""
from dataclasses import replace
from zoneinfo import ZoneInfo

from .audit import content_hash, policy_content_hash
from .calibration import calibrate_working_load
from .models import (CustomizedProfile, ExerciseCatalog, PlanningContext, DecisionTrace,
    ExposureTarget, PlannedExercise, DraftSession, ExposureLedgerRow, PlanPreview)
from .pilot_models import PilotDesign, PilotStandard, PilotPreview, RegionTotals, CoverageOmission
from .planner import _validation, _select, _time_budget

VERSION = "customized-complete-pilot-c2-v1"
ACTIONS = ("knee_extension", "hip_extension", "knee_flexion", "horizontal_press", "vertical_press",
    "horizontal_pull", "vertical_pull", "shoulder_abduction", "shoulder_horizontal_abduction",
    "elbow_flexion", "elbow_extension", "plantar_flexion", "trunk_flexion")
REGIONS = ("quadriceps", "glutes", "hamstrings", "chest", "upper_back", "lats", "anterior_deltoid",
    "lateral_deltoid", "posterior_deltoid", "elbow_flexors", "triceps", "calves", "trunk")
RULES_HASH = content_hash((VERSION, ACTIONS, REGIONS, "explicit_slots_complete_coverage_no_silent_truncation",
    "reuse_c1_selection_time_calibration", "local_approval_never_authorizes_activation"))


def plan_pilot(*, profile: CustomizedProfile, catalog: ExerciseCatalog, standard: PilotStandard | None,
        design: PilotDesign, context: PlanningContext, simulate: bool = False,
        accepted_omissions: tuple[CoverageOmission, ...] = (), exposures=(), strength_reports=()) -> PilotPreview:
    """Model a complete original candidate, or expose infeasibility/missing data.

    `complete_candidate` describes only declared action/region coverage, not
    scientific or medical qualification. No approval field, content hash, mode
    or consent reference can make this offline result activatable.
    """
    if (not isinstance(profile, CustomizedProfile) or not isinstance(catalog, ExerciseCatalog)
            or not isinstance(design, PilotDesign) or not isinstance(context, PlanningContext)
            or (standard is not None and not isinstance(standard, PilotStandard))):
        raise TypeError("C2 requires typed normalized review inputs")
    science = standard.science if standard else None
    trace = DecisionTrace("c2-review-schema-v1", VERSION, RULES_HASH,
        content_hash((profile, catalog, standard, design, context, simulate, accepted_omissions, exposures, strength_reports)),
        content_hash(profile), content_hash(catalog), policy_content_hash(science), content_hash(context),
        content_hash((exposures, strength_reports)),
        tuple(sorted(set((*catalog.sources, *(s for e in catalog.exercises for s in e.sources), *(science.sources if science else ()))),
            key=lambda s: (s.reference, s.version, s.sha256))),
        ("offline_review_only", "scientific_and_owner_approval_pending", "metadata_v2_scoring_unused",
         "no_source_program_layout", "local_hash_is_not_reviewer_authentication",
         "progression_and_deload_rules_review_only", "timing_estimates_not_measured_guarantees"))
    reasons, tradeoffs, selections, sessions, ledger = [], [], [], [], []
    missing_actions, missing_regions, totals, dose_conflicts = (), (), (), ()
    coverage = "not_assessed"
    def output(status):
        plan = PlanPreview(VERSION, status, "review_required", tuple(sessions), tuple(selections), tuple(ledger),
            tuple(dict.fromkeys(reasons)), tuple(dict.fromkeys(tradeoffs)), trace)
        return PilotPreview(plan, coverage, missing_actions, missing_regions, totals, dose_conflicts,
            content_hash(standard), content_hash(design), accepted_omissions)
    if profile.mode != "customized" or not profile.consent_reference:
        reasons.append("explicit_customized_consent_required")
        return output("consent_required")
    if standard is None or science.status == "disabled" or simulate is not True:
        reasons.append("policy_not_approved_explicit_simulation_required")
        return output("policy_not_approved")
    reasons.extend(_validation(profile, catalog, science, context, allowed_actions=set(ACTIONS)))
    if (not standard.version or standard.review_status != "review_required" or not design.version
            or len(design.sessions) != 3 or len({s.key for s in design.sessions}) != 3
            or set(design.desired_actions) != set(ACTIONS) or set(design.desired_regions) != set(REGIONS)):
        reasons.append("invalid_complete_pilot_scope")
    if (len(standard.direct_region_bands) != len(REGIONS)
            or {b.region for b in standard.direct_region_bands} != set(REGIONS)
            or any(type(b.minimum) is not int or type(b.maximum) is not int or not 1 <= b.minimum <= b.maximum for b in standard.direct_region_bands)):
        reasons.append("invalid_direct_region_policy")
    if any(not e.primary_regions for e in catalog.exercises):
        reasons.append("primary_region_metadata_missing")
    for session in design.sessions:
        if (not session.key or not session.slots or len({s.action for s in session.slots}) != len(session.slots)
                or any(s.action not in ACTIONS or type(s.emphasized) is not bool for s in session.slots)):
            reasons.append("invalid_session_design")
    if any(not isinstance(o, CoverageOmission) or o.kind not in {"action", "region", "dose"}
           or not o.name or not o.reason.strip() or not o.confirmation_reference.strip() for o in accepted_omissions):
        reasons.append("explicit_omission_confirmation_required")
    if reasons:
        return output("unsupported_profile" if "policy_profile_not_supported" in reasons or "unsupported_profile_controls" in reasons or "restriction_not_mapped" in reasons else "invalid_input")
    # Never reinterpret a local approval claim as a trusted reviewer endorsement.
    simulation_policy = replace(science, status="provisional", approval=None)
    reasons.extend(("candidate_for_expert_review_nonprescriptive", "exercise_ontology_human_review_pending"))
    if context.previous_training_date is None or context.next_training_date is None:
        reasons.append("adjacent_week_context_unknown_c3_carryover_deferred")
    doses = {d.action: d for d in science.doses}
    dates = sorted(profile.selected_dates)
    neighbors = [d for d in (context.previous_training_date, *dates, context.next_training_date) if d is not None]
    spacing_conflict = any((b - a).days < science.minimum_gap_days for a, b in zip(neighbors, neighbors[1:]))
    if spacing_conflict:
        reasons.append("schedule_spacing_conflict")
        tradeoffs.append("Review the selected dates or candidate spacing; no date was moved or skipped.")
    as_of = context.planning_instant.astimezone(ZoneInfo(profile.timezone)).date()
    full_body_conflict = False
    for day, session in zip(dates, design.sessions):
        planned = []
        for slot in session.slots:
            # Explicit slot pool can distinguish variants without transferring load.
            pool = replace(catalog, exercises=tuple(e for e in catalog.exercises if not slot.variant_ids or e.variant_id in slot.variant_ids))
            e, selection = _select(f"{session.key}:{slot.action}", (slot.action,), profile, pool, doses)
            selections.append(selection)
            if e is None:
                reasons.append("required_slot_unavailable")
                tradeoffs.append(f"{session.key}: {slot.action} has no equipped, unrestricted, confirmed-skill candidate; review explicitly.")
                continue
            dose = doses[e.action]
            sets = dose.emphasis_sets if slot.emphasized else dose.sets
            target = ExposureTarget(dose.reps_min, dose.reps_max, dose.effort_kind, dose.effort_min, dose.effort_max)
            calibration = calibrate_working_load(exercise=e, target=target, policy=simulation_policy, as_of=as_of,
                exposures=exposures, strength_reports=strength_reports, allow_provisional_preview=True)
            planned.append(PlannedExercise(e, sets, dose.reps_min, dose.reps_max, dose.effort_kind,
                dose.effort_min, dose.effort_max, dose.rest_seconds,
                ("original_candidate_action_slot", "stable_variant_identity", "emphasis_dose" if slot.emphasized else "anchor_dose"), calibration))
        actions = {p.exercise.action for p in planned}
        if (not actions & {"knee_extension", "hip_extension", "knee_flexion"}
                or not actions & {"horizontal_press", "vertical_press"}
                or not actions & {"horizontal_pull", "vertical_pull"}):
            full_body_conflict = True
            reasons.append("full_body_session_incomplete")
        if not planned:
            continue
        duration = _time_budget(tuple(planned), science, profile)
        session_id = "c2-" + content_hash((VERSION, day, session, tuple(replace(p, calibration=None) for p in planned), profile.timezone,
            content_hash(standard)))[:24]
        sessions.append(DraftSession(session_id, day, session.key, tuple(planned), duration))
        if duration.status in {"over_cap", "uncertain_over_cap"}:
            reasons.append("hard_session_cap_exceeded")
        if duration.status != "within_estimated_cap":
            tradeoffs.append(f"{day}: {duration.total_seconds.low / 60:.1f}-{duration.total_seconds.high / 60:.1f} estimated minutes vs {profile.cap_kind} {profile.session_cap_minutes:g}; review cap/dose/equipped alternatives, no silent set trimming.")
        for p in planned:
            for involvement, regions in (("primary", p.exercise.primary_regions), ("secondary", p.exercise.secondary_regions), ("unknown", p.exercise.unknown_regions)):
                ledger.extend(ExposureLedgerRow(session_id, p.exercise.variant_id, r, involvement, p.sets) for r in sorted(regions))
    actions = {p.exercise.action for session in sessions for p in session.exercises}
    missing_actions = tuple(a for a in ACTIONS if a not in actions)
    reported_regions = (*REGIONS, *sorted({row.region for row in ledger} - set(REGIONS)))
    totals = tuple(RegionTotals(region, *(sum(row.sets for row in ledger if row.region == region and row.involvement == kind)
        for kind in ("primary", "secondary", "unknown"))) for region in reported_regions)
    counts = {r.region: r.primary_sets for r in totals}
    missing_regions = tuple(r for r in REGIONS if counts[r] == 0)
    dose_conflicts = tuple(b.region for b in standard.direct_region_bands if not b.minimum <= counts[b.region] <= b.maximum)
    gaps = {*(('action', a) for a in missing_actions), *(('region', r) for r in missing_regions), *(('dose', r) for r in dose_conflicts)}
    accepted = {(o.kind, o.name) for o in accepted_omissions}
    if accepted - gaps:
        reasons.append("omission_not_present_in_candidate")
        return output("invalid_input")
    # Missing direct region automatically implies its dose floor is unmet; an
    # explicit region omission covers that floor as well, never a biological credit.
    accepted |= {("dose", r) for kind, r in accepted if kind == "region"}
    coverage = "complete_candidate" if not gaps else "accepted_limited_candidate" if gaps <= accepted else "incomplete"
    if gaps:
        reasons.append("coverage_or_direct_dose_tradeoff")
        tradeoffs.append("Unmet candidate coverage/dose: " + ", ".join(f"{kind}:{name}" for kind, name in sorted(gaps)) + ". No secondary-to-direct equivalence assumed.")
    infeasible = (coverage == "incomplete" or full_body_conflict or spacing_conflict or "hard_session_cap_exceeded" in reasons
        or ("required_slot_unavailable" in reasons))
    return output("infeasible" if infeasible else "policy_not_approved")
