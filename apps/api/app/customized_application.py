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
from .customized_replacement import CustomizedReplacement, plan_digest
from .customized_rescheduling import CustomizedRescheduling

PROGRAM = 'customized_full_body_v1'
HOST_VERSION = 'customized-application-v1'


def application_catalog(profile=None):
    """Source-described variants, with no synthetic attainable-load inventory.

    Metadata is descriptive/provisional; metadata-v2 scoring stays disabled.
    Equipment identity is unresolved until the user calibrates that actual setup.
    """
    catalog = review_catalog()
    catalog=replace(catalog, version='customized-descriptive-library-v1', exercises=tuple(
        replace(e, attainable_loads=(), load_identity=replace(e.load_identity,
            equipment_key='unconfirmed-setup:'+e.variant_id)) for e in catalog.exercises))
    from .customized_inventory import catalog_for_profile
    return catalog_for_profile(catalog,profile)


def bundles(profile=None,exposures=(),reports=()):
    catalog=application_catalog(profile)
    return tuple(ProgramBundle(f'{kind}-{status}',
        shorter_gym_standard() if kind=='shorter' else candidate_standard(status), catalog, gym_design(),exposures=exposures,strength_reports=reports,
        display_name=f'{"Shorter" if kind=="shorter" else "Full"} Full Body · {status}')
        for status in ('new','returning','current') for kind in ('longer','shorter')
        if kind!='shorter' or status=='current')


class ApplicationSchedule:
    def __init__(self, unit, clock):
        self.unit,self.clock,self.week=unit,clock,None
        self.exclude_plan=None

    def resolve(self, subject, timezone):
        from .selected_date_plans import local_week
        _,monday=local_week(timezone,self.clock())
        week=self.week or monday
        context=PlanningContext("c1-context-v1",self.clock(),week,None,None)
        result=ReadOnlyCalendarAdapter(SourceCalendarPort(self.unit),context=context).resolve(subject,timezone)
        if self.exclude_plan:
            evidence=json.loads(result.source_evidence)
            excluded={o['occurrence_id'] for o in evidence['occurrences'] if o['plan_id']==self.exclude_plan}
            result=replace(result,occurrences=tuple(o for o in result.occurrences if o.occurrence_id not in excluded))
        return replace(result,source_kind='unverified')


class ApplicationLifecycle(CustomizedRescheduling, CustomizedReplacement, LifecycleService):
    """Real account lifecycle; inherits immutable revisions and consent replay."""
    def _command(self, actor, key, payload, execute):
        def guarded(tx):
            if payload[0] in {"revise","challenge","accept","decline","withdraw"}:
                previous=tx.read(actor.subject,payload[1])
                if previous and previous["state"]=="active":
                    raise LifecycleError("active_program_immutable")
            if payload[0]=='revise':
                previous=tx.read(actor.subject,payload[1])
                binding=(previous or {}).get('snapshot',{}).get('replacement')
                if binding:
                    self._set_week(payload[3])
                    self._configure_replacement(tx,actor,binding,self.schedule.week)
            return execute(tx)
        # Replacement exclusions are command-local authority, never mutable
        # permission inherited by a subsequent request on a reused service.
        self.schedule.exclude_plan=None
        self.replacement=None
        try:
            return super()._command(actor,key,payload,guarded)
        finally:
            self.schedule.exclude_plan=None
            self.replacement=None

    def _content_stamp(self, request):
        return content_hash((HOST_VERSION,getattr(self,"inventory",None),super()._content_stamp(request)))

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
        if getattr(self,'inventory',None):
            from .customized_inventory import read_profile
            with Session(bind=self.store.unit.connection(actor.subject),join_transaction_mode='rollback_only') as db:
                current=read_profile(db,actor.subject)
            requested_revision=data.get('inventory_revision',current['revision'])
            # A pre-inventory account's normalized request serializes the optional
            # revision as null. It cannot conceal an existing saved inventory.
            if requested_revision is None and current['revision']==0 and current['profile'] is None:
                requested_revision=0
            if current!=self.inventory or requested_revision!=current['revision']:
                raise LifecycleError('stale_inventory',409)
            if current['profile'] and set(data.get('equipment',[]))!=set(current['profile']['equipment']):
                raise LifecycleError('equipment_differs_from_saved_location',422)
        snapshot=super()._snapshot(actor,{**data,'audience':'customized_program'})
        snapshot['inventory']=getattr(self,'inventory',None)
        if getattr(self,'replacement',None):snapshot['replacement']=self.replacement
        from .customized_inventory import inventory_issues
        snapshot['inventory_issues']=inventory_issues(application_catalog(),snapshot['inventory'])
        snapshot['authority']=dict(policy='provisional',metadata='descriptive_provisional_no_scoring',
            inventory='account_declared_no_synthetic_loads',source_verified=False,scheduling='pr83_shared_date_contract',
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
        from .customized_inventory import read_profile
        with Session(bind=self.store.unit.connection(actor.subject),join_transaction_mode='rollback_only') as db:
            if read_profile(db,actor.subject)!=self.inventory:raise LifecycleError('stale_inventory')
        self._set_week(document['snapshot']['request'])
        binding=document['snapshot'].get('replacement')
        if binding:
            with self._transaction(actor) as tx:
                self._configure_replacement(tx,actor,binding,self.schedule.week)
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
        if document['snapshot'].get('replacement'):
            binding=document['snapshot']['replacement']
            terms['acknowledgements'].append(f"explicit_replacement:{binding['plan_id']}:{binding['plan_digest']}:{binding['kind']}")
        return terms,content_hash(terms)

    def _compact_terms(self, document, audit_acknowledgements):
        terms,_=super()._compact_terms(document,audit_acknowledgements)
        terms['text']='I choose Customized and accept this exact program version, dates, workload differences and provisional training assumptions. Activate will publish it to Today. I can decline or revise before activation. Time estimates and hypertrophy outcomes are uncertain.'
        terms['summary']['schema_version']='customized-program-informed-summary-v1'
        terms['summary']['scientific_status']='provisional'
        terms['summary']['explanation']='Less scheduled work may mean less hypertrophy opportunity. Rules and time estimates are provisional. No synthetic load inventory or fabricated training history is used. Unknown neighboring weeks are disclosed; unknown is not verified rest.'
        if document['snapshot'].get('replacement'):
            terms['summary']['replacement']={**document['snapshot']['replacement'],
                'proposed_sessions':document['snapshot']['preview']['sessions']}
            terms['text']='I explicitly replace the identified Customized plan with this exact program version and dates, preserving recorded work. '+terms['text']
        terms['summary_hash']=content_hash(terms['summary'])
        return terms,content_hash(terms)

    def _append(self, tx, actor, document, state):
        if state not in {'active','accepted_candidate'}:
            document['can_activate']=False
        if state=='accepted_candidate':
            document['can_activate']=True
            document['consent_receipt']['authority']='server_verified_account_program_choice_provisional_policy'
        result=super()._append(tx,actor,document,state)
        if state=='active' and document.get('active_plan_id'):
            from .customized_replacement import active_placement
            with Session(bind=tx.connection,join_transaction_mode='rollback_only') as db:
                result['active_placement']=active_placement(db,db.get(WorkoutPlan,document['active_plan_id']))
        return result

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
                from .workout_history import lock_history_user
                from .flexible_training import guard_calendar
                lock_history_user(db, actor.subject)
                guard_calendar(db, actor.subject)
                user=db.get(User,actor.subject)
                if user.scheduling_timezone and user.scheduling_timezone!=request.timezone:
                    raise LifecycleError('schedule_timezone_change_requires_resolution')
                # Every existing row is preserved. Occupied/ambiguous weeks cannot
                # be replaced merely because this is a Customized request.
                binding=snapshot.get('replacement')
                occupied=[r for r in db.query(WorkoutPlan).filter_by(user_id=actor.subject,week_start=self.schedule.week).all()
                    if not r.payload.get('schedule',{}).get('mode','').startswith('selected_dates_superseded')]
                replacing=binding and binding['kind']=='same_week_unstarted'
                if occupied and (not replacing or len(occupied)!=1 or occupied[0].id!=binding['plan_id']):
                    raise LifecycleError('existing_week_requires_resolution')
                old_document=None
                if replacing:
                    old_document=self._owned(tx,actor,binding['proposal_id'])
                    previous=occupied[0]
                    if plan_digest(previous)!=binding['plan_digest']:
                        raise LifecycleError('stale_replacement_target')
                plan=execution_payload(document)
                selected=validate_selected_week(week_start=self.schedule.week,selected_dates=list(request.selected_dates),
                    timezone=request.timezone,planning_instant=self.clock())
                plan=place_on_selected_dates(plan,selected,placement_revision=1,preserve_grouping=True,
                    previous_date=self._schedule(actor,request.timezone).planning_context().previous_training_date,
                    next_date=self._schedule(actor,request.timezone).planning_context().next_training_date)
                record=WorkoutPlan(id=str(uuid4()),user_id=actor.subject,week_start=selected.week_start,
                    split='full_body',phase='customized',payload=plan,placement_revision=1,schedule_timezone=request.timezone)
                db.add(record)
                if replacing:
                    from copy import deepcopy
                    retained=deepcopy(previous.payload)
                    retained['schedule'].update(mode='selected_dates_superseded_v1',superseded_by_plan_id=record.id,
                        replacement_proposal_id=proposal_id)
                    previous.payload=retained
                    old_document['superseded_by_proposal_id']=proposal_id
                    old_document['superseded_by_plan_id']=record.id
                    old_document['prescriptive']=False
                    self._append(tx,actor,old_document,'superseded')
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
                    identity=e['load_identity'],calibration=p['calibration'],rationale=p['reasons'],
                    training_status=snapshot['request']['training_context'],inventory=snapshot.get('inventory')),
                progression_authority='customized_calibration_only'))
        sessions.append(dict(session_id=s['session_id'],title='Customized Full Body '+s['emphasis'][0],
            name=s['emphasis'],date=s['local_date'],exercises=exercises,customized=True,
            estimated_duration=s['duration']['total_seconds'],program_template_id=PROGRAM))
    result=dict(program_template_id=PROGRAM,program_name='Customized Full Body',mode='customized',split='full_body',phase='customized',
        sessions=sessions,customized=dict(version=HOST_VERSION,proposal_id=document['proposal_id'],
            plan_version=document['plan_version'],snapshot_hash=document['snapshot_hash'],
            consent_receipt=document['consent_receipt'],authority=snapshot['authority'],trace=preview['trace']))
    if snapshot.get('replacement'):result['customized']['replacement']=snapshot['replacement']
    return result


def build_service(engine, subject, clock, *, enabled):
    unit=PostgresUnit(engine);gate=PostgresSessionGate(unit,clock=clock)
    from .customized_inventory import read_profile,strength_reports
    from .customized_load_evidence import completed_exposures
    with Session(engine) as db:
        from zoneinfo import ZoneInfo
        as_of=clock().astimezone(ZoneInfo(db.get(User,subject).scheduling_timezone or 'UTC')).date()
        inventory=read_profile(db,subject)
        catalog=application_catalog(inventory)
        exposures=completed_exposures(db,subject,as_of,[e.variant_id for e in catalog.exercises],
            max_age_days=max(b.standard.science.calibration.history_max_age_days for b in bundles()))
    reports=strength_reports(inventory,catalog,as_of)
    server=PreviewServer(enabled=enabled,environment='application',synthetic_enabled=False,allowed_subjects=(subject,),bundles=bundles(inventory,exposures,reports))
    service=ApplicationLifecycle(server=server,store=PostgresProposalStore(unit,gate),schedule=ApplicationSchedule(unit,clock),clock=clock,
        comparison_pairs=(('shorter-current','longer-current'),),authorize_actor=gate.authorize,
        evaluator=partial(evaluate_preview,application=True))
    service.inventory=inventory
    return service,gate
