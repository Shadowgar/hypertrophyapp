#!/usr/bin/env python3
"""Private logical snapshot + isolated restore. Never mutates the source database.

Explicit operator command only; never called by automatic releases. Holds a
read-only exported snapshot through pg_dump and compares all restored rows/schema.
No raw records, passwords, dump bytes or signature values reach console output.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time

PRODUCTION_DB='hypertrophy'
PRODUCTION_USER='hypertrophy'
META_SQL="""SELECT json_build_object(
 'columns',(SELECT json_agg(v ORDER BY table_name,ordinal_position) FROM
 (SELECT table_name,column_name,ordinal_position,data_type,is_nullable,column_default,character_maximum_length,numeric_precision,numeric_scale FROM information_schema.columns WHERE table_schema='public') v),
 'constraints',(SELECT json_agg(v ORDER BY table_name,name) FROM
 (SELECT c.conrelid::regclass::text table_name,c.conname name,pg_get_constraintdef(c.oid) definition FROM pg_constraint c JOIN pg_class r ON r.oid=c.conrelid JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname='public') v),
 'indexes',(SELECT json_agg(v ORDER BY table_name,name) FROM
 (SELECT t.relname table_name,i.relname name,pg_get_indexdef(i.oid) definition,x.indisvalid valid,x.indisready ready FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_class t ON t.oid=x.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='public') v),
 'owners',(SELECT json_agg(v ORDER BY table_name) FROM (SELECT tablename table_name,tableowner FROM pg_tables WHERE schemaname='public') v),
 'grants',(SELECT json_agg(v ORDER BY table_name,grantee,privilege_type) FROM (SELECT table_name,grantee,privilege_type,is_grantable FROM information_schema.table_privileges WHERE table_schema='public') v)
)::text"""
SOURCE_PROGRAM='''
import hashlib,json,sys
from sqlalchemy import text
from sqlalchemy.engine import make_url
from app.config import settings
u=make_url(settings.resolved_database_url)
assert (u.host,u.port,u.database,u.username)==('postgres',5432,'hypertrophy','hypertrophy')
from app.database import engine
with engine.connect().execution_options(isolation_level='REPEATABLE READ') as c:
 c.execute(text('SET TRANSACTION READ ONLY'))
 assert tuple(c.execute(text('SELECT current_database(),current_user')).one())==('hypertrophy','hypertrophy')
 version=list(c.execute(text('SELECT version_num FROM alembic_version')).scalars())
 assert version==['0024_merge_authored_customized']
 snapshot=c.execute(text('SELECT pg_export_snapshot()')).scalar()
 print(json.dumps({'snapshot':snapshot,'revision':version[0]}),flush=True)
 names=list(c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars())
 signatures={}
 for name in names:
  assert name.replace('_','').isalnum()
  digest=hashlib.sha256();count=0
  for row in c.execute(text('SELECT row_to_json(t)::text FROM "'+name+'" t ORDER BY row_to_json(t)::text')):
   digest.update(row[0].encode()+b'\\n');count+=1
  signatures[name]={'count':count,'digest':digest.hexdigest()}
 metadata=json.loads(c.execute(text(META_SQL)).scalar())
 print(json.dumps({'tables':signatures,'schema':metadata}),flush=True)
 assert sys.stdin.readline().strip()=='dump-complete'
'''


def run(args,*,input=None,env=None):
    result=subprocess.run(args,input=input,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode:raise RuntimeError('Private preflight command failed; output withheld')
    return result.stdout


def start_restore_container(container,image):
    # No extra retained host password file or literal secret in process arguments.
    # Docker still holds its normal container environment, visible to its operator.
    # Preserve the same Docker endpoint/context as all preceding identity checks.
    environment={**os.environ,'POSTGRES_DB':'workoutapp_release_restore',
                 'POSTGRES_USER':PRODUCTION_USER,'POSTGRES_PASSWORD':secrets.token_urlsafe(40)}
    run(['docker','run','-d','--name',container,'--network','none',
         '--tmpfs','/var/lib/postgresql/data:rw,noexec,nosuid,size=1g',
         '--env','POSTGRES_DB','--env','POSTGRES_USER','--env','POSTGRES_PASSWORD',image],env=environment)


def target(container):
    if not re.fullmatch(r'workoutapp-release-restore-[0-9]+',container):raise RuntimeError('Restore target name rejected')
    item=json.loads(run(['docker','inspect',container]))[0]
    if item['Mounts'] or item['HostConfig']['NetworkMode']!='none' or '/var/lib/postgresql/data' not in item['HostConfig'].get('Tmpfs',{}):raise RuntimeError('Restore isolation rejected')
    identity=run(['docker','exec',container,'psql','-X','-At','-U',PRODUCTION_USER,'-d','workoutapp_release_restore','-c','SELECT current_database(),current_user']).decode().strip()
    if identity!='workoutapp_release_restore|hypertrophy':raise RuntimeError('Restore database identity rejected')


def restored_signature(container):
    target(container)
    prefix=['docker','exec',container,'psql','-X','-v','ON_ERROR_STOP=1','-At','-U',PRODUCTION_USER,'-d','workoutapp_release_restore','-c']
    names=run(prefix+["SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"]).decode().splitlines()
    result={}
    for name in names:
        if not re.fullmatch('[a-z0-9_]+',name):raise RuntimeError('Unexpected table identifier')
        rows=run(prefix+['SELECT row_to_json(t)::text FROM "'+name+'" t ORDER BY row_to_json(t)::text'])
        result[name]={'count':rows.count(b'\n'),'digest':hashlib.sha256(rows).hexdigest()}
    return {'tables':result,'schema':json.loads(run(prefix+[META_SQL]))}


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True);p.add_argument('--restore-container',required=True);args=p.parse_args()
    root=Path(args.directory)
    if not root.is_dir() or root.is_symlink() or root.stat().st_uid!=os.getuid() or root.stat().st_mode & 0o077:raise RuntimeError('Owned private destination required')
    if any(root.iterdir()):raise RuntimeError('New empty private destination required')
    if not re.fullmatch(r'workoutapp-release-restore-[0-9]+',args.restore_container):raise RuntimeError('Restore target name rejected')
    prod=json.loads(run(['docker','inspect','hypertrophy-postgres']))[0]
    if prod['Config']['Labels']['com.docker.compose.project']!='hypertrophyapp' or not any(m.get('Name')=='hypertrophyapp_postgres_data' for m in prod['Mounts']):raise RuntimeError('Unexpected production source')
    image=prod['Image']
    # The source engine independently validates endpoint/database/user before use.
    program='META_SQL='+repr(META_SQL)+'\n'+SOURCE_PROGRAM
    source=subprocess.Popen(['docker','exec','-i','hypertrophy-api','python','-u','-c',program],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        first=source.stdout.readline()
        if not first:raise RuntimeError('Source snapshot verification failed')
        control=json.loads(first);snapshot=control['snapshot']
        if not re.fullmatch('[0-9A-Fa-f-]+',snapshot):raise RuntimeError('Snapshot identifier rejected')
        file=root/'production.dump'
        fd=os.open(file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as output:
            dump=subprocess.run(['docker','exec','hypertrophy-postgres','sh','-ec','exec pg_dump --format=custom --snapshot="$1" -U "$POSTGRES_USER" "$POSTGRES_DB"','--',snapshot],stdout=output,stderr=subprocess.PIPE)
        if dump.returncode or not file.stat().st_size:raise RuntimeError('Private dump failed')
        before=json.loads(source.stdout.readline())
        source.stdin.write('dump-complete\n');source.stdin.flush();source.stdin.close()
        if source.wait(timeout=30):raise RuntimeError('Source snapshot did not close cleanly')
    finally:
        if source.poll() is None:source.kill();source.wait()
    (root/'source-signature.private.json').write_text(json.dumps(before));(root/'source-signature.private.json').chmod(0o600)
    start_restore_container(args.restore_container,image)
    for _ in range(120):
        try:target(args.restore_container);break
        except RuntimeError:time.sleep(.5)
    else:raise RuntimeError('Restore readiness failed')
    prefix=['docker','exec',args.restore_container,'psql','-X','-At','-U',PRODUCTION_USER,'-d','workoutapp_release_restore','-c']
    if run(prefix+["SELECT count(*) FROM pg_tables WHERE schemaname='public'"]).strip()!=b'0':raise RuntimeError('Restore target not empty')
    target(args.restore_container)
    with file.open('rb') as dump:
        result=subprocess.run(['docker','exec','-i',args.restore_container,'pg_restore','--exit-on-error','-U',PRODUCTION_USER,'-d','workoutapp_release_restore'],stdin=dump,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode:raise RuntimeError('Isolated restore failed; output withheld')
    after=restored_signature(args.restore_container)
    if after!=before:raise RuntimeError('Restored snapshot differs; private signatures retained')
    (root/'restore-signature.private.json').write_text(json.dumps(after));(root/'restore-signature.private.json').chmod(0o600)
    report={'source_database':PRODUCTION_DB,'source_user':PRODUCTION_USER,'source_revision':control['revision'],
            'backup_bytes':file.stat().st_size,'backup_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
            'restore_container':args.restore_container,'restore_database':'workoutapp_release_restore',
            'tables':len(before['tables']),'rows':sum(t['count'] for t in before['tables'].values()),
            'all_table_content_counts_and_digests_equal':True,'columns_constraints_indexes_owners_grants_equal':True,
            'source_read_only_exported_snapshot':True,'restore_network_none_no_mounts_tmpfs':True}
    path=root/'result.private.json';path.write_text(json.dumps(report,indent=2));path.chmod(0o600)
    print('Private production snapshot restored in isolation; all table/row/schema signatures match. No source mutation.')


if __name__=='__main__':
    try:main()
    except Exception:
        print('Private backup preflight failed; no raw data or credentials published.',file=sys.stderr);sys.exit(1)
