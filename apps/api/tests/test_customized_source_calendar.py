"""Actual source-shaped rows in disposable PostgreSQL; no #83 mutation."""
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from test_customized_postgres import pg,system


def seed_calendar(s):
    from app.models import WorkoutPlan
    from research.m4c3a.fixtures import demo_context
    week=demo_context().week_start
    rows=[]
    with s.unit.account(s.actors['a'].subject) as conn:
        for offset,dayoffset in ((-7,6),(0,0),(7,1)):
            monday=week+timedelta(days=offset);day=monday+timedelta(days=dayoffset)
            row=dict(id=uuid4().hex,user_id=s.actors['a'].subject,week_start=monday,placement_revision=1,
                schedule_timezone='America/New_York',split='full_body',phase='synthetic-test-only',
                payload={'program_template_id':'pure_bodybuilding_phase_1_full_body',
                    'schedule':{'mode':'selected_dates_v1','week_start':monday.isoformat(),'timezone':'America/New_York','selected_dates':[day.isoformat()]},
                    'sessions':[{'session_id':'original-synthetic-fixture','scheduled_date':day.isoformat(),'schedule_timezone':'America/New_York','placement_revision':1,
                        'exercises':[{'id':'same-synthetic-exercise','sets':1,'source_lineage':{'source_slot_id':str(i)}} for i in range(2)]}]})
            conn.execute(WorkoutPlan.__table__.insert().values(**row));rows.append(row)
    return rows


def window(s,key='a'):
    from research.m4c3a.fixtures import demo_context
    week=demo_context().week_start
    return s.source.read(s.actors[key].subject,'America/New_York',week-timedelta(days=7),week+timedelta(days=13))


def test_actual_plan_source_dates_dst_repeated_slots_account_filter_and_missing_coverage(system):
    s=system;rows=seed_calendar(s);w=window(s)
    assert w.complete and len(w.occurrences)==3
    assert [r.scheduled_date.isoformat() for r in w.occurrences] and {r.scheduled_date.isoformat() for r in w.occurrences}=={'2026-10-25','2026-10-26','2026-11-03'}
    assert all(len(r.source_slot_ids)==len(set(r.source_slot_ids))==2 for r in w.occurrences)
    assert window(s,'b').occurrences==() and not window(s,'b').complete
    snapshot=s.service.schedule.resolve(s.actors['a'].subject,'America/New_York')
    assert snapshot.source_kind=='synthetic' and s.source.source_verified is False
    # Read adapter must leave the original source payloads unchanged.
    from app.models import WorkoutPlan
    from sqlalchemy import select
    with s.unit.account(s.actors['a'].subject) as conn:
        persisted=[dict(r) for r in conn.execute(select(WorkoutPlan.__table__).where(WorkoutPlan.user_id==s.actors['a'].subject)).mappings()]
    assert {r['id']:r['payload'] for r in persisted}=={r['id']:r['payload'] for r in rows}


def test_source_effective_correction_undo_preserves_frozen_identity_and_freshness(system):
    from app.models import WorkoutOccurrence,WorkoutSetLog,WorkoutLogCommand
    from app.workout_identity import identified_sessions
    s=system;rows=seed_calendar(s);plan=rows[0]
    session=identified_sessions(SimpleNamespace(**plan))[0];occ=session['workout_occurrence_id']
    with s.unit.account(s.actors['a'].subject) as conn:
        conn.execute(WorkoutOccurrence.__table__.insert().values(id=occ,user_id=plan['user_id'],plan_id=plan['id'],
            week_start=plan['week_start'],scheduled_date=__import__('datetime').date.fromisoformat(session['scheduled_date']),
            schedule_timezone='America/New_York',placement_revision=1,session_slot=0,workout_id=session['session_id'],
            program_id=plan['payload']['program_template_id'],payload=session))
        for i,e in enumerate(session['exercises']):
            conn.execute(WorkoutSetLog.__table__.insert().values(id=uuid4().hex,user_id=plan['user_id'],workout_id=session['session_id'],
                workout_occurrence_id=occ,exercise_occurrence_id=e['exercise_occurrence_id'],primary_exercise_id=e['id'],exercise_id=e['id'],
                set_index=1,reps=1,weight=1,rpe=None,set_kind='work'))
    before=window(s);frozen=next(r for r in before.occurrences if r.occurrence_id==occ)
    assert frozen.status=='completed'
    with s.unit.account(plan['user_id']) as conn:
        conn.execute(text("UPDATE workout_set_logs SET voided_at=TIMESTAMP '2026-10-26 12:00:00',void_reason='synthetic undo' WHERE user_id=:s AND workout_occurrence_id=:o"),dict(s=plan['user_id'],o=occ))
    undone=window(s);after=next(r for r in undone.occurrences if r.occurrence_id==occ)
    assert after.status=='started' and after.scheduled_date==frozen.scheduled_date
    assert after.source_slot_ids==frozen.source_slot_ids and undone.source_revision!=before.source_revision
    # A retained amendment/command changes freshness even with no effective sets.
    with s.unit.account(plan['user_id']) as conn:
        conn.execute(WorkoutLogCommand.__table__.insert().values(id=uuid4().hex,user_id=plan['user_id'],command_id=uuid4().hex,
            request_digest='synthetic',workout_occurrence_id=occ,exercise_occurrence_id=session['exercises'][0]['exercise_occurrence_id'],
            response={'synthetic':True},undone_at=__import__('datetime').datetime(2026,10,26,12)))
    assert window(s).source_revision!=undone.source_revision


def test_conflicting_active_source_weeks_and_frozen_placement_fail_closed(system):
    from app.models import WorkoutPlan
    from app.customized_lifecycle_models import LifecycleError
    s=system;rows=seed_calendar(s);duplicate=deepcopy(rows[0]);duplicate['id']=uuid4().hex
    with s.unit.account(duplicate['user_id']) as conn:conn.execute(WorkoutPlan.__table__.insert().values(**duplicate))
    with pytest.raises(LifecycleError,match='ambiguous_source_week'):window(s)


def test_frozen_snapshot_placement_revision_mismatch_is_rejected(system):
    from app.models import WorkoutOccurrence
    from app.workout_identity import identified_sessions
    from app.customized_lifecycle_models import LifecycleError
    s=system;row=seed_calendar(s)[0];session=identified_sessions(SimpleNamespace(**row))[0]
    with s.unit.account(row['user_id']) as conn:
        conn.execute(WorkoutOccurrence.__table__.insert().values(id=session['workout_occurrence_id'],user_id=row['user_id'],plan_id=row['id'],
            week_start=row['week_start'],scheduled_date=__import__('datetime').date.fromisoformat(session['scheduled_date']),
            schedule_timezone='America/New_York',placement_revision=2,session_slot=0,workout_id=session['session_id'],
            program_id=row['payload']['program_template_id'],payload=session))
    with pytest.raises(LifecycleError,match='frozen_occurrence_changed'):window(s)


def test_empty_or_mismatched_dated_plan_is_not_complete_source_coverage(system):
    from app.models import WorkoutPlan
    s=system;rows=seed_calendar(s)
    with s.unit.account(rows[0]['user_id']) as conn:
        for row in rows:
            payload=deepcopy(row['payload']);payload['sessions']=[];payload['schedule']['selected_dates']=[]
            conn.execute(WorkoutPlan.__table__.update().where(WorkoutPlan.id==row['id']).values(payload=payload))
    assert window(s).complete is False
