"""Guarded lifecycle integration, with real app bearer auth + disposable lookup."""
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient

from test_customized_lifecycle import harness, request


def factory(harness):
    from app.customized_lifecycle_http import create_lifecycle_app
    s,a,b,*_=harness
    def account_dependency():
        return a
    app=create_lifecycle_app(service=s,account_dependency=account_dependency,trusted_origin="http://testserver")
    return TestClient(app)


def post(client,path,data,key="request-1",**kwargs):
    headers={"Authorization":"Bearer synthetic-test-only", "Origin":"http://testserver","Idempotency-Key":key}
    headers.update(kwargs.pop("headers",{}))
    return client.post(path,json=data,headers=headers,**kwargs)


def test_factory_is_separate_and_disabled_before_any_auth_or_storage():
    from app import customized_preview_http
    import importlib.util
    assert importlib.util.find_spec("app.customized_lifecycle_http"), "Missing account-owned flow factory"
    from app.customized_lifecycle_http import create_lifecycle_app
    client=TestClient(create_lifecycle_app())
    response=client.post("/customized/proposals",json=request())
    assert response.status_code==404
    assert "no-store" in response.headers["cache-control"]


def test_http_proposal_challenge_accept_block_revision_decline(harness):
    client=factory(harness)
    p=post(client,"/customized/proposals",request()).json()
    assert p["state"]=="review_required"
    id=p["proposal_id"]
    c=post(client,f"/customized/proposals/{id}/challenge",dict(expected_revision=p["revision"],snapshot_hash=p["snapshot_hash"]),"challenge").json()
    data=dict(expected_revision=c["revision"],snapshot_hash=c["snapshot_hash"],challenge=c["challenge"],
        terms_hash=c["terms_hash"],acknowledgements=c["required_acknowledgements"],mode="customized",agree=True)
    response=post(client,f"/customized/proposals/{id}/accept",data,"accept")
    assert response.status_code==200
    accepted=response.json();assert accepted["state"]=="accepted_candidate"
    blocked=post(client,f"/customized/proposals/{id}/authorization",{"expected_revision":accepted["revision"]},"authorization").json()
    assert blocked["state"]=="activation_blocked" and blocked["can_activate"] is False
    page=client.get(f"/customized/proposals/{id}/render",headers={"Authorization":"Bearer synthetic-test-only"})
    assert page.status_code==200
    assert '33' in page.text and 'activation_blocked' in page.text
    revised=post(client,f"/customized/proposals/{id}/revisions",{"expected_revision":blocked["revision"],"request":request(short=False,cap=90)},"revise").json()
    assert revised["plan_version"]==2 and revised["consent_receipt"] is None
    stale=post(client,f"/customized/proposals/{id}/decline",{"expected_revision":accepted["revision"]},"stale")
    assert stale.status_code==409 and stale.json()["status"]=="stale_revision"
    declined=post(client,f"/customized/proposals/{id}/decline",{"expected_revision":revised["revision"]},"decline").json()
    assert declined["state"]=="declined"
    for path in ("/activate","/start","/workout/log-set"):
        assert post(client,path,{},path).status_code==404


@pytest.mark.parametrize("headers,want",[({"Authorization":""},401),({"Origin":"https://evil.example"},403),({"Sec-Fetch-Site":"cross-site"},403)])
def test_cookie_or_cross_origin_cannot_authorize_mutation(harness,headers,want):
    response=post(factory(harness),"/customized/proposals",request(),headers=headers)
    assert response.status_code==want


def test_validation_and_size_errors_do_not_echo_private_input(harness):
    client=factory(harness)
    response=post(client,"/customized/proposals",{**request(),"owner_id":"private-secret-should-not-echo"})
    assert response.status_code==422
    assert "private-secret" not in response.text
    response=post(client,"/customized/proposals",{**request(),"unknown":"x"*17000})
    assert response.status_code==413
    response=client.post("/customized/proposals",content='{"secret":"never-echo"',headers={"Authorization":"Bearer synthetic-test-only"})
    assert response.status_code==422 and "never-echo" not in response.text


def test_real_app_jwt_current_user_dependency_maps_account_without_production_db(harness):
    from app.customized_lifecycle_http import create_lifecycle_app, existing_account_dependency
    from app.deps import get_db
    from app.models import User
    from app.security import create_access_token
    # No connection or DDL: execute the actual SQLAlchemy ownership predicate on
    # a synthetic account lookup via a disposable lookup, retaining real JWT auth.
    class Lookup:
        def __init__(self,ids): self.ids=ids
        def filter(self,predicate):
            self.subject=predicate.right.value
            return self
        def first(self): return User(id=self.subject) if self.subject in self.ids else None
    def disposable_lookup():
        yield SimpleNamespace(query=lambda model: Lookup({"alice","bob"}))
    s,*_=harness
    app=create_lifecycle_app(service=s,account_dependency=existing_account_dependency(),trusted_origin="http://testserver")
    app.dependency_overrides[get_db]=disposable_lookup
    client=TestClient(app)
    alice=create_access_token("alice");bob=create_access_token("bob")
    p=post(client,"/customized/proposals",request(),headers={"Authorization":f"Bearer {alice}"}).json()
    assert p["subject"]=="alice"
    for id in (p["proposal_id"],"unknown"):
        response=client.get(f"/customized/proposals/{id}",headers={"Authorization":f"Bearer {bob}"})
        assert response.status_code==404 and response.json()=={"status":"not_found"}
    assert post(client,"/customized/proposals",request(),headers={"Authorization":"Bearer forged.invalid.token"}).status_code==401
    assert post(client,"/customized/proposals",request(),headers={"Authorization":f"Bearer {create_access_token('absent')}"}).status_code==401
    # Test adapter does not import main/startup or open the unused configured DB.
    import sys,os
    assert "app.main" not in sys.modules
    assert not os.path.exists('/tmp/hypertrophy-c3b1-unused.sqlite')
