# M0-DOC: documentation integration baseline

Status: **Implemented / awaiting owner review** on `docs/planning-baseline-2026-09-28`. Documentation integration/publication authorized 2026-09-28, starting from `64c3269dd33bea8c6a72e5a6151d985cf9ea8470`. This is not completion of M0-SEC/SAFE/HIST/CI or main integration.

Scope: activate one index/hierarchy, account for every audited inventory entry, preserve D-001–D-022 and original evidence/tasks, replace blanket AI context with ordered area scopes, retain source/runtime boundaries and publish a reviewable documentation commit. Requirements: [GEN-003 / GEN-009](../requirements/catalog.md#gen). Detailed ADRs stay Proposed.

Acceptance: resolve active local links/anchors/IDs and manifest paths; account for historical exceptions; verify original-body retention, path consumers and original asset hashes; show changed/moved/deleted paths and docs-only diff. Retain sanitized audit/inventory and migration report. No app tests, services, personal data, secrets, runtime/source/rules edits, production mutation, main merge or PR.

Evidence: [migration report](../audits/2026-09-28-documentation-authority-migration.md), [199-row registry](../audits/2026-09-28-documentation-migration-registry.md), [retained tasks](../audits/2026-09-28-legacy-task-register.md), [sanitized audit](../audits/2026-09-28-codebase-product-documentation-audit.md). Owner review, future main integration and technical decisions remain open. Recover this reversible docs change through ordinary reviewed Git history; do not reset shared/production work.
