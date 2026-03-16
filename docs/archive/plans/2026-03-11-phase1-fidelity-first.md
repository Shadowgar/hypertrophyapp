# Phase 1 Fidelity-First Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring the adaptive full-body gold runtime materially closer to the actual 5-day Pure Bodybuilding Phase 1 workbook/PDF doctrine while preserving deterministic adaptation, explainability, and current runtime boundaries.

**Architecture:** Keep the current canonical runtime architecture intact. First reconcile the current onboarding package against the actual workbook/PDF source, then strengthen the adaptive gold runtime artifact and loader/scheduler fidelity, and preserve deterministic compression from authored 5-day truth into constrained schedules only when required.

**Tech Stack:** FastAPI, Pydantic schemas, Python core-engine, Next.js/React web app, pytest, npm test

---

### Task 1: Reconcile the actual Phase 1 source against the onboarding package and runtime

**Files:**
- Create: `docs/plans/2026-03-11-phase1-fidelity-diff.md`
- Read: `reference/Pure Bodybuilding Phase 1 - Full Body Sheet.xlsx`
- Read: `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json`
- Read: `programs/gold/adaptive_full_body_gold_v0_1.json`
- Read: `reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf`
- Read: `reference/Hypertrophy Handbook (Jeff Nippard) (z-library.sk, 1lib.sk, z-lib.sk).pdf`

**Step 1: Write the fidelity diff document skeleton**

Include sections for:
- workbook/PDF to onboarding mismatches
- authored week structure
- authored 5-day session structure
- slot roles and weak-point semantics
- intro week / intensification / deload semantics
- exercise-library gaps
- runtime output gaps

**Step 2: Record the concrete gaps**

Write the exact mismatches between:
- workbook/PDF and onboarding package
- onboarding package and current adaptive-gold runtime

Minimum required output:
- authored day IDs and names
- concrete workbook/PDF day-level exercise differences
- which exercise families are missing or compressed
- which slot roles are currently dropped or weakened
- which week-role semantics are underrepresented

**Step 3: Verify the diff doc is grounded**

Run a quick sanity script or manual check to ensure all cited exercise/day/week IDs actually exist in the source files.

Run: `apps/api/.venv/bin/python -m json.tool programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json >/dev/null && apps/api/.venv/bin/python -m json.tool programs/gold/adaptive_full_body_gold_v0_1.json >/dev/null`
Expected: both commands succeed with exit code `0`

**Step 4: Commit**

```bash
git add docs/plans/2026-03-11-phase1-fidelity-diff.md
 git commit -m "docs: add phase1 fidelity gap audit"
```

### Task 2: Correct the authored source artifacts before runtime expansion

**Files:**
- Modify: `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json`
- Modify: `programs/gold/adaptive_full_body_gold_v0_1.json`
- Test: `apps/api/tests/test_program_loader.py`
- Test: `apps/api/tests/test_program_catalog_and_selection.py`

**Step 1: Write the failing loader/runtime tests**

Add tests that prove the runtime template preserves more of the corrected authored 5-day structure.

Examples:
```python
def test_adaptive_gold_runtime_preserves_five_authored_days():
    template = load_runtime_template("adaptive_full_body_gold_v0_1")
    assert len(template["authored_weeks"][0]["days"]) == 5


def test_adaptive_gold_runtime_preserves_weak_point_and_arms_day_role():
    template = load_runtime_template("adaptive_full_body_gold_v0_1")
    roles = [day.get("day_role") for day in template["authored_weeks"][0]["days"]]
    assert "weak_point_arms" in roles
```

**Step 2: Run the targeted tests to confirm failure**

Run: `cd apps/api && /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_program_loader.py -k 'adaptive_gold_runtime_preserves' -v`
Expected: FAIL because the current artifact/loader does not yet preserve the new fidelity expectations.

**Step 3: Update the authored source artifacts minimally**

Bring `pure_bodybuilding_phase_1_full_body.onboarding.json` and `adaptive_full_body_gold_v0_1.json` closer to the actual 5-day source.

Minimum implementation goals:
- preserve 5 authored days
- preserve explicit day roles where available
- preserve weak-point and arms day semantics
- preserve later-week authored differences where justified by source doctrine

**Step 4: Run the targeted tests to verify pass**

Run: `cd apps/api && /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_program_loader.py -k 'adaptive_gold_runtime_preserves' -v`
Expected: PASS

**Step 5: Commit**

```bash
git add programs/gold/adaptive_full_body_gold_v0_1.json apps/api/tests/test_program_loader.py apps/api/tests/test_program_catalog_and_selection.py
 git commit -m "feat: expand adaptive gold runtime toward authored 5-day doctrine"
```

### Task 3: Preserve corrected authored semantics through loader schemas

**Files:**
- Modify: `apps/api/app/adaptive_schema.py`
- Modify: `apps/api/app/template_schema.py`
- Modify: `apps/api/app/program_loader.py`
- Test: `apps/api/tests/test_program_loader.py`
- Test: `apps/api/tests/test_adaptive_gold_schema_contract.py`

**Step 1: Write the failing schema/loader tests**

Add tests for the richer authored semantics.

Examples:
```python
def test_adaptive_gold_loader_preserves_day_role_and_slot_role_metadata():
    template = load_runtime_template("adaptive_full_body_gold_v0_1")
    first_day = template["authored_weeks"][0]["days"][0]
    assert "day_role" in first_day
    assert any("slot_role" in slot for slot in first_day["slots"])


def test_adaptive_gold_schema_accepts_extended_authored_week_metadata():
    payload = build_adaptive_gold_fixture_with_day_roles()
    model = AdaptiveGoldProgramTemplate.model_validate(payload)
    assert model.authored_weeks[0].days[0].day_role is not None
```

**Step 2: Run tests to verify failure**

Run: `cd apps/api && /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_program_loader.py tests/test_adaptive_gold_schema_contract.py -k 'day_role or slot_role' -v`
Expected: FAIL because the schema/loader currently drop or ignore the richer metadata.

**Step 3: Implement minimal schema and loader support**

Add only the authored metadata needed for fidelity in this phase:
- day role
- preserved slot role
- richer authored week semantics only where source-backed

Do not invent a new generalized doctrine system.

**Step 4: Re-run tests**

Run: `cd apps/api && /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_program_loader.py tests/test_adaptive_gold_schema_contract.py -k 'day_role or slot_role' -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/api/app/adaptive_schema.py apps/api/app/template_schema.py apps/api/app/program_loader.py apps/api/tests/test_program_loader.py apps/api/tests/test_adaptive_gold_schema_contract.py
 git commit -m "feat: preserve richer authored gold metadata through loader"
```

### Task 4: Improve scheduler fidelity for authored 5-day truth and constrained compression

**Files:**
- Modify: `packages/core-engine/core_engine/scheduler.py`
- Test: `packages/core-engine/tests/test_scheduler.py`
- Test: `apps/api/tests/test_program_catalog_and_selection.py`

**Step 1: Write the failing scheduler tests**

Add tests that prove the scheduler starts from a more faithful 5-day authored truth and compresses downward intelligently.

Examples:
```python
def test_scheduler_preserves_weak_point_day_when_compressing_five_day_authored_source_to_four_days():
    plan = generate_week_plan(..., days_available=4)
    day_roles = [session.get("day_role") for session in plan["sessions"]]
    assert "weak_point_arms" in day_roles


def test_scheduler_reduces_lower_priority_accessories_before_primary_compounds_when_compressing():
    plan = generate_week_plan(..., days_available=3)
    all_roles = [slot["slot_role"] for session in plan["sessions"] for slot in session["exercises"]]
    assert "primary_compound" in all_roles
```

**Step 2: Run targeted tests and verify failure**

Run: `cd packages/core-engine && /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_scheduler.py -k 'five_day_authored_source_to_four_days or lower_priority_accessories' -v`
Expected: FAIL

**Step 3: Implement minimal scheduler changes**

Update scheduler behavior to:
- treat 5-day authored structure as the doctrinal source
- preserve day-role semantics where possible
- protect weak-point / arms intent during compression
- continue trimming lower-priority accessories first
- keep current deterministic mesocycle and SFR behavior intact

**Step 4: Re-run targeted tests**

Run: `cd packages/core-engine && /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_scheduler.py -k 'five_day_authored_source_to_four_days or lower_priority_accessories' -v`
Expected: PASS

**Step 5: Run adjacent API verification**

Run: `cd apps/api && TEST_DATABASE_URL=sqlite:///./test_local_phase1_fidelity.sqlite3 /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_program_catalog_and_selection.py -k 'adaptive_gold' -v`
Expected: PASS

**Step 6: Commit**

```bash
git add packages/core-engine/core_engine/scheduler.py packages/core-engine/tests/test_scheduler.py apps/api/tests/test_program_catalog_and_selection.py
 git commit -m "feat: improve scheduler fidelity for authored phase1 compression"
```

### Task 5: Surface the richer authored block clearly in the product

**Files:**
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/app/week/page.tsx`
- Modify: `apps/web/app/today/page.tsx`
- Modify: `apps/web/components/coaching-intelligence-panel.tsx`
- Test: `apps/web/tests/coaching.intelligence.routes.test.tsx`
- Test: `apps/web/tests/week.page.test.tsx`
- Test: `apps/web/tests/today.page.test.tsx`

**Step 1: Write the failing web tests**

Add tests that prove the UI shows richer authored block structure.

Examples:
```tsx
it('shows authored day role and week role in week view', async () => {
  render(<WeekPage />)
  expect(await screen.findByText(/weak point/i)).toBeInTheDocument()
})

it('shows session intent derived from authored doctrine on today page', async () => {
  render(<TodayPage />)
  expect(await screen.findByText(/session intent/i)).toBeInTheDocument()
})
```

**Step 2: Run targeted tests to verify failure**

Run: `cd apps/web && npm test -- --run tests/week.page.test.tsx tests/today.page.test.tsx tests/coaching.intelligence.routes.test.tsx`
Expected: FAIL because the richer authored semantics are not yet surfaced clearly.

**Step 3: Implement minimal UI changes**

Expose only source-backed items:
- week role
- day role / session intent
- weak-point / arms emphasis when present
- clearer explanation of why the week looks the way it does

Do not invent unsupported analytics or fake AI messaging.

**Step 4: Re-run targeted tests**

Run: `cd apps/web && npm test -- --run tests/week.page.test.tsx tests/today.page.test.tsx tests/coaching.intelligence.routes.test.tsx`
Expected: PASS

**Step 5: Run broader web suite**

Run: `cd apps/web && npm test -- --run`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/web/lib/api.ts apps/web/app/week/page.tsx apps/web/app/today/page.tsx apps/web/components/coaching-intelligence-panel.tsx apps/web/tests/coaching.intelligence.routes.test.tsx apps/web/tests/week.page.test.tsx apps/web/tests/today.page.test.tsx
 git commit -m "feat: surface authored phase1 block structure in web app"
```

### Task 6: Update docs and release-readiness evidence

**Files:**
- Modify: `docs/Master_Plan.md`
- Modify: `docs/archive/ai-handoffs/GPT5_MINI_HANDOFF.md`
- Modify: `docs/archive/ai-handoffs/GPT5_MINI_EXECUTION_BACKLOG.md`
- Modify: `docs/audits/Master_Plan_Checkmark_Audit.md`
- Modify: `docs/current_state_decision_runtime_map.md`
- Modify: `docs/DOCUMENTATION_STATUS.md`

**Step 1: Document what changed**

Update the source-of-truth docs to reflect:
- the fidelity-first shift in immediate priority
- why this is not a divergence from the deterministic plan
- what is now validated about the gold full-body path

**Step 2: Run final focused verification for the phase batch**

Run:
- `cd packages/core-engine && /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_scheduler.py tests/test_generation.py -q`
- `cd apps/api && TEST_DATABASE_URL=sqlite:///./test_local_phase1_fidelity_docs.sqlite3 /home/rocco/hypertrophyapp/apps/api/.venv/bin/python -m pytest tests/test_program_loader.py tests/test_program_catalog_and_selection.py tests/test_workout_session_state.py -k 'adaptive_gold' -q`
- `cd apps/web && npm test -- --run`

Expected:
- all suites pass

**Step 3: Clean up temporary databases**

Run:
- `rm -f apps/api/test_local_phase1_fidelity.sqlite3 apps/api/test_local_phase1_fidelity_docs.sqlite3`

Expected:
- temp files removed

**Step 4: Commit**

```bash
git add docs/Master_Plan.md docs/archive/ai-handoffs/GPT5_MINI_HANDOFF.md docs/archive/ai-handoffs/GPT5_MINI_EXECUTION_BACKLOG.md docs/audits/Master_Plan_Checkmark_Audit.md docs/current_state_decision_runtime_map.md docs/DOCUMENTATION_STATUS.md
 git commit -m "docs: record phase1 fidelity-first execution evidence"
```
