# Gold Constraint Preservation And Multi-Day Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prove weak-point preservation and bounded removal under constrained time/frequency, then expand the adaptive-gold sample from one oversized session into authored multi-day doctrine.

**Architecture:** Keep the current adaptive-gold loader boundary and scheduler runtime path. Add deterministic scheduler prioritization based on canonical slot-role metadata so low time budgets and compressed day selection preserve weak-point work while reducing lower-priority slots first. Then reshape the adaptive-gold authored template into multiple days within the same first week so frequency compression can be tested honestly through the existing loader/runtime path.

**Tech Stack:** FastAPI API tests, Python core-engine scheduler/runtime, Pydantic adaptive-gold schemas, pytest with SQLite temp DBs.

---

### Task 1: Add scheduler tests for bounded time-cap removal and weak-point-preserving frequency compression

**Files:**
- Modify: `packages/core-engine/tests/test_scheduler.py`

**Step 1: Write the failing tests**
- Add one scheduler test proving low `session_time_budget_minutes` keeps `weak_point` slots while dropping `isolation`/`accessory` slots first.
- Add one scheduler test proving `days_available=2` on a 3-session template preserves the session containing `weak_point` slots.

**Step 2: Run test to verify it fails**
Run: `cd packages/core-engine && /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_scheduler.py -k 'weak_point_preservation' -v`
Expected: FAIL because scheduler currently truncates by position and does not score weak-point sessions when history is empty.

**Step 3: Write minimal implementation**
- Add optional `slot_role` propagation/use in scheduler scoring.
- For session caps, rank exercises by role priority, keep highest-priority items, then restore authored order.
- For session selection with no history targets, seed priority targets from `weak_point` slot roles so compressed-day selection can preserve those sessions.

**Step 4: Run tests to verify they pass**
Run the same scheduler tests.

### Task 2: Broaden adaptive gold into authored multi-day doctrine

**Files:**
- Modify: `programs/gold/adaptive_full_body_gold_v0_1.json`
- Modify: `apps/api/tests/test_program_loader.py`
- Modify: `apps/api/tests/test_program_catalog_and_selection.py`
- Modify: `apps/api/tests/test_workout_session_state.py`

**Step 1: Write the failing tests**
- Loader test should expect multiple adaptive-gold sessions/days from the first week.
- API tests should search across sessions for hinge/weak-point/arm slots instead of assuming everything lives in session 1.
- Add a focused API test proving `days_available=2` preserves the authored weak-point day on adaptive gold.
- Add a focused API test proving low time budget retains weak-point slots while boundedly dropping lower-priority slots on the affected session.

**Step 2: Run tests to verify they fail**
Run focused loader/API tests for adaptive-gold multi-day and constraint-preservation behavior.

**Step 3: Write minimal implementation**
- Split the adaptive-gold first week into 3 authored days while keeping the existing substitution-proven compounds on day 1.
- Move hinge/arm/weak-point work onto days 2 and 3.
- Preserve canonical ids and existing session order expectations where possible.

**Step 4: Run tests to verify they pass**
Run focused adaptive-gold loader/API/workout tests.

### Task 3: Update docs with new current-state truth

**Files:**
- Modify: `docs/archive/ai-handoffs/GPT5_MINI_EXECUTION_BACKLOG.md`
- Modify: `docs/archive/ai-handoffs/GPT5_MINI_HANDOFF.md`
- Modify: `docs/audits/Master_Plan_Checkmark_Audit.md`
- Modify: `docs/archive/ai-handoffs/CODEX_5_3_PASSOFF_PROMPT.md`

**Step 1: Update evidence**
- Record that adaptive gold is now multi-day authored doctrine.
- Record that scheduler preserves weak-point work under constrained time/frequency.

**Step 2: Verification**
Run the focused scheduler and adaptive-gold suites, then remove temp SQLite files.
