# Live Workout Guidance Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move the remaining live workout guidance decision family out of `packages/core-engine/core_engine/intelligence.py` into one authoritative decision-family module while preserving deterministic traces and stable API behavior.

**Architecture:** Treat live workout guidance as its own decision family. The new owner should handle set-feedback interpretation, adjustment recommendation, guidance rationale/humanization, and session-guidance summaries. `intelligence.py` should retain only thin compatibility wrappers where external call signatures still matter. Routers stay unchanged unless imports or helper call sites need mechanical rewiring.

**Tech Stack:** Python, FastAPI API layer, `packages/core-engine`, pytest, structured `decision_trace` payloads

---

### Task 1: Freeze the current ownership and target functions

**Files:**
- Modify: `docs/current_state_decision_runtime_map.md`
- Inspect: `packages/core-engine/core_engine/intelligence.py`
- Inspect: `packages/core-engine/core_engine/decision_workout_session.py`

**Step 1: Confirm the target functions still live in `intelligence.py`**

Run:

```bash
rg -n "recommend_live_workout_adjustment|interpret_workout_set_feedback|summarize_workout_session_guidance|_resolve_workout_set_guidance|_workout_guidance_rationale|_humanize_workout_guidance" packages/core-engine/core_engine/intelligence.py
```

Expected: all target functions resolve in `intelligence.py`.

**Step 2: Confirm the authority map still marks live workout guidance as mixed ownership**

Run:

```bash
rg -n "live workout guidance|set feedback" docs/current_state_decision_runtime_map.md
```

Expected: authority map shows live workout guidance as the next extraction target.

**Step 3: Update the authority map once implementation lands**

After code changes, edit the row so the new decision-family module becomes authoritative and `intelligence.py` is marked as wrapper-only.

### Task 2: Write failing decision-family tests

**Files:**
- Create: `packages/core-engine/tests/test_decision_live_workout_guidance.py`
- Inspect: `packages/core-engine/tests/test_intelligence.py`
- Inspect: `packages/core-engine/tests/test_decision_workout_session.py`

**Step 1: Add focused tests for authoritative behavior**

Cover at least:
- `interpret_workout_set_feedback`
- `recommend_live_workout_adjustment`
- session-guidance summary output
- rationale/humanization output
- decision-trace propagation

**Step 2: Run the new tests first**

Run:

```bash
cd packages/core-engine && /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_decision_live_workout_guidance.py -v
```

Expected: failing tests that demonstrate the new module is not wired yet.

### Task 3: Create the authoritative decision-family module

**Files:**
- Create: `packages/core-engine/core_engine/decision_live_workout_guidance.py`
- Modify: `packages/core-engine/core_engine/__init__.py`

**Step 1: Move the core logic**

Implement the new authoritative module with:
- set-feedback interpretation
- adjustment recommendation
- guidance resolution
- rationale generation
- humanization helpers
- session guidance summary builders

**Step 2: Preserve trace behavior**

Keep or improve structured `decision_trace` payloads. Do not lose machine-readable fields that current callers or tests rely on.

**Step 3: Export the new module cleanly**

Expose the public surface from `__init__.py` if the package currently relies on package-level imports.

### Task 4: Reduce `intelligence.py` to compatibility wrappers

**Files:**
- Modify: `packages/core-engine/core_engine/intelligence.py`

**Step 1: Replace moved bodies with thin wrappers**

Each wrapper should delegate directly to `decision_live_workout_guidance.py`.

**Step 2: Remove duplicated helper internals**

Delete superseded internal bodies once callers are routed through the new owner.

**Step 3: Keep signature stability**

Do not break existing router or core-engine imports unless there is a clear package-level replacement already covered by tests.

### Task 5: Rewire tests and callers

**Files:**
- Modify: `packages/core-engine/tests/test_intelligence.py`
- Modify: any direct callers identified by `rg`

**Step 1: Keep backward-compatibility coverage**

Existing `intelligence.py` tests should continue to pass if wrappers remain public.

**Step 2: Add owner-module coverage**

New tests should assert the authoritative module directly.

### Task 6: Verify engine and API behavior

**Files:**
- Test: `packages/core-engine/tests/test_decision_live_workout_guidance.py`
- Test: `packages/core-engine/tests/test_intelligence.py`
- Test: `apps/api/tests/test_workout_logset_feedback.py`
- Test: `apps/api/tests/test_workout_session_state.py`
- Test: `apps/api/tests/test_workout_summary.py`

**Step 1: Run focused engine tests**

Run:

```bash
cd packages/core-engine && /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_decision_live_workout_guidance.py tests/test_intelligence.py -k "workout_set_feedback or live_workout_adjustment or workout_session_guidance" -v
```

Expected: PASS

**Step 2: Run focused API regressions**

Run:

```bash
cd apps/api && TEST_DATABASE_URL=sqlite:///./test_local_live_guidance.sqlite3 /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_workout_logset_feedback.py tests/test_workout_session_state.py tests/test_workout_summary.py -v
```

Expected: PASS

**Step 3: Clean up temp database**

Run:

```bash
rm -f apps/api/test_local_live_guidance.sqlite3
```

Expected: file removed if created.

### Task 7: Update branch-state docs

**Files:**
- Modify: `docs/current_state_decision_runtime_map.md`
- Modify: `docs/archive/ai-handoffs/GPT5_MINI_HANDOFF.md`
- Modify: `docs/archive/ai-handoffs/GPT5_MINI_EXECUTION_BACKLOG.md`
- Modify: `docs/audits/Master_Plan_Checkmark_Audit.md`

**Step 1: Mark the new owner**

Record `decision_live_workout_guidance.py` as the authoritative module.

**Step 2: Update next-step guidance**

After this extraction, the next likely phase should be:
- richer persisted coaching-state schema
- deterministic SFR scoring layer

### Task 8: Final verification snapshot

**Files:**
- Inspect only

**Step 1: Review the final diff**

Run:

```bash
git diff --stat
```

Expected: only the intended decision-family and doc files changed.

**Step 2: Record completion**

Report:
- seam selected and why
- files changed
- focused tests passed
- whether `mini_validate` ran
- next likely seam
