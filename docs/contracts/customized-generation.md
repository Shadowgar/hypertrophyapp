# Customized generation

Owner-approved mode direction; mechanisms Proposed. Governing [product](../requirements/product-contract.md), [ADR-002](../adr/0002-mode-authority-and-consent.md), [ADR-004](../adr/0004-deterministic-runtime-and-ai-boundary.md), [profile](onboarding-profile.md), [runtime authority](../architecture/runtime-authority.md), [GEN requirements](../requirements/catalog.md#gen), [M4 plan](../plans/generated-stabilization.md).

Customize My Workout requires explicit consent distinct from manual/auto program selection. Generated programs never overwrite/reinterpret authored templates. Retain D-014/D-015 Full Body v1 scope and D-019–D-022 original-design/anti-copy boundaries: source program IDs may support exercise provenance/ranking, never reconstruction of source topology. Existing Phase 1 scaffolding/fallback is a current-state deviation, not permanent target authority.

Given normalized inputs, explicit history/context and versioned rules, produce deterministic original construction with one named policy owner per decision. Hard constraints hold or the output explains infeasibility. Reduced plans/fallbacks identify changed dose/constraints and do not silently grant additional mode permission. Preview/apply use the same effective input/version snapshot and preserve previous history.

Keep doctrine, policy and engine distinct; routers/executors may orchestrate but do not invent extra policy. Floors, fatigue, weak-point bounds, recovery/re-entry rules, split expansion and numerical bands need declared owners, origins and evidence. Metadata-v2 scoring remains frozen; accounting is not scoring approval. A new split or scoring activation is separately gated.

Qualification requires replay/active-control tests, trace-versus-actual-output consistency, safe fallback/infeasibility, absence of authored source writes/layout replay, and independent program/rule lifecycle evidence. [Legacy doctrine](../architecture/GENERATED_PLAN_DOCTRINE.md), [strategy](../GENERATED_PROGRAM_STRATEGY.md) and [remediation phases](../implementation/GENERATED_PLAN_REMEDIATION_ROADMAP.md) retain detailed proposals; they do not expand accepted scope.


## Implemented application boundary, 2026-10-19

The owner authorized the existing original three-day Full Body planner to enter the actual application under clearly disclosed provisional numerical policies. This authorization is distinct from scientific approval; no external reviewer or fabricated endorsement is required for continuing implementation. `ApplicationLifecycle` reuses the immutable proposal/consent protocol, revalidates content and calendar freshness under the User lock, and atomically publishes the accepted snapshot and lifecycle event. A version-bound single acknowledgement covers all backend workload differences and provisional assumptions.

The application never supplies synthetic equipment loads, inferred historical effort or generic seed loads. Today supports user calibration and actual receipt logging; sparse/incomparable evidence produces no new load recommendation. A completed workout describes effective logged sets, not hypertrophy or a requirement to train through pain. Active snapshots cannot be rewritten; occupied/ambiguous weeks require visible resolution. [Implementation evidence](../evidence/2026-10-19-m4-application-integration.md) names what is verified and what remains unfinished.
