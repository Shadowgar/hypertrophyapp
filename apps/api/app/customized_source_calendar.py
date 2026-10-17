"""Read-only projection of actual #83 source tables. No source-verification grant.

Pinned source: selected_date_plans.py@3f4927b and unchanged workout_identity/history
models. This reads real ORM table shapes on the candidate's account transaction;
#83 is unmerged, so source_verified is permanently False in this adapter.
"""
from collections import defaultdict
from datetime import date,timedelta
from types import SimpleNamespace
from sqlalchemy import select
from core_engine.customized.audit import content_hash
from .models import WorkoutPlan,WorkoutOccurrence,WorkoutSetLog,WorkoutLogCommand,WorkoutSessionState
from .workout_identity import identified_sessions
from .customized_staging_schedule import CalendarWindow,CalendarOccurrence,SOURCE_CONTRACT
from .customized_lifecycle_models import LifecycleError

AUTHORED=frozenset(('pure_bodybuilding_phase_1_full_body','pure_bodybuilding_phase_2_full_body'))


class SourceCalendarPort:
    source_verified=False
    def __init__(self,unit):self.unit=unit

    def read(self,subject,timezone,start,end):
        with self.unit.account(subject) as conn:
            def owned(model):
                table=model.__table__
                return [dict(r) for r in conn.execute(select(table).where(table.c.user_id==subject)).mappings()]
            # Never join on catalog exercise IDs; occurrence/slot identities survive
            # repeated exercises. Retained void/amendment/command rows bind freshness.
            plans=[r for r in owned(WorkoutPlan) if start<=r['week_start']<=end]
            snapshots=[r for r in owned(WorkoutOccurrence) if start<=r['week_start']<=end]
            ids={r['id'] for r in snapshots}
            logs=owned(WorkoutSetLog);commands=owned(WorkoutLogCommand);states=owned(WorkoutSessionState)
            relevant_logs=[r for r in logs if r['workout_occurrence_id'] in ids]
            relevant_commands=[r for r in commands if r['workout_occurrence_id'] in ids]
            relevant_states=[r for r in states if r['workout_occurrence_id'] in ids]
            evidence=dict(plans=plans,snapshots=snapshots,logs=relevant_logs,commands=relevant_commands,states=relevant_states,
                legacy_logs=[r for r in logs if r['workout_occurrence_id'] is None])
            for rows in evidence.values():rows.sort(key=lambda r:r['id'])
            revision=content_hash(evidence)
            by_week=defaultdict(list);complete=not evidence['legacy_logs'];sessions={}
            snap_by_id={r['id']:SimpleNamespace(**r) for r in snapshots}
            for row in plans:
                payload=row['payload'];schedule=payload.get('schedule') or {}
                if schedule.get('mode','').startswith('selected_dates_superseded'):continue
                by_week[row['week_start']].append(row)
                sessions_payload=payload.get('sessions') or []
                if not isinstance(sessions_payload,list) or any(not isinstance(v,dict) for v in sessions_payload):
                    raise LifecycleError('invalid_source_sessions')
                dates=schedule.get('selected_dates')
                session_dates=[v.get('scheduled_date') for v in sessions_payload]
                valid_dates=isinstance(dates,list) and all(type(v) is str for v in dates)
                valid_session_dates=all(type(v) is str for v in session_dates)
                if (schedule.get('mode')!='selected_dates_v1' or row['schedule_timezone']!=timezone
                        or not sessions_payload or not valid_dates or not dates or not valid_session_dates
                        or len(dates)!=len(set(dates)) or sorted(dates)!=sorted(session_dates)
                        or type(row['placement_revision']) is not int or row['placement_revision']<1
                        or schedule.get('week_start')!=row['week_start'].isoformat() or schedule.get('timezone')!=timezone):
                    complete=False
                for session in identified_sessions(SimpleNamespace(**row),snap_by_id):
                    id=session['workout_occurrence_id']
                    sessions[id]=(row,session)
            for week in (start,start+timedelta(days=7),start+timedelta(days=14)):
                if len(by_week[week])>1:raise LifecycleError('ambiguous_source_week')
                if len(by_week[week])!=1:complete=False
            # Execution snapshots remain even if their plan row is superseded or absent.
            plan_by_id={r['id']:r for r in plans}
            for snapshot in snapshots:
                row=plan_by_id.get(snapshot['plan_id'])
                session=dict(snapshot['payload']);session.update(workout_occurrence_id=snapshot['id'])
                if row is None:
                    complete=False
                    row=dict(id=snapshot['plan_id'],week_start=snapshot['week_start'],schedule_timezone=snapshot['schedule_timezone'],
                        placement_revision=snapshot['placement_revision'],payload={'program_template_id':snapshot['program_id']})
                # A frozen snapshot must not disagree with stored date/revision identity.
                if snapshot['scheduled_date'] is None or session.get('scheduled_date')!=snapshot['scheduled_date'].isoformat():
                    raise LifecycleError('frozen_occurrence_changed')
                if (snapshot['schedule_timezone']!=timezone or row['placement_revision']!=snapshot['placement_revision']):
                    raise LifecycleError('frozen_occurrence_changed')
                sessions[snapshot['id']]=(row,session)
            result=[]
            for id,(row,session) in sorted(sessions.items()):
                try:day=date.fromisoformat(session['scheduled_date'])
                except (KeyError,ValueError,TypeError):raise LifecycleError('source_date_unknown') from None
                if not start<=day<=end:raise LifecycleError('source_date_outside_window')
                program=row['payload'].get('program_template_id')
                mode='authored' if program in AUTHORED else row['payload'].get('mode')
                if mode not in ('authored','customized'):raise LifecycleError('source_mode_unknown')
                exercises=session.get('exercises') or []
                slots=tuple(e.get('exercise_occurrence_id') for e in exercises)
                if not slots or not all(slots) or len(slots)!=len(set(slots)):raise LifecycleError('source_slot_unknown')
                history=[r for r in relevant_logs if r['workout_occurrence_id']==id]
                effective=[r for r in history if r['voided_at'] is None and (r['set_kind'] or 'work')=='work' and r['parent_set_index'] is None]
                frozen=id in snap_by_id
                # Snapshot existence freezes the week even when all sets are undone.
                completed=all(type(e.get('sets')) is int and e['sets']>0 and
                    len([r for r in effective if r['exercise_occurrence_id']==e['exercise_occurrence_id']])>=e['sets'] for e in exercises)
                status=('completed' if completed else 'partial' if effective else 'started') if frozen else 'planned'
                result.append(CalendarOccurrence(subject,id,row['id'],row['week_start'],day,timezone,
                    row['placement_revision'],status,mode,content_hash(session),slots,False,content_hash((history,
                        [r for r in relevant_commands if r['workout_occurrence_id']==id],
                        [r for r in relevant_states if r['workout_occurrence_id']==id]))))
            return CalendarWindow(subject,timezone,start,end,revision,SOURCE_CONTRACT,tuple(result),complete)
