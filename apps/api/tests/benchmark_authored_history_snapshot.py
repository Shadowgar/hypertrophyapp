"""Run with an explicit verified disposable PostgreSQL environment; no defaults.

python tests/benchmark_authored_history_snapshot.py --phase before --output DIR
Run again with --phase after against the SAME fixtures/DB after the code change.
"""
import argparse
from copy import deepcopy
from datetime import date, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import statistics
import time
from uuid import uuid4

from test_authored_history_snapshot import multi_plan, add_history, CONTEXT
from test_authored_load_intelligence import SessionLocal, engine, User, WorkoutPlan, WorkoutOccurrence, WorkoutSetLog
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from app.main import app
from auth_test_helpers import create_access_token
from app.security import hash_password
from app import workout_load_state as state


def seed():
    fixtures = []
    for size in (25, 100, 250):
        uid = str(uuid4())
        with SessionLocal() as db:
            db.add(User(id=uid, email=f"issue80-{size}-{uid}@example.com", name="Synthetic history benchmark",
                password_hash=hash_password("Synthetic-Issue80-Only!"),
                selected_program_id="pure_bodybuilding_phase_1_full_body", equipment_profile=[]))
            db.commit()
        session = multi_plan(uid, performed_date=date.today(), exercises=6)
        add_history(uid, session, size)
        with SessionLocal() as db:
            db.add(WorkoutOccurrence(id=session["workout_occurrence_id"], user_id=uid,
                plan_id=db.query(WorkoutPlan).filter_by(user_id=uid).one().id,
                week_start=date.today()-timedelta(days=date.today().weekday()), scheduled_date=date.today(),
                session_slot=session["session_slot"], workout_id=session["session_id"],
                program_id="pure_bodybuilding_phase_1_full_body", payload=deepcopy(session)))
            db.flush()
            for ex in session["exercises"]:
                db.add(WorkoutSetLog(user_id=uid, workout_id=session["session_id"],
                    workout_occurrence_id=session["workout_occurrence_id"], exercise_occurrence_id=ex["exercise_occurrence_id"],
                    primary_exercise_id=ex["id"], exercise_id=ex["id"], set_index=1, set_kind="work",
                    reps=12, weight=40, rpe=9, created_at=datetime.now(),
                    replay_context={"version":2,"load_intelligence":{"load_context":deepcopy(CONTEXT)}}))
            db.commit()
            email = db.get(User, uid).email
        fixtures.append({"user_id":uid,"email":email,"history_workouts":size,"exercises":6,
            "workout_occurrence_id":session["workout_occurrence_id"],"token":create_access_token(uid)})
    return fixtures


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before","after"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=3)
    args = parser.parse_args()
    assert engine.dialect.name == "postgresql" and os.environ.get("M2A_POSTGRES_ISOLATED") == "1"
    assert args.samples >= 3
    root = args.output.resolve(strict=True)
    assert root.is_relative_to(Path(os.environ["CI_TEST_ROOT"]).resolve(strict=True))
    with engine.connect() as db:
        assert db.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0022_authored_load_states"
    fixture_file = root / "benchmark-fixtures-private.json"
    if not fixture_file.exists():
        assert args.phase == "before"
        fixture_file.write_text(json.dumps(seed()))
        fixture_file.chmod(0o600)
    fixtures = json.loads(fixture_file.read_text())
    expected_file = root / "benchmark-responses-private.json"
    expected = json.loads(expected_file.read_text()) if args.phase == "after" else {}
    observations, active = [], {}
    original = state._all_groups
    def measured(db, user):
        result = original(db, user)
        active["full_history_reconstructions"] += 1
        active["history_exposures_summarized"] += len(result)
        return result
    def query(_conn, _cursor, sql, *_args):
        active["sql_queries"] += 1
        compact = " ".join(sql.lower().split())
        if "from workout_set_logs join workout_occurrences" in compact or (
                "from workout_occurrences" in compact and "program_id in" in compact):
            active["history_sql_queries"] += 1
    state._all_groups = measured
    try:
        with TestClient(app) as client:
            for fixture in fixtures:
                headers = {"Authorization":"Bearer "+fixture["token"]}
                for route in ("today","progress","summary"):
                    path = "/workout/today" if route == "today" else f"/workout/{fixture['workout_occurrence_id']}/{route}"
                    active.update(full_history_reconstructions=0,history_exposures_summarized=0,sql_queries=0,history_sql_queries=0)
                    warm = client.get(path, headers=headers)
                    assert warm.status_code == 200, warm.text
                    key = f"{fixture['history_workouts']}:{route}"
                    if args.phase == "before": expected[key] = warm.json()
                    else: assert warm.json() == expected[key], key
                    for sample in range(args.samples):
                        active.update(full_history_reconstructions=0,history_exposures_summarized=0,sql_queries=0,history_sql_queries=0)
                        event.listen(engine,"before_cursor_execute",query)
                        start = time.perf_counter()
                        try: response = client.get(path,headers=headers)
                        finally:
                            elapsed = (time.perf_counter()-start)*1000
                            event.remove(engine,"before_cursor_execute",query)
                        assert response.status_code == 200, response.text
                        assert response.json() == expected[key], key
                        observations.append({"history_workouts":fixture["history_workouts"],"exercises":6,
                            "route":route,"sample":sample,"latency_ms":elapsed,**active})
    finally: state._all_groups = original
    if args.phase == "before":
        expected_file.write_text(json.dumps(expected,sort_keys=True));expected_file.chmod(0o600)
    summaries=[]
    for fixture in fixtures:
        for route in ("today","progress","summary"):
            rows=[x for x in observations if x["history_workouts"]==fixture["history_workouts"] and x["route"]==route]
            summaries.append({"history_workouts":fixture["history_workouts"],"route":route,
                "median_latency_ms":round(statistics.median(x["latency_ms"] for x in rows),2),
                **{key:rows[0][key] for key in ("sql_queries","history_sql_queries","full_history_reconstructions","history_exposures_summarized")}})
    report={"phase":args.phase,"samples":args.samples,"fixtures_sha256":hashlib.sha256(fixture_file.read_bytes()).hexdigest(),
        "equivalent_full_responses":True,"summary":summaries,"observations":observations}
    root.joinpath(f"benchmark-{args.phase}.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!="observations"},indent=2))


if __name__ == "__main__": run()
