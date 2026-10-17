"""Explicit resource-bounded fresh fixture; never reuses or resets a target."""
import argparse,json,subprocess
from pathlib import Path
from uuid import uuid4

IMAGE='sha256:0f7a666480d0a8efb29f3c7876fc612147be6a37f071b74a3131248d3818ae3e'


def provision(root):
    root=Path(root)
    if root.is_symlink() or root.exists() or root.parent.resolve()!=Path('/tmp'):raise ValueError('New direct /tmp directory required')
    root.mkdir(mode=0o700);name='hypertrophy-c3b2b-pg97-'+uuid4().hex[:10];database='c3b2b97_'+uuid4().hex[:10]
    id=subprocess.check_output(['docker','run','-d','--rm','--name',name,'--label','hypertrophy.scope=c3b2b97-disposable',
        '--memory','256m','--cpus','0.5','--pids-limit','128','--publish','127.0.0.1::5432',
        '--tmpfs','/var/lib/postgresql/data:rw,size=192m,mode=0700','--env','POSTGRES_USER=c3b2b_owner',
        '--env','POSTGRES_DB='+database,'--env','POSTGRES_PASSWORD=synthetic-c3b2b97-only',
        '--env','POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256',IMAGE,'postgres','-c','max_connections=20',
        '-c','shared_buffers=16MB','-c','fsync=on'],text=True).strip()
    i=json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0];port=i['NetworkSettings']['Ports']['5432/tcp'][0]
    if i['Id']!=id or port['HostIp']!='127.0.0.1':raise ValueError('Container ownership/binding mismatch')
    path=root/'target.json';path.write_text(json.dumps(dict(root=str(root),container=name,container_id=id,database=database,
        user='c3b2b_owner',image=IMAGE,port=int(port['HostPort']))));path.chmod(0o600)
    print(str(path));return path


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fresh-disposable-root',required=True)
    args=parser.parse_args();provision(args.fresh_disposable_root)
