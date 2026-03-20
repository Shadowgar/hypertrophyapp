# Active Remediation Rail

Last updated: 2026-03-20

## Current Confirmed State

- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json` is now the real workbook-faithful Phase 1 package on this branch: authored slot fields, notes, warm-up protocol, weak-points table, week/block labels, banners, and workbook-backed video links are explicit.
- `programs/gold/pure_bodybuilding_phase_2_full_body.onboarding.json` and `programs/gold/pure_bodybuilding_phase_2_full_body.json` are now canonical Phase 2 full-body assets with authored week/block identity.
- Generated-week and today runtime exercises now carry the authored Phase 1 slot fields through the loader/API boundary instead of flattening them away.
- Week and today surfaces now show authored execution detail directly: early-set RPE, last-set RPE, last-set intensity technique, rest, authored substitutions, demo link, and tracking loads when present.
- Live administered identities now include canonical Phase 1 and Phase 2 full-body programs; `full_body_v1` and `adaptive_full_body_gold_v0_1` remain compatibility aliases.
- Runtime template source selection for the active Phase 1 path is now canonicalized to `pure_bodybuilding_phase_1_full_body`; legacy runtime IDs resolve only through compatibility normalization/fallback.
- Phase 2 full-body sheet aliases now resolve deterministically to `pure_bodybuilding_phase_2_full_body`.
- Canonical end-to-end API smoke coverage now exists for the administered path (onboarding -> generate-week -> today -> authored detail -> log-set -> check-in/review -> history -> adaptation apply -> regenerate-week -> training-state continuity).
- Phase 2 runtime now emits `mesocycle.transition_checkpoint` for block-boundary deload transitions (week 5 -> week 6 checkpoint visibility).
- `intelligence.py` remains compatibility forwarding only. It is not a valid place to add new coaching meaning.

Current product order for active implementation is:
1. workbook-faithful Phase 1 + Phase 2 full-body canonical artifacts
2. runtime/API carry-through of authored fields
3. visible week/today authored execution detail
4. deterministic week/block transition behavior and trace visibility
5. end-to-end dogfooding on canonical full-body administered paths before broader cleanup/generalization

## Latest Completed Slice

- Completed bounded dogfood hardening slice (2026-03-20):
  - Today page now includes safe-area bottom padding to reduce fixed-nav overlap on mobile flows
  - Exercise detail overlay now includes a direct `Check-In` link in quick actions
  - Workout auto-load flow now avoids re-entry while soreness modal is open
  - Added focused web regression coverage in `apps/web/tests/today.runner.test.tsx` for overlay check-in affordance and soreness-dismiss behavior
  - Added progression continuity coverage for frequency windows in `apps/api/tests/test_program_frequency_adaptation_api.py::test_frequency_adaptation_preserves_progression_state_across_5_to_3_to_5_windows`
  - Validation evidence refreshed:
    - `apps/web`: `today.runner.test.tsx` and `npm run build` pass
    - `apps/api`: frequency-adaptation and focused phase2 transition/restriction tests pass
    - `packages/core-engine`: `tests/test_rules_runtime.py` and `tests/test_scheduler.py` pass

- Completed first browser dogfood run (2026-03-16):
  - Full loop verified via Docker Compose at localhost:18080: register → onboarding (Phase 1 program) → auto-generate week → load today → log set → weekly review → generate next week → history
  - Coaching engine produced real adaptive output: readiness 65, `progressive_overload_ready`, volume shift -1, load scale 0.931
  - Four non-blocking UX issues logged in `DOGFOOD_PHASE1_CHECKLIST.md`: uniform starting loads, soreness form re-trigger, bottom nav z-index, check-in nav from overlay
  - Phase C build tools (schema validation, importer v2, PDF-to-rules v2) implemented and verified
  - Master_Plan Phase B/C checkboxes updated; audit items promoted to VERIFIED

- Prior slice — completed canonical-path hardening and branch-truth cleanup for the administered Phase 1 flow:
  - active API/web runtime path remains canonical on `pure_bodybuilding_phase_1_full_body` across onboarding, generated week, today/log-set, check-in/review, and history surfaces
  - path-facing API/web tests, fixtures, and snapshots now use `pure_bodybuilding_phase_1_full_body` as the default administered path
  - loader runtime-source resolution now prefers the canonical Phase 1 template source directly and keeps legacy source IDs as compatibility fallbacks only
  - one explicit canonical-path smoke test now validates adaptation/regeneration continuity and authored-field availability on the active API path
  - legacy IDs remain only in explicit compatibility handling/tests, not as primary user-path fixtures
  - added dev-only canonical dogfood reset hook: `POST /profile/dev/reset-phase1` clears user training state, clears active adaptation, and restores canonical Phase 1 selection without deleting the account
  - onboarding Developer Tools now expose this reset as `Reset Current User to Clean Phase 1`
  - focused API runs now initialize test DB config at session startup (`tests/conftest.py`) to reduce local failures caused by missing Postgres during targeted pytest runs
  - today surface now includes a direct recovery action (`Generate Week and Reload Today`) when no workout exists yet, so canonical dogfood loops can continue without manual route-hopping
  - Today page auto-loads the workout on mount when API health is OK (same soreness/review gate as the Load Today Workout button); a guard prevents double-invoke; recovery action remains when no week exists
  - `./scripts/mini_validate.sh` when run without docker falls back to `python3 -m pytest` when `pytest` is not on PATH, so local API validation can run in more environments
  - Settings visual/snapshot and program tests now assert one-program-first UI (Program Settings, active program display, Wipe Current User Data); no program selector in current product mode

## Next Recommended Action

- Run real training weeks through the app (Phase 3 Internal Dogfooding) across the active full-body family. Canonical Phase 1 and Phase 2 paths are validated in tests; the next step is repeated real use to surface coaching-decision quality issues.
- Keep compatibility aliases explicit at boundaries, and keep broader architecture/generalization work downstream unless directly blocking canonical-path reliability.

## Next Tasks (task rail)

Use this ordered list as the single source of "what to do next." Complete one task before moving to the next; update this section when priorities change.

1. ~~**Dogfood Phase 1 path (desktop + mobile)**~~ DONE — Simulated loop completed 2026-03-16; API smoke test green; 4 failing tests corrected. See `docs/implementation/DOGFOOD_PHASE1_CHECKLIST.md`.

2. ~~**Fix dogfood blockers**~~ DONE — Test assertion mismatches fixed (progression guidance hold-load, starting-load rounding, exercise name hyphen). All API tests green.

3. ~~**Phase C build tools**~~ DONE — Schema validation (`apps/api/tests/test_schema_validation.py`), importer v2 (`importers/xlsx_to_canonical_v2.py`), PDF-to-rules v2 (`importers/pdf_doctrine_rules_v2.py`) implemented and verified.

4. **Real-use dogfooding (Phase 3 exit criteria)**
   Goal: Run actual training weeks (not simulated) through the gold path; identify coaching-decision quality issues with trace-backed reproduction data.
   Files: `docs/implementation/DOGFOOD_PHASE1_CHECKLIST.md`, `docs/ROADMAP_MASTER_DEVELOPMENT_PLAN.md` § Phase 3.
   Validation: Manual; repeated real training cycles without engineering intervention.
   Done when: Creator can complete multiple training weeks; observed issues captured with decision-trace evidence; mobile auth/session continuity blocker is resolved.

5. ~~**Activate Phase 2 program path (Wave 5)**~~ DONE — Canonical Phase 2 assets, loader/rule linkage, and transition/constraint tests now pass on active branch.

6. **Progression continuity across frequency windows (Wave 5)**
   Goal: Verify load/set progression state carries correctly across 5→3→5 frequency changes.
   Files: `packages/core-engine/core_engine/decision_progression.py`, `apps/api/tests/test_program_frequency_adaptation_api.py`.
   Validation: Focused test proving state continuity.
   Done when: Frequency compress/rejoin preserves exercise progression history.

## Next Full-Body Variant Go/No-Go Gate

Any next in-family full-body onboarding candidate must satisfy all checks before activation:

1. **Canonical artifacts present**
   - Runtime template JSON and onboarding package JSON exist under `programs/gold/`.
   - Canonical rules exist under `docs/rules/canonical/` and load with no schema errors.

2. **Authored identity contract**
   - `authored_weeks` preserve week index, week role, and block label semantics from source intent.
   - Transition checkpoints are trace-visible where deload/block boundaries are program-critical.

3. **Metadata safety baseline**
   - Active-path exercises and substitutions include required restriction/equipment metadata.
   - Placeholder substitution references are rejected by loader validation on active paths.

4. **Constraint behavior parity**
   - Time-budget and movement-restriction tests pass on early, mid, and transition-week samples.
   - Restriction-sensitive sparse metadata is deny-safe (no allow-with-warning for missing movement pattern when restrictions are active).

5. **Minimum parity matrix**
   - Test evidence exists for week 1, transition week, and final authored week generation.
   - Interruption/resume behavior and substitution consistency are covered.

6. **Release evidence linked**
   - `docs/validation/*` handoff + parity docs added for the candidate program.
   - `docs/implementation/RELEASE_CHECKLIST.md` gate rows updated with explicit pass/fail.

## Expansion Gate Decision (2026-03-20)

- **Decision:** Continue hardening mode (NO-GO for next full-body onboarding this wave).
- **Owner:** Runtime/docs consolidation wave owner.
- **Reason:** Gate 1 remains open due mobile-flow blocker (`Invalid token` session continuity) and pending additional real-use qualitative confirmation for substitution/compression behavior.
- **Re-open condition:** Move to GO only after mobile loop passes end-to-end and Gate 1 unresolved rows are closed or explicitly accepted.

## Done: Today Page Redesign

- **Implemented:** Today uses a compact list at a glance and a full-screen exercise detail overlay; Session Intent and Between-Set Coach cards are removed from the main view.
- "Do this set" on the detail overlay uses API guidance only (via `resolveGuidanceText(rationale, guidance)` or neutral prescription). Design and implementation plan: `docs/plans/2026-03-15-today-page-redesign-design.md`, `docs/plans/2026-03-15-today-page-redesign-implementation.md`.

## Closed Work Do Not Reopen Without Evidence

The following seams are considered closed unless a current-code regression is demonstrated:

- `apps/web/components/coaching-intelligence-panel.tsx` no longer fabricates transition meaning.
- `apps/web/app/settings/page.tsx` no longer rewrites transition rationale into local prose.
- `apps/web/app/week/page.tsx` uses authoritative generated-week reasoning instead of local explanation synthesis.
- `apps/web/app/history/page.tsx` no longer invents progression headlines from aggregate telemetry.
- `apps/web/app/checkin/page.tsx` renders authoritative/raw weekly-review fields instead of local coaching prose.
- `packages/core-engine/core_engine/intelligence.py` no longer owns local program/progression reason-message maps.

If a patch does not show a regression in current code, do not spend time re-auditing these seams.

## Current Target Wave

Keep full-body family mode explicit while hardening real administered user paths.

This wave is about:

- keeping Pure Bodybuilding Phase 1 + Phase 2 Full Body authoritative from onboarding artifacts through runtime and week/today delivery
- enforcing canonical administered identities (`pure_bodybuilding_phase_1_full_body`, `pure_bodybuilding_phase_2_full_body`) on user-facing catalog/selection paths
- keeping legacy IDs (`full_body_v1`, `adaptive_full_body_gold_v0_1`) as compatibility aliases only at boundaries
- keeping `decision_*` modules as the only owners of coaching meaning
- keeping `intelligence.py` as compatibility forwarding only

## Exact Remaining Seams

1. Dogfood and harden the canonical administered Phase 1 path end to end (including adaptation/regeneration continuity) across real user flows.
   Files:
   - `apps/api/tests/test_phase1_canonical_path_smoke.py`
   - `apps/api/tests/test_program_catalog_and_selection.py`
   - `apps/api/tests/test_workout_session_state.py`
   - `apps/api/tests/test_weekly_checkin.py`
   - `apps/api/tests/test_weekly_review.py`
   - `apps/api/tests/test_history_calendar.py`
   - `apps/web/tests/week.program.test.tsx`
   - `apps/web/tests/today.runner.test.tsx`
   - `apps/web/tests/history.analytics.test.tsx`

2. Broader canonical coaching-state / SFR cleanup remains secondary work and should only be pulled forward when it directly helps the administered Phase 1 path.
   File:
   - `packages/core-engine/core_engine/intelligence.py`

3. Presentation surfaces must remain rendering-only while active implementation continues elsewhere.
   Regression-watch files:
   - `apps/web/app/checkin/page.tsx`
   - `apps/web/app/history/page.tsx`
   - `apps/web/app/settings/page.tsx`
   - `apps/web/app/week/page.tsx`
   - `apps/web/components/coaching-intelligence-panel.tsx`

## Exact Forbidden Residues

These are not allowed to reappear on active paths:

- `humanizeCode(`
- `resolveReadinessLabel(`
- `Primed to push`
- `Manage fatigue carefully`
- `Recovery-first week`
- `_PROGRAM_REASON_MESSAGES`
- `_PROGRESSION_REASON_CLAUSES`
- `_PHASE_TRANSITION_REASON_MESSAGES`
- local `reason -> message` tables inside `intelligence.py`
- local UI helpers that turn raw reason codes into coaching prose
- router or façade helpers that claim rationale not emitted by a decision-family owner

## Grep-Based Acceptance Checks

Run these checks before claiming a cleanup is complete:

```bash
rg -n "humanizeCode|resolveReadinessLabel|Primed to push|Manage fatigue carefully|Recovery-first week" \
  apps/web/app apps/web/components

rg -n "_PROGRAM_REASON_MESSAGES|_PROGRESSION_REASON_CLAUSES|_PHASE_TRANSITION_REASON_MESSAGES|def humanize_program_reason\\(|def humanize_specialization_reason\\(|def resolve_coaching_recommendation_rationale\\(" \
  packages/core-engine/core_engine/intelligence.py

rg -n "Weak points: |Guidance: |Readiness [0-9]|\\+[0-9]+ set delta|x target" \
  apps/web/app/checkin/page.tsx
```

Expected result:

- the first two commands return no matches for forbidden residues
- the check-in grep returns no fabricated label patterns on the audited surface

## Bad Patch vs Good Patch

Bad patch:

- adds a new UI helper that maps codes like `progressive_overload_ready` to polished prose
- adds a dict in `intelligence.py` that turns reason codes into sentences
- adds scheduler or rules-runtime heuristics that quietly decide doctrine instead of executing owner policy
- updates tests to assert narrative labels instead of owner boundaries or raw authoritative fields
- reopens a closed Tier 4A seam because the copy feels nicer

Good patch:

- moves new coaching meaning into the correct `decision_*` owner
- keeps `intelligence.py` to direct aliasing, forwarding, or deletion-only contraction
- expands canonical state in `models.py` / `user_state.py` because an owner actually needs it
- renders `rationale`, `reason`, `decision_trace.reason_summary`, or raw values directly on UI surfaces
- updates tests to prove boundaries, traces, owner identity, and raw rendering instead of prose polish

## Done Means

A change in this wave is done only when all are true:

- the decision family owner is explicit and unchanged by routers, façades, or UI
- any new meaning lives in a `decision_*` owner or canonical state assembler, not in `intelligence.py` or web code
- forbidden grep checks stay clean
- focused tests prove the boundary that changed
- `docs/current_state_decision_runtime_map.md` and this rail still describe branch reality
