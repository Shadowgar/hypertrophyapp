# Bounded plan registry

One forward roadmap: [M0–M6 milestones](../roadmap/milestones.md). A plan describes a bounded package; its status is independent of desired product approval, ADR status and release acceptance. Old plans retained under [archive](../archive/README.md) or successor notices are not active execution rails.

| Plan | Scope / milestone | Current status / authorization |
|---|---|---|
| [Flexible training progression](flexible-training-progression.md) | M2B/M6 completion-driven source sequence, optional calendar and actual execution dates. | Owner approved implementation with End Early, non-rewinding corrections, finite account reconciliation and guarded unstarted conversion, 2026-10-30. Draft PR #133; no merge/deployment. |
| [Flexible Today and workload correction](flexible-today-workload.md) | M2B/M6 same-week unstarted preview/move and source-preserving workload. | Owner-authorized implementation 2026-10-30; isolated qualification and one unmerged PR required. |
| [FERRAVIS pre-relaunch](ferravis-prelaunch.md) | Security/runtime, two UI repairs, public rebrand and guarded reset preparation. | Owner-authorized engineering and isolated qualification on 2026-10-29; two unmerged PRs. No live reset, deployment, merge or control change. |
| [Truthful onboarding and history preservation](truthful-onboarding-2026-10-26.md) | Registration observations/targets, guarded setup recovery and ordinary profile preservation. | Implemented in PR #122; isolated tests/browser qualified, final-head CI recorded on the PR; no merge/deployment. |
| [Unified UX first implementation](unified-ux-gym.md) | Account protection, shared appearance and gym execution. | Implemented in PR #110; isolated integration qualification with #111/#112 in progress. No main merge, deployment or production migration. |
| [Documentation integration baseline](M0-baseline.md) | M0-DOC only: authority, inventory, context, audit references and static checks. | Completed documentation work / owner-reviewed; repository integration pending. No whole-M0 release accepted. |
| [Urgent account recovery](urgent-account-recovery.md) | M0-SEC S1 credential/config closure, S2 lifecycle. | **Proposed**; not approved for implementation/deployment. Security work need not wait for broad history redesign. |
| [Generated stabilization](generated-stabilization.md) | M4 bounded ownership/normalization/originality consolidation. | **Proposed**; no runtime execution authorized. |
| [M0-HIST-B correction and reconstruction](m0-hist-correction-reconstruction.md) | Effective history, retained amendments, deterministic projection replay and retry/concurrency. | Primary implementation merged and owner-authorized 0020/API/web activation completed; [activation and open follow-ups](../evidence/2026-09-28-m0-hist-b-activation.md). No whole-milestone acceptance. |
| [M1-A authored source fidelity](m1-authored-source-fidelity.md) | AUTH-FID-001/005/006/007 source/import/canonical/execution preservation. | Merged PR #41 / separately owner-authorized API/web activation; [activation evidence](../evidence/2026-09-29-m1-authored-fidelity-activation.md). No whole-M1 acceptance. |
| [M1-B constraint authority](m1-authored-constraint-authority.md) | AUTH-FID-002/004 slot conflicts and explicit source-approved variant consent. | PR #42 merged / separately owner-authorized API/web activation; [activation evidence](../evidence/2026-09-29-m1-authored-constraints-activation.md). No whole-M1 acceptance. |
| [M0 security dependency remediation](m0-security-dependency-remediation.md) | BLOCK NOW Caddy/Go HTTP transport/parser findings; one pinned image. | Owner-authorized implementation / locally qualified candidate; unmerged review PR and no Caddy deployment. M1-C paused. |
| [Deferred security hardening](security-hardening.md) | Cross-release security follow-ups outside urgent closure. | **Proposed**; scope/owners and individual package approval pending. |
| [M2B-1 actual-date scheduling](m2b-actual-date-scheduling.md) | Manual current-week dates, lossless placement, occurrence revisions and Today/Week routing. | PR #76 merged / separately owner-authorized live 0021 and API/web activation completed; [activation evidence](../evidence/2026-10-06-m2b-activation.md). M2B-1 LIVE; remaining M2B stays separate. |
| [M2B-2 next-week scheduling](m2b-next-week-scheduling.md) | Current/next-week navigation, independent placements, source-successor resolution and stale preview dependencies. | Owner-authorized implementation in the 2026-10-15 attached task; implementation candidate on `m2b/next-week-scheduling`, qualification and PR review pending. No merge, deployment or live migration authorized. |
| [M2A-1 completed-exposure load intelligence](m2a-load-intelligence.md) | Authored completed-exposure load-only decisions, optional actual RPE, prefill/override and effective-history reconstruction. | Owner-authorized implementation in the 2026-10-06 merge/deploy-M2B and implement-M2A task; isolated qualification and unmerged PR required. No M2A migration/deployment or merge authorization. |
| [M2A-2 authored warm-up guidance](m2a-authored-warmup-guidance.md) | LOAD-008 source-preserving guidance and distinct warm-up receipts in Today. | Owner-authorized implementation on the deployed M2A-1 base; isolated qualification and PR review required. No merge, deployment or live data changes authorized. |

| [M4-C3B2A staging integration](m4-c3b2a-staging-integration.md) | Explicit account/session candidate admission, compact versioned consent/comparison and read-only #83-shaped calendar port. | Issue #94 / owner-authorized isolated implementation and stacked draft; synthetic qualification only. No live activation, migration, merge or deployment approval. |

| [M4-C3B2B PostgreSQL/source integration](m4-c3b2b-postgres-integration.md) | Existing candidate persistence/replay, server sessions, User-lock races and exact source reads. | Issue #97 / authorized isolated implementation and stacked draft; no production migration, merge, deployment or workout activation. Science #96 stays separate. |

| Status | Required meaning |
|---|---|
| Proposed | Reviewable intent; no execution authorization. |
| Approved for implementation | Explicit approval names package and safe target; deployment remains separately scoped. |
| In progress | Authorized implementation started; criteria/evidence tracked. |
| Implemented / awaiting qualification | Named revision exists, applicable checks or review remain open. |
| Qualified for revision/environment | Evidence supports named criteria within recorded limits; no automatic release acceptance. |
| Superseded | Named successor, preserved original rationale/tasks/evidence. |
| Completed / owner accepted | Explicit owner acceptance of this bounded scope/evidence and remaining deviations. |

Additional M0-HIST packages, M0-SAFE, M0-CI, remaining M1 slices and M2A/M2B implementation detail awaits bounded plans; the roadmap contains their dependencies and gates. Historical task scripts cannot select approved work from old checklists. [Retained tasks](../audits/2026-09-28-legacy-task-register.md) remain pending reconciliation and do not authorize implementation.

## 2026-10-21 first-party vision is not a bounded implementation plan

The owner approved [PERS-001–PERS-020 supplemental outcomes](../requirements/personal-workoutapp-2026-10-21.md) and their [placement within M0–M6](../roadmap/personal-capability-crosswalk-2026-10-21.md). This does **not** register a new executable plan or authorize the import/HealthKit, coaching, redesign or personal-response implementations. The [next coder handoff](../operations/next-coder-handoff-2026-10-21.md) is for **read-only discovery and a proposed bounded gym-UX implementation package**. Register specific future plans here only after their scope, dependencies, tests and authorization have been reviewed; deployment approval remains separate.

## Subsequent bounded authorizations — 2026-10-24 integration rehearsal

The 2026-10-21 vision/handoff text above records its original permission boundary.
The owner subsequently approved PR #108 at `33598c3` and explicitly authorized
#110 implementation, #111's provisional initial-load amendment and #112's
Today work. The current [integration plan/evidence](../evidence/integration-2026-10-24/PLAN.md)
is limited to combining #109 → #110 → #111 → #112, contract-established inherited
CI repairs and synthetic qualification. The vision itself remains outcomes only;
Home/onboarding and later layouts are the approved next stream after readiness,
not part of this rehearsal. No additional roadmap or release acceptance is created.

## 2026-10-24 bounded deployment automation

The owner authorized [continuous-release implementation and preflight](../operations/continuous-release-plan.md), including read-only production diagnosis, private backup/isolated restoration and focused release qualification. [Operational evidence/procedure](../operations/continuous-release.md) keeps exact cutover, schema changes and service activation separately owner-controlled. This is not Home/onboarding or another product roadmap.

- [Gmail password-reset delivery](../operations/gmail-password-reset.md): owner-selected configuration-only replacement for the superseded self-hosted/operator-code approaches. No new app/schema authority or automatic activation.
