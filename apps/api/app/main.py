import os
from datetime import date
from contextlib import asynccontextmanager
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import settings
from .database import Base, engine
from .observability import (
    configure_logging,
    log_event,
    reset_request_id,
    set_request_id,
    validation_failure_event_name,
)
from .routers import auth, history, plan, profile, workout

APP_VERSION = os.environ.get("APP_VERSION", "dev")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(
        log_level=settings.log_level,
        log_file_path=settings.log_file_path,
        log_max_bytes=settings.log_max_bytes,
        log_backup_count=settings.log_backup_count,
    )
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Rocco's HyperTrophy Plan API", version=APP_VERSION, lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "date": date.today().isoformat(), "version": APP_VERSION}


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    messages = [error.get("msg", "Validation error") for error in exc.errors()]
    validation_errors: list[dict[str, Any]] = []
    for error in exc.errors():
        loc = ".".join(str(part) for part in error.get("loc", []))
        validation_errors.append(
            {
                "field": loc,
                "rejected_value": error.get("input"),
                "range": error.get("ctx"),
                "error_type": error.get("type"),
                "message": error.get("msg"),
            }
        )
    log_event(
        validation_failure_event_name(request.url.path),
        level="warning",
        route=request.url.path,
        action=request.method.lower(),
        user_id=getattr(request.state, "user_id", None),
        request_path=request.url.path,
        validation_errors=validation_errors,
        error_class=exc.__class__.__name__,
        error_message="; ".join(messages),
    )
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


@app.middleware("http")
async def log_unhandled_exceptions(request: Request, call_next):
    incoming_request_id = str(request.headers.get("x-request-id") or "").strip()
    request_id = incoming_request_id[:128] if incoming_request_id else str(uuid4())
    request.state.request_id = request_id
    request_id_token = set_request_id(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        log_event(
            "request_failed_exception",
            level="exception",
            route=request.url.path,
            action=request.method.lower(),
            user_id=getattr(request.state, "user_id", None),
            error_class=exc.__class__.__name__,
            error_message=str(exc),
        )
        raise
    finally:
        reset_request_id(request_id_token)


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(profile.router, tags=["profile"])
app.include_router(plan.router, tags=["plan"])
app.include_router(workout.router, tags=["workout"])
app.include_router(history.router, tags=["history"])
