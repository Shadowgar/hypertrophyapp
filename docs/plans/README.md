# Bounded plan registry

One forward roadmap: [M0–M6 milestones](../roadmap/milestones.md). A plan describes a bounded package; its status is independent of desired product approval, ADR status and release acceptance. Old plans retained under [archive](../archive/README.md) or successor notices are not active execution rails.

| Plan | Scope / milestone | Current status / authorization |
|---|---|---|
| [Documentation integration baseline](M0-baseline.md) | M0-DOC only: authority, inventory, context, audit references and static checks. | Completed documentation work / owner-reviewed; repository integration pending. No whole-M0 release accepted. |
| [Urgent account recovery](urgent-account-recovery.md) | M0-SEC S1 credential/config closure, S2 lifecycle. | **Proposed**; not approved for implementation/deployment. Security work need not wait for broad history redesign. |
| [Generated stabilization](generated-stabilization.md) | M4 bounded ownership/normalization/originality consolidation. | **Proposed**; no runtime execution authorized. |
| [M0-HIST-B correction and reconstruction](m0-hist-correction-reconstruction.md) | Effective history, retained amendments, deterministic projection replay and retry/concurrency. | Primary implementation merged and owner-authorized 0020/API/web activation completed; [activation and open follow-ups](../evidence/2026-09-28-m0-hist-b-activation.md). No whole-milestone acceptance. |
| [M1-A authored source fidelity](m1-authored-source-fidelity.md) | AUTH-FID-001/005/006/007 source/import/canonical/execution preservation. | Merged PR #41 / separately owner-authorized API/web activation; [activation evidence](../evidence/2026-09-29-m1-authored-fidelity-activation.md). No whole-M1 acceptance. |
| [M1-B constraint authority](m1-authored-constraint-authority.md) | AUTH-FID-002/004 slot conflicts and explicit source-approved variant consent. | PR #42 merged / separately owner-authorized API/web activation; [activation evidence](../evidence/2026-09-29-m1-authored-constraints-activation.md). No whole-M1 acceptance. |
| [M0 security dependency remediation](m0-security-dependency-remediation.md) | BLOCK NOW Caddy/Go HTTP transport/parser findings; one pinned image. | Owner-authorized implementation / locally qualified candidate; unmerged review PR and no Caddy deployment. M1-C paused. |
| [Deferred security hardening](security-hardening.md) | Cross-release security follow-ups outside urgent closure. | **Proposed**; scope/owners and individual package approval pending. |

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
