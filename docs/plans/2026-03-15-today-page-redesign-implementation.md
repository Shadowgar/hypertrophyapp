# Today Page Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the Today page redesign from `docs/plans/2026-03-15-today-page-redesign-design.md`: mobile-first list at a glance, tap row to open exercise detail (full-screen overlay), simplified top section, no Session Intent or Between-Set Coach cards on main view, single “Do this set” line on detail using only API-sourced guidance.

**Architecture:** Single Today page (`apps/web/app/today/page.tsx`) keeps all state; a full-screen overlay (or slide-up panel) shows exercise detail when `selectedExerciseId` is set. List is a compact row list; tapping a row sets `selectedExerciseId`; back clears it. No new routes initially so we avoid URL/refresh complexity; structure is iOS-push-friendly for a later route split.

**Tech Stack:** Next.js 14 App Router, React, Tailwind, existing `api` and `ExerciseControlModule`, `resolveGuidanceText` from `@/lib/today-guidance` (pass-through only; no new prose).

**Design reference:** `docs/plans/2026-03-15-today-page-redesign-design.md`

---

## Task 1: Add detail overlay state and back control

**Files:**
- Modify: `apps/web/app/today/page.tsx`

**Step 1.1:** Add state for selected exercise.

In the component state block (around line 366), add:
```ts
const [selectedExerciseId, setSelectedExerciseId] = useState<string | null>(null);
```

**Step 1.2:** Add a test that expects the list to be present and that no detail overlay is visible when no exercise is selected.

File: `apps/web/tests/today.runner.test.tsx` (or add to existing test block).

Add after workout is loaded:
```ts
expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
expect(screen.getByText(/Load Today Workout|Arms & weak points|Full Body/i)).toBeInTheDocument();
```
(Adjust selector to match “session title” or list content after load.)

**Step 1.3:** Run test.

Run: `cd apps/web && npm run test -- --run today.runner -t "today" `
Ensure the test runs (may already pass).

**Step 1.4:** Commit.

```bash
git add apps/web/app/today/page.tsx apps/web/tests/today.runner.test.tsx
git commit -m "refactor(today): add selectedExerciseId state for detail overlay"
```

---

## Task 2: Simplify top section (header, one button, one line, alerts)

**Files:**
- Modify: `apps/web/app/today/page.tsx` (top block and after-load block)

**Step 2.1:** Replace the “Runner Status” / “API ok” block with header only.

Current block (approx lines 633–647):
- Remove the `telemetry-header` that shows “Runner Status” and “API {health}”.
- Keep: `<h1 className="ui-title-page">Today</h1>` and add date next to it (e.g. format `new Date().toISOString().slice(0, 10)` or `toLocaleDateString`).
- Keep the single full-width “Load today’s workout” button; ensure min-height 44px (e.g. `min-h-[44px]`).

**Step 2.2:** After load, show only one line: session title + total progress.

When `workout` is set:
- Replace any “Session Intent” card and “Between-Set Coach” card in the main view with a single line, e.g.:
  - `{workout.title} · {workoutProgress?.completed ?? 0}/{workoutProgress?.planned ?? 0} sets`
- Do not render `SessionIntentCard` or `BetweenSetCoachCard` in the main (list) view.

**Step 2.3:** Keep the existing message/alert block for “Sunday review required”, “No workout”, and “Go to Check-In” / “Generate Week and Reload Today” as-is (single block).

**Step 2.4:** Run tests.

Run: `cd apps/web && npm run test -- --run today.runner visual.routes.snapshot`
Update snapshot if needed: `npm run test -- --run visual.routes.snapshot -u`

**Step 2.5:** Commit.

```bash
git add apps/web/app/today/page.tsx apps/web/tests/
git commit -m "feat(today): simplify top section to header, one button, one progress line"
```

---

## Task 3: Replace exercise blocks with compact list rows

**Files:**
- Modify: `apps/web/app/today/page.tsx`

**Step 3.1:** Replace the current `workout.exercises.map` that renders full cards with a list of compact rows.

For each exercise:
- One tappable row: `min-h-[44px]`, `onClick={() => setSelectedExerciseId(exercise.id)}`.
- Row content: exercise name (use `resolveExerciseName(exercise, swapIndexByExercise)`), then sets progress `{completed}/{exercise.sets}`, then optional one line prescription `{exercise.rep_range[0]}-{exercise.rep_range[1]} reps @ {exercise.recommended_working_weight} kg`.
- Do not include: “Exercise Slot” label, status-dot, RPE, technique, rest, “Authored substitutions” inside the row. No `ExerciseExecutionDetails` or `ExerciseControlModule` in the list row.

**Step 3.2:** Ensure list is scrollable (e.g. parent has overflow or layout that allows scroll). Keep visual separation between rows (border or spacing).

**Step 3.3:** Run tests; update any assertions that expected full exercise cards on the main view.

Run: `cd apps/web && npm run test -- --run today.runner`
Fix assertions that break (e.g. “Current context”, “Today follows…”, or specific exercise content that now only appears in detail).

**Step 3.4:** Commit.

```bash
git add apps/web/app/today/page.tsx apps/web/tests/
git commit -m "feat(today): replace exercise cards with compact tappable list rows"
```

---

## Task 4: Add full-screen exercise detail overlay

**Files:**
- Modify: `apps/web/app/today/page.tsx`

**Step 4.1:** When `selectedExerciseId` is set, render a full-screen overlay (e.g. `fixed inset-0 z-50 bg-background` or similar) that contains:
- A back control (button or link) with “Back” or arrow, `onClick={() => setSelectedExerciseId(null)}`, min touch target 44pt.
- Resolve `exercise = workout.exercises.find(e => e.id === selectedExerciseId)`; if missing, clear `selectedExerciseId` and do not render overlay.

**Step 4.2:** Inside the overlay, in order:
1. **Title:** Exercise name (with link to guide if `activeProgramId` and guide path exist), e.g. `ExerciseTitleLink` or equivalent.
2. **Prescription:** “{sets} sets · {rep_range[0]}-{rep_range[1]} reps @ {recommended_working_weight} kg”.
3. **Authored execution block:** Early-set RPE, last-set RPE, technique, rest, tracking loads, authored substitutions, demo/video link — only when present in API payload; compact labels + values; no invented copy.
4. **“Do this set” line:**  
   - If `liveRecommendationByExercise[exercise.id]`: use `resolveGuidanceText(recommendation.guidance_rationale, recommendation.guidance)`; if empty, show “Next set: {recommended_reps_min}-{recommended_reps_max} reps @ {recommended_weight} kg”.  
   - Else if `setFeedbackByExercise[exercise.id]`: use `resolveGuidanceText(feedback.guidance_rationale, feedback.guidance)`; if empty, show planned prescription for next set.  
   - Else: show “Do {rep_range[0]}-{rep_range[1]} reps @ {recommended_working_weight} kg this set”.  
   - Do **not** use the phrase “Log the opening set to unlock within-session load guidance” unless it comes from the API.
5. **Set logging:** Render `ExerciseControlModule` for this exercise (same props as current: exerciseId, totalSets, defaultRestSeconds, recommendedWorkingWeight, repRange, initialCompletedSets, onSetComplete).
6. **Actions:** Video (open media URL if present), “I don’t have this equipment” (opens substitution flow for this exercise), Notes (toggle notes for this exercise). Min 44pt touch targets.

**Step 4.3:** Reuse existing substitution modal and soreness modal; when opening substitution from detail, set `swapTargetExerciseId` to `selectedExerciseId` (or the exercise id) so the same picker works; after selection, remain in detail overlay.

**Step 4.4:** After logging a set, optionally show last-logged set and next recommendation in a short block using only API `guidance`/`rationale`; keep “Do this set” and log control visible.

**Step 4.5:** Remove the old inline “Between-Set Coach” card and “Session Intent” card from the main view if not already removed in Task 2. Remove the hardcoded “Log the opening set to unlock within-session load guidance” from any remaining code path (e.g. `BetweenSetCoachCard` or fallback in detail); use only the logic in Step 4.2.4.

**Step 4.6:** Run tests.

Run: `cd apps/web && npm run test -- --run today.runner today.substitution today.logset`
Ensure: load workout, tap row opens detail, back closes it, set logging works, substitution from detail works.

**Step 4.7:** Commit.

```bash
git add apps/web/app/today/page.tsx apps/web/tests/
git commit -m "feat(today): add full-screen exercise detail overlay with Do this set and set logging"
```

---

## Task 5: Copy and compliance audit

**Files:**
- Grep: `apps/web/app/today/page.tsx`, `apps/web/lib/today-guidance.ts`
- Modify: `apps/web/app/today/page.tsx` if any forbidden residue found

**Step 5.1:** Run forbidden-residue greps from ACTIVE_REMEDIATION_RAIL.

```bash
rg -n "humanizeCode|resolveReadinessLabel|Primed to push|Manage fatigue carefully|Recovery-first week" apps/web/app apps/web/components
rg -n "unlock within-session load guidance" apps/web/app/today/
```
Expected: no matches. If “unlock within-session load guidance” appears, remove or replace with API-sourced/neutral copy per design.

**Step 5.2:** Confirm all guidance text in Today page comes from `resolveGuidanceText(rationale, guidance)` or from planned prescription (rep range, weight). No new local coaching prose.

**Step 5.3:** Commit if any change.

```bash
git add apps/web/app/today/page.tsx
git commit -m "chore(today): remove forbidden copy and ensure API-only guidance"
```

---

## Task 6: Update and add tests

**Files:**
- Modify: `apps/web/tests/today.runner.test.tsx`
- Modify: `apps/web/tests/coaching.intelligence.routes.test.tsx` (Today test)
- Modify: `apps/web/tests/visual.routes.snapshot.test.tsx` if needed
- Modify: `apps/web/tests/today.substitution.test.tsx`, `apps/web/tests/today.logset.test.tsx` if they assert on old layout

**Step 6.1:** Today runner test: assert list is visible after load; assert tapping an exercise row opens the detail (e.g. dialog or overlay with exercise name); assert back closes detail; assert set logging still works (log set, then verify feedback or progress). Remove assertions that depended on “Current context”, “Session Intent”, or “Between-Set Coach” on the main view.

**Step 6.2:** Coaching intelligence routes test: the “Today page shows Load Today Workout and does not show coaching panel” test should still pass; ensure no expectation for “Generate coaching preview” or “Current context” on Today.

**Step 6.3:** Substitution and logset tests: if they click “Load Today Workout” then look for an exercise by name or “I don’t have this equipment”, update to: after load, click the first exercise row to open detail, then trigger substitution or log set from within the overlay.

**Step 6.4:** Update visual snapshot if layout changed.

Run: `cd apps/web && npm run test -- --run visual.routes.snapshot -u`

**Step 6.5:** Run full web test suite.

Run: `cd apps/web && npm run test -- --run`
Expected: all tests pass.

**Step 6.6:** Commit.

```bash
git add apps/web/tests/
git commit -m "test(today): update tests for list + detail overlay redesign"
```

---

## Task 7: Update docs

**Files:**
- Modify: `docs/implementation/ACTIVE_REMEDIATION_RAIL.md`
- Modify: `docs/current_state_decision_runtime_map.md`

**Step 7.1:** In ACTIVE_REMEDIATION_RAIL, under “Planned: Today Page Redesign”, add a short “Done” note: e.g. “Implemented: Today uses list + detail overlay; Session Intent and Between-Set Coach cards removed from main view; ‘Do this set’ on detail uses API guidance only. See `docs/plans/2026-03-15-today-page-redesign-design.md`.”

**Step 7.2:** In current_state_decision_runtime_map, update the bullet that says “Today page redesign is planned” to “Today page redesign implemented: list + detail overlay, simplified top, API-only guidance (see design doc).”

**Step 7.3:** Commit.

```bash
git add docs/implementation/ACTIVE_REMEDIATION_RAIL.md docs/current_state_decision_runtime_map.md
git commit -m "docs: mark Today page redesign as implemented"
```

---

## Execution handoff

Plan complete and saved to `docs/plans/2026-03-15-today-page-redesign-implementation.md`.

**Two execution options:**

1. **Subagent-driven (this session)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Parallel session (separate)** — You open a new session (e.g. in the same repo or worktree) and run through the plan with the executing-plans skill and checkpoints.

Which approach do you want?
