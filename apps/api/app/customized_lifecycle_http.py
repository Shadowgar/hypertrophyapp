"""Unregistered nonproduction account lifecycle. No main import, DDL or workouts.

Host selects the existing-account dependency explicitly. Bearer authentication
only: cookies cannot authorize these commands, no CORS is enabled, browser Origin
must match an explicit host origin, and cross-site Fetch requests are denied.
"""
import hashlib
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import Field, StrictInt

from .customized_preview_http import _BoundedIsolatedRequests, HEADERS
from .customized_preview_models import PreviewServer, StrictPreviewModel
from .customized_lifecycle_models import AccountActor, LifecycleError
from .customized_lifecycle_view import render_lifecycle, render_shell, SCRIPT


class RevisionCommand(StrictPreviewModel):
    expected_revision: StrictInt = Field(ge=1)


class ChallengeCommand(RevisionCommand):
    snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReviseCommand(RevisionCommand):
    request: dict


def existing_account_dependency():
    """Explicit bridge; existing verifier + account lookup keep identity authority.

    Importing the factory alone does not import settings/database. Qualification
    overrides only get_db with synthetic lookup, retaining JWT/current-user code.
    No claim of live session revocation or production capability approval.
    """
    from .deps import get_current_user
    def account(request: Request, user=Depends(get_current_user)):
        token=request.headers.get("authorization","")
        return AccountActor(user.id,hashlib.sha256(token.encode()).hexdigest(),
            ("customized:preview","customized:proposal"))
    return account


def create_lifecycle_app(*, service=None, account_dependency=None, trusted_origin: str | None=None,
                         initial_request: dict | None=None, consent_protocol="granular-candidate-consent-v1") -> FastAPI:
    server=service.server if service else PreviewServer()
    if trusted_origin is not None:
        parsed=urlsplit(trusted_origin)
        if parsed.scheme not in {"http","https"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("Exact trusted origin required")
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    headers={**HEADERS,"Content-Security-Policy":"default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"}
    app.add_middleware(_BoundedIsolatedRequests,server=server,headers=headers)

    def missing_account(): raise LifecycleError("authentication_required",401)
    dependency=account_dependency or missing_account

    async def actor(request: Request, account=Depends(dependency)):
        bearer=request.headers.get("authorization","")
        if not bearer.startswith("Bearer ") or not bearer[7:].strip() or len(bearer)>8192:
            raise LifecycleError("authentication_required",401)
        if request.headers.get("sec-fetch-site")=="cross-site":
            raise LifecycleError("origin_denied",403)
        origin=request.headers.get("origin")
        if origin is not None and (trusted_origin is None or origin!=trusted_origin):
            raise LifecycleError("origin_denied",403)
        service._guard(account)
        return account

    def key(request): return request.headers.get("idempotency-key","")

    @app.exception_handler(LifecycleError)
    async def lifecycle_error(request,exc):
        return JSONResponse({"status":exc.code},status_code=exc.status)

    @app.exception_handler(HTTPException)
    async def auth_error(request,exc):
        return JSONResponse({"status":"authentication_required" if exc.status_code==401 else "request_denied"},status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def invalid(request,exc):
        return JSONResponse({"status":"invalid_request"},status_code=422)

    @app.get("/customized/lifecycle",response_class=HTMLResponse)
    def shell():
        # No account or proposal data in this shell. Token stays in memory.
        return HTMLResponse(render_shell(server,initial_request,consent_protocol=consent_protocol))

    @app.get("/customized/lifecycle.js")
    def script(): return Response(SCRIPT,media_type="text/javascript")

    @app.post("/customized/proposals")
    def create(body: dict, request: Request, account=Depends(actor)):
        return service.create(account,body,idempotency_key=key(request))

    @app.get("/customized/proposals/{proposal_id}")
    def read(proposal_id: str, account=Depends(actor)):
        return service.get(account,proposal_id)

    @app.get("/customized/proposals/{proposal_id}/history")
    def history(proposal_id: str, account=Depends(actor)):
        return service.history(account,proposal_id)

    @app.get("/customized/proposals/{proposal_id}/render",response_class=HTMLResponse)
    def render(proposal_id: str, account=Depends(actor)):
        return HTMLResponse(render_lifecycle(service.get(account,proposal_id)))

    @app.post("/customized/proposals/{proposal_id}/challenge")
    def challenge(proposal_id: str,body: ChallengeCommand,request: Request,account=Depends(actor)):
        return service.challenge(account,proposal_id,**body.model_dump(),idempotency_key=key(request),protocol=consent_protocol)

    @app.post("/customized/proposals/{proposal_id}/accept")
    def accept(proposal_id: str,body: dict,request: Request,account=Depends(actor)):
        if consent_protocol=="compact-candidate-consent-v2" and body.get("protocol")!=consent_protocol:
            raise LifecycleError("invalid_consent_protocol",422)
        return service.accept(account,proposal_id,body,idempotency_key=key(request))

    @app.post("/customized/proposals/{proposal_id}/revisions")
    def revise(proposal_id: str,body: ReviseCommand,request: Request,account=Depends(actor)):
        return service.revise(account,proposal_id,body.request,expected_revision=body.expected_revision,idempotency_key=key(request))

    @app.post("/customized/proposals/{proposal_id}/{action}")
    def action(proposal_id: str,action: str,body: RevisionCommand,request: Request,account=Depends(actor)):
        if action=="authorization":
            return service.check_activation(account,proposal_id,expected_revision=body.expected_revision,idempotency_key=key(request))
        if action not in {"decline","withdraw"}:
            raise LifecycleError("not_found",404)
        return service.transition(account,proposal_id,action,expected_revision=body.expected_revision,idempotency_key=key(request))

    return app
