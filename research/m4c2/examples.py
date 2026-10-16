"""Reproducible synthetic C2 review scenarios; no live-user or runtime defaults."""
from datetime import date, datetime, UTC

from core_engine.customized.models import CustomizedProfile, PlanningContext, CompletedSet, CompletedExposure, ExposureTarget
from core_engine.customized.pilot import plan_pilot
from .catalog import review_catalog
from .science import candidate_standard, gym_design


def synthetic_profile(*, gym=True, cap=60, cap_kind="flexible", status="current", equipment=None):
    supplied = ("machine", "dumbbell", "bodyweight", "floor", "bench", "leg_press_station", "chest_press_station",
        "row_station", "leg_curl_station", "pulldown_station", "calf_station") if gym else ("dumbbell", "bodyweight", "floor")
    return CustomizedProfile("c1-profile-v1", "customized", "synthetic-c2-review-consent", "hypertrophy", status,
        (date(2026, 10, 27), date(2026, 10, 29), date(2026, 11, 1)), "America/New_York", cap, cap_kind,
        supplied if equipment is None else equipment, "intermediate", (), (),
        ("gym_chest_press", "gym_leg_press", "gym_high_row", "gym_calf", "db_rear_fly") if gym else (), "supported" if gym else None,
        (("all_inputs", "synthetic-review-fixture"),), ())


def explicit_context():
    return PlanningContext("c1-context-v1", datetime(2026, 10, 26, 12, tzinfo=UTC), date(2026, 10, 26), None, None)


def synthetic_exposure():
    identity = next(e.load_identity for e in review_catalog().exercises if e.variant_id == "gym_chest_press")
    records = tuple(CompletedSet(f"synthetic-receipt-{i}", f"set-{i}", i, 0, "completed", "work", None,
        20, 12, "rir", 2, "acceptable", False, identity, 99) for i in (1, 2))
    return CompletedExposure("c1-exposure-v1", "synthetic-workout", "synthetic-chest", date(2026, 10, 25), identity,
        ExposureTarget(8, 12, "rir", 1, 3), (1, 2), True, records, "synthetic-effective-history")


def render_week(result):
    """Review artifact renderer only; never edits a program or history record."""
    lines = ["CANDIDATE FOR EXPERT REVIEW / NONPRESCRIPTIVE", "", "| Day | Proposed exercises (working sets × reps) | Estimated minutes |", "|---|---|---|"]
    for session in result.plan.sessions:
        exercises = "; ".join(f"{p.exercise.name}: {p.sets} × {p.reps_min}–{p.reps_max}" for p in session.exercises)
        d = session.duration.total_seconds
        lines.append(f"| {session.local_date} {session.emphasis} | {exercises} | {d.low/60:.1f}–{d.high/60:.1f} |")
    lines.extend(("", "| Region | Primary sets | Secondary involved sets | Unknown sets |", "|---|---:|---:|---:|"))
    lines.extend(f"| {r.region} | {r.primary_sets} | {r.secondary_sets} | {r.unknown_sets} |" for r in result.region_totals)
    return "\n".join(lines)


if __name__ == "__main__":
    result = plan_pilot(profile=synthetic_profile(), catalog=review_catalog(), standard=candidate_standard("current"),
        design=gym_design(), context=explicit_context(), simulate=True)
    print(render_week(result))
