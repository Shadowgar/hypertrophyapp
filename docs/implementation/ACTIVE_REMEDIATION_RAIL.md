# Active Remediation Rail

Last updated: 2026-03-14

## Current Confirmed State

- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json` is now the real workbook-faithful Phase 1 package on this branch: authored slot fields, notes, warm-up protocol, weak-points table, week/block labels, banners, and workbook-backed video links are explicit.
- Generated-week and today runtime exercises now carry the authored Phase 1 slot fields through the loader/API boundary instead of flattening them away.
- Week and today surfaces now show authored execution detail directly: early-set RPE, last-set RPE, last-set intensity technique, rest, authored substitutions, demo link, and tracking loads when present.
- Live administered identity for the first real program is now unified on `pure_bodybuilding_phase_1_full_body`; `full_body_v1` and `adaptive_full_body_gold_v0_1` now resolve as compatibility aliases on active API/web paths.
- Runtime template source selection for the active Phase 1 path is now canonicalized to `pure_bodybuilding_phase_1_full_body`; legacy runtime IDs resolve only through compatibility normalization/fallback.
- Canonical end-to-end API smoke coverage now exists for the administered path (onboarding -> generate-week -> today -> authored detail -> log-set -> check-in/review -> history -> adaptation apply -> regenerate-week -> training-state continuity).
- `intelligence.py` remains compatibility forwarding only. It is not a valid place to add new coaching meaning.

Current product order for active implementation is:
1. workbook-faithful Pure Bodybuilding Phase 1 package
2. runtime/API carry-through of authored fields
3. visible week/today authored execution detail
4. unified administered identity on `pure_bodybuilding_phase_1_full_body`
5. end-to-end dogfooding on the real Phase 1 administered path before broader cleanup/generalization

## Latest Completed Slice

- Completed canonical-path hardening and branch-truth cleanup for the administered Phase 1 flow:
  - active API/web runtime path remains canonical on `pure_bodybuilding_phase_1_full_body` across onboarding, generated week, today/log-set, check-in/review, and history surfaces
  - path-facing API/web tests, fixtures, and snapshots now use `pure_bodybuilding_phase_1_full_body` as the default administered path
  - loader runtime-source resolution now prefers the canonical Phase 1 template source directly and keeps legacy source IDs as compatibility fallbacks only
  - one explicit canonical-path smoke test now validates adaptation/regeneration continuity and authored-field availability on the active API path
  - legacy IDs remain only in explicit compatibility handling/tests, not as primary user-path fixtures
  - added dev-only canonical dogfood reset hook: `POST /profile/dev/reset-phase1` clears user training state, clears active adaptation, and restores canonical Phase 1 selection without deleting the account
  - onboarding Developer Tools now expose this reset as `Reset Current User to Clean Phase 1`
  - focused API runs now initialize test DB config at session startup (`tests/conftest.py`) to reduce local failures caused by missing Postgres during targeted pytest runs
  - today surface now includes a direct recovery action (`Generate Week and Reload Today`) when no workout exists yet, so canonical dogfood loops can continue without manual route-hopping

## Next Recommended Action

- Execute repeated browser dogfooding on the canonical Phase 1 loop using `/profile/dev/reset-phase1`, and fix only blockers found in onboarding -> generate-week -> today/log-set -> check-in/review -> history -> adaptation/regenerate continuity.
- Keep compatibility aliases explicit at boundaries, and keep broader architecture/generalization work downstream unless directly blocking canonical-path reliability.

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

Keep one-program-first mode explicit while hardening the real administered Phase 1 user path.

This wave is about:

- keeping Pure Bodybuilding Phase 1 Full Body authoritative from onboarding artifact through runtime and week/today delivery
- enforcing `pure_bodybuilding_phase_1_full_body` as the only active administered program identity on user-facing catalog/selection paths
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
