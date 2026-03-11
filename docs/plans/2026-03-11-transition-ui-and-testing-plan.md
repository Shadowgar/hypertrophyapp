# Transition UI And Testing Readiness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose authored-sequence completion guidance in the web coaching UI and add lightweight internal tester docs for desktop/mobile browser dogfooding.

**Architecture:** Reuse the existing coaching intelligence panel and extend only the frontend contract already backed by the API. Keep the new transition UX additive and conditional so legacy preview states remain unchanged. Add tester docs in `docs/` without changing runtime behavior.

**Tech Stack:** Next.js/React, TypeScript, Vitest, Testing Library, Markdown docs

---

### Task 1: Add failing UI tests for transition-pending coaching state

**Files:**
- Modify: `apps/web/tests/settings.intelligence.test.tsx`
- Modify: `apps/web/tests/coaching.intelligence.routes.test.tsx`

**Step 1: Write the failing tests**
- Add preview payloads with `phase_transition.transition_pending: true`
- Assert the coaching panel shows:
  - `Program Transition`
  - `Current block complete`
  - `Rotate program`

**Step 2: Run tests to verify they fail**
Run:
```bash
cd apps/web && npm test -- --run tests/settings.intelligence.test.tsx tests/coaching.intelligence.routes.test.tsx
```
Expected: FAIL because the panel does not render the new transition section yet.

### Task 2: Implement minimal frontend contract and UI

**Files:**
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/components/coaching-intelligence-panel.tsx`

**Step 1: Extend the frontend response type**
- Add optional phase-transition fields:
  - `authored_sequence_complete`
  - `transition_pending`
  - `recommended_action`
  - `post_authored_behavior`
- Add a humanized reason/fallback message for authored-sequence completion if needed.

**Step 2: Implement the transition section**
- Render the new section only when `transition_pending` is true.
- Keep existing progression and phase messaging unchanged.
- Use rationale text from API first.

**Step 3: Run tests to verify they pass**
Run:
```bash
cd apps/web && npm test -- --run tests/settings.intelligence.test.tsx tests/coaching.intelligence.routes.test.tsx
```
Expected: PASS.

### Task 3: Add tester docs for internal browser dogfooding

**Files:**
- Create: `docs/testing/INTERNAL_TESTER_RUNBOOK.md`
- Create: `docs/testing/INTERNAL_TEST_ISSUE_TEMPLATE.md`
- Modify: `docs/plans/2026-03-11-user-testing-rollout-plan.md`
- Modify: `docs/GPT5_MINI_HANDOFF.md`
- Modify: `docs/GPT5_MINI_EXECUTION_BACKLOG.md`

**Step 1: Write concise tester docs**
- Runbook should cover:
  - desktop/mobile browser targets
  - core flows to test
  - what screenshots/data to capture
- Issue template should capture:
  - device/browser
  - exact steps
  - expectation vs actual behavior
  - coaching context / rationale / recommendation id

**Step 2: Link docs from rollout plan and handoff logs**
- Keep wording current-state and practical.

### Task 4: Run verification

**Files:**
- No code changes; verification only

**Step 1: Run targeted web tests**
Run:
```bash
cd apps/web && npm test -- --run tests/settings.intelligence.test.tsx tests/coaching.intelligence.routes.test.tsx
```
Expected: PASS.

**Step 2: If available, run a narrow build-safe check**
Run:
```bash
cd apps/web && npm run test -- --run
```
Expected: no regressions in touched coaching routes.
