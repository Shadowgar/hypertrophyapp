"""Explicit loopback/in-process integration demo, no production app/startup.

The shell's credential input is development-only. Credentials can be written to
an explicitly requested, exclusively created /tmp file for browser tooling; no
HTTP credential endpoint exists and CLI output contains no tokens or keys.
"""
import argparse
from pathlib import Path
import tempfile
import json


def reproduce(demo):
    from fastapi.testclient import TestClient
    from research.m4c3b1.demo import proposed_request
    client=TestClient(demo.app)
    def command(path,data,key,subject='alice'):
        return client.post(path,json=data,headers={'Authorization':'Bearer '+demo.tokens[subject],
            'Origin':'http://testserver','Idempotency-Key':key})
    p=command('/customized/proposals',proposed_request(),'preview').json()
    prefix='/customized/proposals/'+p['proposal_id']
    c=command(prefix+'/challenge',dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']),'summary').json()
    payload=dict(protocol=c['consent_protocol'],expected_revision=c['revision'],snapshot_hash=c['snapshot_hash'],
        challenge=c['challenge'],terms_hash=c['terms_hash'],summary_hash=c['summary_hash'],mode='customized',agree=True)
    a=command(prefix+'/accept',payload,'accept').json()
    b=command(prefix+'/authorization',dict(expected_revision=a['revision']),'authorization').json()
    r=command(prefix+'/revisions',dict(expected_revision=b['revision'],request={**proposed_request(),'bundle_id':'longer-current','cap_minutes':90}),'revision').json()
    stale=command(prefix+'/decline',dict(expected_revision=a['revision']),'stale')
    d=command(prefix+'/decline',dict(expected_revision=r['revision']),'decline').json()
    foreign=client.get(prefix,headers={'Authorization':'Bearer '+demo.tokens['bob']})
    demo.access.revoke('alice')
    revoked=command(prefix+'/accept',payload,'accept')
    print(json.dumps(dict(protocol=c['consent_protocol'],flow=[p['state'],a['state'],b['state'],r['state'],d['state']],
        plan_versions=[p['plan_version'],r['plan_version']],consumer_acknowledgements=1,
        retained_audit_terms=len(a['consent_receipt']['acknowledgements']),specific_set_changes=len(c['summary']['workload_changes']),
        unapproved_range_conflicts=len(c['summary']['proposed_range_conflicts']),
        short_upper_minutes=c['summary']['candidate']['upper_minutes'],long_upper_minutes=c['summary']['reference']['upper_minutes'],
        stale_http=stale.status_code,foreign_http=foreign.status_code,revoked_retry_http=revoked.status_code,
        actual_disposable_users=demo.accounts.private_row_count(),can_activate=False),indent=2))


def main():
    p=argparse.ArgumentParser();p.add_argument('--synthetic-review',action='store_true');p.add_argument('--serve',action='store_true')
    p.add_argument('--port',type=int,default=8767);p.add_argument('--credentials-file',type=Path)
    args=p.parse_args()
    if not args.synthetic_review:p.error('Explicit --synthetic-review required')
    if args.credentials_file and (not args.serve or not args.credentials_file.parent.resolve().is_relative_to(Path('/tmp')) or args.credentials_file.is_symlink()):
        p.error('Browser credentials require an explicitly requested new /tmp file and --serve')
    # Verify ordinary import target before importing any app settings/models.
    import os
    url=os.environ.get('DATABASE_URL','');test_url=os.environ.get('TEST_DATABASE_URL','')
    if url!=test_url or not url.startswith('sqlite:////tmp/') or Path(url.removeprefix('sqlite:///')).exists():
        p.error('Explicit identical unused /tmp DATABASE_URL/TEST_DATABASE_URL required')
    with tempfile.TemporaryDirectory(prefix='hypertrophy-c3b2a-demo-') as root:
        from .fixtures import build_staging_demo
        demo=build_staging_demo(root,origin=f'http://127.0.0.1:{args.port}' if args.serve else 'http://testserver')
        try:
            if args.serve:
                if args.credentials_file:
                    fd=os.open(args.credentials_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                    with os.fdopen(fd,'w') as file:json.dump(demo.tokens,file)
                import uvicorn
                uvicorn.run(demo.app,host='127.0.0.1',port=args.port,access_log=False,log_level='warning')
            else:reproduce(demo)
        finally:demo.accounts.close()


if __name__=='__main__':main()
