"""Explicit staging entitlement/session boundary layered on existing app auth.

The application currently verifies sub/exp and current User only. This adapter
adds no global JWT revocation or role migration. A host must independently supply
an enabled grant for this exact verified account/credential/session. No JWT claim
or client request can create a grant. All production/default ports are absent.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
from typing import Protocol

from core_engine.customized.audit import content_hash
from .customized_lifecycle_models import AccountActor,LifecycleError

SCOPES=frozenset(('customized:preview','customized:proposal'))


@dataclass(frozen=True)
class SessionGrant:
    subject: str
    session_id: str
    credential_revision: str
    entitlement_reference: str
    revision: int
    scopes: tuple[str,...]
    valid_from: datetime
    expires_at: datetime
    enabled: bool


class SessionAccessPort(Protocol):
    def resolve(self,subject: str,session_id: str) -> SessionGrant | None: ...


class StagingAccessGate:
    def __init__(self,port: SessionAccessPort,*,clock,current_credential_revision):
        self.port,self.clock=port,clock
        # Server-owned fresh read, independent of the request ORM identity map.
        # A production adapter must serialize this check with credential/grant
        # changes and candidate commit; no such adapter is installed here.
        self.current_credential_revision=current_credential_revision

    def _grant(self,subject,session_id):
        grant=self.port.resolve(subject,session_id)
        if grant is None:raise LifecycleError('entitlement_required',403)
        if (not isinstance(grant,SessionGrant) or grant.subject!=subject or grant.session_id!=session_id
                or not grant.entitlement_reference or type(grant.revision) is not int or grant.revision<1):
            raise LifecycleError('invalid_session_grant',401)
        now=self.clock()
        if (now.tzinfo is None or grant.valid_from.tzinfo is None or grant.expires_at.tzinfo is None
                or grant.enabled is not True or not grant.valid_from<=now<grant.expires_at):
            raise LifecycleError('session_unavailable',401)
        if not SCOPES<=set(grant.scopes):raise LifecycleError('capability_required',403)
        return grant

    def bind(self,user,authorization_header):
        session_id=hashlib.sha256(authorization_header.encode()).hexdigest()
        grant=self._grant(user.id,session_id)
        credential=hashlib.sha256(user.password_hash.encode()).hexdigest()
        if not grant.credential_revision or credential!=grant.credential_revision:
            raise LifecycleError('session_unavailable',401)
        return AccountActor(user.id,session_id,grant.scopes,content_hash(grant))

    def authorize(self,actor):
        grant=self._grant(actor.subject,actor.session_id)
        if (not grant.credential_revision
                or self.current_credential_revision(actor.subject)!=grant.credential_revision):
            raise LifecycleError('session_unavailable',401)
        if actor.authorization_revision!=content_hash(grant):
            raise LifecycleError('stale_session_grant',401)


def staging_account_dependency(gate: StagingAccessGate):
    # Explicit lazy bridge retains the app's actual signature/expiry/current-user
    # verifier and can use a disposable lookup in tests. No main/startup import.
    from fastapi import Depends,Request
    from .deps import get_current_user
    def account(request: Request,user=Depends(get_current_user)):
        return gate.bind(user,request.headers.get('authorization',''))
    return account
