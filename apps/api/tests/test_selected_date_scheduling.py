"""Current-week selected dates on an explicit disposable test database only."""
from datetime import UTC, date, datetime, timedelta
import os
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, WorkoutOccurrence, WorkoutPlan
from app.security import create_access_token
from app.workout_identity import identified_sessions


def current_monday() -> date:
    today = datetime.now(UTC).astimezone(ZoneInfo("America/New_York")).date()
    return today - timedelta(days=today.weekday())


@pytest.fixture
def scenario():
    explicit = os.environ.get("TEST_DATABASE_URL")
    assert explicit == engine.url.render_as_string(hide_password=False)
    assert engine.dialect.name == "sqlite"
    assert Path(engine.url.database).resolve().is_relative_to(Path(os.environ["HIST_TEST_ROOT"]).resolve())
    Base.metadata.create_all(engine)
    user_id = str(uuid4())
    with SessionLocal() as db:
        db.add(User(id=user_id, email=f"{uuid4()}@example.com", name="Synthetic date test",
            password_hash="unused", split_preference="full_body",
            selected_program_id="pure_bodybuilding_phase_1_full_body",
            days_available=5, equipment_profile=["dumbbell", "barbell", "bench", "cable", "machine"],
            nutrition_phase="maintenance"))
        db.commit()
    return user_id, {"Authorization": f"Bearer {create_access_token(user_id)}"}, TestClient(app)


def request_dates(monday: date, offsets=(1, 4, 6), *, revision=0, phase="pure_bodybuilding_phase_1_full_body"):
    return {"template_id": phase, "week_start": monday.isoformat(),
        "selected_dates": [(monday + timedelta(days=offset)).isoformat() for offset in offsets],
        "timezone": "America/New_York", "target_days": len(offsets),
        "expected_placement_revision": revision}


@pytest.mark.parametrize("phase", ["pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"])
def test_authored_tue_fri_sun_dates_and_occurrence_identity(scenario, phase):
    user_id, headers, client = scenario
    monday = current_monday()
    request = request_dates(monday, phase=phase)
    response = client.post("/plan/generate-week", headers=headers, json=request)
    assert response.status_code == 200, response.text
    plan = response.json()
    assert [session["scheduled_date"] for session in plan["sessions"]] == request["selected_dates"]
    assert [session["date"] for session in plan["sessions"]] == request["selected_dates"]
    assert plan["schedule"]["timezone"] == "America/New_York"
    assert plan["schedule"]["placement_revision"] == 1
    assert len({session["workout_occurrence_id"] for session in plan["sessions"]}) == 3
    assert all(exercise.get("source_lineage", {}).get("source_slot_id")
        for session in plan["sessions"] for exercise in session["exercises"])
    assert client.get("/plan/latest-week", headers=headers).json()["schedule"] == plan["schedule"]
    with SessionLocal() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=user_id).one()
        assert row.placement_revision == 1
        assert row.schedule_timezone == "America/New_York"


def test_unstarted_revision_keeps_occurrence_ids_and_old_placement(scenario):
    user_id, headers, client = scenario
    monday = current_monday()
    first = client.post("/plan/generate-week", headers=headers, json=request_dates(monday))
    assert first.status_code == 200, first.text
    changed = client.post("/plan/generate-week", headers=headers,
        json=request_dates(monday, offsets=(0, 2, 5), revision=1))
    assert changed.status_code == 200, changed.text
    old, new = first.json(), changed.json()
    assert [session["workout_occurrence_id"] for session in old["sessions"]] == [
        session["workout_occurrence_id"] for session in new["sessions"]]
    assert new["schedule"]["placement_revision"] == 2
    assert new["schedule"]["placement_history"][0]["selected_dates"] == request_dates(monday)["selected_dates"]
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 1
    stale = client.post("/plan/generate-week", headers=headers,
        json=request_dates(monday, offsets=(0, 3, 6), revision=1))
    assert stale.status_code == 409


def test_started_occurrence_keeps_original_date(scenario):
    user_id, headers, client = scenario
    monday = current_monday()
    response = client.post("/plan/generate-week", headers=headers, json=request_dates(monday))
    assert response.status_code == 200, response.text
    session = response.json()["sessions"][0]
    exercise = session["exercises"][0]
    logged = client.post(f"/workout/{session['workout_occurrence_id']}/log-set", headers=headers,
        json={"command_id": str(uuid4()), "exercise_id": exercise["id"],
            "exercise_occurrence_id": exercise["exercise_occurrence_id"],
            "set_index": 1, "reps": 8, "weight": 25})
    assert logged.status_code == 200, logged.text
    changed = client.post("/plan/generate-week", headers=headers,
        json=request_dates(monday, offsets=(0, 2, 5), revision=1))
    assert changed.status_code == 409
    with SessionLocal() as db:
        occurrence = db.query(WorkoutOccurrence).filter_by(id=session["workout_occurrence_id"], user_id=user_id).one()
        assert occurrence.scheduled_date == monday + timedelta(days=1)
        assert occurrence.schedule_timezone == "America/New_York"
        assert occurrence.placement_revision == 1


def test_today_uses_selected_local_date_and_rest_day_is_explicit(scenario):
    _, headers, client = scenario
    monday = current_monday()
    local_today = datetime.now(UTC).astimezone(ZoneInfo("America/New_York")).date()
    today_offset = (local_today - monday).days
    other_offsets = [offset for offset in range(7) if offset != today_offset]
    offsets = tuple(sorted([today_offset, other_offsets[0], other_offsets[-1]]))
    response = client.post("/plan/generate-week", headers=headers, json=request_dates(monday, offsets=offsets))
    assert response.status_code == 200, response.text
    planned = response.json()["sessions"]
    today = client.get("/workout/today", headers=headers)
    assert today.status_code == 200, today.text
    expected = next(session for session in planned if session["scheduled_date"] == local_today.isoformat())
    assert today.json()["workout_occurrence_id"] == expected["workout_occurrence_id"]
    rest_offsets = tuple(offset for offset in range(7) if offset != today_offset)[:3]
    rest = client.post("/plan/generate-week", headers=headers,
        json=request_dates(monday, offsets=rest_offsets, revision=1))
    assert rest.status_code == 200, rest.text
    no_workout = client.get("/workout/today", headers=headers)
    assert no_workout.status_code == 404
    assert no_workout.json()["detail"] == "No workout scheduled today"


@pytest.mark.parametrize("change", [
    {"selected_dates": []},
    {"selected_dates": ["2026-09-29", "2026-09-29"]},
    {"timezone": "Not/AZone"},
    {"selected_dates": ["not-a-date", "2026-10-02"]},
])
def test_bad_dates_reject_without_persistence(scenario, change):
    user_id, headers, client = scenario
    request = request_dates(current_monday())
    request.update(change)
    request["target_days"] = len(request["selected_dates"])
    response = client.post("/plan/generate-week", headers=headers, json=request)
    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 0


def test_legacy_count_generation_cannot_erase_selected_dates(scenario):
    _, headers, client = scenario
    monday = current_monday()
    response = client.post("/plan/generate-week", headers=headers, json=request_dates(monday))
    assert response.status_code == 200, response.text
    legacy = client.post("/plan/generate-week", headers=headers,
        json={"template_id": "pure_bodybuilding_phase_1_full_body", "target_days": 3})
    assert legacy.status_code == 409


def test_cross_week_identity_is_distinct_for_same_session_slot(scenario):
    user_id, headers, client = scenario
    monday = current_monday()
    response = client.post("/plan/generate-week", headers=headers, json=request_dates(monday))
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        first = db.query(WorkoutPlan).filter_by(user_id=user_id).one()
        second = WorkoutPlan(user_id=user_id, week_start=monday + timedelta(days=7),
            split=first.split, phase=first.phase, payload=first.payload)
        db.add(second)
        db.commit()
        db.refresh(second)
        assert identified_sessions(first)[0]["workout_occurrence_id"] != identified_sessions(second)[0]["workout_occurrence_id"]


def test_preview_never_persists_profile_plan_or_occurrence(scenario):
    user_id, headers, client = scenario
    request = request_dates(current_monday())
    preview = client.post('/plan/selected-dates/preview', headers=headers, json=request)
    assert preview.status_code == 200, preview.text
    assert [s['scheduled_date'] for s in preview.json()['sessions']] == request['selected_dates']
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user.days_available == 5
        assert user.scheduling_timezone is None
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 0
        assert db.query(WorkoutOccurrence).filter_by(user_id=user_id).count() == 0
    applied = client.post('/plan/generate-week', headers=headers, json=request)
    assert applied.status_code == 200, applied.text
    assert [[e['source_lineage']['source_slot_id'] for e in s['exercises']] for s in applied.json()['sessions']] == [
        [e['source_lineage']['source_slot_id'] for e in s['exercises']] for s in preview.json()['sessions']]


def test_context_uses_persisted_timezone_and_current_week_only(scenario):
    user_id, headers, client = scenario
    request = request_dates(current_monday())
    assert client.post('/plan/generate-week', headers=headers, json=request).status_code == 200
    with SessionLocal() as db:
        assert db.get(User, user_id).scheduling_timezone == 'America/New_York'
    context = client.get('/plan/scheduling-context?timezone=Pacific/Auckland', headers=headers)
    assert context.status_code == 200, context.text
    assert context.json()['timezone'] == 'America/New_York'
    assert context.json()['week_start'] == current_monday().isoformat()
    assert context.json()['selected_dates'] == request['selected_dates']
    assert context.json()['placement_revision'] == 1


def test_count_change_explicitly_supersedes_unstarted_identity_and_preserves_dose(scenario):
    user_id, headers, client = scenario
    first = client.post('/plan/generate-week', headers=headers, json=request_dates(current_monday()))
    assert first.status_code == 200, first.text
    request = request_dates(current_monday(), offsets=(1, 5), revision=1)
    revised = client.post('/plan/generate-week', headers=headers, json=request)
    assert revised.status_code == 200, revised.text
    old_ids = {s['workout_occurrence_id'] for s in first.json()['sessions']}
    assert old_ids.isdisjoint(s['workout_occurrence_id'] for s in revised.json()['sessions'])
    assert [e['source_lineage']['source_slot_id'] for s in first.json()['sessions'] for e in s['exercises']] == [
        e['source_lineage']['source_slot_id'] for s in revised.json()['sessions'] for e in s['exercises']]
    assert sum(e['sets'] for s in first.json()['sessions'] for e in s['exercises']) == sum(
        e['sets'] for s in revised.json()['sessions'] for e in s['exercises'])
    assert revised.json()['schedule']['placement_revision'] == 2
    with SessionLocal() as db:
        rows = db.query(WorkoutPlan).filter_by(user_id=user_id).all()
        assert len(rows) == 2
        assert sum((row.payload.get('schedule') or {}).get('mode') == 'selected_dates_v1' for row in rows) == 1


def test_reschedule_same_count_preserves_every_exercise_and_identity(scenario):
    _, headers, client = scenario
    first = client.post('/plan/generate-week', headers=headers, json=request_dates(current_monday()))
    revised = client.post('/plan/generate-week', headers=headers,
        json=request_dates(current_monday(), offsets=(1, 2, 3), revision=1))
    assert revised.status_code == 200, revised.text
    assert [s['exercises'] for s in first.json()['sessions']] == [s['exercises'] for s in revised.json()['sessions']]
    assert any('Consecutive' in w for w in revised.json()['schedule']['spacing']['warnings'])


def test_legacy_other_binding_and_frequency_cannot_erase_selected_plan(scenario):
    user_id, headers, client = scenario
    first = client.post('/plan/generate-week', headers=headers, json=request_dates(current_monday()))
    assert first.status_code == 200, first.text
    count = client.post('/plan/generate-week', headers=headers,
        json={'template_id':'pure_bodybuilding_phase_2_full_body', 'target_days':3})
    assert count.status_code == 409
    frequency = client.post('/plan/adaptation/apply', headers=headers,
        json={'program_id':'pure_bodybuilding_phase_1_full_body', 'target_days':2, 'duration_weeks':1})
    assert frequency.status_code == 409
    with SessionLocal() as db:
        assert db.get(User, user_id).selected_program_id == 'pure_bodybuilding_phase_1_full_body'


def test_timezone_change_requires_separate_policy_and_rejects_without_mutation(scenario):
    user_id, headers, client = scenario
    request = request_dates(current_monday())
    assert client.post('/plan/generate-week', headers=headers, json=request).status_code == 200
    request.update(timezone='Pacific/Honolulu', expected_placement_revision=1)
    response = client.post('/plan/generate-week', headers=headers, json=request)
    assert response.status_code == 409
    with SessionLocal() as db:
        assert db.get(User, user_id).scheduling_timezone == 'America/New_York'


def test_context_requires_timezone_for_undated_user(scenario):
    _, headers, client = scenario
    assert client.get('/plan/scheduling-context', headers=headers).status_code == 422
    assert client.get('/plan/scheduling-context?timezone=Not/AZone', headers=headers).status_code == 422


def fixed_clock(monkeypatch, instant):
    from app.routers import plan, workout
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(plan, 'datetime', Clock)
    monkeypatch.setattr(workout, 'datetime', Clock)


@pytest.mark.parametrize('instant, expected_today, expected_week', [
    (datetime(2026, 11, 2, 3, 30, tzinfo=UTC), '2026-11-01', '2026-10-26'),
    (datetime(2026, 3, 9, 3, 30, tzinfo=UTC), '2026-03-08', '2026-03-02'),
])
def test_context_preserves_dst_sunday_when_utc_is_monday(scenario, monkeypatch, instant, expected_today, expected_week):
    _, headers, client = scenario
    fixed_clock(monkeypatch, instant)
    response = client.get('/plan/scheduling-context?timezone=America/New_York', headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()['local_today'] == expected_today
    assert response.json()['week_start'] == expected_week


def test_completed_today_and_next_local_week_leave_frozen_history_intact(scenario, monkeypatch):
    from test_authored_typed_execution import typed_plan
    user_id, headers, client = scenario
    instant = datetime(2026, 10, 6, 16, tzinfo=UTC)
    fixed_clock(monkeypatch, instant)
    minimal = typed_plan(user_id, raw='8-12')  # Independent synthetic two-set source fixture.
    with SessionLocal() as db:
        row = db.get(WorkoutPlan, minimal['plan_id'])
        payload = deepcopy(row.payload)
        first = payload['sessions'][0]
        first.update(date='2026-10-06', scheduled_date='2026-10-06', schedule_timezone='America/New_York', placement_revision=1)
        second = deepcopy(first)
        second.update(session_id='distinct-source-session', date='2026-10-09', scheduled_date='2026-10-09')
        second['exercises'][0]['source_lineage']['source_slot_id'] = 'synthetic:second-session:slot1'
        payload.update(week_start='2026-10-05', sessions=[first, second], schedule={
            'mode':'selected_dates_v1', 'timezone':'America/New_York', 'selected_dates':['2026-10-06', '2026-10-09'],
            'placement_revision':1, 'placement_history':[]})
        row.payload, row.week_start, row.schedule_timezone, row.placement_revision = payload, date(2026,10,5), 'America/New_York', 1
        user = db.get(User, user_id)
        user.scheduling_timezone, user.selected_program_id = 'America/New_York', 'pure_bodybuilding_phase_2_full_body'
        db.commit()
        session = identified_sessions(row)[0]
    exercise = session['exercises'][0]
    for index in (1, 2):
        response = client.post(f"/workout/{session['workout_occurrence_id']}/log-set", headers=headers,
            json={'command_id':str(uuid4()), 'exercise_id':exercise['id'], 'exercise_occurrence_id':exercise['exercise_occurrence_id'],
                'set_index':index, 'reps':10, 'weight':25})
        assert response.status_code == 200, response.text
        today = client.get('/workout/today', headers=headers)
        assert today.status_code == 200, today.text
        assert today.json()['workout_occurrence_id'] == session['workout_occurrence_id']
        assert today.json()['exercises'][0]['completed_sets'] == index
        if index == 1:
            assert today.json()['resume'] is True
    before = client.post('/plan/generate-week', headers=headers,
        json=request_dates(date(2026,10,5), revision=1, phase='pure_bodybuilding_phase_2_full_body'))
    assert before.status_code == 409
    with SessionLocal() as db:
        original = deepcopy(db.get(WorkoutOccurrence, session['workout_occurrence_id']).payload)
    fixed_clock(monkeypatch, instant + timedelta(days=7))
    context = client.get('/plan/scheduling-context?timezone=America/New_York', headers=headers)
    assert context.json()['selected_dates'] == []
    assert context.json()['plan'] is None
    assert client.get('/workout/today', headers=headers).json()['detail'] == 'No workout scheduled today'
    generated = client.post('/plan/generate-week', headers=headers,
        json=request_dates(date(2026,10,12), phase='pure_bodybuilding_phase_2_full_body'))
    assert generated.status_code == 200, generated.text
    assert session['workout_occurrence_id'] not in {s['workout_occurrence_id'] for s in generated.json()['sessions']}
    with SessionLocal() as db:
        frozen = db.get(WorkoutOccurrence, session['workout_occurrence_id'])
        assert frozen.scheduled_date == date(2026,10,6)
        assert frozen.payload == original


@pytest.mark.parametrize('offsets', [(1,2,3), (1,5)])
def test_legacy_authored_week_conversion_preserves_saved_prescriptions(scenario, offsets):
    user_id, headers, client = scenario
    response = client.post('/plan/generate-week', headers=headers,
        json={'template_id': 'pure_bodybuilding_phase_1_full_body', 'target_days': 3})
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=user_id).one()
        saved = deepcopy(row.payload)
        saved['mesocycle']['authored_week_index'] = 4
        saved['mesocycle']['week_index'] = 4
        saved['sessions'][0]['exercises'][0]['recommended_working_weight'] = 77.5
        row.payload = saved
        db.commit()
        plan_id = row.id
        before_sessions = identified_sessions(row)
    preview = client.post('/plan/selected-dates/preview', headers=headers, json=request_dates(current_monday(), offsets))
    activated = client.post('/plan/generate-week', headers=headers, json=request_dates(current_monday(), offsets))
    for response in (preview, activated):
        assert response.status_code == 200, response.text
        placed = response.json()
        assert placed['mesocycle'] == saved['mesocycle']
        # Projection-only occurrence IDs are added by activation; source content stays byte-equivalent.
        strip_projection = lambda e: {k: v for k, v in e.items() if k not in ('exercise_occurrence_id', 'workout_occurrence_id', 'execution_slot')}
        assert [strip_projection(e) for s in placed['sessions'] for e in s['exercises']] == [
            strip_projection(e) for s in saved['sessions'] for e in s['exercises']]
    after_sessions = activated.json()['sessions']
    def identity_slots(sessions):
        return {e['exercise_occurrence_id']: e['source_lineage']['source_slot_id']
            for s in sessions for e in s['exercises']}
    if len(offsets) == 3:
        assert identity_slots(after_sessions) == identity_slots(before_sessions)
        assert [s['workout_occurrence_id'] for s in after_sessions] == [s['workout_occurrence_id'] for s in before_sessions]
    else:
        assert set(identity_slots(after_sessions)).isdisjoint(identity_slots(before_sessions))
        assert activated.json()['schedule']['replaces_plan_id'] == plan_id
        with SessionLocal() as db:
            retained = db.get(WorkoutPlan, plan_id).payload
            assert retained['sessions'] == saved['sessions']
            assert retained['mesocycle'] == saved['mesocycle']
            assert retained['schedule']['mode'] == 'selected_dates_superseded_v1'


def test_new_dated_week_uses_generation_history_instead_of_resetting_to_week_one(scenario, monkeypatch):
    _, headers, client = scenario
    instant = datetime(2026, 10, 6, 16, tzinfo=UTC)
    fixed_clock(monkeypatch, instant)
    first = client.post('/plan/generate-week', headers=headers, json=request_dates(date(2026,10,5)))
    assert first.status_code == 200, first.text
    fixed_clock(monkeypatch, instant + timedelta(days=7))
    following = client.post('/plan/generate-week', headers=headers, json=request_dates(date(2026,10,12)))
    assert following.status_code == 200, following.text
    assert following.json()['mesocycle']['authored_week_index'] == 2
    assert following.json()['mesocycle']['week_index'] == 2


def test_auto_first_week_uses_existing_selector_without_preview_profile_writes(scenario):
    user_id, headers, client = scenario
    with SessionLocal() as db:
        user = db.get(User, user_id)
        user.selected_program_id = None
        user.program_selection_mode = 'auto'
        db.commit()
    request = request_dates(current_monday())
    request['template_id'] = None
    preview = client.post('/plan/selected-dates/preview', headers=headers, json=request)
    assert preview.status_code == 200, preview.text
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user.selected_program_id is None and user.program_selection_mode == 'auto'
        assert user.scheduling_timezone is None and user.days_available == 5
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 0
    activated = client.post('/plan/generate-week', headers=headers, json=request)
    assert activated.status_code == 200, activated.text
    assert activated.json()['program_template_id'] == preview.json()['program_template_id']
    assert [s['scheduled_date'] for s in activated.json()['sessions']] == request['selected_dates']
    with SessionLocal() as db:
        assert db.query(User).filter_by(id=user_id).count() == 1
        assert db.get(User, user_id).program_selection_mode == 'auto'


def test_legacy_regeneration_cannot_replace_previous_local_week_at_utc_boundary(scenario, monkeypatch):
    from app.routers import plan as plan_router
    user_id, headers, client = scenario
    fixed_clock(monkeypatch, datetime(2026,10,11,20,tzinfo=UTC))  # Auckland Monday; UTC Sunday.
    class ServerSunday(date):
        @classmethod
        def today(cls):
            return date(2026,10,11)
    monkeypatch.setattr(plan_router, 'date', ServerSunday)
    saved = {'program_template_id':'pure_bodybuilding_phase_1_full_body', 'sessions':[],
        'schedule':{'mode':'selected_dates_v1', 'selected_dates':['2026-10-06','2026-10-09','2026-10-11']}}
    with SessionLocal() as db:
        db.get(User, user_id).scheduling_timezone = 'Pacific/Auckland'
        row = WorkoutPlan(user_id=user_id, week_start=date(2026,10,5), split='full_body', phase='maintenance',
            payload=deepcopy(saved), schedule_timezone='Pacific/Auckland', placement_revision=1)
        db.add(row)
        db.commit()
        plan_id = row.id
    response = client.post('/plan/generate-week', headers=headers,
        json={'template_id':'pure_bodybuilding_phase_1_full_body', 'target_days':3})
    assert response.status_code == 409, response.text
    with SessionLocal() as db:
        assert db.get(WorkoutPlan, plan_id).payload == saved
        assert db.query(WorkoutPlan).filter_by(user_id=user_id).count() == 1
