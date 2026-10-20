"""Unregistered staging/test app factory. Production main never imports this.

Authentication and schedule context are server-owned ports. The default factory
is disabled, has no authenticator/allowlist/bundles, and no database/startup work.
It does not install production account auth or expose activation/logging routes.
"""
import inspect
from typing import Awaitable, Callable

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse

from core_engine.customized.models import PlanningContext
from .customized_preview_models import PreviewRequest, PreviewPrincipal, PreviewServer, PreviewResponse
from .customized_preview_service import preview_program
from .customized_preview_view import render_preview

CSP="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
HEADERS={"Cache-Control":"no-store","Content-Security-Policy":CSP,"X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer"}


class _BoundedIsolatedRequests:
    def __init__(self,app,server,headers=None):
        self.app,self.server=app,server
        self.headers=HEADERS if headers is None else headers

    async def __call__(self,scope,receive,send):
        if scope["type"]!="http":
            await self.app(scope,receive,send)
            return
        if self.server.enabled is not True or self.server.environment not in {"staging","test"}:
            await JSONResponse({"status":"feature_disabled","message":"Experimental preview unavailable; no approved production policy is admitted."},status_code=404,headers=self.headers)(scope,receive,send)
            return
        chunks=[]; size=0
        while True:
            message=await receive()
            if message["type"]=="http.disconnect":
                return
            chunk=message.get("body",b"");size+=len(chunk)
            if size>16384:
                await JSONResponse({"status":"request_too_large"},status_code=413,headers=self.headers)(scope,receive,send)
                return
            chunks.append(chunk)
            if not message.get("more_body",False):
                break
        sent=False
        async def bounded_receive():
            nonlocal sent
            if sent:
                return await receive()
            sent=True
            return {"type":"http.request","body":b"".join(chunks),"more_body":False}
        async def secure_send(message):
            if message["type"]=="http.response.start":
                message={**message,"headers":[*message.get("headers",[]),*((k.lower().encode(),v.encode()) for k,v in self.headers.items())]}
            await send(message)
        await self.app(scope,bounded_receive,secure_send)


def create_preview_app(*, server: PreviewServer | None=None,
    authenticate: Callable[[Request], PreviewPrincipal | None | Awaitable[PreviewPrincipal | None]] | None=None,
    context_port: Callable[[str], PlanningContext | None] | None=None) -> FastAPI:
    server=PreviewServer() if server is None else server
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    app.add_middleware(_BoundedIsolatedRequests,server=server)

    async def principal(request: Request):
        actor=authenticate(request) if authenticate else None
        actor=await actor if inspect.isawaitable(actor) else actor
        if not isinstance(actor,PreviewPrincipal) or not actor.subject:
            raise HTTPException(401,"Authenticated preview principal required")
        if actor.subject not in server.allowed_subjects or "customized:preview" not in actor.scopes:
            raise HTTPException(403,"Experimental preview access required")
        return actor

    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        # Never echo input/body, credentials, raw values or arbitrary error text.
        return JSONResponse({"status":"invalid_request","message":"Check required preview fields and date-only values."},status_code=422)

    def decide(body,actor):
        result=preview_program(body,server=server,principal=actor,
            context=context_port(body.timezone) if context_port else None)
        code=409 if not result.sessions else 200
        return result,code

    @app.post("/customized/preview",response_model=PreviewResponse)
    def preview(body: PreviewRequest, actor: PreviewPrincipal=Depends(principal)):
        result,code=decide(body,actor)
        return JSONResponse(result.model_dump(mode="json"),status_code=code)

    @app.post("/customized/preview/render",response_class=HTMLResponse)
    def render(body: PreviewRequest, actor: PreviewPrincipal=Depends(principal)):
        result,code=decide(body,actor)
        return HTMLResponse(render_preview(result),status_code=code)

    return app
