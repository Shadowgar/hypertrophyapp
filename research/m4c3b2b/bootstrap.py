"""Rehearse additive schema only in the explicitly owned empty PG container."""
import argparse,json,secrets,subprocess
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL


def bootstrap(path, *, marker_only=False):
    path=Path(path)
    if path.is_symlink() or not path.resolve().is_relative_to(Path('/tmp')):raise ValueError('Explicit /tmp manifest required')
    m=json.loads(path.read_text())
    if not m['container'].startswith('hypertrophy-c3b2b-pg97-') or not m['database'].startswith('c3b2b97_') or m['user']!='c3b2b_owner':
        raise ValueError('Target not allowlisted')
    i=json.loads(subprocess.check_output(['docker','inspect',m['container']],text=True))[0]
    if (i['Id']!=m['container_id'] or i['Config']['Labels'].get('hypertrophy.scope')!='c3b2b97-disposable'
            or any(v['Type']!='tmpfs' for v in i['Mounts'])):raise ValueError('Owned container mismatch')
    port=i['NetworkSettings']['Ports']['5432/tcp'][0]
    if port['HostIp']!='127.0.0.1' or int(port['HostPort'])!=m['port']:raise ValueError('Loopback port mismatch')
    m.update(host='127.0.0.1',password='synthetic-c3b2b97-only',marker=secrets.token_hex(32))
    engine=create_engine(URL.create('postgresql+psycopg',username=m['user'],password=m['password'],host=m['host'],port=m['port'],database=m['database']))
    try:
        with engine.begin() as conn:
            if tuple(conn.execute(text('SELECT current_database(),current_user')).one())!=(m['database'],m['user']):raise ValueError('Target identity mismatch')
            if conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")).scalar()!=0:
                raise ValueError('Fresh EMPTY target required; existing database will not be reset')
            conn.execute(text('CREATE TABLE c3b2b_disposable_marker(marker varchar(64) NOT NULL)'))
            conn.execute(text('INSERT INTO c3b2b_disposable_marker VALUES (:m)'),dict(m=m['marker']))
        path.write_text(json.dumps(m));path.chmod(0o600)
    finally:engine.dispose()
    from .target import open_target
    verified=open_target(path)
    try:
        if marker_only:
            # Full-chain rehearsal uses actual Alembic from an empty schema,
            # rather than the selected table copies used by older probes.
            print(json.dumps(dict(database=m['database'],user=m['user'],
                marker_only=True,production=False)))
            return
        # Config already has an explicit unused ordinary import target. Create only
        # these named existing table copies, never Base.metadata.create_all/reset.
        from app.models import User,WorkoutPlan,WorkoutOccurrence,WorkoutSetLog,WorkoutLogCommand,WorkoutSessionState
        with verified.begin() as conn:
            for model in (User,WorkoutPlan,WorkoutOccurrence,WorkoutSetLog,WorkoutLogCommand,WorkoutSessionState):
                model.__table__.create(conn)
            migration=Path(__file__).with_name('001_candidate_integration.sql').read_text()
            conn.exec_driver_sql(migration)
            conn.exec_driver_sql(Path(__file__).with_name('002_source_read_indexes.sql').read_text())
        print(json.dumps(dict(database=m['database'],user=m['user'],host=m['host'],port=m['port'],
            PostgreSQL='16.13',existing_source_table_copies=6,additive_candidate_tables=5,production=False)))
    finally:verified.dispose()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True)
    p.add_argument('--marker-only',action='store_true')
    args=p.parse_args();bootstrap(args.manifest,marker_only=args.marker_only)
