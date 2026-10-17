"""Narrow PR98 coverage/query corrections on explicitly disposable PostgreSQL."""
from copy import deepcopy
from datetime import datetime,timedelta
from uuid import uuid4
import pytest
from sqlalchemy import text
from test_customized_postgres import pg,system
from test_customized_source_calendar import seed_calendar,window


def legacy_log(s,*,workout_id='unrelated-old',created=datetime(2010,1,1),amended=None,voided=None):
    from app.models import WorkoutSetLog
    with s.unit.account(s.actors['a'].subject) as conn:
        conn.execute(WorkoutSetLog.__table__.insert().values(id=uuid4().hex,user_id=s.actors['a'].subject,
            workout_id=workout_id,primary_exercise_id='synthetic',exercise_id='synthetic',set_index=1,reps=1,weight=1,
            created_at=created,amended_at=amended,voided_at=voided))


def test_unrelated_old_legacy_does_not_poison_clean_window_or_freshness(system):
    s=system;seed_calendar(s);before=window(s)
    legacy_log(s)
    after=window(s)
    assert after.complete and after.source_revision==before.source_revision


@pytest.mark.parametrize('change',[dict(created=datetime(2026,10,25)),dict(amended=datetime(2026,11,20)),
    dict(voided=datetime(2026,10,26)),dict(workout_id='original-synthetic-fixture')])
def test_unbound_log_that_might_intersect_window_stays_unknown(system,change):
    s=system;seed_calendar(s);legacy_log(s,**change)
    w=window(s);assert not w.complete
    assert any('unbound_log' in c.reasons for c in w.coverage)


def test_new_account_has_observed_absence_not_authoritative_rest_weeks(system):
    w=window(system)
    assert w.occurrences==() and not w.complete
    assert len(w.coverage)==3
    assert all(c.state=='observed_empty' and c.authoritative is False for c in w.coverage)
    assert all('negative_coverage_not_defined_by_pr83' in c.reasons for c in w.coverage)


def test_empty_neighbors_are_distinct_from_malformed_or_unknown_coverage(system):
    from app.models import WorkoutPlan
    s=system;rows=seed_calendar(s)
    # Keep just the current week active; supersede both neighbors as #83 does.
    with s.unit.account(rows[0]['user_id']) as conn:
        for row in (rows[0],rows[2]):
            payload=deepcopy(row['payload']);payload['schedule']['mode']='selected_dates_superseded_v1'
            conn.execute(WorkoutPlan.__table__.update().where(WorkoutPlan.id==row['id']).values(payload=payload))
    w=window(s)
    assert [c.state for c in w.coverage]==['observed_empty','dated','observed_empty']
    assert not w.complete and len(w.occurrences)==1
    with s.unit.account(rows[0]['user_id']) as conn:
        payload=deepcopy(rows[1]['payload']);payload['sessions']=[]
        conn.execute(WorkoutPlan.__table__.update().where(WorkoutPlan.id==rows[1]['id']).values(payload=payload))
    w=window(s)
    assert w.coverage[1].state=='unknown' and 'malformed_dated_plan' in w.coverage[1].reasons


def test_legacy_session_state_relevance_is_bounded_but_late_updates_stay_unknown(system):
    from app.models import WorkoutSessionState
    s=system;seed_calendar(s);subject=s.actors['a'].subject;id=uuid4().hex
    with s.unit.account(subject) as conn:
        conn.execute(WorkoutSessionState.__table__.insert().values(id=id,user_id=subject,workout_id='unrelated-old',
            primary_exercise_id='synthetic',exercise_id='synthetic',planned_sets=1,planned_reps_min=1,planned_reps_max=1,
            planned_weight=1,recommended_reps_min=1,recommended_reps_max=1,recommended_weight=1,last_guidance='synthetic',
            created_at=datetime(2010,1,1),updated_at=datetime(2010,1,1)))
    assert window(s).complete
    with s.unit.account(subject) as conn:
        conn.execute(WorkoutSessionState.__table__.update().where(WorkoutSessionState.id==id).values(updated_at=datetime(2026,11,20)))
    w=window(s)
    assert not w.complete and all('unbound_session_state' in c.reasons for c in w.coverage)


def test_known_occurrence_keeps_old_receipts_late_corrections_and_voids(system):
    from app.models import WorkoutOccurrence,WorkoutSetLog
    from app.workout_identity import identified_sessions
    from types import SimpleNamespace
    from datetime import date
    s=system;row=seed_calendar(s)[0];session=identified_sessions(SimpleNamespace(**row))[0]
    subject=row['user_id'];occ=session['workout_occurrence_id'];exercise=session['exercises'][0]
    parent=uuid4().hex;child=uuid4().hex
    with s.unit.account(subject) as conn:
        conn.execute(WorkoutOccurrence.__table__.insert().values(id=occ,user_id=subject,plan_id=row['id'],week_start=row['week_start'],
            scheduled_date=date.fromisoformat(session['scheduled_date']),schedule_timezone='America/New_York',placement_revision=1,
            session_slot=0,workout_id=session['session_id'],program_id=row['payload']['program_template_id'],payload=session))
        values=dict(user_id=subject,workout_id=session['session_id'],workout_occurrence_id=occ,
            exercise_occurrence_id=exercise['exercise_occurrence_id'],primary_exercise_id=exercise['id'],exercise_id=exercise['id'],
            set_index=1,reps=1,weight=1,set_kind='work')
        conn.execute(WorkoutSetLog.__table__.insert().values(**values,id=parent,created_at=datetime(2010,1,1)))
    before=window(s)
    with s.unit.account(subject) as conn:
        conn.execute(WorkoutSetLog.__table__.update().where(WorkoutSetLog.id==parent).values(voided_at=datetime(2030,1,1)))
        conn.execute(WorkoutSetLog.__table__.insert().values(**values,id=child,created_at=datetime(2030,1,1),supersedes_id=parent))
    after=window(s)
    assert before.source_revision!=after.source_revision
    assert next(r for r in after.occurrences if r.occurrence_id==occ).status=='partial'
    assert s.source.source_verified is False
    # A corrupt connected cycle must not masquerade as two effective records.
    from app.customized_lifecycle_models import LifecycleError
    with pytest.raises(LifecycleError,match='source_amendment_cycle'):
        with s.unit.account(subject) as conn:
            conn.execute(WorkoutSetLog.__table__.update().where(WorkoutSetLog.id==parent).values(supersedes_id=child))
            window(s)
