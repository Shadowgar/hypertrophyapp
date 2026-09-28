# Urgent account-recovery decision brief

Date: 2026-09-28. Status: **Proposed; no live inspection or remediation authorized by this brief**. Source revision: `df9965232ce731f8234d222acc526a90bc6be620`. Evidence: [audit](../../../Hypertrophy-Audit-2026-09-28.md), [independent security findings](../../../security-worker.json), [verification notes](../../../Verification-Notes.md). This is a narrow account-recovery brief, not a new security scan.

## What the source establishes

| Established behavior | Risk and condition |
|---|---|
| `password_reset_request` returns the raw reset token when `password_reset_expose_token` is true **or SMTP is unconfigured**. Source/Compose defaults permit exposure. | High source finding: an unauthenticated requester knowing an existing email can obtain its credential under those conditions. Setting the exposure flag false alone does not close the no-SMTP fallback. Actual deployed conditions are unknown. |
| JWT configuration has a known placeholder default and no production-strength startup check. | Medium conditional finding: retaining that key permits forged authentication. Source defaults do not prove which key production uses. |
| Reset confirmation changes the password without invalidating existing access tokens. JWTs carry `sub` and `exp`; authentication checks no session version. | Medium finding: a previously stolen token can continue working until expiry. This does not establish that any token was stolen. |
| SMTP STARTTLS uses no explicit verified SSL context. | Medium finding under an active mail-path attacker: credential/reset-mail interception risk. Effective SMTP usage and upstream controls are unknown. |
| Validation logging stores rejected inputs under a generic key; field-name secret redaction does not reliably cover them. | Low finding for a log reader: password/token input can leak. No production logs were inspected. |
| No repository-level recovery throttling was established; reset confirmation hashes input with 600,000 PBKDF2 iterations. | Availability and abuse concern. Effective edge limits and origin protection are unknown; a full dependency/ingress review was not performed. |

The development wipe endpoint is flag-gated and defaults off; it is not described as unconditionally exposed. Related open-redirect follow-up remains outside this bounded recovery plan. Original security severities and qualifications remain in the audit.

## Minimum separately authorized production assessment

An authorized operator may determine the following states using approved configuration/control metadata. This pass does none of these inspections. Do not dump environments, credentials, headers, tokens, reset links, logs, database records or user sessions into evidence. Report only the listed sanitized states; use **unknown** when a state cannot be established safely.

| Question | Allowed reporting |
|---|---|
| Does the deployed artifact match the examined baseline? | matches / differs / unknown, with a nonsecret revision identifier if available. |
| Are request and confirmation routes reachable through every relevant ingress, including direct origin access? | enabled / disabled / unknown for each route and ingress. |
| Is the exposure flag enabled? Are SMTP host, username, password and sender configuration present? | enabled / disabled / unknown; individual present / missing / unknown states and derived complete / incomplete / unknown. No values. |
| Are required mail TLS and certificate-validation controls configured? | enabled / disabled / unknown; validation control present / missing / unknown. Configuration alone is not delivery qualification. |
| Does the signing-key configuration pass the approved validator and differ from known placeholders? | present / missing / unknown; validation pass / fail / unknown. No key values or key-length output. |
| Are ingress TLS, recovery rate policies and protected-origin controls effective? | controls present / missing / unknown; route coverage enabled / disabled / unknown. No claim of coverage from configuration presence alone. |

Do not make a live recovery request or send mail to a production account as part of this minimum assessment. Staging transport and negative-route qualification are separate authorized verification. A configuration mismatch or inability to establish safe states is an unresolved deployment condition, not permission to widen inspection.

## Containment and remediation choices

If effective conditions cannot rule out exposure, the recommended containment is to disable **both** reset request and confirmation across every ingress until a qualified patch and delivery path exist. Blocking only requests leaves previously issued tokens usable. This is a proposed operator action requiring separate authorization, not an action taken here. Record availability impact and a safe user-facing explanation.

The immediate [SEC-S1 plan](../plans/urgent-account-recovery.md) removes every HTTP credential-return path, validates signing configuration, verifies mail TLS, redacts validation secrets and makes request acknowledgments uniform. It needs no training-history migration or auth-version schema change. It can be reviewed and released before full documentation migration.

SEC-S2 separately qualifies atomic credential consumption, password-reset session revocation, auth-version migration and abuse controls. Until then, label prior-session persistence and concurrency/rate limitations explicitly. Key rotation is an incident option if the signing key is compromised/defaulted; it causes broad sign-out and invalidates reset-token lookup under the current hashing design. It does not undo an earlier account takeover. Do not rotate a live key automatically from this plan.

## Decisions and deployment prerequisites

Two owner decisions are genuinely unresolved:

1. **Recovery availability before qualified mail:** recommended disabled until qualification; alternatively enable after a validated delivery path and the applicable security gates. Syntactic acknowledgment must not promise delivery.
2. **Legacy JWT cutover for SEC-S2:** recommended reject versionless tokens and require fresh sign-in; alternatively a short explicitly bounded compatibility window for unchanged accounts, never accepting a legacy token after that account's reset. A compromised signing key rules out such a grace period.

Effective production configuration, ingress coverage, operator ownership and rate capacity remain unknown facts to resolve through separately authorized work. Their unknown status is not owner acceptance of risk.

Before deployment: qualify the exact patch in a disposable environment, verify secret-free negative cases and verified staging mail, approve configuration/key strategy, confirm recovery and rollback prerequisites, and qualify PostgreSQL migration/concurrency for SEC-S2. Rollback must preserve the closed recovery boundary; vulnerable rollback requires route containment or a forward fix. The [implementation plan](../plans/urgent-account-recovery.md) supplies exact gates and stop conditions.

The managed security export remains **failed**; `.codex` permissions were not changed. Neither this brief nor SQLite test evidence certifies live secrets, TLS edge, active sessions, backups, dependency coverage or production security.
