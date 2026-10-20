"""Full additive Alembic, retention, containment and restore qualification.

Uses only a newly provisioned harness-owned cluster. It never opens an inherited
DB URL, resets a schema, downgrades, or contacts an application service.
"""
import argparse
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from .bootstrap import bootstrap
from .provision import provision
from .target import open_target

REPO = Path(__file__).resolve().parents[2]
HEAD = '0024_merge_authored_customized'


def signature(engine, tables=None):
    with engine.connect() as conn:
        tables = tables or conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars().all()
        return {table: tuple(conn.execute(text(
            "SELECT count(*),md5(COALESCE(string_agg(to_jsonb(t)::text,'' ORDER BY to_jsonb(t)::text),'')) FROM "
            + conn.dialect.identifier_preparer.quote(table) + ' t')).one()) for table in tables}


def upgrade(manifest, revision, log):
    m = json.loads(manifest.read_text())
    url = URL.create('postgresql+psycopg', username=m['user'], password=m['password'],
        host=m['host'], port=m['port'], database=m['database'])
    start = time.monotonic()
    result = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', revision],
        cwd=REPO/'apps/api', env={**os.environ, 'DATABASE_URL': url.render_as_string(hide_password=False)},
        capture_output=True, text=True)
    with log.open('a') as output:
        output.write(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('Alembic failed; inspect private rehearsal log')
    return round(time.monotonic() - start, 3)


def owned_cluster(m):
    info = json.loads(subprocess.check_output(['docker', 'inspect', m['container']], text=True))[0]
    assert info['Id'] == m['container_id']
    assert info['Config']['Labels']['hypertrophy.scope'] == 'c3b2b97-disposable'
    assert all(v['Type'] == 'tmpfs' for v in info['Mounts'])
    assert info['NetworkSettings']['Ports']['5432/tcp'][0]['HostIp'] == '127.0.0.1'
    return info


def new_database(source_manifest):
    m = json.loads(source_manifest.read_text())
    owned_cluster(m)
    name = 'c3b2b97_fullchain_' + uuid4().hex[:10]
    subprocess.run(['docker', 'exec', m['container'], 'createdb', '-U', m['user'], name], check=True)
    path = source_manifest.parent/(name + '.json')
    url = URL.create('postgresql+psycopg', username=m['user'], password=m['password'],
        host=m['host'], port=m['port'], database=name)
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            assert tuple(conn.execute(text('SELECT current_database(),current_user')).one()) == (name, m['user'])
            assert conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")).scalar_one() == 0
            conn.exec_driver_sql('CREATE TABLE c3b2b_disposable_marker(marker varchar(64) NOT NULL)')
            conn.execute(text('INSERT INTO c3b2b_disposable_marker VALUES(:marker)'), {'marker': m['marker']})
    finally:
        engine.dispose()
    path.write_text(json.dumps({**m, 'database': name})); path.chmod(0o600)
    verified = open_target(path); verified.dispose()
    return path


def seed_authored(engine, revision):
    from app.models import (User, PasswordResetToken, WorkoutPlan, WorkoutOccurrence,
        WorkoutSetLog, WorkoutLogCommand, WorkoutSessionState, AuthoredLoadState)
    from app.security import hash_password
    now = datetime(2026, 10, 19, 12)
    with engine.begin() as conn:
        for phase in (1, 2):
            prefix = 'synthetic-retained-phase' + str(phase)
            program = f'pure_bodybuilding_phase_{phase}_full_body'
            conn.execute(User.__table__.insert().values(id=prefix, email=prefix+'@synthetic.invalid',
                name='Synthetic authored retention', password_hash=hash_password('Synthetic-only-safe-123!'),
                selected_program_id=program, created_at=now))
            conn.execute(PasswordResetToken.__table__.insert().values(id=prefix+'-used-reset', user_id=prefix,
                token_hash=str(phase)*64, expires_at=now+timedelta(minutes=30), used_at=now, created_at=now))
            conn.execute(PasswordResetToken.__table__.insert().values(id=prefix+'-pending-reset', user_id=prefix,
                token_hash=str(phase+2)*64, expires_at=now+timedelta(minutes=30), used_at=None, created_at=now))
            payload = {'program_template_id': program, 'mode': 'authored', 'synthetic': True,
                'source_lineage': {'phase': phase, 'source_sha256': str(phase)*64},
                'prescription': {'sets': 2, 'rep_range': [8, 12], 'effort': None}}
            conn.execute(WorkoutPlan.__table__.insert().values(id=prefix+'-plan', user_id=prefix,
                week_start=date(2026,10,19), split='full_body', phase='maintenance', payload=payload,
                placement_revision=2, schedule_timezone='America/New_York', created_at=now))
            conn.execute(WorkoutOccurrence.__table__.insert().values(id=prefix+'-occurrence', user_id=prefix,
                plan_id=prefix+'-plan', week_start=date(2026,10,19), scheduled_date=date(2026,10,19),
                schedule_timezone='America/New_York', placement_revision=2, session_slot=0,
                workout_id=prefix+'-workout', program_id=program, payload=payload, created_at=now))
            for correction in (False, True):
                key = prefix + ('-corrected' if correction else '-original')
                conn.execute(WorkoutSetLog.__table__.insert().values(id=key, user_id=prefix,
                    workout_id=prefix+'-workout', workout_occurrence_id=prefix+'-occurrence',
                    exercise_occurrence_id=prefix+'-slot', primary_exercise_id='synthetic-exercise',
                    exercise_id='synthetic-exercise', command_id=key, request_digest=('b' if correction else 'a')*64,
                    set_index=1, reps=9 if correction else 8, weight=12 if correction else 10, rpe=None,
                    amended_at=None if correction else now, supersedes_id=prefix+'-original' if correction else None,
                    replay_context={'source':payload,'unknown_effort':True}, created_at=now))
                conn.execute(WorkoutLogCommand.__table__.insert().values(id=key, user_id=prefix, command_id=key,
                    request_digest=('b' if correction else 'a')*64, workout_occurrence_id=prefix+'-occurrence',
                    exercise_occurrence_id=prefix+'-slot', response={'id':key, 'retry_retained':True}, created_at=now))
            conn.execute(WorkoutSessionState.__table__.insert().values(id=prefix+'-state', user_id=prefix,
                workout_id=prefix+'-workout', workout_occurrence_id=prefix+'-occurrence', exercise_occurrence_id=prefix+'-slot',
                primary_exercise_id='synthetic-exercise', exercise_id='synthetic-exercise', planned_sets=2,
                planned_reps_min=8, planned_reps_max=12, planned_weight=10, recommended_reps_min=8,
                recommended_reps_max=12, recommended_weight=10, last_guidance='synthetic unknown effort',
                completed_sets=1,total_logged_reps=9,total_logged_weight=12,remaining_sets=1,set_history=[{'reps':9,'weight':12}]))
            if revision == '0022_authored_load_states':
                conn.execute(AuthoredLoadState.__table__.insert().values(id=prefix+'-load', user_id=prefix,
                    comparison_key=str(phase)*64, primary_exercise_id='synthetic-exercise',
                    source_identity=payload, state={'action':'monitor','unknown_effort':True}))


@contextmanager
def application(engine):
    # Deliberately no metadata/create_all: missing migration tables must fail.
    from fastapi.testclient import TestClient
    from pytest import MonkeyPatch
    from app.main import app
    import app.main as main
    from app.database import get_db
    from app.config import settings
    from app.routers import workout, plan
    patch = MonkeyPatch()
    Session = sessionmaker(bind=engine)
    def database():
        with Session() as db:
            yield db
    app.dependency_overrides[get_db] = database
    patch.setattr(settings, 'customized_enabled', True)
    patch.setattr(main, 'customized_clock', lambda: datetime(2026,10,19,12,tzinfo=UTC), raising=False)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            instant = main.customized_clock()
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    patch.setattr(workout, 'datetime', Clock); patch.setattr(plan, 'datetime', Clock)
    client = TestClient(app)
    try:
        yield client, Session, patch
    finally:
        client.close(); app.dependency_overrides.clear(); patch.undo()


def seed_customized(engine):
    sys.path.insert(0, str(REPO/'apps/api/tests'))
    from test_customized_application import test_real_workflow_publish_today_log_correct_complete_history
    with application(engine) as (client, Session, _):
        account = dict(email=uuid4().hex+'@example.com', name='Synthetic migration', password='Synthetic-only-safe-123!')
        registration = client.post('/auth/register', json=account)
        assert registration.status_code == 200
        headers = {'Authorization':'Bearer '+registration.json()['access_token']}
        test_real_workflow_publish_today_log_correct_complete_history((client, headers, Session, account))


def read_restored(engine):
    before = signature(engine)
    with application(engine) as (client, Session, patch):
        from app.config import settings
        patch.setattr(settings, 'customized_enabled', False)
        with Session() as db:
            email, occurrence, receipt = db.execute(text(
                "SELECT u.email,l.workout_occurrence_id,l.id FROM users u JOIN workout_set_logs l ON l.user_id=u.id "
                "JOIN workout_occurrences o ON o.id=l.workout_occurrence_id WHERE o.program_id='customized_full_body_v1' "
                "AND l.amended_at IS NOT NULL AND (SELECT count(*) FROM workout_set_logs all_logs "
                "WHERE all_logs.user_id=u.id)>=12 ORDER BY u.email LIMIT 1")).one()
        login = client.post('/auth/login',json={'email':email,'password':'Synthetic-only-safe-123!'})
        assert login.status_code == 200
        headers = {'Authorization':'Bearer '+login.json()['access_token']}
        paths = ['/workout/today', f'/workout/{occurrence}/progress', f'/workout/set/{receipt}/audit',
            '/history/calendar?start_date=2026-10-19&end_date=2026-10-25']
        for path in paths:
            response = client.get(path,headers=headers)
            assert response.status_code == 200, (path, response.status_code)
        assert client.get('/customized/options',headers=headers).status_code == 404
    assert signature(engine) == before
    return {'restored_login_today_progress_correction_history': 'passed', 'reads_changed_no_rows': True,
        'customized_disabled': True}


def prove(root):
    if any((directory/'.env').exists() for directory in (REPO, REPO/'apps/api')):
        raise ValueError('Rehearsal checkout must not contain .env')
    manifest = provision(root)
    m = json.loads(manifest.read_text())
    deadline = time.monotonic()+45
    while True:
        # The image's temporary initdb server listens only on a Unix socket.
        # Require TCP readiness so its shutdown cannot race bootstrap.
        ready = subprocess.run(['docker','exec',m['container'],'pg_isready','-q','-h','127.0.0.1',
            '-U',m['user'],'-d',m['database']],capture_output=True)
        if ready.returncode == 0:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('Owned PostgreSQL did not become ready')
        time.sleep(.25)
    bootstrap(manifest, marker_only=True)
    results = []
    for revision in ('0021_selected_workout_dates','0022_authored_load_states','0023_customized_inventory'):
        branch = new_database(manifest)
        engine = open_target(branch)
        try:
            baseline_seconds = upgrade(branch,revision,root/'alembic.log')
            seed_authored(engine,revision)
            if revision == '0023_customized_inventory':
                seed_customized(engine)
            before = signature(engine)
            retained = {k:v for k,v in before.items() if k!='alembic_version'}
            elapsed = upgrade(branch,'head',root/'alembic.log')
            assert signature(engine,list(retained)) == retained
            with engine.connect() as conn:
                assert conn.execute(text('SELECT version_num FROM alembic_version')).scalars().all() == [HEAD]
                indexes = dict(conn.execute(text(
                    "SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' "
                    "AND (indexname LIKE 'ix_c3b2b_%' OR indexname='ix_customized_load_cohort_date') ORDER BY indexname")).all())
                assert len(indexes) == 12, indexes
                assert 'WHERE (workout_occurrence_id IS NULL)' in indexes['ix_c3b2b_legacy_log_reference']
                assert '(user_id, program_id, scheduled_date)' in indexes['ix_customized_load_cohort_date']
                assert conn.execute(text("SELECT count(*) FROM pg_index WHERE NOT indisvalid OR NOT indisready")).scalar_one() == 0
            repeat = upgrade(branch,'head',root/'alembic.log')
            assert signature(engine,list(retained)) == retained
            results.append(dict(from_revision=revision,baseline_seconds=baseline_seconds,upgrade_seconds=elapsed,
                repeat_seconds=repeat,retained_tables=len(retained),retained_rows=sum(v[0] for v in retained.values()),
                exact_source_digests_unchanged=True,head=HEAD,source_read_indexes=len(indexes),indexes_all_ready_valid=True,
                premerge_customized_workflow=revision=='0023_customized_inventory',manifest=str(branch)))
        finally:
            engine.dispose()
    primary = Path(results[1]['manifest'])
    env = {**os.environ,'C3B2B_TARGET_MANIFEST':str(primary)}
    tests = ['apps/api/tests/test_customized_application.py::test_real_workflow_publish_today_log_correct_complete_history',
        'apps/api/tests/test_customized_inventory.py::test_complete_easy_exposure_gives_attainable_next_load_and_correction_rebuilds',
        'apps/api/tests/test_m4_integrated_recovery.py']
    run = subprocess.run([sys.executable,'-m','pytest',*tests,'-q'],cwd=REPO,env=env,capture_output=True,text=True)
    (root/'workflow-tests.log').write_text(run.stdout+run.stderr)
    if run.returncode:
        raise RuntimeError('Integrated workflows failed; inspect private workflow-tests.log')
    from .backup_restore import prove as backup_restore
    restore = backup_restore(primary)
    restored = list(root.glob('restore-*.json'))
    assert len(restored) == 1
    restored_engine = open_target(restored[0])
    try:
        recovery = read_restored(restored_engine)
    finally:
        restored_engine.dispose()
    result = dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        branches=results,workflow_tests=run.stdout,backup_restore=restore,recovery=recovery,production=False)
    (root/'full-chain-results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    # Stop only this checked owned container; never operate on app services.
    owned_cluster(json.loads(manifest.read_text()))
    subprocess.run(['docker','stop',m['container']],check=True,stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--fresh-disposable-root',required=True)
    prove(Path(parser.parse_args().fresh_disposable_root))
