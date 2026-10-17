"""Apply the final additive migration to copies of populated source tables."""
import argparse,json,subprocess
from pathlib import Path
from uuid import uuid4
from sqlalchemy import text
from .target import open_target

SOURCE_TABLES=('users','workout_plans','workout_occurrences','workout_set_logs','workout_log_commands','workout_session_states','c3b2b_disposable_marker')


def prove(manifest):
    path=Path(manifest);m=json.loads(path.read_text());source=open_target(path)
    try:
        info=json.loads(subprocess.check_output(['docker','inspect',m['container']],text=True))[0]
        if info['Id']!=m['container_id'] or info['Config']['Labels'].get('hypertrophy.scope')!='c3b2b97-disposable':raise ValueError('Owned cluster required')
        name='c3b2b97_migration_'+uuid4().hex[:10];dump=path.parent/('source-only-'+uuid4().hex+'.sql')
        with dump.open('xb') as file:
            dump.chmod(0o600)
            subprocess.run(['docker','exec',m['container'],'pg_dump','-U',m['user'],'--no-owner','--no-privileges',
                *[arg for table in SOURCE_TABLES for arg in ('--table',table)],m['database']],stdout=file,check=True)
        subprocess.run(['docker','exec',m['container'],'createdb','-U',m['user'],name],check=True)
        with dump.open('rb') as file:
            subprocess.run(['docker','exec','-i',m['container'],'psql','-X','-q','-v','ON_ERROR_STOP=1','-U',m['user'],'-d',name],stdin=file,stdout=subprocess.DEVNULL,check=True)
        out=path.parent/('migration-'+uuid4().hex+'.json');out.write_text(json.dumps({**m,'database':name}));out.chmod(0o600)
        target=open_target(out)
        try:
            def digest():
                with target.connect() as conn:
                    return {table:tuple(conn.execute(text("SELECT count(*),md5(COALESCE(string_agg(to_jsonb(t)::text,'' ORDER BY to_jsonb(t)::text),'')) FROM "+table+' t')).one()) for table in SOURCE_TABLES}
            before=digest()
            with target.begin() as conn:conn.exec_driver_sql(Path(__file__).with_name('001_candidate_integration.sql').read_text())
            after=digest()
            if before!=after:raise AssertionError('Existing source records changed')
            result=dict(database=name,populated_source_tables=len(SOURCE_TABLES)-1,
                retained_source_rows=sum(v[0] for table,v in before.items() if table!='c3b2b_disposable_marker'),
                source_digests_unchanged=True,additive_candidate_tables=5,production=False)
            print(json.dumps(result));return result
        finally:target.dispose()
    finally:source.dispose()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);args=p.parse_args();prove(args.manifest)
