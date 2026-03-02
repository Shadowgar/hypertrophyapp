from datetime import date

from fastapi import FastAPI

from .database import Base, engine
from .routers import auth, history, plan, profile, workout

app = FastAPI(title="Rocco's HyperTrophy Plan API", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "date": date.today().isoformat()}


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(profile.router, tags=["profile"])
app.include_router(plan.router, tags=["plan"])
app.include_router(workout.router, tags=["workout"])
app.include_router(history.router, tags=["history"])
