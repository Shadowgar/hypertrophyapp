"""Application host for the existing C1–C3 lifecycle; no second planner.

Numerical policy remains provisional. Owner authorization permits bounded runtime
use, not a claim of professional approval. No fabricated inventory/history enters
calibration. The source reader retains its explicit unverified admission status.
"""
from dataclasses import replace
from datetime import date, timedelta
from functools import partial
import json
from uuid import uuid4

from sqlalchemy.orm import Session
from core_engine.customized.audit import content_hash
from core_engine.customized.library import review_catalog
from core_engine.customized.policies import candidate_standard, shorter_gym_standard, gym_design
from core_engine.customized.models import PlanningContext
from core_engine.selected_date_scheduler import validate_selected_week, place_on_selected_dates, SelectedDateError
from .customized_lifecycle import LifecycleService
from .customized_lifecycle_models import LifecycleError
from .customized_preview_models import PreviewServer, ProgramBundle
from .customized_preview_service import evaluate_preview
from .customized_postgres import PostgresUnit, PostgresSessionGate, PostgresProposalStore
from .customized_source_calendar import SourceCalendarPort
from .customized_staging_schedule import ReadOnlyCalendarAdapter
from .models import User, WorkoutPlan

PROGRAM = 'customized_full_body_v1'
HOST_VERSION = 'customized-application-v1'


def application_catalog():
    """Source-described variants, with no synthetic attainable-load inventory.

    Metadata is descriptive/provisional; metadata-v2 scoring stays disabled.
    Equipment identity is unresolved until the user calibrates that actual setup.
    """
    catalog = review_catalog()
    return replace(catalog, version='customized-descriptive-library-v1', exercises=tuple(
        replace(e, attainable_loads=(), load_identity=replace(e.load_identity,
            equipment_key='unconfirmed-setup:'+e.variant_id)) for e in catalog.exercises))


def bundles():
    catalog=application_catalog()
    return tuple(ProgramBundle(f'{kind}-{status}',
        shorter_gym_standard() if kind=='shorter' else candidate_standard(status), catalog, gym_design(),
        display_name=f'{"Shorter" if kind=="shorter" else "Full"} Full Body · {status}')
        for status in ('new','returning','current') for kind in ('longer','shorter')
        if kind!='shorter' or status=='current')


class ApplicationSchedule:
    def __init__(self, unit, clock):
        self.unit,self.clock,self.week=unit,clock,None

    def resolve(self, subject, timezone):
        from .selected_date_plans import local_week
        _,monday=local_week(timezone,self.clock())
        week=self.week or monday
        context=PlanningContext("c1-context-v1",self.clock(),week,None,None)
        result=ReadOnlyCalendarAdapter(SourceCalendarPort(self.unit),context=context).resolve(subject,timezone)
        return replace(result,source_kind='unverified')


class ApplicationLifecycle(LifecycleService):
    """Real account lifecycle; inherits immutable revisions and consent replay."""
    def _command(self, actor, key, payload, execute):
        def guarded(tx):
            if payload[0] in {"revise","challenge","accept","decline","withdraw"}:
                previous=tx.read(actor.subject,payload[1])
                if previous and previous["state"]=="active":
                    raise LifecycleError("active_program_immutable")
            return execute(tx)
        return super()._command(actor,key,payload,guarded)

    def _content_stamp(self, request):
        return content_hash((HOST_VERSION,super()._content_stamp(request)))

    def _guard(self, actor):
        if not self.server.enabled:
            raise LifecycleError('feature_disabled',404)
        if not actor or not actor.subject or not actor.session_id:
            raise LifecycleError('authentication_required',401)
        self.authorize_actor(actor)
        if self.clock().tzinfo is None:
            raise LifecycleError("invalid_server_clock",503)

    @staticmethod
    def _request(data):
        if not isinstance(data, dict) or data.get("audience", "customized_program") != "customized_program":
            raise LifecycleError("invalid_request",422)
        return LifecycleService._request({**data,"audience":"customized_program"})

    def _set_week(self, data):
        request=self._request(data)
        if not request.selected_dates:
            raise LifecycleError('three_actual_dates_required',422)
        week=min(request.selected_dates)-timedelta(days=min(request.selected_dates).weekday())
        try:
            validate_selected_week(week_start=week,selected_dates=list(request.selected_dates),
                timezone=request.timezone,planning_instant=self.clock())
        except SelectedDateError as exc:
            raise LifecycleError(str(exc),422) from None
        self.schedule.week=week

    def _snapshot(self, actor, data):
        self._set_week(data)
        snapshot=super()._snapshot(actor,{**data,'audience':'customized_program'})
        snapshot['authority']=dict(policy='provisional',metadata='descriptive_provisional_no_scoring',
            inventory='unknown_no_seed_loads',source_verified=False,scheduling='pr83_shared_date_contract',
            execution_authorization='owner_requested_m4_application_integration')
        return snapshot

    def _base_reasons(self, snapshot):
        reasons=[]
        schedule=snapshot['schedule']
        source=json.loads(schedule['source_evidence'])
        if any(w['state']=='unknown' for w in source['coverage']):
            reasons.append('ambiguous_source_coverage_requires_resolution')
        week=date.fromisoformat(schedule['context']['week_start'])
        if any(week<=date.fromisoformat(o['local_date'])<week+timedelta(days=7)
               and o['status']!='cancelled' for o in schedule['occurrences']):
            reasons.append('retained_week_occurrence_requires_resolution')
        return reasons

    def _fresh(self, actor, document):
        self._set_week(document['snapshot']['request'])
        super()._fresh(actor,document)

    def _candidate(self, document):
        p=document['snapshot']['preview']
        allowed={'coverage_or_direct_dose_tradeoff','science_policy_not_approved',
            'candidate_for_expert_review_nonprescriptive','exercise_ontology_human_review_pending',
            'adjacent_week_context_unknown_c3_carryover_deferred'}
        if (document['blocking_reasons'] or len(p['sessions'])!=3 or p['missing_actions'] or p['missing_regions']
                or any(s['cap_status']!='within_estimated_cap' for s in p['sessions'])
                or set(p['reasons'])-allowed):
            raise LifecycleError('candidate_infeasible')
        if p['dose_conflicts'] and not document['snapshot']['comparison_complete']:
            raise LifecycleError('workload_comparison_required')

    @staticmethod
    def _terms(document):
        terms,_=LifecycleService._terms(document)
        terms['text']='I choose this exact Customized program version and its dates. The training rules remain provisional; no optimality, equal-results or measured-time guarantee is established.'
        terms['acknowledgements']=[x for x in terms['acknowledgements'] if x!='inactive_candidate_unapproved_science']
        terms['acknowledgements'].append('provisional_policy_no_professional_approval_claim')
        return terms,content_hash(terms)

    def _compact_terms(self, document, audit_acknowledgements):
        terms,_=super()._compact_terms(document,audit_acknowledgements)
        terms['text']='I choose Customized and accept this exact program version, dates, workload differences and provisional training assumptions. Activate will publish it to Today. I can decline or revise before activation. Time estimates and hypertrophy outcomes are uncertain.'
        terms['summary']['schema_version']='customized-program-informed-summary-v1'
        terms['summary']['scientific_status']='provisional'
        terms['summary']['explanation']='Less scheduled work may mean less hypertrophy opportunity. Rules and time estimates are provisional. No synthetic load inventory or fabricated training history is used. Unknown neighboring weeks are disclosed; unknown is not verified rest.'
        terms['summary_hash']=content_hash(terms['summary'])
        return terms,content_hash(terms)

    def _append(self, tx, actor, document, state):
        if state not in {'active','accepted_candidate'}:
            document['can_activate']=False
        if state=='accepted_candidate':
            document['can_activate']=True
            document['consent_receipt']['authority']='server_verified_account_program_choice_provisional_policy'
        return super()._append(tx,actor,document,state)

    def activate(self, actor, proposal_id, *, expected_revision, snapshot_hash, idempotency_key):
        def execute(tx):
            document=self._owned(tx,actor,proposal_id)
            self._expected(document,expected_revision)
            if document['state']!='accepted_candidate' or not document['consent_receipt']:
                raise LifecycleError('explicit_program_acceptance_required')
            if snapshot_hash!=document['snapshot_hash']:
                raise LifecycleError('stale_content')
            self._fresh(actor,document)
            self._candidate(document)
            with Session(bind=tx.connection,join_transaction_mode='rollback_only') as db:
                snapshot=document['snapshot'];request=self._request(snapshot['request'])
                user=db.get(User,actor.subject)
                if user.scheduling_timezone and user.scheduling_timezone!=request.timezone:
                    raise LifecycleError('schedule_timezone_change_requires_resolution')
                # Every existing row is preserved. Occupied/ambiguous weeks cannot
                # be replaced merely because this is a Customized request.
                if db.query(WorkoutPlan).filter_by(user_id=actor.subject,week_start=self.schedule.week).first():
                    raise LifecycleError('existing_week_requires_resolution')
                plan=execution_payload(document)
                selected=validate_selected_week(week_start=self.schedule.week,selected_dates=list(request.selected_dates),
                    timezone=request.timezone,planning_instant=self.clock())
                plan=place_on_selected_dates(plan,selected,placement_revision=1,preserve_grouping=True,
                    previous_date=self._schedule(actor,request.timezone).planning_context().previous_training_date,
                    next_date=self._schedule(actor,request.timezone).planning_context().next_training_date)
                record=WorkoutPlan(id=str(uuid4()),user_id=actor.subject,week_start=selected.week_start,
                    split='full_body',phase='customized',payload=plan,placement_revision=1,schedule_timezone=request.timezone)
                db.add(record)
                user.scheduling_timezone=request.timezone
                # Future plans do not overwrite current program preferences.
                db.flush()
                document['active_plan_id']=record.id
                document['can_activate']=False
                document['prescriptive']=True
            return self._append(tx,actor,document,'active')
        return self._command(actor,idempotency_key,('activate',proposal_id,expected_revision,snapshot_hash),execute)


def execution_payload(document):
    snapshot=document['snapshot'];preview=snapshot['preview']
    evidence=snapshot['evidence'];sessions=[]
    for s in evidence['result']['plan']['sessions']:
        exercises=[]
        for p in s['exercises']:
            e=p['exercise']
            exercises.append(dict(id=e['variant_id'],primary_exercise_id=e['variant_id'],name=e['name'],sets=p['sets'],
                rep_range=[p['reps_min'],p['reps_max']],recommended_working_weight=None,warmups=[],
                primary_muscles=e['primary_regions'],notes='Calibrate this exercise and setup; record actual kg. No automatic increase from unknown evidence.',
                load_semantics=e['load_identity']['basis'],customized=dict(version=HOST_VERSION,target_kind=p['effort_kind'],
                    target_min=p['effort_min'],target_max=p['effort_max'],rest_seconds=p['rest_seconds'],
                    identity=e['load_identity'],calibration=p['calibration'],rationale=p['reasons']),
                progression_authority='customized_calibration_only'))
        sessions.append(dict(session_id=s['session_id'],title='Customized Full Body '+s['emphasis'][0],
            name=s['emphasis'],date=s['local_date'],exercises=exercises,customized=True,
            estimated_duration=s['duration']['total_seconds'],program_template_id=PROGRAM))
    return dict(program_template_id=PROGRAM,program_name='Customized Full Body',mode='customized',split='full_body',phase='customized',
        sessions=sessions,customized=dict(version=HOST_VERSION,proposal_id=document['proposal_id'],
            plan_version=document['plan_version'],snapshot_hash=document['snapshot_hash'],
            consent_receipt=document['consent_receipt'],authority=snapshot['authority'],trace=preview['trace']))


def build_service(engine, subject, clock, *, enabled):
    unit=PostgresUnit(engine);gate=PostgresSessionGate(unit,clock=clock)
    server=PreviewServer(enabled=enabled,environment='application',synthetic_enabled=False,allowed_subjects=(subject,),bundles=bundles())
    service=ApplicationLifecycle(server=server,store=PostgresProposalStore(unit,gate),schedule=ApplicationSchedule(unit,clock),clock=clock,
        comparison_pairs=(('shorter-current','longer-current'),),authorize_actor=gate.authorize,
        evaluator=partial(evaluate_preview,application=True))
    return service,gate
