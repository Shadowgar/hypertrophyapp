import os
from datetime import date
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import Base, engine
from .routers import auth, history, plan, profile, workout

APP_VERSION = os.environ.get("APP_VERSION", "dev")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Rocco's HyperTrophy Plan API", version=APP_VERSION, lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "date": date.today().isoformat(), "version": APP_VERSION}


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(profile.router, tags=["profile"])
app.include_router(plan.router, tags=["plan"])
app.include_router(workout.router, tags=["workout"])
app.include_router(history.router, tags=["history"])
