"""Minimal logical backup/restore proof, confined to the verified owned cluster.

Never overwrite an existing database. No DROP, reset or cleanup SQL. Dumps stay
private in the explicit /tmp target directory and contain synthetic records only.
"""
import argparse,json,subprocess
from pathlib import Path
from uuid import uuid4
from sqlalchemy import text
from .target import open_target


def prove(manifest):
    path=Path(manifest);m=json.loads(path.read_text());source=open_target(path)
    info=json.loads(subprocess.check_output(['docker','inspect',m['container']],text=True))[0]
    if info['Id']!=m['container_id'] or info['Config']['Labels'].get('hypertrophy.scope')!='c3b2b97-disposable':raise ValueError('Owned cluster required')
    restore_db='c3b2b97_restore_'+uuid4().hex[:10]
    dump=path.parent/('synthetic-backup-'+uuid4().hex+'.sql')
    try:
        with dump.open('xb') as file:
            dump.chmod(0o600)
            subprocess.run(['docker','exec',m['container'],'pg_dump','-U',m['user'],'--no-owner','--no-privileges',m['database']],stdout=file,check=True)
        subprocess.run(['docker','exec',m['container'],'createdb','-U',m['user'],restore_db],check=True)
        with dump.open('rb') as file:
            subprocess.run(['docker','exec','-i',m['container'],'psql','-X','-v','ON_ERROR_STOP=1','-q','-U',m['user'],'-d',restore_db],stdin=file,stdout=subprocess.DEVNULL,check=True)
        restored=path.parent/('restore-'+uuid4().hex+'.json');restored.write_text(json.dumps({**m,'database':restore_db}));restored.chmod(0o600)
        target=open_target(restored)
        try:
            def signature(engine):
                with engine.connect() as conn:
                    tables=conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars().all()
                    # Names are from the known fresh schema, quoted defensively.
                    return {name:tuple(conn.execute(text('SELECT count(*),md5(COALESCE(string_agg(to_jsonb(t)::text,\'\' ORDER BY to_jsonb(t)::text),\'\')) FROM '+conn.dialect.identifier_preparer.quote(name)+' t')).one()) for name in tables}
            a,b=signature(source),signature(target)
            if a!=b:raise AssertionError('Backup restored rows differ')
            # Reconstruct all candidate histories, not only aggregate row counts.
            from app.customized_postgres import PostgresUnit,_Transaction
            unit=PostgresUnit(target);replayed=0
            with target.connect() as conn:
                proposals=conn.execute(text('SELECT DISTINCT subject,proposal_id FROM customized_candidate_events')).all()
            for subject,proposal in proposals:
                with unit.account(subject) as conn:
                    _Transaction(conn,subject).history(subject,proposal);replayed+=1
            result=dict(source_database=m['database'],restored_database=restore_db,tables=len(a),
                rows=sum(v[0] for v in a.values()),exact_table_digests_equal=True,replayed_proposals=replayed,
                backup_bytes=dump.stat().st_size,production=False)
            print(json.dumps(result));return result
        finally:target.dispose()
    finally:source.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',required=True);args=parser.parse_args();prove(args.manifest)
