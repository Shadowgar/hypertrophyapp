import os
from datetime import UTC, date, datetime
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.routing import Match

from .config import settings
from .database import Base, engine
from .observability import (
    configure_logging,
    log_event,
    reset_request_action,
    reset_request_id,
    reset_request_route,
    set_request_action,
    set_request_id,
    set_request_route,
    validation_failure_event_name,
    sanitize_auth_validation_errors,
)
from .routers import auth, history, plan, profile, workout, customized, training

def customized_clock():
    return datetime.now(UTC)


APP_VERSION = os.environ.get("APP_VERSION", "dev")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.validate_signing_configuration()
    configure_logging(
        log_level=settings.log_level,
        log_file_path=settings.log_file_path,
        log_max_bytes=settings.log_max_bytes,
        log_backup_count=settings.log_backup_count,
    )
    from pathlib import Path
    from alembic.script import ScriptDirectory
    from app.schema_management import ensure_schema

    expected = ScriptDirectory(str(Path(__file__).resolve().parents[1] / "alembic")).get_current_head()
    ensure_schema(engine, Base.metadata, settings.schema_management_mode, expected)
    yield


app = FastAPI(title="FERRAVIS API", version=APP_VERSION, lifespan=lifespan)


def request_route_template(request: Request) -> str:
    """Use registered route metadata, never user-controlled path segments."""
    matched = request.scope.get("route")
    if matched is not None and hasattr(matched, "path"):
        return matched.path
    for route in app.routes:
        if route.matches(request.scope)[0] == Match.FULL:
            return getattr(route, "path", "[unmatched]")
    return "[unmatched]"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "date": date.today().isoformat(), "version": APP_VERSION}


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = sanitize_auth_validation_errors(exc.errors())
    route = request_route_template(request)
    log_event(
        validation_failure_event_name(request.url.path),
        level="warning",
        route=route,
        action=request.method.lower(),
        user_id=getattr(request.state, "user_id", None),
        request_path=route,
        validation_errors=errors,
        error_class=exc.__class__.__name__,
        error_message="Invalid request",
    )
    return JSONResponse(status_code=422, content={"detail": errors})


@app.middleware("http")
async def log_unhandled_exceptions(request: Request, call_next):
    incoming_request_id = str(request.headers.get("x-request-id") or "").strip()
    request_id = incoming_request_id[:128] if incoming_request_id else str(uuid4())
    request.state.request_id = request_id
    request_id_token = set_request_id(request_id)
    route = request_route_template(request)
    route_token = set_request_route(route)
    action_token = set_request_action(request.method.lower())
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        is_auth = request.url.path.startswith("/auth/")
        log_event(
            "request_failed_exception",
            level="error",
            route=route,
            action=request.method.lower(),
            user_id=getattr(request.state, "user_id", None),
            error_class=exc.__class__.__name__,
            error_message="Authentication operation failed" if is_auth else "Request operation failed",
        )
        return JSONResponse(status_code=500, content={"detail": "Authentication operation failed" if is_auth else "Request operation failed"})
    finally:
        reset_request_action(action_token)
        reset_request_route(route_token)
        reset_request_id(request_id_token)


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(profile.router, tags=["profile"])
app.include_router(plan.router, tags=["plan"])
app.include_router(workout.router, tags=["workout"])
app.include_router(history.router, tags=["history"])
app.include_router(customized.router, tags=["customized"])

app.include_router(training.router, tags=["training"])
