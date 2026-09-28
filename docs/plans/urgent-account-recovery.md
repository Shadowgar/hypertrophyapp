# Urgent account-recovery implementation plan

Date: 2026-09-28. Status: **Proposed; implementation and deployment require separate authorization**. Baseline: `df9965232ce731f8234d222acc526a90bc6be620`. Scope: M0-SEC in the [roadmap](../roadmap/milestones.md). Source findings, sanitized inspection and owner choices are in the [decision brief](../security/urgent-account-recovery.md); original qualification limits are in the [verification notes](../../../Verification-Notes.md).

## Objective and release boundaries

An unauthenticated recovery requester must never receive a reset credential. Recovery must use a qualified delivery path, avoid leaking secrets in validation output, consume a credential safely, and revoke earlier account sessions on reset. Abuse controls must cover the real request paths.

Split implementation into **SEC-S1**, a no-schema correction closing disclosure/configuration/transport boundaries, and **SEC-S2**, the independently reviewed recovery lifecycle with auth-version migration and concurrency/rate qualification. SEC-S1 is not held for full documentation migration, general history redesign or unrelated baseline-test repairs. Its remaining session/concurrency/abuse limitations must remain visible; S1 alone does not complete M0-SEC.

Do not change workout routing, generation, training artifacts, personal records, load algorithms or historical identity. Do not add a development HTTP endpoint that returns credentials. Do not include raw secrets or reset URLs in evidence. This plan performs no work against a live account, database or service.

## Affected implementation surfaces

| Surface | SEC-S1 responsibility | SEC-S2 responsibility |
|---|---|---|
| [auth router](/home/rocco/hypertrophyapp/apps/api/app/routers/auth.py) | `password_reset_request`: credential-free generic acknowledgment, safe delivery failure handling. | `password_reset_confirm`: atomic consumption/password update/revocation; `register`/`login`: issue versioned access tokens; recovery limit hooks. |
| [schemas](/home/rocco/hypertrophyapp/apps/api/app/schemas.py) | Preserve response compatibility with `reset_token: null`; no returned credential. | Keep confirm input semantics; version claim need not become a client-supplied field. |
| [mail adapter](/home/rocco/hypertrophyapp/apps/api/app/emailer.py) | `is_smtp_configured`, `send_password_reset_email`: complete configuration, verified TLS, approved link origin, bounded timeouts and sanitized error categories. | Maintain delivery controls; do not expand into a general mail/outbox rewrite. |
| [settings](/home/rocco/hypertrophyapp/apps/api/app/config.py), [Compose](/home/rocco/hypertrophyapp/docker-compose.yml), [startup](/home/rocco/hypertrophyapp/apps/api/app/main.py) | Reject missing/placeholder/insufficient signing-key configuration before serving; remove exposure permission and insecure deployment defaults. Secret-free validation output. | Require an explicit supported auth-version rollout state; no production `create_all` used as migration evidence. |
| [security helpers](/home/rocco/hypertrophyapp/apps/api/app/security.py), [authentication dependency](/home/rocco/hypertrophyapp/apps/api/app/deps.py) | Retain reset-token randomness, 30-minute TTL and current digest format for bounded compatibility. | `create_access_token` includes validated account version; `get_current_user` checks it against stored version. |
| [models](/home/rocco/hypertrophyapp/apps/api/app/models.py), `apps/api/alembic/versions/` | No schema change. | Add proposed `User.auth_version`; next available reviewed Alembic revision, not a preassigned revision number. |
| [validation/observability](/home/rocco/hypertrophyapp/apps/api/app/observability.py) | Ensure generic rejected-input keys, messages and exception details cannot retain passwords/tokens. | Secret-free rate/consumption/revocation outcome categories. |
| [reset UI](/home/rocco/hypertrophyapp/apps/web/app/reset-password/page.tsx) | Remove token autofill from HTTP response and no-SMTP development copy; retain token input from mailbox flow. Generic request acknowledgment. | Handle invalid/expired/consumed credentials and fresh-login outcome consistently. |
| [recovery tests](/home/rocco/hypertrophyapp/apps/api/tests/test_auth_password_reset.py), [observability tests](/home/rocco/hypertrophyapp/apps/api/tests/test_route_observability.py), disposable test setup | Replace credential-exposure assumptions with fake-mail capture and negative checks; provide explicit isolated settings. | Concurrent consumption, migration/legacy-token and abuse-control tests; PostgreSQL-specific qualification. |

These are bounded target surfaces, not a claim that every dependency has been audited. A newly discovered consumer or incompatible behavior is recorded and reviewed before expanding scope.

## SEC-S1: closed recovery boundary

### Proposed API, delivery and configuration behavior

For every syntactically valid reset request, return HTTP 200 with `{"status":"accepted","reset_token":null}`, whether the email is unknown, SMTP is incomplete, delivery succeeds or delivery fails. Do not return `email_failed`, account-specific 502 or a credential. Malformed inputs can return secret-free 422; rate limiting, when qualified, can return a uniform 429. This avoids explicit existence disclosure; it does not claim constant-time execution or elimination of timing inference.

Keep the nullable `reset_token` response field temporarily for client compatibility; make it always null. Ignore/deprecate `password_reset_expose_token` as an exposure permission and remove the `or not smtp_configured` fallback. Future field removal is a versioned compatibility decision. Internal test mail capture is an in-process fake, not a deployable retrieval API.

Incomplete SMTP configuration must not create a usable reset credential. For a complete qualified path, retain random-token generation, hashed storage and the existing 30-minute validity boundary. On failed delivery, make the newly issued credential unusable and acknowledge generically; record only a safe outcome category. Never persist or log plaintext tokens outside the delivery call.

The current implementation invalidates earlier tokens and commits the new row before attempting mail. The implementer must explicitly test and document how failed delivery affects a prior pending token. Proposed minimum: never leave the failed new token usable; retain existing supersession semantics for this bounded patch and disclose the availability tradeoff. Do not claim database commit and SMTP are atomic or add a full outbox merely to close disclosure. A compensation-write failure is an operational error requiring safe escalation/containment; it must not expose the token in the response.

Require a verified TLS context, such as `ssl.create_default_context()`, for STARTTLS. Missing TLS capability, failed handshake or certificate verification must prevent login and send. Do not fall back to plaintext or unverified TLS. Bound connection/operation timeouts. Use an explicitly approved HTTPS reset-link origin in production; never derive it from an untrusted request host. Tests use a fake transport without weakening deployable verification. Avoid raw exception strings in outward responses or logs.

Require an explicit signing key before serving. Proposed validator rejects known placeholders, missing keys and keys shorter than 32 bytes; the deployment process must supply a cryptographically generated key, since length alone proves no entropy. Report validation categories only. All test environments supply their own clearly nonproduction test key before settings/app imports; no implicit development signing fallback.

Remove insecure exposure defaults from deployment examples and make required TLS/delivery states explicit. Unconfigured recovery remains unavailable internally and acknowledged generically. Do not automatically rotate an existing live key: under the present design rotation invalidates JWT signatures and pending reset-token hash lookups, requiring a separately approved cutover.

### Proposed UI and validation behavior

Remove reading `response.reset_token`, development autofill and copy advertising reset without SMTP. Keep mailbox-link token entry and new-password confirmation. Display acknowledgment such as “If recovery is available for this account, check your email.” It must not assert delivery merely because the API accepted the request. Invalid/expired-token messaging must not expose account existence or echo input.

Validation logs and responses should retain safe field locations and allowlisted error codes, rather than raw `input`, rejected-value, exception context or messages containing credentials. Test nested/generic validation shapes, not only keys literally named password/token. Preserve useful nonsensitive diagnostics and current decision-route logging protections.

### Compatibility and residual risk

S1 requires no schema migration. Existing clients that accept a nullable field continue parsing; clients relying on returned credentials intentionally lose that insecure behavior. Pending email-issued tokens retain their normal validity if the key remains unchanged. No old exposed token should be represented as safe merely because the response is now fixed; containment/cutover handles that risk separately.

S1 does not revoke existing sessions on reset or prove concurrent reset consumption. Shared rate-control qualification belongs to S2; a separately verified edge policy can provide interim containment. Public rollout without effective abuse coverage needs explicit residual-risk disposition or route containment. Do not claim session revocation or complete recovery qualification from S1.

## SEC-S2: atomic recovery and session lifecycle

### Proposed schema and authentication contract

Add nonnegative integer `User.auth_version`, default 0 with an explicit migration/backfill contract. Access JWTs include `ver`; issue it from the stored user version on registration/login. Change the token helper to require that version explicitly. Authentication rejects a missing, malformed or mismatched version according to the approved legacy strategy. Never let a caller choose its own trusted account version.

Reset confirmation must perform these actions in one database transaction: revalidate an unused/unexpired credential, update the password hash, consume that credential, invalidate other outstanding reset credentials for the account, and increment `auth_version`. Commit success once. A concurrent retry/reuse produces a generic invalid/expired result, never a second successful reset. Failed transaction leaves all five effects unapplied.

Proposed concurrency mechanism: identify the candidate credential, then lock the account followed by the credential in a consistent order; re-read/recheck credential state under those locks before mutation. Every competing consumption path uses the same ordering. Account serialization prevents two different valid tokens from producing independent successful resets. Expiry is checked with a controlled clock at the authoritative decision point. Calculate expensive password hashing outside the critical lock where safe, without accepting an unvalidated credential. PostgreSQL evidence must demonstrate this contract; a read-then-update SQLite test is insufficient.

Legacy-token decision remains open. Recommended: reject versionless tokens after coordinated cutover and require fresh sign-in. Alternative: time-bounded versionless-as-zero compatibility only for accounts still at version 0, with a fixed removal deadline. A reset increments the version and must reject every older/versionless token immediately. If the signing key is compromised/defaulted, no grace period is acceptable. Record expiration and mixed-worker compatibility explicitly.

### Proposed abuse controls

Apply request/confirmation budgets before PBKDF2, password hashing and SMTP. Cover normalized account identifier and caller/network dimensions without exposing identifiers in logs; do not trust arbitrary forwarded addresses. Avoid creating account-specific public status differences.

The enforcement location may be a shared application limiter or verified ingress policy covering every route and bypass/origin path. Process-local counters are not qualified multi-worker coverage. Thresholds, burst allowances, retention and capacity require measured operational selection; this plan does not invent numbers or mandate a new Redis deployment. Test uniform rejection and recovery after the budget window. Rate-limiter failure policy must be explicit before public qualification.

### Migration and rollout compatibility

Allocate the next migration revision after checking the authorized implementation baseline; do not assume an available filename. Rehearse upgrade/backfill and recovery against an isolated PostgreSQL database containing synthetic pre-version accounts. Prove default, nullability, claim checks and transactional increments. `create_all` is not a schema-upgrade procedure or migration qualification.

Migrate the schema before enabling strict versioned authentication. Drain or otherwise prevent old workers from serving authentication once revocation is declared active: old code can ignore `ver`, and an ordinary rollback can re-enable stale sessions. Record the agreed deployment ordering, legacy treatment and recovery window. Do not delete the version column or roll back to a verifier that ignores it as routine recovery. Keep reset/JWT hashing compatibility separate from the version migration.

## Tests to add or correct

The existing `test_password_reset_happy_path` expects a response token; replace that expectation with in-process fake-mail capture while preserving reset and new-password login protection. Reuse `test_password_reset_sends_email_when_smtp_is_configured`. Replace the account-specific 502 expectation in `test_password_reset_reports_email_failure_when_delivery_is_required` with generic outward acknowledgment plus internal failure/invalidation assertions. Preserve invalid-token, email-normalization and explicitly gated dev-wipe protections.

| Criterion | Required isolated evidence |
|---|---|
| S1-A: no credential response | Existing/unknown email × complete/incomplete SMTP × delivery success/failure × exposure flag values: no response credential, uniform valid-request shape; no usable newly issued token on failed/unavailable delivery. |
| S1-B: safe settings/mail | Missing/default/short signing keys rejected without secret output; fake bad-cert/failed-STARTTLS proves no login/send; approved HTTPS origin and bounded timeout; no plaintext fallback. |
| S1-C: private diagnostics/UI | Malformed password/token payloads absent from validation responses and captured logs, including generic/nested errors; UI never autofills from API, uses generic copy and still completes the mailbox flow. |
| S1-D: maintained recovery | Mail-captured valid token resets password; old password fails; expiry/invalid token fails; delivery failure supersession and compensation outcomes covered. |
| S2-A: revocation | Previously issued access token rejected after reset; fresh login token accepted; wrong/malformed/missing version follows approved legacy contract; no cross-user version effect. |
| S2-B: atomicity | Concurrent same-token and different-token submissions yield one winning account reset; no partial password/consumption/version state on failure; expiry and retries covered under PostgreSQL. |
| S2-C: migration/rollout | Synthetic legacy upgrade, default/backfill checks, claim transition, mixed-worker exclusion and safe recovery rehearsal. SQLite results labeled separately. |
| S2-D: abuse | Budget enforcement before expensive work, distributed coverage or qualified edge coverage, uniform responses, window recovery and explicit enforcement-failure policy. |

Place new transport/config/auth tests in focused modules as needed; do not claim those files already exist. Add meaningful UI verification appropriate to the changed flow. Preserve intended protections instead of deleting failing tests to obtain a green suite. Record unrelated baseline failures separately rather than silently folding them into this patch.

## Isolated verification and deployment prerequisites

Future verification requires separate authorization and a disposable checkout/environment. Use explicit disposable `DATABASE_URL` and `TEST_DATABASE_URL`, copied program/knowledge trees where imports require them, synthetic accounts, temporary logs and a guard rejecting outside-root database targets. Clear inherited production settings, disable network by default and use fake mail; any staging TLS test has a specifically approved endpoint. Never run API fixtures that drop/create tables against a guessed or inherited target.

Record source/patch revision, environment, command/procedure, criterion, result, artifact and limitations. Redact secrets at capture rather than publishing test credentials or reset URLs. Review relevant API/UI checks and configuration negative tests; SEC-S2 additionally needs PostgreSQL concurrency/migration evidence. No current draft run supplies this evidence.

Before deployment, require: approved patch and owner choices; the sanitized effective-state assessment from the brief; a provisioned validated key and qualified mail path; verified ingress/rate coverage or explicit containment; exact artifact/configuration identity; an operator-approved recovery plan. SEC-S2 needs a compatible backup/isolated restore prerequisite and reviewed migration/worker cutover. These minimal prerequisites do not require full M0-DOC/HIST completion or a complete operations-document migration.

Post-deployment qualification is separately approved, uses nonpersonal synthetic/staging checks where possible, and records only safe outcomes. Do not probe production accounts or sessions by implication from this plan. No release is marked owner-accepted without an explicit recorded acceptance decision.

## Recovery and stop conditions

For S1, recovery must keep HTTP token return disabled and preserve secret validation/verified transport. If reverting would reopen exposure, contain both recovery routes or forward-fix under separate operator authorization; do not simply restore the vulnerable artifact. A pre-patch rollback candidate needs the same disclosure gates. Key rotation and invalidation of pending credentials have explicit availability effects and are incident decisions.

For S2, favor a forward-compatible application recovery retaining `auth_version` enforcement. Ordinary schema downgrade or old-verifier rollback can defeat revocation; stop and use the approved contained recovery path. Backup/restore is not a routine undo for account changes and must not silently resurrect consumed tokens or old session validity.

Stop the affected implementation/release if:

- Source drift changes the bounded contract or target consumers; document it before extending scope.
- Any credential-return path, secret-bearing diagnostics, invalid TLS path or signing-key validation failure remains.
- Verification can reach production persistence, credentials, personal data or an unapproved network destination.
- Schema/legacy-token/worker ordering is unreviewed, PostgreSQL evidence is missing for S2, or recovery reopens exposure/revocation.
- Delivery, ingress/rate coverage or required operator recovery states cannot be established; maintain containment rather than asserting qualification.

These are proposed release gates, not permission requests or actions performed in this documentation pass. The two unresolved owner choices are identified in the brief. Approval to continue documenting, approval to implement S1/S2, and approval to deploy remain separate.
