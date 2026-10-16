"""Isolated preview app: no production main/auth/database or live fixtures."""
from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from app.customized_preview_http import create_preview_app
from app.customized_preview_models import PreviewRequest, PreviewPrincipal, PreviewServer
from app.customized_preview_service import preview_program
from app.customized_preview_view import render_preview
from research.m4c3a.fixtures import demo_request, demo_server, demo_principal, demo_context


def call(request=None, server=None, principal=None, context=None):
    return preview_program(request or demo_request(), server=server or demo_server(),
        principal=principal or demo_principal(), context=demo_context() if context is None else context)


def client(server=None, principal=None, authenticate=True):
    async def auth(request):
        return (principal or demo_principal()) if request.headers.get("authorization")=="Bearer synthetic-test-session" else None
    return TestClient(create_preview_app(server=server or demo_server(), authenticate=auth if authenticate else None,
        context_port=lambda timezone: demo_context()))


HEADERS={"Authorization":"Bearer synthetic-test-session"}


def test_disabled_factory_and_production_fail_closed_without_a_principal_or_policy_default():
    with TestClient(create_preview_app()) as c:
        response=c.post("/customized/preview",json=demo_request().model_dump(mode="json"))
        assert response.status_code==404
    for server in (replace(demo_server(),enabled=False), replace(demo_server(),environment="production"),
                   replace(demo_server(),synthetic_enabled=False)):
        with client(server) as c:
            response=c.post("/customized/preview",json=demo_request().model_dump(mode="json"),headers=HEADERS)
            assert response.status_code in (404,409)
            assert not response.json().get("sessions")


def test_authentication_and_server_allowlist_cannot_be_claimed_in_request():
    body=demo_request().model_dump(mode="json")
    for c in (client(),client(authenticate=False)):
        with c:
            assert c.post("/customized/preview",json=body).status_code==401
    with client(principal=PreviewPrincipal("another-user",("customized:preview",))) as c:
        assert c.post("/customized/preview",json=body,headers=HEADERS).status_code==403
    with client(principal=PreviewPrincipal("synthetic-reviewer",())) as c:
        assert c.post("/customized/preview",json=body,headers=HEADERS).status_code==403


def test_synthetic_short_long_preview_has_real_workout_and_no_optimization_or_activation_claim():
    long=call(); short=call(demo_request(short=True,accept_tradeoffs=True))
    assert long.status=="infeasible" and long.sessions[1].maximum_minutes==70.5
    assert short.status=="policy_not_approved" and short.coverage_status=="accepted_limited_candidate"
    assert [s.maximum_minutes for s in short.sessions]==[57.5,59,57.5]
    assert all(len(s.exercises)==7 for s in short.sessions)
    assert short.audience=="synthetic_review_preview" and not short.can_activate and not short.prescriptive
    assert short.effectiveness=="not_established" and "nominal" in short.coverage_meaning.lower()
    assert "fixed_design_not_personalized_optimization" in short.limitations
    assert all(e.observed_effort==() for s in short.sessions for e in s.exercises)
    assert all(e.working_load is None for s in short.sessions for e in s.exercises)
    assert call(demo_request(short=True)).coverage_status=="incomplete"


def test_consented_explicit_inputs_are_normalized_through_existing_profile_without_using_numeric_defaults():
    result=call(demo_request(short=True,accept_tradeoffs=True))
    assert result.trace["normalizer"]=="build_generated_training_profile"
    assert result.trace["legacy_path_family"]=="generated"
    assert result.trace["core_profile_version"]=="c1-profile-v1"
    assert "legacy.trace_only_controls" in result.trace_only_fields
    assert "legacy.recovery_modifier" in result.trace_only_fields
    assert "skill" in result.active_fields and "training_context" in result.active_fields
    assert result.sessions[0].exercises[0].target_min==1
    assert call(demo_request(short=True,accept_tradeoffs=True))==result


@pytest.mark.parametrize("field,value,reason",[("mode","authored","customized_consent_required"),
    ("mode","auto","customized_consent_required"),("mode","manual","customized_consent_required"),
    ("consent",False,"customized_consent_required"),("skill",None,"confirmed_skill_required"),
    ("training_context","unknown","training_context_required"),("selected_dates",(),"three_actual_dates_required"),
    ("population","rehabilitation","population_out_of_scope"),("goal","military","goal_not_supported"),
    ("restrictions",("unmapped_health_issue",),"restriction_not_supported")])
def test_missing_or_out_of_scope_input_has_value_free_fallback(field,value,reason):
    request=demo_request().model_copy(update={field:value})
    result=call(request)
    assert not result.sessions and reason in result.reasons
    assert result.can_activate is False


def test_missing_schedule_port_dates_timezone_and_dst_are_explicit():
    result=preview_program(demo_request(),server=demo_server(),principal=demo_principal(),context=None)
    assert not result.sessions and "schedule_context_required" in result.reasons
    assert call().sessions[-1].local_date==date(2026,11,1)
    for changes in (dict(selected_dates=(date(2026,10,27),)*3),dict(timezone="Bad/Zone"),dict(selected_dates=(date(2026,10,28),date(2026,10,29),date(2026,11,1)))):
        result=call(demo_request().model_copy(update=changes))
        assert result.status in ("invalid_input","infeasible")
        assert not result.can_activate


def test_missing_equipment_and_reduced_skill_do_not_invent_compatible_variants():
    assert call(demo_request().model_copy(update={"equipment":()})).status=="infeasible"
    result=call(demo_request().model_copy(update={"skill":"basic"}))
    assert result.status=="infeasible" and result.issues


def test_no_client_policy_reviewer_catalog_or_approval_fields_and_safe_validation_errors():
    body=demo_request().model_dump(mode="json")
    with client() as c:
        for key in ("policy","reviewer","approved","catalog","inventory","principal","environment","enabled"):
            response=c.post("/customized/preview",json={**body,key:"SECRET-SENTINEL"},headers=HEADERS)
            assert response.status_code==422
            assert "SECRET-SENTINEL" not in response.text
        response=c.post("/customized/preview",json={**body,"selected_dates":["2026-10-27T00:00:00Z"]},headers=HEADERS)
        assert response.status_code==422
        assert c.post("/customized/preview",content=b'x'*17000,headers=HEADERS).status_code==413


def test_unadmitted_approved_audience_returns_no_plan_and_no_synthetic_substitution():
    request=demo_request().model_copy(update={"audience":"approved_prescription"})
    result=call(request)
    assert result.status=="policy_not_approved" and result.sessions==()
    assert result.audience=="approved_prescription"
    assert "unknown_or_ambiguous_policy" in result.reasons
    with client() as c:
        response=c.post("/customized/preview",json=request.model_dump(mode="json"),headers=HEADERS)
        assert response.status_code==409 and response.json()["sessions"]==[]


def test_readonly_http_renders_same_preview_and_has_no_workout_or_activation_routes():
    with client() as c:
        request=demo_request(short=True,accept_tradeoffs=True).model_dump(mode="json")
        result=c.post("/customized/preview",json=request,headers=HEADERS)
        assert result.status_code==200
        html=c.post("/customized/preview/render",json=request,headers=HEADERS)
        assert html.status_code==200 and "57.5" in html.text and "59" in html.text
        assert html.headers["cache-control"]=="no-store"
        assert "frame-ancestors 'none'" in html.headers["content-security-policy"]
        assert "Start workout" not in html.text and "<button" not in html.text
        assert c.post("/customized/activate",json=request,headers=HEADERS).status_code==404
        assert c.post("/workout/log-set",json={},headers=HEADERS).status_code==404


def test_renderer_escapes_dynamic_content_and_preserves_unknown_observed_effort():
    result=call()
    text=render_preview(result.model_copy(update={"message":"<script>alert(1)</script>"}))
    assert "<script>" not in text and "&lt;script&gt;" in text
    assert "Observed effort: unknown" in text
    assert "Target effort" in text and "CANDIDATE FOR EXPERT REVIEW" in text


def test_adapter_has_no_database_or_file_mutation_during_decisions():
    code=r'''
import sys
from app.customized_preview_service import preview_program
from research.m4c3a.fixtures import demo_server,demo_request,demo_principal,demo_context
args=dict(server=demo_server(),principal=demo_principal(),context=demo_context())
request=demo_request(short=True,accept_tradeoffs=True)
first=preview_program(request,**args)
assert 'app.database' not in sys.modules and 'app.main' not in sys.modules
before=repr((request,args))
def deny(event,args):
    if event=='open':
        path,mode,flags=args
        assert str(path).startswith('/usr/share/zoneinfo/') and mode=='r' and flags & 3==0
    if event.startswith(('socket.','sqlite3.','subprocess.')) or event in {'os.remove','os.rename','os.mkdir','os.rmdir','os.system','os.truncate'}:
        raise AssertionError(event)
sys.addaudithook(deny)
assert preview_program(request,**args)==first
assert repr((request,args))==before
'''
    result=subprocess.run([sys.executable,"-c",code],env=dict(os.environ),capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr


def test_future_trusted_admission_still_cannot_create_or_activate_a_workout(monkeypatch):
    from core_engine.customized.admission import AdmissionDecision
    monkeypatch.setattr("app.customized_preview_service.admit_policy",lambda *args,**kwargs:
        AdmissionDecision("admitted_for_future_use","future-test","a"*64,("trusted_future_admission_only_activation_disabled",)))
    result=call(demo_request().model_copy(update={"audience":"approved_prescription"}))
    assert result.status=="activation_disabled" and result.sessions==()
    assert result.can_activate is False and result.prescriptive is False


def test_explicit_input_sensitivity_without_silent_status_or_cap_substitution():
    baseline=call()
    roomy=call(demo_request().model_copy(update={"cap_minutes":75}))
    assert baseline.status=="infeasible" and roomy.status=="policy_not_approved"
    assert baseline.trace["input_hash"]!=roomy.trace["input_hash"]
    returning=call(demo_request().model_copy(update={"training_context":"returning"}))
    assert not returning.sessions and returning.status=="unsupported_profile"
    assert "policy_profile_not_supported" in returning.reasons


def test_server_cannot_mislabel_local_approval_claim_as_synthetic_review():
    from core_engine.customized.models import PolicyApproval
    server=demo_server(); bundle=server.bundles[0]
    science=replace(bundle.standard.science,status="approved",approval=PolicyApproval("a"*64,"claimed-coach","claimed-owner"))
    bundle=replace(bundle,standard=replace(bundle.standard,science=science))
    result=call(server=replace(server,bundles=(bundle,)))
    assert not result.sessions and "review_bundle_not_provisional" in result.reasons


def test_consumer_candidate_label_is_server_owned_not_guessed_from_bundle_id():
    server=demo_server()
    bundle=replace(server.bundles[0],bundle_id="opaque-id",display_name="Explicit proposal label")
    result=call(demo_request().model_copy(update={"bundle_id":"opaque-id"}),server=replace(server,bundles=(bundle,)))
    assert result.candidate_name=="Explicit proposal label"
    assert '<h2>Explicit proposal label</h2>' in render_preview(result)


def test_absent_restrictions_are_unknown_while_explicit_empty_is_a_reported_clear():
    body=demo_request().model_dump(mode="json")
    with client() as c:
        for missing in ({k:v for k,v in body.items() if k!="restrictions"},{**body,"restrictions":None}):
            result=c.post("/customized/preview",json=missing,headers=HEADERS)
            assert result.status_code==409 and result.json()["status"]=="needs_information"
            assert result.json()["sessions"]==[] and "movement_restrictions_required" in result.json()["reasons"]
        result=c.post("/customized/preview",json={**body,"restrictions":[]},headers=HEADERS)
        assert result.status_code==200 and len(result.json()["sessions"])==3


@pytest.mark.parametrize("condition,expected",[("pain","pain_reported"),("stale","exposure_stale_or_future"),
    ("unsupported","load_semantics_or_variant_unsupported")])
def test_renderer_preserves_specific_calibration_abstention(condition,expected):
    from research.m4c2.examples import synthetic_exposure
    server=demo_server(); bundle=server.bundles[0]; exp=synthetic_exposure()
    if condition=="pain": exp=replace(exp,records=tuple(replace(r,pain=True) for r in exp.records))
    if condition=="stale": exp=replace(exp,performed_on=date(2026,9,1))
    result=call(server=replace(server,bundles=(replace(bundle,exposures=(exp,)),)))
    assert any(expected in e.calibration_reasons for s in result.sessions for e in s.exercises)
    assert expected in render_preview(result)


def test_missing_optional_controls_do_not_claim_explicit_user_origin():
    body=demo_request().model_dump(mode="json")
    missing=PreviewRequest.model_validate({k:v for k,v in body.items() if k!="excluded_variants"})
    explicit=PreviewRequest.model_validate({**body,"excluded_variants":[]})
    absent_result,explicit_result=call(missing),call(explicit)
    assert "excluded_variants:missing_input" in absent_result.trace["field_origins"]
    assert "excluded_variants:explicit_preview_request" in explicit_result.trace["field_origins"]
    assert absent_result.sessions==explicit_result.sessions
    assert absent_result.trace["normalized_profile_hash"]!=explicit_result.trace["normalized_profile_hash"]
