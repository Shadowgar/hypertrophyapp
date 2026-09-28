"""Behavior, audit, negative boundaries and PostgreSQL transaction races."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.main import app
from app.models import ExerciseState, WorkoutSetLog, WorkoutSessionState, User
from app.security import create_access_token
from app.workout_history import state_snapshot
from test_workout_occurrence_identity import scenario, plan, submission, log


def progression(user):
    with SessionLocal() as db:
        return state_snapshot(db.query(ExerciseState).filter_by(user_id=user, exercise_id="same-catalog").first())


def session_projection(user, session, slot=0):
    with SessionLocal() as db:
        row = db.query(WorkoutSessionState).filter_by(user_id=user, workout_occurrence_id=session["workout_occurrence_id"],
            exercise_occurrence_id=session["exercises"][slot]["exercise_occurrence_id"]).one()
        return {k: getattr(row, k) for k in ("completed_sets", "total_logged_reps", "total_logged_weight", "remaining_sets", "set_history", "recommended_weight", "last_guidance")}


def undo(client, headers, session, *, slot=0, command=None):
    return client.post(f"/workout/{session['workout_occurrence_id']}/undo-last-set", headers=headers,
        json={"command_id": command or str(uuid4()), "exercise_id": "same-catalog", "exercise_occurrence_id": session["exercises"][slot]["exercise_occurrence_id"]})


def correct(client, headers, record, *, reps=4, weight=30, command=None, **extra):
    return client.post(f"/workout/set/{record}/correct", headers=headers,
        json={"command_id": command or str(uuid4()), "reps": reps, "weight": weight, "reason": "Correct entry", **extra})


def test_undo_restores_initial_projection_and_retains_original_and_retry(scenario):
    user, headers, client = scenario
    before = progression(user)
    session = plan(user, date(2026, 9, 7))
    payload = submission(session, index=3)
    result = log(client, headers, session, payload)
    assert result.status_code == 200
    record = result.json()["id"]
    assert progression(user)["exposure_count"] == 1
    undone = undo(client, headers, session)
    assert undone.status_code == 200, undone.text
    assert progression(user) == before
    state = session_projection(user, session)
    assert state["completed_sets"] == state["total_logged_reps"] == state["total_logged_weight"] == 0
    assert state["set_history"] == [] and state["remaining_sets"] == 3
    assert log(client, headers, session, payload).json() == result.json()
    assert log(client, headers, session, {**payload, "reps": 11}).status_code == 409
    assert progression(user) == before
    audit = client.get(f"/workout/set/{record}/audit", headers=headers).json()["revisions"]
    assert len(audit) == 1 and not audit[0]["effective"]
    assert audit[0]["reps"] == 10 and audit[0]["weight"] == 25 and audit[0]["rpe"] is None
    assert audit[0]["voided_at"] and audit[0]["source"] == "user_undo"
    assert client.get(f"/workout/{session['workout_occurrence_id']}/progress", headers=headers).json()["completed_total"] == 0


def test_multiple_exposures_undo_restores_every_prior_progression_field(scenario):
    user, headers, client = scenario
    first = plan(user, date(2026, 9, 7))
    assert log(client, headers, first, {**submission(first, index=3), "reps": 4}).status_code == 200
    before = progression(user)
    before_session = session_projection(user, first)
    second = plan(user, date(2026, 9, 14))
    assert log(client, headers, second, {**submission(second, index=3), "reps": 14}).status_code == 200
    assert progression(user) != before
    assert undo(client, headers, second).status_code == 200
    assert progression(user) == before
    assert session_projection(user, first) == before_session
    assert client.get(f"/workout/{first['workout_occurrence_id']}/progress", headers=headers).json()["completed_total"] == 1


def test_undo_restores_captured_existing_projection_not_invented_legacy_evidence(scenario):
    user, headers, client = scenario
    with SessionLocal() as db:
        db.add(WorkoutSetLog(user_id=user, workout_id="unknown-legacy", primary_exercise_id="same-catalog", exercise_id="same-catalog",
            set_index=1, reps=9, weight=17, rpe=None, created_at=datetime(2026, 1, 1)))
        db.add(ExerciseState(user_id=user, exercise_id="same-catalog", current_working_weight=17, exposure_count=7,
            consecutive_under_target_exposures=2, fatigue_score=4, last_progression_action="hold", last_updated_at=datetime(2026, 1, 1)))
        db.commit()
    before = progression(user)
    session = plan(user, date(2026, 9, 7))
    assert log(client, headers, session, submission(session, index=3)).status_code == 200
    result = undo(client, headers, session)
    assert result.status_code == 200, result.text
    assert result.json()["decision_trace"]["earlier_context_missing"] is True
    assert progression(user) == before
    with SessionLocal() as db:
        legacy = db.query(WorkoutSetLog).filter_by(user_id=user, workout_id="unknown-legacy").one()
        assert legacy.workout_occurrence_id is None and legacy.exercise_occurrence_id is None and legacy.rpe is None
        assert legacy.voided_at is None and legacy.replay_context is None and legacy.weight == 17
        legacy_id = legacy.id
    assert correct(client, headers, legacy_id).status_code == 409
    assert progression(user) == before


def test_correction_replays_in_original_order_and_effective_views_never_double_count(scenario):
    user, headers, client = scenario
    session = plan(user, date(2026, 9, 7))
    original = log(client, headers, session, submission(session, index=3)).json()
    corrected = correct(client, headers, original["id"], rpe=None)
    assert corrected.status_code == 200, corrected.text
    replacement = corrected.json()["effective_set_id"]
    audit = client.get(f"/workout/set/{replacement}/audit", headers=headers).json()["revisions"]
    assert len(audit) == 2 and audit[0]["id"] == original["id"]
    assert audit[0]["reps"] == 10 and audit[0]["weight"] == 25 and not audit[0]["effective"]
    assert audit[1]["supersedes_id"] == original["id"] and audit[1]["effective"]
    assert audit[1]["reps"] == 4 and audit[1]["weight"] == 30 and audit[1]["rpe"] is None
    assert audit[1]["created_at"] == audit[0]["created_at"] and audit[1]["amended_at"]
    state = session_projection(user, session)
    assert state["completed_sets"] == 1 and state["total_logged_reps"] == 4 and state["total_logged_weight"] == 30
    assert progression(user)["exposure_count"] == 1 and progression(user)["consecutive_under_target_exposures"] == 1
    history = client.get("/history/exercise/same-catalog", headers=headers).json()["history"]
    assert len(history) == 1 and history[0]["id"] == replacement and history[0]["weight"] == 30
    summary = client.get(f"/workout/{session['workout_occurrence_id']}/summary", headers=headers).json()
    assert summary["completed_total"] == 1 and summary["exercises"][0]["average_performed_weight"] == 30
    assert undo(client, headers, session).status_code == 200
    assert client.get("/history/exercise/same-catalog", headers=headers).json()["history"] == []
    assert progression(user) is None


def test_correction_week_two_and_repeated_slot_are_isolated(scenario):
    user, headers, client = scenario
    first = plan(user, date(2026, 9, 7), repeats=True)
    second = plan(user, date(2026, 9, 14), repeats=True)
    first_record = log(client, headers, first, submission(first)).json()
    assert log(client, headers, second, submission(second, slot=0)).status_code == 200
    target = log(client, headers, second, submission(second, slot=1)).json()
    earlier = session_projection(user, first)
    other_slot = session_projection(user, second)
    assert correct(client, headers, target["id"]).status_code == 200
    assert session_projection(user, first) == earlier
    assert session_projection(user, second) == other_slot
    assert session_projection(user, second, slot=1)["total_logged_reps"] == 4
    assert client.get(f"/workout/set/{first_record['id']}/audit", headers=headers).json()["revisions"][0]["effective"]


def test_correction_before_later_exposure_matches_fresh_effective_history(scenario):
    user, headers, client = scenario
    first = plan(user, date(2026, 9, 7))
    original = log(client, headers, first, {**submission(first, index=3), "reps": 14}).json()
    second = plan(user, date(2026, 9, 14))
    assert log(client, headers, second, {**submission(second, index=3), "reps": 6}).status_code == 200
    assert correct(client, headers, original["id"], reps=4, weight=25).status_code == 200
    rebuilt = progression(user)
    with SessionLocal() as db:
        other = User(id=str(uuid4()), email=f"{uuid4()}@example.com", name="Replay control", password_hash="unused")
        db.add(other); db.commit(); other_id=other.id
    other_headers = {"Authorization": f"Bearer {create_access_token(other_id)}"}
    for week, reps in [(date(2026, 9, 7), 4), (date(2026, 9, 14), 6)]:
        occurrence = plan(other_id, week)
        assert log(client, other_headers, occurrence, {**submission(occurrence, index=3), "reps": reps}).status_code == 200
    control = progression(other_id)
    assert {k:v for k,v in rebuilt.items() if k != "last_updated_at"} == {k:v for k,v in control.items() if k != "last_updated_at"}


def test_history_commands_retry_conflict_and_undo_cannot_remove_future_attempt(scenario):
    user, headers, client = scenario
    session = plan(user, date(2026, 9, 7))
    payload = submission(session)
    original = log(client, headers, session, payload).json()
    command = str(uuid4())
    first = correct(client, headers, original["id"], command=command)
    assert first.status_code == 200
    assert correct(client, headers, original["id"], command=command).json() == first.json()
    assert correct(client, headers, original["id"], command=command, reps=5).status_code == 409
    assert correct(client, headers, original["id"]).status_code == 409
    undo_command = str(uuid4())
    undone = undo(client, headers, session, command=undo_command)
    assert undone.status_code == 200
    assert log(client, headers, session, payload).json() == original
    assert log(client, headers, session, submission(session)).status_code == 200
    before = progression(user)
    assert undo(client, headers, session, command=undo_command).json() == undone.json()
    assert progression(user) == before
    assert client.get(f"/workout/{session['workout_occurrence_id']}/progress", headers=headers).json()["completed_total"] == 1


def test_correction_owner_boundary_and_transaction_rollback(scenario, monkeypatch):
    from app.routers import workout
    user, headers, client = scenario
    session = plan(user, date(2026, 9, 7))
    original = log(client, headers, session, submission(session)).json()
    before = progression(user)
    with SessionLocal() as db:
        other=User(id=str(uuid4()), email=f"{uuid4()}@example.com", name="Other", password_hash="unused")
        db.add(other);db.commit();other_id=other.id
    other_headers={"Authorization": f"Bearer {create_access_token(other_id)}"}
    assert correct(client, other_headers, original["id"]).status_code == 404
    assert client.get(f"/workout/set/{original['id']}/audit", headers=other_headers).status_code == 404
    def failure(*args, **kwargs): raise RuntimeError("Synthetic reducer failure")
    monkeypatch.setattr(workout, "rebuild_exercise_state", failure)
    response = correct(TestClient(app, raise_server_exceptions=False), headers, original["id"])
    assert response.status_code == 500
    assert progression(user) == before
    with SessionLocal() as db:
        rows = db.query(WorkoutSetLog).filter_by(user_id=user).all()
        assert len(rows) == 1 and rows[0].voided_at is None


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL transaction qualification")
@pytest.mark.parametrize("action", ["correct", "undo"])
def test_postgres_concurrent_log_and_history_action_are_coherent(scenario, action):
    user, headers, client = scenario
    session = plan(user, date(2026, 9, 7))
    original = log(client, headers, session, submission(session)).json()
    barrier = Barrier(2)
    def mutate():
        with TestClient(app) as current:
            barrier.wait(timeout=10)
            return correct(current, headers, original["id"]) if action == "correct" else undo(current, headers, session)
    def append():
        with TestClient(app) as current:
            barrier.wait(timeout=10)
            return log(current, headers, session, submission(session, index=2))
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(mutate),pool.submit(append)]
        results=[job.result(timeout=30) for job in jobs]
    assert [r.status_code for r in results] == [200,200]
    with SessionLocal() as db:
        rows = db.query(WorkoutSetLog).filter_by(user_id=user).filter(WorkoutSetLog.voided_at.is_(None)).all()
        state=db.query(WorkoutSessionState).filter_by(user_id=user).one()
        assert state.completed_sets == len(rows) == (2 if action=="correct" else 1)
        assert state.total_logged_reps == sum(row.reps for row in rows)
        assert state.total_logged_weight == sum(row.weight for row in rows)
        assert db.query(ExerciseState).filter_by(user_id=user).one().exposure_count == len(rows)


def test_correction_invalidates_later_advice_without_erasing_payloads_or_applied_decisions(scenario):
    from app.models import CoachingRecommendation, WeeklyReviewCycle
    from app.workout_history import valid_weekly_reviews
    user, headers, client = scenario
    session = plan(user, date(2026, 9, 7))
    original = log(client, headers, session, submission(session)).json()
    with SessionLocal() as db:
        preview=CoachingRecommendation(user_id=user, template_id="full_body_v1", recommendation_type="coach_preview", current_phase="maintenance",
            recommended_phase="maintenance", progression_action="hold", request_payload={}, recommendation_payload={"retained": True}, status="previewed")
        applied=CoachingRecommendation(user_id=user, template_id="full_body_v1", recommendation_type="phase_apply", current_phase="maintenance",
            recommended_phase="maintenance", progression_action="hold", request_payload={}, recommendation_payload={"retained": True}, status="applied")
        review=WeeklyReviewCycle(user_id=user, reviewed_on=date.today(), week_start=date(2026, 9, 28), previous_week_start=date(2026, 9, 21),
            body_weight=80, calories=2500, protein=170, fat=70, carbs=260, adherence_score=4, faults={}, adjustments={"original": True}, summary={"retained": True})
        db.add_all([preview,applied,review]);db.commit();preview_id,applied_id,review_id=preview.id,applied.id,review.id
    assert correct(client, headers, original["id"]).status_code == 200
    response=client.post("/plan/intelligence/apply-phase", headers=headers,json={"recommendation_id": preview_id, "confirm": True})
    assert response.status_code == 409
    with SessionLocal() as db:
        assert db.get(CoachingRecommendation,preview_id).status == "invalidated_history"
        assert db.get(CoachingRecommendation,preview_id).recommendation_payload == {"retained":True}
        assert db.get(CoachingRecommendation,applied_id).status == "applied"
        assert db.get(WeeklyReviewCycle,review_id).adjustments == {"original":True}
        assert db.get(WeeklyReviewCycle,review_id).summary["retained"] is True
        assert valid_weekly_reviews(db).filter_by(user_id=user).count() == 0


def test_technique_child_correction_and_undo_never_replace_working_set_projection(scenario):
    user, headers, client = scenario
    session=plan(user,date(2026,9,7))
    assert log(client,headers,session,submission(session)).status_code==200
    before=session_projection(user,session)
    child={**submission(session), "parent_set_index":1,"set_kind":"drop_set","technique":{"ordinal":1},"reps":5,"weight":15}
    original=log(client,headers,session,child)
    assert original.status_code==200,original.text
    assert session_projection(user,session)==before
    assert correct(client,headers,original.json()["id"],reps=6,weight=16).status_code==200
    assert session_projection(user,session)==before
    assert progression(user)["exposure_count"]==1
    assert client.get(f"/workout/{session['workout_occurrence_id']}/summary",headers=headers).json()["completed_total"]==1
    assert undo(client,headers,session).status_code==200
    assert session_projection(user,session)==before
    assert progression(user)["exposure_count"]==1


def test_working_set_technique_metadata_cannot_bypass_logical_slot_gate(scenario):
    user, headers, client=scenario
    session=plan(user,date(2026,9,7))
    assert log(client,headers,session,submission(session)).status_code==200
    assert log(client,headers,session,{**submission(session),"technique":{"ordinal":2}}).status_code==409
