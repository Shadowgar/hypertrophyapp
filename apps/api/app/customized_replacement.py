"""Explicit account-owned replacement; the original planner remains prescription owner."""
from copy import deepcopy
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session
from core_engine.customized.audit import content_hash
from .customized_lifecycle_models import LifecycleError
from .models import WorkoutPlan, WorkoutOccurrence, User
from .workout_identity import identified_sessions


def plan_digest(plan):
    return content_hash((plan.id,plan.user_id,plan.week_start,plan.placement_revision,plan.schedule_timezone,plan.payload))


def active_placement(db,plan):
    frozen=db.query(WorkoutOccurrence).filter_by(user_id=plan.user_id,plan_id=plan.id).all()
    return dict(plan_id=plan.id,placement_revision=plan.placement_revision,timezone=plan.schedule_timezone,
        dates=plan.payload['schedule']['selected_dates'],sessions=identified_sessions(plan,{r.id:r for r in frozen}),
        frozen_dates=[r.scheduled_date.isoformat() for r in frozen if r.scheduled_date])


class CustomizedReplacement:
    def _replacement_target(self,tx,actor,proposal_id,expected_revision=None):
        old=self._owned(tx,actor,proposal_id)
        if expected_revision is not None:self._expected(old,expected_revision)
        if old['state']!='active' or not old.get('active_plan_id'):
            raise LifecycleError('active_customized_plan_required')
        with Session(bind=tx.connection,join_transaction_mode='rollback_only') as db:
            plan=db.query(WorkoutPlan).filter_by(user_id=actor.subject,id=old['active_plan_id']).first()
            if (not plan or plan.payload.get('mode')!='customized' or
                    plan.payload.get('program_template_id')!='customized_full_body_v1' or
                    plan.payload.get('schedule',{}).get('mode')!='selected_dates_v1' or
                    plan.payload.get('customized',{}).get('proposal_id')!=proposal_id or
                    plan.payload.get('customized',{}).get('snapshot_hash')!=old['snapshot_hash'] or
                    plan.payload.get('customized',{}).get('consent_receipt')!=old['consent_receipt']):
                raise LifecycleError('active_customized_plan_required')
            placement=active_placement(db,plan)
            return dict(proposal_id=proposal_id,proposal_revision=old['revision'],plan_id=plan.id,
                plan_digest=plan_digest(plan),placement_revision=plan.placement_revision,
                week_start=plan.week_start.isoformat(),sessions=deepcopy(placement['sessions']),
                preserved_work=[dict(occurrence_id=s['workout_occurrence_id'],scheduled_date=s['scheduled_date'],
                    status='immutable_execution_snapshot') for s in placement['sessions']
                    if s.get('scheduled_date') in placement['frozen_dates']])

    def _configure_replacement(self,tx,actor,binding,week):
        current=self._replacement_target(tx,actor,binding['proposal_id'])
        if any(current[k]!=binding[k] for k in ('plan_digest','proposal_revision','placement_revision','plan_id')):
            raise LifecycleError('stale_replacement_target')
        old_week=date.fromisoformat(current['week_start'])
        if week==old_week:
            if current['preserved_work']:
                raise LifecycleError('started_plan_requires_future_week_replacement')
            self.schedule.exclude_plan=current['plan_id']
            kind='same_week_unstarted'
        elif week==old_week+timedelta(days=7):
            self.schedule.exclude_plan=None
            kind='future_week'
        else:
            raise LifecycleError('replacement_requires_same_or_next_week')
        self.replacement={**current,'kind':kind}
        return self.replacement

    def create_replacement(self,actor,proposal_id,data,*,expected_revision,idempotency_key):
        def execute(tx):
            target=self._replacement_target(tx,actor,proposal_id,expected_revision)
            self._set_week(data)
            self._configure_replacement(tx,actor,target,self.schedule.week)
            snapshot=self._snapshot(actor,data)
            document=dict(proposal_id=str(uuid4()),subject=actor.subject,plan_version=1,revision=0,
                snapshot=snapshot,snapshot_hash=content_hash(snapshot),events=[],consent_receipt=None,
                pending_challenge=None,blocking_reasons=self._base_reasons(snapshot),can_activate=False,prescriptive=False)
            self._append(tx,actor,document,'previewed')
            return self._append(tx,actor,document,self._assessment(snapshot))
        return self._command(actor,idempotency_key,('replacement',proposal_id,expected_revision,data),execute)

    def get(self,actor,proposal_id):
        self._guard(actor)
        with self._transaction(actor) as tx:
            document=self._public(self._owned(tx,actor,proposal_id))
            if document['state']=='active':
                with Session(bind=tx.connection,join_transaction_mode='rollback_only') as db:
                    plan=db.query(WorkoutPlan).filter_by(user_id=actor.subject,id=document['active_plan_id']).one()
                    document['active_placement']=active_placement(db,plan)
            return document

    def active(self,actor):
        self._guard(actor)
        with self._transaction(actor) as tx:
            from .selected_date_plans import local_week
            with Session(bind=tx.connection,join_transaction_mode='rollback_only') as db:
                user=db.get(User,actor.subject)
                _,week=local_week(user.scheduling_timezone or 'UTC',self.clock())
            ids=tx.connection.execute(text('''SELECT h.proposal_id FROM customized_candidate_heads h
                JOIN customized_candidate_events e ON e.subject=h.subject AND e.proposal_id=h.proposal_id AND e.revision=h.revision
                JOIN workout_plans p ON p.id=e.document->>'active_plan_id' AND p.user_id=h.subject
                WHERE h.subject=:s AND e.document->>'state'='active' AND p.week_start BETWEEN :start AND :end
                ORDER BY p.week_start,h.proposal_id'''),dict(s=actor.subject,start=week,end=week+timedelta(days=7))).scalars().all()
            plans=[]
            for id in ids:
                document=self._public(self._owned(tx,actor,id))
                with Session(bind=tx.connection,join_transaction_mode='rollback_only') as db:
                    plan=db.query(WorkoutPlan).filter_by(user_id=actor.subject,id=document['active_plan_id']).one()
                    document['active_placement']=active_placement(db,plan)
                plans.append(document)
            return dict(plans=plans)
