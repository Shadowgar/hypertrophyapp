"""Future admission test authorities are synthetic; no approved policy ships."""
from dataclasses import replace
from datetime import datetime, timedelta, UTC
import hashlib
import hmac

import pytest

from core_engine.customized.audit import content_hash
from core_engine.customized.admission import (
    ApprovalAuthority, PolicyEndorsement, PolicyRecord, TrustedPolicyRegistry,
    AdmissionAudience, admit_policy, endorsement_payload, record_digest,
)
from research.m4c2.catalog import review_catalog
from research.m4c2.science import candidate_standard, gym_design

NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)
AUDIENCE = AdmissionAudience("hypertrophy", "current", "broadly_healthy_adult")


def signed_registry():
    """Local positive control, never a real approval/qualification assertion."""
    standard = candidate_standard("current")
    catalog = review_catalog()
    catalog = replace(catalog, exercises=tuple(replace(e, metadata_qualified=True) for e in catalog.exercises))
    policy = replace(standard.science, version="synthetic-future-approval-test", status="approved", approval=None)
    record = PolicyRecord("future-test", "registry-test-v1", "approved", policy, catalog, content_hash(gym_design()),
        "hypertrophy", ("current",), "broadly_healthy_adult", NOW-timedelta(days=1), NOW+timedelta(days=10),
        "test-metadata-receipt", "test-inventory-receipt", "verified", ())
    authorities = tuple(ApprovalAuthority(name, role, key, (proof,), NOW-timedelta(days=2), NOW+timedelta(days=20))
        for name,role,key,proof in (("test-scientist", "science", b'synthetic-science-key-00000000000000', 'test-science-receipt'),
                                   ("test-owner", "owner", b'synthetic-owner-key-000000000000000', 'test-owner-receipt')))
    registry = TrustedPolicyRegistry((record,), authorities,
        tuple(set((*policy.sources,*catalog.sources))), ("test-metadata-receipt",), ("test-inventory-receipt",))
    return resign(registry)


def resign(registry):
    record = registry.records[0]
    endorsements=[]
    for a in registry.authorities:
        proof=PolicyEndorsement(a.authority_id,a.role,a.evidence_references[0],record_digest(record), NOW-timedelta(hours=1),NOW+timedelta(days=5),"")
        signature=hmac.new(a.key, endorsement_payload(proof), hashlib.sha256).hexdigest()
        endorsements.append(replace(proof,signature=signature))
    return replace(registry, records=(replace(record, endorsements=tuple(endorsements)),))


def resolve(registry, **kwargs):
    return admit_policy("future-test", registry=registry, audience=AUDIENCE, as_of=NOW, **kwargs)


def test_empty_unknown_and_unsigned_registry_fail_closed():
    assert admit_policy("missing",registry=TrustedPolicyRegistry(),audience=AUDIENCE,as_of=NOW).status == "policy_not_approved"
    registry=signed_registry()
    assert resolve(replace(registry,records=(replace(registry.records[0], endorsements=()),))).status == "policy_not_approved"
    assert admit_policy("missing",registry=registry,audience=AUDIENCE,as_of=NOW).record_digest is None


def test_only_two_distinct_trusted_endorsements_admit_future_policy_without_activation():
    result=resolve(signed_registry())
    assert result.status == "admitted_for_future_use" and result.audience == "approved_prescription"
    assert result.can_activate is False
    assert result == resolve(signed_registry())
    assert len(result.record_digest)==64


@pytest.mark.parametrize("mutation", ["signature", "reviewer", "proof", "content", "status", "local_hash"])
def test_forgery_and_record_replay_fail_closed(mutation):
    registry=signed_registry(); record=registry.records[0]; proof=record.endorsements[0]
    if mutation=="signature": proof=replace(proof, signature="0"*64)
    if mutation=="reviewer": proof=replace(proof, authority_id="claimed-expert")
    if mutation=="proof": proof=replace(proof, evidence_reference="arbitrary-owner-id")
    if mutation=="content": record=replace(record, policy=replace(record.policy, version="changed"))
    if mutation=="status": record=replace(record, status="review_required")
    if mutation=="local_hash": proof=replace(proof, signature=record_digest(record))
    record=replace(record, endorsements=(proof,*record.endorsements[1:]))
    assert resolve(replace(registry,records=(record,))).status == "policy_not_approved"


@pytest.mark.parametrize("mutation",["expired_record","future_record","expired_signature","naive_clock","revoked","expired_authority","weak_key","duplicate_authority","same_key","duplicate_record"])
def test_freshness_and_authority_ambiguity_fail_closed(mutation):
    registry=signed_registry(); record=registry.records[0]; authorities=registry.authorities
    if mutation=="expired_record": registry=replace(registry, records=(replace(record, expires_at=NOW),))
    if mutation=="future_record": registry=replace(registry, records=(replace(record, valid_from=NOW+timedelta(days=1)),))
    if mutation=="expired_signature": registry=replace(registry, records=(replace(record, endorsements=(replace(record.endorsements[0], expires_at=NOW),*record.endorsements[1:])),))
    if mutation=="naive_clock":
        assert admit_policy("future-test",registry=registry,audience=AUDIENCE,as_of=NOW.replace(tzinfo=None)).status == "policy_not_approved"
        return
    if mutation=="revoked": registry=replace(registry,authorities=(replace(authorities[0],enabled=False),authorities[1]))
    if mutation=="expired_authority": registry=replace(registry,authorities=(replace(authorities[0],expires_at=NOW),authorities[1]))
    if mutation=="weak_key": registry=replace(registry,authorities=(replace(authorities[0],key=b"weak"),authorities[1]))
    if mutation=="duplicate_authority": registry=replace(registry,authorities=(*authorities,authorities[0]))
    if mutation=="same_key": registry=resign(replace(registry,authorities=(authorities[0],replace(authorities[1],key=authorities[0].key))))
    if mutation=="duplicate_record": registry=replace(registry,records=(record,record))
    assert resolve(registry).status == "policy_not_approved"


@pytest.mark.parametrize("mutation",["unqualified","synthetic_inventory","missing_inventory","missing_metadata","source_pin","missing_source","empty_catalog"])
def test_even_signed_metadata_inventory_and_source_mismatch_abstains(mutation):
    registry=signed_registry(); record=registry.records[0]
    if mutation=="unqualified": record=replace(record,catalog=review_catalog())
    if mutation=="synthetic_inventory": record=replace(record,inventory_kind="synthetic")
    if mutation=="missing_inventory": record=replace(record,inventory_evidence_reference="unverified")
    if mutation=="missing_metadata": record=replace(record,metadata_evidence_reference="unverified")
    if mutation=="source_pin": registry=replace(registry,source_pins=())
    if mutation=="missing_source": record=replace(record,policy=replace(record.policy,sources=()))
    if mutation=="empty_catalog": record=replace(record,catalog=replace(record.catalog,exercises=()))
    registry=resign(replace(registry,records=(record,)))
    assert resolve(registry).status == "policy_not_approved"


@pytest.mark.parametrize("audience", [AdmissionAudience("military","current","broadly_healthy_adult"),
    AdmissionAudience("hypertrophy","returning","broadly_healthy_adult"), AdmissionAudience("hypertrophy","current","rehabilitation")])
def test_audience_is_not_inferred_or_broadened(audience):
    assert admit_policy("future-test",registry=signed_registry(),audience=audience,as_of=NOW).status=="policy_not_approved"
