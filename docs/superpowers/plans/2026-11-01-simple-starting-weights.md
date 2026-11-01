# Simple starting weights implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make existing deterministic starting-load help discoverable beside set entry without requiring technical setup for manual logging.

**Architecture:** Reuse AuthoredCalibration, server initial-calibration commands and useAtlasSet. Place optional help after the stationary composer; disclose estimate-only setup progressively. Customized retains its independent consent/calibration authority, with an explicit unsupported-estimate boundary.

**Tech Stack:** React/TypeScript, Vitest, existing FastAPI/core policies, disposable persistence and Playwright.

**Spec:** Owner's 2026-11-01 assignment; PERS-002/PERS-008; Issues #103/#105 approved unified UX; docs/contracts/proposals/authored-starting-load-v1.md.

## Global constraints

- No production writes, migrations, deployments, release-control changes or merge.
- Preserve Authored prescriptions, compiler inputs and artifacts byte-for-byte.
- Preserve source/history/consent/recovery gates and the single saved-set authority.
- Saved lb/kg preference; pounds by default; canonical kg internally, exact pending commands.
- No new training calculation or machine assumptions. Estimates are provisional, history wins.

## Review focus

- Preference changes and reload must not reinterpret a previously entered benchmark magnitude.
- Interrupted benchmark saves must retain the original command and setup despite later UI changes.
- A pending benchmark must not create a second authority or block safe manual actual logging.
- Bodyweight, unsupported source targets and Customized must not acquire an Authored formula.
- Completing the first set must not move Save Set or hide an unresolved benchmark retry.

### Task 1: Inline choices and unit-safe benchmark presentation

**Files:** apps/web/components/authored-calibration.tsx, apps/web/components/atlas-runner.tsx, apps/web/tests/starting-load.test.tsx.
**Interfaces:** Existing InitialCalibrationCommand and AtlasRunner props stay unchanged; no API/schema change. Benchmark reports remain separate from actual sets.

- [x] Add failing UI tests: three visible choices, manual logs without setup, progressive setup, unsupported/history boundaries, original-unit benchmark surviving preference changes/reload and exact retries.
- [x] Run focused tests to observe failures.
- [x] Implement inline choices below composer, progressive estimate-only setup, and saved-preference presentation without reinterpreting underlying units. Keep one calibration component, pending commands accessible, and separate Customized disclosure.
- [x] Run starting-load, atlas-set, appearance and Customized/Today nonregressions; typecheck and lint changed files.
- [x] Commit the implementation and focused tests.

### Task 2: Isolated journey qualification and review

**Files:** Focused browser harness/evidence under docs/evidence/simple-starting-weights-2026-11-01; narrowly justified test changes only.
**Interfaces:** Task 1 consumes unchanged server calibration/logging endpoints and persisted canonical-kg receipts.

- [x] Verify explicit disposable targets and use synthetic accounts only. Capture before/after desktop and 390×844 mobile.
- [x] Exercise Phase 1, Phase 2, Flexible and Customized first-set paths; known/recent/manual, absent evidence/equipment mismatch, units, interrupted retry, correction/undo/account switch and keyboard/composer stability. Record measured scope and limits.
- [x] Run focused existing API/core calibration and history tests with explicit disposable environment; compare protected compiler/artifact bytes to base.
- [x] Run fresh changed-file review, fix substantive findings with red/green tests, then create one PR linked to #103/#105 without closing either.
- [ ] Run normal qualification at final review head once; record exact head/check outcomes and physical iPhone acceptance steps. Do not merge.
