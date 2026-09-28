# M0-DOC: documentation integration baseline

Status: **Completed documentation work / owner-reviewed; repository integration pending**. Documentation migration was completed at `4f8178d5fdb39b7ce2adfc3ce76c902d6b105151` and reviewed by the owner. This does not complete M0-SEC/SAFE/HIST/CI, accept ADR mechanisms or qualify a release.

Completed scope: activate one index/hierarchy, account for every audited inventory entry, preserve D-001–D-022 and original evidence/tasks, replace blanket AI context with ordered area scopes, retain source/runtime boundaries and publish a reviewable documentation commit. Requirements: [GEN-003 / GEN-009](../requirements/catalog.md#gen). Detailed ADRs stay Proposed.

Documentation criteria: resolve active local links/anchors/IDs and manifest paths; account for historical exceptions; verify original-body retention, path consumers and original asset hashes; show changed/moved/deleted paths and docs-only diff. Retain sanitized audit/inventory and migration report. These documentation criteria do not qualify runtime behavior or authorize application tests, production changes or deployment.

Evidence: [migration report](../audits/2026-09-28-documentation-authority-migration.md), [199-row registry](../audits/2026-09-28-documentation-migration-registry.md), [retained tasks](../audits/2026-09-28-legacy-task-register.md), [sanitized audit](../audits/2026-09-28-codebase-product-documentation-audit.md). Documentation review is complete; repository integration, technical decisions and milestone/release acceptance remain separate. Recover this reversible docs change through ordinary reviewed Git history; do not reset shared/production work.
