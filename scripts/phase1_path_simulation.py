#!/usr/bin/env python3
"""
Minimal Phase 1 user path simulation. Run against a live API.

Usage:
  API_BASE_URL=http://localhost:8000 python scripts/phase1_path_simulation.py
  Or with default http://localhost:8000:
  python scripts/phase1_path_simulation.py

Requires: requests (pip install requests)
"""
from __future__ import annotations

import os
import sys
import time
from datetime import date, timedelta

try:
    import requests
except ImportError:
    print("Requires: pip install requests")
    sys.exit(1)

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
CANONICAL_PROGRAM_ID = "pure_bodybuilding_phase_1_full_body"
# Unique per run so we can re-run without wiping (timestamp avoids "Email already used")
RUN_ID = f"{date.today().isoformat().replace('-', '')}-{int(time.time())}-pathsim"
EMAIL = f"phase1-pathsim-{RUN_ID}@example.com"
PASSWORD = "Phase1PathSim1"

results: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def main() -> None:
    print(f"Phase 1 path simulation — BASE_URL={BASE_URL}")
    print()

    session = requests.Session()
    session.headers["Content-Type"] = "application/json"

    # 1. Create user
    r = session.post(f"{BASE_URL}/auth/register", json={"email": EMAIL, "password": PASSWORD, "name": "Phase1 PathSim"})
    if r.status_code != 200:
        step("1. Create user (POST /auth/register)", False, f"{r.status_code} {r.text[:200]}")
    else:
        step("1. Create user (POST /auth/register)", True)
        session.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    if not session.headers.get("Authorization"):
        print("\nAborting (no auth). Fix step 1 and re-run.")
        _report()
        sys.exit(1)

    # 2. Onboard program (POST /profile with program and preferences)
    profile_payload = {
        "name": "Phase1 PathSim",
        "age": 31,
        "weight": 82,
        "gender": "male",
        "split_preference": "full_body",
        "selected_program_id": CANONICAL_PROGRAM_ID,
        "training_location": "gym",
        "equipment_profile": ["barbell", "dumbbell", "bench", "machine", "cable"],
        "weak_areas": ["chest", "hamstrings"],
        "days_available": 5,
        "nutrition_phase": "maintenance",
        "calories": 2600,
        "protein": 180,
        "fat": 70,
        "carbs": 280,
    }
    r = session.post(f"{BASE_URL}/profile", json=profile_payload)
    if r.status_code != 200:
        step("2. Onboard program (POST /profile)", False, f"{r.status_code} {r.text[:200]}")
    else:
        j = r.json()
        step("2. Onboard program (POST /profile)", j.get("selected_program_id") == CANONICAL_PROGRAM_ID, j.get("selected_program_id") or "")

    # 3. Generate week
    r = session.post(f"{BASE_URL}/plan/generate-week", json={})
    if r.status_code != 200:
        step("3. Generate week (POST /plan/generate-week)", False, f"{r.status_code} {r.text[:200]}")
    else:
        j = r.json()
        sessions = j.get("sessions") or []
        step("3. Generate week (POST /plan/generate-week)", len(sessions) >= 1 and j.get("program_template_id") == CANONICAL_PROGRAM_ID, f"{len(sessions)} sessions")

    # 4. Fetch today's workout
    r = session.get(f"{BASE_URL}/workout/today")
    if r.status_code != 200:
        step("4. Fetch today's workout (GET /workout/today)", False, f"{r.status_code} {r.text[:200]}")
        _report()
        sys.exit(1)
    j = r.json()
    session_id = j.get("session_id")
    exercises = j.get("exercises") or []
    step("4. Fetch today's workout (GET /workout/today)", bool(session_id) and len(exercises) >= 1, f"session_id={session_id}, exercises={len(exercises)}")

    if not session_id or not exercises:
        print("\nAborting (no session or exercises). Fix step 4 and re-run.")
        _report()
        sys.exit(1)

    # 5 & 6. Log sets and complete workout (log at least one set per first two exercises to simulate “complete workout”)
    first_ex = exercises[0]
    ex_id = first_ex.get("id")
    primary_ex_id = first_ex.get("primary_exercise_id") or ex_id
    rep_range = first_ex.get("rep_range") or [10, 12]
    weight = float(first_ex.get("recommended_working_weight") or 20)
    num_working = len(first_ex.get("working_sets") or [{"reps": "10-12"}])
    all_log_ok = True
    for set_idx in range(1, min(num_working + 1, 4)):  # up to 3 sets for first exercise
        r = session.post(
            f"{BASE_URL}/workout/{session_id}/log-set",
            json={
                "primary_exercise_id": primary_ex_id,
                "exercise_id": ex_id,
                "set_index": set_idx,
                "reps": int(rep_range[0]),
                "weight": weight,
            },
        )
        if r.status_code != 200:
            step(f"5/6. Log set {set_idx} (POST /workout/.../log-set)", False, f"{r.status_code} {r.text[:150]}")
            all_log_ok = False
        else:
            step(f"5/6. Log set {set_idx} (POST /workout/.../log-set)", True)
    if all_log_ok and num_working >= 1:
        step("6. Complete workout (log sets)", True, f"logged {min(num_working, 3)} set(s) for first exercise")

    # 7. Weekly review (check-in then review)
    week_start = date.today() - timedelta(days=date.today().weekday())
    r = session.post(
        f"{BASE_URL}/weekly-checkin",
        json={
            "week_start": week_start.isoformat(),
            "body_weight": 82.0,
            "adherence_score": 4,
            "sleep_quality": 3,
            "stress_level": 2,
            "pain_flags": [],
            "notes": "path sim check-in",
        },
    )
    if r.status_code != 200:
        step("7a. Weekly check-in (POST /weekly-checkin)", False, f"{r.status_code} {r.text[:150]}")
    else:
        step("7a. Weekly check-in (POST /weekly-checkin)", True)

    r = session.post(
        f"{BASE_URL}/weekly-review",
        json={
            "body_weight": 82.0,
            "calories": 2600,
            "protein": 180,
            "fat": 70,
            "carbs": 280,
            "adherence_score": 4,
            "notes": "path sim weekly review",
        },
    )
    if r.status_code != 200:
        step("7b. Weekly review (POST /weekly-review)", False, f"{r.status_code} {r.text[:200]}")
    else:
        j = r.json()
        step("7b. Weekly review (POST /weekly-review)", j.get("status") == "review_logged", j.get("status") or "")

    # 8. Generate next week
    r = session.post(f"{BASE_URL}/plan/generate-week", json={})
    if r.status_code != 200:
        step("8. Generate next week (POST /plan/generate-week)", False, f"{r.status_code} {r.text[:200]}")
    else:
        j = r.json()
        step("8. Generate next week (POST /plan/generate-week)", j.get("program_template_id") == CANONICAL_PROGRAM_ID and len(j.get("sessions") or []) >= 1, f"{len(j.get('sessions') or [])} sessions")

    _report()


def _report() -> None:
    print()
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"--- Result: {passed}/{total} steps passed ---")
    failed = [(n, d) for n, ok, d in results if not ok]
    if failed:
        print("Failed steps:")
        for name, detail in failed:
            print(f"  - {name}: {detail}")
    print()


if __name__ == "__main__":
    main()
