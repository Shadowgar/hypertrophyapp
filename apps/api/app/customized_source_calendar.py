"""Read-only projection of actual #83 source tables. No source-verification grant.

Pinned source: selected_date_plans.py@3f4927b and unchanged workout_identity/history
models. This reads real ORM table shapes on the candidate's account transaction;
#83 is unmerged, so source_verified is permanently False in this adapter.
"""
from collections import defaultdict
from datetime import UTC,date,datetime,time,timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from sqlalchemy import select,or_
from core_engine.customized.audit import content_hash
from .models import WorkoutPlan,WorkoutOccurrence,WorkoutSetLog,WorkoutLogCommand,WorkoutSessionState
from .workout_identity import identified_sessions
from .customized_staging_schedule import CalendarWindow,CalendarOccurrence,WeekCoverage,SOURCE_CONTRACT
from .customized_lifecycle_models import LifecycleError

AUTHORED=frozenset(('pure_bodybuilding_phase_1_full_body','pure_bodybuilding_phase_2_full_body'))


class SourceCalendarPort:
    source_verified=False
    def __init__(self,unit):self.unit=unit

    def read(self,subject,timezone,start,end):
        with self.unit.account(subject) as conn:
            try:
                lower=datetime.combine(start,time.min,tzinfo=ZoneInfo(timezone)).astimezone(UTC).replace(tzinfo=None)
            except (ZoneInfoNotFoundError,ValueError,TypeError):
                raise LifecycleError('invalid_calendar_context') from None
            # Query in the source's local week/date window, including inconsistent
            # date/week pairs so the projector can reject them rather than hide them.
            occurrence=WorkoutOccurrence.__table__;plan=WorkoutPlan.__table__
            occurrence_ids=select(occurrence.c.id).where(occurrence.c.user_id==subject,or_(
                occurrence.c.week_start.between(start,end),occurrence.c.scheduled_date.between(start,end)))
            def rows(statement):return [dict(r) for r in conn.execute(statement).mappings()]
            snapshots=rows(select(occurrence).where(occurrence.c.id.in_(occurrence_ids)))
            ids={r['id'] for r in snapshots}
            # A covered key lookup keeps wide JSON payloads out of the range
            # scan; fetch only the few window/retained-lineage plans by primary key.
            keys=set(conn.execute(select(plan.c.id).where(plan.c.user_id==subject,
                plan.c.week_start.between(start,end))).scalars())
            keys.update(r['plan_id'] for r in snapshots)
            plans=rows(select(plan).where(plan.c.user_id==subject,plan.c.id.in_(tuple(keys))))
            # Retain the complete connected amendment chain regardless of receipt
            # timestamp. UNION terminates even corrupt cycles; later integrity
            # checks fail closed for missing/foreign or cross-occurrence parents.
            log=WorkoutSetLog.__table__
            lineage=select(log.c.id,log.c.supersedes_id).where(log.c.user_id==subject,
                log.c.workout_occurrence_id.in_(occurrence_ids)).cte('calendar_log_lineage',recursive=True)
            adjacent=log.alias('amendment')
            lineage=lineage.union(select(adjacent.c.id,adjacent.c.supersedes_id).join(lineage,or_(
                adjacent.c.id==lineage.c.supersedes_id,adjacent.c.supersedes_id==lineage.c.id)).where(adjacent.c.user_id==subject))
            relevant_logs=rows(select(log).where(log.c.user_id==subject,log.c.id.in_(select(lineage.c.id))))
            by_log_id={r['id']:r for r in relevant_logs}
            for row in relevant_logs:
                parent=row['supersedes_id']
                if parent and (parent not in by_log_id or by_log_id[parent]['workout_occurrence_id']!=row['workout_occurrence_id']):
                    raise LifecycleError('source_amendment_identity_unknown')
                if row['workout_occurrence_id'] not in ids:
                    raise LifecycleError('source_amendment_identity_unknown')
            checked=set()
            for id in by_log_id:
                path=set();cursor=id
                while cursor and cursor not in checked:
                    if cursor in path:raise LifecycleError('source_amendment_cycle')
                    path.add(cursor);cursor=by_log_id[cursor]['supersedes_id']
                checked.update(path)
            def linked(model):
                table=model.__table__
                return rows(select(table).where(table.c.user_id==subject,table.c.workout_occurrence_id.in_(occurrence_ids)))
            relevant_commands=linked(WorkoutLogCommand);relevant_states=linked(WorkoutSessionState)
            references={r['workout_id'] for r in snapshots}
            for row in plans:
                sessions_payload=row['payload'].get('sessions') or []
                if isinstance(sessions_payload,list):
                    references.update(v['session_id'] for v in sessions_payload if isinstance(v,dict) and isinstance(v.get('session_id'),str))
            # A receipt timestamp is not a performed date. Old unrelated receipts
            # with no later change cannot intersect this source window. Reused
            # workout references and late corrections/voids stay ambiguous; no
            # upper timestamp cutoff discards a backdated amendment.
            state=WorkoutSessionState.__table__
            uncertain_log=select(log.c.id).where(log.c.user_id==subject,log.c.workout_occurrence_id.is_(None),or_(
                log.c.workout_id.in_(tuple(references)),log.c.created_at>=lower,log.c.amended_at>=lower,log.c.voided_at>=lower)).exists()
            uncertain_state=select(state.c.id).where(state.c.user_id==subject,state.c.workout_occurrence_id.is_(None),or_(
                state.c.workout_id.in_(tuple(references)),state.c.created_at>=lower,state.c.updated_at>=lower)).exists()
            unbound_log,unbound_state=conn.execute(select(uncertain_log,uncertain_state)).one()
            ambiguity=tuple(name for name,found in (('unbound_log',unbound_log),('unbound_session_state',unbound_state)) if found)
            evidence=dict(plans=plans,snapshots=snapshots,logs=relevant_logs,commands=relevant_commands,states=relevant_states)
            for rows in evidence.values():rows.sort(key=lambda r:r['id'])
            by_week=defaultdict(list);invalid_weeks=set();sessions={}
            snap_by_id={r['id']:SimpleNamespace(**r) for r in snapshots}
            for row in plans:
                payload=row['payload'];schedule=payload.get('schedule') or {}
                if schedule.get('mode','').startswith('selected_dates_superseded'):continue
                if not start<=row['week_start']<=end:
                    raise LifecycleError('source_date_outside_window')
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
                    invalid_weeks.add(row['week_start'])
                for session in identified_sessions(SimpleNamespace(**row),snap_by_id):
                    id=session['workout_occurrence_id']
                    sessions[id]=(row,session)
            for week in (start,start+timedelta(days=7),start+timedelta(days=14)):
                if len(by_week[week])>1:raise LifecycleError('ambiguous_source_week')
            # Execution snapshots remain even if their plan row is superseded or absent.
            plan_by_id={r['id']:r for r in plans}
            for snapshot in snapshots:
                row=plan_by_id.get(snapshot['plan_id'])
                session=dict(snapshot['payload']);session.update(workout_occurrence_id=snapshot['id'])
                if row is None:
                    invalid_weeks.add(snapshot['week_start'])
                    row=dict(id=snapshot['plan_id'],week_start=snapshot['week_start'],schedule_timezone=snapshot['schedule_timezone'],
                        placement_revision=snapshot['placement_revision'],payload={'program_template_id':snapshot['program_id']})
                # A frozen snapshot must not disagree with stored date/revision identity.
                if snapshot['scheduled_date'] is None or session.get('scheduled_date')!=snapshot['scheduled_date'].isoformat():
                    raise LifecycleError('frozen_occurrence_changed')
                if (snapshot['schedule_timezone']!=timezone or row['placement_revision']!=snapshot['placement_revision']):
                    raise LifecycleError('frozen_occurrence_changed')
                sessions[snapshot['id']]=(row,session)
            coverage=[]
            for week in (start,start+timedelta(days=7),start+timedelta(days=14)):
                reasons=list(ambiguity)
                if week in invalid_weeks:reasons.append('malformed_dated_plan')
                active=by_week[week]
                retained=[r for r in snapshots if r['week_start']==week]
                if not active and not retained and not reasons:
                    state='observed_empty';reasons.append('negative_coverage_not_defined_by_pr83')
                elif len(active)==1 and not reasons:
                    state='dated'
                else:
                    state='unknown'
                    if not active:reasons.append('missing_dated_source')
                coverage.append(WeekCoverage(week,state,tuple(reasons)))
            complete=all(c.state=='dated' for c in coverage)
            revision=content_hash(dict(version='pr98-source-window-v2',**evidence,coverage=tuple(coverage)))
            histories=defaultdict(list);commands=defaultdict(list);states=defaultdict(list)
            for row in relevant_logs:histories[row['workout_occurrence_id']].append(row)
            for row in relevant_commands:commands[row['workout_occurrence_id']].append(row)
            for row in relevant_states:states[row['workout_occurrence_id']].append(row)
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
                history=histories[id]
                effective=[r for r in history if r['voided_at'] is None and (r['set_kind'] or 'work')=='work' and r['parent_set_index'] is None]
                frozen=id in snap_by_id
                # Snapshot existence freezes the week even when all sets are undone.
                completed=all(type(e.get('sets')) is int and e['sets']>0 and
                    len([r for r in effective if r['exercise_occurrence_id']==e['exercise_occurrence_id']])>=e['sets'] for e in exercises)
                status=('completed' if completed else 'partial' if effective else 'started') if frozen else 'planned'
                result.append(CalendarOccurrence(subject,id,row['id'],row['week_start'],day,timezone,
                    row['placement_revision'],status,mode,content_hash(session),slots,False,content_hash((history,
                        commands[id],states[id]))))
            return CalendarWindow(subject,timezone,start,end,revision,SOURCE_CONTRACT,tuple(result),complete,tuple(coverage))
