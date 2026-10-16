"""Canonical content identities; no implicit clock, filesystem or network reads."""
from dataclasses import asdict, is_dataclass, replace
from datetime import date, datetime
from hashlib import sha256
import json
import math

from .models import SciencePolicy


def canonical(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {"invalid_number": str(value)}
    if is_dataclass(value):
        return canonical(asdict(value))
    if isinstance(value, dict):
        return {str(k): canonical(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [canonical(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def content_hash(value) -> str:
    return sha256(json.dumps(canonical(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def policy_content_hash(policy: SciencePolicy | None) -> str:
    # Approval binds the entire policy payload except lifecycle/approval fields.
    return content_hash(replace(policy, status="provisional", approval=None) if policy else None)


def policy_is_approved(policy: SciencePolicy) -> bool:
    approval = policy.approval
    return bool(policy.status == "approved" and approval and approval.reviewer_reference
                and approval.decision_reference and approval.policy_hash == policy_content_hash(policy))
