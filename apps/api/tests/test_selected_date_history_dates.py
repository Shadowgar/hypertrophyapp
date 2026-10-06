"""Performed-date history on explicitly verified disposable SQLite/PostgreSQL."""
from datetime import UTC, date, datetime, timedelta
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

explicit = os.environ.get('TEST_DATABASE_URL')
assert explicit and os.environ.get('DATABASE_URL') == explicit
target = make_url(explicit)
if target.get_backend_name() == 'postgresql':
    assert os.environ.get('M2B_POSTGRES_ISOLATED') == '1'
    assert (target.drivername, target.host, target.port, target.database, target.username) == (
        'postgresql+psycopg', '127.0.0.1', 25461, 'm2b_qualification', 'm2b_test')
    probe = create_engine(target)
    with probe.connect() as db:
        assert tuple(db.execute(text('SELECT current_database(),current_user,inet_server_port()')).one()) == (
            'm2b_qualification', 'm2b_test', 5432)
        assert db.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0021_selected_workout_dates'
    probe.dispose()
else:
    root = Path(os.environ['HIST_TEST_ROOT']).resolve(strict=True)
    assert target.get_backend_name() == 'sqlite' and target.database not in (None, ':memory:')
    database = Path(target.database).resolve()
    assert root != Path('/') and database.is_relative_to(root)
    with sqlite3.connect(database) as db:
        identity = db.execute('PRAGMA database_list').fetchall()
        assert len(identity) == 1 and Path(identity[0][2]).resolve() == database

from fastapi.testclient import TestClient
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, WorkoutOccurrence, WorkoutPlan, WorkoutSetLog
from app.routers import history, profile
from app.security import create_access_token


BOUNDARIES = [
    ('America/Los_Angeles', date(2026, 10, 11), datetime(2026, 10, 12, 1),
     datetime(2026, 10, 12, 4, tzinfo=UTC)),
    ('Pacific/Auckland', date(2026, 10, 12), datetime(2026, 10, 11, 13),
     datetime(2026, 10, 11, 14, tzinfo=UTC)),
]


def freeze_clock(monkeypatch, instant):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    class ServerDate(date):
        @classmethod
        def today(cls):
            return instant.date()
    for module in (history, profile):
        monkeypatch.setattr(module, 'datetime', Clock)
        monkeypatch.setattr(module, 'date', ServerDate)


@pytest.fixture
def scenario():
    assert engine.url == target
    if target.get_backend_name() == 'sqlite':
        Base.metadata.create_all(engine)
    client = TestClient(app)  # No lifespan; fixture/migration owns schema.
    user_ids = []

    def seed(timezone, scheduled_day, created_at, *, occurrence_owner=None, no_occurrence=False):
        user_id, occurrence_id, log_id = str(uuid4()), str(uuid4()), str(uuid4())
        with SessionLocal() as db:
            db.add(User(id=user_id, email=f'{uuid4()}@example.invalid', name='Synthetic history date',
                password_hash='not-a-login', scheduling_timezone=timezone,
                selected_program_id='pure_bodybuilding_phase_1_full_body',
                split_preference='full_body', days_available=5, nutrition_phase='maintenance'))
            db.flush()
            if not no_occurrence:
                day = scheduled_day or created_at.date()
                monday = day - timedelta(days=day.weekday())
                db.add(WorkoutOccurrence(id=occurrence_id, user_id=occurrence_owner or user_id,
                    plan_id=str(uuid4()), week_start=monday, scheduled_date=scheduled_day,
                    schedule_timezone=timezone, placement_revision=1 if scheduled_day else None,
                    session_slot=0, workout_id='synthetic-history-workout',
                    program_id='pure_bodybuilding_phase_1_full_body', payload={'exercises': []},
                    created_at=created_at))
                db.flush()
            db.add(WorkoutSetLog(id=log_id, user_id=user_id, workout_id='synthetic-history-workout',
                workout_occurrence_id=None if no_occurrence else occurrence_id,
                exercise_occurrence_id=None if no_occurrence else 'synthetic-exercise-occurrence',
                primary_exercise_id='bench_press', exercise_id='bench_press',
                set_index=1, reps=8, weight=50, created_at=created_at))
            db.add(WorkoutPlan(user_id=user_id, week_start=date(2026, 10, 5), split='full_body', phase='accumulation',
                payload={'program_template_id': 'pure_bodybuilding_phase_1_full_body', 'sessions': [
                    {'session_id': 'synthetic-review-session', 'exercises': [
                        {'id': 'bench_press', 'name': 'Bench press', 'sets': 1, 'rep_range': [8, 10],
                         'recommended_working_weight': 50}]}]}))
            db.commit()
        user_ids.append(user_id)
        return user_id, {'Authorization': f'Bearer {create_access_token(user_id)}'}, client, log_id

    yield seed
    client.close()


def stored_logs(user_id):
    with SessionLocal() as db:
        return [{c.key: getattr(row, c.key) for c in WorkoutSetLog.__table__.columns}
            for row in db.query(WorkoutSetLog).filter_by(user_id=user_id).order_by(WorkoutSetLog.id)]


@pytest.mark.parametrize('timezone,day,created_at,instant', BOUNDARIES)
def test_day_and_exact_calendar_window_use_scheduled_date_without_mutation(
    scenario, monkeypatch, timezone, day, created_at, instant,
):
    user_id, headers, client, _ = scenario(timezone, day, created_at)
    freeze_clock(monkeypatch, instant)
    original = stored_logs(user_id)
    for query_day, expected in [(day, 1), (created_at.date(), 0)]:
        detail = client.get(f'/history/day/{query_day.isoformat()}', headers=headers)
        assert detail.status_code == 200, detail.text
        assert detail.json()['totals']['set_count'] == expected
        calendar = client.get('/history/calendar', headers=headers,
            params={'start_date': query_day.isoformat(), 'end_date': query_day.isoformat()})
        assert calendar.status_code == 200, calendar.text
        assert len(calendar.json()['days']) == 1
        assert calendar.json()['days'][0]['set_count'] == expected
        assert calendar.json()['active_days'] == expected
    exercise = client.get('/history/exercise/bench_press', headers=headers).json()['history']
    assert len(exercise) == 1
    assert exercise[0]['performed_date'] == day.isoformat()
    assert exercise[0]['created_at'] == created_at.isoformat()
    assert stored_logs(user_id) == original


@pytest.mark.parametrize('timezone,day,created_at,instant', BOUNDARIES)
def test_weekly_review_uses_performed_week_not_utc_timestamp_week(
    scenario, monkeypatch, timezone, day, created_at, instant,
):
    user_id, headers, client, _ = scenario(timezone, day, created_at)
    freeze_clock(monkeypatch, instant)
    before = stored_logs(user_id)
    status = client.get('/weekly-review/status', headers=headers)
    assert status.status_code == 200, status.text
    expected = 1 if day.weekday() == 6 else 0
    assert status.json()['previous_week_summary']['completed_sets_total'] == expected
    assert stored_logs(user_id) == before


@pytest.mark.parametrize('timezone,day,created_at,instant', BOUNDARIES)
def test_analytics_and_calendar_default_clock_are_local_and_heatmap_is_dated(
    scenario, monkeypatch, timezone, day, created_at, instant,
):
    _, headers, client, _ = scenario(timezone, day, created_at)
    freeze_clock(monkeypatch, instant)
    calendar = client.get('/history/calendar', headers=headers).json()
    assert calendar['end_date'] == day.isoformat()
    analytics = client.get('/history/analytics', headers=headers, params={'limit_weeks': 2}).json()
    assert analytics['window']['end_date'] == day.isoformat()
    monday = day - timedelta(days=day.weekday())
    week = next(w for w in analytics['volume_heatmap']['weeks'] if w['week_start'] == monday.isoformat())
    assert week['days'][day.weekday()]['sets'] == 1
    assert sum(c['sets'] for w in analytics['volume_heatmap']['weeks'] for c in w['days']) == 1


@pytest.mark.parametrize('no_occurrence', [False, True])
def test_null_and_legacy_occurrences_keep_created_day_and_audit_timestamp(scenario, no_occurrence):
    from app.history_dates import performed_log_rows
    timestamp = datetime(2026, 10, 12, 1, 23, 45)
    user_id, headers, client, log_id = scenario(None, None, timestamp, no_occurrence=no_occurrence)
    before = stored_logs(user_id)
    with SessionLocal() as db:
        rows = performed_log_rows(db, user_id=user_id, start_date=timestamp.date(), end_date=timestamp.date())
    assert len(rows) == 1 and rows[0]['id'] == log_id
    assert rows[0]['performed_date'] == timestamp.date() and rows[0]['created_at'] == timestamp
    assert set(rows[0]) == set(before[0]) | {'performed_date'}
    assert client.get('/history/day/2026-10-12', headers=headers).json()['totals']['set_count'] == 1
    assert stored_logs(user_id) == before


def test_cross_owner_occurrence_cannot_supply_date_and_other_user_logs_are_excluded(scenario):
    from app.history_dates import performed_log_rows
    owner_id, _, _, _ = scenario(None, None, datetime(2026, 10, 1), no_occurrence=True)
    user_id, headers, client, log_id = scenario('America/Los_Angeles', date(2026, 10, 11),
        datetime(2026, 10, 12, 1), occurrence_owner=owner_id)
    with SessionLocal() as db:
        rows = performed_log_rows(db, user_id=user_id)
        assert len(rows) == 1 and rows[0]['id'] == log_id and rows[0]['performed_date'] == date(2026, 10, 12)
        assert not performed_log_rows(db, user_id=user_id, start_date=date(2026, 10, 11), end_date=date(2026, 10, 11))
    assert client.get('/history/day/2026-10-11', headers=headers).json()['totals']['set_count'] == 0
    assert client.get('/history/day/2026-10-12', headers=headers).json()['totals']['set_count'] == 1


def test_void_and_next_week_correction_keep_original_scheduled_membership(scenario, monkeypatch):
    from app.history_dates import performed_log_rows
    user_id, headers, client, old_id = scenario('America/Los_Angeles', date(2026, 10, 11), datetime(2026, 10, 12, 1))
    amended_id = str(uuid4())
    with SessionLocal() as db:
        old = db.get(WorkoutSetLog, old_id)
        old.voided_at = datetime(2026, 10, 19, 12)
        old.void_reason = 'corrected synthetic set'
        db.add(WorkoutSetLog(id=amended_id, user_id=user_id, workout_id=old.workout_id,
            workout_occurrence_id=old.workout_occurrence_id, exercise_occurrence_id=old.exercise_occurrence_id,
            primary_exercise_id=old.primary_exercise_id, exercise_id=old.exercise_id,
            set_index=1, reps=10, weight=55, supersedes_id=old_id,
            amended_at=datetime(2026, 10, 19, 12), created_at=datetime(2026, 10, 19, 12)))
        db.commit()
    before = stored_logs(user_id)
    with SessionLocal() as db:
        rows = performed_log_rows(db, user_id=user_id, start_date=date(2026, 10, 11), end_date=date(2026, 10, 11))
        assert [r['id'] for r in rows] == [amended_id]
        assert rows[0]['created_at'] == datetime(2026, 10, 19, 12)
        assert rows[0]['supersedes_id'] == old_id
    freeze_clock(monkeypatch, datetime(2026, 10, 12, 4, tzinfo=UTC))
    assert client.get('/weekly-review/status', headers=headers).json()['previous_week_summary']['completed_sets_total'] == 1
    assert client.get('/history/day/2026-10-11', headers=headers).json()['totals']['total_volume'] == 550
    assert client.get('/history/day/2026-10-19', headers=headers).json()['totals']['set_count'] == 0
    assert stored_logs(user_id) == before


def test_date_window_is_applied_in_sql_before_fetch_and_boundaries_are_inclusive(scenario):
    from app.history_dates import performed_log_query, performed_log_rows
    user_id, _, _, _ = scenario('Pacific/Auckland', date(2026, 10, 12), datetime(2026, 10, 11, 13))
    with SessionLocal() as db:
        query = performed_log_query(db, user_id=user_id, start_date=date(2026, 10, 12), end_date=date(2026, 10, 12))
        compiled = str(query.statement.compile(dialect=engine.dialect)).lower()
        assert 'left outer join' in compiled and 'workout_occurrences.user_id = workout_set_logs.user_id' in compiled
        assert 'coalesce' in compiled and 'date(' in compiled and 'voided_at is null' in compiled
        assert 'workout_set_logs.user_id =' in compiled and '>=' in compiled and '<=' in compiled
        assert len(performed_log_rows(db, user_id=user_id, start_date=date(2026, 10, 12), end_date=date(2026, 10, 12))) == 1
        assert not performed_log_rows(db, user_id=user_id, end_date=date(2026, 10, 11))
        assert not performed_log_rows(db, user_id=user_id, start_date=date(2026, 10, 13))


def test_timezone_less_default_calendar_and_analytics_keep_server_day(scenario, monkeypatch):
    _, headers, client, _ = scenario(None, None, datetime(2026, 10, 12, 1), no_occurrence=True)
    freeze_clock(monkeypatch, datetime(2026, 10, 12, 4, tzinfo=UTC))
    assert client.get('/history/calendar', headers=headers).json()['end_date'] == '2026-10-12'
    assert client.get('/history/analytics', headers=headers).json()['window']['end_date'] == '2026-10-12'


@pytest.mark.parametrize('scheduled_day,timestamp,expected', [
    (date(2026, 10, 5), datetime(2026, 10, 4, 13), 1),
    (date(2026, 10, 4), datetime(2026, 10, 5, 1), 0),
])
def test_analytics_start_window_filters_by_performed_date_before_fetch(
    scenario, monkeypatch, scheduled_day, timestamp, expected,
):
    _, headers, client, _ = scenario('Pacific/Auckland', scheduled_day, timestamp)
    freeze_clock(monkeypatch, datetime(2026, 10, 11, 14, tzinfo=UTC))
    body = client.get('/history/analytics', headers=headers, params={'limit_weeks': 2}).json()
    assert body['window']['start_date'] == '2026-10-05'
    assert sum(cell['sets'] for week in body['volume_heatmap']['weeks'] for cell in week['days']) == expected
    assert sum(item['total_sets'] for item in body['strength_trends']) == expected


def test_weekly_summary_ignores_newer_retained_superseded_plan(scenario, monkeypatch):
    user_id, headers, client, _ = scenario('America/Los_Angeles', date(2026, 10, 11), datetime(2026, 10, 12, 1))
    with SessionLocal() as db:
        db.add(WorkoutPlan(user_id=user_id, week_start=date(2026, 10, 5), split='full_body', phase='accumulation',
            created_at=datetime(2026, 10, 13), payload={
                'program_template_id': 'pure_bodybuilding_phase_1_full_body',
                'schedule': {'mode': 'selected_dates_superseded_v1'},
                'sessions': [{'session_id': 'superseded-synthetic-session', 'exercises': [
                    {'id': 'bench_press', 'name': 'Bench press', 'sets': 99, 'rep_range': [8, 10]}]}]}))
        db.commit()
    freeze_clock(monkeypatch, datetime(2026, 10, 12, 4, tzinfo=UTC))
    with SessionLocal() as db:
        before = [(p.id, p.payload) for p in db.query(WorkoutPlan).filter_by(user_id=user_id).order_by(WorkoutPlan.id)]
    summary = client.get('/weekly-review/status', headers=headers).json()['previous_week_summary']
    assert summary['planned_sets_total'] == 1
    assert summary['completed_sets_total'] == 1
    assert summary['completion_pct'] == 100
    with SessionLocal() as db:
        assert [(p.id, p.payload) for p in db.query(WorkoutPlan).filter_by(user_id=user_id).order_by(WorkoutPlan.id)] == before


def test_analytics_excludes_future_scheduled_receipt_but_explicit_history_retains_it(scenario, monkeypatch):
    today = date(2026, 10, 6)
    future_day = date(2026, 10, 11)
    user_id, headers, client, _ = scenario('America/New_York', today, datetime(2026, 10, 6, 16))
    occurrence_id = str(uuid4())
    with SessionLocal() as db:
        db.add(WorkoutOccurrence(id=occurrence_id, user_id=user_id, plan_id=str(uuid4()),
            week_start=date(2026, 10, 5), scheduled_date=future_day, schedule_timezone='America/New_York',
            placement_revision=1, session_slot=1, workout_id='synthetic-future-workout',
            program_id='pure_bodybuilding_phase_1_full_body', payload={'exercises': []},
            created_at=datetime(2026, 10, 6, 16, 5)))
        db.flush()
        db.add(WorkoutSetLog(user_id=user_id, workout_id='synthetic-future-workout',
            workout_occurrence_id=occurrence_id, exercise_occurrence_id='synthetic-future-exercise',
            primary_exercise_id='bench_press', exercise_id='bench_press', set_index=1,
            reps=8, weight=99, created_at=datetime(2026, 10, 6, 16, 5)))
        db.commit()
    before = stored_logs(user_id)
    assert len(before) == 2
    freeze_clock(monkeypatch, datetime(2026, 10, 6, 16, 10, tzinfo=UTC))
    response = client.get('/history/analytics', headers=headers, params={'limit_weeks': 2})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['window']['end_date'] == today.isoformat()
    assert sum(item['total_sets'] for item in body['strength_trends']) == 1
    assert sum(cell['sets'] for week in body['volume_heatmap']['weeks'] for cell in week['days']) == 1
    this_week = next(week for week in body['volume_heatmap']['weeks'] if week['week_start'] == '2026-10-05')
    assert this_week['days'][1]['sets'] == 1 and this_week['days'][6]['sets'] == 0
    explicit = client.get(f'/history/day/{future_day.isoformat()}', headers=headers)
    assert explicit.status_code == 200 and explicit.json()['totals']['set_count'] == 1
    assert stored_logs(user_id) == before
