"""Server-owned future policy admission. No approved records or keys ship.

Only a trusted host constructs the immutable registry; HTTP clients select an
ID, never submit policy content, roots, evidence pins or endorsement claims.
Distinct science/owner HMAC roots authenticate provisioned authorities, not a
human's credentials. Out-of-band authority qualification remains mandatory.
No signature, admission or record can enable C3A workout activation.
"""
from dataclasses import dataclass, field, replace
from datetime import datetime
import hashlib
import hmac
import re
from typing import Literal

from .audit import content_hash
from .models import SciencePolicy, ExerciseCatalog, SourceRef, finite


@dataclass(frozen=True)
class ApprovalAuthority:
    authority_id: str
    role: Literal["science", "owner"]
    key: bytes = field(repr=False)
    evidence_references: tuple[str, ...]
    valid_from: datetime
    expires_at: datetime
    enabled: bool = True


@dataclass(frozen=True)
class PolicyEndorsement:
    authority_id: str
    role: Literal["science", "owner"]
    evidence_reference: str
    record_digest: str
    issued_at: datetime
    expires_at: datetime
    signature: str


@dataclass(frozen=True)
class PolicyRecord:
    policy_id: str
    revision: str
    status: Literal["review_required", "approved", "disabled"]
    policy: SciencePolicy
    catalog: ExerciseCatalog
    design_hash: str
    goal: str
    training_statuses: tuple[str, ...]
    population: str
    valid_from: datetime
    expires_at: datetime
    metadata_evidence_reference: str | None
    inventory_evidence_reference: str | None
    inventory_kind: Literal["synthetic", "verified"]
    endorsements: tuple[PolicyEndorsement, ...]


@dataclass(frozen=True)
class TrustedPolicyRegistry:
    records: tuple[PolicyRecord, ...] = ()
    authorities: tuple[ApprovalAuthority, ...] = ()
    source_pins: tuple[SourceRef, ...] = ()
    metadata_evidence_pins: tuple[str, ...] = ()
    inventory_evidence_pins: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdmissionAudience:
    goal: str
    training_status: str
    population: str


@dataclass(frozen=True)
class AdmissionDecision:
    status: Literal["policy_not_approved", "admitted_for_future_use"]
    policy_id: str
    record_digest: str | None
    reasons: tuple[str, ...]
    audience: Literal["approved_prescription"] = "approved_prescription"
    can_activate: Literal[False] = field(default=False, init=False)
    rules_version: str = field(default="trusted-science-admission-c3a-v1", init=False)


def record_digest(record: PolicyRecord) -> str:
    return content_hash(("c3a-policy-record-v1", replace(record, endorsements=())))


def endorsement_payload(endorsement: PolicyEndorsement) -> bytes:
    """Domain-separated signed content. No signing or key-export API exists."""
    return ("hypertrophyapp:science-admission:c3a:v1:" + content_hash(replace(endorsement, signature=""))).encode("ascii")


def _aware(value):
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _active(start, end, now):
    return all(_aware(v) for v in (start,end,now)) and start <= now < end


def admit_policy(policy_id: str, *, registry: TrustedPolicyRegistry, audience: AdmissionAudience,
                 as_of: datetime) -> AdmissionDecision:
    """Resolve pinned immutable content by ID, fail closed, never activate.

    Source/metadata/inventory pins are a trusted server manifest, not runtime
    network verification. Both qualified authorities endorse their exact content
    and expiry. Real provisioning, evidence retention and revocation are C3B.
    """
    if not isinstance(registry, TrustedPolicyRegistry) or not isinstance(audience, AdmissionAudience):
        raise TypeError("Server-owned registry and typed audience required")
    matches=tuple(r for r in registry.records if r.policy_id == policy_id)
    if len(matches) != 1:
        return AdmissionDecision("policy_not_approved",policy_id,None,("unknown_or_ambiguous_policy",))
    record=matches[0]; digest=record_digest(record); reasons=[]
    if not _active(record.valid_from,record.expires_at,as_of):
        reasons.append("policy_not_current")
    if (not record.revision or not record.policy.version or record.status != "approved"
            or record.policy.status != "approved" or not re.fullmatch(r"[0-9a-f]{64}",record.design_hash)):
        reasons.append("policy_not_approved")
    if (audience.goal != record.goal or audience.goal != record.policy.goal
            or audience.training_status not in record.training_statuses
            or audience.training_status != record.policy.training_status or audience.population != record.population):
        reasons.append("policy_audience_mismatch")
    sources=(*record.policy.sources,*record.catalog.sources,*(s for e in record.catalog.exercises for s in e.sources))
    if (not record.policy.sources or not record.catalog.sources or not record.catalog.version
            or any(not e.sources for e in record.catalog.exercises)
            or any(not s.reference.startswith("https://") or not s.version or not re.fullmatch(r"[0-9a-f]{64}",s.sha256)
                   or s not in registry.source_pins for s in sources)):
        reasons.append("source_pin_mismatch")
    if (not record.catalog.exercises or any(e.metadata_qualified is not True for e in record.catalog.exercises)
            or not record.metadata_evidence_reference or record.metadata_evidence_reference not in registry.metadata_evidence_pins):
        reasons.append("exercise_metadata_not_qualified")
    if (record.inventory_kind != "verified" or not record.inventory_evidence_reference
            or record.inventory_evidence_reference not in registry.inventory_evidence_pins
            or any(e.load_identity.variant_id != e.variant_id or not e.load_identity.equipment_key
                or not e.load_identity.rom or not e.load_identity.setup or not e.required_equipment
                or (e.load_identity.basis != "bodyweight" and (not e.attainable_loads
                    or any(not finite(w) or w <= 0 for w in e.attainable_loads))) for e in record.catalog.exercises)):
        reasons.append("equipment_inventory_not_verified")
    roots=registry.authorities
    if len({a.authority_id for a in roots}) != len(roots):
        reasons.append("ambiguous_authority_registry")
    good=[]
    for proof in record.endorsements:
        authorities=tuple(a for a in roots if a.authority_id==proof.authority_id and a.role==proof.role)
        if len(authorities)!=1:
            reasons.append("untrusted_endorsement_authority")
            continue
        a=authorities[0]
        if (a.enabled is not True or not isinstance(a.key,bytes) or len(a.key)<32
                or proof.record_digest != digest or proof.evidence_reference not in a.evidence_references
                or not proof.evidence_reference or not _active(a.valid_from,a.expires_at,as_of)
                or not _active(proof.issued_at,proof.expires_at,as_of)
                or not all(_aware(v) for v in (record.valid_from,record.expires_at))
                or proof.issued_at < max(a.valid_from,record.valid_from)
                or proof.expires_at > min(a.expires_at,record.expires_at)):
            reasons.append("invalid_or_expired_endorsement")
            continue
        expected=hmac.new(a.key,endorsement_payload(proof),hashlib.sha256).hexdigest()
        if not isinstance(proof.signature,str) or not re.fullmatch(r"[0-9a-f]{64}",proof.signature) or not hmac.compare_digest(expected,proof.signature):
            reasons.append("invalid_endorsement_signature")
            continue
        good.append(a)
    if (len(good)!=2 or {a.role for a in good}!={"science","owner"}
            or len({a.authority_id for a in good})!=2 or len({a.key for a in good})!=2):
        reasons.append("independent_science_and_owner_endorsements_required")
    return AdmissionDecision("policy_not_approved" if reasons else "admitted_for_future_use",policy_id,digest,
        tuple(dict.fromkeys(reasons)) or ("trusted_future_admission_only_activation_disabled",))
