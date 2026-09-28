# Security architecture and qualification

Status: **Source-scoped descriptive baseline plus Proposed controls**. Source revision: `df9965232ce731f8234d222acc526a90bc6be620`. [Audit registry](../evidence/README.md#audit-reference-and-migration-plan), [threat model](threat-model.md), [urgent recovery brief](urgent-account-recovery.md), [implementation plan](../plans/urgent-account-recovery.md). No live production security certification or new scan is performed here.

## Current boundaries and controls

Browser Next.js calls API through source-defined Caddy/Next rewrites. Credentials are bearer JWTs stored in localStorage. FastAPI verifies the configured JWT algorithm/subject and loads current user; reviewed personal-data queries use server-derived ownership. Password hashes and random hashed/expiring reset tokens are stored in PostgreSQL; sequential single-use exists. These positive source controls do not prove cross-account safety of every endpoint or deployed settings.

Offline source/importer/knowledge writers and production artifact consumers remain distinct. Enumerated IDs/containment checks protect inspected loader paths; runtime does not use raw references or LLM prescription inference. Docker/operator/database privileges are separate from ordinary API permission. Logging/backup copies are not protected by API ownership filters.

| Area | Source-established state | Proposed required control | Qualification state |
|---|---|---|---|
| Recovery capability | HTTP credential under exposure flag or incomplete SMTP. | No HTTP token path; generic acknowledgment, unavailable/failed-delivery credential unusable. | Known source defect; S1 qualification missing. |
| Signing/lifecycle | Placeholder default accepted; JWT only sub/exp; old sessions survive reset. | Explicit validated key, approved rotation; atomic consumption/session revocation. | Source conditions known; live key/session conditions unknown; S2 mechanism Proposed. |
| SMTP | Configured delivery with optional STARTTLS lacking verified context. | Required verified transport/approved HTTPS link origin; bounded timeout, no insecure fallback. | Source defect conditional on active SMTP attacker; effective transport unqualified. |
| Diagnostics | Generic rejected inputs can evade key-name redaction. | Secret-free validation/log output and private diagnostic access/retention. | Source finding; deployed logs not inspected. |
| Abuse/ingress | No repo-level auth/recovery rate control established; source Caddy HTTP, external edge unknown. | Qualified all-ingress/origin rate/transport/proxy policy; protect expensive work. | Coverage/capacity unknown; Proposed controls. |
| Development operations | Email-targeted wipe unauthenticated only when flag enabled; self-wipe requires auth+flag. Default off. | Production-disabled state separately verified; explicit endpoint capabilities. | Not an unconditional public vulnerability; live state unknown. |
| Data/schema/testing | Scoped ORM reads; startup and Compose both own DDL; destructive helpers can inherit ordinary database target. | Reviewed migration-only DDL/runtime grants; enforce explicit disposable targets before DDL. | User isolation positive in reviewed paths; grants/tool safety not qualified. |
| Browser/history | localStorage token; reused session-key caches; unchecked login next destination. | Approved session/redirect/origin strategy; user/occurrence cache clearing, reliable retries. | Conditional compromise/redirect concerns; no XSS or token leak established. |
| Packaging/recovery | Broad API copy/input boundary; basic plaintext caller-relative pg_dump. | Positive image-input boundary; manifests/access/encryption/retention and compatible isolated restore. | Deployed image/backup jobs unknown; not proven absent external controls. |

## Remediation and authority

SEC-S1 closes recovery/configuration/transport/logging without history schema changes. SEC-S2 separately qualifies proposed auth_version, concurrency, legacy-token cutover and rate coverage. Do not imply recovery approval accepts that specific mechanism. Both can be reviewed independently of complete documentation migration; each needs minimum safe verification/recovery.

[ADR-009](../adr/0009-production-schema-and-data-authority.md) proposes schema/grant/test authority; [ADR-010](../adr/0010-account-recovery-and-auth-lifecycle.md) proposes auth lifecycle. Further session-storage/ingress/backup decisions require their own bounded design, effective-state review and acceptance. No configuration, secret/key rotation, account/session inspection or deployment occurs here.

Only sanitized enabled/disabled/present/missing/unknown states enter production-control evidence; see the urgent brief. Do not dump environments, credentials, URLs containing tokens, logs or user records. Fake mail/synthetic accounts and explicitly isolated PostgreSQL qualify behavior, not the live edge. Threat hypotheses, verified source findings, conditional exposure and qualified live controls are separate statuses.

Managed export remains **failed** for directory privacy; no `.codex` permission changes or sealed scan are claimed. No complete dependency/CVE, ingress, personal-data, backup or deployed-image audit exists. Report vulnerabilities privately per [SECURITY.md](../../SECURITY.md); this documentation publication does not create new advisories or messages to third parties.
