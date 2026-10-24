# Next coder AI handoff — read-only gym-use implementation planning

> **Subsequent authorization (2026-10-24):** This is the original planning request,
> retained as history. The owner later approved the unified design at PR #108
> `33598c3`, implementation in #110, the bounded numerical amendment/#111 and
> Today slice/#112, then this isolated integration rehearsal. Those explicit
> approvals supersede this handoff's read-only and pending-visual instructions
> for their named scopes. They do not authorize main merge or production work.
> Current qualification: [integration record](../evidence/integration-2026-10-24/README.md).

**Prepared:** 2026-10-21. **Permission:** read-only discovery and planning only. Not approval to write product code, merge, run migrations or deployment. This is a first implementation-slice proposal request under the existing M0/M2A/M6 roadmap, not a new milestone.

## Copy-ready instruction for the coding assistant

You are working in **Shadowgar/hypertrophyapp**. The product owner has approved a **first-party-only personal WorkoutApp vision**, not a new code release. Read and obey, in this order:

1. `AGENTS.md`, `DB_SAFETY_LOCK.md`, `docs/README.md`, `docs/requirements/product-contract.md`, `docs/governance/constitution.md`, `docs/governance/ai-working-rules.md`, the context manifest groups relevant to UX/Today, load, scheduling, history, generated/Custom permissions and security.
2. Owner-approved [personal requirements](../requirements/personal-workoutapp-2026-10-21.md), [capability crosswalk](../roadmap/personal-capability-crosswalk-2026-10-21.md), [original milestone roadmap](../roadmap/milestones.md), [catalog](../requirements/catalog.md) and relevant contracts.
3. [Issue #103](https://github.com/Shadowgar/hypertrophyapp/issues/103), [Issue #105](https://github.com/Shadowgar/hypertrophyapp/issues/105), [draft PR #108](https://github.com/Shadowgar/hypertrophyapp/pull/108) including [unified working-set flow](https://github.com/Shadowgar/hypertrophyapp/blob/docs/astra-ux-review-2026-10-20/docs/ux/astra-2026-10-20/unified-2026-10-21/WORKING-SET-FLOW.md), and merged [PR #107](https://github.com/Shadowgar/hypertrophyapp/pull/107). Verify live GitHub states before relying on these 2026-10-21 snapshots.

**Purpose:** Prepare the *smallest high-value, safely implementable next package* that makes the iPhone workout experience dependable while protecting current training rules and data. The owner wants a fast, stable, first-party WorkoutApp; no other fitness app or third-party fitness/AI-coach API may become an integration.

**Required read-only investigation:**

- Map the actual current Today page, load sequence, starting-load flow, weight unit conversions, active set composer, effective saved receipts, correction/undo, retry/reconciliation, rest timer, and Authored-versus-Customized differences. Distinguish what is currently implemented, only mocked in PR #108, proposed in #103, and not yet designed.
- Analyze evidence for the owner-reported approximate two-minute Today loading experience without attributing cause from code inspection alone. Propose instrumented performance measurements and a safe *disposable* browser/API test; do **not** access real user data, secrets or production DB. No actual instrumenting or launches in this planning task unless separately authorized.
- Verify current source and tests for optional known-1RM/recent-set/manual baseline, UI behavior and units. Preserve canonical kg storage, explicit lb UI preference, identity/comparability and source-prescribed sets/reps.
- Review observed moving/duplicated set inputs and saved receipts; propose a stable, accessible one-composer/one-authoritative-receipt solution with measured iPhone Safari checks.
- Check #108's visual-acceptance gate: the owner's approval of feature ideas is **not** automatic final approval of those specific sketches. Do not merge #108, code the unapproved redesign or reinterpret a static mockup as production.
- Inventory current failing/inherited CI and M4 release status. Do not declare the pipeline green, Customized live/disabled status or database migration status without relevant evidence.
- Treat new shift planning, Health import, native HealthKit/Watch, performance learning and coaching interface as later bounded packages; do not attempt to implement the whole vision in one PR.

**Return exactly these deliverables (in your reply, no code changes):**

1. A concise **source-verified current-state matrix** with references to current files/functions/tests, each row labeled Implemented/Partial/Mockup/Proposed/Unknown.
2. A **ranked 2–4 slice sequence**, identifying the *first recommended bounded implementation PR* and why; account for cross-dependencies between #103 and #108, avoiding a redesign conflict. No new milestone.
3. For the first slice only, a **design and acceptance proposal**: intended UX, command/API/data flows, authoritative decision owner, preservation of live history, error/retry states, performance budget measurement approach, tests and real iPhone qualification. List assumptions and unresolved design/approval decisions. Distinguish numerical coaching-rule research from UI correctness.
4. **Safety/permission statement:** no code commits, DB contact, migration, production actions, live data inspection, PR #108 merge, external app integration or deployment was performed. If any state was inaccessible, state that precisely rather than guess.
5. A short **implementation prompt for the following authorized coding pass**, explicitly conditional on owner review of the proposed scope/visual acceptance and naming an isolated branch and safe test environment.

**Stop after presenting the plan.** The owner and project lead will review the bounded design and explicitly authorize implementation. Do not use this instruction as permission to make changes to production code or production state.

## Review checklist for project lead

- Proposal starts from actual source and current GitHub status, not historical descriptions.
- It preserves the single M0–M6 roadmap, existing 80 requirements and the separate new PERS-001–020 owner outcomes.
- It respects Authored source immutability and explicit Customized consent; no loss of work or rewritten history.
- No third-party workout app/API/exporter is included; Apple Health import is later and first-party.
- It has observable, reproducible phone tests for load time, stable save, unit integrity and retry/correction, with missing evidence clearly called out.
- PR #108 remains separate until final visual acceptance.
- No unauthorized product implementation or production operations occurred.

**After review:** convert only the accepted first slice into a scoped implementation plan/PR. Keep subsequent slices separate. Data backup, production deployment, migration and enabled feature status always need independent authority and explicit evidence.
