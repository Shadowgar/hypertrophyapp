#!/usr/bin/env python3
"""Read-only host metadata preflight; no credential values are copied or printed."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def prepare(inspect):
    api=inspect('hypertrophy-api');web=inspect('hypertrophy-web')
    labels=api['Config']['Labels']
    assert labels['com.docker.compose.project']=='hypertrophyapp'
    assert web['Config']['Labels']['com.docker.compose.project.config_files']==labels['com.docker.compose.project.config_files']
    paths=labels['com.docker.compose.project.config_files'].split(',')
    environment=labels['com.docker.compose.project.environment_file']
    def identity(name):
        path=Path(name)
        assert path.is_absolute() and path.is_file() and not path.is_symlink()
        return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'uid':path.stat().st_uid,'mode':path.stat().st_mode & 0o777}
    env=dict(item.split('=',1) for item in api['Config']['Env'])
    assert env.get('CUSTOMIZED_ENABLED')=='true'
    web_env=dict(item.split('=',1) for item in web['Config']['Env'])
    # Only these two public/non-credential build inputs may be retained.
    build={k:web_env[k] for k in ('NEXT_PUBLIC_API_BASE_URL','SERVER_API_BASE_URL') if k in web_env}
    assert build.get('NEXT_PUBLIC_API_BASE_URL','/api')=='/api'
    assert build.get('SERVER_API_BASE_URL','http://api:8000')=='http://api:8000'
    return {'enabled':False,'automatic_rollback':False,'state_dir':str(Path.home()/'.local/state/workoutapp-release'),'compose_files':[identity(p) for p in paths],
            'environment_file':identity(environment),'web_build':build,'expected_customized_enabled':True}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    target=Path(args.output)
    assert target.parent.is_dir() and not target.parent.is_symlink() and not target.parent.stat().st_mode & 0o077
    def inspect(name):return json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    config=prepare(inspect)
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as output:json.dump(config,output,indent=2)
    print('Prepared inactive path/integrity manifest; no credentials copied and no service changed.')


if __name__=='__main__':main()
