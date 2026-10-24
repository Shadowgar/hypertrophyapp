from datetime import date, datetime
from core_engine import build_history_day_detail


def test_history_retains_actual_kind_effort_and_amendment_identity():
    rows = [dict(id='warm', workout_id='occ', exercise_id='cross_body', primary_exercise_id='cross_body', set_index=1, reps=8, weight=10, rpe=None, set_kind='warmup', parent_set_index=None, supersedes_id=None, created_at=datetime(2026,10,21,10), replay_context={}),
        dict(id='corrected', workout_id='occ', exercise_id='cross_body', primary_exercise_id='cross_body', set_index=1, reps=12, weight=20, rpe=None, set_kind='work', parent_set_index=None, supersedes_id='original', created_at=datetime(2026,10,21,10,3), replay_context={'actual_rir':2})]
    result=build_history_day_detail(day=date(2026,10,21),log_rows=rows,plans=[])
    sets=result['workouts'][0]['exercises'][0]['sets']
    assert [(s['id'],s['set_kind'],s['supersedes_id'],s['actual_rir']) for s in sets] == [('warm','warmup',None,None),('corrected','work','original',2)]
    assert all(s['rpe'] is None for s in sets)
