# Active Remediation Rail

Last updated: 2026-03-13

## Current Confirmed State

- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json` is now the real workbook-faithful Phase 1 package on this branch: authored slot fields, notes, warm-up protocol, weak-points table, week/block labels, banners, and workbook-backed video links are explicit.
- Generated-week and today runtime exercises now carry the authored Phase 1 slot fields through the loader/API boundary instead of flattening them away.
- Week and today surfaces now show authored execution detail directly: early-set RPE, last-set RPE, last-set intensity technique, rest, authored substitutions, demo link, and tracking loads when present.
- Temporary 5-days-to-3-days adaptation for Pure Bodybuilding Phase 1 Full Body now emits a program-specific policy trace (`pure_bodybuilding_phase_1_full_body_5_to_3`) with preserved/merged day-role context and preservation focus.
- Generated-week `applied_frequency_adaptation` now carries that Phase 1 policy metadata forward, and active adaptation state now survives alias differences between the selected runtime template and the real onboarding package ID.
- `intelligence.py` remains compatibility forwarding only. It is not a valid place to add new coaching meaning.

## Latest Completed Slice

- Extended the Phase 1 temporary frequency-adaptation seam so the real 5-to-3 compression path is program-aware instead of generic-only.
- Preview weeks for `pure_bodybuilding_phase_1_full_body` now carry authored week/block metadata, adapted day labels/roles, action summaries, and explicit policy ID `pure_bodybuilding_phase_1_full_body_5_to_3`.
- Apply/runtime now preserves `policy_mode`, `policy_id`, and `preservation_focus` into generated-week `applied_frequency_adaptation`.
- Active adaptation state now targets the selected runtime template while preserving the real onboarding program identity, so Phase 1 apply -> generate-week works even when the selected runtime template still uses a legacy alias such as `full_body_v1`.

## Next Recommended Action

- Align the live administered full-body program identity so the product stops splitting this path across `full_body_v1`, `adaptive_full_body_gold_v0_1`, and `pure_bodybuilding_phase_1_full_body`; make the Phase 1 authored runtime the single user-facing baseline while preserving backward-compatible alias handling where needed.

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

Finish one real administered program path before reopening broad architecture-cleanup work.

This wave is about:

- keeping Pure Bodybuilding Phase 1 Full Body authoritative from onboarding artifact through runtime and week/today delivery
- keeping frequency adaptation deterministic and program-aware for this same path
- keeping `decision_*` modules as the only owners of coaching meaning
- keeping `intelligence.py` as compatibility forwarding only

## Exact Remaining Seams

1. The live full-body program identity is still split across legacy aliases and the real Phase 1 package/runtime.
   Files:
   - `apps/api/app/program_loader.py`
   - `apps/api/app/routers/plan.py`
   - `apps/web/app/onboarding/page.tsx`
   - `apps/web/app/settings/page.tsx`

2. Phase 1 temporary frequency adaptation now has the right backend policy trace, but the user-facing full-body selection path still needs to consume the same Phase 1 runtime identity cleanly.
   Files:
   - `apps/api/tests/test_program_catalog_and_selection.py`
   - `apps/api/tests/test_program_frequency_adaptation_api.py`
   - `apps/web/tests/settings.intelligence.test.tsx`

3. Broader canonical coaching-state / SFR cleanup remains secondary work and should only be pulled forward when it directly helps the administered Phase 1 path.
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
