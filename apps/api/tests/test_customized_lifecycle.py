"""Account command integrity against actual planning + disposable append-only storage."""
from dataclasses import replace
from datetime import timedelta
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from app import customized_preview_service as preview
from app.customized_preview_models import PreviewPrincipal
from research.m4c3a.fixtures import demo_context, demo_request, demo_server


def test_internal_evaluation_captures_normalized_profile_and_full_evidence():
    # Dropping calibration/catalog/profile provenance from a proposal must fail.
    assert hasattr(preview, "evaluate_preview"), "C3A needs immutable internal evidence for lifecycle snapshots"
    response, evidence = preview.evaluate_preview(demo_request(short=True), server=demo_server(),
        principal=PreviewPrincipal("synthetic-reviewer", ("customized:preview",)), context=demo_context())
    assert response.prescriptive is False
    assert evidence.profile.training_status == "current"
    assert evidence.profile.restrictions == ()
    assert len(evidence.result.plan.sessions) == 3
    assert evidence.bundle.catalog.exercises


@pytest.fixture
def harness(tmp_path):
    from app.customized_lifecycle import LifecycleService
    from app.customized_lifecycle_models import AccountActor
    from app.customized_lifecycle_schedule import ScheduleSnapshot
    from research.m4c3b1.store import DisposableProposalStore
    server = replace(demo_server(), allowed_subjects=("alice", "bob"))
    context = demo_context()
    class Schedule:
        revision = "synthetic-placement-1"
        occurrences = ()
        complete = True
        def resolve(self, subject, timezone):
            return ScheduleSnapshot(subject=subject, timezone=timezone, revision=self.revision,
                context=context, occurrences=self.occurrences, complete=self.complete,
                source_kind="synthetic", source_reference="test-only:#83-port")
    schedule = Schedule()
    store = DisposableProposalStore.create(tmp_path / "proposal.sqlite", disposable_root=tmp_path)
    service = LifecycleService(server=server, store=store, schedule=schedule,
        clock=lambda: context.planning_instant,comparison_pairs=(("shorter-current","longer-current"),))
    alice = AccountActor("alice", "alice-session", ("customized:preview", "customized:proposal"))
    bob = AccountActor("bob", "bob-session", alice.scopes)
    yield service, alice, bob, schedule, store


def request(short=True, cap=60, **changes):
    data=demo_request(short=short).model_dump(mode="json")
    data.update(changes)
    data["cap_minutes"]=cap
    # Lifecycle accepts no client's consent or arbitrary omission receipt.
    for field in ("consent", "consent_reference", "omissions"):
        data.pop(field, None)
    return data


def create(h, key="create-1", **changes):
    s,a,*_=h
    return s.create(a, request(**changes), idempotency_key=key)


def challenge(h, p):
    s,a,*_=h
    return s.challenge(a,p["proposal_id"], expected_revision=p["revision"], snapshot_hash=p["snapshot_hash"],
        idempotency_key="challenge-"+str(p["revision"]))


def accept(h, p, key="accept-1", **changes):
    s,a,*_=h
    command=dict(expected_revision=p["revision"],snapshot_hash=p["snapshot_hash"],
        challenge=p["challenge"],terms_hash=p["terms_hash"],acknowledgements=p["required_acknowledgements"],
        mode="customized",agree=True)
    command.update(changes)
    return s.accept(a,p["proposal_id"],command,idempotency_key=key)


def fails(code, callback):
    from app.customized_lifecycle_models import LifecycleError
    with pytest.raises(LifecycleError) as exc:
        callback()
    assert exc.value.code == code


def test_short_candidate_consent_is_exact_durable_and_inactive(harness):
    p=create(harness)
    assert p["state"]=="review_required"
    assert [e["state"] for e in p["events"]]==["previewed","review_required"]
    snap=p["snapshot"]
    assert sum(e["sets"] for s in snap["preview"]["sessions"] for e in s["exercises"])==33
    assert [s["maximum_minutes"] for s in snap["preview"]["sessions"]]==[57.5,59,57.5]
    assert len(snap["preview"]["dose_conflicts"])==6
    assert sum(c["removed_sets"] for c in snap["workload_changes"])==12
    assert len(snap["workload_changes"])==12
    assert snap["evidence"]["profile"]["restrictions"]==[]
    assert snap["schedule"]["window_start"]=="2026-10-19"
    assert snap["schedule"]["window_end"]=="2026-11-08"
    c=challenge(harness,p)
    assert len(c["required_acknowledgements"])>=6
    fails("acknowledgement_mismatch",lambda:accept(harness,c,acknowledgements=[]))
    result=accept(harness,c)
    assert result["state"]=="accepted_candidate" and result["can_activate"] is False
    assert result["consent_receipt"]["subject"]=="alice"
    assert result["consent_receipt"]["snapshot_hash"]==p["snapshot_hash"]
    assert accept(harness,c)==result
    fails("challenge_consumed_or_stale",lambda:accept(harness,c,key="replay-new-key"))
    s,a,_,_,store=harness
    from research.m4c3b1.store import DisposableProposalStore
    from app.customized_lifecycle import LifecycleService
    reopened=LifecycleService(server=s.server,store=DisposableProposalStore.open(store.path,disposable_root=store.path.parent),
        schedule=s.schedule,clock=s.clock,comparison_pairs=s.comparison_pairs)
    assert reopened.get(a,p["proposal_id"])==result
    assert reopened.history(a,p["proposal_id"])[0]["snapshot"]==snap


def test_longer_and_hard_45_are_unacceptably_infeasible_without_truncation(harness):
    for key,changes,sets,upper in (("long",{"short":False},45,[69,70.5,69]),("hard45",{"cap":45},33,[57.5,59,57.5])):
        p=create(harness,key=key,**changes)
        assert sum(e["sets"] for s in p["snapshot"]["preview"]["sessions"] for e in s["exercises"])==sets
        assert [s["maximum_minutes"] for s in p["snapshot"]["preview"]["sessions"]]==upper
        fails("candidate_infeasible",lambda:challenge(harness,p))


def test_account_and_session_scope_has_no_foreign_object_leak(harness):
    s,a,b,_,_=harness
    p=create(harness);c=challenge(harness,p)
    for id in (p["proposal_id"],"does-not-exist"):
        fails("not_found",lambda:s.get(b,id))
        fails("not_found",lambda:s.history(b,id))
    from app.customized_lifecycle_models import AccountActor
    harness2=(s,replace(a,session_id="new-session"),*harness[2:])
    fails("challenge_session_mismatch",lambda:accept(harness2,c))
    fails("not_found",lambda:accept((s,b,*harness[2:]),c))
    fails("capability_required",lambda:s.get(AccountActor(a.subject,a.session_id,()),p["proposal_id"]))


def test_revision_withdrawal_and_decline_preserve_exact_history_and_dates(harness):
    s,a,*_=harness
    p=create(harness);c=challenge(harness,p);accepted=accept(harness,c)
    withdrawn=s.transition(a,p["proposal_id"],"withdraw",expected_revision=accepted["revision"],idempotency_key="withdraw")
    assert withdrawn["state"]=="withdrawn" and withdrawn["consent_receipt"] is None
    assert accept(harness,c)==accepted  # Historical retry cannot resurrect current consent.
    assert s.get(a,p["proposal_id"])["state"]=="withdrawn"
    revised=s.revise(a,p["proposal_id"],request(short=False,cap=90),expected_revision=withdrawn["revision"],idempotency_key="revise")
    assert revised["plan_version"]==2 and revised["consent_receipt"] is None
    assert revised["snapshot_hash"]!=p["snapshot_hash"]
    assert revised["snapshot"]["request"]["selected_dates"]==p["snapshot"]["request"]["selected_dates"]
    declined=s.transition(a,p["proposal_id"],"decline",expected_revision=revised["revision"],idempotency_key="decline")
    assert declined["state"]=="declined"
    assert s.history(a,p["proposal_id"])[0]["snapshot_hash"]==p["snapshot_hash"]
    fails("stale_revision",lambda:s.revise(a,p["proposal_id"],request(),expected_revision=1,idempotency_key="stale"))


@pytest.mark.parametrize("changes",[{"skill":None},{"restrictions":None},{"training_context":"unknown"}])
def test_unknown_inputs_require_information_not_clearance(harness,changes):
    p=create(harness,**changes)
    assert p["state"]=="requires_information"
    assert not p["snapshot"]["preview"]["sessions"]
    fails("candidate_infeasible",lambda:challenge(harness,p))


@pytest.mark.parametrize("field,value",[("consent_reference","forged"),("omissions",[]),("owner_id","bob"),("science_approved",True),("mode","auto"),("mode","authored")])
def test_client_cannot_invent_consent_identity_or_authority(harness,field,value):
    s,a,*_=harness
    data=request();data[field]=value
    fails("invalid_request",lambda:s.create(a,data,idempotency_key="bad"))


def test_idempotency_payload_conflicts_and_concurrent_commands(harness):
    s,a,*_=harness;p=create(harness)
    assert create(harness)==p
    fails("idempotency_conflict",lambda:create(harness,cap=45))
    def race(i):
        try:
            return s.transition(a,p["proposal_id"],"decline",expected_revision=p["revision"],idempotency_key=f"race-{i}")["state"]
        except Exception as e:
            return e.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(race,range(2)))==["declined","stale_revision"]


def test_schedule_policy_and_correction_changes_require_new_preview(harness):
    s,a,_,schedule,_=harness
    p=create(harness);c=challenge(harness,p)
    schedule.revision="corrected-or-undone-placement-2"
    fails("stale_schedule",lambda:accept(harness,c))
    schedule.revision="synthetic-placement-1"
    bundle=s.server.bundles[1]
    s.server=replace(s.server,bundles=(s.server.bundles[0],replace(bundle,display_name="revised-catalog-or-policy")))
    fails("stale_content",lambda:accept(harness,c))


@pytest.mark.parametrize("status",["started","completed"])
def test_protected_authored_occurrences_block_without_mutation(harness,status):
    from app.customized_lifecycle_schedule import ScheduleOccurrence
    s,a,_,schedule,_=harness
    schedule.occurrences=(ScheduleOccurrence("authored-occurrence",demo_request().selected_dates[0],status,
        "authored","source-prescription-hash",("source-slot-1","source-slot-2")),)
    original=schedule.occurrences
    p=create(harness)
    assert "protected_authored_occurrence" in p["blocking_reasons"]
    fails("schedule_conflict",lambda:challenge(harness,p))
    assert schedule.occurrences==original


def test_activation_is_a_separate_permanently_blocked_authorization(harness):
    s,a,*_=harness;p=create(harness);c=challenge(harness,p);accepted=accept(harness,c)
    checked=s.check_activation(a,p["proposal_id"],expected_revision=accepted["revision"],idempotency_key="check")
    assert checked["state"]=="activation_blocked"
    assert checked["can_activate"] is False
    assert {"c3b1_activation_disabled","science_policy_not_approved","synthetic_catalog_inventory","source_verified_schedule_required"} <= set(checked["blocking_reasons"])
    assert checked["consent_receipt"]==accepted["consent_receipt"]


def test_forged_expired_and_duplicate_acknowledgement_commands_do_not_commit(harness):
    s,a,*_=harness;p=create(harness);c=challenge(harness,p)
    before=s.history(a,p["proposal_id"])
    fails("invalid_consent_challenge",lambda:accept(harness,c,challenge="forged-nonce-that-was-not-issued"))
    fails("invalid_consent_challenge",lambda:accept(harness,c,snapshot_hash="0"*64))
    fails("invalid_request",lambda:accept(harness,c,agree="true"))
    fails("acknowledgement_mismatch",lambda:accept(harness,c,agree=False))
    fails("acknowledgement_mismatch",lambda:accept(harness,c,acknowledgements=c["required_acknowledgements"]*2))
    s.clock=lambda: demo_context().planning_instant+timedelta(minutes=10)
    fails("consent_challenge_expired",lambda:accept(harness,c))
    assert s.history(a,p["proposal_id"])==before


def test_registry_rotation_invalidates_pending_consent(harness):
    from core_engine.customized.admission import ApprovalAuthority
    s,a,*_=harness;p=create(harness);c=challenge(harness,p)
    now=demo_context().planning_instant
    authority=ApprovalAuthority("fake-test-authority","science",b"not-a-real-signing-key-000000000000",("test-evidence",),now-timedelta(days=1),now+timedelta(days=1))
    s.server=replace(s.server,registry=replace(s.server.registry,authorities=(authority,)))
    fails("stale_content",lambda:accept(harness,c))


def test_cryptographic_admission_alone_never_means_eligibility(harness,monkeypatch):
    from types import SimpleNamespace
    import app.customized_lifecycle as module
    s,a,*_=harness;p=create(harness);c=challenge(harness,p);accepted=accept(harness,c)
    monkeypatch.setattr(module,"admit_policy",lambda *args,**kwargs:SimpleNamespace(status="admitted_for_future_use",reasons=(),record_digest="f"*64))
    result=s.check_activation(a,p["proposal_id"],expected_revision=accepted["revision"],idempotency_key="signed-still-blocked")
    assert result["authorization"]["admission_status"]=="admitted_for_future_use"
    assert result["authorization"]["eligible"] is False
    assert "professional_qualification_and_independence_required" in result["blocking_reasons"]
    assert result["can_activate"] is False


def test_disposable_adapter_rejects_unmarked_or_ordinary_paths(tmp_path):
    from research.m4c3b1.store import DisposableProposalStore
    with pytest.raises(ValueError):
        DisposableProposalStore.create(tmp_path/"unsafe.sqlite",disposable_root="/tmp")
    existing=tmp_path/"existing.sqlite";existing.write_bytes(b"do not overwrite")
    with pytest.raises(FileExistsError):
        DisposableProposalStore.create(existing,disposable_root=tmp_path)
    assert existing.read_bytes()==b"do not overwrite"


def test_empty_or_foreign_schedule_and_out_of_week_dates_never_grant_consent(harness):
    s,a,*_=harness
    original=s.schedule.resolve
    s.schedule.resolve=lambda subject,zone:replace(original(subject,zone),subject="bob")
    fails("invalid_schedule_context",lambda:create(harness))
    s.schedule.resolve=original
    p=create(harness,selected_dates=["2026-10-27","2026-10-30","2026-11-02"])
    fails("candidate_infeasible",lambda:challenge(harness,p))


def test_dst_and_adjacent_week_occurrences_are_preserved_and_trace_missing_context(harness):
    from app.customized_lifecycle_schedule import ScheduleOccurrence
    s,a,_,schedule,_=harness
    schedule.complete=False
    schedule.occurrences=(
        ScheduleOccurrence("prev",demo_context().week_start-timedelta(days=1),"completed","authored","old-hash",("slot-a",)),
        ScheduleOccurrence("next",demo_context().week_start+timedelta(days=7),"planned","authored","future-hash",("slot-b",)),)
    p=create(harness)
    assert p["snapshot"]["request"]["selected_dates"]==["2026-10-27","2026-10-29","2026-11-01"]
    assert p["snapshot"]["schedule"]["timezone"]=="America/New_York"
    assert p["snapshot"]["schedule"]["complete"] is False
    assert [o["local_date"] for o in p["snapshot"]["schedule"]["occurrences"]]==["2026-10-25","2026-11-02"]
    assert p["snapshot"]["evidence"]["profile"]["timezone"]=="America/New_York"
    # Unknown observed RIR is not copied from the target.
    assert all(not e["observed_effort"] for ss in p["snapshot"]["preview"]["sessions"] for e in ss["exercises"])


def test_comparison_revision_and_history_correction_invalidate_consent(harness):
    s,a,*_=harness;p=create(harness);c=challenge(harness,p)
    original=s.server
    reference=s.server.bundles[0]
    s.server=replace(s.server,bundles=(replace(reference,display_name="changed comparison"),s.server.bundles[1]))
    fails("stale_content",lambda:accept(harness,c))
    s.server=original
    from core_engine.customized.models import CompletedExposure,CompletedSet,ExposureTarget
    bundle=s.server.bundles[1];exercise=bundle.catalog.exercises[0]
    exposure=CompletedExposure("test-v1","workout-1","exercise-1",demo_context().week_start-timedelta(days=1),
        exercise.load_identity,ExposureTarget(8,12,"rir",1,3),(1,),True,
        (CompletedSet("receipt-1","logical-1",1,2,"voided","work",None,None,None,None,None,"unknown",None,exercise.load_identity),),"synthetic-correction")
    s.server=replace(s.server,bundles=(reference,replace(bundle,exposures=(exposure,))))
    fails("stale_content",lambda:accept(harness,c))
    assert s.get(a,p['proposal_id'])['snapshot_hash']==p['snapshot_hash']


def test_reduced_candidate_without_valid_reference_cannot_skip_omitted_work(harness):
    s,a,*_=harness
    s.comparison_pairs=()
    p=create(harness)
    fails("workload_comparison_required",lambda:challenge(harness,p))


@pytest.mark.parametrize("status",["planned","started","completed","partial"])
def test_retained_same_week_authored_context_fails_closed_instead_of_ignoring_spacing(harness,status):
    from app.customized_lifecycle_schedule import ScheduleOccurrence
    s,a,_,schedule,_=harness
    schedule.occurrences=(ScheduleOccurrence("retained-monday",demo_context().week_start,status,"authored","frozen-source-hash",("slot-1",)),)
    before=schedule.occurrences
    p=create(harness)
    assert "retained_week_occurrence_requires_resolution" in p["blocking_reasons"]
    fails("schedule_conflict",lambda:challenge(harness,p))
    assert schedule.occurrences==before


@pytest.mark.parametrize("reference",["unknown","incompatible"])
def test_missing_or_incompatible_reference_cannot_produce_partial_work_acknowledgement(harness,reference):
    s,a,*_=harness
    if reference=="unknown":
        s.comparison_pairs=(("shorter-current","does-not-exist"),)
    else:
        bundle=s.server.bundles[0]
        from core_engine.customized.pilot_models import ProgramSlot
        session=bundle.design.sessions[0]
        altered=replace(session,slots=(replace(session.slots[0],variant_ids=("nonexistent-variant",)),*session.slots[1:]))
        s.server=replace(s.server,bundles=(replace(bundle,design=replace(bundle.design,sessions=(altered,*bundle.design.sessions[1:]))),s.server.bundles[1]))
    p=create(harness)
    assert p["snapshot"]["workload_changes"]==[]
    fails("workload_comparison_required",lambda:challenge(harness,p))
