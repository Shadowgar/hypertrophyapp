# Personal WorkoutApp capability crosswalk and delivery sequence

**Owner-approved direction:** 2026-10-21. **Technical placement:** Proposed; preserve the one [M0–M6 milestone roadmap](milestones.md). **Implementation/release acceptance:** no approval implied by this planning document. Requirements source: [personal WorkoutApp supplement](../requirements/personal-workoutapp-2026-10-21.md), [original 80-ID catalog](../requirements/catalog.md) and [product contract](../requirements/product-contract.md).

This is a **cross-cutting integration map**, not a new roadmap, milestone, replacement for existing source contracts, mandate to enable frozen metadata scoring, or permission to merge draft UX work. Every package requires scoped implementation authorization, isolated testing, real-device qualification when applicable, safe migration plan when applicable and separate deployment authorization.

## Grounded starting point on 2026-10-21

- [PR #107](https://github.com/Shadowgar/hypertrophyapp/pull/107) merged the M4 integrated Customized workflow into GitHub main on 2026-10-20. Its release evidence records remaining baseline-red qualification and production cutover preconditions. A GitHub merge is **not proof of the current production image or schema**.
- [Issue #103](https://github.com/Shadowgar/hypertrophyapp/issues/103) documents firsthand iPhone gym defects: approximately two-minute load symptom (not measured backend latency), lb/kg inconsistency, absent visible direct known-1RM pathway, crowded/moving set UI and confusing grouped-session title. It demands objective investigation and preservation of existing logs.
- [Issue #105](https://github.com/Shadowgar/hypertrophyapp/issues/105) governs end-to-end mobile/desktop redesign order. Draft [PR #108](https://github.com/Shadowgar/hypertrophyapp/pull/108) contains static sketches/interaction specifications and is **not** a merged or qualified UI implementation. Final owner acceptance of those visuals and subsequent separately scoped implementation permission remain distinct from approval of this product-vision update.
- The existing M0–M6 authority and unaccepted technical ADRs stay unchanged. Do not mark feature aspirations as already shipped because a mockup or import/export experiment exists.

## Existing milestone ownership — without new top-level milestones

| Existing workstream | New personal requirements integrated here | Scope and dependency |
| --- | --- | --- |
| **M0** safety, history and operational integrity | PERS-001, 002, 011, 019, 020 | Protect effective history, authorization, safe imports, test DB isolation, backups/privacy, honest release evidence. Cross-cutting guards apply immediately; no unapproved production work. |
| **M1** Authored source/execution fidelity | PERS-004, 005, 007, 008, 009 | Keep source work/dose/relationships fixed. Time-limited Authored handling may reschedule remaining work, not remove prescribed work. Exercise instructional assets require provenance. |
| **M2A** load and performed-exposure intelligence (parallel with M2B) | PERS-006, 008, 009 | Comparable exercise/setup/equipment identity; verified actual work; load advice and optional known-1RM; bounded increments; override and correction replay. |
| **M2B** actual dates and allocation (parallel with M2A) | PERS-003, 004, 005 | Rotating shifts, daytime/split sleep, actual dates, missed sessions, realistic times and pause/resume. Feasibility/duration estimation can be separate scoped packages. |
| **M3** performance analytics and recommendations | PERS-006, 010, 014, 015, 017, 018 | Progress, exercise comparison, conditioning and honest trend analytics; preparation for recovery context. Do not present growth or causal-optimality scores. |
| **M4** Customized lifecycle and scope | PERS-003, 004, 005, 014 | Personal time/goal preferences modify generated plans only via explicit Customized consent, deterministic hard constraints and versioned plan preview/application. Existing implementation is separate from future enhancements. |
| **M5** personal-response intelligence | PERS-010, 014, 015, 016, 017, 018, 020 | Adequate longitudinal evidence, recommendation outcome/reversal, controlled comparisons, uncertainty and prospective validation. No unbounded self-modification. |
| **M6** gym UX/mobile/offline/reliability | PERS-001, 002, 005, 007, 011, 012, 013, 017, 019 | Fix gym-blocking interactions *early*, alongside other active work, not only at the end of M6; qualify realistic mobile use, upload security, future first-party iPhone/Watch and offline policy in bounded scopes. |

Items intentionally span more than one milestone; **this does not create multiple competing owners**. The package lead must name one authoritative decision module and precise shared API contract before implementation.

## Priority waves (delivery order inside M0–M6, not milestones)

### Wave A — reliable gym execution and UX acceptance

**Next first-party value.** Review #103 priority and #105/#108 visual boundaries; get explicit final visual acceptance before implementing unaccepted #108 screens. Build separately approved bounded fixes in the existing M0/M2A/M6 seams: measured Today latency, stable one-receipt set composer, lb/kg storage round trips, qualified known-1RM/recent-set/manual entry, clear rest/correction/retry/reload, correct grouped-workload disclosure. Preserve performed data and source slots.

- **Gate:** performance instrumentation identifies actual bottleneck; relevant API/unit/core/browser tests; source-prescription and effective-history nonregressions; physical iPhone Safari keyboard/save/reload/error cases, with measured before/after. Existing red CI must be candidly dispositioned.
- **Out:** new health imports, third-party app APIs, native Watch features, unaccepted training-rule changes, full application deployment without owner approval.

### Wave B — planning that fits the owner's schedule and real available time

Add independently scoped proposals for rotating shifts/daytime sleep, selected date windows, robust missed-workout continuation, personal rest/setup timing estimates, and changed-available-time options. A duration estimate should be an estimate with coverage and confidence, not a promise. No fixed global 45-minute claim when the proposed work demonstrably exceeds the target.

- **Authored:** explain overload/time conflict; retain prescribed doses and remaining slots, preserve source and completed history.
- **Customized:** provide preview of altered exercises/set counts/expected training impact, request explicit acceptance and respect hard constraints before any replacement.

### Wave C — performance, recovery and physical-capability evidence

Add equipment and comparable-variant memory, personal exercise help, meaningful strength/adherence analytics, goal-prioritized conditioning/occupational metrics, body-context trends and a very short optional subjective readiness check. Support no-data states and prioritize the actual training record over wearable-derived presentation scores. No made-up per-muscle physiological recovery percentages.

### Wave D — Apple-only measurements, manual import first

Write **a separate bounded import security/privacy spec** (format variants and selected metric types, streaming and archive/XML safety, scope preview, deduplication/retractions/selection, user data deletion, consent, timezone/source/provenance, secure storage and audit). Only then implement manually uploaded native Apple Health XML export. The upload must not accidentally grant permission to ingest all health categories simply because Apple's export contains them. No intermediary app or commercial API.

A native WorkoutApp iOS companion is a **future separate package** after this path is validated, using direct HealthKit authorization, consent, reconciliation and last-sync coverage. watchOS companion follows only if useful and accepted. Watch repetition/motion recognition needs an additional feasibility and measurement-quality study; never present it as already solved.

### Wave E — verified personal-response optimization and explainable coach

Review predeclared hypotheses, comparable actual performance, time/adherence outcomes, contextual confounders and data sufficiency before changing a program. Suggestions have confidence and reversal path; an external LLM or SaaS coach never gains runtime prescription authority. Explanations must map to actual versioned engine evidence. A request for time-limited training returns bounded options, not hidden edits.

## Complete supplemental-ID-to-milestone map

Each approved supplemental requirement is listed explicitly so later packages can trace it without interpreting grouped ranges. This maps desired ownership and dependencies only; no row is evidence of implementation or release acceptance.

| ID | Primary placement / dependencies | First acceptance focus |
| --- | --- | --- |
| PERS-001 | M0 governance, across M0–M6 | No third-party app/fitness/AI-coach API dependency |
| PERS-002 | M0-HIST + M6; #103/#105 | Stable confirmed logging, latency and retry/correction checks |
| PERS-003 | M2B / M4 | Actual dates and user-reported shift/daytime-sleep constraints |
| PERS-004 | M2B / M4 | Empirical duration and explicit source-preserving tradeoffs |
| PERS-005 | M2B / M4 / M6 | Interruption with remaining work and completed history intact |
| PERS-006 | M2A / M3 | Variant/machine/load semantics and comparable cohort negatives |
| PERS-007 | M1 / M6 | Accessible instruction/cues with source rights and no clutter |
| PERS-008 | M2A; #103 | Known-1RM baseline versus completed exposure, explicit units |
| PERS-009 | M2A / M3 | Optional effort and pain/technique missingness, no silent source change |
| PERS-010 | M3 / M5 | Qualified recovery context, no per-muscle physiological certainty |
| PERS-011 | M0-SAFE / M6 | Direct bounded Apple XML import with privacy/security/reconciliation |
| PERS-012 | M6 after PERS-011 | First-party native HealthKit consent and eventual sync |
| PERS-013 | M6 after PERS-012 | First-party Watch interaction; motion recognition separate exploratory scope |
| PERS-014 | M3 / M4 / M5 | Goal-prioritized strength/conditioning/physical benchmarks |
| PERS-015 | M3 / M5 | Optional physique/nutrition trends with measurement limitations |
| PERS-016 | M5 after qualified M2A/M2B/M3 | Predeclared and reversible longitudinal comparisons |
| PERS-017 | M3 / M5 / M6 | Evidence-linked first-party explanations without LLM prescription authority |
| PERS-018 | M3 / M5 | Performance/adherence/benchmark analytics with evidence sufficiency |
| PERS-019 | M0-SAFE / M6 | Account-scoped sensitive import, retention and deletion controls |
| PERS-020 | M3–M5 governance | Versioned evidence with constrained, tested rule adoption |

## Release acceptance matrix

| Capability family | Minimum evidence before acceptance |
| --- | --- |
| Workout execution | Real-device iPhone action flows, measured response/load, deterministic/idempotent save/retry/undo and correction reconstruction, account isolation, source-mode invariants, accessibility and explicit known exceptions |
| Timing/scheduling | Repeated week/shift/timezone/DST cases, chosen dates, measured versus predicted durations, missed-session recovery, Authored no-dose-loss and Customized explicit preview/consent |
| Progression/equipment | Same-setup/changed-setup comparability negatives; lb/kg/per-hand/assistance identity, known/e1RM versus actual evidence, abstention on missing effort, corrected/void replay |
| Recovery/analytics | Freshness/coverage flags, unknown/missingness paths, no causal claims, valid comparable cohorts, recorded recommendation overrides and outcomes |
| Apple XML ingestion | Safe file parsing (malformed/oversize/XML expansion/zip slip); selected-category import preview; secure storage/retention/deletion; idempotent imports; source/timestamp/timezone unit conversions; no health data in logs/telemetry |
| Native iOS/Watch | Opt-in permissions/revocation, native-device tests, offline/eventual sync, conflict/deletion reconciliation, same canonical backend account and history, no browser HealthKit assertion |
| Longitudinal personal learning | A priori questions/outcomes/windows, sufficiency guard, confounder/holdout discipline, versioned recommendation trial, non-adoption on ambiguous results, reversibility |

## No-go and non-goals

Do not integrate competitors or their APIs, third-party fitness exporters, paid/cloud LLM decision services, generalized leaderboards/social, large meal-tracking product, faux biological age, fabricated hypertrophy/recovery measurements, always-on surveillance, unvalidated exercise recognition or a second training-record authority. None should distract from completed reliable training. No copyrighted exercise videos/source programs may be copied without a qualified right to use them.

## Sequence and handoff

1. **Documentation-only**: preserve owner-approved direction, requirements, roadmap crosswalk and next bounded coder brief on their own reviewable branch; no feature activation.
2. **Owner reviews the documents**, plus independently approves or amends the final PR #108 visual interaction package when ready.
3. **Coder's immediate next task is read-only scoped preparation** using [next handoff](../operations/next-coder-handoff-2026-10-21.md): audit actual branch/issues, compare overlaps, propose the smallest gym-use correction package and tests. It must not start a new platform architecture or erase existing work.
4. **After the owner accepts the particular implementation plan**, authorize an isolated implementation PR; maintain source/history/data invariants. Production deployment and backup/migrations require separately named authorization.
5. Iterate one bounded capability at a time with real user feedback and accurate evidence, then proceed through the waves only as applicable to existing milestones.

The original [milestones roadmap](milestones.md), [contract](../requirements/product-contract.md), [scoped agent rules](../../AGENTS.md), [documentation hierarchy](../README.md) and [database safety lock](../../DB_SAFETY_LOCK.md) govern every package.
