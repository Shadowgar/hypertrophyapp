"""Read-only C3A orchestration. No database or prescription writer.

Existing GeneratedTrainingProfile normalization (including registered ID resolution,
not source-template construction) is reused for compatibility;
its numerical defaults remain trace-only. The explicit CustomizedProfile is the
only planning input. Production routing/activation and real inventory admission
are intentionally absent, rather than inferred from this staging demonstration.
"""
from dataclasses import asdict, dataclass

from core_engine.customized.admission import AdmissionAudience, admit_policy
from core_engine.customized.audit import content_hash
from core_engine.customized.models import CustomizedProfile, PlanningContext
from core_engine.customized.pilot import ACTIONS, plan_pilot
from core_engine.customized.pilot_models import CoverageOmission, PilotPreview

from .generated_training_profile import build_generated_training_profile
from .customized_preview_models import (PreviewRequest, PreviewPrincipal, PreviewServer,
    PreviewResponse, ExercisePreview, SessionPreview, RegionPreview, SyntheticReviewBundle)

ACTIVE = ("goal","training_context","selected_dates","timezone","cap_minutes","cap_kind","equipment","skill",
    "restrictions","preferred_variants","excluded_variants","preferred_stability","omissions","mode","consent")
TRACE_ONLY = ("legacy.trace_only_controls","legacy.recovery_modifier","legacy.weakpoint_targets",
    "legacy.generated_mode","legacy.training_status","legacy.detraining_status","legacy.equipment_scope",
    "legacy.session_time_band","weakpoints","recovery")
LIMITATIONS = ("candidate_for_expert_review_nonprescriptive","fixed_design_not_personalized_optimization",
    "science_policy_and_exercise_qualification_pending","synthetic_inventory_not_real_equipment_verification",
    "self_reported_rir_is_uncertain","timing_estimates_not_measured_guarantees",
    "cross_week_persistence_and_carryover_deferred","no_growth_or_injury_probability_estimated")


@dataclass(frozen=True)
class PreviewEvidence:
    """Internal decision evidence, never accepted from an HTTP caller."""
    profile: CustomizedProfile
    bundle: SyntheticReviewBundle
    context: PlanningContext
    result: PilotPreview


def preview_program(request: PreviewRequest, *, server: PreviewServer, principal: PreviewPrincipal | None,
                    context: PlanningContext | None) -> PreviewResponse:
    return evaluate_preview(request, server=server, principal=principal, context=context)[0]


def evaluate_preview(request: PreviewRequest, *, server: PreviewServer, principal: PreviewPrincipal | None,
                     context: PlanningContext | None, application: bool = False) -> tuple[PreviewResponse, PreviewEvidence | None]:
    evidence = []
    response = _preview_program(request, server=server, principal=principal, context=context, evidence=evidence, application=application)
    return response, evidence[0] if evidence else None


def _preview_program(request: PreviewRequest, *, server: PreviewServer, principal: PreviewPrincipal | None,
                    context: PlanningContext | None, evidence: list, application: bool = False) -> PreviewResponse:
    """A host supplies registry, authorization and exact context; never the client."""
    if not isinstance(request,PreviewRequest) or not isinstance(server,PreviewServer):
        raise TypeError("Typed preview request and server context required")
    def blocked(status,reason,message):
        return PreviewResponse(audience=request.audience,status=status,reasons=(reason,),message=message)
    if server.enabled is not True:
        return blocked("feature_disabled","preview_disabled","Experimental preview is disabled.")
    if server.environment not in ({"application"} if application else {"staging","test"}):
        return blocked("feature_disabled","production_preview_disabled","Experimental preview is unavailable in production; no approved policy is admitted here.")
    if principal is None or not principal.subject:
        return blocked("unauthorized","authenticated_principal_required","Sign in to the isolated preview environment.")
    if principal.subject not in server.allowed_subjects or "customized:preview" not in principal.scopes:
        return blocked("forbidden","preview_capability_required","This account has no experimental preview access.")
    if request.mode != "customized" or request.consent is not True or not request.consent_reference.strip():
        return blocked("consent_required","customized_consent_required","Choose Customized and explicitly consent to this experimental preview; manual or automatic program selection is separate.")
    if request.goal != "hypertrophy":
        return blocked("unsupported_profile","goal_not_supported","This pilot supports hypertrophy only; choose a separately reviewed policy for another goal.")
    if request.population != "broadly_healthy_adult":
        return blocked("unsupported_profile","population_out_of_scope","This pilot does not cover that population; qualified individualized review is needed.")
    if request.training_context == "unknown":
        return blocked("needs_information","training_context_required","Clarify your current training context; no dose is assigned from missing information.")
    if request.skill is None:
        return blocked("needs_information","confirmed_skill_required","Confirm exercise skill independently of training recency; equipment ownership does not establish technique.")
    if len(request.selected_dates) != 3:
        return blocked("needs_information","three_actual_dates_required","Choose three actual local dates; no workout is moved or invented.")
    if request.restrictions is None:
        return blocked("needs_information","movement_restrictions_required","Declare any movement restrictions, or explicitly report none; absence is unknown, not medical clearance.")
    if any(r not in {f"avoid_{a}" for a in ACTIONS} for r in request.restrictions):
        return blocked("unsupported_profile","restriction_not_supported","This movement or health restriction has no qualified mapping. Obtain a reviewed alternative; no medical clearance is inferred.")
    if not isinstance(context,PlanningContext):
        return blocked("needs_information","schedule_context_required","Exact planning/week context is unavailable; no schedule or carryover is inferred.")
    if (application and request.audience != "customized_program") or (not application and request.audience == "customized_program"):
        return blocked("invalid_input","invalid_audience","Use the matching application context.")
    if request.audience == "approved_prescription":
        admission=admit_policy(request.bundle_id,registry=server.registry,
            audience=AdmissionAudience(request.goal,request.training_context,request.population),as_of=context.planning_instant)
        return PreviewResponse(audience=request.audience,status="activation_disabled" if admission.status=="admitted_for_future_use" else "policy_not_approved",
            message="No real workout can be activated through C3A. An approved policy, qualified inventory and separate activation integration are required.",
            reasons=admission.reasons,trace={"admission_rules":admission.rules_version,"record_digest":admission.record_digest or "none"})
    if not application and server.synthetic_enabled is not True:
        return blocked("feature_disabled","synthetic_preview_disabled","Synthetic review preview is disabled.")
    bundles=tuple(b for b in server.bundles if b.bundle_id==request.bundle_id)
    if len(bundles)!=1:
        return blocked("policy_not_approved","unknown_or_ambiguous_review_bundle","No review bundle is available; no substitute policy or exercise catalog was selected.")
    bundle=bundles[0]
    if (bundle.standard.science.status != "provisional" or bundle.standard.review_status != "review_required"
            or bundle.standard.science.approval is not None):
        return blocked("policy_not_approved","review_bundle_not_provisional","This review bundle cannot be treated as an approved policy.")
    # Reuse the established normalization boundary, never the legacy constructor,
    # authored scaffold, defaults, starting RIR, volume bands or physiology rules.
    legacy=None
    if not application:
        legacy=build_generated_training_profile(selected_program_id="full_body_v1",program_selection_mode="generated",
            days_available=len(request.selected_dates),session_time_budget_minutes=request.cap_minutes,
            temporary_duration_minutes=None,near_failure_tolerance=request.recovery,weak_areas=list(request.weakpoints),
            movement_restrictions=list(request.restrictions),equipment_profile=list(request.equipment),
            onboarding_answers={"goal_mode":request.goal,"training_status":request.training_context},training_state={})
        if legacy.path_family != "generated" or legacy.runtime_active.target_days != 3 or legacy.decision_profile.goal_mode != "lean_gain":
            return blocked("invalid_input","normalization_inconsistent","The normalized profile is inconsistent; no preview was constructed.")
    origins=tuple((name,"explicit_preview_request" if name in request.model_fields_set else "missing_input") for name in ACTIVE)
    profile=CustomizedProfile("c1-profile-v1","customized",request.consent_reference,request.goal,request.training_context,
        request.selected_dates,request.timezone,request.cap_minutes,request.cap_kind,request.equipment,request.skill,
        request.restrictions,request.excluded_variants,request.preferred_variants,request.preferred_stability,
        origins,())
    result=plan_pilot(profile=profile,catalog=bundle.catalog,standard=bundle.standard,design=bundle.design,context=context,
        simulate=True,accepted_omissions=tuple(CoverageOmission(o.kind,o.name,o.reason,o.confirmation_reference) for o in request.omissions),
        exposures=bundle.exposures,strength_reports=bundle.strength_reports)
    evidence.append(PreviewEvidence(profile, bundle, context, result))
    sessions=[]
    for s in result.plan.sessions:
        exercises=[]
        for p in s.exercises:
            calibration=p.calibration
            observed=tuple(r.actual_effort for a in calibration.assessments if a.comparable
                for r in a.effective_records if r.record_id in calibration.evidence_ids and r.actual_effort is not None and r.effort_kind==p.effort_kind)
            exercises.append(ExercisePreview(variant_id=p.exercise.variant_id,name=p.exercise.name,sets=p.sets,
                reps_min=p.reps_min,reps_max=p.reps_max,target_scale=p.effort_kind,target_min=p.effort_min,target_max=p.effort_max,
                observed_effort=observed,rest_min_seconds=p.rest_seconds.low,rest_max_seconds=p.rest_seconds.high,
                working_load=calibration.working_load,load_unit=calibration.unit,load_basis=calibration.basis,
                calibration_status=calibration.status,calibration_reasons=calibration.reasons))
        sessions.append(SessionPreview(local_date=s.local_date,design_label=s.emphasis,
            minimum_minutes=s.duration.total_seconds.low/60,maximum_minutes=s.duration.total_seconds.high/60,
            cap_status=s.duration.status,exercises=tuple(exercises)))
    issues=tuple(f"{choice.group}: {rejected.variant_id}: {reason}" for choice in result.plan.selections
        if choice.selected_variant_id is None for rejected in choice.rejected for reason in rejected.reasons
        if reason != "different_action_group")
    return PreviewResponse(audience=request.audience,status=result.plan.status,
        message=("Provisional Full Body program. Review workload, dates and uncertainty before accepting." if application else "Synthetic review only. No approved training policy; this preview cannot start or log a workout."),
        candidate_name=bundle.display_name,timezone=request.timezone,cap_minutes=request.cap_minutes,cap_kind=request.cap_kind,
        sessions=tuple(sessions),coverage_status=result.coverage_status,regions=tuple(RegionPreview(**asdict(r)) for r in result.region_totals),
        missing_actions=result.missing_actions,missing_regions=result.missing_regions,dose_conflicts=result.dose_conflicts,
        accepted_omissions=request.omissions,reasons=result.plan.reasons,issues=issues,tradeoffs=result.plan.tradeoffs,
        limitations=(("provisional_training_policy_no_optimality_or_growth_guarantee", "descriptive_exercise_metadata_no_scoring", "no_assumed_load_inventory_or_historical_effort", "working_load_requires_exercise_specific_calibration", "timing_estimates_not_measured_guarantees", "unknown_adjacent_schedule_disclosed") if application else LIMITATIONS),active_fields=ACTIVE,trace_only_fields=TRACE_ONLY,
        trace={"bundle_id":bundle.bundle_id,"normalizer":"core_engine.customized.models.CustomizedProfile" if application else "build_generated_training_profile","legacy_path_family":"generated" if application else legacy.path_family,
            "core_profile_version":profile.version,"field_origins":tuple(f"{name}:{origin}" for name,origin in origins),"ignored_legacy_defaults":() if application else tuple(legacy.decision_trace.defaults_applied),
            "rules_version":result.plan.trace.owner,"rules_hash":result.plan.trace.rules_hash,
            "input_hash":result.plan.trace.input_hash,"normalized_profile_hash":content_hash(profile),
            "standard_hash":result.standard_hash,"design_hash":result.design_hash,"context_hash":content_hash(context)})
