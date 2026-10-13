from copy import deepcopy
from datetime import date, timedelta
from uuid import uuid4
import pytest
from app.database import SessionLocal
from app.models import WorkoutPlan, WorkoutOccurrence, WorkoutSetLog, ExerciseState, User
from app.workout_identity import identified_sessions
from app.program_loader import load_program_template, _adaptive_slot_to_runtime_exercise
from app.routers.plan import _prepare_authored_frequency_adapted_template
from core_engine.scheduler import generate_week_plan, AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY
from core_engine.authored_constraints import annotate_constraints
from test_authored_typed_execution import typed_plan
from test_workout_occurrence_identity import scenario, submission, log


def constrained_plan(user, *, alternatives=True, bodyweight=True):
    session = typed_plan(user, raw="8-12")
    exercise = session["exercises"][0]
    exercise["source_approved_alternatives"] = [{"option_id": "substitution_option_1", "id": "source-variant",
        "name": "Approved variant", "movement_pattern": "hinge", "equipment_tags": ["bodyweight"],
        "load_semantics": "bodyweight" if bodyweight else "external_load", "permission": {
            **exercise["source_lineage"], "source_option": "substitution_option_1", "source_option_value": "Approved variant"}}] if alternatives else []
    exercise = annotate_constraints(exercise, restrictions=["deep_knee_flexion"])
    session["exercises"][0] = exercise
    with SessionLocal() as db:
        user_row = db.get(User, user);user_row.movement_restrictions = ["deep_knee_flexion"]
        row = db.get(WorkoutPlan, session["plan_id"])
        value = deepcopy(row.payload);value["sessions"][0]["exercises"][0] = exercise
        row.payload = value;db.commit()
    return session


def decision(session, action, **kwargs):
    e = session["exercises"][0]
    return {"command_id": str(uuid4()), "exercise_id": e["id"], "exercise_occurrence_id": e["exercise_occurrence_id"],
        "expected_revision": e.get("authored_constraint", {}).get("revision", 0),
        "expected_source_lineage": e["source_lineage"], "action": action, **kwargs}


def send(client, headers, session, payload):
    return client.post(f"/workout/{session['workout_occurrence_id']}/authored-substitution", headers=headers, json=payload)


@pytest.mark.parametrize("phase", [1, 2])
@pytest.mark.parametrize("days", [3, 5])
def test_plan_preparation_preserves_source_with_irrelevant_and_supported_restrictions(phase, days):
    id = f"pure_bodybuilding_phase_{phase}_full_body";template = load_program_template(id)
    results = []
    for restrictions in [[], ["unmatched"], ["deep_knee_flexion"]]:
        runtime, trace = _prepare_authored_frequency_adapted_template(selected_template_id=id, program_template=template,
            current_days_available=days, active_frequency_adaptation=None, training_state={}, stored_weak_areas=["shoulders", "biceps"],
            equipment_profile=[], session_time_budget_minutes=15, movement_restrictions=restrictions, prior_generated_weeks=0)
        assert runtime[AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY] and trace["authoritative_passthrough_eligible"]
        p = generate_week_plan({"name": "Synthetic"}, days, "full_body", runtime, [], "maintenance",
            weak_areas=["shoulders", "biceps"], session_time_budget_minutes=15, movement_restrictions=restrictions)
        from core_engine.generation import prepare_generate_week_finalize_runtime
        from types import SimpleNamespace
        review = SimpleNamespace(adjustments={"exercise_adjustments": [{"exercise_id": p["sessions"][0]["exercises"][0]["id"], "set_delta": 10, "weight_scale": 0.5}]},
            week_start=date.today(), body_weight=80, calories=2500, protein=150, adherence_score=4)
        finalized = prepare_generate_week_finalize_runtime(user_id="synthetic", base_plan=p,
            template_selection_trace={}, generation_runtime_trace={}, generated_adaptive_runtime=None,
            selected_template_id=id, active_frequency_adaptation=None, review_cycle=review)
        assert finalized["response_payload"]["sessions"] == p["sessions"]
        results.append([[{k:e.get(k) for k in ['id','sets','rep_range','authored_prescription','source_lineage','slot_role']} for e in s['exercises']] for s in p['sessions']])
    assert results[0] == results[1] == results[2]
    assert not template.get(AUTHORITATIVE_AUTHORED_PASSTHROUGH_KEY)


def test_source_permission_comes_from_slot_not_generic_library():
    slot = {"exercise_id": "source", "exercise": "Source", "authored_prescription": {
        "raw": {"substitution_option_1": "Approved variant"}, "sets": [{"rep_target": {"kind":"reps","min":8,"max":12}}]},
        "source_lineage": {"source_slot_id": "slot", "source_sha256": "source"}}
    library = {"source": {"canonical_name": "Source", "valid_substitutions": [{"exercise_id":"generic"}]},
        "approved": {"exercise_id":"approved", "canonical_name":"Approved variant", "equipment_tags":["bodyweight"], "movement_pattern":"hinge"},
        "generic": {"exercise_id":"generic", "canonical_name":"Generic"}}
    result = _adaptive_slot_to_runtime_exercise(slot, library, artifact_hash="artifact")
    assert [c["id"] for c in result["source_approved_alternatives"]] == ["approved"]
    assert result["source_approved_alternatives"][0]["permission"]["source_slot_id"] == "slot"
    missing = deepcopy(slot);missing["authored_prescription"]["raw"] = {}
    assert _adaptive_slot_to_runtime_exercise(missing, library, artifact_hash="artifact")["source_approved_alternatives"] == []


def test_confirmed_variant_retains_source_retry_today_history_correction_and_undo(scenario):
    user, headers, client = scenario;session = constrained_plan(user);source = deepcopy(session["exercises"][0])
    assert log(client, headers, session, submission(session)).status_code == 409
    request = decision(session, "confirm", option_id="substitution_option_1")
    r = send(client, headers, session, request);assert r.status_code == 200, r.text
    assert send(client, headers, session, request).json() == r.json()
    changed = r.json()["exercise"]
    assert changed["id"] == source["id"] and changed["source_lineage"] == source["source_lineage"]
    assert changed["authored_prescription"] == source["authored_prescription"]
    assert changed["performed_variant"]["id"] == "source-variant"
    assert changed["substitution_consent"]["confirmed"] and changed["substitution_consent"]["timestamp"]
    assert send(client, headers, session, {**request, "option_id":"generic"}).status_code == 409
    payload = submission(session);payload["weight"] = 0
    logged = log(client, headers, session, payload);assert logged.status_code == 200, logged.text
    today = client.get('/workout/today',headers=headers).json()["exercises"][0]
    assert today["performed_variant"] == changed["performed_variant"] and today["completed_sets"] == 1
    assert today["exercise_occurrence_id"] == source["exercise_occurrence_id"]
    history = client.get(f"/history/exercise/{source['id']}",headers=headers).json()["history"][0]
    assert history["weight"] == 0 and history["performed_variant"] == changed["performed_variant"]
    assert history["substitution_consent"] == changed["substitution_consent"]
    day = client.get(f"/history/day/{date.today().isoformat()}", headers=headers)
    assert day.status_code == 200, day.text
    entries = [entry for workout in day.json()["workouts"] for e in workout["exercises"] for entry in e["sets"]]
    assert entries[0]["performed_variant"] == changed["performed_variant"]
    assert entries[0]["exercise_occurrence_id"] == source["exercise_occurrence_id"]
    assert entries[0]["original_authored_name"] == source["name"]
    summary = client.get(f"/workout/{session['workout_occurrence_id']}/summary",headers=headers).json()["exercises"][0]
    assert summary["performed_variant"] == changed["performed_variant"] and summary["load_recommendation_available"] is False
    correction = client.post(f"/workout/set/{logged.json()['id']}/correct",headers=headers,
        json={"command_id":str(uuid4()),"reps":11,"weight":0,"reason":"Synthetic correction"})
    assert correction.status_code == 200, correction.text
    assert client.post(f"/workout/{session['workout_occurrence_id']}/undo-last-set",headers=headers,
        json={"command_id":str(uuid4()),"exercise_id":source["id"],"exercise_occurrence_id":source["exercise_occurrence_id"]}).status_code == 200
    with SessionLocal() as db:
        assert db.query(ExerciseState).filter_by(user_id=user).count() == 0
        assert all(row.replay_context["planned_exercise"]["performed_variant"] == changed["performed_variant"]
            for row in db.query(WorkoutSetLog).filter_by(user_id=user).all())
        assert db.get(WorkoutOccurrence, session["workout_occurrence_id"]).payload["exercises"][0]["id"] == source["id"]


@pytest.mark.parametrize("alternatives", [True, False])
def test_decline_or_missing_alternative_preserves_visible_unresolved_slot(scenario, alternatives):
    user, headers, client = scenario;session = constrained_plan(user, alternatives=alternatives)
    e = session['exercises'][0]
    assert e['authored_constraint']['status'] == ('unresolved' if alternatives else 'infeasible')
    assert not e.get('performed_variant')
    assert log(client,headers,session,submission(session)).status_code == 409
    r = send(client,headers,session,decision(session,'decline'));assert r.status_code == 200
    assert r.json()['exercise']['authored_constraint']['status'] == 'declined'
    assert not r.json()['exercise'].get('performed_variant')
    assert send(client,headers,session,decision(session,'confirm',option_id='generic')).status_code == 409


def test_stale_source_or_decision_and_foreign_occurrence_cannot_confirm(scenario):
    user, headers, client = scenario;session = constrained_plan(user)
    request = decision(session,'confirm',option_id='substitution_option_1')
    assert send(client,headers,session,{**request,'expected_revision':99}).status_code == 409
    assert send(client,headers,session,{**request,'expected_source_lineage':{}}).status_code == 409
    assert send(client,headers,{**session,'workout_occurrence_id':str(uuid4())},request).status_code == 404
    with SessionLocal() as db:assert db.get(WorkoutOccurrence,session['workout_occurrence_id']) is None


def test_external_variant_still_rejects_zero_and_regeneration_does_not_transfer_consent(scenario):
    user,headers,client = scenario;session = constrained_plan(user,bodyweight=False)
    r=send(client,headers,session,decision(session,'confirm',option_id='substitution_option_1'));assert r.status_code == 200
    payload=submission(session);payload['weight']=0
    assert log(client,headers,session,payload).status_code == 422
    payload['weight']=12
    assert log(client,headers,session,payload).status_code == 200
    with SessionLocal() as db:
        first=db.get(WorkoutPlan,session['plan_id']);new=WorkoutPlan(user_id=user,week_start=date.today()+timedelta(days=7),
            split=first.split,phase=first.phase,payload=deepcopy(first.payload))
        db.add(new);db.commit();new_session=identified_sessions(new)[0]
        assert new_session['workout_occurrence_id'] != session['workout_occurrence_id']
        assert not new_session['exercises'][0].get('performed_variant')
        assert new_session['exercises'][0]['authored_constraint']['status']=='unresolved'
        assert db.get(WorkoutOccurrence,session['workout_occurrence_id']).payload['exercises'][0]['performed_variant']


def test_pain_report_is_slot_scoped_and_pauses_a_started_confirmed_variant(scenario):
    user,headers,client=scenario;session=constrained_plan(user)
    confirmed=send(client,headers,session,decision(session,'confirm',option_id='substitution_option_1'))
    assert confirmed.status_code==200
    session['exercises'][0]=confirmed.json()['exercise']
    payload=submission(session);payload['weight']=0
    assert log(client,headers,session,payload).status_code==200
    reported=send(client,headers,session,decision(session,'report',reason='pain'))
    assert reported.status_code==200
    e=reported.json()['exercise']
    assert e['authored_constraint']['status']=='confirmed'
    assert e['authored_constraint']['execution_status'] in {'unresolved', 'infeasible'}
    assert any(r['kind']=='pain' for r in e['authored_constraint']['reasons'])
    assert e['performed_variant']==confirmed.json()['exercise']['performed_variant']
    next_set=submission(session,index=2);next_set['weight']=0
    assert log(client,headers,session,next_set).status_code==409
    with SessionLocal() as db:
        assert db.query(WorkoutSetLog).filter_by(user_id=user).count()==1
        assert db.query(WorkoutSetLog).filter_by(user_id=user).one().replay_context['planned_exercise']['authored_constraint']['status']=='confirmed'


def test_current_profile_conflict_pauses_confirmed_variant_without_rewriting_frozen_receipts(scenario):
    user,headers,client=scenario;session=constrained_plan(user,bodyweight=False)
    r=send(client,headers,session,decision(session,'confirm',option_id='substitution_option_1'));assert r.status_code==200
    with SessionLocal() as db:
        u=db.get(User,user);u.equipment_profile=['dumbbell']
        occurrence=db.get(WorkoutOccurrence,session['workout_occurrence_id']);before=deepcopy(occurrence.payload)
        changed=deepcopy(occurrence.payload);changed['exercises'][0]['performed_variant']['equipment_tags']=['barbell']
        occurrence.payload=changed;db.commit()
    today=client.get('/workout/today',headers=headers).json()['exercises'][0]
    assert today['authored_constraint']['status']=='confirmed'
    assert today['authored_constraint']['execution_status']=='infeasible'
    assert log(client,headers,session,submission(session)).status_code==409
    with SessionLocal() as db:
        assert db.get(WorkoutOccurrence,session['workout_occurrence_id']).payload['exercises'][0]['authored_constraint']['status']=='confirmed'
        assert db.query(WorkoutSetLog).filter_by(user_id=user).count()==0


def test_confirmed_variant_cannot_change_after_a_receipt_and_foreign_owner_is_rejected(scenario):
    from app.security import create_access_token
    user,headers,client=scenario;session=constrained_plan(user)
    r=send(client,headers,session,decision(session,'confirm',option_id='substitution_option_1'));assert r.status_code==200
    session['exercises'][0]=r.json()['exercise'];payload=submission(session);payload['weight']=0
    assert log(client,headers,session,payload).status_code==200
    assert send(client,headers,session,decision(session,'decline')).status_code==409
    with SessionLocal() as db:
        other=User(id=str(uuid4()),email=f'{uuid4()}@example.com',name='Synthetic foreign',password_hash='unused',selected_program_id='full_body_v1')
        db.add(other);db.commit();foreign={'Authorization':'Bearer '+create_access_token(other.id)}
    assert send(client,foreign,session,decision(session,'confirm',option_id='substitution_option_1')).status_code==404


def test_legacy_authored_conflict_stays_unresolved_without_invented_permission(scenario):
    from test_workout_occurrence_identity import plan
    user,headers,client=scenario
    session=plan(user,date.today(),program='pure_bodybuilding_phase_1_full_body')
    with SessionLocal() as db:
        u=db.get(User,user);u.movement_restrictions=['deep_knee_flexion'];db.commit()
    today=client.get('/workout/today',headers=headers).json()['exercises'][0]
    assert today['authored_constraint']['status']=='infeasible'
    assert not today.get('source_lineage') and not today.get('performed_variant')
    assert log(client,headers,session,submission(session)).status_code==409
    request={'command_id':str(uuid4()),'exercise_id':today['id'],'exercise_occurrence_id':today['exercise_occurrence_id'],
        'expected_revision':0,'expected_source_lineage':{},'action':'report','reason':'safety'}
    assert send(client,headers,session,request).status_code==200
    assert send(client,headers,session,{**request,'command_id':str(uuid4()),'action':'confirm','expected_revision':1,'option_id':'generic'}).status_code==409


@pytest.mark.parametrize("kind", ["equipment", "restriction"])
@pytest.mark.parametrize("declined", [False, True])
def test_profile_changes_restore_unconfirmed_original_without_new_occurrence(scenario, kind, declined):
    user, headers, client = scenario
    session = constrained_plan(user)
    with SessionLocal() as db:
        u = db.get(User, user)
        row = db.get(WorkoutPlan, session['plan_id'])
        value = deepcopy(row.payload)
        e = value['sessions'][0]['exercises'][0]
        if kind == 'equipment':
            u.movement_restrictions = []
            u.equipment_profile = ['dumbbell']
            e['equipment_tags'] = ['barbell']
            e = annotate_constraints(e, equipment=u.equipment_profile)
            value['sessions'][0]['exercises'][0] = e
            row.payload = value
        db.commit()
    assert client.get('/workout/today', headers=headers).json()['exercises'][0]['authored_constraint']['status'] in {'unresolved', 'infeasible'}
    assert log(client, headers, session, submission(session)).status_code == 409
    if declined:
        assert send(client, headers, session, decision(session, 'decline')).status_code == 200
    with SessionLocal() as db:
        u = db.get(User, user)
        u.movement_restrictions = []
        u.equipment_profile = ['barbell', 'bodyweight']
        db.commit()
    today = client.get('/workout/today', headers=headers).json()['exercises'][0]
    assert today['authored_constraint']['status'] == 'ready'
    assert today['exercise_occurrence_id'] == session['exercises'][0]['exercise_occurrence_id']
    assert log(client, headers, session, submission(session)).status_code == 200


@pytest.mark.parametrize("reason", ['pain', 'safety'])
def test_profile_refresh_does_not_erase_reported_conflicts(scenario, reason):
    user, headers, client = scenario
    session = constrained_plan(user)
    r = send(client, headers, session, decision(session, 'report', reason=reason))
    assert r.status_code == 200
    with SessionLocal() as db:
        db.get(User, user).movement_restrictions = []
        db.commit()
    today = client.get('/workout/today', headers=headers).json()['exercises'][0]
    assert today['authored_constraint']['reasons'] == [{'kind': reason, 'details': ['user_reported']}]
    assert log(client, headers, session, submission(session)).status_code == 409


def test_external_variant_response_clears_source_load_but_retains_frozen_source(scenario):
    user, headers, client = scenario
    session = constrained_plan(user, bodyweight=False)
    source = deepcopy(session['exercises'][0])
    response = send(client, headers, session, decision(session, 'confirm', option_id='substitution_option_1'))
    assert response.status_code == 200
    e = response.json()['exercise']
    assert e['recommended_working_weight'] == 0 and e['load_recommendation_available'] is False
    assert e['source_load_context']['recommended_working_weight'] == source['recommended_working_weight']
    assert e['authored_prescription'] == source['authored_prescription']
    assert not e['warmups']
    with SessionLocal() as db:
        frozen = db.get(WorkoutOccurrence, session['workout_occurrence_id']).payload['exercises'][0]
        assert frozen['recommended_working_weight'] == source['recommended_working_weight']
    today = client.get('/workout/today', headers=headers).json()['exercises'][0]
    assert today['recommended_working_weight'] is None and not today['warmups']
    assert today['load_intelligence']['next_exposure']['action'] == 'monitor'
