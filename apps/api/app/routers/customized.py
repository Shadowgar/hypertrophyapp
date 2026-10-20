"""Authenticated application routes for the existing Customized lifecycle."""
from datetime import UTC, datetime
from hashlib import sha256

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from .auth import DbSession
from ..config import settings
from ..deps import get_current_user
from ..customized_application import build_service,application_catalog
from core_engine.customized.pilot import ACTIONS
from ..customized_lifecycle_models import LifecycleError
from ..customized_consent_summary import COMPACT_PROTOCOL
from ..customized_preview_models import StrictPreviewModel
from ..customized_lifecycle_http import ChallengeCommand, RevisionCommand, ReviseCommand
from pydantic import Field, StrictInt, StrictBool

router=APIRouter()


class ActivateCommand(StrictPreviewModel):
    expected_revision: StrictInt=Field(ge=1)
    snapshot_hash: str=Field(pattern=r'^[0-9a-f]{64}$')


def clock():
    # One injectable application clock, never a client planning instant.
    from ..main import customized_clock
    return customized_clock()


def context(request: Request, db: DbSession, user=Depends(get_current_user)):
    if not settings.customized_enabled:
        raise HTTPException(404,'Customized is not enabled in this deployment')
    if db.get_bind().dialect.name!='postgresql':
        raise HTTPException(503,'Customized requires migrated PostgreSQL persistence')
    if request.headers.get('sec-fetch-site')=='cross-site':
        raise HTTPException(403,'Cross-site action denied')
    authorization=request.headers.get('authorization','')
    try:
        claims=jwt.decode(authorization.removeprefix('Bearer '),settings.jwt_secret,algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError:
        raise HTTPException(401,'Session expired; sign in again') from None
    if not claims.get('jti') or claims.get('cv')!=sha256(user.password_hash.encode()).hexdigest():
        raise HTTPException(401,'Sign in again to use Customized')
    service,gate=build_service(db.get_bind(),user.id,clock,enabled=settings.customized_enabled)
    try:
        with gate.unit.account(user.id) as conn:
            # Existing/revoked fingerprints are never automatically reissued.
            from sqlalchemy import text
            current_password=conn.execute(text('SELECT password_hash FROM users WHERE id=:s'),dict(s=user.id)).scalar_one()
            if claims['cv']!=sha256(current_password.encode()).hexdigest():
                raise LifecycleError('session_credentials_changed',401)
            exists=conn.execute(text('SELECT 1 FROM customized_candidate_sessions WHERE subject=:s AND credential_fingerprint=:f'),
                dict(s=user.id,f=sha256(authorization.encode()).hexdigest())).first()
            if not exists:
                gate.issue(user.id,authorization,entitlement_reference='authenticated_account_customized_choice_v1',
                    scopes=('customized:preview','customized:proposal'),valid_from=clock(),
                    expires_at=datetime.fromtimestamp(claims['exp'],UTC))
            actor=gate.bind(user,authorization)
    except LifecycleError as exc:
        raise HTTPException(exc.status,exc.code) from None
    return service,actor,gate


def run(fn):
    try:return fn()
    except LifecycleError as exc:raise HTTPException(exc.status,exc.code) from None


def key(request):return request.headers.get('idempotency-key','')


@router.get('/customized/options')
def options(ctx=Depends(context)):
    service,_,_=ctx
    from ..customized_inventory import inventory_issues
    return dict(inventory_issues=inventory_issues(application_catalog(),service.inventory),program='Customized Full Body',policy_status='provisional',
        bundles=[dict(id=b.bundle_id,name=b.display_name,training_status=b.standard.science.training_status) for b in service.server.bundles],
        equipment=sorted({tag for e in application_catalog().exercises for tag in e.required_equipment}|{'barbell','rack'}),
        inventory=service.inventory,variants=[dict(id=e.variant_id,name=e.name,implement=e.load_identity.implement,basis=e.load_identity.basis) for e in application_catalog().exercises],
        restrictions=[f'avoid_{a}' for a in ACTIONS])


@router.post('/customized/session/revoke')
def revoke(ctx=Depends(context)):
    _,actor,gate=ctx
    return run(lambda:(gate.revoke(actor.subject,actor.session_id),{'status':'revoked'})[1])


@router.post('/customized/proposals')
def create(body:dict,request:Request,ctx=Depends(context)):
    service,actor,_=ctx
    return run(lambda:service.create(actor,body,idempotency_key=key(request)))


@router.get('/customized/proposals/{proposal_id}')
def read(proposal_id:str,ctx=Depends(context)):
    service,actor,_=ctx
    return run(lambda:service.get(actor,proposal_id))


@router.get('/customized/proposals/{proposal_id}/history')
def history(proposal_id:str,ctx=Depends(context)):
    service,actor,_=ctx
    return run(lambda:service.history(actor,proposal_id))


@router.post('/customized/proposals/{proposal_id}/challenge')
def challenge(proposal_id:str,body:ChallengeCommand,request:Request,ctx=Depends(context)):
    service,actor,_=ctx
    return run(lambda:service.challenge(actor,proposal_id,**body.model_dump(),protocol=COMPACT_PROTOCOL,idempotency_key=key(request)))


@router.post('/customized/proposals/{proposal_id}/accept')
def accept(proposal_id:str,body:dict,request:Request,ctx=Depends(context)):
    service,actor,_=ctx
    if body.get('protocol')!=COMPACT_PROTOCOL:raise HTTPException(422,'Single informed acknowledgement required')
    return run(lambda:service.accept(actor,proposal_id,body,idempotency_key=key(request)))


@router.post('/customized/proposals/{proposal_id}/activate')
def activate(proposal_id:str,body:ActivateCommand,request:Request,ctx=Depends(context)):
    service,actor,_=ctx
    return run(lambda:service.activate(actor,proposal_id,**body.model_dump(),idempotency_key=key(request)))


@router.post('/customized/proposals/{proposal_id}/revisions')
def revise(proposal_id:str,body:ReviseCommand,request:Request,ctx=Depends(context)):
    service,actor,_=ctx
    return run(lambda:service.revise(actor,proposal_id,body.request,expected_revision=body.expected_revision,idempotency_key=key(request)))


class ReschedulePreviewCommand(StrictPreviewModel):
    expected_revision: StrictInt=Field(ge=1)
    expected_placement_revision: StrictInt=Field(ge=1)
    selected_dates: list[str]=Field(min_length=3,max_length=3)
    timezone: str=Field(min_length=1,max_length=64)


class RescheduleConfirmCommand(StrictPreviewModel):
    expected_revision: StrictInt=Field(ge=1)
    expected_placement_revision: StrictInt=Field(ge=1)
    digest: str=Field(pattern=r'^[0-9a-f]{64}$')
    agree: StrictBool


@router.get('/customized/active')
def active_plans(ctx=Depends(context)):
    service,actor,_=ctx
    return run(lambda:service.active(actor))


@router.post('/customized/proposals/{proposal_id}/replacement')
def replacement(proposal_id:str,body:ReviseCommand,request:Request,ctx=Depends(context)):
    service,actor,_=ctx
    return run(lambda:service.create_replacement(actor,proposal_id,body.request,expected_revision=body.expected_revision,idempotency_key=key(request)))


@router.post('/customized/proposals/{proposal_id}/reschedule/preview')
def reschedule_preview(proposal_id:str,body:ReschedulePreviewCommand,request:Request,ctx=Depends(context)):
    service,actor,_=ctx
    return run(lambda:service.preview_reschedule(actor,proposal_id,dict(selected_dates=body.selected_dates,timezone=body.timezone),
        expected_revision=body.expected_revision,expected_placement_revision=body.expected_placement_revision,idempotency_key=key(request)))


@router.post('/customized/proposals/{proposal_id}/reschedule/confirm')
def reschedule_confirm(proposal_id:str,body:RescheduleConfirmCommand,request:Request,ctx=Depends(context)):
    service,actor,_=ctx
    return run(lambda:service.confirm_reschedule(actor,proposal_id,**body.model_dump(),idempotency_key=key(request)))


@router.post('/customized/proposals/{proposal_id}/{action}')
def transition(proposal_id:str,action:str,body:RevisionCommand,request:Request,ctx=Depends(context)):
    service,actor,_=ctx
    if action not in {'decline','withdraw'}:raise HTTPException(404,'Not found')
    return run(lambda:service.transition(actor,proposal_id,action,expected_revision=body.expected_revision,idempotency_key=key(request)))


@router.get('/customized/profile')
def equipment_profile(ctx=Depends(context)):
    from sqlalchemy.orm import Session
    from ..customized_inventory import read_profile
    service,actor,gate=ctx
    with gate.unit.account(actor.subject) as conn:
        run(lambda:gate.authorize(actor))
        with Session(bind=conn,join_transaction_mode='rollback_only') as db:
            return read_profile(db,actor.subject)


from ..customized_inventory import ProfileCommand

@router.put('/customized/profile')
def save_equipment_profile(body:ProfileCommand,ctx=Depends(context)):
    from sqlalchemy.orm import Session
    from ..models import TrainingEquipmentProfile
    from ..customized_inventory import read_profile,bind_report_setups
    from datetime import datetime,UTC
    _,actor,gate=ctx
    with gate.unit.account(actor.subject) as conn:
        run(lambda:gate.authorize(actor))
        with Session(bind=conn,join_transaction_mode='rollback_only') as db:
            current=read_profile(db,actor.subject);data=bind_report_setups(current,body.profile.model_dump(mode='json'))
            if current['revision']!=body.expected_revision:
                if current['profile']==data and current['revision']==body.expected_revision+1:return current
                raise HTTPException(409,'Inventory changed; reload before editing')
            row=db.get(TrainingEquipmentProfile,actor.subject)
            if row is None:row=TrainingEquipmentProfile(user_id=actor.subject);db.add(row)
            row.revision=current['revision']+1;row.data=data;row.updated_at=datetime.now(UTC).replace(tzinfo=None)
            db.flush()
            return read_profile(db,actor.subject)
