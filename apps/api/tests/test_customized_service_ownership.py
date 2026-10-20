from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.customized_staging_http import create_staging_app
from app.customized_lifecycle import LifecycleService
from app.customized_lifecycle_models import LifecycleError
from research.m4c3a.fixtures import demo_server


def test_factory_cannot_overwrite_a_shared_services_authority():
    def owner(actor):raise LifecycleError('owner_denied',403)
    def stranger(actor):raise LifecycleError('stranger_denied',403)
    service=LifecycleService(server=demo_server(),store=None,schedule=None,clock=None,authorize_actor=owner)
    with pytest.raises(ValueError,match='authoriz'):
        create_staging_app(service=service,access_gate=SimpleNamespace(authorize=stranger))
    assert service.authorize_actor is owner
    with pytest.raises(AttributeError):service.authorize_actor=stranger


def test_factory_deny_by_default_and_distinct_host_services():
    def first(actor):raise LifecycleError('first_denied',403)
    def second(actor):raise LifecycleError('second_denied',403)
    a=LifecycleService(server=demo_server(),store=None,schedule=None,clock=None,authorize_actor=first)
    b=LifecycleService(server=demo_server(),store=None,schedule=None,clock=None,authorize_actor=second)
    create_staging_app(service=a,access_gate=SimpleNamespace(authorize=first))
    create_staging_app(service=b,access_gate=SimpleNamespace(authorize=second))
    assert a.authorize_actor is first and b.authorize_actor is second
    client=TestClient(create_staging_app(service=a))
    assert client.get('/customized/proposals/unknown',headers={'Authorization':'Bearer arbitrary'}).status_code==403
