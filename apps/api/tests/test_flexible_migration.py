"""Opt-in populated PostgreSQL migration rehearsal; never use runtime defaults."""
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.skipif(os.environ.get("FLEXIBLE_MIGRATION_POSTGRES") != "1",
    reason="Requires independently verified, explicitly opted-in disposable PostgreSQL")
OLD_REVISION = "0026_initial_calibration"
NEW_REVISION = "0027_flexible_training"
API_ROOT = Path(__file__).resolve().parents[1]


def _verified_engine():
    raw = os.environ["TEST_DATABASE_URL"]
    target = make_url(raw)
    assert os.environ.get("TEST_DATABASE_DISPOSABLE") == "1"
    assert target.get_backend_name() == "postgresql" and not target.query
    assert target.host == "127.0.0.1" and target.port == int(os.environ["TEST_DATABASE_PORT"]) and target.port != 5432
    assert target.username == os.environ["TEST_DATABASE_USER"] == "flexible_migration_test"
    assert target.database == os.environ["TEST_DATABASE_NAME"] and target.database.startswith("flexible_migration_qualification_")
    assert os.environ["DATABASE_URL"] == raw
    engine = sa.create_engine(raw)
    with engine.connect() as connection:
        assert tuple(connection.execute(sa.text("SELECT current_database(),current_user")).one()) == (target.database, target.username)
        assert not sa.inspect(connection).get_table_names(), "Migration test requires its own NEW empty disposable database"
    return engine


def _alembic():
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    return config


def _populate_legacy(engine):
    """Populate every preexisting application table through its reflected FKs."""
    metadata = sa.MetaData()
    metadata.reflect(engine)
    inserted = {}
    now = datetime(2026, 10, 19, 12)
    overrides = {"users": {"email": "synthetic-migration@example.invalid", "age": 43, "weight": 84.123,
            "days_available": 3, "onboarding_answers": {"preserved": [False, 0, None]}},
        "user_interface_preferences": {"theme_family": "graphite", "appearance": "dark", "weight_unit": "lb"},
        "customized_candidate_sessions": {"valid_from": now.replace(tzinfo=timezone.utc),
            "expires_at": (now + timedelta(days=1)).replace(tzinfo=timezone.utc)},
        "workout_occurrences": {"payload": {"session_id": "legacy-workout", "exercises": [{"id": "press", "sets": 2, "rep_range": [8, 12]}]}},
        "workout_set_logs": {"reps": 9, "weight": 45.359237, "rpe": None, "set_kind": "work"}}
    with engine.begin() as connection:
        for table in metadata.sorted_tables:
            if table.name == "alembic_version":
                continue
            existing = connection.execute(sa.select(table)).mappings().all()
            if existing:
                inserted[table.name] = dict(existing[0])
                continue
            values = {}
            for column in table.columns:
                if column.nullable:
                    values[column.name] = None
                elif isinstance(column.type, sa.Uuid):
                    values[column.name] = uuid4()
                elif isinstance(column.type, sa.Boolean):
                    values[column.name] = False
                elif isinstance(column.type, sa.Integer):
                    values[column.name] = 1
                elif isinstance(column.type, sa.Numeric):
                    values[column.name] = 12.375
                elif isinstance(column.type, sa.DateTime):
                    values[column.name] = now.replace(tzinfo=timezone.utc) if column.type.timezone else now
                elif isinstance(column.type, sa.Date):
                    values[column.name] = date(2026, 10, 19)
                elif isinstance(column.type, sa.JSON):
                    values[column.name] = {"synthetic": table.name, "preserved": [1, "two", None]}
                else:
                    text = f"synthetic-{table.name}-{column.name}"
                    values[column.name] = text[:column.type.length] if getattr(column.type, "length", None) else text
                for foreign in column.foreign_keys:
                    parent = inserted.get(foreign.column.table.name)
                    if parent and not column.nullable:
                        values[column.name] = parent[foreign.column.name]
            values.update(overrides.get(table.name, {}))
            connection.execute(table.insert().values(**values))
            inserted[table.name] = values
    return metadata


def _snapshot(engine, metadata):
    with engine.connect() as connection:
        return {table.name: sorted(json.dumps(dict(row), sort_keys=True, default=str)
            for row in connection.execute(sa.select(table)).mappings())
            for table in metadata.sorted_tables if table.name != "alembic_version"}


def _reject(connection, statement, constraint):
    with pytest.raises(IntegrityError) as error:
        with connection.begin_nested():
            connection.execute(statement)
    assert error.value.orig.diag.constraint_name == constraint


def _index_drift(differences, legacy):
    result = []
    for item in differences:
        if not isinstance(item, tuple) or item[0] not in ("add_index", "remove_index"):
            continue
        operation, index = item
        if (index.table.name in legacy.tables
                and {column.name for column in index.columns} <= set(legacy.tables[index.table.name].columns.keys())):
            result.append((operation, index.table.name, index.name, tuple(column.name for column in index.columns)))
    return sorted(result)


def _constraints(engine):
    from app.models import User, TrainingSequence, TrainingSequenceCommand, WorkoutOccurrence, WorkoutSetLog
    now = datetime(2026, 10, 30, 12)
    with engine.begin() as connection:
        for identity in ("owner-a", "owner-b"):
            connection.execute(User.__table__.insert().values(id=identity, email=f"{identity}@example.invalid", name=identity,
                password_hash="synthetic-not-a-login", created_at=now))
        sequence = dict(id="current-a", user_id="owner-a", program_id="authored", source_digest="0" * 64,
            source_catalog={}, timezone="UTC", revision=1, cursor=0, state="active", consent={}, created_at=now)
        connection.execute(TrainingSequence.__table__.insert().values(**sequence))
        _reject(connection, TrainingSequence.__table__.insert().values(**{**sequence, "id": "second-a", "state": "attention_required"}), "uq_training_sequence_current")
        connection.execute(TrainingSequence.__table__.insert().values(**{**sequence, "id": "historical-a", "state": "finished"}))
        for invalid, constraint in (({"revision": 0}, "ck_training_sequence_revision"),
                ({"cursor": -1}, "ck_training_sequence_revision"),
                ({"expected_sessions_per_week": 8}, "ck_training_sequence_frequency"),
                ({"state": "invented"}, "ck_training_sequence_state")):
            _reject(connection, TrainingSequence.__table__.insert().values(**{**sequence, "id": str(uuid4()), "user_id": "owner-b", **invalid}), constraint)
        occurrence = dict(id="flexible-a", user_id="owner-a", plan_id=None, week_start=None, session_slot=0,
            sequence_id="current-a", source_position=0, execution_state="active", workout_id="source-native",
            payload={"preserved": True}, created_at=now)
        connection.execute(WorkoutOccurrence.__table__.insert().values(**occurrence))
        _reject(connection, WorkoutOccurrence.__table__.insert().values(**{**occurrence, "id": "foreign-occ", "user_id": "owner-b", "source_position": 1}), "fk_occurrence_sequence_owner")
        _reject(connection, WorkoutOccurrence.__table__.insert().values(**{**occurrence, "id": "duplicate-position"}), "uq_sequence_source_position")
        _reject(connection, WorkoutOccurrence.__table__.insert().values(**{**occurrence, "id": "invented-anchor", "plan_id": "fake-plan", "source_position": 1}), "ck_occurrence_anchor")
        _reject(connection, WorkoutOccurrence.__table__.insert().values(**{**occurrence, "id": "unbound-anchor", "sequence_id": None, "source_position": None}), "ck_occurrence_anchor")
        receipt = dict(id="receipt-a", user_id="owner-a", command_id="command", request_digest="1" * 64,
            sequence_id="current-a", operation="start", response={"preserved": True}, created_at=now)
        connection.execute(TrainingSequenceCommand.__table__.insert().values(**receipt))
        _reject(connection, TrainingSequenceCommand.__table__.insert().values(**{**receipt, "id": "foreign-command", "user_id": "owner-b"}), "fk_sequence_command_owner")
        _reject(connection, TrainingSequenceCommand.__table__.insert().values(**{**receipt, "id": "duplicate-command"}), "uq_training_sequence_command_user")
        connection.execute(WorkoutSetLog.__table__.insert().values(id="actual-date", user_id="owner-a", workout_id="source-native",
            workout_occurrence_id="flexible-a", exercise_occurrence_id="slot", primary_exercise_id="press", exercise_id="press",
            set_index=1, reps=8, weight=45.359237, created_at=now, performed_local_date=date(2026, 10, 29),
            performed_timezone="America/New_York", execution_context_id="context-a"))
        assert connection.execute(sa.select(WorkoutSetLog.performed_local_date).where(WorkoutSetLog.id == "actual-date")).scalar_one() == date(2026, 10, 29)


def test_populated_0026_upgrade_preserves_all_legacy_values_and_enforces_flexible_ownership():
    engine = _verified_engine()
    command.upgrade(_alembic(), OLD_REVISION)
    legacy = _populate_legacy(engine)
    before = _snapshot(engine, legacy)
    assert all(before.values()), "Every legacy application table must contain synthetic preservation evidence"
    from app.database import Base
    from app import models  # noqa: F401
    with engine.connect() as connection:
        inherited_indexes = _index_drift(compare_metadata(MigrationContext.configure(connection), Base.metadata), legacy)
    command.upgrade(_alembic(), NEW_REVISION)
    assert _snapshot(engine, legacy) == before
    from app.schema_management import ensure_schema
    ensure_schema(engine, Base.metadata, "validate", NEW_REVISION)
    with engine.connect() as connection:
        assert set(sa.inspect(connection).get_table_names()) - set(legacy.tables) == {"training_sequences", "training_sequence_commands"}
        assert connection.execute(sa.text("SELECT count(*) FROM training_sequences")).scalar_one() == 0
        assert connection.execute(sa.text("SELECT count(*) FROM training_sequence_commands")).scalar_one() == 0
        assert connection.execute(sa.text("SELECT schedule_mode,expected_sessions_per_week FROM users")).one() == ("calendar", None)
        assert connection.execute(sa.text("SELECT sequence_id,source_position,execution_state,execution_context,advancement FROM workout_occurrences")).one() == (None, None, None, None, None)
        assert connection.execute(sa.text("SELECT performed_local_date,performed_timezone,execution_context_id FROM workout_set_logs")).one() == (None, None, None)
        schema_diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
        assert _index_drift(schema_diff, legacy) == inherited_indexes
        assert all(item[0] in ("add_index", "remove_index") for item in schema_diff), repr(schema_diff)
        assert len(schema_diff) == len(inherited_indexes), repr(schema_diff)
    _constraints(engine)
    evidence = {"old_revision": OLD_REVISION, "new_revision": NEW_REVISION,
        "preserved_populated_tables": sorted(before), "preserved_rows": sum(len(rows) for rows in before.values()),
        "new_model_schema_diff": [], "inherited_index_drift": inherited_indexes,
        "postgresql_constraints": "passed"}
    output = os.environ.get("FLEXIBLE_MIGRATION_EVIDENCE")
    if output:
        target = Path(output).resolve()
        assert target.is_relative_to(Path(os.environ["CI_TEST_ROOT"]).resolve(strict=True))
        target.write_text(json.dumps(evidence, indent=2) + "\n")
    engine.dispose()
