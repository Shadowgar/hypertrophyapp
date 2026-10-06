"""Weekly-review local dates on an explicitly verified disposable SQLite target."""
from datetime import UTC, date, datetime
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url

# Verify the isolated persistence target before application imports.
explicit_url = os.environ.get("TEST_DATABASE_URL")
assert explicit_url and os.environ.get("DATABASE_URL") == explicit_url
root = Path(os.environ["HIST_TEST_ROOT"]).resolve(strict=True)
target = make_url(explicit_url)
assert target.get_backend_name() == "sqlite" and target.database not in (None, ":memory:")
database = Path(target.database).resolve()
assert root != Path("/") and database.is_relative_to(root)
with sqlite3.connect(database) as connection:
    identity = connection.execute("PRAGMA database_list").fetchall()
    assert len(identity) == 1 and Path(identity[0][2]).resolve() == database

from fastapi.testclient import TestClient
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, WeeklyCheckin, WeeklyReviewCycle
from app.routers import profile
from app.security import create_access_token


BOUNDARIES = [
    ("America/Los_Angeles", datetime(2026, 10, 4, 4, tzinfo=UTC), date(2026, 10, 3), False,
     date(2026, 9, 28), date(2026, 9, 21)),
    ("Pacific/Auckland", datetime(2026, 10, 3, 13, tzinfo=UTC), date(2026, 10, 4), True,
     date(2026, 10, 5), date(2026, 9, 28)),
]
REVIEW = {"body_weight": 83, "calories": 2500, "protein": 170, "fat": 70,
          "carbs": 260, "adherence_score": 4}


@pytest.fixture
def scenario():
    assert engine.url == target and engine.dialect.name == "sqlite"
    Base.metadata.create_all(engine)
    client = TestClient(app)  # Schema initialization belongs to this verified fixture.

    def create_user(timezone):
        user_id = str(uuid4())
        with SessionLocal() as db:
            db.add(User(id=user_id, email=f"{uuid4()}@example.invalid", name="Synthetic review clock",
                password_hash="not-a-login", scheduling_timezone=timezone,
                selected_program_id="pure_bodybuilding_phase_1_full_body",
                split_preference="full_body", days_available=5, nutrition_phase="maintenance"))
            db.commit()
        return user_id, {"Authorization": f"Bearer {create_access_token(user_id)}"}, client

    yield create_user
    client.close()


def freeze_profile_clock(monkeypatch, instant):
    class ServerDate(date):
        @classmethod
        def today(cls):
            return instant.date()

    class PlanningClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz is not None else instant.replace(tzinfo=None)

    monkeypatch.setattr(profile, "date", ServerDate)
    monkeypatch.setattr(profile, "datetime", PlanningClock)


@pytest.mark.parametrize("timezone,instant,local_day,sunday,week_start,previous_week", BOUNDARIES)
def test_status_uses_persisted_local_sunday_and_review_window(
    scenario, monkeypatch, timezone, instant, local_day, sunday, week_start, previous_week,
):
    user_id, headers, client = scenario(timezone)
    freeze_profile_clock(monkeypatch, instant)
    response = client.get("/weekly-review/status", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["today_is_sunday"] is sunday
    assert body["review_required"] is sunday
    assert body["week_start"] == week_start.isoformat()
    assert body["previous_week_start"] == previous_week.isoformat()
    assert body["previous_week_summary"]["previous_week_start"] == previous_week.isoformat()
    with SessionLocal() as db:
        assert db.query(WeeklyReviewCycle).filter_by(user_id=user_id).count() == 0


@pytest.mark.parametrize("timezone,instant,local_day,sunday,week_start,previous_week", BOUNDARIES)
def test_submit_uses_local_window_and_persists_local_reviewed_on(
    scenario, monkeypatch, timezone, instant, local_day, sunday, week_start, previous_week,
):
    user_id, headers, client = scenario(timezone)
    freeze_profile_clock(monkeypatch, instant)
    response = client.post("/weekly-review", headers=headers, json=REVIEW)
    assert response.status_code == 200, response.text
    assert response.json()["week_start"] == week_start.isoformat()
    assert response.json()["previous_week_start"] == previous_week.isoformat()
    with SessionLocal() as db:
        review = db.query(WeeklyReviewCycle).filter_by(user_id=user_id).one()
        assert review.reviewed_on == local_day
        assert review.week_start == week_start and review.previous_week_start == previous_week
        assert db.query(WeeklyCheckin).filter_by(user_id=user_id).one().week_start == week_start
    status = client.get("/weekly-review/status", headers=headers).json()
    assert status["existing_review_submitted"] is True
    assert status["review_required"] is False
    assert status["week_start"] == week_start.isoformat()


@pytest.mark.parametrize("instant,sunday,week_start", [
    (datetime(2026, 10, 4, 4, tzinfo=UTC), True, date(2026, 10, 5)),
    (datetime(2026, 10, 3, 13, tzinfo=UTC), False, date(2026, 9, 28)),
])
def test_timezone_less_users_keep_server_date_for_status_and_submission(
    scenario, monkeypatch, instant, sunday, week_start,
):
    user_id, headers, client = scenario(None)
    freeze_profile_clock(monkeypatch, instant)
    status = client.get("/weekly-review/status", headers=headers)
    assert status.status_code == 200, status.text
    assert status.json()["today_is_sunday"] is sunday
    assert status.json()["week_start"] == week_start.isoformat()
    response = client.post("/weekly-review", headers=headers, json=REVIEW)
    assert response.status_code == 200, response.text
    assert response.json()["week_start"] == week_start.isoformat()
    with SessionLocal() as db:
        assert db.query(WeeklyReviewCycle).filter_by(user_id=user_id).one().reviewed_on == instant.date()


def test_explicit_review_week_keeps_request_authority_and_local_reviewed_on(scenario, monkeypatch):
    user_id, headers, client = scenario("America/Los_Angeles")
    freeze_profile_clock(monkeypatch, datetime(2026, 10, 4, 4, tzinfo=UTC))
    response = client.post("/weekly-review", headers=headers, json={**REVIEW, "week_start": "2026-09-07"})
    assert response.status_code == 200, response.text
    assert response.json()["week_start"] == "2026-09-07"
    with SessionLocal() as db:
        review = db.query(WeeklyReviewCycle).filter_by(user_id=user_id).one()
        assert review.reviewed_on == date(2026, 10, 3)
        assert review.week_start == date(2026, 9, 7)


def test_submit_refreshes_timezone_activated_after_authentication(scenario, monkeypatch):
    user_id, headers, client = scenario(None)
    freeze_profile_clock(monkeypatch, datetime(2026, 10, 4, 4, tzinfo=UTC))
    original_lock = profile.lock_history_user

    def activation_wins_lock(db, locked_user_id):
        # Authentication has already loaded the timezone-less identity object.
        assert locked_user_id == user_id
        assert db.get(User, user_id).scheduling_timezone is None
        with SessionLocal() as activation:
            activation.get(User, user_id).scheduling_timezone = "America/Los_Angeles"
            activation.commit()
        original_lock(db, locked_user_id)

    monkeypatch.setattr(profile, "lock_history_user", activation_wins_lock)
    response = client.post("/weekly-review", headers=headers, json=REVIEW)
    assert response.status_code == 200, response.text
    assert response.json()["week_start"] == "2026-09-28"
    assert response.json()["previous_week_start"] == "2026-09-21"
    with SessionLocal() as db:
        review = db.query(WeeklyReviewCycle).filter_by(user_id=user_id).one()
        assert review.reviewed_on == date(2026, 10, 3)
        assert db.get(User, user_id).scheduling_timezone == "America/Los_Angeles"


@pytest.mark.parametrize("method,path", [("get", "/weekly-review/status"), ("post", "/weekly-review")])
def test_invalid_persisted_timezone_rejects_without_review_writes(scenario, method, path):
    user_id, headers, client = scenario("Invalid/Timezone")
    arguments = {"headers": headers}
    if method == "post":
        arguments["json"] = REVIEW
    response = getattr(client, method)(path, **arguments)
    assert response.status_code == 422, response.text
    with SessionLocal() as db:
        assert db.query(WeeklyReviewCycle).filter_by(user_id=user_id).count() == 0
        assert db.query(WeeklyCheckin).filter_by(user_id=user_id).count() == 0
        assert db.get(User, user_id).weight is None
