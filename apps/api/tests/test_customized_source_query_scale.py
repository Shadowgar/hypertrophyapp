"""Real PostgreSQL query-plan qualification; never a wall-clock CI SLA."""
import json
import os
import statistics
import time
from pathlib import Path
from sqlalchemy import event,text
from test_customized_postgres import pg,system
from test_customized_source_calendar import seed_calendar,window


def populate_history(s):
    subject=s.actors['a'].subject
    with s.unit.account(subject) as conn:
        # 1,500 workouts / 500 weeks / 30,000 set rows (~10 years at3/week),
        # plus3,000 old unbound receipts and3,000 commands/states each.
        conn.execute(text("""INSERT INTO workout_plans(id,user_id,week_start,placement_revision,schedule_timezone,split,phase,payload,created_at)
            SELECT :s||'-p-'||n,:s,DATE '2000-01-03'+n*7,1,'America/New_York','full_body','synthetic',
            '{"schedule":{"mode":"selected_dates_v1"},"sessions":[]}'::json,TIMESTAMP '2010-01-01' FROM generate_series(0,499) n"""),dict(s=subject))
        conn.execute(text("""INSERT INTO workout_occurrences(id,user_id,plan_id,week_start,scheduled_date,schedule_timezone,placement_revision,
            session_slot,workout_id,program_id,payload,created_at)
            SELECT :s||'-o-'||n,:s,:s||'-p-'||(n/3),DATE '2000-01-03'+(n/3)*7,DATE '2000-01-03'+(n/3)*7+(n%3)*2,
            'America/New_York',1,n%3,'old-synthetic','synthetic','{}'::json,TIMESTAMP '2010-01-01' FROM generate_series(0,1499) n"""),dict(s=subject))
        conn.execute(text("""INSERT INTO workout_set_logs(id,user_id,workout_id,workout_occurrence_id,exercise_occurrence_id,
            primary_exercise_id,exercise_id,set_index,reps,weight,created_at)
            SELECT :s||'-l-'||n,:s,'old-synthetic',:s||'-o-'||(n/20),'e'||(n%2),'synthetic','synthetic',n%20+1,1,1,
            TIMESTAMP '2010-01-01' FROM generate_series(0,29999) n"""),dict(s=subject))
        conn.execute(text("""INSERT INTO workout_set_logs(id,user_id,workout_id,primary_exercise_id,exercise_id,set_index,reps,weight,created_at)
            SELECT :s||'-legacy-'||n,:s,'unrelated-old','synthetic','synthetic',1,1,1,TIMESTAMP '2010-01-01'
            FROM generate_series(0,2999) n"""),dict(s=subject))
        conn.execute(text("""INSERT INTO workout_log_commands(id,user_id,command_id,request_digest,workout_occurrence_id,
            exercise_occurrence_id,response,created_at)
            SELECT :s||'-c-'||n,:s,'old-c-'||n,'synthetic',:s||'-o-'||(n/2),'e'||(n%2),'{}'::json,TIMESTAMP '2010-01-01'
            FROM generate_series(0,2999) n"""),dict(s=subject))
        conn.execute(text("""INSERT INTO workout_session_states(id,user_id,workout_id,workout_occurrence_id,exercise_occurrence_id,
            primary_exercise_id,exercise_id,planned_sets,planned_reps_min,planned_reps_max,planned_weight,completed_sets,
            total_logged_reps,total_logged_weight,set_history,remaining_sets,recommended_reps_min,recommended_reps_max,recommended_weight,
            last_guidance,created_at,updated_at)
            SELECT :s||'-state-'||n,:s,'old-synthetic',:s||'-o-'||(n/2),'e'||(n%2),'synthetic','synthetic',1,1,1,1,0,0,0,
            '[]'::json,1,1,1,1,'synthetic',TIMESTAMP '2010-01-01',TIMESTAMP '2010-01-01' FROM generate_series(0,2999) n"""),dict(s=subject))
    # Disposable statistics only, no source mutation or planner switches.
    with s.engine.begin() as conn:
        for table in ('workout_plans','workout_occurrences','workout_set_logs','workout_log_commands','workout_session_states'):
            conn.execute(text('ANALYZE '+table))


def test_source_queries_scale_with_window_not_lifetime(system):
    from app.models import WorkoutOccurrence,WorkoutSetLog
    from app.workout_identity import identified_sessions
    from types import SimpleNamespace
    from datetime import date
    from uuid import uuid4
    s=system;row=seed_calendar(s)[0];session=identified_sessions(SimpleNamespace(**row))[0]
    with s.unit.account(row['user_id']) as conn:
        conn.execute(WorkoutOccurrence.__table__.insert().values(id=session['workout_occurrence_id'],user_id=row['user_id'],plan_id=row['id'],
            week_start=row['week_start'],scheduled_date=date.fromisoformat(session['scheduled_date']),schedule_timezone='America/New_York',
            placement_revision=1,session_slot=0,workout_id=session['session_id'],program_id=row['payload']['program_template_id'],payload=session))
        for exercise in session['exercises']:
            conn.execute(WorkoutSetLog.__table__.insert().values(id=uuid4().hex,user_id=row['user_id'],workout_id=session['session_id'],
                workout_occurrence_id=session['workout_occurrence_id'],exercise_occurrence_id=exercise['exercise_occurrence_id'],
                primary_exercise_id=exercise['id'],exercise_id=exercise['id'],set_index=1,reps=1,weight=1))
    before=window(s);small=[]
    for _ in range(3):
        start=time.perf_counter();window(s);small.append((time.perf_counter()-start)*1000)
    populate_history(s)
    measure(s,before,small)


def measure(s,before,small):
    """Also supports read-only remeasurement without reseeding large history."""
    captured=[]
    def capture(conn,cursor,statement,parameters,context,many):
        if statement.lstrip().startswith(('SELECT','WITH')):
            captured.append((statement,parameters,cursor.rowcount))
    event.listen(s.engine,'after_cursor_execute',capture)
    try:
        started=time.perf_counter();after=window(s);locked_read_ms=(time.perf_counter()-started)*1000
    finally:event.remove(s.engine,'after_cursor_execute',capture)
    assert after==before  # Unrelated old records cannot change coverage/freshness.
    assert sum(max(0,v[2]) for v in captured)<32
    plans=[]
    with s.unit.account(s.actors['a'].subject) as conn:
        for sql,params,count in captured:
            if 'FROM users' in sql:continue
            value=conn.exec_driver_sql('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+sql,params).scalar_one()[0]
            def nodes(node):
                yield node
                for child in node.get('Plans',[]):yield from nodes(child)
            scan_nodes=[v for v in nodes(value['Plan']) if 'Scan' in v['Node Type']]
            examined=sum((v.get('Actual Rows',0)+v.get('Rows Removed by Filter',0))*v.get('Actual Loops',1) for v in scan_nodes)
            assert examined<128,(examined,value)
            plans.append(dict(returned_rows=count,examined_scan_rows=examined,planning_ms=value['Planning Time'],
                execution_ms=value['Execution Time'],index_names=sorted({v['Index Name'] for v in nodes(value['Plan']) if 'Index Name' in v})))
    large=[]
    for _ in range(3):
        start=time.perf_counter();window(s);large.append((time.perf_counter()-start)*1000)
    report=dict(synthetic_old_plans=500,synthetic_old_occurrences=1500,synthetic_bound_sets=30000,synthetic_unbound_old_sets=3000,
        synthetic_old_commands=3000,synthetic_old_states=3000,source_queries=len(plans),
        rows_returned=sum(max(0,p['returned_rows']) for p in plans),small_median_ms=statistics.median(small),
        large_median_ms=statistics.median(large),captured_account_read_ms=locked_read_ms,query_plans=plans,
        source_verified=False,complete=after.complete,postgres_only=True)
    path=os.environ.get('C3B2B_SOURCE_QUERY_REPORT')
    if path:
        target=Path(path)
        assert target.parent.resolve().is_relative_to(Path('/tmp')) and not target.is_symlink()
        target.write_text(json.dumps(report,indent=2)+'\n')
    return report
