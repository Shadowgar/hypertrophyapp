# Active Remediation Rail

Last updated: 2026-03-12

## Current Confirmed State

- Blocker 1 is complete.
- Blocker 2 is complete.
- Blocker 3 is complete.
- Canonical `progression_state_per_exercise` now preserves persisted `ExerciseState.fatigue_score`, so first-class user training state no longer drops exercise-level recovery-pressure input before downstream owner consumption.
- Canonical training/coaching state now preserves a derived `stimulus_fatigue_response` snapshot assembled from persisted readiness, adherence, soreness, and stall inputs, and generated-week runtime now prefers that canonical snapshot instead of recomputing it when present.
- Coach preview trace/context plumbing now surfaces canonical `coaching_state.stimulus_fatigue_response` as persisted recovery-pressure context without changing request-time progression scoring ownership.
- Weekly review now prefers canonical `coaching_state.stimulus_fatigue_response` as persisted recovery-pressure context when present, while keeping fallback SFR derivation owner-bound inside `decision_weekly_review.py`.
- Generated-week scheduler / `rules_runtime.py` trace plumbing now carries the consumed `stimulus_fatigue_response` source, so mesocycle scheduling explicitly records whether recovery-pressure context came from canonical coaching state or an upstream fallback without re-owning SFR derivation.
- Response-facing generated-week payload helpers now surface scheduler mesocycle `stimulus_fatigue_response_source` on the top-level generated-week `decision_trace`, while keeping SFR derivation and scheduler policy ownership unchanged.
- API-facing generated-week response tests now assert that shipped plans preserve scheduler mesocycle `stimulus_fatigue_response_source` on the top-level `decision_trace`.
- Tier 4A structural, doctrinal, and felt-behavior audits currently call the audited gold path ready for internal dogfood.
- `intelligence.py` is down to compatibility forwarding for the extracted recommendation, progression, weekly-review, and coach-preview seams. It is not a valid place to add new coaching meaning.

## Latest Completed Slice

- Extended `apps/api/tests/test_program_catalog_and_selection.py` so shipped generated-week API responses now assert the top-level plan `decision_trace` preserves the fallback `stimulus_fatigue_response_source` when mesocycle trace context is absent and the response must fall back to generation runtime output.
- Verified the API-facing fallback path without changing generated-week owners: payload helper ownership stays in `decision_generated_week.py`, scheduler policy stays in `rules_runtime.py`, and SFR derivation stays upstream.

## Next Recommended Action

- Extend API-facing generated-week response tests to assert the shipped plan `decision_trace` preserves `stimulus_fatigue_response_source` on scheduled-deload paths where mesocycle trace context remains present, while keeping payload-helper, scheduler-policy, and SFR-derivation ownership unchanged.

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

Preserve Tier 4A honesty while continuing owner-boundary cleanup and canonical coaching-state deepening.

This wave is about:

- keeping `decision_*` modules as the only owners of coaching meaning
- keeping `intelligence.py` as compatibility forwarding only
- deepening canonical state where new deterministic behavior actually needs richer inputs
- preventing UI and router layers from reintroducing local explanation logic

## Exact Remaining Seams

1. Canonical coaching-state depth is still thinner than the decision surface now being exposed.
   Files:
   - `apps/api/app/models.py`
   - `packages/core-engine/core_engine/user_state.py`

2. The deterministic stimulus-fatigue-response and readiness family exists, but broader owner-level consumption is still incomplete.
   Files:
   - `packages/core-engine/core_engine/decision_progression.py`
   - `packages/core-engine/core_engine/decision_weekly_review.py`
   - `packages/core-engine/core_engine/decision_coach_preview.py`
   - `packages/core-engine/core_engine/rules_runtime.py`

3. `intelligence.py` still exists as a compatibility surface and must continue shrinking, not regrowing.
   File:
   - `packages/core-engine/core_engine/intelligence.py`

4. Presentation surfaces must remain rendering-only while active implementation continues elsewhere.
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
