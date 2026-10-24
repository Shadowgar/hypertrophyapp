#!/usr/bin/env python3
"""Fixed WorkoutApp release admission/host executor. No remote shell or migrations.

Install a reviewed copy operator-owned outside candidate checkouts. Host reads public
GitHub metadata over authenticated HTTPS; only Actions can issue admitted requests.
"""
from __future__ import annotations
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

REPO = 'Shadowgar/hypertrophyapp'
REPO_ID = 1170768155
BASE = 'https://api.github.com/repos/' + REPO
ENVIRONMENT = 'workoutapp-production'
REQUIRED_JOBS = frozenset(('api-tests','core-tests','web-checks','workflow-checks','documentation','container-build','CI qualification'))
CODEQL_CHECKS = frozenset(('Analyze (python)','Analyze (javascript-typescript)','Analyze (actions)'))
INPUTS = ('apps/api','apps/web','packages/core-engine','docs/rules','importers','knowledge','programs','.dockerignore')


class Refused(Exception):
    """Only fixed, non-sensitive categories cross the reporting boundary."""


def sha(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{40}',value):raise Refused('invalid_revision')
    return value


def admit(*, sha: str, current: str, protected: bool, run: dict, jobs: list, checks: list):
    globals()['sha'](sha)
    if sha != current or protected is not True:raise Refused('main_not_current_and_protected')
    if (run.get('head_sha'),run.get('head_branch'),run.get('conclusion'),run.get('path')) != (sha,'main','success','.github/workflows/ci.yml') or run.get('event') not in ('push','workflow_dispatch'):
        raise Refused('ci_origin_or_result')
    for entries,names in ((jobs,REQUIRED_JOBS),(checks,CODEQL_CHECKS)):
        successful={item.get('name') for item in entries if item.get('conclusion')=='success'}
        if not names <= successful or any(item.get('name') in names and item.get('conclusion')!='success' for item in entries):raise Refused('required_checks_incomplete')


def require_code_only(paths):
    if any(p.startswith('apps/api/alembic/') or p=='apps/api/app/models.py' for p in paths):
        raise Refused('schema_review_required')


def request(deployment):
    revision=sha(deployment.get('sha'))
    creator=deployment.get('creator',{})
    run_id=deployment.get('payload',{}).get('ci_run_id')
    if (creator.get('login'),creator.get('id'))!=('github-actions[bot]',41898282) or deployment.get('environment')!=ENVIRONMENT or deployment.get('task')!='workoutapp-release' or deployment.get('ref')!=revision or type(run_id) is not int or run_id<=0:
        raise Refused('release_request_origin')
    return revision,run_id


def api(path, *, token=None, body=None):
    # Callers supply only fixed paths or validated integers/full Git SHAs.
    headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'WorkoutApp-release'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(BASE+path,headers=headers,data=None if body is None else json.dumps(body).encode())
    try:
        with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
    except (OSError,ValueError):raise Refused('github_metadata_unavailable') from None


def qualify(revision,run_id, *, token=None):
    sha(revision)
    if type(run_id) is not int or run_id<=0:raise Refused('invalid_run')
    branch=api('/branches/main',token=token)
    run=api('/actions/runs/'+str(run_id),token=token)
    if run.get('repository',{}).get('id')!=REPO_ID or run.get('head_repository',{}).get('id')!=REPO_ID:
        raise Refused('foreign_repository')
    # At most 100 jobs; extra pages cannot silently hide a failed required job.
    jobs=api('/actions/runs/'+str(run_id)+'/jobs?per_page=100',token=token)
    if jobs.get('total_count',0)>100:raise Refused('unexpected_ci_inventory')
    checks=api('/commits/'+revision+'/check-runs?per_page=100&filter=latest',token=token)
    checks=[c for c in checks['check_runs'] if c.get('app',{}).get('id')==15368]
    admit(sha=revision,current=branch['commit']['sha'],protected=branch.get('protected'),run=run,jobs=jobs['jobs'],checks=checks)
    # Public default-setup run metadata authenticates the analysis without a
    # server token capable of reading private security findings.
    runs=api('/actions/runs?head_sha='+revision+'&per_page=100',token=token)['workflow_runs']
    if not any(r.get('path')=='dynamic/github-code-scanning/codeql' and r.get('head_sha')==revision and r.get('head_branch')=='main' and r.get('conclusion')=='success' and r.get('repository',{}).get('id')==REPO_ID for r in runs):
        raise Refused('codeql_incomplete')



def public_response(path,origin='https://hypertrophy.theroccos.us'):
    req=urllib.request.Request(origin+path,headers={'User-Agent':'WorkoutApp-release-health','Cache-Control':'no-cache'})
    return urllib.request.urlopen(req,timeout=10)


def legacy_web_revision(revision,origin='https://hypertrophy.theroccos.us'):
    """Initial pre-/version release only: match its SHA in actually served JS."""
    try:
        with public_response('/login',origin) as response:html=response.read(2_000_000).decode()
        if revision in html:return True
        paths=re.findall(r'<script[^>]+src="([^"?]+)',html)
        for path in paths[:25]:
            if not re.fullmatch(r'/_next/static/[A-Za-z0-9_./-]+[.]js',path) or '..' in path:continue
            with public_response(path,origin) as response:
                if revision.encode() in response.read(2_000_000):return True
    except (OSError,UnicodeError):pass
    return False


def atomic(path,value):
    fd,temp=tempfile.mkstemp(dir=path.parent,prefix='.release-')
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(value,stream,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def trusted_file(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_uid!=os.geteuid() or path.stat().st_mode & 0o022:raise Refused('unsafe_operator_file')
    return path


# Run inside a candidate API image; metadata only, before any application startup.
# It also works for the initial, otherwise unchanged 59d541c source.
SCHEMA_PROBE = '''
import os
from sqlalchemy import inspect,text
from app.database import engine,Base
from app import models
from alembic.config import Config
from alembic.script import ScriptDirectory
expected=ScriptDirectory.from_config(Config('alembic.ini')).get_current_head()
with engine.connect() as c:
 c.execute(text('SET TRANSACTION READ ONLY'))
 identity=tuple(c.execute(text('SELECT current_database(),current_user')).one())
 assert identity==(os.environ['DATABASE_NAME'],os.environ['DATABASE_USER'])
 assert list(c.execute(text('SELECT version_num FROM alembic_version')).scalars())==[expected]
 i=inspect(c)
 for table in Base.metadata.sorted_tables:
  assert i.has_table(table.name)
  assert {col.name for col in table.columns}<={col['name'] for col in i.get_columns(table.name)}
print('schema-compatible')
'''


class Host:
    def __init__(self,config,*,bootstrap=False):
        self.config=config;self.bootstrap=bootstrap
        profile=config.get('profile','production')
        if profile not in ('production','qualification'):raise Refused('unknown_operator_profile')
        self.project='hypertrophyapp' if profile=='production' else 'workoutapp-release-qualification'
        self.prefix='hypertrophy' if profile=='production' else 'workoutapp-release-q'
        self.origin='https://hypertrophy.theroccos.us' if profile=='production' else 'http://127.0.0.1:55320'
        self.state=Path(config['state_dir']);self.state.mkdir(mode=0o700,parents=True,exist_ok=True)
        if self.state.is_symlink() or self.state.stat().st_uid!=os.geteuid() or self.state.stat().st_mode & 0o077:raise Refused('unsafe_state_directory')
        self.compose_files=config['compose_files']
        self.verify_configuration()
        if config.get('enabled') is not True:raise Refused('operator_activation_required')
        self.log=self.state/'commands.private.log'
        self.mirror=self.state/'source.git'

    def verify_configuration(self):
        import hashlib
        for item in [*self.compose_files,self.config['environment_file']]:
            file=Path(item['path'])
            if file.is_symlink() or file.stat().st_uid!=item['uid'] or file.stat().st_mode & 0o777 != item['mode'] or hashlib.sha256(file.read_bytes()).hexdigest()!=item['sha256']:
                raise Refused('production_configuration_changed')

    def command(self,args,*,input=None,timeout=1800):
        # No shell, inherited credentials, arbitrary arguments or public stderr.
        env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(self.state),'GIT_TERMINAL_PROMPT':'0','DOCKER_CONFIG':str(self.state/'docker')}
        if args[:2]==['docker','compose']:
            env['RELEASE_ID']=self.release_revision
        result=subprocess.run(args,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=timeout)
        fd=os.open(self.log,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
        with os.fdopen(fd,'ab') as log:log.write(result.stderr)
        if result.returncode:raise Refused('local_command_failed')
        return result.stdout

    def inspect(self,kind,name):return json.loads(self.command(['docker',kind,'inspect',name]))[0]

    def running(self):
        images={};versions=set()
        for service in ('api','web'):
            container=self.inspect('container',self.prefix+'-'+service)
            if container['Config'].get('Labels',{}).get('com.docker.compose.project')!=self.project:raise Refused('wrong_compose_project')
            image=self.inspect('image',container['Image'])
            versions.add(image['Config'].get('Labels',{}).get('org.opencontainers.image.revision'))
            images[service]=container['Image']
        if len(versions)!=1:raise Refused('mixed_running_revision')
        return sha(versions.pop()),images

    def compose(self,images,revision):
        # Reference the existing secret-bearing files; never copy their contents.
        body={'services':{}}
        for service in ('api','web'):
            value={'image':images[service],'labels':{'org.opencontainers.image.revision':revision},'environment':{}}
            value['environment']['APP_VERSION' if service=='api' else 'NEXT_PUBLIC_APP_VERSION']=revision
            if service=='api':
                value['environment']['SCHEMA_MANAGEMENT_MODE']='validate'
                value['command']=['uvicorn','app.main:app','--host','0.0.0.0','--port','8000']
            body['services'][service]=value
        self.release_revision=revision
        file=self.state/'candidate.json';atomic(file,body)
        command=['docker','compose','--project-name',self.project,'--env-file',self.config['environment_file']['path']]
        for item in self.compose_files:command+=['-f',item['path']]
        return command+['-f',str(file)]

    def build(self,revision,previous):
        if not self.mirror.exists():self.command(['git','-c','credential.helper=','clone','--bare','https://github.com/'+REPO+'.git',str(self.mirror)])
        git=['git','--git-dir',str(self.mirror)]
        self.command(git+['fetch','--no-tags','origin','refs/heads/main'])
        self.command(git+['cat-file','-e',revision+'^{commit}'])
        if not self.bootstrap:
            self.command(git+['merge-base','--is-ancestor',previous,revision])
            changes=self.command(git+['diff','--name-only',previous,revision,'--','apps/api']).decode().splitlines()
            require_code_only(changes)
        with tempfile.TemporaryDirectory(dir=self.state,prefix='build-') as temp:
            context=Path(temp)
            archive=self.command(git+['archive','--format=tar',revision,'--',*INPUTS])
            import io,tarfile
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                # A tracked symlink must not smuggle a host file into a build context.
                if any(m.issym() or m.islnk() or m.name.startswith('/') or '..' in Path(m.name).parts for m in tar.getmembers()):raise Refused('unsafe_build_input')
                tar.extractall(context,filter='data')
            images={}
            for service in ('api','web'):
                tag='hypertrophyapp-'+service+':'+revision
                args=['docker','build','--label','org.opencontainers.image.revision='+revision,'--build-arg',('APP_VERSION=' if service=='api' else 'NEXT_PUBLIC_APP_VERSION=')+revision]
                if service=='web':
                    for key in ('NEXT_PUBLIC_API_BASE_URL','SERVER_API_BASE_URL'):
                        value=self.config.get('web_build',{}).get(key)
                        if value:args+=['--build-arg',key+'='+value]
                self.command(args+['-t',tag,'-f',str(context/'apps'/service/'Dockerfile'),str(context)],timeout=3600)
                image=self.inspect('image',tag)
                if image['Config'].get('Labels',{}).get('org.opencontainers.image.revision')!=revision:raise Refused('image_revision_mismatch')
                if service=='api' and image['Config'].get('Entrypoint'):raise Refused('unreviewed_api_entrypoint')
                images[service]=image['Id']
            return images

    def schema(self,compose):
        output=self.command(compose+['run','--rm','--no-deps','-T','api','python','-c',SCHEMA_PROBE],timeout=120)
        if output.strip()!=b'schema-compatible':raise Refused('schema_review_required')

    def ready(self,revision,*,allow_legacy=False):
        for _ in range(90):
            try:
                versions=[]
                for path in ('/api/health','/version'):
                    with public_response(path,self.origin) as response:
                        versions.append(json.load(response)['version'])
                if versions==[revision,revision]:return
            except (OSError,ValueError,KeyError):
                if allow_legacy and legacy_web_revision(revision,self.origin):
                    try:
                        with public_response('/api/health',self.origin) as response:
                            if json.load(response).get('version')==revision:return
                    except (OSError,ValueError):pass
            time.sleep(2)
        raise Refused('public_version_probe_failed')

    def deploy(self,revision,run_id):
        previous,old=self.running()
        if previous==revision:return
        qualify(revision,run_id)
        images=self.build(revision,previous)
        candidate=self.compose(images,revision)
        self.schema(candidate)
        qualify(revision,run_id)  # stale/main/protection race check immediately before cutover
        self.verify_configuration()
        try:
            self.command(candidate+['up','-d','--no-deps','--no-build','api','web'],timeout=240)
            self.ready(revision,allow_legacy=self.bootstrap)
            actual,ids=self.running()
            if actual!=revision or ids!=images:raise Refused('cutover_identity_mismatch')
        except (Refused,subprocess.TimeoutExpired):
            # Only code-only releases recover automatically; never undo schema or records.
            if not self.bootstrap and self.config.get('automatic_rollback') is True:
                self.verify_configuration()
                recovery=self.compose(old,previous);self.schema(recovery)
                self.command(recovery+['up','-d','--no-deps','--no-build','api','web'],timeout=240)
                self.ready(previous,allow_legacy=True)
                raise Refused('cutover_failed_approved_recovery_attempted') from None
            raise Refused('cutover_failed_operator_recovery_required') from None
        atomic(self.state/'last-success.json',{'revision':revision,'images':images,'previous_revision':previous,'previous_images':old,'ci_run_id':run_id,'completed_unix':int(time.time())})


def publish(run_id):
    token=os.environ.get('GITHUB_TOKEN')
    if not token:raise Refused('actions_identity_required')
    run=api('/actions/runs/'+str(run_id),token=token);revision=sha(run.get('head_sha'))
    # CI and CodeQL finish independently; wait without weakening either gate.
    for _ in range(60):
        try:qualify(revision,run_id,token=token);break
        except Refused as e:
            if str(e) not in ('required_checks_incomplete','codeql_incomplete'):raise
            time.sleep(10)
    else:raise Refused('qualification_timeout')
    api('/deployments',token=token,body={'ref':revision,'auto_merge':False,'required_contexts':['CI qualification'],'environment':ENVIRONMENT,'task':'workoutapp-release','production_environment':True,'payload':{'ci_run_id':run_id},'description':'Qualified main; host enforces schema and immutable pair'})
    for _ in range(180):
        try:
            versions=[]
            for path in ('/api/health','/version'):
                with public_response(path) as response:versions.append(json.load(response)['version'])
            if versions==[revision,revision]:
                print('Release confirmed: '+revision);return
        except (OSError,ValueError,KeyError):pass
        time.sleep(10)
    raise Refused('host_release_timeout_check_private_status')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('request','poll','bootstrap'))
    parser.add_argument('--run-id',type=int);parser.add_argument('--revision');parser.add_argument('--config',default=str(Path.home()/'.config/workoutapp-release/config.json'))
    args=parser.parse_args()
    if args.mode=='request':
        if not args.run_id:raise Refused('invalid_run')
        publish(args.run_id);return
    if os.geteuid()!=1000:raise Refused('operator_identity_required')
    config=json.loads(trusted_file(args.config).read_text())
    host=Host(config,bootstrap=args.mode=='bootstrap')
    with (host.state/'lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        if args.mode=='bootstrap':
            if not args.run_id:raise Refused('invalid_run')
            host.deploy(sha(args.revision),args.run_id);return
        deployments=api('/deployments?environment='+ENVIRONMENT+'&per_page=10')
        if not deployments:return
        revision,run_id=request(deployments[0])
        try:host.deploy(revision,run_id)
        except (Refused,subprocess.TimeoutExpired) as e:
            category=str(e) if isinstance(e,Refused) else 'command_timeout'
            atomic(host.state/'last-failure.json',{'revision':revision,'category':category,'failed_unix':int(time.time())})
            raise Refused(category) from None


if __name__=='__main__':
    try:main()
    except (Refused,OSError,ValueError,KeyError) as e:
        print('WorkoutApp release refused: '+(str(e) if isinstance(e,Refused) else 'private_operator_diagnostics_required'),file=sys.stderr)
        sys.exit(1)
