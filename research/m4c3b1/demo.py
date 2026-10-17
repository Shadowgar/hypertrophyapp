"""Explicit synthetic loopback demo and CLI reproduction; never app startup.

Run with --synthetic-review; CLI prints no credentials or challenge secrets.
The optional loopback server uses two fixed, visibly fake research-only tokens.
It has no production auth/config/database imports, mail, migrations or workouts.
"""
from dataclasses import replace
from pathlib import Path
import argparse
import json
import tempfile

from fastapi import Request
from fastapi.testclient import TestClient
from app.customized_lifecycle import LifecycleService
from app.customized_lifecycle_http import create_lifecycle_app
from app.customized_lifecycle_models import AccountActor
from app.customized_lifecycle_schedule import ScheduleSnapshot
from research.m4c3a.fixtures import demo_context,demo_request,demo_server
from .store import DisposableProposalStore


class SyntheticSchedule:
    def resolve(self,subject,timezone):
        return ScheduleSnapshot(subject=subject,timezone=timezone,revision="synthetic-placement-1",context=demo_context(),
            occurrences=(),complete=False,source_kind="synthetic",source_reference="disposable-demo-not-#83")


def proposed_request():
    data=demo_request(short=True).model_dump(mode="json")
    for key in ("consent","consent_reference","omissions"):data.pop(key,None)
    return data


def demo_app(root,*,origin):
    server=replace(demo_server(),allowed_subjects=("alice","bob"))
    store=DisposableProposalStore.create(Path(root)/"proposals.sqlite",disposable_root=root)
    service=LifecycleService(server=server,store=store,schedule=SyntheticSchedule(),clock=lambda:demo_context().planning_instant,
        comparison_pairs=(("shorter-current","longer-current"),))
    def synthetic_account(request: Request):
        token=request.headers.get("authorization","")
        subject={"Bearer synthetic-alice-test-only":"alice","Bearer synthetic-bob-test-only":"bob"}.get(token)
        return AccountActor(subject,"synthetic-session-"+subject,("customized:preview","customized:proposal")) if subject else None
    return create_lifecycle_app(service=service,account_dependency=synthetic_account,trusted_origin=origin,
        initial_request=proposed_request())


def reproduce(app):
    client=TestClient(app)
    headers={"Authorization":"Bearer synthetic-alice-test-only","Origin":"http://testserver"}
    def command(path,data,key):
        response=client.post(path,json=data,headers={**headers,"Idempotency-Key":key})
        return response.status_code,response.json()
    _,p=command('/customized/proposals',proposed_request(),'preview')
    prefix='/customized/proposals/'+p['proposal_id']
    _,c=command(prefix+'/challenge',dict(expected_revision=p['revision'],snapshot_hash=p['snapshot_hash']),'challenge')
    accept=dict(expected_revision=c['revision'],snapshot_hash=c['snapshot_hash'],challenge=c['challenge'],terms_hash=c['terms_hash'],
        acknowledgements=c['required_acknowledgements'],mode='customized',agree=True)
    _,a=command(prefix+'/accept',accept,'accept')
    _,b=command(prefix+'/authorization',dict(expected_revision=a['revision']),'authorization')
    revision=proposed_request();revision.update(bundle_id='longer-current',cap_minutes=90)
    _,r=command(prefix+'/revisions',dict(expected_revision=b['revision'],request=revision),'revision')
    stale,conflict=command(prefix+'/decline',dict(expected_revision=a['revision']),'stale')
    _,d=command(prefix+'/decline',dict(expected_revision=r['revision']),'decline')
    foreign=client.get(prefix,headers={'Authorization':'Bearer synthetic-bob-test-only'})
    retry_code,retry=command(prefix+'/accept',accept,'accept')
    current=client.get(prefix,headers=headers).json()
    history=client.get(prefix+'/history',headers=headers).json()
    print(json.dumps(dict(proposal_id=p['proposal_id'],flow=[p['state'],a['state'],b['state'],r['state'],d['state']],
        plan_versions=[p['plan_version'],r['plan_version']],weekly_sets=33,maximum_minutes=[57.5,59,57.5],
        exact_acknowledgements=len(c['required_acknowledgements']),removed_sets=sum(x['removed_sets'] for x in p['snapshot']['workload_changes']),
        stale=dict(http=stale,status=conflict['status']),foreign_account_http=foreign.status_code,
        retry_historical_state=retry['state'],current_state=current['state'],stored_events=len(history),
        no_workout_writer=True,can_activate=False,blockers=b['blocking_reasons']),indent=2))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--synthetic-review',action='store_true')
    parser.add_argument('--serve',action='store_true')
    parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args()
    if not args.synthetic_review:parser.error('Explicit --synthetic-review required')
    with tempfile.TemporaryDirectory(prefix='hypertrophy-c3b1-demo-') as root:
        if args.serve:
            import uvicorn
            app=demo_app(root,origin=f'http://127.0.0.1:{args.port}')
            uvicorn.run(app,host='127.0.0.1',port=args.port,access_log=False,log_level='warning')
        else:reproduce(demo_app(root,origin='http://testserver'))


if __name__=='__main__':main()
