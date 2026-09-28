# Deferred security hardening proposal

Status: **Proposed**; drafting/integration is not implementation/deployment approval. [Security architecture](../security/architecture.md), [threat model](../security/threat-model.md), [ADR-009](../adr/0009-production-schema-and-data-authority.md), [ADR-010](../adr/0010-account-recovery-and-auth-lifecycle.md), [SEC/OPS requirements](../requirements/catalog.md#sec) and [roadmap](../roadmap/milestones.md) control scope.

Urgent credential/configuration closure and recovery lifecycle remain independently bounded in [urgent recovery](urgent-account-recovery.md). Later packages cover session/browser cache strategy, same-origin navigation, verified ingress/proxy trust/headers, positive image-input boundaries, schema/runtime grants, backup retention/encryption/restore, observability redaction/readiness and scoped dependency review. Live controls remain unknown; no defect is called deployed or fixed here.

Each package needs its own ownership, threat prerequisites, compatibility/cutover, disposable target, automated negatives and manual effective-state/recovery evidence. Choose session mechanisms, rate-limit ownership/limits, RPO/RTO, ingress strategy and disclosure contact before affected rollout. Do not couple urgent S1 delivery closure to broad identity or architecture redesign.

[Legacy security design](../architecture/Security_Hardening_Architecture.md) and [auth expansion](../architecture/Auth_Expansion_Architecture.md) retain alternatives and deferred federation/passkey ideas, not active approval. No new broad security scan or live probe is performed. Preserve the failed managed export limitation in the [audit](../audits/2026-09-28-codebase-product-documentation-audit.md).
