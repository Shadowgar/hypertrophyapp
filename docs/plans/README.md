# Bounded plan registry

One forward roadmap: [M0–M6 milestones](../roadmap/milestones.md). A plan describes a bounded package; its status is independent of desired product approval, ADR status and release acceptance. Old plans retained under [archive](../archive/README.md) or successor notices are not active execution rails.

| Plan | Scope / milestone | Current status / authorization |
|---|---|---|
| [Documentation integration baseline](M0-baseline.md) | M0-DOC only: authority, inventory, context, audit references and static checks. | Implemented / awaiting owner review on this branch; this documentation work and branch publication were authorized. No whole-M0 release accepted. |
| [Urgent account recovery](urgent-account-recovery.md) | M0-SEC S1 credential/config closure, S2 lifecycle. | **Proposed**; not approved for implementation/deployment. Security work need not wait for broad history redesign. |
| [Generated stabilization](generated-stabilization.md) | M4 bounded ownership/normalization/originality consolidation. | **Proposed**; no runtime execution authorized. |
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

M0-HIST, M0-SAFE, M0-CI, M1 and M2A/M2B implementation detail awaits bounded plans; the roadmap contains their dependencies and gates. Historical task scripts cannot select approved work from old checklists. [Retained tasks](../audits/2026-09-28-legacy-task-register.md) remain pending reconciliation and do not authorize implementation.
