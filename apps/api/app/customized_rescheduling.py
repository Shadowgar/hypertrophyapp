"""Consent-bound placement revisions for an existing Customized WorkoutPlan.

The #83 validator and placer own local dates and unchanged ordered sessions.
C1's accepted policy supplies its existing hard minimum calendar gap. No planner,
new occurrence, replacement prescription or parallel persistence store is used.
"""
from datetime import date, timedelta
import json
from uuid import uuid4

from sqlalchemy.orm import Session
from core_engine.customized.audit import content_hash
from core_engine.selected_date_scheduler import SelectedDateError, place_on_selected_dates, validate_selected_week
from .customized_lifecycle_models import LifecycleError
from .models import User, WorkoutOccurrence, WorkoutPlan
from .workout_identity import identified_sessions


class CustomizedRescheduling:
    def _reschedule_active(self, db, actor, document, expected_placement_revision):
        if document['state']!='active' or not document.get('active_plan_id'):
            raise LifecycleError('active_customized_program_required')
        plan=db.get(WorkoutPlan,document['active_plan_id'])
        if plan is None or plan.user_id!=actor.subject:
            raise LifecycleError('active_customized_program_required')
        payload=plan.payload;binding=payload.get('customized') or {}
        if (payload.get('mode')!='customized' or binding.get('proposal_id')!=document['proposal_id']
                or binding.get('snapshot_hash')!=document['snapshot_hash']
                or binding.get('consent_receipt')!=document['consent_receipt']
                or (payload.get('schedule') or {}).get('mode')!='selected_dates_v1'):
            raise LifecycleError('active_customized_identity_conflict')
        if type(expected_placement_revision) is not int or expected_placement_revision!=plan.placement_revision:
            raise LifecycleError('stale_placement_revision')
        if db.query(WorkoutPlan).filter_by(user_id=actor.subject,week_start=plan.week_start).filter(
                WorkoutPlan.id!=plan.id).filter(~WorkoutPlan.payload['schedule']['mode'].as_string().startswith('selected_dates_superseded')).first():
            raise LifecycleError('ambiguous_source_week')
        return plan

    def _reschedule_preview(self, db, actor, document, data, expected_placement_revision):
        plan=self._reschedule_active(db,actor,document,expected_placement_revision)
        if not isinstance(data,dict) or set(data)-{'selected_dates','timezone'}:
            raise LifecycleError('invalid_reschedule_request',422)
        try:
            raw_dates=data['selected_dates'];timezone=data['timezone']
            if not isinstance(raw_dates,list) or len(raw_dates)!=len(plan.payload['sessions']):
                raise ValueError()
            dates=[date.fromisoformat(d) if type(d) is str else d for d in raw_dates]
            if any(type(d) is not date for d in dates):raise ValueError()
        except (KeyError,ValueError,TypeError):
            raise LifecycleError('three_actual_dates_required',422) from None
        if timezone!=plan.schedule_timezone or db.get(User,actor.subject).scheduling_timezone!=timezone:
            raise LifecycleError('schedule_timezone_change_requires_resolution')
        if any(not plan.week_start<=d<plan.week_start+timedelta(days=7) for d in dates):
            raise LifecycleError('cross_week_move_requires_future_replacement')
        try:
            selected=validate_selected_week(week_start=plan.week_start,selected_dates=dates,
                timezone=timezone,planning_instant=self.clock())
        except SelectedDateError as exc:
            raise LifecycleError(str(exc),422) from None
        self.schedule.week=plan.week_start
        schedule=self._schedule(actor,timezone)
        source=json.loads(schedule.source_evidence)
        if any(w['state']=='unknown' for w in source['coverage']):
            raise LifecycleError('ambiguous_source_coverage_requires_resolution')
        frozen=db.query(WorkoutOccurrence).filter_by(user_id=actor.subject,plan_id=plan.id).all()
        frozen_by_id={o.id:o for o in frozen}
        sessions=identified_sessions(plan)
        # Any immutable occurrence freezes its slot even when every set was voided.
        if set(frozen_by_id)-{s['workout_occurrence_id'] for s in sessions}:
            raise LifecycleError('incompatible_frozen_history')
        placements=[]
        for session,day in zip(sessions,selected.dates,strict=True):
            occurrence=frozen_by_id.get(session['workout_occurrence_id'])
            previous=date.fromisoformat(session['scheduled_date'])
            if occurrence and (occurrence.scheduled_date!=previous or day!=occurrence.scheduled_date):
                raise LifecycleError('frozen_occurrence_requires_future_replacement')
            if not occurrence and day<selected.local_today:
                raise LifecycleError('selected_date_passed')
            placements.append(dict(workout_occurrence_id=session['workout_occurrence_id'],session_slot=session['session_slot'],
                from_date=previous.isoformat(),to_date=day.isoformat(),frozen=occurrence is not None))
        context=schedule.planning_context()
        try:
            minimum_gap=document['snapshot']['evidence']['bundle']['standard']['science']['minimum_gap_days']
            if type(minimum_gap) is not int or minimum_gap<1:raise ValueError()
        except (KeyError,TypeError,ValueError):
            raise LifecycleError('accepted_spacing_policy_unknown') from None
        neighbors=[d for d in (context.previous_training_date,*selected.dates,context.next_training_date) if d is not None]
        if any((right-left).days<minimum_gap for left,right in zip(neighbors,neighbors[1:])):
            raise LifecycleError('schedule_spacing_conflict',422)
        try:
            placed=place_on_selected_dates(plan.payload,selected,placement_revision=plan.placement_revision+1,
                preserve_grouping=True,previous_date=context.previous_training_date,next_date=context.next_training_date)
        except SelectedDateError as exc:
            raise LifecycleError(str(exc),422) from None
        pending=dict(version='customized-active-reschedule-v1',plan_id=plan.id,proposal_id=document['proposal_id'],
            expected_placement_revision=plan.placement_revision,timezone=timezone,
            selected_dates=[d.isoformat() for d in selected.dates],placements=placements,
            frozen_occurrence_ids=sorted(frozen_by_id),source_revision=schedule.freshness_hash(),
            plan_content_hash=content_hash(plan.payload),session_binding=content_hash(actor.session_id),source_verified=False,
            spacing=dict(owner='core_engine.customized.pilot.plan_pilot',minimum_gap_days=minimum_gap,
                previous_date=context.previous_training_date.isoformat() if context.previous_training_date else None,
                next_date=context.next_training_date.isoformat() if context.next_training_date else None),
            warnings=placed['schedule']['spacing']['warnings'])
        pending['digest']=content_hash(pending)
        return plan,placed,pending

    def preview_reschedule(self,actor,proposal_id,data,*,expected_revision,expected_placement_revision,idempotency_key):
        def execute(tx):
            document=self._owned(tx,actor,proposal_id);self._expected(document,expected_revision)
            with Session(bind=tx.connection,join_transaction_mode='rollback_only') as db:
                _,_,pending=self._reschedule_preview(db,actor,document,data,expected_placement_revision)
            document['pending_reschedule']=pending
            return self._append(tx,actor,document,'active')
        return self._command(actor,idempotency_key,('preview_reschedule',proposal_id,expected_revision,expected_placement_revision,data),execute)

    def confirm_reschedule(self,actor,proposal_id,*,expected_revision,expected_placement_revision,digest,agree,idempotency_key):
        def execute(tx):
            document=self._owned(tx,actor,proposal_id);self._expected(document,expected_revision)
            pending=document.get('pending_reschedule')
            if agree is not True:raise LifecycleError('explicit_date_change_agreement_required',422)
            if not pending or pending['digest']!=digest:
                raise LifecycleError('stale_reschedule_preview')
            if pending['session_binding']!=content_hash(actor.session_id):
                raise LifecycleError('reschedule_session_mismatch',403)
            data={key:pending[key] for key in ('selected_dates','timezone')}
            with Session(bind=tx.connection,join_transaction_mode='rollback_only') as db:
                plan,placed,fresh=self._reschedule_preview(db,actor,document,data,expected_placement_revision)
                if fresh!=pending:raise LifecycleError('stale_reschedule_preview')
                receipt=dict(receipt_id=str(uuid4()),digest=digest,subject=actor.subject,session_binding=content_hash(actor.session_id),
                    previous_placement_revision=plan.placement_revision,placement_revision=plan.placement_revision+1,
                    selected_dates=pending['selected_dates'],placements=pending['placements'],at=self.clock().isoformat(),
                    authorization_revision=actor.authorization_revision,source_verified=False)
                placed['schedule']['reschedule_receipts']=[*(plan.payload['schedule'].get('reschedule_receipts') or []),receipt]
                placed['schedule']['decision_trace']['customized_hard_spacing']=pending['spacing']
                plan.payload=placed;plan.placement_revision+=1
                db.flush()
                document['pending_reschedule']=None;document['reschedule_receipt']=receipt
            return self._append(tx,actor,document,'active')
        return self._command(actor,idempotency_key,('confirm_reschedule',proposal_id,expected_revision,
            expected_placement_revision,digest,agree),execute)
