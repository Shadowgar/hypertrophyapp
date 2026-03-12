# Tier 4A Doctrinal Fidelity Gaps

Date: 2026-03-12
Branch: `main`

## Verdict

Tier 4A is not ready.

## Current Doctrinal State

- Generated-week scheduling doctrine is now contract-backed and interpreted outside `scheduler.py`.
- Workout-today selection authority now lives under `decision_workout_session.py`.
- Progression family outputs now carry `decision_trace` directly.
- The reviewed UI surfaces in this pass now prefer authoritative rationale fields over local explanation fabrication.

## Remaining Doctrinal Gaps

1. `apps/web/app/checkin/page.tsx`
   - still converts runtime codes into coaching-style language locally
   - still derives user-facing readiness meaning from score bands instead of authoritative explanation classification
   - still humanizes weekly-review guidance and fault guidance in the UI layer

2. `packages/core-engine/core_engine/intelligence.py`
   - specialization rationale resolution still depends on local explanation helper ownership instead of living entirely inside the coach-preview decision family

## Doctrinal Risk

The branch is now much closer to truthful gold-path behavior, but internal users can still be shown coaching meaning that did not originate from a named owner trace. That keeps the gold path below Tier 4A honesty.
