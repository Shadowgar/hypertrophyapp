# ADR-010: Account recovery and authentication lifecycle

Date/context: 2026-09-28 owner review. ADR status: **Proposed**. Technical approval: pending. Release owner acceptance: none. Owner approved the overall direction on 2026-09-28 subject to corrections; the technical decision below has not been accepted.

## Context

The audit establishes conditional reset-token exposure, weak signing defaults, no post-reset session revocation, unverified SMTP context and validation-secret risks. Live controls remain unknown. Current-source facts refer to application revision `df9965232ce731f8234d222acc526a90bc6be620`, via the [audit reference](../evidence/README.md#audit-reference-and-migration-plan).

## Proposed decision

Propose the bounded S1 closed HTTP recovery boundary and separate S2 atomic reset/revocation/rate qualification in the urgent plan. No credential response under any flag/SMTP condition; generic acknowledgment and verified delivery. Account auth_version is one proposed mechanism, not owner-approved architecture. Recovery-availability and legacy-token cutover decisions remain open.

## Alternatives and consequences

Flag-only mitigation leaves the no-SMTP fallback; a full authentication rewrite delays closure; or independent S1/S2 packages. Propose independent packages with explicit residual limits and safe rollback. The decision creates contract/qualification obligations; it does not authorize implementation or certify production.

## Compatibility and migration

Preserve nullable response compatibility; no-schema S1; schema/revocation S2 has reviewed backfill, worker ordering and legacy treatment. Key rotation also invalidates pending reset hashes and causes sign-out; no live action is authorized.

## Verification and relationships

No token response/log reflection; bad TLS prevents mail; validated signing config; prior JWT rejection and one-winner reset under PostgreSQL; effective abuse coverage and recovery rehearsal. Source finding is not deployment certification.

Controlling document: [plans/urgent-account-recovery.md](../plans/urgent-account-recovery.md). Milestone: M0-SEC. Historical concordance: D-005 deterministic planning is not authentication design approval; no historical auth lifecycle acceptance asserted. Existing ledger date/IDs remain unchanged; this record does not silently supersede them. A conflict requires a named accepted successor. See [ADR governance](README.md).
