"""Account-owned inactive candidate lifecycle. Training decisions stay in C1/C2/C3A.

Only the trusted actor, server bundle, effective schedule port and explicit clock
enter this owner. Transactions append snapshots/commands and retry receipts. No
workout/session writer, production ORM, policy key or activation permission exists.
"""
from datetime import date, datetime, timedelta
import hashlib
import json
import secrets
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from core_engine.customized.audit import canonical, content_hash
from core_engine.customized.admission import AdmissionAudience, admit_policy, record_digest
from .customized_preview_models import PreviewPrincipal, PreviewRequest
from .customized_preview_service import evaluate_preview
from .customized_lifecycle_models import (AccountActor, AcceptCommand, LifecycleError,
    ProposalRequest, ProposalStore)
from .customized_lifecycle_schedule import SchedulePort, ScheduleSnapshot

RULES = "customized-account-lifecycle-c3b1-v1"
CONSENT_TEXT = ("I choose Customized and accept this exact inactive candidate revision for review only. "
    "It cannot start a workout. Numerical rules, exercise metadata, load inventories and time estimates "
    "remain unapproved. Acknowledging omitted work is not scientific or medical approval; equal or optimal results are not established.")


def _json(value):
    return json.loads(json.dumps(canonical(value), sort_keys=True, allow_nan=False))


class LifecycleService:
    def __init__(self, *, server, store: ProposalStore, schedule: SchedulePort, clock,
                 comparison_pairs: tuple[tuple[str,str], ...] = ()):
        self.server, self.store, self.schedule, self.clock = server, store, schedule, clock
        self.comparison_pairs = comparison_pairs

    def _guard(self, actor):
        if self.server.enabled is not True or self.server.environment not in {"test","staging"}:
            raise LifecycleError("feature_disabled",404)
        if not isinstance(actor,AccountActor) or not actor.subject or not actor.session_id:
            raise LifecycleError("authentication_required",401)
        if (actor.subject not in self.server.allowed_subjects
                or not {"customized:preview","customized:proposal"}<=set(actor.scopes)):
            raise LifecycleError("capability_required",403)
        now=self.clock()
        if now.tzinfo is None:
            raise LifecycleError("invalid_server_clock",503)

    def _command(self,actor,key,payload,execute):
        self._guard(actor)
        if not isinstance(key,str) or not 1<=len(key)<=96 or not all(33<=ord(c)<=126 for c in key):
            raise LifecycleError("invalid_idempotency_key",422)
        digest=content_hash((RULES,actor.subject,actor.session_id,payload))
        with self.store.transaction() as tx:
            retry=tx.retry(actor.subject,key)
            if retry:
                if retry[0]!=digest:
                    raise LifecycleError("idempotency_conflict")
                return retry[1]
            response=execute(tx)
            tx.remember(actor.subject,key,digest,response)
            return response

    def _owned(self,tx,actor,proposal_id):
        document=tx.read(actor.subject,proposal_id)
        if document is None:
            raise LifecycleError("not_found",404)
        return document

    @staticmethod
    def _expected(document,expected):
        if type(expected) is not int or expected!=document["revision"]:
            raise LifecycleError("stale_revision")

    def _append(self,tx,actor,document,state):
        previous=document["revision"]
        document["revision"]+=1
        document["state"]=state
        document["events"].append(dict(revision=document["revision"],state=state,
            plan_version=document["plan_version"],at=self.clock().isoformat()))
        tx.append(actor.subject,document,previous)
        return self._public(document)

    @staticmethod
    def _public(document):
        # Challenges are not read endpoints or credential-bearing history.
        return _json({k:v for k,v in document.items() if k!="pending_challenge"})

    def get(self,actor,proposal_id):
        self._guard(actor)
        with self.store.transaction() as tx:
            return self._public(self._owned(tx,actor,proposal_id))

    def history(self,actor,proposal_id):
        self._guard(actor)
        with self.store.transaction() as tx:
            self._owned(tx,actor,proposal_id)
            return [self._public(d) for d in tx.history(actor.subject,proposal_id)]

    @staticmethod
    def _request(data):
        if (not isinstance(data,dict) or {"consent","consent_reference","omissions"}&set(data)):
            raise LifecycleError("invalid_request",422)
        try:
            request=ProposalRequest.model_validate(data)
        except ValidationError:
            raise LifecycleError("invalid_request",422) from None
        # Do not promote a defaulted compatibility input into an explicit origin.
        internal=request.model_dump(exclude_unset=True)
        internal.update(consent=True,consent_reference="server_preview_permission_only",omissions=())
        return PreviewRequest.model_validate(internal)

    def _schedule(self,actor,timezone):
        schedule=self.schedule.resolve(actor.subject,timezone)
        if not isinstance(schedule,ScheduleSnapshot):
            raise LifecycleError("schedule_context_required")
        if schedule.subject!=actor.subject or schedule.timezone!=timezone:
            raise LifecycleError("invalid_schedule_context")
        schedule.document()  # Validate the trusted port's structural contract.
        return schedule

    def _content_stamp(self,request):
        relevant={request.bundle_id,*(reference for candidate,reference in self.comparison_pairs if candidate==request.bundle_id)}
        bundles=tuple(b for b in self.server.bundles if b.bundle_id in relevant)
        return content_hash((RULES,bundles, self.comparison_pairs,
            tuple((record_digest(r),r.endorsements) for r in self.server.registry.records),
            tuple((a.authority_id,a.role,a.evidence_references,a.valid_from,a.expires_at,a.enabled,hashlib.sha256(a.key).hexdigest())
                for a in self.server.registry.authorities),self.server.registry.source_pins,
            self.server.registry.metadata_evidence_pins,self.server.registry.inventory_evidence_pins))

    def _snapshot(self,actor,data):
        request=self._request(data)
        schedule=self._schedule(actor,request.timezone)
        principal=PreviewPrincipal(actor.subject,actor.scopes)
        response,evidence=evaluate_preview(request,server=self.server,principal=principal,context=schedule.planning_context())
        comparisons=[]
        comparison_complete=False
        references=[reference for candidate,reference in self.comparison_pairs if candidate==request.bundle_id]
        if len(references)==1:
            reference=references[0]
            original,_=evaluate_preview(request.model_copy(update={"bundle_id":reference}),
                server=self.server,principal=principal,context=schedule.planning_context())
            if len(original.sessions)==len(response.sessions)==3:
                comparison_complete=True
                for old,new in zip(original.sessions,response.sessions):
                    if (old.local_date!=new.local_date
                            or tuple(e.variant_id for e in old.exercises)!=tuple(e.variant_id for e in new.exercises)):
                        comparison_complete=False
                        break
                    for old_e,new_e in zip(old.exercises,new.exercises):
                        # Set differences cannot establish equivalence when other
                        # prescriptions/variants differ. Fail closed on that case.
                        fields=("reps_min","reps_max","target_scale","target_min","target_max","rest_min_seconds","rest_max_seconds")
                        if old_e.sets<new_e.sets or any(getattr(old_e,k)!=getattr(new_e,k) for k in fields):
                            comparison_complete=False
                            break
                        if old_e.sets!=new_e.sets:
                            comparisons.append(dict(local_date=new.local_date.isoformat(),variant_id=new_e.variant_id,
                                reference_sets=old_e.sets,candidate_sets=new_e.sets,removed_sets=old_e.sets-new_e.sets,
                                reference_bundle=reference,reference_preview_hash=content_hash(original.model_dump(mode="json"))))
                comparison_complete=comparison_complete and bool(comparisons)
        if not comparison_complete:
            comparisons=[]
        snapshot=dict(schema_version=RULES,request=request.model_dump(mode="json",exclude={"consent","consent_reference","omissions"}),
            preview=response.model_dump(mode="json"),evidence=canonical(evidence) if evidence else None,
            schedule=schedule.document(),schedule_freshness=schedule.freshness_hash(),
            content_stamp=self._content_stamp(request),workload_changes=comparisons,comparison_complete=comparison_complete,
            authority=dict(policy="review_required",metadata="unqualified",inventory="synthetic",
                professional_approval="missing",owner_release_decision="missing",scheduling=schedule.source_kind))
        return _json(snapshot)

    def _assessment(self,snapshot):
        p=snapshot["preview"]
        return "requires_information" if p["status"]=="needs_information" else "review_required"

    def _base_reasons(self,snapshot):
        reasons=["c3b1_activation_disabled","science_policy_not_approved","professional_qualification_and_independence_required",
            "signed_owner_release_decision_required","synthetic_catalog_inventory","verified_exercise_skill_required",
            "source_verified_schedule_required","production_lifecycle_and_release_not_authorized"]
        selected=set(snapshot["request"]["selected_dates"])
        for occurrence in snapshot["schedule"]["occurrences"]:
            week=snapshot["schedule"]["context"]["week_start"]
            local_date=date.fromisoformat(occurrence["local_date"])
            week_start=date.fromisoformat(week)
            if occurrence["status"]!="cancelled" and week_start<=local_date<week_start+timedelta(days=7):
                # The C1 context cannot represent an intervening retained workout.
                # No implicit replacement/stacking or second spacing policy.
                reasons.append("retained_week_occurrence_requires_resolution")
            if occurrence["status"] in {"started","completed","partial"} and occurrence["local_date"] in selected:
                reasons.append("protected_authored_occurrence" if occurrence["mode"]=="authored" else "protected_occurrence")
        return sorted(set(reasons))

    def create(self,actor,data,*,idempotency_key):
        def execute(tx):
            snapshot=self._snapshot(actor,data)
            document=dict(proposal_id=str(uuid4()),subject=actor.subject,plan_version=1,revision=0,
                snapshot=snapshot,snapshot_hash=content_hash(snapshot),events=[],consent_receipt=None,
                pending_challenge=None,blocking_reasons=self._base_reasons(snapshot),can_activate=False,prescriptive=False)
            self._append(tx,actor,document,"previewed")
            return self._append(tx,actor,document,self._assessment(snapshot))
        return self._command(actor,idempotency_key,("create",data),execute)

    def revise(self,actor,proposal_id,data,*,expected_revision,idempotency_key):
        def execute(tx):
            document=self._owned(tx,actor,proposal_id)
            self._expected(document,expected_revision)
            snapshot=self._snapshot(actor,data)
            document.update(snapshot=snapshot,snapshot_hash=content_hash(snapshot),plan_version=document["plan_version"]+1,
                consent_receipt=None,pending_challenge=None,blocking_reasons=self._base_reasons(snapshot))
            self._append(tx,actor,document,"previewed")
            return self._append(tx,actor,document,self._assessment(snapshot))
        return self._command(actor,idempotency_key,("revise",proposal_id,expected_revision,data),execute)

    def _fresh(self,actor,document):
        snapshot=document["snapshot"]
        request=self._request(snapshot["request"])
        if self._content_stamp(request)!=snapshot["content_stamp"]:
            raise LifecycleError("stale_content")
        schedule=self._schedule(actor,request.timezone)
        if schedule.freshness_hash()!=snapshot["schedule_freshness"]:
            raise LifecycleError("stale_schedule")
        local_today=self.clock().astimezone(ZoneInfo(request.timezone)).date()
        if any(d<local_today for d in request.selected_dates):
            raise LifecycleError("selected_date_passed")

    def _candidate(self,document):
        p=document["snapshot"]["preview"]
        if "retained_week_occurrence_requires_resolution" in document["blocking_reasons"]:
            raise LifecycleError("schedule_conflict")
        if (len(p["sessions"])!=3 or any(s["cap_status"]!="within_estimated_cap" for s in p["sessions"])
                or p["missing_actions"] or p["missing_regions"]
                or set(p["reasons"])-{"coverage_or_direct_dose_tradeoff","science_policy_not_approved",
                    "candidate_for_expert_review_nonprescriptive","exercise_ontology_human_review_pending",
                    "adjacent_week_context_unknown_c3_carryover_deferred"}):
            raise LifecycleError("candidate_infeasible")
        if p["dose_conflicts"] and not document["snapshot"]["comparison_complete"]:
            raise LifecycleError("workload_comparison_required")
        if {"protected_authored_occurrence","protected_occurrence"}&set(document["blocking_reasons"]):
            raise LifecycleError("schedule_conflict")

    @staticmethod
    def _terms(document):
        snapshot=document["snapshot"];p=snapshot["preview"]
        acknowledgements=["inactive_candidate_unapproved_science", "uncalibrated_time_estimates_no_equal_or_optimal_results"]
        counts={r["region"]:r["primary_sets"] for r in p["regions"]}
        bands={b["region"]:b for b in (snapshot["evidence"] or {}).get("bundle",{}).get("standard",{}).get("direct_region_bands",[])}
        for region in p["dose_conflicts"]:
            band=bands[region]
            acknowledgements.append(f"dose:{region}:primary={counts[region]}:proposed_band={band['minimum']}-{band['maximum']}:unapproved")
        for change in snapshot["workload_changes"]:
            acknowledgements.append(f"work:{change['local_date']}:{change['variant_id']}:{change['reference_sets']}->{change['candidate_sets']}")
        terms=dict(text=CONSENT_TEXT,subject=document["subject"],mode="customized",proposal_id=document["proposal_id"],
            plan_version=document["plan_version"],snapshot_hash=document["snapshot_hash"],acknowledgements=acknowledgements)
        return terms,content_hash(terms)

    def challenge(self,actor,proposal_id,*,expected_revision,snapshot_hash,idempotency_key):
        def execute(tx):
            document=self._owned(tx,actor,proposal_id)
            self._expected(document,expected_revision)
            if document["state"] not in {"previewed","review_required","requires_information"}:
                raise LifecycleError("invalid_transition")
            if snapshot_hash!=document["snapshot_hash"]:
                raise LifecycleError("stale_content")
            self._fresh(actor,document);self._candidate(document)
            token=secrets.token_urlsafe(32)
            terms,digest=self._terms(document)
            document["pending_challenge"]=dict(token_hash=hashlib.sha256(token.encode()).hexdigest(),session_id=actor.session_id,
                terms_hash=digest,expires_at=(self.clock()+timedelta(minutes=10)).isoformat())
            result=self._append(tx,actor,document,document["state"])
            result.update(challenge=token,terms=terms,terms_hash=digest,required_acknowledgements=terms["acknowledgements"])
            return result
        return self._command(actor,idempotency_key,("challenge",proposal_id,expected_revision,snapshot_hash),execute)

    def accept(self,actor,proposal_id,data,*,idempotency_key):
        try:
            command=AcceptCommand.model_validate(data)
        except ValidationError:
            raise LifecycleError("invalid_request",422) from None
        def execute(tx):
            document=self._owned(tx,actor,proposal_id)
            pending=document.get("pending_challenge")
            if not pending or command.expected_revision!=document["revision"]:
                raise LifecycleError("challenge_consumed_or_stale")
            if pending["session_id"]!=actor.session_id:
                raise LifecycleError("challenge_session_mismatch",403)
            if (not secrets.compare_digest(hashlib.sha256(command.challenge.encode()).hexdigest(),pending["token_hash"])
                or command.snapshot_hash!=document["snapshot_hash"] or command.terms_hash!=pending["terms_hash"]):
                raise LifecycleError("invalid_consent_challenge",403)
            if self.clock()>=datetime.fromisoformat(pending["expires_at"]):
                raise LifecycleError("consent_challenge_expired")
            terms,digest=self._terms(document)
            if (command.agree is not True or digest!=command.terms_hash
                or sorted(command.acknowledgements)!=sorted(terms["acknowledgements"])):
                raise LifecycleError("acknowledgement_mismatch")
            self._fresh(actor,document);self._candidate(document)
            document["consent_receipt"]=dict(receipt_id=str(uuid4()),subject=actor.subject,session_binding=content_hash(actor.session_id),
                mode="customized",proposal_id=proposal_id,plan_version=document["plan_version"],snapshot_hash=document["snapshot_hash"],
                terms_hash=digest,acknowledgements=list(command.acknowledgements),at=self.clock().isoformat(),
                authority="server_verified_account_action_candidate_only")
            document["pending_challenge"]=None
            return self._append(tx,actor,document,"accepted_candidate")
        return self._command(actor,idempotency_key,("accept",proposal_id,command.model_dump(mode="json")),execute)

    def transition(self,actor,proposal_id,action,*,expected_revision,idempotency_key):
        def execute(tx):
            document=self._owned(tx,actor,proposal_id);self._expected(document,expected_revision)
            if action not in {"decline","withdraw"} or document["state"] in {"declined","withdrawn"}:
                raise LifecycleError("invalid_transition")
            document.update(consent_receipt=None,pending_challenge=None)
            return self._append(tx,actor,document,"declined" if action=="decline" else "withdrawn")
        return self._command(actor,idempotency_key,(action,proposal_id,expected_revision),execute)

    def check_activation(self,actor,proposal_id,*,expected_revision,idempotency_key):
        def execute(tx):
            document=self._owned(tx,actor,proposal_id);self._expected(document,expected_revision)
            reasons=self._base_reasons(document["snapshot"])
            if document["consent_receipt"] is None:
                reasons.append("authentic_consent_required")
            try: self._fresh(actor,document)
            except LifecycleError as exc: reasons.append(exc.code)
            request=document["snapshot"]["request"]
            admission=admit_policy(request["bundle_id"],registry=self.server.registry,
                audience=AdmissionAudience(request["goal"],request["training_context"],request["population"]),as_of=self.clock())
            document["authorization"]=dict(rules=RULES,admission_status=admission.status,
                admission_reasons=list(admission.reasons),record_digest=admission.record_digest,
                eligible=False,can_activate=False,
                explanation="Cryptographic admission is distinct from professional qualification, authentic consent and release authorization. C3B1 has no activation implementation.")
            document["blocking_reasons"]=sorted(set(reasons))
            return self._append(tx,actor,document,"activation_blocked")
        return self._command(actor,idempotency_key,("check_activation",proposal_id,expected_revision),execute)
